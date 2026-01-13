---
work_package_id: "WP05"
subtasks:
  - "T025"
  - "T026"
  - "T027"
  - "T028"
  - "T029"
  - "T030"
  - "T031"
  - "T032"
title: "Documentation Generator Protocol"
phase: "Phase 1 - Core Logic"
lane: "doing"
assignee: "test"
agent: "claude"
shell_pid: "65572"
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

# Work Package Prompt: WP05 – Documentation Generator Protocol

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
1. Ensure WP01 is complete
2. Mission directory exists and mission.yaml is valid
3. No dependency on WP02-04 (templates); generators are independent

---

## Objectives & Success Criteria

**Goal**: Implement a Python protocol defining the interface for documentation generators, plus three concrete implementations (JSDoc, Sphinx, rustdoc) that detect projects, generate configuration files, and invoke generator tools via subprocess.

**Success Criteria**:
- `src/specify_cli/doc_generators.py` module created with protocol and implementations
- `DocGenerator` protocol defined with `detect()`, `configure()`, `generate()` methods
- `GeneratorResult` dataclass captures success/failure, errors, warnings, generated files
- `JSDocGenerator` class implements protocol for JavaScript/TypeScript projects
- `SphinxGenerator` class implements protocol for Python projects
- `RustdocGenerator` class implements protocol for Rust projects
- Each generator correctly detects appropriate projects
- Each generator generates valid configuration files
- Each generator invokes subprocess correctly (with error handling)
- Graceful degradation when generator tools are not installed
- Generator config templates created for Sphinx and JSDoc
- All generators tested with sample projects

## Context & Constraints

**Prerequisites**:
- Python 3.11+ with subprocess module
- Understanding of JSDoc, Sphinx, rustdoc from research

**Reference Documents**:
- [research.md](../research.md) - Generator integration patterns (lines 87-312)
  - JSDoc integration (lines 87-137)
  - Sphinx integration (lines 139-189)
  - rustdoc integration (lines 191-240)
- [data-model.md](../data-model.md) - Documentation Generator entity (lines 244-328)
- [plan.md](../plan.md) - Generator abstraction design (lines 213-221)
- [spec.md](../spec.md) - Generator requirements (FR-018 to FR-026, lines 125-134)

**Constraints**:
- Generators invoke external tools (npx, sphinx-build, cargo) via subprocess
- Must handle missing tools gracefully (detect and fail with helpful message)
- Must capture stdout/stderr for error reporting
- Must be cross-platform (macOS, Linux, Windows paths)
- Configuration templates must be parametrizable (project name, paths, etc.)

**Generator Characteristics** (from research):

| Generator | Language | Tool | Config File | Output |
|-----------|----------|------|-------------|--------|
| JSDoc | JS/TS | npx jsdoc | jsdoc.json | HTML |
| Sphinx | Python | sphinx-build | conf.py | HTML/Markdown |
| rustdoc | Rust | cargo doc | Cargo.toml | HTML |

## Subtasks & Detailed Guidance

### Subtask T025 – Create doc_generators.py Module

**Purpose**: Create the Python module that will house the generator protocol and implementations.

**Steps**:
1. Create `src/specify_cli/doc_generators.py`
2. Add module docstring:
   ```python
   """Documentation generator integration for spec-kitty.

   This module provides a protocol-based interface for integrating documentation
   generators (JSDoc, Sphinx, rustdoc) into the documentation mission workflow.

   Generators detect project languages, create configuration files, and invoke
   generator tools via subprocess to produce API reference documentation.
   """
   ```
3. Add imports:
   ```python
   from __future__ import annotations

   import json
   import subprocess
   from dataclasses import dataclass, field
   from pathlib import Path
   from typing import Any, Dict, List, Optional, Protocol
   ```
4. Verify module can be imported

**Files**: `src/specify_cli/doc_generators.py` (new file)

**Parallel?**: No (foundation for other subtasks)

**Notes**: This is the module entry point; all other subtasks add to this file.

### Subtask T026 – Define DocGenerator Protocol

**Purpose**: Define the protocol (interface) that all documentation generators must implement.

