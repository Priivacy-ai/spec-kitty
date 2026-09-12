---
work_package_id: WP03
title: 'Baseline-file toll drains: derive count / skip-marker warn / inert-key / fast markers'
dependencies: []
requirement_refs:
- FR-003
- FR-004
- FR-005
- FR-006
- NFR-002
- NFR-003
planning_base_branch: fix/frozen-baseline-toll-reduction
merge_target_branch: fix/frozen-baseline-toll-reduction
branch_strategy: Planning artifacts for this mission were generated on fix/frozen-baseline-toll-reduction. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/frozen-baseline-toll-reduction unless the human explicitly redirects the landing branch.
subtasks:
- T012
- T013
- T014
- T015
- T016
- T017
- T018
- T019
- T020
history:
- at: '2026-08-18T12:40:00+00:00'
  actor: claude
  note: WP created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_ratchet_baselines.py
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/test_ratchet_baselines.py
- tests/architectural/_baselines.yaml
- tests/architectural/test_ratchet_positional_anchor_ban.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile: `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`). ATDD; mypy `--strict` + zero new suppressions; complexity ≤ 15.

## Objective

Drain the four genuine-toll behaviors in the baseline gates without weakening any **load-bearing** sibling: derive the redundant migration count (FR-004), make skip-marker growth reviewable-not-blocking (FR-003), fully remove the inert dead-symbol key + its grandfather residue (FR-005), and fast-mark the two sub-second gates (FR-006). Contracts B/C/D in `contracts/gate-behavior-contracts.md` are the verbatim acceptance criteria.

## Context (do-not-touch fence — C-001)

Leave untouched: `legacy_contract_allowlist=151`, `grandfathered_orphans`, `no_inert_schema_slots`, `reference_enum_ratchet`, `egress_consent_boundary`×2, `unfiltered_journal_read_boundary`, `backcompat_shims=0`, `known_ungated_files=0`, `test_artifact_kinds`. Every change below is a carve-out C-001 authorizes; nothing here may loosen a fenced gate.

## Subtasks

### T012 — FR-004 derive count (growth arm)
- In `test_ratchet_baselines.py` growth arm (`~:268-270`), set the `category_1` expected to the frozenset length **read dynamically** — `len(_import_module_attr(nd_module, "_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS"))` (that exact call is already on `:270`; the constant is **not** statically imported, so a bare `len(_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS)` raises `NameError`). **Do NOT** re-implement a `glob ∩ no-static-importer` predicate (no accessor exists → `_has_caller` split-brain) and **do NOT** use `len(glob("m_*.py"))` (105, over-counts by 5). The frozenset (100) is the single authority; its *membership correctness* is validated by the untouched `test_no_dead_modules`.

### T013 — FR-004 derive count (shrink arm) + decorative-YAML honesty
- Apply the same derivation in the shrinkage-warns arm (`:405`) — both arms or a stale arm survives. Keep the `_baselines.yaml` `category_1` sub-key present but assert `data[...]["category_1"] == len(_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS)` so the now-decorative integer can't silently drift.

### T014 — FR-004 derivation test (non-vacuous)
- A test that **monkeypatches** `_CATEGORY_1_AUTO_DISCOVERED_MIGRATIONS` to size N and asserts the **production arm's pass/fail verdict** responds to N with **no `_baselines.yaml` edit** — drive the real comparison at `:270`/`:405` and assert the growth/shrink verdict flips, **not** two inline `len()`s equated to each other (`len(x)==len(x)` is the tautology to avoid). Include the US3-AC2 shrink case (a migration gains an importer → frozenset shrinks → derived count drops, no manual edit).

