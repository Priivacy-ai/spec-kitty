---
work_package_id: WP04
title: Full regression/NFR sweep + NFR-002 documentation deliverable
dependencies:
- WP03
requirement_refs:
- NFR-001
- NFR-002
- NFR-004
- FR-009
- FR-011
- FR-012
planning_base_branch: fix/custom-mission-guard-3704
merge_target_branch: fix/custom-mission-guard-3704
branch_strategy: Planning artifacts for this mission were generated on fix/custom-mission-guard-3704. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/custom-mission-guard-3704 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-custom-mission-guard-failure-blocking-inert-01M0STY0
base_commit: 8685dec23a28ee51026cfcebbf2ecea17ad619ed
created_at: '2026-08-24T18:42:17.848736+00:00'
subtasks:
- T023
- T024
- T025
- T026
- T027
- T028
- T029
phase: Phase 4 - Full regression/NFR sweep + NFR-002 documentation deliverable
history:
- timestamp: '2026-08-24T15:45:00Z'
  agent: tasks-author
  action: Prompt authored directly during tasks-phase authoring (spec-kitty agent tasks tasks-outline/tasks-packages do not exist as CLI subcommands in this checkout's v3.2.6rc3 build; authored per tasks.md decomposition of plan.md's WP04, which owns NFR-002's documentation deliverable per PLAN-ARCH-001, reviews/plan.confirmed.yaml).
authoritative_surface: tests/specify_cli/next/
create_intent: []
execution_mode: code_change
owned_files:
- CHANGELOG.md
- tests/specify_cli/next/test_runtime_bridge_composition.py
tags: []
tracker_refs: []
---

# Work Package Prompt: WP04 – Full regression/NFR sweep + NFR-002 documentation deliverable

## Mission context

Issue #3704, closing WP. This mission is STACKED on `fix/org-tier-expected-artifacts-3703` (PR
#3708) — red-verify against that branch, never `main`. Full spec: `../spec.md`. Full plan:
`../plan.md`. This WP implements plan.md's WP04 exactly as scoped there, and is the sole owner of
NFR-002's mandatory documentation deliverable (PLAN-ARCH-001, `../reviews/plan.confirmed.yaml` —
this finding was raised and fixed at the plan phase precisely because no WP originally owned this
obligation; do not let it go unowned again here).

## Goal

Confirm, at the mission's final commit, that:
- The 4 built-in families (`research`, `documentation`, `software-dev`, `plan`) produce
  byte-identical `guard_failures` output before and after this mission (NFR-001/AC-7) — the FR-001
  fallback only activates when `_GUARD_TABLES.get(family)` is `None`, structurally unreachable for
  any of the four (FR-009).
- AC-3/AC-9's three-outcome distinguishability holds end to end: a genuinely unregistered/typeless
  family still raises `UnregisteredMissionFamilyError` / degrades to `[]` (C-001), unchanged.
- `test_coverage_floor_is_met`'s `_GUARD_BRANCH_FLOOR` (18) stays met (NFR-004).
- The frozen-template e2e walk for an unregistered custom mission type still runs to completion
  (`TestCustomMissionComposition`, C-001).
