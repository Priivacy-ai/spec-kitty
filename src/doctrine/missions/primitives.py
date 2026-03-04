"""Primitive execution context for mission framework.

This module defines the PrimitiveExecutionContext dataclass that carries
state through the middleware pipeline. Glossary-specific fields were added
in WP09 (feature 041) to enable term extraction, conflict detection,
strictness resolution, and checkpoint/resume across middleware layers.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
    inputs: dict[str, Any]
    metadata: dict[str, Any]
    config: dict[str, Any]

    # --- Glossary middleware fields (populated by pipeline) ---
    extracted_terms: list[ExtractedTerm] = field(default_factory=list)
    conflicts: list[SemanticConflict] = field(default_factory=list)
    effective_strictness: Strictness | None = None
    retry_token: str | None = None
    # Backward-compat alias used by some callers; mirrors retry_token.
    checkpoint_token: str | None = None
    scope_refs: list[ScopeRef] = field(default_factory=list)

    # --- Internal pipeline state ---
    step_input: dict[str, Any] = field(default_factory=dict)
    step_output: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Populate step_input from inputs for middleware compatibility."""
        if not self.step_input and self.inputs:
            self.step_input = dict(self.inputs)
        if self.retry_token and not self.checkpoint_token:
            self.checkpoint_token = self.retry_token
        elif self.checkpoint_token and not self.retry_token:
            self.retry_token = self.checkpoint_token

    @property
    def mission_strictness(self) -> Strictness | None:
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
    def step_strictness(self) -> Strictness | None:
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

    def _glossary_enabled_from_metadata(self, value: object) -> bool | None:
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            lower = value.lower()
            return lower not in ("disabled", "false")
        if value is not None:
            return True
        return None

    def is_glossary_enabled(self) -> bool:
        """Determine if glossary checks are enabled for this step.

        Rules (in precedence order):
        1. Explicit metadata ``glossary_check: false`` / ``"disabled"`` / ``"false"``
           -> False
        2. Explicit metadata ``glossary_check: true`` / ``"enabled"`` / ``"true"``
           -> True
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
            result = self._glossary_enabled_from_metadata(
                self.metadata["glossary_check"]
            )
            if result is not None:
                return result

        # Mission config
        if "glossary" in self.config:
            glossary_cfg = self.config["glossary"]
            if isinstance(glossary_cfg, dict) and "enabled" in glossary_cfg:
                return glossary_cfg["enabled"] is not False

        # Default: enabled (per FR-020)
        return True
