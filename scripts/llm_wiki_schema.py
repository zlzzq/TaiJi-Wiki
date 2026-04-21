from __future__ import annotations

import re
from pathlib import Path
from typing import Any


PUBLIC_FORBIDDEN_PATTERNS = [
    "## 全文",
    "corpus-fulltext",
    "output/knowledge/text",
    "output\\knowledge\\text",
    "output/external",
    "output\\external",
    "agent_runs",
    "private_notes",
    "evidence.jsonl",
    "wiki/docs",
    "wiki\\docs",
]

REQUIRED_SECTIONS_BY_TYPE = {
    "source": ["## Summary", "## Source Metadata", "## Key Claims", "## Related Topics"],
    "topic": ["## Summary", "## Related Pages", "## Evidence Anchors"],
    "concept": ["## Summary", "## Related Terms", "## Evidence Anchors"],
    "term": ["## Summary"],
    "contradiction": ["## The Tension", "## Stable Reading"],
    "query": ["## Answer", "## Sources Used", "## Follow-Up Questions"],
    "map": ["## Summary"],
    "index": ["## Start Here"],
    "log": [],
    "rule": [],
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    aliases = {
        "三晳": "sanxi",
        "三界": "three-realms",
        "太极": "taiji",
        "本知": "ben-zhi",
        "客知": "ke-zhi",
        "性知": "xing-zhi",
        "理入": "li-ru",
        "行入": "xing-ru",
        "无极": "wuji",
        "化生": "huasheng",
        "生成": "shengcheng",
        "对待": "duidai",
        "流行": "liuxing",
        "变化": "bianhua",
        "悟": "wu",
        "证": "zheng",
    }
    if value in aliases:
        return aliases[value]
    value = re.sub(r"[^\w\u4e00-\u9fff]+", "-", value, flags=re.UNICODE)
    value = value.strip("-")
    if re.fullmatch(r"[\u4e00-\u9fff-]+", value):
        # Stable pinyin-like fallback is not available; keep short Chinese slugs readable.
        return value
    return value or "untitled"


def yaml_list(items: list[str], indent: int = 2) -> str:
    pad = " " * indent
    if not items:
        return f"{pad}[]"
    return "\n".join(f"{pad}- {item}" for item in items)


def frontmatter(
    *,
    title: str,
    page_type: str,
    status: str = "compiled",
    visibility: str = "public",
    source_count: int = 0,
    last_compiled: str,
    tags: list[str] | None = None,
    related: list[str] | None = None,
) -> str:
    tags = tags or []
    related = related or []
    return (
        "---\n"
        f"title: {title}\n"
        f"type: {page_type}\n"
        f"status: {status}\n"
        f"visibility: {visibility}\n"
        f"source_count: {source_count}\n"
        f"last_compiled: {last_compiled}\n"
        "tags:\n"
        f"{yaml_list(tags)}\n"
        "related:\n"
        f"{yaml_list(related)}\n"
        "---\n\n"
    )


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell.replace("\n", "<br>") for cell in row) + " |")
    return "\n".join(lines)


def bullets(items: list[str], empty: str = "暂无。") -> str:
    clean = [item for item in items if item]
    if not clean:
        return f"- {empty}"
    return "\n".join(f"- {item}" for item in clean)


def strip_markdown_links(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


def truncate_cn(text: str, limit: int = 40) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip("`-• ，,。；;：:")
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def remove_private_sections(content: str) -> str:
    lines = content.splitlines()
    output: list[str] = []
    skip = False
    for line in lines:
        if line.strip() == "## Private Notes":
            skip = True
            continue
        if skip and line.startswith("## "):
            skip = False
        if not skip:
            output.append(line)
    return "\n".join(output).rstrip() + "\n"


def use_public_quote_anchors(content: str) -> str:
    if "## Public Quote Anchors" not in content:
        return content
    content = re.sub(
        r"\n## Evidence Anchors\n.*?(?=\n## Public Quote Anchors\n)",
        "\n",
        content,
        flags=re.S,
    )
    return content.replace("## Public Quote Anchors", "## Evidence Anchors")


def is_private_page(content: str) -> bool:
    head = content[:500]
    return bool(re.search(r"^visibility:\s*private\s*$", head, re.MULTILINE))


def public_transform(content: str) -> str:
    content = remove_private_sections(content)
    content = use_public_quote_anchors(content)
    replacements = {
        "output/knowledge/text/": "私有全文资料库：",
        "output\\knowledge\\text\\": "私有全文资料库：",
        "wiki/docs/corpus/": "私有全文页：",
        "wiki\\docs\\corpus\\": "私有全文页：",
    }
    for old, new in replacements.items():
        content = content.replace(old, new)
    content = content.replace("visibility: private", "visibility: public")
    return content


def parse_frontmatter(content: str) -> dict[str, Any]:
    if not content.startswith("---"):
        return {}
    end = content.find("\n---", 3)
    if end == -1:
        return {}
    raw = content[3:end].strip().splitlines()
    data: dict[str, Any] = {}
    key = None
    for line in raw:
        if re.match(r"^[A-Za-z_]+:", line):
            key, value = line.split(":", 1)
            value = value.strip()
            data[key] = [] if value == "" else value
            continue
        if key and line.strip().startswith("- "):
            if not isinstance(data.get(key), list):
                data[key] = []
            data[key].append(line.strip()[2:])
    return data


def validate_page(path: Path, *, public: bool = False) -> list[str]:
    content = path.read_text(encoding="utf-8", errors="ignore")
    problems: list[str] = []
    if not content.startswith("---"):
        problems.append("missing frontmatter")
        return problems
    meta = parse_frontmatter(content)
    page_type = str(meta.get("type", ""))
    required = REQUIRED_SECTIONS_BY_TYPE.get(page_type, ["## Summary"])
    for section in required:
        if section not in content:
            problems.append(f"missing section {section}")
    if "title" not in meta:
        problems.append("missing title")
    if "visibility" not in meta:
        problems.append("missing visibility")
    if public:
        lower = content.lower()
        for pattern in PUBLIC_FORBIDDEN_PATTERNS:
            if pattern.lower() in lower:
                problems.append(f"public forbidden pattern: {pattern}")
    return problems


def iter_markdown_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.md") if path.is_file())
