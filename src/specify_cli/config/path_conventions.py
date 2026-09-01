"""Project-level path-convention override reader (#3016).

Reads the ``project.path_conventions`` subkey of ``.kittify/config.yaml`` and returns a validated,
remap-only override mapping. Resolved AHEAD of mission-type doctrine defaults by
``validators.paths.validate_mission_paths`` (see ``contracts/precedence-contract.md``), the override lets
a project whose real source layout is not ``src/`` (Django ``apps/``, Go ``internal/``) be accepted
honestly — WITHOUT changing the blocking-by-default policy established by #3783.

Fail-closed policy (FR-008): a malformed ``path_conventions`` *section* — present but not a mapping, a
non-string / null value, or an unknown key — raises :class:`PathConventionsConfigError`. This is scoped to
the section shape only: an absent key, or a whole ``config.yaml`` that is missing/unreadable, returns
``{}`` (lenient), matching the co-resident section readers (e.g. ``charter_runtime/preflight/config.py``).
"""

from __future__ import annotations

import warnings
from pathlib import Path

from specify_cli.mission import VALID_PATH_KEYS

# Only the runtime entry point is exported. ``ARTIFACT_ROUTED_KEYS`` is a module-internal constant and
# ``PathConventionsConfigError`` propagates as a typed exception (SC-007) rather than being caught by a
# co-resident src caller; both stay importable by name (tests reference them directly) without entering
# the exported surface, keeping the symbol-level dead-code gate honest.
__all__ = ["load_project_path_conventions"]

# Keys whose mission default value is a mission artifact token (they resolve on the mission's
# ``feature_dir`` rather than the repo root). Overriding one would flip its resolution surface and drop
# the mission-surface artifact check — ``validators.paths`` decides routing from ``declared[key]`` — so
# they are excluded from the override vocabulary (C-010). ``deliverables`` (default value ``contracts/``)
# is the sole such key across the four built-in mission types.
ARTIFACT_ROUTED_KEYS: frozenset[str] = frozenset({"deliverables"})

# The section key, hoisted so the error/warning f-strings below don't repeat the literal (Sonar S1192).
_SECTION = "project.path_conventions"


class PathConventionsConfigError(ValueError):
    """Raised when the ``project.path_conventions`` section is malformed (FR-008)."""


def load_project_path_conventions(repo_root: Path) -> dict[str, str]:
    """Return the validated project ``path_conventions`` override, or ``{}`` when absent.

    Reads ONLY the ``project.path_conventions`` subkey — never the whole ``project:`` block, which
    carries identity fields (``uuid``/``slug``/``node_id``/``build_id``) that must not be rejected (C-011).
    Remap-only: an artifact-routed key (``deliverables``) is warned-and-ignored (C-010); filtering to keys
    a given mission actually declares happens at the merge site in ``validate_mission_paths``.

    Args:
        repo_root: Repository root containing ``.kittify/config.yaml``.

    Returns:
        A mapping of path-convention key to the project's declared directory (may be empty).

    Raises:
        PathConventionsConfigError: the section is present but not a mapping, names a key outside
            :data:`specify_cli.mission.VALID_PATH_KEYS` (a typo), carries a non-string/null value, an
            empty/blank-string value (a bare ``Path("")`` collapses to the repo root, which always
            exists, silently defeating strict enforcement), or a value that is an absolute path or
            contains a ``..`` traversal segment (override values are repo-relative layout dirs only).
            Section-shape only — a missing or unreadable ``config.yaml`` is lenient and returns ``{}``.
    """
    config_path = repo_root / ".kittify" / "config.yaml"
    if not config_path.exists():
        return {}

    try:
        from ruamel.yaml import YAML

        yaml = YAML(typ="safe")
        data = yaml.load(config_path)
    except Exception:  # noqa: BLE001 — best-effort file read; a corrupt file never breaks accept.
        return {}

    if not isinstance(data, dict):
        return {}

    project = data.get("project")
    if not isinstance(project, dict):
        return {}

    section = project.get("path_conventions")
    if section is None:
        return {}
    if not isinstance(section, dict):
        raise PathConventionsConfigError(f"{_SECTION} must be a mapping of path-convention key to directory, got {type(section).__name__}.")

    override: dict[str, str] = {}
    for key, value in section.items():
        if key not in VALID_PATH_KEYS:
            raise PathConventionsConfigError(f"Unknown path-convention key {key!r} in {_SECTION}. Known keys: {sorted(VALID_PATH_KEYS)}.")
        if key in ARTIFACT_ROUTED_KEYS:
            warnings.warn(
                f"{_SECTION}.{key} is ignored: {key!r} is artifact-routed and cannot be "
                "overridden (it would flip the artifact-resolution surface). See ADR "
                "project-path-convention-override-precedes-doctrine.",
                stacklevel=2,
            )
            continue
        if not isinstance(value, str):
            raise PathConventionsConfigError(f"{_SECTION}.{key} must be a string directory, got {type(value).__name__}.")
        if not value.strip():
            # An empty/blank value collapses `Path("")` to the repo root under
            # `validate_mission_paths`, which always exists — silently defeating strict
            # enforcement (SC-006/SC-007) instead of naming the missing directory.
            raise PathConventionsConfigError(f"{_SECTION}.{key} must not be empty or blank.")
        normalized_value = value.strip()
        candidate = Path(normalized_value)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise PathConventionsConfigError(f"{_SECTION}.{key} must be a repo-relative path with no '..' traversal, got {value!r}.")
        override[key] = normalized_value
    return override
