# Specification: Synthesized DRG Stale-Refresh Fix

**Mission:** `synthesized-drg-stale-refresh-01KXN8KZ`
**Mission ID:** `01KXN8KZYA1MY8RTXJR5BKH1TR`
**Type:** software-dev
**Created:** 2026-07-16
**Source:** GitHub issue [#2681](https://github.com/Priivacy-ai/spec-kitty/issues/2681)

## Purpose

Any project whose charter uses a **synthesized DRG** (an org-authored / non-built-in doctrine graph) can become permanently blocked from running `spec-kitty agent action implement <WP>`. The command fails with `Error: synthesized_drg stale`, and none of the prescribed remediations (`charter synthesize`, `charter resynthesize`, `materialize`, `init`, `upgrade`, `doctor`) clear it — every one of them reports success while leaving the project in the exact same blocked state.

This happens because two correct, individually-justified behaviors interact badly: freshness is judged by comparing a timestamp that a prior fix (#1912/#1913) deliberately freezes on no-op runs (to keep the git tree clean) against a bundle timestamp that keeps advancing on ordinary git operations (clone, checkout, rebase, machine migration) even when doctrine content hasn't changed. Once the frozen timestamp falls behind, it can never catch up, because the only operation that would refresh it is a no-op write that is, by design, suppressed.

This mission makes DRG freshness reflect whether the synthesized graph still matches the doctrine content it was built from — not incidental filesystem timestamps — while fully preserving the clean-tree guarantee that #1912/#1913 introduced.

## User Scenarios & Testing

**Primary actor:** an operator or agent running `spec-kitty agent action implement <WP>` (or any command gated on charter freshness) in a project configured with a synthesized (non-built-in) charter DRG.

### Primary scenario (the behavior we are fixing)

1. A project has a synthesized DRG that was built from the doctrine/bundle content currently on disk — nothing in the doctrine or the synced bundle has changed since it was synthesized.
2. The operator performs an ordinary git operation that touches file mtimes without changing file content — a fresh clone, a `git checkout`, a rebase, or moving the checkout to a new machine.
3. The operator runs `spec-kitty agent action implement <WP>`.
4. **Expected (post-fix):** the DRG is reported fresh and `implement` proceeds normally.
5. **Current (defective) behavior:** the DRG is reported `stale`, `implement` refuses to run, and every prescribed remediation command reports success without changing the outcome — the project is permanently stuck.

### Acceptance scenarios

- **AS-1 (fresh survives mtime perturbation):** *Given* a synthesized DRG built from doctrine content that is still current on disk, *when* an operator performs any sequence of git operations that changes file mtimes without changing doctrine content (clone, checkout, rebase, machine migration), *then* the DRG freshness sub-state is `fresh` before and after, and `implement` is not blocked.
- **AS-2 (genuine staleness still detected):** *Given* a synthesized DRG, *when* the doctrine or synced-bundle content it was built from is subsequently edited, *then* the DRG freshness sub-state is reported `stale`.
- **AS-3 (remediation actually clears genuine staleness):** *Given* a DRG correctly reported `stale` per AS-2, *when* the operator runs either remediation command — `spec-kitty charter synthesize` or `spec-kitty charter resynthesize` — *then* the DRG freshness sub-state becomes `fresh` and `implement` proceeds — the remediation is not a no-op with respect to the reported state. Both commands must be capable of clearing genuine staleness; it is not acceptable to leave them broken and clear staleness only via a newly-introduced command.
- **AS-4 (no permanent deadlock, single-pass):** *Given* any project state, *when* the operator runs the prescribed remediation once and re-checks, *then* the sub-state is `fresh` after that single remediation invocation (≤1 remediation attempt) — it never requires an unbounded remediation-then-check loop and never reports `stale` indefinitely against unchanged doctrine content.
- **AS-5 (#2681 full reproduction resolved):** *Given* the full reproduction sequence reported in #2681 — synthesize once; let a subsequent no-op-stable run occur; perform a git operation that advances the bundle mtime (status now reports `stale`); then attempt remediation via **both** `spec-kitty charter synthesize` (step 4) **and** `spec-kitty charter resynthesize` (step 5), which on pre-fix code both report success while leaving the DRG stuck `stale` — *when* the operator runs `implement`, *then* (after the fix) the remediation has cleared the DRG to `fresh`, `implement` is not blocked, and no manual edit to any doctrine or manifest file is required.
- **AS-6 (built_in_only unaffected):** *Given* a project using only the built-in doctrine (no synthesized DRG), *when* the operator runs `implement` or checks charter freshness, *then* behavior and reported sub-state are unchanged from before this mission.

### Edge Cases

- Doctrine content changes **and** a git operation advances the bundle mtime in the same window — the DRG must still be correctly reported `stale` (content change takes precedence over any mtime-only signal).
- Repeated no-op runs of the remediation command against an already-fresh DRG must remain no-op-stable (see NFR-001) — the fix must not turn every remediation run into a git-dirtying write.
- A synthesis manifest, graph file, or synced-bundle record is missing or unreadable — the existing `missing` sub-state and its remediation guidance must continue to be reported, not `stale`.
- A project migrates from a legacy fresh-project seed (pre-manifest) into a manifest-backed synthesized DRG — freshness reporting must not regress for that transition.
- Clock skew or non-monotonic timestamps between the machine that synthesized the DRG and the machine now checking it must not, by themselves, produce a false `stale` report when content is unchanged.
- **Pre-fix / already-deadlocked manifest:** a synthesis manifest written by a *pre-fix* CLI build — either already stuck `stale`, or lacking whatever content-identity signal the fix introduces — must self-heal to `fresh` within a **single** prescribed remediation run, with no second stale bounce and no manual edit. This is the real upgrade path (the #2681 reporter hit exactly this on a downstream project).
- **Upstream-bundle precedence (regression pin, `computer.py`'s `synced_bundle.state != "fresh"` branch):** when the synced bundle is itself not `fresh` (its own upstream content is stale/missing), the synthesized DRG must still be reported `stale` — the upstream-content signal takes precedence and the fix must not drop this pre-existing correct guard.
- **Fail-posture on comparison failure:** if the freshness comparison mechanism itself fails on files that *exist* (e.g. an unreadable or corrupt bundle/manifest, distinct from the already-covered `missing` case), the result must not silently reintroduce a permanent false-`stale` trap; the failure posture must be explicit, documented, and recoverable via a prescribed remediation.

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | A synthesized DRG whose underlying doctrine/bundle content is unchanged from what it was synthesized against MUST be reported `fresh`, regardless of filesystem-mtime perturbation caused by git operations (clone, checkout, rebase, machine migration). | Proposed |
| FR-002 | A synthesized DRG whose underlying doctrine/bundle content has genuinely changed since it was synthesized MUST continue to be reported `stale`. | Proposed |
| FR-003 | The remediation commands operators use to clear a `stale` synthesized DRG — `spec-kitty charter synthesize` (the command the freshness gate emits as its `remediation` string) and `spec-kitty charter resynthesize` (the parallel resynthesis path #2681 also exercised) — MUST each be able to clear a genuinely `stale` DRG and bring it to `fresh`. Freshness gating MUST NOT be capable of reaching a state where such a remediation reports success while the gate stays permanently blocked. Introducing a *new* remediation command is permitted only as an **addition**; it MUST NOT be used as a substitute that leaves `synthesize`/`resynthesize` still incapable of clearing genuine staleness. | Proposed |
| FR-004 | Projects using only built-in doctrine (`built_in_only`) MUST see no change in reported freshness sub-state or gating behavior as a result of this mission. | Proposed |
| FR-005 | The **full** reproduction sequence described in #2681 — synthesize once; let a no-op-stable run occur; perform a git operation that advances the bundle mtime (status now reports `stale`); attempt remediation via **both** `spec-kitty charter synthesize` (step 4) and `spec-kitty charter resynthesize` (step 5); then run `implement` — MUST no longer produce a permanent block, and MUST require no manual edit to any doctrine or manifest file to unblock. | Proposed |
| FR-006 | The `missing` and `built_in_only` freshness sub-states, and their existing remediation guidance, MUST continue to be reported exactly as before for the conditions that produce them today. | Proposed |
| FR-007 | Any canonical documentation of the freshness-detection rule that this mission changes (for example, the charter-status JSON contract referenced by the freshness computer's module docstring) MUST be updated to describe the corrected behavior, so the published contract does not drift from the implementation. The plan phase MUST confirm the canonical location of that contract document. | Proposed |

### Non-Functional Requirements

| ID | Requirement | Measurable threshold | Status |
|----|-------------|----------------------|--------|
| NFR-001 | Runs of the synthesis/resynthesis pipeline that produce no content change MUST leave the git working tree clean, preserving the #1912/#1913 intent. | `git status --porcelain` is byte-identical before and after a no-op-stable synthesis/resynthesis run — 0 file modifications. | Proposed |
| NFR-002 | Freshness computation MUST stay within the CLI's interactive response budget. | Freshness computation (charter status / gate check) completes in under 2 seconds wall-clock on a representative project (e.g. this repository's own `.kittify/`). | Proposed |
| NFR-003 | The fix MUST NOT introduce a new required manual step or external dependency for operators. | 0 new manual steps and 0 new external dependencies added to the freshness-check or remediation path, verified by mission review. | Proposed |
| NFR-004 | New/changed code MUST meet the project quality bar. | `mypy --strict` passes, `ruff check` reports 0 issues on changed files. | Proposed |
| NFR-005 | New/changed logic MUST be adequately tested. | ≥90% line coverage on new/changed lines in the affected modules. | Proposed |
| NFR-006 | The regression suite MUST reproduce the defect with **realistic** timestamps and follow red-first discipline. | ≥1 test constructs the #2681 failure with a past-dated manifest `created_at` relative to an advancing bundle mtime, is verified RED on the pre-fix code and GREEN after the fix, for **both** the `synthesize` and `resynthesize` entry points; the pre-existing future-dated (`2099-…`) `fresh` test MUST NOT be counted as this guard. | Proposed |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | MUST NOT weaken or revert the #1912/#1913 clean-tree behavior — no-op-stable synthesis/resynthesis runs must remain non-dirtying. | Proposed |
| C-002 | MUST NOT change `built_in_only` freshness semantics or gating behavior. | Proposed |
| C-003 | MUST use canonical terminology — "Mission" not "Feature" — in all new user-facing text, error messages, and documentation touched by this mission. | Proposed |
| C-004 | MUST NOT introduce any new blocking manual remediation step that the operator has to discover on their own (e.g. hand-editing a manifest file). The fix must be self-resolving via the documented remediation commands (`charter synthesize` / `charter resynthesize`), which must be *corrected* rather than left broken behind a new escape-hatch command. | Proposed |
| C-005 | MUST reuse the project's existing canonical content-identity freshness pattern — an input-content hash stored at write time and compared at read time, as already implemented for the `charter_source` sub-state (`charter_hash` in `metadata.yaml`) — rather than inventing a third, divergent freshness algorithm. There MUST remain **one** canonical **read** authority for "is the synthesized DRG current with respect to the doctrine/bundle content it was built from", and its relationship to the existing manifest output-integrity check (`manifest.verify()` / per-artifact `content_hash`) MUST be stated, so the two do not drift into competing authorities. | Proposed |
| C-006 | The content-identity freshness signal introduced per C-005 MUST be produced by a **single canonical writer** — one shared helper consumed by BOTH manifest-construction sites, `write_pipeline.promote` (the `synthesize` path) and `resynthesize_pipeline._rewrite_manifest` (the `resynthesize` path) — so the two entry points cannot compute or store the signal differently. Write-side unification MUST be structural (one shared producer), not enforced only by parallel tests. | Proposed |

## Success Criteria

| ID | Outcome |
|----|---------|
| SC-001 | The #2681 reproduction sequence ends with `implement` unblocked, with zero manual manifest edits required. |
| SC-002 | Across repeated git operations (clone/checkout/rebase) that leave doctrine content unchanged, the reported freshness sub-state stays `fresh` — 0% false-`stale` occurrences. |
| SC-003 | 100% of genuinely stale DRGs (doctrine content changed since synthesis) are still correctly reported `stale` and are clearable to `fresh` by a prescribed remediation. |
| SC-004 | `built_in_only` projects show 0% behavior change in freshness reporting or gating, before vs. after this mission. |
| SC-005 | No-op-stable synthesis/resynthesis runs continue to produce 0 git working-tree modifications. |

## Key Entities

- **Synthesis manifest** (`synthesis-manifest.yaml`): the record of when/how a synthesized DRG was built, including its authored timestamp and a set of fields that are treated as volatile (excluded from no-op-stability comparison).
- **Synthesized DRG** (`graph.yaml`): the org/non-built-in doctrine relationship graph built from doctrine content by the synthesis pipeline.
- **Synced bundle**: the local copy of doctrine content synchronized from its source, whose own freshness/change timestamp currently drives DRG staleness comparison.
- **Freshness sub-state**: the reported status of a charter artifact — one of `built_in_only`, `fresh`, `stale`, or `missing` — each carrying its own remediation guidance.

## Related Issues

- **Fixes:** [#2681](https://github.com/Priivacy-ai/spec-kitty/issues/2681) — this mission's sole in-scope defect (synthesized DRG permanently stuck `stale`).
- **Regression source:** [#1912](https://github.com/Priivacy-ai/spec-kitty/issues/1912) / [PR #1913](https://github.com/Priivacy-ai/spec-kitty/pull/1913) — introduced the no-op-stable manifest write that this mission's fix must continue to honor (C-001). The originating fix is correct and preserved; only its interaction with mtime-based freshness is defective.
- **Related, out of scope:**
  - [#1914](https://github.com/Priivacy-ai/spec-kitty/issues/1914) — open umbrella issue for no-op-stable governed operations generally. This mission resolves one instance of that class (the synthesized-DRG freshness gate); the umbrella issue remains open for other instances.
  - [#2157](https://github.com/Priivacy-ai/spec-kitty/issues/2157) — an adjacent `implement`-gate bounce, but caused by `synthesized_drg: MISSING`, a different terminal state from the `stale` deadlock this mission addresses. Not folded into this mission's scope.
  - [#2373](https://github.com/Priivacy-ai/spec-kitty/issues/2373) — a sibling no-op-stable lineage issue in `build_charter_context`, a different code surface from the freshness computer this mission touches. Not folded into this mission's scope.
- **Explicitly not related:** [#2009](https://github.com/Priivacy-ai/spec-kitty/issues/2009) — a shipped (3.2.1) BOM/CRLF hash-comparison fix. Different mechanism; not to be conflated with this mission's mtime/timestamp defect.

## Assumptions / Open Design Decision

- **The fix must be content-identity-based; mtime-tolerance approaches are ruled out.** Filesystem mtimes are not a reliable freshness signal across git operations — clone, checkout, rebase, and machine migration reset or advance mtimes non-deterministically. A purely timestamp-tolerance/threshold heuristic *cannot* satisfy this spec's own edge cases together: a genuine content edit and an innocuous git-operation mtime bump are indistinguishable in timestamp-space (both set mtime to "now"), machine migration can produce unbounded jumps, and clock skew must not by itself trip `stale`. Therefore freshness MUST reflect whether the synthesized DRG matches the doctrine/bundle **content** it was built from. This is a determined design outcome, not one of several co-equal options.
- **What remains genuinely open for `/spec-kitty.plan`** is narrower: *where and how* the content-identity signal is sourced and stored (which input set is hashed; whether the signal lives on `SynthesisManifest` with a `schema_version` bump; how a pre-fix manifest lacking the signal is backfilled on first remediation), and *how it reconciles* with the existing manifest output-integrity check (`manifest.verify()` / per-artifact `content_hash`). Per C-005 the plan MUST reuse the existing `charter_source` `charter_hash` pattern rather than invent a third algorithm, and per C-006 the write-side signal MUST be produced by one shared helper consumed by both the `synthesize` and `resynthesize` manifest builders.
- **Critical design interaction for the plan phase (from the squad):** the new content-identity signal must be **substantive** (i.e. NOT added to `_VOLATILE_MANIFEST_FIELDS`), so a pre-fix manifest lacking it triggers exactly one backfilling rewrite — satisfying the single-pass self-heal in AS-4 and the pre-fix-manifest edge case — **yet deterministic** under unchanged input, so steady-state runs recompute the same value and stay no-op-stable (C-001/NFR-001). Adding the field to the volatile set to "avoid churn" would silently break backfill and re-introduce the deadlock; the plan must explicitly avoid that trap.
- **Test-design input for plan/tasks (from the post-spec squad):** AS-1 and AS-5 are the load-bearing bug-reproductions and MUST be RED on the pre-fix code (past-dated `created_at` vs an advancing bundle); AS-2/AS-3/AS-6 are regression pins that already pass on pre-fix code. The existing `tests/specify_cli/charter_freshness/test_computer.py::test_synthesized_drg_fresh_when_graph_followed_bundle` uses a future-dated (`2099-…`) `created_at` sentinel that never reaches the defective comparison branch — it MUST NOT be treated as the regression guard (see NFR-006). Write-side no-op-stability guards that C-001/NFR-001 must keep green: `tests/architectural/test_no_op_stable_writes.py::test_charter_synthesis_is_no_op_stable`, `tests/charter/synthesizer/test_orchestrator_resynthesize.py`.
- No other unresolved clarifications remain; the narrowed open question above is a bounded design task for the plan phase, not a blocking ambiguity in scope or acceptance criteria.
- **No blocking dependencies.** This mission is independently shippable and does not depend on #1914, #2157, or #2373 landing first; it resolves one concrete instance of the #1914 umbrella without waiting on the umbrella's broader resolution. Seed-only scope was re-confirmed by code-surface inspection: #2373 (`build_charter_context`) has zero overlap with the freshness computer, and #2157 hits the same function but on the `missing` branch with a different root cause (implement-preflight cascade ordering), not the `stale` comparison this mission fixes.
