"""Expected artifact manifest schema (FR-009 / C-001).

Relocated from ``specify_cli.dossier.manifest`` (mission
rc3-charter-gate-predicate-inversion-01M0GGT1, WP04 / #3599) so the
artifact-filename resolution seam
(:func:`specify_cli.runtime.resolver.resolve_configured_artifact_name`) can
consume these pure pydantic data models directly from the doctrine layer.
``charter`` must not import ``specify_cli`` (C-001); these models have no
``specify_cli`` dependency of their own, so doctrine — not a ``specify_cli``
subpackage — is their correct home. ``specify_cli.dossier.manifest`` keeps a
lazy PEP 562 ``__getattr__`` re-export so existing importers
(``from specify_cli.dossier.manifest import ExpectedArtifactManifest``) are
unaffected at runtime — see that module and
``tests/doctrine/missions/test_expected_artifact_manifest_relocation.py``.

Key concepts:
- ArtifactClassEnum: 6 artifact classes (input, workflow, output, evidence, policy, runtime)
- ExpectedArtifactSpec: Single expected artifact definition
- ExpectedArtifactManifest: Complete manifest for a mission (required_always, required_by_step, optional_always)

See: kitty-specs/042-local-mission-dossier-authority-parity-export/data-model.md
"""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ArtifactClassEnum",
    "ExpectedArtifactManifest",
    "ExpectedArtifactSpec",
]


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

    def get_step_ids(self) -> list[str]:
        """Return all step IDs in required_by_step.

        Returns:
            List of step IDs (keys of required_by_step dict)
        """
        return list(self.required_by_step.keys())
