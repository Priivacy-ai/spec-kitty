# Research: Execution-State Domain Remediation — #1619 Strangler Fig

**Phase 0 output for**: [plan.md](plan.md)  
**Date**: 2026-06-03

---

## 1. Existing `_resolve_mission_ulid` Availability

**Decision**: Use `_resolve_mission_ulid` from `src/runtime/next/runtime_bridge.py:95` to populate the new `mission_id` field on `MissionRunSnapshot` at `start_mission_run` time.

**Rationale**: The function already reads `meta.json` from the mission directory to extract the canonical ULID. It is accessible at run-creation time because `start_mission_run` is called from `runtime_bridge.py` where the slug is already available. Confirmed at line 145 that the function is already called internally.

**Alternatives considered**: Reading `meta.json` directly in `engine.py` was rejected because the engine should not own the slug-to-path resolution — that belongs to the bridge layer where the slug is already known.

---

## 2. MissionRunSnapshot Snapshot-Copy Sites (blast radius)

**Decision**: Update the following sites in `engine.py` to carry `mission_id` and `mission_slug` through when constructing or copying snapshot fragments:

| Line (approx.) | Pattern | Action |
|----------------|---------|--------|
| 207 | `MissionRunRef(run_id=..., mission_key=...)` | Add `mission_id=mission_id, mission_slug=mission_slug` |
| 227 | `return MissionRunRef(...)` | Same |
| 282–283 | Snapshot-copy block | Add field carry-through |
| 368–369 | Snapshot-copy block | Add field carry-through |
| 393–394 | Snapshot-copy block | Add field carry-through |
| 448 | Partial snapshot ref | Add field carry-through |

Line 465 (`MissionRunStartedPayload`) is out of scope (C-005) — `spec_kitty_events` external type.

**Rationale**: Pydantic `Optional[str] = None` default means existing deserialization of on-disk `state.json` files is unaffected. Only newly-written runs will carry the fields.

**Alternatives considered**: A separate index file (run→mission mapping) was rejected — the back-reference is cleaner as a field on the snapshot itself.

---

## 3. `status/__init__.py` Public API Audit

**Decision**: The following additional symbols need promotion to `__all__` to support `MissionStatus` callers that currently bypass via direct imports:

- `emit_status_transition_transactional` (from `coordination/status_transition.py` — actually this is coordination, not status; external callers of it should go through `MissionStatus.transition()` instead)
- `MissionStatus` (new — add after WP04)
- `ActiveWPStatus` (new — add after WP04)

Symbols currently bypassed by external callers that have genuine external use cases will be enumerated by the WP03 implementer using the AST scan before deciding promote vs. rename. The ~245 count from #1664 should be re-verified at WP03 time.

**Rationale**: Promoting needed symbols is cleaner than leaving bypass imports scattered; it makes the public surface explicit and searchable.

**Alternatives considered**: Re-exporting all internal symbols was rejected — it defeats the purpose of the boundary and makes future restructuring impossible.

---

## 4. Architectural Test Pattern

**Decision**: `test_execution_context_parity.py` (WP02) and `test_status_module_boundary.py` (WP03) both go in `tests/architectural/` and use the dual-mechanism pattern from `test_shared_package_boundary.py`:
- `pytestarch` for rule declaration
- AST scanner for injection proof

**Rationale**: `tests/architectural/` is the established location for invariant-enforcement tests. The existing `test_shared_package_boundary.py` provides a directly reusable pattern for the boundary test. The e2e parity ratchet is an architectural invariant (CWD-invariance), not a feature behavior test, so `tests/architectural/` is correct even though it exercises a multi-step command sequence.

**Alternatives considered**: `tests/integration/` for the ratchet was rejected because the test proves an architectural invariant (CWD-invariance), not end-to-end feature behavior.

---

## 5. `coordination/status_transition.py` Exemption

**Decision**: `coordination/status_transition.py` is exempt from the `status/` boundary enforcement because it is internal domain plumbing — it orchestrates transactional status transitions and is part of the same Mission Management domain as `status/`.

**Rationale**: The boundary rule is "external callers must use the public facade". `coordination/status_transition.py` is not an external caller — it is part of the same bounded module. Its imports of `status.emit`, `status.reducer`, etc. are intentional and correct. The boundary test must explicitly allowlist it.

**Alternatives considered**: Merging `coordination/status_transition.py` into `status/` was considered but deferred — it is infrastructure plumbing that coordinates multiple bounded modules and does not belong inside the status package.

---

## 6. e2e Ratchet Test Fixture Strategy

**Decision**: Use the existing spec-kitty test helper infrastructure (already used in `tests/integration/`) to create a temporary mission in `tmp_path`. The ratchet does not need a real git remote; the local repo + worktree setup is sufficient for CWD-parity testing.

**Implementation approach**:
1. Use `conftest.py` shared fixtures from `tests/integration/conftest.py` to get a repo with initialized `.kittify/`.
2. Create a mission with 2 WPs using `spec-kitty agent mission create` subprocess call or direct Python API.
3. Run the command sequence as subprocess calls (not Python API calls) to ensure CWD is accurately simulated.
4. Assert on the final `agent status` JSON output — lane field equality is sufficient for the ratchet.

**Rationale**: Subprocess invocations are more realistic than Python API calls for CWD-parity testing — they exercise the actual argv/CWD parsing paths that diverge in the wild.

**Alternatives considered**: Mocking the CWD with `os.chdir()` was rejected — it mutates global process state and could cause test isolation failures. Subprocess calls with `cwd=` argument are cleaner.

---

## 7. ADR Format Reference

**Decision**: All three ADRs follow the format in `architecture/3.x/adr/2026-04-25-1-shared-package-boundary.md` with sections: Status, Context, Decision, Consequences.

**File names**:
- `2026-06-03-1-execution-state-domain-model.md`
- `2026-06-03-2-executioncontext-owner-and-committarget.md`
- `2026-06-03-3-effector-actor-model.md`

**Rationale**: Consistency with existing ADR corpus in `architecture/3.x/adr/`.

---

## 8. Glossary Entries Needed

**Decision**: Add or update the following entries in the project glossary (exact file to be located by WP01 implementer):

| Term | Definition |
|------|-----------|
| GovernanceContext | The resolved set of Charter and Doctrine artifacts active for an operation. Owned by the Governance bounded module. |
| ExecutionContext | The resolved set of workspace, branch, feature-dir, and WP identity for an operation. Owned by `core/execution_context.py` (OHS). |
| InfraContext | The resolved set of infrastructure credentials and endpoints for an operation (git remote, CI, etc.). |
| Effector | The Actor realized inside the Execution domain — the execution-bound realization of an Actor. Named concept only; no code type until a concrete actor-kind-mismatch bug triggers materialization. |
| communication artefact | A durable artifact produced or consumed by an Effector during a mission run (e.g., a commit, a PR, a comment). Distinct from planning artifacts (spec, plan, tasks). |
