"""Interview answer model for charter generation."""

from __future__ import annotations

import importlib.resources
import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from ruamel.yaml import YAML

from charter._io import load_charter_file
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
        if path.endswith(("/", "\\")):
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
_LYNN_COLE_DIRECTIVE = "DIRECTIVE_039"
_LYNN_COLE_PARADIGM = "deep-module-design"
_LYNN_COLE_EXPLICIT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\blynn\s+cole\b"),
)
_LYNN_COLE_CONCERN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bagents?\s+(?:write|produce|generate|create)\s+too\s+much\s+code\b"),
    re.compile(r"\b(?:ai|llm|agentic|generated)\s+code\s+(?:is\s+)?(?:bloated|sprawling|too\s+long)\b"),
    re.compile(r"\b(?:code|implementation)\s+bloat\b"),
    re.compile(r"\b(?:avoid|stop|prevent|reduce)\s+(?:agentic\s+)?(?:code\s+)?bloat\b"),
    re.compile(r"\bover[- ]?abstract(?:ion|ed|ing)?\b"),
    re.compile(r"\bsprawling\s+(?:helpers?|functions?|code|implementation)\b"),
    re.compile(r"\btoo\s+many\s+(?:helpers?|abstractions?|files?|layers?)\b"),
)


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

        return apply_doctrine_intent_aliases(cls(
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
        ))


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

    return apply_doctrine_intent_aliases(CharterInterview(
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
    ))


def read_interview_answers(path: Path, *, unsafe: bool = False) -> CharterInterview | None:
    """Read interview answers from YAML, returning None when missing/invalid.

    Encoding-consistency failures (:class:`CharterEncodingError`, a subclass
    of :class:`kernel.errors.KittyInternalConsistencyError`) propagate to the
    caller so the operator sees the diagnostic with remediation guidance.
    Other failure modes (missing file, malformed YAML structure on a
    successfully-decoded file, wrong top-level type) continue to degrade to
    ``None`` per the pre-existing contract.

    Args:
        path: filesystem path to the interview YAML file.
        unsafe: when True, bypass CHARTER_ENCODING_AMBIGUOUS by accepting the
            highest-confidence decode candidate and logging bypass_used=True in
            provenance.  Use only when you have inspected the file and accept
            the operational risk; the bypass is recorded in
            ``.encoding-provenance.jsonl``.
    """
    if not path.exists():
        return None

    yaml = YAML(typ="safe")
    text = load_charter_file(path, unsafe=unsafe).text
    try:
        data = yaml.load(text) or {}
    except Exception:  # noqa: BLE001 — YAML parse failures degrade to None
        # Pre-existing resilience contract: a syntactically-broken YAML file
        # whose encoding decoded cleanly is treated as "no usable answers"
        # rather than halting the interview command. Encoding errors are NOT
        # caught here — they raise above in load_charter_file().
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


def apply_org_charter_pre_fill_to_answers(
    *,
    answers_path: Path,
    interview_defaults: dict[str, str | bool],
    required_directives: list[str],
) -> list[str]:
    """Pure data side-effect: non-destructively pre-fill ``answers.yaml``.

    The org-layer caller (``specify_cli.doctrine.org_charter``) loads and
    merges org-pack policies and passes the resulting interview defaults
    and required directives into this helper as plain Python data.  This
    keeps the ``charter`` layer free of ``specify_cli`` imports
    (ADR 2026-03-27-1) while letting the YAML side-effect live next to
    the rest of the interview answer machinery.

    Semantics:

    * For each key in ``interview_defaults``, set the value in
      ``answers.yaml`` **only when the key is missing**.  Existing values
      are preserved so re-running the interview never reverts
      project-specific choices to org defaults.
    * For ``required_directives``, append entries that are not already
      present in ``selected_directives`` (set-like union, order preserved).
    * When nothing changes, ``answers.yaml`` is not written.

    Returns a list of human-readable messages describing what was applied.
    Returns an empty list when no changes were needed.
    """
    if not interview_defaults and not required_directives:
        return []

    yaml = YAML()
    yaml.default_flow_style = False

    existing: dict[str, Any] = {}
    if answers_path.exists():
        try:
            with answers_path.open("r", encoding="utf-8") as handle:
                loaded = yaml.load(handle)
        except Exception:  # noqa: BLE001 — malformed YAML treated as empty
            loaded = None
        if isinstance(loaded, dict):
            existing = loaded

    messages: list[str] = []
    prefilled = 0
    for key, value in interview_defaults.items():
        if key not in existing:
            existing[key] = value
            prefilled += 1

    existing_directives_raw = existing.get("selected_directives")
    if isinstance(existing_directives_raw, list):
        existing_directives: list[str] = [
            str(d) for d in existing_directives_raw
        ]
    elif isinstance(existing_directives_raw, str):
        existing_directives = _normalize_csv(existing_directives_raw)
    else:
        existing_directives = []

    new_required = [
        d for d in required_directives if d not in existing_directives
    ]
    if new_required:
        existing["selected_directives"] = existing_directives + new_required
        messages.append(
            f"Pre-selected {len(new_required)} directives from org charter "
            "required_directives."
        )

    if prefilled:
        messages.append(
            f"Pre-filled {prefilled} interview defaults from org charter."
        )

    if messages:
        answers_path.parent.mkdir(parents=True, exist_ok=True)
        with answers_path.open("w", encoding="utf-8") as handle:
            yaml.dump(existing, handle)

    return messages


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

    return apply_doctrine_intent_aliases(CharterInterview(
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
    ))


def apply_doctrine_intent_aliases(interview: CharterInterview) -> CharterInterview:
    """Select doctrine implied by well-known user shorthand in interview text."""
    if not _matches_lynn_cole_alias(interview):
        return interview

    selected_directives = _append_unique(interview.selected_directives, _LYNN_COLE_DIRECTIVE)
    selected_paradigms = _append_unique(interview.selected_paradigms, _LYNN_COLE_PARADIGM)
    if (
        selected_directives == interview.selected_directives
        and selected_paradigms == interview.selected_paradigms
    ):
        return interview

    return CharterInterview(
        mission=interview.mission,
        profile=interview.profile,
        answers=dict(interview.answers),
        selected_paradigms=selected_paradigms,
        selected_directives=selected_directives,
        available_tools=list(interview.available_tools),
        agent_profile=interview.agent_profile,
        agent_role=interview.agent_role,
        local_supporting_files=list(interview.local_supporting_files or []),
        selected_tactics=list(interview.selected_tactics),
    )


def _matches_lynn_cole_alias(interview: CharterInterview) -> bool:
    haystack = " ".join(str(value).lower() for value in interview.answers.values())
    if not haystack.strip():
        return False
    return any(pattern.search(haystack) for pattern in _LYNN_COLE_EXPLICIT_PATTERNS) or any(
        pattern.search(haystack) for pattern in _LYNN_COLE_CONCERN_PATTERNS
    )


def _append_unique(values: list[str], item: str) -> list[str]:
    result = list(values)
    if item not in result:
        result.append(item)
    return result


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
