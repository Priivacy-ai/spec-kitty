"""Documentation State Management for Spec Kitty.

This module manages documentation mission state persistence in feature meta.json files.
State includes iteration mode, selected Divio types, configured generators, and audit metadata.

Documentation State Schema for meta.json
========================================

The documentation_state field is added to feature meta.json files for
documentation mission features. It persists state between iterations.

Schema:
{
    "documentation_state": {
        "iteration_mode": "initial" | "gap_filling" | "feature_specific",
        "divio_types_selected": ["tutorial", "how-to", "reference", "explanation"],
        "generators_configured": [
            {
                "name": "sphinx" | "jsdoc" | "rustdoc",
                "language": "python" | "javascript" | "typescript" | "rust",
                "config_path": "relative/path/to/config.py"
            }
        ],
        "target_audience": "developers" | "end-users" | "contributors" | "operators",
        "last_audit_date": "2026-01-12T00:00:00Z" | null,
        "coverage_percentage": 0.75  # 0.0 to 1.0
    }
}

Fields:
- iteration_mode: How this documentation mission was run
- divio_types_selected: Which Divio types user chose to include
- generators_configured: Which generators were set up and where
- target_audience: Primary documentation audience
- last_audit_date: When gap analysis last ran (null if never)
- coverage_percentage: Overall doc coverage from most recent audit (0.0 if initial)
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import List, Literal, Optional, TypedDict


class GeneratorConfig(TypedDict):
    """Generator configuration entry."""

    name: Literal["sphinx", "jsdoc", "rustdoc"]
    language: str
    config_path: str


class DocumentationState(TypedDict):
    """Documentation state schema for meta.json."""

    iteration_mode: Literal["initial", "gap_filling", "feature_specific"]
    divio_types_selected: List[str]
    generators_configured: List[GeneratorConfig]
    target_audience: str
    last_audit_date: Optional[str]  # ISO datetime or null
    coverage_percentage: float  # 0.0 to 1.0
