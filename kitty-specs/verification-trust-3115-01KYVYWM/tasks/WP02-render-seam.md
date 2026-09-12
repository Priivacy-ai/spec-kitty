---
work_package_id: WP02
title: 'The render seam: pin the surface at the conftest owner that already owns the console'
dependencies:
- WP01
requirement_refs:
- FR-002
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: d8d0ad7eff9ddeb14e154afd82450cf2dfd5472d
created_at: '2026-07-31T12:00:00+00:00'
subtasks:
- T005
- T006
- T007
history: []
authoritative_surface: tests/
execution_mode: code_change
owned_files:
- tests/conftest.py
- scripts/mutants/disable_render_seam_3115.py
create_intent:
- scripts/mutants/disable_render_seam_3115.py
tags: []
tracker_refs: []
---

# WP02 — The render seam

Extend `_plain_cli_console_seam` (`tests/conftest.py:307-329`) to pin the render surface **as well as**
the colour — **both** `width` and `height` (or `TTY_COMPATIBLE=0`, or `force_terminal=False`), set →
`yield` → restore in `finally` (C-002). **Never `COLUMNS`** (C-012).

## Why this layer, and why not a second fixture

The house precedent is two doors down: `tests/conftest.py:307-329` (`_plain_cli_console_seam`, autouse,
set → `yield` → restore in `finally`) already owns exactly this concern **for colour**, and
`tests/specify_cli/cli/commands/_help_snapshot.py` already pins `10_000 × 100` for exactly this reason
and documents the trap in its module docstring — *"Rich early-returns the explicit size only when width
AND height are set"*. **One owner; one `finally`; the docstring that already explains the colour half
gains the width half.** A second autouse fixture is a second thing to disable and a second restore
path.

`tests/conftest.py` now has **exactly one owner** in this mission. WP08 was the second; it is retired,
and the sequential-handoff risk on the root conftest disappeared with it.

## Two hard constraints on the pin, both from post-plan measurements

- **The width must be ≥ 240** (F2). `tests/specify_cli/cli/commands/charter/test_activation_layout.py:111`
  passes `env={"COLUMNS": "240"}` and is **live**: under `CliRunner` in the default environment
  `is_terminal` is False, the `is_dumb_terminal` early return does **not** fire, and `COLUMNS` *is*
  consulted. An explicit size below 240 narrows that test's render surface below what it asks for. The
  four measured trap values below were taken at 220; **the shipped value is ≥ 240 and the docstring
  states both**.
- **Pin the singletons only; exempt the explicitly-sized specials** (F1). `CliConsole._instances`
  (`src/specify_cli/cli/console.py:49`) is a `WeakSet` that also holds three **deliberately-sized**
  consoles — `src/specify_cli/cli/commands/charter/list_cmd.py:26` (`width=200`),
  `src/specify_cli/cli/commands/glossary.py:46` (`width=120`), and
  `src/specify_cli/cli/commands/docs.py:43` (`width=120`, whose 120 is stated load-bearing in the
  comment at `docs.py:40-42`). **A blanket `size = (W, H)` walk overwrites all three.** The seam pins
  `console` and `err_console` (`console.py:126-127`), **or** walks `_instances` while skipping any
  instance constructed with an explicit `width=`. **Whichever it chooses, it states which and why.**

## Definition of done — measurable evidence

### T005 / T007 — both directions on one commit

- WP01's falsifier **greens**, count line quoted **beside its collected count**: `4 passed` / 4 for
  `tests/cli/commands/test_sync_status_per_project_3030.py`, `12 passed` / 12 for
  `tests/cli/commands/test_sync_doctor_per_project_3030.py`.
- The same command with the seam disabled **by the plugin** reds with **WP01's exact assertion text**:
  `1 failed, 3 passed` / 4 and `1 failed, 11 passed` / 12. **A green that was never shown to be able to
  red is not a pass** (R8).

### T006 — the plugin obeys the corrected mutant contract, in full

This replaces every "loaded via `PYTHONPATH`" statement in the earlier draft. The post-plan squad
probed the old contract against a known-answer baseline and found it produced a **silently inert**
mutant in two independent ways — the plan committing the exact rot mode it exists to guard against.

1. **Loading.** `PYTHONPATH=scripts/mutants pytest -p disable_render_seam_3115 …`. **The `-p` flag is
   quoted in the evidence**, because `PYTHONPATH` alone loads nothing: a `PYTHONPATH`-only mutant is
   imported by nothing, binds nothing, and its run reads as a passing gate.
