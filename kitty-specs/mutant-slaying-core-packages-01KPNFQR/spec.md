# Mission Specification: Mutant Slaying in Core Packages

**Mission Branch**: `mutant-slaying-core-packages-01KPNFQR`
**Created**: 2026-04-20
**Status**: Draft
**Input**: User description: "Kill mutation-testing survivors across compat, kernel, doctrine, charter packages using mutmut 3.5.0 and the mutation-aware test design doctrine. Track issue #711. Targets: ≥80 % mutation score on core business-logic sub-modules (compat.registry, kernel._safe_re, doctrine.resolver, charter.resolver); ≥60 % elsewhere."

## User Scenarios & Testing *(mandatory)*

The "users" of this mission are **Spec Kitty contributors and reviewers**. The value is a test suite that actually detects real bugs — not one that merely executes the code. Each user story is a phase of the mission; they are independently reviewable and ship-worthy on their own.

### User Story 1 — Narrow-surface foundation (compat + kernel) (Priority: P1)

A contributor maintaining the compatibility-shim registry or the kernel utility modules needs confidence that a regression in validation logic or regex safety will fail the test suite. Today, 77 surviving mutants show that boundary conditions, operator selections, and identity-value inputs are not distinguished by existing assertions.

**Why this priority**: The baseline is already stable (no pending mutants in either package), the surface is small (~160 mutants total across both), and the code gates the rest of the compatibility-shim lifecycle and filesystem-IO paths used by every other package. Quick demonstrable wins; sets the pattern for later waves.

**Independent Test**: After this phase, `uv run mutmut run "specify_cli.compat*"` and `uv run mutmut run "kernel*"` must each produce a mutation score at or above the per-sub-module target (≥ 80 % on `compat.registry` and `kernel._safe_re`; ≥ 60 % on `kernel.paths` and `kernel.atomic`). The combined diff can ship as one or two PRs without depending on doctrine or charter changes.

**Acceptance Scenarios**:

1. **Given** the current 20 survivors in `specify_cli.compat.registry`, **When** the phase's new tests land, **Then** re-running mutmut scoped to `specify_cli.compat*` shows at most 4 survivors (≥ 80 % kill rate on the 20 initial survivors, or equivalent-mutant annotations with rationale for any remaining).
2. **Given** the 26 survivors in `kernel._safe_re`, **When** the phase's new tests land, **Then** the kill rate on that sub-module is ≥ 80 % and every remaining survivor is either annotated `# pragma: no mutate` or explicitly listed as "accepted residual" with a one-line reason.
3. **Given** a reviewer opening the PR, **When** they inspect the commit messages, **Then** each commit cites at least one mutmut mutant ID and names the mutation-aware pattern applied (Boundary Pair / Non-Identity Inputs / Bi-Directional Logic).

---

### User Story 2 — Doctrine core (Priority: P2)

A contributor changing doctrine resolver logic, agent-profile schemas, mission metadata, or shared error handling needs confidence that field-presence checks, version-order guards, and schema-validation paths are meaningfully asserted. Today, 466+ doctrine survivors (and ~900 still-pending) signal assertion-strength gaps in the resolution/validation code used on every mission start.

**Why this priority**: Doctrine is loaded at mission boot and at every action boundary. A silent regression here poisons the entire downstream workflow. However, the baseline is not yet stable (mutmut run in progress), so this phase gates on a full baseline being available before WP planning.

**Independent Test**: After this phase, `uv run mutmut run "doctrine*"` scoped to the four target sub-modules (`doctrine.resolver`, `doctrine.agent_profiles`, `doctrine.missions`, `doctrine.shared`) produces ≥ 80 % on `doctrine.resolver` and ≥ 60 % on the other three, measured against the full-run baseline captured after Phase 1 completes.

**Acceptance Scenarios**:

1. **Given** the recorded doctrine survivors from the full baseline snapshot, **When** the phase's new tests land for each of the four target sub-modules, **Then** each sub-module meets its score target or publishes a documented residual list.
2. **Given** a change to `doctrine.resolver._resolve_asset`, **When** a mutation test flips the fallback-vs-primary branch, **Then** an existing assertion-level test fails immediately (no silent regression).

---

### User Story 3 — Charter core (Priority: P3)

A contributor working on the charter synthesizer, context resolver, or evidence pipeline needs the same assertion-strength guarantees as doctrine. Today, 1270+ charter survivors (and ~1800 still-pending) represent the single largest concentration of weak-assertion risk in the repository.

**Why this priority**: Charter is lower in the mission boot path than doctrine — errors here affect charter generation and charter-based gates but do not (usually) break runtime command dispatch. Volume is highest and baseline is least stable, so this phase is explicitly the last of the three and allowed to be the narrowest in coverage.

