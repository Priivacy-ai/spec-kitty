"""5-tier asset resolution: override > legacy > global-mission > global > package default.

Resolution tiers (checked in order):
1. OVERRIDE        -- .kittify/overrides/{templates,command-templates}/
2. LEGACY          -- .kittify/{templates,command-templates}/ (deprecated; emits warning)
3. GLOBAL_MISSION  -- ~/.kittify/missions/{mission}/{templates,command-templates}/
4. GLOBAL          -- ~/.kittify/{templates,command-templates}/
5. PACKAGE         -- charter-resolved doctrine/missions/{mission}/{templates,command-templates}/

After ``spec-kitty migrate`` has been run (i.e. ``~/.kittify/`` is
populated), legacy-tier warnings are suppressed.  Pre-migration projects
receive a single "run ``spec-kitty migrate``" nudge per CLI invocation.
"""

from __future__ import annotations

import logging
import sys
import warnings
from functools import lru_cache
from pathlib import Path
from typing import Protocol, cast

# Single source of truth for the resolution enum / result dataclass.
# Re-exported via the charter.resolution facade (which itself re-exports
# from doctrine.resolver, preserving object identity) so every importer
# shares one class identity — otherwise `ResolutionTier.X == ResolutionTier.X`
# fails across modules and test suites that import from both paths flake on
# `is`/`==`. Historical note: prior to 2026-04-15 this module defined its
# own duplicate ResolutionTier/ResolutionResult, which caused ~30 CI failures
# on the release-readiness job where doctrine.test_resolver and
# runtime.test_resolver_unit ran in the same session. The charter facade
# route was adopted in mission charter-mediated-doctrine-selection-01KRTZCA
# (WP07) to enforce the runtime → charter → doctrine boundary.
from charter.mission_type_profiles import ResolvedMissionType
from charter.resolution import ResolutionResult, ResolutionTier
from specify_cli.core.paths import assert_safe_path_segment

__all__ = [
    "ResolutionResult",
    "ResolutionTier",
    "TemplateConfigurationError",
    "TemplateURNError",
    "resolve_command",
    "resolve_configured_template",
    "resolve_mission",
    "resolve_template",
    "resolve_template_by_urn",
]

from specify_cli.runtime.home import get_kittify_home, get_package_asset_root

logger = logging.getLogger(__name__)

