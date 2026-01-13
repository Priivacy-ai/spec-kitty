"""Gap analysis for documentation missions.

This module provides functionality to audit existing documentation, classify
docs into Divio types, build coverage matrices, and identify gaps.

The multi-strategy approach:
1. Detect documentation framework from file structure
2. Parse frontmatter for explicit type classification
3. Apply content heuristics if no explicit type
4. Build coverage matrix showing what exists vs what's needed
5. Prioritize gaps by user impact
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from ruamel.yaml import YAML
