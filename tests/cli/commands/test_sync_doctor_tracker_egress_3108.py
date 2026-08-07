"""`sync doctor` reports the tracker-egress verdict the gates enforce (#3108 WP06, FR-014).

`doctor` reported healthy throughout the 2026-07-27 incident: a refusal an operator could
only discover by running the command that fails is a diagnostic gap. This suite pins the new
``Tracker egress`` block that closes it -- one row per :class:`EgressDestination` member,
printed unconditionally including the fully-permitted case, built from
``tracker_egress_verdict`` (the *same* function WP04/WP05's gates enforce), never routed
through ``_render_consent_fault`` (that helper's contract is a readability fault over the
pinned ``CONFIG_FAULT_KINDS`` vocabulary, not a tracker-egress verdict -- routing through it
was measured wrong three ways: it discards the refusal text, or announces a readable file as
UNREADABLE, or prints ``_CONSENT_FAULT_NOT_ABSENCE`` unconditionally, which is false for most
of this verdict's states).

Seven checkouts, matching SC-014 exactly (14 rows: 7 checkouts x 2 destinations):

1. ``tracker.egress: refused``                              -- refused, Channel 2, both rows.
2. a tracker-key fault (a near-miss value, ``"refuse"``)     -- refused, Channel 2, fault text.
3. Channel-1 recorded refusal, no tracker key                -- refused, Channel 1.
4. Channel-1 absent (no record), no tracker key               -- refused, Channel 1.
5. Channel-1 not consentable (no ``project.uuid``)            -- refused, Channel 1.
6. ``tracker.egress: permitted``, Channel-1 absent            -- **discriminating**: permitted
   locally, refused hosted (the case a one-row block cannot express, SC-014).
7. fully permitted (Channel 1 granted, no tracker key)        -- permitted, both rows.

An **eighth** case -- ``locate_project_root(Path.cwd())`` returning ``None`` -- is asserted
separately, deliberately *outside* the 7/14 counts (SC-014 pins those two numbers literally;
folding the eighth case in would silently change one of them for the next reader).

Checkouts 1 and 2 record Channel 1 as *granted* (``sync.enabled: true``) so their rows isolate
a clean Channel-2-only refusal, matching the table in the WP06 prompt exactly (``refused,
Channel 2`` on both rows, not muddied by an additional Channel-1 refusal clause).

**Fresh uuid per checkout, never shared.** The consent index is machine-global and
uuid-keyed and outlives any one test's ``tmp_path``; a shared uuid across checkouts would let
one checkout's recorded decision leak into another's "no record" fixture as a stale
machine-index hit.
"""

from __future__ import annotations

import re
import uuid as uuid_module
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from typer.testing import CliRunner

from specify_cli.cli.commands import sync as sync_module
from specify_cli.cli.commands.sync import app
from specify_cli.tracker.local_service import LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS
from specify_cli.tracker.saas_client import TRACKER_EGRESS_IDENTIFIER_KINDS
from specify_cli.tracker.egress_verdict import (
    CHANNEL1_GRANTED,
    CHANNEL1_NOT_CONSENTABLE,
    CHANNEL1_NO_RECORD,
    CHANNEL1_RECORDED_REFUSAL,
    CHANNEL1_UNCLASSIFIED,
    CHANNEL1_UNDETERMINED,
    CHANNEL_1,
    CHANNEL_2,
    EgressDestination,
    TrackerEgressVerdict,
    tracker_egress_verdict,
)

pytestmark = pytest.mark.fast

runner = CliRunner()

# Rich wraps at the console width; assertions normalise whitespace, but a width this
# generous keeps a mid-phrase break from splitting a short asserted string -- the same
# value ``test_sync_doctor_consent_health_3030.py`` uses for the same reason.
_WIDE_TERMINAL = "220"

DESTINATIONS: tuple[EgressDestination, ...] = (
    EgressDestination.LOCAL_SUBPROCESS,
    EgressDestination.HOSTED_SERVICE,
)

#: The identifier-set fragment each destination's **owning transport** passes. This suite
#: re-derives verdicts to compare against what ``doctor`` printed, so it must pass exactly
#: what ``doctor`` passes -- a different fragment here would render a different refusal and
#: the row-matching assertions would compare two strings that were never meant to agree.
_IDENTIFIERS_FOR = {
    EgressDestination.LOCAL_SUBPROCESS: LOCAL_SUBPROCESS_EGRESS_IDENTIFIER_KINDS,
    EgressDestination.HOSTED_SERVICE: TRACKER_EGRESS_IDENTIFIER_KINDS,
}

_SYNC_ENABLED_TRUE = "sync:\n  enabled: true\n"
_SYNC_ENABLED_FALSE = "sync:\n  enabled: false\n"

