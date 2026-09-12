---
work_package_id: WP03
title: 'Width guard by named singleton, and the forbidden remedy proved forbidden'
dependencies:
- WP01
- WP02
requirement_refs:
- FR-003
- FR-004
planning_base_branch: feat/verification-trust-3115
merge_target_branch: feat/verification-trust-3115
branch_strategy: Planning artifacts for this mission were generated on feat/verification-trust-3115. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/verification-trust-3115 unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-verification-trust-3115-01KYVYWM
base_commit: d8d0ad7eff9ddeb14e154afd82450cf2dfd5472d
created_at: '2026-07-31T12:00:00+00:00'
subtasks:
- T008
- T009
- T010
- T011
- T012
history: []
authoritative_surface: tests/
execution_mode: code_change
owned_files:
- tests/architectural/test_cli_console_render_width.py
- tests/cli/commands/test_render_fold_not_repairable_3115.py
- tests/cli/commands/fixtures/render_width_3115/**
- tests/_arch_shard_map.py
create_intent:
- tests/architectural/test_cli_console_render_width.py
- tests/cli/commands/test_render_fold_not_repairable_3115.py
- tests/cli/commands/fixtures/render_width_3115/capture_width80.txt
- tests/cli/commands/fixtures/render_width_3115/capture_width80.provenance.json
- tests/cli/commands/fixtures/render_width_3115/capture_pinned.txt
- tests/cli/commands/fixtures/render_width_3115/capture_pinned.provenance.json
tags: []
tracker_refs: []
---

# WP03 — Width guard + the forbidden remedy proved forbidden

Two deliverables: a durable guard so a narrow render surface cannot come back silently (FR-003), and a
**measurement** — not a sentence — that whitespace flattening does not repair the fold (FR-004).

## Why the fixture directory is declared as a glob

`tests/cli/commands/fixtures/render_width_3115/` is a **directory**, and a literal directory path with
no repo match is a hard `exit 1` at `/spec-kitty.tasks`
(`src/specify_cli/ownership/validation.py:418-448`, raised at
`src/specify_cli/cli/commands/agent/mission_finalize.py:998-1006`), whereas a **glob** degrades to a
soft warning. `owned_files` therefore carries the glob; the four capture and provenance files are named
concretely in `create_intent` so the intent is a **commitment** rather than a directory-shaped promise,
and the glob is what keeps the write scope honest if the capture set grows.

## Why `tests/_arch_shard_map.py` is owned here

`tests/architectural/test_arch_shard_marker_completeness.py` proves the arch shard partition is
**total**. A new file under `tests/architectural/` with no assignment row **reds that guard**. WP03 is
the only WP adding an arch test file, so it owns the map outright.

## Definition of done — measurable evidence

### T008 — FR-003 red first

With WP02's seam disabled by the plugin — **loaded with `-p disable_render_seam_3115` under
`PYTHONPATH=scripts/mutants` (the `-p` flag quoted in the evidence), neutralising at hook level, and
reporting a non-zero suppressed count** (C-003's corrected contract) — the guard reds **naming the
console, its measured `size.width`, and the identifier length** it compared against. **No verdict may
be drawn from a run whose mutant suppressed zero calls.**

### T009 — FR-003 positive control: named singletons, not a count

With the seam in place the guard passes **and asserts, by object identity, that it saw
`specify_cli.cli.console.console` and `specify_cli.cli.console.err_console`** (`console.py:126-127`).

**A non-zero inspected count is not sufficient.** `CliConsole._instances` (`console.py:49`) is a
`WeakSet` that also holds three deliberately-sized specials, so **a count of 3 is satisfiable with both
singletons absent from the set.** Alongside the identity assertion the guard prints:

1. the inspected count;
2. the longest asserted identifier length (the 36-character project uuid is the current maximum);
3. the **exempted** specials by `module:line` with their widths — `list_cmd.py:26` 200,
   `glossary.py:46` 120, `docs.py:43` 120;
4. as a **named gap**, the two consoles constructed inside functions that no setup-time walk can
   reach — `src/specify_cli/cli/helpers.py:234` and `src/specify_cli/cli/logging_bootstrap.py:92`.

**The gap is printed on the passing path**, so it is visible in a green run rather than only in a red
one.

**It detects and fails; it does not repair** (H8) — a guard that widens the console it is watching
silences what it guards. **Rot control**: if `_instances` or the seam is renamed, moved or deleted, the
guard **fails loudly** rather than silently inspecting nothing.

### T010 — FR-004 capture provenance

Each committed capture carries a sidecar (`*.provenance.json`) recording:

- the **exact command** that produced it;
- the **commit** it was taken at (`bb2020fea9`);
- the `TERM` / `FORCE_COLOR` / `TTY_COMPATIBLE` / `COLUMNS` values in force;
- the **observed `Console.size` tuple** at capture time.

**A capture with no provenance is a recollection, and a fixture nobody can re-derive is the same shape
as a gate that prints like a pass.** A meta-assertion reds if a capture file exists without its
sidecar.

### T011 — FR-004: the fold is not repairable, and the test is anchored

- After **full** whitespace collapse (`re.sub(r"\s+", " ", out)`) of the committed 80-column capture,
  the uuid is **still** not a substring, and the test **reports the number of characters the fold
  interleaved** between the two fragments.
- **In-file positive anchor.** "The uuid is not a substring" is satisfied just as well by a capture
  that lost the uuid **entirely**, which would make the test trivially true and silently wrong. So the
  same test additionally asserts, against the 80-column capture: **(i)** both uuid fragments **are**
  present; **(ii)** their **concatenation equals the uuid**; **(iii)** the **interleaved character
  count is > 0**. **Each of the three is a separate assertion with its own message**, so the failure
  names which one broke.
- The identical substring assertion against the **pinned-width control capture finds the uuid** — so
  the test **discriminates across two captures** *and* is anchored inside the one it is really about.

`overflow="fold"` on the Project column **stays** (C-009 — `sync.py:1430-1436` states why: an
ellipsized identity is a prefix the operator cannot pass to `sync purge`). No whitespace flattening is
adopted as a remedy; FR-004 **proves** it forbidden rather than asserting it, because the fold
interleaves the rest of the table row *between* the two uuid fragments.

### T012 — both new test files must be selected by a live CI gate

State **which gate** selects each file and **under which marker**, **with the collected count of that
gate's selection before and after the files land** (NFR-008). *"The marker is right"* without a
collected count is the `exit 5` shape — `fast-tests-cli` carries `|| test $? -eq 5`
(`ci-quality.yml:1545`), so an empty collection is a **green job**.

`tests/architectural/test_gate_coverage.py`'s orphan ratchet reds on any new file that no CI gate
selects. **The correct response is to make the new tests gate-selected (correct markers, correct
directory) — never to widen the baseline.** `tests/architectural/_gate_coverage_baseline.json` is on
the nobody-may-edit list. WP03 additionally registers its arch file in `tests/_arch_shard_map.py`.

### Cross-cutting

**NFR-009**: merge the mission branch into the worktree before the first measurement; state the commit
and merge-base. **NFR-003**: output to a file, tail read; count line quoted with its assertion text.
**NFR-006**: the guard's added wall clock over the `fast-tests-cli` selection is measured before/after
at the same worker count and coverage state; **over 5% changes the guard's implementation, never its
reach.**

## Files other agents hold

`tests/conftest.py` and `scripts/mutants/disable_render_seam_3115.py` are **WP02's** — this WP *loads*
that plugin, it does not author or edit it. The five `578a659162` files are **WP07's**.
`tests/specify_cli/cli/commands/charter/test_activation_layout.py` is nobody's write scope.
`tests/architectural/_baselines.yaml` is **WP10's** and no other WP may edit it.
`tests/architectural/_gate_coverage_baseline.json` is **nobody's**.
