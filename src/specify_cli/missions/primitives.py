"""Primitive execution context for mission framework.

This module defines the PrimitiveExecutionContext dataclass that carries
state through the middleware pipeline. Glossary-specific fields were added
in WP09 (feature 041) to enable term extraction, conflict detection,
strictness resolution, and checkpoint/resume across middleware layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from specify_cli.glossary.checkpoint import ScopeRef
from specify_cli.glossary.extraction import ExtractedTerm
from specify_cli.glossary.models import SemanticConflict
from specify_cli.glossary.strictness import Strictness


@dataclass
class PrimitiveExecutionContext:
    """Execution context for mission primitives.

    This context flows through the glossary middleware pipeline. Each middleware
    layer reads and writes fields on this object.

    **Mutability design (intentional):**
    The context is mutable by design. All middleware stages in the pipeline
    receive and modify the **same** ``PrimitiveExecutionContext`` instance.
    Each middleware's ``process()`` method mutates fields in-place (e.g.,
    appending to ``extracted_terms``, setting ``effective_strictness``) and
    returns the same object. This is a deliberate pipeline pattern choice:
    middleware stages are sequentially composed, never run in parallel, and
    the shared-mutable-context avoids the overhead of copying potentially
    large term/conflict lists at each layer boundary. Callers should be
    aware that the context they pass to ``GlossaryMiddlewarePipeline.process()``
    will be mutated in-place by intermediate middleware layers.

    Fields are grouped into two categories:
    - Core fields: Required for every primitive execution
    - Glossary fields: Populated by the glossary middleware pipeline (WP09)
    """

    # --- Core fields (required) ---
    step_id: str
    mission_id: str
    run_id: str
    inputs: Dict[str, Any]
    metadata: Dict[str, Any]
    config: Dict[str, Any]

    # --- Glossary middleware fields (populated by pipeline) ---
    extracted_terms: List[ExtractedTerm] = field(default_factory=list)
    conflicts: List[SemanticConflict] = field(default_factory=list)
    effective_strictness: Optional[Strictness] = None
    checkpoint_token: Optional[str] = None
    scope_refs: List[ScopeRef] = field(default_factory=list)

    # --- Internal pipeline state ---
    step_input: Dict[str, Any] = field(default_factory=dict)
    step_output: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Populate step_input from inputs for middleware compatibility."""
        if not self.step_input and self.inputs:
            self.step_input = dict(self.inputs)

    @property
    def mission_strictness(self) -> Optional[Strictness]:
        """Extract mission-level strictness from config.

        Returns:
            Strictness enum value if present in config['glossary']['strictness'],
            None otherwise. Returns None on invalid values.
        """
        if "glossary" in self.config and "strictness" in self.config["glossary"]:
            raw = self.config["glossary"]["strictness"]
            try:
                return Strictness(raw)
            except ValueError:
                return None
        return None

    @property
    def step_strictness(self) -> Optional[Strictness]:
        """Extract step-level strictness from metadata.

        Returns:
            Strictness enum value if present in metadata['glossary_check_strictness'],
            None otherwise. Returns None on invalid values.
        """
        if "glossary_check_strictness" in self.metadata:
            raw = self.metadata["glossary_check_strictness"]
            if raw is None:
                return None
            try:
                return Strictness(raw)
            except ValueError:
                return None
        return None

    def is_glossary_enabled(self) -> bool:
        """Determine if glossary checks are enabled for this step.

        Rules (in precedence order):
        1. Explicit metadata ``glossary_check: false`` / ``"disabled"`` / ``"false"`` -> False
        2. Explicit metadata ``glossary_check: true`` / ``"enabled"`` / ``"true"`` -> True
        3. Metadata ``glossary_check: null`` -> fall through to mission config
        4. Mission config ``glossary.enabled: false`` -> False
        5. Default -> True (enabled by default per FR-020)

        Boolean values from YAML (``glossary_check: false`` parses as Python ``False``)
        are handled explicitly. String comparisons are case-insensitive.

        Returns:
            True if glossary checks should run, False to skip.
        """
        # Step metadata (highest precedence)
        if "glossary_check" in self.metadata:
            value = self.metadata["glossary_check"]
            if value is None:
                pass  # Treat null as unset, fall through
            elif isinstance(value, bool):
                return value
            elif isinstance(value, str):
                lower = value.lower()
                if lower in ("disabled", "false"):
                    return False
                if lower in ("enabled", "true"):
                    return True
                # Unknown string value -> treat as enabled (safe default)
                return True
            else:
                return True  # Any explicit non-null, non-bool, non-string value = enabled

        # Mission config
        if "glossary" in self.config:
            glossary_cfg = self.config["glossary"]
            if isinstance(glossary_cfg, dict) and "enabled" in glossary_cfg:
                return glossary_cfg["enabled"] is not False

        # Default: enabled (per FR-020)
        return True
