"""Stale-assertion analyzer for post-merge reliability.

Compares two git refs (typically merge-base and HEAD) and emits a structured
report listing test assertions likely invalidated by merged source changes.

Uses stdlib ``ast`` on both source and test files — no regex on test text,
no libcst, no tree-sitter, no test-suite execution (FR-002).

Algorithm overview:
  1. ``git diff base_ref..head_ref -- '*.py'`` → list of changed source files
  2. For each changed file, parse both revisions with ``ast.parse`` and extract
     changed identifiers (function/class names) and changed string literals.
  3. For each test file from ``git ls-files 'tests/**/*.py'``, parse with ``ast``
     and find assertion-bearing nodes that reference changed identifiers.
  4. Assign confidence per FR-003 rules; never produce "definitely_stale".
  5. Populate ``StaleAssertionReport`` with findings + self-monitoring metrics.
"""

from __future__ import annotations

import ast
import subprocess
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

# ---------------------------------------------------------------------------
# Public types (re-exported from __init__.py)
# ---------------------------------------------------------------------------

Confidence = Literal["high", "medium", "low"]

# FR-003: never produce this value — it is listed here only to document what
# the analyzer MUST NOT emit.
_FORBIDDEN_CONFIDENCE = "definitely_stale"

FP_CEILING = 5.0  # NFR-002: max findings per 100 LOC of merged change


@dataclass(frozen=True)
class StaleAssertionFinding:
    """A single test assertion that may be invalidated by a source change."""

    test_file: Path       # absolute path to the test file
    test_line: int        # 1-indexed line of the suspect assertion
    source_file: Path     # absolute path to the source file that changed
    source_line: int      # 1-indexed line of the changed source identifier
    changed_symbol: str   # the identifier or literal that changed
    confidence: Confidence  # "high" | "medium" | "low"
    hint: str             # one-line human-readable explanation (no newlines)

    def __post_init__(self) -> None:
        assert self.confidence in ("high", "medium", "low"), (
            f"confidence must be 'high', 'medium', or 'low', got {self.confidence!r}"
        )
        assert "\n" not in self.hint, "hint must be a single line"


@dataclass(frozen=True)
class StaleAssertionReport:
    """Aggregated results of a stale-assertion analysis run."""

    base_ref: str
    head_ref: str
    repo_root: Path
    findings: list[StaleAssertionFinding]
    elapsed_seconds: float    # for NFR-001 self-reporting
    files_scanned: int        # count of test files parsed successfully
    findings_per_100_loc: float  # for NFR-002 self-monitoring


# ---------------------------------------------------------------------------
# Internal helper types
# ---------------------------------------------------------------------------

@dataclass
class _SourceSymbol:
    """An identifier or literal that was removed/changed in the source diff."""

    name: str            # function/class name OR literal string value
    kind: Literal["identifier", "literal"]
    source_file: Path    # absolute path
    source_line: int     # 1-indexed line in base_ref version


# ---------------------------------------------------------------------------
# T002 — Source-side AST extraction
# ---------------------------------------------------------------------------

def _git_run(args: list[str], cwd: Path) -> str:
    """Run a git command and return stdout, raising on non-zero exit."""
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {result.returncode}):\n{result.stderr}"
        )
    return result.stdout


def _parse_safely(source_text: str, filename: str = "<unknown>") -> ast.AST | None:
    """Parse Python source with ast.parse; return None on SyntaxError."""
    try:
        return ast.parse(source_text, filename=filename)
    except SyntaxError as exc:
        warnings.warn(
            f"SyntaxError while parsing {filename}: {exc}",
            stacklevel=2,
        )
        return None


