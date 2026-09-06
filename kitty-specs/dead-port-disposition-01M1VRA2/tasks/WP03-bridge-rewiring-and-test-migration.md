---
work_package_id: WP03
title: Bridge rewiring and test-site migration
dependencies:
- WP01
- WP02
requirement_refs:
- FR-002
- FR-003
- NFR-002
- NFR-006
- NFR-007
planning_base_branch: feat/dead-port-disposition
merge_target_branch: feat/dead-port-disposition
branch_strategy: Planning artifacts for this mission were generated on feat/dead-port-disposition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dead-port-disposition unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dead-port-disposition-01M1VRA2
base_commit: b913f78cc66016e3ed2e7a9beea406540875f778
created_at: '2026-09-06T19:32:19.948010+00:00'
subtasks:
- T014
- T015
- T016
- T017
- T018
- T019
- T020
phase: Phase 3 - Consolidation
history:
- at: '2026-09-06T16:48:26Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/runtime/next/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/runtime_bridge_engine.py
- tests/runtime/_bridge_oracle.py
- tests/runtime/test_bridge_decide_next.py
- tests/next/test_runtime_bridge_blocked_paths.py
- tests/next/test_runtime_bridge_unit.py
- tests/specify_cli/next/test_runtime_bridge_composition.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP03 – Bridge rewiring and test-site migration

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Objectives & Success Criteria

Bind the bridge to the factory from WP01 and migrate every test that patched the concrete class, so the suite is green with the bridge no longer importing `runtime.next.event_emitter`. The concrete module itself is deleted in WP04, not here.

Done means:

- `grep -n "event_emitter" src/runtime/next/runtime_bridge.py src/runtime/next/runtime_bridge_engine.py` → no hits.
- `runtime_bridge.py` constructs the seam only via `runtime_emitter_for_mission(...)` at both sites (`:1552`, `:2739`).
- All fifteen test patch sites use `monkeypatch.setattr(rb, "runtime_emitter_for_mission", ...)` (or `patch.object(rb, "runtime_emitter_for_mission")`), and the oracle spy wraps the factory.
- `pytest tests/runtime/ tests/next/ tests/specify_cli/next/ tests/specify_cli/events/` green (NFR-002).
- Zero `feature*` identifiers in your added lines; the pre-existing `feature_dir` keyword may be passed through (NFR-006).

### Declared out-of-map edit (read this)

