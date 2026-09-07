# Research — CI Pipeline Reinstatement (Phase 0)

No open `[NEEDS CLARIFICATION]`. This records the load-bearing design decisions and the
supply-chain / adversarial evidence for the dependency additions (DIR-051, advisory).

## Decisions

### D1 — Change router: `dorny/paths-filter`, two-authority model
- **Decision:** revive the pre-fork `dorny/paths-filter` router with the two-authority invariant (dorny
  filter block = path→group; job `if:` = group→job), fail-closed `unmatched(src/**)→run-all`.
- **Rationale:** proven at `e8cc2f444f^`; canonical (SO#6); the mission's "docs/packs-only PR skips the
  full run" (NFR-002) is exactly this engine. **Alternatives:** hand-rolled path globs per job (drifts,
  no completeness oracle) — rejected.
- **Guard:** the `test_ci_quality_path_filters.py` assertion currently pins *no* filter on the husk;
  it is rewritten in lockstep when filters return (Topology T1).

### D2 — Warmup env: cache, pinned-PR / latest-nightly
- **Decision:** a warmup composite resolves + builds the editable env once; **PR mode pins a recorded
  `spec_kitty_events` rev**, **nightly/full pulls latest mainline**; publish via `actions/cache` keyed on
  `uv.lock` + the resolved events rev (not a bare `upload-artifact`, which architect flagged conflates
  cache semantics).
- **Rationale:** kills #3283 venv-lock cascade; deterministic PR builds satisfy the charter Shared-Package
  pinned-rev policy (operator decision B); nightly still catches upstream drift. **Alternatives:** always
  latest (non-deterministic, charter tension) / always pinned (misses drift) — rejected in favor of the
  split.

### D3 — Dual-mode failure behavior
- **Decision:** PR mode = fail-fast (matrix `fail-fast: true`, tiered `needs:` so a red tier short-circuits
  dependents); full mode (nightly + `workflow_dispatch` "run full") = `fail-fast: false` + `if: always()`
  so every job runs. A **mode input** threads through reusable workflows. Merge-eligibility: a successor
  skipped by short-circuit is NOT green — the required-check set treats "skipped-due-to-upstream" distinctly
  (SC-009). **Alternatives:** single mode (either churns or hides signal) — rejected.

### D4 — Governance-map `introduced` disposition (BLOCKER fix)
- **Decision:** extend `interim-ci-producer.md` + `test_release_ci_ownership.py` from the closed
  `restore|defer|never-restore` set to add `introduced` (net-new workflows with no pre-fork ancestor:
  Sonar, new `module-*.yml`, router, aggregate, nightly, packs). The enforcer asserts the introduced set
  as data, keeping stock-runner + no-`SK_CI_TOKEN` invariants.
- **Rationale:** the enforcer asserts an *exact closed set*; "append a row" is not representable
  (architect BLOCKER). **Alternatives:** shoehorn net-new as `restore` (lies about provenance) — rejected.

### D5 — P1 dead-code census as machine oracle
- **Decision:** promote the dead-code census (grounding `25-dead-code-census`) into an **in-repo machine
  artifact** that (a) authorizes each base-red drop + each shard exclusion, (b) excludes the coverage
  denominator, (c) is cross-checked by a non-vacuity floor + a planted dead-code/retired-import negative
  test. The enforcement allowlists (`test_no_dead_*`, `test_no_retired_subsystems`) stay always-on.
- **Rationale:** post-spec squad convergence — P1 must be machine-enforced, not prose+reviewer scrub;
  closes the "mislabel a live regression as dead-code test" loophole. **Alternatives:** reviewer scrub
  (fakeable) — rejected.

### D6 — Sonar: SonarCloud, nightly, fork-safe
- **Decision:** net-new `sonar.yml` runs `SonarSource/sonarqube-scan-action` + quality-gate action from
  the spec-kitty repo, **nightly/dispatch**, aggregating per-shard `coverage-*.xml`; skip-green without
  `SONAR_TOKEN`. **Verify the `Priivacy-ai_spec-kitty` project identity before wiring** (client-inversion).
  Promotable to per-PR without re-architecting the artefact flow. **Alternatives:** self-hosted SonarQube
  (no instance today) / PR-blocking now (backlog risk) — deferred.

### D7 — Full-tree modularization, phased
- **Decision:** every per-module test group → its own `workflow_call` `module-*.yml`, delivered in the
  FOUNDATION→TOPOLOGY→LEAN-SUITE cluster gates. **Rationale:** operator's explicit scope, ROI concern
  reconciled by phasing (planner). **Alternatives:** hybrid (kernel/doctrine/packs only) — offered,
  operator chose phased full-tree.

## Supply-chain & adversarial evidence (DIR-051, advisory)

Dependencies added/pinned by this plan: `dorny/paths-filter`, `SonarSource/sonarqube-scan-action` +
`sonarqube-quality-gate-action`, `actions/*` (checkout/setup-uv/upload-artifact/download-artifact/cache),
`astral-sh/setup-uv`; pytest plugins (`pytest-cov`, `diff-cover`, `pytest-xdist`) already in `pyproject`.

- **Authenticity + freshness:** all third-party **actions pinned to a full commit SHA** (not a moving
  tag); versions recorded and periodically reviewed. First-party `actions/*` + `astral-sh` + `SonarSource`
  are the canonical publishers.
- **Lifecycle-script discipline:** CI installs run under `uv` with no arbitrary `postinstall`; the warmup
  composite executes only pinned, reviewed steps.
- **Secrets:** `SONAR_TOKEN` only on the canonical repo; never `SK_CI_TOKEN` on public jobs; tokens never
  echoed (DIR-050).
- **Adversarial disposition** (post-spec squad, `contracts/adversarial-evidence-contract.md` posture):
  all contested findings dispositioned — governance-map schema `changed` (D4); P1 machine-oracle
  `changed` (D5); warmup pinned-PR `changed` (D2); full-tree ROI `deferred_with_rationale` (phased, D7);
  #3189 claim `changed` (downgraded to follow-up). None silently dropped.
