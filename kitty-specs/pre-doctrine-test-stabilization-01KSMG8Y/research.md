# Research: Pre-Doctrine Test Stabilization

**Phase 0 output** | Mission `01KSMG8Y` | 2026-05-27

This document consolidates findings from the pre-mission cross-examination of `upstream/main`
against the 01KSF9HJ triage documentation. All root-cause confirmations were made by reading
source files and running targeted Python expressions against the current codebase.

---

## FR-001 / #1302 — TOML escape bug

**Decision**: Fix the source template at line 168; do not change the rendering engine.

**Root cause confirmed**:
```python
# Confirmed by render_command_template() invocation:
# gemini: TOML ERROR: Unescaped '\' in a string (at line 146, column 68)
# qwen:   TOML ERROR: Unescaped '\' in a string (at line 146, column 68)
```

Source line 168 of `src/specify_cli/missions/software-dev/command-templates/implement.md`:
```bash
CHANGED_PY=$(git diff --name-only --diff-filter=AMR HEAD | rg '\.py$' || true)
```

The `\.` in the `rg` pattern contains a literal backslash. When rendered into a TOML
multi-line basic string (used by gemini and qwen formats), unescaped backslashes are invalid.

**Fix**: Replace `rg '\.py$'` with `grep -E '\.py$'` (no backslash in the regex) or
use `rg '[.]py$'` (character class avoids the backslash entirely).

**Rationale**: `grep -E '\.py$'` is universally available without backslash-in-TOML issues.
`rg` is not universally installed; the fallback `|| true` already handles the case where it
is absent. Switching to `grep -E` removes the dependency and the TOML escape problem.

**Alternatives considered**:
- Double-escape in template (`rg '\\\\.py$'`) — rejected: produces correct TOML but breaks
  Markdown agents that render the template literally.
- TOML literal strings (`'''...'''`) — rejected: the template renderer does not control TOML
  string quoting; the fix must be in the template content, not the renderer.

**Snapshot refresh**: After fixing the template, run:
```bash
PYTEST_UPDATE_SNAPSHOTS=1 pytest tests/specify_cli/regression/ -v
```
All 13 non-migrated agents will produce a diff in their baseline; the diff should be identical
across all agents (only the `rg` → `grep -E` substitution).

---

## FR-002 / #1308 — README Governance layer section

**Decision**: Add the section directly to `README.md`; no new files needed.

**Root cause confirmed**: `grep '## Governance' README.md` → 0 matches.

**Test expectations** (from `tests/specify_cli/docs/test_readme_governance.py`):
1. `## Governance layer` heading must be present
2. `docs/trail-model.md` must be linked within the section
3. `docs/host-surface-parity.md` must be linked within the section
4. (fourth assertion — read test for exact text; likely a section-present check)

**Content guidance**: The section should reference the trail model and host-surface parity
docs. The section content does not need to be lengthy — two or three sentences with the two
required links is sufficient to satisfy all four test assertions.

---

## FR-003 / #1309 — Frontmatter lane regression in wp_files.py

**Decision**: Replace `frontmatter.get("lane")` with `lane_reader.get_wp_lane()`.

**Root cause confirmed** (`src/specify_cli/audit/classifiers/wp_files.py:92`):
```python
lane = frontmatter.get("lane") or frontmatter.get("status")
```

This is a Phase-2 regression — frontmatter `lane` was retired as the authority in 3.0 /
mission 060. The canonical read is `specify_cli.status.lane_reader.get_wp_lane()`.

**Fix surface**: `wp_files.py:92` — replace the two `frontmatter.get()` calls with a call
to `get_wp_lane(feature_dir, wp_id)`. The `feature_dir` and `wp_id` must be derivable from
the file path context already available in the classifier.

**Test**: `tests/specify_cli/test_lane_regression_guard.py` parameterises over source files;
`wp_files.py` must be clean after the fix.

---

## FR-004 / #1310 (partial) — Doctrine CLI group still registered

**Decision**: Remove the `doctrine` group registration; leave the `doctrine.py` file on disk.

