# © 2026 BUPT_Mint-Green
# All rights reserved.

import re
from collections import Counter

import jieba

from backend.data_loader import normalize_poem

STOP_WORDS = {"写", "一首", "诗", "诗词", "帮我", "请", "的", "以", "为", "主题", "关于", "进行", "分析", "赏析"}


def tokenize(text: str) -> list[str]:
    words = []
    for word in jieba.lcut(text):
        word = word.strip()
        if word and word not in STOP_WORDS and not re.fullmatch(r"\W+", word):
            words.append(word)
    return words


def poem_lines(record: dict) -> list[str]:
    return [line.strip() for line in normalize_poem(record).split("|") if line.strip()]


def infer_form(record: dict) -> str:
    lines = poem_lines(record)
    lengths = {len(line) for line in lines}
    if len(lines) == 4 and lengths == {5}:
        return "五言绝句"
    if len(lines) == 4 and lengths == {7}:
        return "七言绝句"
    if len(lines) == 8 and lengths == {5}:
        return "五言律诗"
    if len(lines) == 8 and lengths == {7}:
        return "七言律诗"
    return "古体诗"


class PoetryRetriever:
    def __init__(self, records: list[dict]):
        self.records = records
        self.documents = []
        for record in records:
            searchable = " ".join(str(record.get(key, "")) for key in ("title", "author", "poet", "dynasty", "keywords"))
            searchable += " " + normalize_poem(record)
            self.documents.append(Counter(tokenize(searchable)))

    def search(self, query: str, top_k: int = 5, form: str = "", dynasty: str = "") -> list[dict]:
        query_terms = Counter(tokenize(query))
        scored = []
        for record, document in zip(self.records, self.documents):
            if form and form != "不限" and infer_form(record) != form:
                continue
            if dynasty and dynasty != "不限" and dynasty.lower() not in str(record.get("dynasty", "")).lower():
                continue
            exact = sum(min(count, document.get(term, 0)) * (2 if len(term) > 1 else 1) for term, count in query_terms.items())
            keyword_bonus = sum(2 for term in query_terms if term in str(record.get("keywords", "")))
            score = exact + keyword_bonus
            if score:
                scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [{**record, "form": infer_form(record), "retrieval_score": score} for score, record in scored[:top_k]]
