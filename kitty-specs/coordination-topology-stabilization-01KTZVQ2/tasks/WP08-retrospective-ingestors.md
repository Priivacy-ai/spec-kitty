---
work_package_id: WP08
title: Retrospective Generator Ingestors
dependencies: []
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T036
- T037
- T038
- T039
- T040
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "3878"
history:
- date: '2026-06-12'
  author: spec-kitty.tasks
  note: Initial generation
agent_profile: python-pedro
authoritative_surface: src/specify_cli/post_merge/retrospective/
execution_mode: code_change
owned_files:
- src/specify_cli/post_merge/retrospective/generator.py
- tests/specify_cli/test_retrospective_content.py
priority: P1-Critical
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

---

## Objective

Add mission-local artifact ingestors to the retrospective generator so it can produce non-empty findings on real missions. Revisit the "helped only by contrast" rule that guarantees `ran_no_findings=true` on clean missions. Fix the stale docstring. Add a golden test against the mission-131 fixture.

**This WP handles the CONTENT/GENERATOR half. WP07 (triggering) handles the merge-path postcondition and is independent — both can be developed in parallel.**

---

## Context

### The Bug (Issue #1164, content half)

Even when the retrospective IS triggered, the generator finds nothing useful because it only ingests artifacts that existed at the time of the original "helped only by contrast" rule. Mission-local failure and review artifacts (`workflow-failures-log.md`, `analysis-report.md`, `mission-review-report.md`) are never read. For mission-131, which had significant findings in these files, `ran_no_findings=true` was the output — a useless retrospective.

### "Helped Only By Contrast" Rule

`generator.py:684` contains a rule: retrospective findings are only emitted when there is a clear contrast between what was planned and what actually happened. Clean missions (no failures, no review comments) satisfy neither side — the generator returns `ran_no_findings=true`. This rule needs to be revisited: add ingestors for mission-local artifacts so the generator has signal even on missions that look clean from the primary planning artifacts.

### Mission-Local Artifact Ingestors

New artifacts to ingest:
1. `workflow-failures-log.md` — CI/workflow failure records
2. `analysis-report.md` — doc/analysis outputs (some missions have these)
3. `mission-review-report.md` — review findings (if present)

For each: read if present, extract key sections, inject as input signal to the generator prompt.

---

## Subtasks

### T036 — Add `workflow-failures-log.md` ingestor

1. Read `src/specify_cli/post_merge/retrospective/generator.py` lines 675–720.
2. Identify the pattern for existing ingestors (how artifacts are found and their content added to the generator context).
3. Add an ingestor for `workflow-failures-log.md`:
   - Path: `kitty-specs/<slug>/workflow-failures-log.md` (relative to `feature_dir`)
   - Extract: all failure entries (lines starting with `- [ ] FAIL:` or `### FAIL:` patterns — read existing log format).
   - Add to generator context as "Workflow Failures" section.
4. Run `mypy --strict src/specify_cli/post_merge/retrospective/generator.py`.

### T037 — Add `analysis-report.md` and `mission-review-report.md` ingestors

1. Following the same pattern as T036:
2. `analysis-report.md` → "Analysis Findings" context section (if present; skip if absent).
3. `mission-review-report.md` → "Review Findings" context section (if present; skip if absent).
4. All ingestors must be optional: if the file doesn't exist, the generator continues without it.

### T038 — Revisit "helped only by contrast" rule

1. Read `generator.py:684` and surrounding context to understand the rule's implementation.
2. The rule should be relaxed when mission-local artifact ingestors provide signal:
   - If `workflow-failures-log.md` has entries → do NOT apply "only by contrast" → emit findings.
   - If `mission-review-report.md` has entries → similarly relax.
3. The rule still applies when NO mission-local artifact content is available (preserves backward compat for truly clean missions).
4. Update the rule's inline comment to explain the new conditional.

### T039 — Fix stale docstring in `generator.py:844–846`

1. Read `generator.py` lines 840–850.
2. The docstring references a deprecated artifact path or parameter name.
3. Update it to match the current implementation.
4. This is a one-line fix — do it as part of this WP rather than a separate PR.

### T040 — Golden test: mission-131 fixture → non-empty findings

File: `tests/specify_cli/test_retrospective_content.py` (new)

Write a pytest test that:
1. Uses a fixture representing mission-131's `kitty-specs/` directory (including `workflow-failures-log.md` with known failure entries).
2. Runs the retrospective generator against the fixture.
3. Asserts:
   - `ran_no_findings=False` OR `findings` is non-empty.
   - The generator does NOT return `ran_no_findings=true` when there are workflow failure entries.
4. The fixture can be a minimal subset — you do not need to reproduce all of mission-131's artifacts; just enough workflow-failures-log.md entries to trigger a finding.

---

## Branch Strategy

**Planning base**: `main` | **Merge target**: `main`

```bash
spec-kitty agent action implement WP08 --agent <name>
```

---

## Definition of Done

- [ ] `workflow-failures-log.md` ingestor present and tested
- [ ] `analysis-report.md` and `mission-review-report.md` ingestors present
- [ ] "Helped only by contrast" rule relaxed when ingestor content is present
- [ ] Stale docstring at `:844-846` fixed
- [ ] `test_retrospective_content.py` passes (mission-131 fixture → non-empty findings)
- [ ] All ingestors are optional (missing file → generator continues)
- [ ] `mypy --strict` zero issues
- [ ] `ruff check .` zero issues

## Risks

- **Fixture construction**: The mission-131 fixture needs to include `workflow-failures-log.md` content. If the real mission-131 files are available, copy the minimum needed. If not, construct a synthetic fixture with the same format.
- **Generator prompt length**: Adding three new ingestor sections may push the generator context too long for the model. Add a max-length truncation (e.g., first 500 chars per artifact) if needed.
- **"Helped only by contrast" rule coupling**: The rule may be deeply coupled to the generator's scoring model. If relaxing it causes false-positive findings on all missions, add a minimum-signal threshold (e.g., at least 2 failure entries).

## Activity Log

- 2026-06-13T07:59:49Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55522 – Assigned agent via action command
- 2026-06-13T08:08:49Z – claude:sonnet-4-6:implementer:implementer – shell_pid=55522 – Ready for review: retrospective generator ingestors implemented
- 2026-06-13T08:09:29Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=3878 – Started review via action command
- 2026-06-13T08:14:45Z – user – shell_pid=3878 – Review passed: all 3 ingestors (workflow-failures-log.md, analysis-report.md, mission-review-report.md) registered and optional, _build_ingestor_findings extracted and called from _build_findings at line 925, stale docstring updated with canonical read order, 17 tests pass, mypy --strict clean, ruff clean