_WINDOWS_RESERVED_TEMPLATE_BASENAMES = frozenset(
    {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
    | {f"COM{index}" for index in range(1, 10)}
    | {f"LPT{index}" for index in range(1, 10)}
)


class TemplateConfigurationError(ValueError):
    """Raised when activated mission configuration cannot select a template.

    Attributes:
        mission_type: Activated mission-type ID, exact invalid candidate, or
            ``"<typeless>"`` for a neutral context.
        artifact_kind: Semantic template key requested by the caller.
        mapped_filename: Configured filename, when selection reached that far.
    """

    def __init__(
        self,
        *,
        mission_type: str | None,
        artifact_kind: str,
        reason: str,
        mapped_filename: str | None = None,
    ) -> None:
        self.mission_type = "<typeless>" if mission_type is None else mission_type
        self.artifact_kind = artifact_kind
        self.mapped_filename = mapped_filename
        super().__init__(
            f"Template configuration for mission type {self.mission_type!r} "
            f"and artifact kind {artifact_kind!r} {reason}."
        )


class TemplateURNError(ValueError):
    """Raised when a mission-qualified template URN cannot be resolved.

    Covers both malformed URNs (absent, blank, missing the ``template:``
    prefix, or not of the ``<mission>/<name>`` shape after the prefix) and
    well-formed URNs that no tier resolves. Fail-closed per C-001: the
    mission segment is never inferred or defaulted when absent.

    Attributes:
        urn: The exact URN string that failed to resolve.
    """

    def __init__(self, *, urn: str, reason: str) -> None:
        self.urn = urn
        super().__init__(f"Template URN {urn!r} {reason}.")


class _CharterTemplateResolver(Protocol):
    def resolve_command_template_path(self, mission: str, command: str) -> Path | None:
        ...

    def resolve_content_template_path(self, mission: str, name: str) -> Path | None:
        ...

    def resolve_mission_config_path(self, mission: str) -> Path | None:
        ...


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _assert_portable_template_filename(filename: str) -> None:
    """Reject single-segment filenames that alias Windows device paths."""
    if filename.endswith((".", " ")):
        raise ValueError(
            f"Template filename {filename!r} is not portable to Windows: "
            "filenames must not end with a dot or space"
        )

    basename = filename.split(".", maxsplit=1)[0].upper()
    if basename in _WINDOWS_RESERVED_TEMPLATE_BASENAMES:
        raise ValueError(
            f"Template filename {filename!r} is not portable to Windows: "
            f"{basename!r} is a reserved device basename"
        )


def _is_global_runtime_configured() -> bool:
    """Return True if ``~/.kittify/`` has been populated by ``ensure_runtime``.

    The presence of ``cache/version.lock`` is the authoritative indicator
    that the global runtime has been bootstrapped at least once.  This
    avoids false positives from an empty ``~/.kittify/`` directory.
    """
    try:
        home = get_kittify_home()
        return (home / "cache" / "version.lock").is_file()
    except RuntimeError:
        return False


# Module-level flag: ensures the migrate nudge is emitted at most once per
# CLI invocation (not per resolution call).
_migrate_nudge_shown = False


def _is_json_mode_invocation() -> bool:
    """Return True when the active CLI invocation requested machine JSON."""
    return "--json" in sys.argv[1:]


def _warn_legacy_asset(path: Path) -> None:
    """Emit a deprecation warning for a legacy-tier asset hit.

    When the global runtime is already configured (``~/.kittify/`` has
    ``cache/version.lock``), the warning is suppressed because the user
    simply hasn't run ``spec-kitty migrate`` for this *project* yet.
    Instead, a one-time stderr nudge is printed.
    """
    if _is_global_runtime_configured():
        # Global runtime exists — suppress noisy DeprecationWarning, emit
        # a single one-time nudge to stderr instead.
        _emit_migrate_nudge()
        return

    msg = (
        f"Legacy asset resolved: {path} — run 'spec-kitty migrate' to clean up. "
        f"Legacy resolution will be removed in the next major version."
    )
    logger.warning(msg)
    warnings.warn(msg, DeprecationWarning, stacklevel=3)


def _emit_migrate_nudge() -> None:
    """Print a one-time "run ``spec-kitty migrate``" message to stderr.

    Uses a module-level flag so the nudge appears at most once per CLI
    invocation regardless of how many assets are resolved.  Output goes
    to stderr so it never interferes with ``--json`` output on stdout.

    The runtime path shown in the message is rendered via
    :func:`specify_cli.paths.render_runtime_path` so Windows users see the
    real ``%LOCALAPPDATA%\\spec-kitty\\`` path and not a POSIX tilde literal
    (SC-002 of the Windows Compatibility Hardening mission).
    """
    global _migrate_nudge_shown  # noqa: PLW0603
    if _migrate_nudge_shown:
        return
    if _is_json_mode_invocation():
        return
    _migrate_nudge_shown = True
    from specify_cli.paths import render_runtime_path  # noqa: PLC0415
    from specify_cli.runtime.home import get_kittify_home  # noqa: PLC0415
    runtime_display = render_runtime_path(get_kittify_home())
    print(
        "Note: Run `spec-kitty migrate` to clean up legacy project files and use the "
        f"global runtime ({runtime_display}).",
        file=sys.stderr,
    )


def _reset_migrate_nudge() -> None:
    """Reset the one-time nudge flag (for testing only)."""
    global _migrate_nudge_shown  # noqa: PLW0603
    _migrate_nudge_shown = False


@lru_cache(maxsize=8)
def _charter_template_resolver_for(missions_root: str) -> _CharterTemplateResolver:
    """Return a charter template resolver for ``missions_root``.

    Kept at the Tier-5 boundary so package-default filesystem access remains
    routed through charter and repeated lookups reuse the same repository.
    """
    from charter.template_resolver import CharterTemplateResolver  # noqa: PLC0415

    return cast(
        _CharterTemplateResolver,
        CharterTemplateResolver.from_missions_root(Path(missions_root)),
    )


def _package_default_path(
    *,
    pkg_missions: Path,
    mission: str,
    subdir: str,
    name: str,
) -> Path | None:
    """Resolve package defaults through charter's doctrine facade."""
    charter_resolver = _charter_template_resolver_for(str(pkg_missions))
    if subdir == "command-templates":
        resolved = charter_resolver.resolve_command_template_path(mission, Path(name).stem)
        return resolved if isinstance(resolved, Path) else None
    if subdir == "templates":
        resolved = charter_resolver.resolve_content_template_path(mission, name)
        return resolved if isinstance(resolved, Path) else None

    pkg_path = pkg_missions / mission / subdir / name
    return pkg_path if pkg_path.is_file() else None


def _resolve_asset(
    name: str,
    subdir: str,
    project_dir: Path,
    mission: str = "software-dev",
) -> ResolutionResult:
    """Core 5-tier resolution logic shared by public helpers.

    Args:
        name: Filename to resolve (e.g. ``"plan.md"``).
        subdir: Subdirectory within each tier (``"templates"`` or
                ``"command-templates"``).
        project_dir: Root of the user project that contains ``.kittify/``.
        mission: Mission key used for tiers 3-5.

    Returns:
        ResolutionResult with the winning path, tier and mission.

    Raises:
        FileNotFoundError: If no tier provides the requested asset.
    """
    kittify = project_dir / ".kittify"

    # Tier 1 -- override
    override = kittify / "overrides" / subdir / name
    if override.is_file():
        return ResolutionResult(path=override, tier=ResolutionTier.OVERRIDE, mission=mission)

    # Tier 2 -- legacy
    legacy = kittify / subdir / name
    if legacy.is_file():
        _warn_legacy_asset(legacy)
        return ResolutionResult(path=legacy, tier=ResolutionTier.LEGACY, mission=mission)

    # Tier 3 -- global mission-specific (~/.kittify/missions/{mission}/...)
    try:
        global_home = get_kittify_home()

        global_mission_path = global_home / "missions" / mission / subdir / name
        if global_mission_path.is_file():
            return ResolutionResult(
                path=global_mission_path,
                tier=ResolutionTier.GLOBAL_MISSION,
                mission=mission,
            )

        # Tier 4 -- global non-mission (~/.kittify/{subdir}/{name})
        global_path = global_home / subdir / name
        if global_path.is_file():
            return ResolutionResult(path=global_path, tier=ResolutionTier.GLOBAL, mission=mission)
    except RuntimeError:
        # Cannot determine home directory -- skip tiers 3 and 4
        pass

    # Tier 5 -- package default via charter. Keep this call routed through
    # charter so runtime never binds directly to doctrine's repository shape.
    try:
        pkg_missions = get_package_asset_root()
        pkg_path = _package_default_path(
            pkg_missions=pkg_missions,
            mission=mission,
            subdir=subdir,
            name=name,
        )
        if pkg_path is not None and pkg_path.is_file():
            return ResolutionResult(
                path=pkg_path,
                tier=ResolutionTier.PACKAGE_DEFAULT,
                mission=mission,
            )
    except FileNotFoundError:
        pass

    raise FileNotFoundError(
        f"Asset '{name}' not found in any resolution tier "
        f"(subdir={subdir!r}, mission={mission!r}, project={project_dir})"
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def resolve_template(
    name: str,
    project_dir: Path,
    mission: str = "software-dev",
) -> ResolutionResult:
    """Resolve a template file through the 5-tier precedence chain.

    Checks (in order):
    1. .kittify/overrides/templates/{name}
    2. .kittify/templates/{name}  (legacy -- emits warning/nudge)
    3. ~/.kittify/missions/{mission}/templates/{name}
    4. ~/.kittify/templates/{name}
    5. <package>/missions/{mission}/templates/{name}

    Args:
        name: Template filename (e.g. ``"spec-template.md"``).
        project_dir: Project root containing ``.kittify/``.
        mission: Mission key (default ``"software-dev"``).

    Returns:
        ResolutionResult with the resolved path, tier, and mission.

    Raises:
        FileNotFoundError: If the template is not found at any tier.
    """
    return _resolve_asset(name, "templates", project_dir, mission)


def resolve_configured_template(
    artifact_kind: str,
    project_dir: Path,
    resolved_mission_type: ResolvedMissionType,
) -> ResolutionResult:
    """Resolve a content template selected by activated mission configuration.

    This first-stage mapping seam reads ``artifact_kind`` from an explicit
    activated mission context, then delegates the configured filename to
    :func:`resolve_template`. The existing five-tier filesystem precedence
    remains wholly owned by that second-stage resolver.

    This seam has no repository or activation-registry input, so it cannot
    revalidate whether a syntactically safe mission type was activated. That
    authenticity remains the producing charter resolver's responsibility. It
    does validate the ID as a safe path segment before reading the lazy mapping,
    preventing a forged context from escaping mission-scoped resolution roots.

    Args:
        artifact_kind: Semantic mapping key, such as ``"spec"`` or ``"plan"``.
        project_dir: Project root containing ``.kittify/``.
        resolved_mission_type: Explicit activated mission context. A neutral
            context is rejected rather than inferred as software development.

    Returns:
        ResolutionResult from the unchanged five-tier resolver.

    Raises:
        TemplateConfigurationError: If the context is typeless, its mapping is
            null, the key is absent or blank, or the configured file cannot be
            resolved at any permitted tier.
    """
    mission_type = resolved_mission_type.mission_type
    if mission_type is None:
        raise TemplateConfigurationError(
            mission_type=None,
            artifact_kind=artifact_kind,
            reason="requires an activated, non-typeless mission context",
        )

    try:
        assert_safe_path_segment(mission_type)
    except ValueError as exc:
        raise TemplateConfigurationError(
            mission_type=mission_type,
            artifact_kind=artifact_kind,
            reason=f"has unsafe mission type {mission_type!r} ({exc})",
        ) from exc

    template_set = resolved_mission_type.template_set
    if template_set is None:
        raise TemplateConfigurationError(
            mission_type=mission_type,
            artifact_kind=artifact_kind,
            reason="has no configured template mapping",
        )

    mapped_filename = template_set.get(artifact_kind)
    if mapped_filename is None:
        raise TemplateConfigurationError(
            mission_type=mission_type,
            artifact_kind=artifact_kind,
            reason="is missing the requested mapping key",
        )
    if not mapped_filename.strip():
        raise TemplateConfigurationError(
            mission_type=mission_type,
            artifact_kind=artifact_kind,
            mapped_filename=mapped_filename,
            reason="maps to a blank filename",
        )

    try:
        assert_safe_path_segment(mapped_filename)
        _assert_portable_template_filename(mapped_filename)
    except ValueError as exc:
        raise TemplateConfigurationError(
            mission_type=mission_type,
            artifact_kind=artifact_kind,
            mapped_filename=mapped_filename,
            reason=f"maps to unsafe filename {mapped_filename!r} ({exc})",
        ) from exc

    try:
        return resolve_template(mapped_filename, project_dir, mission=mission_type)
    except FileNotFoundError as exc:
        raise TemplateConfigurationError(
            mission_type=mission_type,
            artifact_kind=artifact_kind,
            mapped_filename=mapped_filename,
            reason=f"maps to unresolved filename {mapped_filename!r}",
        ) from exc


#: URN prefix identifying a template node's DRG identity, mirroring
#: ``doctrine.drg.models.NodeKind.TEMPLATE.value`` (``"template"``).
_TEMPLATE_URN_PREFIX = "template:"

#: ``resolve_template_by_id`` only consults ``TierRoot.project_dir`` for the
#: override/legacy tiers (verified against ``doctrine.template_catalog``);
#: ``missions_root`` matters solely to the discovery surface
#: (``discover_templates``), which this URN lane never calls. A fixed,
#: non-existent sentinel keeps that fact explicit instead of silently
#: reusing an unrelated path.
_URN_LANE_MISSIONS_ROOT_SENTINEL = Path("/nonexistent-template-urn-missions-root")


def resolve_template_by_urn(
    urn: str,
    project_dir: Path,
) -> ResolutionResult:
    """Resolve a mission-qualified ``template:<mission>/<name>`` URN.

    This is Lane 2 of the name↔URN resolution contract (C-004,
    ``contracts/name-urn-resolution.md``): a graph-addressed resolution path
    added *alongside* :func:`resolve_configured_template` (Lane 1, the
    name-based creation path). Neither lane re-wires the other --
    :func:`resolve_configured_template`'s signature is unchanged.

    The URN is split into its mission-qualified ``<mission>/<name>`` template
    ID and handed to
    :func:`doctrine.template_catalog.resolve_template_by_id`, which performs
    that split itself and delegates to the same Stage-2 five-tier precedence
    (override > legacy > global-mission > global > package) that
    :func:`resolve_template` implements -- so an override at
    ``.kittify/overrides/templates/<file>`` wins on this lane exactly as it
    does on the name-based lane (US3.3).

    Args:
        urn: Mission-qualified template URN, e.g.
            ``"template:software-dev/spec-template.md"``.
        project_dir: Project root containing ``.kittify/`` (participates in
            the override/legacy tiers).

    Returns:
        ResolutionResult from the unchanged five-tier resolver.

    Raises:
        TemplateURNError: If the URN is absent/blank, missing the
            ``"template:"`` prefix, malformed (not ``"<mission>/<name>"``
            after the prefix), or unresolvable at any tier. The mission
            segment is never inferred or defaulted (C-001, no #2660
            inference reintroduction) -- an unqualified URN fails closed
            rather than defaulting to ``"software-dev"``.
    """
    if not urn or not urn.strip():
        raise TemplateURNError(urn=urn, reason="is absent or blank")

    if not urn.startswith(_TEMPLATE_URN_PREFIX):
        raise TemplateURNError(
            urn=urn,
            reason=f"does not start with the required {_TEMPLATE_URN_PREFIX!r} prefix",
        )

    template_id = urn[len(_TEMPLATE_URN_PREFIX) :]

    from doctrine.template_catalog import TierRoot, resolve_template_by_id  # noqa: PLC0415

    tier_roots = [
        TierRoot(
            tier=ResolutionTier.PACKAGE_DEFAULT,
            missions_root=_URN_LANE_MISSIONS_ROOT_SENTINEL,
            project_dir=project_dir,
        )
    ]

    try:
        return resolve_template_by_id(template_id, tier_roots=tier_roots)
    except ValueError as exc:
        raise TemplateURNError(urn=urn, reason=f"is malformed ({exc})") from exc
    except FileNotFoundError as exc:
        raise TemplateURNError(
            urn=urn,
            reason=f"could not be resolved at any tier ({exc})",
        ) from exc


def resolve_command(
    name: str,
    project_dir: Path,
    mission: str = "software-dev",
) -> ResolutionResult:
    """Resolve a command template through the 5-tier precedence chain.

    Checks (in order):
    1. .kittify/overrides/command-templates/{name}
    2. .kittify/command-templates/{name}  (legacy -- emits warning/nudge)
    3. ~/.kittify/missions/{mission}/command-templates/{name}
    4. ~/.kittify/command-templates/{name}
    5. <package>/missions/{mission}/command-templates/{name}

    Args:
        name: Command template filename (e.g. ``"plan.md"``).
        project_dir: Project root containing ``.kittify/``.
        mission: Mission key (default ``"software-dev"``).

    Returns:
        ResolutionResult with the resolved path, tier, and mission.

    Raises:
        FileNotFoundError: If the command template is not found at any tier.
    """
    return _resolve_asset(name, "command-templates", project_dir, mission)


def resolve_mission(
    name: str,
    project_dir: Path,
) -> ResolutionResult:
    """Resolve a mission.yaml through the precedence chain.

    Checks (in order):
    1. .kittify/overrides/missions/{name}/mission.yaml
    2. .kittify/missions/{name}/mission.yaml  (legacy -- emits warning/nudge)
    3. ~/.kittify/missions/{name}/mission.yaml
    4. <package>/missions/{name}/mission.yaml

    Note: missions are inherently mission-scoped, so there is no separate
    "global non-mission" tier for mission configs.

    Args:
        name: Mission key (e.g. ``"software-dev"``).
        project_dir: Project root containing ``.kittify/``.

    Returns:
        ResolutionResult with the resolved path, tier, and mission.

    Raises:
        FileNotFoundError: If the mission config is not found at any tier.
    """
    kittify = project_dir / ".kittify"
    filename = "mission.yaml"

    # Tier 1 -- override
    override = kittify / "overrides" / "missions" / name / filename
    if override.is_file():
        return ResolutionResult(path=override, tier=ResolutionTier.OVERRIDE, mission=name)

    # Tier 2 -- legacy
    legacy = kittify / "missions" / name / filename
    if legacy.is_file():
        _warn_legacy_asset(legacy)
        return ResolutionResult(path=legacy, tier=ResolutionTier.LEGACY, mission=name)

    # Tier 3 -- global (missions are inherently mission-scoped)
    try:
        global_home = get_kittify_home()
        global_path = global_home / "missions" / name / filename
        if global_path.is_file():
            return ResolutionResult(path=global_path, tier=ResolutionTier.GLOBAL_MISSION, mission=name)
    except RuntimeError:
        pass

    # Tier 4 -- package default via charter.
    try:
        pkg_missions = get_package_asset_root()
        pkg_path = _charter_template_resolver_for(str(pkg_missions)).resolve_mission_config_path(
            name
        )
        if pkg_path is not None and pkg_path.is_file():
            return ResolutionResult(path=pkg_path, tier=ResolutionTier.PACKAGE_DEFAULT, mission=name)
    except FileNotFoundError:
        pass

    raise FileNotFoundError(f"Mission '{name}' config not found in any resolution tier (project={project_dir})")
