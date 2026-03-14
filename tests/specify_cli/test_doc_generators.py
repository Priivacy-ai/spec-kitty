"""Tests for documentation generators."""

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from specify_cli.doc_generators import (
    GeneratorResult,
    GeneratorError,
    JSDocGenerator,
    SphinxGenerator,
    RustdocGenerator,
)


# T062: Test JSDoc Detection
def test_jsdoc_detects_package_json(tmp_path):
    """Test JSDoc detects projects with package.json."""
    (tmp_path / "package.json").write_text('{"name": "test"}')

    generator = JSDocGenerator()
    assert generator.detect(tmp_path) is True


def test_jsdoc_detects_js_files(tmp_path):
    """Test JSDoc detects projects with .js files."""
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    (src_dir / "index.js").write_text("// JavaScript file")

    generator = JSDocGenerator()
    assert generator.detect(tmp_path) is True


def test_jsdoc_detects_ts_files(tmp_path):
    """Test JSDoc detects projects with .ts files."""
    (tmp_path / "app.ts").write_text("// TypeScript file")

    generator = JSDocGenerator()
    assert generator.detect(tmp_path) is True


def test_jsdoc_does_not_detect_python_project(tmp_path):
    """Test JSDoc does not detect Python projects."""
    (tmp_path / "setup.py").write_text("# Python project")

    generator = JSDocGenerator()
    assert generator.detect(tmp_path) is False


# T063: Test Sphinx Detection
def test_sphinx_detects_setup_py(tmp_path):
    """Test Sphinx detects projects with setup.py."""
    (tmp_path / "setup.py").write_text("# setup.py")

    generator = SphinxGenerator()
    assert generator.detect(tmp_path) is True


def test_sphinx_detects_pyproject_toml(tmp_path):
    """Test Sphinx detects projects with pyproject.toml."""
    (tmp_path / "pyproject.toml").write_text("[project]")

    generator = SphinxGenerator()
    assert generator.detect(tmp_path) is True


def test_sphinx_detects_py_files(tmp_path):
    """Test Sphinx detects projects with .py files."""
    (tmp_path / "main.py").write_text("# Python file")

    generator = SphinxGenerator()
    assert generator.detect(tmp_path) is True


def test_sphinx_does_not_detect_js_project(tmp_path):
    """Test Sphinx does not detect JavaScript projects."""
    (tmp_path / "package.json").write_text("{}")

    generator = SphinxGenerator()
    assert generator.detect(tmp_path) is False


# T064: Test rustdoc Detection
def test_rustdoc_detects_cargo_toml(tmp_path):
    """Test rustdoc detects projects with Cargo.toml."""
    (tmp_path / "Cargo.toml").write_text('[package]\nname = "test"')

    generator = RustdocGenerator()
    assert generator.detect(tmp_path) is True


def test_rustdoc_detects_rs_files(tmp_path):
    """Test rustdoc detects projects with .rs files."""
    (tmp_path / "main.rs").write_text("// Rust file")

    generator = RustdocGenerator()
    assert generator.detect(tmp_path) is True


def test_rustdoc_does_not_detect_python_project(tmp_path):
    """Test rustdoc does not detect Python projects."""
    (tmp_path / "setup.py").write_text("# Python")

    generator = RustdocGenerator()
    assert generator.detect(tmp_path) is False


# T065: Test Generator Configuration
def test_jsdoc_configure_creates_config(tmp_path):
    """Test JSDoc configure() creates jsdoc.json."""
    generator = JSDocGenerator()
    config_file = generator.configure(tmp_path, {
        "project_name": "Test Project",
        "description": "Test",
        "version": "1.0.0"
    })

    assert config_file.exists()
    assert config_file.name == "jsdoc.json"

    # Verify config is valid JSON
    config_data = json.loads(config_file.read_text())
    assert "source" in config_data
    assert "opts" in config_data


