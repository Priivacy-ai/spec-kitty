"""Fix-mode prompt generator for rejected work packages.

Generates a focused fix-mode prompt (~40 lines) from a persisted ReviewCycleArtifact
instead of replaying the full WP implement prompt (~400-500 lines) when a WP is
rejected and re-claimed.

This is the core token-saving mechanism for mission 066-review-loop-stabilization.

Usage:
    from specify_cli.review.fix_prompt import generate_fix_prompt

    prompt = generate_fix_prompt(
        artifact=artifact,
        worktree_path=workspace_path,
        mission_slug="066-review-loop-stabilization",
        wp_id="WP01",
    )
"""

from __future__ import annotations

from pathlib import Path

from specify_cli.review.artifacts import ReviewCycleArtifact

# Maximum number of lines to show for a file without a line range
_MAX_FULL_FILE_LINES = 100

# Number of context lines to show above/below the line_range
_CONTEXT_LINES = 5

# Extension-to-language mapping for code block syntax highlighting
_EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".rs": "rust",
    ".go": "go",
    ".java": "java",
    ".rb": "ruby",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".md": "markdown",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".json": "json",
    ".html": "html",
    ".css": "css",
    ".sql": "sql",
    ".tf": "hcl",
    ".hcl": "hcl",
}


def _detect_language(file_path: str) -> str:
    """Derive a language name from a file extension for code blocks."""
    suffix = Path(file_path).suffix.lower()
    return _EXT_TO_LANGUAGE.get(suffix, "")


def _extract_snippet(
    file_path: Path,
    line_range: str | None,
) -> tuple[str, bool]:
    """Read file content and extract a focused snippet.

    Args:
        file_path: Absolute path to the file.
        line_range: "start-end" string (1-indexed) or None to show full file.

    Returns:
        A tuple of (snippet_text, truncated) where truncated is True if the
        file was longer than _MAX_FULL_FILE_LINES and we cut it short.
    """
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return f"[File not found: {file_path}]", False

    lines = content.splitlines()
    total_lines = len(lines)
    truncated = False

    if line_range is not None:
        try:
            parts = line_range.split("-")
            start_line = max(1, int(parts[0]))
            end_line = int(parts[1]) if len(parts) > 1 else start_line
        except (ValueError, IndexError):
            # Bad line_range format — fall through to show full file
            start_line = 1
            end_line = total_lines
        else:
            # Apply context padding, clamped to valid range
            start_line = max(1, start_line - _CONTEXT_LINES)
            end_line = min(total_lines, end_line + _CONTEXT_LINES)

        snippet_lines = lines[start_line - 1 : end_line]
        snippet = "\n".join(snippet_lines)
    else:
        if total_lines > _MAX_FULL_FILE_LINES:
            snippet_lines = lines[:_MAX_FULL_FILE_LINES]
            snippet = "\n".join(snippet_lines)
            truncated = True
        else:
            snippet = "\n".join(lines)

    return snippet, truncated


def generate_fix_prompt(
    artifact: ReviewCycleArtifact,
    worktree_path: Path,
    mission_slug: str,
    wp_id: str,
) -> str:
    """Generate a focused fix-mode prompt from a review-cycle artifact.

    The prompt is intentionally compact — it is a replacement for the full WP
    implement prompt, not an addition to it. It contains only what the
    implementing agent needs to fix the specific issues raised during review.

    Args:
        artifact: The review-cycle artifact from the prior rejection.
        worktree_path: Root of the execution worktree (for reading source files).
        mission_slug: Mission identifier, e.g. "066-review-loop-stabilization".
        wp_id: Normalized work package ID, e.g. "WP01".

    Returns:
        The complete fix-mode prompt as a string.
    """
    sections: list[str] = []

    # ── Header ──────────────────────────────────────────────────────────────
    sections.append(f"# Fix Mode: {wp_id} — Cycle {artifact.cycle_number}")
    sections.append("")

    # ── Review Findings ──────────────────────────────────────────────────────
    sections.append("## Review Findings")
    sections.append("")
    if artifact.body.strip():
        sections.append(artifact.body.strip())
    else:
        sections.append("_(No review body provided — see reproduction command below.)_")
    sections.append("")

    # ── Affected Files ───────────────────────────────────────────────────────
    if artifact.affected_files:
        sections.append("## Affected Files")
        sections.append("")

        for affected in artifact.affected_files:
            range_label = f" (lines {affected.line_range})" if affected.line_range else ""
            sections.append(f"### {affected.path}{range_label}")
            sections.append("")

            abs_path = worktree_path / affected.path
            snippet, truncated = _extract_snippet(abs_path, affected.line_range)
            language = _detect_language(affected.path)

            sections.append(f"```{language}")
            sections.append(snippet)
            sections.append("```")

            if truncated:
                sections.append(
                    f"_(File has more than {_MAX_FULL_FILE_LINES} lines; "
                    "only the first portion is shown. Read the full file if needed.)_"
                )
            sections.append("")

    # ── Reproduction ─────────────────────────────────────────────────────────
    if artifact.reproduction_command:
        sections.append("## Reproduction")
        sections.append("")
        sections.append("```bash")
        sections.append(artifact.reproduction_command)
        sections.append("```")
        sections.append("")

    # ── Instructions ────────────────────────────────────────────────────────
    sections.append("## Instructions")
    sections.append("")
    sections.append("1. Read the review findings above carefully")
    sections.append("2. Fix ONLY the issues described — do not refactor or improve unrelated code")
    if artifact.reproduction_command:
        sections.append("3. Run the reproduction command to verify your fix")
        sections.append("4. Commit your changes")
        sections.append(
            f"5. Move this WP back to for_review:\n"
            f"   spec-kitty agent tasks move-task {wp_id} --to for_review"
            f" --mission {mission_slug}"
        )
    else:
        sections.append("3. Commit your changes")
        sections.append(
            f"4. Move this WP back to for_review:\n"
            f"   spec-kitty agent tasks move-task {wp_id} --to for_review"
            f" --mission {mission_slug}"
        )
    sections.append("")

    return "\n".join(sections)
