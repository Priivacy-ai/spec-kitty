---
work_package_id: WP01
title: Ship documentation prompt templates
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-documentation-mission-composition-fixup-01KQ6N5X
base_commit: 25700d4e9daf5ac83b3e4b7f31f3c78d38989e87
created_at: '2026-04-27T05:12:07.046816+00:00'
subtasks:
- T01
- T02
- T03
- T04
- T05
- T06
- T07
- T08
shell_pid: "30176"
agent: "claude:opus-4.7:implementer-ivan:implementer"
history:
- action: created
  at: '2026-04-27T05:05:00Z'
  by: tasks
authoritative_surface: src/specify_cli/missions/documentation/templates/
execution_mode: code_change
owned_files:
- src/specify_cli/missions/documentation/templates/discover.md
- src/specify_cli/missions/documentation/templates/audit.md
- src/specify_cli/missions/documentation/templates/design.md
- src/specify_cli/missions/documentation/templates/generate.md
- src/specify_cli/missions/documentation/templates/validate.md
- src/specify_cli/missions/documentation/templates/publish.md
- src/specify_cli/missions/documentation/templates/accept.md
- tests/specify_cli/test_documentation_prompt_resolution.py
tags: []
---

# WP-FIX-1 — Ship Documentation Prompt Templates

## Objective

Close finding F-1: ship 7 markdown prompt templates so `_build_prompt_safe` returns a non-null `prompt_file` for every documentation step (discover, audit, design, generate, validate, publish, accept). Add a parametrized unit test that pins this resolution.

## Context

The runtime sidecar at `src/specify_cli/missions/documentation/mission-runtime.yaml:24-65` declares `prompt_template: <verb>.md` for each step. The runtime resolves these via `resolve_command(...)` in the live `spec-kitty next` path. With the files absent, `_build_prompt_safe` returns `None` and the operator/host harness gets a documentation-native step with no runnable prompt.

Reference templates: read `src/specify_cli/missions/research/templates/` (if it exists) for shape. If research doesn't ship templates either, follow the prose style of the existing action-bundle `guidelines.md` files at `src/doctrine/missions/documentation/actions/<action>/guidelines.md` but more procedural and operator-facing.

## Subtasks

### T01-T07 — 7 prompt template files

For each documentation step, author a markdown file at `src/specify_cli/missions/documentation/templates/<verb>.md`:

- `discover.md`: Frame the documentation mission's discovery phase. Include: identify the audience, iteration mode (initial/gap-filling/feature-specific), goals, success criteria. Reference `gap-analysis.md` and `spec.md` as outputs. ~30-50 lines.
- `audit.md`: Frame the documentation audit phase. Include: gap analysis methodology, coverage matrix per Divio type (tutorial/how-to/reference/explanation), prioritization. Reference `gap-analysis.md` as the deliverable. ~30-50 lines.
- `design.md`: Frame the documentation design phase. Include: Divio type planning, generator selection (JSDoc/Sphinx/rustdoc), navigation hierarchy, ADR-style decisions. Reference `plan.md` as deliverable. ~30-50 lines.
- `generate.md`: Frame the documentation generation phase. Include: produce artifacts faithful to plan.md, generator invocation, source-of-truth alignment. Reference `docs/**/*.md` outputs. ~30-50 lines.
- `validate.md`: Frame the validation phase. Include: quality gates (Divio adherence, accessibility, completeness), risk review, audit-report.md as the canonical evidence. ~30-50 lines.
- `publish.md`: Frame the publish phase. Include: release readiness, deployment handoff, release.md, post-publish living-documentation sync. ~30-50 lines.
- `accept.md`: Frame the terminal acceptance phase. Include: validate completeness, quality gates, readiness for publication. ~20-30 lines.

Each template's tone matches the existing research action templates (if they exist). Do NOT include implementation code. These are governance/authorship prose for the host LLM.

### T08 — Parametrized prompt-resolution test

Create `tests/specify_cli/test_documentation_prompt_resolution.py`:

```python
"""Regression test for documentation prompt template resolution (#502 fix-up F-1)."""
from __future__ import annotations
from pathlib import Path
import pytest

_DOC_STEPS = ("discover", "audit", "design", "generate", "validate", "publish", "accept")
_TEMPLATES_DIR = Path(__file__).resolve().parents[2] / "src" / "specify_cli" / "missions" / "documentation" / "templates"


@pytest.mark.parametrize("step_id", _DOC_STEPS)
def test_prompt_template_exists_and_is_nonempty(step_id: str) -> None:
    path = _TEMPLATES_DIR / f"{step_id}.md"
    assert path.is_file(), f"missing template: {path}"
    content = path.read_text(encoding="utf-8").strip()
    assert content, f"empty template: {path}"
    assert len(content.splitlines()) >= 10, f"template too short ({len(content.splitlines())} lines): {path}"
```

If you can also assert via `Decision.prompt_file` from a runtime call (read research walk's lifecycle test for the import pattern), add a second test that drives `decide_next_via_runtime` and asserts `decision.prompt_file` is non-null and points at one of the 7 template files. If the runtime API doesn't expose this cleanly, the file-existence test is sufficient — note that in the test docstring.

## Verification

- All 7 template files exist, ≥10 non-empty lines each.
- `uv run --python 3.13 --extra test python -m pytest tests/specify_cli/test_documentation_prompt_resolution.py -v --timeout=60` — all 7 tests PASS.
- `ruff check tests/specify_cli/test_documentation_prompt_resolution.py` — clean.
- `mypy --strict tests/specify_cli/test_documentation_prompt_resolution.py` — clean.

## After Implementation

1. `git add src/specify_cli/missions/documentation/templates/ tests/specify_cli/test_documentation_prompt_resolution.py`
2. `git commit -m "feat(WP-FIX-1): ship 7 documentation prompt templates (#502 F-1)"`
3. `spec-kitty agent tasks mark-status T01 T02 T03 T04 T05 T06 T07 T08 --status done --mission documentation-mission-composition-fixup-01KQ6N5X`
4. `spec-kitty agent tasks move-task WP-FIX-1 --to for_review --mission documentation-mission-composition-fixup-01KQ6N5X --note "T01-T08 complete; 7 templates + test; 7/7 PASS; ruff+mypy clean"`

## Reviewer Guidance

- Verify each template is non-empty governance/authorship prose, not implementation code or boilerplate.
- Verify all 7 file paths match the runtime sidecar's `prompt_template:` declarations exactly.
- Run the test and confirm it PASSes.
- Verify no edits outside the 8 owned files.

## Activity Log

- 2026-04-27T05:12:08Z – claude:opus-4.7:implementer-ivan:implementer – shell_pid=30176 – Assigned agent via action command
