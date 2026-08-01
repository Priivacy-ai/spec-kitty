---
work_package_id: WP01
title: 'The reproducer: two environment variables, one file, one process'
dependencies: []
requirement_refs:
- FR-001
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: 9ed8757b6fa46ef3fa51544ff791ded9765df4ee
created_at: '2026-07-31T14:38:32.449130+00:00'
subtasks:
- T001
- T002
- T003
- T004
history: []
authoritative_surface: scripts/
create_intent:
- scripts/repro_3115_render_width.sh
execution_mode: code_change
owned_files:
- scripts/repro_3115_render_width.sh
- docs/development/testing-parallel.md
tags: []
tracker_refs: []
---

# WP01 — The reproducer

`TERM=dumb FORCE_COLOR=1`, **one file, one process, no xdist**. Committed to the repo — a reproducer
described in a PR comment is not a reproducer. Everything else in the CLI half is unfalsifiable
without it, and `578a659162` is the proof: a credible fix was written and shipped and nobody could say
whether it did anything.

## The measured cause — stated so it is not re-derived

`rich.console.Console.size` returns `ConsoleDimensions(80, 25)` from the `if self.is_dumb_terminal:`
branch, which sits **above** the `COLUMNS` read. `is_terminal` is true whenever `FORCE_COLOR` is set
non-empty; `is_dumb_terminal` is `is_terminal and TERM.lower() in ("dumb", "unknown")`. The `Project`
column is `overflow="fold"` (`src/specify_cli/cli/commands/sync.py:1440`, deliberate, documented at
`:1430-1436`), so at width 80 a 36-character uuid folds across two lines and **stops being a
contiguous substring**. The journal is populated — 14 events retained, all four rows present, counts
7/4/2/1 — so the issue's *"reads an EMPTY journal"* premise is falsified.

**`SILENT` / `OPTED_OUT` pass at width 80 only incidentally**, via an un-tabled warning paragraph that
reprints the identity outside the folding table. `CONSENTED` has no such paragraph, which is why
exactly one of three loop iterations fails, and always the first. **Only the `CONSENTED` iteration
demonstrates anything.**

## Collected counts — binding on every count line below

Re-measured with `pytest --collect-only -q` on a tree level with `bb2020fea9`:

| File | Collects | Red count line | Green count line |
|---|---|---|---|
| `tests/cli/commands/test_sync_status_per_project_3030.py` | **4** | `1 failed, 3 passed` | `4 passed` |
| `tests/cli/commands/test_sync_doctor_per_project_3030.py` | **12** | `1 failed, 11 passed` | `12 passed` |

The earlier draft attributed `1 failed, 3 passed` / `4 passed` to the **doctor** file. **The four-test
count line belongs to the status file.** Every count line in this WP's evidence is quoted **beside its
file's collected count** (NFR-008); a count line that does not reconcile against the collected count is
not evidence and is **re-measured, not argued about**.

## Definition of done — measurable evidence

- **T002 — red first, on the base commit.** `pytest tests/cli/commands/test_sync_status_per_project_3030.py`
  under the two env vars, **output to a file, tail of the file read** (NFR-003). Count line
  `1 failed, 3 passed` quoted beside the collected count **4**. The assertion text is quoted and it
  must be the per-file assertion text quoted verbatim from source — ``<uuid> is in the journal but `status` did not name it`` (backticks, `test_sync_status_per_project_3030.py:154`) or `<uuid> is in the journal but doctor did not name it` (no delimiters, `test_sync_doctor_per_project_3030.py:174`); they differ, and neither is normalised. **A `TypeError`, a fixture error, a
  collection error or an empty output file satisfies nothing.** `Queue 0 event(s)` is **excluded** as a
  signature — it renders from `OfflineQueue().size()` (`sync.py:5182-5185`) on the green path too.
- Independently repeated for `test_sync_doctor_per_project_3030.py`, whose count line is
  `1 failed, 11 passed` beside the collected count **12** — **not** `1 failed, 3 passed`.
- **T003 — determinism, rewritten so it can fail** (post-plan squad, F3). The old criterion ("three
  consecutive runs, same node-id") was **trivially satisfied**: `pytest-randomly` is **not installed**
  on this tree (`importlib.util.find_spec("pytest_randomly")` → `None`; absent from
  `pyproject.toml:101-113` and from every workflow), so nothing randomises order and repetition cannot
  go the other way. Green for the wrong reason, in the mission built to eliminate that. **Report
  both:**
  - **(a) the stability observation, no longer load-bearing** — three consecutive runs, same node-id,
    **same assertion text byte-for-byte**, same collected count, all three quoted; and the run's own
    `plugins:` header line quoted, so the ordering-plugin state is a *measurement* rather than an
    assumption.
  - **(b) the falsifiable clause** — the red reproduces with the failing case selected **alone by
    node-id**: `TERM=dumb FORCE_COLOR=1 pytest '<file>::<node-id>'`, same assertion text, **collected
    count 1**. A red that needs its file-siblings to run first is order-dependent, falsifies "two
    environment variables and one file", and fails C-004. **This is the clause that must be able to
    red, and it is what the determinism claim rests on.**
- **T004 — control.** The same command `+ TTY_COMPATIBLE=0` on the base commit quotes `4 passed` for
  the status file and `12 passed` for the doctor file. This is what separates *"the width is the
  cause"* from *"this file is broken"*.
- **T001 — NFR-005.** Wall clock **under 2 minutes** (measured at ~57s on the base commit), and the
  documented command is **one line**. A reproducer nobody runs is documentation, not a tool.
- **NFR-009.** State the commit every measurement was taken at and this lane's merge-base against the
  mission branch. **Merge the mission branch into the worktree before the first measurement.** A
  baseline whose commit is unstated is void and is re-taken.
- **NFR-002.** If any measurement is taken in a `git worktree`, state `PYTHONPATH=$WT/src` or a
  dedicated venv created **inside** the worktree — `.venv/.../_editable_impl_spec_kitty_cli.pth` holds
  the **absolute path of the main checkout**, so a worktree using the main `.venv` imports the live
  tree and makes isolation *look* performed.

## Forbidden

- **Editing any test file.** This WP owns `scripts/repro_3115_render_width.sh` and
  `docs/development/testing-parallel.md` and nothing else. WP02 holds `tests/conftest.py`; WP07 holds
  the five `578a659162` files, including both victim files this reproducer runs.
- **`COLUMNS`.** It is not a fix — it is the thing that was already there and was never read (C-012).
- **xdist.** `--dist loadfile` assignment is dynamic and work-stealing; a reproducer that depends on a
  particular assignment is not reproducible by construction (C-004).
- **`-p no:randomly` is pointless rather than forbidden.** C-005 is **struck**. If any run uses it, say
  so and state why, but it changes nothing on this tree.

## Files other agents hold

`tests/conftest.py` (WP02) · the five `578a659162` files including both victim files (WP07) ·
`docs/development/toc.yml` and `docs/development/3-2-page-inventory.yaml` (WP04 — **this WP appends a
section to an existing page and touches neither the nav nor the generated lockfile**) ·
`scripts/mutants/*` (one file per authoring WP; WP01 authors none).
