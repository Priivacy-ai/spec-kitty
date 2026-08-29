"""T011: one identity-resolution chain, four writer sites (#3030 WP04).

Three consumers must agree on how a project identity is read out of an event:
FR-004's pre-POST refusal (in ``delivery/``), FR-009's backfill, and FR-013's
consent writer (in ``sync/``). NFR-001 is a subset invariant over what actually
ships, so a disagreement between the backfill and the predicate is a leak, not a
cosmetic inconsistency — the plan calls it "the single likeliest divergence in
this mission".

There is a fixture per writer site, because the pre-#3030 chain silently missed
the fourth (``payload.subject.project_uuid``, written by ``_enrich_proof_subject``
at ``emitter.py:1689``).
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from specify_cli.sync.project_identity import (
    NIL_PROJECT_UUID,
    PROJECT_UUID_RESOLUTION_CHAIN,
    resolve_event_project_slug,
    resolve_event_project_uuid,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

UUID_A = "11111111-1111-1111-1111-111111111111"
UUID_B = "22222222-2222-2222-2222-222222222222"


# --- one fixture per writer site ------------------------------------------


def test_site_1_namespace_block() -> None:
    event = {"namespace": {"project_uuid": UUID_A}, "payload": {}}
    assert resolve_event_project_uuid(event) == UUID_A


def test_site_2_envelope_top_level() -> None:
    event = {"project_uuid": UUID_A, "payload": {}}
    assert resolve_event_project_uuid(event) == UUID_A


def test_site_3_payload_top_level() -> None:
    event = {"payload": {"project_uuid": UUID_A}}
    assert resolve_event_project_uuid(event) == UUID_A


def test_site_4_payload_subject() -> None:
    """The site the pre-#3030 chain never inspected."""
    event = {"payload": {"subject": {"project_uuid": UUID_A}}}
    assert resolve_event_project_uuid(event) == UUID_A


def test_namespace_outranks_a_clobbered_top_level() -> None:
    """``envelope_fields`` can overwrite the top-level value (emitter.py:2048)."""
    event = {
        "namespace": {"project_uuid": UUID_A},
        "project_uuid": UUID_B,
        "payload": {},
    }
    assert resolve_event_project_uuid(event) == UUID_A


def test_envelope_outranks_payload_for_the_same_path() -> None:
    event = {"project_uuid": UUID_A, "payload": {"project_uuid": UUID_B}}
    assert resolve_event_project_uuid(event) == UUID_A


# --- absence is absence, never a value ------------------------------------


@pytest.mark.parametrize(
    "event",
    [
        {},
        {"payload": {}},
        {"project_uuid": None, "payload": {}},
        {"project_uuid": "", "payload": {}},
        {"project_uuid": "   ", "payload": {}},
        {"namespace": {}, "payload": {"subject": {}}},
        None,
    ],
)
def test_unresolvable_identity_is_none(event) -> None:
    assert resolve_event_project_uuid(event) is None


def test_nil_sentinel_normalizes_to_none() -> None:
    """The nil uuid must never become a groupable, consentable key.

    ``emitter.py:2150`` substitutes it for a missing uuid. Left as a value it
    would pool every identity-less event from every project under one key that
    a consent record could then match.
    """
    event = {"project_uuid": NIL_PROJECT_UUID, "payload": {}}
    assert resolve_event_project_uuid(event) is None


def test_nil_sentinel_does_not_mask_a_real_later_site() -> None:
    event = {
        "project_uuid": NIL_PROJECT_UUID,
        "payload": {"subject": {"project_uuid": UUID_A}},
    }
    assert resolve_event_project_uuid(event) == UUID_A


def test_explicit_payload_argument_is_honoured() -> None:
    """Backfill callers hold the decoded payload separately from the envelope."""
    assert resolve_event_project_uuid({}, {"project_uuid": UUID_A}) == UUID_A


def test_slug_resolves_over_the_same_shape() -> None:
    assert resolve_event_project_slug({"payload": {"project_slug": "acme"}}) == "acme"
    assert resolve_event_project_slug({"namespace": {"project_slug": "acme"}}) == "acme"
    assert resolve_event_project_slug({"payload": {}}) is None


def test_malformed_nesting_does_not_raise() -> None:
    """Real journals hold hand-edited and legacy payloads."""
    for event in (
        {"namespace": "not-a-dict", "payload": {}},
        {"payload": {"subject": ["not", "a", "dict"]}},
        {"payload": "not-a-dict"},
        {"namespace": {"project_uuid": {"nested": "dict"}}},
    ):
        resolve_event_project_uuid(event)  # must not raise


# --- NFR-001: a single definition site ------------------------------------


def _src_root() -> Path:
    root = Path(__file__).resolve().parents[2] / "src"
    assert root.is_dir()
    return root


def test_the_resolution_chain_has_exactly_one_definition_site() -> None:
    """No module may re-declare the chain (NFR-001).

    A second copy is how the backfill and the predicate come to disagree, which
    NFR-001 exists to prevent. Scans for any *other* module assigning a
    chain-shaped constant.
    """
    canonical = Path("specify_cli/sync/project_identity.py")
    offenders: dict[str, list[str]] = {}

    for path in sorted(_src_root().rglob("*.py")):
        rel = path.relative_to(_src_root())
        if rel == canonical:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover - defensive
            continue
        hits = [
            target.id
            for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for target in (
                node.targets if isinstance(node, ast.Assign) else [node.target]
            )
            if isinstance(target, ast.Name)
            and "RESOLUTION_CHAIN" in target.id
        ]
        if hits:
            offenders[str(rel)] = hits

    assert not offenders, (
        "The identity-resolution chain must have exactly one definition site "
        "(specify_cli/sync/project_identity.py). A second copy is how the "
        f"backfill and the selection predicate silently diverge. Found: {offenders}"
    )


def test_the_legacy_queue_helper_delegates_rather_than_reimplementing() -> None:
    """``queue.py`` must never resolve event identity with a private chain.

    Re-pointed by #3030 C-004/WP08. The original form required ``queue.py`` to
    *import* ``resolve_event_project_uuid``, because its ``remove_project_events``
    walked a hand-rolled three-site chain that missed
    ``payload.subject.project_uuid`` — the divergence NFR-001 exists to prevent.
    C-004 deleted that method (its store has had no drain since WP02, and its one
    caller now purges the journal through ``delivery/retention.py``), so
    ``queue.py`` resolves no event's project identity at all and the import
    requirement became vacuously satisfiable — it would pass on a module that had
    reintroduced a private chain *and* left an unused import behind.

    The invariant that actually matters is stated directly: if this module ever
    resolves an event's project identity again, it delegates. Either arm is a real
    contract — the second arm fails the moment a project-events purge returns here
    without delegating.
    """
    source = (_src_root() / "specify_cli/sync/queue.py").read_text(encoding="utf-8")
    delegates = "resolve_event_project_uuid" in source
    has_project_event_purge = "def remove_project_events" in source
    assert delegates or not has_project_event_purge, (
        "sync/queue.py resolves an event's project identity without the shared "
        "resolver; its private three-site chain was the original divergence risk."
    )


def test_chain_covers_all_four_known_sites() -> None:
    """Guards against someone trimming the chain back to the pre-#3030 three."""
    assert PROJECT_UUID_RESOLUTION_CHAIN == (
        "namespace.project_uuid",
        "project_uuid",
        "subject.project_uuid",
    )
