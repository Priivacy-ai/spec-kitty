---
description: Produce a documentation mission plan with audit/design guidance and generator setup.
---

# Command Template: /spec-kitty.plan (Documentation Mission)

**Phases**: Audit (if gap-filling), Design
**Purpose**: Plan documentation structure, configure generators, prioritize gaps, design content outline.

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Location Pre-flight Check

Verify you are in the main repository (not a worktree). Planning happens in main for ALL missions.

```bash
git branch --show-current  # Should show "main"
```

**Note**: Planning in main is standard for all spec-kitty missions. Implementation happens in per-WP worktrees.

---

## Planning Interrogation

For documentation missions, planning interrogation is lighter than software-dev:
- **Simple projects** (single language, initial docs): 1-2 questions about structure preferences
- **Complex projects** (multiple languages, existing docs): 2-3 questions about integration approach

**Key Planning Questions**:

**Q1: Documentation Framework**
"Do you have a preferred documentation framework/generator?"
- Sphinx (Python ecosystem standard)
- MkDocs (Markdown-focused, simple)
- Docusaurus (React-based, modern)
- Jekyll (GitHub Pages native)
- None (plain Markdown)

**Why it matters**: Determines build system, theming options, hosting compatibility.

**Q2: Generator Integration Approach** (if multiple languages detected)
"How should API reference for different languages be organized?"
- Unified (all APIs in one reference section)
- Separated (language-specific reference sections)
- Parallel (side-by-side comparison)

**Why it matters**: Affects directory structure, navigation design.

---

## Outline

1. **Setup**: Run `spec-kitty agent feature setup-plan --json` to initialize plan.md

2. **Load context**: Read spec.md, meta.json (especially `documentation_state`)

3. **Phase 0: Research** (if gap-filling mode)

   ### Gap Analysis (gap-filling mode only)

   **Objective**: Audit existing documentation and identify gaps.

   **Steps**:
   1. Scan existing `docs/` directory (or wherever docs live)
   2. Detect documentation framework (Sphinx, MkDocs, Jekyll, etc.)
   3. For each markdown file:
      - Parse frontmatter for `type` field
      - Apply content heuristics if no explicit type
      - Classify as tutorial/how-to/reference/explanation or "unclassified"
   4. Build coverage matrix:
      - Rows: Project areas/features
      - Columns: Divio types (tutorial, how-to, reference, explanation)
      - Cells: Documentation files (or empty if missing)
   5. Calculate coverage percentage
   6. Prioritize gaps:
      - **High**: Missing tutorials (blocks new users)
      - **High**: Missing reference for public APIs
      - **Medium**: Missing how-tos for common tasks
      - **Low**: Missing explanations (nice-to-have)
   7. Generate `gap-analysis.md` with:
      - Current documentation inventory
      - Coverage matrix (markdown table)
      - Prioritized gap list
      - Recommendations

   **Output**: `gap-analysis.md` file in feature directory

   ---

   ### Generator Research (all modes)

   **Objective**: Research generator configuration options for detected languages.

   **For Each Detected Language**:

   **JavaScript/TypeScript → JSDoc/TypeDoc**:
   - Check if JSDoc installed: `npx jsdoc --version`
   - Research config options: output format (HTML/Markdown), template (docdash, clean-jsdoc)
   - Determine source directories to document
   - Plan integration with manual docs

   **Python → Sphinx**:
   - Check if Sphinx installed: `sphinx-build --version`
   - Research extensions: autodoc (API from docstrings), napoleon (Google/NumPy style), viewcode (source links)
   - Research theme: sphinx_rtd_theme (Read the Docs), alabaster (default), pydata-sphinx-theme
   - Plan autodoc configuration (which modules to document)
   - Plan integration with manual docs

   **Rust → rustdoc**:
   - Check if Cargo installed: `cargo doc --help`
   - Research rustdoc options: --no-deps, --document-private-items
   - Plan Cargo.toml metadata configuration
   - Plan integration with manual docs (rustdoc outputs HTML, may need linking)

   **Output**: research.md with generator findings and decisions

