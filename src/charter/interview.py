"""Interview answer model for charter generation."""

from __future__ import annotations

import importlib.resources
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import cast

from ruamel.yaml import YAML

from charter.catalog import DoctrineCatalog, load_doctrine_catalog
from charter.resolver import DEFAULT_TOOL_REGISTRY

# Known action values for LocalSupportDeclaration normalization.
_KNOWN_ACTIONS: frozenset[str] = frozenset({"specify", "plan", "implement", "review"})

# Glob characters that indicate a path pattern rather than an explicit file.
_GLOB_CHARS: tuple[str, ...] = ("*", "?", "[", "]")


@dataclass(frozen=True)
class LocalSupportDeclaration:
    """One project-local doctrine support file declared in interview answers."""

    path: str
    action: str | None = None
    target_kind: str | None = None
    target_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {"path": self.path}
        if self.action is not None:
            d["action"] = self.action
        if self.target_kind is not None:
            d["target_kind"] = self.target_kind
        if self.target_id is not None:
            d["target_id"] = self.target_id
        return d

    @classmethod
    def from_dict(cls, data: object) -> LocalSupportDeclaration | None:
        """Parse a single declaration dict, returning None for invalid entries."""
        if not isinstance(data, dict):
            return None
        raw_path = data.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            return None
        path = raw_path.strip()
        action = _normalize_optional_string(data.get("action"))
        target_kind = _normalize_optional_string(data.get("target_kind"))
        target_id = _normalize_optional_string(data.get("target_id"))
        return cls(path=path, action=action, target_kind=target_kind, target_id=target_id)


def validate_local_support_declarations(
    declarations: list[LocalSupportDeclaration],
) -> tuple[list[LocalSupportDeclaration], list[str]]:
    """Validate and normalize a list of declarations.

    Returns (valid_declarations, error_messages).
    Rejects directory paths (trailing slash or no extension when a glob char present)
    and paths containing glob characters.
    """
    valid: list[LocalSupportDeclaration] = []
    errors: list[str] = []

    for decl in declarations:
        path = decl.path
        # Reject glob patterns
        if any(c in path for c in _GLOB_CHARS):
            errors.append(
                f"local_supporting_files path '{path}' contains glob characters; "
                "explicit file paths only."
            )
            continue
        # Reject paths that look like directories (trailing slash)
        if path.endswith("/") or path.endswith("\\"):
            errors.append(
                f"local_supporting_files path '{path}' looks like a directory; "
                "explicit file paths only."
            )
            continue
        # Normalize action: unknown values are silently dropped (set to None)
        normalized_action: str | None = None
        if decl.action is not None:
            if decl.action in _KNOWN_ACTIONS:
                normalized_action = decl.action
            else:
                errors.append(
                    f"local_supporting_files path '{path}': unknown action "
                    f"'{decl.action}' (expected one of {sorted(_KNOWN_ACTIONS)}); "
                    "treating as global."
                )
                # Still include the declaration but with action=None
        normalized = LocalSupportDeclaration(
            path=path,
            action=normalized_action,
            target_kind=decl.target_kind,
            target_id=decl.target_id,
        )
        valid.append(normalized)

    return valid, errors


QUESTION_ORDER: tuple[str, ...] = (
    "project_intent",
    "languages_frameworks",
    "testing_requirements",
    "quality_gates",
    "review_policy",
    "performance_targets",
    "deployment_constraints",
    "documentation_policy",
    "risk_boundaries",
    "amendment_process",
    "exception_policy",
)

MINIMAL_QUESTION_ORDER: tuple[str, ...] = (
    "project_intent",
    "languages_frameworks",
    "testing_requirements",
    "quality_gates",
    "review_policy",
    "performance_targets",
    "deployment_constraints",
)


QUESTION_PROMPTS: dict[str, str] = {
    "project_intent": "What is the core user outcome this project optimizes for?",
    "languages_frameworks": "What languages/frameworks are expected?",
    "testing_requirements": "What testing and coverage expectations apply?",
    "quality_gates": "What quality gates must pass before merge?",
    "review_policy": "What review/approval policy should contributors follow?",
    "performance_targets": "What performance targets matter most (or N/A)?",
    "deployment_constraints": "What deployment/platform constraints apply?",
    "documentation_policy": "What documentation standards should be enforced?",
    "risk_boundaries": "What safety, privacy, or reliability boundaries are non-negotiable?",
    "amendment_process": "How should charter changes be proposed and approved?",
    "exception_policy": "How should exceptions to the charter be handled?",
}