**Steps**:
1. In `doc_generators.py`, define the `DocGenerator` protocol:
   ```python
   class DocGenerator(Protocol):
       """Protocol for documentation generators.

       All generators (JSDoc, Sphinx, rustdoc) implement this interface to provide
       consistent detection, configuration, and generation capabilities.
       """

       name: str  # Generator identifier (e.g., "jsdoc", "sphinx", "rustdoc")
       languages: List[str]  # Supported languages (e.g., ["javascript", "typescript"])

       def detect(self, project_root: Path) -> bool:
           """Detect if this generator is applicable to the project.

           Args:
               project_root: Root directory of the project to check

           Returns:
               True if generator should be used for this project, False otherwise
           """
           ...

       def configure(self, output_dir: Path, options: Dict[str, Any]) -> Path:
           """Generate configuration file for this generator.

           Args:
               output_dir: Directory where config file should be created
               options: Generator-specific options (project_name, author, etc.)

           Returns:
               Path to the generated configuration file

           Raises:
               GeneratorError: If configuration generation fails
           """
           ...

       def generate(self, source_dir: Path, output_dir: Path) -> 'GeneratorResult':
           """Run generator to produce documentation.

           Args:
               source_dir: Directory containing source code to document
               output_dir: Directory where documentation should be generated

           Returns:
               GeneratorResult with success status, errors, warnings, generated files

           Raises:
               GeneratorError: If generator invocation fails catastrophically
           """
           ...
   ```

**Files**: `src/specify_cli/doc_generators.py` (modified)

**Parallel?**: No (other classes depend on this protocol)

**Notes**:
- Protocol uses typing.Protocol (Python 3.8+)
- Methods have clear docstrings
- Return types and parameters are explicit

**Quality Validation**:
- Does protocol define all necessary methods?
- Are method signatures clear?
- Do docstrings explain purpose and parameters?

### Subtask T027 – Define GeneratorResult Dataclass

**Purpose**: Define the dataclass that generators return to report results.

**Steps**:
1. In `doc_generators.py`, define `GeneratorResult`:
   ```python
   @dataclass
   class GeneratorResult:
       """Result of running a documentation generator.

       Attributes:
           success: True if generation completed without errors
           output_dir: Directory where documentation was generated
           errors: List of error messages (empty if success=True)
           warnings: List of warning messages (may be present even if success=True)
           generated_files: List of generated documentation files
       """
       success: bool
       output_dir: Path
       errors: List[str] = field(default_factory=list)
       warnings: List[str] = field(default_factory=list)
       generated_files: List[Path] = field(default_factory=list)

       def __repr__(self) -> str:
           """Human-readable representation."""
           status = "✓ Success" if self.success else "✗ Failed"
           file_count = len(self.generated_files)
           error_count = len(self.errors)
           warning_count = len(self.warnings)
           return (
               f"GeneratorResult({status}, "
               f"{file_count} files, "
               f"{error_count} errors, "
               f"{warning_count} warnings)"
           )
   ```

2. Add `GeneratorError` exception:
   ```python
   class GeneratorError(Exception):
       """Raised when a generator encounters an unrecoverable error."""
       pass
   ```

**Files**: `src/specify_cli/doc_generators.py` (modified)

**Parallel?**: No (generators return this type)

**Notes**:
- Dataclass for easy instantiation
- Default empty lists for errors/warnings/files
- Custom __repr__ for logging
- Separate exception for generator errors

**Quality Validation**:
- Are all result fields present?
- Is success field boolean?
- Are error/warning lists initialized?

### Subtask T028 – Implement JSDocGenerator

**Purpose**: Implement JSDoc generator for JavaScript/TypeScript projects.

