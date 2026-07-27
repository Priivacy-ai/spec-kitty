# Data Model: Documentation Mission

**Feature**: 012-documentation-mission
**Date**: 2026-01-12
**Purpose**: Define entities and relationships for documentation mission functionality

## Overview

This data model describes the entities, attributes, and relationships for the documentation mission feature. Unlike traditional database-backed applications, spec-kitty uses filesystem-based storage with YAML, JSON, and Markdown files. This model defines the conceptual entities and their representations in files.

## Entity Definitions

### 1. Mission Configuration

**Purpose**: Defines the documentation mission's workflow, artifacts, and behavior.

**File Location**: `src/specify_cli/missions/documentation/mission.yaml`

**Schema**:
```yaml
name: string                    # "Documentation Kitty"
description: string             # Mission description
version: string                 # Semver (e.g., "1.0.0")
domain: enum                    # "other" (or extend to "documentation")

workflow:
  phases:                       # List of workflow phases
    - name: string              # Phase identifier (e.g., "discover")
      description: string       # Phase description

artifacts:
  required:                     # List of required artifact filenames
    - string
  optional:                     # List of optional artifact filenames
    - string

paths:                          # Path conventions
  workspace: string             # Default: "docs/"
  deliverables: string          # Default: "docs/output/"
  documentation: string         # Default: "docs/"

validation:
  checks:                       # List of validation check names
    - string
  custom_validators: boolean    # Whether to use validators.py

mcp_tools:
  required:                     # Required MCP tools
    - string
  recommended:                  # Recommended MCP tools
    - string
  optional:                     # Optional MCP tools
    - string

agent_context: string           # Multi-line agent instructions

task_metadata:
  required:                     # Required task metadata fields
    - string
  optional:                     # Optional task metadata fields
    - string

commands:                       # Command-specific configurations
  specify:
    prompt: string
  plan:
    prompt: string
  # ... (other commands)
```

**Relationships**:
- Has many: Divio Documentation Templates
- Has many: Generator Configuration Templates
- Has many: Command Templates

**Validation Rules**:
- Version must match semver pattern: `^\d+\.\d+\.\d+$`
- Workflow must have at least 1 phase
- Domain must be valid enum value

---

### 2. Divio Documentation Type

**Purpose**: Represents one of the four documentation types from the Divio system.

**Enumeration Values**:
- `tutorial` - Learning-oriented, hands-on lessons
- `how-to` - Goal-oriented problem-solving guides
- `reference` - Technical descriptions and API docs
- `explanation` - Understanding-oriented discussions

**Template Location**: `src/specify_cli/missions/documentation/templates/divio/{type}-template.md`

**Template Structure**:
```markdown
---
type: string                    # Divio type (tutorial/how-to/reference/explanation)
audience: string                # Target audience description
purpose: string                 # What this doc accomplishes
created: date                   # Creation date
---

# [Title]

[Content sections specific to Divio type]
```

**Characteristics** (from research):

| Type | Purpose | Audience | Structure | Tone |
|------|---------|----------|-----------|------|
| tutorial | Teaching through doing | Beginners | Step-by-step sequence | Encouraging, explicit |
| how-to | Solving specific problems | Experienced users | Goal-oriented steps | Practical, concise |
| reference | Technical specification | All users | Structured by code | Factual, complete |
| explanation | Understanding concepts | Curious users | Thematic discussion | Informative, insightful |

**Validation Rules**:
- Must have frontmatter with `type` field
- Type must be one of 4 valid values
- Must include sections appropriate to type (defined per type)

---

### 3. Documentation Template

**Purpose**: Pre-structured file with placeholders and guidance for authoring documentation.

**File Location**: `src/specify_cli/missions/documentation/templates/*.md`

**Types**:
- **Standard templates**: spec-template.md, plan-template.md, tasks-template.md, task-prompt-template.md
- **Divio templates**: Located in `divio/` subdirectory (see Divio Documentation Type)
- **Generator config templates**: Located in `generators/` subdirectory