**Root cause confirmed** (`src/specify_cli/cli/commands/__init__.py`):
- Line 40: `from . import doctrine as doctrine_module`
- Line 78: `app.add_typer(doctrine_module.app, name="doctrine", help="Manage org-layer doctrine packs")`

The original removal was committed to by mission `excise-doctrine-curation-and-inline-references-01KP54J6`
(Phase 1, WP01 per `tests/specify_cli/cli/test_doctrine_cli_removed.py` docstring). The
re-registration is a regression.

**Fix**: Remove lines 40 and 78. The `doctrine.py` module may remain; it is not imported
elsewhere. No downstream breakage expected — `charter` remains registered separately.

**Risk**: None identified. The `doctrine.py` module registering a Typer sub-app is self-contained.

---

## FR-005 / #1304 — Doctrine / glossary anchor drift

**Decision**: Add missing anchors and fix tactic schema in-place.

**Root cause** (per 01KSF9HJ triage):
- Two missing glossary anchors: `doctrine-pack` and `platform-darwin--platform-linux`
- `five-paradigm-parallel-debugging.tactic.yaml`: schema invalid + unresolved refs

**Investigation needed** (WP03 implementer):
```bash
pytest tests/doctrine/test_glossary_link_integrity.py -v --tb=long 2>&1 | head -60
pytest tests/doctrine/test_tactic_compliance.py -v --tb=long 2>&1 | head -60
```
Output will name the exact context YAML files and which fields are unresolved.

**Known tactic file**: `src/doctrine/tactics/built-in/five-paradigm-parallel-debugging.tactic.yaml`
exists — fix is in-place schema correction.

---

## FR-006 / #1306 — Status / lifecycle event drift

**Decision**: Four targeted fixes; each is independent.

| Sub-issue | Surface | Fix direction |
|-----------|---------|---------------|
| `SpecifyStarted` not emitted | `src/specify_cli/core/mission_creation.py` or emit.py | Emit the event at the correct call site |
| Atomic commit leaves artifacts dirty | `src/specify_cli/git/` (atomic commit helpers) | Ensure status artifact is committed atomically |
| Wrong commit message on lane branch | `src/specify_cli/tasks/move_task.py` | Trace the commit message propagation path |
| `implement` does not block on alloc failure | `src/specify_cli/cli/commands/implement.py` | Add the guard |

**Investigation needed** (WP04 implementer): run each failing test with `--tb=long` before
editing production code to identify the exact divergence point.

---

## FR-007 / #1307 — Charter integration suite regressions

**Decision**: Six independent integration fixes; each requires test-driven investigation.

**Investigation needed** (WP05 implementer): run each test in isolation:
```bash
pytest tests/integration/test_charter_lint_lints_all_layers.py -v --tb=long
pytest tests/integration/test_charter_synthesize_fresh.py::test_synthesize_without_charter_md_fails_actionably -v --tb=long
pytest tests/integration/test_documentation_runtime_walk.py::test_full_advancement_through_six_actions -v --tb=long
pytest tests/integration/test_implement_review_retrospect_smoke.py::test_reject_fix_next_retrospect_smoke -v --tb=long
pytest tests/integration/test_rejection_cycle.py::test_implement_uses_review_cycle_artifact_after_review_claim -v --tb=long
pytest tests/integration/test_specify_plan_commit_boundary.py::test_setup_plan_commits_substantive_plan -v --tb=long
```

Integration tests are slow; use `-x` (fail-fast) when debugging one at a time.

---

## FR-008 / #1305 — `next` CLI exit-code regressions

**Decision**: Fix exit-code propagation in the runtime bridge; do not change the `Decision` model.

**Root cause** (per 01KSF9HJ triage): `decide_next_via_runtime` in `src/specify_cli/next/runtime_bridge.py`
returns `1` where it previously returned `0` for terminal states. Mocks for `decide_next`
are no longer being invoked, suggesting a call-path bypass.

**Investigation needed** (WP06 implementer):
```bash
pytest tests/next/test_next_command_integration.py tests/next/test_query_mode_unit.py -v --tb=long
```

