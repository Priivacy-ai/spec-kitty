# Tasks — Nonfatal setup-plan auth diagnostics

**Mission**: `setup-plan-auth-diagnostics-nonfatal-01M0QEAD`  
**Planning branch / merge target**: `fix/setup-plan-auth-diagnostics-nonfatal`  
**Spec**: [spec.md](spec.md) · **Plan**: [plan.md](plan.md) · **Contract**: [contracts/setup-plan-result-envelope.md](contracts/setup-plan-result-envelope.md)

## Delivery Strategy

WP01 establishes and implements the canonical local auth classification, including the rejecting-first probe contract and removal of queue-scope tests that falsely describe routing data as authentication. WP02 then changes the mixed local/hosted `setup-plan` command end-to-end: tests are written first inside the package, diagnostics replace early refusal, local outcomes remain authoritative, and only dossier/hosted side effects are suppressed.

This sequencing deliberately keeps production and its tests in the same ownership package so no later WP must edit another lane's files. There are no migrations, external API changes, new dependencies, or network-based test prerequisites.

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Write rejecting auth-probe cases for unknown evaluation, refresh-capable authentication, and queue-scope independence | WP01 | |
| T002 | Make token-manager evaluation failures return `AuthStatus.UNKNOWN` without changing conclusive logged-out handling | WP01 | |
| T003 | Reframe credential-scope regressions as routing-only and remove setup-plan auth-gate expectations | WP01 | [P] |
| T004 | Run focused readiness, credential routing, lint, and compatibility gates | WP01 | |
| T005 | Write rejecting setup-plan helper tests for diagnostics, ordering, result attachment, and disabled/coherent behavior | WP02 | |
| T006 | Write rejecting CLI integration matrix for auth × completeness and structural boundary classes | WP02 | [P] |
| T007 | Introduce immutable hosted-sync diagnostic and side-effect decision composition in setup-plan | WP02 | |
| T008 | Replace auth and structural exit-2 gates with read-only collection while preserving local result authority | WP02 | |
| T009 | Attach ordered warnings to JSON/human local results, including blocked and local-error paths | WP02 | |
| T010 | Gate only hosted dossier/enqueue delivery and prove local lifecycle/artifact/commit behavior remains active | WP02 | |
| T011 | Retire obsolete refusal evidence, preserve boundaries, and run the complete regression/quality gates | WP02 | |

## Work Packages

### WP01 — Canonical local auth classification

- **Prompt**: [tasks/WP01-canonical-local-auth-classification.md](tasks/WP01-canonical-local-auth-classification.md)
- **Goal**: Make the existing readiness probe the unambiguous local auth authority, preserve supported refresh-capable sessions, classify evaluation failures as unknown, and remove the obsolete test-level claim that queue scope proves authentication.
- **Priority**: P0
- **Dependencies**: none
- **Independent test**: `tests/readiness/test_auth_probe.py` proves all supported auth states and queue independence; `tests/sync/test_credential_scope_signal.py` remains green as a routing/store-invariance suite without setup-plan gate assertions.
- **Estimated prompt size**: approximately 260 lines
- [ ] T001 Write rejecting auth-probe contract cases (WP01)
- [ ] T002 Correct indeterminate token-manager classification (WP01)
- [ ] T003 Reframe credential-scope tests as routing-only (WP01)
- [ ] T004 Run focused auth and routing gates (WP01)

**Implementation sketch**: Update tests first, observe the `is_authenticated` exception case fail, make the smallest change in the existing probe, then remove only obsolete auth-gate assertions from credential-scope coverage. Do not change queue parsing or storage selection.

**Parallel opportunities**: T003 touches a separate test module and can be prepared in parallel with T001/T002, but all changes should be validated together before review.

**Risks**: Collapsing unknown into logged out; accidentally narrowing refresh-capable sessions; deleting routing invariance coverage along with obsolete auth assertions; introducing network I/O.

---

### WP02 — setup-plan local/hosted separation

- **Prompt**: [tasks/WP02-setup-plan-local-hosted-separation.md](tasks/WP02-setup-plan-local-hosted-separation.md)
- **Goal**: Always finish setup-plan's local work, expose logged-out/unknown/structural sync conditions as ordered warnings, preserve the local result and exit status, and refuse only unsafe hosted enqueue/delivery.
- **Priority**: P0
- **Dependencies**: WP01
- **Independent test**: The CLI matrix returns the same local result across auth/boundary states, emits the specified warning codes, and proves hosted calls are skipped while local events/artifact/commit paths run.
- **Estimated prompt size**: approximately 440 lines
- [ ] T005 Write rejecting setup-plan helper contracts (WP02)
- [ ] T006 Write rejecting CLI acceptance matrix (WP02)
- [ ] T007 Add diagnostic and hosted-decision composition (WP02)
- [ ] T008 Replace early auth/boundary exits with collection (WP02)
- [ ] T009 Attach JSON and human warnings to local outcomes (WP02)
- [ ] T010 Isolate hosted side effects while preserving local effects (WP02)
- [ ] T011 Retire obsolete refusal evidence, preserve boundaries, and run regression gates (WP02)

**Implementation sketch**: First rewrite the old refusal tests into the new executable contract. Add small immutable values/helpers in `mission_setup_plan.py`, collect auth before and structural evidence after repository resolution, run the unchanged local workflow, condition only the dossier/hosted seam, and emit exactly one result envelope with deterministic warnings. Keep `sync now` and `sync.preflight` behavior unchanged.

**Parallel opportunities**: Within the WP, T005 and T006 affect different test files and can be drafted independently; T011's evidence cleanup can be reviewed alongside implementation. The production changes remain one cohesive edit in `mission_setup_plan.py`.

**Risks**: Multiple JSON documents; diagnostics lost on early local-result paths; local errors accidentally converted to success; auth duplicated through preflight `auth_present`; local lifecycle events suppressed; unsafe dossier enqueue still called; unrelated sync commands weakened.

## Requirement Coverage

- WP01 owns FR-002 and FR-003.
- WP02 owns FR-001 and FR-004 through FR-012.
- Requirement mappings are registered in WP frontmatter by `map-requirements` before finalization.

## MVP Recommendation

The smallest shippable scope is WP01 plus WP02. WP01 alone fixes the canonical unknown classification but does not change the user-visible setup-plan refusal; WP02 completes issue #3621.
