# Quickstart: FSM Write-Path Integrity

All commands run from the repository root checkout on branch `missions/coreloop-proto-missions`. Venv: `uv sync --frozen --all-extras` once, then use `.venv/bin/pytest` directly.

## Baseline (every WP boundary — NFR-005 / C-010)

```bash
make test-fast
.venv/bin/pytest tests/status tests/specify_cli/status tests/specify_cli/coordination -q
.venv/bin/pytest tests/architectural/test_status_module_boundary.py tests/architectural/test_no_legacy_terminology.py -q
```

Never `make test-full` locally; never the full `tests/architectural/` directory (no cross-cutting file is touched by this mission).

## Per-WP blast radius

| WP | Additional suites |
|---|---|
| WP01 | `tests/specify_cli/retrospective tests/specify_cli/migration tests/specify_cli/merge tests/status/test_locking*.py` |
| WP02 | `tests/specify_cli/coordination/test_status_transition.py` (incl. the #3460 / #1848 pins below), `tests/specify_cli/cli/commands/agent/test_tasks_move_task_degod.py`, `tests/architectural/test_2093_authority_invariant.py` |
| WP03 | the two new gates + `tests/architectural/test_status_module_boundary.py` |
| WP04 | `tests/specify_cli/lanes tests/specify_cli/cli/commands/agent/` (probe-site pins), `tests/status/test_wp_state*.py tests/status/test_transitions*.py` |
| WP05 | `tests/runtime/test_bridge_io.py tests/runtime/test_bridge_engine.py tests/runtime/next`, `tests/architectural/test_layer_rules.py` (ledger) |

## Pins that must stay green through WP02

```bash
.venv/bin/pytest \
  "tests/specify_cli/coordination/test_status_transition.py::test_inner_state_annotation_degrades_when_coordination_branch_missing" \
  "tests/specify_cli/coordination/test_status_transition.py::test_transactional_emit_fails_closed_when_coordination_branch_missing" \
  "tests/specify_cli/cli/commands/agent/test_tasks_move_task_degod.py::test_runtime_state_persistence_error_propagates" -q
```

## Red-first repro checklist (each must be RED on the base before its WP, GREEN after; then deleted/relocated — C-009)

| SC | Repro shape | WP |
|---|---|---|
| SC-001 | force `BookkeepingTransaction` commit failure; interleave `_append_retro_lifecycle_event` between pre-emit size capture and `transaction.py:944` truncate; assert the retro event survives | WP01 |
| SC-006a | two missions, equal slug, distinct `feature_dir.name` ⇒ distinct lock files | WP01 |
| SC-002 | coord-topology mission, fallback arm, commit forced to fail ⇒ zero SaaS/zeitgeist fan-out calls recorded | WP02 |
| SC-003 | owned-mission request via batch door ⇒ `ActionContextError` (today: silently skipped) | WP02 |
| SC-007 | stored-`LANES` mission via plain door ⇒ `git rev-list --count HEAD` unchanged (GREEN on main, stays green) | WP02 |
| SC-004 | synthetic out-of-pipeline `open(.., "a")` on `status.events.jsonl` ⇒ gate RED; zero-match scan ⇒ gate RED; allowlist growth ⇒ RED | WP03 |
| SC-005 | verdict-less shell emit `planned→claimed` with dep `in_progress` ⇒ succeeds on main, refused after | WP04 |
| SC-006b–d | slug-collision distinct runs; crash-window cursor; `status.json` byte-identical; missing `state.json` loud | WP05 |

## Verifying the AST caller census (used for Q4; re-run if the tree moves)

```bash
python3 - <<'EOF'
import ast, pathlib
targets={"emit_status_transition","emit_status_transition_batch","emit_status_transition_transactional",
         "emit_status_transition_batch_transactional","emit_inner_state_changed_transactional","emit_inner_state_changed"}
hits={t:[] for t in targets}
for p in pathlib.Path("src").rglob("*.py"):
    for n in ast.walk(ast.parse(p.read_text())):
        if isinstance(n,ast.Call):
            f=n.func; name=f.id if isinstance(f,ast.Name) else (f.attr if isinstance(f,ast.Attribute) else None)
            if name in targets: hits[name].append(f"{p}:{n.lineno}")
for t in sorted(hits): print(t, len(hits[t]), *hits[t], sep="\n  ")
EOF
```

## Decision records

```bash
spec-kitty agent decision verify --mission fsm-write-path-integrity-01M1TZV6
ls kitty-specs/fsm-write-path-integrity-01M1TZV6/decisions/
```

## Next step

`/spec-kitty.tasks` (operator-invoked). Carry: the five-WP slicing, the Q10 rider (WP05 first, no deps), WP02's design-note obligations (`research.md` §8).
