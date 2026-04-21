from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = ROOT / "output" / "knowledge"
TEXT_DIR = KNOWLEDGE_DIR / "text"
COMPILED_TOPICS_DIR = KNOWLEDGE_DIR / "compiled" / "topics"
PRIVATE_WIKI_DIR = ROOT / "wiki"
PUBLIC_WIKI_DIR = ROOT / "public_wiki"
PRIVATE_REPO_URL = "https://github.com/zlzzq/TaiJi"
PUBLIC_REPO_URL = "https://github.com/zlzzq/TaiJi-Wiki"
PRIVATE_SITE_URL = "https://zlzzq.github.io/TaiJi/"
PUBLIC_SITE_URL = "https://zlzzq.github.io/TaiJi-Wiki/"

MODE = "private"
WIKI_DIR = PRIVATE_WIKI_DIR
DOCS_DIR = WIKI_DIR / "docs"
REPO_URL = PRIVATE_REPO_URL
SITE_URL = PRIVATE_SITE_URL
REPO_NAME = "zlzzq/TaiJi"
SITE_DESCRIPTION = "三晳资料本地知识库生成的私有全文 Wiki"


STATIC_PAGES = {
    "learning/concept-map.md": "concept_map.md",
    "learning/teaching-playbook.md": "teaching_playbook.md",
    "learning/demo-qa.md": "demo_qa.md",
    "terms/glossary.md": "glossary.md",
    "terms/index.md": "term_index.md",
}

TOPIC_TITLES = {
    "sanxi-nine-realms": "三晳九境",
}


MODULE_ORDER = [
    "模块 A：入门总纲",
    "模块 B：三晳结构",
    "模块 C：三界与心性",
    "模块 D：理入与修证",
    "模块 E：答疑与破执",
    "模块 F：总讲与通盘串联",
    "待归类",
]


PRIORITY_ORDER = [
    "一级主干资料",
    "二级基础框架资料",
    "三级专题深化资料",
    "四级问答案例资料",
    "五级附录资料",
    "未分级资料",
]

REQUIREMENTS = """mkdocs>=1.6,<2
mkdocs-material>=9.5,<10
mkdocs-glightbox>=0.4,<1
mkdocs-minify-plugin>=0.8,<1
jieba>=0.42.1,<1
"""


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def configure_mode(mode: str) -> None:
    global MODE, WIKI_DIR, DOCS_DIR, REPO_URL, SITE_URL, REPO_NAME, SITE_DESCRIPTION

    MODE = mode
    if mode == "public":
        WIKI_DIR = PUBLIC_WIKI_DIR
        REPO_URL = PUBLIC_REPO_URL
        SITE_URL = PUBLIC_SITE_URL
        REPO_NAME = "zlzzq/TaiJi-Wiki"
        SITE_DESCRIPTION = "三晳资料本地知识库生成的公开摘要 Wiki"
    else:
        WIKI_DIR = PRIVATE_WIKI_DIR
        REPO_URL = PRIVATE_REPO_URL
        SITE_URL = PRIVATE_SITE_URL
        REPO_NAME = "zlzzq/TaiJi"
        SITE_DESCRIPTION = "三晳资料本地知识库生成的私有全文 Wiki"
    DOCS_DIR = WIKI_DIR / "docs"


def is_public_mode() -> bool:
    return MODE == "public"


def reset_docs_dir() -> None:
    if DOCS_DIR.exists():
        shutil.rmtree(DOCS_DIR)
    for subdir in ["assets", "corpus", "learning", "sources", "terms", "topics"]:
        (DOCS_DIR / subdir).mkdir(parents=True, exist_ok=True)


def sort_key(record: dict[str, Any]) -> tuple[int, str]:
    name = record["file_name"]
    if name.startswith("附"):
        digits = re.findall(r"\d+", name)
        return (1000 + int(digits[0]) if digits else 1999, name)
    match = re.match(r"(\d+)", name)
    if match:
        return (int(match.group(1)), name)
    return (9999, name)


def record_slug(index: int, record: dict[str, Any]) -> str:
    stem = Path(record["file_name"]).stem
    number = re.match(r"(\d+)", stem)
    if number:
        return f"{index:03d}-{number.group(1)}"
    appendix = re.match(r"附(\d+)", stem)
    if appendix:
        return f"{index:03d}-appendix-{appendix.group(1)}"
    return f"{index:03d}"


def bullet_list(items: list[str]) -> str:
    if not items:
        return "- 暂无。"
    return "\n".join(f"- {item}" for item in items)


def inline_list(items: list[str]) -> str:
    return "、".join(f"`{item}`" for item in items) if items else "暂无"


