# © 2026 BUPT_Mint-Green
# All rights reserved.

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from backend.harness.runtime import HOOK_MANAGER, PROMPT_BUILDER, TOOL_REGISTRY

ModelCall = Callable[[dict, str, str], Awaitable[str]]
ToolCall = Callable[[str, dict], Any]


@dataclass(frozen=True)
class AgentSpec:
    """专业 Agent 的能力卡（Profile）。

    Profile 将身份提示词、工具白名单和输出契约放在同一个不可变对象中，
    既供 LangGraph 路由后的执行器使用，也作为防止跨 Agent 越权的工程边界。
    """

    task: str
    name: str
    tools: tuple[str, ...]
    schema: tuple[str, ...]
    system_prompt: str


SPECS = {
    "chat": AgentSpec("chat", "诗词知识问答 Agent", ("hybrid_retrieval", "reranker", "original_verifier"), ("direct_answer", "evidence", "knowledge_points"), "你只负责诗词知识问答。直接、充分地回答当前问题；若输入为诗句，可围绕用户所问补充字义、格律、意象、手法与必要背景。允许展开解释和举证，但每一段都必须服务于问题，不要转做创作、批改、背诵、比较或出题。"),
    "generate": AgentSpec("generate", "诗歌灵感创作 Agent", ("form_constraint", "version_writer"), ("title", "poem", "creation_note"), "你只负责原创诗歌创作。不要解释需求、不要讲无关知识、不要输出创作前言。输出必须是题目、完整诗作和创作说明；创作说明可以写一至两段，充分说明意象组织、主题表达、情感推进与构思取舍，但不得展示后台词谱和校验规则。"),
    "review": AgentSpec("review", "诗作批改 Agent", ("rhythm_checker", "quality_scorer", "sentiment_matcher", "version_writer"), ("form_check", "line_reviews", "revised_poem", "change_summary"), "你只负责诗作批改。必须逐句指出优点、具体问题、修改理由并给出建议句，可以充分解释修改收益与取舍；不要写成脱离修改目标的泛化赏析，不要夹带无关知识。"),
    "appreciate": AgentSpec("appreciate", "诗词赏析 Agent", ("hybrid_retrieval", "reranker", "sentiment_matcher"), ("scene", "close_readings", "emotion_progression", "techniques"), "你只负责诗词赏析。必须围绕当前文本充分细读，引用原句说明意象、炼字、修辞、节奏、结构和情感推进，可结合必要背景深化理解；不要修改原诗，不要创作，不要出题。"),
    "recite": AgentSpec("recite", "诗歌背诵默写 Agent", ("keyword_retrieval", "original_verifier", "weakness_memory"), ("metadata", "verified_text", "memory_units", "exercises", "answers"), "你只负责诗歌背诵默写。必须核准篇目与原文，充分提供意群切分、画面联想、首字线索、易错字提示、接句和填空练习及答案；不要把主要篇幅写成普通赏析。"),
    "compare": AgentSpec("compare", "诗词比较 Agent", ("hybrid_retrieval", "reranker", "original_verifier"), ("targets", "dimensions", "core_conclusion"), "你只负责诗词比较。必须同时围绕两个对象展开充分的逐维对照，引用双方原句解释题材、意象、语言、结构、手法与情感异同；只有一个对象时只提示补充第二个对象。"),
    "expand": AgentSpec("expand", "诗词扩展训练 Agent", ("keyword_retrieval", "sentiment_matcher", "weakness_memory"), ("instructions", "questions", "answers", "rubric"), "你只负责诗词扩展训练。必须围绕当前诗词或知识点生成数量充足、层次清楚的训练题，并给出详细答案、解题依据与可执行评分点；不要写成脱离题目的普通赏析。"),
}


