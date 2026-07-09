"""Durable `/spec-kitty.analyze` report persistence and freshness checks."""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from charter.resolution import (
    NotInsideRepositoryError,
    resolve_canonical_repo_root,
)

# Reuse the existing canonical severity vocabulary (FR-004 binding: do NOT mint a
# 9th Severity model). ``SEVERITY_ORDER`` encodes the blocking ladder used across
# the charter-lint pipeline; the structured findings carrier validates against it.
from specify_cli.charter_runtime.lint.findings import SEVERITY_ORDER
from specify_cli.core.atomic import atomic_write
from specify_cli.core.time_utils import now_utc_iso
from specify_cli.frontmatter import FrontmatterError, FrontmatterManager
from specify_cli.mission_metadata import resolve_mission_identity

ANALYSIS_REPORT_FILENAME = "analysis-report.md"
ANALYSIS_REPORT_ARTIFACT_TYPE = "spec-kitty.analysis-report"
ANALYSIS_REPORT_COMMAND = "/spec-kitty.analyze"
ANALYSIS_REPORT_REASON_CARRIER_FORMAT = "carrier_format_not_wrapped"
_HASH_INPUTS = ("spec.md", "plan.md", "tasks.md")

# --- analysis-findings/v1 structured carrier (FR-004 / #1819) ---------------
#
# The recorder derives the verdict + issue counts from a validated YAML
# frontmatter carrier emitted by the analyzing agent — never from substring
# counting report prose (the #1819 root cause). The carrier reuses the canonical
# ``SEVERITY_ORDER`` vocabulary; minting a parallel severity enum is prohibited.
FINDINGS_SCHEMA_V1 = "analysis-findings/v1"

# Severities that gate the verdict. A finding at or above ``high`` blocks.
_BLOCKING_SEVERITIES = frozenset({"high", "critical"})

# Closed severity vocabulary for findings rows — the canonical ladder, reused.
_FINDING_SEVERITIES = frozenset(SEVERITY_ORDER)

# ``counts`` may additionally carry a presentation-only ``info`` bucket (it is
# not a blocking finding severity and never participates in the verdict).
_COUNT_KEYS = _FINDING_SEVERITIES | {"info"}

# Verdicts the recorder can compute (or fall back to for legacy reports).
VERDICT_READY = "ready"
VERDICT_BLOCKED = "blocked"
VERDICT_UNKNOWN = "unknown"


class FindingsCarrierError(ValueError):
    """Raised when an ``analysis-findings/v1`` carrier is present but malformed.

    Loud failure is intentional and WRITE-path only (C-FIND-2): a drifted carrier
    must never silently fall back to substring inference. Legacy reports with NO
    carrier are handled separately as ``verdict: unknown`` (C-FIND-3).
    """


@dataclass(frozen=True)
class AnalysisReportResult:
    """Result of writing an analysis report artifact."""

    path: Path
    mission_slug: str
    mission_id: str | None
    input_artifacts: dict[str, dict[str, str | None]]
    verdict: str
    issue_counts: dict[str, int | None]
    findings: list[dict[str, Any]]

    def to_dict(self) -> dict[str, object]:
        return {
            "path": str(self.path),
            "mission_slug": self.mission_slug,
            "mission_id": self.mission_id,
            "input_artifacts": self.input_artifacts,
            "verdict": self.verdict,
            "issue_counts": self.issue_counts,
            "findings": self.findings,
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


@dataclass(frozen=True)
class StructuredFindings:
    """A validated ``analysis-findings/v1`` carrier.

    Carries the structured verdict + issue counts derived purely from the
    declared findings (never from report prose) and the report body with the
    carrier frontmatter stripped (the recorder wraps its own frontmatter).
    """

    verdict: str
    issue_counts: dict[str, int | None]
    findings: list[dict[str, Any]]
    body: str


def _split_carrier(body: str) -> tuple[dict[str, Any] | None, str]:
    """Return ``(carrier_frontmatter, body_without_carrier)``.

    The analyzing agent emits the ``analysis-findings/v1`` carrier as a YAML
    frontmatter block at the top of the report body. Returns ``(None, body)``
    when the body has no leading frontmatter block (a legacy/pre-v1 report).
    """

    if not body.startswith("---"):
        return None, body
    yaml = _yaml()
    lines = body.splitlines()
    closing = -1
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            closing = idx
            break
    if closing == -1:
        raise FindingsCarrierError(
            "Malformed analysis-findings carrier: opening '---' has no closing '---'."
        )
    try:
        parsed = yaml.load("\n".join(lines[1:closing]))
    except Exception as exc:  # pragma: no cover - ruamel raises subclasses
        raise FindingsCarrierError(f"Invalid YAML in analysis-findings carrier: {exc}") from exc
    remainder = "\n".join(lines[closing + 1 :]).lstrip("\n")
    if not isinstance(parsed, dict):
        return None, body
    return dict(parsed), remainder


def _validate_findings_carrier(carrier: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, int | None]]:
    """Validate an ``analysis-findings/v1`` carrier; raise loudly on drift.

    Enforces the closed (reused) severity vocabulary, the ``counts == tally``
    invariant, and ``verdict_hint`` agreement. WRITE-path only (C-FIND-2).
    """

    raw_findings = carrier.get("findings", [])
    if not isinstance(raw_findings, list):
        raise FindingsCarrierError("analysis-findings 'findings' must be a list.")

    findings, tally = _normalize_findings(raw_findings)
    counts = _resolve_counts(carrier.get("counts"), tally)
    return findings, counts


