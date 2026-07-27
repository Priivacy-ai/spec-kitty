# Phase 0 Research — Primary & Merge Vocabulary Disambiguation (Track 1)

Full research report (census + decisions): the mission grounding lives in the operator research doc
`research-2653-primary-merge-disambiguation.md`. This file records the plan-relevant conclusions.

## Decisions

- **D1 (operator):** Keep **"Primary Branch"** as the canonical Sense-B term — it is already the blessed
  glossary entry (`docs/context/orchestration.md:429`). The issue's "default branch" proposal is rejected
  (it would regress against the glossary and break the `primary_branch`/`current_is_primary` wire keys).
- **D2 (operator):** Split into an **epic** — Track 1 (this mission, cheap/low-risk) + Track 2 (#2730,
  isolated Sense-C code rename). `src/glossary/` package removal is a third, separate item (#2727).

## Canonical terms (what the glossary + prose will enforce)

| Sense | Canonical term | Authority |
|-------|----------------|-----------|
| primary A — partition | **PRIMARY partition** | keep (spec) |
| primary B — branch | **Primary Branch** | existing glossary entry (D1) |
| primary C — checkout | **repository root checkout** | charter §Branch-Intent Terminology Governance |
| primary D — ref | **target ref / commit target** | spec |
| merge 1 | **lane consolidation / consolidate** | spec |
| merge 2 | **branch integration / git merge** | spec |
| merge 3 | **publish to origin/main / operator merge** | spec |

## Key findings that shaped the plan

- **Glossary home moved.** `glossary/contexts/` is the retired legacy home; `docs/context/*.md` is the
  canonical home (charter FR-009) and is already mature. `glossary/README.md` still points at the dead dir
  (FR-005) → repoint + fold legacy prose (FR-006).
- **Enforcement is thin.** `test_no_legacy_terminology.py` is a hardcoded 2-literal grep (`ceremony`,
  `status-writing`); it CANNOT enforce primary/merge sense-correctness. Track 1 is review-enforced against
  the occurrence map; a durable alias-ban guard is deferred to Track 2 (FR-011). Guard-skip risk #2701.
- **FR-007 correction (squad).** `tasks_shared.resolve_primary_branch` is a **delegating shim** (not a
  divergent copy); the real partial re-implementation is `_resolve_primary_branch_for_recommendation`
  (`mission_branch_context.py:197`) — that is the DIRECTIVE_044 consolidation target.
- **Exempt-surface corrections (squad).** `is_primary_artifact_kind` is **public** (`mission_runtime.__all__`,
  24 callers/7 packages, pinned by `test_mission_runtime_surface` + `test_shared_package_boundary`) →
  excluded from renames. `merge_target_branch` is a serialized WP-frontmatter key pinned by the shape
  registry → exempt. Sense-C serialized tokens (`primary_repo_root`, `primary_candidate`,
  `WorktreeTopology.PRIMARY`, `PRIMARY_CHECKOUT*`) → Track 2.
- **Sequencing risk (squad).** In-flight `mission-step-authority-01KXNZMT` edits `docs/context/orchestration.md`
  and restructures `src/doctrine/missions/mission-steps/` — the exact FR-001/002/003 surfaces → C-006
  (append-only additions; coordinate land order).

## Alternatives considered

- **Do the Sense-C code rename in Track 1** — rejected (D2): ~400 occ / 111 pinning test files / two
  literal-string arch gates / WP00-load-bearing → its own isolated bulk-edit mission (#2730).
- **Rename Sense-B "primary branch" → "default branch"** — rejected (D1): regresses the existing glossary
  and breaks wire keys.
- **Ban "primary" via the terminology guard** — rejected: "primary" is canonical in Senses A/B; only the
  retired *alias phrases* are bannable, and the Sense-C ones persist until Track 2.
