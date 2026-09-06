---
work_package_id: WP04
title: Deletion, single-class guard, docs, disclosure
dependencies:
- WP03
requirement_refs:
- C-001
- C-002
- C-003
- C-006
- C-007
- FR-001
- FR-009
- FR-010
- FR-011
- NFR-003
- NFR-005
- NFR-007
planning_base_branch: feat/dead-port-disposition
merge_target_branch: feat/dead-port-disposition
branch_strategy: Planning artifacts for this mission were generated on feat/dead-port-disposition. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/dead-port-disposition unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-dead-port-disposition-01M1VRA2
base_commit: 4987c711a535cf915d4023dac678aff665cf0235
created_at: '2026-09-06T20:16:44.380920+00:00'
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
phase: Phase 4 - Closure
history:
- at: '2026-09-06T16:48:26Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: implementer-ivan
authoritative_surface: src/runtime/next/
create_intent:
- tests/architectural/test_runtime_emitter_seam.py
execution_mode: code_change
model: ''
owned_files:
- src/runtime/next/event_emitter.py
- tests/specify_cli/events/test_decision_log_coord.py
- tests/status/test_producer_conformance.py
- tests/contract/test_identity_contract_matrix.py
- tests/architectural/test_runtime_emitter_seam.py
- CHANGELOG.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP04 – Deletion, single-class guard, docs, disclosure

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

Close the mission: delete the concrete duplicate class, make the defect class unrepeatable with an architectural guard, correct the two reservation comments that still point at the deleted module, and disclose the behavior change.

Done means:

- `src/runtime/next/event_emitter.py` is gone; `grep -rn "event_emitter\b" src/ tests/ --include="*.py"` → no hits (FR-001, FR-010).
- `grep -rn "^class RuntimeEventEmitter" src/runtime/next/` → exactly one hit, in `_internal_runtime/events.py` (SC-001).
- `tests/architectural/test_runtime_emitter_seam.py` exists and is green; when you temporarily reintroduce `buffer.flush(ctx.sync_emitter)` in a scratch copy, it fails with a message naming ADR 2026-09-06-2 (the `043` by-construction closure).
- `tests/status/test_producer_conformance.py` and `tests/contract/test_identity_contract_matrix.py` comments name `runtime_emitter_for_mission` / `register_runtime_emitter_factory` as the seam (FR-009).
- `CHANGELOG.md` has one `### Fixed` entry under `## [Unreleased] - 3.2.7rc1` (FR-011, C-006).
- Full blast radius (plan.md §Test Plan) green; retired-surface scan 0 hits; net LOC under `src/runtime/next/` decreased (NFR-003).
- `src/specify_cli/__init__.py` untouched (no version bump).

## Context & Constraints

