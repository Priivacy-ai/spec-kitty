# Implementation Plan: Common Docs Doctrine & Reconciliation (Mission A)

**Branch**: `docs/2165-consolidation-research` | **Date**: 2026-06-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/common-docs-consolidation-01KW3Q6M/spec.md`

## Summary

Mission A delivers the *governed foundation* of the Common Docs consolidation: a reconciliation ADR that decides every open mechanism, the built-in Common Docs doctrine (directive + styleguide + tactics) wired into the DRG, and three enforcement "rulers" (the `related:` validator, the frontmatter→inventory lockfile generator + freshness-gate inversion, the anti-sprawl ratchet) authored **report-only** and **each shipped with a self-test**. It mutates **no** doc-tree files. Mission B (the structural move) consumes this foundation across a merge boundary.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing only — typer, ruamel.yaml, pytest, mypy, ruff. **No new dependencies.**
**Storage**: files (markdown frontmatter, `docs/development/3-2-page-inventory.yaml` lockfile, `src/doctrine/graph.yaml` DRG, `src/doctrine/**` artifact YAML)
**Testing**: pytest — every ruler ships a self-test (known-bad fixture → RED, known-good → green); `tests/docs/` + `tests/architectural/` patterns
**Target Platform**: the spec-kitty CLI repository (developer + CI)
**Project Type**: single project (CLI/tooling + doctrine)
**Performance Goals**: the report-only rulers run within the project fast-tier budget (< ~30s)
**Constraints**: **no doc-tree mutation** (C-006); rulers ship **report-only** (C-002); the directive is **bound** to the ratchet (C-003); status frontmatter key is **namespaced** `doc_status` (C-004); the ADR is a **merge boundary** before Mission B (C-001)
**Scale/Scope**: ~6 implementation concerns; the rulers scan a 568-row inventory / ~600 doc pages report-only

## Charter Check

*GATE: charter mode is **compact**.* Governing constraints encoded as C-001…C-006 in spec.md. No charter violations: this mission adds doctrine + tooling + an ADR and changes no product runtime surface. Re-checked post-design: clean (the rulers are additive, report-only, and self-testing; the doctrine artifacts follow the canonical DRG format).

## Project Structure

### Documentation (this mission)

```
kitty-specs/common-docs-consolidation-01KW3Q6M/
├── plan.md              # this file
├── research.md          # Phase 0: the decided mechanisms + ruler approaches
├── data-model.md        # Phase 1: doctrine artifacts, lockfile schema, ruler config
├── quickstart.md        # Phase 1: validation scenarios (run rulers report-only; self-tests RED)
├── contracts/           # Phase 1: the ruler interfaces + self-test contracts
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/doctrine/
├── directive/        # NEW: the Common Docs directive (FR-002) — bound to the ratchet
├── styleguide/       # NEW: the Common Docs styleguide (FR-003) — every rule maps to a check
├── tactic/           # NEW: the Common Docs tactic(s) (FR-004)
└── graph.yaml        # DRG — regenerated via `spec-kitty doctrine regenerate-graph`, freshness-gated

scripts/docs/
├── related_validator.py        # NEW ruler (FR-005) — resolvable-path check, report-only
├── inventory_lockfile.py       # NEW ruler (FR-006) — frontmatter→inventory generator
├── check_docs_freshness.py     # MODIFIED — inverted to generate-and-compare (report-only here)
└── anti_sprawl_ratchet.py      # NEW ruler (FR-007) — report-only, references the directive id

tests/docs/ (and tests/architectural/)
├── test_related_validator.py       # self-test: dangling-edge fixture → RED + checked-count>0
├── test_inventory_lockfile.py      # self-test (LINCHPIN): frontmatter tamper → lockfile changes + RED; lockfile hand-edit → rejected
└── test_anti_sprawl_ratchet.py     # self-test: 4 injection fixtures + the content-anchored floor

architecture/3.x/adr/
└── 2026-06-27-*-common-docs-reconciliation.md   # NEW: the reconciliation ADR (FR-001)
```

**Structure Decision**: single-project tooling + doctrine. The doctrine artifacts live under `src/doctrine/{directive,styleguide,tactic}/` and the DRG `graph.yaml`; the rulers live under `scripts/docs/` with self-tests under `tests/docs/`; the reconciliation ADR is authored in `architecture/3.x/adr/` (its own relocation is Mission B's concern, not A's).

## Complexity Tracking

No charter violations to justify. The one deliberate non-obvious choice — shipping the rulers **report-only** rather than blocking — is mandated by C-002/C-004 and the gate-unmask-cannot-self-validate rule (a ratchet first enforced against an uncleaned tree cannot honestly police it). Mission B flips them.

## Implementation Concern Map

> Concerns, not work packages. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Reconciliation ADR (the serial spine)

- **Purpose**: A single accepted ADR that decides every open mechanism so Mission B opens with zero undecided design.
- **Relevant requirements**: FR-001 (a–g); C-004 (status namespace decided here).
- **Affected surfaces**: `architecture/3.x/adr/2026-06-27-*-common-docs-reconciliation.md`.
- **Decides**: Candidate A (frontmatter SSOT, inventory→lockfile, `citation_refs` dropped); the `doc_status` namespace; the DocFX redirect mechanism (generated `<meta http-equiv=refresh>` stubs into `_site`, since DocFX/GitHub Pages has no native redirect); the glossary read-path mapping (which markdown moves to `context/`, that the dashboard's `.kittify/glossaries/*.yaml` seed read-path is preserved/regenerated, and the doctrine-extraction source); the era-less-ADR migration plan (the 20 flat `architecture/adrs/` ADRs → `adr/3.x/` by date); the 13-section structure; the delete-stale curation + distil-then-retire lifecycle.
- **Sequencing/depends-on**: none — gates IC-02…IC-06.
- **Risks**: the ADR is a **merge boundary** (C-001) — Mission B cannot start until it is accepted+merged; the redirect-mechanism and glossary-read-path decisions are the load-bearing ones (Mission B's NFR-002/C-006 rest on them).

### IC-02 — Common Docs doctrine artifacts + DRG wiring

- **Purpose**: Make the conventions governed, distributable doctrine.
- **Relevant requirements**: FR-002 (directive), FR-003 (styleguide), FR-004 (tactics); C-003, C-005; SC-002.
- **Affected surfaces**: `src/doctrine/{directive,styleguide,tactic}/`, `src/doctrine/graph.yaml`.
- **Sequencing/depends-on**: IC-01 (the ADR fixes the conventions the artifacts codify).
- **Risks**: the directive must be **referenced by the ratchet** (IC-05) to prove binding (C-003); DRG regeneration via `spec-kitty doctrine regenerate-graph --check` has a known footgun (#1755 — read it); the `documentation_policy` directive-codegen path is buggy (#2153) — avoid relying on it.

### IC-03 — `related:` validator (ruler 1, report-only)

- **Purpose**: A resolvable-path cross-link check that Mission B will switch to blocking.
- **Relevant requirements**: FR-005; NFR-001/003; styleguide `related:` rule (FR-003).
- **Affected surfaces**: `scripts/docs/related_validator.py`, `tests/docs/test_related_validator.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: **self-test is the real DoD** — a dangling-edge fixture must assert FAIL and the validator must report the count it checked (assert > 0), else "0 broken" can mean "0 checked."

### IC-04 — Frontmatter→inventory lockfile generator + freshness-gate inversion (ruler 2, report-only)

- **Purpose**: Make in-file frontmatter the SSOT; the inventory becomes a generated/validated lockfile.
- **Relevant requirements**: FR-006; NFR-004; SC-006; (retires `LEAK-FRONTMATTER-MISMATCH`).
- **Affected surfaces**: `scripts/docs/inventory_lockfile.py`, `scripts/docs/check_docs_freshness.py` (inverted), `tests/docs/test_inventory_lockfile.py`.
- **Sequencing/depends-on**: IC-01.
- **Risks**: **the linchpin self-test** — mutate one frontmatter field → regenerate → assert the lockfile **changes** and the gate goes RED; a hand-edit of the lockfile alone is **rejected**. Drop `citation_refs` from the schema. **Retire `LEAK-FRONTMATTER-MISMATCH` only after the new gate is proven red live**, not before. Preserve the inventory's rollup invariants (completeness, ownership, deterministic diff).

### IC-05 — Anti-sprawl ratchet (ruler 3, report-only)

- **Purpose**: Detect a second doc root / missing `index.md` / un-frontmattered ADR / re-introduced shadow tree — emit, don't block (Mission B blocks).
- **Relevant requirements**: FR-007; SC-003/004; C-002.
- **Affected surfaces**: `scripts/docs/anti_sprawl_ratchet.py`, `tests/docs/test_anti_sprawl_ratchet.py`.
- **Sequencing/depends-on**: IC-01, **IC-02** (the directive must exist to reference).
- **Risks**: **four injection fixtures** (one per condition) each assert detection; a **concrete content-anchored floor** (the enumerated 13 sections / "exactly one root") so an empty baseline doesn't pass everything; the violation message **references the FR-002 directive id** (proves the binding, C-003). It runs **report-only** and records the baseline violation count (NFR-003 / SC-004).

### IC-06 — Agent Skills resolution

- **Purpose**: Resolve the dangling `common-docs-write` reference — install the three Common Docs skills or declare them out of scope.
- **Relevant requirements**: FR-008.
- **Affected surfaces**: `.agents/skills/`, `.kittify/command-skills-manifest.json` (if installing); or the consolidation docs (if removing the reference).
- **Sequencing/depends-on**: IC-01 (the ADR records the decision).
- **Risks**: low — but no requirement/scenario may reference a skill that isn't installed; pick one and make the repo consistent.

## Risks (mission-level)

- **The ADR is a merge boundary** (C-001): Mission B is blocked until IC-01 is accepted+merged — sequence the program accordingly.
- **Report-only vs blocking discipline** (C-002): nothing in Mission A flips a ruler to blocking; doing so would violate gate-unmask-cannot-self-validate.
- **Self-test is the real DoD**: each ruler is only "done" when its self-test demonstrably goes RED on the seeded violation — a ruler that can't fail is fake (post-spec squad, renata).
- **DRG regeneration footgun** (#1755): `regenerate-graph` has asymmetric-edge / no-regen-command history — read it before wiring IC-02.
- **Directive-binding** (C-003): an orphan directive doc is a defect; the ratchet must reference it.
- **#2153**: the `documentation_policy` charter-codegen path is buggy — the directive must not depend on it.
