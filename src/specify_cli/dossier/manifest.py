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

from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING
from pydantic import BaseModel, Field
import logging

if TYPE_CHECKING:
    from charter.missions import MissionTemplateRepository

logger = logging.getLogger(__name__)


def _doctrine_repository() -> "MissionTemplateRepository":
    """Return the doctrine mission repository bound to the bundled doctrine tree.

    Lazy import keeps the ``specify_cli.dossier`` package free of an
    import-time dependency on the ``doctrine`` package. The repository is the
    single authority for reading ``<type>/expected-artifacts.yaml`` from the
    canonical doctrine mission tree (WP10 / IC-07).
    """
    from charter.missions import MissionTemplateRepository  # noqa: PLC0415

    return MissionTemplateRepository.default()


def _resolve_existing_org_roots(repo_root: Path) -> list[Path]:
    """Return configured org doctrine roots that exist on disk for *repo_root*.

    Lazy import mirrors :func:`_doctrine_repository` — keeps
    ``specify_cli.dossier`` free of an import-time dependency on
    ``charter``, and reaches ``doctrine`` only through the ``charter.drg``
    proxy (runtime must reach doctrine through charter — never directly;
    see ``tests/architectural/test_runtime_charter_doctrine_boundary.py``).
    Delegates to the shared
    :func:`doctrine.drg.org_pack_config.resolve_existing_org_roots` primitive
    (#3525 Fold A) rather than re-implementing the filter comprehension —
    the same primitive every other "does this org root exist" consumer now
    routes onto (e.g.
    ``charter.doctrine_service_builder._self_resolve_existing_org_roots``): a
    stale/never-fetched ``local_path`` config entry degrades to "no org
    contribution" for this call rather than raising.
    """
    from charter.drg import resolve_existing_org_roots  # noqa: PLC0415

    return resolve_existing_org_roots(repo_root)


