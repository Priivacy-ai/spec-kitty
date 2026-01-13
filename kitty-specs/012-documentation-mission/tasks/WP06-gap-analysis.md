---
work_package_id: "WP06"
subtasks:
  - "T033"
  - "T034"
  - "T035"
  - "T036"
  - "T037"
  - "T038"
  - "T039"
title: "Gap Analysis & Coverage Matrix"
phase: "Phase 1 - Core Logic"
lane: "for_review"
assignee: ""
agent: "claude"
shell_pid: "59241"
review_status: ""
reviewed_by: ""
dependencies:
  - "WP01"
history:
  - timestamp: "2026-01-12T17:18:56Z"
    lane: "planned"
    agent: "system"
    shell_pid: ""
    action: "Prompt generated via /spec-kitty.tasks"
---

# Work Package Prompt: WP06 – Gap Analysis & Coverage Matrix

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_status` field above. If it says `has_feedback`, scroll to the **Review Feedback** section immediately (right below this notice).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Mark as acknowledged**: When you understand the feedback and begin addressing it, update `review_status: acknowledged` in the frontmatter.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

> **Populated by `/spec-kitty.review`** – Reviewers add detailed feedback here when work needs changes. Implementation must address every item listed below before returning for re-review.

*[This section is empty initially. Reviewers will populate it if the work is returned from review.]*

---

## ⚠️ Dependency Rebase Guidance

**This WP depends on**: WP01 (Mission Infrastructure)

**Before starting work**:
1. Ensure WP01 is complete (mission.yaml exists)
2. WP03 (Divio templates) should be complete for best reference, but not strictly required

---

## Objectives & Success Criteria

**Goal**: Implement gap analysis algorithm that audits existing documentation, classifies docs into Divio types, builds coverage matrix, identifies gaps, and generates gap-analysis.md reports.

**Success Criteria**:
- `src/specify_cli/gap_analysis.py` module created
- Framework detection identifies Sphinx, MkDocs, Docusaurus, Jekyll, or plain Markdown
- Divio type classification uses multi-strategy approach (frontmatter, content heuristics)
- `CoverageMatrix` class builds matrix showing coverage by area and Divio type
- Gap prioritization logic assigns high/medium/low based on user impact
- Version mismatch detection compares code APIs vs documented APIs
- `gap-analysis.md` report generated with coverage matrix and prioritized gaps
- Conservative heuristics avoid false positives
- Users can override classification via frontmatter

## Context & Constraints

**Prerequisites**:
- Python 3.11+ with pathlib
- ruamel.yaml for frontmatter parsing
- Understanding of Divio documentation types

**Reference Documents**:
- [research.md](../research.md) - Gap analysis algorithms (lines 242-352)
- [data-model.md](../data-model.md) - Gap Analysis and Coverage Matrix entities (lines 330-407)
- [spec.md](../spec.md) - Gap analysis requirements (FR-005, FR-009, lines 106, 110)

**Constraints**:
- Must handle projects without Divio-structured docs
- Must be conservative (only flag obvious gaps)
- Must allow user override via frontmatter `type` field
- Must work on large documentation sets (performance)
- Should support common doc frameworks (Sphinx, MkDocs, Jekyll, Docusaurus)

**Gap Analysis Strategy** (from research):
1. **File structure analysis**: Detect framework from characteristic files
2. **Frontmatter classification**: Parse YAML frontmatter for explicit `type` field
3. **Content heuristics**: Analyze content patterns to infer Divio type
4. **User overrides**: Trust explicit frontmatter over heuristics

## Subtasks & Detailed Guidance

### Subtask T033 – Create gap_analysis.py Module

**Purpose**: Create the Python module for gap analysis functionality.

**Steps**:
1. Create `src/specify_cli/gap_analysis.py`
2. Add module docstring:
   ```python
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
   ```
3. Add imports:
   ```python
   from __future__ import annotations

   from dataclasses import dataclass, field
   from datetime import datetime
   from enum import Enum
   from pathlib import Path
   from typing import Dict, List, Optional, Tuple

   from ruamel.yaml import YAML
   ```

**Files**: `src/specify_cli/gap_analysis.py` (new file)

**Parallel?**: No (foundation for other subtasks)

**Notes**: This module is independent of doc_generators.py; both are used during planning/implementation.

### Subtask T034 – Implement Framework Detection

**Purpose**: Detect which documentation framework (if any) a project uses by analyzing file structure.

**Steps**:
1. In `gap_analysis.py`, define framework enum:
   ```python
   class DocFramework(Enum):
       """Supported documentation frameworks."""
       SPHINX = "sphinx"
       MKDOCS = "mkdocs"
       DOCUSAURUS = "docusaurus"
       JEKYLL = "jekyll"
       HUGO = "hugo"
       PLAIN_MARKDOWN = "plain-markdown"
       UNKNOWN = "unknown"
   ```

2. Implement detection function:
   ```python
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
   ```

**Files**: `src/specify_cli/gap_analysis.py` (modified)

**Parallel?**: Yes (can develop alongside classification logic)

**Notes**:
- Detection is heuristic-based (checks for characteristic files)
- Sphinx: conf.py
- MkDocs: mkdocs.yml
- Docusaurus: docusaurus.config.js
- Jekyll: _config.yml
- Hugo: config.toml or config.yaml
- Plain Markdown: .md files but no framework config
- UNKNOWN: no docs found

**Quality Validation**:
- Does it detect common frameworks correctly?
- Does it handle projects without frameworks?
- Does it return UNKNOWN rather than crash?

### Subtask T035 – Implement Divio Type Classification

**Purpose**: Classify documentation files into Divio types using frontmatter and content heuristics.

**Steps**:
1. In `gap_analysis.py`, define Divio type enum:
   ```python
   class DivioType(Enum):
       """Divio documentation types."""
       TUTORIAL = "tutorial"
       HOWTO = "how-to"
       REFERENCE = "reference"
       EXPLANATION = "explanation"
       UNCLASSIFIED = "unclassified"
   ```

2. Implement frontmatter parser:
   ```python
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
   ```

3. Implement content heuristics:
   ```python
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
           "step 1", "step 2", "first,", "next,", "now,", "you should see",
           "let's", "you'll learn", "by the end", "what you'll build"
       ]
       tutorial_score = sum(1 for marker in tutorial_markers if marker in content_lower)

       # How-to markers
       howto_markers = [
           "how to", "to do", "follow these steps", "problem:", "solution:",
           "before you begin", "prerequisites:", "verification:"
       ]
       howto_score = sum(1 for marker in howto_markers if marker in content_lower)

       # Reference markers
       reference_markers = [
           "parameters:", "returns:", "arguments:", "options:", "methods:",
           "properties:", "attributes:", "class:", "function:", "api"
       ]
       reference_score = sum(1 for marker in reference_markers if marker in content_lower)

       # Explanation markers
       explanation_markers = [
           "why", "background", "concepts", "architecture", "design decision",
           "alternatives", "trade-offs", "how it works", "understanding"
       ]
       explanation_score = sum(1 for marker in explanation_markers if marker in content_lower)

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
   ```

4. Implement main classification function:
   ```python
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
   ```

**Files**: `src/specify_cli/gap_analysis.py` (modified)

**Parallel?**: Yes (can develop alongside framework detection and coverage matrix)

**Notes**:
- Two-strategy approach: frontmatter (definitive) then heuristics (fallback)
- Confidence score indicates certainty (1.0 = explicit, 0.7 = heuristic, 0.0 = unknown)
- Heuristics use keyword scoring (count markers for each type)
- Conservative approach (high threshold for classification)

**Quality Validation**:
- Does frontmatter parsing handle edge cases (missing closing ---, invalid YAML)?
- Do heuristics correctly identify each Divio type?
- Is confidence score appropriate for each strategy?
- Does it return UNCLASSIFIED when uncertain?

### Subtask T036 – Implement CoverageMatrix Class

**Purpose**: Implement the coverage matrix data structure that shows which project areas have which Divio types.

**Steps**:
1. In `gap_analysis.py`, implement `CoverageMatrix`:
   ```python
   @dataclass
   class CoverageMatrix:
       """Documentation coverage matrix showing Divio type coverage by project area.

       The matrix shows which project areas (features, modules, components) have
       documentation for each Divio type (tutorial, how-to, reference, explanation).
       """

       project_areas: List[str] = field(default_factory=list)  # e.g., ["auth", "api", "cli"]
       divio_types: List[str] = field(default_factory=lambda: [
           "tutorial", "how-to", "reference", "explanation"
       ])

       # Maps (area, type) to doc file path (None if missing)
       cells: Dict[Tuple[str, str], Optional[Path]] = field(default_factory=dict)

       def get_coverage_for_area(self, area: str) -> Dict[str, Optional[Path]]:
           """Get all Divio type coverage for one project area.

           Args:
               area: Project area name

           Returns:
               Dict mapping Divio type to doc file path (or None if missing)
           """
           return {
               dtype: self.cells.get((area, dtype))
               for dtype in self.divio_types
           }

       def get_coverage_for_type(self, divio_type: str) -> Dict[str, Optional[Path]]:
           """Get all project area coverage for one Divio type.

           Args:
               divio_type: Divio type name

           Returns:
               Dict mapping project area to doc file path (or None if missing)
           """
           return {
               area: self.cells.get((area, divio_type))
               for area in self.project_areas
           }

       def get_gaps(self) -> List[Tuple[str, str]]:
           """Return list of (area, type) tuples with missing documentation.

           Returns:
               List of (area, divio_type) tuples where documentation is missing
           """
           gaps = []
           for area in self.project_areas:
               for dtype in self.divio_types:
                   if self.cells.get((area, dtype)) is None:
                       gaps.append((area, dtype))
           return gaps

       def get_coverage_percentage(self) -> float:
           """Calculate percentage of cells with documentation.

           Returns:
               Coverage percentage (0.0 to 1.0)
           """
           total_cells = len(self.project_areas) * len(self.divio_types)
           if total_cells == 0:
               return 0.0

           filled_cells = sum(
               1 for path in self.cells.values()
               if path is not None
           )

           return filled_cells / total_cells

       def to_markdown_table(self) -> str:
           """Generate Markdown table representation of coverage.

           Returns:
               Markdown table showing coverage matrix
           """
           if not self.project_areas:
               return "No project areas identified."

           # Build table header
           header = "| Area | " + " | ".join(self.divio_types) + " |"
           separator = "|" + "|".join(["---"] * (len(self.divio_types) + 1)) + "|"

           # Build table rows
           rows = []
           for area in self.project_areas:
               cells = []
               for dtype in self.divio_types:
                   doc_path = self.cells.get((area, dtype))
                   if doc_path:
                       cells.append("✓")
                   else:
                       cells.append("✗")
               row = f"| {area} | " + " | ".join(cells) + " |"
               rows.append(row)

           # Combine
           table_lines = [header, separator] + rows

           # Add coverage percentage
           coverage_pct = self.get_coverage_percentage() * 100
           summary = f"\n**Coverage**: {len([c for c in self.cells.values() if c])}/{len(self.cells)} cells = {coverage_pct:.1f}%"

           return "\n".join(table_lines) + summary
   ```

**Files**: `src/specify_cli/gap_analysis.py` (modified)

**Parallel?**: No (other functions use this class)

**Notes**:
- Matrix structure: rows = areas, columns = Divio types
- Cells contain Path to doc file or None if missing
- Methods for querying coverage by area or type
- Markdown table generation for reports
- Coverage percentage calculation

**Quality Validation**:
- Can matrix handle empty areas list?
- Does get_gaps() return correct list?
- Does coverage percentage calculate correctly?
- Does markdown table render properly?

### Subtask T037 – Implement Gap Prioritization Logic

**Purpose**: Prioritize identified gaps by user impact (high/medium/low).

**Steps**:
1. In `gap_analysis.py`, define gap priority enum:
   ```python
   class GapPriority(Enum):
       """Priority levels for documentation gaps."""
       HIGH = "high"
       MEDIUM = "medium"
       LOW = "low"
   ```

2. Define gap dataclass:
   ```python
   @dataclass
   class DocumentationGap:
       """Represents a missing piece of documentation.

       Attributes:
           area: Project area missing documentation
           divio_type: Which Divio type is missing
           priority: How important this gap is (high/medium/low)
           reason: Why this gap matters
       """
       area: str
       divio_type: str
       priority: GapPriority
       reason: str

       def __repr__(self) -> str:
           return f"[{self.priority.value.upper()}] {self.area} → {self.divio_type}: {self.reason}"
   ```

3. Implement prioritization logic:
   ```python
   def prioritize_gaps(
       gaps: List[Tuple[str, str]],
       project_areas: List[str],
       existing_docs: Dict[Path, DivioType]
   ) -> List[DocumentationGap]:
       """Assign priorities to documentation gaps based on user impact.

       Prioritization rules (from research):
       - HIGH: Missing tutorials (blocks new users)
       - HIGH: Missing reference for core features (users can't find APIs)
       - MEDIUM: Missing how-tos for common tasks (users struggle with problems)
       - MEDIUM: Missing tutorials for advanced features
       - LOW: Missing explanations (nice-to-have, not blocking)

       Args:
           gaps: List of (area, divio_type) tuples with missing docs
           project_areas: All project areas
           existing_docs: Map of doc paths to classified types (for context)

       Returns:
           List of DocumentationGap objects with priorities assigned
       """
       prioritized = []

       for area, divio_type in gaps:
           # Determine if this is a core area (heuristic: alphabetically first areas are core)
           is_core_area = project_areas.index(area) < len(project_areas) // 2

           # Prioritization logic
           if divio_type == "tutorial":
               if is_core_area:
                   priority = GapPriority.HIGH
                   reason = "New users need tutorials to get started with core functionality"
               else:
                   priority = GapPriority.MEDIUM
                   reason = "Users need tutorials for advanced features"

           elif divio_type == "reference":
               if is_core_area:
                   priority = GapPriority.HIGH
                   reason = "Users need API reference to use core features"
               else:
                   priority = GapPriority.MEDIUM
                   reason = "API reference helps users discover all capabilities"

           elif divio_type == "how-to":
               priority = GapPriority.MEDIUM
               reason = "Users need how-tos to solve common problems and tasks"

           elif divio_type == "explanation":
               priority = GapPriority.LOW
               reason = "Explanations aid understanding but are not blocking"

           else:
               priority = GapPriority.LOW
               reason = "Unknown Divio type"

           prioritized.append(DocumentationGap(
               area=area,
               divio_type=divio_type,
               priority=priority,
               reason=reason
           ))

       # Sort by priority (high first)
       priority_order = {GapPriority.HIGH: 0, GapPriority.MEDIUM: 1, GapPriority.LOW: 2}
       prioritized.sort(key=lambda gap: priority_order[gap.priority])

       return prioritized
   ```

**Files**: `src/specify_cli/gap_analysis.py` (modified)

**Parallel?**: No (uses CoverageMatrix)

**Notes**:
- Prioritization based on user impact (from research)
- HIGH: Tutorials (new users) and Reference (API discovery)
- MEDIUM: How-Tos (problem solving)
- LOW: Explanations (understanding, not blocking)
- Core areas prioritized higher than peripheral areas
- Sorted by priority for reporting

**Quality Validation**:
- Does prioritization logic match spec requirements (FR-037)?
- Are priorities assigned correctly for each type?
- Is sorting working (high gaps first)?
- Are reasons clear and actionable?

### Subtask T038 – Implement Version Mismatch Detection

**Purpose**: Detect when API reference documentation is outdated by comparing code APIs vs documented APIs.

**Steps**:
1. In `gap_analysis.py`, implement code API extraction:
   ```python
   def extract_public_api_from_python(source_dir: Path) -> List[str]:
       """Extract public API elements from Python source.

       Finds:
       - Public functions (not starting with _)
       - Public classes (not starting with _)

       Args:
           source_dir: Directory containing Python source

       Returns:
           List of API element names (e.g., ["ClassName", "function_name"])
       """
       import ast

       api_elements = []

       for py_file in source_dir.rglob("*.py"):
           try:
               source = py_file.read_text()
               tree = ast.parse(source)

               for node in ast.walk(tree):
                   # Extract public functions
                   if isinstance(node, ast.FunctionDef):
                       if not node.name.startswith("_"):
                           api_elements.append(node.name)

                   # Extract public classes
                   elif isinstance(node, ast.ClassDef):
                       if not node.name.startswith("_"):
                           api_elements.append(node.name)

           except Exception:
               # Skip files that can't be parsed
               continue

       return sorted(set(api_elements))  # Unique, sorted
   ```

2. Implement documented API extraction:
   ```python
   def extract_documented_api_from_sphinx(docs_dir: Path) -> List[str]:
       """Extract documented API elements from Sphinx documentation.

       Parses generated Sphinx HTML or source .rst files for documented APIs.

       Args:
           docs_dir: Directory containing Sphinx documentation

       Returns:
           List of documented API element names
       """
       # Look for autodoc-generated files or .rst source
       documented = []

       # Check Sphinx build output
       build_dir = docs_dir / "_build" / "html"
       if build_dir.exists():
           # Parse HTML for documented classes/functions
           for html_file in build_dir.rglob("*.html"):
               content = html_file.read_text()
               # Simple heuristic: look for Sphinx autodoc class/function markers
               # Example: <dt class="sig sig-object py" id="ClassName">
               import re
               matches = re.findall(r'id="([a-zA-Z_][a-zA-Z0-9_]*)"', content)
               documented.extend(matches)

       return sorted(set(documented))  # Unique, sorted
   ```

3. Implement mismatch detection:
   ```python
   def detect_version_mismatch(
       code_dir: Path,
       docs_dir: Path,
       language: str = "python"
   ) -> List[str]:
       """Detect API elements in code that are missing from documentation.

       Args:
           code_dir: Directory containing source code
           docs_dir: Directory containing documentation
           language: Programming language (currently only "python" supported)

       Returns:
           List of API element names present in code but missing from docs
       """
       if language == "python":
           code_api = extract_public_api_from_python(code_dir)
           docs_api = extract_documented_api_from_sphinx(docs_dir)
       else:
           # Other languages not yet supported
           return []

       missing = set(code_api) - set(docs_api)
       return sorted(missing)
   ```

**Files**: `src/specify_cli/gap_analysis.py` (modified)

**Parallel?**: Yes (can develop alongside other gap analysis features)

**Notes**:
- Python-only initially (extensible to other languages)
- Uses AST parsing to extract public APIs from code
- Parses Sphinx HTML to extract documented APIs
- Returns list of APIs in code but not in docs
- Conservative (only public APIs, not private)

**Quality Validation**:
- Does AST parsing correctly identify public APIs?
- Does HTML parsing find documented APIs?
- Are private APIs correctly excluded?
- Is the mismatch list accurate?

### Subtask T039 – Generate gap-analysis.md Report

**Purpose**: Generate comprehensive gap analysis report with coverage matrix, prioritized gaps, and recommendations.

**Steps**:
1. In `gap_analysis.py`, define `GapAnalysis` dataclass:
   ```python
   @dataclass
   class GapAnalysis:
       """Complete gap analysis results.

       Attributes:
           project_name: Project being analyzed
           analysis_date: When analysis was performed
           framework: Detected documentation framework
           coverage_matrix: Coverage matrix showing existing docs
           gaps: Prioritized list of documentation gaps
           outdated: List of outdated documentation files
           existing: Map of existing doc files to their classified types
       """
       project_name: str
       analysis_date: datetime
       framework: DocFramework
       coverage_matrix: CoverageMatrix
       gaps: List[DocumentationGap]
       outdated: List[Tuple[Path, str]] = field(default_factory=list)  # (file, reason)
       existing: Dict[Path, Tuple[DivioType, float]] = field(default_factory=dict)  # (type, confidence)

       def to_markdown(self) -> str:
           """Generate Markdown report of gap analysis.

           Returns:
               Full gap analysis report as Markdown
           """
           lines = [
               f"# Gap Analysis: {self.project_name}",
               "",
               f"**Analysis Date**: {self.analysis_date.strftime('%Y-%m-%d %H:%M:%S')}",
               f"**Documentation Framework**: {self.framework.value}",
               f"**Coverage**: {self.coverage_matrix.get_coverage_percentage() * 100:.1f}%",
               "",
               "## Coverage Matrix",
               "",
               self.coverage_matrix.to_markdown_table(),
               "",
               "## Identified Gaps",
               "",
           ]

           if not self.gaps:
               lines.append("No gaps identified - documentation coverage is complete!")
           else:
               lines.append(f"Found {len(self.gaps)} documentation gaps:")
               lines.append("")

               # Group by priority
               high_gaps = [g for g in self.gaps if g.priority == GapPriority.HIGH]
               medium_gaps = [g for g in self.gaps if g.priority == GapPriority.MEDIUM]
               low_gaps = [g for g in self.gaps if g.priority == GapPriority.LOW]

               if high_gaps:
                   lines.append("### High Priority")
                   lines.append("")
                   for gap in high_gaps:
                       lines.append(f"- **{gap.area} → {gap.divio_type}**: {gap.reason}")
                   lines.append("")

               if medium_gaps:
                   lines.append("### Medium Priority")
                   lines.append("")
                   for gap in medium_gaps:
                       lines.append(f"- **{gap.area} → {gap.divio_type}**: {gap.reason}")
                   lines.append("")

               if low_gaps:
                   lines.append("### Low Priority")
                   lines.append("")
                   for gap in low_gaps:
                       lines.append(f"- **{gap.area} → {gap.divio_type}**: {gap.reason}")
                   lines.append("")

           # Existing documentation inventory
           lines.extend([
               "## Existing Documentation",
               "",
           ])

           if not self.existing:
               lines.append("No existing documentation found.")
           else:
               lines.append(f"Found {len(self.existing)} documentation files:")
               lines.append("")

               # Group by Divio type
               by_type: Dict[DivioType, List[Tuple[Path, float]]] = {}
               for path, (dtype, confidence) in self.existing.items():
                   if dtype not in by_type:
                       by_type[dtype] = []
                   by_type[dtype].append((path, confidence))

               for dtype in DivioType:
                   if dtype in by_type and dtype != DivioType.UNCLASSIFIED:
                       lines.append(f"### {dtype.value.title()}")
                       lines.append("")
                       for path, confidence in by_type[dtype]:
                           conf_str = f"({confidence * 100:.0f}% confidence)" if confidence < 1.0 else ""
                           lines.append(f"- {path} {conf_str}")
                       lines.append("")

               # Unclassified docs
               if DivioType.UNCLASSIFIED in by_type:
                   lines.append("### Unclassified")
                   lines.append("")
                   for path, _ in by_type[DivioType.UNCLASSIFIED]:
                       lines.append(f"- {path}")
                   lines.append("")

           # Outdated documentation
           if self.outdated:
               lines.extend([
                   "## Outdated Documentation",
                   "",
                   f"Found {len(self.outdated)} outdated documentation files:",
                   "",
               ])
               for path, reason in self.outdated:
                   lines.append(f"- **{path}**: {reason}")
               lines.append("")

           # Recommendations
           lines.extend([
               "## Recommendations",
               "",
           ])

           if high_gaps:
               lines.append("**Immediate action needed**:")
               for gap in high_gaps[:3]:  # Top 3 high-priority gaps
                   lines.append(f"1. Create {gap.divio_type} for {gap.area} - {gap.reason}")
               lines.append("")

           if medium_gaps:
               lines.append("**Should address soon**:")
               for gap in medium_gaps[:3]:  # Top 3 medium-priority gaps
                   lines.append(f"- Add {gap.divio_type} for {gap.area}")
               lines.append("")

           if low_gaps:
               lines.append(f"**Nice to have**: {len(low_gaps)} low-priority gaps (see above)")
               lines.append("")

           return "\n".join(lines)
   ```

2. Implement main analysis function:
   ```python
   def analyze_documentation_gaps(
       docs_dir: Path,
       project_root: Optional[Path] = None
   ) -> GapAnalysis:
       """Analyze documentation directory and identify gaps.

       Args:
           docs_dir: Directory containing documentation
           project_root: Project root (for code analysis), defaults to docs_dir.parent

       Returns:
           GapAnalysis object with coverage matrix, gaps, and recommendations
       """
       if project_root is None:
           project_root = docs_dir.parent

       project_name = project_root.name

       # Detect framework
       framework = detect_doc_framework(docs_dir)

       # Discover all markdown files
       doc_files = list(docs_dir.rglob("*.md"))

       # Classify each file
       classified = {}
       for doc_file in doc_files:
           try:
               content = doc_file.read_text()
               divio_type, confidence = classify_divio_type(content)
               classified[doc_file] = (divio_type, confidence)
           except Exception:
               # Skip files that can't be read/classified
               classified[doc_file] = (DivioType.UNCLASSIFIED, 0.0)

       # Detect project areas from directory structure or code
       project_areas = detect_project_areas(docs_dir, project_root)

       # Build coverage matrix
       coverage_matrix = build_coverage_matrix(classified, project_areas)

       # Identify gaps
       gap_tuples = coverage_matrix.get_gaps()

       # Prioritize gaps
       prioritized_gaps = prioritize_gaps(gap_tuples, project_areas, classified)

       # Detect version mismatches (Python only for now)
       outdated = []
       # TODO: Implement version mismatch detection (T038)

       return GapAnalysis(
           project_name=project_name,
           analysis_date=datetime.now(),
           framework=framework,
           coverage_matrix=coverage_matrix,
           gaps=prioritized_gaps,
           outdated=outdated,
           existing=classified
       )
   ```

3. Implement helper functions:
   ```python
   def detect_project_areas(docs_dir: Path, project_root: Path) -> List[str]:
       """Detect project areas from directory structure.

       Heuristics:
       - Check docs/ subdirectories (e.g., docs/tutorials/auth/ → "auth" area)
       - Check source code directories (e.g., src/api/ → "api" area)
       - Fallback: Single area named after project

       Args:
           docs_dir: Documentation directory
           project_root: Project root directory

       Returns:
           List of project area names
       """
       areas = set()

       # Check docs subdirectories
       for item in docs_dir.iterdir():
           if item.is_dir() and item.name not in ["_build", "_static", "_templates"]:
               areas.add(item.name)

       # Check source code directories
       src_dir = project_root / "src"
       if src_dir.exists():
           for item in src_dir.iterdir():
               if item.is_dir():
                   areas.add(item.name)

       # Fallback: project name as single area
       if not areas:
           areas.add(project_root.name)

       return sorted(areas)

   def build_coverage_matrix(
       classified: Dict[Path, Tuple[DivioType, float]],
       project_areas: List[str]
   ) -> CoverageMatrix:
       """Build coverage matrix from classified documents.

       Args:
           classified: Map of doc paths to (DivioType, confidence)
           project_areas: List of project area names

       Returns:
           CoverageMatrix showing coverage by area and type
       """
       matrix = CoverageMatrix(project_areas=project_areas)

       # Map each classified doc to (area, type) cell
       for doc_path, (divio_type, _) in classified.items():
           if divio_type == DivioType.UNCLASSIFIED:
               continue

           # Infer area from path (heuristic: directory name or filename prefix)
           area = infer_area_from_path(doc_path, project_areas)
           if area:
               matrix.cells[(area, divio_type.value)] = doc_path

       return matrix

   def infer_area_from_path(doc_path: Path, project_areas: List[str]) -> Optional[str]:
       """Infer which project area a doc file belongs to.

       Args:
           doc_path: Path to documentation file
           project_areas: Known project areas

       Returns:
           Area name if match found, None otherwise
       """
       # Check if any area name appears in path
       path_str = str(doc_path).lower()
       for area in project_areas:
           if area.lower() in path_str:
               return area

       # Fallback: use first area (generic)
       return project_areas[0] if project_areas else None
   ```

**Files**: `src/specify_cli/gap_analysis.py` (modified)

**Parallel?**: Yes (can develop alongside other analysis features)

**Notes**:
- Python AST parsing to extract public APIs
- HTML/RST parsing to extract documented APIs (simplified for MVP)
- Comparison to find APIs in code but not in docs
- Extensible to other languages (currently Python-focused)
- Conservative (only flags missing public APIs)

**Quality Validation**:
- Does AST parsing correctly identify public functions and classes?
- Are private APIs (starting with _) correctly excluded?
- Does comparison accurately find mismatches?
- Can it handle large codebases (performance)?

### Subtask T039 – Generate gap-analysis.md Report

**Purpose**: Create the main entry point function that runs gap analysis and writes the report file.

**Steps**:
1. In `gap_analysis.py`, implement report generation:
   ```python
   def generate_gap_analysis_report(
       docs_dir: Path,
       output_file: Path,
       project_root: Optional[Path] = None
   ) -> GapAnalysis:
       """Analyze documentation and generate gap analysis report.

       This is the main entry point for gap analysis. It:
       1. Detects documentation framework
       2. Classifies existing docs into Divio types
       3. Builds coverage matrix
       4. Identifies gaps
       5. Prioritizes gaps by impact
       6. Detects outdated documentation
       7. Generates comprehensive report

       Args:
           docs_dir: Directory containing documentation to analyze
           output_file: Path where gap-analysis.md should be written
           project_root: Project root directory (for code analysis)

       Returns:
           GapAnalysis object with full results

       Raises:
           FileNotFoundError: If docs_dir doesn't exist
       """
       if not docs_dir.exists():
           raise FileNotFoundError(f"Documentation directory not found: {docs_dir}")

       # Run analysis
       analysis = analyze_documentation_gaps(docs_dir, project_root)

       # Generate report
       report_content = analysis.to_markdown()

       # Write to file
       output_file.parent.mkdir(parents=True, exist_ok=True)
       output_file.write_text(report_content)

       return analysis
   ```

2. Add convenience function for integration with documentation mission:
   ```python
   def run_gap_analysis_for_feature(feature_dir: Path) -> GapAnalysis:
       """Run gap analysis for a documentation mission feature.

       Assumes standard paths:
       - Documentation: {project_root}/docs/
       - Output: {feature_dir}/gap-analysis.md

       Args:
           feature_dir: Feature directory (kitty-specs/###-doc-feature/)

       Returns:
           GapAnalysis results
       """
       # Find project root (walk up from feature_dir to find docs/)
       project_root = feature_dir
       while project_root != project_root.parent:
           if (project_root / "docs").exists():
               break
           project_root = project_root.parent

       docs_dir = project_root / "docs"
       output_file = feature_dir / "gap-analysis.md"

       return generate_gap_analysis_report(docs_dir, output_file, project_root)
   ```

**Files**: `src/specify_cli/gap_analysis.py` (modified)

**Parallel?**: No (ties together all gap analysis functions)

**Notes**:
- Main entry point for gap analysis
- Generates complete markdown report
- Writes to gap-analysis.md in feature directory
- Returns GapAnalysis object for programmatic use
- Convenience function for documentation mission integration

**Quality Validation**:
- Does report include all sections (coverage, gaps, existing, outdated, recommendations)?
- Is markdown formatting correct (tables, lists, headings)?
- Are gaps sorted by priority?
- Is report readable and actionable?

## Test Strategy

**Unit Tests** (to be implemented in WP09):

1. Test framework detection:
   ```python
   def test_detect_sphinx_framework(tmp_path):
       (tmp_path / "conf.py").write_text("")
       framework = detect_doc_framework(tmp_path)
       assert framework == DocFramework.SPHINX

   def test_detect_mkdocs_framework(tmp_path):
       (tmp_path / "mkdocs.yml").write_text("")
       framework = detect_doc_framework(tmp_path)
       assert framework == DocFramework.MKDOCS
   ```

2. Test Divio classification:
   ```python
   def test_classify_tutorial_from_frontmatter():
       content = """---
   type: tutorial
   ---
   # Some Tutorial
   """
       divio_type, confidence = classify_divio_type(content)
       assert divio_type == DivioType.TUTORIAL
       assert confidence == 1.0  # High confidence (explicit)

   def test_classify_tutorial_from_content():
       content = """# Getting Started

   ## Step 1: Install the software

   First, download...

   ## Step 2: Run it

   Now, let's run...
   """
       divio_type, confidence = classify_divio_type(content)
       assert divio_type == DivioType.TUTORIAL
       assert confidence == 0.7  # Medium confidence (heuristic)
   ```

3. Test coverage matrix:
   ```python
   def test_coverage_matrix_calculates_percentage():
       matrix = CoverageMatrix(
           project_areas=["auth", "api"],
           cells={
               ("auth", "tutorial"): Path("docs/tutorials/auth.md"),
               ("auth", "reference"): Path("docs/reference/auth.md"),
               ("api", "tutorial"): None,  # Gap
               ("api", "reference"): Path("docs/reference/api.md"),
           }
       )

       # 3 filled out of 8 total cells (2 areas × 4 types)
       # But we only populated 4 cells, so 3/4 = 75%
       coverage = matrix.get_coverage_percentage()
       assert coverage == 0.75  # 3 out of 4 defined cells
   ```

4. Test gap prioritization:
   ```python
   def test_prioritize_gaps():
       gaps = [
           ("auth", "tutorial"),
           ("auth", "explanation"),
           ("api", "reference"),
       ]
       project_areas = ["auth", "api"]

       prioritized = prioritize_gaps(gaps, project_areas, {})

       # auth tutorial should be HIGH (core area, new users)
       # api reference should be HIGH (core area, API discovery)
       # auth explanation should be LOW (understanding, not blocking)
       assert prioritized[0].priority == GapPriority.HIGH
       assert prioritized[0].divio_type in ["tutorial", "reference"]
   ```

5. Test gap analysis report generation:
   ```python
   def test_generate_gap_analysis_report(tmp_path):
       # Create test docs directory
       docs_dir = tmp_path / "docs"
       docs_dir.mkdir()
       (docs_dir / "tutorial.md").write_text("""---
   type: tutorial
   ---
   # Tutorial
   """)

       output_file = tmp_path / "gap-analysis.md"

       analysis = generate_gap_analysis_report(docs_dir, output_file)

       assert output_file.exists()
       content = output_file.read_text()
       assert "# Gap Analysis:" in content
       assert "Coverage Matrix" in content
       assert "Identified Gaps" in content
   ```

**Manual Validation**:

1. Test on spec-kitty's own documentation:
   ```bash
   # Run gap analysis on spec-kitty
   python -c "
   from pathlib import Path
   from specify_cli.gap_analysis import generate_gap_analysis_report

   docs_dir = Path('docs')
   if docs_dir.exists():
       analysis = generate_gap_analysis_report(
           docs_dir,
           Path('gap-analysis-test.md')
       )
       print(f'Framework: {analysis.framework.value}')
       print(f'Coverage: {analysis.coverage_matrix.get_coverage_percentage() * 100:.1f}%')
       print(f'Gaps: {len(analysis.gaps)}')
       print('Report written to gap-analysis-test.md')
   else:
       print('No docs/ directory found')
   "
   ```

2. Review generated report:
   - Is coverage matrix accurate?
   - Are gaps identified correctly?
   - Are priorities reasonable?
   - Are recommendations actionable?

3. Test classification accuracy:
   - Create test docs with explicit frontmatter → should classify with 100% confidence
   - Create test docs without frontmatter → should classify with heuristics
   - Create ambiguous docs → should classify as unclassified (conservative)

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| False positives (wrong gaps) | High - confuses users | Conservative heuristics, only flag obvious gaps, allow user override |
| False negatives (missed gaps) | Medium - gaps not filled | Err on side of caution, comprehensive heuristics |
| Misclassification of existing docs | Medium - wrong coverage matrix | Frontmatter takes precedence over heuristics, high confidence threshold |
| Performance on large doc sets | Medium - slow analysis | Limit to .md files only, use efficient parsing |
| Custom doc structures not recognized | Medium - analysis incomplete | Support common frameworks, allow manual classification via frontmatter |
| Area detection inaccurate | Low - coverage matrix structure wrong | Conservative area inference, single-area fallback |

## Definition of Done Checklist

- [ ] `src/specify_cli/gap_analysis.py` module created
- [ ] `DocFramework` enum defined (Sphinx, MkDocs, Docusaurus, Jekyll, Hugo, plain Markdown, unknown)
- [ ] `DivioType` enum defined (tutorial, how-to, reference, explanation, unclassified)
- [ ] `GapPriority` enum defined (high, medium, low)
- [ ] `DocumentationGap` dataclass defined
- [ ] `GapAnalysis` dataclass defined
- [ ] `CoverageMatrix` class implemented:
  - [ ] Stores project areas and Divio types
  - [ ] Maps (area, type) to doc file paths
  - [ ] Calculates coverage percentage
  - [ ] Generates markdown table representation
  - [ ] Returns list of gaps
- [ ] Framework detection implemented:
  - [ ] Detects Sphinx (conf.py)
  - [ ] Detects MkDocs (mkdocs.yml)
  - [ ] Detects Docusaurus (docusaurus.config.js)
  - [ ] Detects Jekyll (_config.yml)
  - [ ] Detects Hugo (config.toml)
  - [ ] Detects plain Markdown (.md files, no framework)
- [ ] Divio classification implemented:
  - [ ] Parses YAML frontmatter for explicit type
  - [ ] Applies content heuristics as fallback
  - [ ] Returns confidence score
  - [ ] Handles unclassifiable docs gracefully
- [ ] Gap prioritization implemented:
  - [ ] Assigns HIGH to missing tutorials and core reference
  - [ ] Assigns MEDIUM to missing how-tos
  - [ ] Assigns LOW to missing explanations
  - [ ] Sorts by priority
- [ ] Version mismatch detection implemented (Python):
  - [ ] Extracts public APIs from Python code
  - [ ] Extracts documented APIs from Sphinx docs
  - [ ] Identifies APIs in code but not in docs
- [ ] `generate_gap_analysis_report()` function implemented:
  - [ ] Runs full analysis
  - [ ] Generates markdown report
  - [ ] Writes to gap-analysis.md
  - [ ] Returns GapAnalysis object
- [ ] Helper functions implemented (detect_project_areas, build_coverage_matrix)
- [ ] Manual testing completed on real documentation
- [ ] Gap analysis report is readable and actionable
- [ ] `tasks.md` in feature directory updated with WP06 status

## Review Guidance

**Key Acceptance Checkpoints**:

1. **Framework Detection**: Correctly identifies common frameworks
2. **Classification Accuracy**: Frontmatter + heuristics work correctly
3. **Coverage Matrix**: Accurately shows what exists vs what's missing
4. **Gap Prioritization**: Priorities match user impact (tutorials/reference high)
5. **Report Quality**: Generated markdown is readable and actionable
6. **Conservative Approach**: Avoids false positives (flags only obvious gaps)

**Validation Commands**:
```bash
# Test module imports
python -c "from specify_cli.gap_analysis import GapAnalysis, CoverageMatrix, detect_doc_framework, classify_divio_type, analyze_documentation_gaps; print('✓ All imports successful')"

