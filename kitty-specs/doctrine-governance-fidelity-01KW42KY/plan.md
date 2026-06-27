# Implementation Plan: Doctrine Governance Fidelity

**Branch**: `mission/doctrine-governance-fidelity` | **Date**: 2026-06-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/doctrine-governance-fidelity-01KW42KY/spec.md`

## Summary

Close three doctrine-governance "signal present, consumer doesn't read it" defects
as file-disjoint lanes: (A) interpolate the `documentation_policy` interview answer
into the generated charter (#2153); (B) make org / extension doctrine-pack agent
profiles visible to `dispatch` routing, to `--profile` governance context, and to
agent-profile projection by wiring `org_dirs` through a single canonical resolver,
guarded by an anti-regression gate (#2156 + #2166); (C) promote the built-in-override
adjudication from test code into production and wire it into `doctor doctrine`, then
retire the override-policy dead-symbol allowlists and lower the `category_7` baseline
7 → 6 (#2082). Approach validated by a pre-planning adversarial squad (4 lenses).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer, rich, ruamel.yaml; internal `doctrine.*`, `charter.*`, `specify_cli.*`, `mission_runtime` packages
**Storage**: Filesystem — `.kittify/config.yaml` (org packs), `.kittify/doctrine/replaceable-builtins.yaml`, `.kittify/charter/interview/answers.yaml`, `kitty-specs/<mission>/`
**Testing**: pytest (`tests/` unit/contract/integration), plus `tests/architectural/` gates (dead-symbol, dead-module, ratchet baselines) and the terminology guard; live-evidence repro via scratch projects with real-format org packs
**Target Platform**: CLI (Linux/macOS), deployed to consumer repos via `spec-kitty init`/`upgrade`
**Project Type**: single (Python CLI)
**Performance Goals**: N/A — correctness/fidelity mission; no hot-path changes
**Constraints**: ruff + mypy zero issues, complexity ≤ 15; no built-in-only regression (NFR-001); live-evidence proof for Lane B (NFR-002); fail-closed governance reads (NFR-004); `topology: lanes`, no coordination branch
**Scale/Scope**: 3 lanes, 4 issues (#2156/#2166/#2153/#2082) + 1 folded layout split-brain (FR-013, to file), **9 implementation concerns**; ~8–12 source files + tests; one new architectural gate; one baseline shrink; charter-activation-gated org overlay

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Charter is the org-resolution entry point (C-008)**: org profiles reach
  dispatch/context/projection ONLY through the charter activation filter
  (`PackContext.activated_agent_profiles`); reuse `build_activation_aware_doctrine_service`,
  never splice raw `org_dirs`. Verified by the architectural-alignment squad
  (unanimous, live-proven) — original raw-`org_dirs` plan rejected. ✅ revised.
- **Canonical sources (C-006)**: reuse `resolve_org_roots`, the activation-aware
  service, and the existing `_doctrine_collect` DRG load; no hand-rolled org-root
  resolution or new DRG plumbing. ✅ planned.
- **Quality gates (NFR-003)**: ruff + mypy clean on new/touched code, complexity
  ≤ 15, focused test per new branch/helper. ✅ enforced per WP.
- **Architectural-gate discipline**: FR-008 new gate carries a concrete floor +
  self-mutation test; FR-011 allowlist shrink is shrink-only and paired with a
  full `tests/architectural/` dry-run pre-PR (C-004, gate-unmask-cannot-self-validate). ✅ planned.
- **Terminology canon**: doctrine/prose touches run the terminology guard pre-push. ✅.
- **No charter violations requiring justification.** Complexity Tracking below is empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/doctrine-governance-fidelity-01KW42KY/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0 (brownfield findings — squad-sourced)
├── issue-matrix.md      # ticket dispositions + claims
├── traces/              # tooling-friction / approach / design-decisions
└── tasks.md             # Phase 2 (/spec-kitty.tasks)
```

### Source Code (repository root)

```
src/
├── charter/
│   └── compiler.py                              # IC-01 (Lane A) — directive interpolation
├── doctrine/
│   ├── agent_profiles/repository.py             # org_dirs layer (read; reference)
│   └── drg/
│       ├── org_pack_config.py                   # resolve_org_roots (canonical helper source)
│       └── override_policy.py                   # IC-06 — promote adjudication into production
└── specify_cli/
    ├── invocation/registry.py                   # IC-03 (Lane B) — dispatch routing org visibility
    ├── tool_surface/profiles/projection.py      # IC-04 (Lane B) — projection org visibility (#2166)
    ├── charter/context.py (or charter/context)  # IC-03 — governance-context org visibility
    └── cli/commands/
        ├── doctor.py / _doctrine_collect.py     # IC-07 (Lane C) — doctor doctrine wiring
        └── (shared org-profile-dir resolver)    # IC-02 — canonical seam (placement TBD in tasks)

tests/
├── architectural/
│   ├── test_no_dead_symbols.py                  # IC-08 — remove _CATEGORY_C override entries
│   ├── test_no_dead_modules.py                  # IC-08 — remove _CATEGORY_7 module entry
│   ├── _baselines.yaml                          # IC-08 — category_7 7→6
│   ├── test_builtin_override_policy.py          # IC-06 — re-point imports to production
│   └── (new) test_org_profile_construction_gate.py  # IC-05 — FR-008 anti-regression gate
├── integration/ + contract/ + unit/             # per-lane red-first + regression tests
```

