---
work_package_id: WP07
title: NFR Enforcement (Perf Test + Coverage CI Guard)
dependencies:
- WP06
requirement_refs:
- NFR-001
- NFR-003
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
- T038
phase: Phase 4 - End-to-end fidelity
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "53630"
history:
- at: '2026-04-25T17:54:43Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: tests/perf/
execution_mode: code_change
owned_files:
- tests/perf/__init__.py
- tests/perf/test_loader_perf.py
- pyproject.toml
- .github/workflows/ci-quality.yml
role: implementer
tags: []
---

# Work Package Prompt: WP07 – NFR Enforcement (Perf + Coverage CI Guards)

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

## Branch Strategy

- **Planning/base branch at prompt creation**: `main`
- **Final merge target for completed work**: `main`
- **Actual execution workspace is resolved later** by `/spec-kitty.implement`. Trust the printed lane workspace.

## Objectives & Success Criteria

Wire the NFR thresholds (perf, coverage, mypy) into the test / CI surface so regressions break the build.

Success criteria:
1. Loader p95 latency < 250 ms locally on the ERP fixture (NFR-001).
2. ERP full walk wall-clock < 10 s (NFR-004) — this is co-asserted with WP06's integration suite.
3. `mission_loader/` package coverage gate ≥ 90% enforced in CI (NFR-003).
4. `mypy --strict` enforced on `mission_loader/` and the new `_internal_runtime/discovery.py` extensions in CI (NFR-005).

## Context & Constraints

- WP07 is mostly configuration / measurement. Resist the urge to optimize — if a perf assertion fails, surface it and decide; do not patch code outside `tests/` or the CI YAML in this WP.
- `pyproject.toml` already has a `pytest --cov` invocation somewhere — locate it before adding a new one.
- See [research.md](../research.md) §R-008 for envelope shape (referenced but not modified here).
- See `.github/workflows/ci-quality.yml` for the existing CI structure.

## Subtasks & Detailed Guidance

### Subtask T035 — Loader p95 < 250 ms perf test

- **Purpose**: NFR-001.
- **Steps**:
  1. Create `tests/perf/__init__.py` (empty).
  2. Create `tests/perf/test_loader_perf.py`:
     ```python
     def test_load_p95_under_250ms(tmp_path):
         """50 invocations of validate_custom_mission against the ERP fixture."""
         _setup_project(tmp_path, fixture="erp-integration")
         from specify_cli.mission_loader.validator import validate_custom_mission
         from specify_cli.next._internal_runtime.discovery import DiscoveryContext
         ctx = DiscoveryContext(project_dir=tmp_path)

         times: list[float] = []
         for _ in range(50):
             t0 = time.perf_counter()
             report = validate_custom_mission("erp-integration", ctx)
             times.append(time.perf_counter() - t0)
             assert report.ok, report.errors

         p95 = sorted(times)[int(0.95 * len(times))]
         # Allow 1.5x slack on CI runners.
         threshold = 0.25 if os.environ.get("CI") != "true" else 0.375
         assert p95 < threshold, f"p95={p95*1000:.1f}ms exceeds {threshold*1000:.0f}ms"
     ```
- **Files**: `tests/perf/test_loader_perf.py`.

### Subtask T036 — ERP fixture full walk < 10 s

- **Purpose**: NFR-004.
- **Steps**:
  1. Add to `tests/perf/test_loader_perf.py`:
     ```python
     def test_erp_full_walk_under_10s(tmp_path):
         """Full ERP runtime walk wall-clock budget."""
         t0 = time.perf_counter()
         # Same flow as test_erp_full_walk in WP06; minimal duplication acceptable
         # because perf tests target a different invocation cadence.
         _run_erp_walk(tmp_path)
         elapsed = time.perf_counter() - t0
         assert elapsed < 10.0, f"ERP walk took {elapsed:.2f}s"
     ```
  2. `_run_erp_walk(tmp_path)` is a private helper duplicated from WP06's integration test (with mocked executor) — do NOT import from `tests/integration/` (test directories shouldn't import from each other in pytest).
- **Files**: `tests/perf/test_loader_perf.py`.

### Subtask T037 — Coverage CI guard for `mission_loader/`

