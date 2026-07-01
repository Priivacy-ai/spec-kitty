# Specification: Doctrine Catfooding

**Mission slug**: `doctrine-catfooding-2196-01KWE16N`
**Mission type**: software-dev
**Status**: Draft
**Epic**: [#2196](https://github.com/Priivacy-ai/spec-kitty/issues/2196) (+ children #2200–#2209, folds #2095)
**Research**: [`research/quality-and-tech-debt-standing-orders.source.md`](./research/quality-and-tech-debt-standing-orders.source.md) · [`research/adversarial-review-2196.md`](./research/adversarial-review-2196.md)

## Purpose

The **Quality & Tech-Debt Standing Orders** — 8 sections of battle-tested practice that keep spec-driven missions honest (adversarial squads, campsite debt paydown, tracer files, test-remediation discipline, non-vacuous architectural gates, canonical-source unification, git/workflow discipline, mission hygiene) — currently live **outside** the doctrine system, as operator standing orders and session-memory notes. Because they are not doctrine artifacts, the tooling cannot activate, enforce, or compile them.

This mission converts those 8 sections into **first-class doctrine artifacts** under `src/doctrine/`, **reconciling with the doctrine that already partially covers them rather than duplicating**, and then **compiles the Spec Kitty Charter from the activated set** so Spec Kitty governs its own development with the same doctrine it ships to consumers (catfooding).

## Background — the review's binding corrections

An adversarial review of epic #2196 (stored as a research artefact) found the epic's *direction* sound but surfaced corrections this mission MUST honor. The central finding: the epic over-provisions **new directives** for the sections that are *already the most heavily doctrined*, risking duplicate/conflicting authorities — the exact "reconcile-not-duplicate" risk the epic names. Concretely, the existing doctrine already covers:

| Section | Existing artifact(s) that already cover it | This mission's move |
|---|---|---|
| §1 Adversarial squad cadence | `procedures/built-in/adversarial-squad-deployment.procedure.yaml` (explicitly **optional**, lists "hard-wiring the squad as a gate" as an anti-pattern), `paradigms/built-in/brownfield-onboarding.paradigm.yaml` | Author as a **cadence styleguide/paradigm**, NOT a required directive; extend the procedure/paradigm |
| §2 Campsite / debt paydown | `directives/025-boy-scout-rule`, `024-locality-of-change`, `040-recurring-bug-structural-intervention`, `planning-and-tracking.styleguide` | EXTEND 025/024/040; author only the genuinely-new atoms (frozen-baseline ratchet, domain-matched fold) |
| §4 Test remediation & bug-fix | `directives/041-tests-as-scaffold-not-friction` (near-total duplicate), `testing-principles.styleguide`, `test-first-bug-fixing.procedure`, `disciplined-defect-diagnosis.procedure`, `tactics/testing/*` | EXTEND 041 (add only "live evidence over static-fixed"); do NOT author a new §4 directive |
| §7 Git & workflow | `clean-linear-commit-history.tactic` (covers "compress history"), `029-agent-commit-signing`, `033-targeted-staging`, git toolguides/paradigms | REFERENCE the commit-history tactic; author only the 4 uncovered rules |
| §8 Mission hygiene | `tiered-standards.styleguide` (tiered-rigour already complete), `planning-and-tracking.styleguide` (issue-matrix, partial) | EXTEND those; author only ownership-map-leeway + role-separation |
| §5a/§5b, §6, §3 | No dedicated existing coverage | Genuinely new — author cleanly |

## User Scenarios & Testing

### Primary scenario (the catfooding loop)
A contributor (human or AI agent) begins work in the Spec Kitty repo. Because the standing orders are now **activated doctrine** compiled into the project charter, `spec-kitty charter context --action <phase>` surfaces them at each workflow phase, and agent profiles carry the relevant directives — so the practices are *applied and enforceable*, not merely remembered. A consumer project that adopts the pack inherits the same hardened doctrine.

### Exception A — reconciliation must not create a second authority
When a section's practice is already encoded (e.g. §4 in `DIRECTIVE_041`), the conversion **extends** the existing artifact. Authoring a parallel directive that restates it is a defect (split-brain doctrine) and is rejected in review.

### Exception B — the cadence must stay optional
§1's adversarial-squad cadence is authored as guidance, not an `enforcement: required` directive — because the shipped `adversarial-squad-deployment.procedure` declares itself optional and names gate-hardwiring an anti-pattern. A required §1 directive would contradict shipped doctrine.

### Exception C — the charter compiles in the right order
The capstone activates the artifacts (writing `config.yaml`) **before** generating the charter (which filters the DRG closure by activation state). Generate-before-activate yields an incomplete reference index.

## Domain Language

| Canonical term | Meaning |
|---|---|
| **Doctrine artifact** | A governed unit under `src/doctrine/<kind>/`: directive / tactic / styleguide / toolguide / paradigm / procedure / template / agent_profile. |
| **Reconcile (extend), not duplicate** | When existing doctrine covers a practice, augment/reference it; never author a second artifact restating the same rule (DIRECTIVE_003). |
| **DRG** | Doctrine Reference Graph (`src/doctrine/graph.yaml`) — nodes (artifact URNs) + edges (`requires`/`suggests`/`refines`/`specializes_from`) that the charter closure and cascade walk. |
| **Charter compile** | `charter activate` (writes activation into `.kittify/config.yaml`) then `charter generate` (renders `charter.md` + `references.yaml` from interview answers + activation-filtered DRG closure). Activation ≠ generation. |
| **Catfooding** | Spec Kitty governing its own development with the doctrine it ships. |

## Requirements

### Functional Requirements

| ID | Requirement | Group | Status |
|---|---|---|---|
| FR-001 | **Step-0: commit the source doc.** Create + commit `docs/development/quality-and-tech-debt-standing-orders.md` (content = the stored research source) as the canonical human-readable text the conversions convert *from* and the charter later mirrors. Register it in the page inventory + frontmatter (docs-freshness gates) **via `scripts/docs/freshen_adr_inventory.py` / `inventory_lockfile.py` (the canonical freshener, PR #2282) — do not hand-edit the lockfile**; expect a trivial tail-append conflict with #2277 on `docs/development/3-2-page-inventory.yaml` (regenerate, don't hand-merge). | Foundation | Draft |
| FR-002 | **Pre-allocate directive numbers.** Reserve the next contiguous directive IDs (currently 043–049) for the new directives this mission authors, so parallel conversions do not collide on the same number. Record the allocation in the plan. | Foundation | Draft |
| FR-003 | **Decide + document the `graph.yaml` regeneration strategy.** `src/doctrine/graph.yaml` is a single generated shared surface; N parallel edits collide. Choose one strategy (per-ticket edges authored + a single serialized regeneration, e.g. at the capstone) and encode it as a constraint the WPs follow. | Foundation | Draft |
| FR-004 | **Resolve the epic parenting contradiction.** #2196 is labeled `scope-tracker`/"not a functional parent" yet natively parents all children. Make #2196 the genuine **functional epic** (drop the scope-tracker framing) so it does not violate the §8 tracker rule it is chartered to encode. | Foundation | Draft |
| FR-005 | **§1 Adversarial squad cadence** → author a **cadence styleguide/paradigm** (NOT an `enforcement: required` directive) capturing **only the cadence recommendation** ("run a bounded squad at every planning point-cut, as strong guidance not a gate"). **Do NOT re-author the squad playbook or the point-cut table** — those already live in `adversarial-squad-deployment.procedure`; the new artifact **references** the procedure (playbook + notes) and `brownfield-onboarding.paradigm`, extending them only where the cadence-recommendation adds signal. Preserve the procedure's optional / never-a-gate invariant. **Folds experiment #2094** (multi-squad pre-flight cadence) — cite it in the artifact's provenance, close-on-land. | Convert | Draft |
| FR-006 | **§2 Campsite cleaning & debt paydown** → EXTEND `DIRECTIVE_025` (+ cross-links 024/040) and `planning-and-tracking.styleguide`; author a new **tactic** only for the genuinely-uncovered atoms (frozen-baseline ratchet, domain-matched fold at point-cut). Do NOT author a duplicate campsite directive. | Convert | Draft |
| FR-007 | **§3 Mission tracer files** → author a **procedure** (seed→append→assess lifecycle) + **template** (the 3-file `traces/` scaffold), and a **tactic** only if it carries content the procedure does not; folds experiment #2095 (close it on land). | Convert | Draft |
| FR-008 | **§4 Test remediation & bug-fix discipline** → EXTEND `DIRECTIVE_041` with **only** the genuinely-uncovered "live evidence over static-fixed / carry OPEN until live repro" atom (confirmed absent from 034/041/`testing-principles`/the procedures), plus a light `testing-principles.styleguide` cross-link. **The red-first "pre-existing entry point, not the fix's new API" refinement already lives verbatim in `DIRECTIVE_034-test-first-development` (lines 16-22) — REFERENCE/cross-link 034; do NOT restate it into 041 or `test-first-bug-fixing.procedure` (that would create a 034↔041↔procedure triple authority).** Do NOT author a new §4 directive. **(Lightest conversion — one new atom + cross-links; do not over-size.)** | Convert | Draft |
| FR-009 | **§5a Architectural-gate construction & non-vacuity** → author a NEW **directive** (close defect classes by construction) + **tactic** (build an AST call-site gate with a concrete floor, self-mutation test, shrink-only allowlist, routed-count floor). Genuinely new. **Cite the real existing exemplars rather than invent one**: the live `tests/architectural/test_protection_resolver_call_sites.py` gate + the shrink-only ratchet work in-flight at #2159 (`tests/architectural/_baselines.yaml`). | Convert | Draft |
| FR-010 | **§5b Post-merge arch-gate adjudication** → author a NEW **procedure** (full-gate sweep on the merged branch, cross-base "pre-existing" verification, run CI-only shards locally). Depends on FR-009. | Convert | Draft |
| FR-011 | **§6 Canonical sources & unification** → author a NEW **directive** (use-canonical-sources + unification-not-parity + missing-command-is-a-gap) + **tactic**; author the terminology-guard sub-rule as a **toolguide** (the guard invocation), not a directive line. | Convert | Draft |
| FR-012 | **§7 Git & workflow discipline** → author the 4 uncovered rules (PRs-only/operator-merges, read-intent-before-high-risk-ops, isolate-PR-touching-agents-in-worktree, no-version-prescription-in-scope) as directive(s)/tactic; **REFERENCE** `clean-linear-commit-history.tactic` for "compress history" (do not re-author). The §7 overlap-audit (C-001) must also check `paradigms/built-in/git-flow.paradigm.yaml` and directives `029`/`033` (adjacent git artifacts) so no second git-workflow authority is minted. **§7 is heterogeneous — decompose into ≥2 WPs at /tasks** (e.g. PRs-only+read-intent directive vs worktree-isolation+no-version tactic); do not carry all 4 rules as one WP. | Convert | Draft |
| FR-013 | **§8 Mission hygiene** → EXTEND `planning-and-tracking.styleguide` (issue-matrix discipline) and REFERENCE the complete `tiered-standards.styleguide` (tiered rigour); author new artifacts only for ownership-map-leeway + role-separation (reviewer≠implementer profile). **Align the ownership-map-leeway artifact with the existing mission-step prompt language** (`missions/mission-steps/software-dev/tasks-packages/prompt.md` + `tasks/prompt.md` state the "no-overlap is the real guard" rule verbatim) — reference it to avoid a doctrine↔prompt split-brain. **Role-separation is already operationalized** in `src/doctrine/missions/*/mission-runtime.yaml` (review-step profile `reviewer-renata`) + the review/implement mission-step prompts — the new artifact REFERENCES that wiring, it does not restate it. | Convert | Draft |
| FR-014 | **Capstone: compile the Spec Kitty Charter.** Sequence: (a) confirm the single `graph.yaml` regeneration landed + DRG freshness/cycle tests pass (`tests/doctrine/drg/*`); (b) **activate** the catfooding artifacts (`charter activate --cascade`, writes `config.yaml`); (c) **mirror the activation set into interview `answers.yaml`** — a named manual sub-step, as no activation→answers auto-bridge exists; (d) **generate** (`charter generate`, renders `charter.md` + `references.yaml`); (e) `doctor doctrine --json` healthy + reference closure non-shallow. Must reconcile/supersede the existing `charter.md` (v1.1.5), not clobber or parallel it. | Capstone | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold | Status |
|---|---|---|---|
| NFR-001 | Doctrine health after the mission. | `spec-kitty doctor doctrine --json` reports **0 skipped/invalid artifacts**; run after **each** conversion (not only at capstone). | Draft |
| NFR-002 | No duplicate authorities. | Every conversion records an explicit overlap-audit + augment-vs-create decision; a reviewer confirms **no new artifact restates a rule already fully encoded** in an existing one (esp. §4/§2/§8/§7). | Draft |
| NFR-003 | Complete charter reference closure. | Every activated catfooding artifact's DRG edges resolve; the generated `references.yaml` is non-shallow (no artifact referenced only by direct interview selection with its `requires`/`suggests` edges dropped). | Draft |
| NFR-004 | Guards + lint clean. | `tests/architectural/test_no_legacy_terminology.py` green on all new/edited doctrine; any code (e.g. graph-regen tooling) passes ruff + mypy with zero issues. | Draft |

### Constraints

| ID | Constraint | Status |
|---|---|---|
| C-001 | **Reconcile-not-duplicate (binding).** Every conversion WP opens with a mandatory overlap-audit of the enumerated existing artifact(s) and records an augment-vs-create decision (DIRECTIVE_003). Extend/reference wins over create when coverage exists. | Draft |
| C-002 | **Per-conversion DoD triad.** Each conversion's Definition of Done includes: (a) DRG node + edges added to `graph.yaml`; (b) `doctor doctrine --json` green; (c) the new directive wired into the relevant agent-profile `directives:` lists (else the doctrine is inert for agent sessions). | Draft |
| C-003 | **Shared-target locks.** Artifacts touched by >1 section are authored once and referenced: `brownfield-onboarding.paradigm` (§1+§2), the frozen-baseline/shrink-only ratchet (§2+§5), **`planning-and-tracking.styleguide` (§2+§8)**, and **the agent-profile `directives:` files** (wired by §5a/§6/§7/§8). The profile-`directives:` edits and the single `graph.yaml` regeneration are consolidated into **one dedicated serialized "wiring" WP** (the last conversion-phase WP) rather than spread across conversions — this owns the C-002(c) profile-wiring + the FR-003 single regen + the DRG freshness/cycle-test pass. | Draft |
| C-004 | **Terminology canon.** All new/edited doctrine passes the legacy-terminology guard; forbidden terms in examples/anti-patterns are quoted-and-marked, never used in canonical voice (esp. §7 git "feature branch" idiom; §6's own terminology-guard artifact). | Draft |
| C-005 | **No version/patch numbers in scope.** Versions are superimposed at release time. | Draft |
| C-006 | **§1 is not a required directive.** Authoring §1 as `enforcement: required` contradicts the shipped `adversarial-squad-deployment.procedure` (optional; gate-hardwiring is an anti-pattern) and is rejected. | Draft |
| C-007 | **Capstone order + non-greenfield.** Charter compile is activate→generate (never generate→activate); the capstone reconciles the existing `charter.md` v1.1.5 rather than compiling over it blind. | Draft |

## Success Criteria

| ID | Criterion | Verification |
|---|---|---|
| SC-001 | All 8 sections are represented in activated doctrine (each maps to ≥1 activated artifact). | `spec-kitty charter list` + the section→artifact map; every section accounted for. |
| SC-002 | No duplicate directive authority for the pre-covered sections. | Audit: §4 extends 041 (no new §4 directive), §2 extends 025, §8 references tiered-standards, §7 references commit-history tactic; single authority per rule. |
| SC-003 | The Spec Kitty Charter is compiled from the activated set. | `charter.md` + `references.yaml` regenerated from the activated catfooding set; `doctor doctrine --json` healthy; reference closure complete (NFR-003). |
| SC-004 | #2196 is a functional epic. | `scope-tracker` framing removed; children map to this mission's WPs. |
| SC-005 | The source doc is committed and is a faithful human-readable mirror of the activated doctrine. | `docs/development/quality-and-tech-debt-standing-orders.md` present, inventoried, docs-freshness green; content matches the activated set. |

## Key Entities

- **Doctrine artifacts** — the directives/tactics/styleguides/toolguides/paradigms/procedures/templates authored or extended, one group per section.
- **DRG (`src/doctrine/graph.yaml`)** — the shared node/edge graph; the charter closure + cascade traverse it.
- **The charter** — `.kittify/charter/charter.md` + `references.yaml` (rendered) + `.kittify/config.yaml` (activation state) + interview `answers.yaml`.
- **Source doc** — `docs/development/quality-and-tech-debt-standing-orders.md`, the human-readable mirror.

## Assumptions

- The named existing artifacts (041, 025, 024, 040, `adversarial-squad-deployment.procedure`, `brownfield-onboarding.paradigm`, `testing-principles`/`tiered-standards`/`planning-and-tracking` styleguides, `clean-linear-commit-history.tactic`, git toolguides) exist and are the correct extension targets (confirmed during review).
- The charter machinery (`charter activate`/`generate`/`interview`/`context`, `activation_engine`, `cascade`, `compiler`) supports the activate→generate flow with no new machinery required (confirmed during review).
- Per DIR-013, any pre-existing unrelated test failures hit during implementation are filed as an issue before being treated as baseline.

## Scope

**In scope:** the step-0 foundation (FR-001..004), all 8 section conversions (FR-005..013, reconciled not duplicated), and the capstone charter compile (FR-014) — the full corrected epic #2196.

**Out of scope:** authoring doctrine for practices not in the 8 sections; changing the charter *machinery* (only using it); consumer-pack migration guidance; retiring `CLAUDE.md`'s parallel restatements (a possible follow-up once the charter governs these — noted, not in scope).

## Dependencies

- Existing doctrine artifacts named in the reconciliation table (extension targets).
- Charter machinery: `src/charter/{activation_engine,cascade,compiler,context}.py`; CLI `charter {activate,generate,interview,context,list}`; `doctor doctrine`.
- Doctrine gates: `tests/architectural/test_no_legacy_terminology.py`, `doctor doctrine`, docs-freshness (source-doc inventory).
- Tracker: epic #2196 + children #2200–#2209, experiment #2095.
