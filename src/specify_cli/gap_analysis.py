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


class DivioType(Enum):
    """Divio documentation types."""

    TUTORIAL = "tutorial"
    HOWTO = "how-to"
    REFERENCE = "reference"
    EXPLANATION = "explanation"
    UNCLASSIFIED = "unclassified"


def parse_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """Parse YAML frontmatter from markdown file.

    Args:
        content: File content

    Returns:
        Frontmatter dict if present, None otherwise
    """
    if not content.startswith("---"):
        return None

    # Find closing ---
    lines = content.split("\n")
    end_idx = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end_idx = i
            break

    if end_idx is None:
        return None

    # Parse YAML frontmatter
    yaml = YAML()
    yaml.preserve_quotes = True
    try:
        frontmatter_text = "\n".join(lines[1:end_idx])
        return yaml.load(frontmatter_text)
    except Exception:
        return None


def classify_by_content_heuristics(content: str) -> DivioType:
    """Classify document by analyzing content patterns.

    Args:
        content: Document content (without frontmatter)

    Returns:
        Best-guess Divio type based on content analysis
    """
    content_lower = content.lower()

    # Tutorial markers
    tutorial_markers = [
        "step 1",
        "step 2",
        "first,",
        "next,",
        "now,",
        "you should see",
        "let's",
        "you'll learn",
        "by the end",
        "what you'll build",
    ]
    tutorial_score = sum(1 for marker in tutorial_markers if marker in content_lower)

    # How-to markers
    howto_markers = [
        "how to",
        "to do",
        "follow these steps",
        "problem:",
        "solution:",
        "before you begin",
        "prerequisites:",
        "verification:",
    ]
    howto_score = sum(1 for marker in howto_markers if marker in content_lower)

    # Reference markers
    reference_markers = [
        "parameters:",
        "returns:",
        "arguments:",
        "options:",
        "methods:",
        "properties:",
        "attributes:",
        "class:",
        "function:",
        "api",
    ]
    reference_score = sum(1 for marker in reference_markers if marker in content_lower)

    # Explanation markers
    explanation_markers = [
        "why",
        "background",
        "concepts",
        "architecture",
        "design decision",
        "alternatives",
        "trade-offs",
        "how it works",
        "understanding",
    ]
    explanation_score = sum(
        1 for marker in explanation_markers if marker in content_lower
    )

    # Determine type by highest score
    scores = {
        DivioType.TUTORIAL: tutorial_score,
        DivioType.HOWTO: howto_score,
        DivioType.REFERENCE: reference_score,
        DivioType.EXPLANATION: explanation_score,
    }

    max_score = max(scores.values())
    if max_score == 0:
        return DivioType.UNCLASSIFIED

    # Return type with highest score
    for divio_type, score in scores.items():
        if score == max_score:
            return divio_type

    return DivioType.UNCLASSIFIED


def classify_divio_type(content: str) -> Tuple[DivioType, float]:
    """Classify document into Divio type.

    Uses multi-strategy approach:
    1. Check frontmatter for explicit 'type' field (confidence: 1.0)
    2. Apply content heuristics (confidence: 0.7)

    Args:
        content: Full document content including frontmatter

    Returns:
        Tuple of (DivioType, confidence_score)
    """
    # Strategy 1: Frontmatter (explicit classification)
    frontmatter = parse_frontmatter(content)
    if frontmatter and "type" in frontmatter:
        type_str = frontmatter["type"].lower()
        type_map = {
            "tutorial": DivioType.TUTORIAL,
            "how-to": DivioType.HOWTO,
            "howto": DivioType.HOWTO,
            "reference": DivioType.REFERENCE,
            "explanation": DivioType.EXPLANATION,
        }
        if type_str in type_map:
            return (type_map[type_str], 1.0)  # High confidence

    # Strategy 2: Content heuristics
    divio_type = classify_by_content_heuristics(content)
    confidence = 0.7 if divio_type != DivioType.UNCLASSIFIED else 0.0

    return (divio_type, confidence)