- **Purpose**: NFR-003.
- **Steps**:
  1. Read existing `pyproject.toml` and `.github/workflows/ci-quality.yml`.
  2. If `pyproject.toml` has `[tool.coverage.run]` or similar, ensure `mission_loader` is in `source = [...]`. Add a per-package fail-under:
     ```toml
     [tool.coverage.report]
     fail_under = 0
     # Per-package gate for new code (Phase 6 #505):
     # See .github/workflows/ci-quality.yml for the strict per-package gate.
     ```
  3. In `.github/workflows/ci-quality.yml`, add a new step `mission-loader-coverage`:
     ```yaml
     - name: Mission loader coverage gate (>=90%)
       run: |
         uv run pytest \
           --cov=src/specify_cli/mission_loader \
           --cov-report=term-missing \
           --cov-fail-under=90 \
           tests/unit/mission_loader/ tests/integration/test_mission_run_command.py
     ```
- **Files**: `pyproject.toml`, `.github/workflows/ci-quality.yml`.
- **Notes**: Don't lower the existing global `fail_under` — the new gate is additive.

### Subtask T038 — `mypy --strict` on new modules in CI

- **Purpose**: NFR-005.
- **Steps**:
  1. Inspect `.github/workflows/ci-quality.yml` for an existing mypy step. If one runs `mypy --strict src/`, the new package is automatically covered — verify by running it locally.
  2. If the existing step targets a narrower scope, add `src/specify_cli/mission_loader` to the args.
  3. If no mypy step exists, add one:
     ```yaml
     - name: mypy --strict on new modules
       run: |
         uv run mypy --strict src/specify_cli/mission_loader src/specify_cli/next/_internal_runtime/discovery.py
     ```
- **Files**: `.github/workflows/ci-quality.yml`.
- **Parallel?**: [P] with T035–T037.

## Test Strategy

```bash
UV_PYTHON=3.13.9 uv run --no-sync pytest tests/perf/test_loader_perf.py -q
UV_PYTHON=3.13.9 uv run --no-sync pytest --cov=src/specify_cli/mission_loader --cov-fail-under=90 tests/unit/mission_loader/ tests/integration/test_mission_run_command.py -q
UV_PYTHON=3.13.9 uv run --no-sync mypy --strict src/specify_cli/mission_loader src/specify_cli/next/_internal_runtime/discovery.py
```

CI YAML changes: confirm `gh workflow run ci-quality.yml` (if available) or `actionlint` clean.

## Risks & Mitigations

- **Risk**: Perf test flakes on slow CI runners.
  - **Mitigation**: 1.5× slack on `CI=true`; revisit if it still flakes (NFR is a target, not a hill to die on).
- **Risk**: Coverage gate measures wrong directory (e.g., `mission_loader/__pycache__`).
  - **Mitigation**: `--cov=src/specify_cli/mission_loader` resolves a Python source directory, not a build artifact. Verify with `--cov-report=term-missing`.
- **Risk**: Existing CI mypy step has different strictness.
  - **Mitigation**: Confirm with the existing step's args before adding a parallel step. Avoid duplicate work.

## Review Guidance

- Reviewer reads the changed CI YAML and confirms additions are in the same `quality` job (or wherever pytest currently runs).
- Reviewer runs the perf tests and confirms they pass on the local machine.
- Reviewer confirms no global coverage gates were lowered.

## Activity Log

- 2026-04-25T17:54:43Z -- system -- Prompt created.
- 2026-04-25T19:17:48Z – claude:sonnet:implementer-ivan:implementer – shell_pid=49074 – Started implementation via action command
- 2026-04-25T19:23:08Z – claude:sonnet:implementer-ivan:implementer – shell_pid=49074 – Perf p95 / wall-clock checks landed; CI guards configured
- 2026-04-25T19:23:43Z – claude:opus:reviewer-renata:reviewer – shell_pid=53630 – Started review via action command
- 2026-04-25T19:26:07Z – claude:opus:reviewer-renata:reviewer – shell_pid=53630 – Review passed: perf p95=3.75ms (well under 250ms), ERP load <2s test passes, mission-loader-coverage CI job added (90% gate, 96.62% actual), mypy --strict src/specify_cli already covers new package, no pyproject.toml changes, ruff/mypy/regressions all clean
