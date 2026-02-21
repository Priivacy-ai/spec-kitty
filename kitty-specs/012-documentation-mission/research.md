# Phase 0 Research: Documentation Mission

**Date**: 2026-01-12
**Feature**: 012-documentation-mission
**Researchers**: Specification phase (Write the Docs, Divio research), Planning phase (generator integration)

## Executive Summary

This research establishes the technical foundation for implementing a documentation mission in spec-kitty. Key findings include:

1. **Doc generators** (JSDoc, Sphinx, rustdoc) are all invocable from Python via subprocess with well-defined configuration patterns
2. **Divio documentation system** provides clear separation of concerns for 4 doc types with distinct characteristics
3. **Gap analysis** can leverage file structure patterns and frontmatter metadata to classify existing docs
4. **Mission phases** should map documentation workflow (discover → audit → design → generate → validate → publish) distinct from software-dev phases
5. **Write the Docs principles** emphasize docs-as-code, accessibility, and bias-free language - all implementable via template guidance

## Research Task 1: JSDoc Integration Patterns

### Decision

Use subprocess to invoke JSDoc CLI, configure via jsdoc.json file, support both Markdown and HTML output.

### Findings

**Invocation from Python**:

```python
import subprocess
from pathlib import Path

def invoke_jsdoc(source_dir: Path, config_path: Path, output_dir: Path) -> subprocess.CompletedProcess:
    """Invoke JSDoc on JavaScript/TypeScript source code."""
    cmd = ["npx", "jsdoc", "-c", str(config_path), "-d", str(output_dir), str(source_dir)]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)
```

**Configuration structure** (jsdoc.json):

```json
{
  "source": {
    "include": ["src/"],
    "includePattern": ".+\\.js(doc|x)?$",
    "excludePattern": "(^|\\/|\\\\)_"
  },
  "opts": {
    "destination": "./docs/api",
    "recurse": true,
    "readme": "README.md",
    "template": "node_modules/docdash"
  },
  "plugins": ["plugins/markdown"],
  "templates": {
    "cleverLinks": false,
    "monospaceLinks": false
  }
}
```

**Output formats**:

- **HTML** (default): Generates browsable site with inter-linked pages
- **Markdown**: Requires plugin (jsdoc-to-markdown) for Markdown output

**Common issues**:

- JSDoc requires Node.js/npm installed - detection needed
- Config file path resolution can be tricky - use absolute paths
- TypeScript requires additional setup (typedoc recommended over jsdoc for TS)

**Alternative for TypeScript**: TypeDoc

```python
def invoke_typedoc(source_dir: Path, output_dir: Path) -> subprocess.CompletedProcess:
    """Invoke TypeDoc for TypeScript projects."""
    cmd = ["npx", "typedoc", "--out", str(output_dir), str(source_dir)]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)
```

### Rationale

JSDoc is the de facto standard for JavaScript documentation, widely known and adopted. Using subprocess provides clean separation and doesn't require Python bindings. Configuration via JSON file allows templating and customization.

### Alternatives Considered

- **Inline Python API**: No stable Python bindings exist for JSDoc
- **Custom parser**: Too complex, JSDoc handles edge cases well
- **TypeScript-only**: Many projects use plain JavaScript

## Research Task 2: Sphinx Integration Patterns

### Decision

Generate Sphinx conf.py from Python template, use autodoc + napoleon extensions, default to Read the Docs theme, support both HTML and Markdown (via myst-parser).

### Findings

**Invocation from Python**:

```python
import subprocess
from pathlib import Path

def invoke_sphinx_quickstart(docs_dir: Path, project_name: str, author: str) -> subprocess.CompletedProcess:
    """Initialize Sphinx documentation structure."""
    cmd = [
        "sphinx-quickstart",
        "-q",  # Quiet mode
        "-p", project_name,
        "-a", author,
        "--ext-autodoc",
        "--ext-napoleon",
        "--makefile",
        "--no-batchfile",
        str(docs_dir)
    ]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)

def invoke_sphinx_build(source_dir: Path, build_dir: Path, builder: str = "html") -> subprocess.CompletedProcess:
    """Build Sphinx documentation."""
    cmd = ["sphinx-build", "-b", builder, str(source_dir), str(build_dir)]
    return subprocess.run(cmd, capture_output=True, text=True, check=False)
```

**Generated conf.py structure**:

```python
# Sphinx configuration template
project = '{project_name}'
author = '{author}'
extensions = [
    'sphinx.ext.autodoc',      # Auto-generate docs from docstrings
    'sphinx.ext.napoleon',     # Support Google/NumPy docstring styles
    'sphinx.ext.viewcode',     # Add links to source code
    'sphinx.ext.intersphinx',  # Link to other project docs
    'myst_parser',             # Markdown support (optional)
]

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# HTML output options
html_theme = 'sphinx_rtd_theme'  # Read the Docs theme
html_static_path = ['_static']

# Autodoc options
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}
```

**Extension: autodoc**

- Automatically generates documentation from Python docstrings
- Supports multiple docstring formats via napoleon extension
- Configuration: autodoc_default_options controls what gets documented

**Extension: napoleon**

- Converts Google/NumPy docstring format to reStructuredText
- More readable than raw reST in source code
- Widely adopted in Python community

**Theme selection**:

- **sphinx_rtd_theme**: Read the Docs theme (default recommendation)
- **alabaster**: Sphinx default theme (simple, clean)
- **pydata-sphinx-theme**: Modern theme for scientific Python projects

**Output formats**:

- **HTML** (default): Full-featured with search, navigation
- **Markdown**: Via MyST parser + markdown builder
- **PDF**: Via LaTeX builder (requires LaTeX installation)

**Common issues**:

- Sphinx requires Python package installed (`pip install sphinx`)
- Path configuration for autodoc (`sys.path.insert` in conf.py)
- Theme packages must be installed separately (`pip install sphinx-rtd-theme`)

### Rationale

Sphinx is the standard documentation tool for Python projects, used by Python itself and major projects like Django, Flask, NumPy. Autodoc + napoleon provide seamless docstring extraction. Read the Docs theme is familiar and widely deployed.

### Alternatives Considered

- **MkDocs**: Simpler but less powerful, no autodoc equivalent
- **Pydoc**: Built-in but limited, no theming
- **pdoc**: Lightweight but lacks Sphinx ecosystem

## Research Task 3: rustdoc Integration Patterns

### Decision

Invoke `cargo doc` for Rust projects, parse HTML output for integration, use `--document-private-items` flag for complete coverage.

### Findings

**Invocation from Python**:

```python
import subprocess
from pathlib import Path

def invoke_rustdoc(project_dir: Path, target_dir: Path) -> subprocess.CompletedProcess:
    """Generate documentation for Rust project."""
    cmd = [
        "cargo", "doc",
        "--no-deps",              # Don't document dependencies
        "--document-private-items",  # Include private items
        "--target-dir", str(target_dir)
    ]
    return subprocess.run(cmd, cwd=str(project_dir), capture_output=True, text=True, check=False)
```

**Output structure**:

```
target/doc/
├── index.html                    # Landing page
├── <crate_name>/
│   ├── index.html               # Crate documentation
│   ├── struct.MyStruct.html     # Per-struct pages
│   ├── fn.my_function.html      # Per-function pages
│   └── ...
├── src/
│   └── <crate_name>/            # Source code viewer
└── search-index.js              # Search functionality
```

**Configuration via Cargo.toml**:

```toml
[package.metadata.docs.rs]
all-features = true
rustdoc-args = ["--document-private-items"]

[package]
# Documentation link for crates.io
documentation = "https://docs.rs/my-crate"
```

**JSON output** (experimental):

```bash
cargo +nightly doc --output-format json
```

Produces machine-readable JSON describing all public items.

**Common issues**:

- Requires Rust toolchain installed (cargo, rustc)
- Large output for big projects (>100MB for complex crates)
- Private items excluded by default (use --document-private-items)
- Cross-crate links require `--no-deps` or careful configuration

### Rationale

rustdoc is the official Rust documentation tool, integrated with Cargo. All Rust developers are familiar with it. HTML output is high-quality and searchable. No configuration file needed for basic use.

### Alternatives Considered

- **Custom Rust parser**: Extremely complex, rustdoc does this correctly
- **Third-party tools**: No widely-adopted alternatives exist
- **docs.rs**: Online service, not suitable for local/private docs

## Research Task 4: Gap Analysis Algorithms

### Decision

Multi-strategy approach: (1) File structure analysis, (2) Frontmatter classification, (3) Content heuristics, (4) User overrides via metadata.

### Findings

**Strategy 1: File structure analysis**

Detect documentation frameworks by characteristic files:

```python
def detect_doc_framework(docs_dir: Path) -> Optional[str]:
    """Detect documentation framework from file structure."""
    if (docs_dir / "conf.py").exists():
        return "sphinx"
    elif (docs_dir / "mkdocs.yml").exists():
        return "mkdocs"
    elif (docs_dir / "docusaurus.config.js").exists():
        return "docusaurus"
    elif (docs_dir / "_config.yml").exists():
        return "jekyll"
    else:
        return None
```

**Strategy 2: Frontmatter classification**

Parse YAML frontmatter to identify Divio type:

```yaml
---
type: tutorial
audience: beginners
goal: "Learn how to set up authentication"
---
```

Classification logic:

```python
def classify_divio_type(content: str) -> Optional[str]:
    """Classify document into Divio type via frontmatter."""
    frontmatter = parse_yaml_frontmatter(content)
    if "type" in frontmatter:
        return frontmatter["type"]  # Explicit classification

    # Heuristic fallback
    if has_step_by_step_structure(content):
        return "tutorial"
    elif is_problem_solution_format(content):
        return "how-to"
    elif has_technical_reference_markers(content):
        return "reference"
    elif is_explanatory_discussion(content):
        return "explanation"

    return None  # Unclassified
```

**Strategy 3: Content heuristics**

Analyze content patterns to infer Divio type:

- **Tutorial markers**: "Step 1", "First, install", "Now, let's", "You should see"
- **How-to markers**: "How to", "To do X", "Follow these steps", "Problem: ... Solution:"
- **Reference markers**: "Parameters:", "Returns:", "Class:", "Function:", API tables
- **Explanation markers**: "Why", "Background", "Concepts", "Architecture", "Design decisions"

**Strategy 4: Coverage matrix**

Build matrix of documentation coverage:

```python
@dataclass
class CoverageMatrix:
    project_areas: List[str]  # e.g., ["auth", "api", "cli", "storage"]
    divio_types: List[str]    # ["tutorial", "how-to", "reference", "explanation"]
    cells: Dict[Tuple[str, str], Optional[Path]]  # (area, type) -> doc file path

    def get_gaps(self) -> List[Tuple[str, str]]:
        """Return list of (area, type) tuples with missing documentation."""
        return [(area, dtype) for (area, dtype), path in self.cells.items() if path is None]
```

**Version mismatch detection**:

```python
def detect_version_mismatch(code_dir: Path, docs_dir: Path) -> List[str]:
    """Detect API elements in code missing from docs."""
    code_api = extract_public_api(code_dir)  # Parse code for public functions/classes
    docs_api = extract_documented_api(docs_dir)  # Parse docs for documented APIs

    missing = set(code_api) - set(docs_api)
    return sorted(missing)
```

### Rationale

Multi-strategy approach balances accuracy and flexibility. Explicit frontmatter allows users to override heuristics. File structure detection supports existing documentation. Content heuristics provide fallback when metadata is missing.

### Alternatives Considered

- **AI classification**: Too slow, requires external API
- **Manual tagging only**: Too much user burden
- **Regex-only heuristics**: Too fragile, many false positives
- **No gap analysis**: Defeats purpose of iterative documentation missions

## Research Task 5: Mission Phase Design

### Decision

Custom phases for documentation mission: discover → audit → design → generate → validate → publish

### Findings

**Phase mapping comparison**:

| Software-Dev | Research | Documentation | Rationale |
|--------------|----------|---------------|-----------|
| research | question | discover | Understand docs needed |
| design | methodology | audit | Assess existing docs |
| implement | gather | design | Plan doc structure |
| test | analyze | generate | Create doc content |
| review | synthesize | validate | Quality check |
| - | publish | publish | Release docs |

**Phase descriptions**:

1. **Discover** (analogous to research/question)
   - Understand project scope and documentation needs
   - Identify target audiences
   - Select relevant Divio types
   - Detect programming languages for generators

2. **Audit** (unique to documentation)
   - Scan existing documentation
   - Classify docs into Divio types
   - Build coverage matrix
   - Identify gaps and outdated content

3. **Design** (analogous to design/methodology)
   - Plan documentation structure
   - Configure generators
   - Select templates
   - Define content outline

4. **Generate** (analogous to implement/gather)
   - Create documentation files from templates
   - Run doc generators for reference material
   - Populate templates with placeholders

5. **Validate** (analogous to test/analyze)
   - Check Divio type adherence
   - Verify accessibility guidelines
   - Validate generator output
   - Review for completeness

6. **Publish** (analogous to review/publish)
   - Prepare for hosting platform
   - Generate final builds
   - Create deployment artifacts
   - Capture optional release.md (publish handoff, deployment notes)

