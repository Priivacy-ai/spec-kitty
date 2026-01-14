# Quickstart: Documentation Mission Implementation

**Feature**: 012-documentation-mission
**For**: Contributors implementing this feature
**Last Updated**: 2026-01-12

## 🎯 What Are We Building?

A new "documentation" mission type for spec-kitty that helps teams create and maintain software documentation following:
- **Write the Docs** best practices (docs as code, accessibility, bias-free language)
- **Divio's 4 documentation types**: tutorial, how-to, reference, explanation
- **Auto-generated docs** from JSDoc (JS/TS), Sphinx (Python), rustdoc (Rust)

## 🏗️ Architecture at a Glance

```
src/specify_cli/missions/
└── documentation/               # NEW mission directory
    ├── mission.yaml            # Mission config (phases, artifacts, validation)
    ├── templates/              # Templates for docs
    │   ├── spec-template.md
    │   ├── plan-template.md
    │   └── divio/              # 4 Divio type templates
    │       ├── tutorial-template.md
    │       ├── howto-template.md
    │       ├── reference-template.md
    │       └── explanation-template.md
    └── command-templates/       # Command instructions
        ├── specify.md
        ├── plan.md
        └── implement.md
```

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- spec-kitty development environment set up
- Familiarity with existing missions (software-dev, research)

### Quick Commands

```bash
# Run tests for documentation mission
pytest tests/specify_cli/missions/test_documentation_mission.py -v

# Load documentation mission config
from specify_cli.mission import get_mission_by_name
doc_mission = get_mission_by_name("documentation")

# Test template loading
template = doc_mission.get_template("divio/tutorial-template.md")
```

## 📋 Work Package Overview

| WP | Name | Description | Dependencies |
|----|------|-------------|--------------|
| WP01 | Mission Infrastructure | Create mission.yaml and directory structure | None |
| WP02 | Core Templates | Create spec/plan/tasks templates | WP01 |
| WP03 | Divio Templates | Create 4 Divio type templates | WP01 |
| WP04 | Generator Abstraction | Implement DocGenerator protocol | WP01 |
| WP05 | Gap Analysis | Implement doc auditing | WP04 |
| WP06 | State Management | Implement iteration state in meta.json | WP01 |
| WP07 | Command Templates | Create specify/plan/implement instructions | WP01 |
| WP08 | Migration | Write migration to install docs mission | WP01-07 |
| WP09 | Testing | Unit tests for mission, templates, generators | WP01-07 |
| WP10 | Documentation | Update spec-kitty docs | WP01-09 |

**Suggested order**: WP01 → WP02, WP03, WP07 (parallel) → WP04 → WP05, WP06 (parallel) → WP08 → WP09 → WP10

## 🔑 Key Concepts

### Divio Documentation Types

1. **Tutorial** - Learning-oriented
   - Step-by-step, hands-on
   - For beginners
   - Example: "Building Your First API"

2. **How-To Guide** - Goal-oriented
   - Practical problem-solving
   - For experienced users
   - Example: "How to Enable LDAP Authentication"

3. **Reference** - Information-oriented
   - Technical specifications
   - API docs, parameters, classes
   - Example: "API Endpoint Reference"

4. **Explanation** - Understanding-oriented
   - Concepts and architecture
   - Design decisions
   - Example: "Why We Use Event Sourcing"

### Mission Workflow Phases

```
discover → audit → design → generate → validate → publish
```

- **discover**: Understand docs needed, select Divio types
- **audit**: Gap analysis of existing docs (if iterating)
- **design**: Plan doc structure, configure generators
- **generate**: Create docs from templates + generators
- **validate**: Quality checks (Divio adherence, accessibility)
- **publish**: Prepare for hosting and handoff (release.md when in scope)

### Iteration Modes

- **initial**: First-time documentation (no existing docs)
- **gap_filling**: Iterative improvement (add missing types)
- **feature_specific**: Document a specific new feature

## 🧪 Testing Strategy

### Test Pyramid

```
╔══════════════════════════╗
║   E2E Tests (10%)        ║  Full mission workflow
║   - Initial mission      ║
║   - Gap-filling          ║
╠══════════════════════════╣
║   Integration (30%)      ║  Generator invocation
║   - JSDoc integration    ║  Template rendering
║   - Sphinx integration   ║  Gap analysis
║   - rustdoc integration  ║
╠══════════════════════════╣
║   Unit Tests (60%)       ║  Mission loading
║   - Config validation    ║  Template validation
║   - Template structure   ║  Entity models
║   - Protocol compliance  ║
╚══════════════════════════╝
```