**Attributes**:
```yaml
filename: string                # Template file name
content: string                 # Template content (Markdown with placeholders)
placeholders:                   # List of placeholder tokens
  - string                      # e.g., "{project_name}", "{author}"
sections:                       # Required sections
  - string                      # Section heading names
guidance:                       # Inline guidance for authors
  - location: string            # Where guidance appears
    text: string                # Guidance content
```

**Placeholder Conventions**:
- `{project_name}` - Project name
- `{author}` - Author name
- `{target_audience}` - Intended readers
- `{divio_type}` - Documentation type
- `[CONTENT PLACEHOLDER: ...]` - Content to be filled by author

**Relationships**:
- Belongs to: Mission Configuration
- Can be instantiated as: Documentation Artifact (in feature directories)

---

### 4. Documentation Generator

**Purpose**: Language-specific tool that automatically creates reference documentation from code.

**Types**: JSDoc (JS/TS), Sphinx (Python), rustdoc (Rust)

**Protocol Definition**:
```python
from typing import Protocol, Dict, Any
from pathlib import Path
from dataclasses import dataclass

@dataclass
class GeneratorResult:
    success: bool
    output_dir: Path
    errors: List[str]
    warnings: List[str]
    generated_files: List[Path]

class DocGenerator(Protocol):
    name: str                   # Generator identifier
    languages: List[str]        # Supported languages

    def detect(self, project_root: Path) -> bool:
        """Detect if this generator is applicable to the project."""
        ...

    def configure(self, output_dir: Path, options: Dict[str, Any]) -> Path:
        """Generate configuration file for this generator."""
        ...

    def generate(self, source_dir: Path, output_dir: Path) -> GeneratorResult:
        """Run generator to produce documentation."""
        ...
```

**Concrete Implementations**:

#### JSDocGenerator
```python
@dataclass
class JSDocGenerator:
    name = "jsdoc"
    languages = ["javascript", "typescript"]

    config_template: Path       # Path to jsdoc.json.template
    requires_npm: bool = True   # Requires Node.js/npm

    # Implementation of detect(), configure(), generate()
```

#### SphinxGenerator
```python
@dataclass
class SphinxGenerator:
    name = "sphinx"
    languages = ["python"]

    config_template: Path       # Path to conf.py.template
    extensions: List[str]       # ["autodoc", "napoleon", "viewcode"]
    theme: str = "sphinx_rtd_theme"

    # Implementation of detect(), configure(), generate()
```

#### RustdocGenerator
```python
@dataclass
class RustdocGenerator:
    name = "rustdoc"
    languages = ["rust"]

    requires_cargo: bool = True # Requires Rust toolchain

    # Implementation of detect(), configure(), generate()
```

**Relationships**:
- Belongs to: Documentation Mission
- Configured by: Generator Configuration

**Validation Rules**:
- Must implement all protocol methods
- Must check for required tools (npm, sphinx, cargo) before generate()
- Must handle subprocess failures gracefully

---

### 5. Gap Analysis

**Purpose**: Assessment of existing documentation identifying present/missing Divio types and outdated content.

**File Location**: `kitty-specs/{feature}/gap-analysis.md` (generated during audit phase)

**Attributes**:
```yaml
project_name: string            # Project being analyzed
analysis_date: datetime         # When analysis ran
framework: Optional[string]     # Detected doc framework (sphinx/mkdocs/etc)

coverage_matrix:                # Coverage by area and type
  project_areas:                # List of project components
    - string
  divio_coverage:               # Map of (area, type) → doc file
    - area: string
      tutorial: Optional[Path]
      how_to: Optional[Path]
      reference: Optional[Path]
      explanation: Optional[Path]

gaps:                           # Identified documentation gaps
  - area: string                # Project area missing docs
    divio_type: string          # Missing Divio type
    priority: enum              # high/medium/low
    reason: string              # Why this gap matters

outdated:                       # Outdated documentation detected
  - file: Path                  # Doc file path
    reason: string              # Why marked outdated
    code_elements: List[string] # Missing API elements

existing:                       # Existing docs inventory
  - file: Path                  # Doc file path
    divio_type: Optional[string] # Classified type
    confidence: float           # Classification confidence (0-1)
    last_modified: datetime     # File modification time
```

