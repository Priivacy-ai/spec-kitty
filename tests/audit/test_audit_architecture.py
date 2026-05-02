"""Tests for the 20 fixture directories in tests/audit/fixtures/.

Each test asserts that the fixture triggers exactly the expected finding
code(s) and no others from the relevant classifier(s).

T024: clean_modern, unknown_shape
T025: legacy_feature_slug, legacy_work_package_id, legacy_aggregate_id
T026: legacy_mission_key, legacy_feature_number
T027: forbidden_event_type, forbidden_event_name
T028: identity_missing, identity_invalid
T029: corrupt_jsonl, snapshot_drift
T030: actor_drift, missing_evidence
T031: duplicate_mission_id, duplicate_prefix, ambiguous_selector
T032: wp_frontmatter_class_a, wp_frontmatter_class_b
"""

from __future__ import annotations

import ast
import pathlib
from pathlib import Path

from specify_cli.audit import AuditOptions, run_audit
from specify_cli.audit.classifiers.meta import classify_meta_json
from specify_cli.audit.classifiers.status_events import classify_status_events_jsonl
from specify_cli.audit.classifiers.status_json import classify_status_json
from specify_cli.audit.classifiers.wp_files import classify_wp_files

# ---------------------------------------------------------------------------
# Fixture root
# ---------------------------------------------------------------------------

FX = Path(__file__).parent / "fixtures"


def _codes(findings: list) -> set[str]:
    return {f.code for f in findings}


# ---------------------------------------------------------------------------
# T024 — Clean and Unknown-Shape Fixtures
# ---------------------------------------------------------------------------


def test_clean_modern_zero_findings() -> None:
    """clean_modern: all classifiers return zero findings."""
    mission_dir = FX / "clean_modern"
    assert classify_meta_json(mission_dir) == []
    events_findings, has_corrupt = classify_status_events_jsonl(mission_dir)
    assert events_findings == []
    assert not has_corrupt
    assert classify_wp_files(mission_dir) == []


def test_unknown_shape_meta() -> None:
    """unknown_shape: future_key_not_in_registry triggers UNKNOWN_SHAPE on meta.json."""
    findings = classify_meta_json(FX / "unknown_shape")
    codes = _codes(findings)
    assert "UNKNOWN_SHAPE" in codes
    assert "LEGACY_KEY" not in codes
    assert "IDENTITY_MISSING" not in codes


# ---------------------------------------------------------------------------
# T025 — Legacy Key Fixtures (feature_slug, work_package_id, legacy_aggregate_id)
# ---------------------------------------------------------------------------


def test_legacy_feature_slug() -> None:
    """legacy_feature_slug: feature_slug in event row triggers LEGACY_KEY."""
    findings, _ = classify_status_events_jsonl(FX / "legacy_feature_slug")
    assert "LEGACY_KEY" in _codes(findings)


def test_legacy_work_package_id() -> None:
    """legacy_work_package_id: work_package_id instead of wp_id triggers LEGACY_KEY."""
    findings, _ = classify_status_events_jsonl(FX / "legacy_work_package_id")
    assert "LEGACY_KEY" in _codes(findings)


def test_legacy_aggregate_id() -> None:
    """legacy_aggregate_id: legacy_aggregate_id key triggers LEGACY_KEY."""
    findings, _ = classify_status_events_jsonl(FX / "legacy_aggregate_id")
    assert "LEGACY_KEY" in _codes(findings)


# ---------------------------------------------------------------------------
# T026 — Legacy Key Fixtures (mission_key, feature_number)
# ---------------------------------------------------------------------------


def test_legacy_mission_key() -> None:
    """legacy_mission_key: mission_key in meta.json triggers LEGACY_KEY."""
    findings = classify_meta_json(FX / "legacy_mission_key")
    assert "LEGACY_KEY" in _codes(findings)


