"""Gate 2: portable dead-code scan."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console

from ._diagnostics import MissionReviewDiagnostic

_IDENTIFIER_CHARCLASS = r"\w"
_UNDETERMINABLE_REMEDIATION = (
    "Verify the baseline commit and Git repository, then rerun `spec-kitty review`."
)
_EXCLUDED_CORPUS_PARTS = frozenset(
    {
        ".git",
        ".nox",
        ".pytest_cache",
        ".tox",
        ".venv",
        ".worktrees",
        "node_modules",
        "venv",
    }
)


@dataclass(frozen=True)
class _Discovery:
    """Result of baseline-to-HEAD symbol discovery."""

    changed_paths: tuple[str, ...]
    symbols: tuple[tuple[str, str], ...]
    error: str | None = None


def _run_git_diff(
    repo_root: Path,
    baseline_merge_commit: str,
    *diff_args: str,
) -> subprocess.CompletedProcess[str] | None:
    """Run a deterministic Git diff, returning ``None`` when Git is unavailable."""
    try:
        return subprocess.run(
            ["git", "diff", *diff_args, f"{baseline_merge_commit}..HEAD", "--"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except FileNotFoundError:
        return None


def _extract_added_symbols(
    diff_output: str,
    supported_paths: frozenset[str],
) -> tuple[tuple[str, str], ...]:
    """Extract added public Python symbols from unified diff text."""
    symbols: list[tuple[str, str]] = []
    current_file = ""
    for line in diff_output.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:]
        elif (
            current_file in supported_paths
            and line.startswith("+")
            and not line.startswith("+++")
        ):
            match = re.match(
                rf"^\+\s*(def|class)\s+([A-Za-z]{_IDENTIFIER_CHARCLASS}*)\s*[\(:]",
                line,
            )
            if match and not match.group(2).startswith("_"):
                symbols.append((match.group(2), current_file))
    return tuple(symbols)


def _discover_changed_symbols(
    repo_root: Path,
    baseline_merge_commit: str,
) -> _Discovery:
    """Discover changed paths and added Python symbols without a source-root assumption."""
    name_result = _run_git_diff(repo_root, baseline_merge_commit, "--name-only")
    if name_result is None:
        return _Discovery((), (), "git executable is unavailable")
    if name_result.returncode != 0:
        return _Discovery((), (), "git diff failed")

    changed_paths = tuple(path for path in name_result.stdout.splitlines() if path)
    if not changed_paths:
        return _Discovery((), (), "git diff reported no changed files")
    changed_python_paths = tuple(
        path for path in changed_paths if path.endswith(".py")
    )
    supported_paths = tuple(
        path
        for path in changed_python_paths
        if path.startswith("src/") or "test" not in path
    )
    if not supported_paths:
        return _Discovery(
            changed_paths,
            (),
            "changed source set contains no supported Python files",
        )

    diff_result = _run_git_diff(repo_root, baseline_merge_commit, "--unified=0")
    if diff_result is None:
        return _Discovery(changed_paths, (), "git executable is unavailable")
    if diff_result.returncode != 0:
        return _Discovery(changed_paths, (), "git diff failed")
    return _Discovery(
        supported_paths,
        _extract_added_symbols(diff_result.stdout, frozenset(supported_paths)),
    )


def _load_python_corpus(
    repo_root: Path,
    changed_paths: tuple[str, ...],
) -> tuple[tuple[tuple[str, str], ...], str | None]:
    """Load the complete Python corpus, including untracked files, deterministically."""
    changed_python_paths = tuple(
        path for path in changed_paths if path.endswith(".py")
    )
    search_root = (
        repo_root / "src"
        if changed_python_paths
        and all(path.startswith("src/") for path in changed_python_paths)
        else repo_root
    )
    try:
        paths = sorted(
            path
            for path in search_root.rglob("*.py")
            if path.is_file()
            and not path.is_symlink()
            and not (
                _EXCLUDED_CORPUS_PARTS
                & set(path.relative_to(repo_root).parts)
            )
        )
    except OSError as exc:
        return (), f"could not enumerate Python source: {exc}"

    corpus: list[tuple[str, str]] = []
    for path in paths:
        relative_path = path.relative_to(repo_root).as_posix()
        try:
            source = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return (), f"could not read Python source: {relative_path}"
        corpus.append((relative_path, source))
    if not corpus:
        return (), "Python source corpus is empty"
    return tuple(corpus), None


def _unreferenced_symbols(
    symbols: tuple[tuple[str, str], ...],
    corpus: tuple[tuple[str, str], ...],
) -> list[dict[str, str]]:
    """Return symbols with no caller, preserving the legacy path filters."""
    dead_symbols: list[dict[str, str]] = []
    for symbol, defined_in in symbols:
        callers = [
            path
            for path, source in corpus
            if symbol in source and path != defined_in and "test" not in path
        ]
        if not callers:
            dead_symbols.append({"symbol": symbol, "file": defined_in})
    return dead_symbols


def _append_undeterminable(
    *,
    reason: str,
    console: Console,
    findings: list[dict[str, str]],
) -> None:
    diagnostic_code = MissionReviewDiagnostic.DEAD_CODE_UNDETERMINABLE
    console.print(
        f"  [red]✗[/red]  Dead-code scan: undeterminable ({diagnostic_code})"
    )
    console.print(f"       reason: {reason}")
    console.print(f"       remediation: {_UNDETERMINABLE_REMEDIATION}")
    findings.append(
        {
            "type": "dead_code_undeterminable",
            "diagnostic_code": str(diagnostic_code),
            "reason": reason,
            "remediation": _UNDETERMINABLE_REMEDIATION,
        }
    )


def _handle_missing_baseline(
    *,
    console: Console,
    findings: list[dict[str, str]],
    mission_id: str | None,
    mission_slug: str | None,
) -> None:
    if mission_id:
        remediation = (
            "Run `spec-kitty merge` to bake baseline_merge_commit into meta.json, "
            "or rerun review with `--mode post-merge` after merge."
        )
        console.print(
            f"  [red]✗[/red]  Dead-code scan: missing baseline_merge_commit "
            f"({MissionReviewDiagnostic.LIGHTWEIGHT_REVIEW_MISSING_BASELINE})"
        )
        console.print(f"       remediation: {remediation}")
        findings.append(
            {
                "type": "dead_code_baseline_missing",
                "diagnostic_code": str(
                    MissionReviewDiagnostic.LIGHTWEIGHT_REVIEW_MISSING_BASELINE
                ),
                "mission_id": mission_id,
                "mission_slug": mission_slug or "",
                "remediation": remediation,
            }
        )
        return
    console.print(
        f"  [yellow]⚠[/yellow]  Dead-code scan skipped: no baseline_merge_commit in meta.json"
        f" (legacy / pre-083 mission, {MissionReviewDiagnostic.LEGACY_MISSION_DEAD_CODE_SKIP})"
    )


def scan_dead_code(
    baseline_merge_commit: str | None,
    repo_root: Path,
    console: Console,
    findings: list[dict[str, str]],
    *,
    mission_id: str | None = None,
    mission_slug: str | None = None,
) -> None:
    """Scan added public Python symbols and emit an earned review verdict."""
    if not baseline_merge_commit:
        _handle_missing_baseline(
            console=console,
            findings=findings,
            mission_id=mission_id,
            mission_slug=mission_slug,
        )
        return

    discovery = _discover_changed_symbols(repo_root, baseline_merge_commit)
    if discovery.error is not None:
        _append_undeterminable(
            reason=discovery.error,
            console=console,
            findings=findings,
        )
        return

    corpus, corpus_error = _load_python_corpus(
        repo_root,
        discovery.changed_paths,
    )
    if corpus_error is not None:
        _append_undeterminable(
            reason=corpus_error,
            console=console,
            findings=findings,
        )
        return

    dead_symbols = _unreferenced_symbols(discovery.symbols, corpus)
    for dead_symbol in dead_symbols:
        findings.append({"type": "dead_code", **dead_symbol})

    if dead_symbols:
        console.print(
            f"  [red]✗[/red]  Dead-code scan: "
            f"{len(dead_symbols)} unreferenced public symbol(s)"
        )
        for dead_symbol in dead_symbols:
            console.print(f"       {dead_symbol['file']}  {dead_symbol['symbol']}")
        return
    console.print(
        "  [green]✓[/green]  Dead-code scan: 0 unreferenced public symbols"
    )
