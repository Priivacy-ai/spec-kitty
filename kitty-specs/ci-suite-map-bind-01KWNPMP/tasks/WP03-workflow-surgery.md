---
work_package_id: WP03
title: 'Workflow surgery: residual job, bounded fixes, drain, catch-all, triggers, self-mapping'
dependencies:
- WP01
- WP02
requirement_refs:
- FR-002
- FR-004
- FR-006
- FR-007
- FR-010
- FR-011
- FR-012
- FR-013
tracker_refs: []
planning_base_branch: tidy/ci-suite-map-2034
merge_target_branch: tidy/ci-suite-map-2034
branch_strategy: Planning artifacts for this mission were generated on tidy/ci-suite-map-2034. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/ci-suite-map-2034 unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
phase: Phase 2 - Surgery
assignee: ''
agent: "claude-orchestrator"
shell_pid: '3883381'
history:
- at: '2026-07-04T05:27:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: .github/workflows/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- .github/workflows/ci-quality.yml
- .github/workflows/ci-windows.yml
- tests/architectural/_gate_coverage_baseline.json
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Workflow surgery (single owner of both workflow files)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

ALL `ci-quality.yml` + `ci-windows.yml` edits, in one owner (co-tenancy spine). Read spec rev 4's FR-002/004/006/007/010/011/012/013 + Adjudicated Decisions 7-8 FIRST — the mechanisms are pre-decided (HiC rulings); do not redesign them.

## Subtasks & Detailed Guidance

### Subtask T007 – Residual job + quality-gate wiring (FR-002)
- New job `unit-contract-residual`: full-tree pytest with the residual expression `(unit or contract) and not (fast or integration or git_repo or slow or e2e or architectural or distribution or windows_ci or quarantine or timing)` — RE-DERIVE the routed set from WP01's parse surface first (NFR-004; ~252 tests, ~seconds; record the collect count). NOT draft-gated; triggered on src/tests changes or always (cheap — prefer always-on for simplicity). Excludes `windows_ci`/`quarantine` by construction of the expression.
- Add to quality-gate's `needs:` AND its result loop (blocking). Run the full selection locally first — must be 100% green (fix-all-before-gate, Decision 5; adjudicate any red via judge-the-test and report).