- ADR §Consequences (Positive / Negative), §Confirmation (1)–(4).
- Plan §Design "Consolidation tests + mechanical rewrites (Concern E)" and "Docs + disclosure (Concern F)".
- Contracts: `emitter-seam.md` S7–S8; `decision-log-flush.md` F7 and §Disclosure.
- Prerequisites delivered by WP03: bridge and engine adapter no longer import `runtime.next.event_emitter`; every test patch site uses the factory name. Confirm with the first grep in T022 before deleting anything.
- CHANGELOG conventions: `CHANGELOG.md:1-30` — Keep a Changelog; entries under `## [Unreleased] - 3.2.7rc1` / `### Fixed` are one bold-led paragraph each with issue/mission references; see the existing `#3871` entry for tone.
- Existing architectural-guard style to mirror: any short file in `tests/architectural/` that reads source text and asserts on it (e.g. `test_no_retired_subsystems.py`'s regex approach). Mark the new test `architectural` (and `fast`); it must not import the runtime.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on feat/dead-port-disposition; completed changes must merge back into feat/dead-port-disposition.
- **Planning base branch**: feat/dead-port-disposition
- **Merge target branch**: feat/dead-port-disposition

> Execution worktrees are allocated per computed lane from `lanes.json`; run `spec-kitty agent action implement WP04 --agent <name>`.

## Subtasks & Detailed Guidance

### Subtask T021 – Move the last live importer

- **Steps**: `tests/specify_cli/events/test_decision_log_coord.py:17`: `from runtime.next.event_emitter import RuntimeEventEmitter` → `from runtime.next._internal_runtime.events import RuntimeEventEmitter`. The six `MagicMock(spec=RuntimeEventEmitter)` uses (`:132, :206, :257, :316, :363, :510`) now spec against the Protocol, which exposes the same eight emit methods; no test body changes. Run the file.
- **Files**: `tests/specify_cli/events/test_decision_log_coord.py`
- **Parallel?**: No (must precede T022).

### Subtask T022 – Delete the concrete module

- **Steps**:
  1. `grep -rn "runtime.next.event_emitter\|from runtime.next import event_emitter\|next/event_emitter" src/ tests/ packs/ docs/ --include="*.py" --include="*.md" --include="*.yaml"` — the only permitted hits are historical mission snapshots under `kitty-specs/` and the ADR text. Any hit under `src/` or `tests/` means WP03 or T021 is incomplete: stop and fix there first.
  2. `git rm src/runtime/next/event_emitter.py`.
  3. `.venv/bin/pytest tests/runtime/ tests/next/ tests/specify_cli/ -q -p no:cacheprovider -x` to prove collection and execution survive the deletion.
- **Files**: `src/runtime/next/event_emitter.py` (deleted)
- **Parallel?**: No.

### Subtask T023 – Architectural guard

- **Purpose**: S7, S8, F7. Make the three regressions this mission fixes impossible to reintroduce silently.
- **Steps**: Create `tests/architectural/test_runtime_emitter_seam.py`:
  ```python
  """Guard the consolidated runtime emitter seam (ADR 2026-09-06-2).

  Three regressions this mission closed must stay closed:
  1. a second class named RuntimeEventEmitter under src/runtime/next/,
  2. any import of the deleted runtime.next.event_emitter module,
  3. an engine-facing reference to the plain seam in the bridge (the flush
     target / composition emitter bypasses that dropped decision events).
  """
  from __future__ import annotations
  import re
  from pathlib import Path
  import pytest

  pytestmark = [pytest.mark.architectural, pytest.mark.fast]
  _ADR = "docs/adr/3.x/2026-09-06-2-runtime-event-emitter-disposition.md"
  _REPO = Path(__file__).resolve().parents[2]
  _RUNTIME_NEXT = _REPO / "src" / "runtime" / "next"
  _BRIDGE = _RUNTIME_NEXT / "runtime_bridge.py"

  def _py_files(root: Path):
      return [p for p in root.rglob("*.py") if ".venv" not in p.parts]

  def test_exactly_one_runtime_event_emitter_class() -> None:
      hits = [p for p in _py_files(_RUNTIME_NEXT) if re.search(r"^class RuntimeEventEmitter\b", p.read_text(encoding="utf-8"), re.M)]
      assert [h.relative_to(_REPO).as_posix() for h in hits] == ["src/runtime/next/_internal_runtime/events.py"], f"one canonical seam class only; see {_ADR}"

  def test_deleted_event_emitter_module_is_not_imported() -> None:
      pat = re.compile(r"runtime\.next\.event_emitter\b|from runtime\.next import event_emitter\b")
      offenders = [p.relative_to(_REPO).as_posix() for p in _py_files(_REPO / "src") + _py_files(_REPO / "tests") if pat.search(p.read_text(encoding="utf-8"))]
      assert offenders == [], f"runtime.next.event_emitter was deleted; see {_ADR}: {offenders}"

  @pytest.mark.parametrize("needle", ["flush(ctx.sync_emitter)", "sync_emitter=ctx.sync_emitter"])
  def test_bridge_never_hands_engine_paths_the_plain_seam(needle: str) -> None:
      assert needle not in _BRIDGE.read_text(encoding="utf-8"), (
          f"{needle!r} reintroduces the decision-log bypass fixed by {_ADR}; engine-facing calls must use ctx.emitter_for_engine"
      )
  ```
  Adjust `parents[2]` if the repo-root resolution differs from sibling tests (check how `test_no_retired_subsystems.py` finds the root and copy it). Verify the negative: copy the bridge to a temp path with the bypass reintroduced and confirm the parametrized test would fail (a quick REPL check is enough; do not commit a red test).
- **Files**: `tests/architectural/test_runtime_emitter_seam.py` (new)
- **Parallel?**: No (after T022).

### Subtask T024 – Reservation comments

- **Steps**:
  - `tests/status/test_producer_conformance.py:10-14`: rewrite the parenthetical to: "(The former second section pinned the sync `EventEmitter`'s `emit_*` methods; that producer died with the sync transport, issue #5. When epic E3 registers a real producer via `runtime.next._internal_runtime.events.register_runtime_emitter_factory` its payloads belong back in this file.)"
  - `tests/contract/test_identity_contract_matrix.py:33-37`: same substitution for "wires a new emitter at the `runtime.next.event_emitter` seam" → "registers a new producer via `register_runtime_emitter_factory` (`runtime.next._internal_runtime.events`)".
  Comment-only; run both files to prove nothing else moved.
- **Files**: both test files.
- **Parallel?**: Yes.

### Subtask T025 – CHANGELOG entry

- **Steps**: Under `## [Unreleased] - 3.2.7rc1` → `### Fixed`, add one entry in the house style (bold lead, then mechanism, before/after). Content it must carry: (1) decision requests raised under the strict retrospective policy (`before_completion` + `block`) and on composition dispatch were never written to the mission's `decisions.events.jsonl`; (2) they now are, exactly once, with rollback on a refused gate unchanged; (3) the permanently no-op `RuntimeEventEmitter` concrete class was consolidated onto the canonical runtime Protocol/`NullEmitter` with a `runtime_emitter_for_mission` factory and `register_runtime_emitter_factory` hook for a future producer; (4) reference ADR `2026-09-06-2` and mission `dead-port-disposition-01M1VRA2`. Do not bump the version.
- **Files**: `CHANGELOG.md`
- **Parallel?**: Yes.

### Subtask T026 – Full blast radius and scans

- **Steps**:
  ```bash
  make test-fast
  .venv/bin/pytest tests/runtime/ tests/next/ tests/specify_cli/next/ tests/specify_cli/events/ -q -p no:cacheprovider
  .venv/bin/pytest tests/status/test_producer_conformance.py tests/contract/test_identity_contract_matrix.py -q -p no:cacheprovider
  .venv/bin/pytest tests/architectural/test_layer_rules.py tests/architectural/test_no_legacy_terminology.py tests/architectural/test_runtime_emitter_seam.py tests/architectural/test_no_retired_subsystems.py -q -p no:cacheprovider
  .venv/bin/ruff check . && .venv/bin/mypy src/runtime/next/_internal_runtime/events.py src/specify_cli/events/decision_log.py
  git diff origin/main...HEAD --stat -- src/runtime/next/    # net negative
  ```
  Retired-surface scan: run the `_RETIRED_SURFACE_RE` from `tests/architectural/test_no_retired_subsystems.py` over `git diff origin/main...HEAD | grep '^+'` (a five-line Python snippet); expect 0 hits. Record every command with counts in the Activity Log; these become the PR's *Tests run* section.
- **Files**: none (verification).

## Test Strategy

See T026. This WP is the last gate before the mission PR; nothing may be left red or unexplained.

## Risks & Mitigations

- **Deleting with a live importer left** → T022 step 1 grep is mandatory before `git rm`.
- **Guard test root resolution wrong in CI** → copy the root-finding idiom from a sibling architectural test.
- **CHANGELOG lint** (`tests/docs/`) → run `pytest tests/docs/test_docs_structural_lint.py -q` after editing.

## Review Guidance

- Verify the guard's third test actually fails on a reintroduced bypass (ask for the negative-check evidence in the Activity Log).
- Verify the CHANGELOG entry discloses the behavior change explicitly, not just the consolidation.
- Verify `docs/adr/` was not edited (the ADR is already Accepted and amended; this mission does not touch it).
- Confirm the net LOC under `src/runtime/next/` decreased.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last). Append at the end. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`.

- 2026-09-06T16:48:26Z – system – Prompt created.
