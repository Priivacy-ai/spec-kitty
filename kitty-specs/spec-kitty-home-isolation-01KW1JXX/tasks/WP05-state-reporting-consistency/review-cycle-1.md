# WP05 Review — Cycle 1 (reviewer-renata)

**Verdict: Changes requested.** The substantive FR work is correct and well-tested
(FR-009, FR-010, SC-004 all verified green — see "What passed" below). The only
blocker is an avoidable suppression that violates an explicit acceptance criterion
and the project charter's suppression policy. The fix is ~2 lines.

---

## Blocking issue

**Issue 1 — New `# type: ignore` suppressions added to the test file (avoidable, no rationale).**

- File: `tests/state/test_doctor_spec_kitty_home.py:35` and `:44`
  ```python
  for r in report.roots      # type: ignore[attr-defined]   (line 35)
  for s in report.surfaces   # type: ignore[attr-defined]   (line 44)
  ```
- Why this blocks: The WP05 review criteria and the project charter both prohibit
  *new* `# type: ignore` additions. The charter allows narrowly-scoped suppressions
  **only when the check is genuinely wrong about correct code, and they must carry an
  inline rationale.** Neither condition is met here:
  1. mypy is correct — the helpers annotate the parameter as `report: object`, and
     `object` genuinely has no `.roots` / `.surfaces`. The suppression masks a
     self-inflicted typing choice, not a mypy defect. (Running `mypy` over the test
     file shows the ignores merely downgrade the error to `no-any-return` on lines
     33/42, confirming they paper over the broad annotation.)
  2. There is no inline rationale comment justifying the suppression.
- Fix (trivial): type the helper parameters with the real return type, which is
  defined and importable from the same module, and delete both ignore comments:
  ```python
  from specify_cli.state.doctor import StateRootsReport, check_state_roots

  def _global_sync_root(report: StateRootsReport) -> Path:
      return next(
          r.resolved_path for r in report.roots if r.name == "global_sync"
      )

  def _sync_config_present(report: StateRootsReport) -> bool:
      return next(
          s.present for s in report.surfaces if s.surface.name == "sync_config"
      )
  ```
  With the concrete type, `.roots` / `.surfaces` resolve cleanly, the
  `no-any-return` warnings disappear, and no `# type: ignore` is needed.
- After fixing, re-run: `.venv/bin/ruff check tests/state` and
  `.venv/bin/mypy src/specify_cli/state` (gate must stay green), plus
  `.venv/bin/pytest tests/state/ -q`.

---

## What passed (for the next implementer's confidence — do not regress these)

- **FR-009 (doctor reports the runtime root):** `state/doctor.py` `check_state_roots`
  now sets `global_sync = get_runtime_root().base` (was `Path.home() / ".spec-kitty"`).
- **FR-010 (no hand-rolled home literal):** `grep -rn 'Path.home() / ".spec-kitty"'`
  and `grep -rn '"\.spec-kitty"'` over `src/specify_cli/state/` return nothing. The
  remaining `Path.home()` at `doctor.py:137` is the **GLOBAL_RUNTIME** (`~/.kittify/`)
  branch — out of WP05 scope, correctly untouched.
- **Both GLOBAL_SYNC sub-branches rerouted:** `doctor.py:142-151` — both the
  `~/.spec-kitty/`-prefixed branch and the bare `else` anchor on
  `sync_base = get_runtime_root().base`. The previously-unreachable `else` is now
  covered by a dedicated test.
- **contract.py frozen surface unchanged:** the WP05 diff touches only the
  `StateRoot` docstring + the `GLOBAL_SYNC` enum comment. No `path_pattern` /
  `StateSurface` line changed — behavior preserved.
- **Tests are real, not synthetic:** all five tests drive production paths
  (`check_state_roots`, `_check_surface_present`). The env-set, env-unset,
  legacy-home-ignored, and bare-pattern cases would fail on the old `Path.home()`
  code, so the FRs are genuinely exercised.
- **Scope:** WP05's own commit touches only `state/doctor.py`, `state/contract.py`,
  and `tests/state/`. (The `paths/`, `tests/kernel/`, `tests/paths/` files in the
  range diff come from the merged WP01 dependency lane — expected.)
- **Validation re-run by reviewer:**
  - `pytest tests/state/ tests/specify_cli/test_state_doctor.py -q` → 21 passed.
  - `ruff check src/specify_cli/state tests/state` → All checks passed.
  - `mypy src/specify_cli/state` → Success, no issues (gate green).

## Anti-pattern checklist
1. Dead code — PASS (`_GLOBAL_SYNC_PATTERN_PREFIX` used at doctor.py:147).
2. Synthetic-fixture test — PASS (tests invoke production code).
3. Silent empty return — N/A (no new exception handlers).
4. FR coverage — PASS (FR-009 / FR-010 each have asserting tests).
5. Frozen surface — PASS (contract.py patterns unchanged).
6. Locked decision — PASS (surface patterns preserved; no MUST-NOT violated).
7. Shared-file ownership — PASS (WP05 owns lane-e alone; owned files only).
8. Production fragility — PASS (no new `raise`).
9. Suppression policy — **FAIL** (Issue 1 above).