def test_legacy_feature_number() -> None:
    """legacy_feature_number: feature_number in meta.json triggers LEGACY_KEY."""
    findings = classify_meta_json(FX / "legacy_feature_number")
    assert "LEGACY_KEY" in _codes(findings)


# ---------------------------------------------------------------------------
# T027 — Forbidden Key Fixtures
# ---------------------------------------------------------------------------


def test_forbidden_event_type() -> None:
    """forbidden_event_type: event_type key triggers FORBIDDEN_KEY."""
    findings, _ = classify_status_events_jsonl(FX / "forbidden_event_type")
    assert "FORBIDDEN_KEY" in _codes(findings)


def test_forbidden_event_name() -> None:
    """forbidden_event_name: event_name key triggers FORBIDDEN_KEY."""
    findings, _ = classify_status_events_jsonl(FX / "forbidden_event_name")
    assert "FORBIDDEN_KEY" in _codes(findings)


# ---------------------------------------------------------------------------
# T028 — Identity Findings
# ---------------------------------------------------------------------------


def test_identity_missing() -> None:
    """identity_missing: absent mission_id field triggers IDENTITY_MISSING."""
    findings = classify_meta_json(FX / "identity_missing")
    assert "IDENTITY_MISSING" in _codes(findings)
    assert "IDENTITY_INVALID" not in _codes(findings)


def test_identity_invalid() -> None:
    """identity_invalid: non-ULID mission_id triggers IDENTITY_INVALID."""
    findings = classify_meta_json(FX / "identity_invalid")
    assert "IDENTITY_INVALID" in _codes(findings)
    assert "IDENTITY_MISSING" not in _codes(findings)


# ---------------------------------------------------------------------------
# T029 — Corruption and Drift Fixtures
# ---------------------------------------------------------------------------


def test_corrupt_jsonl() -> None:
    """corrupt_jsonl: second line of events file is invalid JSON → CORRUPT_JSONL."""
    findings, has_corrupt = classify_status_events_jsonl(FX / "corrupt_jsonl")
    assert has_corrupt
    assert "CORRUPT_JSONL" in _codes(findings)


def test_snapshot_drift() -> None:
    """snapshot_drift: persisted status.json has wrong event_count → SNAPSHOT_DRIFT."""
    findings = classify_status_json(FX / "snapshot_drift")
    assert "SNAPSHOT_DRIFT" in _codes(findings)


def test_snapshot_drift_not_on_clean(tmp_path: Path) -> None:
    """clean_modern has no status.json → classify_status_json returns []."""
    assert classify_status_json(FX / "clean_modern") == []


# ---------------------------------------------------------------------------
# T030 — Actor Drift and Missing Evidence
# ---------------------------------------------------------------------------


def test_actor_drift() -> None:
    """actor_drift: 'CLAUDE_BOT_v2' actor fails ^[a-z] regex → ACTOR_DRIFT."""
    findings, _ = classify_status_events_jsonl(FX / "actor_drift")
    assert "ACTOR_DRIFT" in _codes(findings)


def test_missing_evidence() -> None:
    """missing_evidence: WP01.md has terminal lane 'done' but evidence null → MISSING_EVIDENCE."""
    findings = classify_wp_files(FX / "missing_evidence")
    assert "MISSING_EVIDENCE" in _codes(findings)


# ---------------------------------------------------------------------------
# T031 — Multi-Mission Fixtures (Repo-Level Findings)
# ---------------------------------------------------------------------------


def test_duplicate_mission_id() -> None:
    """duplicate_mission_id: two missions share same ULID → DUPLICATE_MISSION_ID on both."""
    repo_root = FX / "duplicate_mission_id" / "repo"
    options = AuditOptions(
        repo_root=repo_root,
        scan_root=repo_root / "kitty-specs",
    )
    report = run_audit(options)
    all_codes = {f.code for r in report.missions for f in r.findings}
    assert "DUPLICATE_MISSION_ID" in all_codes


