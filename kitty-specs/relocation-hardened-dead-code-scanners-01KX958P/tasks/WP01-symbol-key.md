---
work_package_id: WP01
title: IC-KEY — relocation-tolerant symbol key + live collision classifier
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-009
tracker_refs: []
planning_base_branch: analysis/test-change-coupling
merge_target_branch: analysis/test-change-coupling
branch_strategy: Planning artifacts for this mission were generated on analysis/test-change-coupling. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into analysis/test-change-coupling unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "2171058"
history:
- created at planning (tasks) — keystone relocation key
agent_profile: python-pedro
authoritative_surface: tests/architectural/_symbol_key.py
create_intent:
- tests/architectural/_symbol_key.py
- tests/unit/test_symbol_key.py
execution_mode: code_change
model: sonnet
owned_files:
- tests/architectural/_symbol_key.py
- tests/unit/test_symbol_key.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile
`/ad-hoc-profile-load python-pedro` (role: implementer). Then read [spec.md](../spec.md)
FR-001..005/009 + the (a-k) DoD, [plan.md](../plan.md) §IC-KEY (esp. the FR-003
refuted-reuse note + perf note), [research.md](../research.md) D-1..D-6, and
[contracts/symbol-key-resolver.md](../contracts/symbol-key-resolver.md). The proven
prototype you may lift ClassDef/FunctionDef logic from (DO NOT EDIT):
`tests/architectural/_symbol_identity.py`.

## Objective
Create `tests/architectural/_symbol_key.py` — a relocation-tolerant `SymbolKey` resolver
+ a LIVE collision classifier — plus its unit tests. **Keystone: WP02/WP03 consume this.**
It is a `_`-prefixed, non-collected, **non-`src/`** module (a `src/` module imported only
by tests would red `test_no_dead_modules`).

## Subtasks

### T001 — body-hash normalizer + `definition_span`
Reuse `src/specify_cli/contracts/anchoring.py::code_tokens_by_line` (interpreter-independent;
DO NOT fork a normalizer — S3776). A `body_hash(node, source)` helper hashes the normalized
token lines of the definition span. `definition_span` covers: `ClassDef`, `FunctionDef`,
`AsyncFunctionDef`, `Assign` (lift from the spike), plus the two NEW shapes below (T002, T004).

### T002 — AnnAssign branch (FR-002, HIGHEST)
The spike's `definition_span` has NO `AnnAssign` branch — the ≤14 typed module constants
(`CACHE_PATH: Path = …`, `TTL_SECONDS: int = 3600`, …) would otherwise be un-keyable (the
re-introduced T001 bug). Add a branch matching `isinstance(node, ast.AnnAssign) and
isinstance(node.target, ast.Name)` → span `(node.lineno, node.end_lineno)`, mirroring the
`Assign` branch. All real entries are annotated-with-value (hashable); a bare `X: int` would
still hash (line tokens exist).

### T003 — facade-dict KEY-side resolver, BY SHAPE (FR-003 — read the plan's refuted-reuse note)
There are TWO facade dict shapes: `sync/__init__.py _LAZY_IMPORTS` `{name:(module,attr)}`
(2-tuple) and `runtime/__init__.py _EXPORT_MODULES` `{name:module_const}` (1-value — the 6
`specify_cli.runtime::*` entries). The gate's `_record_facade_edges` handles ONLY the 2-tuple
(guard `len!=2: continue`), is **byte-frozen (C-005)**, and discards the name.
**Re-derive the dict-parse KEY-side** to yield `name → (module, attr)` (needed to locate the
body); reuse ONLY the two PURE helpers `_find_facade_lazy_dict_name` + `_resolve_relative_module`
(DO NOT mutate their signatures — LOW-5 pin). Enumerate by shape, not "all 8".
**⚠️ CIRCULAR-IMPORT (post-tasks squad DEFECT 1)**: `test_no_dead_symbols.py` (WP02) imports
`SymbolKey`/`classify_collisions`/`key_tier` from THIS module — so a TOP-LEVEL
`from ...test_no_dead_symbols import _find_facade_lazy_dict_name` here would be circular at load
time. Import the two pure helpers via a **function-local (deferred) import** inside the facade
resolver, not at module top.

### T004 — single-alias ImportFrom hash (FR-004)
The 33 multi-target `ImportFrom` entries: a whole-statement hash is sibling-contaminated
(zero relocation tolerance). Scope the span/hash to the SINGLE aliased name being keyed.

