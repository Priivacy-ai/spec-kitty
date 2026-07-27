---
work_package_id: WP07
title: Sonar coverage-denominator exclusions
dependencies: []
requirement_refs:
- FR-012
tracker_refs: []
planning_base_branch: feat/ci-test-topology-performance
merge_target_branch: feat/ci-test-topology-performance
branch_strategy: Planning artifacts for this mission were generated on feat/ci-test-topology-performance. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-test-topology-performance unless the human explicitly redirects the landing branch.
subtasks:
- T022
phase: Phase 3 - Coverage fairness
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1171170"
shell_pid_created_at: "1783882894.57"
history:
- at: '2026-07-12T17:43:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: sonar-project.properties
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- sonar-project.properties
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Sonar coverage-denominator exclusions

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

- Add `sonar.coverage.exclusions` to `sonar-project.properties`, restoring a *fair* coverage-only denominator (FR-012, GC-6) without touching the existing `sonar.exclusions` (issue-analysis) line.
- Every excluded glob is confirmed duct-tape/glue or non-Python — never core Python (E5 invariant, data-model.md).
- Success = the exclusion list lands with a rationale comment per entry, and `sonar.exclusions` is unchanged.

## Context & Constraints

This mission's spec evidence (spec.md "Sonar quality gate" section) shows `new_coverage 60.1% < 80%` is *partly unfair*: the denominator counts one-shot migration glue, non-Python dashboard assets, and code exercised only by the Playwright suite (WP08's concern). FR-012 and GC-6 (contracts/guard-contracts.md) scope this WP to the *coverage* denominator only — files stay in Sonar's issue analysis (duplication/hotspots/maintainability), they are only excluded from the coverage percentage.

Current `sonar-project.properties`:
```
sonar.exclusions=**/__pycache__/**,**/*.pyc,**/migrations/**
```
Note `sonar.exclusions` is **plural-only** (`**/migrations/**`) — it already excludes the plural migrations directory from analysis entirely, but misses the **singular** sibling `src/specify_cli/migration/` (one-shot mission-state migration/backfill glue, ~1,333 uncovered lines at 0%, per spec.md FR-012). Do not fold this WP's fix into `sonar.exclusions` — it belongs in the new `sonar.coverage.exclusions` key so the files remain analyzed for other Sonar facets while being dropped only from the coverage denominator.

The three globs to add (verbatim, from data-model.md E5 and FR-012):
1. `src/specify_cli/migration/**` — one-shot mission-state migration/backfill code, the singular sibling `sonar.exclusions`' plural-only glob misses; ~1,333 uncovered lines at 0%.
2. `**/static/**` — dashboard JS/CSS (e.g. `dashboard.js` ~720 lines), non-Python and untestable by `pytest --cov`.
3. `**/__main__.py` — thin CLI entrypoints.

**Post-rebase note**: a fourth glob, `src/specify_cli/next/**` (the deprecation shim), was originally scoped here but the unshim wave already deleted `src/specify_cli/next/` entirely — the canonical runtime now lives at `src/runtime/next/_internal_runtime/` (see CLAUDE.md "Shared Package Boundary"). Since the path no longer exists, the glob is intentionally dropped rather than added dead — there is nothing left for it to exclude.

