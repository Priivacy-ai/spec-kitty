# Research: Test Stabilization — Pre-Existing Failure Cluster Fix

*Compiled from direct codebase analysis during issue triage (2026-06-02)*

---

## Cluster #1303 — Charter Synthesizer Non-Determinism

### Decision: sort artifacts by (kind, slug) before hashing

**Rationale**: The test `test_manifest_hash_is_stable_regardless_of_artifact_insertion_order` explicitly verifies that insertion order does not affect `manifest_hash`. This means the promote pipeline must sort artifacts before computing the hash. If any code path builds the artifact list without sorting, two runs with the same logical content but different insertion order will produce divergent hashes — causing the stored manifest to fail re-validation.

**Alternatives considered**: Sorting at serialization time (inside the YAML dumper) — rejected because the sort must be applied before the hash is computed, not after. The hash is over the canonical YAML bytes, so the sort must precede serialization.

**Root cause confirmed**: The test infrastructure (`_make_v2_manifest` in the test fixtures) creates manifests with a fixed sort — but the production promote pipeline may not apply the same sort. The fix is to add `sorted(artifacts, key=lambda a: (a.kind, a.slug))` in the promote() function before hashing.

---

### Decision: PathGuard is the sole write primitive for synthesizer modules

**Rationale**: The R-10 lint test (`test_no_direct_writes_in_synthesizer`) greps `src/charter/synthesizer/` for direct `Path.write_text`, `Path.write_bytes`, `Path.mkdir`, and `Path.replace` calls. If any module uses these directly, the test fails. The intent is to guarantee that all filesystem writes from the synthesizer pass through `PathGuard`, which enforces that writes only land in `.kittify/doctrine/` or `.kittify/charter/`.

**Investigation method**: Run the lint grep that the test uses:
```bash
grep -rn "\.write_text\|\.write_bytes\|\.mkdir\|\.replace(" \
  src/charter/synthesizer/ \
  --include="*.py" \
  | grep -v "path_guard.py"
```
Any hit is a bug.

**Fix**: Replace each direct call with the corresponding `PathGuard` method.

---

## Cluster #1304 — Doctrine/Glossary Anchor Drift

### Decision: fix content, not tests

**Rationale**: DIRECTIVE_010 and C-002 both require that test fidelity is preserved. The `test_glossary_link_integrity` test slugifies headings using a well-defined algorithm (lowercase, strip backticks, replace spaces with dashes, collapse multiple dashes). The fix must add the missing headings or correct the link fragments — weakening the test is not permitted.

**Anchor slugification algorithm** (from `test_glossary_link_integrity.py`):
```python
def _slugify_heading(text: str) -> str:
    heading = re.sub(r"\s+#+\s*$", "", text.strip())
    heading = heading.replace("`", "").lower()
    heading = re.sub(r"[^a-z0-9 _-]", "", heading)
    heading = heading.replace(" ", "-")
    heading = re.sub(r"-{2,}", "-", heading).strip("-")
    return heading
```

To produce anchor `doctrine-pack`, the heading must be `## Doctrine Pack` (or any casing/punctuation that slugifies to `doctrine-pack`). To produce `platform-darwin--platform-linux` (double dash), this is unusual — a double dash in the fragment means the heading itself contained a double dash or two adjacent words separated by special chars. Investigate the actual link text to determine whether the fragment is correct or the link is simply mistyped.

**Tactic schema fix**: Load the `five-paradigm-parallel-debugging` tactic YAML and run `spec-kitty doctrine validate` or directly validate with Pydantic. The error will name the missing/invalid field. Fix in the YAML source.

---

## Cluster #1305 — `next` CLI Exit-Code Regressions

### Decision: exit-code contract is DecisionKind → sys.exit()

**Rationale**: The integration tests are CliRunner-based and check `result.exit_code`. The mapping must be:
- `DecisionKind.terminal` → `sys.exit(0)` — agent completed all steps
- `DecisionKind.blocked` → `sys.exit(1)` — agent cannot proceed (blocked, failed, nonexistent feature)
- `DecisionKind.step` → `sys.exit(0)` — agent has a next step to execute

**Investigation**: The test `test_result_success_calls_decide_not_query` fails because the `success` result routes to the query path. In `src/runtime/next/_internal_runtime/engine.py` (or `runtime_bridge.py`), there is likely a conditional that routes `success` to `query_next` instead of `decide_next`. The condition may be inverted or missing a case.

**File to check**: `src/specify_cli/next/__init__.py` — the Typer command that calls the engine and maps the result to `sys.exit()`. If the exit-code mapping is correct there, the bug is upstream in the engine routing.

