# © 2026 BUPT_Mint-Green
# All rights reserved.

from dataclasses import asdict, dataclass


@dataclass
class QualityScore:
    fluency: float
    coherence: float
    meaningfulness: float
    overall: float
    level: str
    feedback: str

    def to_dict(self) -> dict:
        return asdict(self)


class QualityScorer:
    def __init__(self, records: list[dict]):
        self.records = records
        self.high = sorted(records, key=lambda item: item.get("overall score", 0), reverse=True)
        self.low = sorted(records, key=lambda item: item.get("overall score", 0))

    @staticmethod
    def level(score: float) -> str:
        if score >= 4.5:
            return "优秀"
        if score >= 3.5:
            return "良好"
        if score >= 2.5:
            return "中等"
        return "待提升"

    def few_shots(self) -> str:
        samples = self.high[:2] + self.low[:2]
        return "\n\n".join(
            f"诗作：{record.get('poem', '')}\n"
            f"流畅度 {record.get('fluency')}，连贯性 {record.get('coherence')}，"
            f"意蕴 {record.get('meaningfulness')}，整体 {record.get('overall score')}"
            for record in samples
        )

    def build_prompt(self, poem: str) -> str:
        return f"""你是严谨的古典诗词教师。请依据人工标注示例评价诗作，不要把整体分简单计算为前三项平均值。

评分维度：fluency（流畅度）、coherence（连贯性）、meaningfulness（意蕴）、overall（综合印象），均为1至5分。

参考样例：
{self.few_shots()}

待评价诗作：
{poem}

仅返回 JSON：{{"fluency": 0, "coherence": 0, "meaningfulness": 0, "overall": 0, "feedback": "具体、鼓励性评语"}}"""

    def fallback_score(self, poem: str) -> QualityScore:
        lines = [line for line in poem.replace("\n", "|").split("|") if line.strip()]
        lengths = [len(line.strip("，。！？；,.!?; ")) for line in lines]
        regularity = 1 - (max(lengths) - min(lengths)) / max(lengths) if lengths else 0
        fluency = round(2.5 + regularity * 1.5, 1)
        coherence = round(2.8 + (0.6 if len(lines) in (4, 8) else 0), 1)
        meaningfulness = round(min(4.2, 2.8 + len(set(poem)) / max(20, len(poem))), 1)
        overall = round((fluency + coherence + meaningfulness) / 3, 1)
        return QualityScore(fluency, coherence, meaningfulness, overall, self.level(overall), "本地启发式评分，仅作演示；配置模型 API 后可获得基于 PQED 样例的详细点评。")
