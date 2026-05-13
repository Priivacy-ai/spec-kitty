"""Coverage supplements for ``src/charter/_io.py`` edge paths introduced by
WP06 of mission ``review-merge-gate-hardening-3-2-x-01KRC57C``.

The main behavioral tests live in:
  - ``tests/charter/test_encoding_chokepoint.py``
  - ``tests/charter/test_unsafe_bypass.py``
  - ``tests/charter/test_provenance_dual_storage.py``
  - ``tests/charter/test_call_site_propagation.py``

This file adds narrow coverage for the smaller branches those scenario
tests do not reach:

- ``load_charter_bytes`` (inline-byte ingest API; not yet used by production
  call sites but part of the public chokepoint surface).
- BOM-prefixed input (UTF-8 BOM detection branch).
- ``CharterEncodingError`` attribute contract (``code``, ``body``,
  ``diagnostic`` enum reference, isinstance with KittyInternalConsistencyError).
- ``_build_ambiguous_body`` output shape (file path + remediation steps).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from charter._diagnostics import CharterEncodingDiagnostic
from charter import _io
from charter._io import CharterContent, CharterEncodingError, load_charter_bytes, load_charter_file
from kernel.errors import KittyInternalConsistencyError


# ---------------------------------------------------------------------------
# load_charter_bytes — inline-byte ingest path
# ---------------------------------------------------------------------------


def test_load_charter_bytes_utf8_succeeds() -> None:
    """Inline UTF-8 bytes load cleanly with confidence=1.0 and no
    normalization."""
    content = load_charter_bytes(b"hello world\n", origin="inline-test")
    assert content.text == "hello world\n"
    assert content.source_encoding == "utf-8"
    assert content.confidence == 1.0
    assert content.normalization_applied is False
    assert content.source_path is None


def test_load_charter_bytes_ambiguous_raises() -> None:
    """Inline bytes that the detector cannot resolve raise CharterEncodingError
    (same contract as load_charter_file)."""
    garbage = b"hi\n" + bytes(range(0x80, 0x100)) + b"\nbye\n"
    with pytest.raises(CharterEncodingError) as excinfo:
        load_charter_bytes(garbage, origin="adversarial-fixture")
    assert excinfo.value.code == CharterEncodingDiagnostic.AMBIGUOUS.value


def test_load_charter_bytes_unsafe_bypass_succeeds() -> None:
    """``unsafe=True`` accepts the highest-confidence candidate even when
    the detector's confidence is below threshold."""
    garbage = b"hi\n" + bytes(range(0x80, 0x100)) + b"\nbye\n"
    content = load_charter_bytes(garbage, origin="adversarial-fixture", unsafe=True)
    assert content.normalization_applied is True
    assert isinstance(content.text, str)


# ---------------------------------------------------------------------------
# BOM detection branch (load_charter_file)
# ---------------------------------------------------------------------------


def test_load_charter_file_recognizes_utf8_bom(tmp_path: Path) -> None:
    """UTF-8 BOM (0xEF 0xBB 0xBF) at the start of a file is detected and
    stripped; normalization_applied is True because the BOM is removed."""
    target = tmp_path / "bom.yaml"
    target.write_bytes(b"\xef\xbb\xbfname: hello\nvalue: 1\n")
    content = load_charter_file(target)
    assert content.source_encoding == "utf-8-sig"
    assert content.confidence == 1.0
    assert content.normalization_applied is True
    assert content.text == "name: hello\nvalue: 1\n"
    assert "﻿" not in content.text


@pytest.mark.parametrize(
    ("bom", "encoding", "expected_encoding"),
    [
        (b"\xff\xfe", "utf-16-le", "utf-16-le"),
        (b"\xfe\xff", "utf-16-be", "utf-16-be"),
    ],
)
def test_load_charter_file_recognizes_utf16_bom_without_leaking_marker(
    tmp_path: Path,
    bom: bytes,
    encoding: str,
    expected_encoding: str,
) -> None:
    """UTF-16 BOM branches strip the marker byte sequence before decoding."""
    target = tmp_path / "utf16.yaml"
    target.write_bytes(bom + "name: hello\nvalue: 1\n".encode(encoding))

    content = load_charter_file(target)

    assert content.source_encoding == expected_encoding
    assert content.confidence == 1.0
    assert content.normalization_applied is True
    assert content.text == "name: hello\nvalue: 1\n"
    assert "\ufeff" not in content.text


# ---------------------------------------------------------------------------
# CharterEncodingError attribute contract
# ---------------------------------------------------------------------------


