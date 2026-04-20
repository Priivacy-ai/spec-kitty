"""Harness plan-artifact scan list for ``spec-kitty intake --auto``.

Each entry is a tuple of:
  (harness_key, source_agent_value, candidate_paths)

Only Verified-docs or Verified-empirical entries appear as active tuples.
Inferred or Unknown entries are commented out as TODO blocks.

Ordering rule: harness-specific hidden dirs (e.g. ``.opencode/plans/``) before
generic root-level names.  Within a harness, list most-specific path first.

Source: docs/reference/agent-plan-artifacts.md
Last updated: 2026-04-20
"""

from __future__ import annotations

from pathlib import Path


# ---------------------------------------------------------------------------
# Active entries: Verified-docs or Verified-empirical confidence only
# ---------------------------------------------------------------------------

HARNESS_PLAN_SOURCES: list[tuple[str, str | None, list[str]]] = [
    # OpenCode — Verified-docs
    # .opencode/plans/*.md is the only directory writable in plan mode.
    # Files are named <unix-timestamp>-<slug>.md.
    # Source: https://opencode.ai/docs/modes/
    (
        "opencode",
        "opencode",
        [".opencode/plans"],
    ),
    # Kiro (Amazon Q rebrand) — Verified-docs
    # Spec-driven workflow produces three files per feature under .kiro/specs/.
    # These files are committed to the repo by design.
    # Source: https://kiro.dev/docs/specs/
    (
        "kiro",
        "amazon-q",
        [
            ".kiro/specs",
        ],
    ),
    # Cursor — Verified-docs (conditional)
    # Only present when the user has clicked "Save to Workspace" in the Cursor UI.
    # Default global path (~/.cursor/plans/) is not scanned (not project-scoped).
    # Source: https://cursor.com/docs/agent/plan-mode
    (
        "cursor",
        "cursor",
        [".cursor/plans"],
    ),
    # Gemini CLI — Verified-docs (conditional)
    # Only present when the user has configured general.plan.directory = ".gemini/plans"
    # in .gemini/settings.json.  Default path is ~/.gemini/tmp/<project>/<session>/plans/
    # (global temp, not scanned here).
    # Source: https://geminicli.com/docs/cli/plan-mode/
    (
        "gemini",
        "gemini",
        [".gemini/plans"],
    ),
]


# ---------------------------------------------------------------------------
# TODO: entries with Inferred or Unknown confidence
# ---------------------------------------------------------------------------

# TODO(claude): Claude Code — plan mode saves to ~/.claude/plans/ by default
# (global, not project-scoped).  Becomes project-local when plansDirectory is
# set in .claude/settings.json.  Auto-generated adjective-noun filenames make
# glob patterns unreliable without knowing the configured directory.
# Confidence: Verified-empirical for default path; no stable project-level default.
# Source: https://claudelog.com/faqs/what-is-plans-directory-in-claude-code/
# When promoted: add (".claude/plans", "claude-code", [".claude/plans"]) and
# document that it only applies when plansDirectory=".claude/plans" is set.
#
# ("claude", "claude-code", [".claude/plans"]),

# TODO(copilot): GitHub Copilot — no confirmed project-level plan file path.
# Plan mode surfaced in IDE/web UI (Copilot Workspace); session artefacts keyed
# by session ID (not stable).  Custom instructions file is .github/copilot-instructions.md
# but that is input, not plan output.
# Confidence: Inferred
# Source: https://github.blog/changelog/2025-11-18-plan-mode-in-github-copilot-now-in-public-preview
#
# ("copilot", "copilot", []),

# TODO(qwen): Qwen Code — plan mode exists but saves session todos as JSON to
# ~/.qwen/todos/, not as project-level Markdown.
# Confidence: Verified-docs
# Source: https://qwenlm.github.io/qwen-code-docs/en/developers/tools/todo-write/
#
# ("qwen", "qwen", []),

# TODO(windsurf): Windsurf Cascade — plans saved globally to ~/.windsurf/plans/.
# No documented project-level directory override.
# Confidence: Verified-docs
# Source: https://docs.windsurf.com/windsurf/cascade/modes
#
# ("windsurf", "windsurf", []),

# TODO(kilocode): Kilocode — forked from OpenCode; plan mode exists but a known
# bug (issue #6370, Feb 2026) causes plans to save to .opencode/plans/ instead
# of a Kilocode-specific directory.  The correct path (.kilocode/plans/) is not
# yet reliably produced.
# Confidence: Inferred
# Source: https://github.com/Kilo-Org/kilocode/issues/6370
#
# ("kilocode", "kilocode", [".kilocode/plans", ".opencode/plans"]),

# TODO(auggie): Augment Code — plan mode saves to ~/.augment/plans/ (global).
# No confirmed project-level path.
# Confidence: Inferred
# Source: augmentcode.com changelog summaries; not in official docs as of 2026-04-20.
#
# ("auggie", "augment", []),

# TODO(roo): Roo Cline — no confirmed plan file path.  Architect mode is the
# closest analogue but does not produce a deterministic on-disk Markdown file.
# Confidence: Unknown
# Source: https://docs.roocode.com/basic-usage/using-modes
#
# ("roo", "roo", []),

# TODO(q): Amazon Q Developer — no confirmed plan mode file output.
# Confidence: Unknown
# Source: https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/software-dev.html
#
# ("q", "amazon-q", []),

# TODO(antigravity): Google Antigravity — Planning mode produces an Implementation
# Plan artifact surfaced in the IDE panel, not a stable per-project Markdown file.
# Knowledge base is at .gemini/antigravity/brain/ but contains architectural notes,
# not user-facing plan files.
# Confidence: Inferred
# Source: https://antigravity.google/docs/implementation-plan
#
# ("antigravity", "antigravity", [".gemini/antigravity/brain"]),

# TODO(vibe): Mistral Vibe — built-in plan agent profile (read-only); no confirmed
# on-disk plan file output.  Config at .vibe/config.toml; skills at .vibe/skills/.
# Confidence: Inferred
# Source: https://docs.mistral.ai/mistral-vibe/agents-skills
#
# ("vibe", "vibe", []),


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def scan_for_plans(cwd: Path) -> list[tuple[Path, str, str | None]]:
    """Scan known harness plan locations under ``cwd``.

    Returns ``(absolute_path, harness_key, source_agent_value)`` tuples
    for every candidate path that exists as a regular file, in declaration order.
    Silently skips paths that do not exist, are directories, or are unreadable.

    When a candidate path is a directory, every ``*.md`` file directly inside it
    (non-recursive) is included.

    Args:
        cwd: Project root to scan under.

    Returns:
        List of ``(absolute_path, harness_key, source_agent_value)`` tuples.
    """
    results: list[tuple[Path, str, str | None]] = []
    for harness_key, source_agent_value, candidate_paths in HARNESS_PLAN_SOURCES:
        for rel_path in candidate_paths:
            abs_path = cwd / rel_path
            try:
                if abs_path.is_file():
                    results.append((abs_path, harness_key, source_agent_value))
                elif abs_path.is_dir():
                    # Expand directory: collect all *.md files (non-recursive)
                    for child in sorted(abs_path.iterdir()):
                        try:
                            if child.is_file() and child.suffix == ".md":
                                results.append(
                                    (child, harness_key, source_agent_value)
                                )
                        except (PermissionError, OSError):
                            pass
            except (PermissionError, OSError):
                pass
    return results
