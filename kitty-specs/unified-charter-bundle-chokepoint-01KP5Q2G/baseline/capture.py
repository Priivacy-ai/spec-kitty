#!/usr/bin/env python3
"""Reproducible dashboard typed-contract capture for FR-014 regression.

This script materializes a deterministic fixture project (charter present,
one mission with three work packages in distinct lanes), invokes the
dashboard typed-contract surfaces (``scan_all_features``, ``scan_feature_kanban``,
``get_feature_artifacts``, ``resolve_project_charter_path``), redacts the
output per R-4 (sort keys, scrub timestamps and non-identity ULIDs, sort
semantically-unordered arrays), and prints the canonical JSON to stdout.

The redacted JSON is committed under
``kitty-specs/unified-charter-bundle-chokepoint-01KP5Q2G/baseline/pre-wp23-dashboard-typed.json``
and is the byte-identical anchor for
``tests/test_dashboard/test_charter_chokepoint_regression.py``.

Usage::

    python kitty-specs/.../baseline/capture.py \
        > kitty-specs/.../baseline/pre-wp23-dashboard-typed.json

Determinism notes:

* The fixture builds a tmp git repo in a deterministic location under the
  system tmp directory keyed by a fixed seed (so local re-runs reuse it
  cleanly).
* All ``"*_at"`` ISO timestamps in the output are replaced with ``"<ts>"``.
* ``"event_id"`` ULIDs are identity values for status-event lookups; per R-4,
  identity ULIDs are kept stable by the fixture using fixed-string event ids
  (e.g. ``"TESTWP01CLAIMED0000000000"``), so they never need redaction.
* Any other 26-character ULID-shaped string under a non-identity key gets
  collapsed to ``"<ulid>"``.
* ``"path"`` fields containing the absolute fixture root get rewritten to
  ``"<fixture_root>/..."`` so the JSON is location-independent.
* Top-level lists that are semantically unordered (``features``,
  ``kanban[lane]``) are sorted by their ``id`` field for determinism.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

# Ensure the in-repo packages take priority over any installed copy.
_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "src"))


_TS_KEY_PATTERN = re.compile(r"_at$|^at$|^timestamp_utc$|^extracted_at$|^last_sync$|^updated_at$|^started_at$|^mtime$")
_ULID_PATTERN = re.compile(r"^[0-9A-HJKMNP-TV-Z]{26}$")
# Identity keys whose ULID values must NOT be redacted (they are required
# to be stable across captures).
_IDENTITY_ULID_KEYS = frozenset({"event_id", "mission_id"})


def _redact(value: Any, key: str | None, fixture_root: str) -> Any:
    """Apply R-4 redactions recursively.

    * Keys matching ``_TS_KEY_PATTERN`` -> ``"<ts>"``
    * 26-char ULID-shaped string under a non-identity key -> ``"<ulid>"``
    * Any string containing the absolute fixture root -> ``<fixture_root>``
      replacement.
    """
    if isinstance(value, dict):
        # Sort keys deterministically by emitting an ordered dict.
        return {k: _redact(value[k], k, fixture_root) for k in sorted(value.keys())}
    if isinstance(value, list):
        # We cannot blindly sort lists here — semantic ordering matters
        # for, e.g., `subtasks`. The caller-level normalize_dashboard_payload
        # explicitly sorts the lists that ARE order-irrelevant.
        return [_redact(item, None, fixture_root) for item in value]
    if isinstance(value, str):
        # Path scrubbing happens before timestamp/ULID checks so paths
        # never get clobbered.
        scrubbed = value.replace(fixture_root, "<fixture_root>")
        if key is not None and _TS_KEY_PATTERN.search(key):
            return "<ts>"
        if key is not None and key not in _IDENTITY_ULID_KEYS and _ULID_PATTERN.match(scrubbed):
            return "<ulid>"
        # Generic ISO-8601 string redaction for values that look like a
        # timestamp regardless of key (e.g. when nested inside a meta dict).
        if re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", scrubbed):
            return "<ts>"
        return scrubbed
    if isinstance(value, float):
        # mtimes / sizes derived from filesystem can drift across runs;
        # any float at this layer is treated as a timestamp surrogate.
        return "<ts>"
    return value


def _normalize_dashboard_payload(payload: dict[str, Any], fixture_root: str) -> dict[str, Any]:
    """R-4 finalization: sort semantically-unordered arrays, then redact."""
    # Sort the features array by id for determinism (it is sorted by id desc
    # in scanner.py:544 already, but we re-sort defensively).
    if "features" in payload and isinstance(payload["features"], list):
        payload["features"] = sorted(payload["features"], key=lambda f: f.get("id", ""))
    # Sort each kanban lane by WP id for determinism.
    if "kanban" in payload and isinstance(payload["kanban"], dict):
        for lane_key in payload["kanban"]:
            lane_value = payload["kanban"][lane_key]
            if isinstance(lane_value, list):
                payload["kanban"][lane_key] = sorted(lane_value, key=lambda w: w.get("id", ""))
    redacted = _redact(payload, None, fixture_root)
    return redacted  # type: ignore[no-any-return]


def _build_fixture(root: Path) -> Path:
    """Build a deterministic project fixture and return its absolute path."""
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    # Init git so the resolver does not blow up.
    subprocess.run(["git", "init", "--quiet", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "baseline@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "config", "user.name", "Baseline"],
        check=True,
    )

    # Charter (the file presence drives the dashboard charter probe).
    charter_dir = root / ".kittify" / "charter"
    charter_dir.mkdir(parents=True)
    (charter_dir / "charter.md").write_text(
        "# Project Charter\n\n## Policy Summary\n\n- Be deterministic.\n",
        encoding="utf-8",
    )

    # One mission with three WPs in distinct lanes.
    feature_dir = root / "kitty-specs" / "001-demo-feature"
    tasks_dir = feature_dir / "tasks"
    tasks_dir.mkdir(parents=True)
    (feature_dir / "spec.md").write_text("# Spec\n", encoding="utf-8")
    (feature_dir / "plan.md").write_text("# Plan\n", encoding="utf-8")
    (feature_dir / "tasks.md").write_text("# Tasks\n", encoding="utf-8")
    (feature_dir / "meta.json").write_text(
        json.dumps(
            {
                "friendly_name": "Demo Feature",
                "mission_id": "01HXBASELINEDEMO000000000Z",  # 26-char identity ULID
                "mission_number": 1,
            },
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    wp_template = """---
work_package_id: {wp_id}
subtasks: ["T1"]
agent: codex
---
# Work Package Prompt: {wp_id}

