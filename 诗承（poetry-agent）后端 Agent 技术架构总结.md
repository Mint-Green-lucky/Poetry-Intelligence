# 诗承（poetry-agent）后端 Agent 技术架构总结

技术栈（`requirements.txt`）：FastAPI + WebSocket、`langgraph 0.2.60` + `langchain-core`、OpenAI 兼容客户端（`openai`/`langchain-openai`）、`chromadb`（向量库）+ `sentence-transformers`（embedding + reranker）、`jieba`（分词）、`aiosqlite`/`sqlite3`（持久化）。

目录结构：`backend/{agents, graph, harness, persistence, retrieval, realtime, tools, self_evolving}`，职责分离清晰。

## 1. 编排框架（LangGraph）

- `backend/graph/poetry_workflow.py` 的 `build_poetry_workflow()`：用 `StateGraph(AgentState)` 构建路由式图——`parse` 节点后按 `task` 字段做条件边（`add_conditional_edges`）分发到 7 个专属 handler 节点，各自直连 `END`。设计说明中明确指出"避免重复意图识别导致业务身份漂移"。
- `poetry_agent.py:_build_legacy_graph()`（211-224 行）保留了一套更复杂的旧图：`parse→retrieve→grade_retrieval→(rewrite|analyze)→draft→validate→(revise|end)`，带自省修订循环，当前生产路径未使用（新流程把工具编排下沉到 SpecialistAgent 内）。
- `AgentState`（`backend/agents/state.py`）为 `TypedDict(total=False)`，是节点间传递的工作记忆，明确区分"运行态"与持久层装载的 `history`/`memory`。

## 2. 多智能体设计（Specialist Agents）

- `backend/agents/specialist_agent.py`：`AgentSpec`（不可变 dataclass）定义 7 个专业 Agent（chat/generate/review/appreciate/recite/compare/expand）的身份提示词、工具白名单、输出 schema，作为"防止跨 Agent 越权的工程边界"。
- `SpecialistAgent.run()` 实现一个类 ReAct 循环：`_plan()` 生成步骤计划 → 最多 4 轮 `_decide_next_action()`（LLM 自主决策 tool/finish，带 fallback 规则）→ 调用 `tool_call` → 记录 observations/actions → 最终生成答案，并对 JSON 输出做 3 次自校验重试（`_valid`/schema 校验失败则重写）。
- `poetry_agent.py:_run_specialist()`（234-246 行）把 LangGraph 节点与 SpecialistAgent 粘合，并生成 `_lifecycle_trace()`（planning/decision/action/observation/validation/memory 六阶段可视化轨迹）。

## 3. Harness（智能体运行时基础设施）

- `backend/harness/runtime.py`：`ToolRegistry`+`ToolDefinition`（工具目录）、`PermissionPolicy`（allow/confirm/deny 服务端权限边界，客户端不可覆盖）、`HookManager`（pre_tool/post_tool/tool_error/pre_response/post_response 五个扩展点）、`PromptBuilder`（按固定分区拼装 Prompt）。
- `backend/harness/tool_executor.py`：`ToolExecutor.execute()` 是工具调用的统一边界，串联权限检查→pre_tool hook→执行→post_tool/tool_error hook，并记录延迟、错误类型、可重试性。
- `backend/harness/context_manager.py`：`ContextManager.hydrate()` 按字符预算（`max_history_chars=6000`）做历史压缩注入（`_fit_history_budget`），并生成 `context_meta`（已加载/已注入消息数、是否发生压缩）。
- `backend/harness/memory_manager.py`：基于规则关键词（"我喜欢"、"容易错"、"下次"等）从对话中抽取长期记忆，分类为 preference/weakness/revision 三种 kind，无 embedding，纯 SQLite。
- `backend/harness/workspace_manager.py`：管理 conversation/branch 工作区快照。

## 4. 检索 / RAG

