"""
Agent profile repository with two-source loading (shipped + project).

Provides:
- Two-source YAML loading (shipped package data + project filesystem)
- Field-level merge semantics for project overrides
- Query methods (list_all, get, find_by_role)
- Hierarchy traversal (get_children, get_ancestors, get_hierarchy_tree)
- Hierarchy validation (cycle detection, orphaned references)
- Context-based matching with weighted scoring
- Save/delete for project profiles
"""

import warnings
from fnmatch import fnmatch
from pathlib import Path
from typing import Any

from importlib.resources import files
from pydantic import ValidationError
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

from .profile import AgentProfile, Role, TaskContext


def _filter_candidates_by_role(candidates: list[AgentProfile], required_role: str | None) -> list[AgentProfile]:
    """Return candidates matching required_role, or all candidates when role is unset."""
    if not required_role:
        return candidates
    role_str = required_role.lower() if isinstance(required_role, str) else required_role
    return [
        p for p in candidates
        if (isinstance(p.role, Role) and p.role.value == role_str)
        or (isinstance(p.role, str) and p.role.lower() == role_str)
        or p.profile_id == role_str
    ]


def _language_signal(context: TaskContext, profile: AgentProfile) -> float:
    """Return 1.0 if the context language matches the profile's specialization."""
    if context.language and profile.specialization_context and context.language.lower() in [
        lang.lower() for lang in profile.specialization_context.languages
    ]:
        return 1.0
    return 0.0


def _framework_signal(context: TaskContext, profile: AgentProfile) -> float:
    """Return 1.0 if the context framework matches the profile's specialization."""
    if context.framework and profile.specialization_context and context.framework.lower() in [
        fw.lower() for fw in profile.specialization_context.frameworks
    ]:
        return 1.0
    return 0.0


def _file_pattern_signal(context: TaskContext, profile: AgentProfile) -> float:
    """Return 1.0 if any context file path matches a profile file pattern."""
    if context.file_paths and profile.specialization_context:
        for file_path in context.file_paths:
            for pattern in profile.specialization_context.file_patterns:
                if fnmatch(file_path, pattern):
                    return 1.0
    return 0.0


def _keyword_signal(context: TaskContext, profile: AgentProfile) -> float:
    """Return 1.0 if any context keyword matches a profile domain keyword."""
    if context.keywords and profile.specialization_context:
        profile_kws = [kw.lower() for kw in profile.specialization_context.domain_keywords]
        for keyword in context.keywords:
            if keyword.lower() in profile_kws:
                return 1.0
    return 0.0


def _exact_id_signal(context: TaskContext, profile: AgentProfile) -> float:
    """Return 1.0 if required_role exactly matches the profile ID or role value."""
    if not context.required_role:
        return 0.0
    req = context.required_role.lower() if isinstance(context.required_role, str) else context.required_role
    role_val = profile.role.value if isinstance(profile.role, Role) else str(profile.role).lower()
    return 1.0 if (req == profile.profile_id or req == role_val) else 0.0


def _workload_penalty(workload: int) -> float:
    """Return score multiplier based on current workload (DDR-011)."""
    if workload <= 2:
        return 1.0
    if workload <= 4:
        return 0.85
    return 0.70


def _complexity_adjustment(is_specialist: bool, complexity: str) -> float:
    """Return score multiplier based on specialist/generalist × task complexity."""
    if is_specialist:
        return {"low": 0.9, "medium": 1.0, "high": 1.1}.get(complexity, 1.0)
    return {"low": 1.0, "medium": 1.0, "high": 0.9}.get(complexity, 1.0)


def _score_profile(context: TaskContext, profile: AgentProfile) -> float:
    """Compute the full adjusted DDR-011 score for a profile against a task context."""
    base_score = (
        _language_signal(context, profile) * 0.40
        + _framework_signal(context, profile) * 0.20
        + _file_pattern_signal(context, profile) * 0.20
        + _keyword_signal(context, profile) * 0.10
        + _exact_id_signal(context, profile) * 0.10
    )
    penalty = _workload_penalty(context.current_workload or 0)
    complexity_adj = _complexity_adjustment(
        profile.specializes_from is not None,
        context.complexity or "medium",
    )
    # When no context signals match (base_score=0), routing_priority becomes dominant.
    return (base_score + profile.routing_priority / 100.0) * penalty * complexity_adj


# ── Profile inheritance helpers ───────────────────────────────────────────────

# List-type profile fields merged by union rather than child-replaces-parent.
_LIST_FIELDS: frozenset[str] = frozenset({
    "capabilities", "directive-references", "canonical-verbs", "mode-defaults",
})