- AC-10 (a custom mission family gates on its own filenames as long as it ships an
  `expected-artifacts.yaml`, at the conventional `<org_root>/missions/<type>/` layout) is
  demonstrable end to end — this is only reachable now that this branch is stacked on #3708's path
  fix (the operator's own stacking rationale, spec.md Clarifications).
- NFR-002's operator-visible-behavior-change documentation lands as a real deliverable, not
  narrative: `Decision.guard_failures` is already part of `spec-kitty next --json`'s serialized
  stdout contract (`src/specify_cli/cli/commands/next_cmd.py:899-905` under `--json`,
  `next_cmd.py:1056-1057` human-readable path) — this mission changes that field's *content* for
  any custom mission family with a declared manifest (a family that previously always emitted
  `guard_failures == []` can now emit real failure strings and a `blocked` `Decision.kind`, at the
  family's *next* evaluation after deploy — past `status.events.jsonl` entries and `Decision`s are
  never rewritten, per NFR-002's Reflexivity clause). A downstream consumer treating
  `guard_failures == []` as "this custom family always passes" will start seeing real blocks after
  this mission ships. NFR-002 requires this be documented, "not silently absorbed."

## Independent Test

Run the full named regression suite below against this WP's final commit; every listed test
file/class is green. The CHANGELOG.md entry and/or `../tracer-design-decisions.md` note exists
and states plainly the behavior-change fact above, in operator-facing language (not just an
internal field-name description).

## Requirement Refs

NFR-001, NFR-002, NFR-004 (final confirm), FR-009, FR-011, FR-012, AC-3, AC-7, AC-9, AC-10, C-001

## Subtasks

**T023** Run the full NFR-001 byte-compat suite:
`tests/specify_cli/runtime/test_configured_artifact_name.py` and the `TestAC14SoftwareDevUnchanged`
class in `tests/runtime/next/test_cli_guard_family.py`. Confirm byte-identical `guard_failures`
for `research`/`documentation`/`software-dev`/`plan` at every existing fixture, before and after
this mission's changes (FR-009/NFR-001/AC-7). This WP does not add new assertions to these files
unless a genuine gap is found while confirming — if so, note the gap and add the minimal
assertion needed, do not restructure the existing suite.

**T024** Run AC-3/AC-9 confirmation: `TestTypelessMissionFamily` and
`TestIssue3627WpIterationUnregisteredFamilyDegrades` in `tests/runtime/next/test_cli_guard_family.py`
stay GREEN — a family with no manifest declared at any tier continues to run to completion via the
frozen template's `agent_profile`/`contract_ref` binding, `evaluate_guards_strict` keeps raising
`UnregisteredMissionFamilyError`, every existing tolerant caller keeps degrading to `[]` (C-001,
unchanged).

**T025** Run `tests/runtime/test_bridge_parity.py::test_coverage_floor_is_met` — confirm the
guard-branch floor (`_GUARD_BRANCH_FLOOR = 18`, `test_bridge_parity.py:1196`) stays met after
WP01-WP03's changes land (NFR-004).

**T026** Run `tests/specify_cli/next/test_runtime_bridge_composition.py::TestCustomMissionComposition`
— confirm the frozen-template e2e walk for an unregistered custom mission type still runs to
completion with no hard block introduced (C-001).

**T027** AC-10 end-to-end demonstration: stand up a custom family (e.g. `qa`, matching the issue's
own running example) with `<org_root>/missions/qa/expected-artifacts.yaml` at the conventional
layout (reachable now that this branch is stacked on #3708's path fix — this could not be
demonstrated at this layout before this mission stacked on that PR). Walk a real `next` decision
sequence showing the family gates on its own declared filenames: absent blocking artifact → step
blocks; artifact created → step advances. Record this walk (command transcript or an integration
test exercising the same path) as this WP's Independent-Test evidence — this is the concrete,
end-to-end proof that AC-10's pre-existing docstring claim (from
`rc3-charter-gate-predicate-inversion-01M0GGT1`) finally has a real consumer, per spec.md's own
framing of this mission's purpose.

**T028** NFR-002 documentation deliverable (required, not optional): add a CHANGELOG.md entry
and/or an operator-facing note in `../tracer-design-decisions.md` stating, in plain
operator-facing language: *"`spec-kitty next --json`'s `guard_failures`/`Decision.kind` output for
a custom mission family with a declared `expected-artifacts.yaml` manifest now reflects genuine
evaluation. Previously such a family's guard evaluation always returned `guard_failures == []`
regardless of what artifacts existed on disk (a silent-pass defect, #3704). After this mission, a
custom mission previously advancing silently past a step with an unmet `blocking: true`
requirement may, on its next evaluation, correctly BLOCK where it previously would not — this is
the intended fix. In-flight missions are not retroactively re-evaluated: past `status.events.jsonl`
entries and `Decision`s are never rewritten; only the mission's next evaluation after deploy uses
the corrected logic."* Cite the charter's Code Review Checklist requirement ("Breaking changes
documented in CHANGELOG.md") as the mechanism satisfied.

**T029** Run the full shared regression command block one final time against this WP's final
commit — every file in the 5-file blast radius, confirmed green end to end:

```bash
uv run pytest tests/runtime/test_bridge_cores.py tests/runtime/test_bridge_parity.py -v
uv run pytest tests/architectural/test_bridge_cores_import_boundary.py -v
uv run pytest tests/architectural/test_no_dead_symbols.py -v
uv run pytest tests/runtime/next/test_pertype_presence_gate.py tests/runtime/next/test_cli_guard_family.py -v
uv run pytest tests/specify_cli/runtime/test_configured_artifact_name.py -v
uv run pytest tests/specify_cli/next/test_runtime_bridge_composition.py -v
```

## Gates that apply to this WP's files

**ENFORCED**: commitlint; markdown lint (this WP's CHANGELOG.md/tracer-note edit is markdown);
doctrine schema freshness (trivial pass); Contextive glossary (trivial pass — no new domain term);
TID251; `patch()` target validation (N/A unless T027's demonstration adds test code); Bandit;
pip-audit; `uv.lock` freshness; `diff-coverage` 90% floor on `src/runtime/next/*` — this WP is not
expected to add meaningful new lines to those files (T023-T026 run existing suites, T027 may add a
small integration test), but any new/changed line it does introduce there is still covered by the
same enforced gate as WP01-WP03.

**ADVISORY-ONLY**: `ruff`, `mypy` — run `make lint` locally.

**NOT a PR gate on this repo**: SonarCloud Quality Gate.

## Dependencies

- Depends on WP03. (Full regression sweep is only meaningful once dispatch (WP01), org-tier
  presence (WP02), and call-site convergence (WP03) are all in place — this WP verifies the whole
  mission together, it does not add new production behavior of its own beyond T027's
  demonstration.)

## Risks

- NFR-002's documentation deliverable (T028) gets treated as optional polish and dropped under
  time pressure. Mitigated: it is a named, numbered subtask with its own row in
  `../tasks.md`'s Requirements Coverage Summary, not folded into a vague "wrap up" bullet — this
  was PLAN-ARCH-001's exact finding at the plan phase and this WP exists in part to close it.
- AC-10's demonstration (T027) is treated as "nice to have" and skipped because it requires
  standing up an org pack. Mitigated: it is the operator's own explicit rationale for stacking
  this mission on PR #3708 in the first place (spec.md Clarifications) — skipping it would waste
  the reason the stacking decision was made.