**Steps**:
1. In `doc_generators.py`, implement `JSDocGenerator`:
   ```python
   @dataclass
   class JSDocGenerator:
       """JSDoc documentation generator for JavaScript/TypeScript projects.

       Generates API reference documentation from JSDoc comments in JavaScript/TypeScript
       code using the JSDoc tool (invoked via npx).
       """

       name: str = "jsdoc"
       languages: List[str] = field(default_factory=lambda: ["javascript", "typescript"])

       def detect(self, project_root: Path) -> bool:
           """Detect if project uses JavaScript/TypeScript.

           Checks for:
           - .js, .jsx, .ts, .tsx files
           - package.json file (Node.js project indicator)
           - node_modules/ directory

           Args:
               project_root: Project root directory

           Returns:
               True if JavaScript/TypeScript files found
           """
           # Check for package.json (strongest indicator)
           if (project_root / "package.json").exists():
               return True

           # Check for JS/TS files in common locations
           for pattern in ["*.js", "*.jsx", "*.ts", "*.tsx"]:
               if list(project_root.glob(f"**/{pattern}")):
                   return True

           return False

       def configure(self, output_dir: Path, options: Dict[str, Any]) -> Path:
           """Generate jsdoc.json configuration file.

           Args:
               output_dir: Directory where jsdoc.json should be created
               options: Configuration options:
                   - project_name: Project name
                   - source_dir: Source directory to document (default: "src/")
                   - template: JSDoc template to use (default: "docdash")

           Returns:
               Path to generated jsdoc.json

           Raises:
               GeneratorError: If config file cannot be written
           """
           source_dir = options.get("source_dir", "src/")
           template = options.get("template", "docdash")
           project_name = options.get("project_name", "Project")

           config = {
               "source": {
                   "include": [source_dir],
                   "includePattern": ".+\\.(js|jsx|ts|tsx)$",
                   "excludePattern": "(^|\\/|\\\\)_"
               },
               "opts": {
                   "destination": str(output_dir / "api" / "javascript"),
                   "recurse": True,
                   "readme": "README.md",
                   "template": f"node_modules/{template}"
               },
               "plugins": ["plugins/markdown"],
               "templates": {
                   "cleverLinks": False,
                   "monospaceLinks": False
               }
           }

           config_file = output_dir / "jsdoc.json"
           try:
               config_file.write_text(json.dumps(config, indent=2))
               return config_file
           except OSError as e:
               raise GeneratorError(f"Failed to write jsdoc.json: {e}")

       def generate(self, source_dir: Path, output_dir: Path) -> GeneratorResult:
           """Run JSDoc to generate documentation.

           Args:
               source_dir: Directory containing JavaScript/TypeScript source
               output_dir: Directory where docs should be generated (contains jsdoc.json)

           Returns:
               GeneratorResult with success status and generated files

           Raises:
               GeneratorError: If JSDoc is not installed
           """
           config_file = output_dir / "jsdoc.json"

           if not config_file.exists():
               return GeneratorResult(
                   success=False,
                   output_dir=output_dir,
                   errors=["jsdoc.json not found - run configure() first"],
               )

           # Check if npx is available
           check_npx = subprocess.run(
               ["npx", "--version"],
               capture_output=True,
               text=True
           )

           if check_npx.returncode != 0:
               raise GeneratorError(
                   "npx not found - install Node.js to use JSDoc generator\n"
                   "Visit: https://nodejs.org/"
               )

           # Run JSDoc
           cmd = ["npx", "jsdoc", "-c", str(config_file)]
           result = subprocess.run(
               cmd,
               cwd=str(source_dir),
               capture_output=True,
               text=True
           )

           # Parse output
           errors = []
           warnings = []
           if result.returncode != 0:
               errors = result.stderr.splitlines()

           # Extract warnings from stdout (JSDoc prints warnings to stdout)
           for line in result.stdout.splitlines():
               if "WARNING" in line.upper():
                   warnings.append(line)

           # Find generated files
           api_dir = output_dir / "api" / "javascript"
           generated_files = []
           if api_dir.exists():
               generated_files = list(api_dir.rglob("*.html"))

           return GeneratorResult(
               success=(result.returncode == 0),
               output_dir=api_dir if api_dir.exists() else output_dir,
               errors=errors,
               warnings=warnings,
               generated_files=generated_files
           )
   ```

**Files**: `src/specify_cli/doc_generators.py` (modified)

**Parallel?**: Yes (can implement alongside SphinxGenerator and RustdocGenerator)

**Notes**:
- Detection checks for package.json and JS/TS files
- Configuration generates jsdoc.json from template
- Generation invokes npx jsdoc via subprocess
- Error handling for missing npx
- Captures errors, warnings, generated files

**Quality Validation**:
- Does detect() correctly identify JS/TS projects?
- Does configure() generate valid jsdoc.json?
- Does generate() invoke JSDoc correctly?
- Are errors captured and reported?
- Is subprocess failure handled gracefully?

### Subtask T029 – Implement SphinxGenerator

**Purpose**: Implement Sphinx generator for Python projects.