### T015 — FR-003 skip-marker reviewable-not-blocking
- Remove `_SKIP_MARKED_BLOCKS` from **both** `single_baselines` lists (growth `:307` **and** shrinkage-warns `:441`). Add a dedicated `fast`-tier test that treats `skip_marker_blocks` as a shrink-tracked high-water mark and **does not `pytest.fail` on growth**, routing growth through `record_property`.
- **`record_property` is write-only in this repo** (`grep -rln user_properties tests/` is empty). So the test MUST **assert the growth property fires** (inspect `request.node.user_properties`) — a `record_property` call nobody asserts is an unverified backstop.
- Teeth accounting: the review-forcing signal is the mandatory co-located `# round-trip: skip: <reason>` diff line (enforced by the *unmodified* `_SKIP_MARKER_RE`); do **not** write a test that merely asserts the regex exists and call that this WP's teeth.

### T016 — FR-003 NFR-003 guard
- Assert `legacy_contract_allowlist=151` remains a **growth-fail** in `single_baselines` (surgical extraction did not loosen the C-001 sibling).

### T017 — FR-005 remove inert key + drain grandfather residue
- Delete the inert `test_no_dead_symbols:` block from `_baselines.yaml` (no comparison reads it). Drain `_GRANDFATHERED_UNREGISTERED_KEYS` (`:141-142`) to `frozenset()` **and** update the coupled equality literal at `:530` (`test_no_unregistered_baseline_keys_are_added` asserts `frozenset({...}) == _GRANDFATHERED_UNREGISTERED_KEYS`) in lockstep — else that test REDs. Retire the now-stale RL-030 comment/docstring (`:133-143`, `:516-524`). **Validation**: gate green; re-adding a `test_no_dead_symbols:` key is now **rejected**.

### T018 — FR-006 fast markers
- Add `fast` to the module `pytestmark` of both `test_ratchet_baselines.py` and `test_ratchet_positional_anchor_ban.py`.

### T019 — FR-006 CI-routing + import hygiene
- **Verify the `arch-adversarial` job's `-m` selector does not exclude `fast`** (`fast` is a routed-by-marker marker; dual-marking could silently drop these two gates from the arch job — check against `test_marker_job_completeness.py` selection expressions). If the selector would drop them, STOP and flag (do not land a silent coverage loss).
- Add a `-m fast` **collection** import-hygiene test: `-m fast` collection must not import the `test_example_round_trip` corpus module (holds today only because `_import_module_attr` defers it).

### T020 — Quality + load-bearing sweep
- ruff + mypy `--strict` clean; complexity ≤ 15. Run the full load-bearing-gate sweep: `test_ratchet_baselines`, `test_no_dead_modules`, `test_ratchet_positional_anchor_ban` green; confirm no C-001 baseline weakened (NFR-003 / SC-004).

## Branch Strategy

Base/merge target `fix/frozen-baseline-toll-reduction`; worktree per computed lane (`lanes.json`). Implement via `spec-kitty agent action implement WP03 --agent claude`. Lane 2, no cross-lane dependency; runs in parallel with Lane 1.

## Definition of Done

- FR-004 count derived in **both** arms (frozenset authority, dynamic `_import_module_attr` read); non-vacuous derivation test green (arm verdict flips with N); the decorative `_baselines.yaml` `category_1` is asserted `== len(frozenset)` so it can't silently drift.
- FR-003 skip growth no longer hard-fails; the `record_property` growth record is **asserted**; `legacy_contract_allowlist=151` still a growth-fail.
- FR-005 inert key + grandfather residue + coupled literal all removed; re-entry rejected; stale RL-030 prose retired.
- FR-006 both gates `fast`-marked and selected under `-m fast`; `test_no_dead_symbols` not selected; arch-job selector verified; import-hygiene test green.
- ruff + mypy `--strict` clean; all load-bearing gates green (zero weakening).

## Risks & Reviewer Guidance

- **Two-arm trap**: FR-004 (`:269`+`:405`) and FR-003 (`:307`+`:441`) each touch two loop arms — reviewer confirm both edited.
- **NFR-003**: FR-003/FR-005 edit near `legacy_contract_allowlist=151` / `_GRANDFATHERED_UNREGISTERED_KEYS` — confirm the C-001 sibling stays a growth-fail (T016) and the `:530` literal moved in lockstep with the constant.
- **FR-006 blast radius**: the marker edit is a one-liner but the CI-routing check (T019) is the real work — do not treat FR-006 as trivial.
