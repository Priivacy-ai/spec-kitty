"""Typed Pydantic v2 model for WP frontmatter metadata.

Provides :class:`WPMetadata` — a frozen, validated value object for every
field observed in ``kitty-specs/*/tasks/WP*.md`` frontmatter — and a
convenience loader :func:`read_wp_frontmatter` that wraps
:class:`~specify_cli.frontmatter.FrontmatterManager`.

Uses ``extra="forbid"`` to reject unrecognised fields at parse time.
If a new frontmatter key appears in the wild, add it to the model
before it can be used.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from specify_cli.status.models import AgentAssignment, Lane


_DEFAULT_PROFILE = "generic-agent"


def _resolve_agent_fallback(
    model: str | None,
    agent_profile: str | None,
    role: str | None,
) -> AgentAssignment:
    """Resolve fallback agent metadata for missing or unsupported agent shapes."""
    return AgentAssignment(
        tool="unknown",
        model=model or "unknown-model",
        profile_id=agent_profile or _DEFAULT_PROFILE,
        role=role or None,
    )


def _resolve_agent_from_assignment(agent: AgentAssignment) -> AgentAssignment:
    """Return an existing AgentAssignment unchanged."""
    return agent


def _parse_agent_string(value: str) -> tuple[str, str | None, str | None, str | None]:
    """Split a colon-separated agent string into (tool, model, profile_id, role).

    Wire format: <tool>[:<model>[:<profile_id>[:<role>]]]
    Unspecified trailing parts are returned as None.
    """
    parts = value.split(":", 3)
    tool = parts[0]
    model = parts[1] if len(parts) > 1 else None
    profile_id = parts[2] if len(parts) > 2 else None
    role = parts[3] if len(parts) > 3 else None
    return tool, model, profile_id, role


def _resolve_agent_from_string(
    value: str,
    model: str | None,
    agent_profile: str | None,
    role: str | None,
) -> AgentAssignment:
    """Resolve agent metadata when the agent field is a non-empty string.

    If the string contains colons it is treated as a wire-format
    ``tool:model:profile_id:role`` tuple; unspecified trailing parts
    fall back to the separate frontmatter fields or the module defaults.
    A plain string without colons is used as-is for ``tool``.
    """
    parsed_tool, parsed_model, parsed_profile, parsed_role = _parse_agent_string(value)
    fallback = _resolve_agent_fallback(model, agent_profile, role)
    return AgentAssignment(
        tool=parsed_tool,
        model=parsed_model or fallback.model,
        profile_id=parsed_profile or fallback.profile_id,
        role=parsed_role or fallback.role,
    )


def _resolve_agent_from_dict(
    agent: dict[str, Any],
    model: str | None,
    agent_profile: str | None,
    role: str | None,
) -> AgentAssignment:
    """Resolve agent metadata when the agent field is a dict."""
    fallback = _resolve_agent_fallback(model, agent_profile, role)
    return AgentAssignment(
        tool=agent.get("tool") or fallback.tool,
        model=agent.get("model") or fallback.model,
        profile_id=agent.get("profile_id") or fallback.profile_id,
        role=agent.get("role") or fallback.role,
    )


class WPMetadata(BaseModel):
    """Typed schema for WP frontmatter.

    Frozen (immutable) value object.  All consumers should treat instances
    as read-only snapshots of a WP file's frontmatter section.
    """

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        populate_by_name=True,
    )

    # ── Required: identity ─────────────────────────────────────
    work_package_id: str
    title: str | None = None

    # ── Required: dependency graph ─────────────────────────────
    dependencies: list[str] = Field(default_factory=list)

    # ── Optional: branch contract (populated post-bootstrap) ───
    base_branch: str | None = None
    base_commit: str | None = None
    created_at: str | None = None

    # ── Optional: planning metadata ────────────────────────────
    planning_base_branch: str | None = None
    merge_target_branch: str | None = None
    branch_strategy: str | None = None
    requirement_refs: list[str] = Field(default_factory=list)
    priority: str | None = None

    # ── Optional: execution context ────────────────────────────
    execution_mode: str | None = None
    owned_files: list[str] = Field(default_factory=list)
    authoritative_surface: str | None = None
    task_type: str | None = None

    # ── Optional: workflow metadata ────────────────────────────
    subtasks: list[Any] = Field(default_factory=list)
    phase: str | None = None
    phases: str | None = None
    assignee: str | None = None
    agent: Any = None  # str in most WPs, dict (tool/model keys) in some legacy files
    model: str | None = None
    agent_profile: str | None = None
    role: str | None = None
    shell_pid: int | None = None
    history: list[Any] = Field(default_factory=list)
    lane: Lane | None = None
    feature_slug: str | None = None
    activity_log: str | None = None

    # ── Optional: review metadata ──────────────────────────────
    review_status: str | None = None
    reviewed_by: str | None = None
    approved_by: str | None = None
    reviewer: Any = None  # str in newer WPs, dict in legacy mission 004
    reviewer_agent: str | None = None
    reviewer_shell_pid: str | None = None
    review_feedback: str | None = None
    review_feedback_file: str | None = None

    # ── Optional: descriptive metadata ─────────────────────────
    subtitle: str | None = None
    description: str | None = None
    estimated_duration: str | None = None
    tags: list[str] = Field(default_factory=list)

    # ── Observed-in-practice fields ────────────────────────────
    mission_id: str | None = None
    mission_number: str | None = None
    mission_slug: str | None = None
    status: str | None = None  # legacy status field seen in some mission WPs
    wp_code: str | None = None
    branch_strategy_override: str | None = None

    # ── Legacy aliases (consumed by model validator) ───────────
    work_package_title: str | None = None

    # ── Pre-processing (model-level) ──────────────────────────

    @model_validator(mode="before")
    @classmethod
    def _normalize_legacy_fields(cls, data: Any) -> Any:
        """Handle legacy field names and type quirks from older WP files."""
        if not isinstance(data, dict):
            return data

        # Legacy: mission 004 uses 'work_package_title' instead of 'title'
        if "title" not in data and "work_package_title" in data:
            data["title"] = data["work_package_title"]

        # Legacy: some files store dependencies as string '[]' instead of list
        deps = data.get("dependencies")
        if isinstance(deps, str):
            stripped = deps.strip()
            if stripped == "[]":
                data["dependencies"] = []
            else:
                # Attempt comma-separated: "WP01, WP02"
                data["dependencies"] = [s.strip() for s in stripped.split(",") if s.strip()]

        # Legacy: some files store requirement_refs as scalar string
        refs = data.get("requirement_refs")
        if isinstance(refs, str):
            data["requirement_refs"] = [s.strip() for s in refs.split(",") if s.strip()]

        return data

    # ── Field validators ───────────────────────────────────────

    @field_validator("work_package_id")
    @classmethod
    def validate_wp_id(cls, v: str) -> str:
        if not re.match(r"^WP\d{2,}$", v):
            raise ValueError(f"Invalid work_package_id: {v!r} (must match WP##)")
        return v

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str | None) -> str | None:
        if v is None:
            return None
        if not v.strip():
            raise ValueError("title must not be empty")
        return v

    @field_validator("base_commit")
    @classmethod
    def validate_base_commit(cls, v: str | None) -> str | None:
        if v is not None and not re.match(r"^[0-9a-f]{7,40}$", v):
            raise ValueError(f"Invalid base_commit: {v!r} (must be hex SHA)")
        return v

    @field_validator("phase", mode="before")
    @classmethod
    def coerce_phase(cls, v: Any) -> str | None:
        """Coerce non-string phase values (e.g. integer) to string."""
        if v is None:
            return None
        return str(v)

    @field_validator("shell_pid", mode="before")
    @classmethod
    def coerce_shell_pid(cls, v: Any) -> int | None:
        """Coerce string shell_pid from YAML frontmatter to int."""
        if v is None or v == "":
            return None
        return int(v)

    # ── Legacy lane aliases ────────────────────────────────────────
    # "doing" was the old name for in_progress before the Lane enum existed.
    _LANE_ALIASES: ClassVar[dict[str, str]] = {"doing": "in_progress"}

    @field_validator("lane", mode="before")
    @classmethod
    def coerce_lane(cls, v: Any) -> Lane | None:
        """Coerce string lane values to Lane enum; reject unknown values.

        The legacy alias ``"doing"`` is silently normalised to ``"in_progress"``
        so that older WP files written before the Lane enum still parse correctly.
        """
        if v is None or v == "":
            return None
        canonical = cls._LANE_ALIASES.get(str(v), str(v))
        try:
            return Lane(canonical)
        except ValueError as err:
            valid = ", ".join(lane.value for lane in Lane)
            raise ValueError(
                f"Invalid lane value: {v!r}. Must be one of: {valid}"
            ) from err

    # ── Computed properties ──────────────────────────────────────

    @property
    def display_title(self) -> str:
        """Human-readable title, falling back to ``work_package_id``.

        Strips surrounding whitespace when *title* is set.  Returns the
        WP id when *title* is ``None`` so callers never need to
        null-check.
        """
        if self.title is not None:
            return self.title.strip()
        return self.work_package_id

    def resolved_agent(self) -> AgentAssignment:
        """Resolve agent assignment with legacy coercion and fallback.

        Unifies agent metadata resolution across all legacy formats and fallback fields.
        Handles string agents, dict agents, None, and falls back to model, agent_profile,
        and role fields when the primary agent field is incomplete.

        Fallback Order:
        1. Direct AgentAssignment from agent field (if already an AgentAssignment)
        2. String agent field → tool=value, model=self.model (fallback to default)
        3. Dict agent field → tool/model/profile_id/role from dict, fallback to other fields
        4. None/missing agent → tool=default, model=self.model (fallback to default)
        5. Fallback to agent_profile field for profile_id
        6. Fallback to role field for role
        7. Return sensible defaults for missing values

        Returns:
            AgentAssignment with all resolved values (no None fields except optional ones)
        """
        if isinstance(self.agent, AgentAssignment):
            return _resolve_agent_from_assignment(self.agent)

        if isinstance(self.agent, str) and self.agent:
            return _resolve_agent_from_string(
                self.agent,
                self.model,
                self.agent_profile,
                self.role,
            )

        if isinstance(self.agent, dict):
            return _resolve_agent_from_dict(
                self.agent,
                self.model,
                self.agent_profile,
                self.role,
            )

        return _resolve_agent_fallback(
            self.model,
            self.agent_profile,
            self.role,
        )

    # ── Immutable update API ───────────────────────────────────

    def update(self, **kwargs: Any) -> WPMetadata:
        """Return a NEW WPMetadata with the specified fields changed.

        All Pydantic validation runs on the result.  The original
        instance is never mutated.

        Raises ``TypeError`` for unknown field names (before Pydantic
        sees them) so callers get a clear error at the call site.
        """
        known = type(self).model_fields
        for key in kwargs:
            if key not in known:
                raise TypeError(f"update() got an unexpected keyword argument {key!r}")
        merged = self.model_dump() | kwargs
        return type(self).model_validate(merged)

    def builder(self) -> _Builder:
        """Return a fluent :class:`_Builder` for multi-step composition.

        Example::

            new_meta = (
                meta.builder()
                .set(lane="in_progress")
                .set(agent="claude")
                .append_to_history(entry)
                .build()
            )
        """
        return _Builder(self)


class _Builder:
    """Fluent builder for composing multi-field WPMetadata updates.

    Accumulates changes and produces a NEW validated WPMetadata on
    :meth:`build`.  The source instance is never mutated.

    This class is intentionally private — consumer code obtains it
    via :meth:`WPMetadata.builder`.
    """

    __slots__ = ("_source", "_overrides", "_history_appends", "_dep_appends")

    def __init__(self, source: WPMetadata) -> None:
        self._source = source
        self._overrides: dict[str, Any] = {}
        self._history_appends: list[Any] = []
        self._dep_appends: list[str] = []

    def set(self, **kwargs: Any) -> _Builder:
        """Stage field overrides (validated on :meth:`build`)."""
        known = WPMetadata.model_fields
        for key in kwargs:
            if key not in known:
                raise TypeError(f"set() got an unexpected keyword argument {key!r}")
        self._overrides.update(kwargs)
        return self

    def append_to_history(self, entry: Any) -> _Builder:
        """Append a history entry (applied on :meth:`build`)."""
        self._history_appends.append(entry)
        return self

    def append_dependency(self, dep: str) -> _Builder:
        """Append a dependency (applied on :meth:`build`)."""
        self._dep_appends.append(dep)
        return self

    def build(self) -> WPMetadata:
        """Produce a new validated WPMetadata from accumulated changes."""
        merged = dict(self._overrides)

        if self._history_appends:
            base_history = list(merged.get("history", self._source.history))
            merged["history"] = base_history + list(self._history_appends)

        if self._dep_appends:
            base_deps = list(merged.get("dependencies", self._source.dependencies))
            merged["dependencies"] = base_deps + list(self._dep_appends)

        base_data = self._source.model_dump()
        base_data.update(merged)
        return WPMetadata.model_validate(base_data)


def read_wp_frontmatter(path: Path) -> tuple[WPMetadata, str]:
    """Load and validate WP frontmatter.

    Returns ``(WPMetadata, body_text)`` on success.

    Uses ``strict=False`` so that non-string values in optional fields
    (e.g. ``agent`` stored as a dict in some legacy WP files) are coerced
    rather than causing validation failures.

    Raises:
        FrontmatterError: On I/O or YAML parse failures.
        ValidationError: If the frontmatter fails ``WPMetadata`` validation.
    """
    from pydantic import ValidationError  # noqa: F401 — re-exported for callers

    from specify_cli.frontmatter import FrontmatterManager

    fm = FrontmatterManager()
    frontmatter_dict, body = fm.read(path)
    return WPMetadata.model_validate(frontmatter_dict, strict=False), body


__all__ = ["WPMetadata", "read_wp_frontmatter"]