**Methods** (conceptual):
```python
def analyze_gaps(docs_dir: Path) -> GapAnalysis:
    """Analyze documentation directory and return gap analysis."""
    ...

def get_gaps_by_priority(self) -> Dict[str, List[Gap]]:
    """Return gaps grouped by priority."""
    ...

def get_coverage_percentage(self) -> float:
    """Calculate percentage of (area, type) cells with docs."""
    ...
```

**Relationships**:
- Created during: Audit phase of documentation mission
- Used by: Plan phase to prioritize documentation work
- References: Existing documentation files

**Validation Rules**:
- All gaps must have valid divio_type (one of 4 types)
- Priority must be high/medium/low
- Confidence score must be between 0 and 1

---

### 6. Generator Configuration

**Purpose**: Settings for automated doc tools including output format, theme, extensions.

**File Locations** (examples):
- Sphinx: `docs/conf.py` (generated from template)
- JSDoc: `jsdoc.json` (generated from template)
- rustdoc: `Cargo.toml` metadata section

**Sphinx Configuration Schema**:
```python
project: string                 # Project name
author: string                  # Author name
extensions: List[string]        # Sphinx extensions to enable
html_theme: string              # Theme name
templates_path: List[string]    # Template directories
exclude_patterns: List[string]  # Patterns to exclude

# Extension-specific config
napoleon_google_docstring: bool
napoleon_numpy_docstring: bool
autodoc_default_options: Dict[str, Any]
```

**JSDoc Configuration Schema**:
```json
{
  "source": {
    "include": [string],        // Source directories
    "includePattern": string,   // Regex for included files
    "excludePattern": string    // Regex for excluded files
  },
  "opts": {
    "destination": string,      // Output directory
    "recurse": boolean,         // Recurse subdirectories
    "template": string          // Theme/template to use
  },
  "plugins": [string]           // JSDoc plugins
}
```

**rustdoc Configuration** (in Cargo.toml):
```toml
[package.metadata.docs.rs]
all-features: boolean           # Document all features
rustdoc-args: List[string]      # Additional rustdoc arguments

[package]
documentation: string           # Documentation URL
```

