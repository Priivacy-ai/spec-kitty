---
work_package_id: WP05
title: RuntimeEventEmitter ADR Execution (rewire-ready consolidation + flush-target fix)
dependencies:
- WP03
requirement_refs:
- C-003
- C-006
- C-007
- FR-012
planning_base_branch: missions/coreloop-proto-missions
merge_target_branch: missions/coreloop-proto-missions
branch_strategy: Planning artifacts for this mission were generated on missions/coreloop-proto-missions. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into missions/coreloop-proto-missions unless the human explicitly redirects the landing branch.
subtasks:
- T018
- T019
- T020
- T021
- T022
- T023
phase: Wave 2 - ADR execution (after WP03; after Mission A merged)
history:
- at: '2026-09-06T16:20:00Z'
  actor: system
  action: 'Prompt generated via /spec-kitty.tasks (WP05 minted when PR #3898 merged with the ADR Accepted — FR-012 gate met; decision OD7 superseded)'
agent_profile: python-pedro
authoritative_surface: src/runtime/next/_internal_runtime/
create_intent:
- tests/runtime/test_emitter_seam_consolidation.py
- tests/runtime/test_decision_flush_target.py
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/event_emitter.py
- src/runtime/next/_internal_runtime/events.py
- src/runtime/next/runtime_bridge.py
- src/runtime/next/runtime_bridge_engine.py
- src/runtime/next/runtime_bridge_retrospective.py
- tests/runtime/test_bridge_parity.py
- tests/runtime/test_emitter_seam_consolidation.py
- tests/runtime/test_decision_flush_target.py
- tests/specify_cli/events/test_decision_log_coord.py
- tests/status/test_producer_conformance.py
- tests/contract/test_identity_contract_matrix.py
role: implementer
agent: claude
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – RuntimeEventEmitter ADR Execution

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log. Address every item before completion and log what changed.

## Review Feedback

*[Populated by the reviewer via the status event log.]*

---

## Objectives & Success Criteria

FR-012 (conditional) is now **executable**: PR #3898 merged into `main` on 2026-09-06 with `docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md` at `status: Accepted`, chosen option **"Rewire-ready consolidation"** (keep the seam; merge the duplicate concrete class into the `_internal_runtime` Protocol/`NullEmitter`; fix the buffer flush-target bug; correct the docstring; do NOT wire a live producer). The ADR's own "Confirmation" section is this WP's definition of done:

1. Exactly one class named `RuntimeEventEmitter` exists under `src/runtime/next/` — the Protocol in `_internal_runtime/events.py:67`. The concrete `src/runtime/next/event_emitter.py::RuntimeEventEmitter` (`:23`, 88 LOC) is deleted (or, only as a transitional step inside this WP, renamed `NullRuntimeEventEmitter`; the target state has one name).
2. The bridge constructs the seam via a **factory** returning `NullEmitter` by default (and under `SPEC_KITTY_SYNC_MINIMAL_IMPORT`), mirroring the env-gated registration pattern at `status/adapters.py:364-365`; the constructor/`seed_from_snapshot` capability stays intact: promote the constructor onto the seam as **`for_mission`** (Terminology Canon; keep `for_feature` only as a transitional alias with a removal note if the two construction sites cannot be renamed in the same change) and `seed_from_snapshot` as a no-op/pass-through on `NullEmitter`. The bridge (`runtime_bridge.py:195,:1552,:2739,:1614,:2745`) and engine (`runtime_bridge_engine.py:80` TYPE_CHECKING import + 16 annotation sites) depend on the Protocol and the factory, never on a concrete class import.
3. **Flush-target bug fixed, not frozen**: `buffer.flush(ctx.sync_emitter)` at `runtime_bridge.py:2187` must target `ctx.emitter_for_engine` (the `DecisionGitLog` wrap built at `:1560-1565`); the composition-path bypass (`:1976` → `runtime_bridge_engine.py:226`) is the same defect class and is fixed too. Each fix lands with a **red-first** test whose fixture is a strict-policy `decision_required` advance proving the buffered `DecisionInputRequested` is appended to `decisions.events.jsonl` after the flush; plus a separate assertion that a refused terminal gate discards the buffer without a git write.
4. `_BufferingRuntimeEmitter` (`runtime_bridge_retrospective.py:69`) stays (C-006 — rollback machinery); only its flush **target** changes at the call site.
5. Existing bridge-parity (`tests/runtime/test_bridge_parity.py:1131-1152` `test_side_effect_sinks_are_actually_reached`) and producer-conformance (`tests/status/test_producer_conformance.py`, `tests/contract/test_identity_contract_matrix.py`) tests stay green — update their comments to point at the consolidated seam; update the one live importer of the concrete class (`tests/specify_cli/events/test_decision_log_coord.py:17`).
6. `sync_emitter` vocabulary: the ADR does not mandate the rename; the spec (US4-1) asks for ONE pass over the 29 sites if it happens. Decide: rename the parameter to `emitter` in the same pass as the retyping (preferred, one pass) or leave it and record why. Never two passes.
7. NOT in scope: wiring a live zeitgeist producer (E3); any `status/adapters.py` change.

