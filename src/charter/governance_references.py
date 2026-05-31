"""Supporting governance reference diagnostics and context rendering."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "GovernanceReferenceStatus",
    "collect_governance_reference_status",
    "render_governance_references",
]


@dataclass(frozen=True)
class GovernanceReferenceStatus:
    """Status for one charter-declared supporting governance document."""

    path: str
    exists: bool
    safe: bool
    warning: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "path": self.path,
            "exists": self.exists,
            "safe": self.safe,
            "warning": self.warning,
        }


def collect_governance_reference_status(
    repo_root: Path,
    references: list[str],
) -> list[GovernanceReferenceStatus]:
    """Return repo-root-scoped diagnostics for declared reference paths."""

    root = repo_root.resolve()
    statuses: list[GovernanceReferenceStatus] = []
    for raw in references:
        path = raw.strip()
        if not path:
            continue
        warning = _path_warning(root, path)
        if warning is not None:
            statuses.append(
                GovernanceReferenceStatus(
                    path=path,
                    exists=False,
                    safe=False,
                    warning=warning,
                )
            )
            continue

        candidate = (root / path).resolve(strict=False)
        exists = candidate.exists()
        if not exists:
            warning = (
                f"Missing governance reference {path}. Create it under the repository root "
                "or remove it from governance_references in .kittify/charter/charter.md."
            )
        elif not candidate.is_file():
            warning = (
                f"Governance reference {path} is not a file. Point governance_references "
                "at a markdown or text document under the repository root."
            )
        statuses.append(
            GovernanceReferenceStatus(
                path=path,
                exists=exists,
                safe=True,
                warning=warning,
            )
        )
    return statuses


def render_governance_references(
    repo_root: Path,
    references: list[str],
) -> str:
    """Render charter-declared supporting governance docs for prompt context."""

    statuses = collect_governance_reference_status(repo_root, references)
    if not statuses:
        return ""

    lines = ["Required Governance Reading:"]
    for status in statuses:
        if status.warning:
            lines.append(f"  - WARNING: {status.warning}")
        else:
            lines.append(f"  - {status.path}")
    return "\n".join(lines)


def _path_warning(root: Path, path: str) -> str | None:
    candidate = Path(path)
    if candidate.is_absolute():
        return (
            f"Unsafe governance reference {path}: paths must be repository-relative, "
            "not absolute."
        )
    if any(part == ".." for part in candidate.parts):
        return (
            f"Unsafe governance reference {path}: parent-directory traversal is not allowed."
        )
    resolved = (root / candidate).resolve(strict=False)
    if not _is_relative_to(resolved, root):
        return (
            f"Unsafe governance reference {path}: resolved path escapes the repository root."
        )
    return None


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True
