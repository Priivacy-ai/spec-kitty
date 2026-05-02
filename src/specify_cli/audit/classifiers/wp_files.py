"""Classifier for WP*.md work-package frontmatter files."""

from __future__ import annotations

from pathlib import Path

from specify_cli.frontmatter import FrontmatterError, FrontmatterManager

from ..detectors import detect_legacy_keys
from ..models import MissionFinding, Severity
from ..shape_registry import check_unknown_keys

# Terminal lanes that require evidence
_TERMINAL_LANES = frozenset({"done", "approved"})

# Use the canonical FrontmatterManager (same ruamel.yaml config as production)
_fm_manager = FrontmatterManager()


def classify_wp_files(mission_dir: Path) -> list[MissionFinding]:
    """Classify WP*.md frontmatter for legacy keys, unknown keys, and missing evidence.

    Globs ``mission_dir / "tasks" / "WP*.md"``, sorted by filename for
    determinism.  For each file:
    - Parses YAML frontmatter via :class:`~specify_cli.frontmatter.FrontmatterManager`.
    - Skips files with absent or empty frontmatter (no finding — frontmatter is optional).
    - Emits ``UNKNOWN_SHAPE`` (info) for files whose frontmatter YAML cannot be parsed.
    - Detects legacy keys and unknown keys.
    - Emits ``MISSING_EVIDENCE`` (warning) when a terminal lane (done/approved)
      has no ``evidence`` field or ``evidence`` is null.

    ``artifact_path`` values use forward slashes (e.g. ``"tasks/WP01.md"``).

    Args:
        mission_dir: Path to the mission directory.

    Returns:
        A list of :class:`~specify_cli.audit.models.MissionFinding` objects.
        Returns ``[]`` when no WP*.md files exist.  Never raises.
    """
    tasks_dir = mission_dir / "tasks"
    if not tasks_dir.exists():
        return []

    wp_files = sorted(tasks_dir.glob("WP*.md"), key=lambda p: p.name)
    if not wp_files:
        return []

    findings: list[MissionFinding] = []

    for wp_path in wp_files:
        filename = wp_path.name
        artifact_path = f"tasks/{filename}"

        try:
            frontmatter, _ = _fm_manager.read(wp_path)
        except FrontmatterError:
            # Frontmatter absent or malformed YAML
            # Check if file starts with "---" to distinguish absent vs malformed
            try:
                content = wp_path.read_text(encoding="utf-8-sig")
            except OSError:
                # File unreadable — skip
                continue

            if not content.startswith("---"):
                # No frontmatter — skip silently (optional)
                continue

            # Has "---" but FrontmatterManager raised — malformed YAML
            findings.append(
                MissionFinding(
                    code="UNKNOWN_SHAPE",
                    severity=Severity.INFO,
                    artifact_path=artifact_path,
                    detail="could not parse YAML frontmatter",
                )
            )
            continue

        if not frontmatter:
            # Empty frontmatter — skip silently
            continue

        # Legacy key detection (work_package_id is valid in WP frontmatter)
        findings.extend(detect_legacy_keys(frontmatter, artifact_path))

        # Unknown key detection
        findings.extend(check_unknown_keys("wp_frontmatter", frontmatter, artifact_path))

        # Missing evidence check for terminal lanes
        lane = frontmatter.get("lane") or frontmatter.get("status")
        if isinstance(lane, str) and lane in _TERMINAL_LANES:
            evidence = frontmatter.get("evidence")
            if evidence is None:
                findings.append(
                    MissionFinding(
                        code="MISSING_EVIDENCE",
                        severity=Severity.WARNING,
                        artifact_path=artifact_path,
                        detail=f"terminal lane {lane!r} but evidence is absent",
                    )
                )

    return findings
