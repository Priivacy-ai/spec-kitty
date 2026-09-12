"""`#3111` — the ownership derivation, exercised directly (SC-014, SC-018, SC-002 (c) refuse half).

This is deliberately a **non-CLI** test module that imports the derivation **by
its public name** — which is what SC-018's last clause is for. A module-private
``def _owns_decision(...)`` at the bottom of ``cli/commands/decision.py`` would
satisfy "one named function with a stated home" and still be the fifth private
answer to the ownership question; only a non-CLI caller importing it by path
distinguishes a seam from a helper.

The `#3111` end-to-end acceptance module lives elsewhere, on purpose:
``tests/specify_cli/saas_client/test_decision_widen_ownership_3111.py``.

**SC-002 clause (c) is two-sided and the two sides live in two modules.** The
*refuse* half — no positive hit **AND** at least one unreadable ledger ⇒ refuse —
is here. The *must-not-veto* half — unreadable ledger under X together with a
positive hit under Y ⇒ the normal single request — is in the acceptance module,
because only there can "a single request" be observed. **Neither half discharges
the other.** ``test_unreadable_ledger_does_not_veto_a_hit_elsewhere`` below is a
unit-level mirror of the must-not-veto half, not a substitute for it.
"""

from __future__ import annotations

import ast
import json
import os
from kernel.clock import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from specify_cli.decisions import ownership as ownership_module
from specify_cli.decisions import store
from specify_cli.decisions.ownership import (
    DecisionOwnership,
    is_well_formed_decision_id,
    ownership_refusal,
    resolve_decision_ownership,
)


pytestmark = [pytest.mark.unit, pytest.mark.fast]


# Well-formed 26-character Crockford-base32 ULIDs (no I, L, O, U).
DECISION_OWNED = "01KZWDENANSWER000000000001"
DECISION_ABSENT = "01KZWDENABSENT000000000002"

#: The fixture's mission count, written as a named integer so the SC-018
#: enumeration assertion pins a **stated non-zero** call count. ``assert calls``
#: would be satisfied by one call, and a zero-call green is exactly what a
#: refactor that stops consulting the ledger produces.
EXPECTED_MISSION_COUNT = 3


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _entry(decision_id: str, slug: str) -> dict[str, Any]:
    mission_id = "01KZMISSION0000000000000ZA"
    return {
        "decision_id": decision_id,
        "origin_flow": "plan",
        "step_id": "step-1",
        "input_key": "key",
        "question": "q?",
        "status": "open",
        "created_at": datetime(2026, 1, 1, tzinfo=UTC).isoformat(),
        "mission_id": mission_id,
        "mission_slug": slug,
    }


def write_ledger(repo_root: Path, slug: str, *decision_ids: str) -> Path:
    """Write ``kitty-specs/<slug>/decisions/index.json`` and return the mission dir."""
    mission_dir = repo_root / "kitty-specs" / slug
    decisions = mission_dir / "decisions"
    decisions.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "mission_id": "01KZMISSION0000000000000ZA",
        "entries": [_entry(d, slug) for d in decision_ids],
    }
    (decisions / "index.json").write_text(json.dumps(payload), encoding="utf-8")
    return mission_dir


def write_mission_without_ledger(repo_root: Path, slug: str) -> Path:
    """A mission directory carrying no ``decisions/index.json`` at all."""
    mission_dir = repo_root / "kitty-specs" / slug
    mission_dir.mkdir(parents=True, exist_ok=True)
    return mission_dir


def mode_bits_enforced(probe: Path) -> bool:
    """Return ``True`` when the process is actually denied by the mode bits.

    **Skip honestly.** Running as root, or on a filesystem that ignores mode
    bits, makes a ``0o000`` test pass while exercising nothing — the vacuous
    case, and it applies to the directory shape exactly as much as to the file
    shape.
    """
    try:
        with probe.open("rb"):
            pass
    except OSError:
        return True
    return False


# ---------------------------------------------------------------------------
# Positive control, and the plain refusal
# ---------------------------------------------------------------------------


def test_positive_control_a_checkout_owns_its_own_decision(tmp_path: Path) -> None:
    """POSITIVE CONTROL — it must pass, or every refusal below proves nothing."""
    write_ledger(tmp_path, "mission-alpha", DECISION_OWNED)

    outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)

    assert outcome.owned is True
    assert outcome.owning_mission_slug == "mission-alpha"
    assert outcome.has_unreadable_ledger is False
    assert ownership_refusal(outcome) is None, "a hit must PERMIT; only None is permission"


def test_outcome_is_an_explicit_verdict_not_a_bare_bool(tmp_path: Path) -> None:
    """C-009: the verdict carries the acting root and what was searched, and names no project B."""
    write_ledger(tmp_path, "mission-alpha", DECISION_OWNED)

    outcome = resolve_decision_ownership(tmp_path, DECISION_ABSENT)

    assert isinstance(outcome, DecisionOwnership)
    assert outcome.repo_root == tmp_path.resolve()
    assert outcome.missions_searched == ("mission-alpha",)
    assert outcome.owning_mission_slug is None, (
        "the search answers owns-it / not-established — it can never identify project B"
    )


def test_refusal_names_the_operator_action(tmp_path: Path) -> None:
    """SC-002 (b): the refusal names the acting root, the missions searched, and `git pull`."""
    write_ledger(tmp_path, "mission-alpha", DECISION_OWNED)

    refusal = ownership_refusal(resolve_decision_ownership(tmp_path, DECISION_ABSENT))

    assert refusal is not None
    assert str(tmp_path.resolve()) in refusal
    assert "mission-alpha" in refusal
    assert "git pull" in refusal
    assert DECISION_ABSENT in refusal


def test_no_kitty_specs_at_all_still_refuses(tmp_path: Path) -> None:
    """THE FORBIDDEN REPAIR, pinned.

    "No ledger anywhere, so allow it" is the fall-through this fix exists to
    close, reached from a different direction — and it would green eight tests in
    ``test_decision_widen_subcommand.py`` in one line. A checkout with no
    ``kitty-specs/`` owns nothing.
    """
    outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)

    assert outcome.owned is False
    assert outcome.missions_searched == ()
    assert ownership_refusal(outcome) is not None


# ---------------------------------------------------------------------------
# MISSING vs MALFORMED vs UNREADABLE — three different things
# ---------------------------------------------------------------------------


def test_missing_ledger_is_a_mission_that_owns_nothing_not_an_unreadable_one(
    tmp_path: Path,
) -> None:
    """A missing ``index.json`` sets **no** unreadable flag; the search moves on."""
    write_mission_without_ledger(tmp_path, "mission-empty")
    write_ledger(tmp_path, "mission-zeta", DECISION_OWNED)

    outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)

    assert outcome.owned is True
    assert "mission-empty" in outcome.missions_searched
    assert outcome.unreadable_ledgers == (), (
        "missing != unreadable: lumping them would make an ordinary mission "
        "look like a corruption and would arm the refuse half of clause (c)"
    )


def test_malformed_json_ledger_is_unreadable(tmp_path: Path) -> None:
    """``json.JSONDecodeError`` out of ``json.loads`` ⇒ not established, flag set."""
    mission = write_ledger(tmp_path, "mission-bad", DECISION_OWNED)
    store.index_path(mission).write_text("{not json", encoding="utf-8")

    outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)

    assert outcome.owned is False
    assert outcome.unreadable_ledgers == ("mission-bad",)


