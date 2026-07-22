"""Pydantic schemas for charter config extraction.

Defines the output schema for:
- governance.yaml (testing, quality, performance, branch strategy)
- directives.yaml (numbered rules and enforcement)
- metadata.yaml (extraction provenance and statistics)
"""

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from ruamel.yaml import YAML

from charter.activations import ActivationEntry

__all__ = [
    "BranchStrategyConfig",
    "CharterCatalog",
    "CharterCatalogReference",
    "CharterTestingConfig",
    "CharterYaml",
    "CharterYamlMetadata",
    "CommitConfig",
    "Directive",
    "DirectivesConfig",
    "DoctrineSelectionConfig",
    "ExtractionMetadata",
    "GovernanceConfig",
    "PerformanceConfig",
    "QualityConfig",
    "SectionsParsed",
    "emit_yaml",
]


# Header comment for all emitted YAML files
YAML_HEADER = (
    "# Auto-generated from charter.md — do not edit directly.\n"
    "# Run 'spec-kitty charter sync' to regenerate.\n\n"
)


class CharterTestingConfig(BaseModel):
    """Testing requirements extracted from charter."""

    min_coverage: int = 0
    tdd_required: bool = False
    framework: str = ""
    type_checking: str = ""


class QualityConfig(BaseModel):
    """Code quality requirements."""

    linting: str = ""
    pr_approvals: int = 1
    pre_commit_hooks: bool = False


class CommitConfig(BaseModel):
    """Commit message conventions."""

    convention: str | None = None


class PerformanceConfig(BaseModel):
    """Performance and scale requirements."""

    cli_timeout_seconds: float = 2.0
    dashboard_max_wps: int = 100


class BranchStrategyConfig(BaseModel):
    """Git branch strategy and rules."""

    main_branch: str = "main"
    dev_branch: str | None = None
    rules: list[str] = Field(default_factory=list)


class DoctrineSelectionConfig(BaseModel):
    """Charter-level selection of active doctrine elements.

    Field naming MUST exactly mirror the corresponding ``DoctrineService``
    property name (e.g. ``selected_styleguides`` mirrors
    ``DoctrineService.styleguides``). This parity rule is pinned by
    ``tests/architectural/test_artifact_selection_completeness.py`` —
    adding a new ``@property`` to ``DoctrineService`` without the matching
    ``selected_<kind>`` field here is a CI failure.
    """

    selected_paradigms: list[str] = Field(default_factory=list)
    selected_directives: list[str] = Field(default_factory=list)
    selected_tactics: list[str] = Field(default_factory=list)
    selected_styleguides: list[str] = Field(default_factory=list)
    """Charter-active styleguide IDs (mirrors ``DoctrineService.styleguides``).
    Default empty preserves backwards compatibility (NFR-005)."""
    selected_toolguides: list[str] = Field(default_factory=list)
    """Charter-active toolguide IDs (mirrors ``DoctrineService.toolguides``).
    Default empty preserves backwards compatibility (NFR-005)."""
    selected_procedures: list[str] = Field(default_factory=list)
    """Charter-active procedure IDs (mirrors ``DoctrineService.procedures``).
    Default empty preserves backwards compatibility (NFR-005)."""
    selected_agent_profiles: list[str] = Field(default_factory=list)
    """Charter-active agent-profile IDs (mirrors
    ``DoctrineService.agent_profiles``). Default empty preserves backwards
    compatibility (NFR-005)."""
    selected_mission_step_contracts: list[str] = Field(default_factory=list)
    """Charter-active mission-step-contract IDs (mirrors
    ``DoctrineService.mission_step_contracts``). Default empty preserves
    backwards compatibility (NFR-005)."""
    available_tools: list[str] = Field(default_factory=list)
    template_set: str | None = None
    authority_paths: list[str] = Field(default_factory=list)
    """Repository-relative directories surfaced as authority pointers
    (e.g. ``docs/context/``). Populated by WP02 (charter sync) from the
    charter's fenced YAML block; consumed by WP04 renderer when building the
    ``Project authority paths:`` section. Default empty preserves backwards
    compatibility (NFR-005): existing YAML without this key parses unchanged."""
    governance_references: list[str] = Field(default_factory=list)
    """Repository-relative supporting governance documents that should be
    included in charter context as required reading (e.g.
    ``spec/constitution.md``). These are supporting references only:
    ``.kittify/charter/charter.md`` remains the runtime governance center."""


