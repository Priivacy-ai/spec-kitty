# Implementation Plan: CI Pipeline Reinstatement

**Branch**: `feat/ci-pipeline-reinstatement` | **Date**: 2026-09-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/ci-pipeline-reinstatement-01M1X35E/spec.md` (commit 41ad507)

## Summary

Rebuild the repo's CI from the post-Convergence husk as a lean, full-tree-modular, path-scoped,
artefact-sharing set of GitHub Actions workflows on **stock runners**, giving the test suite a public
CI home again (today the whole `tests/` suite is skipped on the public tree, and — crucially — the
EXPERIMENTAL Blacksmith producer is **archived/inert**, so the reinstated CI is the *sole/primary*
producer). Restore SonarCloud scanning (nightly first) and add a separate packs workflow. Two paramount
operator directives are **machine-enforced acceptance gates**: P1 (no dead-code tests in CI; the
dead-code census is the authorizing oracle; enforcement allowlists stay always-on) and P2 (low-ROI
shape guards demoted off the blocking gate). Two run modes: PR = fail-fast churn-guard; nightly/manual
"run full" = run-all-regardless for full-spectrum remediation signal. Every workflow is manually
dispatchable.

**Delivery strategy: full-tree modularization, delivered in three phased WP clusters gated by hard
cluster gates** — `FOUNDATION → TOPOLOGY → LEAN-SUITE` — so the ~40-workflow surface lands in gated
stages, not one big-bang. **The retirement scrub (P1, FR-013) is sequenced into FOUNDATION, before the
`--durations` shard-freeze in TOPOLOGY** (post-spec squad correction: scrub → durations → freeze, never
scrub-last).

## Technical Context

**Language/Version**: GitHub Actions workflow YAML; Bash 5 (CI glue); Python 3.11+ (the suite under CI
and the in-repo CI-config gates/oracles). **Primary Dependencies**: GitHub Actions (stock runners
`ubuntu-latest`/`windows-latest`), `dorny/paths-filter` (change router), `pytest` + `pytest-cov` +
`diff-cover` + `pytest-xdist`, `SonarSource/sonarqube-scan-action` + `sonarqube-quality-gate-action`,
`uv` (env resolution). **All third-party actions pinned to a full commit SHA** (supply-chain, DIR-051).
**Storage**: N/A — ephemeral CI artefacts only (coverage `coverage-<tier>-<module>.xml`, xunit XML,
warmed-env cache keyed by lockfile + pinned events rev). **Testing**: the reinstated CI runs the repo's
`pytest` suite (sharded); the mission's *own* correctness is gated by in-repo tests —
`tests/release/test_release_ci_ownership.py` (governance map), the rebuilt CI-integrity oracle
(`tests/architectural/`), and new planted-regression/planted-orphan negative tests. **Target Platform**:
GitHub Actions on the spec-kitty repository (current target). **Project Type**: single (CI/tooling
infrastructure for a Python CLI monorepo). **Performance Goals**: PR blocking path ≤15 min;
`integration-tests-next` ≤7 min; inter-shard skew ≤20%; docs-only & packs-only PR = 0 code shards
(validated against a recorded baseline run, not asserted). **Constraints**: stock runners only; no
`SK_CI_TOKEN` on public jobs; fork-safe advisory degradation on missing secrets; charter pinned-rev for
PR-mode deps; P1/P2 machine-enforced; governance-map lockstep. **Scale/Scope**: ~40 reusable
`module-*.yml` (phased) + router + shift-left front + aggregation/gates + Sonar WF + packs WF (2 lanes)
over ~2568 test files; 7 claimed tickets (#3189 downgraded to linked follow-up).

## Constitution Check (Charter)

*GATE: must pass before Phase 0 and re-check after Phase 1. Charter = `.kittify/charter/charter.md`
(binding). Note: the doctrine resolver reports directives 001–050 "unavailable" (pre-existing CLI/graph
skew); the charter.md bodies + `packs/built-in/` are the authority used here.*

| Charter rule | Applies | Plan compliance |
|---|---|---|
| **ATDD-first (C-011, binding)** | every impl WP | Each WP commits a failing-first ATDD test as a **separate first commit** before implementation; reviewer verifies red-on-base→green-on-final. The CI-config WPs pin behavior via `tests/release/` + `tests/architectural/` tests. |
| **Non-vacuous arch gates (SO#5 / DIR-043)** | P1/P2, integrity oracle | The P1 census-oracle, the CI-integrity oracle rebuild, and the governance-map test all carry a concrete floor + self-mutation/planted-regression negative test; no gate may pass while evaluating nothing. |
| **Red-main discipline (SO#9) + Pre-existing-Failure-Reporting** | base-red triage | #3284 already filed; the 23 reds are census-authorized drop-or-fix (SC-008), never green-washed, never a third "leave-red" disposition. |
| **Canonical sources (SO#6)** | all | Reuse `dorny/paths-filter`, `SonarSource/*` actions, the existing ownership-test + shard-map substrate; extend rather than fork; file upstream gaps (e.g. the doctrine-resolver skew) rather than improvise. |
| **Campsite tidy-first (SO#2) + change-scope reconciliation** | every WP | Each WP campsite-cleans the surfaces it touches (behavior-preserving, distinct preceding step) before the functional change; smallest-viable-diff → boy-scout-inside-fileset → locality brake. |
| **Reviewer ≠ implementer (SO#8)** | implement loop | Distinct agents; issue-matrix rows + claims already recorded. |
| **Git/workflow (SO#7, binding)** | wrap-up | `spec-kitty merge` → local main only; then `issue-<n>-<slug>` branch → **draft PR to upstream → hand off**; agents never merge the mainline; PR-touching agents worktree-isolated. |
| **Shared-package pinned-rev (Architecture)** | warmup | PR-mode resolves a **pinned** `spec_kitty_events` rev (no moving branch ref); latest-mainline only in nightly/full (operator decision B). |
| **Terminology canon (Mission not feature)** | all | Enforced; the reinstated terminology guard is itself an always-on gate. |
| **Supply-chain install safety (DIR-051)** | dependency adds | All actions SHA-pinned; deny-by-default lifecycle scripts; registry authenticity + freshness recorded in `research.md`. |

**Verdict:** no charter violations; no Complexity-Tracking entries required. The full-tree
scope is the operator's explicit choice, reconciled to the ROI concern via hard cluster gates (below).

## Project Structure

### Documentation (this mission)

```
kitty-specs/ci-pipeline-reinstatement-01M1X35E/
├── plan.md              # this file
├── research.md          # Phase 0 — decisions + adversarial/supply-chain evidence
├── data-model.md        # Phase 1 — config "entities": map schema, artefact contract, census, routing model
├── quickstart.md        # Phase 1 — run/dispatch/interpret-modes locally
├── contracts/           # Phase 1 (4 files) — governance-map-schema · p1-census-oracle (census+integrity+gate-selection-authority) · artefact-naming · router-two-authority
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root — surfaces this mission changes)

```
.github/
├── workflows/                       # the reinstated pipeline (net-new + de-deferred)
│   ├── ci-router.yml                #   change router (dorny) + shift-left front (F/T)
│   ├── module-tests.yml (+tiers)    #   reusable shards: MATRIX over the committed module registry (bounded set, ≤20/caller — not ~40 files)
│   ├── ci-aggregate.yml             #   coverage/xunit aggregation + diff-cover PR gate + quality-gate
│   ├── sonar.yml                    #   net-new Sonar scan (nightly/dispatch)
│   ├── packs.yml                    #   built-in + internal lanes
│   ├── ci-nightly.yml               #   full-mode: run-all + performance/e2e + interpreter matrix
│   └── ci.yml                       #   dead EXPERIMENTAL producer → neutralized/retired (F)
├── actions/                         # composite actions (warmup/env, artefact-collect) if extracted
docs/convergence/interim-ci-producer.md   # governance verdict map (+ `introduced` disposition)
tests/release/test_release_ci_ownership.py# map enforcer (extended for `introduced`)
tests/architectural/                      # CI-integrity oracle (non-vacuous), census oracle, planted-regression/-orphan negatives, path-filter two-authority
sonar-project.properties                  # Sonar config (verify identity before wiring)
Makefile / pytest.ini                     # test tiers + markers (shard registry, marker demotions)
packs/{built-in,internal}/                # packs WF subjects
```

**Structure Decision**: single-project CI/tooling. The pipeline is a set of cooperating workflows with
a reusable-`workflow_call` module layer; the mission's own correctness lives in `tests/release/` +
`tests/architectural/` (config gates + oracles), not in a new runtime package.

## Cluster Phasing & Parallel Work Analysis

### Dependency graph (cluster-gated)

```
FOUNDATION  ──(hard cluster gate: base-green + deterministic warmup + census oracle live
                + live-src scrub complete + gov schema + ci.yml retired)──►
TOPOLOGY    ──(hard cluster gate: full pipeline green on a real PR + wallclock targets
                + artefact-sharing + dual-mode verified)──►
LEAN-SUITE  ──(hard cluster gate: P1 negative tests fire + P2 demotion + non-vacuous integrity oracle)
```

**Why this order (post-spec squad correction):** the P1 retirement scrub (FR-013) and fix-before-wiring
(FR-015) re-derive the *live* test-selection basis; the `--durations` shard-freeze (NFR-005) must run on
that scrubbed basis — so scrub sits in FOUNDATION, freeze in TOPOLOGY. Doing scrub last (grounding §10)
would force a re-freeze loop.

### FOUNDATION cluster (~5 WPs) — sequential-ish; unblocks everything
- **F1 — Governance-map `introduced` disposition** (FR-012/C-001): extend `interim-ci-producer.md`
  schema + `test_release_ci_ownership.py` with an `introduced` set/vocabulary so net-new workflows are
  representable. *Unblocks every net-new-workflow WP.*
- **F2 — Base-red triage + dead-code census oracle** (FR-002/#3284; C-006): stand up the dead-code
  census as an in-repo **machine oracle**; classify the 23 reds census-authorized drop vs live-fix; base
  goes green (SC-008, no leave-red). *The P1 authority every scrub/exclusion depends on.*
- **F3 — Warmup / bootstrap** (FR-003/#3283): shared warmup composite (pinned-PR / latest-nightly),
  cached env artefact, kills the venv-lock cascade.
- **F4 — Dead-`ci.yml` neutralization** (FR-017/C-010): retire the archived-EXPERIMENTAL producer in
  lockstep with `test_private_factory_ci_is_scoped_to_experimental_repo`. *Decoupled, early.*
- **F5 — Clean test basis** (FR-013 scrub + FR-015 fix-before-wiring): re-derive dorny groups + `--cov`
  targets against live `src/**`; drop dead-code-test dirs (census-authorized); re-validate the ~5
  strict-xfail landmines + fix the 2 env-leakers **before** they can enter a gated shard.

### TOPOLOGY cluster (~7 WPs) — parallelizable after the cluster gate
- **T1 — Path router + shift-left front + gate-selection authority** (FR-004/005/008/016; NFR-002): dorny
  two-authority router, fail-closed unmatched→run-all, cheapest-first ladder, fast always-on gates split
  from the code-scoped heavy arch battery; build the **single importable gate-selection authority that
  parses the two routing authorities** (one source, not a re-encode) — reused later by L3, not a second parser.
- **T2 — Shard freeze + module matrix** (FR-006/008; NFR-001/005): `--durations` measured run on the
  **scrubbed** basis → committed **module registry** (module → roots, `--cov`, tier, shard_count; skew ≤20%);
  per-module shards realized as a **matrix over the registry inside a bounded set of reusable workflows**
  (≤ GitHub's 20-reusable-workflows-per-caller ceiling — NOT ~40 separate files); de-serialize
  `integration-tests-next` + arch pole. *(Split in tasks: registry+freeze vs matrix-workflow authoring.)*
- **T3 — Artefact contract + aggregation + diff-cover gate** (FR-007/009; C-005; NFR-003).
- **T4 — Dual-mode + dispatch + merge-eligibility** (FR-018/019; NFR-008; SC-009/010): PR fail-fast vs
  full run-all; `workflow_dispatch` everywhere; skipped≠pass realized via `if: always()` on the terminal
  gate + a required-check set that treats short-circuit-skipped distinctly (evidenced by a dispatched run,
  since it is host behavior).
- **T5 — Sonar workflow** (FR-010/C-008; net-new via F1): aggregate coverage → scan; nightly/dispatch;
  fork-safe skip; verify project identity before wiring.
- **T6 — Nightly full-mode: expensive cadence + interpreter lane** (FR-020/021; SC-011): perf/e2e +
  above-3.12 lane off the PR path; mis-marked-performance guard (#3665).
- **T7 — Packs workflow** (FR-011): built-in + internal lanes, `packs/**` trigger independence, corpus
  exit-5 floor.

### LEAN-SUITE cluster (~3 WPs) — hygiene on the live pipeline
- **L1 — P1 machine proofs** (FR-013/C-006/SC-005): planted dead-code-shard / retired-import negative
  test proving the exclusion gate fires + enforcement-allowlist preservation test.
- **L2 — P2 shape-guard demotion** (FR-014/C-007/NFR-007; #3458): golden-count/compat-export/
  marker-baseline/twelve-agent-byte-grid → derive-from-source or off the blocking gate; committed
  membership list.
- **L3 — CI-integrity oracle non-vacuity + gate-selection authority** (FR-016/SC-004; #2967, #2476):
  rebuild the collection oracle against real on-disk YAML with a non-vacuity floor + planted-orphan
  negative; single importable gate-selection authority reused by CI + local pre-PR parity.

### Coordination
- **Cluster gates are hard**: a cluster's exit gate must be green before the next cluster's WPs claim.
- **Within a cluster**, WPs with disjoint file ownership run in parallel lanes (ownership-map leeway,
  SO#8); F-WPs are mostly sequential (F1→F2/F3/F4→F5), T-WPs largely parallel post-gate, L-WPs parallel.
- **Integration**: each cluster gate is validated by a real dispatched pipeline run + the in-repo gates.

## Complexity Tracking

No Charter violations to justify. The one scope tension (full-tree vs ROI) is resolved by cluster
phasing + the matrix-registry realization (GitHub's 20-reusable-workflows/caller ceiling makes ~40
separate files impossible), not a rule exception.

## Post-plan squad folds & tasks inputs

Post-plan adversarial squad (2026-09-07, advisory, SO#1): architect-alphonso / planner-priti /
reviewer-renata — unanimous ready-with-fixes; sequencing fix (scrub before shard-freeze) **confirmed**.
Folded here: (a) full-tree realized as a **matrix over a committed module registry in a bounded set of
reusable workflows** (GitHub 20/caller ceiling — architect HIGH; also discharges the "big-bang/generator"
gap — planner); (b) the two missing contracts added (artefact-naming E2, router-two-authority E5 —
renata HIGH); (c) **bidirectional census guardrail** — independent evidence per base-red drop + a
"known-live is never dead" guard against false-positive drops (architect + renata HIGH); (d)
gate-selection authority built at **T1** parsing one source, reused by L3; (e) SC-009 `if: always()`
mechanism named.

**Carried to `/spec-kitty.tasks`:** split F2 (census oracle vs base-red triage), F5 (scrub vs
fix-before-wiring), T2 (registry+freeze vs matrix-workflow authoring) → target ~18–21 WPs; **demote early**
the specific shape guards the mission's own new files would trip (partial L2 forward, so TOPOLOGY's green
gate doesn't depend on L2 — architect MEDIUM); give WP homes to the two orphan edge cases (stale-artefact
fallback, `__pycache__` sweep — renata MEDIUM). Anti-laziness pass (post-tasks) should target the census
DoD (top fakeable-DoD risk) and the planted-regression negatives (must actually be able to fail).