_ROW_HEADER_RE = re.compile(r"^  (local_subprocess|hosted_service)  (REFUSED|permitted)\s*$")

# The strings this block must never emit -- pinned by name so the reasoning travels with
# the assertion. ``REPAIR THE FILE'S SYNTAX`` and ``_CONSENT_FAULT_NOT_ABSENCE`` are both
# emitted *only* by ``_render_consent_fault``, reached *only* when a project config or the
# machine-global consent index is itself unreadable/unparseable/wrong-shaped/unusable
# (``CONFIG_FAULT_KINDS``). Every checkout in this suite writes well-formed YAML, so that
# renderer's precondition never fires here -- these strings would appear only if the new
# block were (incorrectly) routed through it, which is exactly the regression H-A names.
_REPAIR_SYNTAX_TEXT = "REPAIR THE FILE'S SYNTAX"
_NOT_ABSENCE_TEXT = "This is NOT a missing consent record"


# --------------------------------------------------------------------------- #
# Fixtures and checkout builders
# --------------------------------------------------------------------------- #


@pytest.fixture(autouse=True)
def doctor_environment(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Isolated HOME, no network, no daemon scan -- the house pattern for driving `doctor`
    through the CLI (mirrors ``test_sync_doctor_consent_health_3030.py``'s ``checkout``
    fixture). Does not chdir on its own: several tests drive multiple checkouts from one
    test function, each chdir-ing explicitly via :func:`_run_doctor`.
    """
    from specify_cli.auth.manager import reset_token_manager

    reset_token_manager()
    home = tmp_path / "home"
    home.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("SPEC_KITTY_HOME", str(home))
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "AppData"))
    monkeypatch.setenv("COLUMNS", _WIDE_TERMINAL)
    monkeypatch.delenv("SPEC_KITTY_ENABLE_SAAS_SYNC", raising=False)
    monkeypatch.delenv("SPEC_KITTY_SAAS_URL", raising=False)
    # Never inherited: an ambient override would make every checkout resolve to the same
    # root regardless of which directory was actually chdir-ed into (`core/paths.py`'s
    # env-var tier is checked before the walk-up).
    monkeypatch.delenv("SPECIFY_REPO_ROOT", raising=False)
    monkeypatch.setattr(
        sync_module, "_check_server_connection", lambda _url: ("[dim]Disabled[/dim]", "")
    )
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
        yield home
    finally:
        reset_token_manager()


def _flat(output: str) -> str:
    return " ".join(output.split())


def _project_block(project_uuid: str) -> str:
    return (
        "project:\n"
        f"  uuid: {project_uuid}\n"
        "  slug: wp06-tracker-egress-suite\n"
        "  node_id: node00000001\n"
        "  repo_slug: spec-kitty-tests/wp06-tracker-egress-suite\n"
        f"  build_id: {project_uuid}\n"
    )


def _make_checkout(
    tmp_path: Path,
    name: str,
    *,
    has_identity: bool,
    sync_block: str = "",
    tracker_egress: str | None = None,
) -> Path:
    """Build one isolated checkout with a fresh, never-reused project uuid."""
    root = tmp_path / name
    (root / ".kittify").mkdir(parents=True, exist_ok=True)
    parts: list[str] = []
    if has_identity:
        parts.append(_project_block(str(uuid_module.uuid4())))
    if sync_block:
        parts.append(sync_block)
    if tracker_egress is not None:
        parts.append(f"tracker:\n  egress: {tracker_egress}\n")
    (root / ".kittify" / "config.yaml").write_text("".join(parts), encoding="utf-8")
    return root


def _egress_refused_checkout(tmp_path: Path) -> Path:
    return _make_checkout(
        tmp_path, "egress-refused", has_identity=True, sync_block=_SYNC_ENABLED_TRUE, tracker_egress="refused"
    )


def _egress_fault_checkout(tmp_path: Path) -> Path:
    return _make_checkout(
        tmp_path, "egress-fault", has_identity=True, sync_block=_SYNC_ENABLED_TRUE, tracker_egress="refuse"
    )


def _channel1_recorded_refusal_checkout(tmp_path: Path) -> Path:
    return _make_checkout(tmp_path, "channel1-recorded-refusal", has_identity=True, sync_block=_SYNC_ENABLED_FALSE)


def _channel1_no_record_checkout(tmp_path: Path) -> Path:
    return _make_checkout(tmp_path, "channel1-no-record", has_identity=True)


def _channel1_not_consentable_checkout(tmp_path: Path) -> Path:
    return _make_checkout(tmp_path, "channel1-not-consentable", has_identity=False)


def _channel2_permitted_channel1_absent_checkout(tmp_path: Path) -> Path:
    return _make_checkout(tmp_path, "channel2-permitted-channel1-absent", has_identity=True, tracker_egress="permitted")


def _fully_permitted_checkout(tmp_path: Path) -> Path:
    return _make_checkout(tmp_path, "fully-permitted", has_identity=True, sync_block=_SYNC_ENABLED_TRUE)


@dataclass(frozen=True)
class _CheckoutSpec:
    label: str
    builder: Callable[[Path], Path]


#: The seven checkouts SC-014 counts, in the WP06 prompt's own order. Checkout index 5
#: (0-based) is the discriminating case (SC-014's "checkout 6", 1-based in the prompt).
_CHECKOUTS: tuple[_CheckoutSpec, ...] = (
    _CheckoutSpec("tracker.egress: refused", _egress_refused_checkout),
    _CheckoutSpec("tracker-key fault (near-miss value)", _egress_fault_checkout),
    _CheckoutSpec("Channel-1 recorded refusal, no tracker key", _channel1_recorded_refusal_checkout),
    _CheckoutSpec("Channel-1 absent (no record), no tracker key", _channel1_no_record_checkout),
    _CheckoutSpec("Channel-1 not consentable, no tracker key", _channel1_not_consentable_checkout),
    _CheckoutSpec("tracker.egress: permitted, Channel-1 absent", _channel2_permitted_channel1_absent_checkout),
    _CheckoutSpec("fully permitted", _fully_permitted_checkout),
)

_DISCRIMINATING_CHECKOUT_INDEX = 5  # SC-014's checkout 6, 0-based here.


def _run_doctor(repo: Path, monkeypatch: pytest.MonkeyPatch) -> str:
    from specify_cli.auth.manager import reset_token_manager
    from specify_cli.event_journal.journal import reset_journal_cache

    reset_token_manager()
    reset_journal_cache()
    monkeypatch.chdir(repo)
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0, result.output
    return result.output


# --------------------------------------------------------------------------- #
# Row extraction -- controlled below in test_row_extraction_helper_is_controlled
# --------------------------------------------------------------------------- #


def _tracker_egress_section(output: str) -> str:
    """The new block's own slice of `doctor`'s output.

    Raises a named ``AssertionError`` if the block is absent -- the red-first
    consequence T033 asks for: a missing section fails loudly here rather than
    producing a silently-empty row dict downstream. Named rather than the bare
    ``ValueError`` a plain ``str.index`` would raise (review round 1, LOW-2): a bare
    ``ValueError: substring not found`` cannot be told apart from "the section was
    renamed out from under this probe" without reading this function's source; the
    message below carries that diagnosis at the call site instead.
    """
    assert "Tracker egress" in output, (
        "the 'Tracker egress' block is absent from doctor's output -- either the "
        "renderer did not run, or the section heading was renamed and this probe's "
        "own literal needs to move with it"
    )
    start = output.index("Tracker egress")
    rest = output[start:]
    end = rest.find("\nIssues found:")
    return rest if end == -1 else rest[:end]


def _extract_rows(section: str) -> dict[str, str]:
    """Map each destination's on-disk value to its own row's raw text block.

    A row's block is its header line plus every following line up to the next header (so
    a rich-wrapped continuation line is folded into the row it continues).
    """
    rows: dict[str, list[str]] = {}
    current: str | None = None
    for line in section.splitlines():
        match = _ROW_HEADER_RE.match(line)
        if match:
            current = match.group(1)
            rows[current] = [line]
        elif current is not None:
            rows[current].append(line)
    return {key: "\n".join(value) for key, value in rows.items()}


def test_row_extraction_helper_is_controlled(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Control the diagnostic before trusting it (T033 item 7).

    Positive control: a real, fully-permitted checkout's rendered output, whose two rows'
    content is already known from direct inspection, must extract to exactly 2 rows, both
    reporting ``permitted``. Negative control: text with no ``Tracker egress`` heading at
    all must raise, not silently return an empty mapping -- the exact failure shape T033
    calls the "red first" consequence.
    """
    repo = _fully_permitted_checkout(tmp_path)
    output = _run_doctor(repo, monkeypatch)

    section = _tracker_egress_section(output)
    rows = _extract_rows(section)

    assert set(rows) == {"local_subprocess", "hosted_service"}, "positive control: known-good output must yield 2 rows"
    for destination_value, row_text in rows.items():
        flat_row = _flat(row_text)
        assert flat_row.startswith(f"{destination_value} permitted"), (
            "positive control: a fully-permitted checkout's own row must report `permitted`"
        )

    with pytest.raises(AssertionError, match="Tracker egress"):
        _tracker_egress_section("Sync Doctor\n\nConsent record readability\n  this checkout  readable\n")


