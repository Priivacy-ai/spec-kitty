# Pre-Mission Research: Overlap & Sequencing Intelligence — P0 coord-topology / name-vs-authority slice
**Profile:** researcher-robbie (read-only) · **Date:** 2026-06-12
**Branch:** `feat/doctrine-glossary-consolidation-01KTNWFC` · **HEAD at research time:** `82d2524af`

**Inputs read:**
- `kitty-specs/coordination-merge-stabilization-01KTXRVR/` (spec, issue-matrix, research, tasks, mission-review-report, workflow-failures-log, retrospective)
- `kitty-specs/doctrine-glossary-architecture-consolidation-01KTNWFC/` (spec, issue-matrix)
- `docs/development/3-2-coord-merge-issue-hygiene-log.md`
- `work/convention-enforcement-scan-2026-06-12.md`
- `work/mission-prep-p0/research-authority-seams.md` (alphonso design doc — already exists)
- `work/TRIAGE_FINDINGS_BUGS_P0_P1.md`, `work/TICKET_OVERVIEW.md`, `work/EXECUTIVE_SUMMARY.md`
- `work/MISSION_01KTNWFC_COMPLETED-2026-06-12.md`
- Git log and source diffs for the already-committed convention-scan fixes on this branch

---

## CRITICAL STATE-OF-TREE NOTE (read first)

The **alphonso design doc** (`work/mission-prep-p0/research-authority-seams.md`) is already committed on this branch and directly names the mission scope. It identifies that:

1. **Cluster C in `surface_resolver.py:80`** — already fixed on this branch by commit `b7be1667b` ("fail closed on unresolvable coord mid8 (Cluster C)").
2. **Cluster D workflow.py:781** — already fixed on this branch by commit `2aecf9037` ("typed canonical-status gate + mission-scoped prompt temp paths").
3. **Cluster F (#1831 — temp-path slug threading)** — already fixed on this branch by commit `2aecf9037`.
4. **Cluster E (enum/literal sweep, refs #1881)** — already fixed on this branch by commits `1872f00e2`, `2e9ea962f`.
5. **Cluster D residual typed exceptions (refs #1880)** — fixed by commit `22d855300`.
6. **StructuredError base (refs #1893)** — fixed by commit `c53a4819c`.
7. **org-charter fold (refs #1894)** — fixed by commit `2e9ea962f`.

The **live residual** Cluster C work is NOT `surface_resolver.py` (done) but two un-scanned transaction-identity fabrication sites:
- `coordination/status_transition.py:265` — `_TransactionIdentity.effective_mid8` fabricates mid8
- `cli/commands/implement.py:395` — same fabrication idiom

These are in scope for the new mission (WP-C per alphonso's design). The alphonso doc provides the complete WP decomposition (WP-A topology, WP-B branch-identity, WP-C fail-closed transaction, WP-R3 #1889 deleted-branch row, WP-RATCHET). This research document focuses on the OVERLAP and SEQUENCING questions only.

---

## Section 1: Upstream Coord-Merge-Stabilization Mission (01KTXRVR) — Overlap Facts

### What it fixed and shipped

Mission 131 (`coordination-merge-stabilization-01KTXRVR`) landed as PR #1879 (squash commit `3f2af08f0`) on `upstream/main` on **2026-06-12**. All 5 WPs are `done`. It fixed:
- **#1826** (Class B: ref-advance without coord-worktree resync) — via `src/specify_cli/git/ref_advance.py` shared helper
- **#1861 Part 1** (Class C: validate-only checkout mutation) — `cli/commands/agent/mission.py:2462` guard
- **#1833 residuals** (Class D: husk fall-through) — `workspace/context.py:148`, `workflow.py`, `tasks.py`, new `doctor_husks.py`
- **#1814 residuals** (Class A: finalize residue) — `cli/commands/agent/mission.py:99-131`
- **#1736 residuals** (Class F: merge-driver hardening) — `lanes/merge.py` + `coordination/status_transition.py:399-400`
- **#1735 residuals** (Class A: coord-unaware retrospective reads) — `retrospective/gate.py:597`, `agent_retrospect.py:432`, AC10 ratchet
- **#1827** (baseline regression test)

**Files the mission owned** (now fully merged to upstream/main, no longer locked):
`git/ref_advance.py` (new), `lanes/merge.py`, `cli/commands/merge.py` (lines 993-998 via `advance_branch_ref`), `git/commit_helpers.py`, `cli/commands/agent/mission.py`, `cli/commands/agent/workflow.py`, `cli/commands/agent/tasks.py`, `workspace/context.py`, `cli/commands/doctor.py` (new husk check), `retrospective/gate.py`, `cli/commands/agent_retrospect.py`, `cli/commands/upgrade.py`.

### Overlap analysis: which scan-cluster surfaces does the new P0 mission touch that coord-merge-stabilization ALSO touched?

| New mission surface | Coord-merge-stabilization touched? | Collision type |
|---|---|---|
| `coordination/status_transition.py:114-125` (A5 — `_is_coord_worktree_feature_dir`) | **YES** — WP03/T016 touched `:399-400` (narrow except) | **DIFFERENT lines in same file.** A5 is a routing predicate (lines 114-125); T016 touched exception handling (lines 399-400). Both in the same file; functions are independent. No logical collision. Post-merge the file is owned by nobody — safe to edit. |
| `cli/commands/merge.py:1114` (B4 — legacy branch compose) | **YES** — WP03 touched `:993-998` (advance_branch_ref call) | **DIFFERENT functions in same file.** B4 is `_check_mission_branch` (L1104+); WP03 touched `_bake_mission_number_into_mission_branch` (L1006+). These are independent functions. No logical or semantic collision. |
| `coordination/status_transition.py:265` (C — fabricated mid8) | **YES** — WP03/T016 touched `:399-400` | **DIFFERENT lines, same file, third independent function.** No collision. |
| All other new mission surfaces | No | No collision |

**Conclusion:** The coord-merge-stabilization mission is fully merged and no longer "owns" any files. The two files that overlap (`status_transition.py`, `cli/commands/merge.py`) were each touched in DIFFERENT functions at non-adjacent lines. No semantic or functional conflict exists. The new mission's edits to these files are safe.

### Were the four P0 tickets filed BY the coord-merge-stabilization team as known residuals?

**Evidence from hygiene log and umbrella #1878:**
The coord-merge-stabilization filed umbrella issue #1878 ("complete the coordination placement/identity strangler") on 2026-06-12. The mission's retrospective explicitly names the "ff-merge treadmill," split-brain coord reads, and mid8 identity failures as items tracked in #1878. The alphonso design doc (`research-authority-seams.md`) was committed to this branch as Op evidence `68a31dcbe` on 2026-06-12 after the coord-merge-stabilization mission. Its §0 confirms `surface_resolver.py:80` was scanned as a Cluster C site but was already fixed by the time alphonso wrote the design.

**Key finding:** The **cluster-scan itself** was the vehicle for identifying the new P0 tickets. The mission-review risk findings (R1, R4) for coord-merge-stabilization were addressed in the post-merge remediation commit `9d3aec0a5` on PR #1879. The convention-enforcement scan (Op `01KTY6AN`, committed as `68a31dcbe`) was the analysis that identified Clusters A/B/C as NEXT-SLICE work. The alphonso design doc then mapped those into mission WPs and a decision table. The tickets #1883/#1884/#1885/#1889 referenced in the research scope do not appear in any local files; they are GitHub-only. **Based on the alphonso design doc's §5, #1889 is specifically the "declared-but-not-materialized coord topology" decision table (the R3 deleted-branch row).** The other ticket numbers (#1883-#1885) are most likely the GitHub issues filed for Clusters A, B, and C (transaction-identity sites) respectively, filed as part of the scan Op's ticket-to-file deliverables.

The coord-merge-stabilization team DID generate the evidence that surfaces these tickets (the retrospective, workflow-failures-log, and scan adjudication), but the specific tickets #1883/#1884/#1885/#1889 appear to have been filed AFTER that mission's merge, not as pre-mission known residuals in its issue-matrix. The issue-matrix for coord-merge-stabilization (17 rows) contains none of these numbers.

---

## Section 2: #1844 (Release Pipeline P0) — Verdict

**Finding:** #1844 does not appear in any local file, git log, or CI workflow in the repo. No local evidence exists to characterize its scope. Based on the CLAUDE.md note about `spec-kitty-saas` and the CI quality workflow structure, #1844 is likely a standalone CI or release-pipeline fix. Based on the convention-enforcement scan architecture adjudication (§Q3), which recommends the name-vs-authority slice land BEFORE #1802 and #1804 but makes no mention of release pipeline fixes, a release-pipeline issue would be **orthogonal** to the coord-topology/name-vs-authority mission scope.

**Recommendation: OUT — pending verification of ticket content.** If #1844 is a CI/release pipeline defect (e.g., a flaky test, a broken release workflow step, or a version mismatch), it belongs in a standalone fix commit or its own WP in a CI-hardening mission — not bundled into a mission whose scope is name-vs-authority topology correctness. The two concerns are architecturally independent (topology/identity authority vs. release mechanics). Bundling would inflate scope and make the mission harder to review. If #1844 turns out to be related to mis-routed mid8 identity in CI workflows (e.g., a CI step that builds the wrong branch because `cli/commands/merge.py:1114` composes a legacy branch name), then it becomes **evidence for B4** and its fix is the B4 migration — in which case the ticket should REFERENCE the mission rather than be a standalone scope item. Recommend verifying the ticket content before including in the issue-matrix.

---

## Section 3: Ticket Census for the Issue-Matrix

### Already-fixed on this branch (via post-scan Op commits)

These issues were addressed by commits already on `feat/doctrine-glossary-consolidation-01KTNWFC` (the draft PR #1895 branch) AFTER the convention-enforcement scan, before any new mission spec. They land when PR #1895 merges.

| Ticket | Fix commit | What it closed | Issue-matrix recommendation |
|---|---|---|---|
| #1831 | `2aecf9037` (Cluster F: mission-scoped temp paths) | Cross-mission WP01 collision in `/tmp` prompt files | **EXCLUDE** — verified-already-fixed on branch; cite commit in matrix |
| #1880 | `22d855300` (Cluster D residual: typed exceptions for worktree preflight/validator/dashboard) | 3 of 4 Cluster D residual error-substring control-flow sites | **EXCLUDE** — verified-already-fixed on branch |
| #1881 | `1872f00e2` + `b26fd7a93` (Cluster E: enum/constant sweep) | Raw Lane/DecisionKind/mission-type literals | **EXCLUDE** — verified-already-fixed on branch |
| #1893 | `c53a4819c` (StructuredError base) | Error-code family foundation for typed exceptions | **EXCLUDE** — verified-already-fixed on branch |
| #1894 | `2e9ea962f` (org-charter fold) | Triple merge-fold collapse | **EXCLUDE** — verified-already-fixed on branch |

**Recommendation on already-fixed set:** Include ALL FIVE as `verified-already-fixed` rows in the new mission's issue-matrix (cite both the commit SHA and the PR #1895 where they land). This documents completeness and prevents re-opening. Do NOT include them in the WP scope.

### P0 candidates for the new mission

| Ticket | Description inferred | Scan cluster | Recommend in/out | Rationale |
|---|---|---|---|---|
| **#1883** | Topology predicate split-brain (Cluster A: 5 sites classify worktrees from path shape without registry cross-check) | A | **IN — P0** | CRITICAL per scan ranking; write-contract mis-routing; would have prevented #1589/#1821 split-brain. alphonso WP-A scope. |
| **#1884** | Legacy-shape-only parsers blind to mid8-era names (Cluster B: 7 sites) | B | **IN — P0** | HIGH per scan; silent signal loss on ALL modern missions; would have prevented mid8='' regression. alphonso WP-B scope. |
| **#1885** | Fabricated mid8 transaction identity (Cluster C residual: `status_transition.py:265`, `implement.py:395`) | C | **IN — P0** | HIGH; live fabrication in two additional sites post-scan-correction; `status_transition.py:265` is a direct transaction-directory-naming defect. alphonso WP-C scope. |
| **#1889** | Declared-but-not-materialized coord topology: missing R3 "branch deleted" row in surface resolver | C-adjacent / #1848 carve-out | **IN — P0** | alphonso §5 explicitly defines this decision table; WP-R3 is a named WP in the design doc; the deleted-coord-branch fail-closed signal is currently absent. |

### Scan-slice items (fold cluster)

| Ticket | Description inferred | Recommendation | Rationale |
|---|---|---|---|
| **#1868** (if seams epic) | Likely the "name-vs-authority remediation" epic created to track Clusters A/B/C — NOT a functional defect ticket. Verify: if it is the parent epic for #1883-#1885, include as a `deferred-with-followup` umbrella row (the mission closes children, epic stays open for future slices). If #1868 does not exist or is something else entirely, exclude. | **VERIFY then fold as epic row** | Cannot confirm from local files; ticket number does not appear in any repo artifact |
| **#1865** | Cluster E remainder (DecisionKind enum promotion — the one design item in the literal sweep not covered by #1881 commits; those commits swept the mechanical literals but left `DecisionKind` as a non-enum per alphonso "(c) Tickets to file" note) | **OUT — TICKET-ONLY per scan adjudication** | alphonso ranked E "TICKET-ONLY"; the mechanical literal sweep is already done (#1881). Only the `DecisionKind`→`Enum` promotion remains. That is a design step, not a topology/identity seam. Include in issue-matrix as `deferred-with-followup` pointing to the ticket. |
| **#1866** | Cluster E subbucket (likely Lane/mission-type literals NOT covered by #1881 commits, or the second batch of enum debt) | **OUT — TICKET-ONLY** | Same rationale as #1865. |
| **#1867** | Likely Cluster G read-path accepted-debt (store.py:122 `_find_mission_specs_root`) or Cluster D residual worktree.py:332 | **OUT — ACCEPTED DEBT or TICKET-ONLY** | If G read-path: alphonso explicitly ACCEPTED; document in matrix as `deferred-with-followup`. If D residual: same reasoning. |
| **#1863** | Cluster D residual remainder: worktree.py:332 marker tuple, mission_loader/validator "has no steps" exception hierarchy | **OUT — TICKET-ONLY** | Not in-slice per scan adjudication; typed-exception design work, no topology/identity authority. Include as `deferred-with-followup`. |

### P1 loop-killers

| Ticket | Description | Recommend in/out | Rationale |
|---|---|---|---|
| **#1860** | "handle-as-path" class — mentioned in scan Cluster B as "would have prevented #1860"; an incident caused by Cluster B's bespoke regex returning wrong slug | **OUT — already-evidence for B4** | #1860 is the incident, not the defect. Include as evidence ref in the B4 WP task, not as a standalone issue-matrix row. Closure is implicit when B4 lands. |
| **#1862** | Unknown — not referenced in any local file | **UNKNOWN — verify before including** | Cannot determine scope from repo artifacts. If it is a P1 loop-killer caused by Cluster A/B, include as evidence. If standalone, exclude. |

---

## Section 4: Sequencing — Landing Shape Recommendation

**Current state:** `feat/doctrine-glossary-consolidation-01KTNWFC` is the working branch for draft PR #1895, which contains 121 commits ahead of `upstream/main`. This includes the complete doctrine-glossary mission (01KTNWFC, 10 WPs all done), plus 6 post-merge convention-scan fix commits (Clusters C, D partial, E, F, StructuredError base, org-charter fold).

**The new coord-topology/name-vs-authority mission (P0 set: #1883/#1884/#1885/#1889) is designed to run ON this branch**, per its constraint C-001 ("work plans, implements, and merges on this branch"). This means the new mission's WPs will ADD commits to `feat/doctrine-glossary-consolidation-01KTNWFC`, growing PR #1895 further.

**Recommended landing shape:** Keep the new mission on `feat/doctrine-glossary-consolidation-01KTNWFC` as a single stacked PR (#1895 grows; draft stays draft until the new mission is accepted and merged). Do NOT split into PR-2: the convention-scan fixes already on the branch are logically upstream of the new mission (the scan fixed C/D/E/F; the new mission fixes A/B/C-residual — they are one continuous remediation arc). Splitting creates a rebase dependency chain and coordination overhead with no clarity benefit. The branch is well-named as a "consolidation" branch and has precedent for receiving multiple mission deliverables. The PR description should be updated after the new mission accepts to enumerate both the doctrine-glossary deliverables and the coord-topology/name-vs-authority fixes as separate sections.

**One precondition to verify:** The coord-merge-stabilization (PR #1879) landed on `upstream/main` but this branch has NOT been rebased onto `upstream/main` since then. The new mission commits must follow a rebase of this branch onto `upstream/main` (to include the coord-merge-stabilization fixes as the base they build upon). The alphonso doc §0 confirms the scan was taken at "upstream/main + 01KTNWFC" but the coord-merge-stab was committed to upstream/main AFTER the scan. A rebase is required before any new WP implementation to avoid redundant fixes or semantic conflicts with the coord-merge-stab code.

---

## Overlap Facts Table (compact)

| Surface | Coord-merge-stab touched? | Lines | New mission scope | Collision? |
|---|---|---|---|---|
| `coordination/status_transition.py` | YES (WP03 T016) | :399-400 | A5 (:114-125), C (:265) | NO — independent functions |
| `cli/commands/merge.py` | YES (WP03 T012) | :993-998 | B4 (:1114) | NO — independent functions |
| `workspace/context.py` | YES (WP04 T019) | :148-150 | None | No overlap |
| `cli/commands/agent/workflow.py` | YES (WP04 T020) | :2237-2265 | None | No overlap |
| `cli/commands/doctor.py` | YES (WP04 T022) | new husk check | None | No overlap |
| `retrospective/gate.py` | YES (WP05 T024) | :597 | None | No overlap |
| `coordination/surface_resolver.py` | NO | — | A1 (via helper), C-done (fixed on branch) | Clean — already-fixed C site is done |

**Overall:** zero functional collisions with coord-merge-stabilization. All overlap sites are in already-merged code at different line ranges.

---

## Summary (≤12 lines)

The coord-merge-stabilization mission (131, PR #1879) is fully merged to upstream/main; its 5 WPs fixed #1826/#1861-P1/husks/#1814/#1736 and are no longer in-flight. No file it touched is functionally locked — two files (`status_transition.py`, `cli/commands/merge.py`) overlap with the new mission but at independent, non-adjacent function ranges. The alphonso design doc (`work/mission-prep-p0/research-authority-seams.md`) already defines the full mission WP decomposition (WP-A topology, WP-B branch-identity, WP-C transaction-identity, WP-R3 #1889 deleted-branch, WP-RATCHET). Clusters C, D, E, F are already fixed on this branch via post-scan Op commits (#1831/#1880/#1881/#1893/#1894); include all five as `verified-already-fixed` rows in the issue-matrix. The issue-matrix should include #1883/#1884/#1885/#1889 as P0 in-scope rows; #1863/#1865/#1866/#1867 as `deferred-with-followup` (TICKET-ONLY per scan adjudication); #1868 pending verification (epic row if it exists). #1844 (release pipeline) should be OUT — it is orthogonal to topology/identity authority unless its root cause is a B4-class branch-name mis-compose. #1860 is incident evidence for B4, not a standalone matrix row. The cleanest landing shape is to keep the new mission on `feat/doctrine-glossary-consolidation-01KTNWFC` (PR #1895 grows; draft stays draft), preceded by a rebase onto `upstream/main` to include coord-merge-stab as the base.