**Independent Test**: After this phase, `uv run mutmut run "charter*"` scoped to the four target sub-modules (`charter.synthesizer`, `charter.context`, `charter.resolver`, `charter.evidence`) produces ≥ 80 % on `charter.resolver` and ≥ 60 % on the other three, measured against the full-run baseline.

**Acceptance Scenarios**:

1. **Given** the recorded charter survivors, **When** the phase's new tests land for each of the four target sub-modules, **Then** each sub-module meets its score target or publishes a documented residual list.
2. **Given** a reviewer auditing the charter synthesizer change, **When** they apply the ADR 2026-04-20-1 mutation-score lens, **Then** they can confirm that the new synthesizer-pipeline tests distinguish happy-path success from happy-path "nothing broke but nothing changed" silent-no-op survivors.

---

### Edge Cases

- **Equivalent-mutant inflation in migration-adjacent code**: some sub-modules (notably anything doing idempotent dict copies, path normalization, or log formatting) will produce high survivor counts of genuinely equivalent mutants. The mission accepts residuals documented inline with `# pragma: no mutate` + a reason; it does not accept a wholesale "ignore the module" override.
- **Full-baseline drift during Phase 2 / Phase 3 planning**: the ongoing mutmut run may reveal new survivors in doctrine or charter that are not in the current 2026-04-20 snapshot. The phase's WP planning must re-sample before task-list freeze.
- **Tests that pass in main suite but time out in mutmut sandbox**: already covered by the `non_sandbox` / `flaky` markers from ADR 2026-04-20-1. If a kill-the-survivor PR introduces a new sandbox-hostile test, it must be marked `non_sandbox` in the same commit.
- **A surviving mutant whose kill requires a public-API change**: out of scope for this mission. File a follow-up ticket; do not expand scope by rewriting the API.
- **Sub-modules that are primarily data-model shims**: if >50 % of survivors are `no tests` and adding in-process tests would require extensive fixture investment, the sub-module's coverage-gap question is deferred to a separate ticket; this mission's score target does not apply.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Kill ≥ 80 % of `specify_cli.compat.registry` survivors | As a contributor, I want the compat registry's validators to fail on missing, malformed, and boundary-violating inputs so that a regression in shim classification is caught immediately. | High | Open |
| FR-002 | Kill ≥ 80 % of `kernel._safe_re` survivors | As a contributor, I want the regex-safety wrappers to fail on inputs that would bypass their intended guards so that upstream security properties are preserved. | High | Open |
| FR-003 | Kill ≥ 60 % of `kernel.paths` survivors | As a contributor, I want filesystem path helpers to reject the boundary conditions they claim to reject so that path-traversal or case-folding bugs are caught. | High | Open |
| FR-004 | Kill ≥ 60 % of `kernel.atomic` survivors | As a contributor, I want atomic file operations to fail tests when their atomicity contract is broken so that partial writes are never silent. | High | Open |
| FR-005 | Kill ≥ 80 % of `doctrine.resolver` survivors | As a contributor, I want the doctrine resolution chain (shipped → project → legacy) to fail tests when its precedence is inverted or when fallback triggers incorrectly. | High | Open |
| FR-006 | Kill ≥ 60 % of `doctrine.agent_profiles` survivors | As a contributor, I want profile schema validation to fail tests on missing required fields and invalid enum values. | Medium | Open |
| FR-007 | Kill ≥ 60 % of `doctrine.missions` survivors | As a contributor, I want mission metadata validation to fail tests on schema-version mismatches and invalid step-contract references. | Medium | Open |
| FR-008 | Kill ≥ 60 % of `doctrine.shared` survivors | As a contributor, I want shared doctrine utilities (errors, inline-reference checks) to fail tests on malformed payloads. | Medium | Open |
| FR-009 | Kill ≥ 80 % of `charter.resolver` survivors | As a contributor, I want charter resolution to fail tests when fallback paths or precedence rules are inverted. | High | Open |
| FR-010 | Kill ≥ 60 % of `charter.synthesizer` survivors | As a contributor, I want synthesizer pipeline tests to distinguish "generated correct output" from "no-op returned the input unchanged". | Medium | Open |
| FR-011 | Kill ≥ 60 % of `charter.context` survivors | As a contributor, I want charter-context loaders to fail tests on missing sources, malformed policy summaries, or misrouted action doctrine. | Medium | Open |
| FR-012 | Kill ≥ 60 % of `charter.evidence` survivors | As a contributor, I want evidence collectors to fail tests when they silently drop evidence items or miscompute inputs hashes. | Medium | Open |
| FR-013 | Every kill-the-survivor commit cites at least one mutmut mutant ID | As a reviewer, I want commit messages to explicitly name the killed mutants so that the mutation-testing lineage is traceable across snapshots and releases. | High | Open |
| FR-014 | Equivalent mutants are annotated with `# pragma: no mutate` + rationale | As a reviewer, I want every exempted mutant to carry a one-line reason so that the `no mutate` annotations do not become silent escape hatches. | High | Open |
| FR-015 | Residual (below-target) sub-modules publish a `mutation-testing-findings.md` entry | As a contributor, I want any sub-module that is not brought to target to have an explicit residual list with reasons so that the mission's stop condition is auditable. | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Mutation score, core sub-modules | `compat.registry`, `kernel._safe_re`, `doctrine.resolver`, `charter.resolver` reach ≥ 80 % mutation score measured by `mutmut results` post-run. | Quality | High | Open |
| NFR-002 | Mutation score, supporting sub-modules | Other in-scope sub-modules reach ≥ 60 % mutation score. | Quality | High | Open |
| NFR-003 | Equivalent-mutant density ceiling | For each in-scope sub-module, the count of lines carrying `# pragma: no mutate` must not exceed 10 % of the sub-module's **tested-mutant count** (i.e., mutants with a final status other than `no tests` — so `killed + survived + timeout` from `mutmut results`). Above that indicates gaming. Computed per sub-module at the closer subtask of each WP. | Quality | Medium | Open |
| NFR-004 | Per-PR run cost | A scoped mutmut re-run (`mutmut run "<sub-module>*"`) on a changed sub-module completes in ≤ 15 minutes on developer hardware (32-core machine, 16+ GB RAM). | Performance | Medium | Open |
| NFR-005 | Test-suite collection stability | Main suite collection (`pytest --collect-only -m "not non_sandbox and not flaky"`) continues to succeed with 0 errors after every WP lands. | Quality | High | Open |
| NFR-006 | No regression in existing kill rate | Running the full sandbox baseline post-mission does not produce a lower kill rate than the 2026-04-20 snapshot in any out-of-scope sub-module. **Verification**: at each WP's closer subtask, run the full `mutmut results` and diff killed-count per out-of-scope sub-module against the snapshot recorded in `docs/development/mutation-testing-findings.md`. Any regression blocks merge. | Quality | Medium | Open |
| NFR-007 | Baseline re-sample frequency | Phase 2 (doctrine) and Phase 3 (charter) WP planning gates on a fresh mutmut baseline no older than 7 days. | Process | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Local-only tooling | Mission does not introduce CI integration for mutmut. ADR 2026-04-20-1 governs; any exception requires ADR supersession. | Governance | High | Open |
| C-002 | Migration packages excluded | No mutation testing on `src/specify_cli/upgrade/migrations/` or `src/specify_cli/migration/` (semi-equivalent by construction). | Technical | High | Open |
| C-003 | No public-API changes for a kill | If killing a mutant requires altering a public function signature or observable behaviour, file a follow-up ticket; do not expand mission scope. | Technical | High | Open |
| C-004 | No stylistic test refactoring | Tests may be reshaped only when the reshape directly kills a surviving mutant. Style-only changes (renames, comment tweaks, marker consolidation) are out of scope. | Process | Medium | Open |
| C-005 | No 100 % chasing | Mission stops at per-module targets. Remaining survivors above the target are not pursued unless they are symptomatic of an assertion-style bug also present in other hotspots. | Process | High | Open |
| C-006 | No modification of `non_sandbox` / `flaky` marker lists | Existing marker placements from ADR 2026-04-20-1 stay unless a kill-the-survivor test is structurally sandbox-hostile. Any new marker gets a TODO citing root cause. | Governance | Medium | Open |
| C-007 | Target branch | All WP PRs land on `feature/711-mutant-slaying` until the full mission merges. Final mission PR targets `main`. | Process | High | Open |
| C-008 | Tests must be semantically meaningful | Kill-the-survivor tests must verify **observable behaviour** and make independent sense as regression tests. Tests that only exist to assert an internal flag value, a specific `stacklevel`, or an exact internal-state literal (as opposed to the side-effect it causes) are out of scope — they couple the suite to implementation details without adding safety value. Each new test should read as a clear, standalone example of what the unit does correctly or fails on; mutation-killing is a *consequence*, not the *goal*, of writing good tests. | Quality | High | Open |