# --------------------------------------------------------------------------- #
# The main suite: all 7 checkouts, 14 rows, field-for-field
# --------------------------------------------------------------------------- #


def _assert_row_matches_verdict(row_text: str, verdict: TrackerEgressVerdict) -> None:
    """Field-for-field equality between the rendered row and the independently-enforced
    verdict (US7 sc4, SC-014): the reported answer and the enforced answer must come from
    the same function called with the same destination literal, and this is what proves it.
    """
    flat_row = _flat(row_text)
    expected_verb = "REFUSED" if verdict.refused else "permitted"
    assert flat_row.startswith(f"{verdict.destination.value} {expected_verb}"), (
        f"row header must report the verdict's own `refused` field: {flat_row!r}"
    )

    for channel in (CHANNEL_1, CHANNEL_2):
        if channel in verdict.refusing_channels:
            assert channel in flat_row, f"refusing channel {channel!r} must be named: {flat_row!r}"
    if not verdict.refusing_channels:
        assert "refusing channel(s)" not in flat_row, "a non-refusing verdict must not claim a refusing channel"

    # Rendered from the field via the renderer's own lookup table, never re-derived here.
    expected_state_wording = sync_module._CHANNEL1_STATE_WORDING[verdict.channel1_state]
    assert expected_state_wording in flat_row, (
        f"Channel-1 state {verdict.channel1_state!r} must render as {expected_state_wording!r}: {flat_row!r}"
    )

    assert _flat(verdict.message) in flat_row, f"verdict.message must be rendered verbatim: {flat_row!r}"

    for remedy in verdict.remedies:
        assert _flat(remedy) in flat_row, f"remedy {remedy!r} must be rendered: {flat_row!r}"