---

## Cluster #1307 — Charter Integration Suite

### Decision: repair shim re-exports, not integration tests

**Rationale**: The charter.py split (WP06/WP08 of the prior mission) moved code from a 3328-line monolith into a per-subcommand package structure with a `charter_runtime/` umbrella. A `sys.modules` shim was added to preserve legacy dotted import paths. If the shim does not correctly forward all symbols, integration tests that import via the old path will get `AttributeError` or `ImportError` at runtime.

**Investigation approach**:
1. Run `pytest tests/charter/ -x 2>&1 | head -60` to see the first failure.
2. Identify the import that fails.
3. Trace it through `src/specify_cli/charter_runtime/__init__.py` to see which re-export is missing.
4. Add the missing re-export to the shim.

**Dependency on WP02**: Some integration suite failures may be caused by the synthesizer hash regression (e.g., a test that synthesizes a charter and then validates the manifest). WP06 must be sequenced after WP02.

---

## Cluster #1310 Residual — Auth, Invocation, WP Files, mypy, Mission Switching, Base-Flag

### Auth transport exit code 2

**Decision**: Fix the test fixture — the auth pipeline itself is likely correct.

**Rationale**: Exit code 2 in Typer means a usage error (missing required parameter, type mismatch) before the command body runs. The `test_refresh_through_transport` test uses CliRunner to invoke `sync status --check`. If the sync subsystem is stubbed but a required config (e.g., teamspace ID, storage path) is not provided, Typer will exit with code 2 before reaching the auth token refresh logic. The fix is to provide the missing config in the test fixture, not to change production code.

### Invocation JSON noise

**Decision**: Add a conftest-level auth-state teardown fixture.

**Rationale**: `logged_out_on_connected_teamspace` is a condition that is set by one test and not cleaned up. Because the invocation tests capture JSON from stdout, any extra log line or diagnostic that the condition causes will corrupt the JSON parse. The fix is a `conftest.py` `autouse` fixture that resets the condition to `False` (or `None`) after each test.

### Schema version wording drift

**Decision**: Determine if the production message was intentionally changed; if yes, update the test assertion; if no, restore the original message.

**Rationale**: This is a string drift issue. The test asserts a specific error message wording. If the message was changed as part of another mission's work, the test assertion is stale. If the message was changed accidentally, the production code needs to be reverted. Check git blame on the production file to determine intent.

### WP file Pydantic validation

**Decision**: Update the 6 legacy WP files to the current schema.

**Rationale**: C-004 in the spec states this preference. The Pydantic model is the source of truth; WP files are content. Running `pytest tests/specify_cli/status/test_wp_metadata.py -v` will name the failing files and the validation errors. Each file needs the missing field added or the incorrect value corrected.

### mypy strict on executor.py

**Decision**: Add type annotations to `executor.py` until `mypy --strict` passes.

**Rationale**: This is a pure annotation fix. Run `mypy --strict src/specify_cli/mission_step_contracts/executor.py` to see the exact errors. Common causes: missing return type, untyped function argument, use of `Any` without explicit import.

### Mission switching

**Decision**: Relax the guard condition that blocks valid mission-type switches.

**Rationale**: The test `test_mission_switching_integration` × 2 verifies that switching between mission types works. The guard may be checking for exact mission-type equality or a stale condition. Read the guard in the mission switching code path and identify why it blocks valid transitions.

### Implement base-flag plumbing

**Decision**: Wire `--base` through all layers of the implement command.

**Rationale**: The `--base` flag was added in FR-021 (mission `068-post-merge-reliability-and-release-hardening`). The test `test_implement_base_flag` verifies the flag is passed through to the bulk-edit gate. If the test fails, the flag is being dropped at some intermediate layer. Trace from `src/specify_cli/cli/commands/implement.py` through to the bulk-edit gate function.

---

## Cross-Cutting Findings

### Test isolation is the dominant theme in cluster #1310

Multiple sub-failures in #1310 share a root cause pattern: test state leaks across test cases because auth/config state is set globally and not torn down. The fix pattern is consistent: add `autouse` conftest fixtures that reset global state after each test.

### The charter refactor (WP06/WP08) is the dominant structural risk

The charter.py split and `sys.modules` shim layer is the highest-risk change from the prior mission. Both WP02 (synthesizer) and WP06 (integration suite) are consequences of that refactor. WP06 is intentionally sequenced after WP02 to avoid conflating the two root causes during debugging.

### No new test infrastructure is needed

All five clusters can be fixed using existing test patterns. No new test utilities, fixtures, or conftest abstractions are required beyond the auth-state teardown fixture for WP04.
