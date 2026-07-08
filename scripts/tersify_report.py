#!/usr/bin/env python3
"""Report tersifier savings over the bundled LLM-facing corpus, and scaffold
hand-tersified cache files.

Usage:
    PYTHONPATH=src python scripts/tersify_report.py            # savings report
    PYTHONPATH=src python scripts/tersify_report.py --scaffold <source.md>

The report shows per-file character savings from the dictionary pass (and
token savings when ``tiktoken`` is importable — token counts, not characters,
are the number that matters). ``--scaffold`` writes a hand-cache stub at
``<dir>/terse/<name>.terse.md`` containing the current source hash header and
the unmodified body, ready for a human or LLM to rewrite tersely. Editing the
source file later invalidates the hash, and the runtime falls back to the
dictionary pass — stale hand copies are never served.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

from specify_cli.tersify import Tersifier, hand_cache_path

REPO_ROOT = Path(__file__).resolve().parent.parent

CORPUS_GLOBS = [
    ("mission-step prompts", "src/doctrine/missions/mission-steps/**/prompt.md"),
    ("doctrine skills", "src/doctrine/skills/*/SKILL.md"),
    ("doctrine templates", "src/doctrine/templates/*.md"),
]


def _token_counter():
    try:
        import tiktoken  # noqa: PLC0415

        enc = tiktoken.get_encoding("o200k_base")
        return lambda s: len(enc.encode(s))
    except ImportError:
        return None


def report() -> None:
    tersifier = Tersifier()
    count_tokens = _token_counter()
    unit = "tokens" if count_tokens else "chars (install tiktoken for tokens)"
    print(f"Savings unit: {unit}\n")

    for label, pattern in CORPUS_GLOBS:
        files = sorted(REPO_ROOT.glob(pattern))
        if not files:
            continue
        print(f"== {label} ({len(files)} files) ==")
        total_before = total_after = 0
        for path in files:
            text = path.read_text(encoding="utf-8")
            result = tersifier.tersify(text, source_path=path)
            measure = count_tokens or len
            before, after = measure(text), measure(result.text)
            total_before += before
            total_after += after
            saved = (before - after) / before if before else 0.0
            print(f"  {path.relative_to(REPO_ROOT).as_posix():74s} {before:6d} -> {after:6d}  {saved:6.1%}  [{result.source}]")
        if total_before:
            pct = (total_before - total_after) / total_before
            print(f"  {'TOTAL':74s} {total_before:6d} -> {total_after:6d}  {pct:6.1%}\n")


def scaffold(source: Path) -> None:
    if not source.is_file():
        sys.exit(f"error: {source} is not a file")
    text = source.read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    target = hand_cache_path(source)
    if target.exists():
        sys.exit(f"error: {target} already exists; delete it first to re-scaffold")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f"<!-- tersifier:source-sha256={digest} -->\n{text}", encoding="utf-8")
    print(f"scaffolded {target}\nNow rewrite its body tersely — keep every heading, code fence, placeholder, table, and HTML comment byte-identical.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scaffold", type=Path, help="source .md to scaffold a hand cache for")
    args = parser.parse_args()
    if args.scaffold:
        scaffold(args.scaffold.resolve())
    else:
        report()


if __name__ == "__main__":
    main()
