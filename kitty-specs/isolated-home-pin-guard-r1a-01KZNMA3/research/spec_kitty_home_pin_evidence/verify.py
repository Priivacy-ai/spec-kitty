"""C-011 re-derivation check. Exit 0 iff the checked-in members.json still reproduces.

Added in the post-plan remediation. `clf.py` and `step3.py` are preserved VERBATIM, which
means step3.py writes to the ephemeral scratchpad it was authored in and cannot verify the
artefact C-011 designates. This script is the working counterpart: it imports the sibling
`clf` and compares a fresh derivation against the checked-in `members.json`.

    python3 kitty-specs/.../research/spec_kitty_home_pin_evidence/verify.py

Pure stdlib. No venv, no `uv`. Run from the repository root.
"""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXPECTED = HERE / "members.json"


def _load_clf():  # the sibling instrument, byte-for-byte as the third lens wrote it
    spec = importlib.util.spec_from_file_location("_c011_clf", HERE / "clf.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def derive() -> list[dict[str, object]]:
    clf = _load_clf()
    sites = clf.classify(sorted((clf.ROOT / "tests").rglob("*.py")))
    eff = [s for s in sites if s["value"] == ("tmp_path", ("home",))]
    members: dict[tuple[str, str, int], list[dict[str, object]]] = {}
    for s in eff:
        if s["keyed"] is None:
            continue
        members.setdefault((s["path"], s["keyed_qual"], s["keyed_line"]), []).append(s)
    return sorted(
        (
            {
                "path": k[0],
                "qual": k[1],
                "line": k[2],
                "sites": [s["lineno"] for s in v],
                "fixture": v[0]["keyed_isfixture"],
            }
            for k, v in members.items()
        ),
        key=lambda d: (d["path"], d["line"]),
    )


def main() -> int:
    expected = json.loads(EXPECTED.read_text(encoding="utf-8"))
    actual = derive()
    if actual == expected:
        print(f"C-011 OK: {len(actual)} members reproduce members.json exactly")
        return 0
    exp_k = {(d["path"], d["qual"], d["line"]) for d in expected}
    act_k = {(d["path"], d["qual"], d["line"]) for d in actual}
    print(f"C-011 MISMATCH: expected {len(expected)} members, derived {len(actual)}")
    for k in sorted(exp_k - act_k):
        print(f"  MISSING  {k}")
    for k in sorted(act_k - exp_k):
        print(f"  NEW      {k}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
