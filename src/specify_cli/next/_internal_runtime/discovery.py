"""Mission pack discovery with deterministic precedence."""

# Internalized from spec-kitty-runtime 0.4.3 as part of
# `shared-package-boundary-cutover-01KQ22DS` (mission). See
# `runtime-standalone-package-retirement-01KQ20Z8` for the upstream
# public-API inventory.
from __future__ import annotations

import os
from pathlib import Path

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

from specify_cli.next._internal_runtime.schema import (
    DiscoveredMission,
    MissionPackManifest,
    MissionRuntimeError,
    MissionTemplate,
    load_mission_template_file,
)

_CONFIG_FILENAME = "config.yaml"
_KITTIFY_DIRNAME = ".kittify"
_MISSION_FILENAME = "mission.yaml"
_MISSIONS_DIRNAME = "missions"
_OVERRIDES_DIRNAME = "overrides"
_USER_GLOBAL_MISSIONS = "missions"


# ---------------------------------------------------------------------------
# Reserved built-in mission keys (R-002)
# ---------------------------------------------------------------------------

#: Mission keys reserved for the built-in tier. Custom missions discovered
#: from any non-builtin tier whose ``mission.key`` matches one of these are
#: rejected by ``mission_loader.validator.validate_custom_mission`` with
#: ``MISSION_KEY_RESERVED``. The built-in tier itself is exempt — built-ins
#: are allowed (and expected) to declare these keys.
RESERVED_BUILTIN_KEYS: frozenset[str] = frozenset(
    {
        "software-dev",
        "research",
        "documentation",
        "plan",
    }
)


def is_reserved_key(key: str) -> bool:
    """Return ``True`` iff ``key`` is a reserved built-in mission key."""
    return key in RESERVED_BUILTIN_KEYS


# ---------------------------------------------------------------------------
# Shadowing diagnostics models
# ---------------------------------------------------------------------------


class DiscoveryWarning(BaseModel):
    model_config = ConfigDict(frozen=True)

    path: str
    tier: str
    origin: str
    error: str


class ShadowEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    key: str
    selected_path: str
    selected_tier: str
    selected_origin: str
    shadowed: list[DiscoveredMission] = Field(default_factory=list)


class ShadowingDiagnostics(BaseModel):
    model_config = ConfigDict(frozen=True)

    entries: list[ShadowEntry] = Field(default_factory=list)
    total_discovered: int
    total_shadowed: int


# ---------------------------------------------------------------------------
# Discovery context
# ---------------------------------------------------------------------------