def test_all_seven_checkouts_render_two_verdict_true_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SC-014's core claim, over all seven checkouts at once.

    Asserts, per checkout: the block is printed (would raise otherwise, see
    ``_tracker_egress_section``); exactly 2 rows exist; each row's content is
    field-for-field equal to the independently-computed enforced verdict at the same
    destination; the fault row (checkout 2) names the offending value and both legal
    values verbatim (C-020); and none of the four negative pins fire.

    Then asserts the totals -- 7 checkouts, 14 rows -- explicitly and non-vacuously, and
    separately asserts checkout 6's two rows disagree (the case a one-row block cannot
    express).
    """
    checkouts_rendered = 0
    rows_asserted = 0
    combined_output_for_negative_pins: list[str] = []

    discriminating_refused: dict[str, bool] = {}

    for index, spec in enumerate(_CHECKOUTS):
        repo = spec.builder(tmp_path)
        output = _run_doctor(repo, monkeypatch)
        combined_output_for_negative_pins.append(output)

        section = _tracker_egress_section(output)
        rows = _extract_rows(section)
        assert len(rows) == 2, f"{spec.label}: expected exactly 2 rows, got {sorted(rows)}"  # golden-count: cardinality-is-contract
        checkouts_rendered += 1

        for destination in DESTINATIONS:
            verdict = tracker_egress_verdict(repo, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
            row_text = rows[destination.value]
            _assert_row_matches_verdict(row_text, verdict)
            rows_asserted += 1

            if index == _DISCRIMINATING_CHECKOUT_INDEX:
                discriminating_refused[destination.value] = verdict.refused

        if index == 1:  # the tracker-key fault checkout (C-020)
            fault_verdict = tracker_egress_verdict(
                repo,
                destination=EgressDestination.LOCAL_SUBPROCESS,
                identifiers=_IDENTIFIERS_FOR[EgressDestination.LOCAL_SUBPROCESS],
            )
            flat_row = _flat(rows[EgressDestination.LOCAL_SUBPROCESS.value])
            assert repr("refuse") in flat_row, "the offending raw value must be quoted verbatim"
            assert repr("refused") in flat_row, "the legal value 'refused' must be named"
            assert repr("permitted") in flat_row, "the legal value 'permitted' must be named"
            assert fault_verdict.channel2_raw == "refuse"

    print(f"non-vacuity: {checkouts_rendered} checkouts rendered, {rows_asserted} rows asserted")
    assert checkouts_rendered == 7, "SC-014 pins exactly seven checkouts"
    assert rows_asserted == 14, "SC-014 pins exactly fourteen rows"

    # Checkout 6 (SC-014): the same moment, two different answers -- the assertion a
    # one-row block cannot satisfy.
    assert discriminating_refused == {"local_subprocess": False, "hosted_service": True}, (
        "checkout 6 must render permitted-local / refused-hosted, not the same answer twice"
    )

    flat_all = _flat("\n".join(combined_output_for_negative_pins))
    assert _NOT_ABSENCE_TEXT not in flat_all, "the new block must never emit the readability fault's fixed sentence"
    assert flat_all.count(_REPAIR_SYNTAX_TEXT) == 0, "the new block must contribute 0 to this count in every checkout"
    assert "UNREADABLE" not in flat_all, "the new block must never announce a readable config as UNREADABLE"


# --------------------------------------------------------------------------- #
# The root=None case -- asserted, deliberately OUTSIDE the seven (T033 item 8)
# --------------------------------------------------------------------------- #


def test_root_none_renders_two_undetermined_refused_rows_outside_any_checkout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``locate_project_root(Path.cwd())`` returning ``None`` is a specified case, not an
    error path (the verdict function never raises, NFR-003).

    This is an **eighth** case, counted here and reported separately -- SC-014's own 7/14
    counts stay literal and unaffected by this test. Without this assertion the only place
    ``root=None`` at ``LOCAL_SUBPROCESS`` was exercised was WP03's unit pin; this is what
    proves the renderer that makes that cell reachable in production does not raise, does
    not drop the block, and does not render it identically to a permitted checkout.
    """
    outside = tmp_path / "not-a-checkout"
    outside.mkdir()
    output = _run_doctor(outside, monkeypatch)

    section = _tracker_egress_section(output)
    rows = _extract_rows(section)
    assert len(rows) == 2, "the block must still carry two rows outside any checkout"  # golden-count: cardinality-is-contract
    print("root=None case: 1 invocation, 2 rows (excluded from the 7/14 totals above)")

    for destination in DESTINATIONS:
        verdict = tracker_egress_verdict(None, destination=destination, identifiers=_IDENTIFIERS_FOR[destination])
        _assert_row_matches_verdict(rows[destination.value], verdict)
        assert verdict.refused is True
        assert verdict.channel1_state == "undetermined"

    flat_section = _flat(section)
    assert _NOT_ABSENCE_TEXT not in flat_section
    assert _REPAIR_SYNTAX_TEXT not in flat_section
    # Must not render identically to a permitted checkout (H-F): neither row ever says
    # "permitted" -- both are REFUSED, with the undetermined wording, not the not_consentable
    # one (whose `spec-kitty init` remedy would be wrong advice for a directory that resolves
    # no checkout at all).
    assert "permitted" not in flat_section.lower()
    assert "spec-kitty init" not in flat_section


