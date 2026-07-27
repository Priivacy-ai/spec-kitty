---
title: 'Research Synthesis: Implement-Loop Friction Cluster #2555/#2566/#2493/#2570/#2589'
doc_status: draft
created: '2026-07-12'
origin: 'Pre-spec 4-lens research squad (self-writing guards / authority-split+dedup / gate-subprocess / papercuts), clone spec-kitty-gate-doctrine @ fresh upstream/main 4f7b5629d'
parents: '#2017 (workflow-guard friction, primary) + #2160 (coord-topology authority, adjacent)'
successor_of: 'loop-friction-fastfollow (csf-fastfollow, unmerged quick-wins I: #2581/#2573/#2549B/#2577)'
---

# Friction Cluster — Research Synthesis

Five witnessed issues, decomposed into ~14 distinct frictions, each mapped to a code seam,
blast radius, existing-tracker owner, and INCLUDE/EXCLUDE/SEQUENCE verdict.

## Verdict table

| # | Friction | Code seam (file:line) | Blast | Owner / dedup | Verdict |
|---|----------|-----------------------|-------|---------------|---------|
| 2570.1 | Allocator refuses next lane-alloc on its OWN uncommitted `shell_pid`/`base_*` frontmatter write | guard `implement.py:1345` + `implement_cores.py:334-384`; self-write `implement.py:1400` + `implement_support.py:117-157` | S | NEW; mirrors shipped `_drop_vcs_lock_only_meta` (#2222); strategic parent #2093 | **INCLUDE** |
| 2493.1 | `mark-status` `[D]`/`[P]` pipe-table markers re-stale the analysis-report → next claim blocked | normalizer `analysis_report.py:147-154` (bullet-only); writers `tasks_materialization.py:218-249,276-304` | S | Checkbox case fixed (#1764); pipe-table residual UNPINNED | **INCLUDE** |
| 2570.3 | Pre-review gate runs `sys.executable -m pytest` → pytest is a test-only extra → `No module named pytest` → spurious `no_coverage` → forces `--force` on green tree | `pre_review_gate.py:379-386` | S | NEW; distinct from #2534 (that = missing `_gate_coverage` module). Current real-subprocess tests MASK it | **INCLUDE** |
| 2493.3 | Pre-review gate 300s timeout trips under concurrent-lane CPU contention → `no_coverage` → `--force` | `pre_review_gate.py:109,388-398` | M | #2493 (open); fast-follow deferred redesign | **INCLUDE** (same surface as 2570.3) |
| 2555.4 | Undefined sub-agent contract when dispatched agent hits a multi-minute/background gate | doctrine/skill (`spk-run-implement-review`); gate `tasks_move_task.py:1048` | S(docs) | #2555 §4; #2573 shipped skip-flag but not the contract | **INCLUDE** (doc WP) |
| 2589 | `upgrade` writes machine-ABSOLUTE `output_path` into committed manifest → cross-machine churn | serializer `tool_surface/profiles/manifest.py:106`; prior art `projection.py:52-59` (`source_path` already relative) | S | NEW/unlabeled; net-new win | **INCLUDE** |
| 2555.5 | Issue-matrix gate leads with misleading "Missing rows" when a non-canonical COLUMN broke the parse | msg `tasks_parsing_validation.py:202-216`; early-return `review/_issue_matrix.py:262-287` | S | NEW; #1738/#1742 adjacent (coverage/source, not msg) | **INCLUDE** |
| 2555.3 | Bulk-edit inference blocks on ordinary refactor VERBS (threshold 4, low-weight verbs 1pt) | `bulk_edit/inference.py:44-51,85-125`; gate `implement.py:917-930` | S | NEW; #1257 closed (diff case), #2229 (diff-compliance) both different | **INCLUDE** |
| 2566 | plan/specify scaffold→block→rewrite→rerun on every happy path (returns `blocked` on first write) | scaffold `mission_setup_plan.py:390-404,808`; block `:435-482,646`; twin in `mission_create.py` | M (JSON `result` contract) | #846 CLOSED (made gate); EXPLICITLY DISOWNED by coord-shadows-followups → orphaned | **INCLUDE** (own WP) |
| 2555.2 | move-task sync-daemon fan-out no wall-clock ceiling / clear failure (reads as hang) | `sync/events.py:271` → `daemon.py:1086,1177-1210` (~31s internal) | M (shared fan-out) | #2555 §2; fast-follow did env-deafness only, no timeout | **INCLUDE-optional** (separate subsystem) |
| 2555.1 | move-task coord-lane recovery cascade: untracked-on-primary + lane guard blocks `kitty-specs/` (6 attempts, 0-diff WP) | guard `policy/commit_guard.py:83-89`; staging `tasks_move_task.py:299,1302-1390` | M | Owned by NOBODY (coord placement = merged partition-lock #168, but this cascade residual) | **INCLUDE-if-capacity** (adjacent to coord surface) |
| 2570.2 / 2549A | move-task pollutes LANE branch with `status.*`; stale lane `status.events.jsonl` → illegal transition | `tasks_move_task.py:1248,299,1305`; `tasks_shared.py:369` | M | Coord half owned by merged #168; LANES half = #2549 facet A, EXPLICITLY DEFERRED by fast-follow | **SEQUENCE/defer** (authority line) |
| 2570.4 / 2334 | `agent tasks status` renders stale "In-Progress/⚠️ stale" after a move | `tasks_status_view.py:84-212` | M | Overlaps DRAFT-unmerged `implement-loop-coord-authority-completion` (same read surface) + #2334 open | **SEQUENCE** (don't double-touch) |
| 2493.2 | Hand-written `review-cycle-N.md` non-canonical frontmatter fails merge gate | canonical writer `review/artifacts.py:197`; reject path `review/cycle.py:249-301` ALREADY calls `.write()`+validate | — | Specced fix ALREADY SHIPPED; residual = agent bypassing tool (doctrine) | **EXCLUDE** (optional: alias `cycle:`/`wp:` at `from_dict` + clearer error, tiny) |

## Recommended mission spine (quick-wins II, successor to the fast-follow)

- **WP-A — Guards no-op-stable against their own runtime writes**: 2570.1 (mirror `_drop_vcs_lock_only_meta`) + 2493.1 (broaden `_normalize_tasks_md` to pipe-table cells). Both S, pure-fn, under #2093 line.
- **WP-B — Pre-review gate runner hardening**: 2570.3 (`uv run` interpreter resolution) + 2493.3 (cross-lane gate lock / contention-aware timeout) + 2555.4 (documented sub-agent contract). One surface (`pre_review_gate.py` + `_mt_run_pre_review_gate`). MUST add a pytest-less regression (current tests mask 2570.3).
- **WP-C — Portability + diagnostics papercuts**: 2589 (manifest repo-relative `output_path`) + 2555.5 (schema-drift-first matrix error) + 2555.3 (drop low-weight verbs from bulk-edit `triggered`). All S, single-file, net-new.
- **WP-D — plan/specify scaffold-block ergonomics**: 2566 (return `scaffolded`/`awaiting_content` not `blocked` on first happy-path write; mirror in `mission_create.py`). M, JSON contract — its own WP.
- **Optional WP-E — sync-daemon fan-out budget**: 2555.2 (hard wall-clock + local-first "sync deferred" surface).

**Deferred to coord-authority line (do NOT touch here):** 2570.2/#2549A (lanes status placement), 2570.4/#2334 (status display) — overlap merged #168 and draft `implement-loop-coord-authority-completion`. **2555.1** (recovery cascade) is genuine residual but sits on the same move-task staging surface — include only if we accept the coord-adjacency risk.

**Excluded (already shipped):** 2493.2 review-cycle canonical write; #2549 facet B; #2581; #2573 skip-flag/progress; #2577.