### Key Entities

- **Mutmut mutant**: a single code mutation identified by an `<module>.<function>__mutmut_<N>` key. Each has one of four in-scope states: `killed`, `survived`, `no tests`, `timeout`. Mission tracks changes in the survivor set.
- **Mutation-aware pattern**: one of `Boundary Pair`, `Non-Identity Inputs`, `Bi-Directional Logic` from `src/doctrine/styleguides/shipped/mutation-aware-test-design.styleguide.yaml`. Every kill-the-survivor commit names which pattern it applied.
- **Residual list**: a documented set of survivors accepted as "not worth killing" — typically equivalent mutants. Published in `docs/development/mutation-testing-findings.md` under a per-WP subheading.
- **Phase gate**: a point where the mission can stop or re-plan. Three gates: end of Phase 1 (compat+kernel), end of Phase 2 (doctrine), end of Phase 3 (charter). Each gate requires fresh mutmut baseline data for the next phase's planning.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The four core sub-modules reach ≥ 80 % mutation score each (measured by `mutmut results` on a fresh scoped run).
- **SC-002**: The eight supporting sub-modules reach ≥ 60 % mutation score each, OR publish a documented residual list with per-mutant rationale.
- **SC-003**: No sub-module in scope carries more than 10 % of its total mutants as `# pragma: no mutate` annotations.
- **SC-004**: Every commit in the mission cites at least one mutmut mutant ID and names the applied mutation-aware pattern in its message body.
- **SC-005**: The main pytest suite continues to collect with 0 errors after every WP lands (verified by a pre-push hook or CI job if available; otherwise by local `pytest --collect-only`).
- **SC-006**: The `docs/development/mutation-testing-findings.md` document is updated at least once per phase with refreshed per-package baselines and the per-phase residual lists.
- **SC-007**: Total elapsed calendar time from mission kickoff to Phase 1 completion is ≤ 2 weeks; Phase 2 is ≤ 4 additional weeks; Phase 3 is ≤ 6 additional weeks. Phases may start in parallel; completion ordering is P1 → P2 → P3.
- **SC-008**: Issue #711 is updated at each phase boundary with a link to the merged PR and the per-sub-module score delta.

