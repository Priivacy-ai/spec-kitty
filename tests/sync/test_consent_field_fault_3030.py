"""FR-027 field-fault diagnostics under UUID-owned consent authority.

Checkout ``sync.enabled`` and the machine index are retired as live consent
authorities.  Their malformed values remain useful diagnostics, but only an
explicit decision in the project's own store can grant or refuse hosted egress.
The historical shape matrix remains intact here to prove that no legacy spelling,
fault, clone, or missing field can widen or erase that explicit project decision.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.sync.consent import (
    ConsentLevel,
    consented_project_uuids,
    project_local_consent_fault,
    record_project_opt_in,
    record_project_opt_out,
    resolve_project_consent,
)
from specify_cli.sync.project_store import ProjectSyncStore

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

UUID_A = "aaaaaaaa-0000-0000-0000-000000000001"

_IDENT = f"project:\n  uuid: {UUID_A}\n  slug: proj\n"


@pytest.fixture(autouse=True)
def _isolated_home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A per-test machine home, with the arming env var deleted.

    Load-bearing, not hygiene: ``_answer_project_local`` calls ``_reconcile_index``,
    so a readable-refusal case rewrites the index. Sharing one home across cases is
    how FR-021's first probe read "already fixed" — the reconciliation from an
    earlier case silently supplied the later case's answer, and a leak presented as
    a denial.
    """
    monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    (tmp_path / "home").mkdir(parents=True, exist_ok=True)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)


def _checkout_with_project_decision(tmp_path: Path, body: str | None, *, granted: bool) -> Path:
    """A checkout plus the only authoritative UUID-owned project decision."""
    if granted:
        record_project_opt_in(UUID_A, actor="field-fault-test")
    else:
        record_project_opt_out(UUID_A, actor="field-fault-test")
    root = tmp_path / "proj"
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    if body is not None:
        (root / ".kittify" / "config.yaml").write_text(body, encoding="utf-8")
    return root


# --------------------------------------------------------------------------- #
# Positive controls. Without these the whole file passes by denying everything. #
# --------------------------------------------------------------------------- #


def test_control_a_real_boolean_grant_still_grants(tmp_path: Path) -> None:
    """The falsifier. A probe that denied every case would look like five passes."""
    root = _checkout_with_project_decision(tmp_path, _IDENT + "sync:\n  enabled: true\n", granted=True)

    decision = resolve_project_consent(UUID_A, checkout_roots=[root])

    assert decision.granted is True
    assert decision.level is ConsentLevel.PROJECT_STORE


def test_control_a_real_boolean_refusal_still_denies_at_level_one(tmp_path: Path) -> None:
    """A readable refusal must stay attributed to the file, not downgraded."""
    root = _checkout_with_project_decision(tmp_path, _IDENT + "sync:\n  enabled: false\n", granted=False)

    decision = resolve_project_consent(UUID_A, checkout_roots=[root])

    assert decision.granted is False
    assert decision.level is ConsentLevel.PROJECT_STORE


def test_control_bare_capitalised_False_is_a_yaml_bool_and_denies(tmp_path: Path) -> None:
    """``enabled: False`` unquoted is a real bool — the one shape that already worked.

    Kept as a control precisely because its quoted twin ``"False"`` is a fault: the
    two look identical in a diff and resolve differently, which is why the fault has
    to name the value it could not use.
    """
    root = _checkout_with_project_decision(tmp_path, _IDENT + "sync:\n  enabled: False\n", granted=False)

    decision = resolve_project_consent(UUID_A, checkout_roots=[root])

    assert decision.granted is False
    assert decision.level is ConsentLevel.PROJECT_STORE


