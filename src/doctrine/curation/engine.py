"""Curation engine: discover, present, and promote _proposed/ artifacts."""

from __future__ import annotations

import shutil
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from doctrine.artifact_kinds import ArtifactKind
from doctrine.curation.state import ARTIFACT_TYPES, CurationSession

@dataclass
class ProposedArtifact:
    """A _proposed/ artifact discovered on disk."""

    artifact_type: str
    artifact_id: str
    filename: str
    path: Path
    data: dict[str, Any]

    @property
    def title(self) -> str:
        return (
            self.data.get("title")
            or self.data.get("name")
            or self.data.get("profile-id")
            or self.artifact_id
        )

    @property
    def summary_fields(self) -> dict[str, str]:
        """Extract key fields for presentation."""
        fields: dict[str, str] = {}
        for key in (
            "intent",
            "purpose",
            "summary",
            "description",
            "enforcement",
            "scope",
            "tool",
            "entry_condition",
            "exit_condition",
        ):
            val = self.data.get(key)
            if val:
                fields[key] = str(val)
        refs = self.data.get("tactic_refs")
        if refs:
            fields["tactic_refs"] = ", ".join(str(r) for r in refs)
        steps = self.data.get("steps")
        if steps:
            fields["steps"] = f"{len(steps)} steps"
        principles = self.data.get("principles")
        if principles:
            fields["principles"] = f"{len(principles)} principles"
        return fields


# File-extension globs for each artifact type (derived from ArtifactKind)
_GLOB_PATTERNS: dict[str, str] = {
    kind.plural: kind.glob_pattern
    for kind in ArtifactKind
    if kind.glob_pattern  # excludes TEMPLATE (empty pattern)
}


def _doctrine_src_root() -> Path:
    """Return the src/doctrine/ package root."""
    return Path(__file__).resolve().parent.parent


def discover_proposed(
    doctrine_root: Path | None = None,
) -> list[ProposedArtifact]:
    """Find all artifacts in _proposed/ directories."""
    root = doctrine_root or _doctrine_src_root()
    yaml = YAML()
    yaml.preserve_quotes = True
    artifacts: list[ProposedArtifact] = []

    for art_type in ARTIFACT_TYPES:
        proposed_dir = root / art_type / "_proposed"
        if not proposed_dir.is_dir():
            continue
        pattern = _GLOB_PATTERNS.get(art_type, "*.yaml")
        for yaml_path in sorted(proposed_dir.rglob(pattern)):
            try:
                data = yaml.load(yaml_path)
                if not isinstance(data, dict):
                    continue
                art_id = data.get("id", yaml_path.stem)
                artifacts.append(
                    ProposedArtifact(
                        artifact_type=art_type,
                        artifact_id=str(art_id),
                        filename=yaml_path.name,
                        path=yaml_path,
                        data=data,
                    )
                )
            except (YAMLError, TypeError, KeyError, ValueError) as exc:
                warnings.warn(
                    f"Skipping unreadable proposed artifact {yaml_path}: {exc}",
                    stacklevel=2,
                )

    return artifacts


def discover_shipped(
    doctrine_root: Path | None = None,
) -> list[ProposedArtifact]:
    """Find all artifacts in shipped/ directories."""
    root = doctrine_root or _doctrine_src_root()
    yaml = YAML()
    yaml.preserve_quotes = True
    artifacts: list[ProposedArtifact] = []

    for art_type in ARTIFACT_TYPES:
        shipped_dir = root / art_type / "shipped"
        if not shipped_dir.is_dir():
            continue
        pattern = _GLOB_PATTERNS.get(art_type, "*.yaml")
        for yaml_path in sorted(shipped_dir.rglob(pattern)):
            try:
                data = yaml.load(yaml_path)
                if not isinstance(data, dict):
                    continue
                art_id = data.get("id", yaml_path.stem)
                artifacts.append(
                    ProposedArtifact(
                        artifact_type=art_type,
                        artifact_id=str(art_id),
                        filename=yaml_path.name,
                        path=yaml_path,
                        data=data,
                    )
                )
            except (YAMLError, TypeError, KeyError, ValueError) as exc:
                warnings.warn(
                    f"Skipping unreadable shipped artifact {yaml_path}: {exc}",
                    stacklevel=2,
                )

    return artifacts


