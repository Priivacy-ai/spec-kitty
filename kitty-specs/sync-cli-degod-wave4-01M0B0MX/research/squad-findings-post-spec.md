# Post-spec adversarial squad — convergent findings

Point-cut: post-spec. Three profile-loaded, read-only lenses (architect-alphonso, reviewer-renata,
planner-priti). All three verdicts: **spec spine is sound** (golden-first hard-wired, boundary/
two-authority/ratchet invariants faithful, 6,332 LOC / 3× C901 / 22 commands ground-truthed) —
tighten these gaps before planning. All folded into spec.md.

| # | Sev | Lens | Finding | Disposition |
|---|-----|------|---------|-------------|
| P-1 | HIGH | priti | Grounding brief not persisted (was in session scratchpad, invisible to repo). | **DONE** — persisted to `research/mission-brief.md`. |
| A-1 | HIGH | architect | C-005 husk re-export is **necessary, not sufficient** for the 60 patch-tests: a relocated core that binds a patched private via its own local import escapes `monkeypatch` on the husk name → test silently no-ops. | **FOLDED** — C-005 gains caller-side binding discipline (patched callees reached through the shell / port-injected); the 60 patch-tests named as an explicit **co-gate** alongside the golden test (NFR-001, new AS). |
| R-1 | HIGH | renata | FR-001 golden test fakeable — the GAPs (`workspace`, `status` full human-render cc-90, `doctor` branches, `diagnose --json`) are *render branches*, not subcommands; `--json`-only freeze satisfies the literal bar. | **FOLDED** — FR-001 + US1-AS4: each of {status, doctor, workspace} needs a non-`--json` human-render snapshot AND every `--json` branch frozen *before* that function's extraction. |
| R-2 | HIGH | renata (architect confirms no guard) | FR-004 two-authority invariant verifiable only "from the diff" — a unified `SyncAuthority` passes golden + census and ships the #2160-class regression. | **FOLDED** — FR-004 backed by a new arch-test asserting distinct read-port/write-port symbols, no shared authority class (US2-AS2). |
| R-3 | HIGH | renata | FR-007 env-census has no acceptance scenario / no anti-deletion proof. | **FOLDED** — FR-007 gains a named census-artifact path + a grep guard that the **set** of `SPEC_KITTY_*` refs on the sync surface is unchanged (proof of "deleted none"). |
| A-2/Pr-1 | MED | architect + priti | `primary_feature_dir_for_mission` avoidance demoted to Assumption; no arch-gate guards it (discipline-only). | **FOLDED** — promoted to fail-closed **C-006**. |
| A-3 | MED | architect | #862 status→sync / dossier→sync directional-import rule absent from C-001; two dedicated gates enforce it and placement-option-2 enlarges their frozen surface. | **FOLDED** — C-001 gains the no-new-`status`/`dossier`→sync-edge rule; NFR-004 names both boundary tests. |
| Pr-2 | MED | priti | C-004 "daemon semantics frozen" collides with the mandate to split `sync_workspace`. | **FOLDED** — reworded: reuse/kill/lifecycle **behavior** frozen; daemon-owner read/guard code may relocate intact (pinned by the golden test). |
| Pr-3 | MED | priti | walker.py has zero deps on the golden test/ports/husk; coupling the 2h win behind the refactor is wrong. | **FOLDED** — FR-005/US3 clarified: walker ships as a **standalone campsite slice that lands first**, independent of the degod. |
| Pr-4 | MED | priti | Filing the deferred follow-on is prose-only, not a deliverable. | **FOLDED** — new **FR-008**: file the tracked follow-on issue(s) (adapter-consolidation WS4/WS6-gated + census retirement-candidates). |
| Pr-5 | HIGH→adjusted | priti | Tracker parent #1797 vs #1619. | **RECONCILED** — the roadmap frame names #1797 as "degod/unshim DELIVERY (where god-objects are extracted)" with #1619 the grandparent; spec now references the frame (child of the degod-delivery epic #1797, advancing #1619) rather than asserting one parent. |
| R-4 | MED | renata | NFR-002 "no **blanket** suppressions" leaves a per-line re-suppression loophole. | **FOLDED** — "zero net-new `C901`/`S3776` suppressions anywhere on the sync surface"; net noqa count pinned; existing justified `BLE001`/`S105`/`S608`/`PLC0415` **preserved** (brief invariant I). |
| R-5 | MED | renata | NFR-003 "strictly decreases" gameable + self-reported Sonar. | **FOLDED** — bound to the FR-006 rule *classes* (zero remaining live `S3358`/`S1192` on changed sync functions); before/after Sonar issue list committed as an artifact. |
| R-6 | MED | renata | Spec omits brief-invariant-I: "malformed suppression" fix must correct the format, never delete the guarded `except`. | **FOLDED** — into FR-006. |
| A-4 | LOW | architect | "ambiguity → typed error" half dropped (correctly — adding raises = behavior change) but the tension is silent. | **FOLDED** — new **C-007** states the subordination to SC-004 zero-behavior-change explicitly. |
| R-7 | LOW | renata | SC-001 "god-module threshold"/"thin shell" unmeasurable; FR-006 doesn't name rule IDs. | **FOLDED** — SC-001 pins "thin shell = parse→open ports→call core→render, no decision logic" + a per-module ceiling; FR-006 names `S3358`/`S1192`/`S7632`. |
| A-5 | LOW | architect | NFR-004 baseline re-pin vs upstream/main + DIR-013 (open an issue if merge-base is pre-existing-red). | **NOTED** — plan-phase note (Edge Cases already carries the re-pin rule). |

No contested finding dropped (adversarial-evidence contract). None blocked planning; all are completeness/non-fakeability tightenings.
