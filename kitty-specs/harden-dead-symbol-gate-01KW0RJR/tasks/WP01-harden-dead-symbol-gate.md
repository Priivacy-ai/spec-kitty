---
work_package_id: WP01
title: Harden the dead-symbol gate
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
tracker_refs:
- '2158'
planning_base_branch: feat/harden-dead-symbol-gate
merge_target_branch: feat/harden-dead-symbol-gate
branch_strategy: Planning artifacts for this mission were generated on feat/harden-dead-symbol-gate. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/harden-dead-symbol-gate unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-harden-dead-symbol-gate-01KW0RJR
base_commit: e65501c24e179cca684db3583cf2f0120a513af6
created_at: '2026-06-26T02:11:08.692645+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: claude
shell_pid: '1294729'
history:
- date: '2026-06-26'
  action: created
  actor: claude
agent_profile: python-pedro
authoritative_surface: tests/architectural/
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/_baselines.yaml
- src/specify_cli/sync/owner.py
- src/specify_cli/auth/transport.py
- src/specify_cli/compat/safety_modes.py
- src/specify_cli/legacy_detector.py
- src/specify_cli/readiness/upgrade_ux.py
- src/doctrine/versioning.py
- src/specify_cli/orchestrator_api/envelope.py
- tests/agent/test_envelope_unit.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile via the `/ad-hoc-profile-load` skill (profile: **python-pedro**, role: implementer). Adopt its boundaries, governance scope, and initialization declaration for this work package. Then return here.

## ⚠️ Before you start

1. **DIR-003**: best-effort `unset GITHUB_TOKEN && gh issue edit 2158 --repo Priivacy-ai/spec-kitty --add-assignee MOES-Media` (known to fail upstream — note + continue).
2. **Run all `spec-kitty`/`pytest`/`ruff`/`mypy` via `uv run …`** (installed `spec-kitty` lags local `main`).
3. **Read the design**: `kitty-specs/harden-dead-symbol-gate-01KW0RJR/research.md` (gate internals + per-pattern rules, D-01..D-05) and `data-model.md` (the exact AST structures + detector table). They are authoritative.

## Objective

The dead-symbol gate (`tests/architectural/test_no_dead_symbols.py`) has a parser bug that blinds it to
57 modules and caller detection that only sees `from X import Y`. Fix the parser AND add four
structurally-anchored detectors so the ~119 symbols that surface are recognized **live** (no allowlist
growth), dispose of the genuinely-dead residue, wire a latent security check, and leave the architectural
+ contract suites green — **without weakening the gate** (no false negatives).

## THE LOAD-BEARING INVARIANT (C-001 / NFR-001)

Every detector must bind proof-of-life to a **RESOLVED declaring module**, never a bare name. A dead
`foo` in module X is rescued ONLY when `bar.foo` (or `getattr(bar,"foo")`) is found where `bar` provably
resolves — via the file's own import table — to X. The T004 no-false-negative test is the binding guard.
Do NOT add any rule that counts a bare symbol-name string match, a global annotation-name match, or a
`tests/` import as "alive" (research D-03 — those mask real dead code).

## Constraints

