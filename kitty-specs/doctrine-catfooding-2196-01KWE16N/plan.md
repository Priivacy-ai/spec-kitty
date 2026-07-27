# Implementation Plan: Doctrine Catfooding

**Branch**: `design/doctrine-catfooding-2196` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-catfooding-2196-01KWE16N/spec.md`
**Research inputs**: [`research/adversarial-review-2196.md`](./research/adversarial-review-2196.md), [`research/quality-and-tech-debt-standing-orders.source.md`](./research/quality-and-tech-debt-standing-orders.source.md)

## Summary

Convert the 8-section Quality & Tech-Debt Standing Orders into first-class doctrine artifacts under `src/doctrine/`, **reconciling with (extending/referencing) existing doctrine rather than duplicating it**, then compile the Spec Kitty Charter from the activated set (catfooding). The work is doctrine-YAML authoring + edits to the DRG (`graph.yaml`) + agent-profile wiring + a charter-compile capstone that uses the existing `charter` CLI (no new machinery). The dominant engineering risk is **duplicate/conflicting authorities**, so every conversion opens with an overlap-audit (C-001) and the plan front-loads a foundation lane and back-loads a single serialized wiring lane to avoid shared-surface collisions.

## Technical Context

**Language/Version**: Python 3.11+ (doctrine artifacts are YAML; supporting/gate code is Python 3.11+)
**Primary Dependencies**: `src/doctrine/` artifact schemas (`artifact_kinds.py`, per-kind loaders); the DRG (`src/doctrine/graph.yaml`, regenerated via the canonical `spec-kitty doctrine regenerate-graph` CLI — composes `drg/migration/extractor.py:generate_graph` + calibrator); the charter machinery (`src/charter/{activation_engine,cascade,compiler,context}.py` + `spec-kitty charter {activate,generate,interview,context,list}`); `spec-kitty doctor doctrine`
**Storage**: Files only — YAML doctrine artifacts under `src/doctrine/<kind>/built-in/`; `graph.yaml`; charter state in `.kittify/charter/` + `.kittify/config.yaml`; source doc under `docs/development/`
**Testing**: `pytest` — `tests/doctrine/drg/*` (DRG freshness/cycle/relations), `tests/architectural/test_no_legacy_terminology.py` (terminology guard), `spec-kitty doctor doctrine --json` (artifact health), docs-freshness (source-doc inventory); `ruff` + `mypy` on any Python touched
**Target Platform**: Spec Kitty repo (dogfooding) + consumers who adopt the pack
**Project Type**: single (doctrine pack + CLI)
**Performance Goals**: N/A (authoring mission — no runtime perf target)
**Constraints**: reconcile-not-duplicate (C-001); §1 not a required directive (C-006); capstone activate→generate + reconcile-not-clobber (C-007); per-conversion DoD triad (C-002); shared-target locks (C-003); terminology canon (C-004); no version numbers in scope (C-005)
**Scale/Scope**: 8 sections → ~10-13 WPs across 4 lanes + capstone; touches ~6 existing artifacts (extend) + ~8-10 new artifacts; 1 DRG regeneration; ~5 agent-profile edits; 1 charter compile

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter present (`charter context --action plan` → `mode: compact`, v1.1.5). Governing alignment:

- **DIRECTIVE_003 (decision-recording) + doctrine-daphne curation discipline** → C-001 (overlap-audit before authoring) is the direct application. **PASS** — the mission is *about* honoring this.
- **DIRECTIVE_035 (bulk-edit cross-file safety)** → N/A: this is not a bulk rename (authoring/extending distinct artifacts). Confirmed not `bulk_edit`.
- **Terminology canon** → C-004; every artifact runs the legacy-terminology guard. **PASS by construction**.
- **Self-governance bootstrap** → activating these directives could in principle change agent behavior mid-development. Mitigation (C-006 + C-007): §1 stays optional (never a gate); the charter is compiled at the capstone (end), not incrementally enforced during authoring; no new CI gate is introduced that could block the authoring work. **PASS with mitigation recorded.**

No unjustified violations. Proceed to Phase 0.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-catfooding-2196-01KWE16N/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output (artifact/DRG/charter entities)
├── quickstart.md        # Phase 1 output (the catfooding smoke path)
├── contracts/           # Phase 1 output (per-conversion DoD contract + capstone contract)
├── research/            # authoritative inputs (review + source doc) — already committed
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/doctrine/
├── directives/built-in/        # 043–049 reserved (see Plan Decision PD-1); §5a, §6, §7 new; EXTEND 041/025
├── tactics/built-in/           # §2 ratchet, §5a gate-build, §6, §7, §8 leeway/role-sep (new); REFERENCE clean-linear-commit-history
├── procedures/built-in/        # §5b adjudication (new); EXTEND adversarial-squad-deployment, test-first-bug-fixing; §3 tracer lifecycle (new)
├── styleguides/built-in/       # §1 cadence (new); EXTEND testing-principles, planning-and-tracking; REFERENCE tiered-standards
├── paradigms/built-in/         # EXTEND brownfield-onboarding
├── toolguides/built-in/        # §6 terminology-guard (new)
├── templates/                  # §3 tracer 3-file scaffold (new)
├── agent_profiles/built-in/    # WIRING WP: append new directive IDs to relevant profiles
└── graph.yaml                  # WIRING WP: single regeneration after all edges authored

docs/development/quality-and-tech-debt-standing-orders.md   # FR-001 source doc (new)
.kittify/charter/ + .kittify/config.yaml                    # FR-014 capstone (activate + generate)
```

**Structure Decision**: single doctrine pack. Authoring happens in the repo root checkout; execution worktrees are allocated per lane from `lanes.json` at implement time.

## Plan Decisions (recorded here per spec FR-002/FR-003 — these are decisions, not WPs)

- **PD-1 (FR-002) — Directive-number allocation.** Highest existing built-in directive is `042` (verified). Reserve the next contiguous block **043–049** for this mission's new directives. Assignment (subject to the reconcile-audit possibly collapsing some): `043` §5a arch-gate-construction; `044` §6 canonical-sources-&-unification; `045` §7 PRs-only/operator-merge + read-intent-before-high-risk; `046` §7 (if a 2nd directive is warranted after the §7 split). §8 ownership-leeway/role-separation and §2 ratchet are expected to be **tactics/styleguide**, not directives — so they do not consume numbers unless the authoring WP proves a directive is the right kind. Any conversion that ends up NOT authoring a directive returns its reserved number. **No WP mints a number ad-hoc; the block is the source of truth.**
- **PD-2 (FR-003) — `graph.yaml` regeneration strategy.** `graph.yaml` (2927 lines) is **generated** from inline `requires`/`suggests`/`refines` refs in the artifacts via the canonical CLI **`spec-kitty doctrine regenerate-graph`** (`--check` for freshness/dry-run) — which composes the `drg/migration/extractor.py:generate_graph` extractor + calibrator. It is NOT regenerated by `python extractor.py` (no `__main__`) and NOT hand-edited. Strategy: **each conversion WP authors its artifact's inline DRG edges; the single `spec-kitty doctrine regenerate-graph` run + the DRG freshness/cycle/relations test pass (`tests/doctrine/drg/*`) is owned solely by the WIRING WP** (IC-04). This removes `graph.yaml` as a parallel-write collision surface and gives the regeneration one owner.
- **PD-3 (FR-004) — Epic parenting.** Fold into the Foundation WP: drop the `scope-tracker` framing / "not a functional parent" language on #2196 so it is a genuine functional epic (it already natively parents the children). Tracker-only edit; no code.

## Complexity Tracking

*No Charter Check violations requiring justification.* The one notable complexity — running the whole epic as one mission — is bounded by the lane structure below and the split-seam escape hatch (capstone → follow-on mission) recorded in IC-05.

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs. The lane hints below reflect the post-spec sizing lens; the tasks command owns final WP counts.

### IC-01 — Foundation (blocks everything)

- **Purpose**: Establish the preconditions all conversions depend on: the committed source doc, the directive-number reservation (PD-1), the graph-regen strategy (PD-2), and the epic re-parenting (PD-3).
- **Relevant requirements**: FR-001, FR-002 (PD-1), FR-003 (PD-2), FR-004 (PD-3)
- **Affected surfaces**: `docs/development/quality-and-tech-debt-standing-orders.md` (new, + page-inventory + frontmatter), `docs/development/3-2-page-inventory.yaml`; tracker #2196 (re-parent)
- **Sequencing/depends-on**: none (first). Blocks IC-02, IC-03.
- **Risks**: docs-freshness gates on the new doc (frontmatter description 50-180 chars + page-inventory row — known CI-only gates); keep it a faithful mirror of the source.

### IC-02 — New-artifact conversions (parallelizable)

- **Purpose**: Author the genuinely-new artifacts for sections with no existing coverage.
- **Relevant requirements**: FR-009 (§5a directive+tactic — heaviest, AST gate design), FR-010 (§5b procedure, depends FR-009), FR-007 (§3 procedure+template), FR-011 (§6 directive+tactic + terminology toolguide), FR-012 (§7 — **split into ≥2 WPs**: the 4 heterogeneous rules)
- **Affected surfaces**: new files under `directives/`, `tactics/`, `procedures/`, `toolguides/`, `templates/`; each authors its own inline DRG edges (regen deferred to IC-04)
- **Sequencing/depends-on**: IC-01. FR-010 depends FR-009. Otherwise mutually parallel (disjoint new files).
- **Risks**: FR-009 is tooling-design (AST gate w/ concrete floor + self-mutation test + shrink-only allowlist + routed-count floor) — flag for a post-tasks squad; §7 must be split or it is undersized.

### IC-03 — Extend-conversions (serialized on shared surfaces)

- **Purpose**: Reconcile the sections already covered — extend/reference existing artifacts, authoring only the uncovered atoms (C-001).
- **Relevant requirements**: FR-005 (§1 cadence-only styleguide/paradigm, owns `brownfield-onboarding.paradigm`; C-006 — NOT a required directive; references the squad procedure's playbook, does not re-author it), FR-006 (§2 extend 025/024/040 + owns the frozen-baseline ratchet tactic), FR-008 (§4 — lightest: extend `041` by the live-evidence atom + `testing-principles` + `test-first-bug-fixing` red-first nuance), FR-013 (§8 extend + owns `planning-and-tracking.styleguide`; align ownership-leeway with mission-step prompt language)
- **Affected surfaces**: EXTEND `041`, `025`, `adversarial-squad-deployment.procedure`, `test-first-bug-fixing.procedure`, `brownfield-onboarding.paradigm`, `testing-principles.styleguide`, `planning-and-tracking.styleguide`; new §2 ratchet tactic, §8 leeway/role-sep artifacts
- **Sequencing/depends-on**: IC-01. Shared-surface locks (C-003): `brownfield-onboarding.paradigm` (§1+§2 → single owner), frozen-baseline ratchet (§2+§5 → single owner), `planning-and-tracking.styleguide` (§2+§8 → single owner). WPs sharing a file serialize.
- **Risks**: the reconcile-audit must be real (not a rubber stamp) — the §4/§2 duplication risk is highest here.

### IC-04 — Wiring (single serialized WP, after all conversions)

- **Purpose**: The one place that touches the two remaining shared surfaces — agent-profile `directives:` lists and the generated `graph.yaml`.
- **Relevant requirements**: C-002(c) profile-wiring; C-003 (profile files + graph regen locked here); PD-2
- **Affected surfaces**: `src/doctrine/agent_profiles/built-in/*` (append new directive IDs to relevant profiles), `src/doctrine/graph.yaml` (single regeneration), `tests/doctrine/drg/*` (freshness/cycle/relations pass)
- **Sequencing/depends-on**: ALL of IC-02 + IC-03 (needs every artifact's inline edges authored first). Blocks IC-05.
- **Risks**: known DRG generator gaps (#1755) — the regeneration + cycle-check must be verified, not assumed; a bad edge fails the freshness test here rather than silently at the capstone.

### IC-05 — Capstone: compile the charter

- **Purpose**: Assemble the activated catfooding set into the Spec Kitty Charter (catfooding), reconciling the existing v1.1.5 charter.
- **Relevant requirements**: FR-014, C-007
- **Affected surfaces**: `.kittify/config.yaml` (activation), `.kittify/charter/charter.md` + `references.yaml` (generation), interview `answers.yaml` (manual mirror sub-step)
- **Sequencing/depends-on**: IC-04 (needs the regenerated graph + wired profiles + all artifacts doctor-green). Depends on ALL.
- **Risks**: order-sensitive (activate→generate, C-007); no activation→answers auto-bridge (named manual sub-step); must reconcile not clobber v1.1.5. **Split seam**: if the mission runs long, IC-05 is the clean cut to a thin follow-on mission (charter machinery, not authoring) — recorded so the option is explicit.

## Post-Plan Refinements (binding for /spec-kitty.tasks)

1. **Lanes**: L0 = IC-01 (one foundation WP, blocks all). LA = IC-02 (parallel new-artifact WPs; FR-010 after FR-009; §7/FR-012 split ≥2). LB = IC-03 (extend WPs, serialized where they share `brownfield-onboarding.paradigm` / ratchet / `planning-and-tracking.styleguide`). LC = IC-04 (single wiring WP; sole owner of profile edits + graph regen). Capstone = IC-05 (one WP, depends on all).
2. **owned_files precision**: encode shared-surface locks at file precision so no two WPs own the same artifact. The wiring WP is the ONLY owner of `agent_profiles/**` and `graph.yaml`.
3. **Every conversion WP DoD** carries the C-002 triad (inline DRG edges + `doctor doctrine --json` green + note that profile-wiring is deferred to the wiring WP) and the C-001 overlap-audit as its first subtask.
4. **§4 is light, §5a/§7 are heavy** — size accordingly; flag FR-009 (AST gate) and the §7 split for the post-tasks anti-laziness squad.
