"""Documentation generator integration for spec-kitty.

This module provides a protocol-based interface for integrating documentation
generators (JSDoc, Sphinx, rustdoc) into the documentation mission workflow.

Generators detect project languages, create configuration files, and invoke
generator tools via subprocess to produce API reference documentation.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol


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


class GeneratorError(Exception):
    """Raised when a generator encounters an unrecoverable error."""
    pass


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
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if check.returncode != 0:
        raise GeneratorError(
            f"{tool_name} not found - install required tool\n"
            f"Visit: {install_url}"
        )

    return True


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
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            config_file.write_text(json.dumps(config, indent=2), encoding='utf-8')
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
            text=True,
            encoding="utf-8",
            errors="replace",
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
            text=True,
            encoding="utf-8",
            errors="replace",
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
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            config_file.write_text(config_content, encoding='utf-8')
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
            text=True,
            encoding="utf-8",
            errors="replace",
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
            text=True,
            encoding="utf-8",
            errors="replace",
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
        output_dir.mkdir(parents=True, exist_ok=True)
        try:
            instructions_file.write_text(instructions, encoding='utf-8')
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
            text=True,
            encoding="utf-8",
            errors="replace",
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
            text=True,
            encoding="utf-8",
            errors="replace",
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
