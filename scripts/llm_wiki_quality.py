from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from llm_wiki_schema import iter_markdown_files, parse_frontmatter


OCR_ARTIFACT_PATTERNS = [
    r"\[第\d+页\]\s*\d*",
    r"\b\d{1,4}\s+[\u4e00-\u9fff]",
    r"\.{3,}",
]


def chinese_len(text: str) -> int:
    return len(re.findall(r"[\u4e00-\u9fff]", text))


def clean_quote(text: str) -> str:
    text = re.sub(r"\[第\d+页\]\s*\d*", "", text)
    text = re.sub(r"^\s*\d{1,4}\s+", "", text)
    text = re.sub(r"(?<=[\u4e00-\u9fff])\s+(?=[\u4e00-\u9fff])", "", text)
    text = re.sub(r"中华炎黄文化研究会太极文化专业委员会\s*\d*", "", text)
    text = re.sub(r"^\s*\d{1,4}\s*", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip("`-• ，,。；;：:|")
    text = text.replace("...", "…")
    return text


def extract_section(content: str, heading: str) -> str:
    marker = f"## {heading}"
    start = content.find(marker)
    if start == -1:
        return ""
    start += len(marker)
    next_match = re.search(r"\n##\s+", content[start:])
    end = start + next_match.start() if next_match else len(content)
    return content[start:end].strip()


def detect_self_links(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    meta = parse_frontmatter(content)
    title = str(meta.get("title", "")).strip()
    related = meta.get("related", [])
    problems: list[str] = []
    if title and isinstance(related, list) and title in related:
        problems.append(f"frontmatter related contains self title: {title}")
    basename = path.name
    for link in re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", content):
        if Path(link).name == basename:
            problems.append(f"body link points to self: {link}")
    return problems


def detect_ocr_artifacts(path: Path) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    problems: list[str] = []
    for pattern in OCR_ARTIFACT_PATTERNS:
        if re.search(pattern, content):
            problems.append(f"possible artifact: {pattern}")
    return problems


def count_markdown_rows(section: str) -> int:
    return sum(1 for line in section.splitlines() if line.strip().startswith("|") and "---" not in line)


def count_bullets(section: str) -> int:
    return sum(1 for line in section.splitlines() if line.strip().startswith("- "))


def score_source_page(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    summary = extract_section(content, "Summary")
    key_claims = extract_section(content, "Key Claims")
    evidence = extract_section(content, "Evidence Anchors")
    misreadings = extract_section(content, "Common Misreadings")
    practice = extract_section(content, "Practice Questions")
    problems: list[str] = []
    if chinese_len(summary) < 40:
        problems.append("summary too short")
    if "## Core Problem" not in content:
        problems.append("missing Core Problem")
    if count_markdown_rows(key_claims) < 4:
        problems.append("less than 3 key claims")
    if count_markdown_rows(evidence) < 4:
        problems.append("less than 3 evidence anchors")
    if count_bullets(misreadings) < 2:
        problems.append("less than 2 common misreadings")
    if count_bullets(practice) < 2:
        problems.append("less than 2 practice questions")
    problems.extend(detect_self_links(path))
    return {
        "path": str(path),
        "type": "source",
        "score": max(0, 100 - len(problems) * 15),
        "problems": problems,
    }


def score_topic_page(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    problems: list[str] = []
    required = [
        "## Summary",
        "## Core Problem",
        "## Why This Matters",
        "## Source Matrix",
        "## Claim Map",
        "## Concept Relations",
        "## Misreadings",
        "## Self-QA Lesson",
        "## Practice",
        "## Evidence Anchors",
        "## Related Pages",
    ]
    for section in required:
        if section not in content:
            problems.append(f"missing {section}")
    if count_markdown_rows(extract_section(content, "Source Matrix")) < 6:
        problems.append("source matrix has less than 5 sources")
    if count_markdown_rows(extract_section(content, "Claim Map")) < 6:
        problems.append("claim map has less than 5 claims")
    if count_bullets(extract_section(content, "Misreadings")) < 3:
        problems.append("less than 3 misreadings")
    if content.count("自问：") < 3:
        problems.append("less than 3 self-qa rounds")
    problems.extend(detect_self_links(path))
    return {
        "path": str(path),
        "type": "topic",
        "score": max(0, 100 - len(problems) * 12),
        "problems": problems,
    }


def score_generic_page(path: Path) -> dict[str, Any]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    meta = parse_frontmatter(content)
    problems: list[str] = []
    if "## Summary" in content and chinese_len(extract_section(content, "Summary")) < 20:
        problems.append("summary too short")
    problems.extend(detect_self_links(path))
    return {
        "path": str(path),
        "type": meta.get("type", "unknown"),
        "score": max(0, 100 - len(problems) * 10),
        "problems": problems,
    }


def score_page(path: Path) -> dict[str, Any]:
    meta = parse_frontmatter(path.read_text(encoding="utf-8", errors="ignore"))
    page_type = meta.get("type")
    if page_type == "source":
        return score_source_page(path)
    if page_type == "topic":
        return score_topic_page(path)
    return score_generic_page(path)


def write_quality_report(target_dir: Path, output_path: Path) -> dict[str, Any]:
    reports = [score_page(path) for path in iter_markdown_files(target_dir) if "_templates" not in path.parts]
    failing = [item for item in reports if item["problems"]]
    summary = {
        "target": str(target_dir),
        "page_count": len(reports),
        "failing_count": len(failing),
        "average_score": round(sum(item["score"] for item in reports) / max(1, len(reports)), 2),
        "pages": reports,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    dashboard = output_path.with_suffix(".md")
    lines = [
        "# LLM Wiki Quality Dashboard",
        "",
        f"- Target: `{target_dir}`",
        f"- Page count: {summary['page_count']}",
        f"- Failing count: {summary['failing_count']}",
        f"- Average score: {summary['average_score']}",
        "",
        "## Failing Pages",
        "",
    ]
    if failing:
        for item in failing:
            lines.append(f"- `{Path(item['path']).name}` ({item['type']}): {', '.join(item['problems'])}")
    else:
        lines.append("- No quality failures.")
    dashboard.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summary
