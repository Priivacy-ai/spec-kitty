# Tasks: Meta.json Fail-Closed Read Routing

**Mission**: meta-json-fail-closed-routing-01KZPJ1F | **Branch**: `feat/meta-json-l1-seam-routing-3259`
**Spec**: [spec.md](./spec.md) | **Plan**: [plan.md](./plan.md) | **Data model**: [data-model.md](./data-model.md)

Closes epic #3259 (children #3228/#3229/#3230/#3240). Live census confirmed post-rebase: routed **134**, floor **130**, margin **4**, inline floor **7**.

## Execution model (read before implementing)

- **WP01 lands first** and is census-neutral (additive kernel + L2/L3 re-express, no deletions).
- **WP02/WP03/WP04** each depend on WP01 and are **census-neutral** — they route onto the new `decode_meta`/`parse_meta_file` names, which are NOT in `ROUTED_CALLEES` until WP05. The routed-census gate stays green at 130/134 throughout.
- **WP05 lands last** and is the ONLY WP that touches the floor: it extends `ROUTED_CALLEES` (making the routing countable), re-pins `ROUTED_LOAD_META_FLOOR = fresh_live − 3`, adds the FR-010 gates, and records the #3240 deviation.
- ATDD red-first per site: author the corrupt-file test, capture it RED against pre-routing code, then route.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | kernel/meta_decode.py: decode_meta + MetaDecodeError(ValueError), explicit utf-8 decode | WP01 | |
| T002 | kernel/vcs_lock.py: VCS_LOCK_META_FIELDS + is_vcs_lock_only_change (absent≠null) | WP01 | [P] |
| T003 | Re-express L2 _parse_meta_text via decode_meta; public parse_meta_file; legacy messages + empty→benign | WP01 | |
| T004 | Re-express L3 load_meta_fail_closed on kernel L1; drop mission_metadata back-edge; preserve MissionMetaReadError | WP01 | |
| T005 | tests/architectural/test_meta_decode_l1.py: pure-decode unit coverage (str+bytes, all arms) | WP01 | [P] |
| T006 | Measure live census before/after WP01; confirm in band + 3 named gates green | WP01 | |
| T007 | Delete ref_advance _parse_meta_object + local field-set + comparator; import kernel symbols | WP02 | |
| T008 | Route sites A + B onto kernel L1; absent-at-HEAD stays benign {} | WP02 | |
| T009 | NFR-004 bespoke-AST ratchet: ref_advance imports 0 specify_cli | WP02 | [P] |
| T010 | Red-first test_ref_advance_meta_diagnosability.py [integration,git_repo]; capture proof-of-red | WP02 | |
| T011 | Retarget test_issue_2795_claim_blocker.py onto kernel L1 + comparator | WP02 | |
| T012 | Confirm ref_advance importable + census-neutral + green | WP02 | |
| T013 | Delete implement_cores _parse_meta_mapping; retire its field-set + _is_vcs_lock_only_meta_diff → kernel | WP03 | |
| T014 | Route sites C (:427 inline) + D (:338 GitPort) onto kernel L1 | WP03 | |
| T015 | Reconcile implement.py:62-70 shim (retire/retarget both re-exports; never dangle) | WP03 | |
| T016 | Retarget binding tests: test_implement_cores, test_implement_vcs_lock_claim, test_specify_topology_flag, test_trio_seam_only, test_exemption_registry_ratchet | WP03 | |
| T017 | Red-first C/D arms in test_meta_bypass_diagnosability.py (unit via GitPort fake, NO git_repo); capture red | WP03 | |
| T018 | Confirm implement_cores/implement importable + census-neutral + trio token-substring intact | WP03 | |
| T019 | Route site E _load_json_object onto parse_meta_file; wrapper empty→{}, catch MetaDecodeError→EventLogMergeError(path) | WP04 | |
| T020 | Red-first E arm in tests/merge/test_merge_driver_meta_diagnosability.py (two error arms); capture red | WP04 | |
| T021 | Confirm _parse_json_document:337 untouched; empty→{} preserved; wrappers_2709 green; census-neutral | WP04 | |
| T022 | Extend ROUTED_CALLEES with decode_meta + parse_meta_file | WP05 | |
| T023 | Measure fresh live census; re-pin ROUTED_LOAD_META_FLOOR = fresh_live − 3 (same commit) | WP05 | |
| T024 | FR-010 enumeration gate (meta-content-scoped, excludes :337 + kernel L1) + completeness check | WP05 | |
| T025 | Record #3240 allow-list governance deviation | WP05 | [P] |
| T026 | Verify 3 named gates + full tests/architectural/ green; SC-001/003/004 | WP05 | |