# --------------------------------------------------------------------------- #
# Absence must remain absence. Denying on absence denies the whole machine.     #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("case", "body"),
    [
        ("no file at all", None),
        ("no sync section", _IDENT),
        ("empty sync section", _IDENT + "sync:\n"),
        ("empty sync mapping", _IDENT + "sync: {}\n"),
        ("no enabled key", _IDENT + "sync:\n  auto_start: true\n"),
    ],
)
def test_absence_still_falls_through_to_the_machine_index(tmp_path: Path, case: str, body: str | None) -> None:
    """Each of these means "no record" and must keep meaning it.

    Most checkouts on a machine have no project config, and none of them has ever
    had a ``sync:`` section written by production code. Calling any of these a fault
    would deny every delivery on the machine — which is why the fix has to
    discriminate a *present, unusable* value from an absent one.
    """
    root = _checkout_with_project_decision(tmp_path, body, granted=True)

    decision = resolve_project_consent(UUID_A, checkout_roots=[root])

    assert project_local_consent_fault(root) is None, f"{case} must not be a fault"
    assert decision.granted is True, f"{case} must still defer to the index"
    assert decision.level is ConsentLevel.PROJECT_STORE


# --------------------------------------------------------------------------- #
# The leak: a present-but-unusable sync.enabled                                 #
# --------------------------------------------------------------------------- #

#: Every shape measured granting at ``machine_index`` before the fix, plus the ones
#: the report never named. Probed as a *set*: FR-024 was reported as three shapes
#: and turned out to be eleven in three exception flavours, so a fix pinned only
#: against the reported rows is a fix pinned against the wrong denominator.
_UNUSABLE_ENABLED = [
    ('string "false"', _IDENT + 'sync:\n  enabled: "false"\n'),
    ('string "true"', _IDENT + 'sync:\n  enabled: "true"\n'),
    ("bare no (YAML 1.2 string)", _IDENT + "sync:\n  enabled: no\n"),
    ("bare yes (YAML 1.2 string)", _IDENT + "sync:\n  enabled: yes\n"),
    ("bare off", _IDENT + "sync:\n  enabled: off\n"),
    ("bare on", _IDENT + "sync:\n  enabled: on\n"),
    ("int 0", _IDENT + "sync:\n  enabled: 0\n"),
    ("int 1", _IDENT + "sync:\n  enabled: 1\n"),
    ("float 0.0", _IDENT + "sync:\n  enabled: 0.0\n"),
    ("float 1.5", _IDENT + "sync:\n  enabled: 1.5\n"),
    ("explicit null", _IDENT + "sync:\n  enabled: null\n"),
    ("key with no value", _IDENT + "sync:\n  enabled:\n"),
    ("a list", _IDENT + "sync:\n  enabled: [a, b]\n"),
    ("a nested mapping", _IDENT + "sync:\n  enabled:\n    k: v\n"),
    ('capitalised string "False"', _IDENT + 'sync:\n  enabled: "False"\n'),
    ('shouted string "FALSE"', _IDENT + 'sync:\n  enabled: "FALSE"\n'),
    ('padded string "  false  "', _IDENT + 'sync:\n  enabled: "  false  "\n'),
    ("scalar sync section", _IDENT + "sync: disabled\n"),
    ("list sync section", _IDENT + "sync:\n  - a\n"),
]


@pytest.mark.parametrize(("case", "body"), _UNUSABLE_ENABLED, ids=[c for c, _ in _UNUSABLE_ENABLED])
def test_an_unusable_consent_value_denies_instead_of_deferring_to_the_grant(tmp_path: Path, case: str, body: str) -> None:
    """A record that exists and cannot be understood is a fault, and a fault denies.

    The direction matters: not one assertion here grants something that was
    previously denied. Every one of these previously **granted** at
    ``machine_index`` and now denies.
    """
    root = _checkout_with_project_decision(tmp_path, body, granted=False)

    decision = resolve_project_consent(UUID_A, checkout_roots=[root])

    assert decision.granted is False, (
        f"{case}: the project's own config records something under sync.enabled that "
        "cannot be understood, so a committed refusal cannot be ruled out; "
        f"deferring to the machine index's grant is the FR-021 leak at field level "
        f"(got level={decision.level})"
    )
    assert decision.level is ConsentLevel.PROJECT_STORE, f"{case}: expected the explicit project refusal to remain authoritative, got level={decision.level}"


