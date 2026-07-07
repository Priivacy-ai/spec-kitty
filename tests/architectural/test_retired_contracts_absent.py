"""Static-arm retirement-verification driver: the retired-contract absence sweep.

This is the CT7 / #2077 payload (spec FR-005, NFR-002; design §5 "Static arm").
For every ``status=retired`` record in the Contract Registry it sweeps the
record's **content anchor** across the record's DECLARED consumer set
(``consumers.scan_roots`` minus ``consumers.exemptions``) and reports any live
occurrence — the residual a test-*run* can never prove (absence of a symbol),
generalising the hand-rolled ``test_no_legacy_*`` family into ONE driver.

Advisory / report-only (v1)
---------------------------
Per FR-005 / NFR-002 (design §6 "What stays advisory vs enforcing in v1") this
arm is **report-only**: a live occurrence emits a
:class:`RetiredContractLiveOccurrenceWarning`, it **NEVER** ``pytest.fail`` /
``assert``\\ s on a live-tree find, so it can never block CI. Enforcement (flip
``advisory -> enforcing`` per proven-stable record) is a deferred follow-up
(design §7 WP6). The module carries ``@pytest.mark.filterwarnings("always")`` on
the live-tree arm so the advisory warning can never be escalated to an error by
a ``-W error`` shard — keeping the "never blocks CI" invariant structural, not a
happenstance of the current warning config.

Anti-vacuity control (mandatory)
--------------------------------
An advisory sweep that never matches would pass with zero findings forever, so
:func:`test_sweep_flags_planted_reappearance_of_each_seeded_record` plants each
seeded record's REAL anchors into a temp consumer tree and asserts the sweep
flags every one. That sub-test DOES assert — it guards the driver's own
correctness, not a live-tree retirement. A companion control proves the sweep
respects exemptions (no over-flag), so parity (WP03) rests on a real envelope.

Content anchoring (DIR-041 / NFR-003)
-------------------------------------
The sweep anchors on **content** — a fixed literal or a dotted symbol — never on
a positional ``file:line``. :func:`test_seeded_anchors_are_content_not_file_line`
pins that using :func:`specify_cli.contracts.anchoring.is_file_line_anchor`, and
:func:`test_loader_rejects_fragment_join_file_line` closes the WP01-review
fragment-join gap (a ``file:line`` split across ``fragments`` that reconstructs
to ``path.py:42``) at the loader before the driver ever consumes a literal.

The forbidden terms modelled by the seeded terminology record are only ever
handled as runtime values reconstructed from the registry — this module never
contains either term verbatim, so it does not trip the very sweep it drives
(mirroring ``test_no_legacy_terminology.py``'s fragment self-flag defence).

WP03 reuse
----------
:func:`sweep_record` and :class:`Finding` are the public detection API the WP03
parity test drives against a fabricated fixture tree.
"""

from __future__ import annotations

import warnings
from collections.abc import Iterator, Sequence
from pathlib import Path
from typing import NamedTuple

import pytest

from specify_cli.contracts.anchoring import is_file_line_anchor
from specify_cli.contracts.registry import (
    ContractAnchor,
    ContractConsumers,
    ContractRecord,
    ContractRegistrySchemaError,
    ContractRetirement,
    ContractVerification,
    load_registry,
    validate_registry,
)

pytestmark = [pytest.mark.architectural]


# A distinctive token that appears nowhere in the live tree — used by the
# exemption / over-flag control so this file never has to embed a real
# forbidden term verbatim.
_SYNTHETIC_TOKEN = "synthetic_retired_token_" + "wp02"


class Finding(NamedTuple):
    """One live occurrence of a retired anchor inside a declared consumer file."""

    record_id: str
    anchor: str  # the matched content string (literal or dotted symbol)
    path: str  # repo-root-relative POSIX path of the consumer file
    lineno: int  # 1-based line number of the occurrence
    line: str  # the matching line, stripped


class RetiredContractLiveOccurrenceWarning(UserWarning):
    """Advisory signal (FR-005 / NFR-002): a retired anchor still appears live.

    Emitted — never raised — by the report-only live-tree sweep. A dedicated
    category lets downstream tooling filter on exactly this signal.
    """


