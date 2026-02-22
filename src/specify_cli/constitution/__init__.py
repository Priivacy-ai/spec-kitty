"""Constitution parsing and configuration extraction.

This subpackage provides tools for:
- Parsing constitution markdown into structured sections
- Extracting configuration from markdown tables, YAML blocks, and prose
- Validating extracted config against Pydantic schemas
- Emitting YAML config files for consumption by other modules

Provides:
- sync(): Parse constitution.md → structured YAML files
- load_governance_config(): Load governance rules for hook evaluation
- load_agents_config(): Load agent profiles for routing
- post_save_hook(): Auto-trigger sync after CLI writes
"""

from .parser import ConstitutionParser, ConstitutionSection
from .schemas import (
    AgentProfile,
    AgentsConfig,
    AgentSelectionConfig,
    BranchStrategyConfig,
    CommitConfig,
    DoctrineSelectionConfig,
    Directive,
    DirectivesConfig,
    ExtractionMetadata,
    GovernanceConfig,
    PerformanceConfig,
    QualityConfig,
    SectionsParsed,
    ConstitutionTestingConfig,
    emit_yaml,
)
from .sync import (
    SyncResult,
    load_agents_config,
    load_directives_config,
    load_governance_config,
    post_save_hook,
    sync,
)
from .resolver import (
    GovernanceResolution,
    GovernanceResolutionError,
    collect_governance_diagnostics,
    resolve_governance,
)

__all__ = [
    "ConstitutionParser",
    "ConstitutionSection",
    "AgentProfile",
    "AgentsConfig",
    "AgentSelectionConfig",
    "BranchStrategyConfig",
    "CommitConfig",
    "DoctrineSelectionConfig",
    "Directive",
    "DirectivesConfig",
    "ExtractionMetadata",
    "GovernanceConfig",
    "PerformanceConfig",
    "QualityConfig",
    "SectionsParsed",
    "ConstitutionTestingConfig",
    "emit_yaml",
    "SyncResult",
    "load_agents_config",
    "load_directives_config",
    "load_governance_config",
    "post_save_hook",
    "sync",
    "GovernanceResolution",
    "GovernanceResolutionError",
    "resolve_governance",
    "collect_governance_diagnostics",
]
