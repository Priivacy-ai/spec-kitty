---
work_package_id: WP09
title: Invert the transition-gate hook
dependencies:
  - "WP06"
  - "WP08"
requirement_refs:
- FR-009
- FR-011
- FR-013
- FR-014
planning_base_branch: feat/doctrine-controlled-transition-gates
merge_target_branch: feat/doctrine-controlled-transition-gates
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-controlled-transition-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-controlled-transition-gates unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
- T043
- T044
- T045
- T046
- T047
phase: Phase 4 - Integration
history:
- at: '{{TIMESTAMP}}'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: "python-pedro"
authoritative_surface: src/specify_cli/cli/commands/agent/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/cli/commands/agent/tasks_move_task.py
- src/specify_cli/cli/commands/agent/tasks.py
- docs/development/review-gates.md
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_escape_hatch.py
- tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py
- tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py
- tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py
role: "implementer"
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP09 – Invert the transition-gate hook

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `` (unset — select below)
- **Role**: ``
- **Agent/tool**: ``

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this WP's `task_type` (`implement`) and `authoritative_surface` (`src/specify_cli/cli/commands/agent/`). This is the integrative, highest-coordination WP; a strong Python-implementer profile fits.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``. Use language identifiers in code blocks (` ```python `, ` ```bash `).

---

## Objectives & Success Criteria

Invert the pre-review transition gate from "hardcoded to Spec Kitty's own repo shape" to "resolved from the repo's active doctrine" — the integrative cut that delivers the pre-review-facet closure of #2534. The hook resolves which named handlers the active doctrine binds to the current lane edge (via WP06's `resolve_active_gate_bindings` + WP04's `GATE_REGISTRY`), dispatches each with per-handler fail-open, and aggregates via WP08's `aggregate_verdicts`. **LANDS LAST** — consumes WP06 and WP08.

**Done when:**

