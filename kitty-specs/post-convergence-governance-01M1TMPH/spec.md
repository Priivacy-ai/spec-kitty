# Mission Specification: Post-Convergence Governance & Enforcement

**Mission Branch**: `tier3/governance-enforcement`
**Created**: 2026-09-06
**Status**: Draft
**Input**: Post-Convergence Tier-3 — bring the governance record (ADRs), the modularity single-source-of-truth (SSOT), and the module-boundary enforcement gates back into agreement with the code the Convergence (#3881) actually shipped.

## Context

The Convergence merge (#3881, landed 2026-09-05) inverted feature-ownership: this core repo
(`Priivacy-ai/spec-kitty`) is now a **CLIENT**. The authoritative repositories are
`spec-kitty/zeitgeist` and `spec-kitty/saas`; `src/specify_cli/zeitgeist_client/` and
`src/specify_cli/saas_client/` are consumer code (`saas_client` is generated — PR #3589 / saas#300).
This mirrors the shared-package-boundary model (events/tracker are external deps). Authoring/publishing
the API lives upstream; this repo pulls/uses/integrates the clients.

Three governance surfaces still describe the pre-Convergence world:

1. **ADRs** — four Accepted ADRs govern retired subsystems (sync daemon, SaaS rollout/readiness,
   project-sync store, CLI-tracker-gated-by-SaaS-sync-flag). No ADR records the retirement or the
   client-repo inversion.
2. **Modularity SSOT** — the *enforced* authority pair (`pyproject.toml [wheel].packages` +
   `conftest.landscape`/`test_layer_rules`) agrees with reality, but the document that *self-declares*
   authority (`docs/architecture/05_ownership_manifest.yaml`) is stale (names deleted `src/doctrine/`,
   `src/specify_cli/sync/`, `src/specify_cli/saas/`, and never-created `src/lifecycle/`/`src/orchestrator/`),
   and its schema gate `test_ownership_manifest_schema.py` **pins** the stale 8-key vocabulary — so
   correcting the manifest reds the gate (finding D7).
3. **Runtime boundary gate** — the layer chain places `runtime` below `specify_cli`, but ~93
   `runtime→specify_cli` upward edges are ungated: `TestRuntimeBoundary` forbids only `specify_cli.cli`
   and `specify_cli.next`, and the runtime↔doctrine scan never examines `src/runtime` (#3522). New
   inversions land green. `_PRODUCTION_ROOTS` also lists the retired `doctrine` shim and omits
   `mission_runtime`/`glossary` (finding D6).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The governance record reflects the retirement (Priority: P1)

An engineer reading `docs/adr/` to understand the sync/SaaS subsystems finds the four ADRs that govern
them marked **Superseded** with a pointer to a single new convergence-retirement ADR. That new ADR
records what was retired and the client-repo inversion (core = client; `spec-kitty/zeitgeist` and
`spec-kitty/saas` authoritative upstream; `zeitgeist_client`/`saas_client` are consumer code). The
shared-package-boundary ADR (`2026-04-25-1`) stays **Accepted** — it is the precedent the inversion
extends.

**Why this priority**: ADRs are the binding decision record; a stale Accepted ADR for a deleted
subsystem actively misleads. Pure-docs, zero code-behavior risk, unblocks the SSOT narrative.

**Independent Test**: An ADR-hygiene gate asserts each of the four ADRs carries `status: Superseded`
and links the new ADR; the new ADR exists, is `Accepted`, supersedes the four, and names the inversion;
`2026-04-25-1` remains `Accepted`.

**Acceptance Scenarios**:

1. **Given** the four retired-subsystem ADRs, **When** the ADR-hygiene test runs, **Then** each shows
   `status: Superseded` and references the convergence-retirement ADR.
2. **Given** the new convergence-retirement ADR, **When** the test runs, **Then** it is `Accepted`,
   lists the four superseded ADRs, and records the client-repo inversion.
3. **Given** `2026-04-25-1-shared-package-boundary.md`, **When** the test runs, **Then** its status is
   still `Accepted`.

---

### User Story 2 - One canonical, reality-agreeing modularity SSOT (Priority: P1)

A contributor asking "which source owns module boundaries?" is pointed at the **enforced pair**
(`pyproject.toml [wheel].packages` for inventory + `conftest.landscape`/`test_layer_rules` for
direction), documented as canonical in `CLAUDE.md` and `docs/architecture/00_landscape`. The
ownership docs are demoted: `05_ownership_manifest.yaml` is either deleted or regenerated as a clearly
non-authoritative, code-derived artifact, and `05_ownership_map.md` is reduced to narrative-only. The
D7 schema gate no longer pins stale keys (deleted with the manifest, or repointed to reality-checks if
regenerated). The arch docs frame `zeitgeist_client`/`saas_client` as clients of the upstream
authoritative repos.

**Why this priority**: the de-jure authority is the least true and its gate blocks correction. Naming
the enforced pair as SSOT and demoting the stale doc removes a standing contradiction (D1–D4, D7).

**Independent Test**: `test_ownership_manifest_schema.py`'s hardcoded-8-keys assertion is gone/relaxed;
`CLAUDE.md` + `00_landscape` name the enforced pair as canonical SSOT; the surviving ownership artifact
carries no deleted `src/specify_cli/sync/`+`saas/` (or `src/doctrine/`) `current_state` paths; the
enforced pair (`test_pyproject_shape`, `test_layer_rules`) still passes.

**Acceptance Scenarios**:

1. **Given** the demotion decision, **When** the ownership manifest is deleted, **Then**
   `test_ownership_manifest_schema.py` is deleted with it and no other gate references it.
2. **Given** `05_ownership_map.md`, **When** a reader opens it, **Then** it is narrative-only and states
   the enforced pair is the authority.
3. **Given** `CLAUDE.md` / `00_landscape`, **When** a reader looks for the modularity SSOT, **Then**
   both name the enforced pair and describe `zeitgeist_client`/`saas_client` as upstream clients.

---

### User Story 3 - New `runtime→specify_cli` inversions red CI (Priority: P1)

A future contributor who adds a new `runtime → specify_cli` import finds CI **red**: `runtime` now has
the same enforcement `mission_runtime` already has — a clean `should_not import` LayerRule or a
shrink-only allowed-exception ledger pinned to the current ~93 edges. `_PRODUCTION_ROOTS` is refreshed
(drop the `doctrine` shim, add `mission_runtime` + `glossary`).

**Why this priority**: the single highest-value enforcement fix — it makes the largest live inversion
visible instead of green, closing #3522's exact gap.

**Independent Test**: a red-first test adds a synthetic new `runtime→specify_cli` edge to the ledger
input and asserts the gate flags it (or, for a pure LayerRule, that a non-ledgered edge fails); the
current ~93 edges pass; `_PRODUCTION_ROOTS` contains `mission_runtime` + `glossary` and not `doctrine`.

**Acceptance Scenarios**:

1. **Given** the current tree, **When** `test_layer_rules.py` runs, **Then** the new
   runtime→specify_cli guard passes (the existing edges are ledgered/allowed).
2. **Given** a hypothetical new un-ledgered `runtime→specify_cli` edge, **When** the guard runs,
   **Then** it fails (proven by a non-vacuity/red-first test).
3. **Given** `_PRODUCTION_ROOTS`, **When** `test_shared_package_boundary.py` runs, **Then** it lists
   `mission_runtime` + `glossary`, not the retired `doctrine` shim, and still passes.

### Edge Cases

- The ownership manifest is **regenerated-as-derived** instead of deleted → the D7 gate must be
  repointed to reality-checks (every `current_state`/`canonical_package` path exists on disk), not left
  pinning fixed keys. (Decision recorded in plan: default is DELETE; regenerate only if a consumer needs it.)
- The runtime→specify_cli edge count drifts between authoring and merge → use a shrink-only ledger
  (allow ≤ current set) rather than an exact count, mirroring `mission_runtime`, so ordinary refactors
  that *remove* edges don't red CI.
- A `runtime→specify_cli` **function-local** import (#2986) may bypass a module-level ratchet → note as
  out-of-scope follow-up; this mission closes the module-level hole (#3522), not #2986.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Supersede four retired-subsystem ADRs | As a maintainer, I want the four retired-subsystem ADRs marked Superseded with a pointer so the decision record stops asserting deleted designs. | High | Open |
| FR-002 | Author convergence-retirement ADR | As a maintainer, I want one new ADR that supersedes the four and records the client-repo inversion so the retirement + inversion are governed decisions. | High | Open |
| FR-003 | Keep shared-package-boundary ADR Accepted | As a maintainer, I want `2026-04-25-1` left Accepted so the precedent the inversion extends is preserved. | High | Open |
| FR-004 | Name the enforced pair as canonical modularity SSOT | As a contributor, I want `CLAUDE.md` + `00_landscape` to declare `pyproject [wheel].packages` + `conftest.landscape`/`test_layer_rules` the SSOT so module-boundary questions resolve to enforced sources. | High | Open |
| FR-005 | Demote the ownership docs | As a contributor, I want `05_ownership_manifest.yaml` deleted (or regenerated as non-authoritative) and `05_ownership_map.md` narrative-only, so no stale doc self-declares authority. | High | Open |
| FR-006 | Resolve D7 gate coupling | As a maintainer, I want `test_ownership_manifest_schema.py` deleted (if the manifest is deleted) or repointed to reality-checks (if regenerated), so the gate stops pinning stale keys. | High | Open |
| FR-007 | Frame client packages as upstream clients | As a reader, I want arch docs to describe `zeitgeist_client`/`saas_client` as clients of `spec-kitty/zeitgeist` + `spec-kitty/saas`, not in-repo successor subsystems. | Medium | Open |
| FR-008 | Enforce runtime→specify_cli boundary | As a maintainer, I want a LayerRule or shrink-only ledger so a new `runtime→specify_cli` edge reds CI (#3522). | High | Open |
| FR-009 | Refresh `_PRODUCTION_ROOTS` | As a maintainer, I want `_PRODUCTION_ROOTS` to drop the `doctrine` shim and add `mission_runtime`+`glossary` so the retired-import scan covers the real roots (D6). | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Gate runtime cost | Every new/changed architectural gate completes in ≤5 s locally (suite NFR-002 budget). | Performance | High | Open |
| NFR-002 | No code-behavior change | This mission changes governance docs + tests only; it introduces no runtime code-behavior change (no `src/**` production-logic edits beyond import-boundary conformance if any edge must move). | Reliability | High | Open |
| NFR-003 | Non-vacuous enforcement | Every new gate carries a proof-of-teeth (red-first) test showing it fails on a synthetic violation. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Do not re-litigate the inversion | The client-repo inversion is binding architectural context; no zeitgeist/SaaS redesign or authoring epic is created in this repo. | Technical | High | Open |
| C-002 | Enforced pair is the SSOT | `05_ownership_*` may not be treated as authoritative; the enforced pair wins on every conflict (D2). | Technical | High | Open |
| C-003 | Shrink-only ledger | The runtime→specify_cli enforcement must be shrink-only (allow ≤ current edges), never an exact count, to avoid red-on-removal. | Technical | High | Open |
| C-004 | Targeted verification only | The full `tests/architectural/` suite is session-breaking; verify only the gates this mission touches. | Technical | Medium | Open |

### Key Entities

- **ADR**: a decision record under `docs/adr/{2.x,3.x}/`; carries a `status` field (`Accepted` /
  `Superseded`) and cross-references.
- **Ownership manifest / map**: `docs/architecture/05_ownership_manifest.yaml` (+ `.md` mirror); the
  demoted, formerly self-authoritative slice-ownership doc.
- **Enforced SSOT pair**: `pyproject.toml [tool.hatch.build.targets.wheel].packages` (inventory) +
  `tests/architectural/conftest.py` `landscape` fixture / `test_layer_rules.py` (direction).
- **Runtime boundary ledger**: the allowed-exception set gating `runtime→specify_cli` edges in
  `test_layer_rules.py`, mirroring `_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of the four retired-subsystem ADRs are `Superseded` with a pointer; exactly one new
  convergence-retirement ADR exists and is `Accepted`; `2026-04-25-1` remains `Accepted` — verified by a gate.
- **SC-002**: The stale ownership manifest is no longer treated as authoritative (deleted or
  regenerated-as-derived), and no surviving ownership artifact names a deleted `sync/`/`saas/`/`doctrine/` path.
- **SC-003**: A new `runtime→specify_cli` import reds CI (proven by a red-first test); the current ~93
  edges pass; the enforced pair (`test_pyproject_shape`, `test_layer_rules`) stays green.
- **SC-004**: The touched gates (`test_layer_rules`, `test_shared_package_boundary`,
  `test_ownership_manifest_schema` if kept, `test_no_stale_charter_path_literals`,
  `test_no_legacy_terminology`) pass; each new gate runs in ≤5 s.
