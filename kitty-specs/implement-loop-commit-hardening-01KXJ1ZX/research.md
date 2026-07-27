# Phase 0 Research — Implement-Loop Commit & Move-Task Hardening

Brownfield mission. The load-bearing understanding was captured by the post-spec squad
(paula-patterns brownfield + reviewer-renata) tracing the real code. No `NEEDS
CLARIFICATION` remains.

## Decision 1 — FR-005 is a THREE-site consolidation

- **Decision**: The partition-decision sites to unify are three, not two:
  `implement.py::_partition_files_for_commit` (write), `commit_router::_group_files_by_partition`
  (write), and `implement_cores.py::resolve_precondition_ref` (read, owns the `"HEAD"`
  primary-ref literal). All three land in Lane A.
- **Rationale**: FR-005's "unify read-side HEAD vs write-side planning_branch" is
  impossible without editing the read site (`implement_cores.py:244-270`). The original
  spec named only the two write sites.
- **Evidence**: `implement_cores.py:244` (resolver), `:268` residue classification, `:269` `"HEAD"`.

## Decision 2 — Consolidate toward the residue direction (`kind=None`→PRIMARY) — the #2533-safe one

- **Decision**: The unified authority routes `kind=None` / `meta.json` / unrecognized
  paths → **PRIMARY** (the residue-predicate direction). C-007.
- **Rationale**: The two classifiers disagree exactly on the `kind=None` set. The read
  side (`is_coordination_artifact_residue_path`) routes them PRIMARY (#2533-safe, with an
  explicit code fence at `implement_cores.py:255-262`). `commit_router._group_files_by_partition`
  (`commit_router.py:404`, `kind_f = kind_for_mission_file(file) or kind`) routes a
  `None`-classified file to the **caller's** partition — which can be COORD. Consolidating
  onto the kind classifier's fallback would misroute `meta.json`→COORD and **reintroduce
  #2533** — the bug the predecessor mission just closed.
- **Alternatives rejected**: consolidate onto `commit_router`'s kind classifier as-is
  (rejected: #2533 regression); leave three sites (rejected: FR-005 goal, drift risk).

## Decision 3 — Characterization gate (FR-006) BEFORE the swap (DM-D document-first)

- **Decision**: Enumerate the three sites + the `kind=None` disagreement set and pin the
  intended unified placement in tests before deleting either executor.
- **Rationale**: The suites currently encode **both** fallback directions
  (`tests/specify_cli/coordination/test_commit_router_partition.py:193` pins the
  caller-fallback direction; the read-side tests pin PRIMARY), so NFR-002's "suites pass
  unchanged" is unsatisfiable for a real consolidation. Brownfield DM-D requires
  characterizing the intended behavior first.
- **Alternatives rejected**: swap-then-fix-tests (rejected: brownfield anti-pattern; risks
  silent regression).

## Decision 4 — #2648 warning via a structured, `--json`-visible channel

- **Decision**: Emit the protected-branch diversion warning at WARNING level on the
  write-side path's logging channel, surfaced under `--json`/agent mode (structured field
  or stderr), NOT via `console.print` alone.
- **Rationale**: `implement` runs under `_json_safe_output` (`implement.py:135-177`) which
  captures `console.print` and only flushes the last 20 lines on `typer.Exit` — an
  agent-driven claim would get a silent warning. The regression test asserts the log
  record / structured field.
- **Alternatives rejected**: `console.print` warning (rejected: swallowed under `--json`).

## Decision 5 — Preserve Lane-A→Lane-B symbol contracts (C-006)

- **Decision**: The FR-003 degod preserves the public signature + 5-tuple return of
  `_resolve_bookkeeping_transaction_identifiers`, `_feature_dir_file_paths`,
  `_planning_artifact_source_dir`. Otherwise sequence the Lane-B import path after Lane A.
- **Rationale**: `tasks_move_task.py:1381-1386` (Lane B) imports these Lane-A symbols and
  depends on the 5-tuple (`...[0]` at `:1394`). File-linearization does not cover
  symbol-contract coupling.

## Decision 6 — Characterization-first degod for the implicit-invariant functions

- **Decision**: Before extraction, pin: (a) `_resolve_bookkeeping_transaction_identifiers`
  primary-dir-first cascade order + ambiguous-handle RAISE (`implement.py:353-423`);
  (b) `_json_safe_output` `console._file=None` reset (`:172-175`);
  (c) `_mt_uncheck_rollback_subtasks` #2576 dual-handler separation (`tasks_move_task.py:1634-1649` — C-001, a no-op degod: it is S8572 not S3776, do not merge handlers).
- **Rationale**: these encode real invariants (#1784 handle-resolution, test-isolation,
  #2576 error-recording); naive extraction erases them and existing suites may not catch it.

## Confirmed prerequisites

- No active #2160/#2465 parallel work (operator-confirmed); the #2650 slice is safe here.
- Draft PR #2639 is the only in-flight touch on `_do_move_task` (C-005 rebase note).
- The #2533 fix (residue direction, `kind=None`→PRIMARY) is the merged baseline this
  mission must not regress.