class DiscoveryContext(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    project_dir: Path | None = None
    explicit_paths: list[Path] = Field(default_factory=list)
    env_var_name: str = "SPEC_KITTY_MISSION_PATHS"
    user_home: Path = Field(default_factory=lambda: Path.home())
    builtin_roots: list[Path] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _split_env_paths(value: str) -> list[Path]:
    if not value.strip():
        return []
    return [Path(chunk) for chunk in value.split(os.pathsep) if chunk.strip()]


def _collect_from_manifest(pack_root: Path) -> list[Path]:
    """Collect mission paths from a mission-pack.yaml manifest.

    Validates against MissionPackManifest schema. Raises MissionRuntimeError
    on invalid manifests.
    """
    pack_file = pack_root / "mission-pack.yaml"
    if not pack_file.exists():
        return []
    with open(pack_file, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    if not isinstance(raw, dict):
        raise MissionRuntimeError(f"Mission pack manifest must be a mapping: {pack_file}")

    # Validate against MissionPackManifest schema.
    if "pack" not in raw:
        raise MissionRuntimeError(f"Mission pack manifest missing required 'pack' section: {pack_file}")

    manifest = MissionPackManifest.model_validate(raw)

    paths: list[Path] = []
    for entry in manifest.missions:
        paths.append(pack_root / entry.path)
    return paths


def _scan_root(root: Path) -> list[Path]:
    candidates: list[Path] = []

    if root.is_file() and root.name == _MISSION_FILENAME:
        return [root]

    if not root.exists() or not root.is_dir():
        return []

    # Explicit manifest entries first.
    candidates.extend(_collect_from_manifest(root))

    # Legacy/common mission-root layout: <root>/<mission_key>/mission.yaml
    for mission_file in sorted(root.glob(f"*/{_MISSION_FILENAME}")):
        candidates.append(mission_file)

    # Canonical pack layout.
    missions_dir = root / _MISSIONS_DIRNAME
    if missions_dir.is_dir():
        for mission_file in sorted(missions_dir.glob(f"*/{_MISSION_FILENAME}")):
            candidates.append(mission_file)

    # Direct mission root fallback.
    direct_mission = root / _MISSION_FILENAME
    if direct_mission.exists():
        candidates.append(direct_mission)

    # De-duplicate while preserving order.
    seen: set[Path] = set()
    unique: list[Path] = []
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        unique.append(candidate)
    return unique


def _project_config_pack_paths(project_dir: Path) -> list[Path]:
    config_file = project_dir / _KITTIFY_DIRNAME / _CONFIG_FILENAME
    if not config_file.exists():
        return []
    with open(config_file, encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    mission_packs = raw.get("mission_packs", [])
    if not isinstance(mission_packs, list):
        return []
    return [project_dir / pack for pack in mission_packs if isinstance(pack, str)]


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


class DiscoveryResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    missions: list[DiscoveredMission] = Field(default_factory=list)
    warnings: list[DiscoveryWarning] = Field(default_factory=list)


def _build_tiers(context: DiscoveryContext) -> list[tuple[str, str, list[Path]]]:
    """Build the ordered list of discovery tiers from context."""
    tiers: list[tuple[str, str, list[Path]]] = []

    tiers.append(("explicit", "explicit_paths", context.explicit_paths))

    env_value = os.environ.get(context.env_var_name, "")
    tiers.append(("env", context.env_var_name, _split_env_paths(env_value)))

    project_dir = context.project_dir
    if project_dir:
        tiers.append(
            (
                "project_override",
                str(project_dir / _KITTIFY_DIRNAME / _OVERRIDES_DIRNAME / _MISSIONS_DIRNAME),
                [project_dir / _KITTIFY_DIRNAME / _OVERRIDES_DIRNAME / _MISSIONS_DIRNAME],
            )
        )
        tiers.append(
            (
                "project_legacy",
                str(project_dir / _KITTIFY_DIRNAME / _MISSIONS_DIRNAME),
                [project_dir / _KITTIFY_DIRNAME / _MISSIONS_DIRNAME],
            )
        )

    tiers.append(
        (
            "user_global",
            str(context.user_home / _KITTIFY_DIRNAME / _USER_GLOBAL_MISSIONS),
            [context.user_home / _KITTIFY_DIRNAME / _USER_GLOBAL_MISSIONS],
        )
    )

    if project_dir:
        tiers.append(
            (
                "project_config",
                str(project_dir / _KITTIFY_DIRNAME / _CONFIG_FILENAME),
                _project_config_pack_paths(project_dir),
            )
        )

    tiers.append(("builtin", "builtin_roots", context.builtin_roots))
    return tiers


def discover_missions_with_warnings(context: DiscoveryContext) -> DiscoveryResult:
    """Discover missions by precedence, collecting warnings for load failures.

    Returns DiscoveryResult with both missions and warnings.
    """
    tiers = _build_tiers(context)

    discovered: list[DiscoveredMission] = []
    warnings: list[DiscoveryWarning] = []
    selected_by_key: set[str] = set()

    for tier, origin, roots in tiers:
        for root in roots:
            for mission_yaml in _scan_root(root):
                try:
                    template = load_mission_template_file(mission_yaml)
                except Exception as exc:
                    warnings.append(
                        DiscoveryWarning(
                            path=str(mission_yaml),
                            tier=tier,
                            origin=origin,
                            error=str(exc),
                        )
                    )
                    continue
                key = template.mission.key
                selected = key not in selected_by_key
                if selected:
                    selected_by_key.add(key)
                discovered.append(
                    DiscoveredMission(
                        key=key,
                        path=str(mission_yaml.resolve()),
                        origin=origin,
                        precedence_tier=tier,
                        selected=selected,
                    )
                )

    return DiscoveryResult(missions=discovered, warnings=warnings)


def discover_missions(context: DiscoveryContext) -> list[DiscoveredMission]:
    """Discover missions by precedence.

    Includes shadowed missions with `selected=False` so callers can surface
    collisions with origin metadata.

    For load-failure warnings, use discover_missions_with_warnings() instead.
    """
    return discover_missions_with_warnings(context).missions


def load_mission_template(path_or_key: str, context: DiscoveryContext | None = None) -> MissionTemplate:
    """Load mission template by explicit path or discovered mission key."""
    candidate_path = Path(path_or_key)

    if candidate_path.exists():
        if candidate_path.is_dir():
            candidate_path = candidate_path / "mission.yaml"
        return load_mission_template_file(candidate_path)

    if context is None:
        context = DiscoveryContext()

    discovered = discover_missions(context)
    for item in discovered:
        if item.key == path_or_key and item.selected:
            return load_mission_template_file(Path(item.path))

    raise MissionRuntimeError(f"Mission '{path_or_key}' not found. Checked discovery tiers via context={context.model_dump()}")


# ---------------------------------------------------------------------------
# Shadowing diagnostics
# ---------------------------------------------------------------------------


def diagnose_shadowing(context: DiscoveryContext) -> ShadowingDiagnostics:
    """Run discover_missions() and structure results as a shadowing report."""
    discovered = discover_missions(context)

    # Group by key.
    by_key: dict[str, list[DiscoveredMission]] = {}
    for item in discovered:
        by_key.setdefault(item.key, []).append(item)

    entries: list[ShadowEntry] = []
    total_shadowed = 0

    for key, items in by_key.items():
        selected_item = next((i for i in items if i.selected), items[0])
        shadowed_items = [i for i in items if not i.selected]
        total_shadowed += len(shadowed_items)
        entries.append(
            ShadowEntry(
                key=key,
                selected_path=selected_item.path,
                selected_tier=selected_item.precedence_tier,
                selected_origin=selected_item.origin,
                shadowed=shadowed_items,
            )
        )

    return ShadowingDiagnostics(
        entries=entries,
        total_discovered=len(discovered),
        total_shadowed=total_shadowed,
    )
