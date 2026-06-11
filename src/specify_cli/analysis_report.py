"""Durable `/spec-kitty.analyze` report persistence and freshness checks."""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from charter.resolution import (
    NotInsideRepositoryError,
    resolve_canonical_repo_root,
)
from specify_cli.core.atomic import atomic_write
from specify_cli.frontmatter import FrontmatterError, FrontmatterManager
from specify_cli.mission_metadata import resolve_mission_identity

ANALYSIS_REPORT_FILENAME = "analysis-report.md"
ANALYSIS_REPORT_ARTIFACT_TYPE = "spec-kitty.analysis-report"
ANALYSIS_REPORT_COMMAND = "/spec-kitty.analyze"
_HASH_INPUTS = ("spec.md", "plan.md", "tasks.md")


@dataclass(frozen=True)
class AnalysisReportResult:
    """Result of writing an analysis report artifact."""

    path: Path
    mission_slug: str
    mission_id: str | None
    input_artifacts: dict[str, dict[str, str | None]]
    verdict: str
    issue_counts: dict[str, int | None]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "mission_slug": self.mission_slug,
            "mission_id": self.mission_id,
            "input_artifacts": self.input_artifacts,
            "verdict": self.verdict,
            "issue_counts": self.issue_counts,
            "stale": False,
        }


@dataclass(frozen=True)
class AnalysisFreshness:
    """Freshness status for `analysis-report.md`."""

    ok: bool
    path: Path
    stale: bool
    missing: bool
    reason: str | None
    mismatches: dict[str, dict[str, str | None]]

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "path": str(self.path),
            "stale": self.stale,
            "missing": self.missing,
            "reason": self.reason,
            "mismatches": self.mismatches,
        }


class AnalysisReportError(RuntimeError):
    """Raised when the analysis report cannot be written or validated."""


def _yaml() -> YAML:
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.width = 4096
    return yaml


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()  # noqa: TID251 - file-integrity hash for artifact freshness
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_text(text: str) -> str:
    digest = hashlib.sha256()  # noqa: TID251 - file-integrity hash for artifact freshness
    digest.update(text.encode("utf-8"))
    return digest.hexdigest()


# Subtask checkbox marker, e.g. ``- [x] T001 ...`` / ``- [ ] T001 ...``. The
# ``mark-status``/``move-task`` commands legitimately flip these on every WP
# transition, which must NOT invalidate a recorded analysis (#1764). The
# substantive WP/subtask definitions and requirement refs still gate freshness.
_TASKS_ARTIFACT = "tasks.md"
_CHECKBOX_RE = re.compile(r"(?m)^(\s*[-*]\s*)\[[ xX]\]")


def _normalize_tasks_md(text: str) -> str:
    """Strip status churn (subtask checkbox state) from ``tasks.md`` so the
    freshness hash reflects only substantive content. ``mark-status``/``move-task``
    toggle ``- [ ]``↔``- [x]`` on every transition; canonicalising the marker means
    a recorded analysis stays current across status churn but still goes stale on a
    real spec/plan/task-definition change (#1764)."""

    return _CHECKBOX_RE.sub(r"\1[ ]", text)


def _artifact_hash_entry(path: Path) -> dict[str, str | None]:
    if not path.exists():
        return {"path": str(path), "sha256": None}
    if path.name == _TASKS_ARTIFACT:
        normalized = _normalize_tasks_md(path.read_text(encoding="utf-8"))
        return {"path": str(path), "sha256": _sha256_text(normalized)}
    return {"path": str(path), "sha256": _sha256_file(path)}


def _charter_path(repo_root: Path) -> Path | None:
    # #1823: resolve through the canonical-root resolver so a worktree-local
    # charter copy is never hashed in place of the main checkout's charter.
    # This is a read-only hashing probe over arbitrary roots, so non-git roots
    # degrade to the passed root. Resolver infrastructure failures still
    # propagate; otherwise we would synthesize a local charter hash when the
    # canonical root is unknowable.
    canonical_root: Path
    try:
        canonical_root = resolve_canonical_repo_root(repo_root)
    except NotInsideRepositoryError:
        canonical_root = repo_root
    for candidate in (
        canonical_root / ".kittify" / "charter" / "charter.md",
        canonical_root / "charter" / "charter.md",
    ):
        if candidate.exists():
            return candidate
    return None


def collect_input_artifact_hashes(feature_dir: Path, repo_root: Path) -> dict[str, dict[str, str | None]]:
    """Return current hashes for analyzer source artifacts."""

    inputs = {
        name: _artifact_hash_entry(feature_dir / name)
        for name in _HASH_INPUTS
    }
    charter = _charter_path(repo_root)
    inputs["charter"] = {"path": str(charter) if charter else None, "sha256": _sha256_file(charter) if charter else None}
    return inputs