**Steps**:
1. In `doc_generators.py`, implement `SphinxGenerator`:
   ```python
   @dataclass
   class SphinxGenerator:
       """Sphinx documentation generator for Python projects.

       Generates API reference documentation from Python docstrings using Sphinx
       with autodoc and napoleon extensions.
       """

       name: str = "sphinx"
       languages: List[str] = field(default_factory=lambda: ["python"])

       def detect(self, project_root: Path) -> bool:
           """Detect if project uses Python.

           Checks for:
           - setup.py (Python package indicator)
           - pyproject.toml (modern Python project)
           - .py files in project

           Args:
               project_root: Project root directory

           Returns:
               True if Python files found
           """
           # Check for Python project indicators
           if (project_root / "setup.py").exists():
               return True
           if (project_root / "pyproject.toml").exists():
               return True

           # Check for Python files
           if list(project_root.glob("**/*.py")):
               return True

           return False

       def configure(self, output_dir: Path, options: Dict[str, Any]) -> Path:
           """Generate Sphinx conf.py configuration file.

           Args:
               output_dir: Directory where conf.py should be created
               options: Configuration options:
                   - project_name: Project name
                   - author: Author name
                   - version: Project version
                   - theme: Sphinx theme (default: "sphinx_rtd_theme")

           Returns:
               Path to generated conf.py

           Raises:
               GeneratorError: If config file cannot be written
           """
           project_name = options.get("project_name", "Project")
           author = options.get("author", "Author")
           version = options.get("version", "0.1.0")
           theme = options.get("theme", "sphinx_rtd_theme")

           config_content = f'''# Sphinx configuration for {project_name}
# Auto-generated by spec-kitty documentation mission

project = '{project_name}'
author = '{author}'
version = '{version}'
release = version

# Extensions
extensions = [
    'sphinx.ext.autodoc',      # Auto-generate docs from docstrings
    'sphinx.ext.napoleon',     # Support Google/NumPy docstring styles
    'sphinx.ext.viewcode',     # Add links to source code
    'sphinx.ext.intersphinx',  # Link to other project docs
]

# Napoleon settings for Google-style docstrings
napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_include_init_with_doc = True

# HTML output options
html_theme = '{theme}'
html_static_path = ['_static']

# Autodoc options
autodoc_default_options = {{
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}}

# Path setup
import os
import sys
sys.path.insert(0, os.path.abspath('..'))
'''

           config_file = output_dir / "conf.py"
           try:
               config_file.write_text(config_content)
               return config_file
           except OSError as e:
               raise GeneratorError(f"Failed to write conf.py: {e}")

       def generate(self, source_dir: Path, output_dir: Path) -> GeneratorResult:
           """Run Sphinx to generate documentation.

           Args:
               source_dir: Directory containing Python source (not used directly - Sphinx uses conf.py paths)
               output_dir: Directory where docs should be generated (contains conf.py)

           Returns:
               GeneratorResult with success status and generated files

           Raises:
               GeneratorError: If Sphinx is not installed
           """
           config_file = output_dir / "conf.py"

           if not config_file.exists():
               return GeneratorResult(
                   success=False,
                   output_dir=output_dir,
                   errors=["conf.py not found - run configure() first"],
               )

           # Check if sphinx-build is available
           check_sphinx = subprocess.run(
               ["sphinx-build", "--version"],
               capture_output=True,
               text=True
           )

           if check_sphinx.returncode != 0:
               raise GeneratorError(
                   "sphinx-build not found - install Sphinx to use this generator\n"
                   "Run: pip install sphinx sphinx-rtd-theme"
               )

           # Create build directory
           build_dir = output_dir / "_build" / "html"
           build_dir.mkdir(parents=True, exist_ok=True)

           # Run Sphinx
           cmd = [
               "sphinx-build",
               "-b", "html",           # HTML builder
               "-W",                   # Treat warnings as errors (optional)
               str(output_dir),        # Source directory (contains conf.py)
               str(build_dir)          # Build directory
           ]

           result = subprocess.run(
               cmd,
               capture_output=True,
               text=True
           )

           # Parse output
           errors = []
           warnings = []
           if result.returncode != 0:
               errors = result.stderr.splitlines()

           # Extract warnings from stdout (Sphinx prints warnings to stdout)
           for line in result.stdout.splitlines():
               if "WARNING" in line.upper() or "warning:" in line.lower():
                   warnings.append(line)

           # Find generated files
           generated_files = []
           if build_dir.exists():
               generated_files = list(build_dir.rglob("*.html"))

           return GeneratorResult(
               success=(result.returncode == 0),
               output_dir=build_dir,
               errors=errors,
               warnings=warnings,
               generated_files=generated_files
           )
   ```

**Files**: `src/specify_cli/doc_generators.py` (modified)

**Parallel?**: Yes (can implement alongside JSDocGenerator and RustdocGenerator)

**Notes**:
- Detection checks for setup.py, pyproject.toml, .py files
- Configuration generates conf.py with autodoc + napoleon
- Generation invokes sphinx-build via subprocess
- Error handling for missing sphinx-build
- Warnings extracted from stdout
- Generated HTML files cataloged

**Quality Validation**:
- Does detect() correctly identify Python projects?
- Does configure() generate valid conf.py?
- Does generate() invoke Sphinx correctly?
- Are autodoc and napoleon configured?
- Are errors and warnings captured?

### Subtask T030 – Implement RustdocGenerator

**Purpose**: Implement rustdoc generator for Rust projects.