def md_table(headers: list[str], rows: list[list[str]]) -> str:
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(cell.replace("\n", "<br>") for cell in row) + " |")
    return "\n".join(lines)


def safe_code_block(text: str) -> str:
    return "<pre class=\"corpus-fulltext\"><code>" + html.escape(text) + "</code></pre>"


def corpus_link(record: dict[str, Any]) -> str:
    return f"../corpus/{record['wiki_slug']}.md"


def copy_static_pages() -> None:
    for target, source_name in STATIC_PAGES.items():
        source_path = KNOWLEDGE_DIR / source_name
        if not source_path.exists():
            continue
        content = read_text(source_path)
        if is_public_mode():
            content = content.replace(
                "直接看 `output/knowledge/text/` 下对应全文。",
                "在受控访问的私有资料库中核对对应原文。",
            )
        write_text(DOCS_DIR / target, content)


def discover_compiled_topics() -> list[dict[str, str]]:
    if not COMPILED_TOPICS_DIR.exists():
        return []

    topics = []
    source_name = "public_page.md" if is_public_mode() else "private_dossier.md"
    for topic_dir in sorted(path for path in COMPILED_TOPICS_DIR.iterdir() if path.is_dir()):
        source_path = topic_dir / source_name
        if not source_path.exists():
            continue
        title = TOPIC_TITLES.get(topic_dir.name, topic_dir.name)
        topics.append({"slug": topic_dir.name, "title": title, "source": source_name})
    return topics


def write_topic_pages(topics: list[dict[str, str]]) -> None:
    if not topics:
        write_text(
            DOCS_DIR / "topics" / "index.md",
            "# 专题\n\n当前还没有已编译专题。\n",
        )
        return

    lines = ["# 专题", "", "本页汇总经过多轮编译的专题内容。", ""]
    for topic in topics:
        lines.append(f"- [{topic['title']}]({topic['slug']}.md)")
    lines.append("")
    write_text(DOCS_DIR / "topics" / "index.md", "\n".join(lines))

    for topic in topics:
        source_path = COMPILED_TOPICS_DIR / topic["slug"] / topic["source"]
        write_text(DOCS_DIR / "topics" / f"{topic['slug']}.md", read_text(source_path))
        if not is_public_mode():
            support_pages = {
                "teaching_lesson.md": f"{topic['slug']}-teaching-lesson.md",
                "qa_drills.md": f"{topic['slug']}-qa-drills.md",
                "concept_graph.md": f"{topic['slug']}-concept-graph.md",
                "source_map.md": f"{topic['slug']}-source-map.md",
                "review_report.md": f"{topic['slug']}-review-report.md",
            }
            for source_name, target_name in support_pages.items():
                support_path = COMPILED_TOPICS_DIR / topic["slug"] / source_name
                if support_path.exists():
                    write_text(DOCS_DIR / "topics" / target_name, read_text(support_path))


def build_index_page(records: list[dict[str, Any]], topics: list[dict[str, str]]) -> str:
    total = len(records)
    ok_count = sum(1 for record in records if record["extraction_status"] == "ok")
    pending_count = total - ok_count
    module_counts = defaultdict(int)
    for record in records:
        module_counts[record["module"]] += 1

    rows = []
    for module in MODULE_ORDER:
        if module_counts[module]:
            rows.append([module, str(module_counts[module])])

    if is_public_mode():
        notice_title = "公开摘要版"
        notice_body = "本站只包含资料索引、摘要、术语、概念图和学习路径，不包含抽取全文，也不提供原始资料下载入口。"
    else:
        notice_title = "私有仓库全文版"
        notice_body = "本站包含抽取后的全文内容。默认使用场景是私有仓库或受控访问，不建议公开传播完整原文。"

    topic_lines = ""
    if topics:
        topic_lines = "\n".join(f"- [{topic['title']}](topics/{topic['slug']}.md)" for topic in topics)
    else:
        topic_lines = "- 暂无。"

    return f"""# 三晳资料 Wiki

这是由本地 `output/knowledge` 编译生成的三晳资料静态 Wiki。

!!! warning "{notice_title}"
    {notice_body}

## 资料统计

- 资料总数：{total}
- 已抽取正文：{ok_count}
- 待补证资料：{pending_count}

## 推荐入口

- [概念总图](learning/concept-map.md)
- [核心术语表](terms/glossary.md)
- [资料总览](sources/index.md)
- [待补证资料](sources/pending.md)
- [教学模板](learning/teaching-playbook.md)
- [示例问答](learning/demo-qa.md)

## 专题入口

{topic_lines}

## 模块分布

{md_table(["模块", "资料数"], rows)}

## 建议阅读顺序

1. 先看 [核心术语表](terms/glossary.md) 和 [概念总图](learning/concept-map.md)，建立地图。
2. 再看 [资料总览](sources/index.md)，按模块进入单篇资料。
3. 需要查具体术语时，使用 [术语索引](terms/index.md) 或站内搜索。
4. 学习表达和答问时，看 [教学模板](learning/teaching-playbook.md) 与 [示例问答](learning/demo-qa.md)。

## 编译边界

- 公开摘要版不嵌入抽取全文；私有全文版才使用全文抽取文本。
- Wiki 不直接暴露原始 `.docx` / `.pdf` 下载入口。
- 自动摘要与摘录只作为导航和学习辅助，不替代原文。
- 每个单篇资料页都保留来源文件名，便于回查。
"""