---

## WP01 — Kernel decode + comparator foundation

- **Goal**: Establish the single fail-closed decode authority + unified comparator in `src/kernel/`; re-express L2/L3 on top. Census-neutral, green alone.
- **Priority**: P1 (foundation — blocks all routing). **Dependencies**: none.
- **Independent test**: `test_meta_decode_l1.py` green; `test_inline_meta_read_gate.py` + `test_meta_fail_closed_full_census_contract.py` green; live census still in band.
- **Subtasks**: T001 T002 T003 T004 T005 T006
- **Prompt**: [tasks/WP01-kernel-decode-comparator-foundation.md](./tasks/WP01-kernel-decode-comparator-foundation.md) (~330 lines)
- **Risks**: L3 re-express may drop census by 1 (still in band) — measure; preserve L2 empty→benign + legacy messages; MetaDecodeError MUST subclass ValueError.

## WP02 — ref_advance routing + comparator unification (atomic)

- **Goal**: Route sites A/B fail-closed; switch ref_advance to the kernel comparator; add the NFR-004 ratchet. One importable unit.
- **Priority**: P1. **Dependencies**: WP01.
- **Independent test**: red-first A/B diagnosability green after routing; NFR-004 ratchet green; census-neutral.
- **Subtasks**: T007 T008 T009 T010 T011 T012
- **Prompt**: [tasks/WP02-ref-advance-routing.md](./tasks/WP02-ref-advance-routing.md) (~320 lines)
- **Risks**: atomic deletion+rewire; absent-at-HEAD stays benign; C-005 flips the present-but-null verdict by design.

## WP03 — implement_cores + implement routing + second comparator retirement (atomic)

- **Goal**: Route sites C/D; retire implement_cores' own comparator+field-set (FR-006/NFR-002); reconcile the shim; retarget ~6 binding tests.
- **Priority**: P1. **Dependencies**: WP01.
- **Independent test**: red-first C/D (unit, no git); retargeted binding tests green; trio token-substring intact; census-neutral.
- **Subtasks**: T013 T014 T015 T016 T017 T018
- **Prompt**: [tasks/WP03-implement-cores-routing.md](./tasks/WP03-implement-cores-routing.md) (~400 lines)
- **Risks**: shim blast radius; keep site C read inline; the second comparator MUST be retired here or WP05's NFR-002 gate reds.

## WP04 — merge_driver routing

- **Goal**: Route site E onto public L2 with a MetaDecodeError→EventLogMergeError wrapper; preserve empty→{}.
- **Priority**: P2. **Dependencies**: WP01.
- **Independent test**: red-first E green; `test_merge_driver_wrappers_2709.py` green; `_parse_json_document:337` untouched; census-neutral.
- **Subtasks**: T019 T020 T021
- **Prompt**: [tasks/WP04-merge-driver-routing.md](./tasks/WP04-merge-driver-routing.md) (~230 lines)
- **Risks**: don't drag the row-matrix decoder into scope; preserve the two error-arm contracts.

## WP05 — Census extension, governance gates, closeout

- **Goal**: The single census change + FR-010 gates + #3240 record + green verification.
- **Priority**: P1 (closeout). **Dependencies**: WP02, WP03, WP04.
- **Independent test**: after `ROUTED_CALLEES` extension + floor re-pin, all 3 named gates + FR-010 gates + full `tests/architectural/` green.
- **Subtasks**: T022 T023 T024 T025 T026
- **Prompt**: [tasks/WP05-census-governance-closeout.md](./tasks/WP05-census-governance-closeout.md) (~300 lines)
- **Risks**: floor measured live after ALL routing, not copied; FR-010 gate scoped to meta content (exclude :337 + kernel L1).
