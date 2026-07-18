"""Tests for the #2758 references.yaml fail-closed preflight (WP02).

``sync()`` auto-refreshes ``governance.yaml`` / ``directives.yaml`` /
``metadata.yaml`` (``_SYNC_OUTPUT_FILES`` in ``src/charter/sync.py``), but
``references.yaml`` is written only by ``charter generate``
(``charter.compiler.compile_charter``). A project that has been synced but
never generated therefore has three of the four
``charter.bundle.BUNDLE_CONTENT_HASH_FILES`` present and one missing.

Before this WP, that state was a permanent-stale dead end:
``compute_bundle_content_hash`` fail-safes to ``None`` (by design -- that
contract is UNCHANGED here), the real-run ``charter synthesize`` write path
(``write_pipeline.promote()``) silently persists that ``None`` into the
synthesis manifest, and the freshness reader
(``specify_cli.charter_runtime.freshness.computer``) unconditionally maps a
``None`` stored hash to ``stale`` with remediation text pointing back at
``spec-kitty charter synthesize`` -- which can never fix it, because
synthesize does not itself compile ``references.yaml``.

Resolution (Q1, operator decision): fail-closed preflight. Keep the 4-file
hash (no narrowing); raise an actionable error naming ``charter generate``
*before* the real-run write path can persist the un-healable ``None``.
"""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from charter.bundle import BUNDLE_CONTENT_HASH_FILES, compute_bundle_content_hash, first_missing_bundle_file
from specify_cli.cli.commands.charter import app as charter_app
from specify_cli.cli.commands.charter._synthesis import (
    BUNDLE_INCOMPLETE_MESSAGE,
    _raise_if_bundle_incomplete,
)
from specify_cli.task_utils import TaskCliError

pytestmark = [pytest.mark.unit]

runner = CliRunner()

_GOVERNANCE = "governance:\n  rules: []\n"
_DIRECTIVES = "directives: []\n"
_REFERENCES = "references: []\n"
_METADATA = "metadata:\n  version: 1\n"

# NFR-002 pinned expectation: computed once from the UNCHANGED
# compute_bundle_content_hash recipe over this fixed 4-file content. If this
# WP ever touches the hashing recipe (it must not), this assertion goes red.
_COMPLETE_BUNDLE_PINNED_HASH = (
    "sha256:0048b4ad43a8d1429162f8ad3071e81c93f0f86004c1d9d000bdc9ae2ab38532"
)


def _seed_synced_not_generated_bundle(repo_root: Path) -> Path:
    """Mirror a real ``.kittify/charter/`` layout post-sync, pre-generate.

    ``governance.yaml`` / ``directives.yaml`` / ``metadata.yaml`` present
    (as ``sync()`` would auto-refresh them); ``references.yaml``
    intentionally absent (only ``charter generate`` writes it).
    """
    charter_dir = repo_root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    (charter_dir / "charter.md").write_text("# Charter\n", encoding="utf-8")
    (charter_dir / "governance.yaml").write_text(_GOVERNANCE, encoding="utf-8")
    (charter_dir / "directives.yaml").write_text(_DIRECTIVES, encoding="utf-8")
    (charter_dir / "metadata.yaml").write_text(_METADATA, encoding="utf-8")
    return charter_dir


def _seed_complete_bundle(repo_root: Path) -> Path:
    charter_dir = _seed_synced_not_generated_bundle(repo_root)
    (charter_dir / "references.yaml").write_text(_REFERENCES, encoding="utf-8")
    return charter_dir


