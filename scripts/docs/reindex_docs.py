#!/usr/bin/env python3
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
INDEX = DOCS / "index.md"

SECTIONS = [
    ("tutorials", "Tutorials"),
    ("how-to", "How-To Guides"),
    ("reference", "Reference"),
    ("explanations", "Explanations"),
    ("runbooks", "Runbooks"),
    ("changes", "Changes"),
]

SKIP_DIRS = {".git", ".github", ".venv", "node_modules", "__pycache__"}

MD_LINK_RE = re.compile(r"^# +(.+)$")


def rel(p: Path) -> str:
    return str(p.relative_to(DOCS)).replace("\\", "/")


def collect_tree():
    tree = {}
    for slug, _ in SECTIONS:
        base = DOCS / slug
        if not base.exists():
            continue
        entries = []
        for path in sorted(base.rglob("*.md")):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            # Skip index.md itself
            if path == INDEX:
                continue
            # Derive title from first heading or filename
            title = path.stem.replace("_", " ").replace("-", " ").title()
            try:
                with open(path, "r", encoding="utf-8") as f:
                    for line in f:
                        m = MD_LINK_RE.match(line.strip())
                        if m:
                            title = m.group(1).strip()
                            break
            except Exception:
                pass
            entries.append((title, rel(path)))
        tree[slug] = entries
    return tree


def render_index(tree):
    lines = [
        "# Health Portal — Documentation",
        "",
        "This index is auto-generated. Do not edit by hand.",
        "",
    ]
    for slug, label in SECTIONS:
        if slug not in tree or not tree[slug]:
            continue
        lines.append(f"## {label}")
        for title, path in tree[slug]:
            lines.append(f"- {title}: `{path}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main():
    tree = collect_tree()
    content = render_index(tree)
    with open(INDEX, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Rebuilt docs index at {INDEX}")


if __name__ == "__main__":
    sys.exit(main())