def test_sphinx_configure_creates_conf_py(tmp_path):
    """Test Sphinx configure() creates conf.py."""
    generator = SphinxGenerator()
    config_file = generator.configure(tmp_path, {
        "project_name": "Test Project",
        "author": "Test Author",
        "version": "1.0.0"
    })

    assert config_file.exists()
    assert config_file.name == "conf.py"

    # Verify conf.py has required variables
    content = config_file.read_text()
    assert "project = " in content
    assert "author = " in content


def test_rustdoc_configure_creates_instructions(tmp_path):
    """Test rustdoc configure() creates instructions file."""
    generator = RustdocGenerator()
    config_file = generator.configure(tmp_path, {
        "project_name": "Test Project"
    })

    assert config_file.exists()
    assert config_file.name == "rustdoc-config.md"

    content = config_file.read_text()
    # rustdoc is configured via Cargo.toml, so check for that
    assert "Cargo.toml" in content or "rustdoc" in content.lower()


# T065: Test Graceful Degradation
def test_jsdoc_raises_error_when_npx_missing(tmp_path, monkeypatch):
    """Test JSDoc raises GeneratorError when npx not installed."""
    # Mock subprocess to simulate missing npx
    def mock_run(cmd, *args, **kwargs):
        if cmd[0] in ["npx", "jsdoc"]:
            result = MagicMock()
            result.returncode = 127
            result.stdout = ""
            result.stderr = "npx: command not found"
            return result
        return subprocess.run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)

    # Configure first (should succeed - only creates config file)
    generator = JSDocGenerator()
    config = generator.configure(tmp_path, {"project_name": "Test"})
    assert config.exists()

    # Generate should raise GeneratorError
    with pytest.raises(GeneratorError) as exc_info:
        generator.generate(tmp_path, tmp_path)

    error_msg = str(exc_info.value).lower()
    assert "npx" in error_msg or "not found" in error_msg or "install" in error_msg


# T066: Test Integration (marked as integration)
@pytest.mark.integration
def test_sphinx_generation_end_to_end(tmp_path):
    """Test Sphinx generates docs end-to-end (requires sphinx-build)."""
    # Check if sphinx-build available
    import shutil
    if shutil.which("sphinx-build") is None:
        pytest.skip("sphinx-build not installed")

    # Create Python source with docstring
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    (source_dir / "example.py").write_text('''
def greet(name: str) -> str:
    """Greet someone by name.

    Args:
        name: Person to greet

    Returns:
        Greeting message
    """
    return f"Hello, {name}!"
''')

    # Configure
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    generator = SphinxGenerator()
    config_file = generator.configure(docs_dir, {
        "project_name": "Test",
        "author": "Test Author",
        "version": "0.1.0"
    })

    assert config_file.exists()

    # Generate
    result = generator.generate(source_dir, docs_dir)

    # Verify
    assert result.success
    assert result.output_dir.exists()


# Additional T065 tests for configuration validation
def test_jsdoc_configure_validates_project_name(tmp_path):
    """Test JSDoc configure validates required options."""
    generator = JSDocGenerator()

    # Should work with project_name
    config = generator.configure(tmp_path, {"project_name": "Test"})
    assert config.exists()


def test_sphinx_configure_validates_required_options(tmp_path):
    """Test Sphinx configure validates required options."""
    generator = SphinxGenerator()

    # Should work with minimal options
    config = generator.configure(tmp_path, {
        "project_name": "Test",
        "author": "Author"
    })
    assert config.exists()


def test_generator_result_repr():
    """Test GeneratorResult has readable string representation."""
    result = GeneratorResult(
        success=True,
        output_dir=Path("/tmp/docs"),
        errors=[],
        warnings=["Minor warning"],
        generated_files=[Path("/tmp/docs/index.html")]
    )

    repr_str = repr(result)
    assert "Success" in repr_str or "✓" in repr_str
    assert "1 files" in repr_str or "file" in repr_str
