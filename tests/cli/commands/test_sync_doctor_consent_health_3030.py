"""`sync doctor` must be able to say the consent state is UNREADABLE (#3030 SC-004).

FR-020 exists because a machine fault read as an absence: ``SyncConfig._load``
returned ``{}`` for a corrupt or unreadable ``config.toml``, so every project on the
machine resolved as never-opted-in, the drain delivered nothing, doctor looked idle,
and the operator was told to record consent they had already recorded. The fix
(``c633c548b0``) kept the distinction alive above ``_load`` and exposed it as
``consent_index_health()``; ``project_local_consent_fault()`` does the same for the
checkout's own ``.kittify/config.yaml``. **Neither had a renderer.** SC-004's own
note says so: "``sync doctor`` currently cannot tell an operator their consent index
is unreadable."

Four fault kinds have to be rendered, not one. FR-027 added ``unusable`` (a
present-but-uninterpretable value, e.g. ``sync.enabled: "false"`` as a string, or a
``project.uuid`` that is not a uuid), and the 2026-07-30 vocabulary unification split
the two file-level tokens that the two producers had been using for different states,
adding ``wrong_shape`` — so the set is now ``unreadable`` (cannot open),
``unparseable`` (opened, syntax does not parse), ``wrong_shape`` (parsed, top level is
not a mapping) and ``unusable`` (right shape, unusable value). See
``sync.config.CONFIG_FAULT_KINDS``, which declares it and the reasoning for its size.

Each must name **the operator action that resolves it**. Naming the kind alone
would reproduce FR-020's own defect one layer up: an operator told "undetermined"
who then re-records consent has not only failed to fix it, they have *destroyed the
other records*. That last claim is measured here rather than asserted, in
``test_re_recording_consent_on_a_corrupt_index_discards_the_other_records``.

Every test drives the **command** through ``CliRunner``. WP07 shipped a per-project
renderer that ``doctor`` never called, fully unit-tested one layer down, and the
operator surface rendered nothing; a helper-level test here would re-open exactly
that hole, and a later relocation would orphan the helper with the suite still green.
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_module
from specify_cli.cli.commands.sync import app

from specify_cli.core.saas_sync_config import sync_active
pytestmark = [
    pytest.mark.fast,
    pytest.mark.skipif(
        not sync_active(),
        reason="sync deactivated by default (#3799); set SPEC_KITTY_ENABLE_SAAS_SYNC=1 to run",
    ),
]

runner = CliRunner()

PROJECT = "aaaaaaaa-0000-0000-0000-000000000001"

# Rich wraps at the console width; the assertions normalise whitespace, but a width
# this generous keeps a mid-phrase break from splitting a short asserted string.
_WIDE_TERMINAL = "220"


@pytest.fixture(autouse=True)
def checkout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """An isolated home plus an isolated checkout, with doctor kept off the network.

    Also resets the process-wide ``TokenManager`` singleton, in BOTH setup and
    teardown: ``sync.status``/``sync.doctor`` unconditionally call
    ``get_token_manager()``, which lazily caches its instance for the lifetime
    of the worker process, so under a ``--dist loadfile`` run a sibling CLI
    test file that authenticates a fake session (or otherwise mutates the
    singleton) earlier in the same worker would otherwise leak into this
    file's producer-scope resolution.

    That threat model is **not the #3115 CLI failure** (FR-009, measured
    2026-08-01). The #3030 landing pass shipped this reset as self-declared
    unproven hardening (`578a659162` / `4f8e4ca781`): "could not force a live
    reproduction of the reported empty-journal CI failure locally ... this is
    defensive hardening of a credible process-global, not a
    confirmed-necessary fix." WP02's render-surface finding explains the CI
    failures instead — an 80-column dumb-terminal console folds the project
    uuid across two table lines (C-012). Measured on the arm that actually
    discriminates — WP02's ``tests/conftest.py`` seam disabled by a plugin so
    the failing ``(80, 25)`` surface is genuinely restored, under
    ``TERM=dumb FORCE_COLOR=1``, on the sibling
    ``test_sync_status_per_project_3030.py`` (this WP's shared discriminating
    probe) — the same single test reds with the same assertion text whether
    the reset is live (``1 failed, 3 passed``) or neutralised at hook level
    (``scripts/mutants/neutralise_reset_token_manager_3115.py``, suppressed=8,
    ``1 failed, 3 passed``). This file's own tests were not independently run
    on that discriminating arm; they were exercised, without changing
    outcome, when all five ``578a659162`` files ran together under the mutant
    (``65 passed``, per-site suppressed split 24 / 8 / 18 / 50 /
    30 [this file]) — a composition that covers leakage among these five
    files but not from an arbitrary sibling CLI file outside them, which no
    run has placed in the same session. So the verdict is scoped to what was
    actually measured — the one discriminating file and the five together —
    not asserted flat for every session composition. Kept anyway: FR-006's
    inventory speaks only to ``tests/sync/``, not this ``tests/cli/`` path,
    so it licenses no conclusion about deletion either way. The width in the
    pinned-width runs above was the WP02 conftest seam's pinned ``240×50``
    surface (``_plain_cli_console_seam``, autouse and unconditional,
    overriding via rich's explicit-size early return) — not this file's own
    ``COLUMNS=220``, which is set below but was not what was in effect.
    Reset in both setup and teardown so this file starts clean and never
    poisons whichever file the worker runs next — mirroring the existing
    ``reset_journal_cache()`` isolation below.
    """
    from specify_cli.auth.manager import reset_token_manager

    reset_token_manager()
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    repo = tmp_path / "checkout"
    (repo / ".kittify").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("SPECIFY_REPO_ROOT", str(repo))
    monkeypatch.setenv("COLUMNS", _WIDE_TERMINAL)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    monkeypatch.chdir(repo)
    monkeypatch.setattr(sync_module, "_check_server_connection", lambda _url: ("[dim]Disabled[/dim]", ""))
    from specify_cli.cli.commands._auth_recovery import RecoveryOutcome

    monkeypatch.setattr(
        sync_module,
        "handle_unauthenticated_with_teamspace",
        lambda **_: RecoveryOutcome.NO_TEAMSPACE,
    )
    monkeypatch.setattr("specify_cli.sync.daemon.scan_sync_daemons", lambda: None)
    from specify_cli.event_journal.journal import reset_journal_cache

    reset_journal_cache()
    try:
        yield repo
    finally:
        reset_token_manager()


def _flat(output: str) -> str:
    return " ".join(output.split())


def _index_path() -> Path:
    from specify_cli.sync.config import SyncConfig

    return Path(SyncConfig().config_file)


def _record_consent() -> None:
    """A healthy index holding a real grant — the state a fault must not read as absent."""
    from specify_cli.sync.config import SyncConfig
    from specify_cli.sync.consent import record_project_opt_in

    record_project_opt_in(PROJECT, actor="doctor-consent-health-test")
    # This suite diagnoses the retired machine index as legacy evidence. Seed that
    # evidence directly; it is never allowed to grant hosted-sync authority.
    SyncConfig()._save({"sync": {"project_consent": {PROJECT: {"enabled": True}}}})


def _project_config(repo: Path, text: str) -> None:
    (repo / ".kittify" / "config.yaml").write_text(text, encoding="utf-8")


# --------------------------------------------------------------------------- #
# The premise, measured — why "record consent again" is the wrong advice        #
# --------------------------------------------------------------------------- #


def test_re_recording_consent_on_a_corrupt_index_is_refused() -> None:
    """The premise behind the wording this section uses — now the *fixed* premise.

    This test previously pinned the harm: ``set_project_consent`` is an unlocked
    whole-file read-modify-write over ``_load()``, which returns ``{}`` for an
    unreadable file, so the "obvious" operator response to being told consent is
    undetermined rewrote the index from an empty document and every other project's
    record was gone. That is fixed — the write is refused — so the assertion is
    replaced rather than the test deleted, and the doctor's wording moved with it.

    Its old assertion was also not discriminating, which is worth recording: it
    corrupted the index by *overwriting* the file, which had already removed the grant
    whose loss it then claimed to detect, so ``"aaaaaaaa" not in surviving`` could not
    fail either way. The full-strength measurement — corruption that keeps a bystander
    project's bytes on disk, asserted against a project the call never names — lives in
    ``tests/sync/test_consent_write_refusal_3030.py``.
    """
    from specify_cli.sync.config import SyncConfig
    from specify_cli.sync.consent import LegacyConsentMigrationRequiredError

    _record_consent()
    path = _index_path()
    original = path.read_text(encoding="utf-8")
    assert "aaaaaaaa" in original, "precondition: the grant is on disk"

    # Corrupt while KEEPING the existing record in the bytes, so its survival is a
    # real observation rather than an artefact of the setup.
    path.write_text(original + "\n[sync\nbroken = ", encoding="utf-8")

    with pytest.raises(LegacyConsentMigrationRequiredError):
        SyncConfig().set_project_consent("bbbbbbbb-0000-0000-0000-000000000002", True)

    surviving = path.read_text(encoding="utf-8")
    assert "aaaaaaaa" in surviving, "the refusal must leave the existing record intact"
    assert "bbbbbbbb" not in surviving, "and must not write the refused grant either"


# --------------------------------------------------------------------------- #
# The machine-global consent index                                             #
# --------------------------------------------------------------------------- #


def test_doctor_says_the_consent_index_is_unreadable_and_names_the_action() -> None:
    """SC-004's owed half: the operator learns their index cannot be read.

    Red before this section existed: ``consent_index_health()`` had no renderer, so
    doctor printed its usual table and "No issues detected", while every project on
    the machine silently resolved as undetermined.

    The status word is now the *kind's* own — a broken-TOML index is announced as
    UNPARSEABLE, not as UNREADABLE, because it opened perfectly well and the remedy is
    an edit rather than a chmod.
    """
    _record_consent()
    _index_path().write_text("[sync\nbroken = ", encoding="utf-8")

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    flat = _flat(result.output)
    assert "Consent record readability" in flat
    assert "UNPARSEABLE" in flat
    # The action, not the kind: an operator told "unparseable" still has to guess.
    assert "REPAIR THE FILE'S SYNTAX" in flat
    assert str(_index_path()) in flat
    # The consequence, so a silent machine is explained rather than just flagged.
    assert "every project on this machine" in flat.lower()
    # And the defect FR-020 exists to remove.
    assert "NOT a missing consent record" in flat
    assert "Issues found" in result.output
    assert "No issues detected" not in result.output


def test_doctor_says_re_recording_consent_is_refused_rather_than_destructive() -> None:
    """The measured premise above, in the operator's own output — and kept true.

    Without this line the natural next move after "consent is undetermined" is
    `spec-kitty sync enable`, which cannot help: the write is refused and the file
    still needs repairing.

    The asserted wording changed with the fix. It used to be "discarding every other
    project's record", which was accurate until the write started refusing; advice that
    was true when written and false when read is the defect this whole section exists
    to remove, so the old sentence must NOT still be printed.
    """
    _record_consent()
    _index_path().write_text("not = [valid toml", encoding="utf-8")

    result = runner.invoke(app, ["doctor"])

    flat = _flat(result.output)
    assert "your other projects' records are safe" in flat
    assert "nothing is delivered until the file itself is repaired" in flat
    assert "discarding every other project's record" not in flat, "the doctor still describes a hazard that no longer exists"


def test_a_readable_index_is_stated_rather_than_left_silent() -> None:
    """ "Healthy" and "never checked" must not render identically.

    That equivalence is the incident's own false-green, and this whole section is a
    remedy for it — so the section must print on the healthy path too.
    """
    _record_consent()

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    flat = _flat(result.output)
    assert "Consent record readability" in flat
    assert "machine-global consent index" in flat
    assert "readable" in flat
    assert "UNREADABLE" not in flat
    # A missing record is a legitimate state, not a fault, and saying so here is what
    # keeps an operator from "repairing" a file that is simply empty.
    assert "a missing record is not a fault" in flat.lower()


# --------------------------------------------------------------------------- #
# The checkout's own project-local config — all three fault kinds               #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("label", "config_text", "action"),
    [
        # Opened, and the YAML syntax does not parse. This used to be reported as
        # ``unreadable`` — the same token a chmod 000 file gets — which is why that
        # token's advice had to name two different remedies.
        ("unparseable", "project:\n  uuid: [unclosed\n", "REPAIR THE FILE'S SYNTAX"),
        # Parsed, but the top level is not a mapping. Its own kind now: it used to
        # borrow ``unparseable``, sending an operator to hunt a syntax error that
        # does not exist.
        ("wrong_shape", "- one\n- two\n", "MAKE THE DOCUMENT A MAPPING"),
        # FR-027: parsed, shape fine, a *field* records something unusable. Only a
        # real YAML bool records a decision, so a quoted "false" records nothing.
        ("unusable", f'project:\n  uuid: {PROJECT}\nsync:\n  enabled: "false"\n', "CORRECT THE FIELD VALUE"),
    ],
)
def test_doctor_names_the_action_for_each_project_local_fault_kind(checkout: Path, label: str, config_text: str, action: str) -> None:
    """Each kind renders, and each names what the operator must do.

    ``unusable`` is the one FR-027 added and the one most easily mistaken for
    absence: the file looks fine, so an operator who is told only "no consent
    record" edits nothing and re-runs `sync enable` forever. The permission fault,
    the fourth kind, needs a real chmod and has its own test below.
    """
    _project_config(checkout, config_text)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    flat = _flat(result.output)
    assert action in flat, f"the {label} fault did not name its remedy"
    assert str(checkout / ".kittify" / "config.yaml") in flat
    assert "NOT a missing consent record" in flat
    assert "Issues found" in result.output


def test_the_unusable_kind_explains_that_only_a_real_boolean_records_a_decision(
    checkout: Path,
) -> None:
    """The specific advice that resolves the specific value, not generic advice.

    ``enabled: "false"`` and ``enabled: no`` look like refusals and record nothing;
    ruamel is YAML 1.2, so ``no`` is the string ``"no"``. An operator shown only
    "unusable" would reasonably conclude their refusal is in force.
    """
    _project_config(checkout, f'project:\n  uuid: {PROJECT}\nsync:\n  enabled: "false"\n')

    result = runner.invoke(app, ["doctor"])

    flat = _flat(result.output)
    assert "only a real boolean records a consent decision" in flat.lower()


def test_the_fault_is_reported_as_unattributable_and_as_this_checkouts_own(
    checkout: Path,
) -> None:
    """Two true things that pull in opposite directions, and both are owed.

    A fault cannot be attributed to a project — an unreadable file does not disclose
    which project it declares — so it denies broadly. But its reach is much narrower
    than that sounds: every production supplier of ``checkout_roots`` offers at most
    one root, the cwd's own, so the trigger is the drain's OWN checkout being broken.
    Saying only the first would let an operator conclude an unrelated project broke
    their machine.
    """
    _project_config(checkout, "- one\n- two\n")

    result = runner.invoke(app, ["doctor"])

    flat = _flat(result.output).lower()
    assert "cannot be attributed to a project" in flat
    assert "this checkout's own" in flat
    assert "no sibling checkout" in flat


def test_a_readable_project_config_is_stated_too(checkout: Path) -> None:
    _project_config(checkout, f"project:\n  uuid: {PROJECT}\nsync:\n  enabled: true\n")

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    flat = _flat(result.output)
    assert "this checkout" in flat
    assert "readable" in flat
    assert "MAKE THE FILE READABLE" not in flat


def test_the_action_is_true_for_both_producers_of_the_same_kind(checkout: Path) -> None:
    """``unparseable`` now means the same thing on both surfaces, so the advice narrows.

    Before the 2026-07-30 unification it did not: ``sync/config.py`` tagged a TOML
    **syntax** error ``unparseable`` while ``sync/consent.py`` tagged a **non-mapping
    top level** ``unparseable``, so one kind-keyed advice string had to span both
    readings and was therefore false about one of them for every reader. Both producers
    now mean "opened, and the syntax does not parse".

    Both faults are produced in the same run so the shared advice is checked against
    both at once — a TOML syntax error on the index and a YAML syntax error on the
    project config.
    """
    _record_consent()
    _index_path().write_text("[sync\nbroken = ", encoding="utf-8")  # config.py: syntax
    _project_config(checkout, "project:\n  uuid: [unclosed\n")  # consent.py: syntax

    result = runner.invoke(app, ["doctor"])

    flat = _flat(result.output)
    # Four: two faults, each named once in the section and once in doctor's summary.
    # The count also pins that the two cannot drift apart — they are built from the
    # same strings precisely so the summary can never say something milder.
    assert flat.count("REPAIR THE FILE'S SYNTAX") == 4, "both surfaces reported the same kind, in both places"
    # The advice is now about syntax alone. The shape wording must be *absent*: no
    # wrong-shape fault exists in this run, so its presence would mean the advice is
    # still hedging across two states and telling half its readers something false.
    assert "syntax does not parse" in flat
    assert "top level is not a mapping" not in flat, "the unparseable advice still spans the wrong-shape state, which is the divergence this unification removed"
    # And the detail, which names the actual file and error, is printed for each.
    assert "not valid TOML" in flat
    assert "could not be parsed" in flat


def test_a_wrong_shape_is_not_given_the_syntax_error_advice(checkout: Path) -> None:
    """The half the old vocabulary got wrong, in the operator's own output.

    A valid YAML document whose top level is a list has no syntax error to find. Told
    to "repair the file's structure" alongside advice about syntax, an operator hunts
    for a fault that is not there. The two states are produced in one run and must
    render as two different kinds with two different actions.
    """
    _record_consent()
    _index_path().write_text("[sync\nbroken = ", encoding="utf-8")  # unparseable
    _project_config(checkout, "- one\n- two\n")  # wrong_shape

    result = runner.invoke(app, ["doctor"])

    flat = _flat(result.output)
    assert flat.count("REPAIR THE FILE'S SYNTAX") == 2, "the index's syntax fault, in both places"
    assert flat.count("MAKE THE DOCUMENT A MAPPING") == 2, "the checkout's shape fault, in both places"
    assert "there is none" in flat, "the shape advice must say there is no syntax error to find"
    assert "top-level content is not a mapping" in flat


# --------------------------------------------------------------------------- #
# The section cannot go quiet                                                   #
# --------------------------------------------------------------------------- #


def test_an_unknown_fault_kind_is_still_rendered_with_its_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A fourth kind must not fall through a lookup into silence.

    This mission has added a fault kind once already (FR-027's ``unusable``). A
    kind-keyed table that renders nothing for an unrecognised key would turn the
    next addition into an invisible fault — the exact shape of the defect being
    fixed here.
    """
    from specify_cli.sync.config import ConfigReadFault
    from specify_cli.sync.consent import ConsentIndexHealth

    monkeypatch.setattr(
        "specify_cli.sync.consent.consent_index_health",
        lambda: ConsentIndexHealth(
            readable=False,
            # Not a real path: this string is fault *detail* the renderer echoes, never opened.
            # Deliberately not under a shared temp dir — see tmp-literal-offender-burndown-01KWWRW2
            # FR-002 (category B: a non-shared-temp-dir absolute sentinel).
            fault=ConfigReadFault(
                kind="quarantined",
                detail="/nonexistent/consent-index.toml: held by an antivirus quarantine",
            ),
        ),
    )

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    flat = _flat(result.output)
    assert "quarantined" in flat
    assert "held by an antivirus quarantine" in flat
    assert "Issues found" in result.output


def test_a_raising_consent_read_is_reported_rather_than_hiding_the_section(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every exit path from this section is observable.

    "The consent state is fine", "I could not read it" and "I never looked" must not
    render identically — the three-states-look-alike failure this whole file exists
    to close.
    """

    def _boom() -> None:
        raise RuntimeError("index read exploded")

    monkeypatch.setattr("specify_cli.sync.consent.consent_index_health", _boom)

    result = runner.invoke(app, ["doctor"])

    assert result.exit_code == 0, result.output
    flat = _flat(result.output)
    assert "Consent record readability" in flat
    assert "index read exploded" in flat
    assert "Issues found" in result.output


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads a chmod 000 file regardless")
def test_a_chmod_000_index_is_reported_as_a_fault(tmp_path: Path) -> None:
    """The FR-020 measurement itself: healthy -> granted, unreadable -> undetermined.

    Kept as a real permission fault rather than a stubbed one, because ``read()``'s
    ``OSError`` branch is a different code path from its TOML branch and the two
    produce different kinds.
    """
    _record_consent()
    path = _index_path()
    path.chmod(0o000)
    try:
        result = runner.invoke(app, ["doctor"])
    finally:
        path.chmod(0o600)

    assert result.exit_code == 0, result.output
    flat = _flat(result.output)
    assert "UNREADABLE" in flat
    assert "MAKE THE FILE READABLE" in flat
