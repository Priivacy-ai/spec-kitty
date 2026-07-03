---
work_package_id: WP03
title: Category_7 execution + adjudication records + closeout
dependencies:
- WP02
requirement_refs:
- FR-004
- FR-005
- FR-006
- FR-007
- FR-008
tracker_refs:
- '#2292'
- '#2289'
- '#1797'
planning_base_branch: tidy/unshim-wave1
merge_target_branch: tidy/unshim-wave1
branch_strategy: Planning artifacts for this mission were generated on tidy/unshim-wave1. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into tidy/unshim-wave1 unless the human explicitly redirects the landing branch.
subtasks:
- T008
- T009
- T010
- T011
- T012
phase: Phase 2 - Execution + closeout
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2563467"
history:
- at: '2026-07-03T12:00:28Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/sync/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/task_profile.py
- src/specify_cli/policy/audit.py
- src/specify_cli/sync/replay.py
- src/specify_cli/sync/tracker_client_glue.py
- src/specify_cli/sync/queue.py
- src/specify_cli/retrospective/lifecycle.py
- docs/architecture/documentation-mission.md
- docs/plans/degod-unshim-inventory.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Category_7 execution + adjudication records + closeout

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

Spec FR-004..FR-008 (IC-03 + IC-04): execute the category_7 adjudication — delete 4
orphans + their 3 single-purpose test shields with doc hygiene; drain
category_7/category_b atomically; make the two non-executed verdicts durable
(policy.audit follow-up issue; auth.transport ADR-deferred verdict + #2292
attribution correction); tracker closeout. Success = `_CATEGORY_7` is exactly
`{auth.transport, policy.audit}`, baselines category_7 2 / category_b 224, the C-001
diff check clean, all tracker artifacts posted, NFR-002 merge grep empty, closing
sweep green.

## Context & Constraints

- Read FIRST: spec.md rev 2 Cat-7 verdict table + research.md D2/D3/D4/D5/D8.
- **C-001 HARD BOUNDARY**: `src/specify_cli/auth/transport.py` and
  `test_auth_transport_singleton.py` (arch + any unit twin) MUST NOT appear in any
  diff of this WP. ADR `docs/adr/3.x/2026-05-18-2-delete-specify-cli-auth-transport.md`
  binds this (deferral to Robert). `policy/audit.py` + `test_audit.py` also stay
  intact (adopt-as-follow-up).
- Sibling-name traps (D2, D8): `auth.http.transport` is a DIFFERENT live module;
  `retrospective.lifecycle_events` is the live sibling of the deleted `lifecycle`.
- category_b arithmetic (D5): WP01 already removed the identity_aliases row (−1);
  this WP removes `sync.replay::*` ×8 + `tracker_client_glue::*` ×4 (−12) → baseline
  `category_b_grandfathered_legacy: 237` → `224`.
- Out-of-map leeway: the 3 shared gate files + the tests being deleted are
  WP01-owned or unowned; sequential lane + one-line rationale in the Activity Log.
- gh commands: prefix `unset GITHUB_TOKEN;`.
- Do NOT close #2289/#2292/#2258 by hand — they close via the PR body's `Closes`
  lines (record intended lines in the Activity Log).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: tidy/unshim-wave1
- **Merge target branch**: tidy/unshim-wave1

## Subtasks & Detailed Guidance

### Subtask T008 – Delete the 4 orphans + shields + docstring scrub

- **Steps**:
  1. `git rm`: `retrospective/lifecycle.py` (36), `sync/replay.py` (357),
     `task_profile.py` (155), `sync/tracker_client_glue.py` (285).
  2. `git rm` the 3 single-purpose shields: `test_replay_tenant_collision.py`,
     `test_task_profile_suggestion.py`, `test_tracker_bidirectional_retry.py`
     (locate exact paths via grep; each was adjudicated single-purpose — verify no
     OTHER test imports fixtures from them before deleting: paste the
     `grep -rn <shield_basename> tests/` result — which must show no importer
     outside the file itself — into the Activity Log BEFORE the `git rm`).
  3. Scrub the `:func:` replay docstring xref at `sync/queue.py:1352` (docstring
     text only — no code change).
- **Files**: the 4 modules + 3 test files + queue.py.

### Subtask T009 – Gate drains + C-001 check

- **Steps**:
  1. `test_no_dead_modules.py`: `_CATEGORY_7_GRANDFATHERED_ORPHANS` 6→2 (keep
     `auth.transport`, `policy.audit` rows; remove the 4 deleted).
  2. `test_no_dead_symbols.py`: remove `sync.replay::*` ×8 +
     `tracker_client_glue::*` ×4 category_b rows. Leave `_CATEGORY_B_T001_UNBLINDED`
     auth.transport rows untouched.
  3. `_baselines.yaml`: `category_7_grandfathered_orphans: 6` → `2`;
     `category_b_grandfathered_legacy: 237` → `224`.
  4. C-001 check: `git diff --name-only <WP-base>..HEAD | grep -E
     'auth/transport\.py|test_auth_transport_singleton'` → empty.
