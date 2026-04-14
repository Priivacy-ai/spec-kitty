"""Charter parsing and configuration extraction.

This subpackage provides tools for:
- Parsing charter markdown into structured sections
- Extracting configuration from markdown tables, YAML blocks, and prose
- Validating extracted config against Pydantic schemas
- Emitting YAML config files for consumption by other modules

Provides:
- sync(): Parse charter.md → structured YAML files
- load_governance_config(): Load governance rules for hook evaluation
- post_save_hook(): Auto-trigger sync after CLI writes
"""

from .bundle import (
    CANONICAL_MANIFEST,
    CharterBundleManifest,
    SCHEMA_VERSION,
)
from .catalog import DoctrineCatalog, load_doctrine_catalog
from .compiler import (
    CompiledCharter,
    CharterReference,
    WriteBundleResult,
    compile_charter,
    write_compiled_charter,
)
from .context import CharterContextResult, build_charter_context
from .generator import CharterDraft, build_charter_draft, write_charter
from .interview import (
    CharterInterview,
    MINIMAL_QUESTION_ORDER,
    QUESTION_ORDER,
    QUESTION_PROMPTS,
    apply_answer_overrides,
    default_interview,
    read_interview_answers,
    write_interview_answers,
)
from .parser import CharterParser, CharterSection
from .schemas import (
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
    CharterTestingConfig,
    emit_yaml,
)
from .sync import (
    SyncResult,
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
    resolve_governance_for_profile,
)
from .template_resolver import CharterTemplateResolver

__all__ = [
    "CANONICAL_MANIFEST",
    "CharterBundleManifest",
    "SCHEMA_VERSION",
    "DoctrineCatalog",
    "load_doctrine_catalog",
    "CompiledCharter",
    "CharterReference",
    "WriteBundleResult",
    "compile_charter",
    "write_compiled_charter",
    "CharterContextResult",
    "build_charter_context",
    "CharterDraft",
    "build_charter_draft",
    "write_charter",
    "CharterInterview",
    "QUESTION_ORDER",
    "MINIMAL_QUESTION_ORDER",
    "QUESTION_PROMPTS",
    "default_interview",
    "read_interview_answers",
    "write_interview_answers",
    "apply_answer_overrides",
    "CharterParser",
    "CharterSection",
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
    "CharterTestingConfig",
    "emit_yaml",
    "SyncResult",
    "load_directives_config",
    "load_governance_config",
    "post_save_hook",
    "sync",
    "GovernanceResolution",
    "GovernanceResolutionError",
    "resolve_governance",
    "resolve_governance_for_profile",
    "collect_governance_diagnostics",
    "CharterTemplateResolver",
]
