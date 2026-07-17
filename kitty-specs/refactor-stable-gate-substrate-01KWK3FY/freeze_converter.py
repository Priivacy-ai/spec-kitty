"""Fail-closed freeze converter for the resolution-authority gate allowlist.

Mission ``refactor-stable-gate-substrate-01KWK3FY`` / WP01 (T001).

THROWAWAY / NOT SHIPPED TOOLING. Recorded in the mission dir for the provenance
record only (contract rules 2 + 6): the frozen ``token`` comparands in
``tests/architectural/resolution_gate_allowlist.yaml`` must enter the allowlist
via a fail-closed tool derivation — never typed by hand. This script is that
derivation. It is deliberately NOT under ``src/`` or ``tests/`` and is never
imported by the gate.

What it does
------------
For every current allowlist entry ``(qualname, line)`` it resolves the live
source composite key ``(enclosing_qualname, token)`` via
``tests/architectural/_ratchet_keys.composite_key_from_file`` and the live
scanner (for the ``file:`` attribution that disambiguates the ``implement`` /
``review`` qualname collisions). It ABORTS LOUDLY (``FreezeAbort``) on any of:

* the seed line resolves to ``<module>`` scope,
* the derived token is empty,
* the derived qualname disagrees with the YAML's recorded qualname,
* the file is unparseable / the ``(qualname, line)`` matches no live site.

On success it rewrites the YAML in place to the Design-P shape: each entry gains
``file:`` (repo-relative source path) and ``token:`` (the frozen comparand);
``line:`` survives as a non-authoritative locator; ``rationale:`` is unchanged.
The governance header + shrink-history comments + baseline scalars are preserved
(ruamel round-trip); a Design-P banner documenting the semantics + freshen
procedure is prepended.

Usage
-----
    python kitty-specs/<mission>/freeze_converter.py            # convert in place
    python kitty-specs/<mission>/freeze_converter.py --demo-broken  # fail-closed proof
"""

from __future__ import annotations

import sys
from pathlib import Path

# Resolve repo root from this file: <root>/kitty-specs/<mission>/freeze_converter.py
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ARCH = _REPO_ROOT / "tests" / "architectural"
sys.path.insert(0, str(_REPO_ROOT / "tests"))

from architectural._ratchet_keys import (  # noqa: E402
    composite_key_from_file,
)
from architectural.test_resolution_authority_gates import (  # noqa: E402
    scan_canonicalizer_call_sites,
    scan_coord_authority_call_sites,
    SRC_ROOT,
)

ALLOWLIST_PATH = _ARCH / "resolution_gate_allowlist.yaml"

_DESIGN_P_BANNER = (
    "Resolution-authority gate allowlist — DESIGN-P (frozen tool-derived comparand).\n"
    "\n"
    "Each entry's authoritative comparand is the composite key\n"
    "``(file, qualname, token)``. ``token`` is a FROZEN, tool-derived\n"
    "``code_tokens_by_line`` string (via the WP01 freeze_converter — never typed by\n"
    "hand). ``line:`` is a NON-AUTHORITATIVE locator (jump-to / diagnostics only); no\n"
    "comparison, set-membership, or count logic reads it.\n"
    "\n"
    "FRESHEN PROCEDURE (legitimate site edit moved the token): re-run the gate\n"
    "``pytest tests/architectural/test_resolution_authority_gates.py``; a stale entry\n"
    "fails with the evict-or-re-approve message that PRINTS the nearest live token for\n"
    "the qualname — copy that token into ``token:`` (and refresh ``line:``). Do NOT\n"
    "hand-author tokens; re-run freeze_converter.py if bulk re-derivation is needed.\n"
    "\n"
    "COLLISION (speculative surface, zero real users today): if two live sites in one\n"
    "function share an identical token and the gate must require an exact occurrence\n"
    "count, add ``count: N`` to the entry (default 1 covers any number of matches).\n"
)


class FreezeAbort(RuntimeError):
    """Raised when a seed cannot be safely frozen (fail-closed)."""


def _sites_by_key(scan_fn: object) -> dict[tuple[str, int], str]:
    """Return ``{(qualname, lineno): rel_path}`` for a scanner's live sites."""
    out: dict[tuple[str, int], str] = {}
    for site in scan_fn(SRC_ROOT):  # type: ignore[operator]
        out[(site.key.enclosing_qualname, site.key.token_line)] = site.rel_path
    return out