def _seed_generated_artifact_marker(charter_dir: Path) -> None:
    """Make ``_has_generated_artifacts`` True so the fresh-project short-circuit
    in ``charter_synthesize`` is bypassed and the real-run write path is
    reached (the code path this preflight guards)."""
    generated_dir = charter_dir / "generated" / "directives"
    generated_dir.mkdir(parents=True, exist_ok=True)
    (generated_dir / "sample.directive.yaml").write_text("id: PROJECT_001\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# T005 -- red-first: repro the CURRENT dead-end (compute_bundle_content_hash
# side; this contract stays exactly as-is -- see NFR-002 below)
# ---------------------------------------------------------------------------


def test_synced_not_generated_bundle_hashes_to_none(tmp_path: Path) -> None:
    """references.yaml absent, the other three present -> None (unchanged
    fail-safe contract of compute_bundle_content_hash)."""
    _seed_synced_not_generated_bundle(tmp_path)

    assert compute_bundle_content_hash(tmp_path) is None


def test_first_missing_bundle_file_identifies_references_yaml(tmp_path: Path) -> None:
    """The new preflight helper names the missing file precisely -- this is
    the signal compute_bundle_content_hash's bare None cannot carry."""
    _seed_synced_not_generated_bundle(tmp_path)

    assert first_missing_bundle_file(tmp_path) == "references.yaml"


def test_first_missing_bundle_file_none_when_complete(tmp_path: Path) -> None:
    _seed_complete_bundle(tmp_path)

    assert first_missing_bundle_file(tmp_path) is None


@pytest.mark.parametrize("omit", list(BUNDLE_CONTENT_HASH_FILES))
def test_first_missing_bundle_file_reports_whichever_is_absent(tmp_path: Path, omit: str) -> None:
    """First-missing-in-declared-order semantics, regardless of which file
    is the one that's actually missing (mirrors the parametrization already
    used for compute_bundle_content_hash's None contract)."""
    charter_dir = tmp_path / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    contents = {
        "governance.yaml": _GOVERNANCE,
        "directives.yaml": _DIRECTIVES,
        "references.yaml": _REFERENCES,
        "metadata.yaml": _METADATA,
    }
    for name, text in contents.items():
        if name == omit:
            continue
        (charter_dir / name).write_text(text, encoding="utf-8")

    assert first_missing_bundle_file(tmp_path) == omit


# ---------------------------------------------------------------------------
# T006 -- the fail-closed preflight helper itself
# ---------------------------------------------------------------------------


def test_raise_if_bundle_incomplete_raises_task_cli_error(tmp_path: Path) -> None:
    _seed_synced_not_generated_bundle(tmp_path)

    with pytest.raises(TaskCliError) as excinfo:
        _raise_if_bundle_incomplete(tmp_path)

    message = str(excinfo.value)
    assert message == BUNDLE_INCOMPLETE_MESSAGE.format(missing="references.yaml")
    assert "charter generate" in message


def test_raise_if_bundle_incomplete_is_noop_when_bundle_complete(tmp_path: Path) -> None:
    _seed_complete_bundle(tmp_path)

    # Must not raise.
    _raise_if_bundle_incomplete(tmp_path)


# ---------------------------------------------------------------------------
# T007 -- CLI-level: `charter synthesize` fails closed with the actionable
# message instead of silently reaching the write path
# ---------------------------------------------------------------------------


def test_synthesize_json_fails_closed_when_references_yaml_missing(tmp_path: Path) -> None:
    charter_dir = _seed_synced_not_generated_bundle(tmp_path)
    _seed_generated_artifact_marker(charter_dir)

    evidence_result = SimpleNamespace(warnings=[], bundle=SimpleNamespace())

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.charter._collect_evidence_result", return_value=evidence_result),
        patch(
            "specify_cli.cli.commands.charter._build_synthesis_request",
            return_value=(SimpleNamespace(), SimpleNamespace()),
        ),
    ):
        result = runner.invoke(charter_app, ["synthesize", "--json"])

    assert result.exit_code == 1, result.output
    payload = json.loads(result.output)
    assert payload["result"] == "failure"
    expected_message = BUNDLE_INCOMPLETE_MESSAGE.format(missing="references.yaml")
    assert any(expected_message in warning for warning in payload["warnings"])
    assert any("charter generate" in warning for warning in payload["warnings"])


def test_synthesize_json_succeeds_past_preflight_when_bundle_complete(tmp_path: Path) -> None:
    """Sanity check the guard is not overbroad: a complete bundle does not
    trip the preflight (the real synthesize() call is mocked out here since
    this test is only proving the preflight did not fire, not exercising the
    full synthesis pipeline)."""
    charter_dir = _seed_complete_bundle(tmp_path)
    _seed_generated_artifact_marker(charter_dir)

    evidence_result = SimpleNamespace(warnings=[], bundle=SimpleNamespace())
    synth_result = SimpleNamespace(
        effective_adapter_id="generated",
        effective_adapter_version="0.0.0",
        target_kind="directive",
        target_slug="synthesize-placeholder",
        inputs_hash="deadbeef",
    )

    with (
        patch("specify_cli.cli.commands.charter.find_repo_root", return_value=tmp_path),
        patch("specify_cli.cli.commands.charter._collect_evidence_result", return_value=evidence_result),
        patch(
            "specify_cli.cli.commands.charter._build_synthesis_request",
            return_value=(SimpleNamespace(), SimpleNamespace()),
        ),
        patch("charter.synthesizer.synthesize", return_value=synth_result),
        patch(
            "specify_cli.cli.commands.charter._load_written_artifacts_from_manifest",
            return_value=[],
        ),
    ):
        result = runner.invoke(charter_app, ["synthesize", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["result"] == "success"


# ---------------------------------------------------------------------------
# NFR-002 -- a COMPLETE bundle's compute_bundle_content_hash is byte-unchanged
# by this WP (this WP adds a guard BEFORE the None path; it never touches the
# hashing recipe itself)
# ---------------------------------------------------------------------------


def test_complete_bundle_hash_is_deterministic_and_pinned(tmp_path: Path) -> None:
    _seed_complete_bundle(tmp_path)

    first = compute_bundle_content_hash(tmp_path)
    second = compute_bundle_content_hash(tmp_path)

    assert first == second == _COMPLETE_BUNDLE_PINNED_HASH
