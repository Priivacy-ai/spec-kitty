"""FR-007 — the ``spec-kitty sync`` surface deletes no ``SPEC_KITTY_*`` reference.

The Wave-4 sync de-god (mission ``sync-cli-degod-wave4-01M0B0MX``) relocated
decision logic off the ``cli/commands/sync.py`` god-module into the
``specify_cli.sync.sync_*`` seam modules. A relocation moves a reference from
the husk into a seam module, but the **set** of ``SPEC_KITTY_*`` names on the
surface must be invariant: nothing may silently vanish.

This is the **executable** anti-deletion proof (post-plan finding Pr-5: prose in
``docs/plans/code-quality/sync-env-census.md`` is not enough). It recomputes the
reference set from the live tree and pins it to a frozen expected set. A removed
reference shrinks the live set and turns this test red; a newly-introduced one
grows it and also reds — so the census document stays honest in both directions.

Retirement is out of scope for the Wave-4 mission itself (WS6 / INV-6):
retire-candidates were **documented, not deleted**, by that mission, so they
stayed in the frozen set until a deliberate WS6 follow-on retired them. The
legacy ``SPEC_KITTY_DIR`` module shim was the sole retire-candidate; it was
retired here (#3569) by removing it from ``_EXPECTED_ENV_REFS`` below — a
deliberate, recorded removal, not a silent one. The census with per-name
verdicts lives at ``docs/plans/code-quality/sync-env-census.md``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.architectural, pytest.mark.fast]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"

#: The husk plus the whole ``specify_cli.sync`` package form the sync surface.
_HUSK = _SRC / "specify_cli" / "cli" / "commands" / "sync.py"
_SYNC_PKG = _SRC / "specify_cli" / "sync"

#: #2801 / FR-009 (mission sync-deactivate-by-default) cleanly CUT the pre-review
#: regression gate off the shared sync toggles and onto its OWN dedicated env,
#: ``SPEC_KITTY_PRE_REVIEW_GATE_DISABLE``. That gate lives in the move-task
#: command — deliberately NOT on the sync husk/package surface (a machine that
#: disabled sync must still enforce the review gate). The env census must stay
#: aware of the new gate flag so a silent deletion of the decoupled gate still
#: reds here, so we fold that one file into the scanned surface but admit ONLY
#: its dedicated ``SPEC_KITTY_PRE_REVIEW_*`` family — never its incidental
#: docstring mentions of the (now no-op) sync-disable toggles.
_PRE_REVIEW_GATE_FILE = _SRC / "specify_cli" / "cli" / "commands" / "agent" / "tasks_move_task.py"
_PRE_REVIEW_GATE_FAMILY = re.compile(r"SPEC_KITTY_PRE_REVIEW_[A-Z0-9_]+")

#: Match a ``SPEC_KITTY_*`` token. Trailing-underscore tokens (wildcard family
#: references such as ``SPEC_KITTY_SYNC_*`` written in a comment) are discarded
#: below — a real environment or module name never ends in an underscore.
_TOKEN = re.compile(r"SPEC_KITTY_[A-Z0-9_]+")

#: Frozen contract (FR-007). Mirrors the census table in
#: ``docs/plans/code-quality/sync-env-census.md``. Editing this set is a
#: deliberate act: adding a name means a new reference landed on the surface;
#: removing one means a reference was deliberately retired (and the census doc
#: updated in the same change) — see #3569, which retired ``SPEC_KITTY_DIR``.
_EXPECTED_ENV_REFS: frozenset[str] = frozenset(
    {
        "SPEC_KITTY_CLI_VERSION",
        "SPEC_KITTY_ENABLE_SAAS_SYNC",
        "SPEC_KITTY_HOME",
        "SPEC_KITTY_NO_AUTO_CUTOVER",
        # Added #2801 / FR-009 (sync-deactivate-by-default): the pre-review
        # regression gate's OWN disable env, cut off the shared sync toggles.
        # Referenced from the decoupled ``tasks_move_task.py`` gate (folded into
        # the scanned surface below), not from the sync husk/package. Recorded
        # with a ``live`` verdict in the census doc.
        "SPEC_KITTY_PRE_REVIEW_GATE_DISABLE",
        "SPEC_KITTY_SAAS_URL",
        "SPEC_KITTY_SYNC_MINIMAL_IMPORT",
        "SPEC_KITTY_SYNC_READONLY_IDENTITY",
        # Added #3626 (2026-08-21): the strict-admission opt-in read by
        # ``sync/admission_negotiation.py`` to flip the negotiated gate from
        # its non-strict default to strict enforcement. A new live reference on
        # the surface, recorded with a ``live`` verdict in the census doc.
        "SPEC_KITTY_SYNC_STRICT_ADMISSION",
    }
)


def _sync_surface_files() -> list[Path]:
    """Return every ``*.py`` on the sync surface (husk + package, recursive)."""
    files = [_HUSK, *sorted(_SYNC_PKG.rglob("*.py"))]
    return [p for p in files if "__pycache__" not in p.parts]


def _scan_env_refs() -> set[str]:
    """Compute the live set of ``SPEC_KITTY_*`` references on the sync surface.

    The husk + package supply every token; the decoupled pre-review gate file
    (#2801 / FR-009) additionally contributes ONLY its ``SPEC_KITTY_PRE_REVIEW_*``
    family, so the census tracks the new gate flag without freezing that file's
    incidental docstring mentions of the (now no-op) sync-disable toggles.
    """
    found: set[str] = set()
    for path in _sync_surface_files():
        text = path.read_text(encoding="utf-8")
        for token in _TOKEN.findall(text):
            if token.endswith("_"):
                continue  # wildcard-family artefact (e.g. ``SPEC_KITTY_SYNC_*``)
            found.add(token)
    gate_text = _PRE_REVIEW_GATE_FILE.read_text(encoding="utf-8")
    for token in _PRE_REVIEW_GATE_FAMILY.findall(gate_text):
        if not token.endswith("_"):
            found.add(token)
    return found


def test_sync_surface_files_are_discovered() -> None:
    """Non-vacuity: the scan actually reaches the husk and the package."""
    files = _sync_surface_files()
    assert _HUSK in files, "sync husk not on the scanned surface"
    assert any(p.name == "daemon.py" for p in files), "sync package not scanned"
    # A representative reference must be present, or the scanner regex is broken.
    live = _scan_env_refs()
    assert "SPEC_KITTY_HOME" in live
    # The decoupled pre-review gate family is folded in (#2801 / FR-009); its
    # presence proves the supplemental scan actually reached that file.
    assert "SPEC_KITTY_PRE_REVIEW_GATE_DISABLE" in live


def test_no_spec_kitty_env_reference_was_deleted() -> None:
    """FR-007: no ``SPEC_KITTY_*`` reference disappeared from the sync surface
    without a matching, deliberate ``_EXPECTED_ENV_REFS`` update.
    """
    live = _scan_env_refs()
    missing = _EXPECTED_ENV_REFS - live
    assert not missing, (
        "SPEC_KITTY_* reference(s) deleted from the sync surface without an "
        f"intentional retirement recorded here: {sorted(missing)}. A deliberate "
        "retirement (like #3569's removal of SPEC_KITTY_DIR) must remove the "
        "name from _EXPECTED_ENV_REFS above and update the census doc in the "
        "same change; an accidental deletion should be reverted instead."
    )


def test_env_reference_set_is_frozen_exactly() -> None:
    """The census stays honest: no undocumented reference sneaks onto the surface."""
    live = _scan_env_refs()
    added = live - _EXPECTED_ENV_REFS
    assert not added, (
        "New SPEC_KITTY_* reference(s) on the sync surface not recorded in the "
        f"census: {sorted(added)}. Add them to _EXPECTED_ENV_REFS here and to "
        "docs/plans/code-quality/sync-env-census.md with a live/retire verdict."
    )
    assert live == _EXPECTED_ENV_REFS
