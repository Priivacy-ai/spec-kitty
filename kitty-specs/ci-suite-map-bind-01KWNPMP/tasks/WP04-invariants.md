---
work_package_id: WP04
title: 'Invariant suite: marker completeness, workflow coherence, path-topology guards'
dependencies:
- WP01
- WP03
requirement_refs:
- FR-001
- FR-003
- FR-005
- FR-008
- FR-010
- FR-011
- FR-012
- FR-013
tracker_refs: []
planning_base_branch: tidy/ci-suite-map-2034
merge_target_branch: tidy/ci-suite-map-2034
branch_strategy: Planning artifacts for this mission were generated on tidy/ci-suite-map-2034. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/ci-suite-map-2034 unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
phase: Phase 3 - Guards
assignee: ''
agent: "claude-orchestrator"
shell_pid: '40821'
history:
- at: '2026-07-04T05:27:33Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent:
- tests/architectural/test_marker_job_completeness.py
- tests/architectural/test_workflow_coherence.py
- tests/architectural/test_src_filter_coverage.py
- tests/architectural/_workflow_fixtures/
execution_mode: code_change
model: ''
owned_files:
- tests/architectural/test_marker_job_completeness.py
- tests/architectural/test_workflow_coherence.py
- tests/architectural/test_src_filter_coverage.py
- tests/architectural/_workflow_fixtures/
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Invariant suite

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

The standing guards, bound over WP01's parse surfaces, green against WP03's fixed workflows, each with fault-injection red proof and (FR-010/FR-012) reorder red-negatives. `_gate_coverage.py` is READ-ONLY for you — if a parse surface is missing, that's WP01 feedback, not your edit. All new tests: `pytestmark = pytest.mark.architectural` (CI-selected — NFR-005; verify against pytest.ini + the architectural shard expression).

## Subtasks & Detailed Guidance

