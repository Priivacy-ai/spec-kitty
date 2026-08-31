---
work_package_id: WP04
title: Action-path leak closure (off template_set onto meta.json)
dependencies:
- WP03
requirement_refs:
- C-004
- FR-001
- FR-002
- NFR-002
- NFR-003
tracker_refs:
- '883'
planning_base_branch: mission/883-mission-type-governance-profiles
merge_target_branch: mission/883-mission-type-governance-profiles
branch_strategy: Planning artifacts for this mission were generated on mission/883-mission-type-governance-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/883-mission-type-governance-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T019
- T020
- T021
- T022
- T023
- T024
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1734861"
shell_pid_created_at: "1784088287.19"
history:
- at: '2026-07-14T21:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-04, Lane B — parallel to content lane)
agent_profile: python-pedro
authoritative_surface: src/charter/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/charter/context.py
- src/charter/scope_router.py
- tests/charter/test_context.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read: [plan.md](../plan.md) §IC-04 (esp. the
**Campsite OUT → #2532** boundary and the dead-pair anchors), [spec.md](../spec.md) FR-002 / FR-001 /
FR-003a / C-004, [contracts/resolution-and-enforcement.md](../contracts/resolution-and-enforcement.md) C2,
and the ADR "Close the leak by threading the real mission type — with per-entry behaviour".

## Objective

Rewire the **live** action-doctrine path off `template_set` inference onto `meta.json mission_type`
(FR-002/FR-001), so a documentation/research/plan mission stops silently loading software-dev doctrine.
Delete the **dead** `_render_action_scoped`/`_append_action_doctrine_lines` pair (~100 LOC) and its
orphaned test. Split `template_set` (kept for template-file selection only, C-004). RED-first.

## Context

- The live leak is in `_load_action_doctrine_bundle` (`context.py:865`), reached via
  `build_charter_context:252` **and** `build_charter_context_json:3254`. It infers
  `(template_set or "software-dev-default").removesuffix("-default")` — the exact #883 defect.
- The **second** stale default at `context.py:1465` lives **inside the dead pair** to delete — do not
  thread it, delete it. The dead pair is `_render_action_scoped:1500` / `_append_action_doctrine_lines:1451`;
  deleting it orphans `tests/charter/test_context.py:716` (covers dead code) → delete that test too.
- Do **NOT** delete `_filter_references_for_action` — it survives via a live caller at `context.py:1065`.
- **Campsite boundary:** `context.py` is a 3266-LOC god-module with 45 pre-existing suppressions — its
  decompose is **#2532, OUT of scope**. This WP is a ~100-LOC down-payment (the dead-pair deletion) only;
  do NOT grow into the decompose.
- Per-entry behaviour: the prompt path has `feature_dir`; planning-from-root (`context.py:90`) requires an
  explicit `--mission-type`; the genuinely mission-less callers (`executor.py:270`, `workflow.py:675`,
  which already degrades to "Governance: unavailable") get a defined **neutral/degrade** path — never a
  silent software-dev load (FR-003a).

## Subtask guidance

- **T019 — RED-first.** Write a failing behavioural test through a **shared action name** driving a
  non-software mission that today loads software-dev doctrine via `template_set` inference; assert it
  resolves **only** its own type's doctrine (FR-002). This is the leak reproduction — it must go red
  through the pre-existing entry point before any rewire (DIRECTIVE_041).
- **T020 — rewire the live bundle.** Rewire `_load_action_doctrine_bundle:865` to key off
  `meta.json mission_type` (via WP03's resolver / canonicalizer), never
  `template_set or "software-dev-default"`.
- **T021 — thread the type.** Thread `mission_type`/`feature_dir` through `build_charter_context:252` +
  `build_charter_context_json:3254` and `scope_router.py:66`. The ~6 `build_charter_context` callers + ~36
  test files update to the new signature — **update them, do not shield them** with a compat overload
  kept solely to avoid the edit (C-002).
- **T022 — split `template_set` (C-004).** Retain `template_set` for template-file selection; remove it as
  the mission-type proxy in governance routing. Grep-prove no governance path still infers type from
  `template_set`.
- **T023 — delete the dead pair + orphan test.** Delete `_render_action_scoped:1500` /
  `_append_action_doctrine_lines:1451` (incl. the stale `:1465` default inside it) and its orphaned test
  `tests/charter/test_context.py:716` — **also remove the now-unused import line at
  `tests/charter/test_context.py:22`** (deleting the test orphans its import; leave no dead import for ruff
  to red). Confirm `_filter_references_for_action` is **untouched** (live). **Guardrail (explicit):** this
  dead-pair removal is capped at ~100 LOC — `context.py` is 3266 LOC with 45 pre-existing suppressions;
  the god-module decompose is **OUT of scope → #2532**. Add **no new** `# noqa`/`# type: ignore`; do not
  touch the 45 existing suppressions.
- **T024 — per-entry degrade + gates.** Implement the neutral/degrade path for `executor.py:270` and
  `workflow.py:675` (mission-less → never software-dev; FR-003a). Make the RED test green. `ruff` + `mypy`
  clean; complexity ≤ 15 (no new suppressions — the 45 pre-existing ones are #2532's, not yours to touch).

## Branch Strategy

Planning artifacts were generated on `mission/883-mission-type-governance-profiles`. This WP branches from
the mission base during `/spec-kitty.implement` and merges back into
`mission/883-mission-type-governance-profiles`. It depends on WP03 (the resolver seam) and runs parallel
to the content lane (WP06/07/08).

## Definition of Done

- [ ] RED-first test (shared action name) went red pre-rewire, green post-rewire (FR-002).
- [ ] `_load_action_doctrine_bundle` keys off `meta.json mission_type`; **0** `software-dev-default`
      strings remain on any governance path (grep-proven).
- [ ] `build_charter_context` / `_json` / `scope_router` thread the type; callers + ~36 test files updated
      (not compat-shielded).
- [ ] `template_set` retained for template-file selection only (C-004).
- [ ] Dead pair + orphan test `test_context.py:716` deleted; `_filter_references_for_action` untouched.
- [ ] Mission-less callers degrade neutrally (FR-003a), never software-dev.
- [ ] `ruff` + `mypy` clean; **no new** suppressions; did NOT grow into the #2532 decompose.

## Risks

- **~36 test-file signature churn** is real and expected — update them; do not add a compat overload.
- **Growing into #2532** — the god-module decompose is out of scope; keep to the ~100-LOC dead-pair
  down-payment.
- **Deleting the wrong helper** — `_filter_references_for_action` is live (caller `:1065`); only the
  `_render_action_scoped`/`_append_action_doctrine_lines` pair is dead.
- **Blanket hard-error** on mission-less callers breaks dispatch/workflow — degrade per-entry (FR-003a).

## Reviewer guidance (reviewer-renata, opus)

- Confirm the RED test drives a **shared action name** (non-vacuous) and that it truly went red first.
- Grep the diff for surviving `software-dev-default` / `template_set`-as-type-proxy on governance paths (0).
- Confirm the dead pair + `test_context.py:716` are gone and `_filter_references_for_action` stayed.
- Confirm no new `# noqa`/`# type: ignore` and no scope-creep into the context.py decompose (#2532).

## Activity Log

- 2026-07-14T23:47:08Z – claude:sonnet:python-pedro:implementer – shell_pid=1482167 – Assigned agent via action command
- 2026-07-15T00:22:06Z – claude:sonnet:python-pedro:implementer – shell_pid=1482167 – Action-path sw-dev-default leak closed: _load_action_doctrine_bundle keys off meta.json mission_type (via resolve_mission_type_key seam), threaded through build_charter_context/_json/scope_router + new --mission-type CLI option; typeless/mission-less callers degrade neutral (FR-002/FR-003a). Dead pair + 3 orphaned helpers + orphan test deleted; _filter_references_for_action untouched. RED-first leak-repro green. grep-0 software-dev-default on action path; ruff+mypy clean; arch gates + 3575 tests green. NOTE: --force only to bypass rogue-session .kittify churn (PID 348359); all owned deliverables committed in 0eb9e14c7.
- 2026-07-15T04:04:54Z – claude:opus:reviewer-renata:reviewer – shell_pid=1734861 – Started review via action command
- 2026-07-15T04:19:16Z – user – shell_pid=1734861 – APPROVED (--force: bypasses pre-existing lane-branch status-file pollution from WP03-era auto-commit df5f8fb93 + moved-aside WP11 untracked review files; neither owned by WP04). Action-path sw-dev-default leak CLOSED. RED-first PROVEN empirically: reverting keying to the template_set proxy makes test_action_doctrine_keys_off_meta_json_not_template_set FAIL (DIRECTIVE_100 absent; leaks action:software-dev/implement); rewire -> GREEN. Shared action name 'implement' under both software-dev and documentation nodes via real build_charter_context entry point -> non-vacuous. _load_action_doctrine_bundle keys off resolve_mission_type_key(meta.json); grep-0 software-dev-default in context.py; 0 removesuffix('-default') type-proxy in src/; template_set retained ONLY for template-file selection per C-004. Dead pair + 3 orphaned helpers + orphan test + import DELETED (dead-symbol gate green); _filter_references_for_action SURVIVES. Per-entry degrade OK: executor.py:270/workflow.py:675/workflow_executor.py:340 typeless->empty, never sw-dev (FR-003a); prompt_builder threads feature_dir. No new suppressions; no #2532 creep. Gates: ruff 0, charter 1539 passed/1 skipped, arch 44 passed. ACTION_GRAIN JUDGMENT: action_grain=_EMPTY_GRAIN left; leak closed by keying Surface A (context.py DRG) off meta.json directly, not by unioning live action-grain into ResolvedGovernance. ACCEPTABLE slice-1 boundary: WP04 requirement_refs C-004/FR-001/FR-002/NFR-002/NFR-003 all met; FR-013 + action-grain content (IC-05/06) + enforcement join (IC-09) OUT of scope. FR-002 satisfied on BOTH surfaces (Surface A proven by RED test; Surface B _resolve_governance_slot keys off meta.json type_key). LOOSE END (not a blocker): action_grain empty => FR-013 guard never fires against LIVE content; recommend follow-up under IC-09 to union live action-grain into ResolvedGovernance + fix stale WP03 comment 'action grain threaded through the seam by WP04'. Circular-dep rationale imprecise (lazy imports avoid cycles) but layering concern legitimate.