**Steps**:
1. In `doc_generators.py`, implement `RustdocGenerator`:
   ```python
   @dataclass
   class RustdocGenerator:
       """rustdoc documentation generator for Rust projects.

       Generates API reference documentation from Rust doc comments using rustdoc
       (invoked via cargo doc).
       """

       name: str = "rustdoc"
       languages: List[str] = field(default_factory=lambda: ["rust"])

       def detect(self, project_root: Path) -> bool:
           """Detect if project uses Rust.

           Checks for:
           - Cargo.toml (Rust project indicator)
           - .rs files in project

           Args:
               project_root: Project root directory

           Returns:
               True if Rust project found
           """
           # Check for Cargo.toml (definitive Rust project indicator)
           if (project_root / "Cargo.toml").exists():
               return True

           # Check for Rust source files
           if list(project_root.glob("**/*.rs")):
               return True

           return False

       def configure(self, output_dir: Path, options: Dict[str, Any]) -> Path:
           """Generate rustdoc configuration (updates Cargo.toml).

           For Rust projects, configuration is typically done in Cargo.toml metadata.
           This method returns instructions rather than creating a separate config file.

           Args:
               output_dir: Not used (rustdoc configured via Cargo.toml)
               options: Configuration options:
                   - document_private: Include private items (default: False)

           Returns:
               Path to instructions file

           Raises:
               GeneratorError: If instructions cannot be written
           """
           document_private = options.get("document_private", False)

           instructions = f'''# rustdoc Configuration for spec-kitty

rustdoc is configured via Cargo.toml. Add the following to your Cargo.toml:

```toml
[package.metadata.docs.rs]
all-features = true
rustdoc-args = ["{f"--document-private-items" if document_private else ""}"]
```

This configuration:
- Documents all features
{"- Includes private items in documentation" if document_private else "- Documents only public items"}

No separate configuration file is needed for rustdoc.
'''

           instructions_file = output_dir / "rustdoc-config.md"
           try:
               instructions_file.write_text(instructions)
               return instructions_file
           except OSError as e:
               raise GeneratorError(f"Failed to write rustdoc instructions: {e}")

       def generate(self, source_dir: Path, output_dir: Path) -> GeneratorResult:
           """Run cargo doc to generate documentation.

           Args:
               source_dir: Directory containing Rust source (must have Cargo.toml)
               output_dir: Directory where docs should be generated

           Returns:
               GeneratorResult with success status and generated files

           Raises:
               GeneratorError: If cargo is not installed
           """
           cargo_toml = source_dir / "Cargo.toml"

           if not cargo_toml.exists():
               return GeneratorResult(
                   success=False,
                   output_dir=output_dir,
                   errors=["Cargo.toml not found - not a Rust project"],
               )

           # Check if cargo is available
           check_cargo = subprocess.run(
               ["cargo", "--version"],
               capture_output=True,
               text=True
           )

           if check_cargo.returncode != 0:
               raise GeneratorError(
                   "cargo not found - install Rust toolchain to use rustdoc generator\n"
                   "Visit: https://rustup.rs/"
               )

           # Run cargo doc
           cmd = [
               "cargo", "doc",
               "--no-deps",              # Don't document dependencies
               "--target-dir", str(output_dir)
           ]

           result = subprocess.run(
               cmd,
               cwd=str(source_dir),
               capture_output=True,
               text=True
           )

           # Parse output
           errors = []
           warnings = []
           if result.returncode != 0:
               errors = result.stderr.splitlines()

           # Extract warnings from stderr (cargo prints warnings to stderr)
           for line in result.stderr.splitlines():
               if "warning:" in line.lower():
                   warnings.append(line)

           # Find generated files (cargo doc outputs to target/doc/)
           doc_dir = output_dir / "doc"
           generated_files = []
           if doc_dir.exists():
               generated_files = list(doc_dir.rglob("*.html"))

           return GeneratorResult(
               success=(result.returncode == 0),
               output_dir=doc_dir if doc_dir.exists() else output_dir,
               errors=errors,
               warnings=warnings,
               generated_files=generated_files
           )
   ```

**Files**: `src/specify_cli/doc_generators.py` (modified)

**Parallel?**: Yes (can implement alongside JSDocGenerator and SphinxGenerator)

**Notes**:
- Detection checks for Cargo.toml and .rs files
- Configuration provides instructions (rustdoc configured via Cargo.toml)
- Generation invokes cargo doc via subprocess
- Error handling for missing cargo
- Warnings extracted from stderr
- Generated HTML files in target/doc/ cataloged

