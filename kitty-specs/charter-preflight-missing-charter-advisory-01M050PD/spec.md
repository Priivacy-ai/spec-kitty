# Mission Specification: Charter Preflight Missing-Charter Advisory Mode

**Mission Branch**: `fix/charter-preflight-missing-charter-advisory`
**Created**: 2026-08-16
**Status**: Draft
**Input**: Root-cause investigation filed as Priivacy-ai/spec-kitty#3498: `spec-kitty next` / `spec-kitty implement` hard-block on a missing charter even though a working advisory exemption already exists in `charter_runtime/preflight/runner.py`, because the shared preflight hook used by both consumers never passes `allow_missing_charter=True` (only the read-only dashboard path does). Scope was explicitly widened during discovery to also cover the related-but-distinct legacy-bundle case (`charter.md` present, `charter.yaml` absent — issue #2831), with a stronger warning than the fresh-project case.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Fresh project runs next/implement without a charter (Priority: P1)

A developer creates a brand-new Spec Kitty project and never runs the charter interview. They run `spec-kitty next --mission <handle>` or `spec-kitty implement WP##` to advance a mission. Today this exits 1 with a blocked-reason listing all three charter layers as missing, even though `spec-kitty specify` and `spec-kitty plan` already let them work without a charter.

**Why this priority**: This is the exact scenario reported in #3498 — it silently contradicts specify/plan's documented tolerance and blocks the primary mutation path for every fresh project until governance is set up, which the charter model treats as optional for a new project.

**Independent Test**: Create a project with no `.kittify/charter/` contents at all, run `spec-kitty next` and `spec-kitty implement WP##` in isolation, and confirm both proceed (log a warning, exit 0) instead of aborting.

**Acceptance Scenarios**:

1. **Given** a repo where `.kittify/charter/charter.yaml`, the synced bundle, and the synthesized DRG are all absent, **When** a developer runs `spec-kitty next`, **Then** the command proceeds past the charter preflight check (no exit 1, no `blocked_reason` printed) and logs the existing fresh-project advisory warning.
2. **Given** the same fully-absent charter state, **When** a developer runs `spec-kitty implement WP##`, **Then** the command proceeds to worktree allocation instead of aborting before it.

---

### User Story 2 - Legacy charter.md-only bundle runs next/implement (Priority: P2)

A developer has an older project where `.kittify/charter/charter.md` was authored under the pre-inversion charter workflow, but `charter.yaml` (the current resolving source) was never created. Today this also hard-blocks `next`/`implement`, and gets misdiagnosed as "no charter" even though governance intent clearly existed once.

