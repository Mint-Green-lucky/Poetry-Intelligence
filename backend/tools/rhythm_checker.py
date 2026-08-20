# © 2026 BUPT_Mint-Green
# All rights reserved.

import re
from dataclasses import asdict, dataclass

PUNCTUATION = "，。！？、；：,.!?;: \t"


@dataclass
class RhythmResult:
    genre: str
    lines: list[str]
    tone_patterns: list[str]
    rhyme: dict
    errors: list[str]
    score: float

    def to_dict(self) -> dict:
        return asdict(self)


class RhythmChecker:
    def __init__(self, pingsheng: set[str], zesheng: set[str], char_to_rhyme: dict[str, list[int]]):
        self.pingsheng = pingsheng
        self.zesheng = zesheng
        self.char_to_rhyme = char_to_rhyme

    def tone(self, char: str) -> str:
        in_ping = char in self.pingsheng
        in_ze = char in self.zesheng
        if in_ping and in_ze:
            return "多"
        if in_ping:
            return "平"
        if in_ze:
            return "仄"
        return "?"

    def split_lines(self, poem: str) -> list[str]:
        parts = re.split(r"[|\n，。！？；,.!?;]+", poem)
        return [part.strip(PUNCTUATION) for part in parts if part.strip(PUNCTUATION)]

    def detect_genre(self, lines: list[str]) -> str:
        lengths = {len(line) for line in lines}
        if len(lines) == 4 and lengths == {5}:
            return "五言绝句"
        if len(lines) == 4 and lengths == {7}:
            return "七言绝句"
        if len(lines) == 8 and lengths == {5}:
            return "五言律诗"
        if len(lines) == 8 and lengths == {7}:
            return "七言律诗"
        return "非标准近体诗"

    def check_rhyme(self, lines: list[str]) -> dict:
        positions = []
        for number in range(2, len(lines) + 1, 2):
            char = lines[number - 1][-1]
            positions.append({"line": number, "char": char, "groups": self.char_to_rhyme.get(char, [])})
        if len(positions) < 2:
            return {"consistent": None, "positions": positions, "common_groups": []}
        common = set(positions[0]["groups"])
        for position in positions[1:]:
            common.intersection_update(position["groups"])
        return {"consistent": bool(common), "positions": positions, "common_groups": sorted(common)}

    def check(self, poem: str) -> dict:
        lines = self.split_lines(poem)
        errors: list[str] = []
        genre = self.detect_genre(lines)
        if genre == "非标准近体诗":
            errors.append("句数或每句字数不符合五言、七言绝句/律诗的常见格式")

        patterns = ["".join(self.tone(char) for char in line) for line in lines]
        characters = [[{"char": char, "tone": tone, "position": position + 1} for position, (char, tone) in enumerate(zip(line, pattern))] for line, pattern in zip(lines, patterns)]
        unknown = sum(pattern.count("?") for pattern in patterns)
        total = sum(len(pattern) for pattern in patterns)
        if unknown:
            errors.append(f"有 {unknown} 个字无法由当前 CRRD 字表确定平仄")

        for index, pattern in enumerate(patterns, 1):
            if len(pattern) >= 4 and pattern[1] in "平仄" and pattern[3] in "平仄" and pattern[1] == pattern[3]:
                errors.append(f"第 {index} 句第二、四字同声，可能失替")

        rhyme = self.check_rhyme(lines)
        if rhyme["consistent"] is False:
            errors.append("偶数句韵脚不属于同一平水韵部")

        penalty = 0.18 * sum("可能失替" in error for error in errors)
        penalty += 0.35 if rhyme["consistent"] is False else 0
        penalty += 0.25 if genre == "非标准近体诗" else 0
        coverage = (total - unknown) / total if total else 0
        score = round(max(0, min(1, (1 - penalty) * coverage)), 2)
        result = RhythmResult(genre, lines, patterns, rhyme, errors, score)
        result_dict = result.to_dict()
        rhyme_lines = {item["line"] for item in rhyme["positions"]}
        for line_number, line_chars in enumerate(characters, 1):
            if line_number in rhyme_lines and line_chars:
                line_chars[-1]["rhyme"] = True
                groups = next((item["groups"] for item in rhyme["positions"] if item["line"] == line_number), [])
                line_chars[-1]["rhyme_groups"] = groups
        result_dict["characters"] = characters
        return result_dict
