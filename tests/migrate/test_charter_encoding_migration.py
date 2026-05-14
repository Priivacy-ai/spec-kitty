"""Regression tests for ``spec-kitty migrate charter-encoding``.

Covers:
- T039: CLI surface (help flag, --help)
- T040: corpus scan — files discovered in kitty-specs/*/charter/ and .kittify/charter/
- T041: interactive default / --dry-run / --yes modes
- T042: idempotency — second run writes no new provenance records (NFR-006)
- T043: JSON-stable summary report + non-zero exit on ambiguous files

All filesystem I/O is in tmp_path fixtures. No network calls.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from specify_cli.cli.commands.migrate_cmd import app as migrate_app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_cp1252_file(path: Path, text: str | None = None) -> None:
    """Write a file in cp1252 encoding (bytes that are not valid UTF-8).

    The default text is chosen to be long enough that charset-normalizer
    detects it as cp1252 with >= 0.85 confidence (not ambiguous).
    """
    if text is None:
        # Use a multi-word text with several cp1252 high-byte characters so
        # charset-normalizer can detect it confidently.
        text = "R\xe9sum\xe9 na\xefve caf\xe9 H\xf4tel"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("cp1252"))


def _make_utf8_file(path: Path, text: str = "café naïve") -> None:
    """Write a file in UTF-8 encoding."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _extract_json(output: str) -> dict:
    """Extract the JSON object from mixed CLI output (stdout+stderr in CliRunner).

    CliRunner merges stdout and stderr; diagnostic lines may precede the JSON.
    We locate the first '{' of the outermost JSON object and parse from there.
    """
    idx = output.find("{")
    if idx == -1:
        raise ValueError(f"No JSON object found in output: {output!r}")
    return json.loads(output[idx:])


def _count_provenance_records(provenance_path: Path) -> int:
    """Return the number of lines (records) in a provenance JSONL file."""
    if not provenance_path.exists():
        return 0
    return sum(1 for line in provenance_path.read_text(encoding="utf-8").splitlines() if line.strip())


# ---------------------------------------------------------------------------
# T039: CLI surface
# ---------------------------------------------------------------------------


def test_help_flag() -> None:
    """charter-encoding subcommand is registered and --help exits 0."""
    runner = CliRunner()
    result = runner.invoke(migrate_app, ["charter-encoding", "--help"])

    assert result.exit_code == 0
    plain = re.sub(r"\x1b\[[0-9;]*m", "", result.output)
    assert "charter-encoding" in plain
    assert "--dry-run" in plain
    assert "--yes" in plain
    assert "--json" in plain
    assert "--project-root" in plain


# ---------------------------------------------------------------------------
# T040: Corpus scan
# ---------------------------------------------------------------------------