### Subtask T008 – Bounded fixes + drain + widen (FR-004, FR-006, FR-007)
- FR-004 re-verifications: (a) `integration-tests-charter` phantom — re-verify declared+read (renata says already fixed ~:2938/:2988) → record verified-already-fixed in the Activity Log; (b) `mission-loader-coverage` — add to quality-gate `needs:` + result loop (it's an [ENFORCED] per-package gate; make it reachable); (c) `src/mission_runtime/*` diff-cover vacuous entry — add `--cov=src/mission_runtime` to the job(s) that run `tests/mission_runtime`-owning suites (find them via WP01's parse surfaces), so the critical-path entry is backed (FR-005's invariant will pin it); (d) SAME-CLASS (nightly census 2026-07-04): top-level `src/glossary/` (6,379 LOC) has NO `--cov` emitter in any shard — add `--cov=src/glossary` to the shard running `tests/glossary/` (the measured `glossary/__init__.py` in existing XMLs was the now-deleted `src/specify_cli/glossary` shim, a different package); (e) unshim-wave2 residue (refresh-squad census 2026-07-04, post-rebase onto the #2337 landing): the deleted packages left a dead `'src/specify_cli/next/*'` diff-cover critical-path entry (~:2233 — zero emitters, source dir gone; `src/runtime/next/*` on the adjacent line is the live successor) AND 4 dead src dorny filter globs (`src/specify_cli/next/**` ~:151; `src/specify_cli/charter_freshness|charter_lint|charter_preflight/**` ~:209-211 — the tests/-side globs in those groups are still alive, keep them) — remove the dead entries (FR-003c/FR-005 same-class; WP04's invariants assert this floor).
- FR-006 drain: add `tests/coordination` + `tests/paths` to the matching integration-shard path lists (they use subprocess → the `git_repo/integration` marker family; verify each file's markers). Adjudicate `tests/_support/git_template/test_git_template.py`: route it OR record intentionally-non-gated with rationale (spec US4-AC2 — no silent floor). Then regenerate `_gate_coverage_baseline.json` via the module's regeneration path: orphans → 0 (or the one recorded exception), duplicates re-derived HONEST (baseline said 2,944, live census 3,297 as of the 2026-07-04 post-rebase refresh — treat as indicative, pin YOUR re-derived number; NFR-003 shrink-only from there; the residual job may add duplicates — record the delta and justify: tests selected by both the residual job and a path gate).
- FR-007: `ci-windows.yml` src coverage → `src/**` (or explicit per-package exclusions with rationale in a comment). MECHANISM NOTE (refresh 2026-07-04): ci-windows.yml has NO `on: paths` filter — gating is the dorny `paths-filter` job (`windows_critical`); widen THAT filter's globs, do not add a top-level `on: paths` key.

**WP02 script contract (reviewer-renata notes, 2026-07-04 — the script is APPROVED and frozen; wire to THIS contract):**
1. Pass the six release-required jobs (`build-wheel`, `clean-install-verification`, `consumer-compatibility`, `fast-tests-release`, `integration-tests-release`, `uv-lock-check`) as `release_required_jobs` — the script will not invent them (Decision 8), and each MUST be present in `needs` or it exits 2.
2. All three flags (`run_all`, `catchall_unmatched`, `pr_is_draft`) + non-empty `needs` are REQUIRED fields — no defaults; emit `pr_is_draft: "false"` on non-PR events.
3. Do not map a job to zero groups if it is actually filter-gated (always-run jobs with no `job_groups` entry that report `skipped` pass as legitimately-skipped — WP04's mapping≡gating invariant is the guard).
4. Exit codes: 0 pass / 1 fail / 2 contract-violation-or-C-005-tripwire — the workflow step must fail on ANY non-zero and must not treat 2 as soft.
5. Input shapes accepted: `needs` as job→result-string OR GitHub-native `{"result": ...}` objects; `changes` values as 'true'/'false' strings (dorny) or bools.

### Subtask T009 – Catch-all + trigger + self-mapping + script wiring (FR-010, FR-013, FR-012, FR-011)
- FR-010 mechanism (Decision 7b — EXACTLY this shape): add `any_src: ['src/**']` probe group; a script step after the filter computes `unmatched = any_src && !(g1 || g2 || ...)` FROM THE FILTER'S OWN OUTPUTS (enumerate the group outputs in ONE place in the step; WP04's invariant asserts that list ≡ the parsed group set — a negated path mega-glob is FORBIDDEN); thread `unmatched` into the existing `run_all` OR-seam (~:84-103) so every per-module output forces true. Add a named `glossary` group → route to the natural owner shard (adjudicate which; likely core-misc family) as the first targeted-group example.
- FR-013 (Decision 7a): `on: pull_request: types: [opened, synchronize, reopened, ready_for_review]`.
- FR-012 two-layer: add the OTHER suite-running workflows (`ci-windows.yml`, `drift-detector.yml`, `release.yml`) to ci-quality's outer `on: paths:` AND a dorny group routing them to the architectural shard (core_misc already covers `ci-quality.yml` + `tests/architectural/**` — verify and record verified-already-fixed for that portion).
- FR-011 wiring: replace the inline pass/fail bash in quality-gate with an invocation of `scripts/ci/quality_gate_decision.py` (WP02), assembling its JSON inputs: needs context, changes outputs, the job→groups mapping (generate it inside the workflow adjacent to the `if:` definitions — ONE derived list, which WP04 asserts against the parsed gating; Decision 8), `run_all`/`unmatched`/draft flags + the draft-gated job set. Emit the script's table to `$GITHUB_STEP_SUMMARY`. `quarantine-visibility` stays OUT of the blocking set (C-005).

### Subtask T010 – Gates + probes
- `PWHEADLESS=1 pytest tests/architectural/test_gate_coverage.py -q` — green against the regenerated baseline; `python -m tests.architectural._gate_coverage --check` output pasted (orphans 0 ± exception).
- YAML validity: `python -c "import yaml; yaml.safe_load(open('.github/workflows/ci-quality.yml'))"` (and ci-windows).
- Residual selection dry-run green (T007's run counts recorded).
- Probe branches (C-007, non-draft — record run links in the Activity Log): A) touch `src/glossary/<file>` → unmatched/glossary group fires ≥1 test job; B) touch a well-mapped file → its shard runs, `unmatched=false`; C) draft→ready flip re-triggers ci-quality AND the linked run shows quality-gate completing with the step-summary table present (the re-triggered run must EVALUATE, not merely exist — link the specific run). The mission PR itself is the fourth probe.
- Diff-scoped ruff on any .py touched; existing arch suite green.

## Campsite cleaning (standing rule [[feedback-sonar-attack-vector-campsite]]; paula YAML census 2026-07-04 — SAFE/ADJACENT only, ride the review)

- ci-quality.yml:1222-1242 — [DUP] fast-tests-core-misc 22-line hand-mirrored `--ignore` list: your catch-all mechanism IS this section's replacement authority; do not leave the literal mirror unannotated (FR-012's invariant binds it).
- ci-quality.yml:2916-2958 ↔ 2966-3008 — [DUP] quality-gate re-types the `needs:` list into the bash loop: the decision-script wiring must consume `toJSON(needs)`, never a re-enumerated literal list.
- ci-quality.yml:2964 — [BASH] drop the scaffolding `echo "All upstream jobs completed."` in the rewrite.
- ci-quality.yml:3015-3028 — [BASH] the release-subset "must be success" two-tier rule is load-bearing LOGIC — move it INTO the decision script (WP02's script has the semantics slot); shed only the literal re-listing. Coordinate with WP02 if its input schema needs a release-required job set.
- ci-quality.yml:96 + :172-173 — [DEAD] `orchestrator_api` filter output consumed by zero jobs — remove output+filter (confirm no job for it is planned; record the adjudication).
- ci-quality.yml:84-103 — [PATTERN] the run_all OR-shape is verified consistent across all 20 outputs; your `unmatched` threading and new group outputs must copy that exact shape — no variants.
- ci-windows.yml:25-39 — [SPLIT-BRAIN] the static windows_ci file list has drifted from the `git grep` discovery in the run step (3 marked files missing: tests/lanes/test_acceptance_matrix.py, tests/review/test_baseline.py, tests/specify_cli/cli/commands/test_charter_generate_autotrack.py) — FR-007's widening should make the filter unable to under-fire vs the grep authority.
- ci-windows.yml:102 — [STALE] reword the "WP03 conditional marker" error string (names a PAST mission's WP03) to describe the keyring-absent invariant.
- ci-windows.yml:56 — [NIT] actions/checkout@v4 → @v6 (matches :15 and all of ci-quality.yml).
- OUT (do not fold; tracked homes): 38× copy-pasted setup block → composite-action extraction is a separate CI-hygiene mission (the new residual job MIRRORS the existing block; GitHub workflows do not support YAML anchors); tests/regression vs tests/regressions dir consolidation → test-structure home.

## Definition of Done
- Per-FR reviewer checklist (each line confirmed individually — the broad claim alone does not satisfy this DoD):
  - FR-002: `unit-contract-residual` job exists, not draft-gated, in quality-gate `needs:` AND result loop; local selection run count recorded.
  - FR-004: each named candidate's disposition recorded (fixed vs verified-already-fixed) incl. mission-loader-coverage reachability, `--cov=src/mission_runtime`, `--cov=src/glossary`, AND the unshim-wave2 residue (dead `src/specify_cli/next/*` critical-path entry + 4 dead src filter globs).
  - FR-006: baseline regenerated, orphans 0 (± the one recorded adjudication); `--check` output pasted.
  - FR-007: ci-windows paths cover `src/**` or carry per-package rationale.
  - FR-010: `any_src` group + output-derived `unmatched` step + OR-seam threading + `glossary` group — no negated mega-glob anywhere.
  - FR-011: quality-gate invokes the WP02 script with needs-context + changes-outputs + job→groups JSON (derived adjacent to the `if:`s) + run_all/unmatched/draft flags; `quarantine-visibility` absent from the blocking set.
  - FR-012: outer `on: paths:` + dorny group cover ci-windows/drift-detector/release; the already-covered ci-quality portion recorded verified-already-fixed.
  - FR-013: `types:` includes `ready_for_review`.
- Every re-verification recorded; probe evidence linked (probes A/B/C with the specific run URLs).

## Risks / Reviewer Guidance
- REJECT: a negated mega-glob catch-all; a hand-written job→group table not derived adjacent to the `if:`s; `quarantine-visibility` anywhere in the blocking set; a residual expression hardcoding marker names WP01's parse contradicts.
- The catch-all must NOT fire on mapped-only changes (probe B is the evidence; WP04 adds the fixture assertion).
- CI-minutes: record the residual job's wall-clock (NFR-002 < 3 min) and confirm no shard got heavier.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-04T05:27:33Z – system – Prompt created.
- 2026-07-04T11:59:41Z – claude-orchestrator – shell_pid=3883381 – 4 commits on lane-c (adadac381/40d3ab47e/24e1435e8/424f121f6); all 8 FRs done w/ per-FR dispositions; probes A-D green (flip run 28705381819 in_progress at handoff); 5 out-of-owned judge-the-test re-pins flagged for review. (--force = #2346 guard substring bug: WP04's heading '(depends: WP03)' harvests T011-T014 into WP03's scan; WP03's own T007-T010 all checked)
- 2026-07-04T12:18:50Z – claude-orchestrator – shell_pid=3883381 – reviewer-renata REJECT (1 BLOCKER + 1 MINOR fix): decision-step exit code swallowed by tee pipe under default bash -e (no pipefail) — gate vacuous on GitHub; fix shell/rc-capture + PIN in tests. MINOR: tests/paths shard entry is a routing no-op (unit-marked, residual-routed). All structural cross-checks 0 mismatches; re-pins adjudicated legitimate; census honest.
- 2026-07-04T09:35:00Z – wp03-implementer – RED baseline recorded: --check = 28573 total / 17 orphans / 4 files / 3291 duplicates (my re-derived pin); routed set 8; qg needs 42==reads 42; 20 groups; types=(); dead src/specify_cli/next + 3 charter_* dirs verified absent; orchestrator_api group zero consumers.
- 2026-07-04T09:50:00Z – wp03-implementer – residual re-derived: collect 252/28573; full selection 252 passed in 61.42s local (100% green, no fixes needed).
- 2026-07-04T10:05:00Z – wp03-implementer – ci-quality.yml surgery: FR-013 types, FR-012 outer paths + core_misc routing, FR-010 any_src+unmatched step+OR-seam threading+glossary group, FR-002 residual job, FR-004 fixes (mission-loader needs, cov backings, dead entries removed), FR-006 shard drain; ci-windows.yml src/** + campsite (commit adadac381).
- 2026-07-04T10:10:00Z – wp03-implementer – FR-011 quality-gate rewrite onto WP02 script: toJSON(needs), JOB_GROUPS cross-checked ≡ parsed if:-gating (0 mismatches), 9/9 payload smokes + exact-heredoc e2e PASS, C-005 tripwire verified exit 2.
- 2026-07-04T10:15:00Z – wp03-implementer – FR-006 adjudication: git_template is integration+git_repo (not unit) → ROUTED via misc shard tests/_support; newly-routed 24 passed; baseline regenerated 0 orphans / 0 files / 3550 duplicates (delta +259 justified: residual double-selection) (commit 40d3ab47e).
- 2026-07-04T10:20:00Z – wp03-implementer – judge-the-test re-pins (3 arch): zero-orphan canary conditional-on-baseline, qg needs_result_reads==∅ pin, e2e gate test re-pinned to decision step; arch suite 653 passed / 4 skipped (commit 24e1435e8).
- 2026-07-04T10:30:00Z – wp03-implementer – probes A-D pushed (C-007; lane-b script already merged into lane-c, no cherry-pick needed); PRs #19-#22 on the fork.
- 2026-07-04T10:40:00Z – wp03-implementer – probe C draft run caught 2 stale tests/release pins (critical-path next/* literal; qg steps[0].run KeyError) → re-pinned; all workflow-parsing suites 160 passed (commit 424f121f6); probes force-refreshed.
- 2026-07-04T10:45:00Z – wp03-implementer – FR-010 positive-arm proof: exact unmatched-step script executed with stubbed outputs — unmatched=true + warning (live positive structurally impossible pre-merge: mechanism PR always matches core_misc; WP04 fixture is the permanent guard).
- 2026-07-04T11:10:00Z – wp03-implementer – all four probe runs GREEN; probe-C draft table verbatim: itcm/e2e matched+skipped+OK (draft-exempt), residual always-run success on draft, NFR-002 2m22s; flip re-triggered run 28705381819 (ready_for_review) with draft-skipped suites executing.
- 2026-07-04T11:20:00Z – wp03-implementer – close-out: PRs #19-#22 closed, probe branches deleted (remote+local), tree clean, 4 commits on lane-c.
- 2026-07-04T12:20:00Z – claude-orchestrator – Ported the 11 wp03-implementer entries (2nd attempt: first port landed on lane-c via CWD drift, committed as c82abe796 there — lane reset to 424f121f6, kitty-specs net-zero restored). Probe-C flip run 28705381819 in_progress at review time; mission PR must evidence a completed post-flip evaluation.
- 2026-07-04T12:45:00Z – wp03-implementer – BLOCKER fixed (commit 946148f9e): added `shell: bash` to the "Evaluate quality-gate decision" step in ci-quality.yml — enables `-eo pipefail` so quality_gate_decision.py exit 1/2 propagates through `| tee` (the rewired gate was vacuous on GitHub's default bash -e). Live repro: bash -e → rc=0, bash -eo pipefail → rc=1.
- 2026-07-04T12:45:00Z – wp03-implementer – BLOCKER pinned red-first: extended decision-step assertions in test_ci_quality_path_filters.py::test_e2e_cross_cutting_failures_are_quality_gated and test_release_ci_ownership.py::test_quality_gate_fails_closed_for_release_required_package_jobs to assert shell=="bash"; RED against pre-fix YAML (None == 'bash'), GREEN after.
- 2026-07-04T12:45:00Z – wp03-implementer – MINOR fixed: dropped dead tests/paths entry from integration-tests-core-misc misc shard (unit-marked → routed by unit-contract-residual, never the misc shard; restores parity with the conformance mirror test_core_misc_shards_plus_e2e_owner_cover_legacy_selection). Validation: YAML parses; test_ci_quality_path_filters.py + tests/release/ = 139 passed/7 skipped; ruff clean.
- 2026-07-04T12:32:59Z – claude-orchestrator – shell_pid=3883381 – review-fix 946148f9e: BLOCKER (shell:bash pipefail, red-first pinned in 2 decision-step tests) + MINOR (dead tests/paths dropped) fixed; 139 passed/7 skipped, ruff clean. (--force = #2346 WP04-heading substring guard bug)
- 2026-07-04T12:37:01Z – claude-orchestrator – shell_pid=3883381 – Moved to in_review
- 2026-07-04T12:37:02Z – claude-orchestrator – shell_pid=3883381 – reviewer-renata APPROVE (2nd pass after 1-BLOCKER+1-MINOR reject): fix 946148f9e verified live — shell:bash pipefail propagates exit 1/2 (gate no longer vacuous), pin red-first non-vacuous, tests/paths dropped w/ parity restored, 139 passed/7 skipped. Probe-C flip run 28705381819 completed GREEN. Prior full review stands: all 8 FRs, JOB_GROUPS 0 mismatches, census honest (0 orphans/3550 dup), 5 re-pins legitimate. (--force=#2346 WP04-heading guard bug)