### Key Test Files

```
tests/specify_cli/missions/
├── test_documentation_mission.py      # Mission config loading
├── test_documentation_templates.py    # Template validation
├── test_doc_generators.py             # Generator protocol tests
├── test_gap_analysis.py               # Coverage matrix, gap detection
└── test_documentation_integration.py  # End-to-end workflows
```

## 📝 Code Patterns

### Adding a New Divio Template

```python
# 1. Create template file
# Location: src/specify_cli/missions/documentation/templates/divio/tutorial-template.md

---
type: tutorial
audience: "{target_audience}"
purpose: "Learn how to {goal}"
created: "{date}"
---

# Tutorial: {title}

## What You'll Build

[Describe the end result]

## Prerequisites

- [List requirements]

## Step 1: {action}

[Detailed instructions...]

## Step 2: {next_action}

[Continue...]

## What You Learned

[Summary]

## Next Steps

[Where to go from here]
```

```python
# 2. Add template test
def test_tutorial_template_structure():
    """Verify tutorial template has required sections."""
    mission = get_mission_by_name("documentation")
    template = mission.get_template("divio/tutorial-template.md")

    content = template.read_text()

    # Check frontmatter
    assert has_yaml_frontmatter(content)
    assert get_frontmatter_field(content, "type") == "tutorial"

    # Check required sections
    assert "## What You'll Build" in content
    assert "## Prerequisites" in content
    assert "## What You Learned" in content
```

### Implementing a Doc Generator

```python
# 1. Define generator class
from typing import Protocol
from pathlib import Path
from dataclasses import dataclass

@dataclass
class SphinxGenerator:
    """Sphinx documentation generator for Python projects."""

    name = "sphinx"
    languages = ["python"]

    def detect(self, project_root: Path) -> bool:
        """Detect if project uses Python."""
        return (
            (project_root / "setup.py").exists()
            or (project_root / "pyproject.toml").exists()
            or any(project_root.rglob("*.py"))
        )

    def configure(self, output_dir: Path, options: Dict[str, Any]) -> Path:
        """Generate Sphinx conf.py from template."""
        template = load_template("generators/sphinx-conf.py.template")
        config_content = template.format(**options)

        config_file = output_dir / "conf.py"
        config_file.write_text(config_content)
        return config_file

    def generate(self, source_dir: Path, output_dir: Path) -> GeneratorResult:
        """Run sphinx-build to generate documentation."""
        cmd = ["sphinx-build", "-b", "html", str(source_dir), str(output_dir)]
        result = subprocess.run(cmd, capture_output=True, text=True)

        return GeneratorResult(
            success=(result.returncode == 0),
            output_dir=output_dir,
            errors=result.stderr.splitlines() if result.returncode != 0 else [],
            warnings=extract_warnings(result.stdout),
            generated_files=list(output_dir.rglob("*.html"))
        )
```

```python
# 2. Add generator test
@pytest.mark.integration
def test_sphinx_generator_integration(tmp_path):
    """Test Sphinx generator end-to-end."""
    # Create sample Python project
    project_dir = tmp_path / "sample_project"
    project_dir.mkdir()
    (project_dir / "sample.py").write_text('''
    def hello(name: str) -> str:
        """Greet someone by name.

        Args:
            name: Person to greet

        Returns:
            Greeting message
        """
        return f"Hello, {name}!"
    ''')

    # Run generator
    generator = SphinxGenerator()
    assert generator.detect(project_dir)

    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    config_path = generator.configure(docs_dir, {
        "project_name": "Sample",
        "author": "Test Author"
    })

    result = generator.generate(project_dir, docs_dir)

    assert result.success
    assert (docs_dir / "index.html").exists()
    assert len(result.generated_files) > 0
```

### Gap Analysis Implementation

