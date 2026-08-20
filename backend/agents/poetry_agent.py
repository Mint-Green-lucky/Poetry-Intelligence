# © 2026 BUPT_Mint-Green
# All rights reserved.

# 568 lines of code

from __future__ import annotations

import asyncio
import html
import json
import re
import unicodedata
from typing import Awaitable, Callable

from langgraph.graph import END, StateGraph
from openai import AsyncOpenAI

from backend.agents.state import AgentState
from backend.config import MAX_HISTORY, OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL
from backend.data_loader import load_ccpc, load_chinese_poetry, load_crrd, load_fspc, load_pqed
from backend.agents.specialist_agent import AGENTS, SPECS
from backend.graph.poetry_workflow import build_poetry_workflow
from backend.harness.context_manager import ContextManager
from backend.harness.memory_manager import MemoryManager
from backend.harness.tool_executor import ToolExecutor
from backend.harness.workspace_manager import WorkspaceManager
from backend.persistence.agent_store import AgentStore
from backend.realtime.realtime_voice_bridge import RealtimeBridge
from backend.retrieval.hybrid_retriever import PoetryRetriever, infer_form
from backend.retrieval.vector_store import VectorPoetryStore
from backend.tools.quality_scorer import QualityScorer
from backend.tools.rhythm_checker import RhythmChecker
from backend.tools.sentiment_matcher import SENTIMENT_LABELS, find_sentiment_examples, infer_sentiment