- **C-001**: detectors are AST + resolved-module anchored, never substring.
- **C-002**: each `_baselines.yaml` edit carries a `# justification:` and the declared count equals the live frozenset size.
- **C-003**: re-confirm `category_a`/`category_b` live sizes vs the base (depends on whether #2159/#2048 have merged) before setting counts.
- **C-004**: re-verify each delete/demote symbol against the live tree before acting; a demote is safe only if no `from mod import sym` and no `import *` reaches it.
- **OUT OF SCOPE**: a 5th register-arg detector (DEMOTE those symbols instead); making the symbol-gate baselines a real ratchet (follow-up).

## Subtasks

### T001 — FR-001: fix `_extract_all_literal` + unit test

**Steps**:
1. In `tests/architectural/test_no_dead_symbols.py`, find `def _extract_all_literal` (~L910). In the `elif isinstance(node, ast.AnnAssign):` branch, when the target is NOT `__all__`, `continue` to the next node instead of falling through to `if value is None: return frozenset()` (~L938). Only return the empty frozenset for an `__all__` AnnAssign declared without a value. Preserve the `ast.Assign` and dynamic-`__all__` (`return None`) behavior.
2. Add a focused unit test: a module AST whose first top-level node is a non-`__all__` `AnnAssign` (e.g. `_X: int = 1`) followed by `__all__ = ["foo"]`, asserting `_extract_all_literal` returns `frozenset({"foo"})`.

**Validation**: new unit test passes; the function no longer empties a module's `__all__` on a leading annotated constant.

### T002 — FR-002: per-tree alias map + module-style detector (a) [subsumes (c)]

**Purpose**: Recognize `import mod` / `from pkg import mod as m` then `m.symbol` (and the Typer `app.command()(mod.fn)` sub-case) as a caller.

**Steps**:
1. Build, per cached tree in `path_to_tree`, an `alias_map: dict[str, str]` of `local name → resolved dotted module` from `ast.Import` (`alias.asname or alias.name`) and `ast.ImportFrom` with `asname` (`from pkg import mod as m` → `pkg.mod`, resolving relative levels like `_resolve_import_from`).
2. Add a detector that walks `ast.Attribute` nodes where `node.value` is `ast.Name(id in alias_map)`; resolve `alias_map[id]` → module; record an edge `(module, node.attr)` into the SAME `per_symbol` index `_imports_by_target` builds (so `_symbol_has_caller`'s direct/parent/submodule rules apply unchanged). Fold this into `_imports_by_target` (one extra branch in its existing `ast.walk`) or a sibling pass over `path_to_tree`.
3. Confirm (c) Typer registration is covered: `app.command()(lifecycle_module.specify)` contains the `Attribute` `lifecycle_module.specify` — step 2's walk visits it. No separate rule.
4. Add a unit test: synthetic two-module corpus where module B does `import a` + `a.live_sym()`; assert `a.live_sym` is NOT flagged.

**Validation**: `compat.messages::render_human`, `dashboard.scanner::gather_feature_paths`, `cli.commands.lifecycle::{specify,plan,tasks}` are recognized live (no allowlist entry); the unit test passes.

### T003 — FR-002: getattr-string (d) + `__getattr__` facade (b) detectors

**Steps**:
1. **(d-getattr)**: walk `ast.Call` where `func` is `Name(id="getattr")`, `args[1]` is a string `Constant`, and `args[0]` is `Name(id in alias_map)`; resolve and record `(module, literal)`. (Reuses T002's alias map.)
2. **(b) facade**: detect a module with a top-level `FunctionDef("__getattr__")`; collect re-export targets from any module-level dict-literal whose values are 2-tuples `(<module-ref>, <str name>)` (e.g. `sync/__init__.py:51`); mark the named symbol in the referenced submodule as live (anchored to the tuple's submodule, NOT the facade's `__all__` text).
3. Add unit tests for each (synthetic getattr call; synthetic facade dict).

**Validation**: `migration.schema_version::MIN_SUPPORTED_SCHEMA` (getattr) and the `specify_cli.sync::*` facade re-exports are recognized live; unit tests pass.

### T004 — NFR-001: no-false-negative regression test

**Steps**:
1. Add a test that constructs a synthetic module with a symbol in `__all__` that has NO caller of ANY recognized kind (no `from`-import, no `alias.symbol`, no `getattr`, no facade tuple, no registration) and asserts the gate STILL flags it as an offender. This proves the four detectors widened vision without blinding the gate.

**Validation**: the regression test passes (the synthetic dead symbol is still caught).

### T005 — FR-003/004/006/007: dispose the residue

**Steps** (re-verify each against the live tree first — C-004):
1. **DELETE** `specify_cli.sync.owner::_daemon_root`: remove the re-export (owner.py:51/833) and its `__all__` entry; callers already use `daemon._daemon_root()`.
2. **DEMOTE** (drop from `__all__`, keep def — confirm no external `from`-import / `import *`): `auth.transport::reset_user_facing_dedup`, `sync.owner::check_daemon_owner_match`, `compat.safety_modes::{_ORCHESTRATOR_API_UNSAFE_SUBCOMMANDS, SafetyPredicate, _orchestrator_api_predicate, _mission_state_predicate}`, `legacy_detector::LEGACY_LANE_DIRS`, `readiness.upgrade_ux::{PromptCallback, UpgradeUxOutcome}`, `doctrine.versioning::migrate_v1_to_v2`, and any residual annotation-only/test-only symbol the detectors don't rescue (the gate run after T002/T003 will name them).
3. **ALLOWLIST-as-deferred** the `auth.transport` trio (`get_client`, `get_async_client`, `reset_clients`): one justified allowlist entry referencing the pending SaaS migration wave (`saas_client.py`).
4. **`_baselines.yaml`**: set `category_a`/`category_b` to the post-mission live frozenset sizes (≤ base — no net growth, NFR-003) with `# justification:` comments.

**Validation**: `_daemon_root` gone; demotes applied; auth trio has exactly one deferred allowlist entry; baselines match live sizes and show no growth.

### T006 — FR-005: wire the `BANNED_FLAGS` security check

**Steps**:
1. In `src/specify_cli/orchestrator_api/envelope.py`, in `parse_and_validate_policy`, reject any `dangerous_flags` entry that is a member of `BANNED_FLAGS` (today defined but never enforced) — return/raise the typed validation error the envelope contract uses (match the existing validation-error path).
2. Add a test in `tests/agent/test_envelope_unit.py`: a policy with a banned flag (e.g. `--yolo`) is rejected; a policy with only allowed dangerous flags still passes.
3. This makes `BANNED_FLAGS` a genuinely-referenced constant, so the un-blinded gate sees it live (no disposition needed for it).

**Validation**: banned-flag rejection test passes; `BANNED_FLAGS` is not flagged by the gate.

### T007 — Verify everything green + no growth

**Steps**:
1. `PWHEADLESS=1 uv run pytest tests/architectural/test_no_dead_symbols.py -q` — green, and the previously-hidden 57 modules are now inspected (spot-check that e.g. `compat.messages`/`dashboard.scanner` symbols are evaluated, not skipped).
2. `PWHEADLESS=1 uv run pytest tests/architectural/ tests/contract/ -q`.
3. Confirm ZERO new allowlist entries for the ~107 live symbols (only the deferred auth trio adds one); `category_a`/`category_b` frozenset counts ≤ base.
4. Diff-scoped `uv run ruff check <changed .py>`; `uv run mypy src/specify_cli/orchestrator_api/envelope.py`.
5. IGNORE the documented pre-existing env/order-flake failures (local `python -m ruff` tid251, `test_pytest_marker_convention`, other missions' `MISSING_FRONTMATTER`).

**Validation**:
- [ ] `test_no_dead_symbols.py` green with the 57 modules inspected; no-false-negative test passes.
- [ ] No net allowlist growth; `--yolo` rejected.
- [ ] Full architectural + contract suites green; `ruff`/`mypy` clean on the diff.

## Branch Strategy

- **Planning base branch**: `feat/harden-dead-symbol-gate`.
- **Final merge target**: `feat/harden-dead-symbol-gate`, which merges to `main` via a cross-fork PR (push to `fork`, `gh pr create --repo Priivacy-ai/spec-kitty --head MOES-Media:feat/harden-dead-symbol-gate`). Do not push to `origin/main`.
- Execution worktrees are allocated per computed lane from `lanes.json`.

## Definition of Done

- `_extract_all_literal` fixed (+ unit test); 4 detectors (a/c/d-getattr/b) added, each anchored to a resolved module + unit-tested; the no-false-negative regression test passes.
- `_daemon_root` deleted; the residue DEMOTEd; the auth trio allowlisted-deferred; `BANNED_FLAGS` enforced + tested.
- `category_a`/`category_b` show no net growth; `pytest tests/architectural/ tests/contract/`, `ruff`, `mypy` green.

## Risks & Reviewer Guidance

- **Masking real dead code (the #1 check)**: Reviewer — confirm every detector resolves the alias to the EXACT declaring module (no bare-name/global-annotation/test-only rescue), and that the no-false-negative test genuinely fails if you loosen a rule. Spot-check one detector by temporarily reverting it and confirming the corresponding symbol re-flags.
- **Demote safety (C-004)**: Reviewer — confirm each demoted symbol has no external `from`-import and no `import *` reaching it.
- **No net growth (NFR-003)**: Reviewer — compare `category_a`/`category_b` counts to the base; only the deferred auth trio may add an entry.
- **Security (FR-005)**: Reviewer — confirm a banned flag is actually rejected (not just defined) and the typed error matches the contract.
- **Coupling**: Reviewer — confirm `BANNED_FLAGS` and the other un-blinded symbols are all resolved (live/demoted/deleted/allowlisted) so the gate is green at HEAD.