_DEFAULT_MISSION_PARADIGMS: dict[str, tuple[str, ...]] = {}

_DEFAULT_MISSION_DIRECTIVES: dict[str, tuple[str, ...]] = {}


_UNSET = object()


@dataclass(frozen=True)
class CharterInterview:
    """Persisted interview answers used to compile charter artifacts."""

    mission: str
    profile: str
    answers: dict[str, str]
    selected_paradigms: list[str]
    selected_directives: list[str]
    available_tools: list[str]
    agent_profile: str | None = None
    agent_role: str | None = None
    local_supporting_files: list[LocalSupportDeclaration] | None = None
    selected_tactics: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        # Normalize None to empty list for local_supporting_files (frozen dataclass workaround)
        if self.local_supporting_files is None:
            object.__setattr__(self, "local_supporting_files", [])

    def to_dict(self) -> dict[str, object]:
        d: dict[str, object] = {
            "schema_version": "1.0.0",
            "mission": self.mission,
            "profile": self.profile,
            "answers": dict(self.answers),
            "selected_paradigms": list(self.selected_paradigms),
            "selected_directives": list(self.selected_directives),
            "selected_tactics": list(self.selected_tactics),
            "available_tools": list(self.available_tools),
            "agent_profile": self.agent_profile,
            "agent_role": self.agent_role,
        }
        if self.local_supporting_files:
            d["local_supporting_files"] = [decl.to_dict() for decl in self.local_supporting_files]
        return d

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CharterInterview:
        mission = str(data.get("mission", "software-dev")).strip() or "software-dev"
        profile = str(data.get("profile", "minimal")).strip() or "minimal"
        raw_answers = data.get("answers")
        answers: dict[str, str] = (
            {str(k): str(v) for k, v in raw_answers.items()} if isinstance(raw_answers, dict) else {}
        )

        raw_local = data.get("local_supporting_files")
        local_supporting_files: list[LocalSupportDeclaration] = []
        if isinstance(raw_local, list):
            for item in raw_local:
                parsed = LocalSupportDeclaration.from_dict(item)
                if parsed is not None:
                    local_supporting_files.append(parsed)

        return cls(
            mission=mission,
            profile=profile,
            answers=answers,
            selected_paradigms=_normalize_list(data.get("selected_paradigms")),
            selected_directives=_normalize_list(data.get("selected_directives")),
            available_tools=_normalize_list(data.get("available_tools")),
            agent_profile=_normalize_optional_string(data.get("agent_profile")),
            agent_role=_normalize_optional_string(data.get("agent_role")),
            local_supporting_files=local_supporting_files,
            selected_tactics=_normalize_list(data.get("selected_tactics")),
        )


def default_interview(
    *,
    mission: str,
    profile: str = "minimal",
    doctrine_catalog: DoctrineCatalog | None = None,
) -> CharterInterview:
    """Return deterministic default interview answers."""
    catalog = doctrine_catalog or load_doctrine_catalog()
    defaults = _load_packaged_defaults()
    raw_default_answers = defaults.get("answers", {})
    answers: dict[str, str] = (
        dict(cast(dict[str, str], raw_default_answers))
        if isinstance(raw_default_answers, dict)
        else {}
    )

    if profile == "minimal":
        answers = {key: answers[key] for key in MINIMAL_QUESTION_ORDER}

    default_paradigms = _resolve_default_selection(
        mission=mission,
        configured=_DEFAULT_MISSION_PARADIGMS,
        available=catalog.paradigms,
    )
    default_directives = _resolve_default_selection(
        mission=mission,
        configured=_DEFAULT_MISSION_DIRECTIVES,
        available=catalog.directives,
    )

    return CharterInterview(
        mission=mission,
        profile=profile,
        answers=answers,
        selected_paradigms=_normalize_iterable(
            cast(Iterable[str] | None, defaults.get("selected_paradigms")),
            fallback=default_paradigms,
        ),
        selected_directives=_normalize_iterable(
            cast(Iterable[str] | None, defaults.get("selected_directives")),
            fallback=default_directives,
        ),
        available_tools=_normalize_iterable(
            cast(Iterable[str] | None, defaults.get("available_tools")),
            fallback=sorted(DEFAULT_TOOL_REGISTRY),
        ),
        selected_tactics=_normalize_iterable(
            cast(Iterable[str] | None, defaults.get("selected_tactics")),
            fallback=[],
        ),
    )