**Why this priority**: Distinct root cause from Story 1 (confirmed not a duplicate of #3498 during triage — this is #2831's shape) but the same class of over-blocking; fixing it alongside Story 1 avoids leaving a second half-fixed exemption in the same code path.

**Independent Test**: Create a project with only `.kittify/charter/charter.md` present (`charter.yaml` absent, no synced bundle, no synthesized DRG), run `spec-kitty next` and `spec-kitty implement WP##`, and confirm both proceed with a warning that is visibly different from — and more detailed than — the Story 1 warning.

**Acceptance Scenarios**:

1. **Given** `.kittify/charter/charter.md` exists and `.kittify/charter/charter.yaml` does not, **When** a developer runs `spec-kitty next` or `spec-kitty implement WP##`, **Then** the command proceeds (no exit 1) and logs a warning that explicitly names the legacy `charter.md`-only bundle and recommends running the charter migration/regeneration path.
2. **Given** the same legacy-bundle state, **When** the warning is compared to the Story 1 fresh-project warning, **Then** the two messages are textually distinguishable and the legacy-bundle warning is the more prominent of the two.

---

### User Story 3 - Every other charter state keeps blocking exactly as today (Priority: P1)

An operator has a charter that is present but broken in some way that genuinely requires attention — invalid/unparseable `charter.yaml`, a stale synthesized DRG, or partial sync residue (some layers present, some missing, not matching either exemption shape). These must continue to fail closed exactly as they do today.

**Why this priority**: This is the regression guard for the whole mission. The canonical advisory predicate is narrowly scoped; a coding mistake that bypasses it based on prose presence would silently let stale or broken governance state pass, which is the exact failure PR #1665 was written to prevent for real breakage cases.

**Independent Test**: Run the existing charter-preflight test suite (plus new cases for invalid `charter.yaml`, stale synthesized DRG, and one-of-three-missing residue) against `next` and `implement` and confirm every one of them still exits 1 with its original `blocked_reason`.

**Acceptance Scenarios**:

1. **Given** `charter.yaml` exists but fails to parse, **When** a developer runs `spec-kitty next` or `spec-kitty implement WP##`, **Then** the command still exits 1 with the invalid-charter `blocked_reason` and performs no state mutation.
2. **Given** a charter state that is not canonically safe for the missing-charter exemption — e.g. `charter.yaml` missing but a stale or invalid synced bundle / synthesized DRG is present — **When** a developer runs either command, **Then** the command still exits 1 exactly as before this mission, regardless of whether display-only `charter.md` exists.

---

### Edge Cases

- What happens when both `charter.md` and `charter.yaml` are absent, but a stale `.kittify/doctrine/graph.yaml` residue exists from a previous run? Stale canonical residue is not exempt and must keep blocking under Story 3.
- What happens when `charter_source` and `synced_bundle` are `missing` and `synthesized_drg` is `built_in_only`? This is canonically equivalent to a missing project charter because the built-in graph carries no project charter content, so it is advisory whether `charter.md` is present or absent.
- What happens when the canonical missing-charter stack qualifies for advisory mode **and** `charter.md` is present? `charter.md` selects the legacy-bundle warning instead of the fresh-project warning; it never changes `passed`, `blocked_reason`, or any check state. This display-only probe occurs only after canonical freshness states have decided the outcome (doctrine C-001 / FR-016).
- What happens under `--strict`? Per the existing runner contract, `strict` only changes the CLI exit-code mapping when `passed=False`; since both new advisory paths return `passed=True`, `--strict` has no effect on either exemption and must not be made to re-block them.
- What happens when `cfg.enabled` (project preflight config) is `False`? Preflight already short-circuits to `passed=True` before either exemption is evaluated — this mission must not change that short-circuit.
- What happens on the dashboard consumer? `run_preflight_for_dashboard` never blocks server startup regardless of `passed`; the dashboard command must persist and render passed advisory warnings through the same banner channel used for blocking reasons, while a clean pass clears stale warning state.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Wire fresh-project exemption into next/implement preflight | As a developer on a brand-new project, I want `spec-kitty next`/`implement` to not block on a fully-absent charter, so that I can start using mutation commands before setting up governance, matching specify/plan. | High | Open |
| FR-002 | Detect legacy charter.md-only presentation after canonical exemption | As a developer with a pre-inversion `charter.md`-only project whose canonical layers qualify for missing-charter advisory mode, I want `next`/`implement` to continue and identify the legacy presentation without making `charter.md` a governance input. | High | Open |
| FR-003 | Distinct, visible, actionable warning for legacy-bundle case | As a developer seeing the legacy-bundle warning, I want it emitted by every advancing/query and human/JSON `next` path plus `implement`, persisted by the dashboard, textually distinct from the fresh-project warning, and to name the executable `spec-kitty charter generate --no-from-interview` remediation. JSON stdout must remain machine-clean; advisories use stderr. | Medium | Open |
| FR-004 | Preserve all other blocking behavior unchanged | As an operator relying on charter preflight to catch genuinely broken governance state, I want every state outside the canonically safe missing-charter stack (`missing` source + `missing` synced bundle + `missing|built_in_only` synthesized DRG) to keep blocking exactly as before, regardless of `charter.md` presence, so that this fix cannot silently mask real breakage. | High | Open |
| FR-005 | Share mutation-consumer opt-in and emission | As a maintainer, I want `next` and `implement` to use one shared hook for canonical advisory opt-in and warning emission, while the runner owns one canonical qualification predicate, so consumer drift cannot recur. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No added preflight latency | Legacy-bundle detection adds at most one `charter.md` existence check and must not eagerly import the heavyweight `charter` package on the `next` startup path. Preserve the existing clean-tree budget and keep a fresh-process runner import below 500ms. | Performance | Medium | Open |
| NFR-002 | No regression in blocking coverage | 100% of pre-existing charter-preflight automated test cases (invalid, stale, partial-residue states) must continue to pass unmodified after this change. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Canonical state alone decides exemption | Only `charter_source=missing`, `synced_bundle=missing`, and `synthesized_drg in {missing,built_in_only}` become advisory. Display-only `charter.md` may select fresh-vs-legacy warning copy only after that predicate passes; it must never change pass/block behavior. Every stale, invalid, or other partial canonical state keeps blocking. | Technical | High | Open |
| C-002 | Single shared implementation points | Canonical advisory qualification lives once in `runner.py`; mutation-consumer opt-in and warning emission live once in `hook.py::run_preflight_or_abort`, shared by `next` and `implement`. Dashboard presentation may persist the shared result but may not duplicate qualification logic. | Technical | High | Open |
| C-003 | Regression tests required | Automated tests must cover: fully-absent and built-in-only missing stacks pass independently of `charter.md`; legacy prose selects a distinguishable warning visible on `next`, `implement`, and dashboard; invalid/stale/partial-other canonical states still block even when `charter.md` exists. | Technical | High | Open |

### Key Entities

- **Charter preflight result**: The pass/fail outcome (`passed`, `checks`, `blocked_reason`, `warnings`) computed once per `next`/`implement`/dashboard invocation from the current state of the three charter layers.
- **Charter layer**: One of `charter_source` (`.kittify/charter/charter.yaml`), `synced_bundle`, or `synthesized_drg` — each reports a state of `fresh`, `stale`, `missing`, `built_in_only`, or `invalid`.
- **Legacy charter bundle presentation**: Display-only `.kittify/charter/charter.md` exists while resolving `.kittify/charter/charter.yaml` is absent. This fact selects advisory wording only after canonical layer state qualifies; it is never itself an exemption predicate.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A project with zero charter files can run `spec-kitty next` and `spec-kitty implement WP##` successfully on first invocation, with no exit-1 charter-preflight abort.
- **SC-002**: A project with only `charter.md` present can run `spec-kitty next` and `spec-kitty implement WP##` successfully, and the logged warning is textually distinguishable from the fresh-project warning.
- **SC-003**: Every invalid, stale, or partial-residue canonical state still fails closed (exit 1), including when `charter.md` exists; identical canonical states have identical pass/block outcomes with and without `charter.md`.
- **SC-004**: The reproduction steps described in issue #3498 (fresh project, `spec-kitty next` or `implement` blocked on missing charter) no longer reproduce.
