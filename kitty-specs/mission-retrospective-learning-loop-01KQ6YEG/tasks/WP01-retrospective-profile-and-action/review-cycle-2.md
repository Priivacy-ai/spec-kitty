---
affected_files: []
cycle_number: 2
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
reproduction_command:
reviewed_at: '2026-04-27T08:53:43Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP01
---

# WP01 Review — Cycle 1 Feedback

## Verdict: Changes requested

The implementation is mostly solid (graph wiring, action directories, scope edges, deterministic resolution all check out and the new test suite is well-structured), but **deviation #1 is a real defect, not a cosmetic choice**. The profile is unreachable through the runtime's normal profile-lookup path, which violates FR-001.

## Issue 1 (CRITICAL): Profile filename `retrospective-facilitator.yaml` is invisible to `AgentProfileRepository`

**FR-001** requires `profile:retrospective-facilitator` to "resolve through normal profile lookup." The runtime's normal profile-lookup path is `AgentProfileRepository` (used by `ProfileRegistry.resolve()` in `src/specify_cli/invocation/registry.py`, called from `src/specify_cli/invocation/executor.py:156-157` and `router.py:205`). That repository scans `src/doctrine/agent_profiles/shipped/` for `*.agent.yaml` files only (`repository.py:225`: `self._shipped_dir.rglob("*.agent.yaml")`).

**Verification (run from the worktree):**
```python
from pathlib import Path
from doctrine.agent_profiles.repository import AgentProfileRepository
repo = AgentProfileRepository(shipped_dir=Path("src/doctrine/agent_profiles/shipped"))
repo.get("retrospective-facilitator")
# -> AttributeError ('NoneType' object has no attribute 'profile_id')
# i.e. _profiles dict has 11 entries, retrospective-facilitator absent
```

The DRG node lookup works (the new test confirms that), but the runtime adoption path — which is what executes when an action is invoked with `profile_hint="retrospective-facilitator"` — calls `self._registry.resolve(profile_hint)` (executor.py:157), which raises `ProfileNotFoundError` for this profile. So FR-028 (the lifecycle terminus hook) cannot actually invoke this profile at runtime.

**The implementer's stated rationale was that `tests/doctrine/test_shipped_profiles.py` hardcodes a count of 11.** That test is not the contract — FR-001 is. The correct fix is:

1. Rename `src/doctrine/agent_profiles/shipped/retrospective-facilitator.yaml` → `retrospective-facilitator.agent.yaml`.
2. Add `"retrospective-facilitator"` to the `EXPECTED_PROFILE_IDS` set at `tests/doctrine/test_shipped_profiles.py:25-37`. (That test file is not in WP01's `owned_files`, but the deviation already implicitly required modifying neighbouring code; the count-hardening test is part of the doctrine contract and should be updated alongside the new profile. If WP01 wants to keep `owned_files` strict, raise this with the planner — but shipping a profile that fails its own loading contract is not an acceptable workaround.)

I confirmed locally that copying the file as `retrospective-facilitator.agent.yaml` into a temp shipped dir makes `AgentProfileRepository` load it (12 profiles, retrospective-facilitator present). The validator will need to be checked against the schema (the file currently uses `profile-id`/`schema-version` keys with hyphens, while other shipped profiles look the same — so it likely passes; just confirm the validator runs in the count test path).

There is also a secondary concern: the `validation.py` checker at line 77 explicitly comments that valid shipped profiles "have `.agent.yaml` extension." Shipping a `.yaml`-only file therefore violates the documented schema convention as well as the loader contract.

## Issue 2 (acceptable): Action directory layout `retrospect/index.yaml`

This deviation IS correct. `src/doctrine/missions/software-dev/actions/` already uses the `<action>/index.yaml` convention for `implement/`, `plan/`, `review/`, `specify/`, and `tasks/`. The WP prompt's `retrospect.yaml` flat-file suggestion was wrong; the implementer matched the existing convention as instructed by the WP's own Risks section ("Path discovery: actions may live in a shared location, not per-mission. Read existing patterns first; do NOT invent a new convention."). No change required here. Note: the `owned_files` frontmatter lists `retrospect.yaml` rather than `retrospect/index.yaml`; consider updating the frontmatter for documentation accuracy, but this is not a blocker.

## What works (preserved as-is)

- All 26 new tests in `tests/doctrine/test_retrospective_drg.py` pass.
- All 1410 doctrine tests pass — no regression.
- DRG node + edge wiring in `src/doctrine/graph.yaml` is well-organized, commented, and surfaces the FR-003 minimum URN set (directives 003/010/018, requirements-validation-workflow, stopping-conditions, autonomous-operation-protocol, glossary-curation-interview, kitty-glossary-writing, agent_profile node).
- All three mission action `index.yaml` files are byte-identical and reference appropriate directives/tactics.
- Profile YAML body content is well-structured (identity, boundaries, governance scope, mode-defaults, directive references all present per the WP spec).
- `test_resolve_context_is_deterministic` and `test_resolve_context_all_missions_identical_scope` cover FR-004 and the "three actions are equivalent" expectation.

## Required actions before re-review

1. Rename `src/doctrine/agent_profiles/shipped/retrospective-facilitator.yaml` → `retrospective-facilitator.agent.yaml`.
2. Add `"retrospective-facilitator"` to `EXPECTED_PROFILE_IDS` in `tests/doctrine/test_shipped_profiles.py` (and update any other hardcoded "11" mentions, e.g. the docstring on the load-time perf test at line 324).
3. Add a test (in `test_retrospective_drg.py` or alongside it) that proves the profile resolves through `AgentProfileRepository.get("retrospective-facilitator")` — i.e. the runtime path, not just the DRG node. Suggested:
   ```python
   def test_retrospective_facilitator_resolves_through_profile_repository():
       repo = AgentProfileRepository(shipped_dir=SHIPPED_DIR)
       profile = repo.get("retrospective-facilitator")
       assert profile is not None
       assert profile.profile_id == "retrospective-facilitator"
   ```
4. Re-run `pytest tests/doctrine/ -q` and confirm all tests still pass.

The DRG/graph work is already done correctly; this is purely a filename + count-test fix.
