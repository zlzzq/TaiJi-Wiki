from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from llm_wiki_quality import chinese_len, extract_section
from llm_wiki_schema import parse_frontmatter


V3_SOURCE_REQUIRED = [
    "## Summary",
    "## Core Problem",
    "## 原文命脉",
    "## 三晳解读",
    "### 生成：它从哪里生起",
    "### 对待：它破哪一种二边",
    "### 变化：它怎样转入修证",
    "## 三界安放",
    "## 修证关口",
    "## 常见误读",
    "## 自问自答",
    "## Practice Questions",
    "## Evidence Anchors",
    "## Related Pages",
]

V3_TOPIC_REQUIRED = [
    "## 一句定宗",
    "## 为什么此题是根本关口",
    "## 原文命脉",
    "## 三晳圆转",
    "## 三界定位",
    "## 理入与行入",
    "## 误区破除",
    "## 自问自答带学",
    "## 练习",
    "## Source Matrix",
    "## Evidence Anchors",
    "## Related Pages",
]

V3_CONCEPT_REQUIRED = [
    "## Summary",
    "## Definition By Layer",
    "## 三晳安放",
    "## 使用场景",
    "## 常见误读",
    "## Practice Questions",
    "## Evidence Anchors",
    "## Related Pages",
]

GENERIC_PATTERNS = [
    "回到问题本身",
    "不要堆术语",
    "避免说死",
    "这不是概念而是活法",
    "理解 X 要回到 Y",
]


def compact_text(text: str) -> str:
    text = re.sub(r"\[第\d+页\]\s*\d*", "", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.strip("`-• ，,。；;：:|")


def quote_limit(text: str, limit: int = 40) -> str:
    text = compact_text(text)
    text = text.replace("“", "").replace("”", "").replace('"', "")
    text = re.sub(r"^\s*\d{1,4}\s+", "", text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip("，。；、 ") + "…"


def count_bullets(section: str) -> int:
    return sum(1 for line in section.splitlines() if line.strip().startswith("- "))


def count_rows(section: str) -> int:
    return sum(1 for line in section.splitlines() if line.strip().startswith("|") and "---" not in line)


def find_generic_without_followup(content: str) -> list[str]:
    problems: list[str] = []
    lines = content.splitlines()
    for index, line in enumerate(lines):
        for pattern in GENERIC_PATTERNS:
            if pattern == "理解 X 要回到 Y":
                if re.search(r"理解.+要回到", line) and chinese_len("".join(lines[index : index + 2])) < 55:
                    problems.append(f"generic phrase lacks concrete follow-up: {line[:32]}")
                continue
            if pattern in line and chinese_len("".join(lines[index : index + 2])) < 55:
                problems.append(f"generic phrase lacks concrete follow-up: {pattern}")
    return problems


def detect_self_related(path: Path, content: str) -> list[str]:
    meta = parse_frontmatter(content)
    title = str(meta.get("title", "")).strip()
    related = meta.get("related", [])
    problems: list[str] = []
    if title and isinstance(related, list) and title in related:
        problems.append(f"frontmatter related contains self title: {title}")
    for link in re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", content):
        if Path(link).name == path.name:
            problems.append(f"body link points to self: {link}")
    return problems


def score_v3_page(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    meta = parse_frontmatter(content)
    page_type = str(meta.get("type", ""))
    problems: list[str] = []

    if page_type == "source":
        for section in V3_SOURCE_REQUIRED:
            if section not in content:
                problems.append(f"missing {section}")
        if chinese_len(extract_section(content, "Summary")) < 80:
            problems.append("summary under 80 Chinese chars")
        if count_rows(extract_section(content, "Evidence Anchors")) < 4:
            problems.append("less than 3 evidence anchors")
        if count_bullets(extract_section(content, "常见误读")) < 2:
            problems.append("less than 2 common misreadings")
        if count_bullets(extract_section(content, "Practice Questions")) < 2:
            problems.append("less than 2 practice questions")
        if "生成：" not in content or "对待：" not in content or "变化：" not in content:
            problems.append("missing sheng/dui/bian language")
        if "无极" not in content and "无界" not in content:
            problems.append("missing wuji/wujie placement")
        if "太极" not in content and "有无界" not in content:
            problems.append("missing taiji/youwu placement")
        if "有极" not in content and "有界" not in content:
            problems.append("missing youji/youjie placement")
    elif page_type == "topic":
        for section in V3_TOPIC_REQUIRED:
            if section not in content:
                problems.append(f"missing {section}")
        if count_rows(extract_section(content, "Source Matrix")) < 6:
            problems.append("source matrix has less than 5 sources")
        if content.count("自问：") < 3:
            problems.append("less than 3 self-qa rounds")
        if count_bullets(extract_section(content, "误区破除")) < 3:
            problems.append("less than 3 misreadings")
        if "生成" not in content or "对待" not in content or "变化" not in content:
            problems.append("topic does not rotate through sheng/dui/bian")
    elif page_type == "concept":
        for section in V3_CONCEPT_REQUIRED:
            if section not in content:
                problems.append(f"missing {section}")
    elif page_type in {"query", "contradiction"}:
        if "## Summary" in content and chinese_len(extract_section(content, "Summary")) < 40:
            problems.append("summary too short")
        if "## Practice Questions" in content and count_bullets(extract_section(content, "Practice Questions")) < 2:
            problems.append("less than 2 practice questions")

    problems.extend(detect_self_related(path, content))
    problems.extend(find_generic_without_followup(content))
    return {
        "path": str(path),
        "type": page_type or "unknown",
        "score": max(0, 100 - len(problems) * 10),
        "problems": problems,
    }


def validate_source_profile(data: dict[str, Any]) -> list[str]:
    required = [
        "source_slug",
        "title",
        "core_problem",
        "original_lifeline",
        "sheng_dui_bian",
        "sanjie_position",
        "practice_gate",
        "key_claims",
        "evidence_anchors",
        "common_misreadings",
        "teaching_questions",
    ]
    problems = [f"missing {key}" for key in required if key not in data]
    sdb = data.get("sheng_dui_bian", {})
    if not isinstance(sdb, dict) or not all(key in sdb for key in ["sheng", "dui", "bian"]):
        problems.append("sheng_dui_bian must contain sheng/dui/bian")
    return problems


def dump_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n", encoding="utf-8")
