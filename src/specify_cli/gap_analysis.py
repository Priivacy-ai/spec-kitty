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


class DocFramework(Enum):
    """Supported documentation frameworks."""

    SPHINX = "sphinx"
    MKDOCS = "mkdocs"
    DOCUSAURUS = "docusaurus"
    JEKYLL = "jekyll"
    HUGO = "hugo"
    PLAIN_MARKDOWN = "plain-markdown"
    UNKNOWN = "unknown"


def detect_doc_framework(docs_dir: Path) -> DocFramework:
    """Detect documentation framework from file structure.

    Args:
        docs_dir: Directory containing documentation

    Returns:
        Detected framework or UNKNOWN if cannot determine
    """
    # Sphinx: conf.py is definitive indicator
    if (docs_dir / "conf.py").exists():
        return DocFramework.SPHINX

    # MkDocs: mkdocs.yml is definitive
    if (docs_dir / "mkdocs.yml").exists():
        return DocFramework.MKDOCS

    # Docusaurus: docusaurus.config.js
    if (docs_dir / "docusaurus.config.js").exists():
        return DocFramework.DOCUSAURUS

    # Jekyll: _config.yml
    if (docs_dir / "_config.yml").exists():
        return DocFramework.JEKYLL

    # Hugo: config.toml or config.yaml
    if (docs_dir / "config.toml").exists() or (docs_dir / "config.yaml").exists():
        return DocFramework.HUGO

    # Check for markdown files without framework
    if list(docs_dir.rglob("*.md")):
        return DocFramework.PLAIN_MARKDOWN

    return DocFramework.UNKNOWN
