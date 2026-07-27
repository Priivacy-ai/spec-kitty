---
work_package_id: WP08
title: UI-e2e coverage feed
dependencies: []
requirement_refs:
- FR-013
tracker_refs: []
planning_base_branch: feat/ci-test-topology-performance
merge_target_branch: feat/ci-test-topology-performance
branch_strategy: Planning artifacts for this mission were generated on feat/ci-test-topology-performance. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/ci-test-topology-performance unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
phase: Phase 3 - Coverage fairness
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1200912"
shell_pid_created_at: "1783883208.12"
history:
- at: '2026-07-12T17:43:44Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: .github/workflows/ui-e2e.yml
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/ui-e2e.yml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – UI-e2e coverage feed

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

- Feed the Playwright/UI-e2e suite's Python coverage into the Sonar report so server-side dashboard code it exercises (`src/specify_cli/dashboard/**`) is credited toward `new_coverage`, closing FR-013.
- Investigate (or document a deferral for) JS coverage for `dashboard.js`, which currently reads 0% despite being driven by `tests/ui/`.
- Success = a `coverage-ui-e2e.xml` is produced by `.github/workflows/ui-e2e.yml` and demonstrably reaches the Sonar-consumed `coverage.xml` set (or the cross-workflow wiring gap below is fixed/escalated, not silently left broken); JS coverage is either wired or its deferral is written down next to the exclusion it relies on.
- **Definition of Done — scope boundary (paula-patterns, MEDIUM)**: WP08's shippable contract is **"UI-e2e coverage artifact produced + the JS/cross-workflow decision recorded (wired or documented deferral)"**. FR-013's *closed* outcome — the artifact actually being consumed end-to-end by Sonar — cross-cuts into files WP08 does not own: a cross-workflow `download-artifact` step in `ci-quality.yml` (WP06's owned file) and/or a `sonar.javascript.lcov.reportPaths` key in `sonar-project.properties` (WP07's owned file). Those two wiring outcomes are a **tracked fast-follow routed through WP06/WP07's owners** — they are NOT part of WP08's own Definition of Done. WP08 is Done once the coverage artifact exists, is uploaded, and the cross-workflow-gap analysis + JS-coverage decision are written down (per path 1/2 below and T024) — WP08 does not itself have to land the cross-workflow consumption to be considered complete.

## Context & Constraints

`spec.md` FR-013: "`ui-e2e.yml` runs `pytest tests/ui/` (Playwright-driven) but its coverage does not reach Sonar: (a) the run carries no `--cov`... (b) no JS coverage is produced." Current `.github/workflows/ui-e2e.yml` step (the only test step in the file):
```yaml
- name: Run the dashboard e2e regression guard (headless)
  run: PWHEADLESS=1 uv run pytest tests/ui/ -q
```
No `--cov` flag, no coverage artifact upload.

**T023 (FR-013a)** — add Python coverage: change the run command to emit an XML report scoped to the dashboard package Playwright actually exercises server-side, e.g. `PWHEADLESS=1 uv run pytest tests/ui/ --cov=src/specify_cli/dashboard --cov-report=xml:out/reports/coverage/coverage-ui-e2e.xml -q`, then upload it as an artifact so it can reach the Sonar-consumed set (`sonar.python.coverage.reportPaths`).

**Read this before assuming the artifact "just merges": this file's own header comment (lines 12–20) states `ui-e2e.yml` is "Deliberately its OWN standalone workflow file — not a job appended to `ci-quality.yml` — so it never joins that workflow's ... quality-gate aggregator machinery."** The `sonarcloud` job that builds the merged `coverage.xml` lives in `.github/workflows/ci-quality.yml` and discovers coverage artifacts via:
```yaml
- uses: actions/download-artifact@v8
  with:
    pattern: '*-reports'
    path: out/reports/artifacts/current
```
`download-artifact@v8` without a `run-id` only pulls artifacts uploaded **within the same workflow run**; the fallback step explicitly re-scopes to `workflow_id: 'ci-quality.yml'` (previous run of the *same* workflow). Because `ui-e2e.yml` is a separate workflow with its own run, an artifact uploaded there is **not automatically visible** to `ci-quality.yml`'s `download-artifact` step. Uploading `coverage-ui-e2e.xml` from this WP alone will not reach Sonar — this is the concrete gap T023 must close, not assume away. Two viable paths (pick one, document the choice in the Activity Log):
1. Add a `run-id`-parametrized `download-artifact` step in `ci-quality.yml`'s `sonarcloud` job that resolves the latest successful `ui-e2e.yml` run (mirroring the existing `prev_run` `github-script` pattern, but targeting `workflow_id: 'ui-e2e.yml'`) — this touches `ci-quality.yml`, which is WP06's owned file, so coordinate rather than editing it directly from this WP; if WP06 has already merged, file the addition as a small follow-up PR against `ci-quality.yml`'s sonarcloud job instead of expanding this WP's `owned_files`.
2. If cross-workflow wiring is out of budget for this WP, upload the artifact anyway (useful for local/manual Sonar runs or a future wiring), and **explicitly document in this WP's Activity Log and in T027's docs update (WP09)** that the Python coverage is produced but not yet consumed by the automated Sonar merge — do not claim FR-013a is fully closed if this is the case.

