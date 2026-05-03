"""File I/O utility for dashboard artifact serving."""
from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path

from dashboard.api_types import (
    ArtifactDirectoryFile,
    ArtifactDirectoryResponse,
    ResearchArtifact,
    ResearchResponse,
)
from specify_cli.scanner import resolve_feature_dir


@dataclass
class FileReadResult:
    content: str | None
    found: bool
    encoding_error: bool = field(default=False)


class DashboardFileReader:
    """Locates feature-specific files and returns content or directory listings."""

    _ARTIFACT_MAP: dict[str, str] = {
        "spec": "spec.md",
        "plan": "plan.md",
        "tasks": "tasks.md",
        "research": "research.md",
        "quickstart": "quickstart.md",
        "data-model": "data-model.md",
    }

    def __init__(self, project_dir: Path) -> None:
        self._project_dir = project_dir.resolve()

    def _safe_read(self, path: Path) -> FileReadResult:
        """Read a file, handling encoding errors with UTF-8 recovery."""
        if not path.exists() or not path.is_file():
            return FileReadResult(content=None, found=False)
        try:
            content = path.read_text(encoding="utf-8")
            return FileReadResult(content=content, found=True)
        except UnicodeDecodeError as err:
            error_prefix = (
                f"⚠️ **Encoding Error**\n\n"
                f"This file contains non-UTF-8 characters at position {err.start}.\n"
                "Attempting to read with error recovery...\n\n---\n\n"
            )
            content = path.read_text(encoding="utf-8", errors="replace")
            return FileReadResult(content=error_prefix + content, found=True, encoding_error=True)

    def _check_traversal(self, feature_dir: Path, candidate: Path) -> bool:
        """Return True if candidate is safely within feature_dir."""
        try:
            candidate.relative_to(feature_dir.resolve())
            return True
        except ValueError:
            return False

    def read_research(self, feature_id: str) -> ResearchResponse:
        """Build research response (main_file content + artifacts listing)."""
        response: ResearchResponse = {"main_file": None, "artifacts": []}
        feature_dir = resolve_feature_dir(self._project_dir, feature_id)
        if not feature_dir:
            return response

        research_md = feature_dir / "research.md"
        if research_md.exists():
            result = self._safe_read(research_md)
            response["main_file"] = result.content

        research_dir = feature_dir / "research"
        if research_dir.exists() and research_dir.is_dir():
            for file_path in sorted(research_dir.rglob("*")):
                if file_path.is_file():
                    relative_path = str(file_path.relative_to(feature_dir))
                    icon = "📄"
                    if file_path.suffix == ".csv":
                        icon = "📊"
                    elif file_path.suffix == ".md":
                        icon = "📝"
                    elif file_path.suffix in [".xlsx", ".xls"]:
                        icon = "📈"
                    elif file_path.suffix == ".json":
                        icon = "📋"
                    artifact: ResearchArtifact = {
                        "name": file_path.name,
                        "path": relative_path,
                        "icon": icon,
                    }
                    response["artifacts"].append(artifact)

        return response

    def read_artifact_file(self, feature_id: str, encoded_path: str) -> FileReadResult:
        """Read a file within a feature directory (path-traversal-safe)."""
        feature_dir = resolve_feature_dir(self._project_dir, feature_id)
        if not feature_dir:
            return FileReadResult(content=None, found=False)

        file_path_str = urllib.parse.unquote(encoded_path)
        candidate = (feature_dir / file_path_str).resolve()

        if not self._check_traversal(feature_dir, candidate):
            return FileReadResult(content=None, found=False)

        return self._safe_read(candidate)

    def read_artifact_directory(
        self, feature_id: str, directory_name: str, md_icon: str = "📝"
    ) -> ArtifactDirectoryResponse:
        """Build a directory listing for a named artifact subdirectory."""
        response: ArtifactDirectoryResponse = {"files": []}
        feature_dir = resolve_feature_dir(self._project_dir, feature_id)
        if not feature_dir:
            return response

        artifact_dir = feature_dir / directory_name
        if not artifact_dir.exists() or not artifact_dir.is_dir():
            return response

        for file_path in sorted(artifact_dir.rglob("*")):
            if file_path.is_file():
                relative_path = str(file_path.relative_to(feature_dir))
                icon = "📄"
                if file_path.suffix == ".md":
                    icon = md_icon
                elif file_path.suffix == ".json":
                    icon = "📋"
                entry: ArtifactDirectoryFile = {
                    "name": file_path.name,
                    "path": relative_path,
                    "icon": icon,
                }
                response["files"].append(entry)

        return response

    def read_named_artifact(self, feature_id: str, artifact_name: str) -> FileReadResult:
        """Read a primary artifact file (spec.md, plan.md, etc.) by logical name."""
        feature_dir = resolve_feature_dir(self._project_dir, feature_id)
        if not feature_dir:
            return FileReadResult(content=None, found=False)

        filename = self._ARTIFACT_MAP.get(artifact_name)
        if not filename:
            return FileReadResult(content=None, found=False)

        return self._safe_read(feature_dir / filename)
