"""A write to an unreadable consent store must refuse, not rebuild it from empty (#3030).

FR-022 already settled the other half of this question: *opt-in on an unreadable
project-local config refuses and writes no grant*, "without which the natural remedy
for the new denial would manufacture exactly the stale grant the fix stops honouring".
The machine-global index did the **opposite** — and lost every other project's record
doing it.

Every ``SyncConfig`` setter is a whole-file read-modify-write over ``_load()``, which
returns ``{}`` for a file it cannot read (its documented, deliberately unchanged
contract). So a write over an unreadable ``config.toml`` re-emits the file from an
empty document: the surviving grants, refusals and checkout overrides of every other
project are discarded, and the file the operator has to repair goes with them.

Measured on the tree before the fix, one private ``SPEC_KITTY_HOME`` per case, with a
bystander project's grant and a checkout override planted alongside::

    set_project_consent               bystander lost, no error raised
    set_project_consent_bulk          bystander lost, no error raised
    set_checkout_sync_enabled         bystander lost, no error raised
    set_repository_sync_enabled       bystander lost, no error raised
    set_server_url                    bystander lost, no error raised
    set_max_queue_size                bystander lost, no error raised
    set_background_daemon             bystander lost, no error raised
    mark_checkout_records_unresolved  bystander survived (inert: see its own test)
    resolve_project_consent           bystander lost — from a READ, via _reconcile_index

The asserted consequence is **a bystander project's record disappearing**, never a
boolean about the write, and never the record the call itself writes: ``_reconcile_index``
re-records the very project being resolved, so "project A survived" is satisfied by the
destruction as well as by the fix. Only an uninvolved third project discriminates.

The bystander's bytes are planted for real and the corruption step deliberately *keeps*
them — a test that corrupts by overwriting has already removed the record whose loss it
claims to detect, and its assertion can then never fail.

**Absent and unreadable are different states**, and the line is inherited from
:meth:`SyncConfig.read`, which already draws it in one place: a missing file is
``fault=None``, a legitimate and overwhelmingly common state. Refusing there would
break every first-time opt-in on every machine, so it is regression-pinned here
alongside the refusal.

Each case gets its own ``SPEC_KITTY_HOME``, because ``_answer_project_local``
reconciles the index as a side effect of a *read* — a shared home lets one case's
reconciliation rewrite the index the next case is about to measure.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

pytestmark = pytest.mark.fast

#: The project the calls under test act on.
PROJECT_A = "aaaaaaaa-0000-0000-0000-000000000001"
#: The project a write records — never the one asserted about.
PROJECT_B = "bbbbbbbb-0000-0000-0000-000000000002"
#: The uninvolved third project. Nothing under test ever names it, so its record can
#: only vanish by the file being rebuilt — which is the whole measurement.
BYSTANDER = "cccccccc-0000-0000-0000-000000000003"

#: A second bystander record of a different *type*, so the assertion is not limited to
#: the one table the consent writers happen to touch.
BYSTANDER_CHECKOUT = "/some/other/checkout"


@pytest.fixture(autouse=True)
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """One private ``SPEC_KITTY_HOME`` per test case, parametrized cases included."""
    root = tmp_path / "home"
    root.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(root))
    monkeypatch.setenv("HOME", str(root))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    return root


def _index_path() -> Path:
    from specify_cli.sync.config import SyncConfig

    return SyncConfig().config_file


def _plant_records() -> Path:
    """A healthy index holding A's grant, the bystander's grant and a checkout override."""
    from specify_cli.sync.config import SyncConfig

    config = SyncConfig()
    config.set_project_consent(PROJECT_A, True)
    config.set_project_consent(BYSTANDER, True)
    config.set_checkout_sync_enabled(Path(BYSTANDER_CHECKOUT), True)

    path = _index_path()
    text = path.read_text(encoding="utf-8")
    assert BYSTANDER in text, "precondition: the bystander's grant is on disk"
    assert BYSTANDER_CHECKOUT in text, "precondition: the bystander override is on disk"
    return path


def _assert_bystanders_survive(path: Path, what: str) -> None:
    """The consequence, asserted on records nothing under test ever names."""
    text = path.read_text(encoding="utf-8") if path.exists() else "<the index file is gone>"
    assert BYSTANDER in text, f"{what} rebuilt the unreadable index from an empty document: an uninvolved project's grant is gone and cannot be recovered"
    assert BYSTANDER_CHECKOUT in text, f"{what} discarded an uninvolved checkout override"


def _corrupt_keeping_the_records(path: Path) -> str:
    """Make the index unparseable while **keeping** the planted records in the bytes."""
    text = path.read_text(encoding="utf-8")
    path.write_text(text + "\n[sync\nbroken = ", encoding="utf-8")
    corrupted = path.read_text(encoding="utf-8")
    assert BYSTANDER in corrupted, "precondition: corrupting kept the bystander's record"
    return corrupted


def _assert_index_unreadable(path: Path) -> None:
    """The premise of every refusal case, checked rather than assumed."""
    from specify_cli.sync.config import SyncConfig

    assert SyncConfig().read().fault is not None, f"precondition: {path} reads as a fault"


# --------------------------------------------------------------------------- #
# The consequence: an uninvolved project's record disappearing                 #
# --------------------------------------------------------------------------- #


def test_recording_consent_over_an_unreadable_index_keeps_the_other_records() -> None:
    """Red before the fix: the bystander's grant is gone after B is recorded.

    This is the harm ``sync doctor`` already warns about in prose — "a write rewrites
    the file from an empty document when it cannot be read, discarding every other
    project's record". The warning was accurate, which is the defect.
    """
    from specify_cli.sync.config import ConfigNotReadableError, SyncConfig

    path = _plant_records()
    _corrupt_keeping_the_records(path)
    _assert_index_unreadable(path)

    with pytest.raises(ConfigNotReadableError):
        SyncConfig().set_project_consent(PROJECT_B, True)

    _assert_bystanders_survive(path, "recording consent")
    assert PROJECT_B not in path.read_text(encoding="utf-8"), "the refused grant must not be written either"


def test_the_refusal_names_the_file_and_carries_the_fault() -> None:
    """A silent no-op would be the FR-020 defect again, one direction over.

    An operator whose opt-in quietly did nothing is in the same position as one told
    "no consent record": they try again. The refusal names the file and carries the
    same :class:`ConfigReadFault` the doctor renders, so the two surfaces cannot
    describe one fault differently.
    """
    from specify_cli.sync.config import ConfigNotReadableError, SyncConfig

    path = _plant_records()
    _corrupt_keeping_the_records(path)

    with pytest.raises(ConfigNotReadableError) as excinfo:
        SyncConfig().set_project_consent(PROJECT_B, True)

    assert str(path) in str(excinfo.value)
    assert excinfo.value.fault.kind == "unparseable"


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a chmod 000 file regardless")
def test_a_chmod_000_index_is_refused_rather_than_replaced() -> None:
    """The other file-level fault, on a file whose bytes are perfectly valid.

    ``atomic_write`` replaces via ``os.replace``, which needs the *directory* writable
    and does not care about the file's own mode — so an unreadable-but-intact index is
    destroyed exactly as a corrupt one is. The kind asserted here is the one that
    distinguishes "could not open" from "opened and could not parse".
    """
    from specify_cli.sync.config import ConfigNotReadableError, SyncConfig

    path = _plant_records()
    path.chmod(0o000)
    try:
        with pytest.raises(ConfigNotReadableError) as excinfo:
            SyncConfig().set_project_consent(PROJECT_B, True)
        assert excinfo.value.fault.kind == "unreadable"
    finally:
        path.chmod(0o600)

    _assert_bystanders_survive(path, "recording consent over a chmod 000 index")


# --------------------------------------------------------------------------- #
# The positive control, and the absent case                                    #
# --------------------------------------------------------------------------- #


def test_recording_consent_over_a_readable_index_still_writes() -> None:
    """The control that must pass before and after — otherwise nothing is proven.

    A refusal that fires for every state answers "no" to every question, which looks
    identical to a working fix from the failing cases alone.
    """
    from specify_cli.sync.config import SyncConfig

    path = _plant_records()

    SyncConfig().set_project_consent(PROJECT_B, True)

    _assert_bystanders_survive(path, "recording consent over a readable index")
    assert SyncConfig().get_project_consent(PROJECT_B) is True


def test_a_wholly_absent_index_still_accepts_the_first_grant() -> None:
    """Absence is not a fault, and denying it would break every first-run opt-in.

    ``SyncConfig.read`` returns ``fault=None`` for a missing file precisely so this
    stays the ordinary case; the refusal inherits that line rather than drawing its
    own one function away.
    """
    from specify_cli.sync.config import SyncConfig

    assert not _index_path().exists(), "precondition: no index at all"

    SyncConfig().set_project_consent(PROJECT_A, True)

    assert SyncConfig().get_project_consent(PROJECT_A) is True


def test_an_empty_index_file_still_accepts_a_grant() -> None:
    """A zero-byte ``config.toml`` parses as an empty document, not a fault.

    The neighbouring state to "absent", and the one a half-finished write leaves
    behind; refusing it would strand a machine that can be repaired by writing.
    """
    from specify_cli.sync.config import SyncConfig

    path = _index_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")

    SyncConfig().set_project_consent(PROJECT_A, True)

    assert SyncConfig().get_project_consent(PROJECT_A) is True


# --------------------------------------------------------------------------- #
# The sibling writers — every setter writes the file that holds the records    #
# --------------------------------------------------------------------------- #


def _writers() -> list[tuple[str, object]]:
    from specify_cli.sync.config import BackgroundDaemonPolicy

    return [
        ("set_project_consent", lambda c: c.set_project_consent(PROJECT_B, True)),
        ("set_project_consent_bulk", lambda c: c.set_project_consent_bulk({PROJECT_B: True})),
        ("set_checkout_sync_enabled", lambda c: c.set_checkout_sync_enabled(Path("/new/checkout"), True)),
        ("set_repository_sync_enabled", lambda c: c.set_repository_sync_enabled("acme/repo", True)),
        ("mark_checkout_records_unresolved", lambda c: c.mark_checkout_records_unresolved([BYSTANDER_CHECKOUT])),
        ("set_server_url", lambda c: c.set_server_url("https://example.invalid")),
        ("set_max_queue_size", lambda c: c.set_max_queue_size(42)),
        ("set_background_daemon", lambda c: c.set_background_daemon(BackgroundDaemonPolicy.MANUAL)),
    ]


_WRITER_IDS = [name for name, _ in _writers()]


@pytest.mark.parametrize(("name", "write"), _writers(), ids=_WRITER_IDS)
def test_no_setter_rebuilds_the_index_from_an_empty_document(name: str, write) -> None:
    """Every read-modify-write setter, not only the consent ones.

    ``set_server_url``, ``set_max_queue_size`` and ``set_background_daemon`` have
    nothing to do with consent and destroyed the consent index just as thoroughly —
    measured, all three. They all read the same file through ``_load()`` and re-emit it
    whole, so leaving three of the eight uncovered would leave three ways to lose the
    records.

    ``mark_checkout_records_unresolved`` was the only one that happened to survive the
    before-measurement, and by accident rather than by design: its input is also
    ``_load()``-derived, so on an unreadable index it finds no entries to mark and
    never reaches its save. It refuses here for the same reason the others do — the
    accident is one edit away from not holding.
    """
    from specify_cli.sync.config import ConfigNotReadableError, SyncConfig

    path = _plant_records()
    _corrupt_keeping_the_records(path)
    _assert_index_unreadable(path)

    with pytest.raises(ConfigNotReadableError):
        write(SyncConfig())

    _assert_bystanders_survive(path, name)


@pytest.mark.parametrize(("name", "write"), _writers(), ids=_WRITER_IDS)
def test_every_setter_still_writes_a_readable_index(name: str, write) -> None:
    """The per-writer positive control.

    Without it a refusal that fired unconditionally would satisfy the case above for
    all eight writers — eight apparent successes proving nothing. Each writer is
    checked to have actually changed the file, not merely to have not raised.
    """
    from specify_cli.sync.config import SyncConfig

    path = _plant_records()
    before = path.read_text(encoding="utf-8")

    write(SyncConfig())

    after = path.read_text(encoding="utf-8")
    assert after != before, f"{name} wrote nothing to a perfectly readable index"
    _assert_bystanders_survive(path, f"{name} on a readable index")


# --------------------------------------------------------------------------- #
# The reconcile path — a writer reached from a READ                            #
# --------------------------------------------------------------------------- #


def _checkout_granting(root: Path, uuid: str) -> Path:
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    (root / ".kittify" / "config.yaml").write_text(f"project:\n  uuid: {uuid}\nsync:\n  enabled: true\n", encoding="utf-8")
    return root


def test_resolving_consent_does_not_rewrite_an_unreadable_index(tmp_path: Path) -> None:
    """``_reconcile_index`` is the dangerous caller: it writes as a side effect of a read.

    ``resolve_project_consent`` consults the checkout's own config, and when that
    answers it corrects the machine index to match. On an unreadable index
    ``get_project_consent`` returns ``None``, which differs from the resolved verdict,
    so the reconciliation fires — and merely *asking* whether one project consents
    flattens the file. Measured before the fix: the index came back holding a single
    entry, project A's, with the bystander's grant and the checkout override gone. No
    opt-in, no operator action, just a drain tick.

    Note the assertion is on the bystander and not on A: the reconciliation re-records
    A itself, so "A survived" is satisfied by the destruction too.
    """
    from specify_cli.sync.consent import resolve_project_consent

    path = _plant_records()
    _corrupt_keeping_the_records(path)
    _assert_index_unreadable(path)
    checkout = _checkout_granting(tmp_path / "checkout", PROJECT_A)

    decision = resolve_project_consent(PROJECT_A, repo_root=checkout)

    assert decision.granted is True, "the readable checkout still answers"
    _assert_bystanders_survive(path, "resolving consent")


def test_resolving_consent_still_reconciles_a_readable_index(tmp_path: Path) -> None:
    """The control for the reconcile path: the correction must still happen.

    Suppressing reconciliation everywhere would let a stale index outlive the file
    that overrules it — the never-corrected-cache defect the reconciliation exists for.
    """
    from specify_cli.sync.config import SyncConfig
    from specify_cli.sync.consent import resolve_project_consent

    SyncConfig().set_project_consent(PROJECT_A, False)
    checkout = _checkout_granting(tmp_path / "checkout", PROJECT_A)

    decision = resolve_project_consent(PROJECT_A, repo_root=checkout)

    assert decision.granted is True
    assert SyncConfig().get_project_consent(PROJECT_A) is True, "the index was not corrected to match the authoritative checkout"


def test_a_refused_reconciliation_does_not_break_the_decision(tmp_path: Path) -> None:
    """The read still answers. A refused *cache correction* is not a failed read.

    ``_reconcile_index`` is best effort by design — "a write failure must not turn an
    answered question into an error" — and that reasoning survives the refusal: the
    authoritative file was read, the verdict is known, and only the cache update is
    declined.
    """
    from specify_cli.sync.consent import resolve_project_consent

    path = _plant_records()
    _corrupt_keeping_the_records(path)
    checkout = _checkout_granting(tmp_path / "checkout", PROJECT_A)
    (checkout / ".kittify" / "config.yaml").write_text(f"project:\n  uuid: {PROJECT_A}\nsync:\n  enabled: false\n", encoding="utf-8")

    decision = resolve_project_consent(PROJECT_A, repo_root=checkout)

    assert decision.granted is False
    assert decision.level == "project_local", "the refusal is still attributed to the file"
    _assert_bystanders_survive(path, "resolving a project-local refusal")


# --------------------------------------------------------------------------- #
# The operator surface of the refusal                                          #
# --------------------------------------------------------------------------- #
#
# FR-023's recorded lesson, applied to this fix: "a new exception nobody catches is a
# crash moved, not fixed", so every caller that assumed the write could not raise is
# audited. Three CLI commands write through ``SyncConfig`` with no handler —
# ``sync opt-in``, ``sync opt-out`` and ``sync server`` — and ``opt-in`` is precisely
# the command ``sync doctor`` sends an operator to consider after reporting an
# undetermined consent state. Letting the refusal surface there as an unhandled
# exception (measured: exit 1, empty output) would replace one unhelpful answer with
# another, on the path this mission exists to make honest.


@pytest.mark.parametrize(
    ("command", "what"),
    [
        (["opt-in"], "opt-in"),
        (["opt-out"], "opt-out"),
        (["server", "https://example.invalid"], "server URL"),
    ],
    ids=["opt-in", "opt-out", "server"],
)
def test_a_refused_write_is_reported_rather_than_raised_out_of_the_cli(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, command: list[str], what: str
) -> None:
    """The refusal reaches the operator as an actionable message, not a traceback."""
    from typer.testing import CliRunner

    from specify_cli.cli.commands.sync import app

    repo = tmp_path / "checkout"
    (repo / ".kittify").mkdir(parents=True, exist_ok=True)
    (repo / ".kittify" / "config.yaml").write_text(
        f"project:\n  uuid: {PROJECT_A}\n", encoding="utf-8"
    )
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo))
    monkeypatch.setenv("COLUMNS", "220")
    # ``opt-in`` refuses early and exits non-zero when the rollout flag is off, which
    # would satisfy the exit-code assertion without ever reaching the write.
    monkeypatch.setenv("SPEC_KITTY_ENABLE_SAAS_SYNC", "1")
    monkeypatch.chdir(repo)

    path = _plant_records()
    _corrupt_keeping_the_records(path)

    result = CliRunner().invoke(app, command)

    assert result.exit_code != 0, "a refused write must not report success"
    assert result.exception is None or isinstance(result.exception, SystemExit), (
        f"the refusal escaped `sync {command[0]}` as an unhandled "
        f"{type(result.exception).__name__}: an operator sees a traceback"
    )
    flat = " ".join(result.output.split())
    assert str(path) in flat, "the operator is not told which file to repair"
    assert "could not be read" in flat
    _assert_bystanders_survive(path, f"sync {command[0]}")


def test_the_backfill_writes_nothing_over_an_unreadable_index() -> None:
    """The backfill reads the same unreadable file it would write.

    It is inert here for a reason worth pinning rather than relying on: its input
    (``get_all_checkout_sync_records``) comes from ``_load()``, which yields ``{}``, so
    there is nothing to write and the batched setter returns early. If a future change
    fed it records from anywhere else, the refusal is what stops it flattening the
    index.
    """
    from specify_cli.sync.consent import backfill_uuid_consent_index

    path = _plant_records()
    corrupted = _corrupt_keeping_the_records(path)

    result = backfill_uuid_consent_index()

    assert result.mapped == 0
    assert path.read_text(encoding="utf-8") == corrupted, "the backfill rewrote the index"
