# Contract: Gate-Adjacent Residue + Emitter Slice (SHRUNK variant) (WP03)

**Decisions**: OD7 shrunk (`01M1VAHPARWJKB35F6E1VH8ZTW`), OD8 residue rides this mission (`01M1VAHQN3WFC58K0TS9C1DYFQ`) · **Constraints**: C-002 (satisfied: PR #3888 merged), C-003, C-006, C-007 · **Requirements**: FR-011, FR-012 (shrunk), FR-013, FR-014, SC-006..008 · **Depends on**: WP01 (single owner of `test_no_dead_symbols.py`; WP03 re-pins after)

## 1. Residue actions

| # | Item | Action | Gate touched |
|---|---|---|---|
| R-1 | `constitution` exclusion | delete `tests/architectural/test_layer_rules.py:65-73` (the comment block + `"constitution",` entry); rerun the layer rules | `test_layer_rules.py` (also #3888's ledger — already merged; no conflict) |
| R-2 | `team_projection/` tombstone | `git rm -r src/specify_cli/team_projection/`; confirm `pyproject.toml` `[tool.hatch.build.targets.wheel].packages` does not list it (if it does, remove the entry); bans in `tests/architectural/test_no_retired_subsystems.py:39-40,99-100` and `pyproject.toml` TID251 assert absence and stay | `test_pyproject_shape.py`, `test_no_retired_subsystems.py` (green by construction) |
| R-3 | `ActionContext` alias | delete `src/mission_runtime/context.py:338` + its `__all__` entry `:342`; delete the `__getattr__` branch `src/mission_runtime/__init__.py:139-142` and the listing `:127`; grep `ActionContext\b` across `src tests docs` → zero | `test_no_dead_symbols.py` if pinned (re-pin, out-of-map) |
| R-4 | 13 test-only `__all__` exports | **demote** (remove from package `__all__`, keep the symbols): the `mission_runtime/__init__.py` re-export set (enumerate from `test_no_dead_symbols.py`'s current pins — the gate names them), `mission_runtime/lifecycle_phase.py::content_present_at_primary_tip`, `kernel/paths.py::get_packs_root_default`; in-package callers (`mission_runtime/resolution.py:52`, `kernel/env_expand.py:63`) keep importing by module path; tests that import via the package facade repoint to the module path | `test_no_dead_symbols.py` re-pins (out-of-map; WP01 owns the file; log rationale) |

## 2. Emitter slice — shrunk variant (C-003 record-don't-touch)

- **Docstring correction only**: `src/runtime/next/event_emitter.py:1-10` currently promises "E3 can register a real handler … at this seam". Rewrite to state: this is a no-op concrete class named identically to the live Protocol `runtime.next._internal_runtime.events.RuntimeEventEmitter`; the real E3 fan-out seam is `specify_cli.status.adapters` (`status/adapters.py:364-366`); disposition is pending the ADR in PR #3898. **No code, name, signature, or import change.**
- **Untouched**: `runtime_bridge.py`, `runtime_bridge_engine.py`, `runtime_bridge_retrospective.py` (`_BufferingRuntimeEmitter:69` is rollback machinery, C-006), `_internal_runtime/events.py`, `tests/runtime/test_bridge_parity.py:1131-1152`.

## 3. FR-011 verified record — `kitty-specs/dead-port-disposition-01M1TZVN/research/emitter-adr-inputs.md`

Extract dossier §3 (3.1 safe-regardless facts, 3.2 ADR-blocked) verbatim plus the verification log lines that back it (name collision `event_emitter.py:23` vs `_internal_runtime/events.py:67`; `sync_emitter` 29 sites: engine ×16 with the `TYPE_CHECKING`-only import at `:80`, bridge ×13 incl. `:195,:1552,:2739,:1614,:2745`; buffer swap `:2149-2150`, flush `:2187` vs `DecisionGitLog` wrap `:1560-1565`; `spec_kitty_events` 9.1.6 `VOLATILE_EVENT_TYPES`; parity oracle). Re-verify each anchor at the WP's HEAD and note deltas. Header: "Input to PR #3898 — recorded, not executed (C-003)."

## 4. Follow-up mint (FR-012 when the ADR lands)

Draft in the WP03 design note the text for a follow-up WP/mission: "Execute RuntimeEventEmitter disposition ADR: resolve the name collision per ADR; one pass over the 29 `sync_emitter` sites (vocabulary + signature); adjudicate the flush-target defect explicitly; update `test_side_effect_sinks_are_actually_reached` in the same PR if the capture is removed; respect C-006/C-007." Gate: ADR merged AND Accepted; Mission A merged. The operator mints it.

**Tasks-finalize re-check**: if PR #3898 is merged-and-Accepted by then, WP03's scope grows to include the execution (or a WP05 is minted). Record the check result in `tasks.md`.

## 5. Verification (WP03)

```bash
.venv/bin/pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_retired_subsystems.py tests/architectural/test_pyproject_shape.py -q
.venv/bin/pytest tests/runtime/test_bridge_parity.py -q     # must be untouched and green
grep -rn "ActionContext\b" src tests docs | grep -v "MissionExecutionContext" ; echo "expect: nothing"
make test-fast
```