# Test framework detection
python -c "
from pathlib import Path
from specify_cli.gap_analysis import detect_doc_framework, DocFramework

# Test with spec-kitty's own docs (if they exist)
docs = Path('docs')
if docs.exists():
    framework = detect_doc_framework(docs)
    print(f'Detected framework: {framework.value}')
"

# Test classification
python -c "
from specify_cli.gap_analysis import classify_divio_type, DivioType

content = '''---
type: tutorial
---
# Test
'''

divio_type, confidence = classify_divio_type(content)
print(f'Classified as: {divio_type.value} (confidence: {confidence})')
assert divio_type == DivioType.TUTORIAL
assert confidence == 1.0
print('✓ Classification works')
"

# Test end-to-end analysis (on spec-kitty itself)
python -c "
from pathlib import Path
from specify_cli.gap_analysis import generate_gap_analysis_report

docs = Path('docs')
if docs.exists():
    analysis = generate_gap_analysis_report(
        docs,
        Path('/tmp/gap-analysis-test.md')
    )
    print(f'Analysis complete:')
    print(f'  Framework: {analysis.framework.value}')
    print(f'  Existing docs: {len(analysis.existing)}')
    print(f'  Coverage: {analysis.coverage_matrix.get_coverage_percentage() * 100:.1f}%')
    print(f'  Gaps: {len(analysis.gaps)}')
    print(f'  Report: /tmp/gap-analysis-test.md')
"
```

**Review Focus Areas**:
- Framework detection is accurate
- Classification logic is sound (frontmatter over heuristics)
- Heuristics correctly identify Divio types (test with sample docs)
- Coverage matrix correctly shows gaps
- Gap priorities are appropriate (tutorials/reference high)
- Report is well-formatted and actionable
- Code handles edge cases (empty docs, unclassifiable docs, missing frontmatter)

## Activity Log

- 2026-01-12T17:18:56Z – system – lane=planned – Prompt created.
- 2026-01-13T09:17:04Z – test-agent2 – lane=doing – Moved to doing
- 2026-01-13T10:47:27Z – test-agent2 – lane=planned – Reset to planned (was test activity)
- 2026-01-13T10:48:50Z – claude – shell_pid=59241 – lane=doing – Started implementation via workflow command
- 2026-01-13T10:55:43Z – claude – shell_pid=59241 – lane=for_review – Gap analysis module implementation complete. All 7 subtasks (T033-T039) completed: framework detection, Divio classification, coverage matrix, gap prioritization, version mismatch detection, and report generation. Validated with end-to-end tests on spec-kitty docs (22 files analyzed, 41.7% coverage, 7 gaps identified).