# --------------------------------------------------------------------------- #
# Focused, non-CLI tests executing the new helpers directly (NFR-005): every
# branch, including the one branch unreachable through `tracker_egress_verdict`
# itself, exercised without `doctor`'s own CLI-level setup cost.
# --------------------------------------------------------------------------- #


class _CapturingConsole:
    """A minimal ``console_out`` stand-in: collects printed strings, nothing else."""

    def __init__(self) -> None:
        self.lines: list[str] = []

    def print(self, text: str = "") -> None:
        self.lines.append(text)

    @property
    def text(self) -> str:
        return "\n".join(self.lines)


_RICH_MARKUP_RE = re.compile(r"\[/?[a-zA-Z_ ]+\]")


def _strip_markup(text: str) -> str:
    """Drop rich's ``[tag]``/``[/tag]`` markup.

    ``_CapturingConsole`` is a bare stand-in, not a real ``rich.console.Console`` --
    the CLI-level tests never need this because the real ``Console`` strips markup
    itself when writing to a non-tty, but a fake collector stores the raw markup
    verbatim.
    """
    return _RICH_MARKUP_RE.sub("", text)


def _render_row(
    verdict: TrackerEgressVerdict, *, binding_present: bool = True
) -> tuple[str, list[str]]:
    """Render one row directly.

    ``binding_present`` defaults to ``True`` -- these cells are about the row's own
    content and its issue-append, so they assume a bound tracker. The unbound case
    (rows still render, no issue raised) is pinned separately below.
    """
    console_out = _CapturingConsole()
    issues: list[str] = []
    sync_module._render_tracker_egress_row(
        console_out, issues, verdict, binding_present=binding_present
    )
    return _flat(_strip_markup(console_out.text)), issues