### Subtask T011 – Marker completeness (FR-001), `test_marker_job_completeness.py`
- Three-state: every pytest.ini-registered marker is (i) ROUTED-BY-MARKER (positive token in ≥1 gate — WP01's extractor), (ii) ROUTED-BY-PATH (every collected test carrying the marker reaches ≥1 path gate — reuse the orphan model's evaluation; may reuse its cached collection), or (iii) in `CI_INVISIBLE` (dict marker → non-empty reason, defined in this test file).
- Hard-asserts: `unit`/`contract` MUST be state (i) — red even if someone allowlists them (write the assertion so the allowlist path is unreachable for them). Reverse containment: `CI_INVISIBLE` keys ⊆ registered markers.
- Derive the honest membership: expected state-(i) post-WP03 = the 8 + `unit` + `contract`; classify the remaining ~27 into (ii)/(iii) with per-marker reasons — verify EACH (ii) claim via the orphan model, don't hand-assert. Record the final split in the test's docstring. Note on `quarantine`: its marked population is 18 as of 2026-07-04 (17 under #2295/#2309 + `test_200_missions_under_5s` under #2342) — cite all three issues in any reason string and never hard-pin a population count.
- Fault-injection fixtures (`_workflow_fixtures/`): synthetic unrouted marker → red naming it; de-routed `unit` (fixture gate set without the residual job) → red; `unit` in a fixture CI_INVISIBLE → STILL red. States (i)/(iii) checks collection-free (NFR-001).

**WP03 post-surgery contract notes (2026-07-04 — the surgery is on lane-c; these are your BINDING inputs):**
1. FR-003(d) reshaped: quality-gate consumes needs via step env `NEEDS_JSON: ${{ toJSON(needs) }}` — `needs_result_reads["quality-gate"] == ∅` by construction (WP01's parser reads only `run:` text — known parse-surface gap, do NOT edit the module; model the toJSON form instead: assert the decision step exists with `NEEDS_JSON == "${{ toJSON(needs) }}"` AND zero literal `needs.<job>.result` reads — a literal read reappearing = re-enumeration drift).
2. Greppable anchors WP03 left for you: the unmatched-step enumeration (`steps.filter.outputs.<g>`), the JOB_GROUPS / DRAFT_GATED_JOBS / RELEASE_REQUIRED_JOBS blocks in the quality-gate heredoc, the `any_src` and `glossary` groups.
3. The residual expression negates the routed 8 PLUS `e2e`/`distribution` (path-routed families, prevents heavy double-runs) — your routed-set-consistency assertion must be ⊇-shaped, not ==.
4. The FR-010 positive arm (unmatched=true) is live-unprovable pre-merge (self-mapping matches core_misc on any mechanism PR) — your fixture assertion IS the permanent guard; WP03 proved it via stubbed-output execution only.
5. pytest 9.0.3: `Expression.compile` raises plain `SyntaxError` (ParseError removed) — loud-fail fixtures must expect that. Also exercise WP01's ast-vs-pytest grammar-divergence guard (`_gate_coverage.py:321-326`, currently untested — renata residual).

### Subtask T012 – Coherence + mapping invariants (FR-003, FR-005, FR-008), `test_workflow_coherence.py`
- (a) every `needs.<job>.result` reference declared in that job's `needs:`; (b) every filter output consumed by ≥1 job `if:`; (c) every filter glob matches ≥1 tracked path; (d) quality-gate result-loop ↔ `needs:` symmetry for blocking jobs.
- FR-005: every diff-cover critical-path entry backed by ≥1 matching `--cov` emitter.
- KNOWN FLOOR ITEMS (refresh-squad 2026-07-04): unshim-wave2 left a dead `'src/specify_cli/next/*'` critical-path entry and 4 dead src filter globs in ci-quality.yml — WP03 FR-004(e) removes them. If your FR-005/FR-003(c) invariants red on these live, that is WP03-feedback territory per the standing rule below, NOT a reason to allowlist them.
- FR-008: the pytest-invoking workflow set (content probe over `.github/workflows/`) ≡ the parse model's allowlist — a new suite-running workflow fails closed.
- FR-011 mapping invariant (Decision 8): the job→groups list WP03 assembled for the aggregator ≡ the parsed job-`if:` gating map. Also assert `quarantine-visibility` ∉ the blocking set (C-005 pin).
- Fault-injection per relation on fixture YAML (undeclared needs-read; unconsumed output; dead glob; unbacked critical path; unlisted pytest workflow; mapping drift).

### Subtask T013 – Path-topology invariants (FR-010c/d, FR-012, FR-013), `test_src_filter_coverage.py`
- FR-010c NON-VACUOUS form (paula CRITICAL — exactly this, not "matched-or-caught"): the `unmatched` computation's group-reference set ≡ the parsed filter-group set (a group added/removed without catch-all wiring reds); AND every group output gates ≥1 test-running job. Plus the NFR-006 fixture: a change-set touching only mapped paths yields `unmatched=false` under the computation's logic (simulate on the parsed model).
- FR-012: each catch-all `--ignore` list ≡ the shard-owned test-root set (parsed relation).
- FR-013: `on.pull_request.types` includes `ready_for_review` (parsed, not line-pinned).
- Red-negatives (renata MEDIUM-6, both FR-010 and FR-012): reorder/rename groups and `--ignore` entries in a fixture WITHOUT changing the parsed relation → invariants STAY GREEN. These discriminate the parsed-relation implementation from a literal mirror — a literal-mirror implementation cannot pass them; include them.

### Subtask T014 – Gates
- `PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider` — full sweep green (your three files + everything pre-existing) against the LIVE post-WP03 workflows.
- Runtime: the three files' non-collection checks combined < 5 s (NFR-001; time them, record).
- Every fault-injection + red-negative result pasted verbatim in the Activity Log.
- Diff-scoped ruff exit 0; mypy stays Success.

## Campsite cleaning (standing rule [[feedback-sonar-attack-vector-campsite]]; randy census 2026-07-04 — sibling files you sit beside)

- test_ci_quality_path_filters.py:21-42 — introduce a `_load_workflow()` helper (match the sibling file's pattern); refactor `_path_filters()`, `_job_run_script()`, `_job()` to accept the pre-loaded dict (kills 3× repeated YAML disk loads). If WP01 exposed a canonical filter-block loader in the parse model, DELEGATE both files' `_path_filters()` to it instead (kills the cross-file duplication of the `step.get("id") == "filter"` extraction).
- test_ci_quality_path_filters.py:171-287 — extract `_LEGACY_CORE_MISC_ARGS` + `_SHARD_COMMANDS` as module-level constants (117-line test body → ~40).
- test_ci_quality_path_filters.py:276,:286 — trailing commas (COM812).
- test_ci_architectural_gate_coverage.py:1,:162 — D205 docstring blanks; `:118` list comprehension (PERF401).
- test_marker_registry_single_source.py — zero findings; no action.

## Definition of Done
- All invariants green live; honest marker-state split documented; NFR-001 timing recorded.
- T011's three fault-injection cases each recorded VERBATIM: (a) synthetic unrouted marker → red; (b) de-routed `unit` → red; (c) `unit` placed in a fixture CI_INVISIBLE → STILL red (the ineligibility hard-assert — the mission's core guard; skipping this one fails the DoD).
- Every other invariant's fault-injection red + the FR-010/FR-012 reorder red-negatives recorded verbatim.

## Risks / Reviewer Guidance
- REJECT: any literal job-name@line or `-m`-string pin (C-002); a hand-asserted ROUTED-BY-PATH claim not verified via the orphan model; missing red-negatives; `CI_INVISIBLE` entries without reasons or containing `unit`/`contract`.
- If a live invariant reds on WP03's output, that is WP03 feedback (file:line) — do not bend the invariant to pass.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-04T05:27:33Z – system – Prompt created.
- 2026-07-04T13:13:13Z – claude-orchestrator – shell_pid=40821 – commit 833cef7b1; 3 test files + fixtures; 691 passed/4 skipped live; 3 mandatory T011 reds captured; 2 design calls flagged (FR-012 ⊆ not ≡; 10/15/12 split supersedes spec guesses). (--force=#2346 WP05-heading guard bug)
- 2026-07-04T13:26:05Z – claude-orchestrator – shell_pid=40821 – Moved to in_review
- 2026-07-04T13:26:22Z – claude-orchestrator – shell_pid=40821 – reviewer-renata APPROVE (keystone review): core guarantee airtight (5 allowlist-escape attempts all red); every invariant non-vacuous by perturbation; both design calls legit vs live data; 691 passed/4 skipped; spine untouched. MINOR campsite folded to WP05. (--force=#2346 WP05-heading guard bug)