def _freeze_entry(
    gate: str, entry: dict[str, object], rel_by_key: dict[tuple[str, int], str]
) -> tuple[str, str]:
    """Return ``(file, token)`` for one entry, or raise :class:`FreezeAbort`."""
    qualname = entry.get("qualname")
    line = entry.get("line")
    if not isinstance(qualname, str) or not isinstance(line, int):
        raise FreezeAbort(f"{gate}: entry {entry!r} missing str qualname / int line")
    rel_path = rel_by_key.get((qualname, line))
    if rel_path is None:
        raise FreezeAbort(
            f"{gate}: seed ({qualname!r}, {line}) matches NO live call site "
            "(unparseable file, drifted line, or renamed function) — cannot freeze"
        )
    abs_path = _REPO_ROOT / rel_path
    try:
        derived_qualname, token = composite_key_from_file(abs_path, line)
    except (OSError, SyntaxError) as exc:  # unparseable / unreadable file
        raise FreezeAbort(f"{gate}: {rel_path}:{line} unreadable/unparseable: {exc}") from exc
    if derived_qualname == "<module>":
        raise FreezeAbort(
            f"{gate}: {rel_path}:{line} resolves to <module> scope — refusing to freeze "
            "a module-scope seed (fail-closed)"
        )
    if derived_qualname != qualname:
        raise FreezeAbort(
            f"{gate}: {rel_path}:{line} derived qualname {derived_qualname!r} != "
            f"recorded {qualname!r} — seed drifted, refusing to freeze"
        )
    if not token.strip():
        raise FreezeAbort(
            f"{gate}: {rel_path}:{line} derived an EMPTY token — refusing to freeze"
        )
    return rel_path, token


def convert() -> None:
    from ruamel.yaml import YAML

    yaml_rt = YAML()
    yaml_rt.preserve_quotes = True
    yaml_rt.width = 4096  # do not wrap long token/rationale strings
    data = yaml_rt.load(ALLOWLIST_PATH.read_text(encoding="utf-8"))

    scanners = {
        "canonicalizer": scan_canonicalizer_call_sites,
        "coord_authority": scan_coord_authority_call_sites,
    }
    frozen_report: list[str] = []
    for gate, scan_fn in scanners.items():
        rel_by_key = _sites_by_key(scan_fn)
        for entry in data.get(gate, []):
            rel_path, token = _freeze_entry(gate, entry, rel_by_key)
            entry["file"] = rel_path
            entry["token"] = token
            frozen_report.append(f"  {gate}: {rel_path} :: {entry['qualname']} :: {token!r}")

    data.yaml_set_start_comment(_DESIGN_P_BANNER)
    with ALLOWLIST_PATH.open("w", encoding="utf-8") as fh:
        yaml_rt.dump(data, fh)

    print("FROZEN (tool-derived comparands):")
    print("\n".join(frozen_report))
    print(f"\nRewrote {ALLOWLIST_PATH.relative_to(_REPO_ROOT)} in Design-P shape.")


def demo_broken() -> None:
    """Prove fail-closed: feed a deliberately broken seed and show the abort."""
    rel_by_key = _sites_by_key(scan_canonicalizer_call_sites)
    # 1. Module-scope seed: point at a real file's line 1 (imports / <module>).
    broken_module = {"qualname": "<module>", "line": 1}
    # Synthesize a matching live key so it reaches the composite derivation.
    a_rel = next(iter(rel_by_key.values()))
    rel_by_key_module = dict(rel_by_key)
    rel_by_key_module[("<module>", 1)] = a_rel
    for label, entry, table in (
        ("module-scope seed", broken_module, rel_by_key_module),
        ("no-live-match seed", {"qualname": "does_not_exist", "line": 999999}, rel_by_key),
    ):
        try:
            _freeze_entry("canonicalizer", entry, table)
        except FreezeAbort as exc:
            print(f"[fail-closed OK] {label}: {exc}")
        else:  # pragma: no cover - demo only
            print(f"[UNEXPECTED] {label}: did NOT abort")


if __name__ == "__main__":
    if "--demo-broken" in sys.argv:
        demo_broken()
    else:
        convert()