2. **Neutralisation site — hook level, never a same-named fixture.** `pytest_fixture_setup`
   intercepting `_plain_cli_console_seam`'s setup, or `pytest_configure` unsetting the pin. **A
   same-named autouse fixture defined in a plugin loses to a conftest fixture** for items under that
   conftest's directory — pytest resolves conftest fixtures at higher precedence — so the "define
   `_plain_cli_console_seam` in the plugin" shape is a **guaranteed no-op**. Probed: the hook-level
   form produced a named red (`AssertionError: seam was off`); the fixture form did not bind at all.
3. **Self-proof — three parts, all mandatory.** The plugin **asserts its own binding** and fails loudly
   at `pytest_configure` if the symbol or fixture it intends to patch is absent, renamed or relocated;
   it **reports the per-site split** across every name the seam is reachable by (an aggregate count
   cannot distinguish "both sites mutated" from "one mutated, one inert"); and it **fails loudly if the
   seam it neutralised was never invoked**.
4. **Reporting.** The run under the mutant quotes the mutant's own binding/suppression report **beside**
   its count line and collected count. **A green run under a plugin that suppressed zero sites proves
   nothing about the seam** — "ran under the mutant, still green" without a non-zero suppressed count
   is not a measurement.

### T007 — the seam's docstring

Records, verbatim:

- The four measured `Console.size` values under `TERM=dumb FORCE_COLOR=1 COLUMNS=220`:
  no width → `(80, 25)`; `width=220` **alone** → `(80, 25)`; `width=220, height=50` → `(220, 50)`;
  `TTY_COMPATIBLE=0` → `(220, 25)`. **The width-alone trap is the single most likely way this fix ships
  broken and green** — rich's explicit-size early return requires
  `self._width is not None and self._height is not None`.
- The **shipped** value and **why it is ≥ 240**, alongside the 220-based trap measurements.
- A citation of `tests/specify_cli/cli/commands/_help_snapshot.py` (the house precedent).
- **The `#3115` victim files it covers**, by name.
- **The two consoles it does not reach**, by name and line: `src/specify_cli/cli/helpers.py:234`
  (`CliConsole(stderr=True, color_system=_color)`) and
  `src/specify_cli/cli/logging_bootstrap.py:92` (`CliConsole(stderr=True, highlight=False)`), both
  constructed **inside functions**, i.e. after the seam's setup-time walk has already run. **That gap
  is stated, not left for a non-zero inspected count to conceal.**
- The **correct** `COLUMNS` finding: *inert on the failing path, consulted on the passing one.*

### T007 — blast radius

The golden `--help` snapshot suite (which pins its own console independently via
`_help_snapshot.force_wide_help_console`, so it *should* be unaffected — but *should* is not a
measurement), `tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py`, **and
`tests/specify_cli/cli/commands/charter/test_activation_layout.py`** are run before and after with
their **collected counts** quoted. **Any changed outcome is reconciled, never absorbed.**

### Cross-cutting

- **NFR-009**: merge the mission branch into the worktree before the first measurement; state the
  commit and merge-base. **NFR-003**: output to a file, tail of the file read; quote the count line
  with its assertion text, never "exit 0"; an empty output file is no measurement. **NFR-002**: state
  the worktree import path.

## The `COLUMNS` note is withdrawn — nothing is passed forward

The earlier draft had WP02 record that the seam makes three `monkeypatch.setenv("COLUMNS", …)` sites
"provably dead" and hand their removal to WP08. **That is wrong and WP08 no longer exists.** F2
measured those sets **live** on the non-dumb path. WP02 records the correct finding in the seam's
docstring, and **no work package removes or annotates them.** WP02 does not touch those files at all.

## Files other agents hold

`tests/cli/commands/test_sync_status_per_project_3030.py` and
`tests/cli/commands/test_sync_doctor_per_project_3030.py` — and the other three `578a659162` files —
belong to **WP07**. This WP **runs** them; it does not edit them.
`tests/specify_cli/cli/commands/charter/test_activation_layout.py` is **nobody's write scope** — it is
this WP's blast-radius *subject*. `tests/architectural/test_cli_console_render_width.py`,
`tests/cli/commands/test_render_fold_not_repairable_3115.py` and `tests/_arch_shard_map.py` are WP03's.
`src/**` is nobody's — no production change is required by any FR.