**Quality Validation**:
- Does detect() correctly identify Rust projects?
- Does configure() provide clear instructions?
- Does generate() invoke cargo doc correctly?
- Are errors and warnings captured?
- Is cargo missing handled gracefully?

### Subtask T031 – Add Error Handling for Missing Generators

**Purpose**: Ensure all generators handle missing tools gracefully with helpful error messages.

**Steps**:
1. Review each generator's `generate()` method
2. Verify each checks for tool availability before invoking
3. Verify each raises `GeneratorError` with helpful message if tool missing
4. Add helper function for checking tool availability:
   ```python
   def check_tool_available(tool_name: str, install_url: str) -> bool:
       """Check if a command-line tool is available.

       Args:
           tool_name: Name of the tool to check (e.g., "npx", "sphinx-build", "cargo")
           install_url: URL where tool can be downloaded

       Returns:
           True if tool is available, False otherwise

       Raises:
           GeneratorError: If tool is not available (with installation instructions)
       """
       check = subprocess.run(
           [tool_name, "--version"],
           capture_output=True,
           text=True
       )

       if check.returncode != 0:
           raise GeneratorError(
               f"{tool_name} not found - install required tool\n"
               f"Visit: {install_url}"
           )

       return True
   ```
5. Update each generator to use helper (optional refactoring)

**Files**: `src/specify_cli/doc_generators.py` (modified)

**Parallel?**: No (modifies all generators)

**Notes**:
- Tool availability checked before subprocess invocation
- Clear error messages with installation URLs
- GeneratorError raised (not subprocess exception)
- User gets actionable error message

**Quality Validation**:
- Does each generator check for its tool?
- Are error messages clear and actionable?
- Do error messages include installation URLs?
- Is GeneratorError raised (not generic exception)?

### Subtask T032 – Add Generator Config Templates

**Purpose**: Create template files for Sphinx conf.py and JSDoc jsdoc.json that can be customized during configure().

**Steps**:
1. Create `src/specify_cli/missions/documentation/templates/generators/` directory
2. Create `sphinx-conf.py.template`:
   ```python
   # Sphinx configuration for {project_name}
   # Auto-generated by spec-kitty documentation mission

   project = '{project_name}'
   author = '{author}'
   version = '{version}'
   release = version

   # Extensions
   extensions = [
       'sphinx.ext.autodoc',      # Auto-generate docs from docstrings
       'sphinx.ext.napoleon',     # Support Google/NumPy docstring styles
       'sphinx.ext.viewcode',     # Add links to source code
       'sphinx.ext.intersphinx',  # Link to other project docs
   ]

   # Napoleon settings for Google-style docstrings
   napoleon_google_docstring = True
   napoleon_numpy_docstring = True
   napoleon_include_init_with_doc = True

   # HTML output options
   html_theme = '{theme}'
   html_static_path = ['_static']

   # Autodoc options
   autodoc_default_options = {
       'members': True,
       'undoc-members': True,
       'show-inheritance': True,
   }

   # Path setup
   import os
   import sys
   sys.path.insert(0, os.path.abspath('..'))
   ```
3. Create `jsdoc.json.template`:
   ```json
   {
     "source": {
       "include": ["{source_dir}"],
       "includePattern": ".+\\.(js|jsx|ts|tsx)$",
       "excludePattern": "(^|\\/|\\\\)_"
     },
     "opts": {
       "destination": "{output_dir}",
       "recurse": true,
       "readme": "README.md",
       "template": "node_modules/{template}"
     },
     "plugins": ["plugins/markdown"],
     "templates": {
       "cleverLinks": false,
       "monospaceLinks": false
     }
   }
   ```
4. Update generators to optionally load from templates instead of hardcoding (optional enhancement)

**Files**:
- `src/specify_cli/missions/documentation/templates/generators/sphinx-conf.py.template` (new file)
- `src/specify_cli/missions/documentation/templates/generators/jsdoc.json.template` (new file)

**Parallel?**: Yes (can create templates alongside generator implementation)

**Notes**:
- Templates provide baseline configuration
- Generators currently hardcode config (templates are reference)
- Future enhancement: load template, substitute placeholders
- Placeholders: {project_name}, {author}, {version}, {theme}, {source_dir}, {output_dir}, {template}

**Quality Validation**:
- Are template files valid (Python/JSON syntax)?
- Are placeholders clearly marked?
- Do templates match what generators produce?

## Test Strategy

**Unit Tests** (to be implemented in WP09):

1. Test DocGenerator protocol compliance:
   ```python
   def test_jsdoc_generator_implements_protocol():
       generator = JSDocGenerator()
       assert hasattr(generator, "name")
       assert hasattr(generator, "languages")
       assert hasattr(generator, "detect")
       assert hasattr(generator, "configure")
       assert hasattr(generator, "generate")
   ```

