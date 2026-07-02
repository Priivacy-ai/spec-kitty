# Tracer: Tooling Friction

**Mission**: tasks-py-degod-01KWF08S
**Created**: 2026-07-02 (retrospectively at close — not seeded at planning; captured from the implement-loop history)
**Lifecycle**: seed at planning → append during implement → assess at close (experiment #2095)

Traps, gotchas, and tooling friction hit during this mission. **Read this before the follow-up mission** — several recur.

## mypy / strict-typing

- **CI runs `mypy --strict` over `src/` only** (`src/specify_cli src/charter src/doctrine`), NOT `tests/`. So the pure cores (in `src/`) are strict-gated; pre-existing test-file strict debt (e.g. `test_tasks.py`'s 4 errors) is non-gating → DIR-013 follow-up, not a blocker.
- **BUT: strict-mypy on a changed *test* file must be run TOGETHER with its src core** — `mypy --strict src/…/tasks_status_view.py tests/…/test_tasks_status_view.py`. An `attr-defined` on an imported function's return type (e.g. `build_stale_fallback_results -> dict[str, object]`) only surfaces when BOTH files are in mypy's scope at once. Checking the test alone, or src alone, hides it (WP05 cycle-1 miss: impl ran src-only = "clean", missed 5 real test errors; even the orchestrator saw 1-not-6 checking the test alone).
- **`warn_unused_ignores` (strict) makes a needless `# type: ignore` an ERROR.** A `# type: ignore[misc]` on a frozen-dataclass mutation-in-a-test was UNUSED under strict → failing. Fix = **delete** the comment (the `FrozenInstanceError` still fires at runtime); do NOT `dataclasses.replace` (that defeats the mutation-raises test).
- Local mypy version skew (a stale `.mypy_cache`, or a different local mypy) can under-report — clear the cache / run `--no-incremental` when a claim of "clean" is doubtful.

## typer / lockfile coupling

- The golden `--help` fixtures are **typer/rich-version-coupled**. The shared `.venv` drifted (0.26.8 → 0.25.1) while `uv.lock` pins **typer 0.24.2**. At 0.26.8 `TyperGroup` no longer subclasses `click.Group` → the harness's `isinstance(get_command(app), click.Group)` breaks. **Pin the venv to `uv.lock` (0.24.2)** so local == CI; re-freeze `--help` fixtures only against the locked version.

## coverage / FR-scanner

- The requirement-coverage scanner counts **`FR-\d+` tokens from prose**, not just the FR table rows. Two phantom-FR bites: `#2297`'s "FR-2 suite-map" cross-ref, and the **`FR-008a`** planning-arm shorthand in FR-001/FR-004 (tokenizes as `FR-008`). Descoping/deferring an FR requires **de-tokenizing every `FR-NNN` mention** in prose (reword to a non-matching form), not just deleting the table row.

## implement-loop / status bookkeeping

- **Status bookkeeping must be committed on the primary checkout between WPs** — `tasks.md`/`meta.json`/WP-frontmatter updates from the loop, and `issue-matrix.md`, block the next `agent action implement` claim ("Planning artifacts not committed") until committed.
- **Editing `spec.md` re-stales the recorded `analysis-report.md`** → the next implement claim blocks on `stale_analysis_report`. Re-run `record-analysis` after any spec edit.
- **The approve gate requires terminal issue-matrix verdicts** — placeholder `unknown` verdicts block; set `in-mission` (non-terminal, passes per-WP approved, blocks at `done`) until close.
- A **transient subagent API/connection crash mid-work** leaves the lane clean if it was pre-edit → just re-dispatch (no work lost). Verify the lane worktree git state before re-dispatching.

## arch gates / census

- The **resolution-authority census gate goes RED mid-mission** as rewires drain/shift write-classified sites (census fell 12→9 below the floor of 12, + stale `(qualname, line)` allowlist entries from line-drift). This is *self-inflicted debt* that a dedicated census-cleanup WP must resolve (shrink-only floor-lower + drain/re-pin) before the mission can land green — it is NOT deferrable.
- Several other arch gates (`test_no_tmp_paths_in_tests`, `test_pytest_marker_convention`, `test_status_module_boundary`, `test_untrusted_path_containment`, `test_gate_coverage`) were **pre-existing RED** on the mission base (cross-base-verified) — DIR-013 follow-up territory, not this mission's.

## worktree / editable-install

- The lane worktrees have **no own `.venv`** — use the primary clone's venv (`export PATH="…/spec-kitty-doctrine-fidelity/.venv/bin:$PATH"`). The editable install points at the primary checkout (mission base, WITHOUT the lane's new modules), so bare `python -c "import <new_module>"` fails; **pytest resolves the worktree code correctly** — verify via pytest, not bare imports.