def _extract_identifiers(tree: ast.AST) -> set[tuple[str, int]]:
    """Return {(name, lineno)} for all function/class definitions in a tree."""
    names: set[tuple[str, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add((node.name, node.lineno))
    return names


def _extract_string_literals(tree: ast.AST) -> set[tuple[str, int]]:
    """Return {(value, lineno)} for all string Constant nodes in a tree."""
    literals: set[tuple[str, int]] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            literals.add((node.value, node.lineno))
    return literals


def _extract_changed_symbols(
    base_ref: str,
    head_ref: str,
    repo_root: Path,
) -> list[_SourceSymbol]:
    """Compare base_ref..head_ref and return identifiers/literals that were removed.

    "Removed" means present in base_ref but absent in head_ref for a given file.
    These are the symbols that assertions might reference and that may now be stale.
    """
    # Get list of changed Python source files, excluding tests/ directory.
    diff_output = _git_run(
        ["diff", "--name-only", base_ref, head_ref, "--", "*.py"],
        cwd=repo_root,
    )
    changed_files = [
        line.strip()
        for line in diff_output.splitlines()
        if line.strip() and not line.strip().startswith("tests/")
    ]

    symbols: list[_SourceSymbol] = []

    for rel_path in changed_files:
        abs_path = repo_root / rel_path

        # Get file content at both refs; silently skip if not available.
        try:
            base_content = _git_run(["show", f"{base_ref}:{rel_path}"], cwd=repo_root)
        except RuntimeError:
            base_content = ""

        try:
            head_content = _git_run(["show", f"{head_ref}:{rel_path}"], cwd=repo_root)
        except RuntimeError:
            head_content = ""

        base_tree = _parse_safely(base_content, rel_path) if base_content else None
        head_tree = _parse_safely(head_content, rel_path) if head_content else None

        if base_tree is None:
            continue

        # Identifiers present in base but absent in head → renamed/removed.
        base_ids = _extract_identifiers(base_tree)
        head_ids = _extract_identifiers(head_tree) if head_tree else set()
        base_id_names = {name for name, _ in base_ids}
        head_id_names = {name for name, _ in head_ids}
        removed_ids = base_id_names - head_id_names

        for name, lineno in base_ids:
            if name in removed_ids:
                symbols.append(
                    _SourceSymbol(
                        name=name,
                        kind="identifier",
                        source_file=abs_path,
                        source_line=lineno,
                    )
                )

        # String literals present in base but absent in head.
        base_lits = _extract_string_literals(base_tree)
        head_lits = _extract_string_literals(head_tree) if head_tree else set()
        base_lit_vals = {val for val, _ in base_lits}
        head_lit_vals = {val for val, _ in head_lits}
        removed_lits = base_lit_vals - head_lit_vals

        for val, lineno in base_lits:
            if val in removed_lits:
                symbols.append(
                    _SourceSymbol(
                        name=val,
                        kind="literal",
                        source_file=abs_path,
                        source_line=lineno,
                    )
                )

    return symbols


# ---------------------------------------------------------------------------
# T003 — Test-side AST scan
# ---------------------------------------------------------------------------

_UNITTEST_ASSERT_PREFIXES = frozenset({
    "assertEqual",
    "assertNotEqual",
    "assertTrue",
    "assertFalse",
    "assertIs",
    "assertIsNot",
    "assertIsNone",
    "assertIsNotNone",
    "assertIn",
    "assertNotIn",
    "assertRaises",
    "assertRaisesRegex",
    "assertWarns",
    "assertWarnsRegex",
    "assertGreater",
    "assertGreaterEqual",
    "assertLess",
    "assertLessEqual",
    "assertRegex",
    "assertNotRegex",
    "assertCountEqual",
    "assertMultiLineEqual",
    "assertSequenceEqual",
    "assertListEqual",
    "assertTupleEqual",
    "assertSetEqual",
    "assertDictEqual",
})


def _node_is_assertion_bearing(node: ast.expr | ast.stmt | ast.AST) -> bool:
    """Return True if the node is an assertion-bearing position.

    An assertion-bearing position is:
    - An ``Assert`` statement
    - A ``Call`` whose func is ``Attribute(attr='assert*')``
    """
    if isinstance(node, ast.Assert):
        return True
    if isinstance(node, ast.Call):
        func = node.func
        if isinstance(func, ast.Attribute) and (
            func.attr in _UNITTEST_ASSERT_PREFIXES or func.attr.startswith("assert")
        ):
            return True
    return False


def _collect_assertion_nodes(tree: ast.AST) -> list[ast.AST]:
    """Return all AST nodes that are in assertion-bearing positions."""
    result: list[ast.AST] = []
    for node in ast.walk(tree):
        if _node_is_assertion_bearing(node):
            result.append(node)
    return result


def _names_in_subtree(node: ast.AST) -> set[str]:
    """Return all Name.id and Attribute.attr values in a subtree."""
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Name):
            names.add(child.id)
        elif isinstance(child, ast.Attribute):
            names.add(child.attr)
    return names


def _constants_in_subtree(node: ast.AST) -> set[str]:
    """Return all string Constant values in a subtree."""
    values: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Constant) and isinstance(child.value, str):
            values.add(child.value)
    return values


