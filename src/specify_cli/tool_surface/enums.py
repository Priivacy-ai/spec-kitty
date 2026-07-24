"""Classification enumerations for the tool surface contract bounded context.

All enumerations use :class:`enum.StrEnum` (Python 3.11+). This module has zero
runtime dependencies on other ``specify_cli`` modules so it can be imported in
isolation.
"""

from __future__ import annotations

from enum import StrEnum


class ToolSurfaceKind(StrEnum):
    """The kind of surface a definition describes.

    ``session_presence`` is intentionally **not** a member: it is a *provider*
    name that expands into ``CONTEXT_FILE``, ``HOOK``, and/or ``RULE`` instances
    depending on the harness (see data-model.md).
    """

    COMMAND_SKILL = "command_skill"
    DOCTRINE_SKILL = "doctrine_skill"
    CONTEXT_FILE = "context_file"
    RULE = "rule"
    HOOK = "hook"
    AGENT_PROFILE = "agent_profile"
    PLUGIN_MANIFEST = "plugin_manifest"
    NATIVE_CONFIG = "native_config"
    COMMAND_FILE = "command_file"


class SourceKind(StrEnum):
    """Where the surface content originates."""

    CHECKED_IN = "checked_in"
    GENERATED = "generated"
    USER_GLOBAL = "user_global"
    PACKAGE = "package"
    PLUGIN = "plugin"


class InstallScope(StrEnum):
    """The scope at which a surface is installed."""

    PROJECT = "project"
    USER_GLOBAL = "user_global"
    TEAM = "team"
    PLUGIN_BUNDLE = "plugin_bundle"


class ActivationMode(StrEnum):
    """How a surface is activated at runtime."""

    ALWAYS = "always"
    GLOB = "glob"
    MODEL_DECISION = "model_decision"
    MANUAL = "manual"
    USER_INVOKED = "user_invoked"
    SKILLS_INVOKABLE = "skills_invocable"
    EVENT = "event"
    DISABLED = "disabled"


class CommandSurfaceCapability(StrEnum):
    """Capability of a tool's command surface."""

    ADAPTER = "adapter"
    SKILLS_INVOKABLE = "skills_invocable"
    NONE = "none"


class MutabilityPolicy(StrEnum):
    """How a surface file may be mutated during repair."""

    GENERATED_OVERWRITE_IF_HASH_MATCHES = "generated_overwrite_if_hash_matches"
    PRESERVE_USER_EDITS = "preserve_user_edits"
    USER_EDITABLE = "user_editable"
    READ_ONLY_PACKAGE = "read_only_package"


class RequiredPolicy(StrEnum):
    """Whether a surface is required, repairable, optional, or a research gap."""

    REQUIRED = "required"
    REPAIRABLE_REQUIRED = "repairable_required"
    OPTIONAL = "optional"
    RESEARCH_GAP = "research_gap"