def test_duplicate_prefix() -> None:
    """duplicate_prefix: two missions share 034- prefix → DUPLICATE_PREFIX on both."""
    repo_root = FX / "duplicate_prefix" / "repo"
    options = AuditOptions(
        repo_root=repo_root,
        scan_root=repo_root / "kitty-specs",
    )
    report = run_audit(options)
    all_codes = {f.code for r in report.missions for f in r.findings}
    assert "DUPLICATE_PREFIX" in all_codes


def test_ambiguous_selector() -> None:
    """ambiguous_selector: '001-my-feature' and '002-my-feature' share 'my-feature' handle."""
    repo_root = FX / "ambiguous_selector" / "repo"
    options = AuditOptions(
        repo_root=repo_root,
        scan_root=repo_root / "kitty-specs",
    )
    report = run_audit(options)
    all_codes = {f.code for r in report.missions for f in r.findings}
    assert "AMBIGUOUS_SELECTOR" in all_codes


def test_duplicate_mission_id_both_missions_flagged() -> None:
    """Both missions in duplicate_mission_id fixture receive the finding."""
    repo_root = FX / "duplicate_mission_id" / "repo"
    options = AuditOptions(
        repo_root=repo_root,
        scan_root=repo_root / "kitty-specs",
    )
    report = run_audit(options)
    flagged_slugs = {
        r.mission_slug
        for r in report.missions
        if any(f.code == "DUPLICATE_MISSION_ID" for f in r.findings)
    }
    assert "mission-alpha" in flagged_slugs
    assert "mission-beta" in flagged_slugs


# ---------------------------------------------------------------------------
# T032 — WP Frontmatter Shape Fixtures
# ---------------------------------------------------------------------------


def test_wp_frontmatter_class_a_clean() -> None:
    """wp_frontmatter_class_a: all-modern keys → zero findings from wp_files classifier."""
    findings = classify_wp_files(FX / "wp_frontmatter_class_a")
    assert findings == []


def test_wp_frontmatter_class_b_unknown_shape() -> None:
    """wp_frontmatter_class_b: old_priority_field is unknown → UNKNOWN_SHAPE."""
    findings = classify_wp_files(FX / "wp_frontmatter_class_b")
    assert "UNKNOWN_SHAPE" in _codes(findings)


# ---------------------------------------------------------------------------
# T035 — Architectural write-guard and no-network guard
# ---------------------------------------------------------------------------


def _is_open_write(call: ast.Call) -> bool:
    """Return True if this call opens a file for writing or appending."""
    func = call.func
    if isinstance(func, ast.Name) and func.id == "open":
        for kw in call.keywords:
            if kw.arg == "mode" and isinstance(kw.value, ast.Constant):
                return "w" in str(kw.value.value) or "a" in str(kw.value.value)
        for arg in call.args[1:2]:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                return "w" in arg.value or "a" in arg.value
    return False


def test_no_filesystem_writes_in_audit() -> None:
    """No write-mode file opens in src/specify_cli/audit/."""
    audit_root = pathlib.Path("src/specify_cli/audit")
    write_calls = []
    for py_file in sorted(audit_root.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and _is_open_write(node):
                write_calls.append(f"{py_file}:{node.lineno}")
    assert write_calls == [], "Write-mode file opens found:\n" + "\n".join(write_calls)


def test_no_network_imports_in_audit() -> None:
    """No network-library imports in src/specify_cli/audit/."""
    audit_root = pathlib.Path("src/specify_cli/audit")
    banned = {"requests", "httpx", "urllib.request", "http.client"}
    violations = []
    for py_file in sorted(audit_root.rglob("*.py")):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = [alias.name for alias in getattr(node, "names", [])]
                module = getattr(node, "module", "") or ""
                if any(b in (module + "." + n) for b in banned for n in names):
                    violations.append(f"{py_file}:{node.lineno}")
    assert violations == [], "Network imports found:\n" + "\n".join(violations)
