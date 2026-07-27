# Tracer — Tooling Friction

Mission: `mission-resolver-port-01KX1C05` · #2173 Phase-2 MissionResolver port.
Seeded at planning with **known friction to watch** (from in-lineage retrospectives). **Append every real
friction hit during implement; assess at close and file the durable ones to #2017 / the relevant epic.**

## Watch-list carried in from prior missions (single-authority-resolution-gates, read-surface-ssot, coord-primary-partition-lock)

- **F1 — Arch marker gate is vacuous under `.worktrees/`.** A green marker run inside an execution
  worktree proves nothing; verify arch gates from the **primary checkout** (NFR-002). Confirmed friction
  in the read-surface mission.
- **F2 — Draining one call-site can drop TWO counters at once** (its own allowlist entry AND a
  `primary_feature_dir_for_mission` call inside a removed cascade). Always run the FULL arch suite +
  repo-wide floor-constant grep, not a scoped `pytest -k`.
- **F3 — Floor constants are duplicated across gate files.** `CANONICALIZER_FLOOR==44` /
  `ROUTED_CANONICALIZER_FLOOR==39` are independently pinned in BOTH
  `test_resolution_authority_gates.py` and `test_coord_read_residuals_closeout.py`. A drain must update
  every twin; grep the constant name repo-wide before assuming one file owns it.
- **F4 — `kitty-specs/` tracer edits on a lane branch commit silently, then BLOCK `move-task`.** Write
  these tracer files from the **primary checkout**, not inside a lane worktree.
- **F5 — Census/allowlist entries are token-authoritative; `line:` is non-authoritative.** Pin gate
  allowlists on tokens/symbols, never line numbers (they drift on merge).
- **F6 — `spec-commit` on a protected/coord topology** materializes the coordination worktree and lands
  on the coordination branch. This mission is `topology: coord` (coordination branch
  `kitty/mission-mission-resolver-port-01KX1C05`) — expect spec/plan commits to route there.
- **F7 — CI-only shards.** Some gates (terminology, integration/git) run only in CI's
  `integration-tests-core-misc` job. Run `tests/architectural/` locally before pushing doctrine/prose
  (the #2447 doc tail touches shipped doctrine).

## Post-plan squad additions (2026-07-08)
- **F8 — layer-ledger is subpackage-keyed, not direction-keyed.** `mission_runtime → specify_cli.context`
  reds `test_layer_rules.py` even though `mission_runtime → specify_cli.{core,missions,coordination}` is
  fine. Any new cross-package import must be checked against `_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI`
  (`test_layer_rules.py:76-95`); the gate does a full `ast.walk` so lazy in-function imports don't escape.
- **F9 — plan censuses undershot 4/12/handful → ≥9/14/~16.** Treat plan counts as floors, not exhaustive;
  re-grep before sizing a WP (whack-a-field trap).

## Sonar / campsite watch (operator instruction 2026-07-08 — clean while here)
Run a per-touched-file Sonar census at `/tasks` and per-WP at implement. Known attack-vectors already found:
- **SAFE (fold)**: `cli/commands/agent/mission_parsing.py:259` hardcodes `"%Y-%m-%dT%H:%M:%SZ"` → use the shared constant (IC-06).
- **ADJACENT (note, separate cleanup)**: S1192 — the stamp literal recurs 18× with 4 redundant constant
  defs (`review/cycle.py:23`, `cli/commands/agent/tasks.py:355`, `tasks_materialization.py:43`,
  `task_utils/support.py:22`).
- **OUT (tracked/other track)**: `resolution.py` 1465-LOC god-module extraction → #2173 decomposition;
  `frontmatter.py:191` naive `datetime.now().isoformat()` (no UTC) — latent, separate.
- Per-WP rule: census Sonar issues in each touched file; SAFE→fold, ADJACENT→note, OUT→tracked home
  (memory: sonar-attack-vector-campsite).

## Post-tasks squad findings + remediations (2026-07-08, alphonso/robbie/paula)
Remediated in WP prompts before implement:
- **MUST-FIX (WP01)**: rename omitted `mission_runtime/__init__.py` (re-exports the class + `__all__`) and
  the surface pin `test_mission_runtime_surface.py:53 _PUBLIC_SURFACE` → would break `import mission_runtime`
  suite-wide. Added `__init__.py` to owned_files + T003/T005 steps.
- **WP01 phantom site**: `runtime_bridge.py` was a WRONG rename site (only `StepContractExecutionContext`);
  removed. The `grep -v StrEnum` recipe didn't exclude StrEnum *consumers* (test_context_validation_unit.py
  24 refs) → replaced with import-origin discrimination.
- **WP03 landmine (Paula)**: `apply.py:412 apply_proposals` is C901=14 — extract-first before adding a
  branch or the diff reds ruff. Flagged WP03 as heaviest WP; T015 liftable.
- **WP06 completeness**: ~18 isoformat copies in NON-owned files (sync/review/skills/merge/state) → Priti
  follow-up so "one canonical helper" isn't half-true; added `charter/evidence/code_reader.py:108` to the
  cross-package triage; naming caution (`task_utils.now_utc()` is a stamp, not iso).
- **WP04**: `template_catalog.py`/`neutrality/lint.py` walk NON-kitty-specs trees → gate keys on scan-root,
  don't list them (census over-inclusion).
- **Line drifts corrected**: resolve_placement_only 866→1143, resolve_action_context 1384→1354, sentinel
  944→948, ActionContext alias 349→351, glossary/events 215→217, retrospective_terminus 63→65.
- **CONFIRM-OK**: parallel-group collision safe (siblings have zero ExecutionContext refs); acceptance
  WP03/WP05 boundary safe; dependency spine correct; codebase already clean at C901 ceiling (only SAFE
  campsite = mission_parsing.py:259, already T026).

## Friction encountered during implement
_(append dated entries here)_