## Context & Constraints

- ADR: `docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md` (read it in full — Decision Outcome (a)–(e), Consequences, the "Mission B scope boundary" and "Confirmation" sections are binding). Spec US4, FR-011, FR-012, C-003 (now satisfied), C-006, C-007. Contract `contracts/residue-and-emitter-shrunk.md` §3–§4 (the FR-011 record `research/emitter-adr-inputs.md` is written by WP03 — read it if WP03 landed first). Data model §5. Research §1.
- **Mission A is merged into the branch before this WP is claimed** (C-001): Mission A's WP05 changed `runtime_bridge_io.py` and `_internal_runtime/engine.py`, and its WP04 touched nothing here; re-verify every line anchor above at your HEAD before editing.
- **C-007 runtime ledger**: deleting `event_emitter.py` may remove a ledgered edge; run `tests/architectural/test_layer_rules.py::test_runtime_ledger_has_no_stale_entries` and the widened doctrine-scan baseline (pins `runtime_bridge_io.py`/`runtime_bridge_composition.py` lazy reaches); edit the ledger in the same commit if it reds. `test_layer_rules.py` is WP03's file — a one-line ledger edit is an out-of-map edit with rationale.
- Sonar/CLAUDE.md: complexity ≤15; no `# noqa`/`# type: ignore`; tests for every new helper; terminology "Mission"; `ruff format` new files (live gate `tests/architectural/test_ruff_format_enforcement.py`).
- No `kitty-specs/` files on the lane branch; design note → session scratchpad; Activity Log via `spec-kitty agent tasks add-history WP05 --mission dead-port-disposition-01M1TZVN`.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on missions/coreloop-proto-missions; completed changes must merge back into missions/coreloop-proto-missions.
- **Planning base branch**: missions/coreloop-proto-missions
- **Merge target branch**: missions/coreloop-proto-missions

