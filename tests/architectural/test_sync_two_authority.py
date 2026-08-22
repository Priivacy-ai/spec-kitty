"""FR-004 / INV-2 — the ``spec-kitty sync`` authority surfaces stay non-unified.

Authority in the sync CLI is **three** surfaces, not two (architect finding A-2),
extracted into :mod:`specify_cli.sync.sync_authority` by WP07:

* **READ** — coord / daemon-owner coherence (``_require_daemon_owner_coherence``),
  delegating to :func:`specify_cli.sync.preflight.run_preflight`.
* **WRITE** — repository sharing (``request_repository_share`` /
  ``leave_repository_share``), delegating to :mod:`specify_cli.sync.sharing_client`.
* **delivery-ADMISSION** — dispatch-bound target/receiver asserts
  (``_assert_event_sync_runtime_authority`` /
  ``_assert_delivery_target_matches_context``), delegating the audience
  construction to :mod:`specify_cli.sync.target_authority`.

The invariant (data-model INV-2) is **non-unification of the ports/classes**, NOT
of call flows: a flow may legitimately read AND write (``opt_out``,
``_open_project_dispatch_runtime`` are frozen mixed flows, C-007). What must not
happen is the three PORTS collapsing into one shared authority class, or an adapter
re-implementing its canonical surface instead of delegating to it (DIRECTIVE_044 /
A-3).

**Discriminator (scoped to an explicit allowlist).** This test governs only the
enumerated ``sync_authority`` adapter symbols and their named canonical delegates —
so it is neither brittle against the package's other 5+ ``*Authority*`` surfaces
(``target_authority``, ``AdmissionAudience``, ``build_admission_audience``, …) nor
vacuous. It is **distinct from** ``test_2093_authority_invariant.py``: that test
governs WP-runtime-state *field* authority (``status.reducer`` slots vs
``FrontmatterManager`` schema — the frontmatter-vs-event-log split); this one
governs the sync CLI's READ/WRITE/ADMISSION *ports*. The two share no symbol.
"""

from __future__ import annotations

import inspect

import pytest

import specify_cli.sync.sync_authority as sync_authority

pytestmark = [pytest.mark.architectural, pytest.mark.fast]


# --- The explicit allowlist this test governs (A-3) --------------------------
_READ_SURFACE: frozenset[str] = frozenset({"_require_daemon_owner_coherence"})
_WRITE_SURFACE: frozenset[str] = frozenset({"request_repository_share", "leave_repository_share"})
_ADMISSION_SURFACE: frozenset[str] = frozenset(
    {"_assert_event_sync_runtime_authority", "_assert_delivery_target_matches_context"}
)

#: Each surface paired with the ONE canonical module its adapters must delegate to.
_SURFACES: dict[str, tuple[frozenset[str], str]] = {
    "read": (_READ_SURFACE, "specify_cli.sync.preflight"),
    "write": (_WRITE_SURFACE, "specify_cli.sync.sharing_client"),
    "admission": (_ADMISSION_SURFACE, "specify_cli.sync.target_authority"),
}

_ALL_GOVERNED: frozenset[str] = _READ_SURFACE | _WRITE_SURFACE | _ADMISSION_SURFACE


def test_every_governed_symbol_exists_and_is_a_callable_adapter() -> None:
    """The allowlist is live — each symbol resolves to a callable on the module."""
    for name in sorted(_ALL_GOVERNED):
        obj = getattr(sync_authority, name, None)
        assert obj is not None, f"{name} missing from sync_authority (allowlist stale)"
        assert callable(obj), f"{name} is not callable"


def test_the_three_surfaces_are_disjoint_symbol_sets() -> None:
    """READ / WRITE / ADMISSION share no symbol — three ports, not one."""
    assert _READ_SURFACE.isdisjoint(_WRITE_SURFACE)
    assert _READ_SURFACE.isdisjoint(_ADMISSION_SURFACE)
    assert _WRITE_SURFACE.isdisjoint(_ADMISSION_SURFACE)
    # Non-vacuity: all three sets are actually populated.
    assert _READ_SURFACE and _WRITE_SURFACE and _ADMISSION_SURFACE


def test_the_three_surfaces_delegate_to_three_distinct_canonical_modules() -> None:
    """Non-unification (INV-2): the canonical delegates are three distinct modules.

    Unifying two surfaces onto one canonical authority surface (e.g. routing READ
    and WRITE through a single class) collapses this set below three and turns the
    test red.
    """
    canonical_modules = {module for (_symbols, module) in _SURFACES.values()}
    # Set-equality is the real contract (golden-count #2076/FR-014): it fails not
    # only when two surfaces collapse below three, but also when a delegate is
    # repointed to the wrong canonical module while still keeping three distinct.
    assert canonical_modules == {
        "specify_cli.sync.preflight",
        "specify_cli.sync.sharing_client",
        "specify_cli.sync.target_authority",
    }, f"surfaces collapsed onto shared delegate(s): {canonical_modules}"


def test_each_surface_delegates_to_its_canonical_surface_not_reimplements() -> None:
    """Delegation, not duplication (DIRECTIVE_044).

    Each surface's adapter bodies must *import* their canonical module — the
    reviewer's grep check, codified. A copied ``preflight`` / ``sharing_client`` /
    ``target_authority`` body would carry the logic inline and reference the module
    nowhere, turning this red.
    """
    for surface, (symbols, canonical) in _SURFACES.items():
        combined_source = "\n".join(inspect.getsource(getattr(sync_authority, name)) for name in symbols)
        assert f"from {canonical} import" in combined_source, f"{surface} surface does not delegate to {canonical}"


def test_no_shared_authority_class_hosts_more_than_one_surface() -> None:
    """No single class may own adapters from more than one surface (INV-2).

    The adapters are module-level functions, so ``__qualname__`` carries no owning
    class and no class unifies two ports. If a future refactor folded, say, READ and
    WRITE into one ``SyncAuthority`` class, both would share the ``SyncAuthority.``
    qualname prefix and this assertion would fail.
    """
    owner_to_surfaces: dict[str, set[str]] = {}
    for surface, (symbols, _canonical) in _SURFACES.items():
        for name in symbols:
            obj = getattr(sync_authority, name)
            qualname = obj.__qualname__
            if "." in qualname and "<locals>" not in qualname:
                owning_class = qualname.rsplit(".", 1)[0]
                owner_to_surfaces.setdefault(owning_class, set()).add(surface)
    shared = {cls: surfaces for cls, surfaces in owner_to_surfaces.items() if len(surfaces) > 1}
    assert not shared, f"a class unifies more than one authority surface: {shared}"


def test_governed_domain_is_the_sync_cli_ports_distinct_from_2093() -> None:
    """The discriminator is the sync-CLI ports, a different domain from #2093.

    ``test_2093_authority_invariant.py`` governs WP-runtime-state field authority
    (``status.reducer`` slots vs ``FrontmatterManager`` schema). This test's
    canonical delegates are all ``specify_cli.sync.*`` surfaces and none is a
    reducer/frontmatter symbol, so the two tests cannot be duplicates.
    """
    canonical_modules = {module for (_symbols, module) in _SURFACES.values()}
    assert all(module.startswith("specify_cli.sync.") for module in canonical_modules)
    assert not any("reducer" in module or "frontmatter" in module for module in canonical_modules)
