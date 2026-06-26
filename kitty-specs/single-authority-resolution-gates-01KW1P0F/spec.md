# Single-Authority Resolution Gates

**Mission ID:** 01KW1P0FRYK89H5TK5QK8148X9 · **Type:** software-dev · **Target branch:** `design/infra-logic-separation-2173`
**Epic:** #2173 Phase 1 (sub of #1619) · **Binding design:** ADR `architecture/3.x/adr/2026-06-26-1-single-authority-seam-and-call-site-gate.md` + `docs/engineering_notes/2173-infra-logic-separation/00-SYNTHESIS.md`

> **Revision note (post-plan squad + residual hunt, 2026-06-26):** factual anchors corrected against live code; FR-002 re-scoped from a guard mutation to a 2-site caller fix (the residual hunt proved the guard is sound and mutating it re-opens #1887); discriminators hardened to provenance/def-use with concrete floors; FR-008/SC-006 contradictions resolved. See the Issue Matrix and `research.md` D-5/D-8.

## Overview & Context

Mission-artifact paths (task-index and status files, primary mission dirs) are resolved through seams that *several callers bypass*. Two consequences are live P0 defects, and a third is a latent regression hazard:

- **The write leg bypasses the kind-aware authority (#2154).** `mark_status`'s *write* (`tasks.py:1807`) composes the coordination-worktree dir via the kind-**blind** resolver, while its *commit* (`:1906`) and `move_task`'s *validation* (`:658`) correctly use the kind-**aware** authority targeting the primary surface. Result: every work package blocks on phantom "unchecked subtasks." (Live-confirmed: write_dir != read_dir.)
- **Two mixed-partition commit bundles silently drop status writes (#2155).** `move_task` (`tasks.py:1555`) and the `implement`/claim path (`implement.py:1311`) bundle a *primary* WP file with the *coord*-owned status artifacts (`status.events.jsonl`/`status.json`) in a single **primary-surface** commit. The `safe_commit` `.worktrees/` guard correctly refuses the coord paths — and both callers **swallow** the `SafeCommitPathPolicyError` as a yellow "Auto-commit skipped" warning, silently dropping the WP file's activity-log update from the feature branch (dirty tree). This is the masked tail of #2155. **The guard is not the defect** — the callers committing coord paths through a primary worktree are.
- **The handle-canonicalization boundary has no regression guard (#2164 residual).** The read-leg fix shipped (#2161, a pre-condition), but `primary_feature_dir_for_mission` is topology-blind-by-design and **auto-blessed** by every existing gate; nothing checks whether the handle reaching it was canonicalized. Of **38** live call sites, only ~9–11 are canonical today (the seam-internal sites); a future cloned write seam re-introduces the divergence #2164 fixed, silently.

The unifying defect (ADR 2026-06-26-1): crossing a resolution boundary is a *convention every caller must remember*, and the conventions diverge. The fix is **single-authority routing at the seam + an AST call-site gate** that makes the omission a CI failure. This mission is **Phase 1**: route the bypassing write paths through the *existing* authority, and add the gates. It does **not** introduce the Phase 2 `MissionResolver` DI port, and it does **not** mutate the `safe_commit` guard (that would re-open #1887).

## User Scenarios & Testing

**Primary actor:** an engineer or agent running the `implement → review` loop.

1. **Happy path (unblocked loop):** An implementer marks subtasks done (`mark_status`), then advances the WP (`move_task --to for_review`). The status write and its validation read the *same* surface → the WP advances. *(Today this blocks on "unchecked subtasks.")*
2. **Status write commits, not silently dropped:** `move_task` / claim auto-commit a WP file together with its coord-owned status artifacts. The coord status is committed to the coord surface (via the coordination transaction) and the WP file to primary — **no swallowed `SafeCommitPathPolicyError`, no dropped activity-log**. *(Today the commit is skipped with a warning and the feature branch is left dirty.)*
3. **Regression caught at build time:** A developer adds a new write/placement seam that composes a mission path from a bare, un-canonicalized handle (or uses the kind-blind resolver for a mandated write). The architectural gate fails CI naming the offending call site and the sanctioned seam. *(Today it sails through every gate.)*
4. **Ambiguous handle:** Any seam handed a handle matching more than one mission raises `MissionSelectorAmbiguous` — never silently picks the first match.

**Primary exception path:** a handle for a mission absent from the resolver (cold-miss) fails closed and loud, never a verbatim passthrough that composes a non-existent literal dir. A genuinely wrong-surface `.worktrees/` write is still refused by the unchanged guard.

## Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | `mark_status`'s write leg (`tasks.py:1807`) resolves its target through the same kind-aware authority its commit leg (`:1906`) and `move_task`'s validation (`:658`) use, so the write lands on the surface the validator reads. Acceptance asserts write-target dir == validation-read dir **as the same value, under both coordination AND flat/legacy topologies**. Closes #2154. | Proposed |
| FR-002 | The two mixed-partition auto-commit bundles — `move_task` (`tasks.py:1555`) and `implement`/claim (`implement.py:1311`) — are routed so the coord-owned status artifacts commit to the **coord** surface (via the `BookkeepingTransaction` pattern `workflow.py:_commit_workflow_change` already uses, or by splitting coord status out of the primary-kind commit), and the WP file commits to primary — with **no swallowed `SafeCommitPathPolicyError`**. The `safe_commit` `.worktrees/` guard (`src/specify_cli/git/commit_helpers.py:983-991`) is **NOT modified** (mutating it re-opens #1887). Closes #2155. | Proposed |
| FR-003 | An architectural call-site gate (coord-authority discriminator) fails the build when a mission-artifact **write** uses the kind-blind `resolve_feature_dir_for_mission` where the kind-aware authority is mandated. The discriminator classifies write-vs-read by an explicit, documented predicate (not a one-entry allowlist tautology) and **allowlists the legitimate coord-owned writes that bypass `commit_for_mission` by design** (`decisions/emit.py`, `widen/state.py`). Floor ≥ the live count of write-candidate sites (census at /tasks). | Proposed |
| FR-004 | An architectural call-site gate (canonicalizer discriminator) fails the build when an **un-canonicalized handle** reaches `primary_feature_dir_for_mission`. It scans **calls by name** (the primitive composes the path internally) and judges "canonical" by **provenance/intra-function def-use** — the arg is assigned from `_canonicalize_primary_read_handle` (or is a known-canonical `feature_dir.name`) **in the same function** — explicitly **not** by name-substring matching. Floor ≥ 38 (live census). Closes the #2164 class by construction. | Proposed |
| FR-005 | Every currently-bypassing canonicalizer call site is **routed** through `_canonicalize_primary_read_handle` by default; allowlisting is the justified exception and **each allowlist entry must name an already-canonical provenance** (e.g. a pre-resolved `feature_dir.name`). At least the N sites passing a bare/raw handle (census at /tasks) MUST be routed, not allowlisted. The corrected latent sites are `runtime_bridge.py:98` and `:177` (path `src/runtime/next/runtime_bridge.py`); `decisions/decision_log.py:103` is a **raw `KITTY_SPECS_DIR` join, not a `primary_feature_dir_for_mission` call** → it belongs to FR-003's coord-authority surface, not this sweep. | Proposed |
| FR-006 | A parametrized, **stub-driven** convergence test asserts the read-seam dir == every write/placement-seam dir for every handle form (full slug, `<slug>-<mid8>`, bare `mid8`, ULID, numeric). The stub implements the faithful P1–P5 cascade with **distinguishable** outputs per form (a constant-returning stub is a rejected implementation); it drives the divergent cases — ambiguous → `MissionSelectorAmbiguous` (assert raise), cold-miss → fail-closed (assert raise) — and includes a **negative control**: ≥1 handle form that mapped *differently* under pre-fix code (red-first proof). | Proposed |
| FR-007 | (Fold of #1842, domain-matched) A `/tmp`-literal-in-tests ratchet using IC-01's gate pattern, **frozen-baseline shrink-only**: the current offenders (census ~82 at /tasks) are the frozen baseline; a **new** `/tmp/` literal in any test file fails the build (self-mutation test proves it). The full #1842 litter remediation stays out of scope. | Proposed |
| FR-008 | (Fold of #2034, domain-matched — **conditional**) Empirically re-derive #2034's actually-non-running test-file set in this mission's domain via a `pytest --collect-only` before/after diff per shard. Co-tag only the files proven *currently excluded*. **If the candidate files already run in CI (the audit indicates the two originally-named files do), this FR is satisfied-by-verification — add no redundant markers** and record the verification. | Proposed |

## Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|----|-------------|-----------|--------|
| NFR-001 | The gate allowlists are **composite-keyed** by `(enclosing_qualname, token_line)` derived live from source. **Note:** this key is net-new — neither in-repo precedent implements it (`test_protection_resolver_call_sites.py` is a bare module-path frozenset; `audit.py` keys on raw `rel_path:line`); building it is in-scope, reconciling C-005. | Zero allowlist churn on edits that do not change a call site's enclosing function or token. | Proposed |
| NFR-002 | Each gate is anti-vacuous: a **concrete integer** discovered-row floor (≥38 for the canonicalizer; ≥ live write-candidate count for coord-authority — mirroring the existing gate's `= 20`) plus an in-test self-mutation check that injects a violation **at a site structurally distinct from any IC-04 fix site** → gate FAILS → revert → PASSES. | Both guards present and green for each of the two gates; floor set to the live census, never 0/1. | Proposed |
| NFR-003 | The gate allowlist is a **shrink-only** governance artifact with the baseline pinned to the **pre-sweep** (pre-mission) count, so the sweep cannot inflate-then-freeze; a twin staleness guard fails the build on any entry not matching a live call site. | Allowlist entry count is non-increasing vs the pre-sweep baseline; zero stale entries at merge. | Proposed |
| NFR-004 | The new gates run in the fast test tier. | Each gate completes in < 30 s on the full `src/` tree. | Proposed |

## Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | The canonicalizer guard lives at the **seam in front of** `primary_feature_dir_for_mission`; canonicalization is NEVER folded into the primitive (the canonical fold *probes via* the primitive at `_read_path_resolver.py:454` — folding in recurses; this is the **recursion fence**, the lesson of the prior canonicalizer recursion bug). Acceptance **regression-pins** that `_read_path_resolver.py:454` stays a bare-handle probe and is allowlisted with the recursion-fence rationale. **Merge-blocker.** | Proposed |
| C-002 | Every patched seam propagates `MissionSelectorAmbiguous` unchanged; no silent first-match (C-009/WP07). Cold-miss fails closed and loud. **Merge-blocker.** | Proposed |
| C-003 | The read-leg handle-safety fix (#2161) is a **pre-condition**; a one-step verification confirms it is present on the base before building on it (not re-implemented). | Proposed |
| C-004 | Out of scope (do not expand): Phase 2 (the `MissionResolver` DI port), the `ResolvedMission` identity work (#2138, #2139, #1868), and the distinct surfaces #2091, #2100, #2123, #2115. | Proposed |
| C-005 | The gates **reuse** the existing Idiom-B machinery shape (`tests/architectural/test_single_mission_surface_resolver.py` + `surface_resolution_audit/audit.py`) — scan-by-name discriminator, self-test, floor — but the composite-key allowlist (NFR-001) and the def-use predicate (FR-004) are net-new extensions, not verbatim copies. No parallel/alternate gate mechanism is invented. | Proposed |
| C-006 | The `safe_commit` `.worktrees/` guard's `worktree_root`-foreignness discriminator is **not modified** — it is the #1887 wrong-surface backstop. The #2155 fix is at the two callers, never the guard. **Merge-blocker.** | Proposed |

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | A work package advances through `mark_status` → `move_task --to for_review` with no phantom "unchecked subtasks" block, under **both** coordination and flat topologies (the #2154 reproduction passes). |
| SC-002 | `move_task` and `implement`/claim auto-commit under coordination topology + unprotected branch with **no swallowed `SafeCommitPathPolicyError`** — coord status lands on coord, the WP file on primary, the tree clean (the #2155 reproduction passes); a deliberately wrong-surface `.worktrees/` write is **still refused** by the unchanged guard. |
| SC-003 | A deliberately introduced bypass — an un-canonicalized-handle write (FR-004) or a kind-blind mandated write (FR-003) — fails CI; reverting passes (each gate's self-test, injecting at a site distinct from the IC-04 fix). |
| SC-004 | Zero un-sanctioned bypassing sites: every bare-handle `primary_feature_dir_for_mission` site (census = 38) and every coord-authority write site is **routed** (default) or carries a rationale'd already-canonical allowlist entry; **≥ the bare-handle census count are routed, not allowlisted**; the allowlist is ≤ the pre-sweep baseline. |
| SC-005 | The convergence test passes for every handle form with no live fixtures, drives the ambiguity-raise + cold-miss cases, and includes a red-first negative control; a constant-returning stub is rejected. |
| SC-006 | No **new** `/tmp/` literal can be added to a test file (the frozen-baseline ratchet's self-mutation proves it); FR-008's target files are verified to run in CI via a before/after `--collect-only` diff (or confirmed already-running, no redundant markers added). |

## Key Entities

- **Kind-aware resolution authority** — `commit_for_mission(kind=)`, `resolve_planning_read_dir(kind=)`, `resolve_status_surface_with_anchor`: the single sanctioned decider of coord-vs-primary write/read target. *Present today; bypassed by the write leg and the two mixed bundles.*
- **Coordination transaction** — `BookkeepingTransaction` / `workflow.py:_commit_workflow_change`: re-anchors coord-owned status writes into the coord worktree so the guard passes by construction. The model FR-002's two callers must adopt.
- **Topology-blind primitive** — `primary_feature_dir_for_mission` (TBYD): composes the literal mission dir, handle-blind by contract. Must remain blind (C-001).
- **Canonical fold** — `_canonicalize_primary_read_handle`: the idempotent handle→canonical-dir-name fold the seam applies before the primitive; probes via the primitive at `:454`.
- **`safe_commit` guard** — `commit_helpers.py:983-991`: refuses a staged path whose first segment *relative to `worktree_root`* is `.worktrees/`. The #1887 backstop; unchanged (C-006).
- **Gate allowlists** — composite-keyed, shrink-only governance artifacts recording each sanctioned bypass with an already-canonical rationale.

## Out of Scope

Phase 2 `MissionResolver` DI port (#2173 Phase 2); `ResolvedMission`/identity strangler work (#1868, #2138, #2139); distinct bug surfaces #2091, #2100, #2123, #2115; the full #1842 litter remediation (only the frozen-baseline ratchet is in); the #2034 `ci-quality.yml` matrix change (only mission-owned co-tagging/verification is in); **any modification to the `safe_commit` guard** (C-006). #2140 (`is_committed` surface) is **monitored** — note if the canonicalizer gate covers it incidentally; do not pre-commit.

## Assumptions

- The #2161 read-leg fix is landed on `main` (C-003 verifies on the base).
- The Idiom-B gate *shape* is reusable; the composite-key + def-use predicate are net-new extensions (NFR-001, FR-004).
- Scope: the `mark_status` write leg + the two mixed-bundle callers + two gates (a/b/c-split canonicalizer + coord-authority) + two domain-matched test-hygiene folds. Multi-WP, multi-lane.
- The `move_task`/`implement` swallow of `SafeCommitPathPolicyError` is the reason #2155 has been low-visibility; the fix must surface (not re-swallow) a genuine failure.

## Issue Matrix (pre-planning 3-squad + post-plan residual hunt)

| Issue | Verdict | Note |
|-------|---------|------|
| #2154 | CLOSE | mark_status write-leg routing (FR-001); live-proven 3-leg convergence |
| #2155 | CLOSE | **2-site caller fix** (FR-002) — route the `move_task`/`implement` mixed bundles via the coordination transaction; guard unchanged (C-006). Residual hunt confirmed a genuine but swallow-masked residual at `tasks.py:1555` + `implement.py:1311` |
| #2164 (residual) | CLOSE | the canonicalizer AST gate (FR-004/005); read-leg fix shipped in #2161 |
| #1842 | FOLD (partial) | frozen-baseline `/tmp` ratchet only (FR-007) |
| #2034 | FOLD (conditional) | empirical re-derive + co-tag mission-owned only (FR-008); the two originally-named files already run → likely satisfied-by-verification |
| #2173 / #2160 / #1619 | REFERENCE | epic parent / class / strategic root |
| #1716 / #1868 / #1878 | REFERENCE | sibling epics — not merged |
| #2017 | REFERENCE | guard-friction; incidental, not closed |
| #2136 / #2119 | ALREADY DONE | pre-conditions satisfied (in #2161) |
| #2140 | MONITOR | gate may close incidentally |
| #2138 / #2139 / #2091 / #2100 / #2123 / #2115 | OUT-OF-SCOPE | Phase 2 / ResolvedMission / distinct surfaces / pinned residual |
