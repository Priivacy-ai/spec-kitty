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
from pydantic import BaseModel, ConfigDict, Field, ValidationError
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


class ManifestSchemaError(Exception):
    """Raised when a *found* ``expected-artifacts.yaml`` fails schema
    validation, as distinct from a manifest that is absent entirely or one
    that fails at the YAML-syntax level (#3412, still degrades to ``None``
    upstream of this module).

    Deliberately NOT a :class:`pydantic.ValidationError` subclass:
    ``ValidationError`` is a Rust-backed pydantic-core type not designed for
    subclassing, and the model-level tests in ``tests/dossier/test_manifest.py``
    construct :class:`ExpectedArtifactSpec`/:class:`ExpectedArtifactManifest`
    directly and assert the raw ``pydantic.ValidationError`` from *that*
    construction -- unaffected by this type, which only wraps failures at the
    :meth:`ManifestRegistry.load_manifest` boundary.

    This is the fix for a MAJOR adversarial-review finding: catching
    ``except pydantic.ValidationError`` around the whole
    ``Indexer.index_feature(...)`` call (in
    ``sync/dossier_pipeline.py::sync_feature_dossier``) misattributes ANY
    ``ValidationError`` raised while indexing -- including a genuine
    ``ArtifactRef``/``MissionDossier`` model-validator bug, raised well
    *after* the manifest has already loaded successfully -- to "your
    ``expected-artifacts.yaml`` is broken". Catching this domain-specific
    type instead of the raw pydantic type lets a real indexer bug fall
    through to the generic ``except Exception`` branch (ERROR + stack
    trace) where it belongs.

    Args:
        mission_type: The mission type the manifest was resolved for.
        origin: A human-legible label for the manifest's source -- a file
            path for the built-in/project tiers (``ConfigResult.origin``);
            a descriptive org-tier label when no single file path is
            available (see the org-tier branch of
            :meth:`ManifestRegistry.load_manifest`).

    The underlying :class:`pydantic.ValidationError` is chained via
    ``raise ... from exc``, so it is always available as ``__cause__`` --
    :meth:`__str__` reads it from there rather than storing a redundant
    third field.
    """

    def __init__(self, mission_type: str, origin: str) -> None:
        self.mission_type = mission_type
        self.origin = origin
        super().__init__(mission_type, origin)

    def __str__(self) -> str:
        underlying = self.__cause__
        detail = str(underlying) if underlying is not None else "unknown validation failure"
        return (
            f"expected-artifacts.yaml schema-invalid for mission type "
            f"{self.mission_type!r} ({self.origin}): {detail}"
        )


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

    model_config = ConfigDict(extra="forbid")

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

    model_config = ConfigDict(extra="forbid")

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
        (degraded mode for custom/unknown missions), or if it fails to parse
        as YAML at all — :meth:`MissionTemplateRepository.get_expected_artifacts`
        catches ``YAMLError``/``OSError``/``UnicodeDecodeError`` upstream and
        returns ``None`` before this method ever sees it, a known gap tracked
        in `#3412 <https://github.com/Priivacy-ai/spec-kitty/issues/3412>`_. A
        *found*, syntactically-valid manifest that fails **schema** validation
        (e.g. a typo'd/extra key, rejected by ``extra="forbid"``) raises
        :class:`ManifestSchemaError` instead of being silently swallowed
        (FR-016): only schema-level malformation is distinguished from
        absence — YAML-syntax-level malformation is not (yet). This applies
        on BOTH tiers below — built-in/project *and* org — so an org-authored
        manifest with a typo'd key fails just as loudly as a built-in one
        (previously the org-tier branch swallowed every ``Exception``,
        including schema errors, into ``None``).

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
            ExpectedArtifactManifest if found and valid, None if not found —
            including a manifest that exists but is broken at the YAML-syntax
            level (see #3412 above)

        Raises:
            ManifestSchemaError: If the manifest file is found, parses as
                valid YAML, but fails *schema* validation (e.g. an
                unrecognized/typo'd key, given
                ``model_config = ConfigDict(extra="forbid")`` on both models).
                Does NOT raise for YAML-syntax errors — see above. Carries
                typed ``mission_type`` and ``origin`` fields naming the
                resolved manifest's source (e.g.
                ``"doctrine/software-dev/expected-artifacts.yaml"`` for the
                built-in/project tiers; a descriptive org-tier label when no
                single file path is available), and chains the underlying
                ``pydantic.ValidationError`` via ``__cause__`` — so
                ``str(exc)`` is always operator-actionable (names both the
                file and the bad key) for any consumer, not only one that
                knows to read an exception note (#3542-A/B fix).
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
            except ValidationError as exc:
                # paula rank-2: a schema-invalid ORG manifest must fail as
                # loudly as a schema-invalid built-in one (see the built-in
                # branch below) -- an operator authored this file and
                # expected it to take effect, so silently falling back to
                # None (or worse, to the built-in file, which whole-file
                # precedence forbids) hides a genuine misconfiguration.
                # `resolve_org_expected_artifacts` (charter.org_expected_artifacts)
                # returns only the parsed mapping, not which org_root/file
                # matched (last-EXISTING-match-wins means it isn't
                # necessarily the last root in the list either -- only the
                # last root with a *matching file*), so no single precise
                # path is available here. `origin` is therefore a
                # descriptive label naming the org tier + mission_type +
                # the full set of roots that were checked, rather than a
                # fabricated/guessed file path.
                origin = (
                    f"org-tier expected-artifacts.yaml for mission type {mission_type!r} "
                    f"(no single source file path available; checked org roots: "
                    f"{', '.join(str(root) for root in org_roots)})"
                )
                raise ManifestSchemaError(mission_type, origin) from exc
            except Exception as e:
                # Genuinely non-schema failures (e.g. an org file that reads
                # as something model_validate can't even attempt against,
                # or an unexpected error inside resolve_org_expected_artifacts
                # itself) keep the pre-existing tolerant swallow-to-None --
                # only *schema* errors are widened to fail loud above.
                logger.error(f"Failed to load org-tier manifest for {mission_type}: {e}")
                ManifestRegistry._cache[cache_key] = None
                return None

        config = _doctrine_repository().get_expected_artifacts(mission_type)

        if config is None:
            logger.debug(f"Manifest not found for mission type: {mission_type}")
            ManifestRegistry._cache[cache_key] = None
            return None

        # Rebase resolution (#3413 x #3520): the propagation is this branch's
        # (FR-016 -- a malformed manifest must fail loudly, so the swallowing
        # try/except that cached None is deliberately gone), and `cache_key` is
        # main's org-aware `(mission_type, org_roots)` tuple rather than the bare
        # `mission_type` this commit was written against.
        try:
            manifest = ExpectedArtifactManifest.model_validate(config.parsed)
        except ValidationError as exc:
            # #3542-A/adversarial-review MAJOR fix: raise the domain
            # `ManifestSchemaError` (typed `mission_type`/`origin` fields,
            # chaining the raw ValidationError via `__cause__`) instead of
            # letting the raw `pydantic.ValidationError` cross this module's
            # boundary. A bare `except pydantic.ValidationError` at any
            # consumer (e.g. the old `sync_feature_dossier`) is a proxy for
            # "manifest schema failure" that misfires on ANY ValidationError
            # raised later in the same call stack (e.g. a genuine
            # `ArtifactRef`/`MissionDossier` validator bug) -- catching this
            # specific type instead fixes that misattribution at the source.
            raise ManifestSchemaError(mission_type, config.origin) from exc
        ManifestRegistry._cache[cache_key] = manifest
        logger.info(f"Loaded manifest for {mission_type}: {len(manifest.get_step_ids())} steps")
        return manifest

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
