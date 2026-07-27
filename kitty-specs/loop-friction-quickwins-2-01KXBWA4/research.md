# Phase 0 Research: Implement-Loop Friction Quick-Wins II

All clarifications were resolved pre-spec by a 4-lens research squad (full detail in
[research-synthesis.md](./research-synthesis.md)). This file records the binding **decisions**.
No `[NEEDS CLARIFICATION]` markers remain.

## Decision R-01 — Allocator: exclude runtime frontmatter, do not auto-commit (FR-001)

- **Decision**: Add a `_drop_runtime_frontmatter_only_wp` helper mirroring the shipped
  `_drop_vcs_lock_only_meta` (#2222), wired into `resolve_planning_artifact_staging`. It drops a
  `WP##.md` from the uncommitted-artifact check when its *only* diff vs the placement ref is the
  runtime fields (`shell_pid`, `shell_pid_created_at`, `base_branch`, `base_commit`).
- **Rationale**: "Stop-gating, not auto-committing" is the operator-approved posture already proven
  by #2222; byte-identical no-op when `auto_commit=True`; aligns with #2093 (runtime state → event-log).
- **Alternatives**: auto-commit the frontmatter (rejected — writes on a read-path, muddies history);
  retire the fields to the event log now (rejected — that is #2093's larger scope, out of band).

## Decision R-02 — Freshness normalizer: canonicalize pipe-table status cells (FR-002)

- **Decision**: Broaden `_normalize_tasks_md` so status markers are canonicalized wherever they appear
  as a standalone status cell (`[ ]`/`[x]`/`[X]`/`[D]`/`[P]`), not only at bullet line-start.
- **Rationale**: The #1764 fix is bullet-list-only; pipe-table `[D]`/`[P]` escape it two ways (cell
  position + charclass). One-regex change in one pure helper preserves the "substantive change still
  stales" invariant.
- **Alternatives**: hash only substantive rows (rejected — larger, riskier row-parser rewrite).

## Decision R-03 — Pre-review gate interpreter resolution via `uv run` (FR-003, C-004)

- **Decision**: Resolve the pytest runner via `uv run --project <repo_root> python -m pytest …` when
  `uv` is on PATH and `<repo_root>/pyproject.toml` exists; else fall back to `sys.executable -m pytest`.
  Add a regression under a pytest-lacking interpreter.
- **Rationale**: `pytest` is a test-only optional-dependency extra, so the CLI interpreter
  (`sys.executable`) legitimately lacks it → `no_coverage` → spurious `--force`. `uv run` resolves the
  project venv. Distinct from #2534 (missing `_gate_coverage` module — a scope-derivation failure).
- **Alternatives**: make pytest a runtime dep (rejected — pollutes install); bare `python` (rejected —
  worse, imports primary src in a lane).

## Decision R-04 — Pre-review gate contention safety (FR-004)

- **Decision**: Serialize the scoped gate run with an advisory file lock (reuse the `_acquire_daemon_lock`
  flock idiom) so only one scoped run executes machine-wide at a time; keep `--skip-pre-review-gate`
  (shipped #2573) as the escape hatch.
- **Rationale**: Under N concurrent lanes a 30s shard can exceed the 300s ceiling → false timeout →
  `no_coverage`. A lightweight lock bounds CPU contention; smaller than an async redesign (deferred).
- **Alternatives**: raise/adaptive timeout only (rejected — masks, doesn't bound contention).

## Decision R-05 — Sub-agent long-gate contract (FR-005)

- **Decision**: Define the contract in the implement-review skill/doctrine: a dispatched sub-agent
  polls the synchronous gate to completion; if disabled/skipped, it uses `--skip-pre-review-gate` /
  the honored disable env; the orchestrator does not assume silent hand-back.
- **Rationale**: Behavioral/doc gap, not a code defect; #2573 shipped the mechanisms, the contract
  was left implicit.
- **Alternatives**: code-enforced background polling (rejected — over-engineered for a doc gap).

## Decision R-06 — Manifest `output_path` repo-relative at the serialization seam (FR-006, NFR-004)

- **Decision**: In `_entry_to_json`, write `output_path` relative to `project_root` (fallback absolute
  for out-of-tree, exactly like `_manifest_source_path`); in `_entry_from_json`, rejoin relative values
  to `project_root` and pass absolute values through (legacy-tolerant). Regenerate the committed
  manifest once to the clean 8-field relative form.
- **Rationale**: `source_path` in the same file is already stored relative — mirror it. The in-memory
  representation and internal keying must stay absolute (consumers call `.exists()`/`hash_file`), so
  relativize only on disk. Both-forms tolerance means zero migration.
- **Alternatives**: gitignore the field (rejected — loses provenance); drop `output_path` entirely
  (rejected — consumers read it).

## Decision R-07 — Issue-matrix schema-drift-first error (FR-007)

- **Decision**: In `_issue_matrix_approval_blocker`, detect an `ISSUE_MATRIX_SCHEMA_DRIFT` diagnostic
  and lead with it (surfacing the diagnostic `detail` — the found/normalized columns) instead of
  listing every referenced issue as "Missing rows". Keep "Missing rows" only when rows actually parsed.
- **Rationale**: A malformed mandatory column makes the parser early-return with zero rows, so every
  issue looks "missing"; the real SCHEMA_DRIFT detail already exists but is never surfaced.
- **Alternatives**: teach the parser column aliases (larger; deferred — message clarity is the win here).

## Decision R-08 — Bulk-edit inference: drop low-weight verbs from the trigger (FR-008)

- **Decision**: Exclude `LOW_WEIGHT_KEYWORDS` (update/change/modify/refactor) from the `triggered`
  sum (keep them in `matched_phrases` for display). Genuine bulk edits still trip via HIGH phrases
  ("rename all occurrences") or two MEDIUMs ("rename" + "across the codebase").
- **Rationale**: Scale, not the edit verb, is the real bulk signal; generic refactor vocabulary should
  not push a non-bulk change over the blocking threshold.
- **Alternatives**: require a HIGH/scale co-occurrence (slightly larger; kept as fallback option).

## Decision R-09 — Scaffold-block: distinct non-error result (FR-009)

- **Decision**: When `setup-plan`/`setup-specify` just wrote the scaffold and no populated content
  exists yet, return a distinct non-error result (e.g. `scaffolded`/`awaiting_content`), reserving
  `blocked` for a populated-but-insufficient artifact. Mirror across setup-plan and mission_create.
- **Rationale**: The #846 gate is correct but its happy-path UX cost (a `blocked` on every first run +
  write-then-discard artifact) lands on every mission. `is_substantive` is unchanged.
- **Alternatives**: keep `blocked` (rejected — the friction); auto-populate scaffold (rejected — hides
  the authoring step). Note the JSON `result` contract change (WP-D risk).

## Decision R-10 — move-task coord-lane recovery (FR-010, C-002)

- **Decision**: Route `move-task`'s planning-artifact staging through the established authority path
  (`commit_router` WORK_PACKAGE_TASK routing + `skip_target_commit`, reusing IC-01's
  `resolve_planning_artifact_staging`) so the lane branch is never asked to commit `kitty-specs/`.
- **Rationale**: WP-file commits ALREADY route to primary via `commit_router` (verified); the friction
  is manual agent recovery after `block_mission_specs` refuses a lane commit — the durable fix is
  code-side routing, not a guard exemption.
- **Alternatives**: teach `commit_guard.block_mission_specs` an exemption — **REJECTED** (alphonso F3):
  weakens the partition-lock #168 close-by-construction guard for no benefit.

## Post-Squad Refinements (2026-07-12)

Applied after the 4-lens post-plan adversarial squad (verdict: boundary sound; canonical seams verified).

- **R-01 (FR-001) tightened**: the new `_drop_runtime_frontmatter_only_wp` operates on `WP##.md`
  (YAML frontmatter + markdown body), unlike the JSON-only `_drop_vcs_lock_only_meta` — it must assert
  the **body is byte-unchanged** (else a body edit riding a `shell_pid` write slips the guard) and
  source the runtime field set from the canonical `frontmatter.py::WP_FIELD_ORDER` (not a fresh tuple).
  **Folds #2580** (4th `shell_pid` writer in `_mt_persist_wp_file`) to close the writer set.
- **R-04 (FR-004) tightened**: canonical `MachineFileLock` (`core/file_lock.py:311`) is async-only while
  the gate runner is sync — name the mechanism (async bridge vs scoped `fcntl.flock`); give lock-acquire
  its OWN timeout + fallback-to-run, **decoupled** from the 300s subprocess timeout (else the lock-wait
  re-creates the false `no_coverage`). FR-003+FR-004 are non-splittable (same `subprocess.run`).
- **R-06 (FR-006) re-sized M**: `output_path` is the in-memory manifest KEY and must `.exists()`-resolve,
  so — unlike the never-reconstructed `source_path` — it must be relativized at `_entry_to_json` AND
  reconstructed at `_entry_from_json`, threading `project_root` through `_read`/`save` too (4 functions).
  Add a keying-invariant regression (`get_hash`/`.exists()` unaffected). Own WP, not a papercut.
- **R-08 (FR-008) true-positive guard**: with `INFERENCE_THRESHOLD=4`, dropping the low-weight `+1` lets
  a single-HIGH-phrase bulk edit (score 3) escape — MUST add a single-HIGH-phrase red-first regression
  that still trips; if it can't pass at threshold 4, adopt the HIGH/scale co-occurrence fallback rather
  than lowering detection.
- **R-09 (FR-009) re-apportioned**: the specify twin is ALREADY shipped (`mission_create` returns
  `scaffold_only: success`; no `setup-specify` command) — do NOT budget it. The plan side needs a
  net-new pristine-vs-insufficient predicate, and the true consumer work is the source prompts
  (`src/doctrine/missions/mission-steps/software-dev/plan/prompt.md`), agent-copy regeneration, and the
  `next` engine result-switch (`runtime/next/_internal_runtime/engine.py:287-292`).
- **Coordination**: the coord line C-002 feared already MERGED (#2194, #2545) — reframe to "don't
  regress partition-lock #168"; add gate-registration refactors #2596/#2598 + unification #2300 as
  coordination cross-refs. Fast-follow surfaces are MERGED (not "unmerged") — FR-003/004 build on them.