def build_corpus_index_page(records: list[dict[str, Any]]) -> str:
    rows = []
    for record in records:
        rows.append(
            [
                f"[{record['title']}]({record['wiki_slug']}.md)",
                record["file_name"],
                record["priority"],
                record["module"],
                record["extraction_status"],
                str(record["char_count"]),
            ]
        )
    title = "# 资料摘要索引" if is_public_mode() else "# 资料全文索引"
    return f"{title}\n\n" + md_table(
        ["标题", "来源文件", "层级", "模块", "抽取状态", "字数"],
        rows,
    ) + "\n"


def build_sources_page(records: list[dict[str, Any]]) -> str:
    target = "摘要页" if is_public_mode() else "全文页"
    lines = ["# 资料总览", "", f"本页按教学模块汇总资料，并链接到{target}。", ""]
    grouped = defaultdict(list)
    for record in records:
        grouped[record["module"]].append(record)

    for module in MODULE_ORDER:
        module_records = sorted(grouped.get(module, []), key=sort_key)
        if not module_records:
            continue
        lines.extend([f"## {module}", ""])
        rows = []
        for record in module_records:
            rows.append(
                [
                    f"[{record['title']}]({corpus_link(record)})",
                    record["priority"],
                    inline_list(record["key_terms"][:5]),
                    record["extraction_status"],
                ]
            )
        lines.append(md_table(["资料", "层级", "核心概念", "状态"], rows))
        lines.append("")

    lines.extend(["## 按资料层级", ""])
    priority_groups = defaultdict(list)
    for record in records:
        priority_groups[record["priority"]].append(record)
    for priority in PRIORITY_ORDER:
        priority_records = sorted(priority_groups.get(priority, []), key=sort_key)
        if not priority_records:
            continue
        lines.append(f"### {priority}")
        lines.append("")
        for record in priority_records:
            lines.append(f"- [{record['title']}]({corpus_link(record)})")
        lines.append("")

    return "\n".join(lines)


def build_pending_page(records: list[dict[str, Any]]) -> str:
    pending = [record for record in records if record["extraction_status"] != "ok"]
    lines = ["# 待补证资料", ""]
    if not pending:
        lines.append("当前没有待补证资料。")
        return "\n".join(lines)

    rows = []
    for record in pending:
        rows.append(
            [
                record["file_name"],
                record["extraction_status"],
                record.get("notes", ""),
                f"[查看条目]({corpus_link(record)})",
            ]
        )
    lines.append(md_table(["文件", "状态", "备注", "链接"], rows))
    lines.append("")
    lines.append("首版 Wiki 不处理老式 `.doc` 的稳定抽取问题，仅在此标记。")
    return "\n".join(lines)


def build_learning_path_page(records: list[dict[str, Any]]) -> str:
    lines = [
        "# 学习路径",
        "",
        "本页把现有资料编成一个从入门到总讲的路径。它不替代原文，只给阅读顺序。",
        "",
    ]
    grouped = defaultdict(list)
    for record in records:
        grouped[record["module"]].append(record)
    for module in MODULE_ORDER:
        module_records = sorted(grouped.get(module, []), key=sort_key)
        if not module_records or module == "待归类":
            continue
        lines.extend([f"## {module}", ""])
        for record in module_records:
            lines.append(f"- [{record['title']}](../corpus/{record['wiki_slug']}.md)：{inline_list(record['key_terms'][:4])}")
        lines.append("")
    return "\n".join(lines)


