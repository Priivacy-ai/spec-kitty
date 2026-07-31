"""T014/T015: the one consent resolver and its precedence chain (#3030 WP05).

Implements the FR-013 × FR-019 reconciliation recorded in spec.md. Precedence,
highest first:

1. the project's own ``.kittify/config.yaml`` — authoritative when readable, and a
   **refusal outranks a grant** (two checkouts can share a ``project_uuid`` via a
   committed file and disagree)
2. the machine-global uuid-keyed index — the drain's lookup, and a *cache*, not a
   second source of truth
3. ``SPEC_KITTY_ENABLE_SAAS_SYNC`` — machine-global arming, **never a grant on its
   own**
4. nothing recorded anywhere → **deny** (FR-002)

Every test asserts through the public seam. The chain is not re-derived anywhere
else, which a guard below pins the same way T011 pins identity resolution: a second
copy is how the reporting surface and the drain come to disagree.
"""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from specify_cli.sync import consent as consent_module
from specify_cli.sync.consent import (
    PROJECT_CONSENT_PRECEDENCE,
    ConsentLevel,
    backfill_uuid_consent_index,
    consented_project_uuids,
    resolve_project_consent,
)

pytestmark = [pytest.mark.fast]

UUID_A = "aaaaaaaa-0000-0000-0000-000000000001"
UUID_B = "bbbbbbbb-0000-0000-0000-000000000002"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)


def _checkout(tmp_path: Path, name: str, *, uuid: str, hosted: bool | None) -> Path:
    """A checkout whose .kittify/config.yaml carries identity and consent.

    Writes ``sync.enabled`` — the one canonical project-local consent key as of
    2026-07-30. It previously wrote ``sync.hosted``, a spelling nothing else in the
    tree used; the acceptance pin in ``test_sync_consent_default_deny.py`` writes
    ``sync.enabled``, and having both was C-003's "two representations of one
    invariant".
    """
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    lines = ["project:", f"  uuid: {uuid}", f"  slug: {name}"]
    if hosted is not None:
        lines += ["sync:", f"  enabled: {str(hosted).lower()}"]
    (root / ".kittify" / "config.yaml").write_text("\n".join(lines) + "\n")
    return root


def _index(**entries: bool) -> None:
    """Seed the machine-global uuid-keyed index through the public writer."""
    from specify_cli.sync.consent import set_project_consent

    for uuid, enabled in entries.items():
        set_project_consent(uuid, enabled)


# --- T015 / FR-002: absence denies ----------------------------------------


def test_nothing_recorded_anywhere_denies() -> None:
    decision = resolve_project_consent(UUID_A)
    assert decision.granted is False
    assert decision.level is ConsentLevel.ABSENT


def test_absence_denies_even_with_the_env_var_armed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The env var is machine-global arming, never per-project consent.

    This is the incident: the operator exported the env var, and five projects
    with no record rode along on it.
    """
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    decision = resolve_project_consent(UUID_A)

    assert decision.granted is False
    assert decision.level is ConsentLevel.ABSENT


def test_unresolvable_project_uuid_denies() -> None:
    for value in (None, "", "   "):
        assert resolve_project_consent(value).granted is False


# --- machine-global index -------------------------------------------------


def test_index_grant_is_honoured() -> None:
    _index(**{UUID_A: True})
    decision = resolve_project_consent(UUID_A)
    assert decision.granted is True
    assert decision.level is ConsentLevel.MACHINE_INDEX


def test_index_refusal_is_honoured() -> None:
    _index(**{UUID_A: False})
    assert resolve_project_consent(UUID_A).granted is False


def test_index_answers_when_the_checkout_is_gone(tmp_path: Path) -> None:
    """The relocation case FR-013 exists for.

    A project-local-only design cannot answer here: reading the file needs the
    path, and the checkout has moved or been deleted. Without the index the
    operator's own consented history would strand.
    """
    _index(**{UUID_A: True})

    decision = resolve_project_consent(UUID_A, repo_root=tmp_path / "gone")

    assert decision.granted is True
    assert decision.level is ConsentLevel.MACHINE_INDEX


# --- FR-019: the project's own file outranks the machine ------------------


def test_project_local_grant_outranks_an_absent_index(tmp_path: Path) -> None:
    root = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=True)
    decision = resolve_project_consent(UUID_A, repo_root=root)
    assert decision.granted is True
    assert decision.level is ConsentLevel.PROJECT_LOCAL


def test_project_local_refusal_outranks_an_index_grant(tmp_path: Path) -> None:
    """Pin 3's durable form: a project-local refusal wins."""
    _index(**{UUID_A: True})
    root = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=False)

    decision = resolve_project_consent(UUID_A, repo_root=root)

    assert decision.granted is False
    assert decision.level is ConsentLevel.PROJECT_LOCAL


