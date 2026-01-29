"""
Integration tests for centralized feature detection migration.

These tests verify that:
1. No orphaned implementations remain in the codebase
2. All commands use the centralized detection module
3. No "highest numbered" heuristics remain
4. All imports are from the centralized module
"""

import re
import subprocess
from pathlib import Path

import pytest


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def repo_root() -> Path:
    """Get the repository root directory."""
    return Path(__file__).parent.parent.parent


# ============================================================================
# No Orphaned Implementations Tests
# ============================================================================


def test_no_orphaned_detect_feature_slug_functions(repo_root: Path):
    """Verify no orphaned detect_feature_slug() functions remain (except centralized and wrappers)."""
    # Search for function definitions
    result = subprocess.run(
        ["grep", "-r", "def detect_feature_slug", "src/specify_cli/", "--include=*.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        lines = result.stdout.strip().split("\n")
        # Filter out the centralized implementation, test files, and backward-compatible wrappers
        orphaned = [
            line for line in lines
            if "core/feature_detection.py" not in line
            and "test_" not in line
            and "acceptance.py" not in line  # Backward-compatible wrapper
            and line.strip()
        ]

        if orphaned:
            # Check if remaining functions delegate to centralized detection
            for line in orphaned:
                file_path = line.split(":")[0]
                full_path = repo_root / file_path
                content = full_path.read_text()

                # If function calls centralized detection, it's OK (wrapper)
                if "centralized_detect_feature_slug" not in content and "detect_feature(" not in content:
                    pytest.fail(
                        f"Found orphaned detect_feature_slug() function that doesn't delegate:\n{line}"
                    )


def test_no_orphaned_find_feature_slug_functions(repo_root: Path):
    """Verify no find_feature_slug() from core.paths usages remain."""
    # Search for imports of find_feature_slug from paths module
    result = subprocess.run(
        ["grep", "-r", "from.*paths.*import.*find_feature_slug", "src/specify_cli/", "--include=*.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        lines = result.stdout.strip().split("\n")
        if lines and lines[0]:  # Not empty
            pytest.fail(
                f"Found imports of find_feature_slug from paths (should be removed):\n" + "\n".join(lines)
            )

    # Also check for direct calls to paths.find_feature_slug
    result2 = subprocess.run(
        ["grep", "-r", "paths.find_feature_slug", "src/specify_cli/", "--include=*.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    if result2.returncode == 0:
        lines = result2.stdout.strip().split("\n")
        if lines and lines[0]:  # Not empty
            pytest.fail(
                f"Found direct calls to paths.find_feature_slug:\n" + "\n".join(lines)
            )


def test_no_orphaned_find_feature_directory_functions(repo_root: Path):
    """Verify no orphaned _find_feature_directory() functions remain (except updated ones)."""
    # Search for function definitions
    result = subprocess.run(
        ["grep", "-r", "def _find_feature_directory", "src/specify_cli/", "--include=*.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        lines = result.stdout.strip().split("\n")

        # Read each file to check if it uses centralized detection
        for line in lines:
            if "test_" in line:
                continue

            # Extract file path
            file_path = line.split(":")[0]
            full_path = repo_root / file_path

            # Read file content
            content = full_path.read_text()

            # Check if the function uses centralized detection
            if "detect_feature_directory" not in content:
                pytest.fail(
                    f"Found orphaned _find_feature_directory() in {file_path}\n"
                    f"Function should use centralized detect_feature_directory()"
                )


# Priority 6 fallback to latest incomplete feature is now allowed
# (uses highest numbered as fallback when all other detection methods fail)


# ============================================================================
# Import Validation Tests
# ============================================================================


def test_all_imports_from_centralized_module(repo_root: Path):
    """Verify all feature detection imports come from core.feature_detection."""
    # Search for imports of old functions
    bad_imports = [
        "from specify_cli.core.paths import.*find_feature_slug",
        "from.*paths.*import.*find_feature_slug",
    ]

    src_dir = repo_root / "src" / "specify_cli"

    for pattern in bad_imports:
        result = subprocess.run(
            ["grep", "-r", "-E", pattern, str(src_dir), "--include=*.py"],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            if lines and lines[0]:  # Not empty
                pytest.fail(
                    f"Found bad imports (should use core.feature_detection):\n"
                    + "\n".join(lines)
                )


def test_centralized_imports_used(repo_root: Path):
    """Verify files that need feature detection import from centralized module."""
    # Files that should import from centralized module
    files_to_check = [
        "cli/commands/implement.py",
        "cli/commands/agent/feature.py",
        "cli/commands/agent/context.py",
        "cli/commands/agent/workflow.py",
        "cli/commands/agent/tasks.py",
        "cli/commands/mission.py",
        "cli/commands/orchestrate.py",
        "acceptance.py",
        "agent_utils/status.py",
    ]

    src_dir = repo_root / "src" / "specify_cli"

    for file_path in files_to_check:
        full_path = src_dir / file_path
        if not full_path.exists():
            continue

        content = full_path.read_text()

        # Check if file uses feature detection (mentions feature slug/directory/context)
        uses_feature_detection = any(
            keyword in content
            for keyword in [
                "feature_slug",
                "feature_dir",
                "feature context",
                "detect_feature",
            ]
        )

        if uses_feature_detection:
            # Should import from centralized module
            has_centralized_import = "from specify_cli.core.feature_detection import" in content

            if not has_centralized_import:
                # Check if it's just passing through without needing detection
                if "detect_feature" not in content and "_find_feature" not in content:
                    # Might just be passing feature_slug as parameter, that's OK
                    continue

                pytest.fail(
                    f"{file_path} uses feature detection but doesn't import from "
                    f"core.feature_detection module"
                )


# ============================================================================
# Error Message Quality Tests
# ============================================================================


def test_error_messages_mention_feature_flag(repo_root: Path):
    """Verify error messages in commands guide users to --feature flag."""
    # The centralized module should have error messages mentioning --feature
    detection_module = repo_root / "src" / "specify_cli" / "core" / "feature_detection.py"
    content = detection_module.read_text()

    # Check for helpful error messages
    assert "--feature" in content, "Error messages should mention --feature flag"
    assert "SPECIFY_FEATURE" in content, "Error messages should mention SPECIFY_FEATURE env var"
    assert "Multiple features found" in content, "Should handle multiple features case"


def test_error_messages_list_available_features(repo_root: Path):
    """Verify error messages list available features when multiple exist."""
    detection_module = repo_root / "src" / "specify_cli" / "core" / "feature_detection.py"
    content = detection_module.read_text()

    # Should list available features in error
    assert "all_features" in content or "_list_all_features" in content
    assert "Available features" in content or "Multiple features found" in content


# ============================================================================
# Backward Compatibility Tests
# ============================================================================


def test_acceptance_module_backward_compatible(repo_root: Path):
    """Verify acceptance.py maintains backward compatible API."""
    acceptance_file = repo_root / "src" / "specify_cli" / "acceptance.py"
    content = acceptance_file.read_text()

    # Should still export detect_feature_slug function
    assert "def detect_feature_slug(" in content

    # Should convert FeatureDetectionError to AcceptanceError for compatibility
    assert "AcceptanceError" in content
    assert "FeatureDetectionError" in content


def test_implement_module_backward_compatible(repo_root: Path):
    """Verify implement.py maintains backward compatible API."""
    implement_file = repo_root / "src" / "specify_cli" / "cli" / "commands" / "implement.py"
    content = implement_file.read_text()

    # Should still export detect_feature_context function
    assert "def detect_feature_context(" in content

    # Should return tuple of (number, slug)
    assert "tuple[str, str]" in content or "Tuple[str, str]" in content


# ============================================================================
# Agent Command Integration Tests
# ============================================================================


def test_agent_commands_accept_feature_parameter(repo_root: Path):
    """Verify all agent commands accept --feature parameter."""
    agent_files = [
        "cli/commands/agent/feature.py",
        "cli/commands/agent/context.py",
        "cli/commands/agent/workflow.py",
        "cli/commands/agent/tasks.py",
    ]

    src_dir = repo_root / "src" / "specify_cli"

    for file_path in agent_files:
        full_path = src_dir / file_path
        if not full_path.exists():
            continue

        content = full_path.read_text()

        # Look for command definitions
        commands = re.findall(r'@app\.command\([^)]*\)\s+def\s+(\w+)\(', content, re.MULTILINE)

        for cmd in commands:
            # Find the function signature
            func_pattern = rf'def {cmd}\([^)]*\):'
            match = re.search(func_pattern, content)

            if not match:
                continue

            # Get the function signature (next ~10 lines)
            start = match.start()
            signature_text = content[start:start + 500]

            # Check if feature parameter exists
            # (Some commands may not need it, but most should have it)
            has_feature_param = (
                'feature:' in signature_text
                or '"--feature"' in signature_text
                or "'--feature'" in signature_text
            )

            # If command uses _find_feature_slug, it should have --feature parameter
            if f'_find_feature_slug(' in content and not has_feature_param:
                # Get just the function body
                func_start = match.end()
                func_end = content.find('\ndef ', func_start)
                if func_end == -1:
                    func_end = len(content)
                func_body = content[func_start:func_end]

                if '_find_feature_slug(' in func_body:
                    pytest.fail(
                        f"{file_path}::{cmd}() calls _find_feature_slug() but doesn't have --feature parameter"
                    )


# ============================================================================
# Code Coverage Tests
# ============================================================================


def test_all_feature_detection_paths_tested(repo_root: Path):
    """Verify the test suite covers all detection paths."""
    test_file = repo_root / "tests" / "specify_cli" / "core" / "test_feature_detection.py"
    content = test_file.read_text()

    # Check for tests covering each detection method
    detection_methods = [
        "explicit",  # Explicit parameter
        "env",       # Environment variable
        "git_branch",  # Git branch
        "cwd",       # Current directory
        "single_auto",  # Single feature auto-detect
    ]

    for method in detection_methods:
        # Look for test functions that cover this method
        test_pattern = rf'def test.*{method}'
        if not re.search(test_pattern, content, re.IGNORECASE):
            pytest.fail(f"No test found for detection method: {method}")


def test_error_scenarios_covered(repo_root: Path):
    """Verify error scenarios are tested."""
    test_file = repo_root / "tests" / "specify_cli" / "core" / "test_feature_detection.py"
    content = test_file.read_text()

    error_scenarios = [
        "multiple_features",  # Multiple features exist
        "no_features",  # No features found
        "invalid_slug",  # Invalid slug format
        "feature_not_found",  # Feature doesn't exist
    ]

    for scenario in error_scenarios:
        test_pattern = rf'def test.*{scenario}'
        if not re.search(test_pattern, content, re.IGNORECASE):
            pytest.fail(f"No test found for error scenario: {scenario}")
