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
    """A checkout whose .kittify/config.yaml carries identity and consent."""
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    lines = ["project:", f"  uuid: {uuid}", f"  slug: {name}"]
    if hosted is not None:
        lines += ["sync:", f"  hosted: {str(hosted).lower()}"]
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


def test_precedence_order_is_pinned() -> None:
    """Guards against a reorder that would silently let the machine outrank the project."""
    assert PROJECT_CONSENT_PRECEDENCE == (
        ConsentLevel.PROJECT_LOCAL,
        ConsentLevel.MACHINE_INDEX,
        # Added 2026-07-30: repo-slug-keyed defaults are where `sync enable
        # --remember` has always written, so they are the only record many projects
        # have. Below the uuid index (which is project-specific, where a repo
        # default covers every checkout of a repo) and above the env var (a real
        # per-repo decision, not machine-wide arming).
        ConsentLevel.REPO_DEFAULT,
        ConsentLevel.ENV,
    )