**Out of scope**: raising genuine core-Python `new_coverage` or the `new_reliability_rating` (sibling mission #2071, per spec.md "Out of Scope"). Do not add any path under `src/specify_cli/` that is not one of the three confirmed glue/non-Python globs above — GC-6 is enforced by review, not a runtime test, so precision here is the whole control.

## Branch Strategy

- **Strategy**: Single mission branch — implement directly in the WP's execution workspace created by `spec-kitty implement WP07`.
- **Planning base branch**: `feat/ci-test-topology-performance`
- **Merge target branch**: `feat/ci-test-topology-performance` (mission branch merges to local `main` via `spec-kitty merge`; a PR to `main` follows per CLAUDE.md's no-direct-push policy).

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T022 – Add `sonar.coverage.exclusions` with rationale comment (FR-012, GC-6)

- **Purpose**: Exclude confirmed glue/non-Python assets from the coverage-percentage denominator so `new_coverage` reflects testable code, not migration one-shots or dashboard static assets.
- **Steps**:
  1. Open `sonar-project.properties`.
  2. Immediately above the new key, add a comment block (one line per glob) stating *why* each entry is coverage-only glue — reuse the three rationale lines from Context & Constraints above so the comment is self-explanatory to a future reviewer disposing the Sonar hotspot.
  3. Add the key on its own line, after `sonar.python.xunit.reportPath` and before (or after) the existing `sonar.exclusions` line — keep `sonar.exclusions` textually untouched:
     ```
     sonar.coverage.exclusions=src/specify_cli/migration/**,**/static/**,**/__main__.py
     ```
  4. Do not reorder or reformat unrelated lines (`sonar.projectKey`, `sonar.organization`, `sonar.python.coverage.reportPaths`, etc.) — the `ci-quality.yml` sonarcloud job's "Normalize" step (see `.github/workflows/ci-quality.yml` around the `sonar_settings` step) rewrites some of these keys at run time by line-filtering; an unexpected reformat could break that `grep -v` pipeline.
- **Files**: `sonar-project.properties` (only owned file).
- **Parallel?**: Root WP — no dependencies, independent of WP01–WP06's topology chain and of WP08 (spec.md "WP-J + WP-K together restore a fair coverage denominator" — they are still independently shippable).
- **Notes**: This is a config-only change; there is no dedicated Python guard for GC-6 (contracts/guard-contracts.md: "Enforced by review + the exclusion list's own comment rationale, not a runtime test"). The rationale comment IS the enforcement mechanism — do not skip it.

## Test Strategy (include only when tests are required)

- No automated test asserts this WP's correctness (GC-6 is a review-enforced contract). Instead:
  - `grep -n "coverage.exclusions" sonar-project.properties` — confirm the key exists with all three globs, comma-separated, no line-break inside the value (Sonar properties files do not support line continuation without a trailing `\`).
  - Manually re-read each glob against the three confirmed cases in Context & Constraints; confirm no path segment matches a core-Python directory (e.g. `src/specify_cli/cli/**`, `src/specify_cli/status/**` must NOT match any of the three globs).
  - `git diff sonar-project.properties` — confirm `sonar.exclusions=**/__pycache__/**,**/*.pyc,**/migrations/**` is byte-identical to before (untouched).
  - Run the terminology guard since this touches doctrine-adjacent config comments: `pytest tests/architectural/test_no_legacy_terminology.py`.

## Risks & Mitigations

- **Risk**: accidentally widening a glob to catch real source (e.g. `**/static/**` matching a `static/` dir under a tested package that isn't actually the dashboard's asset tree). **Mitigation**: `grep -rl "static" src/specify_cli --include="*.py" -l` before committing, confirm `**/static/**` only resolves to the dashboard's asset directory.
- **Risk**: this WP is trivial in isolation but its rationale comment is the load-bearing GC-6 artifact — a reviewer six months from now needs it to dispose the Sonar hotspot without re-deriving the ~1,333-line migration figure. **Mitigation**: keep the comment text close to the FR-012 wording so it survives a `git blame`.
- **Risk**: conflicting edits with WP08 if both WPs are worked in parallel and someone edits `sonar-project.properties` for WP08 too (e.g. a stray `sonar.javascript.lcov.reportPaths` edit). **Mitigation**: `owned_files` scopes WP07 to `sonar-project.properties`; WP08 owns `.github/workflows/ui-e2e.yml` only — if WP08's JS-lcov investigation needs a `sonar-project.properties` key, that edit must be re-routed through this WP or a follow-up, not made unilaterally from WP08.

## Review Guidance

- Confirm the three globs match Context & Constraints exactly (no typos, no extra globs, no core-Python path, and no `src/specify_cli/next/**` — that path was deleted by the unshim wave, see Context's post-rebase note).
- Confirm `sonar.exclusions` is unchanged (`git diff` shows only additive lines).
- Confirm the rationale comment names each excluded path and its reason (migration glue / non-Python static / entrypoint) — a bare key with no comment should be rejected.
- Confirm `pytest tests/architectural/test_no_legacy_terminology.py` was run and is green.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Common mistakes (DO NOT DO THIS)**:

- Adding new entry at the top (breaks chronological order)
- Using future timestamps (causes acceptance validation to fail)
- Inserting in middle instead of appending to end

**Why this matters**: The acceptance system reads the LAST activity log entry as the current state. If entries are out of order, acceptance will fail even when the work is complete.

**Initial entry**:

- 2026-07-12T17:43:44Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP07 --to <status>` to change WP status.
- 2026-07-12T18:56:48Z – claude:sonnet:implementer-ivan:implementer – shell_pid=1150293 – Assigned agent via action command
- 2026-07-12T19:01:11Z – claude:sonnet:implementer-ivan:implementer – shell_pid=1150293 – Ready: 3 globs added, next/** confirmed deleted, no core-Python matched
- 2026-07-12T19:01:37Z – claude:opus:reviewer-renata:reviewer – shell_pid=1171170 – Started review via action command
- 2026-07-12T19:09:57Z – user – shell_pid=1171170 – Review passed (reviewer-renata): coverage.exclusions glue-only, next/** dropped, sonar.exclusions untouched, no core-Python caught; matrix now filled
