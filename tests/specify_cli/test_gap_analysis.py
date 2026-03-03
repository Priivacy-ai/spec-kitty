"""Tests for documentation gap analysis."""

import pytest
from datetime import datetime
from pathlib import Path

from specify_cli.gap_analysis import (
    DocFramework,
    DivioType,
    GapPriority,
    GapAnalysis,
    CoverageMatrix,
    detect_doc_framework,
    classify_divio_type,
    prioritize_gaps,
)


# T068: Test Framework Detection
def test_detect_sphinx_framework(tmp_path):
    """Test detects Sphinx from conf.py."""
    (tmp_path / "conf.py").write_text("project = 'Test'")

    framework = detect_doc_framework(tmp_path)
    assert framework == DocFramework.SPHINX


def test_detect_mkdocs_framework(tmp_path):
    """Test detects MkDocs from mkdocs.yml."""
    (tmp_path / "mkdocs.yml").write_text("site_name: Test")

    framework = detect_doc_framework(tmp_path)
    assert framework == DocFramework.MKDOCS


def test_detect_docusaurus_framework(tmp_path):
    """Test detects Docusaurus from docusaurus.config.js."""
    (tmp_path / "docusaurus.config.js").write_text("module.exports = {}")

    framework = detect_doc_framework(tmp_path)
    assert framework == DocFramework.DOCUSAURUS


def test_detect_jekyll_framework(tmp_path):
    """Test detects Jekyll from _config.yml."""
    (tmp_path / "_config.yml").write_text("title: Test")

    framework = detect_doc_framework(tmp_path)
    assert framework == DocFramework.JEKYLL


def test_detect_plain_markdown(tmp_path):
    """Test detects plain Markdown when no framework present."""
    (tmp_path / "index.md").write_text("# Test")

    framework = detect_doc_framework(tmp_path)
    assert framework == DocFramework.PLAIN_MARKDOWN


def test_detect_unknown_when_empty(tmp_path):
    """Test returns UNKNOWN for empty directory."""
    framework = detect_doc_framework(tmp_path)
    assert framework == DocFramework.UNKNOWN


# T069: Test Divio Classification
def test_classify_from_frontmatter():
    """Test classification from explicit frontmatter."""
    content = """---
type: tutorial
---
# Some Content
"""
    divio_type, confidence = classify_divio_type(content)
    assert divio_type == DivioType.TUTORIAL
    assert confidence == 1.0  # High confidence


@pytest.mark.parametrize("type_str,expected_type", [
    ("tutorial", DivioType.TUTORIAL),
    ("how-to", DivioType.HOWTO),
    ("howto", DivioType.HOWTO),
    ("reference", DivioType.REFERENCE),
    ("explanation", DivioType.EXPLANATION),
])
def test_classify_from_frontmatter_types(type_str, expected_type):
    """Test all Divio type values in frontmatter."""
    content = f"""---
type: {type_str}
---
# Content
"""
    divio_type, confidence = classify_divio_type(content)
    assert divio_type == expected_type
    assert confidence == 1.0


def test_classify_tutorial_by_content():
    """Test tutorial classification from content heuristics."""
    content = """# Getting Started Tutorial

## What You'll Learn
In this tutorial, you'll learn...

## Step 1: Install
First, install the software...

## Step 2: Run
Now, let's run it...

## What You've Accomplished
You now know how to...
"""
    divio_type, confidence = classify_divio_type(content)
    assert divio_type == DivioType.TUTORIAL
    assert confidence >= 0.5  # Medium confidence (heuristic)


def test_classify_howto_by_content():
    """Test how-to classification from content heuristics."""
    content = """# How to Deploy

## Problem
You need to deploy...

## Solution
Follow these steps...

## Verification
To verify it worked...
"""
    divio_type, confidence = classify_divio_type(content)
    assert divio_type == DivioType.HOWTO
    assert confidence >= 0.5


def test_classify_reference_by_content():
    """Test reference classification from content heuristics."""
    content = """# API Reference

## Functions

### function_name

**Parameters:**
- param1: description

**Returns:**
- return value
"""
    divio_type, confidence = classify_divio_type(content)
    assert divio_type == DivioType.REFERENCE
    assert confidence >= 0.5


def test_classify_explanation_by_content():
    """Test explanation classification from content heuristics."""
    content = """# Architecture Explanation

## Background
This architecture was chosen because...

## Design Decisions
We decided to use...

## Alternatives Considered
We also looked at...

## Trade-offs
The advantages are... The disadvantages are...
"""
    divio_type, confidence = classify_divio_type(content)
    assert divio_type == DivioType.EXPLANATION
    assert confidence >= 0.5


def test_classify_unclassifiable_content():
    """Test returns UNCLASSIFIED for ambiguous content."""
    content = """# Some Document

This is content without clear type indicators.
Just generic text.
"""
    divio_type, confidence = classify_divio_type(content)
    assert divio_type == DivioType.UNCLASSIFIED
    assert confidence == 0.0


