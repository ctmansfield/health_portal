#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"

MD_LINK = re.compile(r"\[(?P<text>[^\]]+)\]\((?P<link>[^)]+)\)")
ANCHOR_RE = re.compile(r"^#+ +(.+)$")


def slugify(title: str) -> str:
    return (
        re.sub(r"[^a-z0-9 -]", "", title.lower()).replace(" ", "-").replace("--", "-")
    )


def collect_anchors(md_path: Path):
    anchors = set()
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            for line in f:
                m = ANCHOR_RE.match(line.strip())
                if m:
                    anchors.add("#" + slugify(m.group(1)))
    except Exception:
        pass
    return anchors


def check():
    errors = []
    for md in DOCS.rglob("*.md"):
        anchors = collect_anchors(md)
        text = md.read_text(encoding="utf-8", errors="ignore")
        for m in MD_LINK.finditer(text):
            link = m.group("link").strip()
            # Ignore external URLs
            if "://" in link:
                continue
            # Skip inline anchors only
            if link.startswith("#"):
                if link not in anchors:
                    errors.append(f"{md}: missing local anchor {link}")
                continue
            # Split path and optional anchor
            if "#" in link:
                path_s, anchor = link.split("#", 1)
                anchor = "#" + anchor
            else:
                path_s, anchor = link, None
            target = (md.parent / path_s).resolve()
            try:
                target_rel = target.relative_to(ROOT)
            except Exception:
                target_rel = target
            if not target.exists():
                errors.append(f"{md}: broken link to {path_s}")
                continue
            if anchor and target.suffix == ".md":
                t_anchors = collect_anchors(target)
                if anchor not in t_anchors:
                    errors.append(f"{md}: missing anchor {anchor} in {path_s}")
    return errors


def main():
    errors = check()
    if errors:
        print("Broken links found:")
        for e in errors:
            print(" -", e)
        sys.exit(1)
    print("No broken links detected.")


if __name__ == "__main__":
    main()