---

## FR-009 / #1301 — Shared-package events drift residual

**Decision**: Fix the six residual items in-place without upgrading the `spec_kitty_events` package version.

**Context**: 01KSF9HJ WP02 fixed the primary cascade (~130 failures) by aligning the installed
package version. The six residual items in #1301 are structural issues that survived the version fix.

**Items and fix directions**:

| Item | Surface | Fix direction |
|------|---------|---------------|
| `restart.py` daemon-allowlist | `tests/sync/test_daemon_intent_gate.py` allowlist | Add `src/specify_cli/sync/restart.py` to the allowlist or refactor the unauthorized call |
| `BuildRegistered` not queued at init | `src/specify_cli/sync/` init path | Emit the event at init |
| `MissionOriginBound` not queued without WebSocket | `src/specify_cli/sync/` | Queue to offline queue when WebSocket is absent |
| `WPCreated` missing `actor`/`wp_title` | `tests/contract/test_handoff_fixtures.py` fixture | Add fields to the fixture |
| Vendored events tree re-appeared | `src/specify_cli/spec_kitty_events/` | Delete the directory |
| YAML codeblock missing `# pydantic_model:` | Contract example fixture YAML | Add frontmatter comment |

---

## FR-010 / #1303 — Charter synthesizer determinism

**Decision**: Fix manifest hash computation to be deterministic; add `path_guard.py` enforcement.

**Root cause**: Synthesizer manifest hashes are computed from file traversal order, which may
vary across runs. Fix: sort all file lists before hashing.

**Investigation needed** (WP08 implementer): identify which hash computation in the synthesizer
uses non-deterministic traversal, then verify the fix by running the test suite twice and
confirming identical hash output.

---

## FR-011 / #1310 (remainder) — Misc debt

**Decision**: Fix five in-scope items; re-defer two with new issues.

| Item | Status | Fix direction |
|------|--------|---------------|
| Auth exit-code (`test_refresh_through_transport` returning 2) | Fix in-scope | Trace exit-code propagation in `src/specify_cli/auth/` |
| JSON output noise (`logged_out_on_connected_teamspace`) | Fix in-scope | Find the print/echo call and guard with `--json` flag check |
| mypy --strict on `executor.py` | Fix in-scope | Run `mypy --strict src/specify_cli/mission_step_contracts/executor.py` and fix errors |
| Legacy kitty-specs WP Pydantic validation | Fix in-scope | Either fix the 6 legacy WP files or add to the validator's exclude list with rationale |
| Mission switching blocked | Fix in-scope | Run `pytest tests/missions/test_mission_switching_integration.py -v --tb=long` |
| `spec-kitty.checklist` skill package missing | **Re-defer** | File new sub-issue; requires template work outside scope |
| Schema-version wording | **Re-defer** | File new sub-issue; minor UX change |

---

## Test-mark inventory for touched directories

| Directory | Current CI job | Mark required |
|-----------|---------------|---------------|
| `tests/specify_cli/regression/` | kernel (inferred) | `pytest.mark.unit` |
| `tests/specify_cli/docs/` | kernel (inferred) | `pytest.mark.unit` |
| `tests/specify_cli/test_lane_regression_guard.py` | kernel | `pytest.mark.unit` |
| `tests/specify_cli/cli/` | fast-tests-cli | `pytest.mark.fast` |
| `tests/doctrine/` | fast-tests-doctrine | `pytest.mark.doctrine` or `pytest.mark.fast` |
| `tests/integration/` | doctrine integration (inferred) | `pytest.mark.integration` |
| `tests/next/` | fast-tests-next | `pytest.mark.fast` |
| `tests/sync/` | fast-tests-sync | `pytest.mark.fast` |
| `tests/contract/` | kernel (inferred) | `pytest.mark.contract` |
| `tests/agent/` | fast-tests-agent | `pytest.mark.fast` |

**Action for WP10**: for each directory, confirm the current `pytestmark` in every `test_*.py`
file matches the expected mark for its CI job. Files missing a mark get one added; files with
a wrong primary mark get it corrected.