def build_corpus_page(record: dict[str, Any]) -> str:
    full_text = ""
    if not is_public_mode():
        text_path = TEXT_DIR / record["text_path"]
        full_text = read_text(text_path) if text_path.exists() else ""
    source_name = record["file_name"]
    page_note = (
        f"本页由 `{source_name}` 的公开元数据与摘要信息编译生成，不包含抽取全文。"
        if is_public_mode()
        else f"本页由 `{source_name}` 的抽取文本与 `corpus_manifest.json` 元数据编译生成。自动摘录只作导航辅助，不替代原文。"
    )
    theme_heading = "## 主题摘要" if is_public_mode() else "## 主题摘录"
    lines = [
        f"# {record['title']}",
        "",
        "!!! note \"自动生成页\"",
        f"    {page_note}",
        "",
        "## 元数据",
        "",
        md_table(
            ["字段", "值"],
            [
                ["来源文件", f"`{source_name}`"],
                ["文件类型", f"`{record['file_type']}`"],
                ["资料层级", record["priority"]],
                ["教学模块", record["module"]],
                ["抽取状态", record["extraction_status"]],
                ["正文字数", str(record["char_count"])],
                ["段落数", str(record["paragraph_count"]) if record["paragraph_count"] is not None else ""],
                ["页数", str(record["page_count"]) if record["page_count"] is not None else ""],
                ["备注", record.get("notes", "")],
            ],
        ),
        "",
        "## 核心概念",
        "",
        inline_list(record["key_terms"]),
        "",
        theme_heading,
        "",
        bullet_list(record["theme_excerpt"]),
        "",
        "## 常见误区/提醒",
        "",
        bullet_list(record["warning_excerpt"]),
        "",
        "## 适合回答的问题",
        "",
        bullet_list(record["question_types"]),
        "",
    ]
    if is_public_mode():
        lines.extend(
            [
                "## 来源说明",
                "",
                f"- 本页公开显示 `{source_name}` 的摘要与索引信息。",
                "- 公开版不包含抽取全文，也不提供原始 Word/PDF 下载入口。",
                "- 如需引用原文，应回到受控访问的私有全文资料库核对。",
                "",
            ]
        )
    else:
        lines.extend(["## 全文", ""])
    if not is_public_mode():
        if full_text:
            lines.extend(
                [
                    "!!! warning \"全文来源\"",
                    "    以下是自动抽取文本，可能存在页码、换行、OCR 或排版误差。引用时请回查原始资料。",
                    "",
                    safe_code_block(full_text),
                    "",
                ]
            )
        else:
            lines.append("当前资料尚未完成稳定正文抽取。")
            lines.append("")

    lines.extend(
        [
            "## 回链",
            "",
            "- [资料总览](../sources/index.md)",
            "- [术语索引](../terms/index.md)",
            "- [学习路径](../learning/path.md)",
        ]
    )
    return "\n".join(lines)


def write_assets() -> None:
    css = """/* Generated by scripts/build_sanxi_wiki.py */
.corpus-fulltext {
  white-space: pre-wrap;
  word-break: break-word;
  line-height: 1.85;
  font-size: 0.82rem;
  max-height: none;
}

.md-typeset table:not([class]) {
  font-size: 0.75rem;
}
"""
    write_text(DOCS_DIR / "assets" / "wiki.css", css)


def write_requirements() -> None:
    write_text(WIKI_DIR / "requirements.txt", REQUIREMENTS)