- `_mt_run_pre_review_gate` is inverted into `_mt_run_transition_gates`, with `_mt_run_pre_review_gate` kept as a **thin alias** delegating to it (preserves the frozen compat surface + monkeypatch bindings).
- Per-handler fail-open mirrors the incumbent three-catch; exactly **two** hard-stops survive (opt-in `NEW_FAILURES` block; terminal `TIMED_OUT`/`CANCELLED`).
- The dead consumer-repo **reader** + `_PRE_REVIEW_CONSUMER_REPO_REASON` are removed from `tasks_move_task.py` (activation is the sole impl selector); the now-dead `GateAuthoritiesUnavailable.is_consumer_repo` field (in WP03's `pre_review_gate.py`) is retired in a fast-follow (#TBD, cross-file).
- The third config key `review.pre_review_test_command` is aliased to the port's single authority with a one-time deprecation warning (no silent break).
- The compat surface (`tasks.py` barrel + `test_tasks_compat_surface.py` tuple) and the hook-binding tests are migrated together.
- The #2534 closure test — **including the erroneous-activation case** — is green, and parity-through-hook is green against WP08's base-captured fixtures.
- `docs/development/review-gates.md` reflects the new behaviour/precedence/config-key and states #2741 is **inherited, not fixed**.

**Tracker**: #2598, FR-009, FR-013 (+ FR-011 config-key, FR-014 consumption).

## Context & Constraints

- **Mission**: `doctrine-controlled-transition-gates-01KY51Z7` · **Branch**: `feat/doctrine-controlled-transition-gates`.
- **Spec**: [spec.md](../spec.md) FR-009 (`:111`), FR-013 (`:115`), FR-014 (`:116`), User Story 1 (`:22-35`, incl. AS4 erroneous activation), User Story 2 (`:39-52`, parity through the hook), Edge Cases (`:87-95`). **Plan**: [plan.md](../plan.md) IC-05 (`:134-147`), "Existing tests to migrate" table (`:157-168`), squad findings P-F1 (compat double-break), C-C1 (`is_consumer_repo` demolition), P-F5/F6 (config-key alias + docs). **Data-model**: [data-model.md](../data-model.md) §5 (join), §7 (aggregation), §8 (`TransitionGateContext`). **Contract**: [contracts/transition-gate-hook.md](../contracts/transition-gate-hook.md) (the full behavioural pipeline + CLI-observable invariants).
- **The incumbent hook** `_mt_run_pre_review_gate(st)` lives at `tasks_move_task.py:1160-1299`. It: skips unless `st.target_lane == Lane.FOR_REVIEW` (`:1176`); resolves workspace/changed-files/baseline (`:1197-1213`); runs the verdict (`:1234`); catches `KeyboardInterrupt → CANCELLED` (`:1241`) and any `Exception → NO_COVERAGE` (`:1248`); records metadata (`:1262`); hard-stops on terminal interruption (`:1270-1296`, `transition_applied=False` then `Exit(1)`); then blocks (`:1298`). It is invoked from `_do_move_task` (the same slot the inverted hook keeps).
- **The consumer-repo `GateAuthoritiesUnavailable` catch** at `:1056-1069` reads `exc.is_consumer_repo` and picks `_PRE_REVIEW_CONSUMER_REPO_REASON` (`:797-800`). Under the inversion, the generic per-handler fail-open warn supersedes this whole branch — it is dead once activation is the sole selector (see T042).
- **The third config key**: `_PRE_REVIEW_CONFIG_KEY_TEST_COMMAND = "pre_review_test_command"` (`:785`). **The name lies about its axis** — it actually feeds `_mt_pre_review_scope_override` *scope targets*, NOT a command (squad C-C3). Alias it to the port's single authority (WP02/WP03) with a one-time deprecation warning; keep existing configs working (T043).
- **`GateOutcome`** six members: `pre_review_gate.py:742-750`. Do NOT redefine.
- **Compat surface (guaranteed-red without update, squad P-F1)**: `tasks.py:432-455` re-export barrel (`_mt_run_pre_review_gate as _mt_run_pre_review_gate` at `:455`) and `test_tasks_compat_surface.py:217` frozen `_TASKS_MOVE_TASK` tuple (entry `"_mt_run_pre_review_gate"`). Any new/relocated `_mt_*` symbol migrates its barrel line + tuple entry **together** (T044).
- **Hook stays a THIN orchestrator** — the join (`resolve_active_gate_bindings`, WP06) and the aggregation (`aggregate_verdicts`, WP08) are the pure fns; the hook only does I/O + dispatch, keeping each function ≤15 complexity (NFR-006).
- **#2741 (P1) is INHERITED, not fixed** — the gate diffs the working tree, not the WP commit range (`_mt_pre_review_changed_files` → `merge_base_changed_files`, `tasks_move_task.py:927`). Behaviour-preserving parity *preserves* this; do NOT "fix" it here and do NOT flag it as a regression (T047).
- **Deps**: WP06 (`resolve_active_gate_bindings` + loader) and WP08 (`aggregate_verdicts` + base-captured parity fixtures). **Quality**: `mypy --strict` + `ruff` zero issues, complexity ≤15/function, ≥90% new-code coverage. `PYTHONPATH=$(pwd)/src`. No `# noqa` / `# type: ignore`.

## Branch Strategy

- **Strategy**: feature-branch (PR-bound, C-004).
- **Planning base branch**: `feat/doctrine-controlled-transition-gates`.
- **Merge target branch**: `feat/doctrine-controlled-transition-gates`.

> Populated by `spec-kitty agent mission tasks`. Do NOT change manually unless the branch topology changed.

## Subtasks & Detailed Guidance

### Subtask T040 – Invert `_mt_run_pre_review_gate` → `_mt_run_transition_gates`; keep a thin alias

- **Purpose**: Replace the hardcoded `evaluate_pre_review_gate` call with doctrine-resolved dispatch, while preserving the compat surface and shrinking blast radius (FR-009, FR-014 consumption; `contracts/transition-gate-hook.md:12-33`).
- **Steps**:
  1. Author `_mt_run_transition_gates(st)` in `tasks_move_task.py`, keeping the same `_do_move_task` slot, the `st.target_lane == Lane.FOR_REVIEW` guard (`:1176`), the skip-reason escape hatch (`:1184-1192`), and the changed-files/baseline SSOT resolution (`:1197-1213`, `:927`) unchanged.
  2. Build the `TransitionGateContext` (data-model §8: `changed_files`, resolved `ScopeSource`, `baseline`, `repo_root`, `force`, `from_lane`/`to_lane`).
  3. Resolve active bindings via WP06's `resolve_active_gate_bindings(activated_msc_urns, bindings, edge_key, owning_contract_urn)` (the pure join) + the `load_gate_bindings(repo_root, mission, action)` loader; dispatch each active binding's handler via WP04's canonical form `get_gate_handler(b.handler).run(ctx)` in the stable dispatch order.
  4. Aggregate the collected verdicts via WP08's `aggregate_verdicts(verdicts, block_enabled=..., force=st.force)`; translate the pure aggregate result into the metadata payload (`_mt_pre_review_gate_metadata`, `:1071`), console emission, and the two hard-stops (T041).
  5. **Keep `_mt_run_pre_review_gate` as a THIN FORWARDER** — `def _mt_run_pre_review_gate(st): return _mt_run_transition_gates(st)` — and **KEEP the `_do_move_task` call site (`tasks_move_task.py:1911`) calling `_mt_run_pre_review_gate`**. Do NOT repoint `:1911` to `_mt_run_transition_gates`: the observability monkeypatch at `test_tasks_move_task_pre_review_gate_observability.py:552` patches `_mt_run_pre_review_gate`, and repointing the call site would no-op that patch (and break the frozen compat surface). The thin alias only works if the call site stays on it. Do NOT bare-rename (squad P-F1).
- **Files**: `src/specify_cli/cli/commands/agent/tasks_move_task.py`.
- **Parallel?**: No — the spine of this WP.
- **Notes**: The hook must remain **purely additive after the established guard sequence, before emit** (incumbent docstring `:1163-1169`); the FSM adjacency and `_GUARDS` are untouched (`contracts/transition-gate-hook.md:92-98`).

### Subtask T041 – Per-handler fail-open + exactly two hard-stops

- **Purpose**: Preserve FR-013 / C-003 at the new dispatch loop — every handler *execution* error degrades to one visible unverified warning; only the two legitimate non-completions survive.
- **Steps**:
  1. Wrap each handler dispatch in the three-catch mirror of the incumbent: `KeyboardInterrupt → CANCELLED` verdict (mirrors `:1241-1247`); `GateAuthoritiesUnavailable → NO_COVERAGE` unverified warn (mirrors `:1056`); any other `Exception → NO_COVERAGE` unverified warn (mirrors `:1248-1249`). Each fault yields exactly ONE warning and never crosses into another handler.
  2. Enumerate exactly **two hard-stops** after aggregation: (a) terminal interruption (`TIMED_OUT`/`CANCELLED`) → `transition_applied=False` then `Exit(1)`, checked FIRST (`:1270-1296`); (b) opt-in block iff `block_enabled AND any NEW_FAILURES AND not force` → `Exit(1)` (`:1258-1261`, `:1298`). No third hard-stop; no converting a hard-stop into a warn.
  3. Keep `_mt_pre_review_block_enabled` (`:1258`) as the block toggle and `st.force` as the bypass; the `force_bypassed`/`blocked` metadata (`:1260-1261`) is preserved.
- **Files**: `tasks_move_task.py`.
- **Parallel?**: No.
- **Notes**: The aggregation precedence (terminal > block > warn) lives in WP08's `aggregate_verdicts`; here the hook only *acts* on the aggregate result (emits console + performs the `Exit`). Do not re-implement precedence in the hook.

### Subtask T042 – Remove the `is_consumer_repo` reader + `_PRE_REVIEW_CONSUMER_REPO_REASON` (this file only)

- **Purpose**: With activation as the sole impl selector, the consumer-repo branch in `tasks_move_task.py` is dead — removing it prevents vestigial debt (squad C-C1; FR-009). Scope is **this WP's owned file only**.
- **Steps**:
  1. Delete `_PRE_REVIEW_CONSUMER_REPO_REASON` (`tasks_move_task.py:797-800`).
  2. Delete the consumer-repo message branch that **reads** `exc.is_consumer_repo` (`:1056-1069`) — the generic per-handler fail-open warn (T041) supersedes it.
  3. **Do NOT delete the `GateAuthoritiesUnavailable.is_consumer_repo` FIELD** — it lives in `pre_review_gate.py` (WP03's owned file), and its only reader (this branch) outlives its file's owner, so this WP cannot single-own that cross-file removal. Once this reader is gone the field is dead, but retiring it is a **fast-follow (#TBD, cross-file cleanup)**, not this WP. Do not reach into WP03's file to delete it here.
- **Files**: `tasks_move_task.py`.
- **Parallel?**: No.
- **Notes**: The "zero vestigial `is_consumer_repo`" success criterion is **downgraded**: assert a **grep-zero for `_PRE_REVIEW_CONSUMER_REPO_REASON` in `tasks_move_task.py` only**, plus zero *reads* of `exc.is_consumer_repo` from this file. The dead `is_consumer_repo` field on `GateAuthoritiesUnavailable` (in `pre_review_gate.py`) is retired in the fast-follow.

### Subtask T043 – Alias `review.pre_review_test_command` with a one-time deprecation warning

- **Purpose**: Reconcile the third resolution site into the port's single authority (FR-011) without silently breaking a consumer that has the key set (squad P-F5).
- **Steps**:
  1. `_PRE_REVIEW_CONFIG_KEY_TEST_COMMAND` (`:785`) actually feeds `_mt_pre_review_scope_override` *scope targets*, NOT a command — the name lies about its axis (squad C-C3). Alias the key so a config that still sets it keeps working, routed to the ScopeSource's single authority.
  2. Emit a **one-time** deprecation warning (not on every transition — guard with a module-level flag or the standard deprecation surface) naming the replacement key/port.
  3. Do NOT delete the key handling outright — that would be a silent break for existing configs.
- **Files**: `tasks_move_task.py`.
- **Parallel?**: No.
- **Notes**: Adjacent issue #2803 (`review.test_command` resolution) is out of scope — do not re-open it. Keep the alias narrow to the pre-review facet.

### Subtask T044 – Update the compat surface (barrel + tuple) together

- **Purpose**: The frozen compat guard double-breaks on any `_mt_*` symbol change (squad P-F1) — the barrel and tuple must move in lockstep.
- **Steps**:
  1. Add `_mt_run_transition_gates as _mt_run_transition_gates` to the `tasks.py` re-export barrel (`tasks.py:432-455`), keeping the existing `_mt_run_pre_review_gate` alias line (`:455`) since the thin alias is still a real symbol.
  2. Add `"_mt_run_transition_gates"` to the `_TASKS_MOVE_TASK` tuple in `test_tasks_compat_surface.py:217`, keeping the `"_mt_run_pre_review_gate"` entry.
  3. Run the compat guard and confirm the superset invariant holds (barrel exports ⊇ tuple).
- **Files**: `src/specify_cli/cli/commands/agent/tasks.py`, `tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py`.
- **Parallel?**: No — the guard is red until both land.
- **Notes**: This is a "guaranteed-red without update" surface (plan `:143`); land barrel + tuple in the same change.

### Subtask T045 – Migrate the hook-binding tests

- **Purpose**: The incumbent test corpus binds `_mt_run_pre_review_gate` by name (monkeypatch); the thin alias preserves most bindings, but the migration-red must be distinguishable from a regression-red (plan "Existing tests to migrate" `:157-168`).
- **Steps**:
  1. `test_tasks_move_task_pre_review_gate_escape_hatch.py` (11 sites) — these **call `_mt_run_pre_review_gate(st)` DIRECTLY** (not just monkeypatch-and-survive). Post-alias, a direct call now forwards into the **full doctrine-resolved dispatch** (`_mt_run_transition_gates` → join → `GATE_REGISTRY`), so each needs an **activated `software-dev` review-binding fixture** (or the `spec-kitty-pre-review` handler still resolving/running for `software-dev`) to reach the same behaviour — **budget for this**, it is heavier than "the alias keeps the binding". Confirm the skip/escape-hatch path (`:1184-1192`) is unchanged.
  2. `test_tasks_move_task_pre_review_gate_observability.py` (binds `_mt_run_pre_review_gate`, plan `:167` cites `:552`) — migrate to assert the observability payload of the inverted hook (same metadata shape).
  3. `test_tasks_cli_contract_coord.py` (binds `_mt_run_pre_review_gate`, plan `:167` cites `:798`) — migrate the CLI-contract coord binding.
  4. Keep each migration a *migration* (rewire to the alias / new behaviour), NOT a delete-to-green; annotate migration-red in the Activity Log.
- **Files**: `tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_escape_hatch.py`, `..._observability.py`, `test_tasks_cli_contract_coord.py`.
- **Parallel?**: No.
- **Notes**: The stale consumer-repo tests in `tests/review/test_pre_review_gate_engine.py:100-127` are WP03/WP02's owned migration (not this WP's files) — do not edit them here; coordinate the erroneous-activation closure (T046) with that retirement.

### Subtask T046 – #2534 closure incl. the erroneous-activation case; parity-through-hook green

- **Purpose**: Prove the pre-review facet of #2534 is closed **by construction** — the internal `_gate_coverage` module is never imported even when a consumer *erroneously* activates the Spec-Kitty handler (spec US1 AS4 `:35`; `contracts/transition-gate-hook.md:81-85`).
- **Steps**:
  1. Simulate a consumer checkout with no `tests/architectural/_gate_coverage.py` and a non-pytest layout; move a WP to `for_review`.
  2. **Erroneous-activation arm**: force-activate the Spec-Kitty pre-review handler in the consumer's config; assert the internal `_gate_coverage` module is **never imported** (assert on `sys.modules` / an import spy), and the handler's own `GateAuthoritiesUnavailable` degrades to a `NO_COVERAGE` warn — the transition completes.
  3. **No-binding arm**: a consumer whose active doctrine binds no gate to the edge → no gate runs, no internal-path reference (US1 AS3).
  4. **Parity-through-hook**: wire WP08's `test_transition_gate_parity.py` harness through `_mt_run_transition_gates` and assert the base-captured fixtures (all six outcomes + both hard-stops) reproduce identically (NFR-001, SC-002). This is the surface WP08 authored red; it goes green here.
- **Files**: extend `test_tasks_move_task_pre_review_gate_observability.py` / the escape-hatch or coord test (owned here), and drive WP08's parity harness. Keep new assertions within this WP's owned test files.
- **Parallel?**: No.
- **Notes**: The closure must be **structural**, not configuration-dependent — the erroneous-activation arm is the load-bearing proof (squad: closure "does not depend on activation being correctly configured").

### Subtask T047 – Update `docs/development/review-gates.md`

- **Purpose**: Reflect the inverted behaviour/precedence/config-key in the human docs, and record #2741 as inherited (squad P-F6; FR-011).
- **Steps**:
  1. Update the "Pre-review regression gate" section (`docs/development/review-gates.md:138-161`) to describe the doctrine-resolved dispatch (active bindings → handlers → aggregation), the two hard-stops, and per-handler fail-open.
  2. Update the config-key prose: `review.pre_review_test_command` (`:152`) is deprecated/aliased (T043); the precedence chain (`:158-161`) reflects the ScopeSource single authority.
  3. Add an explicit note that **#2741 (working-tree-diff P1) is inherited, NOT fixed** by this mission — parity preserves it; it is tracked separately (plan `:173`). Do not imply the whole class of repo-shape coupling is closed (spec Scope honesty `:16`; only the `for_review` pre-review facet is inverted, C-006).
  4. Markdownlint clean. (Agent-copy propagation is N/A — plan `:144` verified no gate prose under `src/doctrine/missions/*/command-templates/`.)
- **Files**: `docs/development/review-gates.md`.
- **Parallel?**: `[P]` — docs, independent of the code subtasks (but land in the same PR).
- **Notes**: Keep #2741 framed as preserved-by-design so a later reader does not mistake it for a fix or flag it as a regression.

## Test Strategy (tests required)

- **Closure**: the #2534 erroneous-activation + no-binding arms (T046) — assert on import spying, not just outcome.
- **Parity-through-hook**: WP08's `test_transition_gate_parity.py` driven through `_mt_run_transition_gates` against base `e4ef6e850` fixtures (NFR-001).
- **Fail-open**: per-handler degrade + two-hard-stops (T041) — a faulting handler → one warning, transition completes; terminal + block hard-stops preserved.
- **Compat guard**: `test_tasks_compat_surface.py` green after barrel + tuple update (T044).
- **Migrated bindings**: escape-hatch / observability / cli-contract-coord (T045).
- **Commands**:
  ```bash
  PYTHONPATH=$(pwd)/src pytest tests/specify_cli/cli/commands/agent/test_tasks_compat_surface.py -q
  PYTHONPATH=$(pwd)/src pytest tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_escape_hatch.py -q
  PYTHONPATH=$(pwd)/src pytest tests/specify_cli/cli/commands/agent/test_tasks_move_task_pre_review_gate_observability.py -q
  PYTHONPATH=$(pwd)/src pytest tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py -q
  PYTHONPATH=$(pwd)/src pytest tests/review/test_transition_gate_parity.py -q
  mypy --strict src/specify_cli/cli/commands/agent/tasks_move_task.py
  ruff check src/specify_cli/cli/commands/agent/
  ```
- **Red-first**: the migrated bindings + compat guard go red on the rename until the alias + tuple land; the parity harness (WP08) is red until the inverted hook reproduces the base tuples. Record each red→green transition in the Activity Log so migration-red is distinguishable from regression-red.

## Risks & Mitigations

- **Configuration-dependent closure** — closing #2534 only when activation is correct. *Mitigation (GUARD)*: the erroneous-activation arm (T046) proves the internal import is structurally unreachable regardless of activation.
- **Compat double-break** — moving a `_mt_*` symbol without both barrel + tuple. *Mitigation*: T044 lands them together; the thin alias keeps `_mt_run_pre_review_gate` a real symbol.
- **Third hard-stop / hard-stop→warn drift** — introducing a new non-completion or softening a terminal. *Mitigation (GUARD)*: exactly two hard-stops enumerated (T041); C-003.
- **Cross-suppression at dispatch** — a faulting handler removing another's block. *Mitigation*: WP08 aggregation reads every verdict; T041's dispatch never short-circuits on a fault.
- **Circular parity oracle** — re-deriving expected values from the new hook. *Mitigation*: consume WP08's base-captured (`e4ef6e850`) fixtures; never regenerate.
- **#2741 mis-framing** — "fixing" the working-tree-diff bug or flagging it as a regression. *Mitigation (GUARD)*: T047 states it is inherited; parity preserves it by design.
- **Complexity breach** — the hook rewrite ballooning past 15. *Mitigation*: hook is a thin orchestrator; the join (WP06) and aggregation (WP08) are the pure fns it merely calls.
- **Silent config break** — deleting the third key. *Mitigation*: T043 aliases with a one-time deprecation warning; existing configs keep working.

## Review Guidance

- Confirm `_mt_run_pre_review_gate` survives as a thin alias delegating to `_mt_run_transition_gates` (grep both symbols; both exported in the barrel + tuple).
- Confirm the erroneous-activation arm asserts the internal `_gate_coverage` module is never imported (import spy / `sys.modules`), not merely that the outcome matches.
- Confirm exactly two hard-stops remain and per-handler fail-open yields one warning without cross-suppression.
- Confirm the parity harness runs through `_mt_run_transition_gates` (metadata + block/exit + console) against base `e4ef6e850` fixtures — not the engine in isolation.
- Confirm `_PRE_REVIEW_CONSUMER_REPO_REASON` is grep-zero in `tasks_move_task.py` and nothing in this file **reads** `exc.is_consumer_repo` (the field itself stays on `GateAuthoritiesUnavailable` in WP03's `pre_review_gate.py`, retired in a fast-follow #TBD).
- Confirm `review-gates.md` states #2741 is inherited-not-fixed and does not overclaim the closure beyond the `for_review` pre-review facet.
- Confirm no edit to WP02/WP03-owned `pre_review_gate.py` or the `tests/review/test_pre_review_gate_*` corpus beyond this WP's owned files.

## Activity Log

> **CRITICAL**: entries in chronological order (oldest first, newest last). Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>` (UTC, `date -u "+%Y-%m-%dT%H:%M:%SZ"`).

- {{TIMESTAMP}} – system – Prompt created.
