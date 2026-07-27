# Post-spec adversarial squad — findings record

**Mission**: tasks-py-degod-wave2-01KWH9EQ
**Point-cut**: post-spec (2026-07-02)
**Squad**: 4 lenses, profile-loaded — planner-priti (sizing), reviewer-renata (fakeability), debugger-debbie (code-truth census), architect-alphonso (structure/scope-boundaries)
**Outcome**: all findings folded into spec.md rev 2 (same day)

## Verdicts

| Lens | Verdict |
|------|---------|
| Sizing (priti) | UNDERSIZED-BY-~1.5× on WP-count/decomposition completeness (not the 4-5× effort mode); WP estimate 8–10 vs the debrief's 5 |
| Fakeability (renata) | DoDs-FAKEABLE-IN-6-WAYS (2 critical/major structural) |
| Code-truth (debbie) | CENSUS-HAS-4-ERRORS (2 high, 1 medium, 2 low) |
| Structure (alphonso) | 2-STRUCTURAL-RISKS (1 critical seam-topology, 1 major contract-surface) |

## Convergent findings → spec changes

1. **[CRITICAL] Module-level re-exports do NOT preserve patch interception** (alphonso;
   renata independently as "interception-blind seam DoD"). Relocated code calling infra
   by bare name escapes `@patch("...agent.tasks.<sym>")`; defensively-patched tests go
   green-but-blind. The `mission.py` template's real mechanism is lazy parent-module
   attribute routing (`_mission.<attr>` idiom, 40+ occurrences). → **FR-002 seam bridge
   (default mechanism named), NFR-002 re-worded to interception, Domain Language "seam
   bridge", edge case rewritten.**
2. **[CRITICAL] "Golden-42 byte-identical" was factually wrong twice** (debbie: the
   surface harness is 27 cases; renata: only the 10 `--help` fixtures are byte-exact —
   JSON legs are shape-checked). 43 cases exist across BOTH contract files (27 + 16
   coord). → **Harness redefined as two files/43 cases; NEW byte-freeze suite (FR-005
   pre-step) supplies the missing byte-level contract for the 13 emission sites.**
3. **[MAJOR] Branch-coverage ratchet false-red + gutting invitation** (renata):
   `_BRANCH_COVERAGE_FLOORS` is AST-line-range-coupled to the fat wrappers in tasks.py;
   relocation collapses the range → red; the only sanctioned response must be re-pointing.
   → **NEW FR-012 + NFR-001(e) carve-out.**
4. **[MAJOR] #2300 divergence pin lives in the un-named coord harness** (alphonso):
   T004/T005 + the wrong-leg detector; divergence is caller-wiring
   (`_skip_target_branch_commit` pre-gate on move_task only) around a SHARED helper.
   → **C-001 rewritten with the concrete pin + structural warning; NFR-005 requires the
   coord file in commit-router WPs' targeted sets.**
5. **[MAJOR] LOC ceiling was self-certifying** (renata). → **FR-011: ceiling =
   min(achieved, 1400); >1400 escalates to the operator; rationale must record
   delta-from-4569.**
6. **[MAJOR] SC-005 was gameable** (renata): baseline-widening via
   `_gate_coverage_baseline.json --update-baseline` + undefined "tasks-domain".
   → **FR-009: committed glob + committed census artifact + baseline-growth prohibition;
   C-006 extended to cover it.**
7. **[MAJOR] Missing decomposition inventory** (priti): the fifth family (`_ft_*`,
   finalize), 5 State dataclasses, 5 `_default_*_ports` factories, and ~30 cross-family
   shared helpers (56-call-site `_output_result`/`_output_error`, `_find_mission_slug`
   ×66 patches, `_ensure_target_branch_checked_out` ×50) had no named home.
   → **FR-001 enumerates full per-family move-sets; NEW FR-003 shared-helpers module;
   sizing guidance 8–10 WPs.**
8. **Census corrections** (debbie): 12 compact + 1 indent sites = 13 total (not 13+1);
   ~370 patch call-sites/~40 symbols (not ~900); 57 glue helpers (23/11/14/9 + 4 `_ft_`);
   core-module paths spelled out. → **Re-census section rewritten.**