def extract_refs(artifact: ProposedArtifact) -> list[tuple[str, str]]:
    """Extract (artifact_type, artifact_id) pairs referenced by this artifact."""
    refs: list[tuple[str, str]] = []

    # Directives reference tactics via tactic_refs (list of string IDs)
    tactic_refs = artifact.data.get("tactic_refs")
    if isinstance(tactic_refs, list):
        for ref in tactic_refs:
            if isinstance(ref, str):
                refs.append(("tactics", ref))

    # Tactics/styleguides reference others via references list
    references = artifact.data.get("references")
    if isinstance(references, list):
        for ref in references:
            if isinstance(ref, dict):
                ref_type = ref.get("type", "")
                ref_id = ref.get("id", "")
                if ref_type and ref_id:
                    # Map singular type names to plural directory names
                    type_map = {
                        "tactic": "tactics",
                        "styleguide": "styleguides",
                        "directive": "directives",
                        "toolguide": "toolguides",
                        "paradigm": "paradigms",
                        "procedure": "procedures",
                    }
                    mapped = type_map.get(ref_type, ref_type)
                    refs.append((str(mapped), str(ref_id)))

    return refs


def depth_first_order(
    artifacts: list[ProposedArtifact],
) -> list[ProposedArtifact]:
    """Order artifacts depth-first: directive → its tactics → their styleguides.

    Directives are presented first, followed immediately by their referenced
    tactics and styleguides (recursively). Unreferenced artifacts appear at
    the end grouped by type.
    """
    by_key: dict[tuple[str, str], ProposedArtifact] = {
        (a.artifact_type, a.artifact_id): a for a in artifacts
    }
    visited: set[tuple[str, str]] = set()
    ordered: list[ProposedArtifact] = []

    def _walk(key: tuple[str, str]) -> None:
        if key in visited or key not in by_key:
            return
        visited.add(key)
        art = by_key[key]
        ordered.append(art)
        for ref_key in extract_refs(art):
            _walk(ref_key)

    # Start from directives (top of the doctrine hierarchy)
    directives = sorted(
        [a for a in artifacts if a.artifact_type == "directives"],
        key=lambda a: a.filename,
    )
    for d in directives:
        _walk((d.artifact_type, d.artifact_id))

    # Append any remaining unvisited artifacts (orphans, paradigms, etc.)
    for art_type in ARTIFACT_TYPES:
        remaining = sorted(
            [a for a in artifacts if a.artifact_type == art_type and (a.artifact_type, a.artifact_id) not in visited],
            key=lambda a: a.filename,
        )
        for a in remaining:
            _walk((a.artifact_type, a.artifact_id))

    return ordered


def seed_session(
    doctrine_root: Path | None = None,
    existing: CurationSession | None = None,
) -> CurationSession:
    """Create or update a session with all _proposed/ artifacts as pending."""
    session = existing or CurationSession()
    proposed = discover_proposed(doctrine_root)
    for art in proposed:
        if session.get_decision(art.artifact_type, art.artifact_id) is None:
            session.record(
                artifact_type=art.artifact_type,
                artifact_id=art.artifact_id,
                filename=art.filename,
            )
    return session


def promote_artifact(
    artifact: ProposedArtifact,
    doctrine_root: Path | None = None,
) -> Path:
    """Move an artifact from _proposed/ to shipped/.

    Returns the new path in shipped/.
    """
    root = doctrine_root or _doctrine_src_root()
    shipped_dir = root / artifact.artifact_type / "shipped"
    # Preserve subdirectory structure (e.g., writing/ in styleguides)
    proposed_dir = root / artifact.artifact_type / "_proposed"
    relative = artifact.path.relative_to(proposed_dir)
    dest = shipped_dir / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(artifact.path), str(dest))
    return dest


def drop_artifact(artifact: ProposedArtifact) -> None:
    """Remove an artifact from _proposed/."""
    if artifact.path.exists():
        artifact.path.unlink()
