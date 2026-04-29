"""Backward-compat shim — canonical home is specify_cli.doc_analysis.doc_state."""

from specify_cli.doc_analysis.doc_state import (  # noqa: F401
    DocumentationState,
    GeneratorConfig,
    ensure_documentation_state,
    get_state_version,
    initialize_documentation_state,
    read_documentation_state,
    set_audit_metadata,
    set_divio_types_selected,
    set_generators_configured,
    set_iteration_mode,
    update_documentation_state,
    write_documentation_state,
)