def yml_quote(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def nav_lines_for_corpus(records: list[dict[str, Any]]) -> list[str]:
    grouped = defaultdict(list)
    for record in records:
        grouped[record["module"]].append(record)

    section_title = "资料摘要" if is_public_mode() else "资料全文"
    index_title = "摘要索引" if is_public_mode() else "全文索引"
    lines = [f"  - {section_title}:", f"    - {index_title}: corpus/index.md"]
    for module in MODULE_ORDER:
        module_records = sorted(grouped.get(module, []), key=sort_key)
        if not module_records:
            continue
        lines.append(f"    - {yml_quote(module)}:")
        for record in module_records:
            lines.append(f"      - {yml_quote(record['title'])}: corpus/{record['wiki_slug']}.md")
    return lines


def nav_lines_for_topics(topics: list[dict[str, str]]) -> list[str]:
    lines = ["  - 专题:", "    - 专题索引: topics/index.md"]
    for topic in topics:
        lines.append(f"    - {yml_quote(topic['title'])}: topics/{topic['slug']}.md")
        if not is_public_mode():
            support_nav = [
                ("概念结构", f"{topic['slug']}-concept-graph.md"),
                ("自问自答带学", f"{topic['slug']}-teaching-lesson.md"),
                ("练习题", f"{topic['slug']}-qa-drills.md"),
                ("来源图", f"{topic['slug']}-source-map.md"),
                ("评审报告", f"{topic['slug']}-review-report.md"),
            ]
            for title, path in support_nav:
                if (DOCS_DIR / "topics" / path).exists():
                    lines.append(f"    - {yml_quote(topic['title'] + '：' + title)}: topics/{path}")
    return lines


def write_mkdocs_config(records: list[dict[str, Any]], topics: list[dict[str, str]]) -> None:
    lines = [
        "site_name: 三晳资料 Wiki",
        f"site_description: {SITE_DESCRIPTION}",
        f"site_url: {SITE_URL}",
        f"repo_url: {REPO_URL}",
        f"repo_name: {REPO_NAME}",
        "docs_dir: docs",
        "site_dir: site",
        "use_directory_urls: true",
        "",
        "theme:",
        "  name: material",
        "  language: zh",
        "  features:",
        "    - navigation.tabs",
        "    - navigation.sections",
        "    - navigation.expand",
        "    - navigation.indexes",
        "    - navigation.top",
        "    - toc.follow",
        "    - search.suggest",
        "    - search.highlight",
        "  palette:",
        "    - scheme: default",
        "      primary: brown",
        "      accent: amber",
        "",
        "plugins:",
        "  - search:",
        "      lang:",
        "        - zh",
        "        - en",
        "  - glightbox",
        "  - minify:",
        "      minify_html: true",
        "",
        "markdown_extensions:",
        "  - admonition",
        "  - attr_list",
        "  - def_list",
        "  - footnotes",
        "  - md_in_html",
        "  - tables",
        "  - toc:",
        "      permalink: true",
        "  - pymdownx.details",
        "  - pymdownx.superfences:",
        "      custom_fences:",
        "        - name: mermaid",
        "          class: mermaid",
        "          format: !!python/name:pymdownx.superfences.fence_code_format",
        "",
        "extra_css:",
        "  - assets/wiki.css",
        "extra_javascript:",
        "  - https://unpkg.com/mermaid@10/dist/mermaid.min.js",
        "",
        "nav:",
        "  - 首页: index.md",
        "  - 学习:",
        "    - 概念总图: learning/concept-map.md",
        "    - 学习路径: learning/path.md",
        "    - 教学模板: learning/teaching-playbook.md",
        "    - 示例问答: learning/demo-qa.md",
        "  - 术语:",
        "    - 核心术语表: terms/glossary.md",
        "    - 术语索引: terms/index.md",
        "  - 资料:",
        "    - 资料总览: sources/index.md",
        "    - 待补证资料: sources/pending.md",
    ]
    if topics:
        lines.extend(nav_lines_for_topics(topics))
    lines.extend(nav_lines_for_corpus(records))
    write_text(WIKI_DIR / "mkdocs.yml", "\n".join(lines) + "\n")


def build_docs(records: list[dict[str, Any]]) -> None:
    reset_docs_dir()
    topics = discover_compiled_topics()
    copy_static_pages()
    write_topic_pages(topics)
    write_assets()
    write_text(DOCS_DIR / "index.md", build_index_page(records, topics))
    write_text(DOCS_DIR / "sources" / "index.md", build_sources_page(records))
    write_text(DOCS_DIR / "sources" / "pending.md", build_pending_page(records))
    write_text(DOCS_DIR / "learning" / "path.md", build_learning_path_page(records))
    write_text(DOCS_DIR / "corpus" / "index.md", build_corpus_index_page(records))
    for record in records:
        write_text(DOCS_DIR / "corpus" / f"{record['wiki_slug']}.md", build_corpus_page(record))
    write_mkdocs_config(records, topics)
    write_requirements()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the Sanxi MkDocs wiki.")
    parser.add_argument(
        "--mode",
        choices=["private", "public"],
        default="private",
        help="private builds the full-text wiki under wiki/; public builds the summary-only wiki under public_wiki/.",
    )
    args = parser.parse_args()
    configure_mode(args.mode)

    manifest_path = KNOWLEDGE_DIR / "corpus_manifest.json"
    if not manifest_path.exists():
        raise SystemExit(f"Missing knowledge manifest: {manifest_path}")

    records = sorted(read_json(manifest_path), key=sort_key)
    for index, record in enumerate(records, start=1):
        record["wiki_slug"] = record_slug(index, record)

    build_docs(records)
    ok_count = sum(1 for record in records if record["extraction_status"] == "ok")
    print(f"Mode: {MODE}")
    print(f"Generated wiki docs: {DOCS_DIR}")
    print(f"Records: {len(records)}")
    print(f"Extracted: {ok_count}")
    print(f"Pending: {len(records) - ok_count}")
    print(f"MkDocs config: {WIKI_DIR / 'mkdocs.yml'}")


if __name__ == "__main__":
    main()
