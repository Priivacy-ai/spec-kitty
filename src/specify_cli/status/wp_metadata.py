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


def _resolve_agent_fallback(
    model: str | None,
    agent_profile: str | None,
    role: str | None,
) -> AgentAssignment:
    """Resolve fallback agent metadata for missing or unsupported agent shapes."""
    return AgentAssignment(
        tool="unknown",
        model=model or "unknown-model",
        profile_id=agent_profile or None,
        role=role or None,
    )


def _resolve_agent_from_assignment(agent: AgentAssignment) -> AgentAssignment:
    """Return an existing AgentAssignment unchanged."""
    return agent


def _resolve_agent_from_string(
    tool: str,
    model: str | None,
    agent_profile: str | None,
    role: str | None,
) -> AgentAssignment:
    """Resolve agent metadata when the agent field is a bare (no-colon) string."""
    fallback = _resolve_agent_fallback(model, agent_profile, role)
    return AgentAssignment(
        tool=tool,
        model=fallback.model,
        profile_id=fallback.profile_id,
        role=fallback.role,
    )


# ── 4-tuple parser (WP03 / GitHub issue #833) ───────────────────────────────


# Per-tool agent registry defaults. Keys are tool identifiers; values are the
# default (model, profile_id) the runtime should assume when a colon-formatted
# agent string omits or empties out those slots. The role default is constant
# at "implementer" per data-model.md §2 and is therefore not stored here.
#
# Currently we expose a generic fallback only — there is no formal agent
# registry shipping per-tool defaults at this layer. The values below preserve
# the historical fallback semantics so existing callers continue to see
# "unknown-model" / None when the underlying WP frontmatter does not carry
# those fields. New tools can be added here without changing the parser.
_AGENT_DEFAULTS: dict[str, tuple[str, str | None]] = {}


def _default_model_for(tool: str, fallback: str | None) -> str:
    """Return the agent registry's default model for *tool*.

    Falls back to the supplied *fallback* (typically ``WPMetadata.model``)
    and, finally, to ``"unknown-model"`` so the returned tuple's ``model``
    slot is always a non-empty string.
    """
    if tool in _AGENT_DEFAULTS:
        registry_default = _AGENT_DEFAULTS[tool][0]
        if registry_default:
            return registry_default
    return fallback or "unknown-model"


def _default_profile_for(tool: str, fallback: str | None) -> str | None:
    """Return the agent registry's default profile_id for *tool*.

    Falls back to *fallback* (typically ``WPMetadata.agent_profile``) and
    finally to ``None`` to preserve historical behavior for callers that
    treat ``profile_id`` as optional.
    """
    if tool in _AGENT_DEFAULTS:
        registry_default = _AGENT_DEFAULTS[tool][1]
        if registry_default is not None:
            return registry_default
    return fallback


def _resolve_agent_from_colon_string(
    raw: str,
    wp_id: str,
    model_field: str | None,
    agent_profile_field: str | None,
    role_field: str | None,
) -> AgentAssignment:
    """Parse a colon-formatted agent identity string into an AgentAssignment.

    This is the **total parser** required by WP03 (GitHub issue #833). It
    handles every supported colon arity (1/2/3/4) without silently
    discarding fields:

    ::

        tool                              -> (tool, default_model, default_profile_id, "implementer")
        tool:model                        -> (tool, model,         default_profile_id, "implementer")
        tool:model:profile_id             -> (tool, model,         profile_id,         "implementer")
        tool:model:profile_id:role        -> (tool, model,         profile_id,         role)

    Empty positional segments (e.g., ``tool::profile_id:role``) fall back
    to the corresponding default. Trailing missing segments fall back to
    defaults. An empty ``tool`` raises ``ValueError`` — parsing is total
    but ``tool`` is required to identify the agent.

    The defaults table is sourced (where available) from the agent registry
    via :func:`_default_model_for` and :func:`_default_profile_for`; the
    ``role`` default is the documented constant ``"implementer"``.

    Tracks: GitHub issue #833.
    """
    segments = raw.split(":")
    # Pad to 4 segments with empty strings so trailing-missing positions
    # share the same fallback path as empty positional segments.
    while len(segments) < 4:
        segments.append("")

    tool, model_seg, profile_seg, role_seg = segments[:4]
    if not tool:
        raise ValueError(f"Empty agent tool for WP {wp_id}: {raw!r}")

    resolved_model = model_seg or _default_model_for(tool, model_field)
    resolved_profile = profile_seg or _default_profile_for(tool, agent_profile_field)
    resolved_role = role_seg or role_field or "implementer"

    return AgentAssignment(
        tool=tool,
        model=resolved_model,
        profile_id=resolved_profile,
        role=resolved_role,
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
        """Resolve agent assignment with legacy coercion and full 4-tuple support.

        Unifies agent metadata resolution across all legacy formats and the
        colon-separated 4-tuple identity introduced for GitHub issue #833.

        Colon-formatted ``agent`` strings are parsed totally: every supplied
        non-empty positional segment is preserved verbatim. Empty positional
        segments and trailing missing segments fall back to the documented
        defaults below.

        **Defaults table (per data-model.md §2)**::

            tool                              -> (tool, default_model, default_profile_id, "implementer")
            tool:model                        -> (tool, model,         default_profile_id, "implementer")
            tool:model:profile_id             -> (tool, model,         profile_id,         "implementer")
            tool:model:profile_id:role        -> (tool, model,         profile_id,         role)

        - ``default_model`` is sourced from the agent registry's current
          default model for the resolved *tool*; if no registry entry exists,
          we fall back to :attr:`WPMetadata.model` and finally to
          ``"unknown-model"``.
        - ``default_profile_id`` is the agent registry's current default
          profile for the resolved *tool*; if no registry entry exists, we
          fall back to :attr:`WPMetadata.agent_profile` (which may be
          ``None``).
        - ``role`` default is the documented constant ``"implementer"``.

        An empty ``tool`` (e.g., ``":opus-4-7"``) raises :class:`ValueError`
        — parsing is total but ``tool`` is required to identify the agent.

        Bare (no-colon) string agents (e.g., ``agent="claude"``) preserve
        the legacy fallback semantics so pre-#833 callers do not see
        regressions in their resolved tuple.

        Tracks: GitHub issue #833.

        Fallback Order (for non-colon-string and dict / None inputs):
        1. Direct AgentAssignment from agent field (if already an AgentAssignment)
        2. Bare string agent field → tool=value, model=self.model (fallback to default)
        3. Dict agent field → tool/model/profile_id/role from dict, fallback to other fields
        4. None/missing agent → tool=default, model=self.model (fallback to default)
        5. Fallback to agent_profile field for profile_id
        6. Fallback to role field for role
        7. Return sensible defaults for missing values

        Returns:
            AgentAssignment with all four identity fields resolved.
            ``tool``, ``model`` and ``role`` are always non-empty for
            colon-formatted inputs. ``profile_id`` may be ``None`` when no
            registry default is available and the WP did not supply one.
        """
        if isinstance(self.agent, AgentAssignment):
            return _resolve_agent_from_assignment(self.agent)

        if isinstance(self.agent, str) and self.agent:
            # WP03 (#833): colon-formatted strings carry the full 4-tuple
            # identity. Dispatch to the total parser so every supplied
            # non-empty segment is preserved verbatim.
            if ":" in self.agent:
                return _resolve_agent_from_colon_string(
                    self.agent,
                    self.work_package_id,
                    self.model,
                    self.agent_profile,
                    self.role,
                )
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
