# Quickstart — Verifying Landing-Pass Campsite Follow-ups

Run all commands from the mission clone root
(`/home/stijn/Documents/_code/SDD/fork/spec-kitty-csf2670`). Use `uv run` so the
lane resolves the clone's own `src/`, never the primary checkout's.

## IC-01 — Shard fallback (#2671)
```bash
# Red-first: a fixture arch file with no shard entry currently double-reds.
uv run pytest tests/architectural/test_arch_shard_marker_completeness.py \
              tests/architectural/test_gate_coverage.py -q
# After the fallback: an unregistered tests/architectural/*.py needs 0 table edits.
uv run pytest tests/test_shard_registry_fallback.py -q      # new registry unit test
```
Green criterion: a new arch file is auto-marked; GC-1 completeness + orphan gates pass; explicit entries still win; header doctrine updated.

## IC-02 — Bite-battery isolation (#2673 + #2638)
```bash
# The structural invariant: real source is byte-unchanged after the mutating test.
uv run pytest tests/architectural/test_single_mission_surface_resolver.py \
              tests/architectural/test_surface_resolution_audit.py \
              tests/architectural/test_untrusted_path_containment.py \
              -n auto --dist loadfile -q     # repeat ≥5× as flake smoke
git status --porcelain src/specify_cli/core/mission_creation.py   # must be empty after the run
```
Green criterion: parallel runs stop racing; the bite-battery still flags the injected raw join.

## IC-03 — Color/synthesis hygiene (#2672)
```bash
uv run pytest <color/synthesis-manifest test> -q
git status --porcelain .kittify/charter/synthesis-manifest.yaml   # must be empty after the run
```
Green criterion: deterministic via CliConsole; no real-file mutation; no NO_COLOR dependence.

## IC-04 — Sync remediation registry (#2674)
```bash
uv run pytest tests/specify_cli/sync/test_preflight_remediation_hints.py -q
```
Green criterion: the guard iterates the full registry; a mistyped inline command fails it; no duplicated remedy literal.

## IC-05 / IC-06 — Type-debt (#2675)
```bash
uv run mypy src/specify_cli/status/lane_reader.py \
            src/specify_cli/cli/commands/agent/workflow_executor.py \
            src/specify_cli/status/status_transition.py \
            src/specify_cli/missions/plan/specify_interview.py \
            src/specify_cli/missions/plan/plan_interview.py \
            src/specify_cli/missions/_read_path_resolver.py \
            src/specify_cli/status/emit.py \
            src/specify_cli/upgrade/migrations/m_2_1_4_enforce_command_file_state.py
uv run pytest tests/specify_cli/ -k "lane_reader or workflow_executor or interview" -q
```
Green criterion: 0 mypy errors on in-scope surfaces; 0 new suppressions; new branches covered.

## Whole-mission gate (pre-PR)
```bash
uv run ruff check .
PWHEADLESS=1 uv run pytest tests/architectural/ -n auto --dist loadfile -q
pytest tests/architectural/test_no_legacy_terminology.py   # terminology guard
```
