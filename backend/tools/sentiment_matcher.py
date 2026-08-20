# © 2026 BUPT_Mint-Green
# All rights reserved.

from collections import Counter

SENTIMENT_LABELS = {
    "1": "直白悲伤",
    "2": "含蓄悲伤",
    "3": "中性",
    "4": "含蓄喜悦",
    "5": "直白喜悦",
}

KEYWORDS = {
    "1": "悲 哀 痛 哭 泣 亡 破 凄 苦",
    "2": "愁 离 别 孤 寂 思 归 秋 暮",
    "3": "山 水 云 风 月 花 雪 江 鸟",
    "4": "暖 闲 静 清 春 友 归 乐",
    "5": "喜 欢 笑 庆 胜 豪 凯",
}


def parse_sentiment(record: dict) -> dict:
    labels = record.get("setiments") or record.get("sentiments") or {}
    holistic = str(labels.get("holistic", "3"))
    lines = [str(labels.get(f"line{i}", holistic)) for i in range(1, 5)]
    return {
        "holistic": holistic,
        "holistic_name": SENTIMENT_LABELS.get(holistic, "未知"),
        "lines": lines,
        "line_names": [SENTIMENT_LABELS.get(label, "未知") for label in lines],
    }


def infer_sentiment(text: str) -> dict:
    scores = Counter()
    for label, words in KEYWORDS.items():
        scores[label] = sum(text.count(word) for word in words.split())
    label = max(scores, key=lambda item: (scores[item], -abs(int(item) - 3))) if any(scores.values()) else "3"
    return {
        "label": label,
        "name": SENTIMENT_LABELS[label],
        "confidence": round(scores[label] / max(1, sum(scores.values())), 2),
        "distribution": {SENTIMENT_LABELS[key]: scores[key] for key in SENTIMENT_LABELS},
    }


def find_sentiment_examples(records: list[dict], target: str, top_k: int = 5) -> list[dict]:
    target_label = target if target in SENTIMENT_LABELS else infer_sentiment(target)["label"]
    matches = []
    for record in records:
        parsed = parse_sentiment(record)
        if parsed["holistic"] == target_label:
            matches.append(record)
        if len(matches) >= top_k:
            break
    return matches
