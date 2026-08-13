---
schema_version: 1
artifact_type: spec-kitty.analysis-report
command: /spec-kitty.analyze
mission_slug: mission-type-guard-registry-01KZY2FG
mission_id: 01KZY2FGYX2B90XXDD1DM3M95B
generated_at: '2026-08-13T23:49:55.572543+00:00'
analyzer_agent: claude-analyze-phase
input_artifacts:
  spec.md:
    path: /home/jeroennouws/dev/SK-missions/3386/kitty-specs/mission-type-guard-registry-01KZY2FG/spec.md
    sha256: a87da21fa264429e25886097b74f0b0d65755728f51d95bbfca2779cdf370051
  plan.md:
    path: /home/jeroennouws/dev/SK-missions/3386/kitty-specs/mission-type-guard-registry-01KZY2FG/plan.md
    sha256: 92e3bdd646e210f004499d2271902c958593067cc52f0df7ea06a86bd1b60d85
  tasks.md:
    path: /home/jeroennouws/dev/SK-missions/3386/kitty-specs/mission-type-guard-registry-01KZY2FG/tasks.md
    sha256: a4ccdd70b7aabf89385d13a6064b9357c24e1fa51c7158e57963fa730eb617d9
  charter:
    path: /home/jeroennouws/dev/SK-missions/3386/.kittify/charter/charter.yaml
    sha256: b976bed223460ac3f4339da1c61c686c6ac96cf9baffdd501073b4e721a1442f
verdict: ready
issue_counts:
  medium: 0
  critical: 0
  high: 0
  low: 0
  info: 2
findings: []
---

# Cross-Artifact Analysis: mission-type-guard-registry-01KZY2FG (#3386)

## Scope

First-hand cross-artifact consistency analysis across `spec.md` ↔ `plan.md` ↔
`tasks.md`/WP01/WP02, per the mission's analyze-phase brief. All checks below were
performed by reading the artifacts and the actual checkout on disk (not carried
over from prior phase reviews unverified), including live execution of the
current `evaluate_guards` dispatch to confirm ATDD RED-pin claims empirically.

## Coverage

- 11/11 Functional Requirements (FR-001..FR-011) mapped to a WP in `tasks.md`'s
  Requirement coverage table: WP01 owns FR-001–FR-006, FR-010, FR-011; WP02 owns
  FR-007–FR-009. No orphan FR.
- NFR-001..NFR-004 all mapped (WP01: NFR-001–NFR-003; WP02: NFR-004). No orphan NFR.
- C-001/C-002 mapped to WP01. C-003/C-004/C-005 are explicitly documented as
  mission-scope/process constraints satisfied by tasks.md's own structure, not by
  a WP code change — stated, not silently omitted.
- Verified no WP task touches any of the four Out-of-Scope deferred sites
  (`mission_type_profiles.py:1041`, `:681`, `mission.py:542`,
  `dashboard/handlers/features.py:68`): neither WP01's nor WP02's `owned_files`
  list includes `src/charter/mission_type_profiles.py`, `src/specify_cli/mission.py`,
  or `src/specify_cli/dashboard/handlers/features.py`. Deferred sites appear only
  as named follow-up, never as work.

## Citation accuracy

Verified first-hand against this checkout (not reasoned from prose): every
`file:line` citation checked below resolves exactly as claimed —
`runtime_bridge_cores.py:351-374` (`evaluate_guards` fall-through, confirmed
byte-exact), `:415/:439/:554` (the three existing guard functions),
`:455-456` (`_evaluate_documentation_guards`'s `accept` terminal-step precedent),
`runtime_bridge.py:680-698` (`_check_cli_guards`, hardcoded
`mission_family="software-dev"` confirmed exactly at line 692),
`runtime_bridge_composition.py:427-486` (`_check_composed_action_guard`),
`runtime_bridge.py:878-891` (compat delegate), `runtime_bridge_io.py:708-718`
(`_PRESENCE_FILE_TAGS` 9-tuple, confirmed exactly 9 entries),
`doctor.py:396-444` (`identity` command, confirmed the `run_identity_audit(...)`
call is the literal line 444), `mission_type_profiles.py:1041/:681/:799`,
`mission.py:542` (`_canonical_meta_mission_type` def line), `mission_type_key.py:24`,
`_identity_audit.py`'s `run_identity_audit`/`_build_identity_json`/`_compute_fail_on`,
`identity_audit.py`'s `IdentityState`/`classify_mission`/`audit_repo`/`summarize`,
all NFR-002-named test functions (`test_unknown_mission_type_returns_false`,
`test_should_dispatch_falls_through_for_unknown_mission_helper`,
`test_dispatch_falls_through_for_unknown_mission`,
`test_should_dispatch_via_composition_both_branches_via_charter_lookup`),
`test_identity_audit.py`'s `test_nfr_002_timing_200_missions` precedent, and the
`ci-quality.yml` line citations in plan.md's Gate Set (job def :2144, `if:` :2147,
docs-only detection :2201, run step :2228, the two `-m` marker selections :2241/:2258,
diff-coverage critical-path :2927/:3489/:3516-3517, Contextive glossary :848,
doctrine-schema-freshness :653). All confirmed exact.