# ---------------------------------------------------------------------------
# The sweep (public detection API — WP03 parity drives this)
# ---------------------------------------------------------------------------


def anchor_needles(record: ContractRecord) -> tuple[str, ...]:
    """Return the record's content anchors as search needles.

    A ``fallback_name`` record anchors on its dotted ``symbol``; a
    ``retired_literal`` record anchors on its reconstructed ``literals``. Both
    are content anchors — never ``file:line`` — so ONE driver serves every
    ``status=retired`` record kind.
    """
    if record.anchor.symbol is not None:
        return (record.anchor.symbol,)
    return record.anchor.literals


def _is_exempt(relpath: str, exemptions: Sequence[str]) -> bool:
    """True when *relpath* falls under any declared ``consumers.exemptions`` fragment."""
    return any(fragment in relpath for fragment in exemptions)


def _iter_consumer_files(scan_dir: Path) -> Iterator[Path]:
    """Yield candidate consumer files under *scan_dir* (compiled caches skipped)."""
    for path in sorted(scan_dir.rglob("*")):
        if path.is_file() and "__pycache__" not in path.parts:
            yield path


def _scan_file(record_id: str, path: Path, relpath: str, needles: tuple[str, ...]) -> list[Finding]:
    """Return every content-anchor occurrence in *path* (binary files skipped)."""
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []  # binary or unreadable — not a text consumer surface
    found: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), start=1):
        for needle in needles:
            if needle in line:
                found.append(Finding(record_id, needle, relpath, lineno, line.strip()))
    return found


def sweep_record(record: ContractRecord, root: Path) -> list[Finding]:
    """Sweep *record*'s content anchor across its declared consumer set under *root*.

    Scans every file under each ``consumers.scan_roots`` entry (resolved relative
    to *root*), skipping any path matching a ``consumers.exemptions`` fragment,
    and returns each live occurrence of the record's anchor. Content-anchored
    (fixed literal or dotted symbol), never ``file:line`` (DIR-041 / NFR-003).
    """
    needles = anchor_needles(record)
    exemptions = record.consumers.exemptions
    findings: list[Finding] = []
    for scan_root in record.consumers.scan_roots:
        scan_dir = root / scan_root
        if not scan_dir.exists():
            continue
        for path in _iter_consumer_files(scan_dir):
            relpath = path.relative_to(root).as_posix()
            if _is_exempt(relpath, exemptions):
                continue
            findings.extend(_scan_file(record.id, path, relpath, needles))
    return findings


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    """Resolve the repo root by walking up to a ``.kittify/`` marker."""
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        if (parent / ".kittify").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root (no .kittify/ marker found).")


def _retired_records() -> list[ContractRecord]:
    """Every ``status=retired`` record in the seeded Contract Registry."""
    return [record for record in load_registry(_repo_root()) if record.status == "retired"]


def _synthetic_retired_record(
    *, needle: str, scan_root: str, exemptions: tuple[str, ...]
) -> ContractRecord:
    """A minimal, in-memory ``retired_literal`` record for temp-tree control tests."""
    return ContractRecord(
        id="test.synthetic-retired",
        kind="retired_literal",
        anchor=ContractAnchor(symbol=None, literals=(needle,)),
        status="retired",
        owner="#2441",
        replaced_by="specify_cli.something.canonical",
        retirement=ContractRetirement("3.0.0", "3.4.0", "#2077"),
        consumers=ContractConsumers(scan_roots=(scan_root,), exemptions=exemptions),
        verification=ContractVerification(enforcement="advisory"),
    )


def _well_formed_record_dict() -> dict[str, object]:
    """A schema-valid ``retired_literal`` record dict (the positive-control base)."""
    return {
        "id": "test.synthetic-literal",
        "kind": "retired_literal",
        "anchor": {"literals": [{"value": "synthetic_retired_token"}]},
        "status": "retired",
        "owner": "#2441",
        "replaced_by": "specify_cli.something.canonical",
        "retirement": {
            "introduced_in": "3.0.0",
            "removal_target": "3.4.0",
            "tracker_issue": "#2077",
        },
        "consumers": {"scan_roots": ["src"], "exemptions": []},
        "verification": {"enforcement": "advisory"},
    }