2. Test detection logic:
   ```python
   def test_jsdoc_detects_javascript_project(tmp_path):
       # Create package.json
       (tmp_path / "package.json").write_text("{}")

       generator = JSDocGenerator()
       assert generator.detect(tmp_path) is True

   def test_jsdoc_does_not_detect_python_project(tmp_path):
       # Create setup.py
       (tmp_path / "setup.py").write_text("")

       generator = JSDocGenerator()
       assert generator.detect(tmp_path) is False
   ```

3. Test configuration generation:
   ```python
   def test_sphinx_configure_creates_conf_py(tmp_path):
       generator = SphinxGenerator()
       config_file = generator.configure(
           tmp_path,
           {"project_name": "Test", "author": "Author"}
       )

       assert config_file.exists()
       assert config_file.name == "conf.py"
       content = config_file.read_text()
       assert "project = 'Test'" in content
       assert "author = 'Author'" in content
   ```

4. Test graceful degradation:
   ```python
   def test_generator_error_when_tool_missing(tmp_path, monkeypatch):
       # Mock subprocess to simulate missing tool
       def mock_run(*args, **kwargs):
           class Result:
               returncode = 127  # Command not found
               stdout = ""
               stderr = "command not found"
           return Result()

       monkeypatch.setattr(subprocess, "run", mock_run)

       generator = JSDocGenerator()
       with pytest.raises(GeneratorError) as exc_info:
           generator.generate(tmp_path, tmp_path)

       assert "npx not found" in str(exc_info.value)
       assert "nodejs.org" in str(exc_info.value)
   ```

5. Test GeneratorResult:
   ```python
   def test_generator_result_success():
       result = GeneratorResult(
           success=True,
           output_dir=Path("/docs"),
           generated_files=[Path("/docs/index.html")]
       )

       assert result.success is True
       assert len(result.errors) == 0
       assert len(result.generated_files) == 1
       assert "✓ Success" in repr(result)
   ```

**Integration Tests** (require actual tools installed):

```python
@pytest.mark.integration
def test_sphinx_end_to_end(tmp_path):
    """Test Sphinx generation end-to-end (requires sphinx-build installed)."""
    # Create Python source with docstring
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "example.py").write_text('''
def hello(name: str) -> str:
    """Greet someone by name.

    Args:
        name: Person to greet

    Returns:
        Greeting message
    """
    return f"Hello, {name}!"
''')

    # Configure generator
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    generator = SphinxGenerator()
    config_file = generator.configure(docs_dir, {
        "project_name": "Test",
        "author": "Test Author"
    })

    assert config_file.exists()

    # Generate docs
    result = generator.generate(source_dir, docs_dir)

    # Verify result
    assert result.success
    assert len(result.generated_files) > 0
    assert (result.output_dir / "index.html").exists()
```

**Manual Validation**:

1. Test JSDoc detection and generation:
   ```bash
   # Create test JS project
   mkdir -p /tmp/test-js
   cd /tmp/test-js
   npm init -y
   echo "/** @function hello */" > index.js

   # Test in Python REPL
   python3 -c "
   from pathlib import Path
   from specify_cli.doc_generators import JSDocGenerator

   gen = JSDocGenerator()
   assert gen.detect(Path('/tmp/test-js'))
   print('✓ JSDoc detection works')
   "
   ```

2. Test Sphinx detection and generation:
   ```bash
   # Create test Python project
   mkdir -p /tmp/test-py
   cd /tmp/test-py
   cat > setup.py << EOF
   from setuptools import setup
   setup(name='test')
   EOF

   # Test in Python REPL
   python3 -c "
   from pathlib import Path
   from specify_cli.doc_generators import SphinxGenerator

   gen = SphinxGenerator()
   assert gen.detect(Path('/tmp/test-py'))
   print('✓ Sphinx detection works')
   "
   ```

3. Test rustdoc detection:
   ```bash
   # Create test Rust project
   mkdir -p /tmp/test-rust
   cd /tmp/test-rust
   cargo init

   # Test in Python REPL
   python3 -c "
   from pathlib import Path
   from specify_cli.doc_generators import RustdocGenerator

   gen = RustdocGenerator()
   assert gen.detect(Path('/tmp/test-rust'))
   print('✓ rustdoc detection works')
   "
   ```

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Generator tools not installed | High - blocks reference doc generation | Check for tool availability, provide clear installation instructions |
| Subprocess failures | High - documentation generation fails | Capture errors, log stderr, raise GeneratorError with context |
| Cross-platform path issues | Medium - works on one OS, fails on others | Use Path objects, test on macOS/Linux/Windows |
| Generator config syntax errors | Medium - generated config invalid | Test generated configs, validate syntax |
| Sparse code comments | Medium - generated docs are empty | Detect and warn user, offer manual templates |
| Generator tool version incompatibility | Low - different tool versions behave differently | Document required versions, handle common version issues |

