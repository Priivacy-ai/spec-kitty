# Research: P0 Test Failure Resolution — Release Blockers 1298-1305

**Phase 0 output for plan.md**  
**Mission**: p0-test-failure-resolution-1298-1305-01KT1R2G  
**Date**: 2026-06-01

---

## Cluster #1301 — Shared-Package Events Drift

### Root Cause (from issue triage C1/C2 + C99-i)

`spec_kitty_events 5.0.0` was installed in the shared venv while `uv.lock` pins `5.2.0`.
This produced three cascading failure modes:
1. **Missing modules**: `project_lifecycle`, `build_lifecycle` not present in 5.0.0.
2. **Missing symbols**: `MissionOriginBoundPayload`, `LOCAL_ONLY_EVENT_TYPES` absent.
3. **Missing snapshot dir**: `tests/contract/snapshots/spec-kitty-events-5.2.0` did not exist.

Additionally, four residual items survived WP02 of mission 01KSF9HJ (which resolved the bulk cascade):
- `test_no_unauthorized_daemon_call_sites` — daemon allowlist entry missing for a new events call site.
- `test_init_emits_project_init_event_offline` — sync lifecycle test fails in offline mode.
- `test_event_queued_when_no_websocket` — offline-queue path in tracker origin integration.
- `test_fixture_payload_passes_emitter_rules[WPCreated:01JMBYA1B2C3]` — fixture payload missing `actor` and `wp_title` fields.
- `test_vendored_events_tree_does_not_exist_on_disk` — vendored copy `src/specify_cli/spec_kitty_events/` was reintroduced.
- `test_contract_example_round_trip[...check_docs_freshness.md::block-MISSING_FRONTMATTER]` — YAML codeblock missing `# pydantic_model:` frontmatter.

### Fix Approach

**Decision**: Run `uv sync --frozen --all-extras` first to confirm the installed version matches the pin. If drift persists, `uv sync` without `--frozen` to update the lock to the latest compatible version is the escape hatch — but only if the pin itself is wrong.

**Vendored copy**: If `src/specify_cli/spec_kitty_events/` exists, remove it. Per the shared-package-boundary cutover (ADR 2026-04-25-1), the vendored copy must not exist; the package is consumed only via the external PyPI dependency.

**Contract fixtures**: Update `tests/contract/fixtures/` (or inline fixture data) for `WPCreated` payloads to include `actor` and `wp_title` fields that match the `5.2.0` schema.

**YAML codeblock**: Add `# pydantic_model: <ModelClass>` frontmatter to the `check_docs_freshness.md` YAML codeblock that the round-trip test exercises.

**Daemon allowlist**: Add the missing call site to `tests/sync/test_daemon_intent_gate.py`'s allowlist (or fix the source so the call site is no longer unauthorized).

**Rationale**: Each residual item is a small, targeted one-file fix. The version mismatch is the root; the others are fixture/allowlist drift that accumulated between events 5.0.0 and 5.2.0.

**Alternatives considered**: Pinning back to 5.0.0 — rejected because `uv.lock` already pins 5.2.0 and reverting would reintroduce regressions that 5.2.0 was cut to fix.

---

## Cluster #1305 — `next` CLI Exit-Code Regressions

### Root Cause (from issue triage C99-f)

The `next` CLI command returns exit code `1` in scenarios that should return `0`. Pattern observed: `assert 1 == 0` in four tests. Additionally, `decide_next` mocks are no longer being invoked, which means the command is taking a different code path than the tests expect.

**Likely causes** (to verify during WP03):
- A recent refactor of the `next` command's dispatch logic changed the call site for `decide_next` (renamed, moved, or wrapped in a guard).
- Or the mock target path in tests is stale (tests mock a symbol at the old import path after a refactor).
- Or the exit-code computation changed: a new early-return or exception-catch path is returning `sys.exit(1)` before the normal flow that would return `0`.

### Fix Approach

**Decision**: Start by running the four failing tests with `-s --tb=long` to capture the actual code path taken. Then grep `src/specify_cli/next/` for `decide_next` call sites and compare against the mock target in the tests.

**Rationale**: The pattern `decide_next` mocks not invoked + wrong exit code strongly suggests a call-site mismatch after a refactor. This is a one-file fix once the divergence is located.

