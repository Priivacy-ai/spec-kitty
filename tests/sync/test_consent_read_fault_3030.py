"""FR-020 read-fault diagnostics under UUID-owned consent authority.

Checkout files and the machine index are retained as diagnostic evidence only.
Neither can grant, refuse, or override an explicit decision in the project's own
store. These tests keep the original corrupt/unreadable matrix while proving that
live decisions remain project-owned and that the diagnostic health seam still names
legacy-index faults truthfully.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from specify_cli.sync import consent as consent_module
from specify_cli.sync.consent import (
    LEVEL_RESOLVERS,
    PROJECT_CONSENT_PRECEDENCE,
    ConsentLevel,
    consent_index_health,
    consented_project_uuids,
    record_project_opt_in,
    record_project_opt_out,
    resolve_project_consent,
)

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

UUID_A = "aaaaaaaa-0000-0000-0000-000000000001"
UUID_B = "bbbbbbbb-0000-0000-0000-000000000002"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A per-test machine home, with the arming env var deleted.

    Isolation matters more here than elsewhere: ``_answer_project_local`` calls
    ``_reconcile_index``, so a readable refusal *rewrites* the index. An earlier
    revision of this file shared one home across cases and the reconciliation from
    case 1 silently supplied case 2's answer, which made a leak look like a denial.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)


def _machine_config(tmp_path: Path) -> Path:
    return tmp_path / "home" / "config.toml"


def _seed_legacy_index(tmp_path: Path, project_uuid: str = UUID_A) -> Path:
    """Write diagnostic-only legacy evidence without invoking a retired writer."""
    path = _machine_config(tmp_path)
    path.write_text(
        f'[sync.project_consent."{project_uuid}"]\nenabled = true\n',
        encoding="utf-8",
    )
    return path


def _checkout(tmp_path: Path, name: str, *, body: str) -> Path:
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    (root / ".kittify" / "config.yaml").write_text(body, encoding="utf-8")
    return root


def _readable_refusal(uuid: str) -> str:
    return f"project:\n  uuid: {uuid}\n  slug: proj\nsync:\n  enabled: false\n"


#: Valid YAML is not enough to be *usable* here; this is a truncated mid-write file,
#: the realistic corruption for a config an editor or a crashed process left behind.
_UNPARSEABLE_YAML = "project:\n  uuid: [unclosed\n ::: @@@ not yaml\nsync:\n enabled: false\n"


@pytest.fixture
def _unreadable():
    """Make a file unreadable for the duration of one assertion, then restore it.

    Restoration is in a fixture rather than inline so a failing assertion cannot
    leave a 000-mode file behind for pytest's own tmp_path cleanup to trip over.
    """
    restore: list[tuple[Path, int]] = []

    def _apply(path: Path) -> Path:
        restore.append((path, stat.S_IMODE(path.stat().st_mode)))
        os.chmod(path, 0o000)
        return path

    yield _apply
    for path, mode in restore:
        if path.exists():
            os.chmod(path, mode)


def _skip_if_root() -> None:
    if os.geteuid() == 0:
        pytest.skip("running as root: mode 000 does not deny access")


# --------------------------------------------------------------------------- #
# Level 2 — the machine-global index. Fails closed; must stop lying about why. #
# --------------------------------------------------------------------------- #


def test_corrupt_machine_index_is_undetermined_not_absent(tmp_path: Path) -> None:
    """A corrupt legacy index is diagnostic and cannot override a refusal."""
    record_project_opt_out(UUID_A, actor="read-fault-test")
    _machine_config(tmp_path).write_text("this is not [valid toml at all", encoding="utf-8")

    decision = resolve_project_consent(UUID_A)

    assert decision.granted is False, "an unreadable index must never grant"
    assert decision.level is ConsentLevel.PROJECT_STORE
    assert consent_index_health().readable is False


def test_unreadable_machine_index_is_undetermined_not_absent(tmp_path: Path, _unreadable) -> None:
    """Same fault class via permissions rather than content."""
    _skip_if_root()
    record_project_opt_out(UUID_A, actor="read-fault-test")
    _unreadable(_seed_legacy_index(tmp_path))

    decision = resolve_project_consent(UUID_A)

    assert decision.granted is False
    assert decision.level is ConsentLevel.PROJECT_STORE
    assert consent_index_health().readable is False


def test_a_missing_machine_index_is_still_plain_absence(tmp_path: Path) -> None:
    """Absence and fault must not collapse in the *other* direction either.

    An unconfigured machine has no ``config.toml`` at all. Reporting that as
    UNDETERMINED would bury FR-002's real and much more common case — no consent
    record — under a fault the operator does not have.
    """
    assert not _machine_config(tmp_path).exists()

    decision = resolve_project_consent(UUID_A)

    assert decision.granted is False
    assert decision.level is ConsentLevel.ABSENT
    assert "no UUID-owned project consent decision" in decision.reason


# --------------------------------------------------------------------------- #
# Level 1 — the project's own file. This one leaked.                           #
# --------------------------------------------------------------------------- #


def test_unparseable_project_file_does_not_let_a_stale_index_grant_through(
    tmp_path: Path,
) -> None:
    """The leak: an unreadable committed refusal must not be replaced by a grant.

    The index carries a grant, as it does for every checkout that was moved,
    renamed or cloned. Before the fix this returned ``granted=True,
    level=machine_index`` — FR-013's refusal-outranks-grant rule voided by a YAML
    syntax error.
    """
    record_project_opt_out(UUID_A, actor="read-fault-test")
    root = _checkout(tmp_path, "proj", body=_UNPARSEABLE_YAML)

    decision = resolve_project_consent(UUID_A, checkout_roots=[root])

    assert decision.granted is False, (
        "the project's own config is unreadable and might refuse; falling through "
        "to the machine index's grant is egress the authoritative file may have "
        "forbidden (FR-013)"
    )
    assert decision.level is ConsentLevel.PROJECT_STORE


def test_unreadable_project_file_does_not_let_a_stale_index_grant_through(tmp_path: Path, _unreadable) -> None:
    """Same leak via permissions."""
    _skip_if_root()
    record_project_opt_out(UUID_A, actor="read-fault-test")
    root = _checkout(tmp_path, "proj", body=_readable_refusal(UUID_A))
    _unreadable(root / ".kittify" / "config.yaml")

    decision = resolve_project_consent(UUID_A, checkout_roots=[root])

    assert decision.granted is False
    assert decision.level is ConsentLevel.PROJECT_STORE


def test_a_readable_refusal_still_answers_at_level_one(tmp_path: Path) -> None:
    """The unchanged happy path for refusal — a fault must not shadow a real answer."""
    record_project_opt_out(UUID_A, actor="read-fault-test")
    root = _checkout(tmp_path, "proj", body=_readable_refusal(UUID_A))

    decision = resolve_project_consent(UUID_A, checkout_roots=[root])

    assert decision.granted is False
    assert decision.level is ConsentLevel.PROJECT_STORE


def test_a_readable_refusal_outranks_an_unreadable_sibling_root(tmp_path: Path) -> None:
    """A fault must not upgrade a denial into a vaguer denial.

    Two checkouts of one project, one refusing and readable, one unreadable. The
    answer is already known and attributable; the fault changes nothing.
    """
    record_project_opt_out(UUID_A, actor="read-fault-test")
    good = _checkout(tmp_path, "good", body=_readable_refusal(UUID_A))
    bad = _checkout(tmp_path, "bad", body=_UNPARSEABLE_YAML)

    decision = resolve_project_consent(UUID_A, checkout_roots=[good, bad])

    assert decision.granted is False
    assert decision.level is ConsentLevel.PROJECT_STORE


def test_a_root_with_no_kittify_config_is_not_a_fault(tmp_path: Path) -> None:
    """Most offered roots have no project config; that is absence, not a fault.

    The drain and the capture path both offer whatever checkout they are standing
    in. Treating a bare directory as unreadable would deny every delivery on the
    machine.
    """
    record_project_opt_in(UUID_A, actor="read-fault-test")
    bare = tmp_path / "bare"
    bare.mkdir()

    decision = resolve_project_consent(UUID_A, checkout_roots=[bare])

    assert decision.granted is True
    assert decision.level is ConsentLevel.PROJECT_STORE


# --------------------------------------------------------------------------- #
# The fail-closed contract every existing caller silently depends on           #
# --------------------------------------------------------------------------- #


def test_undetermined_never_grants_through_the_drain_seam(tmp_path: Path) -> None:
    """``consented_project_uuids`` is the drain's seam and keeps its shape.

    Its signature is unchanged (a ``frozenset`` of granted uuids), so no caller has
    to learn ``UNDETERMINED`` in order to stay safe: an undetermined project is
    simply not in the set. That is the property that makes this change unable to
    open an egress path anywhere it was not already open.
    """
    record_project_opt_out(UUID_A, actor="read-fault-test")
    record_project_opt_out(UUID_B, actor="read-fault-test")
    _machine_config(tmp_path).write_text("not [ toml", encoding="utf-8")

    assert consented_project_uuids([UUID_A, UUID_B]) == frozenset()


def test_a_healthy_grant_is_untouched(tmp_path: Path) -> None:
    """The blanket-deny falsifier. Without this the whole file passes vacuously."""
    record_project_opt_in(UUID_A, actor="read-fault-test")

    decision = resolve_project_consent(UUID_A)

    assert decision.granted is True
    assert decision.level is ConsentLevel.PROJECT_STORE
    assert consented_project_uuids([UUID_A]) == frozenset({UUID_A})


def test_undetermined_is_a_terminal_outcome_not_a_dispatchable_level(
    tmp_path: Path,
) -> None:
    """UNDETERMINED must stay out of the chain, exactly as ABSENT does.

    ``PROJECT_CONSENT_PRECEDENCE`` drives ``LEVEL_RESOLVERS`` through
    ``_check_chain_is_dispatchable()``, which raises when the tuple and the table
    disagree. A member in neither is invisible to that check — that is how ABSENT
    already works, and it is why naming this outcome as a level costs nothing in
    dispatch. This pin is what keeps a later edit from "completing" the chain by
    adding a resolver for it, which would silently insert a fourth level.
    """
    del tmp_path
    assert ConsentLevel.UNDETERMINED not in PROJECT_CONSENT_PRECEDENCE
    assert ConsentLevel.UNDETERMINED not in LEVEL_RESOLVERS
    assert ConsentLevel.ABSENT not in PROJECT_CONSENT_PRECEDENCE, "the precedent this mirrors must still hold"
    consent_module._check_chain_is_dispatchable()  # must not raise


# --------------------------------------------------------------------------- #
# SC-004: what the doctor surface needs (rendering is owed elsewhere)          #
# --------------------------------------------------------------------------- #


def test_index_health_names_a_corrupt_index(tmp_path: Path) -> None:
    """``sync doctor`` cannot currently tell an operator their index is unreadable.

    This is the machine-level question the report layer must ask *once*, rather than
    inferring a fault from N undetermined projects. The rendering lives in an
    unmerged lane; this is the seam it consumes.
    """
    _seed_legacy_index(tmp_path)
    _machine_config(tmp_path).write_text("not [ toml", encoding="utf-8")

    health = consent_index_health()

    assert health.readable is False
    assert health.fault is not None
    assert health.fault.kind == "unparseable"
    assert str(_machine_config(tmp_path)) in health.fault.detail, "the operator must be told which file to fix"


def test_index_health_is_clean_when_the_index_reads(tmp_path: Path) -> None:
    _seed_legacy_index(tmp_path)

    health = consent_index_health()

    assert health.readable is True
    assert health.fault is None


def test_index_health_is_clean_when_there_is_no_index_yet(tmp_path: Path) -> None:
    """A fresh machine is healthy, not faulted."""
    assert not _machine_config(tmp_path).exists()

    health = consent_index_health()

    assert health.readable is True
    assert health.fault is None
