# Contract: mission-DSL v1 Retirement (FULL) + `transitions` Drop (WP01) · `decision.py` dead readers (WP04)

**Decisions**: OD1 FULL (`01M1VAHEBB54DDDVCEX2R4BMCJ`), OD3 delete pack blocks, OD4 events stays · **Constraints**: C-004, C-005, C-007, NFR-001..003 · **Working assumption**: OD2 = retire (deferred marker in `plan.md`)

## 1. Red-first ratchet (FR-004, SC-001) — `tests/specify_cli/mission_v1/test_import_hygiene.py` (new, permanent)

```python
def test_events_import_does_not_load_transitions() -> None:
    code = (
        "import sys, specify_cli.mission_v1.events as e; "
        "bad = sorted(m for m in sys.modules if m == 'transitions' or m.startswith('transitions.') or m == 'six'); "
        "print(','.join(bad))"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True, env=_hermetic_env())
    assert out.stdout.strip() == "", f"hot path loaded: {out.stdout.strip()}"
```
- RED on main (prints `six,transitions`); GREEN after §2; stays forever (negative invariant, not a parity test — C-009 of Mission A does not apply).
- A second assertion: `sorted(m for m in sys.modules if m.startswith('specify_cli.mission_v1'))` == `['specify_cli.mission_v1', 'specify_cli.mission_v1.events']`.

## 2. Deletion / retention list (FULL)

| Action | Paths |
|---|---|
| DELETE | `src/specify_cli/mission_v1/{compat,runner,guards,schema}.py` |
| REWRITE | `src/specify_cli/mission_v1/__init__.py`: docstring (no DSL advertising; states that `events` is the surviving module and why); body = `from specify_cli.mission_v1.events import emit_event, read_events` + `__all__ = ["emit_event", "read_events"]`. Delete `MissionProtocol`, `load_mission`, `load_mission_by_name`, `yaml`/`Path`/`Protocol` imports. |
| KEEP | `src/specify_cli/mission_v1/events.py` byte-identical. |
| DELETE (tests) | `tests/specify_cli/mission_v1/test_mission_v1_runner_unit.py`, `test_mission_v1_compat_unit.py`, `test_mission_v1_guards_unit.py`, `test_mission_v1_schema_unit.py`, `tests/specify_cli/mission_v1/test_guards_bulk_edit.py`, `tests/missions/test_e2e_mission_v1_integration.py`, `tests/missions/test_mission_loading_integration.py`, `tests/missions/test_mission_guards_integration.py` (confirm exact filenames with `ls`; delete only files whose imports are exclusively retired modules). |
| TRIM (tests) | `tests/specify_cli/mission_v1/test_mission_v1_events_unit.py` — remove the runner half (`:228-304`), keep the events half. `tests/research/test_research_plan_missions_integration.py:21` and `tests/missions/test_mission_software_dev_integration.py:21` — remove the `validate_mission_v1` schema-validation halves only; keep the rest. |
| PACKS | delete `states:`/`transitions:` blocks from `packs/built-in/missions/{software-dev,plan,research}/mission.yaml`; `src/specify_cli/mission.py:59-67` comment updated (tolerance retained). |
| DOCSTRINGS | `src/specify_cli/review/gate_registry.py:7,132` → cite git history (`mission_v1/guards.py`, retired in mission dead-port-disposition-01M1TZVN) instead of a live module; `src/specify_cli/skills/manifest_store.py:27` mention of `mission_v1.schema` → remove/reword. |

## 3. Same-WP gate edits (C-005, NFR-003)

1. `tests/architectural/test_no_dead_symbols.py:720-727` — remove the three `mission_v1` pins.
2. `tests/architectural/test_no_dead_symbols.py:3278` — remove `specify_cli.mission_v1.schema::strip_v1_keys` (drift D-1).
3. `tests/specify_cli/test_wp_frontmatter_fold.py:60` — remove `("specify_cli.mission_v1.guards", "read_wp_frontmatter")`; read the surrounding gate docstring (`:4`) and update it.
4. `tests/architectural/_gate_coverage.py:1456` — row stays; run the coverage gate and confirm it does not require every listed dir to contain ≥N tests; if it does, the trimmed events test + ratchet satisfy it.
5. `tests/architectural/test_layer_rules.py:194` — `mission_v1` ledger row stays (live edge `next_invocation_lifecycle.py:332`). Run `test_runtime_ledger_has_no_stale_entries`.
6. Non-vacuity: after the deletions, run the whole `tests/architectural/` once (pyproject touched → cross-cutting rule) and confirm zero red, zero "pin references a missing symbol" warnings.

## 4. Dependency mechanics (FR-005, C-004, NFR-002)

```bash
# pyproject.toml: delete line 82  "transitions>=0.9.2",  # State machine library for mission DSL v1
uv lock                                   # regenerate; never hand-edit
git diff uv.lock | grep '^[-+]name = '    # expect: -name = "transitions" only; six remains (python-dateutil)
uv sync --frozen --all-extras             # clean-install smoke in the worktree venv
.venv/bin/pytest tests/architectural/test_pyproject_shape.py -q
```
CHANGELOG: one entry under `## [Unreleased] - 3.2.7rc1` ("Removed: `transitions` dependency and the mission-DSL v1 runtime (`specify_cli.mission_v1.{compat,runner,guards,schema}`); `mission_v1.events` remains"). No version bump (rc cycle already open). Do NOT bundle `truststore` (PR #3899).

## 5. `decision.py` dead readers (WP04, FR-015, OD9) — after Mission A merges

- Delete `derive_mission_state` (`src/runtime/next/decision.py:187-216`) and `evaluate_guards` (`:218-235`) including their `.. deprecated:: 2.0.0` blocks and the lazy `from specify_cli.mission_v1.events import read_events` at `:200`.
- Delete the legacy section of `tests/next/test_decision_unit.py` (`:28` import, `:189-219`).
- AST proof in the WP: `grep -rn "derive_mission_state\|evaluate_guards" src tests` shows only `runtime_bridge_cores`' unrelated `evaluate_guards*` family.
- Ledger: `mission_v1` row stays (edge at `next_invocation_lifecycle.py:332`); run `test_layer_rules.py`.
- Owned file: `src/runtime/next/decision.py` alone (+ the one test file). No other runtime file.

## 6. Verification (WP01)

```bash
.venv/bin/pytest tests/specify_cli/mission_v1 tests/missions tests/research tests/specify_cli/next/test_next_invocation_lifecycle_seam.py -q
.venv/bin/pytest tests/architectural -q -p no:cacheprovider     # once, cross-cutting (pyproject touched)
.venv/bin/pytest tests/specify_cli/test_wp_frontmatter_fold.py -q
make test-fast
grep -rn "transitions" src --include='*.py' | grep -i "^.*import" ; echo "expect: nothing"
```