**T024 (FR-013b)** — investigate JS coverage: Playwright supports coverage collection via CDP/istanbul instrumentation feeding an `lcov` report consumable by `sonar.javascript.lcov.reportPaths` (not currently set anywhere in `sonar-project.properties`). If wiring this within the CI time budget (`timeout-minutes: 15` on this job, NFR-001-adjacent) is impractical, **document the deferral** rather than leaving it silently unaddressed — note that `**/static/**` (WP07's `sonar.coverage.exclusions` entry) is the interim mitigation: it removes `dashboard.js` from the denominator rather than crediting it with real coverage. `dashboard.js` is ~720 lines per spec.md's evidence table.

Per spec.md "Out of Scope": raising genuine core-Python coverage stays out; this WP is about denominator/credit **fairness**, not padding.

## Branch Strategy

- **Strategy**: Single mission branch — implement directly in the WP's execution workspace created by `spec-kitty implement WP08`.
- **Planning base branch**: `feat/ci-test-topology-performance`
- **Merge target branch**: `feat/ci-test-topology-performance` (mission branch merges to local `main` via `spec-kitty merge`; a PR to `main` follows per CLAUDE.md's no-direct-push policy).

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

## Subtasks & Detailed Guidance

### Subtask T023 – UI-e2e Python coverage merged into the report (FR-013a)

- **Purpose**: Credit `src/specify_cli/dashboard/**` server-side code that Playwright drives but that the backend test jobs in `ci-quality.yml` never import directly.
- **Steps**: add `--cov=src/specify_cli/dashboard --cov-report=xml:out/reports/coverage/coverage-ui-e2e.xml` to the `pytest tests/ui/` run step; add an `actions/upload-artifact@v4` step naming the artifact so it matches the `*-reports` pattern `ci-quality.yml`'s sonarcloud job scans for (e.g. `name: ui-e2e-coverage-reports`, `path: out/reports/coverage/coverage-ui-e2e.xml`); resolve the cross-workflow visibility gap per Context & Constraints (pick path 1 or 2 and record which).
- **Files**: `.github/workflows/ui-e2e.yml` only.
- **Parallel?**: Root WP, independent of WP01–WP06's topology chain and of WP07 (spec.md: "WP-J + WP-K together restore a fair coverage denominator" — independently shippable).
- **Notes**: Do not widen the `--cov` scope beyond `src/specify_cli/dashboard` — a broader scope would double-credit code already covered by other jobs and risks masking a real coverage drop elsewhere.

### Subtask T024 – JS coverage → lcov, or documented deferral (FR-013b)

- **Purpose**: Decide, with evidence, whether `dashboard.js` coverage is feasible to wire this mission or must be deferred.
- **Steps**: spike Playwright's CDP coverage API (`page.coverage.startJSCoverage()`/`stopJSCoverage()`) or an `nyc`/`istanbul`-instrumented serve step; estimate the added job time against the 15-minute timeout. If it fits, wire `sonar.javascript.lcov.reportPaths` in `sonar-project.properties` (coordinate with WP07 — that file is WP07's owned surface, so route the actual property-file edit through WP07 or a fast-follow, don't edit it directly from this WP). If it does not fit, write the deferral rationale directly into this WP's Activity Log and flag it for WP09's T027 docs update.
- **Files**: `.github/workflows/ui-e2e.yml` (investigation/spike changes only); no other file is owned by this WP.
- **Parallel?**: Can run alongside T023; both land in the same file so sequence commits to avoid a self-inflicted merge conflict.
- **Notes**: This is explicitly allowed to conclude "deferred" — GC-6/FR-013 do not mandate JS coverage, only that the decision is not silent.

## Test Strategy (include only when tests are required)

- Local repro: `PWHEADLESS=1 uv run pytest tests/ui/ --cov=src/specify_cli/dashboard --cov-report=term -q` — confirm non-zero coverage percentage is reported for `src/specify_cli/dashboard`.
- `PWHEADLESS=1 uv run pytest tests/ui/ --cov=src/specify_cli/dashboard --cov-report=xml:out/reports/coverage/coverage-ui-e2e.xml -q && test -s out/reports/coverage/coverage-ui-e2e.xml` — confirm the XML is written and non-empty.
- If path 1 (cross-workflow download) is implemented: trigger both workflows (push/PR) and confirm the sonarcloud job's "Discover coverage XMLs" step logs `coverage-ui-e2e.xml` among `Discovered coverage reports`.
- Note the coverage-preservation invariant (WP02, GC-2/GC-2b) is about the *backend* test-selection union, not this WP — it is unaffected by this change, but do not regress `new_coverage` (coverage memory: never pad, only credit real exercised code).
- `pytest tests/architectural/test_no_legacy_terminology.py` — this WP touches workflow prose/comments.

## Risks & Mitigations

- **Risk**: assuming the artifact "just merges" because the property key is `sonar.python.coverage.reportPaths` (plural/comma-joined) — as shown above, the cross-workflow `download-artifact` scoping is the actual blocker, not the Sonar property. **Mitigation**: verify end-to-end via a real workflow run before marking T023 done; do not accept "the XML exists locally" as sufficient evidence.
- **Risk**: adding `--cov` bloats the 15-minute job timeout (`timeout-minutes: 15`). **Mitigation**: measure the added wall-clock on a real run; `--cov` instrumentation overhead on one Playwright test should be small, but confirm rather than assume.
- **Risk**: JS coverage spike (T024) balloons scope trying to make istanbul/CDP wiring "complete." **Mitigation**: time-box the spike; a documented deferral is an acceptable, valid outcome per FR-013's own wording ("or — for assets that genuinely cannot be covered — exclude them (FR-012) and document the decision").
- **Risk**: editing `sonar-project.properties` from this WP conflicts with WP07's `owned_files` scope. **Mitigation**: any Sonar-property-file need from T024 gets routed through WP07 or a fast-follow, never edited unilaterally here.

## Review Guidance

- Confirm `--cov=src/specify_cli/dashboard` (not broader) is added to the `pytest tests/ui/` step.
- Confirm the artifact-visibility gap (cross-workflow `download-artifact` scoping) was addressed OR explicitly documented as deferred — a PR that silently uploads an artifact nobody consumes should not pass review.
- Confirm the JS-coverage decision (wired or deferred) is written down, not left implicit.
- Confirm no edit landed in `sonar-project.properties` from this WP (that surface belongs to WP07).
- **Scope boundary (paula-patterns, MEDIUM)**: do NOT reject this WP for failing to land the actual cross-workflow `download-artifact` step in `ci-quality.yml` or the `sonar.javascript.lcov.reportPaths` key in `sonar-project.properties` — those are WP06/WP07-owned fast-follows, not WP08's Definition of Done. Do reject if the coverage artifact isn't produced/uploaded, or if the cross-workflow-gap analysis / JS-coverage decision is missing or unrecorded.

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

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP08 --to <status>` to change WP status.
- 2026-07-12T18:56:57Z – claude:sonnet:implementer-ivan:implementer – shell_pid=1150293 – Assigned agent via action command
- 2026-07-12T19:06:17Z – claude:sonnet:implementer-ivan:implementer – shell_pid=1150293 – Ready: --cov added to tests/ui step; JS-coverage decision recorded (deferred, static/** exclusion interim)
- 2026-07-12T19:06:50Z – claude:opus:reviewer-renata:reviewer – shell_pid=1200912 – Started review via action command
- 2026-07-12T19:12:00Z – user – shell_pid=1200912 – Review passed (reviewer-renata): FR-013a --cov=src/specify_cli/dashboard correctly scoped (not widened) + xml report out/reports/coverage/coverage-ui-e2e.xml + upload-artifact ui-e2e-coverage-reports (matches ci-quality *-reports pattern); YAML valid; cross-workflow Sonar-consumption gap explicitly recorded as WP06 fast-follow (hardened DoD honored, not rejected for it); T024 JS-coverage decision recorded DEFERRED with rationale (static/** interim via WP07); no edit to sonar-project.properties or ci-quality.yml; sole owned file .github/workflows/ui-e2e.yml changed.