Execution worktrees are allocated per computed lane from `lanes.json`; enter yours with `spec-kitty implement WP05 --mission dead-port-disposition-01M1TZVN` (based on WP03's lane).

## Subtasks & Detailed Guidance

### Subtask T018 – Red-first: flush-target bug (both paths)

- **Purpose**: ADR (c) — the bug must be adjudicated under test, never frozen.
- **Steps**: `tests/runtime/test_decision_flush_target.py` (new). Fixture: a mission under a **strict retrospective gate policy** whose next advance is `decision_required` (read `runtime_bridge.py:2124-2190` for how the buffer replaces the engine emitter at `:2149-2150` and flushes at `:2187`; read `runtime_bridge_retrospective.py:69-149` for one-shot semantics). Test 1: after the advance, `decisions.events.jsonl` (the `DecisionGitLog` sink) contains the `DecisionInputRequested` row — RED on the base (the flush goes to the no-op `ctx.sync_emitter`). Test 2: the composition dispatch path (`runtime_bridge.py:1976` → `runtime_bridge_engine.py:226`) — same assertion, RED. Test 3: a refused terminal gate discards the buffer and writes nothing to the git log (must be GREEN before and after). Paste the RED output into the Activity Log; `xfail(strict=True)` until T020.
- **Files**: `tests/runtime/test_decision_flush_target.py`.
- **Parallel?**: No.

### Subtask T019 – Promote the seam surface; factory; delete the duplicate

- **Purpose**: ADR (a), (b), (d).
- **Steps**: in `_internal_runtime/events.py`: add `for_mission(...)` (a `NullEmitter` classmethod or module-level factory `runtime_event_emitter_for_mission(...)`) returning `NullEmitter` by default and under `SPEC_KITTY_SYNC_MINIMAL_IMPORT`, with the E3 registration hook shaped like `status/adapters.py:364-365` (a module-level registry + `register_runtime_event_emitter_factory(...)`; no producer registered here); add `seed_from_snapshot(self, snapshot)` as a no-op on `NullEmitter` and to the Protocol. Rewire `runtime_bridge.py:1552` and `:2739` to the factory; `:1614`/`:2745` keep calling `seed_from_snapshot`. Delete `src/runtime/next/event_emitter.py`; remove its import at `runtime_bridge.py:195`; retype `runtime_bridge_engine.py:80` and the 16 annotation sites against the Protocol. `grep -rn "event_emitter" src tests docs` → only historical mentions in docs/ADRs remain (reword test comments per item 5). Keep `for_feature` as a deprecated alias ONLY if a same-change rename is impossible; document the removal note.
- **Files**: `_internal_runtime/events.py`, `event_emitter.py` (deleted), `runtime_bridge.py`, `runtime_bridge_engine.py`, `tests/specify_cli/events/test_decision_log_coord.py:17`.
- **Parallel?**: No.

### Subtask T020 – Fix the flush target (both paths); flip T018

- **Purpose**: ADR (c).
- **Steps**: `runtime_bridge.py:2187` `buffer.flush(ctx.sync_emitter)` → `buffer.flush(ctx.emitter_for_engine)`; the composition dispatch at `:1976` passes the `DecisionGitLog`-wrapped emitter (or the engine call at `runtime_bridge_engine.py:226` receives it) — read both to place the fix at the seam, not by patching the engine's signature twice. Confirm rollback semantics are preserved: the gate at `:2178-2181` runs before the flush; the buffer is one-shot. Flip T018's xfails; T018 test 3 still green.
- **Files**: `runtime_bridge.py`, possibly `runtime_bridge_engine.py`.
- **Parallel?**: No.

### Subtask T021 – One pass over `sync_emitter` (decide) + conformance/parity updates

- **Purpose**: US4-1 single-pass rule; item 5.
- **Steps**: decide rename-or-keep for the `sync_emitter` parameter name across the 29 sites (engine ×16, bridge ×13) — if you retyped every site in T019 anyway, renaming to `emitter` in the same diff is the one-pass outcome; record the decision. Update `test_bridge_parity.py:1131-1152` only if the capture shape changed (it asserts the sink is populated by ≥1 fixture — keep it green, do not weaken); update the comments in `tests/status/test_producer_conformance.py:13` and `tests/contract/test_identity_contract_matrix.py:36` to name the consolidated seam.
- **Files**: as listed.
- **Parallel?**: No.

### Subtask T022 – Seam consolidation tests + ledger

- **Purpose**: ADR Confirmation (1), (2), (4); C-007.
- **Steps**: `tests/runtime/test_emitter_seam_consolidation.py` (new): AST/grep assertion that exactly one class named `RuntimeEventEmitter` exists under `src/runtime/next/`; the factory returns `NullEmitter` by default and under `SPEC_KITTY_SYNC_MINIMAL_IMPORT`; a registered fake producer is returned when registered (and the registry is reset by fixture); `NullEmitter.seed_from_snapshot` is a no-op; `for_mission` resolves mission identity like the old `for_feature` did (read the old implementation before deleting it — port its identity resolution, not just its name). Run `tests/architectural/test_layer_rules.py` and the doctrine-scan baseline; fix the ledger in-commit if needed.
- **Files**: new test; possibly `tests/architectural/test_layer_rules.py` (out-of-map, one line).
- **Parallel?**: Yes (alongside T021).

### Subtask T023 – Design note, ADR confirmation record, C-009 cleanup

- **Purpose**: directive 003; ADR "Confirmation".
- **Steps**: write `design-notes/WP05-emitter-adr-execution.md` to the scratchpad: the four Confirmation items with evidence (test nodeids, grep output), the `sync_emitter` rename decision, the `for_feature` alias status, the flush-fix behaviour change called out explicitly (decision events now durably commit on the strict-gated path), LOC delta, and the statement that no live producer is wired. Convert T018's red-first tests to permanent regression pins (rename to behaviour names; drop xfail markers). Confirm `research/emitter-adr-inputs.md` (WP03) is marked "executed by WP05".
- **Files**: scratch note; tests.
- **Parallel?**: No.

## Test Strategy

```bash
.venv/bin/pytest tests/runtime tests/next tests/specify_cli/events tests/status/test_producer_conformance.py tests/contract/test_identity_contract_matrix.py -q -p no:cacheprovider -n 3 --dist loadfile
.venv/bin/pytest tests/runtime/test_decision_flush_target.py tests/runtime/test_emitter_seam_consolidation.py tests/runtime/test_bridge_parity.py -q
.venv/bin/pytest tests/architectural/test_layer_rules.py tests/architectural/test_runtime_charter_doctrine_boundary.py tests/architectural/test_no_dead_symbols.py tests/architectural/test_no_legacy_terminology.py tests/architectural/test_ruff_format_enforcement.py -q
env -u FORCE_COLOR NO_COLOR=1 PWHEADLESS=1 .venv/bin/pytest tests/unit tests/status tests/cli tests/specify_cli/runtime tests/architectural/test_no_retired_subsystems.py -m "(fast or unit) and not slow and not e2e and not integration and not regression and not distribution and not live_adapter and not stress and not windows_ci and not platform_darwin" -n 3 --dist loadfile -p no:cacheprovider -q
CHANGED=$(git diff --name-only --diff-filter=AMR $(git merge-base HEAD missions/coreloop-proto-missions) | grep '\.py$'); echo "$CHANGED" | xargs .venv/bin/ruff check; echo "$CHANGED" | xargs .venv/bin/ruff check --select C901; echo "$CHANGED" | xargs .venv/bin/ruff format --check --force-exclude
.venv/bin/mypy src/runtime/next/_internal_runtime/events.py src/runtime/next/runtime_bridge.py src/runtime/next/runtime_bridge_engine.py src/runtime/next/runtime_bridge_retrospective.py
```
Baseline-red gotcha: `runtime/next/*` carries ~21 pre-existing mypy errors (issue #3913); do not fix them; report only new ones.

## Risks & Mitigations

- Behaviour change on the strict-gated path (decision events now committed) → called out in the design note and the PR; pinned by T018.
- Ledger red on deleting `event_emitter.py` → run `test_layer_rules.py` after T019; edit in-commit.
- `for_feature` callers outside `src/` (tests, docs) → grep before deleting; alias only if unavoidable.
- Mission A line drift → re-verify anchors at HEAD first.

## Review Guidance

- ADR Confirmation (1)–(4) each evidenced; T018 RED proof in the Activity Log; flush fix at the seam for BOTH paths; rollback test green; one-pass `sync_emitter` decision recorded; no live producer; ledger green; parity/conformance tests untouched or comment-only.

## Activity Log

> **CRITICAL**: chronological order, oldest first. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`.

- 2026-09-06T16:20:00Z – system – Prompt created (minted on ADR acceptance).