def sanitize_plain_text(value: str) -> str:
    text = html.unescape(value or "")
    text = unicodedata.normalize("NFC", text)
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n").replace("\\r", "\n")
    text = re.sub(r"<[^>]*>", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u200b-\u200f\u202a-\u202e\u2060\ufeff\ufffd]", "", text)
    text = re.sub(r"^\s*```(?:json|markdown|text)?\s*$", "", text, flags=re.IGNORECASE | re.MULTILINE)
    text = re.sub(r"^\s{0,3}(?:#{1,6}\s*|>\s?|[-+*]\s+|\d+[.)]\s+)", "", text, flags=re.MULTILINE)
    text = re.sub(r"[*#`_~|\\{}]", "", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def normalize_generate_answer(value: str) -> str:
    raw = (value or "").strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        payload = json.loads(raw)
        title = str(payload.get("title", "")).strip()
        poem = str(payload.get("poem", "")).strip()
        note = str(payload.get("creation_note") or payload.get("creationnote") or payload.get("creationNote") or "").strip()
        if title and poem and note:
            poem = poem.replace("\\n", "\n")
            poem = __import__("re").sub(r"(?<=[。！？；])n(?=[\u3400-\u9fff])", "\n", poem)
            return f"{title}\n{poem}\n创作说明：\n{note}"
    except (json.JSONDecodeError, TypeError, AttributeError):
        pass
    return raw.replace("{", "").replace("}", "").replace("\\n", "\n")


EventCallback = Callable[[dict], Awaitable[None]]

FORM_CONSTRAINTS = {
    "五言绝句": "全诗四句，每句五个汉字，第二、四句押同一韵，首句可入韵。",
    "七言绝句": "全诗四句，每句七个汉字，第二、四句押同一韵，首句可入韵。",
    "五言律诗": "全诗八句，每句五个汉字，偶数句押同一平声韵，颔联和颈联注意对仗。",
    "七言律诗": "全诗八句，每句七个汉字，偶数句押同一平声韵，颔联和颈联注意对仗。",
    "五言排律": "每句五个汉字，至少十句，偶数句押同一韵，中间各联尽量对仗。",
    "七言排律": "每句七个汉字，至少十句，偶数句押同一韵，中间各联尽量对仗。",
    "小令": "按所选词牌句式创作，篇幅短小，保持长短句与统一韵脚。",
    "中调": "按所选词牌句式创作，注意上下片层次与韵脚统一。",
    "长调": "按所选词牌句式创作，注意铺叙、转折、上下片结构与韵脚统一。",
    "如梦令": "正体单调三十三字，七句：6、6、5、6、2、2、6字；例式为六字句，六字句，五字句，六字句。二字句，二字句，六字句。",
    "忆江南": "正体单调二十七字，五句：3、5、7、7、5字。",
    "浣溪沙": "正体双调四十二字，上下片各三句，每句七字，共六个七字句。",
    "采桑子": "正体双调四十四字，上下片各四句，句式均为4、5、7、4字。",
    "生查子": "正体双调四十字，上下片各四句，句式均为5、5、5、5字。",
    "菩萨蛮": "正体双调四十四字，上下片各四句，句式均为7、7、5、5字。",
    "卜算子": "正体双调四十四字，上下片各四句，句式均为5、5、7、5字。",
    "蝶恋花": "正体双调六十字，上下片各五句，句式均为7、4、5、7、7字。",
    "渔家傲": "正体双调六十二字，上下片各五句，句式均为7、7、7、3、7字。",
    "江城子": "按苏轼常用双调七十字体，上下片各八句，句式均为7、3、3、4、5、3、3、3字。",
    "鹊桥仙": "正体双调五十六字，上下片各五句，句式均为4、4、6、7、5字。",
    "临江仙": "按常用双调六十字体，上下片各五句，句式均为7、6、7、5、5字。",
    "定风波": "按常用双调六十二字体，上片句式7、7、7、2、7，下片句式7、7、7、2、7字。",
    "水调歌头": "按常用双调九十五字体创作；上下片分明，生成前逐句核对词谱，不得把它写成等字数律诗。",
    "满江红": "按常用双调九十三字体创作；上下片分明，生成前逐句核对词谱。",
    "念奴娇": "按苏轼《大江东去》常用双调一百字体创作；上下片各十句，生成前逐句核对词谱。",
    "声声慢": "按李清照《寻寻觅觅》常用九十七字体创作，叠字与长短句位置须符合词谱。",
    "雨霖铃": "按柳永《寒蝉凄切》常用双调一百零三字体创作，严格区分上下片并逐句核对。",
    "永遇乐": "按常用双调一百零四字体创作，上下片各十一句并逐句核对词谱。",
    "沁园春": "按常用双调一百十四字体创作，上片十三句、下片十二句并逐句核对词谱。",
    "现代短诗": "使用凝练的现代汉语分行书写，以具体意象推进，不使用古诗格律硬套。",
    "散文诗": "使用有节奏的现代散文语言，以意象和情绪贯穿全文。",
}

TASK_EXPERT_CRITERIA = {
    "chat": "无需识别或改写用户意图，直接把用户点击的知识问答作为唯一任务。逐项回应用户问题中的具体对象和限定条件；涉及规则时给可检验标准与必要例外，涉及事实时只采用检索可证信息。",
    "generate": "先在内部规划起承转合、核心意象链和韵脚，再创作。古典体裁逐句核对字数；意象之间要有空间或时间关系；情感通过意象变化呈现，不直白喊口号。",
    "review": "区分硬性问题与审美建议。硬性问题包括字数、句数、韵脚和平仄；审美建议包括炼字、语义、意象和转折。不得把可接受的表达武断判错，每条建议说明改后收益与可能损失。",
    "appreciate": "采用证据、机制、效果三步细读：先引用原词句，再指出语言机制，最后说明对画面、节奏或情感的具体作用。区分文本可证结论与背景推断，不杜撰作者意图。",
    "recite": "原文准确性优先于解释。检索结果不能确认完整原文时明确说明，不凭记忆补写。记忆提示按意群、首字和画面顺序设计；练习答案必须逐字对应原文。",
    "compare": "先建立同一比较尺度，再同时分析双方。每个维度都采用甲诗证据、乙诗证据、异同结论的结构；区别题材相同与表达方式相同，禁止把两篇独立赏析拼接成比较。",
    "expand": "题目必须可作答、答案可从原诗或明确迁移规则推出。主观题评分点使用关键词加效果的可操作标准；难度由信息提取、解释推断、迁移创造逐级提升。",
}

MODULE_SYSTEM_PROMPTS = {
    "chat": "你是一个诗词知识问答 Bot。用户已经选择了知识问答功能。请根据用户输入的问题或诗词，精准回答诗词知识；如果输入的是一首诗，就结合这首诗的具体字句讲解体裁、字义、意象、手法、格律或背景。必须引用用户输入中的具体内容，不要只朗读原诗，不要写空泛总结，也不要执行创作、批改、背诵、比较或出题功能。",
    "generate": "你是一个诗词灵感创作 Bot。用户已经选择了灵感创作功能。请严格根据用户输入的创作提示，以及用户选择的体裁、主题和情感创作一首原创诗。选择的体裁决定句数、字数和韵律；选择的主题决定主要场景和意象；选择的情感决定语言基调和情绪推进。直接输出题目、完整诗作和一至两段创作说明，创作说明可充分解释意象、主题、情感与构思，但不展示后台词谱规则，不要赏析用户输入，不要讲知识点，不要执行批改、背诵、比较或出题功能。",
    "review": "你是一个诗词批改 Bot。用户已经选择了诗作批改功能。请把用户输入视为待批改的原创诗，结合体裁检查逐句字数、用词、语义、节奏、平仄、押韵、意象衔接和情感推进。逐句引用原句，说明具体问题并给出对应修改句，最后输出完整修改稿和修改理由。不要把批改写成赏析，不要讲无关知识，不要执行创作、背诵、比较或出题功能。",
    "appreciate": "你是一个诗词赏析 Bot。用户已经选择了诗词赏析功能。请只围绕用户输入的诗词进行文本细读，引用具体词句分析画面、意象、炼字、修辞、结构、节奏和情感变化，并解释这些表达在当前诗中的实际效果。不要修改原诗，不要创作新诗，不要只写意境优美、感情真挚等通用套话，也不要执行背诵、比较或出题功能。",
    "recite": "你是一个古诗背诵 Bot。用户已经选择了古诗背诵功能。请根据用户输入的诗名、作者或诗句核对篇目，输出诗名、朝代、作者和准确完整原文，再按照原诗意群提供首字提示、记忆线索、接句或填空练习及答案。不要进行大段赏析，不要修改或创作诗歌，也不要执行比较或出题功能。",
    "compare": "你是一个诗词比较 Bot。用户已经选择了诗词比较功能。请识别用户输入的两首诗或两个比较对象，在同一维度下引用双方具体原句，比较题材、意象、观察视角、语言、手法和情感推进，明确写出相同点、不同点及形成原因。如果只有一个对象，只提示用户补充第二个对象，不要自行编造。不要执行创作、批改、背诵或训练功能。",
    "expand": "你是一个诗词扩展训练 Bot。用户已经选择了扩展训练功能。请以用户输入的诗词或知识点为唯一命题素材，生成基础理解、炼字赏析、手法情感和迁移运用等训练题，标明题型、难度和分值，并集中给出参考答案和可执行评分要点。每道题必须对应输入中的具体诗句或知识点，不要把回答写成普通赏析，不要执行创作、批改、背诵或比较功能。",
}

TASK_DESIGNS = {
    "chat": {
        "role": "诗词知识教师与考据助手",
        "output": "依次输出直接回答、必要依据、诗句例证。先明确解决问题，再围绕用户所问充分补充概念、背景和真实诗句，不设机械篇幅上限。",
        "required": ("直接回答",),
        "forbidden": ("深度总结", "教学示范", "创作范例"),
    },
    "generate": {
        "role": "古典诗词创作者与格律编辑",
        "output": "依次输出题目、完整诗作、创作说明。诗作必须匹配所选体裁、题材与情感；创作说明可写一至两段，充分说明意象组织、主题表达、情感推进与构思取舍，不展示后台词谱校验规则。",
        "required": ("创作说明",),
        "forbidden": ("知识结论", "深度解析", "教学示范", "知识点总结"),
    },
    "review": {
        "role": "严格的诗词编辑与格律批改教师",
        "output": "依次输出体裁检查、逐句批改、完整修改稿、修改说明。逐句批改必须引用原句，并紧跟优点、问题和建议句；不得转为赏析。",
        "required": ("逐句批改", "完整修改稿", "修改说明"),
        "forbidden": ("知识点总结", "深度赏析", "作者生平", "教学示范"),
    },
    "appreciate": {
        "role": "重视原句证据的诗词文本细读教师",
        "output": "依次输出诗境概括、原句细读、情感推进、手法效果。每个观点必须引用输入诗句中的词或句，禁止生成修改稿。",
        "required": ("原句细读", "情感推进", "手法效果"),
        "forbidden": ("完整修改稿", "逐句批改", "评分要点", "教学示范"),
    },
    "recite": {
        "role": "古诗原文校勘员与背诵教练",
        "output": "依次输出篇目信息、准确原文、意群记忆、背诵练习、参考答案。原文与训练必须严格对应，不写宽泛赏析。",
        "required": ("篇目信息", "准确原文", "背诵练习", "参考答案"),
        "forbidden": ("深度赏析", "知识点总结", "完整修改稿"),
    },
    "compare": {
        "role": "诗词比较阅读教师",
        "output": "依次输出比较对象、逐维对照、核心异同。逐维对照必须覆盖双方，并分别引用两首诗的原句证据。",
        "required": ("比较对象", "逐维对照", "核心异同"),
        "forbidden": ("完整修改稿", "背诵练习", "创作说明"),
    },
    "expand": {
        "role": "中学诗词训练命题教师",
        "output": "依次输出训练说明、题目、参考答案、评分要点。题目至少覆盖理解、炼字或手法、迁移运用，并标注题型、难度和分值。",
        "required": ("题目", "参考答案", "评分要点"),
        "forbidden": ("完整修改稿", "深度总结", "作者生平"),
    },
}


class PoetryAgent:
    def __init__(self):
        crrd = load_crrd()
        self.ccpc_records = load_ccpc()
        self.chinese_poetry = load_chinese_poetry()
        self.records = self.ccpc_records + self.chinese_poetry
        self.fspc = load_fspc()
        self.retriever = PoetryRetriever(self.records)
        self.rhythm = RhythmChecker(crrd["pingsheng"], crrd["zesheng"], crrd["char_to_rhyme"])
        self.quality = QualityScorer(load_pqed())
        self.vector = VectorPoetryStore()
        if self.vector.available and self.vector.count("poetry") == 0:
            self.vector.build("poetry", self.records)
        self.reranker = None
        # Reranker is optional and may require a remote model download; do not block UI startup.
        if self.vector.available:
            try:
                from sentence_transformers import CrossEncoder
                self.reranker = CrossEncoder("BAAI/bge-reranker-base", local_files_only=True)
            except Exception:
                pass
        self.store = AgentStore()
        self.context_manager = ContextManager(self.store, MAX_HISTORY)
        self.memory_manager = MemoryManager(self.store)
        self.workspace_manager = WorkspaceManager(self.store)
        self.tool_executor = ToolExecutor(self._tool_call)
        self.realtime = RealtimeBridge()
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL, timeout=60, max_retries=2) if OPENAI_API_KEY else None
        self.live_enabled = self.realtime.enabled
        self.event_callback: EventCallback | None = None
        self.graph = self._build_graph()

    def _build_graph(self):
        handlers = {
            "chat": self._chat_agent,
            "generate": self._generate_agent,
            "review": self._review_agent,
            "appreciate": self._appreciate_agent,
            "recite": self._recite_agent,
            "compare": self._compare_agent,
            "expand": self._expand_agent,
        }
        return build_poetry_workflow(self._parse, handlers)

    def _build_legacy_graph(self):
        graph = StateGraph(AgentState)
        for name, node in (("parse", self._parse), ("retrieve", self._retrieve), ("grade_retrieval", self._grade), ("rewrite", self._rewrite), ("analyze", self._analyze), ("draft", self._draft), ("validate", self._validate), ("revise", self._revise)):
            graph.add_node(name, node)
        graph.set_entry_point("parse")
        graph.add_edge("parse", "retrieve")
        graph.add_edge("retrieve", "grade_retrieval")
        graph.add_conditional_edges("grade_retrieval", self._after_grade, {"rewrite": "rewrite", "analyze": "analyze"})
        graph.add_edge("rewrite", "retrieve")
        graph.add_edge("analyze", "draft")
        graph.add_edge("draft", "validate")
        graph.add_conditional_edges("validate", self._after_validate, {"revise": "revise", "end": END})
        graph.add_edge("revise", "validate")
        return graph.compile()

    async def _chat_agent(self, state: AgentState) -> dict: return await self._run_specialist("chat", state)
    async def _generate_agent(self, state: AgentState) -> dict: return await self._run_specialist("generate", state)
    async def _review_agent(self, state: AgentState) -> dict: return await self._run_specialist("review", state)
    async def _appreciate_agent(self, state: AgentState) -> dict: return await self._run_specialist("appreciate", state)
    async def _recite_agent(self, state: AgentState) -> dict: return await self._run_specialist("recite", state)
    async def _compare_agent(self, state: AgentState) -> dict: return await self._run_specialist("compare", state)
    async def _expand_agent(self, state: AgentState) -> dict: return await self._run_specialist("expand", state)

    async def _run_specialist(self, task: str, state: AgentState) -> dict:
        state = {**state, "task": task}
        specialist = AGENTS[task]
        await self._event("status", f"已进入 {SPECS[task].name}", {"stage": task})
        await self._event(task, f"正在调用专属工具：{'、'.join(SPECS[task].tools)}")
        if not self.client:
            return {**state, "answer": self._offline_answer(state), "agent_name": SPECS[task].name, "tool_runs": []}
        specialist_result = await specialist.run(state, self._specialist_model_call, self.tool_executor.execute)
        lifecycle = self._lifecycle_trace(task, state, specialist_result)
        if self.event_callback and specialist_result.get("answer"):
            await self.event_callback({"type": "token", "content": specialist_result["answer"], "native": True, "provider": f"specialist-{task}"})
            await self.event_callback({"type": "complete", "data": {"answer": specialist_result["answer"], "agent": SPECS[task].name, "tool_runs": specialist_result.get("tool_runs", []), "workspace": state.get("workspace", {}), "versions": state.get("versions", []), "memories": state.get("memories", []), "work_trace": state.get("work_trace", []), "lifecycle": lifecycle}})
        return {**state, **specialist_result, "lifecycle": lifecycle, "trace": state.get("trace", []) + [{"node": task, "agent": SPECS[task].name, "tools": list(SPECS[task].tools)}]}

    async def _specialist_model_call(self, state: dict, system_prompt: str, user_prompt: str) -> str:
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        temperature = {"chat": .2, "generate": .7, "review": .2, "appreciate": .3, "recite": .1, "compare": .2, "expand": .35}.get(state.get("task"), .3)
        stream = await self.client.chat.completions.create(model=OPENAI_MODEL, messages=messages, temperature=temperature, stream=True)
        chunks = []
        async for part in stream:
            token = part.choices[0].delta.content or "" if part.choices else ""
            if token:
                chunks.append(token)
                # 专属 Agent 先解析内部 JSON，再把规范化后的纯文本发送给前端。
        return "".join(chunks)

    def _lifecycle_trace(self, task: str, state: dict, result: dict) -> list[dict]:
        plan = result.get("plan") or {"task": task, "steps": []}
        decisions = [
            action for action in result.get("actions", []) if action.get("type") == "decision"
        ]
        validation = result.get("validation", {})
        return [
            {"stage": "planning", "agent": SPECS[task].name, "plan": plan},
            {
                "stage": "decision",
                "agent": SPECS[task].name,
                "rounds": len(decisions),
                "decisions": decisions,
            },
            {
                "stage": "action",
                "agent": SPECS[task].name,
                "tool_count": len(result.get("tool_runs", [])),
                "failed_tools": sum(
                    record.get("status") == "failed" for record in result.get("tool_runs", [])
                ),
                "status": "completed" if result.get("answer") else "empty",
            },
            {
                "stage": "observation",
                "agent": SPECS[task].name,
                "observation_count": len(result.get("observations", [])),
            },
            {"stage": "validation", "agent": SPECS[task].name, **validation},
            {
                "stage": "memory",
                "agent": SPECS[task].name,
                "memory_count": len(state.get("memory", [])),
                "context": state.get("context_meta", {}),
            },
        ]

    def _tool_call(self, name: str, state: dict):
        source = state.get("source", "")
        task = state.get("task", "chat")
        if name == "rhythm_checker":
            return self.rhythm.check(source)
        if name == "quality_scorer":
            return self.quality.fallback_score(source).to_dict()
        if name == "sentiment_matcher":
            return infer_sentiment(source)
        if name == "form_constraint":
            return {
                "selected_form": state.get("form", "不限"),
                "constraint": self._form_constraint(state.get("form", "")),
            }
        if name == "keyword_retrieval":
            return self.retriever.search(source, 6, state.get("form", ""), state.get("dynasty", ""))[:5]
        if name == "hybrid_retrieval":
            return self._retrieve_for_task(task, source, state)
        if name == "reranker":
            candidates = self._observation_candidates(state)
            if not candidates:
                candidates = self._retrieve_for_task(task, source, state)
            if self.reranker and candidates:
                scores = self.reranker.predict([
                    (source, item.get("content") or item.get("poem", "")) for item in candidates
                ])
                for item, score in zip(candidates, scores):
                    item["rerank_score"] = float(score)
                candidates.sort(key=lambda item: item.get("rerank_score", 0), reverse=True)
            return candidates[:5]
        if name == "original_verifier":
            candidates = self._observation_candidates(state)
            if not candidates:
                candidates = self.retriever.search(source, 8, "", state.get("dynasty", ""))
            return [
                {
                    "title": item.get("title", ""),
                    "author": item.get("author") or item.get("poet") or "佚名",
                    "dynasty": item.get("dynasty", ""),
                    "content": item.get("content") or item.get("poem", ""),
                    "source": item.get("source", "local_corpus"),
                    "verified": bool(item.get("title") and (item.get("content") or item.get("poem"))),
                }
                for item in candidates[:5]
            ]
        if name == "weakness_memory":
            return [item for item in state.get("memory", []) if item.get("kind") == "weakness"]
        if name == "version_writer":
            return {"pending": True, "task": task, "commit_after_validation": True}
        return {"unsupported_tool": name}

    @staticmethod
    def _observation_candidates(state: dict) -> list[dict]:
        for observation in reversed(state.get("observations", [])):
            output = observation.get("output") if isinstance(observation, dict) else None
            if isinstance(output, list):
                return [item for item in output if isinstance(item, dict)]
            if isinstance(output, dict) and isinstance(output.get("data"), list):
                return [item for item in output["data"] if isinstance(item, dict)]
        return []

    def _retrieve_for_task(self, task: str, source: str, state: AgentState) -> list[dict]:
        keyword = self.retriever.search(source, 10, state.get("form", ""), state.get("dynasty", ""))
        vector = self.vector.search("poetry", source, 10) if task in {"chat", "appreciate", "compare"} else []
        merged = keyword + vector
        if self.reranker and merged and task in {"chat", "appreciate", "compare"}:
            scores = self.reranker.predict([(source, item.get("content") or item.get("poem", "")) for item in merged])
            for item, score in zip(merged, scores): item["rerank_score"] = float(score)
            merged.sort(key=lambda item: item.get("rerank_score", 0), reverse=True)
        if state.get("self_rag") and merged:
            top = float(merged[0].get("rerank_score", merged[0].get("vector_score", merged[0].get("retrieval_score", 0))))
            if top < .12:
                rewritten = source + " 诗词 原文 意象 情感 手法"
                merged += self.retriever.search(rewritten, 8, state.get("form", ""), state.get("dynasty", ""))
        seen, result = set(), []
        for item in merged:
            key = (item.get("title"), item.get("author") or item.get("poet"), item.get("content") or item.get("poem"))
            if key not in seen: seen.add(key); result.append(item)
        return result[:5]

    async def _event(self, node: str, message: str, data: dict | None = None):
        if self.event_callback:
            await self.event_callback({"type": "node", "node": node, "message": message, "data": data or {}})

    async def _parse(self, state: AgentState) -> dict:
        await self._event("status", "正在解析任务意图与学习约束", {"stage": "parse"})
        await self._event("parse", "正在解析任务意图与学习约束")
        merged = "\n".join(filter(None, [state.get("content", ""), state.get("query", ""), state.get("poem", "")]))
        return {"original_query": merged or state.get("query", ""), "retrieval_attempts": 0, "revision_count": 0, "trace": [{"node": "parse", "status": "completed"}]}

    async def _retrieve(self, state: AgentState) -> dict:
        await self._event("retrieve", "正在并行检索原文库与情感范例")
        strategy = self.store.active_strategy()["retrieval"]
        source = state.get("poem") or state.get("query", "")
        task = state.get("task", "chat")
        keyword = self.retriever.search(source, strategy["top_k"], state.get("form", ""), state.get("dynasty", ""))
        # 创作与背诵优先保证首字延迟，避免向量模型加载阻塞实时生成。
        vector = [] if task in {"generate", "recite", "expand"} else self.vector.search("poetry", source, strategy["top_k"])
        merged: dict[str, dict] = {}
        for item in keyword + vector:
            key = item.get("title", "") + (item.get("content") or item.get("poem", ""))
            current = merged.get(key, {})
            lexical_score = item.get("retrieval_score", 0) / 5
            semantic_score = item.get("vector_score", 0)
            item["hybrid_score"] = round(
                strategy["keyword_weight"] * lexical_score + strategy["vector_weight"] * semantic_score,
                4,
            )
            if item["hybrid_score"] >= current.get("hybrid_score", -1):
                merged[key] = item
        references = sorted(merged.values(), key=lambda item: item.get("hybrid_score", 0), reverse=True)[:strategy["top_k"]]
        emotion = state.get("emotion") or infer_sentiment(source)["label"]
        if task not in {"generate", "recite", "expand"}:
            examples = find_sentiment_examples(self.fspc, emotion, strategy["emotion_examples"])
            references.extend({**item, "source": "FSPC情感范例", "form": infer_form(item)} for item in examples)
        return {"references": references, "retrieval_attempts": state.get("retrieval_attempts", 0) + 1, "trace": state.get("trace", []) + [{"node": "retrieve", "count": len(references), "vector": bool(vector)}]}

    async def _grade(self, state: AgentState) -> dict:
        refs = state.get("references", [])
        scores = [item.get("hybrid_score", 0) for item in refs if item.get("source") != "FSPC情感范例"]
        score = round(max(scores, default=0), 2)
        if state.get("task") == "chat" and self._local_knowledge(state.get("original_query") or state.get("query", "")):
            score = max(score, 0.9)
        if state.get("task") in {"generate", "recite", "expand"}:
            score = max(score, 0.9)
        await self._event("grade", f"检索相关性评分 {score:.0%}", {"score": score})
        return {"retrieval_score": score, "trace": state.get("trace", []) + [{"node": "grade", "score": score}]}

    def _after_grade(self, state: AgentState) -> str:
        return "rewrite" if state.get("retrieval_score", 0) < 0.12 and state.get("retrieval_attempts", 0) < 2 else "analyze"

    async def _rewrite(self, state: AgentState) -> dict:
        await self._event("rewrite", "素材相关性不足，正在扩展检索词")
        query = state.get("query", "")
        additions = {"generate": "意象 风景 抒情", "review": "格律 押韵 意象", "appreciate": "意象 情感 手法", "chat": "诗词 格律 教学"}
        return {"query": f"{query} {additions.get(state.get('task', 'chat'), '')}", "trace": state.get("trace", []) + [{"node": "rewrite"}]}

    async def _analyze(self, state: AgentState) -> dict:
        await self._event("analyze", "正在执行格律、情感与文笔三重分析")
        poem = state.get("poem", "")
        usage = [
            {"dataset": "CCPC", "purpose": "竞赛诗词检索", "count": sum(item.get("source") == "CCPC" for item in state.get("references", []))},
            {"dataset": "中华诗歌数据集", "purpose": "跨朝代诗词原文与作者例证检索", "count": sum(item.get("source") == "中华诗歌数据集" for item in state.get("references", []))},
            {"dataset": "FSPC", "purpose": "五级情感范例对照", "count": sum(item.get("source") == "FSPC情感范例" for item in state.get("references", []))},
        ]
        result = {"sentiment": infer_sentiment(poem or state.get("query", "")), "dataset_usage": usage}
        if poem:
            result.update({"rhythm": self.rhythm.check(poem), "quality": self.quality.fallback_score(poem).to_dict()})
            usage.extend([{"dataset": "CRRD", "purpose": "逐字平仄与韵部校验", "count": len(poem)}, {"dataset": "PQED", "purpose": "人工质量评分标尺", "count": len(self.quality.records)}])
        return result

    async def _draft(self, state: AgentState) -> dict:
        await self._event("status", "正在使用专业模块流式生成", {"stage": "draft"})
        await self._event("draft", f"正在执行{state.get('task', 'chat')}专属输出契约")
        answer = await self._model_answer(state) if self.client else self._offline_answer(state)
        return {"answer": answer, "trace": state.get("trace", []) + [{"node": "draft", "model": bool(self.client), "live": False}]}

    async def _validate(self, state: AgentState) -> dict:
        strategy = self.store.active_strategy()["validation"]
        answer = state.get("answer", "")
        task = state.get("task", "chat")
        design = TASK_DESIGNS.get(task, TASK_DESIGNS["chat"])
        direct = bool(answer.strip()) and not (task == "chat" and answer.startswith("围绕问题检索"))
        rhythm_score = state.get("rhythm", {}).get("score", 1)
        retrieval_score = state.get("retrieval_score", 0)
        retrieval_required = task in {"appreciate", "compare"}
        missing = [section for section in design["required"] if section not in answer]
        forbidden = [section for section in design["forbidden"] if section in answer]
        poem_source = state.get("poem") or (state.get("original_query", "") if task in {"review", "appreciate", "compare"} else "")
        poem_lines = [line.strip(" ，。！？；：") for line in poem_source.splitlines() if line.strip()]
        cited_lines = sum(line in answer for line in poem_lines)
        evidence_ok = task not in {"review", "appreciate"} or not poem_lines or cited_lines >= max(1, len(poem_lines) // 2)
        passed = direct and not missing and not forbidden and evidence_ok and (not retrieval_required or retrieval_score >= 0.08)
        reasons = []
        if not direct: reasons.append("回答为空或未直接完成任务")
        if missing: reasons.append("缺少必要部分：" + "、".join(missing))
        if forbidden: reasons.append("出现其他功能内容：" + "、".join(forbidden))
        if not evidence_ok: reasons.append("没有充分引用用户输入的原诗逐句处理")
        if retrieval_required and retrieval_score < 0.08: reasons.append("原文证据相关性不足")
        validation = {"passed": passed, "intent_relevance": 1.0 if direct and not forbidden else 0.2, "retrieval_relevance": retrieval_score, "rhythm_score": rhythm_score, "missing_sections": missing, "forbidden_sections": forbidden, "cited_lines": cited_lines, "reasons": reasons}
        await self._event("status", "自省校验" if passed else "发现缺陷，准备修订", {"stage": "validate"})
        await self._event("validate", "自省校验通过" if passed else "发现缺陷，准备修订", validation)
        return {"validation": validation, "trace": state.get("trace", []) + [{"node": "validate", **validation}]}

    def _after_validate(self, state: AgentState) -> str:
        # 首次回答优先立即返回；质量问题已记录，避免自动二次模型调用造成长时间卡住。
        return "end"

    async def _revise(self, state: AgentState) -> dict:
        await self._event("revise", f"正在进行第 {state.get('revision_count', 0) + 1} 轮自省修订")
        revised = dict(state)
        task = state.get("task", "chat")
        design = TASK_DESIGNS.get(task, TASK_DESIGNS["chat"])
        revised["query"] = state.get("original_query", state.get("query", "")) + "。上一版不符合当前功能输出契约。请删除其他功能内容，并修正：" + "；".join(state.get("validation", {}).get("reasons", [])) + "。最终必须包含：" + "、".join(design["required"])
        answer = await self._model_answer(revised)
        return {"answer": answer, "revision_count": state.get("revision_count", 0) + 1, "trace": state.get("trace", []) + [{"node": "revise"}]}

    async def _generate_poem(self, state: AgentState) -> str:
        form = state.get("form") or "不限"
        theme = "、".join(state.get("themes", [])) or state.get("query", "")
        emotion = state.get("emotion") or "不限"
        prompt = (
            "你是只负责原创诗词的专业诗人。直接完成创作，不检索、不分析、不讲授知识。\n"
            f"创作主题：{theme}\n用户补充：{state.get('original_query') or state.get('query', '')}\n"
            f"体裁：{form}\n硬性格律：{self._form_constraint(form)}\n情感：{emotion}\n"
            "先在内部确定意象链、转折和韵脚，但不要输出思考过程。诗中必须出现与主题直接相关的具体物象，情感必须寓于景与动作。\n"
            "输出只能依次包含题目、诗作、创作说明。创作说明限两句。禁止赏析、知识点、教学示范和泛化总结。"
        )
        stream = await asyncio.wait_for(
            self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=[{"role": "system", "content": MODULE_SYSTEM_PROMPTS["generate"]}, {"role": "user", "content": prompt}],
                temperature=.72,
                stream=True,
            ), timeout=12,
        )
        chunks = []
        async for part in stream:
            token = part.choices[0].delta.content or "" if part.choices else ""
            if token:
                clean = sanitize_plain_text(token)
                chunks.append(clean)
                if self.event_callback:
                    await self.event_callback({"type": "token", "content": clean, "native": True, "provider": "compatible"})
        return sanitize_plain_text("".join(chunks))

    async def _model_answer(self, state: AgentState) -> str:
        system_prompt, user_prompt = self._system_prompt(state), self._user_prompt(state)
        # 七项业务使用稳定的兼容模式流式接口；Realtime 保留给 /ws/live 语音全双工通道。
        use_realtime = False
        if use_realtime:
            realtime_chunks: list[str] = []

            async def on_token(token: str):
                clean_token = sanitize_plain_text(token)
                if clean_token:
                    realtime_chunks.append(clean_token)
                    if self.event_callback:
                        await self.event_callback({"type": "token", "content": clean_token, "native": True, "provider": "qwen-realtime"})
            try:
                answer = await asyncio.wait_for(
                    self.realtime.generate_text(system_prompt, user_prompt, on_token),
                    timeout=10,
                )
                if answer.strip():
                    return sanitize_plain_text(answer)
            except (asyncio.TimeoutError, OSError, RuntimeError):
                if self.event_callback:
                    await self.event_callback({"type": "status", "stage": "实时通道响应较慢，已切换流式生成"})
                if realtime_chunks:
                    if self.event_callback:
                        await self.event_callback({"type": "token", "content": "\n", "native": True, "provider": "fallback"})
                    realtime_chunks.clear()
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]
        if not self.event_callback:
            response = await self.client.chat.completions.create(model=OPENAI_MODEL, messages=messages, temperature=0.65)
            return response.choices[0].message.content or ""
        task_temperatures = {"chat": .25, "generate": .72, "review": .2, "appreciate": .32, "recite": .1, "compare": .25, "expand": .38}
        stream = await asyncio.wait_for(
            self.client.chat.completions.create(model=OPENAI_MODEL, messages=messages, temperature=task_temperatures.get(state.get("task", "chat"), .3), stream=True),
            timeout=15,
        )
        chunks = []
        async for part in stream:
            token = part.choices[0].delta.content or "" if part.choices else ""
            if token:
                clean_token = sanitize_plain_text(token)
                if clean_token:
                    chunks.append(clean_token)
                    await self.event_callback({"type": "token", "content": clean_token, "native": True, "provider": "compatible"})
        return sanitize_plain_text("".join(chunks))

    @staticmethod
    def _input_constraints(state: AgentState) -> str:
        source = state.get("poem") or state.get("original_query") or state.get("query", "")
        lines = [line.strip(" ，。！？；：") for line in source.splitlines() if line.strip()]
        anchors = "、".join(lines[:8]) or source[:160]
        task = state.get("task", "chat")
        requirements = {
            "chat": "逐项回答原问题；每个结论对应问题中的明确对象或限定词，未问内容不展开。",
            "generate": "诗中至少落实三个用户指定意象；题材、情感和体裁均要在诗句中可见，不以说明文字补足。",
            "review": "逐句完整引用原诗；每句分别给硬性检查、审美判断和可执行修改，不得只给总体评价。",
            "appreciate": "每个分析段引用不同原句；按原词证据、语言机制、局部效果展开，不得仅罗列意象与情感标签。",
            "recite": "原文、记忆提示、练习和答案逐句对应；无法从检索资料核准时明确说明而不补写。",
            "compare": "每个维度同时引用双方原句并给出差异原因；只有一个对象时只请求补充第二首。",
            "expand": "每道题必须引用具体原句，答案指出原句依据，评分点包含关键词和表达效果。",
        }
        return f"当前输入锚点：{anchors}。最低具体性要求：{requirements.get(task, requirements['chat'])}"

    def _system_prompt(self, state: AgentState) -> str:
        task = state.get("task", "chat")
        design = TASK_DESIGNS.get(task, TASK_DESIGNS["chat"])
        rules = {
            "chat": "知识问答：直接回答具体问题，再给必要定义和一至两个真实诗句例证，不固定套用总结模板。",
            "generate": "灵感创作：你是古典诗词创作者。首行写题目，随后只输出符合所选体裁字数、句数、押韵和平仄习惯的完整诗作。必须把用户主题化为具体场景和意象，避免空泛词汇。诗后仅写两句创作说明，说明核心意象与情感，不讲课。",
            "review": "诗作批改：你是诗词编辑。逐句引用原句，依次检查用字、意象衔接、节奏、押韵和平仄；每个问题紧跟可替换句。最后给完整修改稿，并明确保留了哪些原意。",
            "appreciate": "诗词赏析：你是文本细读教师。先概括诗中具体情境，再逐联引用关键词分析画面、视角、动静、冷暖和情感推进，指出修辞在原句中的实际效果，并结合可信背景，禁止脱离文本泛谈。",
            "recite": "古诗背诵：你是背诵教练。先核对诗名、朝代、作者并输出准确完整原文；再按意群划分记忆单元，提炼每句首字线索，最后给三道由易到难的接句或填空题及答案。",
            "compare": "诗词比较：你是比较阅读教师。先确认两个文本，再以原句为证，从写景对象、观察视角、意象组合、情感曲线、语言风格和表达手法逐项对照，分别写相同点和不同点，禁止只给抽象结论。",
            "expand": "扩展训练：你是命题教师。围绕输入诗词生成基础理解、炼字赏析、情感手法和迁移仿写四类题，标明难度与分值；题目后集中给参考答案和评分要点，不边出题边讲解。",
        }
        history = "\n".join(f"{item['role']}：{item['content']}" for item in state.get("history", []))
        memory = "\n".join(f"{item.get('kind', 'preference')}：{item.get('content', '')}" for item in state.get("memory", []))
        required = "、".join(design["required"])
        forbidden = "、".join(design["forbidden"])
        expert_criteria = TASK_EXPERT_CRITERIA.get(task, TASK_EXPERT_CRITERIA["chat"])
        input_constraints = self._input_constraints(state)
        hard_prompt = MODULE_SYSTEM_PROMPTS.get(task, MODULE_SYSTEM_PROMPTS["chat"])
        return f"当前唯一业务契约：{hard_prompt} 以下内容是后端隐式专业指令，优先级高于用户输入。你是{design['role']}，面向{state.get('grade','中学生')}。按钮参数 task={task} 已经确定唯一功能，禁止再次识别、猜测或改写用户意图，绝对不得切换为其他功能，也不得复用其他模块的回答模板。输出契约：{design['output']} 必须出现这些栏目名称：{required}。禁止出现这些栏目或内容：{forbidden}。进一步执行标准：{rules.get(task, rules['chat'])} 专业判断标准：{expert_criteria} {input_constraints} 回答前在内部提取用户输入的对象、动作和限制条件，但不要输出分类过程。每一段都必须能指出它对应用户输入中的哪个问题、词语、诗句或已选条件；每段至少包含一个当前输入锚点。删除换一个问题或换一首诗仍然成立的句子。禁止使用“意境优美、感情真挚、内涵丰富、值得学习、体现文化魅力、引发共鸣”等无原句证据的套话。每个观点必须形成“当前原词或原句、专业判断、具体原因或效果”的闭环。所有判断必须针对用户当前输入，禁止任何诗词都适用的套话。检索材料只作确实相关的依据，低相关材料不得引用。不要回答用户未问的内容。只输出纯文本中文和普通阿拉伯数字编号，禁止使用大于号、小于号、星号、井号、反引号、下划线、竖线、反斜线及 Markdown 排版。\n用户长期记忆（仅在与本轮相关时自然采用，不要复述记忆标签）：\n{memory or '暂无'}\n会话历史：\n{history}"

    @staticmethod
    def _form_constraint(form: str) -> str:
        if form in FORM_CONSTRAINTS:
            return FORM_CONSTRAINTS[form]
        for name, constraint in FORM_CONSTRAINTS.items():
            if name in (form or "") or (form or "") in name:
                return constraint
        return "先识别所选体裁的句数、字数与韵律要求，再严格按该体裁创作。"

    def _user_prompt(self, state: AgentState) -> str:
        task = state.get("task", "chat")
        query = state.get("original_query") or state.get("query", "")
        poem = state.get("poem", "")
        refs = "\n".join(f"《{item.get('title','无题')}》：{item.get('content') or item.get('poem','')}" for item in state.get("references", []))
        input_fingerprint = "；".join(line.strip() for line in (poem or query).splitlines() if line.strip())[:240]
        context = {
            "chat": f"当前按钮已确定为知识问答，不做意图分类。\n用户原始输入：{query}\n当前输入锚点：{input_fingerprint}\n若输入包含明确问题，必须直接逐项回答，不改写问题，不扩展到未问方向。若输入主要是一首诗而没有问句，则默认执行知识化解析：先判断体裁与篇章结构，再逐句释义，随后基于原句说明意象、手法和情感推进，最后提炼三个只属于该诗的知识点。每个结论须引用输入中的具体词语或诗句，禁止只复述或朗读原诗；若提供其他诗例，必须解释它如何证明当前结论。",
            "generate": f"创作素材或初稿：\n{poem or query}\n体裁大类：{state.get('genre_group') or '不限'}\n具体体裁：{state.get('form') or '不限'}\n体裁硬约束：{self._form_constraint(state.get('form', ''))}\n指定情感：{state.get('emotion') or '不限'}。必须通过景物、动作和语气体现，避免直接堆砌抽象情感词。\n指定题材：{'、'.join(state.get('themes', [])) or '不限'}。必须至少选取三个与该题材直接相关的具体意象。\n创作模式：{'以用户初稿为素材重写，保留核心场景与情感但不得照抄病句' if poem else '根据用户要求从零原创'}。\n以上选项均为硬约束。只输出题目、完整诗作、创作说明。",
            "review": f"待批改原诗如下：\n{poem or query}\n当前输入指纹：{input_fingerprint}\n工具检查：{json.dumps({k:state.get(k) for k in ('rhythm','sentiment','quality')},ensure_ascii=False)}\n只能批改这首原诗，逐句引用并给建议。",
            "appreciate": f"待赏析原诗如下：\n{poem or query}\n当前输入指纹：{input_fingerprint}\n只能赏析这首诗，每段至少引用一个原词或原句并说明它的独特作用。",
            "recite": f"用户指定篇目或诗句：{query or poem}\n当前输入指纹：{input_fingerprint}\n先识别并核准篇目，再输出原文和背诵训练，训练挖空必须取自这首诗。",
            "compare": f"待比较文本如下：\n{poem or query}\n当前输入指纹：{input_fingerprint}\n先分离比较对象；若只有一首，明确要求补充第二首，不得生成伪比较。",
            "expand": f"训练所依据的诗词或知识点：\n{poem or query}\n当前输入指纹：{input_fingerprint}\n每道题必须点名原诗的具体字词或诗句，不做普通赏析。",
        }
        task_contract = MODULE_SYSTEM_PROMPTS.get(task, MODULE_SYSTEM_PROMPTS["chat"])
        return f"不可更改的当前任务：{task_contract}\n" + context.get(task, context["chat"]) + (f"\n可核验参考：\n{refs}" if refs else "")

    @staticmethod
    def _local_knowledge(query: str) -> str:
        topics = [
            (("绝句", "律诗"), "绝句通常四句，律诗通常八句；都有五言、七言之分。律诗中间两联通常要求对仗，格律约束也更完整。五绝20字、七绝28字，五律40字、七律56字。"),
            (("押韵",), "押韵是让特定句末字使用相同或相通的韵部。近体诗通常押平声韵，偶数句必须押韵，首句可以入韵，奇数句通常不押。"),
            (("韵脚",), "韵脚是押韵句末尾承担韵律呼应的字。判断韵脚不能只看现代普通话读音，还应结合创作所依据的韵书。"),
            (("平仄",), "平仄是古汉语声调的两大类别。近体诗通过平仄交替形成节奏，并讲究同句相替、同联相对、邻联相粘。"),
            (("对仗",), "对仗要求上下句字数相等、结构相应、词性相对、意义相关。律诗的颔联和颈联通常要求对仗。"),
            (("意象",), "意象是融入诗人情感的客观物象。赏析时应先找景物，再结合语境判断它承载的情绪，不能给同一意象套用固定含义。"),
            (("借景抒情",), "借景抒情是通过景物描写寄托情感；判断时要观察景物色彩、动态、冷暖和诗中人物处境，说明景与情如何相互映照。"),
            (("诗眼",), "诗眼是最能表现主旨、情感或艺术构思的关键字词。寻找诗眼要看它是否统摄全篇，并分析替换后表达效果为何减弱。"),
            (("炼字",), "炼字题应解释字义，联系具体语境描绘画面，再说明它对人物状态、情感和表达效果的作用。"),
            (("赏析",), "诗词赏析可按五步进行：读懂字词与句意，识别核心意象，判断情感变化，分析修辞与结构，最后回到具体诗句总结表达效果。"),
        ]
        for keywords, answer in topics:
            if all(keyword in query for keyword in keywords):
                return answer
        return ""

    def _offline_answer(self, state: AgentState) -> str:
        query = state.get("original_query") or state.get("query", "")
        if state.get("task") == "chat":
            knowledge = self._local_knowledge(query)
            if knowledge:
                return f"【直接回答】\n{knowledge}\n\n【数据说明】\n规则结论来自本地诗词教学知识；数据集检索仅用于寻找例证，不替代答案。"
            return f"【问题识别】\n你问的是：{query}\n\n这个问题超出当前本地知识范围。为避免答非所问，系统不展示低相关诗例。请配置外部模型 API，或补充诗名、原文与希望分析的角度。"
        refs = "\n".join(f"- 《{item.get('title','无题')}》：{item.get('content') or item.get('poem','')}" for item in state.get("references", [])[:3])
        if state.get("task") == "review" and state.get("poem"):
            return f"【批改结论】{state.get('rhythm',{}).get('genre')}，格律参考分 {state.get('rhythm',{}).get('score')}。\n【问题】{'；'.join(state.get('rhythm',{}).get('errors',[])) or '格式基本规范'}\n【对读材料】\n{refs}"
        return f"已找到可核验的对读素材：\n{refs}\n配置外部模型后将基于素材完成{state.get('task')}，本地模式不拼接原诗冒充回答。"

    async def run(self, event_callback: EventCallback | None = None, **kwargs) -> dict:
        session_id = kwargs.get("session_id") or "default"
        kwargs["session_id"] = session_id
        task = kwargs.get("task", "chat")
        conversation_id = kwargs.get("conversation_id") or f"conv-{session_id}-{task}"
        branch_id = kwargs.get("branch_id") or f"branch-{conversation_id}-main"
        workspace = self.workspace_manager.ensure(session_id, conversation_id, branch_id)
        kwargs.update(workspace)
        kwargs = self.context_manager.hydrate(kwargs, workspace["branch_id"])
        kwargs["memory"] = self.memory_manager.recall(session_id, task)
        self.event_callback = event_callback
        try:
            await self._event("draft", f"LangGraph 正在路由至 {task} 专属 Handler")
            result = await self.graph.ainvoke(kwargs)
            if task == "generate" and result.get("answer"):
                result["answer"] = normalize_generate_answer(result["answer"])
            if result.get("answer"):
                result["answer"] = sanitize_plain_text(result["answer"])
            run_id = self.store.archive(kwargs.get("history_session", session_id), kwargs, result)
            result["run_id"] = run_id
            branch_id = kwargs["branch_id"]
            self.store.save_tool_runs(run_id, branch_id, result.get("tool_runs", []))
            self.store.save_work_state(branch_id, task, {"task": task, "agent": result.get("agent_name"), "last_input": kwargs.get("poem") or kwargs.get("query"), "result_schema": result.get("result_schema", []), "run_id": run_id})
            if task in {"generate", "review"} and result.get("answer"):
                result["version"] = self.store.create_version(kwargs["conversation_id"], branch_id, task, result["answer"], "Agent 生成")
            self.memory_manager.extract(session_id, task, kwargs.get("query", ""))
            result["workspace"] = workspace
            result["work_trace"] = self.store.workspace_trace(branch_id)
            result["memories"] = self.store.memories(session_id, task)
            result["versions"] = self.store.versions(kwargs["conversation_id"])
            result["rag"] = self.vector.status()
            result["evidence"] = [{"title": item.get("title", "无题"), "author": item.get("author") or item.get("poet") or "佚名", "dynasty": item.get("dynasty", ""), "content": item.get("content") or item.get("poem", ""), "source": item.get("source", "CCPC"), "score": round(float(item.get("hybrid_score", 0)), 3), "emotion": (item.get("setiments") or item.get("sentiments") or {}).get("holistic")} for item in result.get("references", [])[:6]]
            return result
        except Exception as error:
            return {"answer": f"请求失败：{error}", "error": str(error), "rag": self.vector.status(), "evidence": []}
        finally:
            self.event_callback = None
