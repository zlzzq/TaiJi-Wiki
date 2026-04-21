from __future__ import annotations

import argparse
import re
from pathlib import Path

from llm_wiki_schema import iter_markdown_files, public_transform, validate_page


ROOT = Path(__file__).resolve().parent.parent


def find_links(content: str) -> list[str]:
    return re.findall(r"\[[^\]]+\]\(([^)]+\.md)\)", content)


def lint_links(path: Path, root: Path) -> list[str]:
    problems: list[str] = []
    content = path.read_text(encoding="utf-8", errors="ignore")
    for link in find_links(content):
        if "://" in link or link.startswith("#"):
            continue
        target = (path.parent / link).resolve()
        if not target.exists():
            problems.append(f"broken link: {link}")
    return problems


def lint_quote_lengths(path: Path, *, public: bool) -> list[str]:
    if not public:
        return []
    content = path.read_text(encoding="utf-8", errors="ignore")
    problems = []
    for quote in re.findall(r"“([^”]+)”", content):
        if len(quote) > 45:
            problems.append(f"public quote too long: {quote[:30]}...")
    return problems


def lint_tree(root: Path, *, public: bool = False) -> int:
    if not root.exists():
        print(f"Missing target: {root}")
        return 1
    failures = 0
    files = [path for path in iter_markdown_files(root) if "_templates" not in path.parts]
    for path in files:
        content = path.read_text(encoding="utf-8", errors="ignore")
        if public:
            content = public_transform(content)
        problems = validate_page(path, public=public)
        problems.extend(lint_links(path, root))
        problems.extend(lint_quote_lengths(path, public=public))
        if problems:
            failures += 1
            rel = path.relative_to(root)
            print(f"{rel}:")
            for problem in problems:
                print(f"  - {problem}")
    print(f"Checked {len(files)} markdown files under {root}")
    if failures:
        print(f"Failures: {failures}")
        return 1
    print("LLM Wiki lint passed")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Lint Sanxi LLM Wiki markdown pages.")
    parser.add_argument("--target", required=True)
    parser.add_argument("--public", action="store_true")
    args = parser.parse_args()
    raise SystemExit(lint_tree((ROOT / args.target).resolve() if not Path(args.target).is_absolute() else Path(args.target), public=args.public))


if __name__ == "__main__":
    main()