**Relationships**:
- Created by: Documentation Generator during configure()
- Used by: Documentation Generator during generate()
- Belongs to: Feature (stored in feature's docs directory)

---

### 7. Iteration Mode

**Purpose**: Approach for current documentation mission run determining discovery questions and workflow focus.

**Enumeration Values**:
- `initial` - First-time documentation for a project (no existing docs)
- `gap_filling` - Iterative improvement of existing documentation
- `feature_specific` - Documenting a specific new feature/module

**Storage**: Persisted in feature's `meta.json`:
```json
{
  "feature_number": "012",
  "slug": "documentation-mission",
  "friendly_name": "Documentation Mission",
  "mission": "documentation",
  "created_at": "2026-01-12T00:00:00Z",

  "documentation_state": {
    "iteration_mode": "initial",         // or "gap_filling" or "feature_specific"
    "divio_types_selected": [            // Which Divio types user chose
      "tutorial",
      "reference"
    ],
    "generators_configured": [           // Which generators were set up
      {
        "name": "sphinx",
        "language": "python",
        "config_path": "docs/conf.py"
      }
    ],
    "last_audit_date": "2026-01-12T00:00:00Z",  // When gap analysis last ran
    "coverage_percentage": 0.5           // Overall doc coverage (0-1)
  }
}
```

**Behavior by Mode**:

| Mode | Discovery Questions | Audit Phase | Template Focus |
|------|---------------------|-------------|----------------|
| initial | Target audience, all Divio types | Skipped | All selected types from scratch |
| gap_filling | Docs to improve, priority gaps | Run gap analysis | Templates for missing types only |
| feature_specific | Which feature, which aspects | Audit feature docs only | Targeted templates for feature |

**State Transitions**:
```
initial → gap_filling (after first iteration completes)
gap_filling → gap_filling (subsequent iterations)
feature_specific → gap_filling (after feature docs added)
```

**Relationships**:
- Determines: Specify phase questions
- Influences: Audit phase execution
- Affects: Template generation strategy

---

### 8. Documentation Coverage Matrix

**Purpose**: Structured view of project documentation showing which Divio types exist for which project areas.

**Structure**:
```python
from typing import Optional, Dict, Tuple
from pathlib import Path

@dataclass
class CoverageMatrix:
    project_areas: List[str]    # Component names (e.g., ["auth", "api", "cli"])
    divio_types: List[str]      # Always 4 types: tutorial, how-to, reference, explanation

    # Maps (area, type) to doc file path (None if missing)
    cells: Dict[Tuple[str, str], Optional[Path]]

    def get_coverage_for_area(self, area: str) -> Dict[str, Optional[Path]]:
        """Get all Divio type coverage for one project area."""
        return {dtype: self.cells.get((area, dtype)) for dtype in self.divio_types}

    def get_coverage_for_type(self, divio_type: str) -> Dict[str, Optional[Path]]:
        """Get all project area coverage for one Divio type."""
        return {area: self.cells.get((area, divio_type)) for area in self.project_areas}

    def get_gaps(self) -> List[Tuple[str, str]]:
        """Return list of (area, type) tuples with missing documentation."""
        return [(area, dtype) for (area, dtype), path in self.cells.items() if path is None]

    def get_coverage_percentage(self) -> float:
        """Calculate percentage of cells with documentation."""
        total_cells = len(self.project_areas) * len(self.divio_types)
        filled_cells = sum(1 for path in self.cells.values() if path is not None)
        return filled_cells / total_cells if total_cells > 0 else 0.0

    def to_markdown_table(self) -> str:
        """Generate Markdown table representation of coverage."""
        ...
```

**Example**:
```
Project: spec-kitty

Coverage Matrix:
| Area     | Tutorial | How-To | Reference | Explanation |
|----------|----------|--------|-----------|-------------|
| CLI      | ✓        | ✓      | ✓         | ✗           |
| Missions | ✓        | ✗      | ✓         | ✓           |
| Templates| ✗        | ✓      | ✓         | ✗           |

Coverage: 7/12 cells = 58.3%

Gaps (prioritized):
1. [HIGH] CLI → Explanation (users confused about mission system design)
2. [MEDIUM] Missions → How-To (common tasks not documented)
3. [MEDIUM] Templates → Tutorial (new contributors struggle with templates)
4. [LOW] Templates → Explanation (template philosophy not critical)
```

**Relationships**:
- Created by: Gap Analysis during audit phase
- Used in: Planning phase to prioritize work packages
- Displayed in: Gap analysis reports

---

## Entity Relationships Diagram

```
Mission Configuration (mission.yaml)
├── has many → Divio Documentation Templates
│   ├── tutorial-template.md
│   ├── howto-template.md
│   ├── reference-template.md
│   └── explanation-template.md
├── has many → Standard Templates
│   ├── spec-template.md
│   ├── plan-template.md
│   └── tasks-template.md
└── has many → Command Templates
    ├── specify.md
    ├── plan.md
    └── implement.md

Feature (meta.json)
├── has one → Iteration Mode (stored in documentation_state)
├── may have one → Gap Analysis (gap-analysis.md)
│   └── contains → Coverage Matrix
├── may have many → Generator Configurations
│   ├── conf.py (Sphinx)
│   ├── jsdoc.json (JSDoc)
│   └── Cargo.toml metadata (rustdoc)
└── has many → Documentation Artifacts
    └── generated from → Divio Templates

Documentation Generator (Python Protocol)
├── implements → JSDocGenerator
├── implements → SphinxGenerator
└── implements → RustdocGenerator
```

## Data Flow

### Initial Documentation Mission Flow

1. **Specify Phase**:
   - User selects `iteration_mode = "initial"`
   - User selects Divio types to include (e.g., tutorial, reference)
   - System detects languages and suggests generators
   - Stores selections in `meta.json → documentation_state`

2. **Plan Phase** (current command):
   - Reads feature spec and meta.json
   - Loads documentation mission config
   - Creates plan with generator setup tasks
   - Skips gap analysis (no existing docs)

3. **Implement Phase** (future):
   - Copies Divio templates for selected types
   - Generates generator configs from templates
   - Runs generators to create initial reference docs
   - Populates templates with project-specific placeholders

4. **Review Phase** (future):
   - Validates Divio type adherence
   - Checks accessibility guidelines
   - Verifies generator output quality

### Gap-Filling Iteration Flow

1. **Specify Phase**:
   - User selects `iteration_mode = "gap_filling"`
   - System runs gap analysis (audit phase)
   - Generates Coverage Matrix
   - User reviews gaps and selects which to address

2. **Plan Phase**:
   - Prioritizes gaps by user impact
   - Plans work packages for missing Divio types
   - May include generator re-runs if code updated

3. **Implement Phase**:
   - Creates only templates for missing types
   - Updates existing docs as needed
   - Regenerates outdated reference docs

## File Locations Summary

| Entity | File Location | Format |
|--------|---------------|--------|
| Mission Configuration | `src/specify_cli/missions/documentation/mission.yaml` | YAML |
| Divio Templates | `src/specify_cli/missions/documentation/templates/divio/*.md` | Markdown |
| Standard Templates | `src/specify_cli/missions/documentation/templates/*.md` | Markdown |
| Command Templates | `src/specify_cli/missions/documentation/command-templates/*.md` | Markdown |
| Generator Configs (templates) | `src/specify_cli/missions/documentation/templates/generators/*` | Various |
| Feature Metadata | `kitty-specs/{feature}/meta.json` | JSON |
| Gap Analysis | `kitty-specs/{feature}/gap-analysis.md` | Markdown |
| Release Guidance | `kitty-specs/{feature}/release.md` | Markdown |
| Documentation Artifacts | `kitty-specs/{feature}/docs/*` or project `docs/` | Markdown/HTML |

## Validation Rules Summary

1. **Mission Configuration**: Must have valid semver version, at least 1 workflow phase, valid domain enum
2. **Divio Templates**: Must have frontmatter with type field, type must be valid (tutorial/how-to/reference/explanation)
3. **Gap Analysis**: All gaps must have valid divio_type, priority must be high/medium/low, confidence 0-1
4. **Generator Results**: Must indicate success/failure, must list generated files, must capture errors/warnings
5. **Iteration Mode**: Must be one of initial/gap_filling/feature_specific
6. **Coverage Matrix**: Percentage must be 0-1, all referenced files must exist

## Testing Implications

Based on this data model, the following test categories are needed:

1. **Entity Loading Tests**: Verify Mission, templates, and configs load correctly
2. **Validation Tests**: Test all validation rules for each entity
3. **Relationship Tests**: Verify entity relationships (mission → templates, etc.)
4. **State Persistence Tests**: Test meta.json read/write for iteration state
5. **Gap Analysis Tests**: Test coverage matrix calculation and gap detection
6. **Generator Protocol Tests**: Verify all generators implement protocol correctly
7. **Data Flow Tests**: Test full workflows (initial mission, gap-filling iteration)

---

**Data model complete. Ready for implementation in work packages.**