def test_the_field_fault_names_the_file_the_key_and_the_value(tmp_path: Path) -> None:
    """Denying is half the fix; the operator has to be able to see what to edit.

    A denial indistinguishable from "no consent record" sends them to record consent
    they already recorded — FR-020's own lesson. The value is named because
    ``enabled: False`` and ``enabled: "False"`` are one quote apart in a diff.
    """
    root = _checkout_with_project_decision(tmp_path, _IDENT + 'sync:\n  enabled: "no"\n', granted=False)

    fault = project_local_consent_fault(root)

    assert fault is not None
    assert "config.yaml" in fault.detail
    assert "sync.enabled" in fault.detail
    assert "'no'" in fault.detail or '"no"' in fault.detail


def test_a_readable_refusal_still_outranks_an_unusable_sibling(tmp_path: Path) -> None:
    """FR-020's branch order holds at field level too.

    A sibling checkout nobody could understand cannot make an attributable denial
    *less* certain, and downgrading it to UNDETERMINED would lose the attribution.
    """
    record_project_opt_out(UUID_A, actor="field-fault-test")
    good = tmp_path / "good"
    bad = tmp_path / "bad"
    for root, body in ((good, _IDENT + "sync:\n  enabled: false\n"), (bad, _IDENT + "sync:\n  enabled: no\n")):
        (root / ".kittify").mkdir(parents=True)
        (root / ".kittify" / "config.yaml").write_text(body, encoding="utf-8")

    decision = resolve_project_consent(UUID_A, checkout_roots=[good, bad])

    assert decision.granted is False
    assert decision.level is ConsentLevel.PROJECT_STORE


def test_an_unusable_value_never_grants_through_the_drain_seam(tmp_path: Path) -> None:
    """``consented_project_uuids`` keeps its shape: an undetermined project is absent.

    No caller has to learn ``UNDETERMINED`` to stay safe, which is the property that
    makes this change unable to open a path that was not already open.
    """
    root = _checkout_with_project_decision(tmp_path, _IDENT + "sync:\n  enabled: no\n", granted=False)

    assert consented_project_uuids([UUID_A], checkout_roots=[root]) == frozenset()


# --------------------------------------------------------------------------- #
# The delivery decision, not merely the parsed value                            #
# --------------------------------------------------------------------------- #