- **Files**: 2 gate files + baseline (leeway rule).

### Subtask T010 – Doc hygiene

- **Steps**:
  1. `docs/architecture/documentation-mission.md:899-901`: re-point the three
     `src/specify_cli/{gap_analysis,doc_generators,doc_state}.py` paths to their
     `src/specify_cli/doc_analysis/*.py` canonical homes (live doc, ~3 lines).
  2. `docs/plans/degod-unshim-inventory.md`: strike/mark-executed the category_4
     rows (8) + the 4 executed category_7 rows + the #2258 functions; note the
     mission id and date (~10 lines).
- **Files**: the 2 docs.

### Subtask T011 – Adjudication records + new debt issues

- **Steps** (all gh, `unset GITHUB_TOKEN;`):
  1. File the **policy.audit adopt follow-up** issue: title ~"Wire policy.audit
     governance-evidence log into the live override seams"; body = the intended
     emission points (commit_guard_hook, risk override, merge gate), the JSONL
     schema-freeze note, why it survived the wave (spec FR-006 + research D4);
     cross-link #2292 + this mission; label enhancement.
  2. Post the **#2292 verdict comment**: per-orphan table (4 executed, policy.audit
     follow-up with the new issue number, auth.transport DOCUMENTED-DELETE deferred
     to Robert citing ADR 2026-05-18-2) + the blocker-attribution correction
     (ADR/Robert, not #614/#391).
  3. File the **two new debt-class issues** (spec FR-008; operator may veto — check
     the mission Activity Log / orchestrator note before filing): (a) pre-3.0
     auto-discovered-migration retirement (87 modules, compat-gated — category_1
     census); (b) `test_example_round_trip` legacy-contract allowlist backfill (151
     entries). Reference epic #1797 and this mission in both.
  4. Update `kitty-specs/unshim-wave1-01KWKVHB/issue-matrix.md`: terminal verdicts
     (#2289 fixed, #2292 fixed, #2258 fixed) + rows for the newly filed issues.
- **Files**: issue-matrix.md + tracker.

### Subtask T012 – Tracker closeout + closing sweep

- **Steps**:
  1. Post the **#1797 progress comment**: category_4 8→0, category_7 6→2,
     category_b 237→224, #2258 folded, LOC accounting, what remains (Wave 2:
     #2290/#2291/#2293).
  2. NFR-002 merge grep (quickstart.md pinned pattern) → paste empty result.
  3. Closing sweep: `PWHEADLESS=1 pytest tests/architectural/ -q` +
     `PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider` +
     terminology guard + whole-tree mypy + ruff — record tallies.
  4. Record intended PR-body lines: `Closes #2289`, `Closes #2292`, `Closes #2258`.
- **Files**: none beyond the log (evidence-only).

## Test Strategy

```bash
export PATH="$PWD/.venv/bin:$PATH"
PWHEADLESS=1 pytest tests/architectural/test_no_dead_modules.py tests/architectural/test_no_dead_symbols.py -q
git diff --name-only <base>..HEAD | grep -E 'auth/transport\.py|test_auth_transport_singleton' || echo "C-001 clean"
PWHEADLESS=1 pytest tests/architectural/ -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/ -n auto --dist loadfile -p no:cacheprovider
PWHEADLESS=1 pytest tests/architectural/test_no_legacy_terminology.py -q
python -m mypy src/ 2>&1 | tail -2; ruff check .
```

## Risks & Mitigations

- **C-001 violation via bulk operations** — never `git rm src/specify_cli/auth/`-anything;
  the diff check in T009.4 is mandatory before handoff.
- **Shield deletion strands a fixture** — verify importers of each test file before
  `git rm` (D8 says none, but re-verify live).
- **Premature issue closure** — PR closes them; hand-closing breaks the audit chain.

## Review Guidance

- C-001 diff check output is the first thing to verify.
- `_CATEGORY_7` contents exactly `{auth.transport, policy.audit}`; baseline
  arithmetic 2/224 consistent with WP01's −1.
- The #2292 comment must contain the attribution CORRECTION, not just the verdicts.
- New issues filed (or an operator-veto note in the log) — absence of both is a reject.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-03T12:00:28Z – system – Prompt created.
- 2026-07-03T13:28:09Z – claude:opus:python-pedro:implementer – shell_pid=2346643 – Assigned agent via action command
- 2026-07-03T13:33:08Z – claude:opus:python-pedro:implementer – T008 shield-importer grep (BEFORE `git rm`, C-006 ordering). Command: `grep -rn <shield_basename> tests/` for each of the 3 single-purpose shields. Results (empty = no importer outside the file itself):
  - `grep -rn test_replay_tenant_collision tests/` → (empty)
  - `grep -rn test_task_profile_suggestion tests/` → (empty)
  - `grep -rn test_tracker_bidirectional_retry tests/` → (empty)
  Conclusion: no OTHER test imports fixtures from these shields; safe to delete. Cross-check (orphan live-importer grep across src/): `retrospective.lifecycle` → only status/dashboard `.lifecycle` siblings (different modules); `sync.replay` → only the queue.py:1352 docstring `:func:` xref (scrubbed in T008.3); `task_profile` → none; `sync.tracker_client_glue` → none. Deletion set closed per research D8.
- 2026-07-03T13:33:08Z – claude:opus:python-pedro:implementer – T008 `git rm` of 4 orphan modules (retrospective/lifecycle.py 36, sync/replay.py 357, task_profile.py 155, sync/tracker_client_glue.py 285) + 3 single-purpose shields (tests/integration/test_replay_tenant_collision.py, tests/specify_cli/test_task_profile_suggestion.py, tests/integration/test_tracker_bidirectional_retry.py) + scrubbed the `:func:specify_cli.sync.replay.replay_events` docstring xref at sync/queue.py:1352 (docstring text only, no code change).
- 2026-07-03T13:56:06Z – claude:opus:python-pedro:implementer – T009 gate drains. `_CATEGORY_7_GRANDFATHERED_ORPHANS` 6→2 (removed the 4 deleted; kept auth.transport + policy.audit with documented verdicts). `_CATEGORY_B_GRANDFATHERED_LEGACY`: removed `sync.replay::*` ×8 + `tracker_client_glue::*` ×4 (12 rows). **CASCADE FOUND (falsifies research D8's "strands no sibling"):** the dead-symbol gate (`test_no_public_symbol_in_all_is_unimported`) went RED on `specify_cli.frontmatter::update_field` — `task_profile` was its SOLE src/ caller (twin `update_fields` stays live via implement.py / lanes.implement_support). Live evidence over static: verified 0 src + 0 test references post-deletion. Resolution: per C-002 (deletion/triage only; NO live-code edits beyond docstring xrefs; adopt verdicts→follow-up) the live frontmatter.py was NOT edited (options 1-wire barred by C-002; 2/3-edit-__all__ barred by "no live module change"); the orphan was **adopted-as-follow-up** into `_CATEGORY_B` with a rationale, tracked under epic #1797. Baselines: `category_7_grandfathered_orphans` 6→2; `category_b_grandfathered_legacy` 237→**216**. NOTE on category_b arithmetic: spec FR-005 said 224 assuming baseline==live, but the recorded 237 had drifted +10 above the true pre-edit live (227) via prior warn-on-shrink cleanups; pinned the HONEST live value (227−12+1=216) per the mission's "accurate baselines for Wave 2" intent (#2293) and anti-vacuous-ratchet policy. Live counts verified == baselines (category_7=2 {auth.transport, policy.audit}; category_b=216). Gate tests: `test_no_dead_modules.py` + `test_no_dead_symbols.py` + `test_ratchet_baselines.py` → 14 passed.
- 2026-07-03T13:56:06Z – claude:opus:python-pedro:implementer – T009.4 C-001 boundary check: `git diff --cached --name-only HEAD | grep -E 'auth/transport\.py|test_auth_transport_singleton'` → **empty (C-001 clean)**. Neither `src/specify_cli/auth/transport.py` nor `test_auth_transport_singleton` appears in the WP03 diff (ADR 2026-05-18-2 C-005 honored). policy/audit.py + its test untouched.
- 2026-07-03T13:56:06Z – claude:opus:python-pedro:implementer – T010 doc hygiene. (1) `docs/architecture/documentation-mission.md:899-901`: re-pointed gap_analysis/doc_generators/doc_state to their `src/specify_cli/doc_analysis/*.py` canonical homes. (2) `docs/plans/degod-unshim-inventory.md`: struck the 8 executed category_4 shims + the 4 executed category_7 orphans (kept policy.audit/auth.transport verdicts), updated the category_b row 237→216, added a Wave-1 closeout note (mission id + 2026-07-03; #2258 fold; the frontmatter::update_field cascade; Wave 2 remainder #2290/#2291/#2293); bumped frontmatter `updated:` to 2026-07-03. #2258's record_merge/finalize_merge are not catalogued in this Lens-1 table (separate pre-mission op) → noted in the closeout banner rather than struck.
- 2026-07-03T13:56:06Z – claude:opus:python-pedro:implementer – T011 adjudication records + new debt issues (all `unset GITHUB_TOKEN;`, repo Priivacy-ai/spec-kitty). Filed: **#2321** policy.audit adopt-follow-up (enhancement, FR-006); **#2322** pre-3.0 auto-discovered-migration retirement (tech-debt, 87 modules, FR-008); **#2323** test_example_round_trip legacy-contract allowlist backfill (tech-debt, 151 entries, FR-008); **#2324** move-task subtask-completeness validator misattribution (bug — witnessed live: WP01 move blocked on WP02's T005-T007, WP02 blocked on WP03's T008-T012, both needed --force). Operator veto: NOT exercised (proceeded per orchestrator note). Posted **#2292 verdict comment** (issuecomment-4876939459): per-orphan table (4 deleted / policy.audit→#2321 / auth.transport documented-delete deferred to Robert) **WITH the blocker-attribution correction** (real blocker = ADR 2026-05-18-2 / Robert, NOT #614/#391) + the frontmatter cascade note. Updated `issue-matrix.md`: #2289→fixed, #2292→fixed (terminal), #2258 stays fixed; added deferred-with-followup rows for #2321/#2322/#2323/#2324; kept existing rows' `Issue|Title|Verdict|Evidence ref` schema.
- 2026-07-03T13:56:06Z – claude:opus:python-pedro:implementer – T012 closeout. Posted **#1797 progress comment** (issuecomment-4876944629): category_4 8→0, category_7 6→2, category_b 237→216, #2258 folded (−248 LOC), LOC accounting, Wave 2 remainder #2290/#2291/#2293. **NFR-002 merge grep** (quickstart.md pinned pattern) over src/: the exact-module-path branch is EMPTY (no deleted module imported). The full pinned pattern surfaces ONE benign false-positive — `mission_finalize.py:1218 from specify_cli.acceptance.matrix import scaffold_acceptance_matrix` — the regex `import .*acceptance_matrix\b` matches the substring inside the live function name `scaffold_acceptance_matrix`, importing from the CANONICAL `acceptance.matrix` module, not the deleted `acceptance_matrix` shim. No real violation. Closing sweep tallies: `tests/architectural/` full = **641 passed, 4 skipped, 34 warnings** (exit 0); terminology guard `test_no_legacy_terminology.py` = **3 passed**; whole-tree mypy (primary venv w/ types-toml) = **Success, 0 issues, 1058 files** (the lane/pyenv env lacks types-toml → 6 spurious stub errors, expected per prompt); ruff diff-scoped = **exit 0 clean**; ruff whole-repo = 1 PRE-EXISTING F401 in `kitty-specs/refactor-stable-gate-substrate-01KWK3FY/freeze_converter.py` (unrelated mission's scratch file, on base, NOT my diff — documented, not fixed). Full parallel suite (`pytest tests/ -n auto --dist loadfile`) = **28446 passed, 6 failed, 83 skipped, 19 xfailed** (4m33s). The 6 failures are EXACTLY the prompt's known-acceptable pre-existing/flake set, none touching this diff: `test_sphinx_generation_end_to_end` (env), `test_neutrality_lint::test_generic_artifacts_are_neutral`, `test_upgrade_command::...dry_run_json_contract`, `test_gitignore_contract::...trackable` (pre-existing on base), and the two parallel-order flakes `test_charter_epic_golden_path` + `test_upgrade_post_state::test_upgrade_then_branch_context_does_not_gate` — **verified to PASS in isolation (2 passed, live evidence)**. Documented, not fixed (out of WP03 scope). **Intended PR-body close lines:** `Closes #2289`, `Closes #2292`, `Closes #2258` (do NOT hand-close — the PR closes them).
- 2026-07-03T14:15:36Z – claude:opus:python-pedro:implementer – shell_pid=2346643 – WP03 category_7 execution + closeout complete (lane code commit e3f4fd2d2; planning-artifact commit be1a852f9 on tidy). Executed: 4 orphan deletes (task_profile/sync.replay/tracker_client_glue/retrospective.lifecycle) + 3 shields + queue.py docstring scrub; _CATEGORY_7 6→2 (auth.transport+policy.audit survive, documented verdicts); 12 category_b rows drained; baselines category_7=2, category_b=237→216 (honest live recompute — spec's 224 was off a +10-drifted baseline). CASCADE (falsifies D8): task_profile deletion orphaned frontmatter::update_field → adopted-as-follow-up per C-002 (+1 to category_b). C-001 CLEAN (auth/transport.py + singleton test untouched). Filed #2321/#2322/#2323/#2324; posted #2292 verdict+attribution-correction + #1797 progress comments. Gates: architectural 641p/4s; terminology 3p; mypy 0/1058 (primary venv); ruff diff-scoped clean; full suite 28446p/6f (all 6 known pre-existing/flakes; 2 flakes pass-in-isolation). NFR-002 grep empty (1 benign FP). PR closes: #2289/#2292/#2258.
- 2026-07-03T14:17:21Z – claude:opus:reviewer-renata:reviewer – shell_pid=2563467 – Started review via action command
