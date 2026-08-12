"""C-011's anchor key set, resolved once at the SHA ``members.json`` was authored against.

``members.json`` records each member as ``(path, qual, sites)`` where ``sites`` are **line
numbers**. Those line numbers are only meaningful in the tree they were read from. Resolving
them against any other tree is a category error: an upstream edit that inserts lines *above*
a member site leaves the recorded line number pointing at whatever moved into its place.

That is not hypothetical. Between ``fe5d492ed`` and this mission's landing base, upstream
inserted five lines into ``tests/cli/commands/test_sync_doctor_tracker_egress_3108.py``
above the site recorded as line 124. Re-resolving against the live tree read line 124 as a
**comment**, whose normalized token line is ``''`` — so the anchor silently reported a member
key that no census could ever match, and three set equalities plus two join lookups went red
for a member that had not changed at all.

Note that ``specify_cli.contracts.anchoring.composite_key`` documents itself as
"content-addressed, not line-number-addressed" and "stable against blank-line / comment-line
insertions near the guarded site". That is true of the key's **values** and false of its
**lookup**: the token line is fetched with ``tokens.get(lineno, "")``. Content inserted above
the site moves the site, and the key changes. The claim holds only for insertions *below*.

So the resolution is frozen here, once, and checked in:

* ``members.json`` remains untouched and remains the sole authority on **which** sites are
  members — the one artefact this Mission did not write and must never edit to green a test.
* This file records only the **encoding** of those sites, computed by the repository primitive
  against the frozen SHA's blobs.

The consequence worth stating plainly: the anchor is no longer re-derived from the working
tree on every run, so it can no longer notice that a member site's code changed. It never
usefully could — such a change made it go red without saying why. What it still does, and what
C-011 actually asks of it, is assert the census's membership against an independently authored
list.

Regeneration needs the frozen SHA's blobs to be reachable, which is why it is a one-time
operation recorded in the artefact header rather than a step in any routine gate.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

import yaml

from tests.architectural._ratchet_keys import composite_key

#: The frozen artefact this module reads and writes.
ANCHOR_PATH = "tests/architectural/census/spec_kitty_home_pin_anchor.yaml"

#: Spelled once, emitted into the header, and PARSED back by the census tests — never re-typed
#: in prose, for the same reason the census's own regeneration command is not.
REGENERATION_COMMAND = (
    "python -m tests.architectural._home_pin_anchor "
    "--members kitty-specs/isolated-home-pin-guard-r1a-01KZNMA3/research/"
    "spec_kitty_home_pin_evidence/members.json "
    "--at-sha <sha> --out " + ANCHOR_PATH
)

_HEADER_NOTE = (
    "Generated, never hand-edited. `resolved_at_sha` is the SHA whose blobs `members.json`'s "
    "line numbers index; resolving them against any other tree reads a different line. "
    "`members.json` decides WHICH sites are members and is never edited; this file records only "
    "their key ENCODING. Regenerating requires `resolved_at_sha` to be reachable."
)


def source_at(sha: str, relpath: str) -> str:
    """``relpath``'s content at ``sha``, straight from the object store."""
    completed = subprocess.run(
        ["git", "show", f"{sha}:{relpath}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return completed.stdout


def resolve(members_path: Path, sha: str) -> list[dict[str, object]]:
    """Resolve every ``members.json`` site to its composite key at ``sha``."""
    entries = json.loads(members_path.read_text(encoding="utf-8"))
    rows: list[dict[str, object]] = []
    for entry in entries:
        relpath = str(entry["path"])
        source = source_at(sha, relpath)
        for lineno in entry["sites"]:
            qualname, token_line = composite_key(source, int(lineno))
            rows.append(
                {
                    "key": [Path(relpath).as_posix(), qualname, token_line],
                    "join": [relpath, str(entry["qual"])],
                    "lineno": int(lineno),
                }
            )
    rows.sort(key=lambda row: (row["key"][0], row["lineno"]))  # type: ignore[index]
    return rows


def render(rows: list[dict[str, object]], *, sha: str, members: str) -> str:
    """Render the frozen anchor document."""
    doc = {
        "header": {
            "generated_by": "tests/architectural/_home_pin_anchor.py",
            "regeneration_command": REGENERATION_COMMAND,
            "resolved_at_sha": sha,
            "source": members,
            "note": _HEADER_NOTE,
        },
        "rows": rows,
    }
    return yaml.safe_dump(doc, sort_keys=False, default_flow_style=False, allow_unicode=True)


def load(path: str | Path = ANCHOR_PATH) -> dict[tuple[str, str, str], tuple[str, str]]:
    """The frozen anchor as ``{MemberKey: (rel_path, keyed-def qualname)}``."""
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return {
        (str(row["key"][0]), str(row["key"][1]), str(row["key"][2])): (
            str(row["join"][0]),
            str(row["join"][1]),
        )
        for row in doc["rows"]
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--members", required=True, type=Path)
    parser.add_argument("--at-sha", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args(argv)

    rows = resolve(args.members, args.at_sha)
    args.out.write_text(
        render(rows, sha=args.at_sha, members=args.members.as_posix()), encoding="utf-8"
    )
    sys.stdout.write(f"ANCHOR-FROZEN rows={len(rows)} at={args.at_sha}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
