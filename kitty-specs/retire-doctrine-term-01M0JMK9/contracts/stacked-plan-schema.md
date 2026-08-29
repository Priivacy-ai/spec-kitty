# Contract: M1–M6 Stacked Program

**Produces**: `stacked-plan.md`
**Requirements**: FR-009, FR-010, NFR-003, SC-003, SC-004

## Fixed stack

| Wave | Slug | Exclusive primary responsibility | Invariant |
|---|---|---|---|
| M1 | `charter-authority-flip` | ADR-defined Charter/glossary authority graph, all owning source/interview/synthesis/generated surfaces, explicit override, selection seam, guard arming | I1 |
| M2 | `charter-code-topology` | exhaustive internal+public topology map; merge/relocate old source package into collision-free `src/charter/`; all symbols/imports/tests/build/CLI/serialized/API/workflow/metadata | I2 |
| M3 | `charter-packs-source` | packs/project overlays; verified `.kittify/doctrine/` → `.kittify/charter-packs/` data-preserving migration; no old root after completion | I3 |
| M4 | `charter-agent-assets` | all skills/profiles/directives/prompts/overrides/generated/installed/shared assets and migration; no old installed path after completion | I4 |
| M5 | `charter-current-tree-prose` | all remaining current-tree prose/history/ADR/docs/archive/evidence plus filenames/referrers outside the four immutable historical-record roots (archive referrers recited by `mission_id`/mid8 or token-free path) | I5 |
| M6 | `charter-compatibility-extinction` | every alias/key/path/control/fixture/baseline/allowlist; exact zero content/path audits over `HEAD` with the four fixed exclusion roots | I6 |

## Required wave fields

Every entry includes `slug,purpose,depends_on,inputs,outputs,base_capture,occurrence_map,retires_oc,
introduces_compatibility,removes_compatibility,owned_files_or_surfaces,tests,merge_gate,rollback,
change_mode,invariant_after,local_design_questions`.

- `change_mode` is `bulk_edit` for M1–M6.
- `retires_oc` sets are pairwise disjoint and their union equals all inventory OCs/hits.
- No current-repository hit has an external deferral or X/exempt owner.
- Every CR appears once in one M1–M4 introduction list and once in M6 removal; frozen-base funded source
  OC owner equals introduction wave. Compatibility product/control coordinates created after that base
  are new M6-removal work at their wave-local audit, never duplicate ownership of the source coordinates.
- Each wave captures a fresh current target and exact occurrence map before editing.

## Zero-decision and bounded-design rules

M1 has zero local design questions. Inputs fix the ADR contract's exact per-artifact Charter owner map,
verified no-op behavior, obsolete-graph consumer proof/deletion, glossary authorities, override text,
canonical vocabulary, activation-engine-only activation, lossless answers migration + serializer
hardening, selection key, guard sequence, tests, and rollback.

M2 has one bounded gate: complete `canonical-operator-surface-map.md` and its CLI projection. Before the
first source edit, every old source module/path/symbol/import/test/build/metadata/consumer and every
collision with existing `src/charter/` has an approved exact target/disposition. Missing/unresolved rows
block. The gate cannot alter scope/order/terminal zero rule.

M3/M4 have no ownership-policy design question. Their migration rule is fixed: absent destination →
verified copy/move then remove old; identical destination → verify then remove old; divergent destination →
hard-fail with both intact; completion requires old-named paths absent. This is a bounded migration plan,
not a runtime ledger architecture.

M5 has no history exception beyond the four fixed exclusion roots (`kitty-specs/`,
`.kittify/migrations/mission-state/quarantine/`, `kitty-ops/`, `.kittify/missions/`), none of which it
edits or renames for a pre-existing path. It consumes the occurrence map and rewrites/renames every
remaining prose/history hit and referrer in current `HEAD` outside those roots; `local_design_questions`
is 0 (the disposition of the serialized-records question that previously gated it, `DM-01M0P6C8`, is
resolved).

M6 has no exception question. It removes the complete CR/control/product/fixture set, deletes transition
baseline/allowlist machinery, uses numeric-byte negative tests, and runs the inventory contract's checked,
no-pipeline forced-text content + NUL-safe pathname subprocesses over `HEAD` with the contract's four fixed
exclusion roots; both counts must be zero, any raw git error must fail closed, and any other
pathspec fails.
The zero attestation includes the final commit/tree OIDs; any tree change invalidates it and CI/release
reruns both audits on the merge/publish result tree.
The required M6 output/entrypoint is token-literal-free `scripts/audit_retired_term_zero.py`; required
external check marker is `terminology-zero-current-tree`, and its stdout JSON never modifies the tree.

## Dependency and rollback

M1→M2→M3→M4→M5→M6 is strict. Before a dependent wave lands, revert the current wave. Afterward, reverse
the landed suffix or forward-fix. M3/M4 rollback restores verified backups and never silently overwrites
divergent data. M6 alias rollback is valid only before 4.0 publication; after publication use release-level
rollback. No rollback may claim I6 while either zero audit is nonzero.

## Assignment tables

`stacked-plan.md` contains:

1. one row per OC with its member set (= all TSV rows carrying that `occurrence_class_id`; the ID span is
   orientation only — spans interleave) and exactly one M1–M6 owner;
2. one row per CR with frozen-base source hits/introduction owner plus distinct later-created product/
   control coordinates assigned to M6 removal, target, budget/control/tests;
3. arithmetic proving OC member union equals the complete manifest and wave sets are disjoint;
4. cross-wave input/output joins and merge gates;
5. M1 zero-decision dry run and M2 pre-edit topology-map dry run.
