"""Interview answer model for charter generation."""

from __future__ import annotations

import importlib.resources
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from ruamel.yaml import YAML

from specify_cli.charter.catalog import DoctrineCatalog, load_doctrine_catalog
from specify_cli.charter.resolver import DEFAULT_TOOL_REGISTRY


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


@dataclass(frozen=True)
class CharterInterview:
    """Persisted interview answers used to compile charter artifacts."""

    mission: str
    profile: str
    answers: dict[str, str]
    selected_paradigms: list[str]
    selected_directives: list[str]
    available_tools: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": "1.0.0",
            "mission": self.mission,
            "profile": self.profile,
            "answers": dict(self.answers),
            "selected_paradigms": list(self.selected_paradigms),
            "selected_directives": list(self.selected_directives),
            "available_tools": list(self.available_tools),
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CharterInterview:
        mission = str(data.get("mission", "software-dev")).strip() or "software-dev"
        profile = str(data.get("profile", "minimal")).strip() or "minimal"
        raw_answers = data.get("answers")
        answers: dict[str, str]
        answers = {str(k): str(v) for k, v in raw_answers.items()} if isinstance(raw_answers, dict) else {}

        return cls(
            mission=mission,
            profile=profile,
            answers=answers,
            selected_paradigms=_normalize_list(data.get("selected_paradigms")),
            selected_directives=_normalize_list(data.get("selected_directives")),
            available_tools=_normalize_list(data.get("available_tools")),
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
    answers: dict[str, str] = dict(defaults.get("answers", {}))

    if profile == "minimal":
        answers = {key: answers[key] for key in MINIMAL_QUESTION_ORDER}

    return CharterInterview(
        mission=mission,
        profile=profile,
        answers=answers,
        selected_paradigms=_normalize_iterable(
            defaults.get("selected_paradigms"),
            fallback=[],
        ),
        selected_directives=_normalize_iterable(
            defaults.get("selected_directives"),
            fallback=[],
        ),
        available_tools=_normalize_iterable(
            defaults.get("available_tools"),
            fallback=sorted(DEFAULT_TOOL_REGISTRY),
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
    available_tools: Iterable[str] | None = None,
) -> CharterInterview:
    """Return an updated interview with selected fields overridden."""
    merged_answers = dict(interview.answers)
    if answers:
        for key, value in answers.items():
            if value is None:
                continue
            merged_answers[str(key)] = str(value)

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


def _load_packaged_defaults() -> dict[str, object]:
    """Load authoritative default interview content from the charter package."""
    empty = {
        "answers": {},
        "selected_paradigms": [],
        "selected_directives": [],
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
        "available_tools": _normalize_list(data.get("available_tools")),
    }
