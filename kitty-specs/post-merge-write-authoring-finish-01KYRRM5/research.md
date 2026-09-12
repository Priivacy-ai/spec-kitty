# Research — Post-Consolidation Write Surface and Authoring Finish

Phase 0. Resolves the design decisions the spec deliberately left at spec-level. Grounded in the grounding-squad traces (paula/architect) and the canonical code.

## D1 — Squash-robust E2 CONSOLIDATED resolution predicate (the load-bearing one)

**Question**: After publish-to-trunk (E2) deletes the Target Ref, where does `SurfaceLocations.consolidated` point, and how do we verify the current checkout legitimately carries the mission's consolidated content?

**Decision**: In E2, `consolidated` = the **repository-root checkout**, gated by a **content-presence** predicate: the mission's own committed artifact tree is present at `HEAD` (checked via `git cat-file -e HEAD:kitty-specs/<mission_slug>/meta.json`, or an equivalent committed mission-content marker). Not commit-ancestry.

**Rationale**:
- **Squash-robust.** A squash publish-to-trunk rewrites history — the E1 consolidation commit is NOT a commit-ancestor of the Primary Branch. `git merge-base --is-ancestor <baseline_merge_commit> HEAD` therefore FAILS after a squash even though the content is present. A content-presence check succeeds regardless of commit topology (squash, rebase, or merge-commit).
- **Branch-agnostic.** It does not hard-code "main"; it accepts any checkout that carries the consolidated content (forbidden-ref selection is C-006/write_seam's existing "never a hand-picked ref" rule).
- **Anchored, not guessed.** `baseline_merge_commit` (durable in `meta.json`, landed at E1 on the Target Ref) is the *phase* signal (mission is consolidated); the content-presence check is the *location validity* signal (this checkout is a valid CONSOLIDATED home). Together they replace the non-existent "recorded merge target."

**Alternatives considered**:
- *Commit ancestry (`--is-ancestor baseline_merge_commit HEAD`)* — rejected: breaks under squash (the common publish mode), the exact false-negative the architect flagged.
- *Record a new `merge_target_branch`/`consolidation_ref` field at E1* — rejected as unnecessary scope: the content-presence predicate needs no new durable field beyond `baseline_merge_commit`, which already exists.
- *`git branch --contains`* — rejected: the merge-base is an ancestor of every descendant branch → maximally ambiguous (architect B1).

**FR-006 falls out**: when the phase signal says consolidated but the content-presence check FAILS on the current checkout, refuse-with-recovery, naming a checkout that carries the content (C-004).

## D2 — Lifecycle-phase signal + E2 disambiguation

**Decision**: derive phase inside `resolve_placement_only` from durable `meta.json`:
- **pre-consolidation**: `baseline_merge_commit` absent → route unchanged from #3076 (no regression).
- **consolidated (E1)**: `baseline_merge_commit` present AND Target Ref branch still exists → CONSOLIDATED = Target Ref tree.
- **published (E2)**: `baseline_merge_commit` present AND Target Ref absent → CONSOLIDATED = repo-root checkout gated by D1 content-presence.
- **Legacy null-baseline fallback (C-003)**: Target Ref absent alone is ambiguous (never-created vs deleted). Conjoin with terminal-completion evidence a consolidation produces — **all WPs `done` in the status event log** and/or `mission_number` assigned. Target-Ref-absent + NOT-terminal ⇒ pre-consolidation never-created (route unchanged).

**Rationale**: `baseline_merge_commit` is already durable and already required by `review --mode post-merge`; the status event log and `mission_number` are the only signals a *consolidation* produces that a never-created mission cannot fake. `get_feature_target_branch` stays unrouted (C-003) — the branch-existence probe lives in the new phase reader, not the foundation reader.

## D3 — Internal phase derivation (no threaded parameter)

**Decision**: `resolve_placement_only` derives phase itself; **no** phase parameter threads through `PlacementSeam.write_target` or `commit_for_mission`. Both the probe path and the materializer re-derive from the same durable meta.

**Rationale**: NFR-001/C-001. The probe (`write_target`) and the commit (`commit_for_mission`) re-resolve independently (documented at `write_seam.py:116-119`). A threaded parameter would let them disagree (probe says "routable to consolidated", commit resolves to the deleted Target Ref → split-brain + #3073-shaped residue). Internal derivation from one durable source makes disagreement impossible and preserves the single-resolver invariant (C-006 — phase is an input the resolver computes, not a second resolver).

## D4 — The ADR (one document, two decisions)

**Decision**: author ONE ADR `docs/adr/3.x/2026-07-30-1-consolidated-write-surface-and-consolidate-terminology.md`:
1. **Design** — wire `TopologySurface.CONSOLIDATED` (first production wiring): phase-resolved integrated-tree surface (E1 Target Ref tree / E2 repo-root content-present, D1); internal phase derivation (D3). Extends 2026-07-23-2 (which named `post-consolidation`/`CONSOLIDATED` but wired only the acceptance-verification side); re-affirms 2026-06-24-1 C-006 (single write resolver).
2. **Terminology (FR-014, #3080 foundation)** — `consolidate`/`consolidation` is canonical for the lane-consolidation sense of `merge`; records the "foundation now / full rename in #3080" split.

**Rationale**: wiring CONSOLIDATED *is* where the term becomes load-bearing, so one ADR coherently carries both. Avoids ADR proliferation; #3080 cites it as the canonical-term decision record.

## D5 — Terminology drift-ratchet guard mechanism

**Decision**: extend `tests/architectural/test_no_legacy_terminology.py` with a **curated forbidden-phrasing** check for lane-consolidation-sense "merge" (e.g. "lane merge", "merge the lanes", "merging lanes", "lane-merge"), canonical = "consolidate", with a **baseline allow-set** grandfathering existing occurrences (shrink-only ratchet). Prove a **red-first bite fixture** (a new forbidden phrasing fails) AND green on legitimate git-merge / publish-to-origin "merge" uses and on the grandfathered set (SC-011).

**Rationale**: a bare "merge" ban would flood on the three legitimate senses; a curated phrasing list targets the lane-consolidation sense specifically, matching how the existing guard forbids specific terms ("ceremony", legacy "feature"). Baseline-ratchet matches the repo's arch-gate campsite pattern — stops new drift without demanding the full #3080 rename.

## D6 — Acceptance authoring surfaces (#2318)

**Decision**:
- **Register/execute (FR-007/008)**: extend `agent mission acceptance-verdict` (the canonical authoring command, C-008) with a negative-invariant register + execute path. The `NegativeInvariant` dataclass (`acceptance/matrix.py:107-146`) already carries every field → **no acceptance-matrix schema migration**. Execution reuses the existing engine (`enforce_negative_invariants`, `matrix.py:513`).
- **Diagnose hardening (FR-009)**: wrap `NegativeInvariant.from_dict` per-invariant at the `AcceptanceMatrix.from_dict` load path so a malformed shape is *reported* (which invariant, why) instead of raising — the actual mgifford defect (crash before diagnosis).
- **Fresh verdict (FR-010)**: `gates_core.py` persists the recomputed `overall_verdict` unconditionally under `mutate_matrix` (already fixed in #3076 for the negative-invariant branch; extend to the all-pass/no-invariant branch — samuelgoff's stale `pending`).
- **Prompt (FR-011)**: edit the accept mission-step prompt SOURCE at `src/doctrine/missions/mission-steps/` to DRIVE `acceptance-verdict`; never the 12 generated agent copies (propagation via `spec-kitty upgrade`).

## D7 — Issue-reference URL widening + provenance (#1738)

**Decision**:
- **FR-012**: widen the SINGLE `_GH_ISSUE_PATTERN` (`tasks/issue_matrix.py:61`) in place with a same-repo URL alternation (`https://github.com/Priivacy-ai/spec-kitty/issues/(\d+)` — repo derived from the git remote / a canonical constant, not hard-coded ad hoc). No second matcher (there are already three issue-ref parsers; the module docstring warns against a fourth). Cross-repo URLs are NOT matched → they cannot newly block the completeness gate (SC-008).
- **FR-013**: add `source_file` to the `IssueReference` NamedTuple + its `to_dict`/`from_dict` round-trip. The multi-file dedup (`issue_reference_discovery.py:108-113`, currently `dict` keyed by number, which collapses provenance) changes to preserve **first-occurrence** provenance (matching the existing first-line-context contract) — key on number but retain the first source_file, and assert N-files→provenance in the regression.

**Rationale**: same-repo-only keeps currently-green missions green; single-regex + single-type change avoids the whack-a-field drift paula/architect flagged.

## Open items for /tasks (none blocking)

- The exact committed mission-content marker for D1 (`meta.json` presence vs a dedicated marker) — pick the cheapest committed path during implement; both are squash-robust.
- Same-repo detection source for D7 (git remote parse vs a canonical repo constant) — decide at implement; prefer the existing canonical constant if one exists.
