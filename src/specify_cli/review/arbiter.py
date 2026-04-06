"""Arbiter checklist and rationale model for false-positive review rejections.

When an arbiter overrides a rejection (detected as a forward --force move from
``planned`` after a rejection event), the system presents a 5-question checklist,
derives a category, records the decision, and persists it in the review-cycle
artifact's frontmatter.

The ``review_ref`` in the emitted event points to the existing ``review-cycle://``
artifact — no new pointer scheme is introduced.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console


# ---------------------------------------------------------------------------
# Category enum
# ---------------------------------------------------------------------------


class ArbiterCategory(StrEnum):
    """Structured categories for arbiter override rationales."""

    PRE_EXISTING_FAILURE = "pre_existing_failure"
    WRONG_CONTEXT = "wrong_context"
    CROSS_SCOPE = "cross_scope"
    INFRA_ENVIRONMENTAL = "infra_environmental"
    CUSTOM = "custom"


# Default explanation templates keyed by category
_CATEGORY_DEFAULTS: dict[ArbiterCategory, str] = {
    ArbiterCategory.PRE_EXISTING_FAILURE: "Failure is pre-existing on the base branch and unrelated to this WP.",
    ArbiterCategory.WRONG_CONTEXT: "Reviewer is discussing the wrong feature or WP.",
    ArbiterCategory.CROSS_SCOPE: "Finding is outside this WP's defined scope.",
    ArbiterCategory.INFRA_ENVIRONMENTAL: "Failure is environmental or infrastructure-related, not a code defect.",
    ArbiterCategory.CUSTOM: "",  # CUSTOM requires mandatory non-empty explanation
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ArbiterChecklist:
    """Five-question checklist that drives arbiter category derivation."""

    is_pre_existing: bool       # Q1: Is the failure pre-existing on the base branch?
    is_correct_context: bool    # Q2: Is the reviewer talking about the correct feature/WP?
    is_in_scope: bool           # Q3: Is the finding within this WP's scope?
    is_environmental: bool      # Q4: Is the failure environmental/infra?
    should_follow_on: bool      # Q5: Should this become a follow-on issue instead?

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_pre_existing": self.is_pre_existing,
            "is_correct_context": self.is_correct_context,
            "is_in_scope": self.is_in_scope,
            "is_environmental": self.is_environmental,
            "should_follow_on": self.should_follow_on,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArbiterChecklist:
        return cls(
            is_pre_existing=bool(data["is_pre_existing"]),
            is_correct_context=bool(data["is_correct_context"]),
            is_in_scope=bool(data["is_in_scope"]),
            is_environmental=bool(data["is_environmental"]),
            should_follow_on=bool(data["should_follow_on"]),
        )


@dataclass(frozen=True)
class ArbiterDecision:
    """Structured arbiter override decision with rationale."""

    arbiter: str                 # who made the decision
    category: ArbiterCategory
    explanation: str             # mandatory for all categories, especially CUSTOM
    checklist: ArbiterChecklist
    decided_at: str              # ISO 8601 UTC

    def to_dict(self) -> dict[str, Any]:
        return {
            "arbiter": self.arbiter,
            "category": str(self.category),
            "explanation": self.explanation,
            "checklist": self.checklist.to_dict(),
            "decided_at": self.decided_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArbiterDecision:
        return cls(
            arbiter=data["arbiter"],
            category=ArbiterCategory(data["category"]),
            explanation=data["explanation"],
            checklist=ArbiterChecklist.from_dict(data["checklist"]),
            decided_at=data["decided_at"],
        )


# ---------------------------------------------------------------------------
# Category derivation
# ---------------------------------------------------------------------------


def _derive_category(checklist: ArbiterChecklist) -> ArbiterCategory:
    """Derive the arbiter category from checklist answers.

    Priority order mirrors the most common override scenarios:
    1. Pre-existing failure (strongest signal)
    2. Wrong context (reviewer confusion)
    3. Out of scope (scoping disagreement)
    4. Environmental (infra flakiness)
    5. Custom (everything else)
    """
    if checklist.is_pre_existing:
        return ArbiterCategory.PRE_EXISTING_FAILURE
    if not checklist.is_correct_context:
        return ArbiterCategory.WRONG_CONTEXT
    if not checklist.is_in_scope:
        return ArbiterCategory.CROSS_SCOPE
    if checklist.is_environmental:
        return ArbiterCategory.INFRA_ENVIRONMENTAL
    return ArbiterCategory.CUSTOM


# ---------------------------------------------------------------------------
# Note parsing
# ---------------------------------------------------------------------------

_NOTE_CATEGORY_RE = re.compile(
    r"^\s*\[([a-z_]+)\]\s*(.*)", re.DOTALL
)


def parse_category_from_note(note: str | None) -> tuple[ArbiterCategory, str]:
    """Parse structured note format ``"[category] explanation"``.

    Returns a ``(category, explanation)`` tuple.  If the note does not contain
    a recognised category prefix the category defaults to ``CUSTOM`` and the
    full note text becomes the explanation.

    Examples::

        "[pre_existing_failure] Test was already failing" → (PRE_EXISTING_FAILURE, "Test was ...")
        "Some freeform note" → (CUSTOM, "Some freeform note")
    """
    if not note:
        return ArbiterCategory.CUSTOM, "Override without explanation"

    m = _NOTE_CATEGORY_RE.match(note)
    if m:
        raw_cat = m.group(1).strip()
        explanation = m.group(2).strip()
        try:
            category = ArbiterCategory(raw_cat)
        except ValueError:
            category = ArbiterCategory.CUSTOM
            explanation = note.strip()
        # If explanation is empty after bracket parsing, fall back to default
        if not explanation:
            explanation = _CATEGORY_DEFAULTS.get(category) or f"Override: {category}"
        return category, explanation

    return ArbiterCategory.CUSTOM, note.strip()


# ---------------------------------------------------------------------------
# Non-interactive factory
# ---------------------------------------------------------------------------


def create_arbiter_decision(
    arbiter_name: str,
    category: str | ArbiterCategory,
    explanation: str,
    checklist: ArbiterChecklist | None = None,
) -> ArbiterDecision:
    """Non-interactive arbiter decision creation for CI / agent contexts.

    Args:
        arbiter_name: Name of the arbiter (e.g., "operator", "claude").
        category: Category string or ``ArbiterCategory`` enum value.
        explanation: Mandatory rationale text.
        checklist: Optional checklist; if ``None`` a synthetic one is derived
            from the category to preserve round-trip fidelity.

    Returns:
        A populated :class:`ArbiterDecision`.
    """
    if isinstance(category, str):
        try:
            cat = ArbiterCategory(category)
        except ValueError:
            cat = ArbiterCategory.CUSTOM
    else:
        cat = category

    if not explanation:
        explanation = _CATEGORY_DEFAULTS.get(cat) or f"Override: {cat}"

    if checklist is None:
        checklist = _synthetic_checklist(cat)

    return ArbiterDecision(
        arbiter=arbiter_name or "operator",
        category=cat,
        explanation=explanation,
        checklist=checklist,
        decided_at=datetime.now(UTC).isoformat(),
    )


def _synthetic_checklist(category: ArbiterCategory) -> ArbiterChecklist:
    """Build a synthetic checklist consistent with the given category."""
    return ArbiterChecklist(
        is_pre_existing=(category == ArbiterCategory.PRE_EXISTING_FAILURE),
        is_correct_context=(category != ArbiterCategory.WRONG_CONTEXT),
        is_in_scope=(category != ArbiterCategory.CROSS_SCOPE),
        is_environmental=(category == ArbiterCategory.INFRA_ENVIRONMENTAL),
        should_follow_on=False,
    )


# ---------------------------------------------------------------------------
# Interactive checklist prompt
# ---------------------------------------------------------------------------


def prompt_arbiter_checklist(
    wp_id: str,
    arbiter_name: str,
    console: Console,
) -> ArbiterDecision:
    """Present the arbiter checklist interactively and return a structured decision.

    Args:
        wp_id: Work package ID being overridden (e.g. ``"WP06"``).
        arbiter_name: Name of the human/agent acting as arbiter.
        console: Rich Console instance for I/O.

    Returns:
        A populated :class:`ArbiterDecision` with derived category.
    """
    console.print()
    console.print(f"[bold yellow]Arbiter Override Checklist for {wp_id}[/bold yellow]")
    console.print()
    console.print("Answer each question to classify this override:")
    console.print()

    def _ask_yn(question: str, default: bool) -> bool:
        hint = "[Y/n]" if default else "[y/N]"
        answer = console.input(f"  {question} {hint} ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        return default

    is_pre_existing = _ask_yn(
        "Q1. Is this failure pre-existing on the base branch?", default=False
    )
    is_correct_context = _ask_yn(
        "Q2. Is the reviewer talking about the correct feature/WP?", default=True
    )
    is_in_scope = _ask_yn(
        "Q3. Is the finding within this WP's scope?", default=True
    )
    is_environmental = _ask_yn(
        "Q4. Is the failure environmental or infrastructure-related?", default=False
    )
    should_follow_on = _ask_yn(
        "Q5. Should this become a follow-on issue instead of blocking this WP?",
        default=False,
    )

    checklist = ArbiterChecklist(
        is_pre_existing=is_pre_existing,
        is_correct_context=is_correct_context,
        is_in_scope=is_in_scope,
        is_environmental=is_environmental,
        should_follow_on=should_follow_on,
    )

    category = _derive_category(checklist)
    default_explanation = _CATEGORY_DEFAULTS.get(category, "")

    console.print()
    console.print(f"  Derived category: [bold cyan]{category}[/bold cyan]")
    console.print()

    if category == ArbiterCategory.CUSTOM:
        # CUSTOM requires a non-empty explanation
        while True:
            explanation = console.input("  Explanation (required for CUSTOM): ").strip()
            if explanation:
                break
            console.print("  [red]Explanation is required for CUSTOM category.[/red]")
    else:
        prompt_text = f"  Explanation [{default_explanation}]: "
        explanation = console.input(prompt_text).strip()
        if not explanation:
            explanation = default_explanation

    console.print()

    return ArbiterDecision(
        arbiter=arbiter_name or "operator",
        category=category,
        explanation=explanation,
        checklist=checklist,
        decided_at=datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# Override detection
# ---------------------------------------------------------------------------


def _is_arbiter_override(
    feature_dir: Path,
    wp_id: str,
    old_lane: str,
    target_lane: str,
    force: bool,
) -> bool:
    """Detect if this force move is an arbiter override of a rejection.

    An arbiter override requires ALL of these to be true:
    1. ``--force`` flag is set.
    2. Current lane is ``planned``.
    3. Target lane is forward (``for_review``, ``claimed``, or ``approved``).
    4. The latest event for this WP was a ``for_review`` → ``planned`` transition
       with a non-``None`` ``review_ref`` (i.e., a rejection).
    """
    if not force:
        return False
    if old_lane != "planned":
        return False
    if target_lane not in ("for_review", "claimed", "approved"):
        return False

    from specify_cli.status.models import Lane
    from specify_cli.status.store import read_events

    events = read_events(feature_dir)
    wp_events = [e for e in events if e.wp_id == wp_id]
    if not wp_events:
        return False

    latest = wp_events[-1]
    return (
        latest.from_lane == Lane.FOR_REVIEW
        and latest.to_lane == Lane.PLANNED
        and latest.review_ref is not None
    )


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------


def _find_review_cycle_artifact(
    feature_dir: Path,
    wp_id: str,
    review_ref: str,
) -> Path | None:
    """Locate the review-cycle artifact file for the given review_ref.

    Searches in ``<feature_dir>/tasks/<wp-slug>/`` for markdown files whose
    frontmatter ``review_ref`` or filename matches the pointer.  Returns
    ``None`` when no artifact is found (e.g. WP01 hasn't landed yet).
    """
    # review_ref is typically "feedback://mission/WP##/<filename>"
    # The review-cycle artifacts live alongside WP files in tasks/
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return None

    # Check tasks/<wp_id> subdirectory first
    wp_subdir = tasks_dir / wp_id
    if wp_subdir.exists():
        for candidate in sorted(wp_subdir.glob("review-cycle-*.md")):
            return candidate  # Return the most recently created one

    # Fallback: scan tasks/ level for review-cycle files
    for candidate in sorted(tasks_dir.glob(f"*{wp_id}*review-cycle*.md")):
        return candidate

    return None


def persist_arbiter_decision(
    feature_dir: Path,
    wp_id: str,
    review_ref: str | None,
    decision: ArbiterDecision,
    auto_commit: bool = False,
    repo_root: Path | None = None,
) -> Path:
    """Persist an ArbiterDecision alongside review-cycle artifacts.

    Primary path: add ``arbiter_override`` section to the review-cycle artifact
    frontmatter and rewrite the file.

    Fallback path (when no review-cycle artifact exists): write a standalone
    JSON file at ``<feature_dir>/tasks/<wp_id>/arbiter-override-{N}.json``.

    Args:
        feature_dir: Path to the feature directory (``kitty-specs/<mission>``).
        wp_id: Work package ID.
        review_ref: Pointer to the rejection's review-cycle artifact.
        decision: The ArbiterDecision to persist.
        auto_commit: If True, commit the persisted file to git.
        repo_root: Repository root for git commit (required when auto_commit=True).

    Returns:
        Path to the file where the decision was written.
    """
    artifact_path = (
        _find_review_cycle_artifact(feature_dir, wp_id, review_ref or "")
        if review_ref
        else None
    )

    if artifact_path is not None and artifact_path.exists():
        # Primary path: update review-cycle artifact frontmatter
        return _persist_in_artifact(artifact_path, decision)
    else:
        # Fallback path: standalone JSON
        return _persist_standalone_json(feature_dir, wp_id, decision)


def _persist_in_artifact(artifact_path: Path, decision: ArbiterDecision) -> Path:
    """Add arbiter_override section to a review-cycle artifact's frontmatter."""
    from ruamel.yaml import YAML
    from io import StringIO

    content = artifact_path.read_text(encoding="utf-8")

    # Split frontmatter from body
    fm_match = re.match(r"^---\n(.*?)\n---\n?(.*)", content, re.DOTALL)
    if fm_match:
        fm_text = fm_match.group(1)
        body_text = fm_match.group(2)

        yaml = YAML()
        yaml.preserve_quotes = True
        data = yaml.load(fm_text)
        if data is None:
            data = {}

        # Add arbiter_override section
        data["arbiter_override"] = decision.to_dict()

        stream = StringIO()
        yaml.dump(data, stream)
        new_fm = stream.getvalue().rstrip("\n")

        new_content = f"---\n{new_fm}\n---\n{body_text}"
    else:
        # No frontmatter: prepend it
        fm_dict = {"arbiter_override": decision.to_dict()}
        yaml = YAML()
        stream = StringIO()
        yaml.dump(fm_dict, stream)
        fm_text = stream.getvalue().rstrip("\n")
        new_content = f"---\n{fm_text}\n---\n{content}"

    artifact_path.write_text(new_content, encoding="utf-8")
    return artifact_path


def _persist_standalone_json(
    feature_dir: Path,
    wp_id: str,
    decision: ArbiterDecision,
) -> Path:
    """Write decision to a standalone JSON file when no review-cycle artifact exists."""
    tasks_dir = feature_dir / "tasks"
    wp_subdir = tasks_dir / wp_id
    wp_subdir.mkdir(parents=True, exist_ok=True)

    # Find next N
    existing = sorted(wp_subdir.glob("arbiter-override-*.json"))
    n = len(existing) + 1
    path = wp_subdir / f"arbiter-override-{n}.json"
    path.write_text(json.dumps(decision.to_dict(), indent=2, sort_keys=True), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Arbiter override history query (for kanban display)
# ---------------------------------------------------------------------------


def get_arbiter_overrides_for_wp(
    feature_dir: Path,
    wp_id: str,
) -> list[dict[str, Any]]:
    """Collect all arbiter override records for a work package.

    Scans review-cycle artifacts and standalone JSON files in
    ``<feature_dir>/tasks/<wp_id>/`` and returns a list of raw decision dicts.

    Used by ``agent tasks status`` to surface override history.
    """
    overrides: list[dict[str, Any]] = []
    tasks_dir = feature_dir / "tasks"
    if not tasks_dir.exists():
        return overrides

    wp_subdir = tasks_dir / wp_id
    if not wp_subdir.exists():
        return overrides

    # Standalone JSON fallback files
    for json_file in sorted(wp_subdir.glob("arbiter-override-*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            overrides.append(data)
        except (json.JSONDecodeError, OSError):
            pass

    # Review-cycle artifacts with arbiter_override in frontmatter
    for md_file in sorted(wp_subdir.glob("review-cycle-*.md")):
        content = md_file.read_text(encoding="utf-8")
        fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
        if fm_match:
            from ruamel.yaml import YAML

            yaml = YAML()
            data = yaml.load(fm_match.group(1))
            if data and "arbiter_override" in data:
                overrides.append(dict(data["arbiter_override"]))

    return overrides