def _format_report(record: ContractRecord, findings: list[Finding]) -> str:
    body = "\n  ".join(f"{f.path}:{f.lineno}: {f.line}" for f in findings)
    return (
        f"[advisory] retired contract {record.id!r} (owner {record.owner}) still "
        f"appears in {len(findings)} live location(s); migrate to "
        f"{record.replaced_by!r}:\n  {body}"
    )


# ---------------------------------------------------------------------------
# The advisory live-tree sweep (report-only — FR-005 / NFR-002)
# ---------------------------------------------------------------------------


@pytest.mark.filterwarnings("always")
def test_retired_anchors_absence_sweep_is_advisory() -> None:
    """Sweep every seeded ``status=retired`` record; REPORT live finds, never block.

    The ``filterwarnings("always")`` mark makes the advisory warning immune to
    ``-W error`` escalation, so this arm can never turn a live-tree find into a
    CI failure — enforcement is deferred (design §7 WP6). The only assertion here
    guards the driver's INPUT (at least one retired record exists, so the sweep
    is not vacuously green); it does NOT assert on any live-tree finding.
    """
    records = _retired_records()
    assert records, (
        "no status=retired record in the Contract Registry — the absence sweep "
        "would run over empty input and pass vacuously. This asserts the driver's "
        "INPUT is non-empty; it does NOT assert on any live-tree occurrence."
    )
    for record in records:
        findings = sweep_record(record, _repo_root())
        if findings:
            warnings.warn(
                _format_report(record, findings),
                RetiredContractLiveOccurrenceWarning,
                stacklevel=2,
            )
    # No assert on `findings`: this arm is report-only (FR-005 / NFR-002).


# ---------------------------------------------------------------------------
# Anti-vacuity + envelope controls (these DO assert — they guard the driver)
# ---------------------------------------------------------------------------


def test_sweep_flags_planted_reappearance_of_each_seeded_record(tmp_path: Path) -> None:
    """MANDATORY anti-vacuity control: the sweep BITES on a planted reappearance.

    For each seeded ``status=retired`` record, plant its REAL content anchors
    into a temp consumer tree and assert the sweep flags every one. Proves the
    driver cannot be vacuously green. The real forbidden terms are only ever
    runtime values here (loaded from the registry, written into ``tmp_path``
    which the live gates never scan) — this source stays term-free.
    """
    records = _retired_records()
    assert records, "expected seeded status=retired records to plant"
    for record in records:
        needles = anchor_needles(record)
        scan_root = record.consumers.scan_roots[0]
        planted = tmp_path / scan_root / "planted_reappearance.py"
        planted.parent.mkdir(parents=True, exist_ok=True)
        planted.write_text(
            "\n".join(f"legacy_use_{i} = {needle!r}" for i, needle in enumerate(needles)) + "\n",
            encoding="utf-8",
        )
        findings = sweep_record(record, tmp_path)
        flagged = {f.anchor for f in findings}
        assert set(needles) <= flagged, (
            f"sweep failed to flag planted reappearance of {record.id}: "
            f"needles={needles!r} flagged={flagged!r}"
        )
        assert all(f.path == f"{scan_root}/planted_reappearance.py" for f in findings)


def test_sweep_respects_exemptions_no_over_flag(tmp_path: Path) -> None:
    """The sweep IGNORES an occurrence under an exempted path (no over-flag).

    A token planted under a scan root but inside an exemption fragment must NOT
    be flagged, while one outside the exemption MUST — proving the
    scan_roots-minus-exemptions envelope is honoured (the property WP03 parity
    depends on). Uses a synthetic token, so this file embeds no forbidden term.
    """
    record = _synthetic_retired_record(
        needle=_SYNTHETIC_TOKEN, scan_root="src", exemptions=("src/vendor/",)
    )
    live = tmp_path / "src" / "app" / "module.py"
    live.parent.mkdir(parents=True, exist_ok=True)
    live.write_text(f"x = {_SYNTHETIC_TOKEN!r}\n", encoding="utf-8")
    exempt = tmp_path / "src" / "vendor" / "lib.py"
    exempt.parent.mkdir(parents=True, exist_ok=True)
    exempt.write_text(f"y = {_SYNTHETIC_TOKEN!r}\n", encoding="utf-8")

    findings = sweep_record(record, tmp_path)
    flagged_paths = {f.path for f in findings}
    assert "src/app/module.py" in flagged_paths, "live occurrence must be flagged"
    assert "src/vendor/lib.py" not in flagged_paths, "exempted occurrence must be ignored"