def _get_node_line(node: ast.AST) -> int:
    """Return the line number of an AST node, defaulting to 0 if unavailable."""
    return getattr(node, "lineno", 0)


def _is_directly_inside_assert(
    node: ast.AST, assertion: ast.AST
) -> bool:
    """Return True if node appears as a direct child of an Assert.test or assertEqual call.

    Used to distinguish high vs. medium confidence.
    """
    if isinstance(assertion, ast.Assert):
        test = assertion.test
        # Direct Name or Attribute in the test expression.
        if isinstance(test, ast.Name) and isinstance(node, ast.Name):
            return test.id == node.id  # type: ignore[attr-defined]
        if isinstance(test, ast.Attribute) and isinstance(node, ast.Attribute):
            return test.attr == node.attr  # type: ignore[attr-defined]
        # Walk one level: Compare, BoolOp, etc.
        for direct_child in ast.iter_child_nodes(test):
            if isinstance(direct_child, ast.Name) and isinstance(node, ast.Name) and direct_child.id == node.id:  # type: ignore[attr-defined]
                return True
            if isinstance(direct_child, ast.Attribute) and isinstance(node, ast.Attribute) and direct_child.attr == node.attr:  # type: ignore[attr-defined]
                return True
    return False


def _scan_test_file(
    test_path: Path,
    changed_symbols: list[_SourceSymbol],
) -> list[StaleAssertionFinding]:
    """Parse a single test file and return findings for changed symbols.

    Uses ast.parse only — never reads the file as raw text or executes it.
    """
    findings: list[StaleAssertionFinding] = []

    try:
        source = test_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return findings

    tree = _parse_safely(source, str(test_path))
    if tree is None:
        return findings

    assertion_nodes = _collect_assertion_nodes(tree)

    # Build lookup sets for efficiency.
    changed_identifiers = {
        sym.name: sym for sym in changed_symbols if sym.kind == "identifier"
    }
    changed_literals = {
        sym.name: sym for sym in changed_symbols if sym.kind == "literal"
    }

    for assertion in assertion_nodes:
        line = _get_node_line(assertion)

        # --- Identifier matches ---
        names_in_assertion = _names_in_subtree(assertion)
        for sym_name, sym in changed_identifiers.items():
            if sym_name in names_in_assertion:
                # Determine confidence: high if directly inside Assert/assert*,
                # medium otherwise.
                confidence: Confidence = "medium"
                if isinstance(assertion, ast.Assert):
                    # Check whether the identifier appears directly in test.test
                    test_node = assertion.test
                    direct_names = _names_in_subtree(test_node)
                    if sym_name in direct_names:
                        # Treat as "directly inside assert" → high
                        confidence = "high"
                elif isinstance(assertion, ast.Call):
                    # Direct arg reference → high
                    for arg in assertion.args:
                        if sym_name in _names_in_subtree(arg):
                            confidence = "high"
                            break
                    else:
                        for kw in assertion.keywords:
                            if sym_name in _names_in_subtree(kw.value):
                                confidence = "high"
                                break

                findings.append(
                    StaleAssertionFinding(
                        test_file=test_path,
                        test_line=line,
                        source_file=sym.source_file,
                        source_line=sym.source_line,
                        changed_symbol=sym_name,
                        confidence=confidence,
                        hint=(
                            f"Assertion references '{sym_name}' which was renamed/removed "
                            f"in {sym.source_file.name}:{sym.source_line}"
                        ),
                    )
                )

        # --- Literal matches ---
        constants_in_assertion = _constants_in_subtree(assertion)
        for lit_val, sym in changed_literals.items():
            if lit_val in constants_in_assertion:
                findings.append(
                    StaleAssertionFinding(
                        test_file=test_path,
                        test_line=line,
                        source_file=sym.source_file,
                        source_line=sym.source_line,
                        changed_symbol=lit_val,
                        confidence="low",
                        hint=(
                            f"Assertion contains string literal {lit_val!r} which was "
                            f"removed from {sym.source_file.name}:{sym.source_line}"
                        ),
                    )
                )

    return findings