def test_a_misspelled_refusal_selects_no_event_for_delivery(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The strongest form: a committed ``enabled: no``, a stale grant, zero selected.

    Asserting the *parsed value* would leave the question that matters unanswered —
    whether an event of this project can still reach a receiver. This drives the
    drain's real universe builder through the real default consent predicate, with
    the checkout offered the way the drain offers it (from ``cwd``).
    """
    from specify_cli.delivery.selection import select_consented

    root = _checkout_with_project_decision(tmp_path, _IDENT + "sync:\n  enabled: no\n", granted=False)
    monkeypatch.chdir(root)

    class _Journal:
        """Only the two methods the selector calls, both answering truthfully."""

        project_uuid = UUID_A

        def __init__(self) -> None:
            self.projection_calls: list[object] = []

        def distinct_project_uuids(self) -> list[str]:
            return [UUID_A]

        def read_identity_projection(self, *, project_uuids: list[str]) -> list[object]:
            self.projection_calls.append(project_uuids)
            raise AssertionError("the SQL projection was reached, so an unconsented project's rows were about to be read for delivery")

    journal = _Journal()

    assert select_consented(journal, context=ProjectSyncStore(UUID_A).create_context()).event_ids == []
    assert journal.projection_calls == []


def test_the_same_journal_does_deliver_when_the_refusal_is_absent(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The delivery-path positive control, so the assertion above is not vacuous.

    Same journal, same seam, no project-local record at all: the stale index grant
    legitimately answers and the projection *is* read. Without this, a selector that
    returned ``[]`` unconditionally would pass the test above.
    """
    from specify_cli.delivery.selection import select_consented

    root = _checkout_with_project_decision(tmp_path, _IDENT, granted=True)
    monkeypatch.chdir(root)

    class _Journal:
        project_uuid = UUID_A

        def __init__(self) -> None:
            self.projection_calls: list[object] = []

        def distinct_project_uuids(self) -> list[str]:
            return [UUID_A]

        def read_identity_projection(self, *, project_uuids: list[str]) -> list[object]:
            self.projection_calls.append(project_uuids)
            return []

    journal = _Journal()

    select_consented(journal, context=ProjectSyncStore(UUID_A).create_context())

    assert journal.projection_calls == [[UUID_A]], (
        "a project with no local record must still be reachable through the index; if this is empty the denial above proves nothing"
    )


# --------------------------------------------------------------------------- #
# FR-024's residual: an unusable project.uuid is the same notion, same file     #
# --------------------------------------------------------------------------- #

#: FR-024 stopped these crashing. The residual it left is that they resolve to
#: ``granted=True`` with ``project_uuid=None``, so the events are captured with no
#: identity at all — the population FR-011/FR-017 then have to clean up.
_UNUSABLE_UUID = [
    ("not a uuid", "project:\n  uuid: not-a-uuid\n  slug: proj\n"),
    ("merge conflict marker", "project:\n  uuid: <<<<<<< HEAD\n  slug: proj\n"),
    ("an int", "project:\n  uuid: 42\n  slug: proj\n"),
    ("a mapping", "project:\n  uuid:\n    a: b\n  slug: proj\n"),
    ("a list", "project:\n  uuid: [a]\n  slug: proj\n"),
    ("a non-text sibling slug", f"project:\n  uuid: {UUID_A}\n  slug:\n    a: b\n"),
    # Found by reading a failure rather than a tally: an unquoted ``{uuid}`` is a YAML
    # flow **mapping**, so this is not the braced-uuid spelling it looks like. The
    # quoted form is a valid uuid and is pinned as a grant-carrying match above.
    ("unquoted braces are a flow mapping", f"project:\n  uuid: {{{UUID_A}}}\n"),
]


@pytest.mark.parametrize(("case", "body"), _UNUSABLE_UUID, ids=[c for c, _ in _UNUSABLE_UUID])
def test_an_unusable_identity_value_is_a_fault_not_a_grant(tmp_path: Path, case: str, body: str) -> None:
    """The FR-024 residual, closed by the same notion rather than a second one.

    ``_read_project_local`` defined a fault as unreadable-or-wrong-shape and not as
    an unusable *value*, so FR-022's fence never fired for these. The decision:
    an identity record that cannot be understood is a ``ConfigReadFault``, decided
    by asking ``identity/project.py``'s own single parse site rather than
    re-deciding here what a usable uuid is.
    """
    root = _checkout_with_project_decision(tmp_path, body, granted=False)

    decision = resolve_project_consent(UUID_A, checkout_roots=[root])

    assert project_local_consent_fault(root) is not None, f"{case} must be a fault"
    assert decision.granted is False, f"{case}: got level={decision.level}"
    assert decision.level is ConsentLevel.PROJECT_STORE


@pytest.mark.parametrize(
    ("case", "body"),
    [
        ("no project key", "sync: {}\n"),
        ("empty project section", "project:\n"),
        ("uuid key with no value", "project:\n  uuid:\n  slug: proj\n"),
        ("no uuid key", "project:\n  slug: proj\n"),
        ("project section is a scalar", "project: guard-suite\n"),
    ],
)
def test_an_unrecorded_identity_is_absence_not_a_fault(tmp_path: Path, case: str, body: str) -> None:
    """A checkout that has not been ``init``ed yet is the ordinary pre-identity state.

    ``identity/project.py`` reads every one of these as absence and mints over it —
    including ``project: guard-suite``, which is its recorded FR-023 decision. This
    module must agree, or the two grow separate notions of the same file one function
    apart, which is the C-003 failure the mission keeps closing.
    """
    root = _checkout_with_project_decision(tmp_path, body, granted=True)

    assert project_local_consent_fault(root) is None, f"{case} must not be a fault"
    decision = resolve_project_consent(UUID_A, checkout_roots=[root])
    assert decision.granted is True
    assert decision.level is ConsentLevel.PROJECT_STORE


@pytest.mark.parametrize(
    ("case", "spelling"),
    [
        ("uppercase", UUID_A.upper()),
        ("dash-less 32 hex", UUID_A.replace("-", "")),
        ("urn form", f"urn:uuid:{UUID_A}"),
        # Quoted, deliberately. Unquoted braces are a YAML **flow mapping**, not a
        # braced uuid string — it is a fault, pinned as such just below. The two are
        # one quote apart and resolve to opposite answers, which is the same trap
        # ``enabled: False`` / ``enabled: "False"`` sets.
        ("braced string", f'"{{{UUID_A}}}"'),
    ],
)
def test_a_non_canonical_spelling_of_this_uuid_still_carries_its_refusal(tmp_path: Path, case: str, spelling: str) -> None:
    """Found by probing the set, unreported: a *valid* uuid can fail to match.

    ``_project_local_votes`` compared the file's raw text against the canonical uuid
    the journal stores, so ``AAAAAAAA-…`` — the same uuid, legibly the same project —
    matched nothing and its committed refusal was discarded as belonging to some
    other project. Measured granting at ``machine_index``. Comparing raw text against
    a canonical string is a third representation of one value; parsing both sides
    through ``identity/project.py`` removes it.
    """
    root = _checkout_with_project_decision(
        tmp_path,
        f"project:\n  uuid: {spelling}\n  slug: proj\nsync:\n  enabled: false\n",
        granted=False,
    )

    decision = resolve_project_consent(UUID_A, checkout_roots=[root])

    assert decision.granted is False, f"{case}: this file speaks for exactly this project and refuses; got level={decision.level}"
    assert decision.level is ConsentLevel.PROJECT_STORE


# --------------------------------------------------------------------------- #
# The same field-level question one module over: the machine index's entry       #
# --------------------------------------------------------------------------- #


def test_an_unusable_machine_index_entry_is_undetermined_not_absent(tmp_path: Path) -> None:
    """FR-020's fix, extended to the entry rather than the file.

    A hand-edited ``enabled = "true"`` in ``config.toml`` decoded to ``None``, which
    reports as ``ABSENT`` — "no consent record for this project", the one message
    FR-020 exists to stop sending. It already denied, so this is honesty rather than
    a leak; it is fixed here because leaving it would be the third module deciding
    what a broken record means (C-003).
    """
    (tmp_path / "home" / "config.toml").write_text(f'[sync.project_consent."{UUID_A}"]\nenabled = "true"\n', encoding="utf-8")

    decision = resolve_project_consent(UUID_A)

    assert decision.granted is False
    assert decision.level is ConsentLevel.ABSENT, f"a malformed index entry reported as {decision.level}"
    assert "no consent record" not in decision.reason


def test_a_missing_machine_index_entry_is_still_plain_absence(tmp_path: Path) -> None:
    """The other direction: an unrecorded project must keep reading as unrecorded."""
    record_project_opt_in("bbbbbbbb-0000-0000-0000-000000000002", actor="field-fault-test")

    decision = resolve_project_consent(UUID_A)

    assert decision.granted is False
    assert decision.level is ConsentLevel.ABSENT
    assert "no UUID-owned project consent decision" in decision.reason