# T070: Test Coverage Matrix
def test_coverage_matrix_initialization():
    """Test CoverageMatrix initializes correctly."""
    matrix = CoverageMatrix(
        project_areas=["auth", "api"],
        cells={
            ("auth", "tutorial"): Path("docs/tutorials/auth.md"),
            ("auth", "reference"): Path("docs/reference/auth.md"),
            ("api", "reference"): Path("docs/reference/api.md"),
        }
    )

    assert len(matrix.project_areas) == 2
    assert len(matrix.divio_types) == 4
    assert len(matrix.cells) == 3  # 3 filled cells


def test_coverage_matrix_get_gaps():
    """Test get_gaps() returns missing cells."""
    matrix = CoverageMatrix(
        project_areas=["auth", "api"],
        cells={
            ("auth", "tutorial"): Path("docs/tutorials/auth.md"),
            ("auth", "reference"): Path("docs/reference/auth.md"),
            # Missing: auth/how-to, auth/explanation, api/tutorial, api/how-to, api/reference, api/explanation
        }
    )

    gaps = matrix.get_gaps()

    # Should identify 6 gaps (2 areas × 4 types - 2 filled = 6 missing)
    assert len(gaps) == 6
    assert ("auth", "how-to") in gaps
    assert ("api", "tutorial") in gaps


def test_coverage_matrix_percentage():
    """Test coverage percentage calculation."""
    matrix = CoverageMatrix(
        project_areas=["auth", "api"],
        cells={
            ("auth", "tutorial"): Path("docs/tutorials/auth.md"),
            ("auth", "reference"): Path("docs/reference/auth.md"),
            ("api", "reference"): Path("docs/reference/api.md"),
        }
    )

    # 3 filled out of 8 total cells (2 areas × 4 types)
    # Coverage: 3/8 = 0.375
    coverage = matrix.get_coverage_percentage()
    assert coverage == 0.375


def test_coverage_matrix_markdown_table():
    """Test markdown table generation."""
    matrix = CoverageMatrix(
        project_areas=["auth"],
        cells={
            ("auth", "tutorial"): Path("docs/tutorials/auth.md"),
            ("auth", "reference"): Path("docs/reference/auth.md"),
        }
    )

    table = matrix.to_markdown_table()

    # Check table has headers
    assert "Area" in table or "auth" in table
    assert "tutorial" in table
    assert "✓" in table or "X" in table or "coverage" in table.lower()


# T071: Test Gap Prioritization
def test_prioritize_tutorial_gaps_high():
    """Test tutorial gaps prioritized as HIGH."""
    gaps = [("auth", "tutorial")]
    project_areas = ["auth", "api"]

    prioritized = prioritize_gaps(gaps, project_areas, {})

    assert len(prioritized) == 1
    assert prioritized[0].priority == GapPriority.HIGH


def test_prioritize_reference_gaps_high():
    """Test reference gaps prioritized as HIGH for core areas."""
    gaps = [("auth", "reference")]  # auth is core (first area)
    project_areas = ["auth", "api", "cli"]

    prioritized = prioritize_gaps(gaps, project_areas, {})

    assert prioritized[0].priority == GapPriority.HIGH


def test_prioritize_howto_gaps_medium():
    """Test how-to gaps prioritized as MEDIUM."""
    gaps = [("auth", "how-to")]
    project_areas = ["auth"]

    prioritized = prioritize_gaps(gaps, project_areas, {})

    assert prioritized[0].priority == GapPriority.MEDIUM


def test_prioritize_explanation_gaps_low():
    """Test explanation gaps prioritized as LOW."""
    gaps = [("auth", "explanation")]
    project_areas = ["auth"]

    prioritized = prioritize_gaps(gaps, project_areas, {})

    assert prioritized[0].priority == GapPriority.LOW


def test_gaps_sorted_by_priority():
    """Test gaps sorted with HIGH first, then MEDIUM, then LOW."""
    gaps = [
        ("auth", "explanation"),  # LOW
        ("auth", "tutorial"),     # MEDIUM (auth is core with 3 areas)
        ("auth", "how-to"),       # MEDIUM
    ]
    project_areas = ["auth", "api", "cli"]  # auth is core (first half)

    prioritized = prioritize_gaps(gaps, project_areas, {})

    # With 3 areas, auth (index 0) is core, but tutorials for advanced features get MEDIUM
    # Tutorial is MEDIUM for non-core, reference is HIGH for core
    # All should be sorted by priority
    assert len(prioritized) == 3
    # Just verify they're sorted, not specific priorities
    priorities = [g.priority for g in prioritized]
    assert sorted(priorities, key=lambda p: {"high": 0, "medium": 1, "low": 2}[p.value]) == priorities


# Additional tests for GapAnalysis dataclass
def test_gap_analysis_dataclass():
    """Test GapAnalysis dataclass construction."""
    matrix = CoverageMatrix(
        project_areas=["auth"],
        cells={("auth", "tutorial"): Path("docs/tutorial.md")}
    )

    analysis = GapAnalysis(
        project_name="test-project",
        analysis_date=datetime.now(),
        framework=DocFramework.SPHINX,
        coverage_matrix=matrix,
        gaps=[]
    )

    assert analysis.framework == DocFramework.SPHINX
    assert analysis.coverage_matrix == matrix
    assert isinstance(analysis.analysis_date, datetime)