def test_sweep_flags_symbol_anchor_reappearance(tmp_path: Path) -> None:
    """The driver anchors a ``fallback_name`` dotted symbol on content too.

    Covers the symbol arm of :func:`anchor_needles` so a single driver serves
    every ``status=retired`` record kind, not just ``retired_literal``.
    Content-anchored on the dotted name — never ``file:line``.
    """
    symbol = "specify_cli.legacy.retired_symbol"
    record = ContractRecord(
        id="test.synthetic-symbol",
        kind="fallback_name",
        anchor=ContractAnchor(symbol=symbol, literals=()),
        status="retired",
        owner="#2441",
        replaced_by="specify_cli.status.emit.emit_status_transition",
        retirement=ContractRetirement("3.0.0", "3.4.0", "#2077"),
        consumers=ContractConsumers(scan_roots=("src",), exemptions=()),
        verification=ContractVerification(enforcement="advisory"),
    )
    planted = tmp_path / "src" / "caller.py"
    planted.parent.mkdir(parents=True, exist_ok=True)
    planted.write_text(f"value = {symbol}()\n", encoding="utf-8")

    findings = sweep_record(record, tmp_path)
    assert any(f.anchor == symbol and f.path == "src/caller.py" for f in findings), (
        "sweep must flag a planted dotted-symbol reappearance"
    )


def test_seeded_anchors_are_content_not_file_line() -> None:
    """Every seeded retired anchor is content (symbol/literal), never ``file:line``.

    The driver anchors on content (DIR-041 / NFR-003); it must never consume a
    positional ``file:line``. Guards with the shared anchoring primitive so a
    record that reintroduced ``path.py:42`` anchoring would red here.
    """
    records = _retired_records()
    assert records, "expected seeded status=retired records to check"
    for record in records:
        for needle in anchor_needles(record):
            assert not is_file_line_anchor(needle), (
                f"{record.id} anchor {needle!r} is a positional file:line anchor; "
                f"the driver must anchor on content only (DIR-041 / NFR-003)"
            )


# ---------------------------------------------------------------------------
# WP01-review hardening: fragment-join file:line rejection (red-first)
# ---------------------------------------------------------------------------


def test_loader_rejects_fragment_join_file_line() -> None:
    """A ``file:line`` split across ``fragments`` must be rejected by the loader.

    WP01-review gap: ``["src/foo.py", ":42"]`` reconstructs to ``src/foo.py:42``
    — a positional anchor that slips past the per-fragment guard (each fragment
    is individually benign). Because the driver makes literals anchor-consumed,
    the loader MUST reject a fragment-join that reconstructs a ``file:line``
    before the sweep ever anchors on it (DIR-041 / NFR-003). Red-first: this
    fails against the un-hardened ``_validate_literal_entry``.
    """
    record = _well_formed_record_dict()
    record["anchor"] = {"literals": [{"fragments": ["src/specify_cli/foo.py", ":42"]}]}
    with pytest.raises(ContractRegistrySchemaError) as exc_info:
        validate_registry({"contracts": [record]})
    assert any("file:line" in e or "DIR-041" in e for e in exc_info.value.errors), (
        "fragment-join reconstructing a file:line must be rejected as positional anchoring"
    )


def test_loader_accepts_benign_fragment_join() -> None:
    """Positive control: a benign fragment-join (no line number) still validates.

    Ensures the fragment-join ``file:line`` guard does not over-reject the
    legitimate self-flag-defence fragment form the terminology record relies on.
    """
    record = _well_formed_record_dict()
    # "cere" + "mony" reconstructs a benign term (no trailing :<line>), so it is
    # NOT a file:line anchor and must pass. Built from fragments here too, so this
    # source never contains the term verbatim.
    record["anchor"] = {"literals": [{"fragments": ["cere", "mony"]}]}
    validate_registry({"contracts": [record]})  # must not raise
