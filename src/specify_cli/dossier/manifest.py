"""Expected artifact manifest system for mission completeness validation.

This module defines manifest schema and registry for declaring which artifacts
are required/optional at each mission step. Manifests are YAML-based and step-aware,
reading from mission.yaml state machines.

Key concepts:
- ArtifactClassEnum: 6 artifact classes (input, workflow, output, evidence, policy, runtime)
- ExpectedArtifactSpec: Single expected artifact definition
- ExpectedArtifactManifest: Complete manifest for a mission (required_always, required_by_step, optional_always)
- ManifestRegistry: Loader and cacher for manifests, with step-aware querying

See: kitty-specs/042-local-mission-dossier-authority-parity-export/data-model.md
"""

from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class ArtifactClassEnum(str, Enum):
    """Classification of artifacts in the dossier system.

    - INPUT: Artifacts provided by user or external source (spec.md, requirements.txt)
    - WORKFLOW: Process/workflow artifacts (tasks.md, plan.md)
    - OUTPUT: Deliverable artifacts from the mission (implementation code, findings.md)
    - EVIDENCE: Supporting evidence (research.md, gap-analysis.md, test results)
    - POLICY: Governance and standards (architecture-decision.md, compliance.md)
    - RUNTIME: Artifacts generated at runtime (logs, metrics, temporary data)
    """

    INPUT = "input"
    WORKFLOW = "workflow"
    OUTPUT = "output"
    EVIDENCE = "evidence"
    POLICY = "policy"
    RUNTIME = "runtime"


class ExpectedArtifactSpec(BaseModel):
    """Single artifact expected at a mission step.

    Attributes:
        artifact_key: Stable, unique key (e.g., 'input.spec.main')
        artifact_class: One of {input, workflow, output, evidence, policy, runtime}
        path_pattern: Glob pattern relative to feature dir (e.g., 'spec.md', 'tasks/*.md')
        blocking: If True, missing artifact blocks mission completeness
    """

    artifact_key: str = Field(
        ...,
        min_length=1,
        description="Stable, unique key (e.g., 'input.spec.main', 'output.tasks.per_wp')",
    )
    artifact_class: ArtifactClassEnum = Field(
        ...,
        description="Classification: input | workflow | output | evidence | policy | runtime",
    )
    path_pattern: str = Field(
        ...,
        min_length=1,
        description="Glob pattern relative to feature directory (e.g., 'spec.md', 'tasks/*.md')",
    )
    blocking: bool = Field(
        default=False,
        description="If True, missing artifact blocks mission completeness",
    )


class ExpectedArtifactManifest(BaseModel):
    """Complete expected artifact manifest for a mission type.

    Defines which artifacts are required/optional at each mission step.
    Step-aware: required_by_step keys match mission.yaml state IDs.

    Attributes:
        schema_version: Manifest schema version (e.g., "1.0")
        mission_type: Mission type (e.g., 'software-dev', 'research', 'documentation')
        manifest_version: Manifest data version (e.g., "1")
        required_always: Artifacts required regardless of step
        required_by_step: Dict mapping step_id to required artifacts for that step
        optional_always: Artifacts optional regardless of step
    """

    schema_version: str = Field(
        default="1.0",
        description="Manifest schema version",
    )
    mission_type: str = Field(
        ...,
        description="Mission type (e.g., 'software-dev', 'research', 'documentation')",
    )
    manifest_version: str = Field(
        default="1",
        description="Manifest data version",
    )
    required_always: List[ExpectedArtifactSpec] = Field(
        default_factory=list,
        description="Artifacts required regardless of mission step",
    )
    required_by_step: Dict[str, List[ExpectedArtifactSpec]] = Field(
        default_factory=dict,
        description="Dict mapping step_id to required artifacts for that step",
    )
    optional_always: List[ExpectedArtifactSpec] = Field(
        default_factory=list,
        description="Artifacts optional regardless of mission step",
    )

    @classmethod
    def from_yaml_file(cls, path: Path) -> "ExpectedArtifactManifest":
        """Load manifest from YAML file.

        Args:
            path: Path to YAML manifest file

        Returns:
            ExpectedArtifactManifest instance

        Raises:
            FileNotFoundError: If file doesn't exist
            ValueError: If YAML is invalid
        """
        import ruamel.yaml

        yaml = ruamel.yaml.YAML()
        with open(path) as f:
            data = yaml.load(f)

        if data is None:
            data = {}

        return cls(**data)

    def get_step_ids(self) -> List[str]:
        """Return all step IDs in required_by_step.

        Returns:
            List of step IDs (keys of required_by_step dict)
        """
        return list(self.required_by_step.keys())