## Assumptions

- The background whole-`src/` mutmut run completes within 12 hours of mission kickoff, providing a stable full baseline for Phase 2 and Phase 3 planning.
- The compat package from PR #712 merges into `feature/711-mutant-slaying` before Phase 1 WP implementation begins (the compat code must exist on the mission branch).
- Developer hardware for scoped re-runs meets NFR-004 assumptions (32 cores, 16 GB RAM). Contributors on smaller hardware may halve `max_children` in `pyproject.toml[tool.mutmut]` for their local runs.
- The `non_sandbox` / `flaky` marker taxonomy from ADR 2026-04-20-1 is sufficient to keep the sandbox baseline green across all WPs. New sandbox-hostile tests introduced by kill-the-survivor work get marked with a one-line reason.
- No upstream `mutmut` bug (e.g., the 3.5.0 trampoline `NoneType` issue) is newly unblocked during the mission that would invalidate the current marker list. If one is, the `non_sandbox` marker list shrinks; mission does not regress.

## Doctrine References *(load-bearing for every WP)*

Every kill-the-survivor PR produced by this mission cites the relevant entries below in its commit message. Reviewers use these artefacts — not contributor judgement alone — to validate that a claimed kill applies an accepted pattern rather than a bespoke assertion.

### Tactic

- **`src/doctrine/tactics/shipped/mutation-testing-workflow.tactic.yaml`** — the 5-step human review process (identify targets → generate mental mutants → verify detection → categorise Killed/Survived/No-Coverage/Equivalent → strengthen survivors). WP prompts reference specific step names; review checklists gate against completion of each step.

### Styleguide

- **`src/doctrine/styleguides/shipped/mutation-aware-test-design.styleguide.yaml`** — the pattern library:
  - **Boundary Pair** — for every `>=` / `<=` / `<` / `>` guard, provide three tests (below, at, above threshold). Required for validator-survivor kills in `compat.registry`, `doctrine.resolver`, `charter.resolver`.
  - **Non-Identity Inputs** — arithmetic tests must use values where operator substitution changes the result (no `0` for `+`, no `1` for `*`). Required anywhere arithmetic survivors appear.
  - **Bi-Directional Logic** — `and` / `or` tests must include the exactly-one-true case. Required anywhere boolean survivors appear (many charter `_synthesize_*` branches).
  - **Anti-patterns to reject at review**: Exception-Only Assertion (no-assert tests), Identity Value Inputs, Single-Branch Condition.

### Toolguides

