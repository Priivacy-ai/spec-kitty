"""Pydantic schemas for constitution config extraction.

Defines the output schema for:
- governance.yaml (testing, quality, performance, branch strategy)
- agents.yaml (agent profiles and selection strategy)
- directives.yaml (numbered rules and enforcement)
- metadata.yaml (extraction provenance and statistics)
"""

from pathlib import Path

from pydantic import BaseModel, Field
from ruamel.yaml import YAML

# Header comment for all emitted YAML files
YAML_HEADER = (
    "# Auto-generated from constitution.md — do not edit directly.\n"
    "# Run 'spec-kitty constitution sync' to regenerate.\n\n"
)


class TestingConfig(BaseModel):
    """Testing requirements extracted from constitution."""

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
    """Constitution-level selection of active doctrine elements."""

    selected_paradigms: list[str] = Field(default_factory=list)
    selected_directives: list[str] = Field(default_factory=list)
    selected_agent_profiles: list[str] = Field(default_factory=list)
    available_tools: list[str] = Field(default_factory=list)
    template_set: str | None = None


class GovernanceConfig(BaseModel):
    """Top-level governance configuration."""

    testing: TestingConfig = Field(default_factory=TestingConfig)
    quality: QualityConfig = Field(default_factory=QualityConfig)
    commits: CommitConfig = Field(default_factory=CommitConfig)
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig)
    branch_strategy: BranchStrategyConfig = Field(default_factory=BranchStrategyConfig)
    doctrine: DoctrineSelectionConfig = Field(default_factory=DoctrineSelectionConfig)
    enforcement: dict[str, str] = Field(default_factory=dict)


class AgentProfile(BaseModel):
    """Configuration for a single AI agent."""

    agent_key: str
    role: str = "implementer"
    preferred_model: str | None = None
    capabilities: list[str] = Field(default_factory=list)


class AgentSelectionConfig(BaseModel):
    """Strategy for selecting agents for tasks."""

    strategy: str = "preferred"
    preferred_implementer: str | None = None
    preferred_reviewer: str | None = None


class AgentsConfig(BaseModel):
    """Agent profiles and selection configuration."""

    profiles: list[AgentProfile] = Field(default_factory=list)
    selection: AgentSelectionConfig = Field(default_factory=AgentSelectionConfig)


class Directive(BaseModel):
    """A single numbered directive from the constitution."""

    id: str
    title: str
    description: str = ""
    severity: str = "warn"
    applies_to: list[str] = Field(default_factory=list)


class DirectivesConfig(BaseModel):
    """Collection of directives extracted from constitution."""

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
    constitution_hash: str = ""  # "sha256:..."
    source_path: str = ".kittify/constitution/constitution.md"
    extraction_mode: str = "deterministic"  # "deterministic" | "hybrid" | "ai_only"
    sections_parsed: SectionsParsed = Field(default_factory=SectionsParsed)


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

    # Convert model to dict using Pydantic v2 API
    data = model.model_dump(mode="json")

    # Write with header comment
    with open(path, "w", encoding="utf-8") as f:
        f.write(YAML_HEADER)
        yaml.dump(data, f)
