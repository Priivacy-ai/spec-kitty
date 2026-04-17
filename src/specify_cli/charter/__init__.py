"""Backward-compatibility shim for specify_cli.charter — DEPRECATED.

The canonical charter implementation lives in the ``charter`` package.
All symbols are re-exported here so that existing ``from specify_cli.charter
import X`` call sites continue to work (C-005), but this path is deprecated
and will be removed in release 3.3.0.  Migrate imports to ``charter`` directly.
"""

import warnings as _warnings

__deprecated__: bool = True
__canonical_import__: str = "charter"
__removal_release__: str = "3.3.0"
__deprecation_message__: str = (
    "specify_cli.charter is deprecated and will be removed in 3.3.0. "
    "Use 'charter' instead: replace 'from specify_cli.charter import X' "
    "with 'from charter import X'."
)

_warnings.warn(__deprecation_message__, DeprecationWarning, stacklevel=2)

from charter import (  # noqa: F401
    CANONICAL_MANIFEST,
    CharterBundleManifest,
    SCHEMA_VERSION,
    DoctrineCatalog,
    load_doctrine_catalog,
    CompiledCharter,
    CharterReference,
    WriteBundleResult,
    compile_charter,
    write_compiled_charter,
    CharterContextResult,
    build_charter_context,
    CharterDraft,
    build_charter_draft,
    write_charter,
    CharterInterview,
    QUESTION_ORDER,
    MINIMAL_QUESTION_ORDER,
    QUESTION_PROMPTS,
    default_interview,
    read_interview_answers,
    write_interview_answers,
    apply_answer_overrides,
    CharterParser,
    CharterSection,
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
    SyncResult,
    load_directives_config,
    load_governance_config,
    post_save_hook,
    sync,
    GovernanceResolution,
    GovernanceResolutionError,
    collect_governance_diagnostics,
    resolve_governance,
    resolve_governance_for_profile,
    CharterTemplateResolver,
)

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
    "collect_governance_diagnostics",
    "resolve_governance",
    "resolve_governance_for_profile",
    "CharterTemplateResolver",
]
