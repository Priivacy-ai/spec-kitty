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
REVIEW_ARTIFACT_VERDICTS = frozenset({"approved", "rejected"})


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
        if not isinstance(data, dict):
            raise ValueError(
                "affected_files entries must be mappings with a 'path' key"
            )
        path = data.get("path")
        if not isinstance(path, str) or not path:
            raise ValueError(
                "affected_files entries must include a non-empty string 'path'"
            )
        line_range = data.get("line_range")
        if line_range is not None and not isinstance(line_range, str):
            raise ValueError(
                "affected_files entry 'line_range' must be a string when present"
            )
        return cls(
            path=path,
            line_range=line_range,
        )


@dataclass(frozen=True)
class LatestReviewArtifactVerdict:
    """Verdict summary for the latest ``review-cycle-N.md`` artifact."""

    path: Path
    cycle_number: int
    verdict: str
    has_override: bool = False  # complete approval override stamped on the artifact


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
    # Operator/arbiter override stamped onto a rejected artifact by the approval
    # gate (``agent tasks move-task --to approved`` over a rejected latest). When
    # present and complete, the override IS the approval record — terminal-lane
    # consistency gates must honor it just as the approval gate does (see #1924).
    override_actor: str | None = None
    override_reason: str | None = None

    @property
    def has_complete_override(self) -> bool:
        """True iff a complete approval override (actor + reason) is stamped on."""
        return bool(
            self.override_actor
            and self.override_actor.strip()
            and self.override_reason
            and self.override_reason.strip()
        )

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
        # Round-trip the approval-override block when present so a
        # ``from_file``→``write`` cycle does not silently drop the override that
        # the approval gate stamped onto a rejected artifact (#1924). Keys are
        # emitted only when set, leaving non-overridden artifacts byte-identical.
        if self.override_actor is not None:
            d["review_artifact_override_actor"] = self.override_actor
        if self.override_reason is not None:
            d["review_artifact_override_reason"] = self.override_reason
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any], body: str = "") -> ReviewCycleArtifact:
        """Deserialize from frontmatter dict and optional body string."""
        cycle_number = data.get("cycle_number")
        if cycle_number is None or isinstance(cycle_number, bool):
            raise ValueError("cycle_number must be a positive integer")
        try:
            parsed_cycle_number = int(cycle_number)
        except (TypeError, ValueError) as exc:
            raise ValueError("cycle_number must be a positive integer") from exc
        if parsed_cycle_number < 1:
            raise ValueError("cycle_number must be a positive integer")

        wp_id = data.get("wp_id")
        if not isinstance(wp_id, str) or not wp_id:
            raise ValueError("wp_id must be a non-empty string")
        mission_slug = data.get("mission_slug")
        if not isinstance(mission_slug, str) or not mission_slug:
            raise ValueError("mission_slug must be a non-empty string")
        reviewer_agent = data.get("reviewer_agent")
        if not isinstance(reviewer_agent, str) or not reviewer_agent:
            raise ValueError("reviewer_agent must be a non-empty string")
        verdict = data.get("verdict")
        if not isinstance(verdict, str) or verdict not in REVIEW_ARTIFACT_VERDICTS:
            raise ValueError("verdict must be one of: approved, rejected")
        reviewed_at = data.get("reviewed_at")
        if not isinstance(reviewed_at, str) or not reviewed_at:
            raise ValueError("reviewed_at must be a non-empty string")
        affected_files_data = data.get("affected_files", [])
        if not isinstance(affected_files_data, list):
            raise ValueError("affected_files must be a list")
        reproduction_command = data.get("reproduction_command")
        if reproduction_command is not None and not isinstance(reproduction_command, str):
            raise ValueError("reproduction_command must be a string when present")

        affected_files = [
            AffectedFile.from_dict(af)
            for af in affected_files_data
        ]
        # Optional approval-override block (written by the approval gate onto a
        # rejected artifact when move-task --to approved applies an arbiter/operator
        # override). Tolerant parse: non-string values are treated as absent.
        override_actor = data.get("review_artifact_override_actor")
        override_reason = data.get("review_artifact_override_reason")
        return cls(
            cycle_number=parsed_cycle_number,
            wp_id=wp_id,
            mission_slug=mission_slug,
            reviewer_agent=reviewer_agent,
            verdict=verdict,
            reviewed_at=reviewed_at,
            affected_files=affected_files,
            reproduction_command=reproduction_command,
            body=body,
            override_actor=override_actor if isinstance(override_actor, str) else None,
            override_reason=override_reason if isinstance(override_reason, str) else None,
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
        has_override=artifact.has_complete_override,
    )


def rejected_review_artifact_for_terminal_lane(
    sub_artifact_dir: Path,
    lane: str,
) -> LatestReviewArtifactVerdict | None:
    """Return the latest rejected artifact when a WP is approved or done.

    A rejected artifact carrying a complete approval override (actor + reason) is
    NOT a conflict: the override is the recorded approval that the approval gate
    honored, so the terminal-lane consistency gate must honor it too (#1924).
    """
    state = latest_review_artifact_verdict(sub_artifact_dir)
    if state is None:
        return None
    if (
        str(lane) in TERMINAL_REVIEW_LANES
        and state.verdict == "rejected"
        and not state.has_override
    ):
        return state
    return None