class TestRenderTrackerEgressRowDirectly:
    """Direct calls to ``_render_tracker_egress_row`` with hand-built verdicts -- the
    row-rendering branches, isolated from ``tracker_egress_verdict``'s own construction
    and from the CLI runner's startup cost."""

    def test_refused_row_names_every_refusing_channel_and_appends_one_issue(self) -> None:
        verdict = TrackerEgressVerdict(
            refused=True,
            refusing_channels=frozenset({CHANNEL_1, CHANNEL_2}),
            destination=EgressDestination.LOCAL_SUBPROCESS,
            channel1_state=CHANNEL1_RECORDED_REFUSAL,
            channel2_state="refused",
            channel2_raw="refused",
            message="synthetic refusal message",
            remedies=("do X", "or do Y"),
        )
        flat_row, issues = _render_row(verdict)

        assert flat_row.startswith("local_subprocess REFUSED")
        assert CHANNEL_1 in flat_row
        assert CHANNEL_2 in flat_row
        assert "a refusal is recorded for this project" in flat_row
        assert "synthetic refusal message" in flat_row
        assert "do X" in flat_row
        assert "or do Y" in flat_row
        assert len(issues) == 1  # golden-count: cardinality-is-contract
        assert "synthetic refusal message" in issues[0]

    def test_permitted_row_has_no_refusing_channel_line_and_appends_no_issue(self) -> None:
        verdict = TrackerEgressVerdict(
            refused=False,
            refusing_channels=frozenset(),
            destination=EgressDestination.HOSTED_SERVICE,
            channel1_state=CHANNEL1_GRANTED,
            channel2_state="absent",
            channel2_raw=object(),
            message="synthetic permit message",
            remedies=(),
        )
        flat_row, issues = _render_row(verdict)

        assert flat_row.startswith("hosted_service permitted")
        assert "refusing channel(s)" not in flat_row
        assert "synthetic permit message" in flat_row
        assert issues == []

    def test_unrecognised_channel1_state_falls_back_to_the_raw_state_string(self) -> None:
        """Defensive-only branch (the ``.get(..., state)`` fallback): the six-member
        ``channel1_state`` set is closed, so ``tracker_egress_verdict`` itself can never
        produce this value -- but the renderer must not raise or render nothing if a
        state is ever added to the source module and this table is not updated to match.
        """
        verdict = TrackerEgressVerdict(
            refused=True,
            refusing_channels=frozenset({CHANNEL_1}),
            destination=EgressDestination.LOCAL_SUBPROCESS,
            channel1_state="a_future_state_not_in_the_table",
            channel2_state="absent",
            channel2_raw=object(),
            message="synthetic message",
            remedies=(),
        )
        flat_row, _issues = _render_row(verdict)

        assert "a_future_state_not_in_the_table" in flat_row