class GovernanceConfig(BaseModel):
    """Top-level governance configuration."""

    testing: CharterTestingConfig = Field(default_factory=CharterTestingConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    commits: CommitConfig = Field(default_factory=CommitConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    branch_strategy: BranchStrategyConfig = Field(default_factory=BranchStrategyConfig)
    doctrine: DoctrineSelectionConfig = Field(default_factory=DoctrineSelectionConfig)
    activations: list[ActivationEntry] = Field(default_factory=list)
    """Charter-level activation registry (FR-006 / WP01 T008). The registry
    lives on :class:`GovernanceConfig` (the top-level governance namespace),
    NOT on :class:`DoctrineSelectionConfig`, because activations pair
    artifacts with runtime contexts rather than selecting global defaults.
    Default empty preserves backwards compatibility (NFR-005): existing
    ``governance.yaml`` files without this key parse unchanged, and the
    emitter omits the block via :data:`_OPTIONAL_EMPTY_OMIT_KEYS`."""
    enforcement: dict[str, str] = Field(default_factory=dict)


class Directive(BaseModel):
    """A single numbered directive from the charter.

    Cross-artifact applicability is now expressed via graph edges in
    ``src/doctrine/graph.yaml`` rather than an inline ``applies_to`` field
    (Phase 1 excision — mission
    ``excise-doctrine-curation-and-inline-references-01KP54J6`` WP02).
    """

    id: str
    title: str
    description: str = ""
    severity: str = "warn"
    references: list[str] = Field(default_factory=list)
    """Catalog IDs (e.g. ``["DIRECTIVE_032"]`` or tactic-id slugs) cross-linked
    from the body of a charter-extracted directive. Populated by WP02 (charter
    sync) from cited catalog IDs detected in the directive body; consumed by
    WP03/WP04 resolver/renderer via ``DoctrineService``. Default empty preserves
    backwards compatibility (NFR-005): existing YAML without this key parses
    unchanged."""


class DirectivesConfig(BaseModel):
    """Collection of directives extracted from charter."""

    directives: list[Directive] = Field(default_factory=list)


class SectionsParsed(BaseModel):
    """Statistics about parsed sections."""

    structured: int = 0
    ai_assisted: int = 0
    skipped: int = 0


class ExtractionMetadata(BaseModel):
    """Metadata tracking extraction provenance."""

    schema_version: str = "1.0.0"
    extracted_at: str = ""  # ISO 8601 timestamp
    charter_hash: str = ""  # "sha256:..."
    source_path: str = ".kittify/charter/charter.md"
    extraction_mode: str = "deterministic"  # "deterministic" | "hybrid" | "ai_only"
    sections_parsed: SectionsParsed = Field(default_factory=SectionsParsed)
    bundle_schema_version: int | None = None


# ---------------------------------------------------------------------------
# consolidate-charter-bundle (WP01 / T001): structured charter.yaml (v2.0.0)
# ---------------------------------------------------------------------------
#
# Contract: kitty-specs/consolidate-charter-bundle-01KXSYB9/contracts/
# charter-yaml-schema.md. Data model: ../data-model.md (Landmine 1/2/3,
# INV-1..9). ``CharterYaml`` nests the EXISTING ``GovernanceConfig`` /
# ``DirectivesConfig`` above verbatim (validation inherited, not re-authored)
# — it does not replace ``ExtractionMetadata``/the legacy governance.yaml /
# directives.yaml / metadata.yaml emitters, which remain in place until the
# WPs that retire them land.


class CharterCatalogReference(BaseModel):
    """One reference item inside the charter.yaml ``catalog`` projection.

    Mirrors the retired ``references.yaml`` reference-item shape (charter
    contract G2): ``catalog`` is byte-equivalent in content to that file's
    body, so parity/resolving consumers (``consistency_check.py``) see
    identical data.
    """

    id: str
    kind: str
    title: str
    summary: str
    source_path: str
    local_path: str


class CharterCatalog(BaseModel):
    """The DERIVED-but-committed ``catalog`` projection (charter contract G2).

    Mirrors the retired ``references.yaml`` body verbatim: ``mission``,
    ``template_set``, ``languages``, ``references``. Kept honest by the
    catalog<->activation parity check (``consistency_check.py``) plus
    freshness (data-model.md Landmine 2 extension).
    """

    mission: str
    template_set: str
    languages: list[str] = Field(default_factory=list)
    references: list[CharterCatalogReference] = Field(default_factory=list)


class CharterYamlMetadata(BaseModel):
    """``charter.yaml``'s ``metadata`` block (charter contract G4).

    Deliberately narrower than :class:`ExtractionMetadata`: Landmine 2
    (data-model.md) retires the self-referential ``charter_hash`` (a hash of
    ``charter.yaml`` cannot live *inside* ``charter.yaml`` — chicken-egg)
    along with ``extraction_mode``/``sections_parsed``, which have no
    meaning once ``governance``/``directives``/activation are hand-authored
    rather than extracted. ``bundle_schema_version`` is KEPT — read by
    ``versioning.py``.
    """

    model_config = ConfigDict(extra="forbid")

    generated_at: str = ""
    bundle_schema_version: int = 2


class CharterYaml(BaseModel):
    """The structured shape of the git-tracked, authorable ``charter.yaml``.

    Contract: ``kitty-specs/consolidate-charter-bundle-01KXSYB9/contracts/
    charter-yaml-schema.md``.

    ⚠ Activation is FLAT AT THE ROOT (paula BLOCKER-1) — the ten
    ``activated_*`` / ``mission_type_activations`` fields below are NOT
    nested under an ``activation:`` key, matching
    ``src/charter/packs/default.yaml:5-38``, so
    ``pack_context._read_activated_*`` / ``_read_list_key`` and
    ``activation_engine.commit_plan`` read/write them unchanged.
    ``model_config`` forbids extra fields, which doubles as the structural
    guard against a stray nested ``activation:`` mapping creeping back in
    (a nested mapping is not a declared field on this model, so
    ``extra="forbid"`` rejects it).

    Each ``activated_*`` field is three-state (charter contract G3):
    ``None`` == absent key == default-pack fallback/seed
    (``load_default_pack_activation_ids``); ``[]`` == explicit fail-closed
    empty; a non-empty list == the activated set.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = Field(default="2.0.0", pattern=r"^\d+\.\d+\.\d+$")
    governance: GovernanceConfig = Field(default_factory=GovernanceConfig)
    directives: DirectivesConfig = Field(default_factory=DirectivesConfig)
    catalog: CharterCatalog

    activated_kinds: list[str] | None = None
    mission_type_activations: list[str] | None = None
    activated_directives: list[str] | None = None
    activated_tactics: list[str] | None = None
    activated_styleguides: list[str] | None = None
    activated_toolguides: list[str] | None = None
    activated_paradigms: list[str] | None = None
    activated_procedures: list[str] | None = None
    activated_agent_profiles: list[str] | None = None
    activated_mission_step_contracts: list[str] | None = None

    overrides: dict[str, Any] = Field(default_factory=dict)
    metadata: CharterYamlMetadata = Field(default_factory=CharterYamlMetadata)


# WP02: keys that are NEW additions in this mission and MUST be omitted
# from emitted YAML when their value is empty, so existing serialized
# fixtures and user charters stay byte-identical pre-/post-mission
# (NFR-005). Anchored centrally so future "additive optional" fields can
# join the same allow-list without touching the writer logic.
_OPTIONAL_EMPTY_OMIT_KEYS: frozenset[str] = frozenset({
    "references",                        # Directive.references (cross-link list)
    "authority_paths",                   # DoctrineSelectionConfig.authority_paths
    "governance_references",             # DoctrineSelectionConfig.governance_references
    # WP01 (charter-mediated-doctrine-selection): additive `selected_<kind>`
    # parity fields. Keep empty values out of emitted YAML so existing
    # serialized fixtures and user charters stay byte-identical pre-/post-
    # mission (NFR-005).
    "selected_styleguides",
    "selected_toolguides",
    "selected_procedures",
    "selected_agent_profiles",
    "selected_mission_step_contracts",
    # WP01 T008 (charter-mediated-doctrine-selection): activation registry
    # block on GovernanceConfig — empty list ⇒ omit from emitted YAML so
    # the default-config fixture remains byte-stable (NFR-005).
    "activations",
})


def _prune_optional_empties(node: Any) -> Any:
    """Recursively drop optional list fields whose value is empty.

    Walks dicts/lists and removes entries whose key is in
    :data:`_OPTIONAL_EMPTY_OMIT_KEYS` AND whose value is an empty list.
    Leaves all other keys untouched so existing required defaults (e.g.
    empty strings, zero ints) remain serialized for downstream consumers
    that rely on them.
    """
    if isinstance(node, dict):
        pruned: dict[str, Any] = {}
        for key, value in node.items():
            if key in _OPTIONAL_EMPTY_OMIT_KEYS and isinstance(value, list) and not value:
                continue
            pruned[key] = _prune_optional_empties(value)
        return pruned
    if isinstance(node, list):
        return [_prune_optional_empties(item) for item in node]
    return node


def emit_yaml(model: BaseModel, path: Path) -> None:
    """Write a Pydantic model to a YAML file with header comment.

    Args:
        model: Pydantic model instance to serialize
        path: Output file path

    Example:
        >>> config = GovernanceConfig(testing=TestingConfig(min_coverage=90))
        >>> emit_yaml(config, Path("governance.yaml"))
    """
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.width = 4096  # Prevent line wrapping

    # Convert model to dict using Pydantic v2 API, then prune optional empty
    # additive fields so the on-disk bytes stay backward compatible
    # (NFR-005).
    data = _prune_optional_empties(model.model_dump(mode="json"))

    # Write with header comment
    with open(path, "w", encoding="utf-8") as f:
        f.write(YAML_HEADER)
        yaml.dump(data, f)