- 混合检索：`backend/retrieval/hybrid_retriever.py`（jieba 分词 + 词频加权关键词检索，支持体裁/朝代过滤）+ `backend/retrieval/vector_store.py`（Chroma 持久化 + `bge-small-zh-v1.5` embedding 的语义检索）。`poetry_agent.py:_retrieve()`（387-412 行）按可配置权重融合（`hybrid_score = keyword_weight*lexical + vector_weight*semantic`，权重来自自演化策略）。
- Reranker：`CrossEncoder("BAAI/bge-reranker-base")`（poetry_agent.py 180-187 行），可选加载，失败不阻塞启动。
- Self-RAG 式重写：`_retrieve_for_task()`（358-375 行）当 top 分数 < 0.12 时自动改写检索词重试；`_after_grade()`（425-426 行）+ 旧图 `_rewrite` 节点实现"检索评分不足→改写→重新检索"的反思循环，最多 2 次。
- 数据集特化：CCPC/中华诗歌库做正文检索，FSPC 提供情感范例检索（`find_sentiment_examples`），PQED 用于质量评分标尺，CRRD 提供平仄/韵部字典。

## 5. 工具即评测（Tools）

`backend/tools/`：`rhythm_checker.py`（逐字平仄+押韵规则校验，产出 score/errors）、`quality_scorer.py`（基于 PQED 人工标注做流畅度/连贯性/意义性打分，含 few-shot 抽样）、`sentiment_matcher.py`（五级情感推断）。这些既是 Agent 可调用工具，也是自我验证信号，接入 `TOOL_REGISTRY` 与 `_tool_call()` 分发（poetry_agent.py 297-346 行）。

## 6. 反思/自省（Self-critique）

- `_validate()`（454-478 行）对答案做多维校验：必需/禁止栏目、检索相关性阈值、原诗逐句引用覆盖率，返回 `passed`+`reasons`；`_revise()` 据此生成带修正指令的重写 prompt。当前生产图未启用自动二次调用（`_after_validate` 恒返回 "end"，注释说明为避免卡顿）。
- SpecialistAgent 内部也有独立的 3 轮 JSON schema 自修复循环（163-170 行）和创作体裁字数硬校验 `_generate_form_error()`。

## 7. 持久化 / 记忆

> **2026-09-07 更新**：为记忆系统补充了向量化召回，并新增了默认关闭的 MCP 接入层，详见本节末尾和第 11 节。

`backend/persistence/agent_store.py`（SQLite）：`runs`（运行归档）、`messages`（按 branch 存对话）、`memories`（长期记忆，含 kind/confidence）、`tool_runs`（工具调用日志）、`conversations`/`branches`/`artifact_versions`（支持分支 fork/rollback、作品版本管理，类似 git 分支模型）、`strategies`/`evolution_events`（自演化策略：`maybe_evolve()`/`maybe_rollback()` 根据用户反馈自动调整检索 top_k、向量权重、格律阈值，用固定验证集评估增量后决定是否 promote/reject/rollback）。

**记忆向量化（新增，详见第 11 节）**：`MemoryManager` 现在可选注入 `VectorPoetryStore`，长期记忆在写入 SQLite 的同时增量向量化，支持跨 task 的语义召回。

## 8. 流式与实时

- 主链路：`main.py` 的 `/ws/agent/{session_id}` WebSocket，逐 token 转发 LangGraph 执行中的 `node`/`token`/`status`/`complete` 事件（事件驱动的 `event_callback`）。
- `backend/realtime/realtime_voice_bridge.py`：`RealtimeBridge` 桥接阿里 DashScope/OpenAI Realtime 协议（`wss`），支持文本流 `generate_text()` 和 `/ws/live` 全双工语音（音频增量转发、ASR 转写、打断/VAD 事件转发），是独立于主 Agent 链路的语音通道。

## 9. Prompt 工程

Prompt 分为多层：模块级硬契约（`MODULE_SYSTEM_PROMPTS`）、任务设计（`TASK_DESIGNS` 定义 role/output/required/forbidden 栏目）、专家判据（`TASK_EXPERT_CRITERIA`）、体裁硬约束表（`FORM_CONSTRAINTS`，覆盖近 30 种词牌格律），并用 `PromptBuilder.build()` 做分区拼装，强调"身份隔离"（禁止跨任务复用模板）和"证据闭环"（原句-判断-效果）。

## 10. 与主流开源 Agent 项目的技术栈对比

选取三个定位不同、但都有一定代表性的开源项目做对比：`datawhalechina/hello-agents`（面向教学的智能体原理教程 + 配套框架）、`HKUDS/nanobot`（超轻量个人 AI Agent 运行时）、`shareAI-lab/learn-claude-code`（从零复刻 Claude Code 这类"agent harness"的分阶段教程）。三者代表了智能体工程里三种常见取向：**教学向的范式全覆盖**、**产品向的极简单循环**、**基础设施向的 harness 分层拆解**。诗承在架构选择上更接近第三者的思路，但落地在一个具体的垂直领域上。