def test_charter_encoding_error_is_kitty_internal_consistency_error() -> None:
    """The IS-A relationship the post-merge audit established: catching
    ``KittyInternalConsistencyError`` in CLI/TUI/UI handlers picks up
    charter-encoding diagnostics uniformly."""
    assert issubclass(CharterEncodingError, KittyInternalConsistencyError)


def test_charter_encoding_error_exposes_diagnostic_enum() -> None:
    """The ``.diagnostic`` attribute carries the typed enum member, and the
    ``.code`` attribute carries the JSON-stable string value."""
    err = CharterEncodingError(
        CharterEncodingDiagnostic.NOT_NORMALIZED,
        "the provenance write failed",
    )
    assert err.diagnostic is CharterEncodingDiagnostic.NOT_NORMALIZED
    assert err.code == CharterEncodingDiagnostic.NOT_NORMALIZED.value
    assert "provenance write failed" in err.body


# ---------------------------------------------------------------------------
# Ambiguous-body diagnostic shape (FR-020 surface)
# ---------------------------------------------------------------------------


def test_ambiguous_diagnostic_body_names_file_and_remediation(
    tmp_path: Path,
) -> None:
    """The diagnostic body must name the file path (or ``<inline bytes>``),
    list the detector's candidates, and provide remediation steps. This
    pins FR-020 indirectly — any drift in the body shape breaks the test."""
    bad = tmp_path / "ambiguous.yaml"
    bad.write_bytes(b"hi\n" + bytes(range(0x80, 0x100)) + b"\nbye\n")
    with pytest.raises(CharterEncodingError) as excinfo:
        load_charter_file(bad)
    body = excinfo.value.body
    assert str(bad) in body
    # Candidate list header (detector output).
    assert "Detected candidates" in body or "candidates" in body.lower()
    # At least one remediation pointer.
    assert "Remediation" in body or "--unsafe" in body or "iconv" in body


@dataclass
class _FakeCharsetCandidate:
    encoding: str
    chaos: float
    text: str = "decoded text"

    def __str__(self) -> str:
        return self.text


class _FakeCharsetResults(list[_FakeCharsetCandidate]):
    def best(self) -> _FakeCharsetCandidate | None:
        return self[0] if self else None


def test_ambiguous_diagnostic_body_lists_detector_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Candidate rows include encoding names and derived confidence values."""
    candidates = _FakeCharsetResults(
        [
            _FakeCharsetCandidate("cp1252", 0.42),
            _FakeCharsetCandidate("iso8859_1", 0.33),
        ]
    )
    monkeypatch.setattr("charset_normalizer.from_bytes", lambda _data: candidates)

    body = _io._build_ambiguous_body(b"\x80", source_path=None)

    assert "<inline bytes>" in body
    assert "cp1252 (confidence 0.58)" in body
    assert "iso8859_1 (confidence 0.67)" in body


def test_generate_ulid_uses_new_api() -> None:
    """The normal python-ulid path returns the string value from ulid.new().str."""
    assert isinstance(_io._generate_ulid(), str)
    assert _io._generate_ulid()


def test_write_provenance_failure_is_non_fatal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A filesystem failure while writing provenance logs a warning only."""
    blocker = tmp_path / "blocker"
    blocker.write_text("not a directory", encoding="utf-8")
    monkeypatch.setattr(
        _io,
        "_route_provenance_path",
        lambda _source_path: blocker / ".encoding-provenance.jsonl",
    )
    content = CharterContent(
        text="name: hello\n",
        source_encoding="utf-8",
        confidence=1.0,
        source_path=tmp_path / "charter.yaml",
        normalization_applied=False,
    )

    _io._write_provenance(content, bypass_used=False)

    assert "Failed to write encoding provenance" in caplog.text


def test_resolve_mission_id_reads_meta_json(tmp_path: Path) -> None:
    """Per-mission provenance records include the mission_id from meta.json."""
    mission = tmp_path / "kitty-specs" / "mission-a"
    mission.mkdir(parents=True)
    (mission / "meta.json").write_text(json.dumps({"mission_id": "MISSION-123"}), encoding="utf-8")

    assert _io._resolve_mission_id(mission / "charter.yaml") == "MISSION-123"


def test_resolve_mission_id_handles_bare_kitty_specs_path() -> None:
    """A path that ends at kitty-specs has no mission segment to inspect."""
    assert _io._resolve_mission_id(Path("kitty-specs")) is None
