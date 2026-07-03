"""Unit tests for ``specify_cli.charter_runtime.freshness.computer`` (WP02 / FR-005, FR-009).

Covers each documented sub-state:

* ``fresh`` — when SHA-256 of charter.md matches metadata + bundle/DRG mtimes
  are downstream of the charter source.
* ``stale`` — when charter content has drifted from the stored hash, or
  bundle/DRG files are older than their upstream change.
* ``missing`` — when the synthesized DRG file is absent and the manifest
  does not opt into ``built_in_only=true``.
* ``built_in_only`` — when the manifest declares ``built_in_only: true``.
  A residual ``graph.yaml`` the manifest disowns is *stale graph residue*
  (FR-006 / C2-f): still ``built_in_only`` + a non-blocking diagnostic, never
  the formerly-terminal ``invalid`` state.
* ``invalid`` — a genuine inconsistency from ``_compute_charter_source``:
  ``charter.md`` exists but cannot be hashed. (No ``synthesized_drg`` producer
  returns ``invalid`` after FR-006.)
"""

from __future__ import annotations

import time
from pathlib import Path
from textwrap import dedent

import pytest

from specify_cli.charter_runtime.freshness import (
    CharterFreshness,
    FreshnessSubState,
    compute_freshness,
)
from charter.hasher import hash_content


pytestmark = [pytest.mark.fast]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_charter(repo: Path, body: str = "# Charter\n\nHello") -> tuple[Path, Path]:
    charter_dir = repo / ".kittify" / "charter"
    charter_dir.mkdir(parents=True, exist_ok=True)
    charter_path = charter_dir / "charter.md"
    metadata_path = charter_dir / "metadata.yaml"
    charter_path.write_text(body, encoding="utf-8")
    return charter_path, metadata_path


def _write_metadata(metadata_path: Path, charter_path: Path, *, mismatched: bool = False) -> None:
    digest = hash_content(charter_path.read_text(encoding="utf-8")).split(":", 1)[1]
    if mismatched:
        digest = "0" * 64
    metadata_path.write_text(
        dedent(
            f"""\
            charter_hash: sha256:{digest}
            timestamp_utc: 2026-01-01T00:00:00+00:00
            """
        ),
        encoding="utf-8",
    )


def _seed_bundle_files(repo: Path) -> None:
    charter_dir = repo / ".kittify" / "charter"
    for name in ("governance.yaml", "directives.yaml", "references.yaml"):
        (charter_dir / name).write_text("schema_version: '1'\n", encoding="utf-8")


def _seed_manifest(
    repo: Path,
    *,
    built_in_only: bool,
    created_at: str = "2099-01-01T00:00:00+00:00",
) -> Path:
    manifest_path = repo / ".kittify" / "charter" / "synthesis-manifest.yaml"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        dedent(
            f"""\
            schema_version: '2'
            mission_id: null
            created_at: '{created_at}'
            run_id: 01JTESTRUNIDXXXXXXXXXXXXXX
            adapter_id: test
            adapter_version: '0.0.0'
            synthesizer_version: '0.0.0'
            manifest_hash: {"a" * 64}
            artifacts: []
            built_in_only: {str(built_in_only).lower()}
            """
        ),
        encoding="utf-8",
    )
    return manifest_path


def _seed_graph(repo: Path) -> Path:
    graph_path = repo / ".kittify" / "doctrine" / "graph.yaml"
    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text("schema_version: '1.0'\nnodes: []\nedges: []\n", encoding="utf-8")
    return graph_path


# ---------------------------------------------------------------------------
# Fresh / stale / missing / built_in_only / invalid cases
# ---------------------------------------------------------------------------


def test_returns_three_sub_objects(tmp_path: Path) -> None:
    """The result always exposes all three layers."""
    result = compute_freshness(tmp_path)
    assert isinstance(result, CharterFreshness)
    for sub in (result.charter_source, result.synced_bundle, result.synthesized_drg):
        assert isinstance(sub, FreshnessSubState)
        assert sub.state in {"fresh", "stale", "missing", "built_in_only", "invalid"}


