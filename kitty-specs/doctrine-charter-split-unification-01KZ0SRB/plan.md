# Implementation Plan: Doctrine-Charter Split — Single-Path Authority Foundation

**Branch**: `feat/doctrine-charter-split-unification` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-charter-split-unification-01KZ0SRB/spec.md`

The planner will not begin until all planning questions have been answered — captured below (pre-spec 3-lens
squad + operator scope decision + post-spec 3-lens squad, all folded into the spec).

## Summary

Rest the doctrine-pack & charter split on **one** charter read/path authority — `charter.yaml` is the
deterministic, schema-guarded resolution authority and **takes precedence**; `charter.md` is a secondary
rationale/prose read point. The mission (a) retargets the residual `charter.md` **presence/config** readers
that survived #3146 onto the charter-layer authority (`charter/bundle.py` + `charter/charter_yaml_io`),
(b) migrates the retrospective policy into `charter.yaml` governance (new schema + compiler + resolver),
(c) unifies the `meta.json` fail-closed authority reusing the existing `core/paths` typed reader,
(d) deletes the one real upward layer edge and hardens it (+ the read authority) with **non-vacuous**
architectural gates, and (e) lands the wheel packaging-closure **groundwork** (kernel pyproject, doctrine
pyproject + out-of-tree `packs/` mechanism + closure test, charter-wheel ADR). The #3101 kernel→doctrine→charter
wheel **cutover** is a deferred, explicit follow-on (blocked on the kernel wheel; partial cutover forbidden by
ADR `2026-04-25-1` C-007).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml, pydantic (charter schemas), hatchling (packaging), pytestarch (layer gates)
**Storage**: files — `.kittify/charter/charter.{yaml,md}`, `kitty-specs/<mission>/meta.json`
**Testing**: pytest (ATDD red-first per WP, charter C-011); targeted surfaces per WP; named architectural gates
  (`test_layer_rules`, `test_pyproject_shape`, `test_docs_cli_reference_parity`, the new charter-import /
  literal-authority / wheel-closure gates); terminology guard (`test_no_legacy_terminology`)
**Target Platform**: Linux/macOS/Windows CLI
**Project Type**: single project (`src/{kernel,doctrine,charter,glossary,runtime,mission_runtime,specify_cli}/`)
**Performance Goals**: N/A (correctness/structure mission); no hot-path regressions
**Constraints**: charter.yaml precedence (C-001); **no wheel cutover** (C-002, groundwork only); retrospective
  migration backward-compatible (C-003); classify reds vs base, never green-wash (C-004); coord-topology
  hygiene (C-005)
**Scale/Scope**: ~7–9 WPs across 6 implementation concerns; foundation-first (wheel cutover deferred)

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** (Governing Principle; DIR-044). ✅ The mission's spine: `charter.yaml` is the
  one charter read/path authority (`charter/bundle.py` the single door); `core/paths` is the one meta.json
  fail-closed authority (reused, not duplicated — FR-007 explicitly forbids a second home). Chase unification,
  not parity with the `charter.md`-presence dead quirk.
- **Architectural alignment** (DIR-001). ✅ Respects the declared layer order `kernel <- doctrine <- charter
  <- glossary/runtime <- specify_cli` (already CI-enforced by `test_layer_rules`); removes the single real
  upward edge and adds a non-vacuous AST guard. Extends the `2026-04-25-1` shared-package-boundary pattern for
  the wheel groundwork rather than inventing a new one.
- **ATDD-first** (C-011). ✅ Every implementation WP commits a failing-first test before implementation; the
  two red `test_mission_status_aggregate` fail-closed tests are the executable contract for FR-007; NFR-001's
  `charter.md`-deleted fixtures are the contract for the presence retargets.
- **`__all__` / dead-symbol convention** (C-007). ✅ New symbols under `src/charter/`, `src/kernel/` declare
  `__all__` with a caller; the new public meta.json reader is exported and consumed.
- **Non-vacuous gates** (DIR-043). ✅ FR-008 (charter-import), FR-010 (wheel-closure), FR-016 (path-literal
  authority) each ship with a self-mutation proof; a frozen allowlist is shrink-only.
- **Terminology canon.** ✅ Mission (not feature); run `test_no_legacy_terminology` on doctrine/prose changes.
- **Git/workflow discipline** (DIR-045). ✅ Draft-PR-first; operator merges; coord topology; issue-matrix row
  per folded issue.

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-charter-split-unification-01KZ0SRB/
├── plan.md              # This file
├── spec.md              # Mission spec (15 FR + 5 NFR + 5 C)
├── research.md          # Phase 0 — decisions/spikes (packs out-of-tree mechanism, FR-005 schema shape)
├── data-model.md        # Phase 1 — GovernanceConfig.retrospective schema + meta.json reader contract
├── contracts/           # Phase 1 — the charter-read-authority + meta.json fail-closed contracts
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── kernel/                       # layer root — MINT pyproject.toml (FR-009)
├── doctrine/                     # FIX pyproject.toml: kernel dep + out-of-tree packs mechanism (FR-010)
├── charter/
│   ├── bundle.py                 # THE single charter path/read authority home (FR-001)
│   ├── charter_yaml_io.py        # yaml reader consumed by presence gates
│   ├── schemas.py                # ADD GovernanceConfig.retrospective (FR-005a)
│   ├── context.py                # retire :249 OR-gate → charter.yaml-only presence (FR-002)
│   └── synthesizer/…             # emitter wiring (FR-005b) + delete synthesize_pipeline.py:68 edge (FR-008)
├── specify_cli/
│   ├── analysis_report.py        # hash charter.yaml, drop charter.md entries (FR-004)
│   ├── dashboard/charter_path.py # split presence(yaml)/body(md) (FR-003, #3150)
│   ├── retrospective/{policy,mode,gate}.py  # yaml-first resolver + 1 shared _CHARTER_REL (FR-005c)
│   ├── cli/commands/charter/_status_collectors.py  # scope legacy gate + regression test (FR-006)
│   ├── core/paths.py             # promote the ONE public fail-closed meta reader (FR-007)
│   └── mission_metadata.py       # public surface delegates to core/paths authority (FR-007)
packs/built-in/                   # repo-root, doctrine-sibling (governs the FR-010 out-of-tree mechanism)
tests/architectural/
├── test_layer_rules.py           # existing (pytestarch) — augmented/paired with the AST charter gate
├── test_pyproject_shape.py       # existing — disjoint from the new wheel-closure test
├── test_docs_cli_reference_parity.py  # un-inert BOTH fixtures (FR-013)
├── <new> test_charter_no_specify_cli_import.py   # AST-walk guard (FR-008)
├── <new> test_charter_path_literal_authority.py  # ban inline charter path literals (FR-016)
└── <new> test_doctrine_wheel_closure.py          # kernel dep + packs mechanism (FR-010/NFR-004)
.github/workflows/doctrine-charter-tests.yml      # add cli/commands/charter/** (FR-012)
docs/adr/3.x/<new>-charter-wheel-assessment.md    # FR-011
docs/api/{cli-commands,agent-subcommands}.md      # regenerate (FR-013)
```

