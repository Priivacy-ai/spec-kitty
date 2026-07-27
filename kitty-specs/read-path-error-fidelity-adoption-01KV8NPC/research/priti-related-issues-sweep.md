# Planner Priti — EAGER related-issues sweep

**Mission:** `read-path-error-fidelity-adoption-01KV8NPC` (branch `feat/read-path-error-fidelity`)
**Author:** planner-priti (profile-loaded)
**Date:** 2026-06-16
**Tracker:** `Priivacy-ai/spec-kitty` (upstream — confirmed: #2007 lives here, not the fork)
**Mode:** READ-ONLY tracker sweep. No assign / claim / mutate. `unset GITHUB_TOKEN` on every `gh`.

## Scope clarification (load-bearing)

The "known in-scope set" mixes two numbering systems:

- **#2007 internal bug indices 1–16** (e.g. "#4, #7, #8, #12, #14, #15, #2, #6") — these are *epic-internal* bug numbers, **not** GitHub issue numbers. Their GitHub trackers are the C-cluster children: **#2010** (read-path unification → bugs 4/7/8/11/12/14/15) and **#2011** (submodule root → bug 6).
- **GitHub issue numbers** in scope: epic **#2007**, children **#2010 / #2011**, plus **#1832**, **#1619** (ExecutionContext builder-hardening), and the advanced epics **#1619 / #1868**. Baseline also names **#1827** (merge baseline, re-test-first).

This sweep finds GitHub issues **related to the read-path / context / error-fidelity surface that are NOT already in that baseline set**. Verified each candidate's live state with `gh issue view`.

> **Standing rule applied:** a CLOSED/MERGED issue on this surface is treated as **"claims-fixed, verify"** — Debbie's re-investigation already proved the #2007 "already-fixed five" reproduce despite present fixes. None of the closed items below may be trusted as fixed without a live repro.

---

## FOLD-IN — this mission should address these

| Issue | Title | State | Relation | Rationale (one line) |
|---|---|---|---|---|
| **#1692** | context resolve rejects primary mission dir when coord worktree is absent | CLOSED | Read-path coord/primary; `context resolve` is a named #2007 adoption call-site | The *exact* `StatusReadPathNotFound`-when-primary-exists / fail-closed-pre-read class Debbie pins for #11. CLOSED but on this surface → **verify-and-fold (claims-fixed, verify)**; behavior-equivalence across input classes is this mission's mandate. |
| **#1884** | setup-plan entry gate coordination-blind: `is_committed()` checks only primary HEAD | CLOSED | This IS the GitHub tracker for #2007 bug #7 (`spec_committed:false`) | Debbie: fix present but `is_committed` still has **no primary-target-branch leg** / coord-priority feeds wrong artifact path → reproduces. **Must re-test live, not trust closed.** Core of the error-fidelity/committedness cut. |
| **#1889** | decision open crashes (StatusReadPathNotFound) when `coordination_branch` declared but no coord worktree | CLOSED | GitHub tracker for #2007 bug #8 (`decision open` rejects coord-aware handles) | Same fail-closed-on-missing-coord-worktree class as #1692/#11. CLOSED but bug #8 is a live P0 in the synthesis → **verify live.** |
| **#1981** | map-requirements resolves spec.md against coord worktree instead of main | CLOSED | Read surface: planning artifact read picks wrong (coord) surface | Same coord-vs-primary read-surface defect the mission must make behavior-equivalent; fixed in #1990 but the "resolve from primary" pattern is exactly what the resolver-adoption must own uniformly, not per-callsite. Verify the fix routes through the SSOT, not a local patch. |
| **#1911** | Restore richer query-mode error `next_step` lost in #1910 reconciliation | OPEN | Error-fidelity: typed error must carry actionable remediation | #1910 replaced a rich `QueryModeValidationError` (carried `next_step`) with `MissionNotFoundError` that may drop the actionable affordance. Directly the "preserve typed errors end-to-end, don't flatten remediation" goal. Native child of #1619. |
| **#1914** | Umbrella: governed/gate ops must be no-op-stable (stop self-writes dirtying the tree) | OPEN | Charter status side-effects (#2007 bug #2 / #2009 neighbour) | The charter-status side-effect-free requirement (#2 neighbours) is one instance of this umbrella pattern. The resolver/read-path entry points must not self-write. Native child of #1619; pairs with the read-side adoption. *(Scope-judgement: fold the read-path/status-read no-op slice; leave the broader umbrella to its own track.)* |

## CROSS-REF — related; note in issue-matrix, out of scope for this mission

| Issue | Title | State | Relation | Why CROSS-REF not FOLD-IN |
|---|---|---|---|---|
| #2008 | [2007/C1] Command-surface validation & docs/prompt drift (bugs 1/5/9) | OPEN | Sibling #2007 cluster | Command-contract drift class — orthogonal to read-path/error-fidelity (synthesis Focus A, separate). |
| #2009 | [2007/C2] Charter status/sync/preflight consistency (bug 2) | OPEN | Sibling #2007 cluster | The charter-freshness track; #1914 covers the no-op-stable slice this mission may touch — the rest stays here. |
| #1890 | doctor coordination recommends nonexistent `agent worktree repair` | OPEN | #2007 bug 13 repair-UX tracker | Repair-command UX / command drift, not read-path resolution. |
| #1891 | agent `--json` output broken (`CommitResult not JSON serializable`; implement rejects --json) | OPEN | #2007 bug 16 JSON-contract tracker | JSON contract drift, adjacent but a distinct surface. |
| #1716 | Make coordination topology coherent from mission create through planning | OPEN | Write-side coord topology | Synthesis explicitly: write-side topology redesign is its own later focus (#1878), not this slice. |
| #1878 | Umbrella: complete the coordination placement/identity strangler (post-3.2.0) | OPEN | Write/entry-side strangler umbrella | Alphonso capstone: separate mission; only naming-resolver slices touch our seam. |
| #1666 | Epic: Execution-state & context domain-boundary redesign | OPEN | Parent of the prior context remediation | The grandparent epic; this mission is one increment of #1619/#1666 — reference, not a work item. |
| #1971 | Consolidate 3-way `locate_project_root` split-brain | OPEN | Project-root SSOT | Synthesis: related to #2011 but #2011 pins a *different* resolver (`resolve_canonical_root`); #1971 alone insufficient. Note as the root-resolver sibling. |
| #1993 | extract `resolve_lanes_dir()` pure seam | OPEN | Lanes-dir read surface | Binding sequencing note in #2007: must NOT land alone — pair with #1832 or carry minimal adoption. Flag as a co-dependency. |
| #1734 | in_review→approved guard blocks non-move-task surfaces, forces --force | OPEN | Status-transition guard, not read-path | Guard-surface gap; adjacent to status reads but a different defect. |
| #1862 | Implement gate analysis-freshness hashes tasks.md wholesale | OPEN | Implement-gate freshness, not read-path | Gate-hashing churn; surfaces in the implement loop but distinct. |
| #1827 | merge baseline circularity (re-run re-merges, fails identically) | OPEN | Baseline names it "re-test-first" | Merge-write durability, not read-path; #2007 says retest before folding. Out of scope per synthesis. |
| #1357 | lock-serialize CoordinationWorkspace.resolve() in BookkeepingTransaction | OPEN | Coord worktree creation race | Concurrency/topology mechanics → #1878. |
| #1947 | charter bundle validate fails on tracked provenance sidecars | OPEN | Charter-validate, not read-path | Charter bundle/provenance defect; #2009/#1914 family, distinct. |
| #1900 | Drain topology-ratchet C-002 allowlist | OPEN | Naming-ratchet | #1868 naming slice; pairs with #2000, not read-path. |
| #1832 | (baseline) implement claim 'no workspace could be resolved' | OPEN | Baseline | Already in scope — listed only to confirm it's the safest first-repro per #2007. |

## DEFER — genuinely later

| Issue | Title | State | Why defer |
|---|---|---|---|
| #1979 | WP can change shared source contract pinned by a test outside owned_files | OPEN | Ownership-policy / review-gate; matched on `SPECIFY_REPO_ROOT` keyword but unrelated to read-path. |
| #1057 | retire pre-3.0 status/task readers from active runtime | OPEN | Legacy reader cleanup — adjacent surface but a separate strangler tail. |
| #1231 / #1711 / #1782 | stale-WP indicator / frozen-worktree diagnostic / doctor mission-state --fix drift | OPEN | Worktree-liveness & repair diagnostics; #1666 children but not the read-path/error-fidelity grain. |

## CLOSED / claims-fixed — flag for verification (do NOT trust as fixed)

| Issue | Title | State | Flag |
|---|---|---|---|
| #1990 | fix: resolve spec.md from primary checkout in map-requirements (+ create_intent hint) | MERGED | The fix for #1981/#1982. Verify it routes through the resolver SSOT, not a local map-requirements patch that the mission then has to re-strangle. |
| #1982 | finalize-tasks --validate-only unhelpful error for planned-new-files | CLOSED | Closed by #1990; Debbie's #10 re-investigation says the *exit-1* survives via the overlap gate / validate-only frontmatter-snapshot — **the create_intent hint did not close the witnessed failure.** Re-test. |
| #1718 | scaffold declares coordination_branch but never materializes -coord worktree → StatusReadPathNotFound | CLOSED | The fail-closed condition Debbie names for #11/#1692. Cited as "evidence only" by #2007 but is the structural root of the surviving trigger. Verify materialization on HEAD. |
| #1991 | implement 'validate planning state' reads lanes.json from primary, finalize writes to coord | CLOSED | Coord/primary surface-mismatch class; #2007 lists as historical evidence. Re-test under coord topology (ties to #1993). |
| #1772 | merge silently skips code integration on coord-topology missions w/ .worktrees pollution | CLOSED | Write-side, but the same coord-surface-resolution disease. Evidence; do not reopen unless repro matches. |
| #1615 | Status readers bypass coord-aware read path, see stale main/lane state | CLOSED | #1666 child — the original "readers bypass the resolver" bug. The mission's whole premise is that this class is NON-ADOPTION; verify no new bypass crept back in (the bugs prove adoption is incomplete). |
| #1823 | analysis_report._charter_path doesn't use canonical-root resolver | CLOSED | A specific "didn't use the SSOT resolver" instance — exactly the adoption gap shape. Verify the fix is via the resolver. |

---

## Epic native sub-issue maps (for completeness — children not in baseline)

**#2007 children (all OPEN):** #1890, #1891, #2008, #2009, #2010, #2011 — all dispositioned above.

**#1619 children:** #1666 (epic), #1716, #1795, #1868 (epic), #1829, #1914 (FOLD-IN), #1911 (FOLD-IN); closed: #1684, #1796, #1885.

**#1868 children (naming/identity — all CLOSED except #1900):** #1898, #1899, #1906, #1918, #1978, #1983, #1949 (closed); #1900 (open). None read-path; the naming slice is a separate mission (see CROSS-REF #1900/#1971).

**#1666 children touching this surface — OPEN:** #1734, #1782, #1711, #1862, #1357, #1231, #1888, #1832; the large CLOSED set (#1615/#1672/#1673/#1726/#1735/#1770/#1771/#1816/#1824/#1823/#1860/#1884/#1889/#1692/#1991/#1814 …) is the prior remediation wave — high-value **claims-fixed corpus** to spot-check for regrown bypasses, since the live #2007 bugs prove adoption is incomplete.

## Surprises / flags for the operator

1. **Provenance discrepancy in the established docs.** The naming-SSOT overview (`00-OVERVIEW.md`) states #1888 "landed as #1886". On the tracker, **#1886 is a *different* issue** — "post-merge stale-assertion analyzer false-positives" (CLOSED) — not the ownership existence-check. #1888 (ownership `owned_files` existence) is still **OPEN**. Worth correcting the cross-reference before any verify-and-close work cites #1886.
2. **#1692 + #1884 + #1889 + #1981 are CLOSED but are the literal GitHub trackers for live #2007 bugs (#7, #8, #11-class).** This is exactly the "fix present, bug reproduces" trap Debbie's re-investigation hardened the rule against. Closed state here is misleading — these are the mission's core targets.
3. **#1666 is a large already-shipped context-remediation epic (≈30 closed children).** The mission's premise — "the SSOT exists, finish adoption" — is corroborated: this surface was strangled once and the closed corpus is the place new bypasses regrow. Treat as a regression-verification reservoir, not as "done."
4. **No NEW epic discovered** beyond the known #1619/#1666/#1868/#1878/#1716 cluster — the surface is already well-mapped; the net-new finds are point bugs / error-fidelity items, not a missed epic.
