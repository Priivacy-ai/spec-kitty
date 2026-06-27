# Approach Trace — implement-loop-coord-authority-completion-01KW2E7A

**Purpose:** a running log of the METHODOLOGY used to plan + run this mission — the
front-loaded research squads, the adversarial point-cuts, and WP sizing — so we can
assess afterward whether the approach paid off (squad ROI, sizing realism, front-loading
vs discovery-during-implement). Direct successor to the
`single-authority-topology-cleanup-01KVRJ6P` approach trace (same epic family, #2160/#1716).

---

## Seeded during spec (2026-06-26)

### Front-loaded research (pre-spec, 5 agents)
Two parallel squads ran BEFORE the spec was authored:
- **Research squad (3):** architect-alphonso (post-Phase-1 topology map),
  debugger-debbie (live verification of #2115/#2140 claims), planner-priti (tracker
  cluster + scope boundary). Carved the one-mission-vs-two decision (one) and the
  CLAIM/REFERENCE issue split.
- **Campsite squad (2):** paula-patterns (#1931 domain-matching fold scope),
  randy-reducer (#2183 gate mechanics + dead-symbol).
- ROI so far: surfaced the **invisible 7th residual** (`merge/done_bookkeeping.py`),
  proved **#2140 already-fixed** (turned a "fix" into a "close-with-pin"), and gave the
  exact #2183 floor mechanics. Synthesis: `scratchpad/SYNTHESIS-preplanning.md`.

### Adversarial squads across the cadence
| Point-cut | Squad | Outcome |
|-----------|-------|---------|
| pre-spec | alphonso + debbie + priti + paula + randy | one-mission scope; CLAIM #2115/#2140/#2183; #2140 already-fixed; 7th residual; #2183 mechanics |
| **post-spec** | **alphonso + debbie + renata + paula** | **4-5× undersizing CONFIRMED** — see below |
| post-plan | _(scheduled — brownfield: foldable-issue / split-brain / deprecation)_ | _(pending)_ |
| post-tasks | _(scheduled — anti-laziness on the WP decomposition)_ | _(pending)_ |
| pre-merge | _(scheduled — full-gate dry-run on merged branch, NFR-005)_ | _(pending)_ |

### Post-spec squad — the high-ROI catch (2026-06-26)
The tight 7-residual spec was a **false close**. The squad (operator-verified the 3
top-leverage claims directly) found:
- The dir-read ratchet **scanner is blind to inline `resolver()/"tasks"`** → the census
  it reported was vacuous → SC-002 would go green over real residuals.
- **2 more cli residuals** (`list_tasks`, `_find_first_for_review_wp`) + a **whole
  `workspace/context.py` cluster** the scan never covered.
- **Stale floor math** (floor=27 but live already=31; post-fix >35).
- **Mixed-read trap** (one `feature_dir` → tasks/ + status events; naive swap re-opens
  #2155) and **write-surface co-move** risk (review-cycle artifacts).
- **10 fakeable DoDs** (resolver-stubbing, var-rename trap, vacuous shrink, tautological
  pin, weak dry-run).
- Verdict acted on: spec revised (4→~6 lanes), operator chose absorb workspace cluster +
  whole-`src` scan. Synthesis: `scratchpad/SQUAD-postspec-synthesis.md`. **This is the
  squad-catches-undersizing pattern repeating (the standing-order rationale, proven again).**

### Squad discipline applied
Bounded (≤5 pre-spec, 4 post-spec), profile-LOADED (read the `.agent.yaml`), structured
output, model discipline (opus for analytical/adversarial lenses, sonnet for
tracker/mechanical), second-opinion-on-divergence ready. Read-only.

## During / after implement — APPEND BELOW
<!-- Assess: did the front-loaded squads reduce implement churn, or did the FR-008
     plan-time residual-discovery sweep surface yet more (a 7th undersizing)? which squad
     gave the highest ROI? did WP sizing hold (any WP blow past ~10 subtasks / need
     re-split — note the WP-ID append-scheme friction from the sibling mission)? did the
     post-spec revision prevent a re-opened-epic, or was it still under-scoped? -->

_(append during/after implement)_

### During implement (2026-06-27) — cross-base verification caught a mislabeled regression
- WP05's implementer flagged 2 test failures as "pre-existing." Per the failing-test-remediation standing order I verified via a clean `upstream/main` worktree (NOT trusting the label): `test_routed_files_import_the_seam` genuinely pre-existing (fails at baseline; orchestrator_api resolve_mid8, unrelated). BUT `test_map_and_finalize_agree_on_coord_topology` (#2064) PASSED at baseline → our mission BROKE it. WP03's correct routing of `_map_requirements_feature_dir`→PRIMARY obsoleted #2064's coord-agreement invariant (itself already stale post-#2106). Adjudicated STALE-TEST → re-pinned to #2115 authority (dc44127b: map resolves PRIMARY, diverges from finalize's coord seam; separate fixture preserves the divergence sibling test). Lesson reaffirmed: an implementer's "pre-existing" label is a hypothesis, not a fact — cross-base diff is the arbiter; the squad/loop's broad-sanity `-k` filters can miss a cross-mission test, so verify at the clean base.