9. **[MINOR] `__all__` conflation** (alphonso): charter `__all__` MUST binds
   `src/charter/`+`src/kernel/` only; template siblings declare none. → **FR-008 notes
   the precedent; `__all__` no longer implied as the seam mechanism.**
10. **[MINOR] AST-gate evasion forms + scope** (renata): alias/rebind forms +
    move-next-door. → **FR-007: directory-glob scope + per-form self-mutation proofs.**
11. **[MINOR] `_StatusRender` relocate-then-delete ordering** (priti). → **Edge case +
    FR-004 conditional + sequencing note in Assumptions.**

## Divergences adjudicated

- **Patch-seam count**: priti measured 296 decorators +37 setattr; debbie 367; alphonso
  368/~40 symbols. Adjudicated to "~370 call sites across ~40 distinct symbols"
  (grep-form differences; the honest planning unit is the 40-symbol inventory).
- **Harness case count**: debbie's 27 (surface file only) vs the debrief's 42 —
  orchestrator re-ran collection over both files: 43 combined. Both sub-claims correct;
  the spec now names both files.

## Concessions recorded (where the spec was already sound)

- Boyscout scope honestly small (39/39 tasks-domain test files carry pytestmark; ~1
  residual invisible file).
- Render-seam stream sized to the real site count.
- Adapters-module default placement sound; `agent_tasks_ports.py` top-level placement is
  deliberate (docstring rationale) — added to Non-Goals.
- No template-sync FRs missing (agent dirs call the CLI; they don't reference tasks.py
  internals).
- Per-move risk genuinely low; this is a decomposition-completeness undersize, not the
  4–5× effort mode.

---

# Pre-plan related-issues squad — findings record (2026-07-02)

**Point-cut**: pre-plan (after spec rev 2, before /spec-kitty.plan)
**Squad**: 3 lenses — planner-priti (tracker sweep), debugger-debbie (campsite-fold), paula-patterns (parallel-work collision)

## Verdicts

