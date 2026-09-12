"""Red-first governance-agreement test (WP03, #3064).

Contract: ``kitty-specs/charter-delivery-finish-context-degod-01KYT4BY/
contracts/empty-charter-fallback.md`` ("Governance-context agreement" section)
and ``research.md`` Decision 4.

Verified leak (pre-WP03): ``_render_compact_governance`` ->
``render_compact_view`` (``charter/compact.py:216-230``) merges
``resolver_directives`` from ``resolve_project_governance`` into the
``Directive IDs:`` block, independent of the profile. Under a wholly-empty
charter, ``_resolve_directives_selection`` (``charter/resolver.py:233-260``)
catalog-falls-back to the FULL built-in ``DIR-###``/``DIRECTIVE_###`` canon,
so an unadjusted generic-agent dispatch leaks every built-in directive.

This test reproduces the real dispatch seam end-to-end at the charter layer:
it calls ``resolve_generic_fallback`` (WP02, the composite empty-charter
predicate) first, exactly as ``executor.py`` does at its auto-route branch,
then feeds the resolved ``profile_id``/``action``/``suppress_project_resolver``
(``decision is not None`` -- the same boolean ``executor.py`` names
``empty_charter_fallback``) into ``build_charter_context`` exactly as
``executor.py:288`` does post-T013. This is RED before T013 (the leak) and
GREEN after it lands the bounded suppression.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from charter.activation.context import build_charter_context
from specify_cli.invocation.empty_charter import resolve_generic_fallback

#: This module git-inits a real repo via subprocess (`_init_wholly_empty_repo`)
#: and reproduces the dispatch seam end-to-end, so it is `integration` (not
#: `unit`) and must carry `git_repo` per the subprocess-git convention; `fast`
#: is disqualified because subprocess/git work is not sub-second pure logic
#: (docs/context/testing-taxonomy.md -> 'Fast', 'Git Repo').
pytestmark = [pytest.mark.integration, pytest.mark.git_repo]

# generic-agent's OWN directive-references citation (built-in/generic-agent.agent.yaml).
# The contract permits the Directive IDs block to be empty OR to carry
# exactly this citation -- never the full project catalog-fallback canon.
_GENERIC_AGENT_OWN_DIRECTIVES = frozenset({"DIRECTIVE_028"})


def _init_wholly_empty_repo(tmp_path: Path) -> None:
    """Git-init a repo with NO charter, no interview transcript, no activations.

    This is the maximally-empty charter state (mirrors the "no config at
    all" fixture in ``tests/specify_cli/invocation/test_empty_charter_fallback.py``)
    -- every charter-activatable dimension of the WP02 composite predicate
    is unconfigured. ``PackContext.from_config`` (WP04, C-A1) fail-closes when
    ``mission_type_activations`` is absent from ``.kittify/config.yaml``, so a
    minimal config carrying ONLY that key is provisioned here; this test's own
    subject (directive-leak suppression) is unrelated to mission-type
    activation, and no other activation key is written.
    """
    subprocess.run(
        ["git", "init", "--quiet", str(tmp_path)],
        check=False,
        capture_output=True,
    )
    config_dir = tmp_path / ".kittify"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "config.yaml").write_text(
        "mission_type_activations:\n  - software-dev\n",
        encoding="utf-8",
    )


def _directive_id_lines(text: str) -> list[str]:
    """Extract the bullet entries under the compact ``Directive IDs:`` heading."""
    lines = text.splitlines()
    try:
        start = lines.index("Directive IDs:")
    except ValueError:
        return []
    entries: list[str] = []
    for line in lines[start + 1 :]:
        stripped = line.strip()
        if not stripped.startswith("- "):
            break
        value = stripped[2:]
        if value != "(none)":
            entries.append(value)
    return entries


def test_empty_charter_dispatch_governance_block_has_no_directive_leak(
    tmp_path: Path,
) -> None:
    """Dispatching a request under a wholly-empty charter must not surface
    the full built-in directive canon in the compact governance block.
    """
    _init_wholly_empty_repo(tmp_path)

    decision = resolve_generic_fallback(tmp_path, "please help me tidy this up")
    assert decision is not None
    assert decision.profile_id == "generic-agent"

    result = build_charter_context(
        tmp_path,
        profile=decision.profile_id,
        action=decision.action,
        mark_loaded=False,
        suppress_project_resolver=decision is not None,
    )

    directive_lines = _directive_id_lines(result.text)

    # Contract: empty, or exactly generic-agent's own cited directives --
    # NEVER the project catalog-fallback (currently ~29 built-in ids).
    assert set(directive_lines) <= _GENERIC_AGENT_OWN_DIRECTIVES, (
        "empty-charter generic-agent dispatch must not leak the project "
        f"catalog-fallback directive canon; got {len(directive_lines)} ids: "
        f"{directive_lines}"
    )

    # No specialist marker: no OTHER agent profile's citation surfaces here.
    assert "architect-alphonso" not in result.text
    assert "Profile-Cited Directives (architect" not in result.text


def test_empty_charter_dispatch_reproduces_full_catalog_leak_when_unadjusted(
    tmp_path: Path,
) -> None:
    """Prove the bounded suppression has something to suppress.

    With the suppression DISABLED (``suppress_project_resolver=False``), the
    same wholly-empty-charter dispatch DOES leak the full built-in
    catalog-fallback directive canon into the compact governance block. Pinning
    that pre-fix leak shape here is what stops the "no leak" assertion in
    :func:`test_empty_charter_dispatch_governance_block_has_no_directive_leak`
    from degrading to a *vacuous* pass in lockstep -- if the render ever stopped
    emitting directive ids at all, that test would go green for the wrong
    reason while this negative-shape guard reds.

    This is a *negative-shape* guard, not a literal re-pin of directive IDs:
    it only asserts "far larger than the one profile-cited id", which is
    stable across catalog additions/removals.
    """
    _init_wholly_empty_repo(tmp_path)

    decision = resolve_generic_fallback(tmp_path, "please help me tidy this up")
    assert decision is not None

    # UNADJUSTED: bypass the bounded suppression to reproduce the raw leak the
    # dispatch seam (T013) exists to close. `executor.py` always passes the
    # `empty_charter_fallback` boolean here; feeding False is the counterfactual.
    leaked = build_charter_context(
        tmp_path,
        profile=decision.profile_id,
        action=decision.action,
        mark_loaded=False,
        suppress_project_resolver=False,
    )

    directive_lines = _directive_id_lines(leaked.text)
    assert len(directive_lines) > len(_GENERIC_AGENT_OWN_DIRECTIVES), (
        "expected the UNADJUSTED empty-charter dispatch to leak the full "
        "built-in catalog-fallback directive canon (the leak T013 suppresses); "
        f"got only {len(directive_lines)} ids: {directive_lines}"
    )
