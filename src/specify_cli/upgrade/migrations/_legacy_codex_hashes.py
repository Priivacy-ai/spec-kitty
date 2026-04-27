"""Known filenames for .codex/prompts/spec-kitty.*.md produced by Spec Kitty
releases before 3.2.0.  Used by m_3_2_0_codex_to_skills to classify files as
owned vs third-party.

Simplification (Option A — filename-only matching)
----------------------------------------------------
This migration does **not** attempt to detect user edits via SHA-256 comparison.
Computing the exact bytes that the pre-3.2 renderer would have produced for each
project is not feasible without re-running the old renderer in a sandboxed
subprocess, and that approach is fragile and complex.

Instead, any ``.codex/prompts/spec-kitty.<command>.md`` file whose ``<command>``
appears in :data:`LEGACY_CODEX_FILENAMES` is treated as **owned_unedited** and
deleted after the new ``.agents/skills/`` packages are installed.

Users who have hand-edited these files should stash or rename them before running
``spec-kitty upgrade``.  After the migration their Codex integration will read
from ``.agents/skills/spec-kitty.<command>/SKILL.md`` instead.  Any custom
content can be ported to a separate ``.codex/prompts/`` file with a
non-spec-kitty filename (e.g. ``my-team-workflow.md``).

See spec §Out of Scope (WP06 task spec) for the full rationale.

Canonical command set (3.2.0a5+)
------------------------------------------------
Matches :data:`specify_cli.skills.command_installer.CANONICAL_COMMANDS`.
The deprecated ``spec-kitty.checklist.md`` legacy filename was removed in
3.2.0a5 (FR-003 / FR-004 / #815) — pre-3.2 codex projects that contain
that file should treat it as user-owned content and migrate manually.
"""

from __future__ import annotations

#: Set of ``spec-kitty.*.md`` filenames that were written into ``.codex/prompts/``
#: by every Spec Kitty release before 3.2.0.
#:
#: Filenames are basename-only (no directory component).  The migration
#: classifier checks ``path.name in LEGACY_CODEX_FILENAMES`` after confirming
#: the parent directory is ``.codex/prompts/``.
LEGACY_CODEX_FILENAMES: frozenset[str] = frozenset(
    {
        "spec-kitty.analyze.md",
        "spec-kitty.charter.md",
        "spec-kitty.implement.md",
        "spec-kitty.plan.md",
        "spec-kitty.research.md",
        "spec-kitty.review.md",
        "spec-kitty.specify.md",
        "spec-kitty.tasks.md",
        "spec-kitty.tasks-finalize.md",
        "spec-kitty.tasks-outline.md",
        "spec-kitty.tasks-packages.md",
    }
)