def test_charter_source_missing_when_charter_md_absent(tmp_path: Path) -> None:
    result = compute_freshness(tmp_path)
    assert result.charter_source.state == "missing"
    assert result.charter_source.remediation == "spec-kitty charter sync"


def test_charter_source_fresh_when_hash_matches(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    result = compute_freshness(tmp_path)
    assert result.charter_source.state == "fresh"
    assert result.charter_source.last_change is not None


def test_charter_source_stale_when_hash_mismatches(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path, mismatched=True)
    result = compute_freshness(tmp_path)
    assert result.charter_source.state == "stale"
    assert result.charter_source.remediation == "spec-kitty charter sync"


def test_synced_bundle_missing_when_no_bundle_files(tmp_path: Path) -> None:
    _, _ = _seed_charter(tmp_path)
    result = compute_freshness(tmp_path)
    # Metadata file is one of the bundle files; even though charter.md
    # exists, the rest of the bundle is missing.  We need a true "no files"
    # scenario: drop charter dir except for charter.md.
    bundle = tmp_path / ".kittify" / "charter"
    for stale_file in ("governance.yaml", "directives.yaml", "references.yaml", "metadata.yaml"):
        candidate = bundle / stale_file
        if candidate.exists():
            candidate.unlink()
    result = compute_freshness(tmp_path)
    assert result.synced_bundle.state == "missing"


def test_synced_bundle_fresh_when_bundle_followed_charter(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    # Bundle files written AFTER charter — fresh.
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    result = compute_freshness(tmp_path)
    assert result.charter_source.state == "fresh"
    assert result.synced_bundle.state == "fresh"


def test_synced_bundle_stale_when_charter_is_newer(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    # Re-write charter much later but DO NOT update metadata — that flips
    # charter_source to stale → synced_bundle inherits "stale".
    time.sleep(0.01)
    charter_path.write_text("# Charter (drifted)\n", encoding="utf-8")
    result = compute_freshness(tmp_path)
    assert result.charter_source.state == "stale"
    assert result.synced_bundle.state == "stale"


def test_charter_source_uses_sync_hash_normalization(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path, "# Charter\n\nHello\n\n")
    _write_metadata(metadata_path, charter_path)

    result = compute_freshness(tmp_path)

    assert result.charter_source.state == "fresh"


def test_synced_bundle_fresh_when_matching_hash_but_bundle_mtime_older(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)

    time.sleep(0.01)
    charter_path.write_text("# Charter\n\nHello\n\n", encoding="utf-8")
    result = compute_freshness(tmp_path)

    assert result.charter_source.state == "fresh"
    assert result.synced_bundle.state == "fresh"


def test_synthesized_drg_missing_when_no_graph_no_manifest(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    result = compute_freshness(tmp_path)
    assert result.synthesized_drg.state == "missing"
    assert result.synthesized_drg.remediation == "spec-kitty charter synthesize"


def test_synthesized_drg_built_in_only_when_manifest_declares_it(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    _seed_manifest(tmp_path, built_in_only=True)
    result = compute_freshness(tmp_path)
    assert result.synthesized_drg.state == "built_in_only"
    assert result.synthesized_drg.remediation is None


def test_synthesized_drg_built_in_only_for_legacy_fresh_seed(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    provenance = tmp_path / ".kittify" / "doctrine" / "PROVENANCE.md"
    provenance.parent.mkdir(parents=True, exist_ok=True)
    provenance.write_text(
        "# Spec Kitty Doctrine — Fresh Project Seed\n\n"
        "No LLM-authored YAML was present; using built-in doctrine.\n",
        encoding="utf-8",
    )

    result = compute_freshness(tmp_path)

    assert result.synthesized_drg.state == "built_in_only"
    assert result.synthesized_drg.remediation is None


def test_synthesized_drg_residue_reports_built_in_only(tmp_path: Path) -> None:
    """FR-006 (C2-f): built_in_only=true ∧ graph.yaml present is read-time residue.

    The manifest is the declared authority (#083): a graph.yaml it disowns is
    residue, NOT a contradiction. The reader reports the authoritative
    ``built_in_only`` state with a non-blocking diagnostic instead of the
    formerly-terminal ``invalid`` state — making the blocking branch
    unreachable for this condition (structural, not reactive).
    """
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    _seed_manifest(tmp_path, built_in_only=True)
    _seed_graph(tmp_path)  # residue: built_in_only=true AND graph.yaml present
    result = compute_freshness(tmp_path)
    assert result.synthesized_drg.state == "built_in_only"
    assert result.synthesized_drg.state != "invalid"
    assert result.synthesized_drg.detail is not None
    assert "stale graph residue" in result.synthesized_drg.detail
    # Read-time normalization is NOT a reactive self-heal: no synthesize push.
    assert result.synthesized_drg.remediation is None


def test_synthesized_drg_fresh_when_graph_followed_bundle(tmp_path: Path) -> None:
    charter_path, metadata_path = _seed_charter(tmp_path)
    _write_metadata(metadata_path, charter_path)
    _seed_bundle_files(tmp_path)
    _seed_manifest(tmp_path, built_in_only=False)
    _seed_graph(tmp_path)
    result = compute_freshness(tmp_path)
    assert result.synthesized_drg.state == "fresh"


def test_to_dict_shape_matches_contract(tmp_path: Path) -> None:
    """``CharterFreshness.to_dict`` returns the three documented keys."""
    result = compute_freshness(tmp_path)
    d = result.to_dict()
    assert set(d.keys()) == {"charter_source", "synced_bundle", "synthesized_drg"}
    for layer in d.values():
        assert set(layer.keys()) >= {"state", "last_change", "remediation", "detail"}


@pytest.mark.parametrize(
    "scenario",
    ["fresh", "stale", "missing", "built_in_only", "invalid"],
)
def test_states_are_among_documented_vocabulary(scenario: str, tmp_path: Path) -> None:
    """Smoke: every documented state value is reachable by the computer."""
    charter_path, metadata_path = _seed_charter(tmp_path)
    if scenario == "missing":
        result = compute_freshness(tmp_path)
        states = {
            result.charter_source.state,
            result.synced_bundle.state,
            result.synthesized_drg.state,
        }
        assert "missing" in states
        return
    if scenario == "stale":
        _write_metadata(metadata_path, charter_path, mismatched=True)
        result = compute_freshness(tmp_path)
        assert result.charter_source.state == "stale"
        return
    if scenario == "fresh":
        _write_metadata(metadata_path, charter_path)
        _seed_bundle_files(tmp_path)
        result = compute_freshness(tmp_path)
        assert result.charter_source.state == "fresh"
        return
    if scenario == "built_in_only":
        _write_metadata(metadata_path, charter_path)
        _seed_bundle_files(tmp_path)
        _seed_manifest(tmp_path, built_in_only=True)
        result = compute_freshness(tmp_path)
        assert result.synthesized_drg.state == "built_in_only"
        return
    if scenario == "invalid":
        # FR-006 re-pointed this vocabulary smoke-entry: the only ``invalid``
        # producer is now ``_compute_charter_source`` ("charter.md exists but
        # cannot be hashed"), a genuine inconsistency — NOT the downgraded
        # built_in_only ∧ graph residue case.
        _write_metadata(metadata_path, charter_path)
        charter_path.unlink()
        charter_path.mkdir()  # a directory where a file is expected → unhashable
        result = compute_freshness(tmp_path)
        assert result.charter_source.state == "invalid"
        return
    pytest.fail(f"Unhandled scenario {scenario!r}")