| 维度 | 诗承（本项目） | hello-agents | nanobot | learn-claude-code |
|---|---|---|---|---|
| 编排模型 | LangGraph `StateGraph`，按任务类型路由到专属节点；每个专属节点内部再跑一个类 ReAct 循环 | 教程覆盖 ReAct / Plan-and-Solve / Reflection 等多种范式，框架层可选 LangGraph、AgentScope 等 | 单一 Agent Loop（非图），消息进来→模型决定是否调用工具→直接执行，刻意不做重量级编排层 | 核心也是单一 Agent Loop（消息→工具调用→结果回填→循环），复杂能力都是在这个循环外挂子系统，循环本身17个阶段都不变 |
| 权限与钩子 | 有：`PermissionPolicy`（allow/confirm/deny，服务端强制）+ 5 个 Hook 扩展点（pre/post tool、tool_error、pre/post response） | 教程未强调独立权限层，更偏"如何写出一个能跑的 Agent" | 未见独立权限审批层，工具调用由模型自主决定是否执行 | 有专门阶段（s03 权限规则/审批门、s04 Hook 扩展点），思路与诗承的 harness 高度一致 |
| 上下文管理 | 按字符预算做历史裁剪注入（`max_history_chars`），生成 `context_meta` 记录是否发生压缩 | 作为独立章节讲"Context Engineering"，偏方法论 | 有上下文压缩进度展示、按对话轮次统计 token、展示缓存命中率，工程化程度比诗承更细 | 有专门阶段（s08）做长对话的上下文压缩 |
| 记忆系统 | 规则关键词抽取（偏好/弱项/修订三类），纯 SQLite，无向量化 | 独立章节覆盖"记忆与检索"，含 RAG 存储机制 | 有名为 "Dream" 的长期记忆机制，跨会话持久化 | 有专门阶段（s09）做记忆的筛选/抽取/固化 |
| 多智能体 | 7 个角色化 Specialist Agent，各自工具白名单隔离，但**无跨 Agent 委派/协作机制** | 有完整的多智能体仿真、协作项目案例（第 13-15 章） | 支持"内联子智能体"，可在不离开当前任务的情况下跨会话协调 | 有专门阶段（s13）实现持久化队友、原子任务认领、任务级 worktree，协作能力比诗承成熟 |
| 检索增强（RAG） | 混合检索（关键词+向量）+ CrossEncoder 重排 + Self-RAG 式改写重试，深度绑定诗词领域数据集 | 有独立 RAG 章节，通用方法论覆盖较广 | 依赖工具化的网络搜索/抓取，没有独立向量检索栈 | 未强调 RAG，聚焦通用 harness 能力 |
| 工具协议 / MCP | 固定领域工具注册表（格律校验、质量打分、情感匹配），**未接入 MCP** | 覆盖 MCP、A2A、ANP 等通信协议教学 | 完整 MCP 支持（Stdio + HTTP 两种传输），并自动发现注册工具 | 有专门阶段（s14）做 MCP 插件支持 |
| 长任务 / 后台调度 | 无独立任务图或后台调度机制 | 未强调 | 支持定时任务（cron）、后台网关模式持续运行 | 有专门阶段（s10 持久任务图、s11 后台执行、s12 定时调度） |
| 自我验证 / 反思 | `_validate()` 多维校验 + `_revise()` 修订循环（生产链路目前未自动触发二次修订）；工具评分（格律/质量/情感）本身也是验证信号 | Reflection 是核心范式之一，作为通用能力教学 | 未强调独立反思阶段 | 有目标驱动的独立评估门（s17），但侧重工程闭环而非内容质量判定 |
| 独有能力 | **自演化策略**（`strategies`/`evolution_events`，据用户反馈自动调参并可回滚）+ 对话分支 fork/rollback（类 git 模型）+ 语音全双工实时通道 | 无对应产品化组件，偏教学 | 无自演化，偏个人助理场景 | 无自演化，偏通用 harness 工程能力 |