class ArtifactClassEnum(StrEnum):
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
    required_always: list[ExpectedArtifactSpec] = Field(
        default_factory=list,
        description="Artifacts required regardless of mission step",
    )
    required_by_step: dict[str, list[ExpectedArtifactSpec]] = Field(
        default_factory=dict,
        description="Dict mapping step_id to required artifacts for that step",
    )
    optional_always: list[ExpectedArtifactSpec] = Field(
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

    def get_step_ids(self) -> list[str]:
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

    #: Cache key is ``(mission_type, org_roots_fingerprint)``, NOT bare
    #: ``mission_type`` (FR-008 / WP05 cache-key fix). ``org_roots_fingerprint``
    #: is a **declaration-ordered** tuple of existing org-root path strings —
    #: NOT sorted. Per NFR-003 / C-4 ("last-EXISTING-match wins"), two
    #: `repo_root`s that declare the SAME set of org roots in a DIFFERENT
    #: order can resolve to different manifests; sorting the key would
    #: collide those two cases onto one cache entry and silently hand the
    #: second `repo_root` the first's (order-wrong) manifest. The tuple is
    #: empty when ``repo_root`` is ``None`` (today's call shape, unchanged)
    #: or when no configured org pack resolves to an existing path for that
    #: ``repo_root``. Without order-preservation, the cache — process-global
    #: and previously keyed on ``mission_type`` alone — would let the FIRST
    #: resolution of a given mission type in a long-lived process (a daemon,
    #: or a test session touching two projects with different org overrides)
    #: permanently shadow every later ``repo_root``'s result for that same
    #: mission type: project B's request would silently get project A's org
    #: override (or lack thereof). See
    #: ``tests/dossier/test_manifest.py::TestManifestRegistryOrgTier::test_cache_key_does_not_shadow_across_different_repo_roots``
    #: and ``::test_cache_key_preserves_declaration_order_for_same_root_set``.
    _cache: dict[tuple[str, tuple[str, ...]], ExpectedArtifactManifest | None] = {}

    @staticmethod
    def load_manifest(
        mission_type: str, repo_root: Path | None = None
    ) -> ExpectedArtifactManifest | None:
        """Load manifest for mission type from the canonical doctrine tree.

        Reads ``<type>/expected-artifacts.yaml`` from the doctrine mission tree
        via :meth:`MissionTemplateRepository.get_expected_artifacts` and adapts
        the returned :class:`ConfigResult` into an
        :class:`ExpectedArtifactManifest` (WP10 / IC-07). The adapted model —
        not the raw ``ConfigResult`` — is cached, preserving the registry cache
        semantics. Gracefully returns ``None`` if the manifest is not found
        (degraded mode for custom/unknown missions).

        FR-008 (WP05): when *repo_root* is given and resolves to 1+ existing
        configured org roots, an org-pack
        ``<org_root>/<mission_type>/expected-artifacts.yaml`` (see
        :func:`charter.org_expected_artifacts.resolve_org_expected_artifacts`,
        contract C-4) takes precedence over the built-in file, whole-file —
        never field-merged with it. *repo_root* is optional and defaults to
        ``None`` (today's exact behavior: no org lookup, built-in tree only)
        so a caller without a ``repo_root`` in scope is unaffected by
        this signature change. (The former sole production caller lived in
        the deleted sync namespace module, issue #5.)

        Args:
            mission_type: Mission type (e.g., 'software-dev', 'research')
            repo_root: Project root to resolve org-pack overrides for, or
                ``None`` (default) for built-in-tree-only resolution.

        Returns:
            ExpectedArtifactManifest if found and valid, None otherwise
        """
        org_roots = _resolve_existing_org_roots(repo_root) if repo_root is not None else []
        cache_key = (mission_type, tuple(str(root) for root in org_roots))
        if cache_key in ManifestRegistry._cache:
            return ManifestRegistry._cache[cache_key]

        org_parsed: object | None = None
        if org_roots:
            from charter.org_expected_artifacts import resolve_org_expected_artifacts  # noqa: PLC0415

            org_parsed = resolve_org_expected_artifacts(org_roots, mission_type)

        if org_parsed is not None:
            try:
                manifest = ExpectedArtifactManifest.model_validate(org_parsed)
                ManifestRegistry._cache[cache_key] = manifest
                logger.info(
                    f"Loaded org-tier manifest for {mission_type}: {len(manifest.get_step_ids())} steps"
                )
                return manifest
            except Exception as e:
                logger.error(f"Failed to load org-tier manifest for {mission_type}: {e}")
                ManifestRegistry._cache[cache_key] = None
                return None

        config = _doctrine_repository().get_expected_artifacts(mission_type)

        if config is None:
            logger.debug(f"Manifest not found for mission type: {mission_type}")
            ManifestRegistry._cache[cache_key] = None
            return None

        try:
            manifest = ExpectedArtifactManifest.model_validate(config.parsed)
            ManifestRegistry._cache[cache_key] = manifest
            logger.info(f"Loaded manifest for {mission_type}: {len(manifest.get_step_ids())} steps")
            return manifest
        except Exception as e:
            logger.error(f"Failed to load manifest for {mission_type}: {e}")
            ManifestRegistry._cache[cache_key] = None
            return None

    @staticmethod
    def get_required_artifacts(
        manifest: ExpectedArtifactManifest,
        step_id: str,
    ) -> list[ExpectedArtifactSpec]:
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
        specs: list[ExpectedArtifactSpec],
    ) -> list[ExpectedArtifactSpec]:
        """Filter artifact specs to only blocking ones.

        Args:
            specs: List of ExpectedArtifactSpec

        Returns:
            List of specs where blocking=True
        """
        return [s for s in specs if s.blocking]

    @staticmethod
    def get_optional_artifacts(manifest: ExpectedArtifactManifest) -> list[ExpectedArtifactSpec]:
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
        mission_dir: Path,  # noqa: ARG004
    ) -> tuple[bool, list[str]]:
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
                        f"Path pattern must be relative: '{spec.path_pattern}' (artifact_key={spec.artifact_key})"
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