def test_project_local_refusal_outranks_the_env_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pin 4: project-local refusal beats the machine-global env var."""
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    root = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=False)

    assert resolve_project_consent(UUID_A, repo_root=root).granted is False


def test_a_project_local_file_for_another_project_is_ignored(tmp_path: Path) -> None:
    """The file only speaks for the uuid it declares.

    Otherwise standing in checkout B while resolving project A would let B's
    consent answer for A — a fuzzy correspondence FR-013's conflict rule and
    #3031 Defect 2 both exist to eliminate.
    """
    _index(**{UUID_A: False})
    other = _checkout(tmp_path, "other", uuid=UUID_B, hosted=True)

    decision = resolve_project_consent(UUID_A, repo_root=other)

    assert decision.granted is False
    assert decision.level is not ConsentLevel.PROJECT_LOCAL


# --- conflict rule: deny if ANY checkout is opted out ---------------------


def test_refusal_in_any_checkout_denies_the_project(tmp_path: Path) -> None:
    """Two checkouts, one uuid, opposite settings → deny.

    FR-013's stated rule, encoded once. A committed .kittify/config.yaml makes
    this reachable in practice, not hypothetical.
    """
    granting = _checkout(tmp_path, "clone-a", uuid=UUID_A, hosted=True)
    refusing = _checkout(tmp_path, "clone-b", uuid=UUID_A, hosted=False)

    decision = resolve_project_consent(
        UUID_A, checkout_roots=[granting, refusing]
    )

    assert decision.granted is False
    assert decision.level is ConsentLevel.PROJECT_LOCAL


def test_all_checkouts_granting_grants(tmp_path: Path) -> None:
    a = _checkout(tmp_path, "clone-a", uuid=UUID_A, hosted=True)
    b = _checkout(tmp_path, "clone-b", uuid=UUID_A, hosted=True)
    assert resolve_project_consent(UUID_A, checkout_roots=[a, b]).granted is True


# --- the index is a cache, not a second source of truth -------------------


def test_a_readable_checkout_corrects_a_stale_index(tmp_path: Path) -> None:
    """Reported state and enforced state must agree.

    The index said yes; the project's own file says no. The file wins *and* the
    index is corrected, so a later lookup without the checkout does not resurrect
    the stale grant.
    """
    _index(**{UUID_A: True})
    root = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=False)

    assert resolve_project_consent(UUID_A, repo_root=root).granted is False

    # Same question, checkout no longer available: the corrected value persists.
    assert resolve_project_consent(UUID_A).granted is False


# --- FR-019: a repo slug is never an authorization key --------------------


def test_repo_default_grant_does_not_consent_for_an_unrecorded_uuid(
    tmp_path: Path,
) -> None:
    """The re-``git init`` / fresh-clone case: a repo default must NOT grant.

    spec.md records the edge case explicitly — a re-initialised repo "starts
    non-consented". A repo-slug-keyed ``[sync.repo_defaults]`` grant survives the
    re-init untouched, because the git *remote* did not change; only the project
    identity did. If that record were a level of the consent chain, the brand-new
    uuid would resolve to *granted* on its first emit, having never been asked.

    The same record covers every fresh clone of the repo, on any machine, for any
    operator — which is precisely why FR-019 condemns "a record keyed on a mutable
    git remote". A level for it existed briefly on 2026-07-30 and was removed.

    Set up as the incident's own shape: the machine-global config carries an
    ``enabled = true`` repo default, the project's uuid has no record anywhere, and
    the answer must still be deny.
    """
    from specify_cli.sync.config import SyncConfig

    repo_slug = "client-org/confidential-work"
    SyncConfig().set_repository_sync_enabled(repo_slug, True)
    assert SyncConfig().get_repository_sync_enabled(repo_slug) is True, (
        "premise: the repo default really is recorded as a grant"
    )

    fresh_uuid = "dddddddd-0000-0000-0000-000000000004"
    decision = resolve_project_consent(fresh_uuid)

    assert decision.granted is False, (
        "a repo-slug-keyed default must never grant consent for a project uuid "
        "that has no record of its own: the slug is a mutable git remote (FR-019), "
        "so a re-`git init`ed or freshly cloned project would inherit a decision "
        "nobody made about it"
    )
    assert decision.level is ConsentLevel.ABSENT, (
        "the decision must fall through to the terminal default, naming absence — "
        "not report a repo-slug level as having answered"
    )

    # And the drain's seam must agree with the resolver, since that is the path
    # delivery actually takes.
    assert consented_project_uuids([fresh_uuid]) == frozenset(), (
        "the drain predicate must reach the same answer as the resolver"
    )

    # The load-bearing half. The two assertions above cannot go red on their own
    # under the reverted implementation, because there the repo slug had to be
    # *passed in* and neither call passes one. The drain did pass one: the journal
    # row carries repo_slug, and selection.py forwarded it into the resolver. So the
    # pin has to enter through selection, or it pins nothing.
    from specify_cli.delivery.selection import selectable_event_ids
    from specify_cli.event_journal import EventIdentityRow

    row = EventIdentityRow(
        event_id="evt-fresh-clone",
        created_at="2026-07-30T00:00:00Z",
        project_uuid=fresh_uuid,
        repo_slug=repo_slug,
        # Drain-open: nothing about machine readiness may be doing this work.
        drain_blocked_reason=None,
    )

    assert selectable_event_ids([row]) == [], (
        "a drain-open row whose repo_slug carries an `enabled = true` repo default "
        "must NOT be selectable while its project uuid has no consent record: that "
        "is the fresh-clone/re-init grant FR-019 forbids, and the row's repo_slug "
        "must never be forwarded to the consent chain as an authorization key"
    )


# --- the drain's seam -----------------------------------------------------


def test_consented_project_uuids_filters_the_candidate_set() -> None:
    _index(**{UUID_A: True, UUID_B: False})

    consented = consented_project_uuids([UUID_A, UUID_B, "cccccccc-0000-0000-0000-000000000003"])

    assert consented == frozenset({UUID_A})


def test_consented_project_uuids_never_returns_none() -> None:
    """NFR-001's second half: an unresolved identity is never consentable."""
    _index(**{UUID_A: True})
    assert consented_project_uuids([UUID_A, None, ""]) == frozenset({UUID_A})


