"""TDD-verify for #1888 — phantom path existence check in ownership validation.

Issue #1888: finalize-tasks ownership validation accepted non-glob ``owned_files``
paths that did not exist (pattern-validated, never existence-checked).  The exact
bug: a literal path like ``src/specify_cli/no_such_file.py`` declared in
``owned_files`` with no matching file in the repository was silently passed with no
warning or error.

Repro test (T022): write the failing test for the exact phantom-path case first.
- If it PASSES on HEAD  → fix already landed (verify-and-close evidence).
- If it FAILS on HEAD   → gap exists; add the missing check in T023.

Scoping rules enforced:
- Literal paths in ``owned_files`` that match zero files → hard error.
- Literal paths in ``owned_files`` that appear in ``create_intent`` → suppressed
  (planned-new-file; not an error).
- Glob patterns (contain *, ?, [, {) that match zero files → soft warning only.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from specify_cli.ownership.models import ExecutionMode, OwnershipManifest
from specify_cli.ownership.validation import validate_glob_matches

pytestmark = [pytest.mark.unit, pytest.mark.fast]


# ---------------------------------------------------------------------------
# T022 — #1888 exact repro: phantom literal path silently accepted (bug)
# ---------------------------------------------------------------------------


class TestPhantomPathExistenceCheck:
    """#1888 repro: literal owned_files paths that don't exist must be rejected."""

    def test_phantom_literal_path_is_hard_error(self, tmp_path: Path) -> None:
        """#1888 exact repro: a non-existent literal path must produce a hard error.

        Before the fix: ``validate_glob_matches`` silently passed a literal
        ``owned_files`` path that matched zero files in the repository, giving
        no indication to the operator that the declared path was phantom.

        After the fix (commit 991162c0a): the function emits a hard error
        (``result.passed == False``) and the error text identifies the
        offending path.
        """
        phantom = "src/specify_cli/non_existent_module.py"

        manifests = {
            "WP01": OwnershipManifest(
                owned_files=(phantom,),
                authoritative_surface="src/specify_cli/",
                execution_mode=ExecutionMode.CODE_CHANGE,
            )
        }

        result = validate_glob_matches(manifests, tmp_path)

        assert not result.passed, (
            f"#1888 bug: phantom literal path '{phantom}' was silently accepted. "
            "Expected a hard error; got none."
        )
        assert result.errors, "Expected at least one error message for the phantom path."
        assert any(phantom in e for e in result.errors), (
            f"Error message must name the offending path '{phantom}'. "
            f"Got: {result.errors!r}"
        )

    def test_phantom_path_error_includes_create_intent_hint(self, tmp_path: Path) -> None:
        """The error for a missing literal path must guide the operator to create_intent."""
        phantom = "src/specify_cli/planned_but_absent.py"

        manifests = {
            "WP02": OwnershipManifest(
                owned_files=(phantom,),
                authoritative_surface="src/specify_cli/",
                execution_mode=ExecutionMode.CODE_CHANGE,
            )
        }

        result = validate_glob_matches(manifests, tmp_path)

        assert not result.passed
        error_text = " ".join(result.errors)
        assert "create_intent" in error_text, (
            "Error for missing literal path must mention 'create_intent' so the "
            f"operator knows how to suppress it for planned-new-files. Got: {error_text!r}"
        )

    def test_phantom_path_suppressed_by_create_intent(self, tmp_path: Path) -> None:
        """A literal path listed under create_intent must NOT be a hard error.

        The scoping rule: if a file does not exist *yet* but the WP declares it in
        create_intent (planned-new-file), the zero-match must be suppressed — only
        an informational note is emitted.  This ensures that declaring future files
        in owned_files does not break finalize-tasks.
        """
        future_path = "src/specify_cli/new_planned_module.py"

        manifests = {
            "WP03": OwnershipManifest(
                owned_files=(future_path,),
                authoritative_surface="src/specify_cli/",
                execution_mode=ExecutionMode.CODE_CHANGE,
            )
        }
        create_intent = {"WP03": [future_path]}

        result = validate_glob_matches(manifests, tmp_path, create_intent=create_intent)

        assert result.passed, (
            f"A future file declared in create_intent must NOT be a hard error. "
            f"Got errors: {result.errors!r}"
        )
        assert not result.errors, (
            f"create_intent-suppressed path must produce zero errors. Got: {result.errors!r}"
        )

    def test_glob_zero_match_remains_warning_not_error(self, tmp_path: Path) -> None:
        """Glob pattern zero-matches must remain warnings, not hard errors.

        Distinction: ``**`` and ``*`` patterns may match zero files legitimately
        (in-flight work, empty directories).  They must never become hard errors.
        """
        manifests = {
            "WP04": OwnershipManifest(
                owned_files=("src/specify_cli/nonexistent/**",),
                authoritative_surface="src/specify_cli/",
                execution_mode=ExecutionMode.CODE_CHANGE,
            )
        }

        result = validate_glob_matches(manifests, tmp_path)

        assert result.passed, (
            "Glob zero-match must remain a soft warning, not a hard error. "
            f"Unexpected errors: {result.errors!r}"
        )
        assert result.warnings, "Expected a warning for the glob zero-match."

    def test_existing_literal_path_passes_cleanly(self, tmp_path: Path) -> None:
        """A literal path that actually exists must pass with no errors or warnings."""
        src_dir = tmp_path / "src" / "specify_cli"
        src_dir.mkdir(parents=True)
        real_file = src_dir / "real_module.py"
        real_file.write_text("# real\n", encoding="utf-8")

        manifests = {
            "WP05": OwnershipManifest(
                owned_files=("src/specify_cli/real_module.py",),
                authoritative_surface="src/specify_cli/",
                execution_mode=ExecutionMode.CODE_CHANGE,
            )
        }

        result = validate_glob_matches(manifests, tmp_path)

        assert result.passed, f"Existing literal path must pass. Errors: {result.errors!r}"
        assert not result.errors
        assert not result.warnings