def test_schema_invalid_ledger_is_unreadable(tmp_path: Path) -> None:
    """pydantic ``ValidationError`` out of ``model_validate`` ⇒ not established, flag set."""
    mission = write_ledger(tmp_path, "mission-bad", DECISION_OWNED)
    store.index_path(mission).write_text(
        json.dumps({"version": 1, "mission_id": "x", "entries": [{"nope": 1}]}),
        encoding="utf-8",
    )

    outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)

    assert outcome.owned is False
    assert outcome.unreadable_ledgers == ("mission-bad",)


# ---------------------------------------------------------------------------
# SC-014 [standing] — the unreadable-ledger test, in the DIRECTORY shape
# ---------------------------------------------------------------------------


def test_unreadable_decisions_directory_yields_not_established_with_the_flag(
    tmp_path: Path,
) -> None:
    """SC-014 + SC-002 (c) REFUSE half: ``decisions/`` at ``0o000``.

    **The directory, not the file.** ``stat(2)`` needs *search* permission on the
    parent, not read permission on the file — POSIX, not an interpreter quirk —
    so the file shape yields the SAME answer on every interpreter and a test
    built on it proves nothing while appearing to discharge the portability
    requirement.

    **What is asserted is ``resolve_decision_ownership``'s OUTCOME**, never
    ``Path.exists()``'s return value: a ``Path.exists()`` characterization test
    passes identically whether or not ``ownership.py`` carries its ``except
    OSError``, i.e. it cannot red on the one regression this whole branch exists
    to catch.

    Why the branch exists — measured in this clone, non-root euid, **through
    ``load_index`` itself**, control first::

                              3.11.15            3.12.13            3.14.4
        CONTROL readable      1 entry, hit       1 entry, hit       1 entry, hit
        file=0o000            PermissionError    PermissionError    PermissionError
        decisions/=0o000      PermissionError    PermissionError    OK, 0 entries

    On **both CI interpreters** a permission-denied ledger raises out of
    ``load_index`` uncaught. ``ownership.py`` therefore probes readability
    explicitly instead of leaning on ``load_index``'s ``Path.exists()``, which is
    why this assertion holds on all three — and why removing the probe reds this
    test on **every** interpreter rather than only on CI.
    """
    mission = write_ledger(tmp_path, "mission-locked", DECISION_OWNED)
    decisions = store.decisions_dir(mission)
    index_file = store.index_path(mission)
    os.chmod(decisions, 0o000)
    try:
        if not mode_bits_enforced(index_file):
            pytest.skip(
                "SKIPPED HONESTLY, not passed: this process can read through a "
                "0o000 directory (running as root, or a filesystem that ignores "
                "mode bits), so the unreadable branch cannot be constructed here."
            )

        outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)
    finally:
        os.chmod(decisions, 0o755)

    assert outcome.owned is False, "an unreadable ledger cannot establish ownership"
    assert outcome.has_unreadable_ledger is True
    assert outcome.unreadable_ledgers == ("mission-locked",)
    # SC-002 clause (c), REFUSE half: no positive hit AND at least one unreadable
    # ledger ⇒ refuse, and the refusal says which ledger could not answer.
    refusal = ownership_refusal(outcome)
    assert refusal is not None
    assert "mission-locked" in refusal
    assert "could not be read or parsed" in refusal


def test_unreadable_index_file_is_also_handled(tmp_path: Path) -> None:
    """COMPANION CASE, and it is labelled.

    This asserts that the ``OSError`` handling covers a failure of the **read**
    (``read_text`` at ``store.py:66``) as well as of the ``exists()`` probe. It is
    **explicitly NOT the version-divergent path** — with ``file=0o000`` the answer
    is identical on 3.11, 3.12 and 3.14 (measured) — and it **must not** be
    offered as NFR-006 evidence. The directory-shape test above is the only one
    that carries that.
    """
    mission = write_ledger(tmp_path, "mission-locked-file", DECISION_OWNED)
    index_file = store.index_path(mission)
    os.chmod(index_file, 0o000)
    try:
        if not mode_bits_enforced(index_file):
            pytest.skip(
                "SKIPPED HONESTLY, not passed: this process can read a 0o000 file."
            )
        outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)
    finally:
        os.chmod(index_file, 0o644)

    assert outcome.owned is False
    assert outcome.unreadable_ledgers == ("mission-locked-file",)


def test_unreadable_ledger_does_not_veto_a_hit_elsewhere(tmp_path: Path) -> None:
    """The must-not-veto rule at unit level (the BINDING assertion is in the acceptance module).

    Mission ``x`` sorts before mission ``y``, so the unreadable ledger is
    genuinely traversed before the hit — an ordering that would let a naive
    "refuse on any unreadable index" implementation win.
    """
    mission_x = write_ledger(tmp_path, "mission-x-corrupt", DECISION_ABSENT)
    store.index_path(mission_x).write_text("{not json", encoding="utf-8")
    write_ledger(tmp_path, "mission-y-owner", DECISION_OWNED)

    outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)

    assert outcome.owned is True, (
        "an unreadable ledger in a mission that is NOT the answer must never veto "
        "a positive membership hit elsewhere — measured: 49 ledgers across 333 "
        "mission dirs in this repository, so an unrelated corrupt file is not theoretical"
    )
    assert outcome.owning_mission_slug == "mission-y-owner"
    assert outcome.unreadable_ledgers == ("mission-x-corrupt",)
    assert ownership_refusal(outcome) is None


# ---------------------------------------------------------------------------
# SC-018 — the enumeration equality (FR-021 discharge (ii))
# ---------------------------------------------------------------------------


