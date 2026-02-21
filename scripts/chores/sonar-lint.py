#!/usr/bin/env python3
"""Local Sonar-parity lint checks for selected Python rules.

Current rules:
- python:S3776 (Cognitive Complexity > 15)
- python:S1192 (Duplicated string literal >= 3 occurrences)
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


S3776_MAX_COMPLEXITY = 15
S1192_MIN_OCCURRENCES = 3
S1192_MIN_LITERAL_LENGTH = 5
EXCLUDED_DIRS = {".git", ".venv", "__pycache__", ".pytest_cache", ".worktrees"}


@dataclass(frozen=True)
class LintFinding:
    rule: str
    path: Path
    line: int
    message: str


def _iter_python_files(paths: list[Path]) -> Iterable[Path]:
    for path in paths:
        if path.is_file() and path.suffix == ".py":
            yield path
            continue
        if not path.is_dir():
            continue
        for candidate in path.rglob("*.py"):
            if any(part in EXCLUDED_DIRS for part in candidate.parts):
                continue
            yield candidate


class _CognitiveComplexityVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.score = 0
        self.nesting = 0

    def _add_decision(self, amount: int = 1) -> None:
        self.score += amount + self.nesting

    def _visit_block(self, body: list[ast.stmt], *, nested: bool = True) -> None:
        if nested:
            self.nesting += 1
        for node in body:
            self.visit(node)
        if nested:
            self.nesting -= 1

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        # Nested functions are measured independently.
        return None

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        # Nested functions are measured independently.
        return None

    def visit_If(self, node: ast.If) -> None:  # noqa: N802
        self._add_decision()
        self.score += _count_bool_ops(node.test)
        self._visit_block(node.body, nested=True)
        if len(node.orelse) == 1 and isinstance(node.orelse[0], ast.If):
            # elif: no extra nesting layer for the chain itself
            self.visit(node.orelse[0])
        elif node.orelse:
            self._visit_block(node.orelse, nested=True)

    def visit_IfExp(self, node: ast.IfExp) -> None:  # noqa: N802
        self._add_decision()
        self.score += _count_bool_ops(node.test)
        self.nesting += 1
        self.visit(node.body)
        self.visit(node.orelse)
        self.nesting -= 1

    def visit_For(self, node: ast.For) -> None:  # noqa: N802
        self._add_decision()
        self._visit_block(node.body, nested=True)
        if node.orelse:
            self._visit_block(node.orelse, nested=True)

    def visit_AsyncFor(self, node: ast.AsyncFor) -> None:  # noqa: N802
        self._add_decision()
        self._visit_block(node.body, nested=True)
        if node.orelse:
            self._visit_block(node.orelse, nested=True)

    def visit_While(self, node: ast.While) -> None:  # noqa: N802
        self._add_decision()
        self.score += _count_bool_ops(node.test)
        self._visit_block(node.body, nested=True)
        if node.orelse:
            self._visit_block(node.orelse, nested=True)

    def visit_Try(self, node: ast.Try) -> None:  # noqa: N802
        self._visit_block(node.body, nested=False)
        for handler in node.handlers:
            self._add_decision()
            self._visit_block(handler.body, nested=True)
        if node.orelse:
            self._visit_block(node.orelse, nested=True)
        if node.finalbody:
            self._visit_block(node.finalbody, nested=True)

    def visit_Match(self, node: ast.Match) -> None:  # noqa: N802
        for case in node.cases:
            self._add_decision()
            self._visit_block(case.body, nested=True)

    def visit_comprehension(self, node: ast.comprehension) -> None:  # noqa: N802
        self._add_decision()
        for clause in node.ifs:
            self._add_decision()
            self.score += _count_bool_ops(clause)
        self.generic_visit(node)


def _count_bool_ops(node: ast.AST) -> int:
    count = 0
    for child in ast.walk(node):
        if isinstance(child, ast.BoolOp):
            count += max(0, len(child.values) - 1)
    return count


def _function_complexity(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    visitor = _CognitiveComplexityVisitor()
    for stmt in node.body:
        visitor.visit(stmt)
    return visitor.score


def _find_s3776(path: Path, tree: ast.AST) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        score = _function_complexity(node)
        if score <= S3776_MAX_COMPLEXITY:
            continue
        findings.append(
            LintFinding(
                rule="python:S3776",
                path=path,
                line=node.lineno,
                message=(
                    f"Refactor function '{node.name}' to reduce cognitive complexity "
                    f"from {score} to <= {S3776_MAX_COMPLEXITY}."
                ),
            )
        )
    return findings


def _is_docstring_constant(node: ast.Constant, parent: ast.AST | None) -> bool:
    if not isinstance(node.value, str):
        return False
    if not isinstance(parent, ast.Expr):
        return False
    return True


def _find_s1192(path: Path, tree: ast.AST) -> list[LintFinding]:
    occurrences: dict[str, list[int]] = {}
    parent_map: dict[int, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            parent_map[id(child)] = parent

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        text = node.value.strip()
        if len(text) < S1192_MIN_LITERAL_LENGTH:
            continue
        parent = parent_map.get(id(node))
        if _is_docstring_constant(node, parent):
            continue
        occurrences.setdefault(text, []).append(node.lineno)

    findings: list[LintFinding] = []
    for literal, lines in occurrences.items():
        if len(lines) < S1192_MIN_OCCURRENCES:
            continue
        preview = literal if len(literal) <= 40 else literal[:37] + "..."
        findings.append(
            LintFinding(
                rule="python:S1192",
                path=path,
                line=lines[0],
                message=(
                    f"Define a constant instead of duplicating literal "
                    f"{preview!r} {len(lines)} times."
                ),
            )
        )
    return findings


def lint_paths(paths: list[Path]) -> list[LintFinding]:
    findings: list[LintFinding] = []
    for path in sorted(set(_iter_python_files(paths))):
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        try:
            tree = ast.parse(content, filename=str(path))
        except SyntaxError:
            continue
        findings.extend(_find_s3776(path, tree))
        findings.extend(_find_s1192(path, tree))
    return sorted(findings, key=lambda item: (str(item.path), item.line, item.rule))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run local Sonar-parity lint checks for selected Python rules."
    )
    parser.add_argument(
        "paths",
        nargs="*",
        default=["src"],
        help="Files/directories to lint (default: src)",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    paths = [Path(p).resolve() for p in args.paths]
    findings = lint_paths(paths)
    for finding in findings:
        print(
            f"{finding.path}:{finding.line}: {finding.rule}: {finding.message}"
        )
    if findings:
        print(
            f"\nFound {len(findings)} Sonar-parity lint issue(s) "
            f"(rules: python:S3776, python:S1192)."
        )
        return 1
    print("No Sonar-parity lint issues found (python:S3776, python:S1192).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
