#!/usr/bin/env python3
"""
Performance tests for GitignoreManager.

Tests that operations complete within the <1 second requirement.
"""

import sys
import tempfile
import time
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "specify_cli"))

import gitignore_manager
GitignoreManager = gitignore_manager.GitignoreManager


def test_performance_protect_all_agents():
    """Test that protect_all_agents completes in under 1 second."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        manager = GitignoreManager(project_path)

        # Measure time
        start_time = time.perf_counter()
        result = manager.protect_all_agents()
        elapsed = time.perf_counter() - start_time

        assert result.success, "Operation should succeed"
        assert elapsed < 1.0, f"Operation took {elapsed:.3f}s, should be <1s"

        print(f"✓ protect_all_agents completed in {elapsed:.3f}s")


def test_performance_with_large_gitignore():
    """Test performance with a large existing .gitignore file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        gitignore_path = project_path / ".gitignore"

        # Create large .gitignore (10,000 lines)
        large_content = "\n".join([f"pattern{i}/" for i in range(10000)])
        gitignore_path.write_text(large_content)

        manager = GitignoreManager(project_path)

        # Measure time
        start_time = time.perf_counter()
        result = manager.protect_all_agents()
        elapsed = time.perf_counter() - start_time

        assert result.success, "Operation should succeed"
        assert elapsed < 1.0, f"Large file operation took {elapsed:.3f}s, should be <1s"

        print(f"✓ Large file (10K lines) completed in {elapsed:.3f}s")


def test_performance_multiple_runs():
    """Test performance of multiple consecutive runs (idempotency)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        manager = GitignoreManager(project_path)

        # First run
        start1 = time.perf_counter()
        result1 = manager.protect_all_agents()
        elapsed1 = time.perf_counter() - start1

        # Second run (should be faster - just checking)
        start2 = time.perf_counter()
        result2 = manager.protect_all_agents()
        elapsed2 = time.perf_counter() - start2

        # Third run
        start3 = time.perf_counter()
        result3 = manager.protect_all_agents()
        elapsed3 = time.perf_counter() - start3

        assert elapsed1 < 1.0, f"First run took {elapsed1:.3f}s"
        assert elapsed2 < 1.0, f"Second run took {elapsed2:.3f}s"
        assert elapsed3 < 1.0, f"Third run took {elapsed3:.3f}s"

        print(f"✓ Multiple runs: {elapsed1:.3f}s, {elapsed2:.3f}s, {elapsed3:.3f}s")


def test_performance_selected_agents():
    """Test performance of protect_selected_agents."""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = Path(tmpdir)
        manager = GitignoreManager(project_path)

        # Test with various selections
        test_cases = [
            (["claude"], "single"),
            (["claude", "codex", "gemini"], "three"),
            (["claude", "codex", "gemini", "cursor", "qwen", "roo"], "six"),
        ]

        for agents, desc in test_cases:
            start_time = time.perf_counter()
            result = manager.protect_selected_agents(agents)
            elapsed = time.perf_counter() - start_time

            assert result.success, f"Operation should succeed for {desc}"
            assert elapsed < 1.0, f"Operation for {desc} took {elapsed:.3f}s"

            print(f"✓ protect_selected_agents ({desc}) completed in {elapsed:.3f}s")


def run_performance_tests():
    """Run all performance tests."""
    tests = [
        test_performance_protect_all_agents,
        test_performance_with_large_gitignore,
        test_performance_multiple_runs,
        test_performance_selected_agents,
    ]

    print("Running Performance Tests")
    print("=" * 40)
    print("Requirement: All operations must complete in <1 second")
    print()

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"✗ {test.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {test.__name__}: Unexpected error: {e}")
            failed += 1

    print()
    print("=" * 40)
    print(f"Results: {passed} passed, {failed} failed")

    if passed == len(tests):
        print("✅ Performance requirement met: All operations <1 second")
    else:
        print("❌ Performance requirement NOT met")

    return failed == 0


if __name__ == "__main__":
    success = run_performance_tests()
    sys.exit(0 if success else 1)