# --- T016: backfill path-keyed records into the uuid index ----------------


def test_backfill_maps_path_keyed_records_to_uuids(tmp_path: Path) -> None:
    from specify_cli.sync.config import SyncConfig

    granting = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=None)
    refusing = _checkout(tmp_path, "other", uuid=UUID_B, hosted=None)
    cfg = SyncConfig()
    cfg.set_checkout_sync_enabled(granting, True)
    cfg.set_checkout_sync_enabled(refusing, False)

    result = backfill_uuid_consent_index()

    assert result.mapped == 2
    assert resolve_project_consent(UUID_A).granted is True
    assert resolve_project_consent(UUID_B).granted is False


def test_backfill_marks_unresolvable_paths_instead_of_dropping_them(
    tmp_path: Path,
) -> None:
    """US2 scenario 3: 'consented but unresolvable' must be reportable.

    An absent checkout yields no uuid, so it cannot enter the index. Dropping the
    record would silently lose the operator's decision; keeping it unmarked would
    imply it is enforced. It is retained and marked, so WP07 can render it and
    the predicate can ignore it.
    """
    from specify_cli.sync.config import SyncConfig

    SyncConfig().set_checkout_sync_enabled(tmp_path / "vanished", True)

    result = backfill_uuid_consent_index()

    assert result.mapped == 0
    assert result.unresolved == 1
    assert [entry.path for entry in result.unresolved_entries] == [
        str((tmp_path / "vanished").resolve())
    ]