**Workflow configuration**:

```yaml
workflow:
  phases:
    - name: "discover"
      description: "Understand documentation needs and scope"
    - name: "audit"
      description: "Analyze existing documentation and identify gaps"
    - name: "design"
      description: "Plan documentation structure and templates"
    - name: "generate"
      description: "Create documentation from templates and generators"
    - name: "validate"
      description: "Review documentation quality and completeness"
    - name: "publish"
      description: "Prepare documentation for hosting and deployment"
```

### Rationale

Custom phases provide clarity for documentation-specific workflow. "Audit" phase is unique requirement for gap analysis. "Generate" is more accurate than "implement" for documentation. "Validate" emphasizes quality over testing code.

### Alternatives Considered

- **Reuse software-dev phases**: Confusing nomenclature (what does "implement" mean for docs?)
- **Minimal phases** (just specify/plan/implement): Loses documentation-specific nuances
- **Research phases**: Doesn't capture auditing and gap-filling iterations

## Cross-Cutting Findings

### Write the Docs Best Practices

**Docs as Code** implementation:

- Documentation lives in version control (Git)
- Changes reviewed via pull requests
- CI/CD for documentation builds
- Documentation versioned alongside code

**Accessibility implementation**:

- Template prompts remind authors to use proper heading hierarchy
- Alt text placeholders for images
- Plain language guidance
- Screen reader considerations

**Bias-free language implementation**:

- Template examples use diverse names and scenarios
- Guidance to avoid unnecessarily gendered language
- Inclusive pronoun usage examples
- Cultural sensitivity reminders

### Testing Strategy

**Template validation tests**:

```python
def test_divio_template_structure():
    """Verify Divio templates have required sections."""
    for divio_type in ["tutorial", "how-to", "reference", "explanation"]:
        template = load_template(f"divio/{divio_type}-template.md")
        assert has_frontmatter(template)
        assert has_required_sections(template, divio_type)
```

**Generator integration tests**:

```python
@pytest.mark.integration
def test_sphinx_generation(tmp_path):
    """Test Sphinx doc generation end-to-end."""
    project_dir = create_sample_python_project(tmp_path)
    result = invoke_sphinx_build(project_dir, tmp_path / "docs")
    assert result.returncode == 0
    assert (tmp_path / "docs" / "index.html").exists()
```

**Gap analysis tests**:

```python
def test_gap_detection():
    """Test gap analysis identifies missing Divio types."""
    docs_dir = create_docs_with_only_tutorials(tmp_path)
    gaps = analyze_gaps(docs_dir)
    assert ("how-to" in gaps)
    assert ("reference" in gaps)
    assert ("explanation" in gaps)
    assert ("tutorial" not in gaps)
```

## Recommendations

1. **Start with templates**: Implement Divio templates and mission config first (WP01-03)
2. **Add generators incrementally**: Sphinx first (Python-focused), then JSDoc, then rustdoc
3. **Conservative gap analysis**: Flag only obvious gaps to avoid false positives
4. **Extensive testing**: Mission config, templates, and generators all need comprehensive tests
5. **Migration testing**: Verify software-dev and research missions unaffected
6. **Dogfooding**: Use documentation mission on spec-kitty itself as validation

## Open Questions

**Q1**: Should generator invocation be blocking or async?
**A**: Blocking for MVP. Generators typically complete in < 10 seconds. Async can be future enhancement.

**Q2**: How to handle generator failures gracefully?
**A**: Log error, offer to create manual reference templates instead, continue with other Divio types.

**Q3**: Should gap analysis be automatic or opt-in?
**A**: Opt-in via discovery question during specify phase. Some users may want fresh docs, not gap-filling.

**Q4**: Support for documentation versioning (multiple versions simultaneously)?
**A**: Out of scope for MVP (per spec.md). Add to backlog as future enhancement.

## References

- Write the Docs Guide: <https://www.writethedocs.org/guide/>
- Divio Documentation System: <https://docs.divio.com/documentation-system/>
- Sphinx Documentation: <https://www.sphinx-doc.org/>
- JSDoc Reference: <https://jsdoc.app/>
- rustdoc Book: <https://doc.rust-lang.org/rustdoc/>
- Read the Docs: <https://docs.readthedocs.io/>
- MyST Parser (Markdown for Sphinx): <https://myst-parser.readthedocs.io/>
- TypeDoc (TypeScript docs): <https://typedoc.org/>