class TestRenderTrackerEgressDirectly:
    """Direct calls to ``_render_tracker_egress`` itself -- the two literal calls and the
    root resolution, against a real checkout, without `doctor`'s own auth/daemon/network
    setup cost."""

    def test_prints_the_section_title_and_two_rows_for_a_real_checkout(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        repo = _fully_permitted_checkout(tmp_path)
        monkeypatch.chdir(repo)
        console_out = _CapturingConsole()
        issues: list[str] = []

        sync_module._render_tracker_egress(console_out, issues)

        flat_text = _flat(_strip_markup(console_out.text))
        assert sync_module._TRACKER_EGRESS_SECTION_TITLE in flat_text
        assert "local_subprocess permitted" in flat_text
        assert "hosted_service permitted" in flat_text
        assert issues == []


# --------------------------------------------------------------------------- #
# HIGH-1 (review round 1): the fault row renders an operator-controlled string
# through rich markup. C-020 requires ``verdict.message`` to quote the offending
# ``tracker.egress`` value **verbatim** (``repr(raw)``), so that value can legally
# contain ``[`` / ``]`` -- and this is a ``rich`` surface. Unescaped, ``'[refused]'``
# reads back as a colour tag and is silently erased (C-020 becomes a false
# statement about the operator's own file), and ``'[/bold]'`` is an unmatched
# closing tag that raises ``MarkupError`` out of `doctor` entirely. A real
# ``rich.console.Console`` is used here, not ``_CapturingConsole``: the defect is
# in rich's own markup interpreter, and a fake collector that never parses
# markup cannot reproduce it -- this is the "vary the offending value's shape"
# ratchet, exercised as a direct ``_render_tracker_egress_row`` case rather than
# an eighth SC-014 checkout.
# --------------------------------------------------------------------------- #


_BRACKET_SHAPED_OFFENDING_VALUES: tuple[str, ...] = (
    "[refused]",  # silent-erasure shape: reads back as a bare colour tag
    "[/bold]",  # crash shape: an unmatched closing tag
    "[bold]refused[/bold]",  # both open and close tags in one value
)


def _render_fault_row_through_a_real_console(offending: object) -> tuple[str, str]:
    """Render one Channel-2-fault row through a genuine ``rich.console.Console``
    (non-tty, colour disabled) so the escape-then-render round trip is real, not
    merely "a backslash was inserted somewhere".

    Also renders the captured ``issues`` entry through a **second**, independent
    ``Console`` -- reproducing ``doctor()``'s own summary loop
    (``console.print(f"  [yellow]![/yellow] {issue}")``) rather than inspecting the
    ``issues`` string's raw (still-escaped) bytes directly. The entry is deliberately
    stored pre-escaped so *that* render is also safe; asserting on the raw string
    would be asserting the wrong thing -- the escape is only meant to disappear once
    rich has parsed it.
    """
    import io

    from rich.console import Console

    verdict = TrackerEgressVerdict(
        refused=True,
        refusing_channels=frozenset({CHANNEL_2}),
        destination=EgressDestination.HOSTED_SERVICE,
        channel1_state=CHANNEL1_GRANTED,
        channel2_state="fault",
        channel2_raw=offending,
        message=(
            f"Channel 2 refused: tracker.egress is set to {offending!r}, which is not a "
            "legal value; refusing tracker egress to hosted_service (legal values are "
            "'refused' and 'permitted')"
        ),
        remedies=(),
    )
    row_buf = io.StringIO()
    console_out = Console(file=row_buf, force_terminal=False, no_color=True, width=300)
    issues: list[str] = []
    sync_module._render_tracker_egress_row(
        console_out, issues, verdict, binding_present=True
    )  # must not raise
    assert len(issues) == 1, f"expected exactly one issues entry, got {issues!r}"  # golden-count: cardinality-is-contract

    summary_buf = io.StringIO()
    summary_console = Console(file=summary_buf, force_terminal=False, no_color=True, width=300)
    summary_console.print(f"  ! {issues[0]}")  # doctor()'s own summary-loop render, reproduced
    return row_buf.getvalue(), summary_buf.getvalue()


class TestUnparseableConfigDoesNotAbortDoctor:
    """The binding probe must not raise on a broken config -- `doctor` exists for that case.

    Regression pin (CI, fast-tests-cli). `load_tracker_config` RAISES on an unparseable
    `.kittify/config.yaml`. The unguarded probe added for the unbound-issue gate aborted
    the whole command mid-render, measured as `test_sync_doctor_consent_health_3030`'s
    `REPAIR THE FILE'S SYNTAX` count dropping 4 -> 2 because every line after this block
    stopped printing.

    Same class as WP03 review round 1 HIGH-1: `tracker_egress_verdict` is defended
    internally (NFR-003), and a *second*, direct config read was not. The pin is here
    rather than only in the consent-health suite because this block is what breaks it.
    """

    def test_unparseable_config_still_renders_both_rows(self, tmp_path: Path) -> None:
        root = tmp_path / "broken"
        (root / ".kittify").mkdir(parents=True)
        (root / ".kittify" / "config.yaml").write_text(
            "project:\n  uuid: [unclosed\n", encoding="utf-8"
        )
        console_out = _CapturingConsole()
        issues: list[str] = []
        monkey = pytest.MonkeyPatch()
        try:
            monkey.chdir(root)
            sync_module._render_tracker_egress(console_out, issues)
        finally:
            monkey.undo()
        flat = _flat(_strip_markup(console_out.text))
        assert sync_module._TRACKER_EGRESS_SECTION_TITLE in flat, "the block must render at all"
        assert flat.count("REFUSED") == 2, flat  # golden-count: cardinality-is-contract


class TestUnboundCheckoutRaisesNoIssue:
    """A checkout with no tracker bound renders both rows but reports no *issue*.

    Regression pin (CI, fast-tests-sync): `issues` drives `doctor`'s problem summary,
    and appending unconditionally told every unbound project something was wrong with
    it -- absence of both channels refuses a transmission nothing is attempting. It
    broke `tests/sync/test_sync_doctor.py::TestDoctorCommand::test_doctor_healthy`,
    which mocks doctor's dependencies heavily but still resolves the real checkout, so
    this renderer's contribution depended on ambient state.

    The rows must still say REFUSED: suppressing them would rebuild the false green
    where "tracker egress is fine" and "I never looked" render identically.
    """

    def test_unbound_renders_the_refusal_but_appends_no_issue(self) -> None:
        verdict = TrackerEgressVerdict(
            refused=True,
            refusing_channels=frozenset({CHANNEL_1, CHANNEL_2}),
            destination=EgressDestination.LOCAL_SUBPROCESS,
            channel1_state=CHANNEL1_RECORDED_REFUSAL,
            channel2_state="refused",
            channel2_raw="refused",
            message="synthetic refusal message",
            remedies=("do X",),
        )
        flat, issues = _render_row(verdict, binding_present=False)
        assert "REFUSED" in flat, "the row must still report the refusal"
        assert issues == [], "an unbound checkout has no tracker-egress problem to remediate"

    def test_bound_still_appends_the_issue(self) -> None:
        """Positive control: without it the assertion above passes if issues never fill."""
        verdict = TrackerEgressVerdict(
            refused=True,
            refusing_channels=frozenset({CHANNEL_1, CHANNEL_2}),
            destination=EgressDestination.LOCAL_SUBPROCESS,
            channel1_state=CHANNEL1_RECORDED_REFUSAL,
            channel2_state="refused",
            channel2_raw="refused",
            message="synthetic refusal message",
            remedies=("do X",),
        )
        _flat_text, issues = _render_row(verdict, binding_present=True)
        assert len(issues) == 1, issues  # golden-count: cardinality-is-contract


class TestFaultRowMarkupSafety:
    """HIGH-1: the fix must both (a) preserve C-020's verbatim quote and (b) never
    crash `doctor`, for every bracket-shaped offending value -- not only the
    bracket-free ``"refuse"`` the main suite's C-020 assertion already covers. Both
    the row itself and doctor()'s later summary-loop render of the ``issues`` entry
    are checked, since escaping only the row would move the crash rather than
    removing it (review round 1, HIGH-1).
    """

    @pytest.mark.parametrize("offending", _BRACKET_SHAPED_OFFENDING_VALUES)
    def test_bracket_shaped_value_survives_verbatim_and_does_not_raise(self, offending: str) -> None:
        rendered_row, rendered_summary = _render_fault_row_through_a_real_console(offending)

        assert repr(offending) in rendered_row, (
            f"the offending value must survive verbatim in the printed row: {rendered_row!r}"
        )
        assert repr(offending) in rendered_summary, (
            "the offending value must also survive doctor()'s own summary-loop render "
            f"of the issues entry: {rendered_summary!r}"
        )

    def test_bracket_free_value_is_unaffected_by_the_escape(self) -> None:
        """Positive control: a value with nothing to escape must render identically to
        before the fix -- the escape must be invisible for the common case."""
        rendered_row, rendered_summary = _render_fault_row_through_a_real_console("refuse")
        assert repr("refuse") in rendered_row
        assert repr("refuse") in rendered_summary


def test_channel1_state_wording_is_exhaustive_literal_and_distinct() -> None:
    """MEDIUM-1 (review round 1): pins content and distinctness, not just provenance.

    At ``HOSTED_SERVICE`` all three refusal-flavoured Channel-1 messages are
    byte-identical (FR-016's carve-out) -- ``_CHANNEL1_STATE_WORDING`` is the *only*
    place left that still tells those states apart for an operator.
    ``_assert_row_matches_verdict`` reads this table for its own expectation, which
    pins that the renderer performed the lookup (provenance) but not that the six
    wordings are actually six distinct strings (content): a mutant that collapses
    ``no_record`` and ``not_consentable`` onto one wording, or that swaps
    ``undetermined``'s wording for ``not_consentable``'s -- the exact substitution
    T033 item 8 forbids by name -- passed unnoticed. This test reads the six
    wordings directly and pins both properties, plus exhaustiveness over the six
    exported ``CHANNEL1_*`` constants (LOW-1): a seventh state would otherwise
    degrade silently through the ``.get(..., state)`` fallback with nothing here to
    notice the docstring's exhaustiveness claim had gone stale.
    """
    wording = sync_module._CHANNEL1_STATE_WORDING
    expected_states = {
        CHANNEL1_GRANTED,
        CHANNEL1_NO_RECORD,
        CHANNEL1_RECORDED_REFUSAL,
        CHANNEL1_NOT_CONSENTABLE,
        CHANNEL1_UNCLASSIFIED,
        CHANNEL1_UNDETERMINED,
    }
    assert set(wording) == expected_states, "must be exhaustive over the six exported CHANNEL1_* constants"
    assert len(set(wording.values())) == 6, "all six wordings must be pairwise distinct"  # golden-count: cardinality-is-contract

    assert wording[CHANNEL1_GRANTED] == "hosted-sync consent is granted for this project"
    assert wording[CHANNEL1_NO_RECORD] == "no record of hosted-sync consent exists for this project"
    assert wording[CHANNEL1_RECORDED_REFUSAL] == "a refusal is recorded for this project"
    assert wording[CHANNEL1_NOT_CONSENTABLE] == "not consentable, no project identity resolved"
    assert wording[CHANNEL1_UNCLASSIFIED] == "refuses, but the specific reason could not be classified"
    assert wording[CHANNEL1_UNDETERMINED] == "undetermined -- this directory is not inside a checkout"