def test_backfill_is_idempotent(tmp_path: Path) -> None:
    from specify_cli.sync.config import SyncConfig

    root = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=None)
    SyncConfig().set_checkout_sync_enabled(root, True)

    first = backfill_uuid_consent_index()
    second = backfill_uuid_consent_index()

    assert first.mapped == 1
    assert second.mapped == 0, "a converged index has nothing left to map"
    assert resolve_project_consent(UUID_A).granted is True


def test_backfill_applies_the_conflict_rule(tmp_path: Path) -> None:
    """Two path records for one uuid, one opted out → the project denies."""
    from specify_cli.sync.config import SyncConfig

    a = _checkout(tmp_path, "clone-a", uuid=UUID_A, hosted=None)
    b = _checkout(tmp_path, "clone-b", uuid=UUID_A, hosted=None)
    cfg = SyncConfig()
    cfg.set_checkout_sync_enabled(a, True)
    cfg.set_checkout_sync_enabled(b, False)

    backfill_uuid_consent_index()

    assert resolve_project_consent(UUID_A).granted is False


# --- NFR-001: one definition site for the chain ---------------------------


def test_precedence_chain_has_one_definition_site() -> None:
    root = Path(__file__).resolve().parents[2] / "src"
    canonical = Path("specify_cli/sync/consent.py")
    offenders: dict[str, list[str]] = {}

    for path in sorted(root.rglob("*.py")):
        rel = path.relative_to(root)
        if rel == canonical:
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):  # pragma: no cover
            continue
        hits = [
            t.id
            for node in ast.walk(tree)
            if isinstance(node, (ast.Assign, ast.AnnAssign))
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target])
            if isinstance(t, ast.Name) and "CONSENT_PRECEDENCE" in t.id
        ]
        if hits:
            offenders[str(rel)] = hits

    assert not offenders, (
        "the consent precedence chain must have exactly one definition site "
        f"(specify_cli/sync/consent.py); found: {offenders}"
    )


def _chain(monkeypatch: pytest.MonkeyPatch, *levels: ConsentLevel) -> None:
    """Rewrite the declared chain for one test.

    Patches the module attribute, not the imported alias, because the resolver must
    read the constant at call time. A resolver that captured the order at import — or
    hardcoded it — is unaffected by this, which is exactly what the tests below are
    for.
    """
    monkeypatch.setattr(consent_module, "PROJECT_CONSENT_PRECEDENCE", tuple(levels))


def test_reordering_the_declared_chain_reorders_the_resolver(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """C-003: the constant must be load-bearing, not decorative.

    ``PROJECT_CONSENT_PRECEDENCE`` documents itself as the single site where the
    chain is expressed. That is only true if the resolver *derives* its order from
    it. Swap the top two levels in the data and the outcome must swap with them: the
    machine index, promoted above the project's own file, now answers a question that
    ``test_project_local_refusal_outranks_an_index_grant`` shows the file answers
    under the declared order.

    Against a resolver with the order baked into an if-chain this asserts the
    opposite of what happens, so it goes red — the two representations had drifted by
    construction the moment one was edited.
    """
    _index(**{UUID_A: True})
    root = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=False)

    _chain(
        monkeypatch,
        ConsentLevel.MACHINE_INDEX,
        ConsentLevel.PROJECT_LOCAL,
        ConsentLevel.ENV,
    )

    decision = resolve_project_consent(UUID_A, repo_root=root)

    assert decision.level is ConsentLevel.MACHINE_INDEX, (
        "the resolver consulted the project-local level first even though the "
        "declared chain puts the machine index first: the order is expressed in a "
        "second place"
    )
    assert decision.granted is True