```python
def analyze_gaps(docs_dir: Path) -> GapAnalysis:
    """Analyze documentation and identify gaps."""
    # 1. Detect framework
    framework = detect_doc_framework(docs_dir)

    # 2. Discover all markdown files
    doc_files = list(docs_dir.rglob("*.md"))

    # 3. Classify each file into Divio type
    classified = {}
    for doc_file in doc_files:
        content = doc_file.read_text()
        divio_type = classify_divio_type(content)
        classified[doc_file] = divio_type

    # 4. Build coverage matrix
    project_areas = detect_project_areas(docs_dir.parent)  # Infer from code structure
    coverage = CoverageMatrix(
        project_areas=project_areas,
        divio_types=["tutorial", "how-to", "reference", "explanation"],
        cells=build_coverage_cells(classified, project_areas)
    )

    # 5. Identify gaps
    gaps = coverage.get_gaps()
    prioritized_gaps = prioritize_gaps(gaps, project_areas)

    return GapAnalysis(
        project_name=docs_dir.parent.name,
        analysis_date=datetime.now(),
        framework=framework,
        coverage_matrix=coverage,
        gaps=prioritized_gaps,
        existing=classified
    )
```

## 🐛 Common Issues & Solutions

### Issue: Mission config not loading

**Symptom**: `MissionNotFoundError: Mission 'documentation' not found`

**Solution**:
```bash
# Check mission directory exists
ls -la src/specify_cli/missions/documentation/

# Check mission.yaml is valid YAML
python -c "import yaml; yaml.safe_load(open('src/specify_cli/missions/documentation/mission.yaml'))"

# Verify mission appears in list
from specify_cli.mission import list_available_missions
print(list_available_missions())
```

### Issue: Template not found

**Symptom**: `FileNotFoundError: Template not found: divio/tutorial-template.md`

**Solution**:
```bash
# Check template exists
ls -la src/specify_cli/missions/documentation/templates/divio/

# Verify template is loadable
from specify_cli.mission import get_mission_by_name
mission = get_mission_by_name("documentation")
print(mission.list_templates())
```

### Issue: Generator subprocess fails

**Symptom**: `GeneratorResult(success=False, errors=['sphinx-build: command not found'])`

**Solution**:
```bash
# Check generator tool is installed
which sphinx-build  # For Sphinx
which npx          # For JSDoc
which cargo        # For rustdoc

# Install if missing
pip install sphinx sphinx-rtd-theme  # Sphinx
npm install -g jsdoc                 # JSDoc
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh  # Rust
```

## 📚 Key Files Reference

### Mission Configuration

**File**: `src/specify_cli/missions/documentation/mission.yaml`
**Purpose**: Defines workflow phases, artifacts, validation rules
**Schema**: See [data-model.md](data-model.md#1-mission-configuration)

### Divio Templates

**Files**: `src/specify_cli/missions/documentation/templates/divio/*.md`
**Purpose**: Pre-structured templates for 4 Divio types
**Schema**: See [data-model.md](data-model.md#2-divio-documentation-type)

### Generator Protocol

**File**: Define in `src/specify_cli/doc_generators.py` (new module)
**Purpose**: Abstraction for JSDoc, Sphinx, rustdoc
**Schema**: See [data-model.md](data-model.md#4-documentation-generator)

### Meta.json Extension

**File**: `kitty-specs/{feature}/meta.json`
**Purpose**: Store iteration state between documentation missions
**Schema**: See [data-model.md](data-model.md#7-iteration-mode)

## 🔗 Related Documentation

- **Specification**: [spec.md](spec.md) - Full feature requirements
- **Implementation Plan**: [plan.md](plan.md) - Technical design
- **Research**: [research.md](research.md) - Generator integration patterns
- **Data Model**: [data-model.md](data-model.md) - Entity definitions
- **Release Guidance**: [release.md](release.md) - Optional publish and handoff notes

## 💡 Pro Tips

1. **Start with mission.yaml**: Get the config right first, everything else follows
2. **Test templates early**: Validate structure before writing content
3. **Mock generators**: Use subprocess.run mocks for fast tests
4. **Use existing missions as reference**: software-dev and research are good templates
5. **Dogfood it**: Use documentation mission on spec-kitty itself for validation

## 🤝 Contributing

When implementing work packages:
1. Create branch: `012-documentation-mission-WP{NN}`
2. Write tests first (TDD)
3. Implement feature
4. Validate against spec requirements
5. Update this quickstart if patterns change

## ❓ Questions?

- See [plan.md](plan.md) for detailed technical design
- See [research.md](research.md) for generator integration details
- See [data-model.md](data-model.md) for entity schemas
- Check existing missions (`src/specify_cli/missions/software-dev/`) for patterns

---

**Happy building! 🚀**