4. **Phase 1: Design**

   ### Documentation Structure Design

   **Directory Layout**:
   Design docs/ structure following Divio organization:

   ```
   docs/
   ├── index.md                    # Landing page
   ├── tutorials/                  # Learning-oriented
   │   ├── getting-started.md
   │   └── advanced-usage.md
   ├── how-to/                     # Problem-solving
   │   ├── authentication.md
   │   ├── deployment.md
   │   └── troubleshooting.md
   ├── reference/                  # Technical specs
   │   ├── api/                    # Generated API docs
   │   │   ├── python/             # Sphinx output
   │   │   ├── javascript/         # JSDoc output
   │   │   └── rust/               # rustdoc output
   │   ├── cli.md                  # Manual CLI reference
   │   └── configuration.md        # Manual config reference
   └── explanation/                # Understanding
       ├── architecture.md
       ├── concepts.md
       └── design-decisions.md
   ```

   **Adapt based on**:
   - Selected Divio types (only create directories for selected types)
   - Project size (small projects may flatten structure)
   - Existing docs (extend existing structure if gap-filling)

   ---

   ### Generator Configuration Design

   **For Each Generator**:

   **Sphinx (Python)**:
   ```python
   # docs/conf.py
   project = '{project_name}'
   author = '{author}'
   extensions = [
       'sphinx.ext.autodoc',      # Generate from docstrings
       'sphinx.ext.napoleon',     # Google/NumPy docstring support
       'sphinx.ext.viewcode',     # Link to source
       'sphinx.ext.intersphinx',  # Link to other projects
   ]
   html_theme = 'sphinx_rtd_theme'
   autodoc_default_options = {
       'members': True,
       'undoc-members': False,
       'show-inheritance': True,
   }
   ```

   **JSDoc (JavaScript)**:
   ```json
   {
     "source": {
       "include": ["src/"],
       "includePattern": ".+\\.js$"
     },
     "opts": {
       "destination": "docs/reference/api/javascript",
       "template": "node_modules/docdash",
       "recurse": true
     }
   }
   ```

   **rustdoc (Rust)**:
   ```toml
   [package.metadata.docs.rs]
   all-features = true
   rustdoc-args = ["--document-private-items"]
   ```

   **Output**: Generator config snippets in plan.md, templates ready for implementation

   ---

   ### Data Model

   Generate `data-model.md` with entities:
   - **Documentation Mission**: Iteration state, selected types, configured generators
   - **Divio Documentation Type**: Tutorial, How-To, Reference, Explanation with characteristics
   - **Documentation Generator**: JSDoc, Sphinx, rustdoc configurations
   - **Gap Analysis** (if applicable): Coverage matrix, prioritized gaps

   ---

   ### Work Breakdown

   Outline high-level work packages (detailed in `/spec-kitty.tasks`):

   **For Initial Mode**:
   1. WP01: Structure Setup - Create docs/ dirs, configure generators
   2. WP02: Tutorial Creation - Write selected tutorials
   3. WP03: How-To Creation - Write selected how-tos
   4. WP04: Reference Generation - Generate API docs, write manual reference
   5. WP05: Explanation Creation - Write selected explanations
   6. WP06: Quality Validation - Accessibility checks, link validation, build

   **For Gap-Filling Mode**:
   1. WP01: Gap Analysis Review - Review audit results with user
   2. WP02: High-Priority Gaps - Fill critical missing docs
   3. WP03: Medium-Priority Gaps - Fill important missing docs
   4. WP04: Generator Updates - Regenerate outdated API docs
   5. WP05: Quality Validation - Validate new and updated docs

   **For Feature-Specific Mode**:
   1. WP01: Feature Documentation - Document the specific feature across Divio types
   2. WP02: Integration - Integrate with existing documentation
   3. WP03: Quality Validation - Validate feature docs

   ---

   ### Quickstart

   Generate `quickstart.md` with:
   - How to build documentation locally
   - How to add new documentation (which template to use)
   - How to regenerate API reference
   - How to validate documentation quality

5. **Report completion**:
   - Plan file path
   - Artifacts generated (research.md, data-model.md, gap-analysis.md, quickstart.md, release.md when publish is in scope)
   - Next command: `/spec-kitty.tasks`

---

## Key Guidelines

**For Agents**:
- Run gap analysis only for gap-filling mode
- Auto-detect documentation framework from existing docs
- Configure generators based on detected languages
- Design structure following Divio principles
- Prioritize gaps by user impact (tutorials/reference high, explanations low)
- Plan includes both auto-generated and manual documentation

**For Users**:
- Planning designs documentation structure, doesn't write content yet
- Generator configs enable automated API reference
- Gap analysis (if iterating) shows what needs attention
- Work breakdown will be detailed in `/spec-kitty.tasks`