# ---------------------------------------------------------------------------
# T004 — run_check() orchestration
# ---------------------------------------------------------------------------

def _count_diff_loc(base_ref: str, head_ref: str, repo_root: Path) -> int:
    """Return the number of lines added+removed in the diff (for NFR-002)."""
    try:
        output = _git_run(
            ["diff", "--shortstat", base_ref, head_ref, "--", "*.py"],
            cwd=repo_root,
        )
        # Example: " 3 files changed, 42 insertions(+), 7 deletions(-)"
        insertions = 0
        deletions = 0
        for token in output.split(","):
            token = token.strip()
            if "insertion" in token:
                insertions = int(token.split()[0])
            elif "deletion" in token:
                deletions = int(token.split()[0])
        return insertions + deletions
    except (RuntimeError, ValueError):
        return 0


def run_check(
    base_ref: str,
    head_ref: str,
    repo_root: Path,
) -> StaleAssertionReport:
    """Compare base_ref..head_ref and return likely-stale test assertions.

    Algorithm:
      1. git diff base_ref..head_ref -- '*.py' → list of changed source files
      2. For each changed file, parse both revisions with ast and extract
         changed identifiers (function/class names) and changed string literals.
      3. For each test file from ``git ls-files 'tests/**/*.py'``, parse with ast
         and walk for assertion-bearing nodes referencing changed identifiers.
      4. Assign confidence per FR-003 rules (never "definitely_stale").
      5. Compute findings_per_100_loc against the changed-line count.

    Args:
        base_ref: Git ref for the base (e.g., merge-base SHA or "HEAD~1").
        head_ref: Git ref for the head (e.g., "HEAD").
        repo_root: Absolute path to the repository root.

    Returns:
        StaleAssertionReport with findings list, elapsed_seconds,
        files_scanned, and findings_per_100_loc populated.
    """
    start_time = time.monotonic()

    # Step 1+2: extract changed symbols from source side.
    changed_symbols = _extract_changed_symbols(base_ref, head_ref, repo_root)

    # Step 3: enumerate test files.
    try:
        ls_output = _git_run(
            ["ls-files", "tests/"],
            cwd=repo_root,
        )
        test_files = [
            repo_root / line.strip()
            for line in ls_output.splitlines()
            if line.strip().endswith(".py")
        ]
    except RuntimeError:
        test_files = []

    # Step 4: scan each test file.
    all_findings: list[StaleAssertionFinding] = []
    files_scanned = 0

    if changed_symbols:
        for tf in test_files:
            file_findings = _scan_test_file(tf, changed_symbols)
            all_findings.extend(file_findings)
            files_scanned += 1
    else:
        # No changed symbols → nothing to scan; still count files.
        files_scanned = len(test_files)

    # Step 5: compute metrics.
    elapsed_seconds = time.monotonic() - start_time
    loc_changed = _count_diff_loc(base_ref, head_ref, repo_root)
    findings_per_100_loc: float = (
        (len(all_findings) / loc_changed * 100.0) if loc_changed > 0 else 0.0
    )

    # FR-022: self-monitoring warning if FP ceiling exceeded.
    if findings_per_100_loc > FP_CEILING:
        warnings.warn(
            f"stale-assertion analyzer: findings_per_100_loc={findings_per_100_loc:.1f} "
            f"exceeds NFR-002 ceiling of {FP_CEILING}. "
            "Consider narrowing scope to function-rename detection only (FR-022).",
            UserWarning,
            stacklevel=2,
        )

    return StaleAssertionReport(
        base_ref=base_ref,
        head_ref=head_ref,
        repo_root=repo_root,
        findings=all_findings,
        elapsed_seconds=elapsed_seconds,
        files_scanned=files_scanned,
        findings_per_100_loc=findings_per_100_loc,
    )