class SpecialistAgent:
    def __init__(self, spec: AgentSpec):
        self.spec = spec

    async def run(self, state: dict, model_call: ModelCall, tool_call: ToolCall) -> dict:
        records: list[dict] = []
        context: dict[str, Any] = {}
        source = (state.get("content") or state.get("poem") or state.get("query") or "").strip()
        plan = self._plan(source, state)
        context["plan"] = plan
        observations: list[dict] = []
        actions: list[dict] = []
        remaining_tools = list(self.spec.tools)
        max_tool_rounds = min(4, len(remaining_tools))
        task_steps = [
            {"id": f"step-{index + 1}", "title": title, "status": "pending"}
            for index, title in enumerate(plan.get("steps", []))
        ]

        for round_index in range(max_tool_rounds):
            decision = await self._decide_next_action(
                state, source, plan, observations, remaining_tools, model_call
            )
            actions.append({
                "type": "decision",
                "round": round_index + 1,
                "decision": decision["action"],
                "reason": decision["reason"],
            })
            if task_steps:
                task_steps[min(round_index, len(task_steps) - 1)]["status"] = "in_progress"
            if decision["action"] == "finish":
                break
            tool = decision["tool"]
            output = tool_call(tool, {
                **state,
                "source": source,
                "plan": plan,
                "observations": observations,
            })
            failed = isinstance(output, dict) and output.get("ok") is False
            status = "failed" if failed else "completed"
            summary = self._summary(output)
            context[tool] = output
            actions.append({"type": "tool_call", "tool": tool, "status": status})
            observations.append({
                "source": tool,
                "status": status,
                "summary": summary,
                "output": output,
            })
            records.append({"tool": tool, "status": status, "summary": summary})
            if task_steps:
                task_steps[min(round_index, len(task_steps) - 1)]["status"] = (
                    "failed" if failed else "completed"
                )
            remaining_tools.remove(tool)
            if not remaining_tools:
                break

        output_schemas = {
            "chat": (("direct_answer", "直接回答"), ("evidence", "原句依据"), ("knowledge_points", "专属知识点")),
            "generate": (("title", "题目"), ("poem", "完整诗作"), ("creation_note", "创作说明")),
            "review": (("form_check", "体裁检查"), ("line_reviews", "逐句批改"), ("revised_poem", "完整修改稿"), ("change_summary", "修改说明")),
            "appreciate": (("scene", "诗境概括"), ("close_readings", "原句细读"), ("emotion_progression", "情感推进"), ("techniques", "手法效果")),
            "recite": (("metadata", "篇目信息"), ("verified_text", "准确原文"), ("memory_units", "意群记忆"), ("exercises", "背诵默写"), ("answers", "参考答案")),
            "compare": (("targets", "比较对象"), ("dimensions", "逐维对照"), ("core_conclusion", "核心异同")),
            "expand": (("instructions", "训练说明"), ("questions", "题目"), ("answers", "参考答案"), ("rubric", "评分要点")),
        }
        task_rules = {
            "chat": "先判断问题意图。若用户要求介绍作者，direct_answer 应覆盖姓名、字/号、朝代、生卒、主要经历、文学地位、诗风、代表作与重要生平节点；evidence 给出与问题直接相关的作品、原句或可靠依据；knowledge_points 可补充释义、语法、格律、意象、手法或背景。除非用户只问一个简单事实，否则应给出有层次的完整回答，不设机械字数上限，但禁止堆砌无关材料。",
            "generate": "title 只放诗题；poem 只放完整诗作；creation_note 可写一至两段，每段围绕意象组织、主题表达、情感推进或构思取舍展开，可适当具体分析作品中的关键词。词谱、字数、句数、平仄、押韵等属于后台校验信息，creation_note 禁止复述这些规则，也禁止声称‘严格依照某格式创作’。",
            "review": "form_check 充分判断体裁、句式、韵律与整体完成度；line_reviews 逐句写明优点、问题、建议句及理由；revised_poem 放完整修改稿；change_summary 解释关键改动、整体收益及必要取舍。",
            "appreciate": "scene 完整概括诗境与观察视角；close_readings 选择足够多的关键原句深入细读；emotion_progression 说明情感如何分层推进；techniques 结合具体措辞解释手法及效果，可补充与文本直接相关的必要背景。",
            "recite": "metadata 放完整篇目信息；verified_text 放准确原文；memory_units 按意群提供画面、首字和易错字提示；exercises 提供由易到难的多种默写题；answers 给出逐题对应答案。",
            "compare": "targets 明确双方对象及比较尺度；dimensions 至少从题材、意象、语言、手法、结构或情感中选择多个有效维度，并逐维引用双方原句；core_conclusion 总结最关键的共性、差异及其表达效果。",
            "expand": "instructions 说明训练目标与适用层次；questions 提供数量充足且难度递进的题目；answers 给出对应答案与原句依据；rubric 为主观题提供明确、可执行的评分点。", 
        }
        templates = {task: f"只输出一个可被 JSON.parse 解析的 JSON 对象，不要 Markdown 代码块或对象外文字。对象格式固定为：{json.dumps({key: f'{title}的实质内容' for key, title in fields}, ensure_ascii=False)}。所有字段必须是非空字符串，不得增加、缺少或更改字段；字段内容禁止重复一级栏目，不得输出‘暂无’。" for task, fields in output_schemas.items()}
        templates[self.spec.task] += task_rules[self.spec.task]
        memory = self._relevant_memory(state.get("memory", []), source)
        history = state.get("history", [])[-8:]
        prior = "\n".join(f"{item.get('role', 'user')}：{item.get('content', '')}" for item in history)
        followup_rule = "这是继续追问。继承已确认的约束、作品版本、用户否定意见和未完成目标；只完成本轮追问，禁止重复上一轮。" if state.get("followup") else "这是新任务。"
        variation = {
            "chat": "把输入诗作为知识问答对象，只解释用户问到的概念、字词或规则；若只给诗而没有问题，概括可追问的知识点。不得形成完整赏析、批改意见、背诵题或仿作。",
            "generate": "把用户输入视为不可遗漏的创作要求。所选体裁是硬约束：若为词牌必须按该词牌创作；题材大类与细分题材必须成为全诗核心叙事或核心意象，不能只在说明中提及；情感大类与细分情感必须决定措辞、节奏和结尾走向。逐项核对体裁、题材、情感后另写原创作品，不得复述、赏析或批改输入。只允许三个一级标题，每个标题恰好出现一次，标题下直接填写内容，禁止在内容内部再次输出“一、二、三”或空栏目。",
            "review": "把输入诗视为待修改稿，以可操作问题为核心，逐句给出保留或修改判断并形成修改稿。不得用大段审美赏析代替诊断，不得出题。",
            "appreciate": "把输入诗视为不可改动的文学文本，从最突出的炼字、视角、声音、时空或结构切入，解释原句如何产生审美效果。不得修改原诗、仿写或出题。",
            "recite": "把输入诗视为要准确记忆的定本，保留原文而做意群切分、线索和默写练习。不得改写原句，不得把主要篇幅用于赏析。",
            "compare": "把输入识别为比较材料，必须存在两个对象才开展对照；只有一首时仅指出缺少第二对象并给出补充方式，严禁把单篇赏析冒充比较。",
            "expand": "把输入诗视为命题材料，围绕具体字词、诗句、手法和情感设计分层题目、答案及评分点。不得输出普通赏析、修改稿或仿作。",
        }[self.spec.task]
        isolation_rule = f"当前唯一身份是“{self.spec.name}”。当前任务只允许使用本轮用户输入以及当前任务分支的历史；其他 Agent 曾选择的体裁、词牌、题材、情感和正文一律无效。除 generate 外，界面创作筛选条件不得成为回答依据；当前输入未出现的具体篇名、词牌或作者，禁止从工具噪声、旧任务或长期记忆中擅自引入。即使七个功能收到相同文本，也必须按照本身份重新解释用途，禁止复制其他功能的栏目和正文。"
        specificity_rule = "准确清晰要求：先识别用户真正询问的对象与范围，再给结论；每个事实性判断必须由当前输入原句或工具检索结果直接支持，不得虚构篇名、卷次、原句、作者、格律或文献记录。检索无结果不等于文献不存在，只能表述为‘当前检索结果未发现’。原文、作者、题名存在冲突时明确指出不同版本或不确定性，不作武断断言。每个分析结论必须回指当前输入中的具体诗名、作者、词语或原句，并紧接着解释证据与结论的关系。先结论后依据，一句话只表达一个要点，删除重复、空泛和换到任意诗词仍成立的套话。工具结果只作证据，不得喧宾夺主。"
        creative_constraints = f"体裁={state.get('form','不限')}；主题={'、'.join(state.get('themes',[])) or '不限'}；情感={state.get('emotion','不限')}。" if self.spec.task == "generate" else "本任务无创作筛选条件。"
        user_prompt = PROMPT_BUILDER.build([
            ("输出契约", templates[self.spec.task]),
            ("会话状态", followup_rule),
            ("身份与任务隔离", isolation_rule),
            ("准确性与证据", specificity_rule),
            ("当前任务执行标准", variation),
            ("可审计计划", json.dumps(plan, ensure_ascii=False)),
            ("任务步骤状态", json.dumps(task_steps, ensure_ascii=False)),
            ("用户输入", source),
            ("业务约束", creative_constraints),
            ("当前分支历史", prior),
            ("当前工作状态", state.get("work_state", {})),
            ("相关长期记忆", memory),
            ("工具观察", context),
            ("最终要求", "如果不符合格式，重写后只输出最终答案。"),
        ])
        response_envelope = HOOK_MANAGER.emit(
            "pre_response", {"system_prompt": self.spec.system_prompt, "user_prompt": user_prompt}
        )
        answer = await model_call(
            state,
            response_envelope.get("system_prompt", self.spec.system_prompt),
            response_envelope.get("user_prompt", user_prompt),
        )
        for attempt in range(3):
            schema_valid = self._valid(answer)
            form_error = self._generate_form_error(answer, state) if self.spec.task == "generate" else ""
            if schema_valid and not form_error:
                break
            failure = form_error or "JSON 字段与内容校验失败"
            repair_prompt = f"第 {attempt + 1} 次输出未通过 {self.spec.name} 校验：{failure}。丢弃上一版并重新创作，不得只改创作说明。\n{user_prompt}\n错误输出：\n{answer}\n生成后逐句默数字数，确认完全符合词谱；仅返回符合指定字段的 JSON 对象。"
            answer = await model_call(state, self.spec.system_prompt, repair_prompt)
        answer = self._normalize_answer(answer)
        answer = self._enforce_identity(answer)
        if self.spec.task == "generate":
            answer = answer.replace("{", "").replace("}", "").replace("\\n", "\n")
        answer = HOOK_MANAGER.emit("post_response", {"answer": answer}).get("answer", answer)
        for step in task_steps:
            if step["status"] in {"pending", "in_progress"}:
                step["status"] = "completed"
        validation = {
            "schema_valid": self._valid_json_shape(answer),
            "identity_enforced": True,
            "revision_attempts": attempt if "attempt" in locals() else 0,
        }
        actions.append({"type": "respond", "status": "completed", "schema": list(self.spec.schema)})
        return {
            "answer": answer,
            "plan": {**plan, "task_steps": task_steps},
            "task_steps": task_steps,
            "observations": observations,
            "actions": actions,
            "validation": validation,
            "result_schema": self.spec.schema,
            "tool_runs": records,
            "tool_context": context,
            "agent_name": self.spec.name,
        }

    async def _decide_next_action(
        self,
        state: dict,
        source: str,
        plan: dict,
        observations: list[dict],
        remaining_tools: list[str],
        model_call: ModelCall,
    ) -> dict:
        if not remaining_tools:
            return {"action": "finish", "tool": "", "reason": "没有剩余可用工具"}
        tool_catalog = TOOL_REGISTRY.catalog(remaining_tools)
        prompt = PROMPT_BUILDER.build([
            ("角色", "你是 Agent 的行动决策器，只决定下一步是否调用工具，不生成最终答案。"),
            ("决策协议", "只输出 JSON：{\"action\":\"tool\"或\"finish\",\"tool\":\"工具名或空字符串\",\"reason\":\"一句可审计理由\"}。工具只能从可用工具中选择；已有观察足够时 finish；不得重复已调用工具。"),
            ("当前任务", self.spec.task),
            ("用户输入", source[:1200]),
            ("执行计划", json.dumps(plan, ensure_ascii=False)),
            ("已有观察", json.dumps(observations, ensure_ascii=False)),
            ("可用工具及权限", json.dumps(tool_catalog, ensure_ascii=False)),
        ])
        raw = await model_call(state, "你负责选择必要且最少的工具，禁止回答用户问题。", prompt)
        try:
            decision = json.loads(raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip())
            action = decision.get("action")
            tool = decision.get("tool", "")
            if action == "finish":
                return {"action": "finish", "tool": "", "reason": str(decision.get("reason", "证据已足够"))[:160]}
            if action == "tool" and tool in remaining_tools:
                return {"action": "tool", "tool": tool, "reason": str(decision.get("reason", "需要补充证据"))[:160]}
        except (json.JSONDecodeError, TypeError, AttributeError):
            pass
        fallback = self._fallback_tool(remaining_tools)
        return {"action": "tool", "tool": fallback, "reason": "决策输出无效，按任务安全策略选择必要工具"}

    def _fallback_tool(self, remaining_tools: list[str]) -> str:
        priorities = {
            "chat": ("original_verifier", "hybrid_retrieval", "reranker"),
            "generate": ("form_constraint", "version_writer"),
            "review": ("rhythm_checker", "quality_scorer", "sentiment_matcher", "version_writer"),
            "appreciate": ("hybrid_retrieval", "sentiment_matcher", "reranker"),
            "recite": ("original_verifier", "keyword_retrieval", "weakness_memory"),
            "compare": ("original_verifier", "hybrid_retrieval", "reranker"),
            "expand": ("keyword_retrieval", "weakness_memory", "sentiment_matcher"),
        }
        for name in priorities.get(self.spec.task, ()):
            if name in remaining_tools:
                return name
        return remaining_tools[0]

    def _valid_json_shape(self, answer: str) -> bool:
        if self.spec.task == "generate":
            return "创作说明：" in answer and "{" not in answer and "}" not in answer
        expected = self._output_schemas()[self.spec.task]
        return all(f"{index}、{title}" in answer for index, (_, title) in enumerate(expected, start=1))

    def _normalize_answer(self, answer: str) -> str:
        schemas = self._output_schemas()
        raw = answer.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            payload = json.loads(raw)
            fields = schemas[self.spec.task]
            if self.spec.task == "generate":
                title = str(payload.get("title", "")).strip()
                poem = str(payload.get("poem", "")).strip()
                note = str(
                    payload.get("creation_note")
                    or payload.get("creationnote")
                    or payload.get("creationNote")
                    or ""
                ).strip()
                if title and poem and note:
                    return self._format_generate_answer(title, poem, note)
            sections = [str(payload[key]).strip() for key, _ in fields]
            if set(payload) == {key for key, _ in fields} and all(sections) and not any("暂无" in content for content in sections):
                numerals = ("一", "二", "三", "四", "五")
                return "\n\n".join(f"{numerals[index]}、{title}\n{content}" for index, ((_, title), content) in enumerate(zip(fields, sections)))
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        if self.spec.task == "generate":
            repaired = self._repair_generate_answer(raw)
            if repaired:
                return repaired
        return raw

    @staticmethod
    def _format_generate_answer(title: str, poem: str, note: str) -> str:
        clean_title = title.strip().strip("{}")
        clean_poem = poem.replace("\\n", "\n").strip().strip("{}")
        clean_poem = re.sub(r"(?<=[。！？；])n(?=[\u3400-\u9fff])", "\n", clean_poem)
        clean_note = note.replace("\\n", "\n").strip().strip("{}")
        clean_note = re.sub(
            r"(?:严格|完全)?(?:依照|依据|按照|遵循|依)?[^。；\n]{0,20}(?:正体|词谱|格律|格式)[^。；\n]*(?:[。；]|$)",
            "",
            clean_note,
        )
        clean_note = re.sub(r"(?:每句|句式|字数|句数)[^。；\n]*(?:[。；]|$)", "", clean_note)
        clean_note = re.sub(r"[（(]?\d+(?:[、,，]\d+){2,}[字]?[）)]?", "", clean_note)
        clean_note = re.sub(r"^[；;，,、：:\s]+|[；;，,、：:\s]+$", "", clean_note).strip()
        if not clean_note:
            clean_note = "以核心意象串联主题，并通过景物变化推进情感。"
        return f"{clean_title}\n{clean_poem}\n创作说明：\n{clean_note}"

    @staticmethod
    def _repair_generate_answer(raw: str) -> str:
        text = re.sub(r"^\s*(?:一[、.]\s*)?(?:题目|完整诗作)\s*[:：]?\s*", "", raw.strip())
        text = re.split(r"\n\s*二[、.]\s*完整诗作", text, maxsplit=1)[0].strip()
        note_parts = re.split(r"\n\s*(?:三[、.]\s*)?创作说明\s*[:：]?\s*", text, maxsplit=1)
        body = note_parts[0].strip()
        note = note_parts[1].strip() if len(note_parts) > 1 else ""
        lines = [line.strip() for line in body.splitlines() if line.strip()]
        if len(lines) < 2:
            return ""
        title = re.sub(r"^[一二三四五六七八九十]+[、.]\s*", "", lines[0]).strip()
        poem = "\n".join(lines[1:]).strip()
        if not title or not poem or not note:
            return ""
        return SpecialistAgent._format_generate_answer(title, poem, note)

    @staticmethod
    def _generate_form_error(answer: str, state: dict) -> str:
        patterns = {
            "五言绝句": [5] * 4,
            "七言绝句": [7] * 4,
            "五言律诗": [5] * 8,
            "七言律诗": [7] * 8,
            "如梦令": [6, 6, 5, 6, 2, 2, 6],
            "忆江南": [3, 5, 7, 7, 5],
            "浣溪沙": [7] * 6,
            "采桑子": [4, 5, 7, 4] * 2,
            "生查子": [5] * 8,
            "菩萨蛮": [7, 7, 5, 5] * 2,
            "卜算子": [5, 5, 7, 5] * 2,
            "蝶恋花": [7, 4, 5, 7, 7] * 2,
            "渔家傲": [7, 7, 7, 3, 7] * 2,
            "鹊桥仙": [4, 4, 6, 7, 5] * 2,
            "临江仙": [7, 6, 7, 5, 5] * 2,
        }
        form = str(state.get("form") or "")
        expected = patterns.get(form)
        if not expected:
            return ""
        raw = answer.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            poem = str(json.loads(raw).get("poem", ""))
        except (json.JSONDecodeError, TypeError, AttributeError):
            return ""
        lines = [line.strip() for line in re.split(r"[\n。！？；]+", poem.replace("\\n", "\n")) if line.strip()]
        counts = [len(re.findall(r"[\u3400-\u9fff]", line)) for line in lines]
        if counts != expected:
            return f"{form}词谱应为每句字数 {expected}，当前为 {counts}"
        return ""

    def _valid(self, answer: str) -> bool:
        required = {
            "chat": ("直接回答", "原句依据", "专属知识点"), "generate": ("题目", "完整诗作", "创作说明"),
            "review": ("体裁检查", "逐句批改", "完整修改稿", "修改说明"), "appreciate": ("诗境概括", "原句细读", "情感推进", "手法效果"),
            "recite": ("篇目信息", "准确原文", "意群记忆", "背诵默写", "参考答案"), "compare": ("比较对象", "逐维对照", "核心异同"),
            "expand": ("训练说明", "题目", "参考答案", "评分要点"),
        }[self.spec.task]
        forbidden = {
            "chat": ("完整修改稿", "背诵默写", "评分要点"),
            "generate": ("逐句批改", "原句细读", "评分要点"),
            "review": ("诗境概括", "背诵默写", "训练说明"),
            "appreciate": ("完整修改稿", "背诵默写", "评分要点"),
            "recite": ("完整修改稿", "逐句批改", "手法效果"),
            "compare": ("完整修改稿", "背诵默写", "训练说明"),
            "expand": ("完整修改稿", "创作说明", "诗境概括"),
        }[self.spec.task]
        raw = answer.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            payload = json.loads(raw)
            fields = self._output_schemas()[self.spec.task]
            values = [payload[key] for key, _ in fields]
            return (
                set(payload) == {key for key, _ in fields}
                and all(isinstance(value, str) and value.strip() and "暂无" not in value for value in values)
                and not any(title in value for value in values for title in required)
                and not any(title in value for value in values for title in forbidden)
            )
        except (json.JSONDecodeError, KeyError, TypeError):
            return False

    def _enforce_identity(self, answer: str) -> str:
        if self.spec.task == "generate" and "创作说明：" in answer:
            return answer.replace("{", "").replace("}", "").strip()
        signatures = {
            "chat": ("一、直接回答", "二、原句依据", "三、专属知识点"),
            "generate": ("一、题目", "二、完整诗作", "三、创作说明"),
            "review": ("一、体裁检查", "二、逐句批改", "三、完整修改稿", "四、修改说明"),
            "appreciate": ("一、诗境概括", "二、原句细读", "三、情感推进", "四、手法效果"),
            "recite": ("一、篇目信息", "二、准确原文", "三、意群记忆", "四、背诵默写", "五、参考答案"),
            "compare": ("一、比较对象", "二、逐维对照", "三、核心异同"),
            "expand": ("一、训练说明", "二、题目", "三、参考答案", "四、评分要点"),
        }
        if self.spec.task == "generate" and "创作说明：" in answer and "{" not in answer and "}" not in answer:
            return answer.strip()
        if self.spec.task == "generate":
            repaired = self._repair_generate_answer(answer)
            if repaired:
                return repaired
            return answer.strip()
        expected = signatures[self.spec.task]
        if all(answer.count(title) == 1 for title in expected) and "暂无" not in answer:
            positions = [answer.index(title) for title in expected]
            if positions == sorted(positions):
                contents = [
                    answer[position + len(title): next_position if index + 1 < len(positions) else None].strip()
                    for index, (title, position) in enumerate(zip(expected, positions))
                    for next_position in [positions[index + 1] if index + 1 < len(positions) else len(answer)]
                ]
                if all(contents):
                    return "\n\n".join(f"{title}\n{content}" for title, content in zip(expected, contents))
        if self.spec.task == "generate":
            repaired = self._repair_generate_answer(answer)
            if repaired:
                return repaired
        return answer.strip()

    @staticmethod
    def _output_schemas() -> dict[str, tuple[tuple[str, str], ...]]:
        return {
            "chat": (("direct_answer", "直接回答"), ("evidence", "原句依据"), ("knowledge_points", "专属知识点")),
            "generate": (("title", "题目"), ("poem", "完整诗作"), ("creation_note", "创作说明")),
            "review": (("form_check", "体裁检查"), ("line_reviews", "逐句批改"), ("revised_poem", "完整修改稿"), ("change_summary", "修改说明")),
            "appreciate": (("scene", "诗境概括"), ("close_readings", "原句细读"), ("emotion_progression", "情感推进"), ("techniques", "手法效果")),
            "recite": (("metadata", "篇目信息"), ("verified_text", "准确原文"), ("memory_units", "意群记忆"), ("exercises", "背诵默写"), ("answers", "参考答案")),
            "compare": (("targets", "比较对象"), ("dimensions", "逐维对照"), ("core_conclusion", "核心异同")),
            "expand": (("instructions", "训练说明"), ("questions", "题目"), ("answers", "参考答案"), ("rubric", "评分要点")),
        }

    @staticmethod
    def _summary(value: Any) -> str:
        text = str(value)
        return text[:500] + ("…" if len(text) > 500 else "")

    @staticmethod
    def _relevant_memory(memories: list[dict], source: str, limit: int = 8) -> list[dict]:
        if len(memories) <= limit:
            return memories
        source_chars = set(source)
        ranked = sorted(
            memories,
            key=lambda item: (
                len(source_chars & set(str(item.get("content", "")))),
                float(item.get("confidence", 0)),
            ),
            reverse=True,
        )
        return ranked[:limit]

    def _plan(self, source: str, state: dict) -> dict:
        task = self.spec.task
        base = {
            "chat": ["定位问题对象", "确定应答边界", "挑选检索证据"],
            "generate": ["确定体裁约束", "确定主题意象", "确定情感走向", "输出原创诗作"],
            "review": ["检查格式", "逐句批改", "给出修改稿"],
            "appreciate": ["抽取原句", "分析语言机制", "说明效果"],
            "recite": ["核对篇目", "切分意群", "生成默写练习"],
            "compare": ["确认比较对象", "设定维度", "对照分析"],
            "expand": ["抽取考点", "生成题目", "给出答案与评分点"],
        }
        return {
            "task": task,
            "steps": base.get(task, []),
            "input_fingerprint": source[:120],
            "selected_form": state.get("form", "不限"),
            "selected_emotion": state.get("emotion", ""),
            "selected_themes": state.get("themes", []),
        }

AGENTS = {task: SpecialistAgent(spec) for task, spec in SPECS.items()}