def _normalize_findings(
    raw_findings: list[Any],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Validate each finding entry and return ``(findings, severity tally)``."""

    findings: list[dict[str, Any]] = []
    tally = dict.fromkeys(_FINDING_SEVERITIES, 0)
    for entry in raw_findings:
        if not isinstance(entry, dict):
            raise FindingsCarrierError("Each analysis-findings entry must be a mapping.")
        severity = entry.get("severity")
        if severity not in _FINDING_SEVERITIES:
            raise FindingsCarrierError(
                f"Unknown finding severity {severity!r}; allowed (canonical): "
                f"{sorted(_FINDING_SEVERITIES)}."
            )
        tally[severity] += 1
        findings.append(
            {
                "id": entry.get("id"),
                "severity": severity,
                "category": entry.get("category"),
                "summary": entry.get("summary"),
            }
        )
    return findings, tally


def _resolve_counts(
    declared: Any, tally: dict[str, int]
) -> dict[str, int | None]:
    """Reconcile the declared ``counts`` block (if any) against the tally."""

    if declared is None:
        counts: dict[str, int | None] = {key: int(tally[key]) for key in _FINDING_SEVERITIES}
        counts["info"] = 0
        return counts
    if not isinstance(declared, dict):
        raise FindingsCarrierError("analysis-findings 'counts' must be a mapping.")
    unknown_keys = set(declared) - _COUNT_KEYS
    if unknown_keys:
        raise FindingsCarrierError(
            f"Unknown counts keys {sorted(unknown_keys)}; allowed: {sorted(_COUNT_KEYS)}."
        )
    for key in _FINDING_SEVERITIES:
        declared_count = declared.get(key, 0)
        if declared_count != tally[key]:
            raise FindingsCarrierError(
                f"counts[{key!r}]={declared_count} does not equal findings tally {tally[key]}."
            )
    counts = {key: int(tally[key]) for key in _FINDING_SEVERITIES}
    counts["info"] = int(declared.get("info", 0))
    return counts


def compute_verdict_from_findings(findings: list[dict[str, Any]]) -> str:
    """Verdict = f(findings[].severity) ONLY. Any high|critical → blocked, else ready."""

    if any(finding.get("severity") in _BLOCKING_SEVERITIES for finding in findings):
        return VERDICT_BLOCKED
    return VERDICT_READY


def parse_structured_findings(body: str) -> StructuredFindings | None:
    """Parse + validate the ``analysis-findings/v1`` carrier from a report body.

    Returns ``None`` for a legacy/pre-v1 report (no carrier, or a leading
    frontmatter block that is not an analysis-findings/v1 carrier) — the caller
    treats that as ``verdict: unknown`` (C-FIND-3). Raises
    :class:`FindingsCarrierError` when a carrier IS present but malformed
    (C-FIND-2, write-path only).
    """

    carrier, remainder = _split_carrier(body)
    if carrier is None:
        return None
    if carrier.get("schema") != FINDINGS_SCHEMA_V1:
        # A leading frontmatter block that is not our carrier: treat the report
        # as legacy rather than hijacking an unrelated block.
        return None

    findings, counts = _validate_findings_carrier(carrier)
    verdict = compute_verdict_from_findings(findings)

    hint = carrier.get("verdict_hint")
    if hint is not None and hint != verdict:
        raise FindingsCarrierError(
            f"verdict_hint {hint!r} disagrees with the computed verdict {verdict!r} "
            "(verdict is derived from findings severities; correct the hint or the findings)."
        )

    return StructuredFindings(
        verdict=verdict,
        issue_counts=counts,
        findings=findings,
        body=remainder,
    )


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

    # Verdict + counts derive from the structured analysis-findings/v1 carrier
    # ONLY (#1819). A malformed carrier fails loudly here on the write path
    # (C-FIND-2); a legacy report with no carrier records as verdict: unknown
    # (C-FIND-3) — never substring-inferred, never fabricated.
    structured = parse_structured_findings(body)
    if structured is None:
        verdict = VERDICT_UNKNOWN
        issue_counts: dict[str, int | None] = dict.fromkeys(_COUNT_KEYS)
        findings: list[dict[str, Any]] = []
        report_body = body
    else:
        verdict = structured.verdict
        issue_counts = dict(structured.issue_counts)
        findings = structured.findings
        report_body = structured.body

    frontmatter: dict[str, Any] = {
        "schema_version": 1,
        "artifact_type": ANALYSIS_REPORT_ARTIFACT_TYPE,
        "command": ANALYSIS_REPORT_COMMAND,
        "mission_slug": identity.mission_slug,
        "mission_id": identity.mission_id,
        "generated_at": now_utc_iso(),
        "analyzer_agent": analyzer_agent or "unknown",
        "input_artifacts": input_artifacts,
        "verdict": verdict,
        "issue_counts": issue_counts,
        "findings": findings,
    }
    normalized_body = report_body if report_body.endswith("\n") else report_body + "\n"
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
        findings=findings,
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

    if frontmatter.get("schema") == FINDINGS_SCHEMA_V1:
        return AnalysisFreshness(
            ok=False,
            path=path,
            stale=True,
            missing=False,
            reason=ANALYSIS_REPORT_REASON_CARRIER_FORMAT,
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
