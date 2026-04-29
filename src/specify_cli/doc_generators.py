"""Backward-compat shim — canonical home is specify_cli.doc_analysis.doc_generators."""

from specify_cli.doc_analysis.doc_generators import (  # noqa: F401
    DocGenerator,
    GeneratorError,
    GeneratorResult,
    JSDocGenerator,
    RustdocGenerator,
    SphinxGenerator,
    check_tool_available,
)