def read_interview_answers(path: Path) -> CharterInterview | None:
    """Read interview answers from YAML, returning None when missing/invalid."""
    if not path.exists():
        return None

    yaml = YAML(typ="safe")
    try:
        data = yaml.load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return None

    if not isinstance(data, dict):
        return None

    return CharterInterview.from_dict(data)


def write_interview_answers(path: Path, interview: CharterInterview) -> None:
    """Persist interview answers to YAML."""
    path.parent.mkdir(parents=True, exist_ok=True)
    yaml = YAML()
    yaml.default_flow_style = False
    with path.open("w", encoding="utf-8") as handle:
        yaml.dump(interview.to_dict(), handle)


def apply_answer_overrides(
    interview: CharterInterview,
    *,
    answers: dict[str, str] | None = None,
    selected_paradigms: Iterable[str] | None = None,
    selected_directives: Iterable[str] | None = None,
    selected_tactics: Iterable[str] | None = None,
    available_tools: Iterable[str] | None = None,
    agent_profile: str | None | object = _UNSET,
    agent_role: str | None | object = _UNSET,
    local_supporting_files: list[LocalSupportDeclaration] | None | object = _UNSET,
) -> CharterInterview:
    """Return an updated interview with selected fields overridden."""
    merged_answers = dict(interview.answers)
    if answers:
        for key, value in answers.items():
            if value is None:
                continue
            merged_answers[str(key)] = str(value)

    resolved_local: list[LocalSupportDeclaration]
    if local_supporting_files is _UNSET:
        resolved_local = list(interview.local_supporting_files or [])
    elif local_supporting_files is None:
        resolved_local = []
    else:
        resolved_local = list(cast(list[LocalSupportDeclaration], local_supporting_files))

    return CharterInterview(
        mission=interview.mission,
        profile=interview.profile,
        answers=merged_answers,
        selected_paradigms=_normalize_iterable(
            selected_paradigms,
            fallback=interview.selected_paradigms,
        ),
        selected_directives=_normalize_iterable(
            selected_directives,
            fallback=interview.selected_directives,
        ),
        available_tools=_normalize_iterable(
            available_tools,
            fallback=interview.available_tools,
        ),
        agent_profile=interview.agent_profile if agent_profile is _UNSET else _normalize_optional_string(agent_profile),
        agent_role=interview.agent_role if agent_role is _UNSET else _normalize_optional_string(agent_role),
        local_supporting_files=resolved_local,
        selected_tactics=_normalize_iterable(
            selected_tactics,
            fallback=interview.selected_tactics,
        ),
    )


def _normalize_iterable(values: Iterable[str] | None, *, fallback: list[str]) -> list[str]:
    if values is None:
        return list(fallback)
    normalized: list[str] = []
    for value in values:
        item = str(value).strip()
        if item and item not in normalized:
            normalized.append(item)
    return normalized


def _normalize_list(raw: object) -> list[str]:
    if isinstance(raw, str):
        return _normalize_csv(raw)
    if isinstance(raw, list):
        return _normalize_iterable(raw, fallback=[])
    return []


def _normalize_csv(raw: str) -> list[str]:
    parts = [part.strip() for part in raw.split(",")]
    return [part for part in parts if part]


def _normalize_optional_string(raw: object) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    return value or None


def _load_packaged_defaults() -> dict[str, object]:
    """Load authoritative default interview content from ``defaults.yaml``."""
    empty: dict[str, object] = {
        "answers": {},
        "selected_paradigms": [],
        "selected_directives": [],
        "selected_tactics": [],
        "available_tools": [],
    }
    try:
        defaults_path = importlib.resources.files("charter").joinpath("defaults.yaml")
        content = defaults_path.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError, TypeError):
        return empty

    yaml = YAML(typ="safe")
    try:
        data = yaml.load(content) or {}
    except Exception:
        return empty

    if not isinstance(data, dict):
        return empty

    answers = data.get("answers")
    normalized_answers = (
        {str(key): str(value) for key, value in answers.items()}
        if isinstance(answers, dict)
        else {}
    )
    return {
        "answers": normalized_answers,
        "selected_paradigms": _normalize_list(data.get("selected_paradigms")),
        "selected_directives": _normalize_list(data.get("selected_directives")),
        "selected_tactics": _normalize_list(data.get("selected_tactics")),
        "available_tools": _normalize_list(data.get("available_tools")),
    }


def _resolve_default_selection(
    *,
    mission: str,
    configured: dict[str, tuple[str, ...]],
    available: frozenset[str],
) -> list[str]:
    selected: list[str] = []
    for candidate in configured.get(mission, ()):
        if candidate in available and candidate not in selected:
            selected.append(candidate)
    return selected
