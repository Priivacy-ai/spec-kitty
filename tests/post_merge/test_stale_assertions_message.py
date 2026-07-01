"""Regression tests for message-content FP suppression in stale-assertion analyzer.

Covers FR-009: when a removed literal is the RHS of an ``in``/``not in``
comparison whose LHS is a message-capture expression, the finding must be
downgraded to ``info`` grade with label ``message-content-check`` rather than
emitted as a ``low``-confidence stale-assertion finding.

Also covers the ``changed_literals`` multi-site fix (T022): the same literal
removed across multiple source files must produce one finding per removal site.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.fast]

from specify_cli.post_merge.stale_assertions import (
    _SourceSymbol,
    _is_message_capture_expr,
    _literal_findings_for_assertion,
    _scan_test_file,
)
import ast


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_first_assert(source: str) -> ast.AST:
    """Return the first Assert node from *source*."""
    tree = ast.parse(textwrap.dedent(source))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assert):
            return node
    raise ValueError("No Assert node found in source")


def _make_sym(name: str, source_file: Path, line: int = 1) -> _SourceSymbol:
    return _SourceSymbol(name=name, kind="literal", source_file=source_file, source_line=line)


# ---------------------------------------------------------------------------
# Unit tests: _is_message_capture_expr
# ---------------------------------------------------------------------------

class TestIsMessageCaptureExpr:
    """Unit tests for the _is_message_capture_expr helper."""

    def _parse_expr(self, source: str) -> ast.expr:
        """Parse a single expression and return its AST node."""
        tree = ast.parse(source, mode="eval")
        assert isinstance(tree, ast.Expression)
        return tree.body

    def test_str_call_is_message_capture(self) -> None:
        node = self._parse_expr("str(exc)")
        assert _is_message_capture_expr(node)

    def test_repr_call_is_message_capture(self) -> None:
        node = self._parse_expr("repr(exc)")
        assert _is_message_capture_expr(node)

    def test_dot_message_is_message_capture(self) -> None:
        node = self._parse_expr("exc.message")
        assert _is_message_capture_expr(node)

    def test_dot_stderr_is_message_capture(self) -> None:
        node = self._parse_expr("result.stderr")
        assert _is_message_capture_expr(node)

    def test_dot_stdout_is_message_capture(self) -> None:
        node = self._parse_expr("result.stdout")
        assert _is_message_capture_expr(node)

    def test_dot_output_is_message_capture(self) -> None:
        node = self._parse_expr("proc.output")
        assert _is_message_capture_expr(node)

    def test_dot_value_is_message_capture(self) -> None:
        node = self._parse_expr("excinfo.value")
        assert _is_message_capture_expr(node)

    def test_capsys_readouterr_out_is_message_capture(self) -> None:
        node = self._parse_expr("capsys.readouterr().out")
        assert _is_message_capture_expr(node)

    def test_capsys_readouterr_err_is_message_capture(self) -> None:
        node = self._parse_expr("capsys.readouterr().err")
        assert _is_message_capture_expr(node)

    def test_plain_name_is_not_message_capture(self) -> None:
        node = self._parse_expr("some_set")
        assert not _is_message_capture_expr(node)

    def test_list_literal_is_not_message_capture(self) -> None:
        node = self._parse_expr("['a', 'b']")
        assert not _is_message_capture_expr(node)

    def test_dot_name_not_in_allowlist_is_not_message_capture(self) -> None:
        node = self._parse_expr("obj.some_other_attr")
        assert not _is_message_capture_expr(node)


# ---------------------------------------------------------------------------
# Unit tests: _literal_findings_for_assertion — message-capture FP suppression
# ---------------------------------------------------------------------------

class TestMessageCaptureFPSuppression:
    """FR-009: message-capture in-operator findings → info grade."""

    def _changed_literals(
        self, literal: str, source_file: Path, line: int = 1
    ) -> dict[str, list[_SourceSymbol]]:
        return {literal: [_make_sym(literal, source_file, line)]}

    def test_str_exc_in_assert_emits_info_not_low(self, tmp_path: Path) -> None:
        """assert "old text" in str(exc) → info grade, not low."""
        assertion = _parse_first_assert('assert "old text" in str(exc)')
        changed = self._changed_literals("old text", tmp_path / "src.py")
        findings = _literal_findings_for_assertion(assertion, 1, changed, tmp_path / "test.py")

        assert len(findings) == 1
        assert findings[0].confidence == "info"
        assert findings[0].label == "message-content-check"

    def test_repr_exc_in_assert_emits_info(self, tmp_path: Path) -> None:
        """assert "old text" in repr(exc) → info grade."""
        assertion = _parse_first_assert('assert "old text" in repr(exc)')
        changed = self._changed_literals("old text", tmp_path / "src.py")
        findings = _literal_findings_for_assertion(assertion, 1, changed, tmp_path / "test.py")

        assert len(findings) == 1
        assert findings[0].confidence == "info"
        assert findings[0].label == "message-content-check"

    def test_dot_message_emits_info(self, tmp_path: Path) -> None:
        """assert "old text" in exc.message → info grade."""
        assertion = _parse_first_assert('assert "old text" in exc.message')
        changed = self._changed_literals("old text", tmp_path / "src.py")
        findings = _literal_findings_for_assertion(assertion, 1, changed, tmp_path / "test.py")

        assert len(findings) == 1
        assert findings[0].confidence == "info"
        assert findings[0].label == "message-content-check"

    def test_dot_stderr_emits_info(self, tmp_path: Path) -> None:
        """assert "old text" in result.stderr → info grade."""
        assertion = _parse_first_assert('assert "old text" in result.stderr')
        changed = self._changed_literals("old text", tmp_path / "src.py")
        findings = _literal_findings_for_assertion(assertion, 1, changed, tmp_path / "test.py")

        assert len(findings) == 1
        assert findings[0].confidence == "info"

    def test_capsys_readouterr_out_emits_info(self, tmp_path: Path) -> None:
        """assert "old text" in capsys.readouterr().out → info grade."""
        assertion = _parse_first_assert('assert "old text" in capsys.readouterr().out')
        changed = self._changed_literals("old text", tmp_path / "src.py")
        findings = _literal_findings_for_assertion(assertion, 1, changed, tmp_path / "test.py")

        assert len(findings) == 1
        assert findings[0].confidence == "info"
        assert findings[0].label == "message-content-check"

    def test_plain_set_membership_still_emits_low(self, tmp_path: Path) -> None:
        """assert "old text" in some_set → still low confidence (not a message capture)."""
        assertion = _parse_first_assert('assert "old text" in some_set')
        changed = self._changed_literals("old text", tmp_path / "src.py")
        findings = _literal_findings_for_assertion(assertion, 1, changed, tmp_path / "test.py")

        assert len(findings) == 1
        assert findings[0].confidence == "low"
        assert findings[0].label == ""

    def test_equality_check_still_emits_low(self, tmp_path: Path) -> None:
        """assert result == "old text" → still low confidence."""
        assertion = _parse_first_assert('assert result == "old text"')
        changed = self._changed_literals("old text", tmp_path / "src.py")
        findings = _literal_findings_for_assertion(assertion, 1, changed, tmp_path / "test.py")

        assert len(findings) == 1
        assert findings[0].confidence == "low"

    def test_no_findings_when_literal_absent(self, tmp_path: Path) -> None:
        """No findings when the assertion does not contain the changed literal."""
        assertion = _parse_first_assert('assert "different text" in str(exc)')
        changed = self._changed_literals("old text", tmp_path / "src.py")
        findings = _literal_findings_for_assertion(assertion, 1, changed, tmp_path / "test.py")

        assert findings == []


# ---------------------------------------------------------------------------
# T022: changed_literals multi-site — all removal sites reported
# ---------------------------------------------------------------------------

class TestChangedLiteralsMultiSite:
    """T022: same literal removed from N source files → N findings emitted."""

    def test_three_removal_sites_produce_three_findings(self, tmp_path: Path) -> None:
        """A literal removed from 3 different source files produces 3 findings."""
        test_file = tmp_path / "test_sample.py"
        test_file.write_text(textwrap.dedent("""\
            def test_bad_request():
                assert result == "bad request"
        """))

        syms = [
            _make_sym("bad request", tmp_path / "module_a.py", line=10),
            _make_sym("bad request", tmp_path / "module_b.py", line=20),
            _make_sym("bad request", tmp_path / "module_c.py", line=30),
        ]
        findings = _scan_test_file(test_file, syms)

        # All 3 removal sites should be reported.
        assert len(findings) == 3, (
            f"Expected 3 findings (one per removal site), got {len(findings)}: {findings}"
        )
        source_files = {f.source_file.name for f in findings}
        assert source_files == {"module_a.py", "module_b.py", "module_c.py"}

    def test_two_different_literals_each_from_two_sites(self, tmp_path: Path) -> None:
        """Two different literals, each removed from 2 files → 4 findings total."""
        test_file = tmp_path / "test_sample.py"
        test_file.write_text(textwrap.dedent("""\
            def test_errors():
                assert result == "error alpha"
                assert result == "error beta"
        """))

        syms = [
            _make_sym("error alpha", tmp_path / "alpha_a.py", line=1),
            _make_sym("error alpha", tmp_path / "alpha_b.py", line=2),
            _make_sym("error beta", tmp_path / "beta_a.py", line=1),
            _make_sym("error beta", tmp_path / "beta_b.py", line=2),
        ]
        findings = _scan_test_file(test_file, syms)

        assert len(findings) == 4, (
            f"Expected 4 findings, got {len(findings)}: {findings}"
        )
        alpha_findings = [f for f in findings if f.changed_symbol == "error alpha"]
        beta_findings = [f for f in findings if f.changed_symbol == "error beta"]
        assert len(alpha_findings) == 2
        assert len(beta_findings) == 2

    def test_single_removal_site_still_works(self, tmp_path: Path) -> None:
        """Baseline: single removal site produces one finding (no regression)."""
        test_file = tmp_path / "test_sample.py"
        test_file.write_text(textwrap.dedent("""\
            def test_it():
                assert result == "old value"
        """))

        syms = [_make_sym("old value", tmp_path / "source.py", line=5)]
        findings = _scan_test_file(test_file, syms)

        assert len(findings) == 1
        assert findings[0].source_file.name == "source.py"
        assert findings[0].source_line == 5


# ---------------------------------------------------------------------------
# Integration: message-capture assertions in a full _scan_test_file call
# ---------------------------------------------------------------------------

class TestScanTestFileMessageCapture:
    """End-to-end: _scan_test_file demotes message-capture in-operator assertions."""

    def test_str_exc_in_assert_downgraded_to_info(self, tmp_path: Path) -> None:
        """Full scan: assert 'old msg' in str(exc) → info, not low."""
        test_file = tmp_path / "test_exc.py"
        test_file.write_text(textwrap.dedent("""\
            import pytest

            def test_raises_with_old_message():
                with pytest.raises(ValueError) as exc_info:
                    do_thing()
                assert "old error message" in str(exc_info.value)
        """))

        sym = _make_sym("old error message", tmp_path / "module.py", line=3)
        findings = _scan_test_file(test_file, [sym])

        assert len(findings) >= 1
        info_findings = [f for f in findings if f.confidence == "info"]
        assert len(info_findings) >= 1, (
            f"Expected at least one info-grade finding for message-capture assertion, "
            f"got: {findings}"
        )
        assert all(f.label == "message-content-check" for f in info_findings)
        # Must NOT have any high/medium findings for this literal.
        high_or_medium = [
            f for f in findings
            if f.confidence in ("high", "medium") and f.changed_symbol == "old error message"
        ]
        assert high_or_medium == [], (
            f"Message-capture assertion must not emit high/medium findings: {high_or_medium}"
        )

    def test_plain_equality_check_still_low(self, tmp_path: Path) -> None:
        """Full scan: assert result == 'old value' still emits low confidence."""
        test_file = tmp_path / "test_eq.py"
        test_file.write_text(textwrap.dedent("""\
            def test_value():
                assert result == "old value"
        """))

        sym = _make_sym("old value", tmp_path / "module.py", line=1)
        findings = _scan_test_file(test_file, [sym])

        low_findings = [f for f in findings if f.confidence == "low"]
        assert len(low_findings) >= 1

    def test_mixed_assertions_correct_grades(self, tmp_path: Path) -> None:
        """A test file with both kinds of assertions gets correct grades for each."""
        test_file = tmp_path / "test_mixed.py"
        test_file.write_text(textwrap.dedent("""\
            def test_eq():
                assert result == "old literal"

            def test_msg():
                assert "old literal" in str(exc)
        """))

        sym = _make_sym("old literal", tmp_path / "src.py", line=1)
        findings = _scan_test_file(test_file, [sym])

        confidences = {f.confidence for f in findings}
        # Should have at least one low (equality) and at least one info (message).
        assert "low" in confidences, f"Expected low-confidence finding, got: {findings}"
        assert "info" in confidences, f"Expected info-confidence finding, got: {findings}"
