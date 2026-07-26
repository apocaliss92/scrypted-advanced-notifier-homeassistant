#!/usr/bin/env python3
"""Fail when a documentation page cites something that no longer exists.

The generator (``scripts/docs_generate.py``) keeps the derivable pages honest.
This keeps the *prose* honest: every repository path, constant, project class and
internal link a page names must still resolve in the source tree. Deleting a
constant, renaming a module or moving a file therefore breaks the build instead
of leaving a page that quietly lies.

    python3 scripts/docs_check_refs.py           # exit 1 on the first problem set
    python3 scripts/docs_check_refs.py -v        # also list what was checked
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from docs_source import REPO_ROOT, load_symbol_index  # noqa: E402

CONTENT_DIR = REPO_ROOT / "docs" / "content" / "docs"

# Files that count as "the source". A documented identifier must appear in one of
# them; docs pages are deliberately excluded, so docs cannot vouch for docs.
SOURCE_GLOBS = (
    "custom_components/**/*.py",
    "custom_components/**/*.json",
    "scripts/*.py",
    "scripts/*.js",
    ".github/workflows/*.yml",
    "docs/Dockerfile",
    "docs/package.json",
    "package.json",
    "hacs.json",
    "VERSION",
)

INLINE_CODE = re.compile(r"`([^`\n]+)`")
MARKDOWN_LINK = re.compile(r"\]\(([^)\s]+)\)")

PATH_LIKE = re.compile(r"^[\w][\w./@-]*\.(py|json|yml|yaml|js|mjs|tsx?|mdx?|css)$")
CONSTANT_LIKE = re.compile(r"^_?[A-Z][A-Z0-9]*(_[A-Z0-9]+)+$")
PROJECT_EVENT_LIKE = re.compile(r"^scrypted_an_[a-z0-9_]+$")
PROJECT_CLASS_LIKE = re.compile(r"^Scrypted[A-Z][A-Za-z0-9]*$")


@dataclass(frozen=True)
class Problem:
    page: str
    kind: str
    token: str
    detail: str


def source_corpus() -> str:
    """Every source file's text, concatenated. Word-presence is the membership test."""
    chunks: list[str] = []
    for pattern in SOURCE_GLOBS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            if path.is_file():
                chunks.append(path.read_text(encoding="utf-8", errors="replace"))
    return "\n".join(chunks)


def content_pages() -> list[Path]:
    return sorted(CONTENT_DIR.rglob("*.mdx"))


def known_slugs() -> set[str]:
    """Every URL the docs site will actually serve, e.g. ``/docs/reference/entities``."""
    slugs = {"/docs"}
    for page in content_pages():
        rel = page.relative_to(CONTENT_DIR).with_suffix("")
        parts = [part for part in rel.parts if part != "index"]
        slugs.add("/docs" + ("/" + "/".join(parts) if parts else ""))
    return slugs


IGNORED_DIRS = {"node_modules", ".next", ".source", ".git", "out", ".code-review-graph"}


def _strip_code_fences(text: str) -> str:
    """Drop fenced blocks — shell snippets are examples, not claims about the tree."""
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def repo_filenames() -> set[str]:
    """Bare file names present anywhere in the tracked tree."""
    names: set[str] = set()
    stack = [REPO_ROOT]
    while stack:
        current = stack.pop()
        for child in current.iterdir():
            if child.name in IGNORED_DIRS or child.name.startswith("."):
                if child.name not in {".github"}:
                    continue
            if child.is_dir():
                stack.append(child)
            else:
                names.add(child.name)
    return names


def top_level_entries() -> set[str]:
    return {child.name for child in REPO_ROOT.iterdir()}


def check_page(
    page: Path,
    corpus: str,
    classes: frozenset[str],
    slugs: set[str],
    filenames: set[str],
    top_level: set[str],
) -> list[Problem]:
    rel = str(page.relative_to(REPO_ROOT))
    text = _strip_code_fences(page.read_text(encoding="utf-8"))
    problems: list[Problem] = []

    for token in {match.group(1).strip() for match in INLINE_CODE.finditer(text)}:
        # A token with whitespace is a command line and a token with `*` is a glob;
        # neither claims that one exact path exists.
        if any(char.isspace() for char in token) or "*" in token:
            continue
        if "/" in token:
            candidate = token.split("?")[0].rstrip("/")
            # Only judge paths anchored at a real top-level entry. `reference/` on
            # its own is a fragment of prose, not a repo path.
            if candidate.split("/")[0] in top_level:
                if not (REPO_ROOT / candidate).exists():
                    problems.append(
                        Problem(rel, "path", token, "no such file or directory in the repo")
                    )
            continue
        if PATH_LIKE.match(token):
            if token not in filenames:
                problems.append(Problem(rel, "path", token, "no file with this name in the repo"))
            continue
        if CONSTANT_LIKE.match(token):
            if not re.search(rf"\b{re.escape(token)}\b", corpus):
                problems.append(
                    Problem(rel, "constant", token, "not found in any source file")
                )
            continue
        if PROJECT_EVENT_LIKE.match(token):
            if not re.search(rf"\b{re.escape(token)}", corpus):
                problems.append(
                    Problem(rel, "identifier", token, "not found in any source file")
                )
            continue
        if PROJECT_CLASS_LIKE.match(token) and token not in classes:
            problems.append(
                Problem(rel, "class", token, "not a class in custom_components/scrypted_an")
            )

    for target in {match.group(1) for match in MARKDOWN_LINK.finditer(text)}:
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        slug = target.split("#")[0].rstrip("/")
        if slug and slug not in slugs:
            problems.append(Problem(rel, "link", target, "does not resolve to a docs page"))

    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    pages = content_pages()
    if not pages:
        print("no MDX pages found — is docs/content/docs missing?", file=sys.stderr)
        return 1

    corpus = source_corpus()
    classes = load_symbol_index().classes
    slugs = known_slugs()
    filenames = repo_filenames()
    top_level = top_level_entries()

    if args.verbose:
        print(
            f"pages: {len(pages)}  slugs: {len(slugs)}  "
            f"classes: {len(classes)}  files: {len(filenames)}"
        )

    problems: list[Problem] = []
    for page in pages:
        problems.extend(check_page(page, corpus, classes, slugs, filenames, top_level))

    if problems:
        for problem in problems:
            print(f"{problem.page}: {problem.kind} `{problem.token}` — {problem.detail}")
        print(
            f"\n{len(problems)} broken reference(s). "
            "Either the docs are stale or the code lost something they rely on.",
            file=sys.stderr,
        )
        return 1

    print(f"docs:check-refs OK — {len(pages)} pages, every cited path/identifier resolves")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