def test_every_path_fed_to_load_index_is_a_member_of_the_globs_own_result_set(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SC-018 under discharge (ii) — containment holds by construction, so this is the substitute.

    **ANTI-VACUITY.** "Every path fed to ``load_index`` is a member of the glob's
    result set" is trivially satisfiable by re-deriving both sides from one
    helper: compare a list to itself and it holds for any implementation,
    including one that never calls ``load_index`` at all. So the two sides come
    from **different sources** — the expected set from this module's own glob, the
    observed set from a **recording spy on the real callee**
    ``specify_cli.decisions.store.load_index`` — and the call count is pinned to a
    **stated non-zero integer**. ``assert calls`` would be satisfied by one call,
    and a zero-call green is exactly what a refactor that stops consulting the
    ledger produces.
    """
    for name in ("mission-a", "mission-b", "mission-c"):
        write_ledger(tmp_path, name, DECISION_OWNED if name == "mission-c" else DECISION_ABSENT)

    recorded: list[Path] = []
    real_load_index = store.load_index

    def _spy(mission_dir: Path):  # type: ignore[no-untyped-def]
        recorded.append(mission_dir)
        return real_load_index(mission_dir)

    monkeypatch.setattr(store, "load_index", _spy)

    # Drive the real derivation, on a decision that is absent from the first two
    # missions, so every mission directory is actually visited.
    outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)
    assert outcome.owned is True

    # Expected set: this module's OWN glob, written independently of the
    # implementation's helper. One level, and the depth is pinned by the separate
    # test below.
    globbed = {p.resolve() for p in (tmp_path / "kitty-specs").glob("*") if p.is_dir()}

    assert len(recorded) == EXPECTED_MISSION_COUNT, (
        f"expected exactly {EXPECTED_MISSION_COUNT} ledger consultations, got "
        f"{len(recorded)} — a zero or short count means the derivation stopped "
        f"consulting the ledger, which is the vacuous green this assertion exists to catch"
    )
    assert {p.resolve() for p in recorded} <= globbed, (
        f"a path outside the glob's own result set reached load_index: "
        f"{[str(p) for p in recorded]} vs {[str(p) for p in sorted(globbed)]}"
    )


def test_glob_depth_is_one_level(tmp_path: Path) -> None:
    """The one-level depth is an assumption held by MEASUREMENT, so it is pinned.

    Measured in this repository: a one-level enumeration and a repo-wide
    ``rglob`` both find **49** ledgers across **333** mission directories, with
    **0** missed. A ledger nested one level deeper is therefore *not* searched,
    and this test is what tells a future reader that the shape changed.
    """
    nested = tmp_path / "kitty-specs" / "group" / "mission-nested" / "decisions"
    nested.mkdir(parents=True)
    (nested / "index.json").write_text(
        json.dumps(
            {
                "version": 1,
                "mission_id": "01KZMISSION0000000000000ZA",
                "entries": [_entry(DECISION_OWNED, "mission-nested")],
            }
        ),
        encoding="utf-8",
    )

    outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)

    assert outcome.owned is False
    assert outcome.missions_searched == ("group",)


def test_symlinked_mission_directory_pointing_outside_is_excluded(tmp_path: Path) -> None:
    """Candidates are ``.resolve()``d BEFORE the containment test.

    ``Path.glob`` follows a symlinked mission directory, and ``is_relative_to`` on
    the *unresolved* path answers ``True`` for a link that leaves the checkout.
    Measured: **0** symlinks under ``kitty-specs/`` today — held by measurement,
    not by construction, which is why it is pinned.
    """
    outside = tmp_path / "elsewhere" / "mission-outside"
    (outside / "decisions").mkdir(parents=True)
    (outside / "decisions" / "index.json").write_text(
        json.dumps(
            {
                "version": 1,
                "mission_id": "01KZMISSION0000000000000ZA",
                "entries": [_entry(DECISION_OWNED, "mission-outside")],
            }
        ),
        encoding="utf-8",
    )
    specs = tmp_path / "kitty-specs"
    specs.mkdir()
    (specs / "mission-link").symlink_to(outside, target_is_directory=True)

    outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)

    assert outcome.owned is False
    assert outcome.missions_searched == ()


# ---------------------------------------------------------------------------
# FR-003 — the slug narrows WITHIN the checkout, it never redirects
# ---------------------------------------------------------------------------


def test_mission_slug_narrows_within_the_checkout(tmp_path: Path) -> None:
    write_ledger(tmp_path, "mission-alpha", DECISION_OWNED)
    write_ledger(tmp_path, "mission-beta", DECISION_ABSENT)

    assert resolve_decision_ownership(
        tmp_path, DECISION_OWNED, mission_slug="mission-alpha"
    ).owned is True
    assert resolve_decision_ownership(
        tmp_path, DECISION_OWNED, mission_slug="mission-beta"
    ).owned is False


def test_slug_naming_a_mission_this_checkout_lacks_is_an_ownership_failure(
    tmp_path: Path,
) -> None:
    """Not a redirection. The slug selects among the missions already enumerated."""
    write_ledger(tmp_path, "mission-alpha", DECISION_OWNED)

    outcome = resolve_decision_ownership(
        tmp_path, DECISION_OWNED, mission_slug="mission-owned-by-someone-else"
    )

    assert outcome.owned is False
    assert outcome.missions_searched == ()


# ---------------------------------------------------------------------------
# FR-005 — the shape check reuses ONE existing regex (Q7)
# ---------------------------------------------------------------------------


def test_shape_check_rejects_non_crockford_and_wrong_length() -> None:
    assert is_well_formed_decision_id(DECISION_OWNED) is True
    # 22 chars, and contains `I` — the shape the pre-existing widen fixture used.
    assert is_well_formed_decision_id("01KWIDETEST00000000001") is False
    assert is_well_formed_decision_id("01KZWDENANSWER00000000000I") is False
    assert is_well_formed_decision_id("") is False


def test_the_shape_check_reuses_an_existing_ulid_regex_rather_than_adding_a_fourth() -> None:
    """Q7, made executable: the CLI binds the SAME compiled pattern, not a copy."""
    from specify_cli.decisions import ownership
    from specify_cli.invocation import record

    assert ownership.ULID_RE is record._ULID_RE


# ---------------------------------------------------------------------------
# SC-018 — the seam's own shape
# ---------------------------------------------------------------------------


def test_the_derivation_lives_outside_cli_commands_and_is_importable_by_name() -> None:
    """SC-018: a single named function, in a stated module, outside ``cli/commands/**``.

    This module is the non-CLI caller the criterion requires; the import at the
    top of the file is the assertion's real subject.
    """
    from specify_cli.decisions import ownership

    assert ownership.__name__ == "specify_cli.decisions.ownership"
    assert "cli.commands" not in ownership.__name__
    assert callable(ownership.resolve_decision_ownership)
    assert "resolve_decision_ownership" in ownership.__all__


# ---------------------------------------------------------------------------
# The specs-root listability probe (review HIGH-1 / BLOCKER-2).
#
# These exist because the branch they cover shipped once with NO test: deleting
# the probe entirely left this module green at 18 passed. Ad-hoc shell
# measurement is how you FIND the answer; a committed test is how you KEEP it —
# which is exactly why SC-014 makes the analogous per-ledger branch a [standing]
# obligation rather than a plan-phase judgement.
# ---------------------------------------------------------------------------


def test_unreadable_specs_root_is_flagged_not_reported_as_empty(tmp_path: Path) -> None:
    """An unlistable ``kitty-specs/`` is *could not look*, never *found nothing*.

    ``Path.glob`` SWALLOWS EACCES and returns ``[]`` on every interpreter, so the
    obvious `except OSError` around the glob is unreachable and this case would
    silently read as an empty checkout — sending the operator to ``git pull`` for
    a permission denial.
    """
    specs = tmp_path / "kitty-specs"
    specs.mkdir()
    # Probe must be a FILE inside the locked directory and read AFTER the chmod.
    # `mode_bits_enforced` opens its argument: on a DIRECTORY that always raises
    # IsADirectoryError (an OSError), so the helper is constant True and the
    # guard cannot fire — it would RED as root instead of skipping honestly.
    canary = specs / "canary"
    canary.write_text("{}", encoding="utf-8")
    os.chmod(specs, 0o000)
    try:
        if not mode_bits_enforced(canary):
            pytest.skip(
            "SKIPPED HONESTLY, not passed: this process can read through a "
            "0o000 directory (running as root, or a filesystem that ignores "
            "mode bits), so the branch cannot be constructed here."
        )
        outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)
    finally:
        os.chmod(specs, 0o700)

    assert outcome.owned is False, "an unlistable specs root must never permit"
    assert outcome.unreadable_ledgers == ("kitty-specs",), (
        "the specs root was unlistable and must be FLAGGED; reporting it as "
        f"'no missions found' misdiagnoses a permission denial: {outcome!r}"
    )
    # LOW-7's PAIRED CONTROL, and it lives here rather than in a test of its own
    # because the property is a DISCRIMINATION between two messages and half a
    # discrimination proves nothing. This row is the permission-shaped one: it
    # must keep the permission diagnosis and must NOT drift onto LOW-7's
    # shape-shaped prose. `test_kitty_specs_that_is_a_regular_file_is_a_shape_error`
    # asserts the exact converse of both lines.
    assert outcome.specs_root_fault == "unlistable", (
        f"EACCES on the specs root is the 'unlistable' fault, not a shape error: {outcome!r}"
    )
    refusal = ownership_refusal(outcome)
    assert refusal is not None
    assert "PERMISSION problem" in refusal, (
        f"an EACCES specs root must still be diagnosed as a permission problem: {refusal}"
    )
    assert "is not a directory" not in refusal, (
        f"an unlistable DIRECTORY must not be reported as the wrong kind of object: {refusal}"
    )


def test_unreadable_ANCESTOR_of_specs_root_refuses_without_raising(tmp_path: Path) -> None:
    """REGRESSION TEST — this is the one that reds on 3.11/3.12 without the fix.

    An earlier form guarded the probe with ``if specs_root.exists():``. That is
    the same EACCES-divergent call this module's header exists to warn about,
    reintroduced one level up: when an **ancestor** of ``kitty-specs/`` is
    unreadable, ``stat(2)`` fails and ``exists()`` RAISES on both CI
    interpreters, so ``cmd_widen`` produced a traceback instead of a refusal —
    R3 verbatim, green locally on 3.14 and broken on CI.

    Reachable without exotic setup: ``SPECIFY_REPO_ROOT`` is operator-supplied
    and is the highest-priority tier of ``locate_project_root``.
    """
    repo_root = tmp_path / "checkout"
    (repo_root / "kitty-specs").mkdir(parents=True)
    canary = repo_root / "canary"
    canary.write_text("{}", encoding="utf-8")
    os.chmod(repo_root, 0o000)
    try:
        if not mode_bits_enforced(canary):
            pytest.skip(
            "SKIPPED HONESTLY, not passed: this process can read through a "
            "0o000 directory (running as root, or a filesystem that ignores "
            "mode bits), so the branch cannot be constructed here."
        )
        # Must not raise. The assertion is the absence of an escaping OSError as
        # much as the verdict itself.
        outcome = resolve_decision_ownership(repo_root, DECISION_OWNED)
    finally:
        os.chmod(repo_root, 0o700)

    assert outcome.owned is False
    assert outcome.unreadable_ledgers == ("kitty-specs",), (
        "an unreadable ancestor must yield a flagged refusal, not a traceback "
        f"and not a silent empty search: {outcome!r}"
    )


def test_probe_does_not_over_fire_on_a_readable_empty_specs_root(tmp_path: Path) -> None:
    """DO-NOT-OVER-FIRE CONTROL. Without this the two tests above are satisfiable
    by a probe that flags everything, which would refuse every widen invocation
    on a checkout that simply has no missions yet."""
    (tmp_path / "kitty-specs").mkdir()

    outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)

    assert outcome.owned is False, "an empty checkout owns nothing"
    assert outcome.unreadable_ledgers == (), (
        "a readable, empty specs root is MISSING-shaped, not unreadable-shaped; "
        f"flagging it would conflate the two: {outcome!r}"
    )


def test_symlinked_SPECS_ROOT_pointing_outside_is_refused(tmp_path: Path) -> None:
    """HIGH-2 — the containment check one level UP from the mission directories.

    ``test_symlinked_mission_directory_pointing_outside_is_excluded`` pins the
    mission-directory case. This pins the case nobody asked about: ``kitty-specs``
    **itself** being a symlink out of the acting root.

    ``.resolve()`` follows it, and every downstream ``is_relative_to(specs_root)``
    is then measured against the RESOLVED target — so containment held trivially
    and the search read another checkout's ledgers as if they were ours. Measured
    end-to-end before the fix: the command exited 0 and put the other checkout's
    ``decision_id`` on the wire under this checkout's token. The spec's symlink
    survey measured "0 symlinks UNDER kitty-specs/", which is a different question.
    """
    other = tmp_path / "other-checkout"
    write_ledger(other, "mission-of-other-project", DECISION_OWNED)

    acting = tmp_path / "acting-checkout"
    acting.mkdir()
    (acting / "kitty-specs").symlink_to(other / "kitty-specs", target_is_directory=True)

    outcome = resolve_decision_ownership(acting, DECISION_OWNED)

    assert outcome.owned is False, (
        "a kitty-specs/ symlinked OUT of the acting root must not confer "
        f"ownership of the target checkout's decisions: {outcome!r}"
    )
    assert ownership_refusal(outcome) is not None, "and it must refuse"


def test_symlinked_specs_root_INSIDE_the_root_still_works(tmp_path: Path) -> None:
    """DO-NOT-OVER-FIRE CONTROL for the test above.

    Without this, HIGH-2's guard is satisfiable by refusing every symlink, which
    would break a monorepo that links ``kitty-specs`` to a sibling **inside** the
    checkout. Containment, not symlink-phobia, is the property.
    """
    root = tmp_path / "checkout"
    real = root / "nested" / "specs-home"
    (real).mkdir(parents=True)
    write_ledger(real.parent, "mission-inside", DECISION_OWNED)
    (root / "kitty-specs").symlink_to(real.parent / "kitty-specs", target_is_directory=True)

    outcome = resolve_decision_ownership(root, DECISION_OWNED)

    assert outcome.owned is True, (
        "a kitty-specs/ symlink that stays WITHIN the acting root is a legitimate "
        f"layout and must still resolve ownership: {outcome!r}"
    )


def test_mission_symlink_into_an_unsearchable_location_refuses_without_raising(
    tmp_path: Path,
) -> None:
    """HIGH-3 — ``Path.is_dir()`` is the third instance of the EACCES trap.

    ``is_dir()`` calls ``stat()`` and, like ``exists()``, does not ignore EACCES
    on 3.11/3.12. A mission directory symlinked into a location the process
    cannot search made it RAISE out of ``_mission_dirs`` on both CI interpreters
    while 3.14 returned cleanly — R3 verbatim, and invisible to a local run.

    An unstattable candidate cannot answer the ownership question, so skipping it
    is fail-closed: it can only remove a mission from the search, never add one.
    """
    vault = tmp_path / "vault"
    (vault / "m-target" / "decisions").mkdir(parents=True)
    root = tmp_path / "checkout"
    (root / "kitty-specs").mkdir(parents=True)
    (root / "kitty-specs" / "m-link").symlink_to(vault / "m-target", target_is_directory=True)

    canary = vault / "canary"
    canary.write_text("{}", encoding="utf-8")
    os.chmod(vault, 0o000)
    try:
        if not mode_bits_enforced(canary):
            pytest.skip(
                "SKIPPED HONESTLY, not passed: this process can stat through a "
                "0o000 directory (running as root, or a filesystem that ignores "
                "mode bits), so the branch cannot be constructed here."
            )
        # The assertion is the ABSENCE of an escaping OSError as much as the verdict.
        outcome = resolve_decision_ownership(root, DECISION_OWNED)
    finally:
        os.chmod(vault, 0o700)

    assert outcome.owned is False
    assert ownership_refusal(outcome) is not None


# ---------------------------------------------------------------------------
# MEDIUM-4 — containment at the file actually opened, two levels below the
# mission directory `_mission_dirs` checks. Same outcome as the specs-root case
# above; a different depth. FR-021: proved to lie under the acting root BEFORE
# its index is consulted.
# ---------------------------------------------------------------------------


def test_symlinked_DECISIONS_DIR_pointing_outside_is_refused(tmp_path: Path) -> None:
    """`<mission>/decisions/` linked out of the checkout must not confer ownership.

    Measured before the fix: ``owned=True`` and the other project's
    ``decision_id`` on the wire under this checkout's token. The
    mission-directory containment check cannot see this — the mission dir is
    genuinely local; only the ledger beneath it is foreign.
    """
    other = tmp_path / "other-checkout"
    other_mission = write_ledger(other, "mission-of-other-project", DECISION_OWNED)

    acting = tmp_path / "acting-checkout"
    mine = acting / "kitty-specs" / "mission-mine"
    mine.mkdir(parents=True)
    (mine / "decisions").symlink_to(other_mission / "decisions", target_is_directory=True)

    outcome = resolve_decision_ownership(acting, DECISION_OWNED)

    assert outcome.owned is False, f"an out-of-root ledger must not own: {outcome!r}"
    assert outcome.unreadable_ledgers == ("mission-mine",), (
        "an out-of-root ledger is UNREADABLE-shaped, not MISSING-shaped: it "
        "exists but cannot answer for THIS checkout, so it must not be silently "
        f"skipped: {outcome!r}"
    )


def test_symlinked_index_json_pointing_outside_is_refused(tmp_path: Path) -> None:
    """The same hole one level deeper still: the ledger FILE itself linked out."""
    other = tmp_path / "other-checkout"
    other_mission = write_ledger(other, "mission-of-other-project", DECISION_OWNED)

    acting = tmp_path / "acting-checkout"
    decisions = acting / "kitty-specs" / "mission-mine" / "decisions"
    decisions.mkdir(parents=True)
    (decisions / "index.json").symlink_to(other_mission / "decisions" / "index.json")

    outcome = resolve_decision_ownership(acting, DECISION_OWNED)

    assert outcome.owned is False, f"an out-of-root ledger file must not own: {outcome!r}"
    assert outcome.unreadable_ledgers == ("mission-mine",)


def test_symlinked_decisions_dir_INSIDE_the_root_still_works(tmp_path: Path) -> None:
    """DO-NOT-OVER-FIRE CONTROL for the two tests above.

    Containment is measured against the **acting root**, not the mission
    directory, so a layout that links ``decisions/`` elsewhere *within* the
    checkout keeps working. Without this control the guard is satisfiable by
    refusing every symlinked ledger.
    """
    root = tmp_path / "checkout"
    real_mission = write_ledger(root, "mission-real", DECISION_OWNED)
    alias = root / "kitty-specs" / "mission-alias"
    alias.mkdir(parents=True)
    (alias / "decisions").symlink_to(real_mission / "decisions", target_is_directory=True)

    outcome = resolve_decision_ownership(root, DECISION_OWNED)

    assert outcome.owned is True, (
        "a decisions/ symlink that stays WITHIN the acting root is a legitimate "
        f"layout and must still resolve ownership: {outcome!r}"
    )
    # ANTI-VACUITY, and this line is the whole control.
    #
    # `mission-real` is inside the search space, so under a symlink-phobic
    # implementation the alias is refused, the search falls through to
    # `mission-real`, and `owned` is STILL True — the assertion above passes
    # while the property it guards is broken. Measured: unmutated the answer is
    # 'mission-alias'; symlink-phobic it is 'mission-real', and without this line
    # the test cannot tell the two apart.
    #
    # Same short-circuit-by-another-mission shape as the vacuous must-not-veto
    # test this module's own review found. Assert WHICH mission answered, not
    # merely that one did.
    assert outcome.owning_mission_slug == "mission-alias", (
        "the ALIASED mission must be the one that answered. A different mission "
        "answering means this control cannot distinguish containment from blanket "
        f"symlink refusal, which is what it exists to distinguish: {outcome!r}"
    )


# ---------------------------------------------------------------------------
# LOW-7 — a shape error is not a permission error
# ---------------------------------------------------------------------------


def test_kitty_specs_that_is_a_regular_file_is_a_shape_error_not_a_permission_error(
    tmp_path: Path,
) -> None:
    """``NotADirectoryError`` is an ``OSError``, so this took the EACCES branch.

    Measured before the fix, this clone, non-root euid: with ``kitty-specs`` a
    regular file the outcome was ``unreadable_ledgers=('kitty-specs',)`` and the
    refusal said *"This is a PERMISSION problem … `chmod u+rx`"*. Fail-closed and
    right in **verdict**, confidently wrong in **cause** — and that is worse prose
    than before LOW-6 was fixed, because it asserts a wrong diagnosis rather than
    merely omitting the right one. No mode bit on a regular file will ever make it
    enumerable.

    **The verdict half is asserted first and separately from the prose half.** A
    message test that did not also pin ``owned is False`` could be greened by an
    implementation that produced beautiful prose and permitted the send.

    Re-measured after the fix on both CI interpreters, same answer on each::

                              3.11.15               3.12.13
        raw iterdir() on it   NotADirectoryError    NotADirectoryError
        fault                 not-a-directory       not-a-directory
        refusal cause         SHAPE                 SHAPE

    so this is not a 3.11-only nicety. Note the requirement this test also
    encodes by *not* doing it: the fix must not reach for ``Path.exists()`` or
    ``Path.is_dir()`` on the specs root. Those calls are EACCES-divergent and this
    module has had to remove one three times; ``NotADirectoryError`` is a distinct
    exception class and costs no extra stat.
    """
    (tmp_path / "kitty-specs").write_text("I am a file, not a directory", encoding="utf-8")

    outcome = resolve_decision_ownership(tmp_path, DECISION_OWNED)

    # Verdict: unchanged, and still fail-closed.
    assert outcome.owned is False, "a kitty-specs of the wrong shape must never permit"
    assert outcome.missions_searched == ()
    # Cause: recorded as its own fault, not lumped with EACCES.
    assert outcome.specs_root_fault == "not-a-directory", (
        f"a non-directory kitty-specs is a SHAPE fault, not an EACCES one: {outcome!r}"
    )
    assert outcome.unreadable_ledgers == ("kitty-specs",), (
        "it still could not answer, so the flag stays set — the fix separates the "
        f"CAUSE from the flag, it does not drop the flag: {outcome!r}"
    )

    refusal = ownership_refusal(outcome)
    assert refusal is not None, "and it must refuse"
    assert "is not a directory" in refusal, (
        f"the refusal must name the real cause — the wrong kind of object: {refusal}"
    )
    # The converse of the paired control in
    # `test_unreadable_specs_root_is_flagged_not_reported_as_empty`. Asserting the
    # absence of the permission prose is the whole point of LOW-7: the pre-fix
    # message contained exactly this phrase, which is what establishes that this
    # absence would otherwise have happened.
    assert "PERMISSION problem" not in refusal, (
        f"a shape error must not be diagnosed as a permission problem: {refusal}"
    )
    # `chmod u+rx`, the permission branch's *instruction* — not the bare word
    # `chmod`. A first cut asserted the bare word and red on the message's own
    # "neither `chmod` nor `git pull` will fix it", which is the message
    # PREEMPTING the wrong action and is exactly what LOW-7 wants. The contract is
    # "does not INSTRUCT a chmod", so that is what is pinned.
    assert "chmod u+rx" not in refusal, (
        f"`chmod` cannot fix an object of the wrong kind and must not be offered "
        f"as the remedy: {refusal}"
    )
    assert "neither `chmod` nor `git pull` will fix it" in refusal, (
        "and the two wrong actions must be ruled OUT by name: an operator holding "
        "this refusal has already been told `chmod u+rx` (LOW-6's branch) and "
        f"`git pull` (the generic branch) for other causes: {refusal}"
    )


# ---------------------------------------------------------------------------
# LOW-8 — an unstattable mission candidate is skipped, but not in silence
# ---------------------------------------------------------------------------


def test_unstattable_mission_candidate_is_flagged_not_reported_as_no_missions(
    tmp_path: Path,
) -> None:
    """HIGH-3 skipped it correctly and **silently**; the silence was the defect.

    Measured before the fix: an unstattable mission symlink with no other mission
    yielded ``unreadable_ledgers=()``, so the refusal told the operator *"no
    missions were found … run `git pull`"* for a permission problem — the same
    missing-vs-unreadable conflation this module fixed one level down (per-ledger)
    and one level up (the specs root, LOW-6), at the one level that was left.

    ``m-link`` is the **only** candidate here, deliberately: with any readable
    mission alongside it the refusal would name that mission and the sentence
    under test would not be reachable.
    """
    vault = tmp_path / "vault"
    (vault / "m-target" / "decisions").mkdir(parents=True)
    root = tmp_path / "checkout"
    (root / "kitty-specs").mkdir(parents=True)
    (root / "kitty-specs" / "m-link").symlink_to(vault / "m-target", target_is_directory=True)

    # Probe must be a FILE inside the locked directory, read AFTER the chmod — on
    # a directory `mode_bits_enforced` is constant True (IsADirectoryError is an
    # OSError) and the guard could not fire, so it would RED as root instead of
    # skipping honestly. That was a real finding on this mission.
    canary = vault / "canary"
    canary.write_text("{}", encoding="utf-8")
    os.chmod(vault, 0o000)
    try:
        if not mode_bits_enforced(canary):
            pytest.skip(
                "SKIPPED HONESTLY, not passed: this process can stat through a "
                "0o000 directory (running as root, or a filesystem that ignores "
                "mode bits), so the branch cannot be constructed here."
            )
        outcome = resolve_decision_ownership(root, DECISION_OWNED)
        refusal = ownership_refusal(outcome)
    finally:
        os.chmod(vault, 0o700)

    # FAIL-CLOSED, first. The flag must not have turned a skip into a permit.
    assert outcome.owned is False, "an unstattable candidate must never confer ownership"
    assert outcome.missions_searched == (), (
        "it was dropped from the search, which is the fail-closed half and is "
        f"unchanged: a candidate can only ever be removed, never added: {outcome!r}"
    )
    assert outcome.unreadable_ledgers == ("m-link",), (
        "and the drop must be RECORDED: an unstattable mission that leaves no "
        f"trace is indistinguishable from a checkout with no missions: {outcome!r}"
    )
    # This is not a specs-root fault — the specs root listed fine.
    assert outcome.specs_root_fault is None, (
        f"the specs root was listable; only one candidate under it was not: {outcome!r}"
    )

    assert refusal is not None
    assert "m-link" in refusal, "the refusal must name what could not answer"
    assert "no missions were found" not in refusal, (
        "a mission WAS found — it could not be looked at. That sentence is the "
        f"misdiagnosis this residual quotes, verbatim: {refusal}"
    )
    # LOW-1: the remedy must match the diagnosis. `git pull` does not fix a
    # permission denial, and this assertion is what stopped that half of the
    # misdiagnosis surviving unpinned.
    refusal = ownership_refusal(outcome)
    assert refusal is not None
    assert "To fix: run `git pull`" not in refusal, (
        f"a candidate that could not be stat'ed is not a missing checkout: {refusal}"
    )



def test_unstattable_mission_candidate_does_not_veto_a_hit_elsewhere(
    tmp_path: Path,
) -> None:
    """R12's rule, applied to the NEW source of the unreadable flag.

    R12's dedicated control (``test_sc002_clause_c_unreadable_ledger_must_not_veto_a_hit_elsewhere``,
    acceptance module) covers an unreadable *ledger*. LOW-8 adds a **second** way
    for the flag to be set — a dropped mission candidate — and a flag that vetoes
    is exactly the defect R12 exists to catch. Nothing in R12's control exercises
    this source, so it gets its own.

    ``m-link`` sorts before ``mission-owner``, so the unstattable candidate is
    genuinely encountered first.
    """
    vault = tmp_path / "vault"
    (vault / "m-target" / "decisions").mkdir(parents=True)
    root = tmp_path / "checkout"
    write_ledger(root, "mission-owner", DECISION_OWNED)
    (root / "kitty-specs" / "m-link").symlink_to(vault / "m-target", target_is_directory=True)
    assert "m-link" < "mission-owner", "the traversal order this test depends on"

    canary = vault / "canary"
    canary.write_text("{}", encoding="utf-8")
    os.chmod(vault, 0o000)
    try:
        if not mode_bits_enforced(canary):
            pytest.skip(
                "SKIPPED HONESTLY, not passed: this process can stat through a "
                "0o000 directory (running as root, or a filesystem that ignores "
                "mode bits), so the branch cannot be constructed here."
            )
        outcome = resolve_decision_ownership(root, DECISION_OWNED)
    finally:
        os.chmod(vault, 0o700)

    # ANTI-VACUITY, and it comes first: without this line the test passes on an
    # implementation where the flag never fires at all, which is the very state
    # LOW-8 exists to leave behind. "It did not veto" is only meaningful once the
    # thing that could have vetoed is proved to have happened.
    assert outcome.unreadable_ledgers == ("m-link",), (
        f"the unstattable candidate was never flagged, so this test proves "
        f"nothing about not-vetoing: {outcome!r}"
    )
    assert outcome.owned is True, (
        "an unstattable mission candidate must never veto a positive membership "
        f"hit elsewhere — that is R12's rule: {outcome!r}"
    )
    assert outcome.owning_mission_slug == "mission-owner"
    assert ownership_refusal(outcome) is None, "and a hit must still PERMIT"


def _attr_calls(node_tree: ast.AST, names: set[str]) -> list[tuple[int, str]]:
    """Every ``x.<name>()`` call in *node_tree* whose attribute is in *names*."""
    return [
        (n.lineno, n.func.attr)
        for n in ast.walk(node_tree)
        if isinstance(n, ast.Call)
        and isinstance(n.func, ast.Attribute)
        and n.func.attr in names
    ]


def _eacces_offenders(
    tree: ast.AST, banned_anywhere: set[str], banned_unguarded: set[str]
) -> list[tuple[int, str]]:
    """Banned EACCES-divergent probe calls in *tree*, as ``(lineno, attr)``.

    Extracted to module level so the standing guard below and its **paired
    known-bad control** run the identical rule. FU-S is why: the guard's previous
    form was never exercised against the shape it was written to catch, so it could
    pass on the defect while reading as though it covered the family. A rule with no
    control is an assertion about itself.
    """
    guarded = {
        id(n)
        for node in ast.walk(tree)
        if isinstance(node, ast.Try)
        for stmt in node.body
        for n in ast.walk(stmt)
    }
    by_site = {
        (n.lineno, n.func.attr): n
        for n in ast.walk(tree)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
    }
    return [
        (lineno, attr)
        for lineno, attr in _attr_calls(tree, banned_anywhere | banned_unguarded)
        if attr in banned_anywhere or id(by_site[(lineno, attr)]) not in guarded
    ]


def test_ownership_module_has_no_unguarded_eacces_divergent_stat_call() -> None:
    """STANDING GUARD against the trap this module fell into three times.

    ``Path.exists()`` handles ``EACCES`` differently per interpreter — it RAISES on
    3.11/3.12, both CI interpreters, and returns ``False`` on 3.14 — so it ships a
    traceback where a local run is green. This module removed it three times:

    1. ``load_index``'s own ``Path.exists()`` could not express FR-002's unreadable
       branch at all, which is why ``_read_ledger`` probes with ``open()``.
    2. A fix for the specs-root diagnosis guarded its probe with
       ``if specs_root.exists():`` — reintroducing the divergence one level up, so
       an unreadable *ancestor* raised on both CI interpreters.
    3. ``resolved.is_dir()`` is the same ``stat()`` semantics under a different
       name, and escaped uncaught on both CI interpreters for a symlinked mission.

    Three incidents, three reviews, zero gates. This is the gate.

    **An earlier version of this guard pinned only trap 2.** It matched the
    attribute name ``exists`` alone, so trap 3's spelling — and ``stat``,
    ``is_file``, ``is_symlink``, ``lstat``, which share the identical divergence —
    passed it silently, while its own docstring claimed it enforced a try-context
    rule it never implemented. A guard that catches one spelling while reading as
    though it covers the family is worse than no guard. It now covers the family
    and implements the rule.

    **The rule, and it was wrong until #3177.** It used to ban ``exists`` outright
    and permit the rest — ``is_dir`` included — **inside a ``try``**. That is exactly
    no protection, because a ``try`` around a call that does not raise is inert. The
    module shipped ``resolved.is_dir()`` in a ``try`` and this guard was GREEN while
    the defect was live: on 3.14 the predicate returned ``False``, control took the
    bare ``continue``, and the ``except OSError`` beneath it never ran. A guard whose
    docstring reads as though it closed the family, while the family's own worst
    member is permitted by it, is the same failure as the one-spelling version above.

    The split is now on **raise behaviour**, which is the property that matters,
    measured on 3.14.4 through a symlink into a ``0o000`` directory:

    ===============  ==========================
    ``exists``       returns ``False``
    ``is_dir``       returns ``False``
    ``is_file``      returns ``False``
    ``is_symlink``   returns ``False``
    ``stat``         RAISES ``PermissionError``
    ``lstat``        RAISES ``PermissionError``
    ===============  ==========================

    So **every predicate is banned outright** — none of them can express "could not
    look" on 3.14 at all, and a ``try`` around one is effect-free exception handling
    that reads as a handled case while handling nothing. ``stat``/``lstat`` are
    permitted **only inside a ``try``**, because they raise on every interpreter and
    a guarded ``stat`` is how this module legitimately probes.

    Not covered, stated rather than implied: ``getattr(p, "exists")()``, a name
    held in a variable, ``operator.methodcaller``, and a bare imported
    ``os.path.exists``. A guard cannot beat deliberate evasion, and nobody reaches
    for ``getattr`` to stat a path — but the limit belongs in writing, not in a
    reader's assumption.
    """
    #: Split on RAISE BEHAVIOUR, measured — not on which spelling bit us. Every
    #: predicate swallows EACCES on 3.14 and so cannot express "could not look"
    #: under any amount of `try`; `stat`/`lstat` raise everywhere, so a guarded
    #: probe with them is the module's legitimate idiom. See the `stat()` call
    #: site's comment, which carries the four-interpreter table.
    banned_anywhere = {"exists", "is_dir", "is_file", "is_symlink"}
    banned_unguarded = {"stat", "lstat"}

    source = Path(ownership_module.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)

    # ANTI-VACUITY, ANCHORED ON THE SCANNED TREE ITSELF.
    #
    # The previous control parsed a *separate* planted fragment. That proved the
    # walk worked and never proved this file had been read — so repointing
    # `__file__` at an empty file left the guard GREEN. Fifth instance of the
    # vacuous-anti-vacuity-control shape on this mission.
    #
    # `iterdir` is the call this module's docstring makes load-bearing, so it is a
    # content anchor rather than a line number: if it is absent, the wrong file was
    # read (or read empty) and every emptiness result below means nothing.
    iterdir_sites = _attr_calls(tree, {"iterdir"})
    assert iterdir_sites, (
        f"the scanned source ({ownership_module.__file__}) contains no iterdir() "
        "call. This module's listability probe is built on iterdir, so its absence "
        "means the wrong file was read or it was read empty — and an empty result "
        "below would be vacuous rather than clean."
    )

    offenders = _eacces_offenders(tree, banned_anywhere, banned_unguarded)

    assert offenders == [], (
        f"{ownership_module.__file__} makes {len(offenders)} EACCES-divergent "
        f"stat call(s) that this module has banned: {offenders} "
        f"(scanned {len(source.splitlines())} lines, {len(iterdir_sites)} iterdir "
        "anchor(s) found). Every PREDICATE (`exists`, `is_dir`, `is_file`, "
        "`is_symlink`) is banned outright, in a `try` or not: all four return False "
        "on EACCES on 3.14, so they cannot express `could not look` at all and a "
        "`try` around one handles nothing. Use an `open()` probe, `iterdir()` "
        "(FileNotFoundError for absent, OSError for unlistable), or "
        "`S_ISDIR(p.stat().st_mode)`. `stat`/`lstat` are permitted only inside a "
        "`try` — they raise on every interpreter, which is what makes a guarded "
        "probe with them meaningful. #3177 is what this rule now encodes: the "
        "previous form permitted `is_dir` in a `try` and stayed GREEN while that "
        "exact call shipped the defect."
    )


def test_dangling_mission_symlink_is_absent_not_unreadable(tmp_path: Path) -> None:
    """The PAIRED HALF of the #3177 fix — LOW-8's conflation must not run BACKWARDS.

    Replacing ``resolved.is_dir()`` with ``S_ISDIR(resolved.stat().st_mode)`` is what
    makes ``EACCES`` observable. But it also makes the *absence-like* failures RAISE
    where the predicate merely returned ``False`` — and a **dangling** mission symlink
    raises ``ENOENT``. Routed to the same handler, it would be recorded in
    ``unreadable_ledgers`` and the operator would get a *"could not read it"* refusal
    naming something that simply is not there.

    That is exactly LOW-8's missing-vs-unreadable conflation, inverted: the first
    version of the #3177 fix in this branch had it, and it was caught by re-reading
    the hunk rather than by any test — which is why this one exists.

    The discrimination is on errno (``_ABSENT_ERRNOS``), reproducing the set
    ``pathlib._ignore_error`` used through 3.13. Both halves are asserted here, since
    half a discrimination proves nothing — this module's own repeated lesson.
    """
    root = tmp_path / "checkout"
    (root / "kitty-specs").mkdir(parents=True)
    # Target never existed -> stat raises ENOENT through the link.
    (root / "kitty-specs" / "m-dangling").symlink_to(
        tmp_path / "never-existed", target_is_directory=True
    )

    outcome = resolve_decision_ownership(root, DECISION_OWNED)
    refusal = ownership_refusal(outcome)

    # HALF 1 — ABSENT: dropped, and NOT recorded.
    assert outcome.owned is False, "a dangling candidate must never confer ownership"
    assert outcome.unreadable_ledgers == (), (
        "a dangling symlink is ABSENT, not unreadable. Recording it here produces a "
        f"'could not read it' refusal for something that is not there: {outcome!r}"
    )
    assert outcome.specs_root_fault is None, (
        f"the specs root listed fine; only a candidate under it was dangling: {outcome!r}"
    )
    assert refusal is not None
    assert "m-dangling" not in refusal, (
        f"the refusal must not name a candidate that was merely absent: {refusal}"
    )

    # HALF 2 — the CONTROL that stops this test being satisfiable by simply never
    # recording anything. The same shape with EACCES instead of ENOENT MUST record.
    vault = tmp_path / "vault"
    (vault / "m-target").mkdir(parents=True)
    canary = vault / "canary"
    canary.write_text("{}", encoding="utf-8")
    (root / "kitty-specs" / "m-locked").symlink_to(
        vault / "m-target", target_is_directory=True
    )
    os.chmod(vault, 0o000)
    try:
        if not mode_bits_enforced(canary):
            pytest.skip(
                "SKIPPED HONESTLY, not passed: this process can stat through a 0o000 "
                "directory, so the EACCES half of the discrimination cannot be built."
            )
        locked = resolve_decision_ownership(root, DECISION_OWNED)
    finally:
        os.chmod(vault, 0o700)

    assert locked.unreadable_ledgers == ("m-locked",), (
        "EACCES must still be RECORDED — otherwise this test would pass just as well "
        f"against code that records nothing at all, and #3177 would be back: {locked!r}"
    )


def test_eacces_guard_rule_catches_the_shape_that_shipped_the_defect() -> None:
    """FU-S — the PAIRED CONTROL the guard above shipped without, and #3177 is the cost.

    The guard was GREEN while ``ownership.py`` carried ``resolved.is_dir()`` inside a
    ``try``, because its rule permitted the whole family in a ``try`` and a ``try``
    around a call that does not raise handles nothing. A rule that is only ever run
    against source it passes on is an assertion about itself: nothing distinguishes
    "the module is clean" from "the rule cannot see this".

    So the rule is exercised here against four synthetic sources whose verdicts are
    known independently of it — the known-bad cases FIRST, because a control that only
    demonstrates the clean case proves the walk runs and not that it discriminates.

    The interpreter table lives at the ``stat()`` call site in ``ownership.py``. The
    only fact this control needs from it: predicates return ``False`` on EACCES on
    3.14, ``stat``/``lstat`` raise on every interpreter.
    """
    banned_anywhere = {"exists", "is_dir", "is_file", "is_symlink"}
    banned_unguarded = {"stat", "lstat"}

    def offenders(src: str) -> list[str]:
        return [attr for _, attr in _eacces_offenders(ast.parse(src), banned_anywhere, banned_unguarded)]

    # KNOWN-BAD 1 — the exact shape that shipped: a predicate inside a `try`, whose
    # False branch drops silently and never reaches the handler below it.
    assert offenders(
        "try:\n"
        "    if not resolved.is_dir():\n"
        "        pass\n"
        "except OSError:\n"
        "    record()\n"
    ) == ["is_dir"], (
        "the try-wrapped predicate is the FU-Q/#3177 shape and MUST be flagged; if it "
        "is not, this guard has regressed to the form that passed on the live defect"
    )

    # KNOWN-BAD 2 — the rest of the predicate family, same reasoning, also in a `try`.
    for attr in ("exists", "is_file", "is_symlink"):
        assert offenders(f"try:\n    p.{attr}()\nexcept OSError:\n    pass\n") == [attr], (
            f"`{attr}` returns False on EACCES on 3.14 exactly as `is_dir` does, so a "
            "`try` cannot redeem it either"
        )

    # KNOWN-BAD 3 — an UNGUARDED stat. It raises on every interpreter, which is why it
    # is permitted in a `try`; outside one it escapes as a traceback.
    assert offenders("p.stat()\n") == ["stat"], (
        "an unguarded stat must still be flagged — the try-context rule is what makes "
        "the permission conditional, and dropping it would permit a bare stat anywhere"
    )

    # KNOWN-GOOD — the module's own idiom: a guarded stat, which is how it legitimately
    # probes. This case is last on purpose; on its own it would prove nothing.
    assert offenders(
        "try:\n"
        "    if not S_ISDIR(resolved.stat().st_mode):\n"
        "        pass\n"
        "except OSError:\n"
        "    record()\n"
    ) == [], "the guarded stat is the prescribed remedy and must not be flagged"


def test_kitty_specs_resolving_out_of_the_root_is_containment_not_permission(
    tmp_path: Path,
) -> None:
    """MEDIUM-4 — the PAIRED control MEDIUM-1's remediation shipped without.

    LOW-7's whole lesson is that a discrimination between two messages needs both
    halves pinned, because half a discrimination proves nothing. The third fault
    member landed with neither half: nothing stopped it being re-merged into the
    ``unlistable`` branch, which is the exact state the fix removed.

    Containment beats permission when they co-occur, and that ordering is correct:
    fixing mode bits would still not make another project's ledger able to answer
    for this one.
    """
    other = tmp_path / "other-checkout"
    write_ledger(other, "mission-of-other-project", DECISION_OWNED)
    acting = tmp_path / "acting-checkout"
    acting.mkdir()
    (acting / "kitty-specs").symlink_to(other / "kitty-specs", target_is_directory=True)

    outcome = resolve_decision_ownership(acting, DECISION_OWNED)
    refusal = ownership_refusal(outcome)

    assert outcome.owned is False
    assert outcome.specs_root_fault == "outside-acting-root", (
        f"a specs root resolving out of the acting checkout is a CONTAINMENT fault, "
        f"not EACCES — reporting it as 'unlistable' sends the operator to `chmod` "
        f"for a healthy symlink: {outcome!r}"
    )
    assert refusal is not None
    assert "resolves outside this checkout" in refusal
    # The converse half. Without these the discrimination is one-sided and
    # re-merging this branch into `unlistable` would stay green.
    assert "PERMISSION problem" not in refusal
    assert "chmod u+rx" not in refusal
    assert "To fix: run `git pull`" not in refusal
    assert "neither `chmod` nor `git pull` will fix it" in refusal


def test_kitty_specs_symlinked_WITHIN_the_root_sets_no_fault(tmp_path: Path) -> None:
    """DO-NOT-OVER-FIRE control for the test above.

    Without it the containment fault is satisfiable by flagging every symlink,
    which would refuse a monorepo that links ``kitty-specs`` to a sibling inside
    the checkout. Containment is the property, not symlink-phobia.
    """
    root = tmp_path / "checkout"
    real = root / "nested"
    write_ledger(real, "mission-inside", DECISION_OWNED)
    (root / "kitty-specs").symlink_to(real / "kitty-specs", target_is_directory=True)

    outcome = resolve_decision_ownership(root, DECISION_OWNED)

    assert outcome.specs_root_fault is None, (
        f"an in-root symlink is a legitimate layout and must set no fault: {outcome!r}"
    )
    assert outcome.owned is True
    assert ownership_refusal(outcome) is None