### T005 — live collision classifier + key_tier (FR-005 + FR-009 ≥2-escalation)
`classify_collisions(all_symbols)` builds a `bare_name → [live locations sharing a body_hash]`
index by ONE walk of the `src/` corpus (reuse cached trees where possible — perf). This runs
**every gate invocation** — NOT frozen. `key_tier(key, index)`: content key whose bare_name is
NOT a collision and resolves to exactly one location → `content`; a collision bare_name OR a
key resolving to ≥2 live locations → escalate to `(bare_name, module_path, body_hash)` if that
disambiguates, ELSE **fail-closed**. Today's collision set == the ArtifactKind trio, but the
classifier MUST re-derive it (a future byte-identical pair must be caught automatically).

### T006 — fail-closed for None-key (FR-009)
Any shape the resolver cannot span returns `None`. NO `if key is None: <exempt>` — the consumer
(WP02) fail-closes. Provide a clear reason string so WP02 can flag it.

### T007 — unit tests + DoD-j key-invariance probe + perf-budget
`tests/unit/test_symbol_key.py` (`pytestmark = [pytest.mark.unit]`; NOT under
`tests/architectural/` → no shard-map tax). Cover: content-tier relocation invariance
(module move + sibling reorder + blank/comment); **DoD-j key-invariance** — body_hash stable
under AnnAssign annotation whitespace (`X:int` vs `X : int`) + single-alias ImportFrom +
3.11↔3.12 (`code_tokens_by_line` parity); ≥2-resolution → fail-closed; None-key → None; the
ArtifactKind-trio collision → module_path/fail-close. Add a **perf-budget assertion** (the
tokenize pass is net-new — assert the index build stays under a bound).

## Branch Strategy
Planning/merge branch `analysis/test-change-coupling`; worktree per `lanes.json` via
`spec-kitty agent action implement WP01 --agent <you>`. No dependencies (keystone).

## Definition of Done
- `_symbol_key.py` resolves Class/Func/Assign/AnnAssign/single-alias-ImportFrom/facade (both
  shapes); content-only default, module_path/fail-close on ≥2; None on undecidable.
- Unit tests green incl DoD-j invariance + perf-budget; ruff + mypy clean on new files.
- WP02/WP03 can import the resolver + classifier. WP06-spike files UNTOUCHED.

## Reviewer guidance (reviewer-renata, opus)
Confirm: NOT bare-name-alone; AnnAssign branch present + real entries hashable; facade resolver
handles BOTH shapes (esp. the runtime 1-value the gate skips) and does NOT edit `_record_facade_edges`;
single-alias scoping; collision classifier is LIVE (re-derived, not frozen) and fail-closes on ≥2;
`code_tokens_by_line` reused (no forked normalizer). Confirm test_symbol_key.py is under tests/unit.

## Activity Log
- 2026-07-11T18:54:37Z – claude:sonnet:python-pedro:implementer – shell_pid=2013062 – Assigned agent via action command
- 2026-07-11T19:19:54Z – claude:sonnet:python-pedro:implementer – shell_pid=2013062 – Ready: SymbolKey resolver (Class/Func/Assign/AnnAssign/single-alias/facade-both-shapes) + live collision classifier (>=2 fail-close, re-derived) + fail-closed None-key; 37 unit tests incl DoD-j invariance + perf-budget; ruff+mypy clean.
- 2026-07-11T19:20:27Z – claude:opus:reviewer-renata:reviewer – shell_pid=2171058 – Started review via action command
- 2026-07-11T19:23:12Z – user – shell_pid=2171058 – Review PASSED (opus/reviewer-renata). All 8 make-or-break criteria verified against real code+canonical sources. (1) NOT bare-name-alone: SymbolKey always carries body_hash; byte-identical same-name collisions escalate to module_path via live key_tier or fail-close — T004 no-false-negative preserved. (2) AnnAssign branch present (definition_span L171-174); <=14 typed constants keyable+hashable; whitespace-invariance tested. (3) Facade by-shape: _facade_target handles BOTH sync 2-tuple _LAZY_IMPORTS AND runtime 1-value _EXPORT_MODULES (the shape gate's _record_facade_edges len!=2 SKIPS); _record_facade_edges untouched (empty git log); 2 pure helpers imported via function-local deferred import — no circular load. (4) Single-alias hash scoped to the one ast.alias's own columns; sibling-edit immunity tested. (5) Live classifier: classify_collisions re-derives bare_name->[Location] index every call from corpus, NOT frozen — proven by test_dod_i catching a NEW non-ArtifactKind byte-identical pair. (6) Fail-closed: None-key + >=2-resolution both return None; no 'if key is None: exempt'. (7) body_hash reuses code_tokens_by_line (no forked normalizer). (8) test under tests/unit/ w/ pytest.mark.unit, DoD-j invariance + perf-budget. 37 passed, ruff+mypy clean, only 2 owned files touched.
