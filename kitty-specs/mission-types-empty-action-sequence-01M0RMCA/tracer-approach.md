# Tracer: Approach

Read `.kittify/charter/charter.md` in full first (governing principles, the nine quality/tech-debt standing orders, the change-scope reconciliation order, the branch/PR/merge rules), then `AGENTS.md` and `CLAUDE.md` at the repo root — no drift found between them for this mission's scope. Fetched issue #3701 verbatim via `gh issue view` (with `GITHUB_TOKEN` unset) rather than trusting the mission brief's paraphrase, and cross-checked its quoted line numbers and code snippets against this checkout's actual `src/doctrine/missions/mission_type_repository.py` (read the file in full: `MissionTypeRepository`, `_inject_projected_fields`, `_load_layered_mission_type_file`, `scan_mission_types_dir`, `resolve_layered_mission_types`) — the issue's line numbers matched closely (small drift, e.g. `_inject_projected_fields`'s hardcoded call sits at line 244-245 here vs. 245 quoted in the issue; immaterial). Also read `src/charter/mission_type_profiles.py` around `_resolve_action_slot`/`MissionTypeEmptyActionSequenceError` and `_resolve_template_set_slot`, `src/charter/pack_manager.py` around line 865, and `src/charter/pack_context.py`'s `PackContext` shape, to ground the Functional Requirements' call-site claims in real code rather than the issue's snapshot.

Confirmed the two binding decision records (Decision 1: thread `PackContext`, not migrate to consumption-boundary sourcing; Decision 2: activation-gate fix is #3702's scope, not this mission's) against the evidence cited in the mission brief, re-verifying each specific claim in the current checkout (the eight `.action_sequence` call sites via targeted greps, the `template_set` retirement docstring, SK-81 and SK-82 in `SPEC-KITTY-LEDGER.md`) rather than copying the brief's assertions uncritically, then wrote both into `spec.md`'s `## Clarifications` section with their evidence so a later `sk-review` pass can audit them independently. Read `tests/doctrine/missions/test_mission_type_repository.py`'s existing test-class layout and `tests/runtime/test_runtime_seam.py`'s `TestGoldenParityUnaffectedByPackContextThreading` (the WP04 precedent for threading a real `PackContext` through this exact family of functions and asserting built-in byte-parity) to ground the spec's NFR-001/NFR-002 and User Story 1's acceptance scenarios in the repo's own existing test idioms, not an invented pattern.

## Plan phase (2026-08-24)

Re-verified every line number and code citation spec.md makes against the live checkout rather than trusting spec.md's own numbers (spec.md itself flags "some drift is expected"): all matched exactly (`_inject_projected_fields` at line 209, its hardcoded call at line 245, `_load_layered_mission_type_file` at line 313, `scan_mission_types_dir` at line 359, `resolve_layered_mission_types` at line 410 with `pack_context: _PackContextLike | None` already at line 412, `MissionTypeRepository._load()`'s untouched call site at line 165, `pack_manager.py:865`'s `scan_mission_types_dir(scan_dir)` call, `mission_step_repository.py:41`'s `_PackContextLike` Protocol, `mission_type_profiles.py`'s `MissionTypeEmptyActionSequenceError` at line 259 and `_resolve_action_slot` at line 916). No drift found on this specific check — spec.md's own citations are accurate against this HEAD. This "no drift found" is scoped narrowly to that one check (spec.md's pre-existing citations against the live file); it is **not** a claim that this plan-authoring pass's own subsequent writing was itself error-free — see the fix-round entry below, where a caller-count claim this pass wrote independently (not one of spec.md's citations) was found wrong and corrected.

**Fix round (2026-08-24, commit `862a0508d`), correcting PLAN-ARCH-001 (round-1 plan-phase adversarial squad finding, confirmed, severity 4):** this plan-authoring pass's own first draft of the "Blast radius on downstream workspaces" section cited `mission_type_repository.py`'s `__all__`-adjacent module comment (the "WP03... until a real `src/` caller existed" comment, lines 23-32) as the basis for a claim that `resolve_layered_mission_types` has "exactly one production caller" (`_resolve_action_slot`). That comment predates later additions to the codebase and was trusted uncritically instead of independently grepped — exactly the failure mode this mission's own "verify rather than trust" standard exists to catch. The round-1 adversarial squad caught it (PLAN-ARCH-001, confirmed severity 4); the correction re-ran `grep -rn "resolve_layered_mission_types(" src/` (including through the `charter.missions` re-export alias) and found **three** production `src/` callers, not one: `_resolve_action_slot` (`charter/mission_type_profiles.py:976`), `resolve_layered_roster` (`specify_cli/cli/commands/charter/mission_type.py:87`), and `_resolve_layered_roster` (`specify_cli/cli/commands/_mission_type_audit.py:170`). `plan.md`'s "Blast radius on downstream workspaces" section now states the corrected count and the verifying grep command directly; this entry records that the audit trail matches what `plan.md` itself now says happened, per this mission's own honesty requirement for tracer files.

Traced the exact fix shape by reading `resolve_layered_mission_types`'s body line by line: it already receives `pack_context` as a required parameter (pre-existing, not something this mission adds), but its three internal `scan_mission_types_dir(...)` calls (built-in-equivalent layer, org layer, project layer) never forward it — that omission, not a missing top-level parameter, is the actual root cause once you trace one level deeper than the issue's own framing. This matters for tasks-phase decomposition: the fix is "add a parameter to three functions AND fix three call-site omissions inside a fourth (already-parameterized) function's body," not simply "add a parameter to four functions."

Verified the CI gate set directly against `.github/workflows/ci-quality.yml` and its reusable sub-workflows (`module-kernel.yml`, `module-doctrine-fast.yml`) rather than accepting the mission brief's framing at face value. Found and corrected one imprecision: the brief's "mission-loader coverage floor is a REAL gate here" claim conflates the literally-named `mission-loader-coverage` CI job (scoped to `src/specify_cli/mission_loader`, unrelated to this mission) with the actually-applicable gate, `diff-coverage (critical-path, enforced)` (`ci-quality.yml:3280-3383`), whose `--include` list contains `src/doctrine/*` and therefore genuinely binds this mission's changed lines to a 90% floor. Also verified `.markdownlint-cli2.jsonc`'s `ignores` array includes `kitty-specs/**` directly (so the markdown-lint gate is provably inert for this mission's diff, not just "probably fine"), and verified the `sonarcloud` job's own `if:` condition (`ci-quality.yml:3502`) has no `pull_request` branch, confirming the memory note that Sonar does not run on PRs here. All three corrections/confirmations are recorded in `plan.md`'s "The gate set" section with their exact line-number citations.

## WP01 implementation phase (2026-08-24) — T001 baseline capture

Per WP01's T001, before touching any production code (and before writing any new test),
ran exactly the WP's mandated baseline command against the unmodified base commit
(`a2527c314`, HEAD at WP01 start):

```
$ .venv/bin/python -m pytest tests/doctrine/missions/test_mission_type_repository.py tests/runtime/test_runtime_seam.py -q -p no:cacheprovider
......................................................................   [100%]
70 passed in 0.72s
```

Zero red, zero errors. This matches the orchestrator's own preflight run recorded in the WP
prompt verbatim (`70 passed in 34.13s` there vs. `70 passed in 0.72s` here — timing differs by
run environment/warm cache, counts and outcome are identical). No red test ids to cross-check
against `gh issue view 3284` — both target files are 100% green at this baseline, so the
~23 known-red/2-error baseline on `main` (issue #3284) is confirmed elsewhere in the suite, not
in these two files, and T001's cross-check step is a no-op by construction (nothing red to
triage). Proceeding to T002 (red-first test) on this confirmed-clean baseline.

## WP01 implementation phase (2026-08-24) — T005/T006

**T005**: Added `test_project_tier_steps_only_projection_resolves`
(`tests/doctrine/missions/test_mission_type_repository.py`), verifying the project-tier path
conventions live against `mission_step_repository.py`'s own source before writing the fixture
(not assumed): project-tier mission-type YAML at
`<repo_root>/.kittify/missions/mission_types/<id>.yaml`
(`_PROJECT_MISSION_TYPES_RELATIVE`), project-tier step tree at
`<repo_root>/.kittify/overrides/mission-steps/<id>/<step>/step.yaml`
(`_project_mission_type_dir`/`_resolve_project_layer`). Manual verification per T005's own
validation step: temporarily reverted ONLY the project-dir call site
(`mission_type_repository.py:574`, `scan_mission_types_dir(project_dir, pack_context=pack_context)`
→ `scan_mission_types_dir(project_dir)`), reran the new test — it FAILED
(`action_sequence` was `None` instead of the expected 7-step list), confirming the test genuinely
exercises the project layer specifically, not vacuously. Restored the line immediately
(`git diff --stat` confirmed zero pending change before continuing); never committed.

**T006**: Confirmed rather than duplicated — `TestLayeredMissionTypesCacheKeyAndClear`'s existing
tests (e.g. `test_same_key_is_a_cache_hit`, `test_two_projects_same_process_return_distinct_correct_results`)
already use `_mission_type_yaml(mission_type_id, action_sequence=[...])` (which always authors an
explicit `action_sequence:` key) with a real `_StubPackContext` and **no** matching step tree
written for that type, so the step-file projection is empty and the explicit YAML value is what's
returned. These tests exercise exactly FR-006/Acceptance Scenario 4's fallback shape and pass
unchanged post-WP01 (confirmed in the T008 full targeted-suite run below), so per WP01's own T006
step 2 ("if an equivalent case already exists ... note that explicitly rather than duplicating a
test"), no new test was added for T006.

## WP01 implementation phase (2026-08-24) — T007 red-first witness (SC-004)

T002's test commit (`ca75f7efd`) and T003's fix commit (`a03a39c7f`) are separate, already
committed. Per WP01's own SC-004 procedure (using `git revert --no-commit`, NOT `git stash`,
because T002/T003 land as separate commits — C-011/plan.md, and `spec.md`/`plan.md`'s own
"stash" wording is superseded by WP01's own executed correction, accepted at analyze finding A2):

**Run 1 — fix reverted (must FAIL):**
```
$ git revert --no-commit a03a39c7f
(clean apply, no conflicts)
$ .venv/bin/python -m pytest tests/doctrine/missions/test_mission_type_repository.py -k "TestLayeredProjectionThreadsPackContext" -v -p no:cacheprovider
tests/doctrine/missions/test_mission_type_repository.py::TestLayeredProjectionThreadsPackContext::test_org_tier_steps_only_projection_resolves_non_empty_sequence FAILED
tests/doctrine/missions/test_mission_type_repository.py::TestLayeredProjectionThreadsPackContext::test_governed_entry_point_does_not_raise_for_steps_only_org_type FAILED
tests/doctrine/missions/test_mission_type_repository.py::TestLayeredProjectionThreadsPackContext::test_project_tier_steps_only_projection_resolves FAILED
3 failed, 42 deselected in 0.44s
```
Observed `action_sequence` values: `None` (both the direct `resolve_layered_mission_types` cases —
org-tier and project-tier), and `MissionTypeEmptyActionSequenceError: mission type 'qa' resolved
from layer 'org' has an empty action sequence.` raised (governed entry point case) — exactly the
pre-fix defect shape.

**Restore:**
```
$ git revert --abort
$ git status --short   # only the tracer file itself (this entry, being written) shows pending
$ git diff --stat src/doctrine/missions/mission_type_repository.py   # empty — fix fully restored
```

**Run 2 — fix restored (must PASS):**
```
$ .venv/bin/python -m pytest tests/doctrine/missions/test_mission_type_repository.py -k "TestLayeredProjectionThreadsPackContext" -v -p no:cacheprovider
tests/doctrine/missions/test_mission_type_repository.py::TestLayeredProjectionThreadsPackContext::test_org_tier_steps_only_projection_resolves_non_empty_sequence PASSED
tests/doctrine/missions/test_mission_type_repository.py::TestLayeredProjectionThreadsPackContext::test_governed_entry_point_does_not_raise_for_steps_only_org_type PASSED
tests/doctrine/missions/test_mission_type_repository.py::TestLayeredProjectionThreadsPackContext::test_project_tier_steps_only_projection_resolves PASSED
3 passed, 42 deselected in 0.69s
```
Observed `action_sequence` value post-fix: `['discovery', 'specify', 'plan', 'tasks', 'implement', 'review', 'accept']` for both direct cases; the governed entry point returns a bundle with the
same list, no exception raised.

Genuinely witnessed fail-then-pass across the same revert/restore cycle, not merely asserted — T007
satisfied. All three tests in `TestLayeredProjectionThreadsPackContext` pin the defect (none is
vacuous under this cycle).

## WP01 implementation phase (2026-08-24) — T008 full targeted-suite run + baseline triage (SC-005)

```
$ .venv/bin/python -m pytest tests/doctrine/missions/test_mission_type_repository.py tests/runtime/test_runtime_seam.py -q -p no:cacheprovider
........................................................................ [ 97%]
..                                                                       [100%]
74 passed in 1.30s
```

74 passed, 0 failed, 0 errors — against T001's baseline of 70 passed, 0 failed, 0 errors. The
delta (+4) is accounted for exactly by this WP's own new tests: T002 added 2
(`test_org_tier_steps_only_projection_resolves_non_empty_sequence`,
`test_governed_entry_point_does_not_raise_for_steps_only_org_type`), T004 added 1
(`test_builtin_layer_scan_receives_the_real_pack_context_once_per_type`), T005 added 1
(`test_project_tier_steps_only_projection_resolves`). No test id present at baseline is red
post-fix — zero mission-introduced red. No test id is red at all in this scoped run, so there is
nothing to cross-check against issue #3284's baseline breakdown here (that breakdown lives
elsewhere in the suite, per T001's own finding).
