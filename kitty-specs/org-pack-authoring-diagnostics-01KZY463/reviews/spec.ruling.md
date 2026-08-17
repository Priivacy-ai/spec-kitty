# Operator ruling — spec phase, mission `org-pack-authoring-diagnostics-01KZY463`

**Date**: 2026-08-13
**Issued by**: operator, via Orchestrator Orry
**Status**: BINDING. This ruling **replaces** the acceptance bar for FR-001 and C-001.
Any verifier, refuter or later-phase agent that evaluates FR-001 evaluates it against
*this* ruling, not against the spec's original FR-001 text or the review findings that
shaped it.

---

## Why this ruling exists

The spec's FR-001 and C-001 were written on the premise that ADR
`docs/adr/3.x/2026-08-13-1-built-in-mission-subtree-stays-nested-retire-legacy-step-contracts.md`
(open PR #3378) was *proposed and unratified*, and that the legacy step-contract surface was
therefore fair game for a small consolidating code change.

That premise was **false**. First-hand verification (`gh pr diff 3378`) shows the ADR is:

```
status: Accepted
```

dated 2026-08-13, choosing **Option B**: the nested `packs/built-in/missions/` subtree is the
canonical built-in mission layout, and *"the legacy step-contract surface is **retired in its
entirety**"*. Its stated removal set covers `built_in_step_contracts/` (17
`*.step-contract.yaml` files), `src/doctrine/missions/step_contracts.py`, the
`src/specify_cli/mission_step_contracts/` package, the `mission_step_contract` ArtifactKind,
`packs/built-in/mission_step_contract.graph.yaml` (34 nodes), and every remaining caller.
Option C — keep everything as-is, including both step surfaces — was explicitly rejected.

Investing implementation effort in a surface an Accepted ADR retires wholesale is work that
lands and is then deleted. The operator was put the choice and ruled as below.

## The ruling

**FR-001 is narrowed to the guide correction only. It becomes a documentation-only
requirement.**

### In scope for FR-001 (all that remains)

1. Correct `docs/guides/how-to/governance/create-an-org-doctrine-pack.md` at **`:65`** (the
   layout tree) and **`:140`** (the namespace table) from `*.contract.yaml` to
   `*.step-contract.yaml`, so the guide stops instructing authors to create files the
   loader can never read.
2. In the same guide, **point authors at ADR `2026-08-13-1`** so an author reading the
   corrected instruction learns that this surface is slated for retirement in its entirety
   and does not treat the corrected suffix as a durable authoring target.

### Out of scope for FR-001 — explicitly dropped

- The **shared step-contract suffix constant** consumed by
  `step_contracts.py:MissionStepContractRepository.GLOB` and
  `pack_validator.py:_artifact_schema_registry()`. Dropped. The two definitions already
  agree today; de-duplicating them hardens a surface that is being deleted.
- **Removal of `snapshot.py`'s dead `_ARTIFACT_BUCKETS` table.** Dropped from this mission.
  It is genuinely dead code and the finding that identified it stands as a true observation,
  but it belongs to the retirement work under ADR `2026-08-13-1`, not here. It is *not*
  campsite-clean scope for this mission: the charter's campsite standing order folds
  **domain-matched** debt, and this mission's domain is org-pack authoring diagnostics, not
  the legacy step-contract surface.
- The new `pack_validator.py` **near-miss mismatch diagnostic** for
  `mission_step_contracts/` (the `*.contract.yaml`-with-no-matching-`*.step-contract.yaml`
  error). Dropped — it is new code on the retiring surface.

### Consequences the spec must absorb

- **C-001** must be rewritten. Its current text ("FR-001 touches `step_contracts.py` / the
  legacy `MissionStepContract` model only... that ADR is `Accepted` ... but its retirement
  ... has not yet been implemented") no longer describes the constraint. The constraint is
  now: *FR-001 changes no code at all; it corrects documentation and defers the surface to
  ADR `2026-08-13-1`.*
- The **Edge Cases** bullet that says "FR-001's diagnostic still fires for the stray
  `*.contract.yaml` file" is now describing a dropped behaviour and must go or be rewritten.
- The **Verified Code Surfaces** row on the snapshot bucket-counting mechanism keeps its
  factual finding (`_ARTIFACT_BUCKETS` is dead; `_count_artifacts` counts by directory
  membership) — the correction was verified and is worth preserving as evidence — but its
  concluding sentence, which assigns the removal to FR-001, must be restated to say the
  removal is deferred to ADR `2026-08-13-1`'s retirement work and is not this mission's.
- **User Story 1**'s scope and acceptance scenarios must be consistent with a docs-only
  FR-001. A scenario asserting a validator diagnostic fires is no longer satisfiable.
- The **FR table** row for FR-001 must retitle to match ("Guide correction for the
  step-contract suffix"), and any priority/dependency statement that treats FR-001 as a code
  change must be corrected.
- FR-002, FR-003 and FR-004 are **untouched** by this ruling. Do not re-open them.

## What the ruling does not do

It does not reverse, soften or re-litigate any confirmed finding from the spec squad's R1–R6
trail. Every finding fixed in `spec.confirmed.yaml` and the fresh-sweep rounds stands. This
ruling changes the *requirement*, and the fixes to text that no longer exists simply cease to
apply — it is not evidence that the squad erred.

## Instruction to the next verifier

The acceptance bar for FR-001 is **this file**. A verifier handed the original spec text will
re-derive the original verdict and file the docs-only FR-001 as an under-specified
requirement. That would be wrong. Verify FR-001 against the "In scope" list above, and verify
that every item in "Consequences the spec must absorb" has actually been absorbed — a
re-scope that edits FR-001's body but leaves C-001, the edge case, the FR table row or User
Story 1 describing the old behaviour is an **incomplete** re-scope and is a finding.