**Structure Decision**: Single Python CLI project. Three file-disjoint lanes map onto
the existing package layout; the only new file is the FR-008 architectural gate. The
canonical org-profile-dir resolver (IC-02) is a small shared helper whose final module
placement is decided in `/spec-kitty.tasks` (candidate: alongside `resolve_org_roots`
or a `specify_cli` profile-resolution helper) — it must not create a cycle.

## Complexity Tracking

*No Charter Check violations — section intentionally empty.*

## Implementation Concern Map

> Concerns, NOT work packages. `/spec-kitty.tasks` translates these into executable WPs.

### IC-01 — Charter documentation-policy interpolation (Lane A)

- **Purpose**: Render the operator's `documentation_policy` answer into the generated charter directive instead of a hardcoded string.
- **Relevant requirements**: FR-001, FR-002.
- **Affected surfaces**: `src/charter/compiler.py` (directive builder, ~line 942-944).
- **Sequencing/depends-on**: none (self-contained).
- **Risks**: must preserve the empty-answer branch; mirror the `risk_boundaries` shape exactly; single sink (charter.md Project Directives) — no `directives.yaml` ripple.

### IC-02 — Charter-activation-aware org-profile resolver (Lane B foundation)

- **Purpose**: One helper returning the **charter-activated** org-pack profiles as a provenance-bearing record `list[ResolvedOrgProfile]` (`{profile, source_layer, source_path}`) — NOT a bare `list[AgentProfile]` (which carries no provenance; post-tasks squad found that breaks WP04's `source_layer="org"`). Recovers provenance/source_path from the activation-aware service's inner repository (`get_provenance`/`get_source_path`), so every org-honouring consumer resolves the org overlay through the charter gate identically. Composes `resolve_org_roots` + `PackContext.activated_agent_profiles` (three-state) — NOT a raw `org_dirs` list.
- **Relevant requirements**: FR-003, FR-007, C-002, C-006, C-008.
- **Affected surfaces**: new shared helper (e.g. `resolve_activated_org_profiles(repo_root) -> list[AgentProfile]`; placement decided in tasks); reuses `doctrine_service_factory.build_activation_aware_doctrine_service` + `charter/resolver.py` gate.
- **Sequencing/depends-on**: none — foundation for IC-03/IC-04/IC-05.
- **Risks**: must reuse the existing activation wrapper (never re-implement the gate); preserve provenance so IC-04 can set `source_layer`; avoid import cycles; honour the `None`-default (all admitted).

### IC-03 — Dispatch routing + governance-context org visibility (Lane B)

- **Purpose**: `ProfileRegistry` (routing catalog) and the governance-context repo include the **activation-admitted** org subset, **merged onto** their existing project layer (`.kittify/profiles`) — not by passing raw `org_dirs` into `AgentProfileRepository`.
- **Relevant requirements**: FR-004, FR-005, NFR-002, C-008.
- **Affected surfaces**: `src/specify_cli/invocation/registry.py`, `src/charter/context.py` (`_DEFAULT_AGENT_PROFILE_REPO` / context-building path — note it already has the `_build_activation_aware_doctrine_service` precedent for `charter context --include`).
- **Sequencing/depends-on**: IC-02.
- **Risks**: routed-but-context-empty half-fix if only registry is fixed; **must NOT splice raw `org_dirs`** (would bypass de-activation); prove with the TWO-regime live assertion (admitted visible / de-activated hidden).

### IC-04 — Agent-profile projection org visibility / #2166 (Lane B)

- **Purpose**: `default_profile_repository()`/projection emits the **activation-admitted** org agents to the host surface + manifest with a non-builtin `source_layer`, merged onto the existing project layer.
- **Relevant requirements**: FR-006, C-008.
- **Affected surfaces**: `src/specify_cli/tool_surface/profiles/projection.py`.
- **Sequencing/depends-on**: IC-02.
- **Risks**: manifest `source_layer` provenance correctness; de-activated profiles must not project; built-in-only repos unchanged.

### IC-05 — Activation-bypass architectural gate (Lane B)

- **Purpose**: Fail CI if a routing/projection surface splices **raw** `org_dirs`/`resolve_org_roots` that bypass the activation filter (i.e. assert the activation-aware seam is used — NOT merely that `org_dirs` is passed, which would certify the bypass).
- **Relevant requirements**: FR-008, C-003, C-008.
- **Affected surfaces**: new `tests/architectural/` gate; scoped allowlist of confirmed built-in-only sites with rationale.
- **Sequencing/depends-on**: IC-03, IC-04.
- **Risks**: gate must assert the CONTRACT (activation seam) not a fakeable proxy (`org_dirs` presence); non-vacuous floor + self-mutation test; do not over-scope to intentional built-in-only sites (`agent/tasks.py`, `charter/context` language cache).

### IC-09 — Unify activation-CLI pack layout with runtime resolution (Lane B)

- **Purpose**: Make `charter activate/deactivate agent-profile <id>` resolve org packs from the **same** layout runtime uses, so activating a runtime-resolvable org profile no longer fails "Unknown agent-profile ID" (folded layout split-brain).
- **Relevant requirements**: FR-013.
- **Affected surfaces**: `src/specify_cli/cli/commands/charter/_layer_roots.py:24-26` (the `(org_root / "doctrine").is_dir()` gate that rejects flat packs), `src/charter/pack_manager.py:_scan_layer_dirs:566-567` (org-layer branch scans `<pack>/doctrine/<plural>/org/`). Reference contract: `src/doctrine/drg/org_pack_config.py:resolve_org_roots` + `DoctrineService._org_dirs` (flat `<pack>/<plural>/`).
- **Sequencing/depends-on**: independent of IC-02..05 but completes the #2156 end-to-end story for activation-list projects; verify before Lane B's two-regime proof.
- **Canonical layout (operator-decided 2026-06-27)**: `<pack>/agent_profiles/` (the flat runtime layout) is canonical. The **charter activation subsystem** is the offender — its `<pack>/doctrine/<plural>/org/` nesting is the mess to remove (unification, not parity).
- **Approach (post-tasks squad — BINDING)**: implement a **layout-tolerant resolver — flat preferred, nested fallback** — as the DEFAULT, NOT a hard cutover. A hard cutover turns the non-owned `tests/charter/test_pack_manager_catalog.py` (≥6 nested fixtures) RED out-of-ownership. Tolerant-default makes flat work (FR-013) while keeping existing nested fixtures green.
- **Risks**: the org-layer scan convention is shared across **all** org-pack kinds (directives/tactics/styleguides/…). Add regression coverage per kind touched; verify `charter list/activate/deactivate` for ≥2 kinds.

### IC-06 — Override-adjudication promotion to production (Lane C foundation)

- **Purpose**: Move `find_overridden_builtin_urns` / `find_unsanctioned_overrides` / `UnsanctionedOverride` from `tests/architectural/test_builtin_override_policy.py` into `src/doctrine/drg/override_policy.py` (pure, fail-closed); re-point the test to import from production.
- **Relevant requirements**: FR-009, NFR-004.
- **Affected surfaces**: `src/doctrine/drg/override_policy.py`, `tests/architectural/test_builtin_override_policy.py`.
- **Sequencing/depends-on**: none — foundation for IC-07/IC-08.
- **Risks**: must keep `tests/doctrine/test_drg_merge.py` + the override test green; preserve fail-closed semantics.

### IC-07 — doctor doctrine override diagnostics wiring (Lane C)

- **Purpose**: `doctor doctrine` reports unsanctioned built-in overrides in a deployed repo (org-packs-present branch), guarded by the existing no-packs short-circuit; project-tier overrides stay ungoverned (documented).
- **Relevant requirements**: FR-010, FR-012.
- **Affected surfaces**: `src/specify_cli/cli/commands/doctor.py` / `_doctrine_collect.py` (reuse the already-built merged 3-layer DRG); JSON + human emitters; `healthy`/exit-code path.
- **Sequencing/depends-on**: IC-06.
- **Risks**: do not introduce new DRG plumbing (C-006); diagnostics only meaningful when `registry.packs` non-empty; don't flip healthy repos to RC≠0.

### IC-08 — Dead-symbol allowlist retirement + baseline shrink (Lane C)

- **Purpose**: Remove the 4 override-policy symbols from `_CATEGORY_C_BUILTIN_OVERRIDE_POLICY` and the module from `_CATEGORY_7_GRANDFATHERED_ORPHANS`; lower `category_7_grandfathered_orphans` baseline 7 → 6.
- **Relevant requirements**: FR-011, C-004; references #2049 (burn-down item, no sweep).
- **Affected surfaces**: `tests/architectural/test_no_dead_symbols.py`, `test_no_dead_modules.py`, `_baselines.yaml`.
- **Sequencing/depends-on**: IC-06, IC-07 (symbols must have a live runtime caller first).
- **Risks**: gate-unmask cannot self-validate — pair with a full `tests/architectural/` (incl. CI-only shards) dry-run before the PR.