- **`src/doctrine/toolguides/shipped/python-mutation-tools.toolguide.yaml`** + **`PYTHON_MUTATION_TOOLS.md`** — the operator reference tables for Python (comparison, arithmetic, logical, membership/identity, collection aggregates `any`/`all`, loop control `break`/`continue`, string/sequence methods). Each survivor maps to a family; WP prompts cite the family and the recommended kill strategy.
- **`src/doctrine/toolguides/shipped/typescript-mutation-tools.toolguide.yaml`** + **`TYPESCRIPT_MUTATION_TOOLS.md`** — parallel reference retained because adjacent work (dashboard frontend, if it lands in scope) uses Stryker. Not load-bearing for the current Python-only mission scope but co-located for consistency.

### Contributor reference

- **`docs/how-to/run-mutation-tests.md`** — the end-to-end local workflow. WP prompts point new contributors here before their first kill.
- **`architecture/2.x/adr/2026-04-20-1-mutation-testing-as-local-only-quality-gate.md`** — the governing decision record. The `non_sandbox` / `flaky` marker taxonomy defined here is enforced by every WP.
- **`docs/development/mutation-testing-findings.md`** — the durable findings log. Each phase updates it with a fresh snapshot; each WP adds a residual-list subheading for any accepted-equivalent survivors.

### Test annotation conventions *(must match existing tests)*

New tests added by this mission follow the established conventions visible in `tests/specify_cli/compat/`, `tests/kernel/`, `tests/doctrine/`, and `tests/charter/`. Specifically:

- **Module docstring first line.** Every test file opens with a one-line `"""Focused tests for <thing under test>."""` docstring describing the surface being asserted. Mutation-aware tests use the same convention; no separate docstring section for mutation-targeted assertions.
- **`from __future__ import annotations`** immediately after the module docstring. Required for forward references and deferred-evaluation annotations; existing tests are uniform on this.
- **Import grouping** follows the repo's isort convention: stdlib → third-party (`pytest`, `ruamel.yaml`) → first-party (`specify_cli.*`, `doctrine.*`, `charter.*`, `kernel.*`). One blank line between groups. No `from src....` imports; canonical module names only (per `pytest.ini` comment on `pythonpath = src`).
- **`pytestmark`** at module level after the imports, set to `pytest.mark.fast` (or the appropriate existing marker such as `git_repo`, `integration`) as a scalar or list. Do **not** introduce new markers to identify "mutation-aware" tests — the marker taxonomy is deliberately coarse. The `non_sandbox` / `flaky` markers are added only when a kill-the-survivor test is structurally sandbox-hostile.
- **Helper naming** uses the existing `_snake_case` convention for module-private helpers (e.g., `_write_charter_files`, `_make_evidence`). Do not introduce `class TestHelpers:` containers or pytest fixtures for one-off setup that fits in 3–5 lines.
- **Test function naming** uses the existing `test_<subject>_<scenario>` pattern with descriptive scenario suffixes. Boundary-pair tests commonly use `test_<subject>_at_<boundary>` (e.g., `test_classify_at_deadline_is_overdue` from the styleguide). Bi-directional-logic tests commonly use `test_<subject>_<operand>_only` or `test_<subject>_neither`.
- **Assertion style** uses plain `assert <expr>, <message>` or `assert <expr> == <expected>` — no `self.assertEqual(...)` unittest carry-overs. `pytest.raises` for exception assertions; parametrize via `@pytest.mark.parametrize` only when three or more test cases share structure.
- **Type annotations on helpers** follow the existing pattern (`-> None` for test functions, explicit parameter types). `# type: ignore[...]` comments cite the specific rule code and include a one-line reason on the same line.
- **No copy-pasted scaffolding.** If a mutation-aware test reuses a fixture pattern already present in the file, extend or parametrize the existing helper rather than duplicating it.

### DRG graph anchoring

All five shipped doctrine artefacts above are registered as nodes in `src/doctrine/graph.yaml` and anchored to `DIRECTIVE_034` (Test-First Development). A change to any of them — or to the directive — requires ADR supersession before this mission can reference the updated guidance. Runtime doctrine-consistency tests (`tests/doctrine/ -m doctrine`) validate the graph on every commit.

## Dependencies

- PR #712 (the mutation-testing scaffold: ADR 2026-04-20-1, doctrine artifacts, `pyproject.toml[tool.mutmut]`, pytestmark migration, `docs/how-to/run-mutation-tests.md`) must land on `feature/711-mutant-slaying` before Phase 1 implementation.
- The doctrine artefacts enumerated in the **Doctrine References** section above are the authoritative sources. Changes to them during the mission require ADR supersession before being cited by WP prompts.
- Issue #711 on `Priivacy-ai/spec-kitty` is the public tracking anchor.