**Structure Decision**: Single-project layered `src/` — no new top-level trees. The mission seats the charter
path/read authority in the **charter** layer (`bundle.py`), the meta.json fail-closed authority in its
existing **core/paths** home, and the packaging groundwork in the sub-wheel pyprojects — nothing crosses a
layer boundary upward (the one edge that did is deleted).

## Complexity Tracking

*No charter-check violations — none.*

## Implementation Concern Map

> Concerns are NOT work packages. `/spec-kitty.tasks` translates these into executable WPs — one concern may
> become several WPs (e.g. IC-01's per-file retargets), and small concerns may merge. The **write-scope
> discipline** below is load-bearing: FR-001 owns ONLY the shared constant home; each per-file `charter.md`
> repoint folds into the surface WP that already rewrites that file, so coord lanes do not collide
> (architect-alphonso, post-spec).

### IC-01 — Charter presence/path single authority

- **Purpose**: Retarget every residual `charter.md` **presence/path** reader onto the charter-layer authority
  (`charter/bundle.py` + `charter_yaml_io`), keyed on `charter.yaml`, so "does a charter exist / where is it"
  gets one answer that survives `charter.md` deletion.
- **Relevant requirements**: FR-001 (constant home), FR-002 (`context.py:249` OR-gate), FR-003 (#3150 dashboard
  probe split), FR-004 (`analysis_report` hash set), FR-006 (`_status_collectors` legacy-gate scope + regression),
  NFR-001 (charter.md-deleted fixtures per surface).
- **Affected surfaces**: `charter/bundle.py`, `charter/context.py`, `specify_cli/dashboard/charter_path.py`,
  `specify_cli/analysis_report.py`, `specify_cli/cli/commands/charter/_status_collectors.py`.
- **Sequencing/depends-on**: constant-home slice first (FR-001) so per-file repoints import it; the four
  surface repoints are otherwise independent (distinct files → parallelizable WPs).
- **Risks**: the classic fake-green (fixture seeds BOTH files) — NFR-001 mandates each presence fixture
  DELETES `charter.md`. Do **not** touch the C-003 prose readers (`context.py:300-302,366-371`, compact,
  section-bodies).

### IC-02 — Retrospective policy → charter.yaml governance (schema + compiler + resolver)

- **Purpose**: Move the retrospective policy from a **resolving** read of `charter.md` frontmatter to
  `charter.yaml` governance (authoritative, precedence), with `charter.md` frontmatter as an overridden
  secondary — realizing the charter.yaml-precedence model for a decision input.
- **Relevant requirements**: FR-005 (a: `GovernanceConfig.retrospective` schema; b: compiler/emitter
  omit-when-empty; c: yaml-first resolver + one shared `_CHARTER_REL`), SC-002, C-003 (backward compatible).
- **Affected surfaces**: `charter/schemas.py`, the charter compiler/emitter (`charter/synthesizer/…`,
  `write_compiled_charter` path), `specify_cli/retrospective/{policy,mode,gate}.py`.
- **Sequencing/depends-on**: schema (a) → emitter (b) → resolver (c) within the concern; independent of IC-01
  except sharing the `bundle` constants.
- **Risks**: biggest single change; NOT a read-swap (debugger-debbie). Must ship migration/back-compat + three
  regression tests (yaml-wins, both-present-precedence, legacy-md-only). Acceptance Scenario 1 is unsatisfiable
  until schema+emitter exist.

### IC-03 — meta.json fail-closed single authority (#3140)

- **Purpose**: A corrupt/non-dict `meta.json` fails closed everywhere (typed `MissionMetaReadError` or `None`),
  reusing the existing `core/paths` typed authority — never a raw `ValueError`, never a second home.
- **Relevant requirements**: FR-007 (one public reader, enumerated caller census, route unwrapped callers +
  divergent wrappers), NFR-003 (full-census contract test), C-004 (the two aggregate reds are ours).
- **Affected surfaces**: `specify_cli/core/paths.py` (`MissionMetaReadError:506`, `_load_meta_fail_closed:660`),
  `specify_cli/mission_metadata.py` (public surface), the ~108 `load_meta(` call sites (census artifact),
  `mission_runtime/lifecycle_phase.py` (the leak path to the red tests).
- **Sequencing/depends-on**: publish the one public reader first, then route callers; census artifact is a
  reviewable deliverable before the routing WP.
- **Risks**: scope creep (fix only the 2 red tests, leave ~20 leaking) — the census + full-set contract test is
  the guard. Preserve deliberately-silent callers (`load_meta_or_empty`, `on_malformed="none"`).

### IC-04 — Layer edge deletion + durability gates

- **Purpose**: Delete the one real upward edge and make both it and the read authority **durable** with
  non-vacuous gates, so neither silently returns on a later PR.
- **Relevant requirements**: FR-008 (delete `synthesize_pipeline.py:68` + AST-walk charter-import gate),
  FR-016 (ban inline charter path literals + new `charter.md` presence gates), SC-004, NFR-004 (self-mutation
  proofs).
- **Affected surfaces**: `charter/synthesizer/synthesize_pipeline.py`, `tests/architectural/` (two new gates).
- **Sequencing/depends-on**: FR-016's literal gate lands AFTER IC-01/IC-02 unify the readers (else it fails on
  the pre-existing literals) — with a frozen shrink-only allowlist capturing any sanctioned residue.