def test_corpus_scan_discovers_mission_charter_files(tmp_path: Path) -> None:
    """Files in kitty-specs/*/charter/*.yaml are discovered."""
    charter_dir = tmp_path / "kitty-specs" / "042-foo-feature" / "charter"
    _make_utf8_file(charter_dir / "charter.yaml")
    _make_utf8_file(charter_dir / "notes.md")
    (tmp_path / ".kittify").mkdir()

    runner = CliRunner()
    result = runner.invoke(
        migrate_app,
        ["charter-encoding", "--dry-run", "--json", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    payload = _extract_json(result.output)
    assert payload["files_inspected"] == 2


def test_corpus_scan_discovers_global_charter_files(tmp_path: Path) -> None:
    """Files in .kittify/charter/*.yaml are discovered."""
    global_charter = tmp_path / ".kittify" / "charter"
    _make_utf8_file(global_charter / "global.yaml")
    (tmp_path / "kitty-specs").mkdir()

    runner = CliRunner()
    result = runner.invoke(
        migrate_app,
        ["charter-encoding", "--dry-run", "--json", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    payload = _extract_json(result.output)
    assert payload["files_inspected"] == 1


def test_corpus_scan_empty_project_returns_zero(tmp_path: Path) -> None:
    """No charter directories → files_inspected == 0, exit 0."""
    (tmp_path / ".kittify").mkdir()

    runner = CliRunner()
    result = runner.invoke(
        migrate_app,
        ["charter-encoding", "--yes", "--json", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    payload = _extract_json(result.output)
    assert payload["files_inspected"] == 0
    assert payload["result"] == "success"


# ---------------------------------------------------------------------------
# T041: Mode tests
# ---------------------------------------------------------------------------


def test_dry_run_does_not_rewrite_files(tmp_path: Path) -> None:
    """--dry-run reports would-normalize but leaves files unchanged on disk."""
    charter_dir = tmp_path / "kitty-specs" / "042-foo" / "charter"
    cp1252_file = charter_dir / "charter.yaml"
    _make_cp1252_file(cp1252_file)
    original_bytes = cp1252_file.read_bytes()
    (tmp_path / ".kittify").mkdir()

    runner = CliRunner()
    result = runner.invoke(
        migrate_app,
        ["charter-encoding", "--dry-run", "--json", "--project-root", str(tmp_path)],
    )
    # dry-run: exit 0 (no ambiguity)
    assert result.exit_code == 0, result.output
    # File content unchanged
    assert cp1252_file.read_bytes() == original_bytes


def test_yes_flag_normalizes_without_prompt(tmp_path: Path) -> None:
    """--yes applies normalizations without prompting; file becomes valid UTF-8."""
    charter_dir = tmp_path / "kitty-specs" / "042-foo" / "charter"
    cp1252_file = charter_dir / "charter.yaml"
    # Use multi-word text with high-byte cp1252 chars for confident detection.
    _make_cp1252_file(cp1252_file)
    (tmp_path / ".kittify").mkdir()

    runner = CliRunner()
    result = runner.invoke(
        migrate_app,
        ["charter-encoding", "--yes", "--json", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    payload = _extract_json(result.output)
    assert payload["result"] == "success"
    assert len(payload["normalized"]) == 1
    # File must now be valid UTF-8 (no UnicodeDecodeError).
    normalized_text = cp1252_file.read_text(encoding="utf-8")
    assert len(normalized_text) > 0


def test_yes_exits_nonzero_on_ambiguous_file(tmp_path: Path) -> None:
    """--yes exits non-zero when any file is ambiguous (CI contract).

    The mock patches ``charter._io.load_charter_file`` — the canonical location
    used by the lazy local import in charter_encoding.py.
    """
    charter_dir = tmp_path / "kitty-specs" / "042-foo" / "charter"
    ambiguous_file = charter_dir / "charter.yaml"
    ambiguous_file.parent.mkdir(parents=True, exist_ok=True)
    # Write non-UTF-8 bytes so the idempotency pre-check fails and the
    # chokepoint is invoked (then mocked to raise CharterEncodingError).
    ambiguous_file.write_bytes(bytes(range(0x80, 0xA0)))
    (tmp_path / ".kittify").mkdir()

    from charter._diagnostics import CharterEncodingDiagnostic
    from charter._io import CharterEncodingError

    with patch("charter._io.load_charter_file") as mock_load:
        mock_load.side_effect = CharterEncodingError(
            CharterEncodingDiagnostic.AMBIGUOUS,
            "ERROR: CHARTER_ENCODING_AMBIGUOUS\n  File: charter.yaml\n  ...",
        )
        runner = CliRunner()
        result = runner.invoke(
            migrate_app,
            ["charter-encoding", "--yes", "--json", "--project-root", str(tmp_path)],
        )

    # Must exit non-zero
    assert result.exit_code != 0
    payload = _extract_json(result.output)
    assert payload["result"] == "ambiguous_present"
    assert len(payload["ambiguous"]) == 1


# ---------------------------------------------------------------------------
# T042: Idempotency (NFR-006)
# ---------------------------------------------------------------------------


def test_idempotency_second_run_is_noop(tmp_path: Path) -> None:
    """Running the migration twice on a normalized corpus is idempotent.

    After the first run all files are UTF-8 — the idempotency pre-check
    (_is_pure_utf8) short-circuits them on the second run, so no new
    provenance records are written.
    """
    charter_dir = tmp_path / "kitty-specs" / "042-foo" / "charter"
    cp1252_file = charter_dir / "charter.yaml"
    _make_cp1252_file(cp1252_file)  # multi-word text for confident detection
    (tmp_path / ".kittify").mkdir()

    runner = CliRunner()

    # First run: normalizes the cp1252 file.
    result1 = runner.invoke(
        migrate_app,
        ["charter-encoding", "--yes", "--json", "--project-root", str(tmp_path)],
    )
    assert result1.exit_code == 0, result1.output
    payload1 = _extract_json(result1.output)
    assert len(payload1["normalized"]) == 1

    # Count provenance records written by the first run.
    provenance_path = tmp_path / "kitty-specs" / "042-foo" / ".encoding-provenance.jsonl"
    records_after_first_run = _count_provenance_records(provenance_path)
    assert records_after_first_run >= 1, "First run should have written at least one provenance record"

    # Second run: file is already UTF-8 → pre-check skips it → no new provenance.
    result2 = runner.invoke(
        migrate_app,
        ["charter-encoding", "--yes", "--json", "--project-root", str(tmp_path)],
    )
    assert result2.exit_code == 0, result2.output
    payload2 = _extract_json(result2.output)
    # File is in already_utf8 bucket, not normalized
    assert len(payload2["normalized"]) == 0
    assert len(payload2["already_utf8"]) == 1

    # No new provenance records written on second run.
    records_after_second_run = _count_provenance_records(provenance_path)
    assert records_after_second_run == records_after_first_run, (
        f"Second run wrote {records_after_second_run - records_after_first_run} extra "
        "provenance record(s); idempotency contract violated (NFR-006)."
    )


def test_idempotency_precheck_skips_utf8_files_without_chokepoint(tmp_path: Path) -> None:
    """Already-UTF-8 files are skipped without invoking load_charter_file.

    This verifies the idempotency pre-check short-circuits the chokepoint,
    preventing new provenance records on re-runs.
    """
    charter_dir = tmp_path / "kitty-specs" / "042-foo" / "charter"
    _make_utf8_file(charter_dir / "charter.yaml")
    (tmp_path / ".kittify").mkdir()

    with patch("charter._io.load_charter_file") as mock_load:
        runner = CliRunner()
        result = runner.invoke(
            migrate_app,
            ["charter-encoding", "--yes", "--json", "--project-root", str(tmp_path)],
        )
        # Chokepoint was never called — the pre-check short-circuited it.
        mock_load.assert_not_called()

    assert result.exit_code == 0, result.output
    payload = _extract_json(result.output)
    assert len(payload["already_utf8"]) == 1
    assert len(payload["normalized"]) == 0


# ---------------------------------------------------------------------------
# T043: JSON-stable summary report
# ---------------------------------------------------------------------------


def test_json_summary_schema_stability(tmp_path: Path) -> None:
    """JSON output has the expected top-level keys (schema stability)."""
    (tmp_path / ".kittify").mkdir()

    runner = CliRunner()
    result = runner.invoke(
        migrate_app,
        ["charter-encoding", "--yes", "--json", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    payload = _extract_json(result.output)

    required_keys = {"result", "files_inspected", "already_utf8", "normalized", "ambiguous", "dry_run"}
    assert required_keys <= set(payload.keys()), (
        f"Missing keys: {required_keys - set(payload.keys())}"
    )


def test_json_dry_run_flag_reflected_in_output(tmp_path: Path) -> None:
    """JSON summary sets ``dry_run: true`` when --dry-run is passed."""
    (tmp_path / ".kittify").mkdir()

    runner = CliRunner()
    result = runner.invoke(
        migrate_app,
        ["charter-encoding", "--dry-run", "--json", "--project-root", str(tmp_path)],
    )
    assert result.exit_code == 0, result.output
    payload = _extract_json(result.output)
    assert payload["dry_run"] is True


def test_json_result_ambiguous_present_when_ambiguous(tmp_path: Path) -> None:
    """``result`` field is ``ambiguous_present`` and exit is non-zero when files are ambiguous.

    Patches ``charter._io.load_charter_file`` (the canonical module location
    used by the lazy local import in charter_encoding.py).
    """
    charter_dir = tmp_path / "kitty-specs" / "042-foo" / "charter"
    bad_file = charter_dir / "charter.yaml"
    bad_file.parent.mkdir(parents=True, exist_ok=True)
    # Write non-UTF-8 bytes so idempotency pre-check fails.
    bad_file.write_bytes(bytes(range(0x80, 0xA0)))
    (tmp_path / ".kittify").mkdir()

    from charter._diagnostics import CharterEncodingDiagnostic
    from charter._io import CharterEncodingError

    with patch("charter._io.load_charter_file") as mock_load:
        mock_load.side_effect = CharterEncodingError(
            CharterEncodingDiagnostic.AMBIGUOUS,
            "ERROR: CHARTER_ENCODING_AMBIGUOUS\n  File: charter.yaml",
        )
        runner = CliRunner()
        result = runner.invoke(
            migrate_app,
            ["charter-encoding", "--yes", "--json", "--project-root", str(tmp_path)],
        )

    assert result.exit_code != 0
    payload = _extract_json(result.output)
    assert payload["result"] == "ambiguous_present"
    ambiguous_paths = [a["path"] for a in payload["ambiguous"]]
    assert any("charter.yaml" in p for p in ambiguous_paths)