def _item_key(item: Any) -> str:
    """Extract a stable identity key for deduplication and exclusion matching.

    For DirectiveRef dicts, uses the 'code' field.
    For other dicts, falls back to full string repr.
    For plain values, uses str().
    """
    if isinstance(item, dict) and "code" in item:
        return str(item["code"])
    return str(item)


def _union_merge(parent_data: dict[str, Any], child_data: dict[str, Any]) -> dict[str, Any]:
    """Merge two profile data dicts with union semantics for list-type fields."""
    merged = parent_data.copy()
    for key, child_value in child_data.items():
        parent_value = merged.get(key)
        if key in _LIST_FIELDS and isinstance(parent_value, list) and isinstance(child_value, list):
            seen = {_item_key(item) for item in parent_value}
            merged[key] = parent_value + [item for item in child_value if _item_key(item) not in seen]
        elif isinstance(parent_value, dict) and isinstance(child_value, dict):
            nested = parent_value.copy()
            nested.update(child_value)
            merged[key] = nested
        else:
            merged[key] = child_value
    return merged


def _apply_excluding(
    merged: dict[str, Any],
    excluding: list[str] | dict[str, list[str]],
) -> dict[str, Any]:
    """Apply excluding declarations to the merged profile data dict."""
    if isinstance(excluding, list):
        for field_name in excluding:
            merged.pop(field_name, None)
    else:
        for field_name, values_to_remove in excluding.items():
            if field_name in merged and isinstance(merged[field_name], list):
                remove_set = {str(v) for v in values_to_remove}
                merged[field_name] = [
                    item for item in merged[field_name] if _item_key(item) not in remove_set
                ]
    return merged