def test_dropping_a_level_from_the_declared_chain_stops_it_being_consulted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Membership is derived too, not just order.

    A level absent from the data must not be reachable. Otherwise a level could be
    retired from the declared chain and go on answering.
    """
    _index(**{UUID_A: True})
    root = _checkout(tmp_path, "acme", uuid=UUID_A, hosted=False)

    _chain(monkeypatch, ConsentLevel.MACHINE_INDEX, ConsentLevel.ENV)

    decision = resolve_project_consent(UUID_A, repo_root=root)

    assert decision.level is ConsentLevel.MACHINE_INDEX
    assert decision.granted is True


def test_an_empty_declared_chain_denies(monkeypatch: pytest.MonkeyPatch) -> None:
    """Nothing outside the chain may grant.

    With no levels declared there is no authority to consult, so FR-002's terminal
    default is the only possible answer — even with a grant sitting in the index.
    This is the fail-closed half of making the constant load-bearing.
    """
    _index(**{UUID_A: True})

    _chain(monkeypatch)

    decision = resolve_project_consent(UUID_A)

    assert decision.granted is False
    assert decision.level is ConsentLevel.ABSENT


def test_the_env_level_cannot_grant_even_promoted_to_the_top(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deriving the order must not turn the env var into a grantable level.

    ``SPEC_KITTY_ENABLE_SAAS_SYNC`` is machine-global arming. Its place in the chain
    is a record that it is *consulted and refused*; no position can make it answer.
    Pinned against position because the dispatch now takes position from data — a
    future edit that gives the env level a decision to return would leak exactly the
    2026-07-27 incident.
    """
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")

    _chain(
        monkeypatch,
        ConsentLevel.ENV,
        ConsentLevel.PROJECT_LOCAL,
        ConsentLevel.MACHINE_INDEX,
    )

    decision = resolve_project_consent(UUID_A)

    assert decision.granted is False
    assert decision.level is ConsentLevel.ABSENT


def test_every_declared_level_has_exactly_one_resolver() -> None:
    """The dispatch table and the declared chain must be in bijection.

    The tuple owns the *order*; the table owns *how* each level answers. A level in
    the tuple with no resolver would be silently skipped, and a resolver for a level
    not in the tuple is unreachable — both are the drift this remediation removes.
    ``ABSENT`` is the terminal default, never a level that can answer.
    """
    resolvers = consent_module.LEVEL_RESOLVERS

    assert set(resolvers) == set(PROJECT_CONSENT_PRECEDENCE)
    assert ConsentLevel.ABSENT not in resolvers


def test_a_declared_level_with_no_resolver_refuses_to_load(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The bijection is enforced at import, not merely asserted by a test.

    Under-enforcing consent silently is the failure this module exists to prevent, so
    a chain the dispatch cannot walk is a load-time error rather than a level quietly
    skipped at runtime.
    """
    _chain(monkeypatch, ConsentLevel.PROJECT_LOCAL, ConsentLevel.ABSENT)

    with pytest.raises(RuntimeError, match="no resolver"):
        consent_module._check_chain_is_dispatchable()

    monkeypatch.setitem(
        consent_module.LEVEL_RESOLVERS, ConsentLevel.ABSENT, lambda _u, _r: None
    )
    _chain(monkeypatch, ConsentLevel.PROJECT_LOCAL)

    with pytest.raises(RuntimeError, match="undeclared"):
        consent_module._check_chain_is_dispatchable()


def test_precedence_order_is_pinned() -> None:
    """Guards against a reorder that would silently let the machine outrank the project."""
    assert PROJECT_CONSENT_PRECEDENCE == (
        ConsentLevel.PROJECT_LOCAL,
        ConsentLevel.MACHINE_INDEX,
        ConsentLevel.ENV,
    )
    assert not hasattr(ConsentLevel, "REPO_DEFAULT"), (
        "a repo-slug-keyed consent level was added on 2026-07-30 and removed the "
        "same day: FR-019 condemns that record because it is keyed on a mutable git "
        "remote. Re-adding it would make a fresh clone or a re-`git init`ed repo "
        "inherit a grant nobody gave it — see "
        "test_repo_default_grant_does_not_consent_for_an_unrecorded_uuid"
    )