- **Risks**: a vacuous gate is worse than none — `test_layer_rules`/pytestarch is green WITH the edge present,
  so the AST-walk must actually walk in-function imports (mirror `_collect_specify_cli_imports`), proven by
  self-mutation.

### IC-05 — Wheel packaging-closure groundwork + charter-wheel ADR

- **Purpose**: Make the sub-wheel manifests closed (kernel exists; doctrine depends on kernel and carries
  `packs/`) so the #3101 cutover becomes mechanical — WITHOUT performing the (forbidden-partial) cutover.
- **Relevant requirements**: FR-009 (mint `spec-kitty-kernel` pyproject), FR-010 (doctrine pyproject: kernel
  dep + out-of-tree `packs/` mechanism + non-vacuous closure test), FR-011 (charter-wheel assessment/ADR),
  SC-005, SC-007, C-002 (no cutover).
- **Affected surfaces**: `src/kernel/pyproject.toml`, `src/doctrine/pyproject.toml`, `tests/architectural/`
  (closure test), `docs/adr/3.x/`, `docs/architecture/`.
- **Sequencing/depends-on**: a **research spike** (`hatch build` of the nested doctrine wheel) resolves the
  out-of-tree `packs/` mechanism before the FR-010 WP — captured in research.md.
- **Risks**: `packs/` is a repo-root `doctrine`-sibling, not in-tree — a naive `../../packs` force-include is
  refused by hatchling; the mechanism must be spiked. Confirm no CI job builds/installs the nested wheel
  standalone (else the unresolvable kernel dep breaks CI — C-002 residual). Disjoint from the existing
  `test_pyproject_shape` wheel-completeness gate (verified).

### IC-06 — Charter/doctrine CI hygiene + docs + adjacency investigation

- **Purpose**: Make the doctrine/charter CI signal honest and the advertised CLI surface accurate; close the
  fixed-but-open item; bounded-investigate two adjacent presence/read issues.
- **Relevant requirements**: FR-012 (#3149 path filter), FR-013 (#3107 both parity fixtures + regen docs),
  FR-014 (#3102 closeout), FR-015 (timeboxed #2831/#2992, default defer), SC-006.
- **Affected surfaces**: `.github/workflows/doctrine-charter-tests.yml`,
  `tests/architectural/test_docs_cli_reference_parity.py`, `docs/api/{cli-commands,agent-subcommands}.md`.
- **Sequencing/depends-on**: independent; FR-013 must repoint BOTH fixtures or the gate stays skipped
  (reviewer-renata). FR-015 is bounded — default defer-with-reason, fold only on a proven shared root cause.
- **Risks**: FR-013 half-fix (repoint one fixture) leaves the gate SKIPPED — assert the test RAN GREEN. FR-015
  must not silently pull a P0 into scope.