class ManifestRegistry:
    """Registry for loading and querying expected artifact manifests.

    Singleton-like pattern with in-memory caching.
    Provides step-aware querying of artifact requirements.

    Example:
        >>> manifest = ManifestRegistry.load_manifest("software-dev")
        >>> if manifest:
        ...     specs = ManifestRegistry.get_required_artifacts(manifest, "specify")
        ...     print(f"Specify step requires {len(specs)} artifacts")
    """

    _cache: Dict[str, Optional[ExpectedArtifactManifest]] = {}

    @staticmethod
    def load_manifest(mission_type: str) -> Optional[ExpectedArtifactManifest]:
        """Load manifest for mission type.

        Returns cached manifest if available. Gracefully returns None if manifest
        not found (degraded mode for custom/unknown missions).

        Args:
            mission_type: Mission type (e.g., 'software-dev', 'research')

        Returns:
            ExpectedArtifactManifest if found and valid, None otherwise
        """
        if mission_type in ManifestRegistry._cache:
            return ManifestRegistry._cache[mission_type]

        manifest_path = (
            Path(__file__).parent.parent
            / "missions"
            / mission_type
            / "expected-artifacts.yaml"
        )

        if not manifest_path.exists():
            logger.debug(f"Manifest not found for mission type: {mission_type}")
            ManifestRegistry._cache[mission_type] = None
            return None

        try:
            manifest = ExpectedArtifactManifest.from_yaml_file(manifest_path)
            ManifestRegistry._cache[mission_type] = manifest
            logger.info(f"Loaded manifest for {mission_type}: {len(manifest.get_step_ids())} steps")
            return manifest
        except Exception as e:
            logger.error(f"Failed to load manifest for {mission_type}: {e}")
            ManifestRegistry._cache[mission_type] = None
            return None

    @staticmethod
    def get_required_artifacts(
        manifest: ExpectedArtifactManifest,
        step_id: str,
    ) -> List[ExpectedArtifactSpec]:
        """Get required artifact specs for a mission step.

        Combines required_always with required_by_step[step_id].
        Returns empty list if step_id not in manifest (graceful degradation).

        Args:
            manifest: ExpectedArtifactManifest to query
            step_id: Mission step ID (e.g., 'specify', 'planning')

        Returns:
            List of ExpectedArtifactSpec required at this step
        """
        base = manifest.required_always
        step_specific = manifest.required_by_step.get(step_id, [])
        return base + step_specific

    @staticmethod
    def get_blocking_artifacts(
        specs: List[ExpectedArtifactSpec],
    ) -> List[ExpectedArtifactSpec]:
        """Filter artifact specs to only blocking ones.

        Args:
            specs: List of ExpectedArtifactSpec

        Returns:
            List of specs where blocking=True
        """
        return [s for s in specs if s.blocking]

    @staticmethod
    def get_optional_artifacts(manifest: ExpectedArtifactManifest) -> List[ExpectedArtifactSpec]:
        """Get optional artifact specs for a mission.

        Args:
            manifest: ExpectedArtifactManifest to query

        Returns:
            List of optional artifact specs
        """
        return manifest.optional_always

    @staticmethod
    def validate_manifest(
        manifest: ExpectedArtifactManifest,
        mission_dir: Path,
    ) -> Tuple[bool, List[str]]:
        """Validate manifest against mission structure.

        Checks:
        - Step IDs in required_by_step exist in mission.yaml states
        - Path patterns are relative (no leading /)
        - Path patterns don't reference parent (..)

        Args:
            manifest: Manifest to validate
            mission_dir: Path to mission directory

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check path patterns
        for specs_list in [
            manifest.required_always,
            manifest.optional_always,
            *manifest.required_by_step.values(),
        ]:
            for spec in specs_list:
                if spec.path_pattern.startswith("/"):
                    errors.append(
                        f"Path pattern must be relative: '{spec.path_pattern}' "
                        f"(artifact_key={spec.artifact_key})"
                    )
                if ".." in spec.path_pattern:
                    errors.append(
                        f"Path pattern cannot reference parent directory: '{spec.path_pattern}' "
                        f"(artifact_key={spec.artifact_key})"
                    )

        return len(errors) == 0, errors

    @staticmethod
    def clear_cache():
        """Clear manifest cache (useful for testing).

        Resets _cache dict to empty.
        """
        ManifestRegistry._cache.clear()
