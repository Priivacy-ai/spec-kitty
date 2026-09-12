"""Architectural test: AGENTS.md must not claim a phantom `lanes.json`-absent
`-WP##` workspace fallback.

Mission ``workflow-mechanics-self-doc-01M02SF1`` WP07 (T015/T016, FR-003,
NFR-002, NFR-005) found the "Execution Workspace Strategy" section of
``AGENTS.md`` claiming::

    - `lanes.json` absent -> legacy: `.worktrees/<feature>-WP##`

That claim is false. ``resolve_workspace_for_wp``
(``src/specify_cli/workspace/context.py``) always resolves through
``require_lanes_json`` (``src/specify_cli/lanes/persistence.py``), which
raises ``MissingLanesError`` when ``lanes.json`` is absent -- there is no
``-WP##`` fallback for flat / ``SINGLE_BRANCH`` / ``LANES`` missions. This
guard pins the corrected doc: the stale claim must never reappear, and the
real (fail-closed) contract must stay documented.

``CLAUDE.md`` in the repo root is a symlink to ``AGENTS.md``, so reading
either file exercises the same on-disk content; this test reads
``AGENTS.md`` directly, the authoritative surface named in the WP07 task
manifest.
"""

from __future__ import annotations

from pathlib import Path

import pytest

#: Without this the CI shard that selects ``-m architectural`` collects none
#: of these tests, and the gate silently never runs. This test is a plain
#: file read (no git subprocess), so it doesn't need ``git_repo``; it reads
#: ``docs``-adjacent content (repo-root ``AGENTS.md``), so it carries
#: ``docs_scoped`` like its doc-guard siblings (e.g.
#: ``test_no_legacy_terminology.py``).
pytestmark = [pytest.mark.architectural, pytest.mark.docs_scoped]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_AGENTS_MD = _REPO_ROOT / "AGENTS.md"

#: The stale, factually-false claims that must never reappear. Both spellings
#: (the literal fallback path, and the "absent -> legacy" framing) are
#: checked independently so a partial rewrite that keeps either half still
#: fails the gate.
_STALE_FALLBACK_PATH = ".worktrees/<feature>-WP##"
_STALE_LEGACY_FRAMING = "absent → legacy"


def _agents_md_text() -> str:
    assert _AGENTS_MD.is_file(), f"expected {_AGENTS_MD} to exist"
    return _AGENTS_MD.read_text(encoding="utf-8")


def test_stale_lanes_json_fallback_claim_is_absent() -> None:
    """The phantom `-WP##` fallback claim must not reappear in AGENTS.md."""
    text = _agents_md_text()
    assert _STALE_FALLBACK_PATH not in text, (
        f"AGENTS.md still claims the phantom fallback path {_STALE_FALLBACK_PATH!r}; "
        "resolve_workspace_for_wp has no such fallback (require_lanes_json "
        "raises MissingLanesError when lanes.json is absent)."
    )
    assert _STALE_LEGACY_FRAMING not in text, (
        f"AGENTS.md still uses the stale {_STALE_LEGACY_FRAMING!r} framing for "
        "the lanes.json-absent case; there is no legacy fallback to describe."
    )


def test_corrected_lanes_json_contract_is_present() -> None:
    """The real, fail-closed contract must be documented in its place."""
    text = _agents_md_text()
    assert "MissingLanesError" in text, (
        "AGENTS.md should name MissingLanesError as the fail-closed outcome "
        "when lanes.json is absent (src/specify_cli/lanes/persistence.py)."
    )
    assert "require" in text and "lanes.json" in text, (
        "AGENTS.md should state that lanes.json is required (no fallback), "
        "not merely referenced."
    )


def test_bare_wp_placeholder_token_survives() -> None:
    """`WP##` is a legitimate bare token elsewhere (e.g. `implement WP##`)
    and must NOT be banned by this guard -- only the specific stale fallback
    phrase and framing above are prohibited.
    """
    text = _agents_md_text()
    assert "spec-kitty implement WP##" in text, (
        "the legitimate `spec-kitty implement WP##` usage should remain "
        "documented; this guard must not over-match and strip it."
    )
