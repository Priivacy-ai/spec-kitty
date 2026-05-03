"""Review cycle artifact model for spec-kitty.

Defines ReviewCycleArtifact and AffectedFile dataclasses for persisting
review feedback as versioned, committed artifacts in kitty-specs/.

Artifacts are stored at:
  kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-{N}.md

and referenced via:
  review-cycle://<mission_slug>/<wp_slug>/review-cycle-{N}.md
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

TERMINAL_REVIEW_LANES = frozenset({"approved", "done"})


def _make_yaml() -> YAML:
    """Create a configured ruamel.yaml instance for frontmatter serialization."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 4096  # prevent line wrapping
    return yaml


@dataclass(frozen=True)
class AffectedFile:
    """A file affected by a review cycle."""

    path: str  # relative to repo root
    line_range: str | None = None  # "start-end" or None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict with sorted keys."""
        d: dict[str, Any] = {"path": self.path}
        if self.line_range is not None:
            d["line_range"] = self.line_range
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AffectedFile:
        """Deserialize from dict."""
        return cls(
            path=data["path"],
            line_range=data.get("line_range"),
        )


@dataclass(frozen=True)
class LatestReviewArtifactVerdict:
    """Verdict summary for the latest ``review-cycle-N.md`` artifact."""

    path: Path
    cycle_number: int
    verdict: str


@dataclass(frozen=True)
class ReviewCycleArtifact:
    """A persisted review cycle artifact.

    Written to disk as a markdown file with YAML frontmatter at:
      kitty-specs/<mission>/tasks/<WP-slug>/review-cycle-{N}.md
    """

    cycle_number: int
    wp_id: str
    mission_slug: str
    reviewer_agent: str
    verdict: str  # "rejected" | "approved"
    reviewed_at: str  # ISO 8601 UTC
    affected_files: list[AffectedFile] = field(default_factory=list)
    reproduction_command: str | None = None
    body: str = ""  # markdown body (not in frontmatter)

    def to_dict(self) -> dict[str, Any]:
        """Serialize frontmatter fields to dict with sorted keys."""
        d: dict[str, Any] = {
            "affected_files": [af.to_dict() for af in self.affected_files],
            "cycle_number": self.cycle_number,
            "mission_slug": self.mission_slug,
            "reproduction_command": self.reproduction_command,
            "reviewed_at": self.reviewed_at,
            "reviewer_agent": self.reviewer_agent,
            "verdict": self.verdict,
            "wp_id": self.wp_id,
        }
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any], body: str = "") -> ReviewCycleArtifact:
        """Deserialize from frontmatter dict and optional body string."""
        affected_files = [
            AffectedFile.from_dict(af)
            for af in data.get("affected_files", [])
        ]
        return cls(
            cycle_number=int(data["cycle_number"]),
            wp_id=data["wp_id"],
            mission_slug=data["mission_slug"],
            reviewer_agent=data["reviewer_agent"],
            verdict=data["verdict"],
            reviewed_at=data["reviewed_at"],
            affected_files=affected_files,
            reproduction_command=data.get("reproduction_command"),
            body=body,
        )

    def write(self, path: Path) -> None:
        """Write this artifact to disk as a markdown file with YAML frontmatter.

        The parent directory is created if it does not exist.
        """
        path.parent.mkdir(parents=True, exist_ok=True)
        yaml = _make_yaml()
        stream = StringIO()
        yaml.dump(self.to_dict(), stream)
        frontmatter_text = stream.getvalue()

        content = f"---\n{frontmatter_text}---\n"
        if self.body:
            content += f"\n{self.body}"

        path.write_text(content, encoding="utf-8")

    @classmethod
    def from_file(cls, path: Path) -> ReviewCycleArtifact:
        """Parse a review-cycle artifact from a markdown file with YAML frontmatter.

        Raises:
            ValueError: If the file cannot be parsed (missing delimiters, bad YAML, etc.)
        """
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            raise ValueError(f"Cannot read review artifact file {path}: {exc}") from exc

        # Split on --- delimiters.  The file must start with "---\n".
        if not text.startswith("---"):
            raise ValueError(
                f"Review artifact file has no YAML frontmatter: {path}"
            )

        # Find the closing --- delimiter
        # text[3:] skips the opening ---
        rest = text[3:]
        # Skip optional newline after opening ---
        if rest.startswith("\n"):
            rest = rest[1:]
        closing = rest.find("\n---")
        if closing == -1:
            raise ValueError(
                f"Review artifact file has no closing '---' delimiter: {path}"
            )

        frontmatter_str = rest[:closing]
        body_raw = rest[closing + 4:]  # skip \n---
        # Strip leading newline from body
        body = body_raw.lstrip("\n")

        yaml = _make_yaml()
        try:
            data = yaml.load(frontmatter_str)
        except Exception as exc:
            raise ValueError(
                f"Failed to parse YAML frontmatter in {path}: {exc}"
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                f"YAML frontmatter in {path} is not a mapping"
            )

        try:
            return cls.from_dict(data, body=body)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                f"Missing or invalid field in review artifact {path}: {exc}"
            ) from exc

    @staticmethod
    def latest(sub_artifact_dir: Path) -> ReviewCycleArtifact | None:
        """Return the highest-numbered review cycle artifact in *sub_artifact_dir*.

        Returns None if no review-cycle-*.md files exist.
        """
        candidates = list(sub_artifact_dir.glob("review-cycle-*.md"))
        if not candidates:
            return None

        def _cycle_num(p: Path) -> int:
            m = re.search(r"review-cycle-(\d+)\.md$", p.name)
            return int(m.group(1)) if m else 0

        candidates.sort(key=_cycle_num)
        return ReviewCycleArtifact.from_file(candidates[-1])

    @staticmethod
    def next_cycle_number(sub_artifact_dir: Path) -> int:
        """Return the next cycle number for a new artifact in *sub_artifact_dir*.

        Returns 1 if no review-cycle-*.md files exist.
        """
        candidates = list(sub_artifact_dir.glob("review-cycle-*.md"))
        return len(candidates) + 1


def latest_review_artifact_verdict(sub_artifact_dir: Path) -> LatestReviewArtifactVerdict | None:
    """Return verdict metadata for the highest-numbered review artifact.

    This helper is intentionally limited to review artifact state.  Callers can
    use it in merge or status gates, but it does not decide whether a workflow
    transition should pass.
    """
    candidates = list(sub_artifact_dir.glob("review-cycle-*.md"))
    if not candidates:
        return None

    def _cycle_num(p: Path) -> int:
        m = re.search(r"review-cycle-(\d+)\.md$", p.name)
        return int(m.group(1)) if m else 0

    candidates.sort(key=_cycle_num)
    path = candidates[-1]
    artifact = ReviewCycleArtifact.from_file(path)
    return LatestReviewArtifactVerdict(
        path=path,
        cycle_number=artifact.cycle_number,
        verdict=artifact.verdict,
    )


def rejected_review_artifact_for_terminal_lane(
    sub_artifact_dir: Path,
    lane: str,
) -> LatestReviewArtifactVerdict | None:
    """Return the latest rejected artifact when a WP is approved or done."""
    state = latest_review_artifact_verdict(sub_artifact_dir)
    if state is None:
        return None
    if str(lane) in TERMINAL_REVIEW_LANES and state.verdict == "rejected":
        return state
    return None