def _count_from_patterns(body: str, severity: str) -> int | None:
    patterns = (
        rf"{severity}\s+Issues?\s+Count\s*[:|]\s*(\d+)",
        rf"{severity}\s+Issues?\s*[:|]\s*(\d+)",
        rf"{severity}\s*[:|]\s*(\d+)",
    )
    for pattern in patterns:
        match = re.search(pattern, body, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def infer_issue_counts(body: str) -> dict[str, int | None]:
    """Infer issue counts from common analyze report wording."""

    counts = {
        key: _count_from_patterns(body, key)
        for key in ("critical", "high", "medium", "low")
    }
    if all(value is None for value in counts.values()):
        for key in counts:
            pattern = rf"\b{key.upper()}\b"
            matches = re.findall(pattern, body)
            if matches:
                counts[key] = len(matches)
    return counts


def infer_verdict(body: str, counts: dict[str, int | None]) -> str:
    """Infer a coarse report verdict for gates and JSON output."""

    upper = body.upper()
    if "READY FOR IMPLEMENTATION" in upper or "PASS" in upper:
        return "ready"
    if "BLOCK" in upper or "CRITICAL" in upper and (counts.get("critical") or 0) > 0:
        return "blocked"
    if (counts.get("critical") or 0) > 0 or (counts.get("high") or 0) > 0:
        return "blocked"
    return "unknown"


def _frontmatter_text(frontmatter: dict[str, Any]) -> str:
    stream = io.StringIO()
    yaml = _yaml()
    yaml.dump(frontmatter, stream)
    return stream.getvalue()


def write_analysis_report(
    *,
    feature_dir: Path,
    repo_root: Path,
    body: str,
    analyzer_agent: str | None = None,
) -> AnalysisReportResult:
    """Persist `analysis-report.md` with source-artifact hashes."""

    for required in _HASH_INPUTS:
        required_path = feature_dir / required
        if not required_path.exists():
            raise AnalysisReportError(f"Required artifact missing: {required_path}")

    identity = resolve_mission_identity(feature_dir)
    input_artifacts = collect_input_artifact_hashes(feature_dir, repo_root)
    issue_counts = infer_issue_counts(body)
    verdict = infer_verdict(body, issue_counts)
    frontmatter: dict[str, Any] = {
        "schema_version": 1,
        "artifact_type": ANALYSIS_REPORT_ARTIFACT_TYPE,
        "command": ANALYSIS_REPORT_COMMAND,
        "mission_slug": identity.mission_slug,
        "mission_id": identity.mission_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "analyzer_agent": analyzer_agent or "unknown",
        "input_artifacts": input_artifacts,
        "verdict": verdict,
        "issue_counts": issue_counts,
    }
    normalized_body = body if body.endswith("\n") else body + "\n"
    content = f"---\n{_frontmatter_text(frontmatter)}---\n\n{normalized_body}"
    path = feature_dir / ANALYSIS_REPORT_FILENAME
    atomic_write(path, content)
    return AnalysisReportResult(
        path=path,
        mission_slug=identity.mission_slug,
        mission_id=identity.mission_id,
        input_artifacts=input_artifacts,
        verdict=verdict,
        issue_counts=issue_counts,
    )


def check_analysis_report_current(feature_dir: Path, repo_root: Path) -> AnalysisFreshness:
    """Return whether `analysis-report.md` exists and matches current inputs."""

    path = feature_dir / ANALYSIS_REPORT_FILENAME
    if not path.exists():
        return AnalysisFreshness(
            ok=False,
            path=path,
            stale=False,
            missing=True,
            reason="missing_analysis_report",
            mismatches={},
        )

    try:
        frontmatter, _body = FrontmatterManager().read(path)
    except FrontmatterError as exc:
        return AnalysisFreshness(
            ok=False,
            path=path,
            stale=True,
            missing=False,
            reason=f"invalid_analysis_report_frontmatter: {exc}",
            mismatches={},
        )

    if frontmatter.get("artifact_type") != ANALYSIS_REPORT_ARTIFACT_TYPE:
        return AnalysisFreshness(
            ok=False,
            path=path,
            stale=True,
            missing=False,
            reason="invalid_analysis_report_artifact_type",
            mismatches={},
        )

    saved_inputs = frontmatter.get("input_artifacts")
    if not isinstance(saved_inputs, dict):
        return AnalysisFreshness(
            ok=False,
            path=path,
            stale=True,
            missing=False,
            reason="missing_input_artifacts",
            mismatches={},
        )

    current = collect_input_artifact_hashes(feature_dir, repo_root)
    mismatches: dict[str, dict[str, str | None]] = {}
    for key in (*_HASH_INPUTS, "charter"):
        saved_entry = saved_inputs.get(key)
        saved_hash = saved_entry.get("sha256") if isinstance(saved_entry, dict) else None
        current_hash = current.get(key, {}).get("sha256")
        if saved_hash != current_hash:
            mismatches[key] = {
                "saved_sha256": saved_hash,
                "current_sha256": current_hash,
            }

    if mismatches:
        return AnalysisFreshness(
            ok=False,
            path=path,
            stale=True,
            missing=False,
            reason="stale_analysis_report",
            mismatches=mismatches,
        )

    return AnalysisFreshness(
        ok=True,
        path=path,
        stale=False,
        missing=False,
        reason=None,
        mismatches={},
    )