**Alternatives considered**: Rewriting the tests to match the new code path without fixing the underlying behavior drift — rejected because the goal is to restore correct behavior, not just green tests.

---

## Cluster #1304 — Doctrine / Glossary Anchor Drift

### Root Cause (from issue triage C99-e)

Two distinct problems:

1. **Missing glossary anchors**: `doctrine-pack` and `platform-darwin--platform-linux` anchors are absent from `glossary/contexts/`. These are referenced by doctrine files but the corresponding anchor definitions were never added (or were removed without updating referencing files).

2. **Invalid tactic schema**: The `five-paradigm-parallel-debugging` tactic YAML is either:
   - Missing required schema fields, or
   - References doctrine terms that no longer resolve (stale refs).

### Fix Approach

**Glossary anchors**: Add anchor entries for `doctrine-pack` and `platform-darwin--platform-linux` to the appropriate files under `glossary/contexts/`. The anchor format follows existing entries in that directory.

**Tactic schema**: Read `five-paradigm-parallel-debugging` YAML, compare against the tactic schema (`src/specify_cli/doctrine/` or `glossary/`), add missing required fields, and resolve dangling references.

**Decision**: Fix is purely additive to doctrine/glossary files — no source code logic changes.

**Rationale**: Pure documentation/definition drift; the test suite enforces schema validity and referential integrity for these files, which is correct behavior. The fix is to bring the data files into compliance.

**Alternatives considered**: Marking the tactic as deprecated or removing it — rejected because the tactic is in use and its removal would require broader cleanup outside this mission's scope.

---

## Cluster #1303 — Charter Synthesizer Non-Determinism

### Root Cause (from issue triage C99-d)

Five tests in `tests/charter/synthesizer/test_bundle_validate_extension.py` fail due to:

1. **Manifest hash drift**: The synthesizer computes and stores manifest hashes, but the stored hash does not match the hash computed at test time — implying the generator output is non-deterministic (ordering, timestamps, or floating dict iteration) OR the fixture is stale vs the current generator output.

2. **Direct write primitives leaking**: Code paths that write files bypass `path_guard.py`, meaning the chokepoint test (`test_path_guard`) fails when it asserts that all writes go through the guard.

3. **Chokepoint coverage gap**: The test for chokepoint coverage (`test_chokepoint_coverage`) fails, confirming that not all write paths are registered with the guard.

### Fix Approach

**Manifest hash determinism**: Identify every place the synthesizer constructs the manifest dict (or the artifact that is hashed). Replace any `dict()` iteration or `set`-based construction with an ordered form (`sorted()` keys, `list` instead of `set`). If the hash depends on a timestamp, replace with a content-only hash.

**Write-primitive leak**: Audit `src/specify_cli/charter_lint/synthesizer/` (or equivalent) for any `open(..., 'w')`, `Path.write_text()`, or `shutil` calls that bypass `path_guard.py`. Route them through the guard.

**Chokepoint coverage**: Once all writes go through the guard, `test_chokepoint_coverage` should pass. If it requires explicit registration, add the missing entries.

**Decision**: Fixes are contained to the synthesizer module and `path_guard.py`. The hash fix is purely a determinism fix (no behavior change for users).

**Rationale**: Non-deterministic hashes are a CI reliability hazard — they produce intermittent failures. Centralizing writes through `path_guard.py` is the established pattern in this codebase and the chokepoint test is explicitly designed to enforce it.

**Alternatives considered**: Re-generating and hard-coding fixture hashes on every run — rejected because it hides the non-determinism rather than fixing it.

---

## Execution Order Rationale

Sequential order was chosen (over parallel lanes) because:
- The baseline refresh (WP01) must gate all subsequent work to avoid fixing issues that have already been resolved by intervening commits.
- Each cluster fix requires focused review before proceeding to reduce the risk of one fix masking another failure.
- The repo is the implementer's sole active checkout; sequential reduces merge complexity.

The priority order (#1301 → #1305 → #1304 → #1303) follows the original triage severity:
- #1301 is the largest cascade (most failing tests) and involves a packaging boundary violation.
- #1305 is behavioral drift in a CLI command (exit-code contract).
- #1304 is pure doctrine data drift (lowest code risk).
- #1303 is synthesizer determinism (isolated to charter subsystem).