## Definition of Done Checklist

- [ ] `src/specify_cli/doc_generators.py` module created
- [ ] `DocGenerator` protocol defined with detect, configure, generate methods
- [ ] `GeneratorResult` dataclass defined with success, errors, warnings, generated_files
- [ ] `GeneratorError` exception defined
- [ ] `JSDocGenerator` class implemented:
  - [ ] Detects JS/TS projects correctly
  - [ ] Generates valid jsdoc.json
  - [ ] Invokes npx jsdoc via subprocess
  - [ ] Checks for npx availability
  - [ ] Captures errors and warnings
  - [ ] Returns GeneratorResult
- [ ] `SphinxGenerator` class implemented:
  - [ ] Detects Python projects correctly
  - [ ] Generates valid conf.py
  - [ ] Invokes sphinx-build via subprocess
  - [ ] Checks for sphinx-build availability
  - [ ] Captures errors and warnings
  - [ ] Returns GeneratorResult
- [ ] `RustdocGenerator` class implemented:
  - [ ] Detects Rust projects correctly
  - [ ] Provides rustdoc configuration instructions
  - [ ] Invokes cargo doc via subprocess
  - [ ] Checks for cargo availability
  - [ ] Captures errors and warnings
  - [ ] Returns GeneratorResult
- [ ] All generators handle missing tools gracefully
- [ ] Generator config templates created (sphinx-conf.py.template, jsdoc.json.template)
- [ ] All generators tested with sample projects
- [ ] Manual testing completed (detection, configuration, generation)
- [ ] `tasks.md` in feature directory updated with WP05 status

## Review Guidance

**Key Acceptance Checkpoints**:

1. **Protocol Compliance**: All generators implement DocGenerator protocol
2. **Detection Accuracy**: Each generator correctly identifies its target language
3. **Configuration Validity**: Generated configs are syntactically valid
4. **Subprocess Invocation**: Generators invoke tools correctly with proper error handling
5. **Graceful Degradation**: Missing tools result in clear, actionable errors
6. **Result Reporting**: GeneratorResult accurately reflects success/failure and lists generated files

**Validation Commands**:
```bash
# Test module imports
python -c "from specify_cli.doc_generators import JSDocGenerator, SphinxGenerator, RustdocGenerator, DocGenerator, GeneratorResult, GeneratorError; print('✓ All imports successful')"

# Test detection (requires test projects)
python -c "
from pathlib import Path
from specify_cli.doc_generators import JSDocGenerator, SphinxGenerator, RustdocGenerator

# Test with current directory (has Python files)
sphinx = SphinxGenerator()
if sphinx.detect(Path('.')):
    print('✓ Sphinx detected Python project')
else:
    print('⚠️ Sphinx did not detect Python (expected if no .py files here)')
"

# Test configuration generation
python -c "
from pathlib import Path
from specify_cli.doc_generators import SphinxGenerator

gen = SphinxGenerator()
config = gen.configure(Path('/tmp'), {'project_name': 'Test', 'author': 'Test'})
print(f'✓ Sphinx config generated: {config}')
"
```

**Review Focus Areas**:
- All three generators implement the protocol correctly
- Detection logic is sound (checks for correct file types)
- Configuration generation produces valid config files
- Subprocess invocation captures stdout/stderr correctly
- Error handling provides actionable guidance
- GeneratorResult accurately reflects generation outcome
- Code is cross-platform (Path objects, no hardcoded separators)

## Activity Log

- 2026-01-12T17:18:56Z – system – lane=planned – Prompt created.
- 2026-01-13T09:16:42Z – test-agent – lane=doing – Moved to doing
- 2026-01-13T10:35:22Z – sparse-test – lane=planned – Moved to planned
- 2026-01-13T10:48:30Z – claude – shell_pid=58940 – lane=doing – Started implementation via workflow command
- 2026-01-13T10:54:28Z – claude – shell_pid=58940 – lane=for_review – Ready for review: Implemented documentation generator protocol with JSDoc, Sphinx, and rustdoc generators. All generators tested and working correctly.
- 2026-01-13T10:58:38Z – claude – shell_pid=65572 – lane=doing – Started review via workflow command