**结论**：诗承没有照搬任一开源项目，而是从 learn-claude-code 这类"harness 分层"思路里借鉴了权限、钩子、上下文管理、记忆管理的工程骨架，用 LangGraph 替代了它的单循环做业务路由，又叠加了 hello-agents 教程里系统讲解的 RAG/Reflection 能力并做了诗词领域的深度定制。相比这三者，诗承在**长任务持久化（任务图/后台调度）、MCP 通用工具协议、多 Agent 协作（子智能体委派）**这几块仍是明显短板；而**自演化策略**和**对话分支版本管理**则是三者都没有的、诗承特有的能力。

## 11. 新增能力：记忆向量化 + MCP 接入（2026-09-07）

对照第 10 节的差距分析，按优先级补上了"记忆向量化"和"MCP 接入"两项，原则是**只加不改**：不动 7 个 Specialist Agent 现有的工具白名单和产出格式，向量库/外部工具不可用时行为与改动前完全一致。

**记忆向量化**：[memory_manager.py](backend/harness/memory_manager.py) 的 `MemoryManager` 新增可选的 `VectorPoetryStore` 注入。`extract()` 在写入 SQLite 的同时，把同一句记忆增量 upsert 进 Chroma 的独立 `memory` 集合（[vector_store.py](backend/retrieval/vector_store.py) 新增的 `upsert()` 方法，与语料库的 `poetry`/`ccpc`/`fspc`/`pqed` 集合互不相干、互不影响）。新增的 `semantic_recall()` 按 session 过滤做向量相似度检索，`merge_recall()` 把它作为精确召回（原有 `recall()`，按 task 精确匹配）之后的补充项去重追加，`poetry_agent.py:run()` 里原来的 `kwargs["memory"] = self.memory_manager.recall(...)` 相应改成"精确召回 → 语义召回 → 合并"三步。当向量库不可用或没有语义命中时，合并结果与旧版逐字节相同；只有向量库可用且命中语义相关但跨 task 的历史记忆时，才会多出最多 5 条补充项。

**MCP 接入**：新增 [mcp_client.py](backend/harness/mcp_client.py)——不引入官方 `mcp` SDK，手写了一个基于子进程 stdio 的极简 JSON-RPC 2.0 客户端（`MCPServerConnection`：`initialize` 握手 → `notifications/initialized` → `tools/list` → `tools/call`，后台线程读 stdout、按请求 id 匹配响应、超时可控），风格延续项目里 `chromadb`/`sentence-transformers` 那种"惰性可选依赖、失败即降级"的写法。`MCPToolManager` 把配置好的 Server 发现到的工具，以 `mcp__{server}__{tool}` 命名动态登记进 [runtime.py](backend/harness/runtime.py) 的 `TOOL_REGISTRY`（新增 `ToolRegistry.register()` 方法），权限统一给 `confirm`（复用既有的 `PermissionPolicy`，外部工具默认需要显式批准才能执行）。`poetry_agent.py` 的 `_tool_call()` 新增一个 `mcp__` 前缀分发分支，转发到 `self.mcp.call()`。

**默认关闭、零侵入**：`MCP_ENABLED` 环境变量默认 `false`，且需要项目根目录存在 `mcp_servers.json`（示例见 `mcp_servers.json.example`）才会真正尝试连接。任何一个条件不满足，`MCPToolManager.connections` 就是空字典，不向 `TOOL_REGISTRY` 添加任何条目，现有 7 个 Specialist Agent 的 `AgentSpec.tools` 白名单没有改动、行为完全不变。要让某个 Agent 用上 MCP 工具，需要显式把 `mcp__server__tool` 加进对应 `AgentSpec.tools`——这一步本次没有做，留给后续按需接入。

**已知限制**：`_tool_call()` 和 `ToolExecutor.execute()` 是同步调用链，MCP 请求走的也是同步阻塞 I/O（带超时），如果真的启用并被某个 Agent 调用，会在等待外部 Server 响应期间阻塞当前请求所在的事件循环线程；默认关闭时不存在这个问题，真正启用后建议只接入低延迟的本地 MCP Server。

## 核心文件路径

`backend/agents/poetry_agent.py`、`backend/agents/specialist_agent.py`、`backend/agents/state.py`、`backend/graph/poetry_workflow.py`、`backend/harness/{runtime,tool_executor,context_manager,memory_manager,workspace_manager,mcp_client}.py`、`backend/persistence/agent_store.py`、`backend/retrieval/{hybrid_retriever,vector_store}.py`、`backend/realtime/realtime_voice_bridge.py`、`backend/tools/*.py`、`backend/main.py`、`mcp_servers.json.example`。