Body for {wp_id}.
"""
    for wp_id in ("WP01", "WP02", "WP03"):
        (tasks_dir / f"{wp_id}-demo.md").write_text(
            wp_template.format(wp_id=wp_id), encoding="utf-8"
        )

    # Seed status events: WP01 planned, WP02 in_progress, WP03 done.
    from specify_cli.status.models import Lane, StatusEvent
    from specify_cli.status.reducer import materialize
    from specify_cli.status.store import append_event

    transitions = [
        ("WP01", Lane.PLANNED, Lane.PLANNED, "PLANNED"),
        ("WP02", Lane.PLANNED, Lane.CLAIMED, "CLAIMED"),
        ("WP02", Lane.CLAIMED, Lane.IN_PROGRESS, "PROGRESS"),
        ("WP03", Lane.PLANNED, Lane.CLAIMED, "CLAIMED"),
        ("WP03", Lane.CLAIMED, Lane.IN_PROGRESS, "PROGRESS"),
        ("WP03", Lane.IN_PROGRESS, Lane.FOR_REVIEW, "REVIEW"),
        ("WP03", Lane.FOR_REVIEW, Lane.IN_REVIEW, "INREVIEW"),
        ("WP03", Lane.IN_REVIEW, Lane.APPROVED, "APPROVED"),
        ("WP03", Lane.APPROVED, Lane.DONE, "DONE"),
    ]
    counter = 0
    for wp_id, from_lane, to_lane, tag in transitions:
        # Stable identity ULIDs derived from a counter so re-runs are identical.
        ulid = f"TESTBASELINE{tag}{wp_id}{counter:04d}"[:26].ljust(26, "0")
        append_event(
            feature_dir,
            StatusEvent(
                event_id=ulid,
                mission_slug=feature_dir.name,
                wp_id=wp_id,
                from_lane=from_lane,
                to_lane=to_lane,
                at="2026-04-14T12:00:00+00:00",
                actor="baseline",
                force=True,
                execution_mode="direct_repo",
            ),
        )
        counter += 1
    materialize(feature_dir)

    return root


def _capture(fixture_root: Path) -> dict[str, Any]:
    """Invoke the dashboard typed-contract surfaces and return the merged payload."""
    from specify_cli.dashboard import scanner
    from specify_cli.dashboard.charter_path import resolve_project_charter_path

    features = scanner.scan_all_features(fixture_root)
    feature_id = "001-demo-feature"
    kanban = scanner.scan_feature_kanban(fixture_root, feature_id)
    feature_dir = fixture_root / "kitty-specs" / feature_id
    artifacts = scanner.get_feature_artifacts(feature_dir, fixture_root)
    workflow = scanner.get_workflow_status(artifacts)
    charter_path = resolve_project_charter_path(fixture_root)

    return {
        "features": features,
        "kanban": kanban,
        "feature_artifacts": artifacts,
        "workflow_status": workflow,
        "charter_path_resolved": charter_path is not None,
    }


def main() -> int:
    fixture_root = Path(tempfile.gettempdir()) / "spec-kitty-wp03-baseline-fixture"
    fixture_root = _build_fixture(fixture_root).resolve()
    payload = _capture(fixture_root)
    normalized = _normalize_dashboard_payload(payload, str(fixture_root))
    sys.stdout.write(json.dumps(normalized, indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
