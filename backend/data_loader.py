# © 2026 BUPT_Mint-Green
# All rights reserved.

from __future__ import annotations

import json
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Optional

from backend.config import (
    CCPC_TEST,
    CCPC_TRAIN,
    CCPC_VALID,
    CRRD_PINGSHENG,
    CRRD_PINGSHUI,
    CRRD_ZESHENG,
    DATA_ROOT,
    THU_DATA_DIR,
    FSPC_DATA,
    MAX_CCPC_IN_MEMORY,
    PQED_DATA,
)


def load_jsonl(filepath: Path, max_lines: Optional[int] = None) -> list[dict]:
    records: list[dict] = []
    with filepath.open("r", encoding="utf-8") as file:
        for index, line in enumerate(file):
            if max_lines is not None and index >= max_lines:
                break
            if line.strip():
                records.append(json.loads(line))
    return records


def normalize_poem(record: dict) -> str:
    return str(record.get("content") or record.get("poem") or "").strip()


@lru_cache(maxsize=1)
def load_ccpc() -> list[dict]:
    per_split = max(1, MAX_CCPC_IN_MEMORY // 3)
    records: list[dict] = []
    for path in (CCPC_TRAIN, CCPC_VALID, CCPC_TEST):
        records.extend(load_jsonl(path, per_split))
    return records


def _iter_chinese_poetry_candidates(root: Path):
    candidates = [
        root / "chinese-poetry-master.zip",
        root / "chinese-poetry-master",
        root / "Chinese-poetry-master.zip",
        root / "Chinese-poetry-master",
    ]
    if DATA_ROOT.exists():
        candidates.extend([
            DATA_ROOT / "chinese-poetry-master.zip",
            DATA_ROOT / "chinese-poetry-master",
            DATA_ROOT / "Chinese-poetry-master.zip",
            DATA_ROOT / "Chinese-poetry-master",
        ])
    return candidates


@lru_cache(maxsize=1)
def load_chinese_poetry(max_records: int = 50000) -> list[dict]:
    source_path: Path | None = None
    for candidate in _iter_chinese_poetry_candidates(DATA_ROOT):
        if candidate.exists():
            source_path = candidate
            break
    if source_path is None:
        return []
    records: list[dict] = []
    if source_path.is_dir():
        json_files = [p for p in source_path.rglob("*.json") if "error" not in p.parts]
        for file_path in json_files:
            try:
                payload = json.loads(file_path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError, OSError):
                continue
            dynasty = "唐" if "全唐诗" in file_path.parts or "唐诗" in file_path.parts else "宋" if "宋词" in file_path.parts else ""
            items = payload if isinstance(payload, list) else []
            for item in items:
                paragraphs = item.get("paragraphs") or []
                content = "".join(str(part) for part in paragraphs).strip()
                if not content:
                    continue
                records.append({
                    "title": item.get("title") or file_path.stem,
                    "author": item.get("author") or item.get("name") or "佚名",
                    "dynasty": dynasty,
                    "category": file_path.relative_to(source_path).parts[0] if file_path.relative_to(source_path).parts else "其他",
                    "content": content,
                    "source": "中华诗歌数据集",
                })
                if len(records) >= max_records:
                    return records
        return records
    with zipfile.ZipFile(source_path) as archive:
        names = [name for name in archive.namelist() if name.endswith(".json") and ("json/poet." in name or "ci/ci." in name)]
        for name in names:
            try:
                payload = json.loads(archive.read(name).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue
            dynasty = "唐" if "/poet.tang." in name else "宋" if "/poet.song." in name else ""
            for item in payload if isinstance(payload, list) else []:
                paragraphs = item.get("paragraphs") or []
                content = "".join(str(part) for part in paragraphs).strip()
                if not content:
                    continue
                records.append({
                    "title": item.get("title") or "无题",
                    "author": item.get("author") or "佚名",
                    "dynasty": dynasty,
                    "content": content,
                    "source": "中华诗歌数据集",
                })
                if len(records) >= max_records:
                    return records
    return records


@lru_cache(maxsize=1)
def load_fspc() -> list[dict]:
    return load_jsonl(FSPC_DATA)


@lru_cache(maxsize=1)
def load_pqed() -> list[dict]:
    return load_jsonl(PQED_DATA)


def _load_character_set(path: Path) -> set[str]:
    characters: set[str] = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        token = line.strip().split(maxsplit=1)[0] if line.strip() else ""
        characters.update(token)
    return characters


@lru_cache(maxsize=1)
def load_crrd() -> dict:
    grouped: dict[int, list[str]] = {}
    char_to_rhyme: dict[str, list[int]] = {}
    pingshui_path = CRRD_PINGSHUI if CRRD_PINGSHUI.exists() else THU_DATA_DIR / "CRRD" / "pingshui.txt"
    pingsheng_path = CRRD_PINGSHENG if CRRD_PINGSHENG.exists() else THU_DATA_DIR / "CRRD" / "pingsheng.txt"
    zesheng_path = CRRD_ZESHENG if CRRD_ZESHENG.exists() else THU_DATA_DIR / "CRRD" / "zesheng.txt"
    if not pingshui_path.exists():
        return {
            "pingsheng": set(),
            "zesheng": set(),
            "pingshui": [],
            "char_to_rhyme": {},
        }
    for line in pingshui_path.read_text(encoding="utf-8").splitlines():
        parts = line.strip().split()
        if len(parts) != 2 or not parts[1].isdigit():
            continue
        char, group_text = parts
        group = int(group_text)
        grouped.setdefault(group, []).append(char)
        char_to_rhyme.setdefault(char, []).append(group)
    groups = ["".join(grouped[key]) for key in sorted(grouped)]
    return {
        "pingsheng": _load_character_set(pingsheng_path),
        "zesheng": _load_character_set(zesheng_path),
        "pingshui": groups,
        "char_to_rhyme": char_to_rhyme,
    }


def dataset_summary() -> dict:
    return {
        "ccpc_loaded": len(load_ccpc()),
        "chinese_poetry": len(load_chinese_poetry()),
        "fspc": len(load_fspc()),
        "pqed": len(load_pqed()),
        "rhyme_groups": len(load_crrd()["pingshui"]),
    }
