#!/usr/bin/env python3
import os
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
UNRELEASED = os.path.join(ROOT, "docs", "changes", "unreleased")
CHANGELOG = os.path.join(ROOT, "CHANGELOG.md")

TYPES = ["breaking", "feature", "fix", "perf", "security", "docs", "chore"]
SECTIONS = {
    "breaking": "Breaking",
    "feature": "Added",
    "fix": "Fixed",
    "perf": "Performance",
    "security": "Security",
    "docs": "Documentation",
    "chore": "Changed",
}


def collect():
    items = {t: [] for t in TYPES}
    for name in sorted(os.listdir(UNRELEASED)):
        if name.startswith(".") or not name.endswith(".md"):
            continue
        parts = name.split(".")
        if len(parts) < 3:
            kind = "chore"
        else:
            kind = parts[-2].lower()
            if kind not in TYPES:
                kind = "chore"
        path = os.path.join(UNRELEASED, name)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if content:
            items[kind].append(content)
    return items


def write_changelog(version: str, items: dict):
    date = datetime.utcnow().strftime("%Y-%m-%d")
    header = f"\n## [{version}] - {date}\n\n"
    sections = []
    for kind in TYPES:
        if not items[kind]:
            continue
        sections.append(f"### {SECTIONS[kind]}\n- " + "\n- ".join(items[kind]) + "\n")
    if not sections:
        print("No change fragments found.")
        return False
    with open(CHANGELOG, "r", encoding="utf-8") as f:
        orig = f.read()
    with open(CHANGELOG, "w", encoding="utf-8") as f:
        f.write(orig)
        f.write(header)
        for sec in sections:
            f.write(sec)
    return True


def clear_unreleased():
    for name in os.listdir(UNRELEASED):
        if name.startswith(".") or not name.endswith(".md"):
            continue
        os.remove(os.path.join(UNRELEASED, name))


def main():
    if len(sys.argv) < 2:
        print("Usage: aggregate_changes.py <version>")
        sys.exit(1)
    version = sys.argv[1]
    items = collect()
    ok = write_changelog(version, items)
    if ok:
        clear_unreleased()
        print(f"CHANGELOG.md updated for version {version}.")


if __name__ == "__main__":
    main()
