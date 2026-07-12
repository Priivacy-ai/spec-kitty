# Approach Trace — coord-shadows-followups

The methodology: research front-loading, squad cadence, WP sizing — to assess ROI at close.
Tracked under #2095.

## Seed (planning)

**Front-loaded research (brownfield onboarding):**
- 4-lens pre-spec squad (renata/randy/paula/priti, all opus, read-only) RE-VERIFIED all 5 findings on aligned main before any spec work. ROI so far: HIGH — caught that (a) #2566 is OUT (wrong epic), (b) F1's better home is the existing `missions/_read_path_resolver.py` (all 3 sites already import it), (c) #2567 is a semantics-CHANGE needing ratification not a mechanical fold, (d) F2/F3 needed new issues (#2575/#2576 filed pre-spec), (e) #2568 sequences after F2.
- Paula's full-landscape sweep confirmed the "known counts" (3 F1 sites, 1 stray parser, 1 stray liveness probe) were EXHAUSTIVE — no hidden 4th sites → prevented an over-broad sweep.

**Squad cadence (per feedback_preflight_squad_cadence):**
- Post-spec 2-lens squad (renata fidelity + randy scope) → unanimous READY; added C-007 (fence the liveness baseline to one additive field) + reworded US2.1 test seam (simulated baseline mismatch, not OS PID-recycle).

**WP sizing:** ~5 WPs, 1:1 item→WP (both squads converged). IC map = IC-01..IC-05.

**Post-plan 2-lens squad (architect-alphonso + planner-priti):** priti = TASKS-READY (keep IC-02 monolithic — don't split; DAG = WP02→WP05 spine + WP01/03/04 free; disjoint owned-files; 5 non-droppable test rows). alphonso = NEEDS-FIX (ONE real gap): the plan under-scoped IC-02's claim-write — `implement.py:1400` is NOT the only `shell_pid` writer; `workflow_executor.py:668` (the primary `agent action implement` claim) + `:1338` (review claim overwrites shell_pid) are independent and staleness reads all of them. HIGH-ROI catch: without it the primary loop emits baseline-less claims → false-stale regression. FOLDED: D3a (additive degradation, absent-baseline preserves live-PID trust = zero legacy regression) + D3b (co-write baseline at all 3 sites via one helper, close-by-construction). Front-loaded squad ROI: HIGH again — a plan-altitude architecture gap caught before /tasks, not at implement.

**Post-tasks 2-lens squad (renata anti-laziness + paula campsite/sonar):** renata = TASKS-SOUND (all 5 non-droppable test rows discrete + placed as T001/T014-T017/T019/T022/T025/T027/T030; FR-001..010 fully covered; all file:line anchors verified live incl. the two load-bearing premises). paula = clean (every edit complexity-REDUCING; no WP crosses 15). FOLDED 4 new-code-coverage tests (direct seam 3-branch, baseline positive-match, direct claim-helper, direct iterator-branch) + WP02 two-write-API design constraint (helper must not branch on API shape) + baseline-field-name-as-constant + don't-clean warnings (process_liveness broad except, WP03 separate-not-swallow handler). All 4 squads (pre-spec/post-spec/post-plan/post-tasks) ROI: HIGH — each caught something the next phase would have paid for.

## Append (implement)

<!-- append: did the WP sizing hold? did squad findings pay off? rework caused/avoided? -->

## Assess (close)

<!-- fill at close: squad-cadence ROI, which point-cut caught the most, front-load value -->
