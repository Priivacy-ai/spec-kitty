# Research — Doctrine Catfooding

Phase 0 consolidation. The heavy research was done as an **adversarial review of epic #2196** (see [`research/adversarial-review-2196.md`](./research/adversarial-review-2196.md)) plus a **post-spec squad** (priti sizing / daphne reconciliation / debbie claim-verification). This file records the resulting decisions in Decision / Rationale / Alternatives form. Every existing-artifact claim below was verified on disk by debbie (all CONFIRMED, zero refuted/stale).

## D-1 — Reconcile (extend/reference), do not duplicate

- **Decision**: Each section maps to the smallest doctrine change that captures its uncovered content; where existing doctrine already encodes a rule, extend/reference it. Every conversion WP opens with an overlap-audit recording an augment-vs-create decision (DIRECTIVE_003).
- **Rationale**: The repo already has 23 directives / 120 tactics / 17 procedures / 15 paradigms / 16 styleguides / 25 toolguides. The dominant failure mode is a second authority for a rule that already exists (split-brain doctrine). The review found the epic over-provisioned new directives for exactly the most-covered sections.
- **Alternatives rejected**: "One new directive per section" (the epic's original shape) — creates duplicate authorities for §4/§2/§8/§7.

## D-2 — Per-section extend-vs-create + artifact kind (the reconciliation map)

| § | Uncovered atom(s) → new | Extend / reference (existing) | Kind | Verified target |
|---|---|---|---|---|
| §1 | cadence *recommendation* only ("run a bounded squad at each point-cut, as guidance") | reference `adversarial-squad-deployment.procedure` playbook + point-cut table; extend `brownfield-onboarding.paradigm` | **styleguide/paradigm** (NOT directive — C-006) | procedure declares itself *optional*, gate-hardwiring an anti-pattern (quoted verbatim) |
| §2 | frozen-baseline ratchet; domain-matched-fold-at-point-cut | extend `025-boy-scout-rule` (+024/040 cross-links), `planning-and-tracking.styleguide` | **tactic** (+ extends) | `025`,`024`,`040` exist |
| §3 | seed→append→assess lifecycle; 3-file scaffold | none (zero tracer coverage) | **procedure + template** (drop standalone tactic unless it carries extra) | grep: no tracer artifact |
| §4 | "live evidence over static-fixed / carry OPEN until live repro"; red-first "pre-existing entry point, not new API" | extend `041-tests-as-scaffold-not-friction` (near-total dup), `testing-principles.styleguide`, `test-first-bug-fixing.procedure` | **directive extension** (no new directive) | `041` covers three-verdict/red-first/no-retry/realistic verbatim |
| §5a | close-by-construction; non-vacuity (concrete floor, self-mutation test, shrink-only allowlist, routed-count floor) | none | **directive + tactic** (new) | no arch-gate-non-vacuity artifact exists |
| §5b | full-gate sweep on merged branch; cross-base pre-existing check; CI-only shards locally | none | **procedure** (new, dep §5a) | none |
| §6 | canonical-sources; unification-not-parity; missing-command-is-a-gap; terminology-guard | none | **directive + tactic + terminology toolguide** | none exist |
| §7 | PRs-only/operator-merge; read-intent-before-high-risk; worktree-isolation; no-version-in-scope | reference `clean-linear-commit-history.tactic` (compress-history); `029`/`033` adjacent-only | **directive(s)+tactic — split ≥2 WPs** | commit-history tactic exists |
| §8 | ownership-map-leeway; role-separation | extend `planning-and-tracking.styleguide`; reference complete `tiered-standards.styleguide` | **styleguide extension + small tactic** | tiered-standards complete; leeway also in mission-step prompts (align) |

## D-3 — §1 must stay optional (not a required directive)

- **Decision**: Author §1 as a cadence styleguide/paradigm; never `enforcement: required`.
- **Rationale**: `adversarial-squad-deployment.procedure.yaml` states *"Optional and charter-…activated — it enriches the flow, it does not gate it"* and lists *"Hard-wiring the squad as a gate"* as an anti-pattern. A required directive would contradict shipped doctrine (and the mission would be self-inconsistent — it codifies the squad while violating the squad's own optionality).
- **Alternatives rejected**: `enforcement: required` §1 directive.

## D-4 — graph.yaml is generated; regen owned by one wiring WP

- **Decision**: Conversion WPs author inline `requires`/`suggests`/`refines` edges in their artifacts; a single wiring WP runs the one `graph.yaml` regeneration via the canonical `spec-kitty doctrine regenerate-graph` CLI (composes `drg/migration/extractor.py:generate_graph` + calibrator; NOT `python extractor.py`, which has no `__main__`) + the DRG freshness/cycle/relations tests.
- **Rationale**: `graph.yaml` is a single 2927-line generated file; N parallel regenerations collide. Making it a generated output of one owner removes the collision and localizes DRG failures.
- **Alternatives rejected**: per-WP regeneration (collides); hand-editing graph.yaml (it's generated).

## D-5 — Charter compile is activate→generate against a non-empty charter

- **Decision**: Capstone sequence = confirm graph regen + DRG tests → `charter activate --cascade` (writes `config.yaml`) → **manually mirror** the activation set into interview `answers.yaml` → `charter generate` (renders `charter.md` + `references.yaml`) → `doctor doctrine --json` healthy + non-shallow reference closure. Reconcile the existing v1.1.5 charter, don't clobber.
- **Rationale**: `charter generate` filters the DRG transitive closure by activation state, so generate-before-activate yields a shallow reference index. `generate` does not activate; there is no activation→answers auto-bridge (both confirmed in the charter code + review). A charter (v1.1.5) already exists.
- **Alternatives rejected**: generate-then-activate (shallow closure); greenfield compile (would clobber v1.1.5).

## D-6 — Whole epic as one mission (with a split seam)

- **Decision**: Execute all 8 sections + capstone in one mission (~10-13 WPs), 4 lanes + capstone (operator choice).
- **Rationale**: 12-13 WPs is under the >15 danger line; NFR-001's per-conversion `doctor doctrine --json` keeps each artifact independently valid; one coherent charter compiled at the end.
- **Alternatives rejected / escape hatch**: foundation-only or foundation+reconcile-slice first (operator chose whole-epic). If the mission runs long, the capstone (IC-05) is the clean split seam to a thin follow-on mission.

## D-7 — Post-plan brownfield addenda (2026-07-01 squad: daphne dual-authority + priti foldable-issue)

Plan holds structurally (043–049 correct, greenfield confirmed, no doctrine/`graph.yaml` PR collisions). Folded corrections:

- **§4 dual-authority MUST-FIX (daphne)**: the red-first "pre-existing entry point, not the fix's new API" atom already lives **verbatim in `DIRECTIVE_034-test-first-development` (lines 16-22)**. FR-008 now REFERENCES 034 for red-first and confines the `041` extension to **only** "live evidence over static-fixed" (the sole atom absent from 034/041/`testing-principles`/`test-first-bug-fixing.procedure`). Routing red-first into 041/the procedure would mint a 034↔041↔procedure triple authority.
- **§8 role-separation (daphne, soft)**: already operationalized in `src/doctrine/missions/*/mission-runtime.yaml` (`reviewer-renata` review step) + review/implement mission-step prompts → FR-013 references, does not restate.
- **§5a exemplar (daphne, soft)**: cite the live gate `tests/architectural/test_protection_resolver_call_sites.py` + the in-flight shrink-only ratchet at #2159 (`tests/architectural/_baselines.yaml`) rather than invent — FR-009 updated.
- **§7 audit widening (priti)**: add `paradigms/built-in/git-flow.paradigm.yaml` to the §7 overlap-audit set — FR-012 updated.
- **#2094 fold (priti)**: the multi-squad pre-flight cadence experiment is the §1 sibling of #2095/§3 → folds into FR-005 §1 as close-on-land (provenance only, no new WP).
- **FR-001 (priti)**: register the source doc via the `freshen_adr_inventory.py`/`inventory_lockfile.py` freshener (#2282), not hand-edit; expect a trivial tail-conflict with #2277 on `3-2-page-inventory.yaml` (regenerate).
- **CLAUDE.md deferral SAFE (daphne)**: every §-rule restated in `CLAUDE.md` (§6/§7/§4/§8) is pure duplication, zero contradiction; §1 is never hard-wired there as a gate → retiring the restatements stays a post-charter follow-up, not an in-mission must-fix.
- **Deprecation check CLEAN**: no extension target is deprecated/superseded/retired.
- **Left (not folded)**: #1840 (delegation-mechanism), #1843 (tiered-standards enforcement epic), #2080/#1923 (DRG audits) — machinery outside the 8-section authoring domain; IC-04's regen must not worsen the orphan count (covered by NFR-003).

## Open items / watch

- FR-009 (§5a AST gate) is tooling-design, not prose — flag for the post-tasks anti-laziness squad.
- §7 (FR-012) must be split into ≥2 WPs at /tasks.
- DRG generator has known gaps (#1755) — the wiring WP must verify the regeneration + cycle-check, not assume.