class AgentProfileRepository:
    """Repository for loading and managing agent profiles from YAML files."""

    def __init__(
        self,
        shipped_dir: Path | None = None,
        project_dir: Path | None = None,
    ):
        """Initialize repository with shipped and/or project directories.

        Args:
            shipped_dir: Directory containing shipped profiles (defaults to package data)
            project_dir: Directory containing project-specific profiles (optional)
        """
        self._profiles: dict[str, AgentProfile] = {}
        self._shipped_dir = shipped_dir or self._default_shipped_dir()
        self._project_dir = project_dir
        self._hierarchy_index: dict[str, list[str]] | None = None
        self._load()

    @staticmethod
    def _default_shipped_dir() -> Path:
        """Get default shipped profiles directory from package data."""
        try:
            resource = files("doctrine.agent_profiles")
            if hasattr(resource, "joinpath"):
                return Path(str(resource.joinpath("shipped")))
            return Path(str(resource)) / "shipped"
        except Exception:
            return Path(__file__).parent / "shipped"

    def _load(self) -> None:
        """Load profiles from shipped and project directories."""
        yaml = YAML(typ="safe")
        shipped_profiles: dict[str, AgentProfile] = {}

        if self._shipped_dir.exists():
            for yaml_file in self._shipped_dir.glob("*.agent.yaml"):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue
                    profile = AgentProfile.model_validate(data)
                    shipped_profiles[profile.profile_id] = profile
                except Exception as e:
                    warnings.warn(
                        f"Skipping invalid shipped profile {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

        # Start with shipped profiles
        self._profiles = shipped_profiles.copy()

        # Load and merge project profiles
        if self._project_dir and self._project_dir.exists():
            for yaml_file in self._project_dir.glob("*.agent.yaml"):
                try:
                    data = yaml.load(yaml_file)
                    if data is None:
                        continue

                    profile_id = data.get("profile-id") or data.get("profile_id")
                    if not profile_id:
                        warnings.warn(
                            f"Skipping project profile {yaml_file.name}: no profile-id",
                            UserWarning,
                            stacklevel=2,
                        )
                        continue

                    # Check if this is an override or new profile
                    if profile_id in shipped_profiles:
                        # Merge with shipped profile
                        merged = self._merge_profiles(shipped_profiles[profile_id], data)
                        self._profiles[profile_id] = merged
                    else:
                        # New project-only profile
                        profile = AgentProfile.model_validate(data)
                        self._profiles[profile.profile_id] = profile
                except Exception as e:
                    warnings.warn(
                        f"Skipping invalid project profile {yaml_file.name}: {e}",
                        UserWarning,
                        stacklevel=2,
                    )

    def _merge_profiles(self, shipped: AgentProfile, project_data: dict[str, Any]) -> AgentProfile:
        """Merge project data into shipped profile at field level.

        Uses exclude_unset=True to detect explicitly set fields in project data.

        Args:
            shipped: Shipped profile to use as base
            project_data: Project profile data (dict from YAML)

        Returns:
            Merged profile with project fields overriding shipped fields
        """
        # Get shipped profile as dict (with by_alias to use kebab-case)
        shipped_dict = shipped.model_dump(by_alias=True)

        # Normalize project data keys to match YAML format (kebab-case)
        def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
            """Recursively merge dictionaries at field level."""
            result = base.copy()
            for key, value in override.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    # Recursively merge nested dicts
                    result[key] = deep_merge(result[key], value)
                else:
                    # Override with project value
                    result[key] = value
            return result

        merged_dict = deep_merge(shipped_dict, project_data)

        return AgentProfile.model_validate(merged_dict)

    def list_all(self) -> list[AgentProfile]:
        """Return all loaded profiles sorted by profile_id."""
        return sorted(self._profiles.values(), key=lambda p: p.profile_id)

    def get(self, profile_id: str) -> AgentProfile | None:
        """Get profile by ID or None if not found."""
        return self._profiles.get(profile_id)

    def find_by_role(self, role: Role | str) -> list[AgentProfile]:
        """Find all profiles matching the given role.

        Args:
            role: Role enum or string (case-insensitive)

        Returns:
            List of profiles with matching role
        """
        # Normalize role to string for comparison
        role_str = role.value if isinstance(role, Role) else role.lower()

        matches = []
        for profile in self._profiles.values():
            profile_role = profile.role.value if isinstance(profile.role, Role) else str(profile.role).lower()
            if profile_role == role_str:
                matches.append(profile)

        return matches

    def _build_hierarchy_index(self) -> None:
        """Build hierarchy index mapping parent_id -> [child_ids]."""
        if self._hierarchy_index is not None:
            return

        index: dict[str, list[str]] = {}

        for profile in self._profiles.values():
            if profile.specializes_from:
                parent_id = profile.specializes_from
                if parent_id not in index:
                    index[parent_id] = []
                index[parent_id].append(profile.profile_id)

        self._hierarchy_index = index

    def get_children(self, profile_id: str) -> list[AgentProfile]:
        """Get direct children of a profile.

        Args:
            profile_id: Parent profile ID

        Returns:
            List of profiles that specialize from this profile
        """
        self._build_hierarchy_index()

        if self._hierarchy_index is None:
            return []

        child_ids = self._hierarchy_index.get(profile_id, [])
        return [self._profiles[cid] for cid in child_ids if cid in self._profiles]

    def get_ancestors(self, profile_id: str) -> list[str]:
        """Get ancestor chain from profile to root.

        Args:
            profile_id: Starting profile ID

        Returns:
            Ordered list of ancestor profile IDs (immediate parent first)
        """
        ancestors = []
        current_id = profile_id
        visited = set()

        while current_id in self._profiles:
            profile = self._profiles[current_id]
            if not profile.specializes_from:
                break

            if profile.specializes_from in visited:
                # Cycle detected - stop
                break

            ancestors.append(profile.specializes_from)
            visited.add(current_id)
            current_id = profile.specializes_from

        return ancestors

    def get_hierarchy_tree(self) -> dict[str, Any]:
        """Get hierarchy as nested dict suitable for Rich Tree rendering.

        Returns:
            Nested dict: {root_id: {"children": {child_id: {...}}}}
        """
        self._build_hierarchy_index()

        # Find roots (profiles with no specializes_from)
        roots = [
            p.profile_id
            for p in self._profiles.values()
            if not p.specializes_from
        ]

        def build_subtree(profile_id: str) -> dict[str, Any]:
            """Recursively build subtree for a profile."""
            children_dict = {}
            for child in self.get_children(profile_id):
                children_dict[child.profile_id] = build_subtree(child.profile_id)
            return {"children": children_dict}

        tree = {}
        for root_id in roots:
            tree[root_id] = build_subtree(root_id)

        return tree

    def validate_hierarchy(self) -> list[str]:
        """Validate hierarchy for cycles, orphans, duplicates.

        Returns:
            List of error/warning messages (empty if valid)
        """
        errors = []

        # Check for cycles using DFS
        visited: set[str] = set()
        in_stack: set[str] = set()

        def has_cycle(profile_id: str) -> bool:
            """DFS to detect cycles."""
            if profile_id in in_stack:
                return True
            if profile_id in visited:
                return False

            visited.add(profile_id)
            in_stack.add(profile_id)

            profile = self._profiles.get(profile_id)
            if profile and profile.specializes_from and has_cycle(profile.specializes_from):
                return True

            in_stack.remove(profile_id)
            return False

        for profile_id in self._profiles:
            if profile_id not in visited and has_cycle(profile_id):
                errors.append(f"Cycle detected in hierarchy involving {profile_id}")

        # Check for orphaned references
        for profile in self._profiles.values():
            if profile.specializes_from and profile.specializes_from not in self._profiles:
                errors.append(
                    f"Orphaned reference: {profile.profile_id} specializes from "
                    f"nonexistent {profile.specializes_from}"
                )

        return errors

    def find_best_match(self, context: TaskContext) -> AgentProfile | None:
        """Find best matching profile for given task context using weighted scoring.

        Scoring algorithm (DDR-011):
            score = language_match × 0.40
                  + framework_match × 0.20
                  + file_pattern_match × 0.20
                  + keyword_match × 0.10
                  + exact_id_match × 0.10

        Adjustments:
            - workload_penalty: 0-2=1.0, 3-4=0.85, 5+=0.70
            - complexity_adjustment: specialist/generalist × complexity
            - routing_priority / 100

        Args:
            context: Task context with language, framework, file_paths, etc.

        Returns:
            Profile with highest adjusted score, or None if no profiles
        """
        if not self._profiles:
            return None

        candidates = [self.resolve_profile(profile_id) for profile_id in self._profiles]
        candidates = _filter_candidates_by_role(candidates, context.required_role)

        if not candidates:
            return None

        return max(candidates, key=lambda p: _score_profile(context, p))

    def resolve_profile(self, profile_id: str) -> AgentProfile:
        """Resolve a profile with inherited fields from its ancestor chain.

        Merge semantics are intentionally shallow within sections:
        - scalar/list fields: child replaces parent
        - dict section fields: child keys override one level deep,
          parent keys not present in child are preserved
        """
        profile = self.get(profile_id)
        if profile is None:
            raise KeyError(f"Profile '{profile_id}' not found")

        chain: list[AgentProfile] = [profile]
        visited: set[str] = {profile.profile_id}
        current = profile

        while current.specializes_from:
            parent_id = current.specializes_from
            if parent_id in visited:
                raise ValueError(f"Cycle detected while resolving profile '{profile_id}'")

            parent = self.get(parent_id)
            if parent is None:
                raise KeyError(
                    f"Profile '{profile_id}' references missing parent '{parent_id}'. "
                    "Ensure the parent profile exists in shipped/ or _proposed/ before resolving."
                )

            visited.add(parent.profile_id)
            chain.append(parent)
            current = parent

        # Build from root -> ... -> child using union merge for list-type fields.
        merged: dict[str, Any] = {}
        for node in reversed(chain):
            node_data = node.model_dump(by_alias=True, exclude_unset=True)
            merged = _union_merge(merged, node_data)

        # Apply excluding from the resolving (child/leaf) profile.
        # Exclusion is applied to the final merged result, not per-ancestor.
        if profile.excluding is not None:
            merged = _apply_excluding(merged, profile.excluding)

        return AgentProfile.model_validate(merged)

    def save(self, profile: AgentProfile) -> None:
        """Save profile to project directory.

        Args:
            profile: Profile to save

        Raises:
            ValueError: If project_dir is not configured
        """
        if self._project_dir is None:
            raise ValueError("Cannot save profile: project_dir not configured")

        # Ensure project_dir exists
        self._project_dir.mkdir(parents=True, exist_ok=True)

        # Write YAML file
        yaml = YAML()
        yaml.default_flow_style = False
        yaml_file = self._project_dir / f"{profile.profile_id}.agent.yaml"

        # Convert profile to dict, excluding unset fields to keep YAML clean
        profile_dict = profile.model_dump(mode='json', by_alias=True, exclude_unset=True)

        with yaml_file.open("w") as f:
            yaml.dump(profile_dict, f)

        # Update in-memory profiles
        self._profiles[profile.profile_id] = profile

        # Invalidate hierarchy index
        self._hierarchy_index = None

    def delete(self, profile_id: str) -> bool:
        """Delete profile from project directory.

        Only deletes from project_dir (cannot delete shipped profiles).
        If profile exists in shipped, reverts to shipped version.

        Args:
            profile_id: Profile ID to delete

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: If project_dir is not configured
        """
        if self._project_dir is None:
            raise ValueError("Cannot delete profile: project_dir not configured")

        yaml_file = self._project_dir / f"{profile_id}.agent.yaml"

        if not yaml_file.exists():
            return False

        # Remove file
        yaml_file.unlink()

        # Check if profile exists in shipped
        shipped_profile = None
        if self._shipped_dir.exists():
            shipped_yaml = self._shipped_dir / f"{profile_id}.agent.yaml"
            if shipped_yaml.exists():
                try:
                    yaml = YAML(typ="safe")
                    data = yaml.load(shipped_yaml)
                    shipped_profile = AgentProfile.model_validate(data)
                except (YAMLError, ValidationError, TypeError):
                    pass  # silently skip invalid shipped YAML during revert

        if shipped_profile:
            # Revert to shipped version
            self._profiles[profile_id] = shipped_profile
        else:
            # Remove from profiles (was project-only)
            self._profiles.pop(profile_id, None)

        # Invalidate hierarchy index
        self._hierarchy_index = None

        return True
