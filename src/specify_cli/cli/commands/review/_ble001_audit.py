"""Gate 3: BLE001 unjustified suppression audit.

Extracted verbatim from src/specify_cli/cli/commands/review.py (WP07).
No behaviour change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_BLE001_NOQA_RE = re.compile(r"#\s*noqa:\s*(?P<body>[^#]*)", re.IGNORECASE)
_BROAD_EXCEPTION_HANDLER_RE = re.compile(
    r"^\s*except\s+"
    r"(?:Exception(?:\s+as\s+\w+)?|\([^#\n]*\bException\b[^#\n]*\)(?:\s+as\s+\w+)?)"
    r"\s*:"
)
_AUTH_STORAGE_BLE001_COMMAND_FILES = frozenset(
    {
        "src/specify_cli/cli/commands/auth.py",
        "src/specify_cli/cli/commands/_auth_doctor.py",
        "src/specify_cli/cli/commands/_auth_login.py",
        "src/specify_cli/cli/commands/_auth_logout.py",
        "src/specify_cli/cli/commands/_auth_status.py",
    }
)
_AUTH_STORAGE_BLE001_AUTH_PREFIX = "src/specify_cli/auth/"
_GENERIC_BLE001_REASONS = frozenset(
    {
        "all exceptions",
        "ble001",
        "blanket",
        "broad catch",
        "broad exception",
        "catch all",
        "catchall",
        "exception",
        "fixme",
        "generic",
        "ignore",
        "ignored",
        "noqa",
        "suppress",
        "suppression",
        "temp",
        "temporary",
        "todo",
    }
)
_BLE001_REMEDIATION = (
    "Add a specific safety reason after '# noqa: BLE001' that names the "
    "boundary, translation, logging, downgrade, or cleanup behavior; otherwise "
    "narrow the exception type."
)


@dataclass(frozen=True)
class Ble001SuppressionFinding:
    """Actionable finding for a scoped auth/storage BLE001 suppression."""

    file: str
    line: int
    suppression: str
    reason: str
    remediation: str = _BLE001_REMEDIATION


def _repo_relative_path(file_path: str | Path, repo_root: Path | None = None) -> str:
    path = Path(file_path)
    if repo_root is not None:
        try:
            return path.resolve(strict=False).relative_to(
                repo_root.resolve(strict=False)
            ).as_posix()
        except ValueError:
            pass

    normalized = path.as_posix().lstrip("/")
    marker = "src/specify_cli/"
    marker_index = normalized.find(marker)
    if marker_index >= 0:
        return normalized[marker_index:]
    return normalized


def _is_auth_storage_ble001_scoped_path(
    file_path: str | Path,
    *,
    repo_root: Path | None = None,
) -> bool:
    repo_path = _repo_relative_path(file_path, repo_root)
    return repo_path.startswith(
        _AUTH_STORAGE_BLE001_AUTH_PREFIX
    ) or repo_path in _AUTH_STORAGE_BLE001_COMMAND_FILES


def _ble001_reason_from_line(line_text: str) -> str | None:
    noqa_match = _BLE001_NOQA_RE.search(line_text)
    if noqa_match is None:
        return None

    body = noqa_match.group("body")
    ble_match = re.search(r"\bBLE001\b(?P<after>.*)$", body)
    if ble_match is None:
        return None

    after = ble_match.group("after")
    while True:
        next_code = re.match(r"\s*,\s*[A-Z]{1,4}\d{3}\b(?P<rest>.*)$", after)
        if next_code is None:
            break
        after = next_code.group("rest")

    return re.sub(r"^\s*[-–—:]+\s*", "", after).strip()


def _is_broad_exception_handler(line_text: str) -> bool:
    return _BROAD_EXCEPTION_HANDLER_RE.search(line_text) is not None


def _is_generic_ble001_reason(reason: str) -> bool:
    normalized = re.sub(r"[\W_]+", " ", reason.casefold()).strip()
    normalized = re.sub(r"\s+", " ", normalized)
    return not normalized or normalized in _GENERIC_BLE001_REASONS


def audit_auth_storage_ble001_line(
    file_path: str | Path,
    line_number: int,
    line_text: str,
    *,
    repo_root: Path | None = None,
) -> Ble001SuppressionFinding | None:
    """Return a finding for an unjustified scoped auth/storage BLE001 suppression."""
    if not _is_auth_storage_ble001_scoped_path(file_path, repo_root=repo_root):
        return None

    reason = _ble001_reason_from_line(line_text)
    if reason is None:
        if not _is_broad_exception_handler(line_text):
            return None
        reason = ""
    elif not _is_generic_ble001_reason(reason):
        return None

    return Ble001SuppressionFinding(
        file=str(file_path),
        line=line_number,
        suppression=line_text.strip(),
        reason=reason,
    )


def collect_auth_storage_ble001_findings(
    repo_root: Path,
) -> list[Ble001SuppressionFinding]:
    """Scan contract-scoped auth/storage files for unjustified BLE001 suppressions."""
    candidates: list[Path] = []
    auth_dir = repo_root / _AUTH_STORAGE_BLE001_AUTH_PREFIX
    if auth_dir.exists():
        candidates.extend(path for path in auth_dir.rglob("*.py") if path.is_file())

    for relative_file in _AUTH_STORAGE_BLE001_COMMAND_FILES:
        path = repo_root / relative_file
        if path.exists():
            candidates.append(path)

    findings: list[Ble001SuppressionFinding] = []
    for path in sorted(set(candidates)):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_number, line_text in enumerate(lines, start=1):
            finding = audit_auth_storage_ble001_line(
                path,
                line_number,
                line_text,
                repo_root=repo_root,
            )
            if finding is not None:
                findings.append(finding)
    return findings
