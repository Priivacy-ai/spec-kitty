"""WP08 — FR-006 mission-type activation gating regression tests.

**This suite is a forward-looking regression guard, NOT proof that this
mission added a new gate.** The activation gate it covers — filtering
``existing_mission_types()``'s return value (and, downstream, the ``is_registered``
membership check in ``resolve_mission_type_context()``) to the project's
activated-mission-type set — already existed, unchanged in substance, before
this mission touched ``charter.mission_type_profiles``: reverting that module
to its pre-mission state and re-running this suite still passes (DIRECTIVE_041
— confirmed: ``7 passed``). There was no missing gate to close, so this module
must not be read, cited, or summarised as evidence that this mission introduced
mission-type activation gating. What it does is make the pre-existing gate's
behaviour *durable*: the moment ``existing_mission_types()`` — the real
authority, per its own docstring — stops filtering by the activation set, this
suite reds.

Per ``data-model.md`` D4 / spec.md FR-006, ``PackContext.activated_mission_types``
is a plain ``frozenset[str]``, never ``None`` — the "no selection authored"
case is already collapsed to ``builtin_mission_type_id_set()`` at
``PackContext`` construction time.  The gate this suite pins is therefore
binary (filtered vs. not), not the three-state contract the other 9 kinds
follow:

* T034 — the gate lives entirely in ``charter.mission_type_profiles``, and its
  authoritative implementation is ``existing_mission_types()``'s filtering
  return statement (``sorted(pack_context.activated_mission_types)``), not the
  membership check in ``resolve_mission_type_context()`` that merely consumes
  it. Note the gate deliberately does **not** intersect against
  ``builtin_mission_type_id_set()`` — a project may legitimately activate a
  custom (non-built-in) mission type id backed by a project-level doctrine
  override, and ``existing_mission_types()`` must keep returning it (locked in
  by
  ``tests/charter/test_action_sequence_dispatch.py::TestExistingMissionTypes::test_returns_custom_type_when_activated``,
  which predates this WP and must not regress).
* T035 — bare-project regression: set-equality against
  ``builtin_mission_type_id_set()``, not a fakeable subset check.
* T036 — subset-activation regression: a proper subset of activated types
  narrows the result to exactly that subset.

No test in this suite touches ``charter.mission_type_profile_repository``
(WP06's exclusive ownership) or adds anything to ``charter.resolver.DoctrineService``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from charter.mission_type_profiles import (
    UnknownMissionTypeError,
    existing_mission_types,
    resolve_mission_type_context,
)
from doctrine.missions.mission_type_repository import builtin_mission_type_id_set

pytestmark = [pytest.mark.fast]


def _write_config(repo_root: Path, activations: list[str]) -> None:
    """Write a minimal ``.kittify/config.yaml`` with an explicit activation list."""
    kittify = repo_root / ".kittify"
    kittify.mkdir(parents=True, exist_ok=True)
    lines = "\n".join(f"  - {mt}" for mt in activations)
    (kittify / "config.yaml").write_text(f"mission_type_activations:\n{lines}\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# T035 — bare-project regression: set-equality (non-fakeable)
# ---------------------------------------------------------------------------


def test_bare_project_existing_mission_types_equals_builtin_catalog(tmp_path: Path) -> None:
    """No ``.kittify/config.yaml`` at all → the full built-in catalog, by set-equality.

    Set-equality (not ``<=`` / subset containment) so a silently dropped
    built-in type would fail this test even though "at least the 4 known
    ones resolve" would still pass a weaker subset check.
    """
    result = set(existing_mission_types(tmp_path))
    assert result == builtin_mission_type_id_set()


def test_bare_project_config_with_no_activation_key_equals_builtin_catalog(
    tmp_path: Path,
) -> None:
    """A ``config.yaml`` that exists but omits ``mission_type_activations``
    is the same bare-project default as no file at all."""
    kittify = tmp_path / ".kittify"
    kittify.mkdir()
    (kittify / "config.yaml").write_text("activated_kinds:\n  - directives\n", encoding="utf-8")

    result = set(existing_mission_types(tmp_path))
    assert result == builtin_mission_type_id_set()


def test_bare_project_resolve_context_registered_ids_equals_builtin_catalog(
    tmp_path: Path,
) -> None:
    """``resolve_mission_type_context`` surfaces the same full catalog through
    ``UnknownMissionTypeError.registered_ids`` when asked for an unknown type —
    proving the gate is live on the resolver's own hard-fail path, not just on
    ``existing_mission_types`` in isolation."""
    with pytest.raises(UnknownMissionTypeError) as exc_info:
        resolve_mission_type_context(tmp_path, mission_type="not-a-real-mission-type")

    assert set(exc_info.value.registered_ids) == builtin_mission_type_id_set()


# ---------------------------------------------------------------------------
# T036 — subset-activation regression: filtering actually narrows
# ---------------------------------------------------------------------------


def test_subset_activation_narrows_existing_mission_types(tmp_path: Path) -> None:
    """Activating a proper subset returns exactly that subset — not the full
    built-in set — proving the filtering actually filters."""
    catalog = sorted(builtin_mission_type_id_set())
    subset = catalog[:2]
    assert 0 < len(subset) < len(catalog), "fixture must exercise a proper subset"

    _write_config(tmp_path, subset)

    result = set(existing_mission_types(tmp_path))
    assert result == set(subset)
    assert result != builtin_mission_type_id_set()


def test_resolve_context_succeeds_for_type_inside_activated_subset(tmp_path: Path) -> None:
    """A type inside the activated subset resolves normally (no hard-fail)."""
    catalog = sorted(builtin_mission_type_id_set())
    subset = catalog[:1]
    _write_config(tmp_path, subset)

    bundle = resolve_mission_type_context(tmp_path, mission_type=subset[0])

    assert bundle.mission_type == subset[0]


def test_resolve_context_raises_for_type_outside_activated_subset(tmp_path: Path) -> None:
    """A real built-in type that is NOT in the activated subset still
    hard-fails (FR-003), and the exception's ``registered_ids`` reports
    exactly the activated subset — the ``resolve_mission_type_context()``-facing
    proof that filtering narrows the result, not just ``existing_mission_types``
    called directly."""
    catalog = sorted(builtin_mission_type_id_set())
    subset = catalog[:1]
    excluded = next(mt for mt in catalog if mt not in subset)
    _write_config(tmp_path, subset)

    with pytest.raises(UnknownMissionTypeError) as exc_info:
        resolve_mission_type_context(tmp_path, mission_type=excluded)

    assert set(exc_info.value.registered_ids) == set(subset)


# ---------------------------------------------------------------------------
# T034 — the gate does not overreach into builtin-only filtering
# ---------------------------------------------------------------------------


def test_custom_activated_type_is_not_dropped_by_the_gate(tmp_path: Path) -> None:
    """A custom (non-built-in) activated mission-type id must still resolve.

    FR-006's gate is binary against the project's *activation* set, not
    against the built-in catalog — a project is free to activate a mission
    type id that has no built-in profile, backed entirely by a project-level
    doctrine override (``_project_has_doctrine_overrides`` tolerance in
    ``_resolve_governance_slot``). Filtering by ``builtin_mission_type_id_set()``
    here would be a *stricter*, wrong gate: it would silently exclude a
    legitimately-activated custom type, contradicting the pre-existing
    contract at
    ``tests/charter/test_action_sequence_dispatch.py::TestExistingMissionTypes::test_returns_custom_type_when_activated``.
    """
    real_type = sorted(builtin_mission_type_id_set())[0]
    _write_config(tmp_path, [real_type, "compliance-audit"])

    result = set(existing_mission_types(tmp_path))

    assert result == {real_type, "compliance-audit"}