**Found and fixed** (info-level, not blocking — resolved in this session's fix
round, see below): tasks.md's "Scope carried forward from plan.md" section cited
the second deferred meta-reader site as `mission.py:551` (the `for field in
(...)` loop line, inside the right function but a less-precise anchor) while
spec.md's Out-of-Scope item 2 cites the same site as `mission.py:542` (the
function's own `def` line). Not a false citation (both resolve inside the
correct function), but an inconsistency between two artifacts describing the
identical deferred site. Fixed: tasks.md now cites `mission.py:542`, matching
spec.md.

## ATDD integrity

Empirically re-ran the exact assertions WP01's T001/T002 describe against the
current checkout (not reasoned from prose):

- `evaluate_guards(plan, review)` → `['Not all work packages are approved or done']`
  (confirms the live defect, RED as claimed).
- `evaluate_guards(plan, research)` absent/present → `[]` / `[]` (confirms the
  documented coincidental-pass for the present case — correctly labeled a
  companion, not RED evidence, per the tasks-phase's own TASKS-VERIFY-001 fix).
- `hasattr(cores, "_evaluate_plan_guards")` → `False`;
  `hasattr(cores, "evaluate_guards_strict")` → `False`;
  `hasattr(cores, "UnregisteredMissionFamilyError")` → `False` (confirms the
  claimed `AttributeError`-RED for T001 step 3 and T002 step 1).
- `evaluate_guards(plan, specify/plan)` absent/present → correct post-fix values
  already via fall-through coincidence (confirms T001 step 3's claim that a
  full-dispatch assertion here would NOT be a genuine RED pin, correctly routed
  to a direct-call assertion on `_evaluate_plan_guards` instead).
- `evaluate_guards(plan, "not-a-real-plan-action")` → `[]` (confirms the
  fail-closed-else full-dispatch RED pin).
- `_check_composed_action_guard("review", ..., mission="totally-unregistered-family")`
  → `['Not all work packages are approved or done']` (confirms T002 step 3's RED
  claim for the composed path).
- No drift since plan.md's baseline capture: `git log --oneline
  7deadff0a4f3dfd2744b5e1e35680c0d70f4565e..HEAD -- src/runtime/next/
  src/specify_cli/cli/commands/doctor.py src/specify_cli/cli/commands/_identity_audit.py
  tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py` returns empty,
  independently re-confirmed.
- WP02's T008 base state confirmed: `_mission_type_audit.py` and
  `test_doctor_mission_type.py` do not exist; no `mission-type` subcommand is
  registered in `doctor.py`; the golden test's `FROZEN_SUBCOMMANDS` currently has
  exactly 19 members (confirmed by direct parse), matching the "19→20" claim.

Every corrected RED-pin claim from the tasks-phase's own review rounds
(TASKS-VERIFY-001/002/003) holds exactly as currently documented. No new ATDD
defect found.

## Silent-success discipline

Confirmed C-001/C-002's asymmetry is coherently specified everywhere it appears
(spec User Story 1/3, plan's Seam & Module Placement, WP01 T005/T006): the
composed path never raises (degrades to `[]` + WARNING log), the legacy path
never silently degrades (raises `UnregisteredMissionFamilyError` uncaught).
`doctor mission-type`'s `error` state (meta.json unreadable) is specified to
classify explicitly, never skip silently or crash the whole audit — consistent
across spec.md FR-008/Edge Cases, plan.md's decision procedure, and WP02 T008/T009.

## Second finding, found and fixed (medium, not blocking after fix)

`lanes.json` (generated by `finalize-tasks`, committed in `15007077c`) was
stale relative to `tasks.md`/WP01's own `owned_files` frontmatter: commit
`037d5e901` (a tasks-phase review fix, TASKS-VERIFY-002) added
`tests/runtime/test_bridge_io.py` to WP01's declared write scope (a disk-backed
revert-discipline test for the `research.md` presence-tag fix) AFTER `lanes.json`
had already been generated, and `finalize-tasks` was never re-run. Lane-a's
`write_scope` in the committed `lanes.json` was missing this file, so the
machine-readable lane manifest under-represented WP01's actual planned write
surface — a real, first-hand-verified drift between a generated planning
artifact and its own source of truth. This is exactly the class of defect this
mission's analyze phase exists to catch on this codebase's own missions.

**Fixed**, via the canonical path per AGENTS.md's own "trace the source, don't
hand-roll" discipline: re-ran `spec-kitty agent mission finalize-tasks --mission
mission-type-guard-registry-01KZY2FG --json`. It hit the already-diagnosed,
pre-existing `PROTECTED_BRANCH_REFUSED` tooling gap (documented first-hand in
this mission's `tracer-tooling-friction.md`, entries 5-7, on a `lanes`-topology
mission with no coordination branch) — but per entry 7's own established
recovery pattern, the generation pass writes files to disk before the terminal
bookkeeping-commit step fails, so `lanes.json` was correctly regenerated with
the missing file present. No hand-editing was used. Independently re-verified
by a separate verifier subagent from a fresh context: `lanes.json`, WP01's
`owned_files` frontmatter, and tasks.md's Write-scope disjointness table now all
agree on the same 7-file set for WP01; lane count, WP-to-lane assignment, and
dependency structure are unchanged; no other file was modified.

## Verdict rationale

Both findings surfaced by this analysis were fixed by a fresh fixer subagent and
independently confirmed by a fresh verifier subagent (author/fixer/verifier
separation maintained throughout, per this mission's own binding discipline).
No remaining open findings. `findings: []` in this carrier reflects that; the
`counts.info: 2` bucket records, for the trail, that two issues were found and
resolved during this analyze pass (see above) — it is presentation-only and does
not participate in verdict computation. Verdict: **ready**.