| Lens | Verdict |
|------|---------|
| Tracker sweep | 5 new REFERENCE issues, 0 folds, 3 IGNOREs; unshim boundary confirmed safe (tasks_ports.py not on #2289's list) |
| Campsite fold | CAMPSITE-DIRTY: 1 fold (#2306, filed) + 2 inline NFR-003 folds; 0 freezes; all #1931/#2071 children out-of-domain |
| Parallel work | 3-LATENT-COLLISION-RISKS, 0 ACTIVE — fenced by comments on #2300/#2289 |

## Actions taken

- **#2306 filed** (C-007): test_untrusted_path_containment RED on main — inventory.md 1325→1326 off-by-one from the Wave 1 merge; folded into the move_task-family WP.
- **Fence comments posted**: #2300 (do-not-start warning naming C-001/T004/T005), #2289 (tasks_ports.py ownership).
- **Issue-matrix extended**: +#2306 (in-mission), +#2031/#2283/#2295 (references).
- **Spec**: new "Campsite Folds" section records the 3 folds + the parallel-work state (DIRECTIVE_003 — not to be re-investigated at plan time).

## Plan-time carry-forwards (from the sweep)

- **FR-011 LOC gate**: author with `composite_key` (not `file:line`) per CT1 #2072 — avoid arriving as ratchet debt.
- **FR-005 byte-freeze suite**: byte-equality assertions, never `len()==N` golden counts (CT5 #2076 anti-pattern).
- **#2031**: expect stale-assertion-analyzer false-positive storms at every WP merge; cross-check against seam checklists, don't act on raw analyzer output.
- **#2283**: FR-010's final census comment should name it as the 3-cause structural parent and state Wave 2 closes cause (a) for its domain only; #2296/#2297 are the blocked/structural repo-wide paths.
- **#2056**: template source (mission.py degod) is itself partially in-flight — confirm the `_mission.<attr>` seam-bridge idiom is still canonical before WP1.
- **Campsite verification correction**: debbie found ALL 34 tasks-domain test files currently gate-visible (the spec's "~1 invisible file" [unit, git_repo] IS selected via the git_repo gate) — FR-009's obligation is maintain-and-evidence, not fix.
- Marker-gate arch gates from Wave 1's tracer are now GREEN except test_untrusted_path_containment (#2306).

---

# Post-tasks anti-laziness squad — findings record (2026-07-02)

**Point-cut**: post-tasks (WPs finalized, before implement)
**Squad**: 3 lenses — reviewer-renata (fakeable DoDs, opus), python-pedro (claims-vs-code, sonnet), paula-patterns (decomposition feasibility, opus)

## Verdicts

| Lens | Verdict |
|------|---------|
| Fakeability | 6-FAKEABLE-GAPS (1 critical, 2 high-class, 3 medium/low) |
| Claims-vs-code | 2-ANCHOR-ERRORS (1 high, 1 low) — all line/count anchors otherwise exact |
| Feasibility | EXECUTABLE-AS-DECOMPOSED with 5 risks (1 high); ordering + linearization independently ENDORSED |

## Convergent CRITICAL (renata + paula, independent): ratchet re-point vacuous-green trap

`_branch_coverage_by_function` returns 100.0 when `total==0`; the session is
single-file (`include=[tasks.py]`). A naive FR-012 re-point measures nothing and passes
every floor. → **WP05 T024 rewritten as a coverage-plumbing rewrite** ({name: (module,
qualname)} map + multi-file include + vacuous-fallback → hard fail); WP06 T029/WP07 T033
add-module semantics; acceptance evidence = demonstrated RED fire, never a recorded
percentage; parity-contract Layer 3 rev 2 (incl. the diff-scope rule for the coord file).

## Other folds applied

1. **LOC mission-cap backstop** (renata HIGH): WP09 T042 now lands `assert _CEILING <= 1400`
   as a standing gate line; escalation mechanism made concrete (move-task to blocked +
   #2305 comment). gate-contracts.md updated.
2. **WP02 stale move-set** (pedro HIGH): `_get_latest_review_cycle_verdict` +
   `_self_review_fallback_option_error` already live in `tasks_parsing_validation.py`
   (Wave 1) — move-set is ~28; WP02/research(D7a)/data-model corrected; mypy fold
   re-scoped to a re-export/import re-point.
3. **WP04 T019 vacuous branch** (paula MEDIUM): none of the 9 sites has `ports` in reach;
   all 6 glue sites + 3 small bodies use the local `RealRender()` default-param seam;
   State-threading explicitly forbidden (protects WP06/WP08 verbatim moves).
4. **Seam checklist formalized** (renata MEDIUM): one committed
   `seam-checklist.md` (fixed columns), WP02 creates, family WPs append; binding leg
   proven by parametrized is-identity tests over the FULL move-set (no spot-checks).
5. **Label collision** (renata MEDIUM): coord-harness case labels T004/T005 disambiguated
   from mission subtask IDs everywhere (tasks.md, WP05/06/08, parity-contract).
6. **Acceptance matrix populated** (renata MEDIUM): all 12 criteria now carry concrete
   descriptions + planned evidence (test ids/artifacts); pass_fail stays pending.
7. **WP08 split-note** (paula MEDIUM): inoperable escape hatch deleted; bundling owned
   explicitly (T035 fully before T036, per-family commits).
8. **mission_finalize idiom count** 10→13 (pedro LOW).

## Accepted-risk decisions

- **lanes.json write_scope** omits the serial shared surfaces (tasks.py + gate file) for
  lanes b–h (paula LOW-MEDIUM): NOT hand-edited — lanes.json is generated; the linear
  chain means no concurrent writer; each WP prompt carries the Shared-surface note. If
  the implement-loop ownership guard blocks, handle per the guard-friction protocol
  (minimal documented override) rather than pre-editing a generated artifact.
- **Coord harness not in WP05-07 owned_files** (renata LOW): covered by the diff-scope
  rule in parity-contract Layer 3 + per-WP Review Guidance instead (adding it to three
  WPs' owned_files would create cross-WP overlap).

## Squad concessions (decomposition confirmed sound)

- Route-then-move ordering independently endorsed (paula traced all 12 sites; zero rework).
- Linearization justified (true contention on tasks.py + gate file; no parallelism left
  on the table; no dependency deadlock — `approved` satisfies the gate).
- WP01 deliverables complete for every later WP's validation (renata verified).
- T001–T046 map 1:1 across index/checkboxes/frontmatter/prompts (46/46).
- WP02 sized honestly (~750–900 LOC module); kept whole to preserve the pattern-
  establishment; flagged as the critical-path link (interception tests BEFORE the cut).