`src/runtime/next/runtime_bridge.py` is owned by WP02 (this WP depends on it, so the two never run concurrently). This WP makes exactly **three** edits to that file — the import at `:195` and the two construction sites at `:1552` and `:2739` — and nothing else. Rationale: the factory binding is inseparable from the test-site migration (the tests patch the name the bridge calls); putting the three lines in WP02 instead would break the fifteen patch sites until this WP lands, and putting the migrations in WP02 would balloon it past ten subtasks. Record the three-line edit with this rationale in your Activity Log. Do not touch `:1976` or `:2187` (WP02's fixes) or any other bridge line.

## Context & Constraints

- ADR §Decision Outcome (a): "The bridge depends on the Protocol and a factory, never on a concrete class import."
- Plan §Design "Bridge rewiring (Concern B)" and "Consolidation tests + mechanical rewrites (Concern E)".
- Contract: `contracts/emitter-seam.md` §Test substitution contract.
- WP01 delivered: `runtime_emitter_for_mission`, `register_runtime_emitter_factory`, `reset_runtime_emitter_factory`, `NullEmitter.for_mission`, `NullEmitter.seed_from_snapshot` in `src/runtime/next/_internal_runtime/events.py`. Confirm they exist before starting.
- WP02 delivered: fixes at `:1976` and `:2187`; `DecisionGitLog.seed_from_snapshot`. Confirm before starting.
- Sites to migrate (verbatim shapes below), verified at `main` `3a4f92b41`:

  | File | Lines | Current shape |
  |---|---|---|
  | `tests/runtime/_bridge_oracle.py` | 471-481 | `real_for_feature = bridge_module.RuntimeEventEmitter.for_feature` … `monkeypatch.setattr(bridge_module.RuntimeEventEmitter, "for_feature", staticmethod(_for_feature_spy))` |
  | `tests/runtime/test_bridge_decide_next.py` | 242, 282, 328, 369, 416 | `monkeypatch.setattr(rb, "RuntimeEventEmitter", _FakeClass)` where `_FakeClass.for_feature(**kw)` returns/raises |
  | `tests/next/test_runtime_bridge_blocked_paths.py` | 205, 260, 311, 362 | `patch.object(rb, "RuntimeEventEmitter") as sync_cls` inside a `with (...)` tuple |
  | `tests/next/test_runtime_bridge_unit.py` | 245, 610, 858, 2159 | `monkeypatch.setattr(runtime_bridge.RuntimeEventEmitter, "for_feature", staticmethod(lambda **_: Fake()))` |
  | `tests/specify_cli/next/test_runtime_bridge_composition.py` | 63 | same shape as unit |

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/dead-port-disposition; completed changes must merge back into feat/dead-port-disposition.
- **Planning base branch**: feat/dead-port-disposition
- **Merge target branch**: feat/dead-port-disposition

> Execution worktrees are allocated per computed lane from `lanes.json`; run `spec-kitty agent action implement WP03 --agent <name>` — the resolver bases this WP on the lane that already contains WP01 and WP02's merged work.

## Subtasks & Detailed Guidance

### Subtask T014 – Bridge import and construction sites (out-of-map, three lines)

- **Purpose**: FR-002. The bridge calls the factory by name.
- **Steps**:
  1. `runtime_bridge.py:195`: replace `from runtime.next.event_emitter import RuntimeEventEmitter` with
     ```python
     from runtime.next._internal_runtime.events import RuntimeEventEmitter, runtime_emitter_for_mission
     ```
     (`RuntimeEventEmitter` stays imported because `:293`, `:1215`, `:1472` annotate with it; it now binds to the Protocol.)
  2. `:1552-1556`: `sync_emitter = RuntimeEventEmitter.for_feature(` → `sync_emitter = runtime_emitter_for_mission(`; keyword args unchanged (`feature_dir=`, `mission_slug=`, `mission_type=`).
  3. `:2739-2743`: same replacement.
  4. `ruff check src/runtime/next/runtime_bridge.py` (import ordering) and `mypy src/runtime/next/runtime_bridge.py` — `_wrap_with_decision_git_log(emitter: RuntimeEventEmitter, ...)` now receives a Protocol-typed value; `NullEmitter` conforms structurally.
- **Files**: `src/runtime/next/runtime_bridge.py` (out-of-map, declared above)
- **Parallel?**: No — everything else depends on it.

### Subtask T015 – Engine adapter `TYPE_CHECKING` import

- **Steps**: `src/runtime/next/runtime_bridge_engine.py:80`: `from runtime.next.event_emitter import RuntimeEventEmitter` → `from runtime.next._internal_runtime.events import RuntimeEventEmitter`. Nothing else in the file changes; the seven `sync_emitter: RuntimeEventEmitter` annotations now name the Protocol. Update the docstring line at `:332` if it says "the same `RuntimeEventEmitter`" in a way that implies the concrete class (optional, one word).
- **Files**: `src/runtime/next/runtime_bridge_engine.py`
- **Parallel?**: Yes (with T016–T019).

### Subtask T016 – Oracle spy

- **Purpose**: `tests/runtime/_bridge_oracle.py:471-481` wraps the real constructor so parity tests can record sync-sink calls. Keep the proxy; change what it wraps.
- **Steps**:
  ```python
  real_factory = bridge_module.runtime_emitter_for_mission

  def _factory_spy(**kwargs: Any) -> Any:
      emitter = real_factory(**kwargs)
      return _RecordingProxy(emitter, active_sink_holder["sync"])

  monkeypatch.setattr(bridge_module, "runtime_emitter_for_mission", _factory_spy)
  ```
  Update the comment at `:465-468` ("share one production classmethod") to say "share one production factory".
- **Files**: `tests/runtime/_bridge_oracle.py`
- **Parallel?**: Yes.
- **Notes**: Run `pytest tests/runtime/test_bridge_parity.py -q` immediately after; the answer-path assertions at `:1165-1166` must still record calls.

### Subtask T017 – `test_bridge_decide_next.py` (five sites)

- **Steps**: For each site, the fake class with a `for_feature` staticmethod becomes a plain callable:
  - `:242` `_FakeSyncEmitter` with `for_feature` → keep the instance class, replace `monkeypatch.setattr(rb, "RuntimeEventEmitter", _FakeSyncEmitter)` with `monkeypatch.setattr(rb, "runtime_emitter_for_mission", lambda **_: _FakeSyncEmitter())`.
  - `:282` `_RaisingEmitter` → `monkeypatch.setattr(rb, "runtime_emitter_for_mission", _raise_assertion)` where `_raise_assertion(**_)` raises the same `AssertionError("a merged mission must not construct an emitter")`.
  - `:328` `_SentinelEmitter` → factory that raises `_Sentinel`.
  - `:369` `_FakeSyncEmitterClass` (returns `fake_emitter`) → `lambda **_: fake_emitter`.
  - `:416` same shape as `:242`.
  Delete the now-unused inner classes whose only member was `for_feature`. Keep any class that is also the returned instance type.
- **Files**: `tests/runtime/test_bridge_decide_next.py`
- **Parallel?**: Yes.

### Subtask T018 – `test_runtime_bridge_blocked_paths.py` (four sites)

- **Steps**: In each `with (...)` tuple replace `patch.object(rb, "RuntimeEventEmitter") as sync_cls,` with `patch.object(rb, "runtime_emitter_for_mission") as sync_factory,`. Then find every use of `sync_cls` in that test body (typically `sync_cls.for_feature.return_value = ...` or an assertion) and rewrite to `sync_factory.return_value = ...` / `sync_factory.assert_called_once()`. Grep `sync_cls` afterwards → no hits.
- **Files**: `tests/next/test_runtime_bridge_blocked_paths.py`
- **Parallel?**: Yes.

### Subtask T019 – `test_runtime_bridge_unit.py` (four) + `test_runtime_bridge_composition.py` (one)

- **Steps**: Replace each
  ```python
  monkeypatch.setattr(runtime_bridge.RuntimeEventEmitter, "for_feature", staticmethod(lambda **_: X()))
  ```
  with
  ```python
  monkeypatch.setattr(runtime_bridge, "runtime_emitter_for_mission", lambda **_: X())
  ```
  at `test_runtime_bridge_unit.py:245, 610, 858, 2159` and `test_runtime_bridge_composition.py:63`. The composition file's `LocalOnlyEmitter(NullEmitter)` subclass that only adds `seed_from_snapshot` is now redundant (WP01 added it to `NullEmitter`); simplify to `lambda **_: NullEmitter()` and delete the subclass.
- **Files**: `tests/next/test_runtime_bridge_unit.py`, `tests/specify_cli/next/test_runtime_bridge_composition.py`
- **Parallel?**: Yes.

### Subtask T020 – Blast radius and terminology grep

- **Steps**:
  ```bash
  grep -rn "RuntimeEventEmitter\b" tests/ --include="*.py" | grep -v "_internal_runtime\|MagicMock(spec=\|test_decision_log_coord"   # expect: only annotation/comment hits, no patch sites
  grep -rn "for_feature" src/ tests/ --include="*.py"        # expect: only src/runtime/next/event_emitter.py (deleted in WP04)
  .venv/bin/pytest tests/runtime/ tests/next/ tests/specify_cli/next/ tests/specify_cli/events/ -q -p no:cacheprovider
  git diff origin/main... | grep "^+" | grep -v "^+++" | grep -n -i "feature" | grep -v "feature_dir"   # expect: empty
  ```
  Record counts in the Activity Log.
- **Files**: none (verification).

## Test Strategy

See T020. Also `ruff check` and `mypy` on the two source files. `make test-fast` before marking done.

## Risks & Mitigations

- **A patch site the table missed** → the WP04 guard test will catch any residual `runtime.next.event_emitter` import; here, the grep in T020 catches residual `for_feature`.
- **`patch.object(...) as sync_cls` bodies that assert on `for_feature`** → rewrite to the factory mock's call assertions; do not drop the assertion.
- **Parity oracle ordering** → the proxy shape is unchanged, only the wrapped callable; if `test_bridge_parity.py` regresses, stop and report — do not loosen the parity assertions.

## Review Guidance

- **Bound the out-of-map edit mechanically**: run `git diff <WP02-merge-base>..HEAD -- src/runtime/next/runtime_bridge.py` and reject the WP if any hunk is outside `:195` (import), `:1552-1556`, `:2739-2743`, or ruff import re-ordering. `:1976` and `:2187` must be byte-identical to WP02's result.
- Verify no test lost an assertion in migration (compare each site's before/after).
- Verify the composition test's redundant subclass was removed, not left dead.
- Run the T020 greps yourself.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append at the end. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`.

- 2026-09-06T16:48:26Z – system – Prompt created.
- 2026-09-06T20:35:00Z – implementer-ivan (claude) – WP03 implemented on lane-c, commit 22593696a. T014: declared out-of-map edit to src/runtime/next/runtime_bridge.py limited to three lines — import retargeted to runtime.next._internal_runtime.events (RuntimeEventEmitter now the Protocol, runtime_emitter_for_mission added) and both construction sites (:1552, :2742) call runtime_emitter_for_mission with keyword args unchanged; rationale: the factory binding is inseparable from the fifteen test-site migrations that patch the name the bridge calls. WP02's :1978/:2190 byte-identical (bound check vs merge-base d1718dd68). T015: engine TYPE_CHECKING import retargeted; because the Protocol stays at eight emit_* methods (R-2) and the engine is mypy-strict while the bridge is quarantined, the unguarded seed call became a new attr-defined error — resolved with a guarded _seed_emitter helper following the seam contract (optional seed_from_snapshot), two focused tests, no suppression; mypy 8 (base) -> 8. T016–T019: oracle spy wraps the factory; 15 sites migrated (decide_next 5, blocked_paths 4, unit 4, composition 1); for_feature-only classes deleted; redundant LocalOnlyEmitter subclasses replaced by NullEmitter(). T020: for_feature only in event_emitter.py; no event_emitter in bridge/engine; pytest runtime 752 passed/1 skipped, next 537 passed, specify_cli/next+events 321 passed/1 skipped; ruff clean; added-line feature grep empty. Moved to for_review.
