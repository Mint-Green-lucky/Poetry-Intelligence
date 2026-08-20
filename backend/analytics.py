# © 2026 BUPT_Mint-Green
# All rights reserved.

from collections import Counter
from functools import lru_cache
from statistics import mean

from backend.data_loader import load_ccpc, load_chinese_poetry, load_crrd, load_fspc, load_pqed, normalize_poem
from backend.retrieval.hybrid_retriever import infer_form, poem_lines

DYNASTY_NAMES = {"Tang": "唐", "Song": "宋", "Ming": "明", "Qing": "清", "Yuan": "元"}
EMOTION_NAMES = {"1": "直白悲伤", "2": "含蓄悲伤", "3": "中性", "4": "含蓄喜悦", "5": "直白喜悦"}


def _top(counter: Counter, limit: int = 8) -> list[dict]:
    return [{"name": str(name), "value": value} for name, value in counter.most_common(limit) if name]


@lru_cache(maxsize=1)
def dataset_analytics() -> dict:
    ccpc, fspc, pqed, crrd, chinese = load_ccpc(), load_fspc(), load_pqed(), load_crrd(), load_chinese_poetry()
    dynasties = Counter(DYNASTY_NAMES.get(str(item.get("dynasty", "")), str(item.get("dynasty", "未知"))) for item in ccpc)
    forms = Counter(infer_form(item) for item in ccpc)
    authors = Counter(str(item.get("author") or item.get("poet") or "佚名") for item in ccpc)
    keywords = Counter()
    for item in ccpc:
        keywords.update(str(item.get("keywords", "")).replace(",", " ").split())
    chinese_dynasties = Counter(str(item.get("dynasty") or "未知") for item in chinese)
    chinese_kinds = Counter(str(item.get("category") or "其他") for item in chinese)
    chinese_forms = Counter(infer_form(item) for item in chinese)
    emotions = Counter(str((item.get("setiments") or item.get("sentiments") or {}).get("holistic", "3")) for item in fspc)
    line_emotions = Counter()
    for item in fspc:
        sentiment = item.get("setiments") or item.get("sentiments") or {}
        line_emotions.update(str(value) for key, value in sentiment.items() if key.startswith("line"))
    averages = {
        "fluency": round(mean(float(item.get("fluency", 0)) for item in pqed), 2),
        "coherence": round(mean(float(item.get("coherence", 0)) for item in pqed), 2),
        "meaningfulness": round(mean(float(item.get("meaningfulness", 0)) for item in pqed), 2),
        "overall": round(mean(float(item.get("overall score", 0)) for item in pqed), 2),
    }
    score_distribution = Counter(str(round(float(item.get("overall score", 0)) * 2) / 2) for item in pqed)
    dataset_metrics = [
        {"name": "CCPC（古典诗词原文库）", "thu": len(ccpc), "open": 0},
        {"name": "CRRD（平仄格律标注库）", "thu": len(crrd["pingshui"]), "open": 0},
        {"name": "FSPC（细粒度情感标注库）", "thu": len(fspc), "open": 0},
        {"name": "PQED（文笔四维打分库）", "thu": len(pqed), "open": 0},
        {"name": "开源中华诗词库", "thu": 0, "open": len(chinese)},
    ]
    imagery_groups = {
        "花草": "花草柳梅竹荷芳",
        "山川": "山水江河海峰岭",
        "风月": "风月云雨雪霜霞",
        "飞鸟": "鸟雁鹤莺燕鸿",
        "楼台": "楼台亭阁城关",
    }
    imagery = []
    all_content = "".join(normalize_poem(item) for item in ccpc[:10000])
    open_content = "".join(normalize_poem(item) for item in chinese[:10000])
    for name, chars in imagery_groups.items():
        imagery.append({"name": name, "thu": sum(all_content.count(char) for char in chars), "open": sum(open_content.count(char) for char in chars)})
    return {
        "totals": {"ccpc": len(ccpc), "chinese_poetry": len(chinese), "fspc": len(fspc), "pqed": len(pqed), "rhyme_groups": len(crrd["pingshui"]), "ping_chars": len(crrd["pingsheng"]), "ze_chars": len(crrd["zesheng"])},
        "ccpc": {"朝代": _top(dynasties, 10), "体裁": _top(forms, 8), "诗人": _top(authors, 10), "关键词": _top(keywords, 15)},
        "chinese_poetry": {"朝代": _top(chinese_dynasties, 10), "类别": _top(chinese_kinds, 12), "体裁": _top(chinese_forms, 10)},
        "fspc": {"整体情感": [{"name": EMOTION_NAMES[key], "value": emotions.get(key, 0)} for key in EMOTION_NAMES], "逐句情感": [{"name": EMOTION_NAMES[key], "value": line_emotions.get(key, 0)} for key in EMOTION_NAMES]},
        "pqed": {"平均分": averages, "综合评分分布": [{"name": key, "value": score_distribution[key]} for key in sorted(score_distribution, key=float)]},
        "crrd": {"韵部数": len(crrd["pingshui"]), "平声字数": len(crrd["pingsheng"]), "仄声字数": len(crrd["zesheng"])},
        "dataset_metrics": dataset_metrics,
        "imagery": imagery,
        "usage": {
            "CCPC": "主题、诗人、朝代、关键词和体裁检索",
            "Chinese-poetry-master": "全唐诗、宋词、诗经、楚辞、四书五经等多类文本统计与检索",
            "FSPC": "整体与逐句五级情感对照",
            "CRRD": "平仄字表、韵部和近体诗规则校验",
            "PQED": "流畅度、连贯性、意蕴和综合质量标尺",
        },
    }
