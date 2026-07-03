---
work_package_id: WP04
title: Render seam unification
dependencies:
- WP03
requirement_refs:
- FR-005
- FR-006
tracker_refs: []
planning_base_branch: degod-follow-ups
merge_target_branch: degod-follow-ups
branch_strategy: Planning artifacts for this mission were generated on degod-follow-ups. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into degod-follow-ups unless the human explicitly redirects the landing branch.
subtasks:
- T016
- T017
- T018
- T019
- T020
phase: Phase 2 - Foundations
assignee: ''
agent: claude
history:
- at: '2026-07-02T12:53:55Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/agent_tasks_ports.py
- tests/specify_cli/cli/commands/agent/test_tasks_ports.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – Render seam unification

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting; address all feedback.

---

## Objectives & Success Criteria

One rendering authority (FR-005 + FR-006, spec US2): `RealRender` gains a constructor
`indent` parameter; `_StatusRender` (tasks.py:1222–1235) is DELETED; all 12 compact
`print(json.dumps(...))` sites route through `Render.json_envelope`. The byte-freeze
suite (13 cases, WP01) must stay green through EVERY step — bytes are the contract.

Success: 0 inline `json.dumps` emission calls left in `tasks.py`/`tasks_shared.py`
(WP09's AST gate will pin this permanently); `_StatusRender` gone; 13/13 byte-freeze +
43/43 harness green; one production Render adapter (C-004).

**Shared-surface note**: edits `tasks.py`, `tasks_shared.py` (the 3 shared emission
helpers WP02 moved), and the gate-file ceiling — sequential shared surfaces.

## Context & Constraints

- `research.md` **D2** (the decided design: constructor param, Protocol UNCHANGED, and
  the byte-compat evidence — `json.dumps(payload)` default separators everywhere; do NOT
  add `separators=(',',':')` anywhere), **D3** (the 13-site map: which line belongs to
  which subcommand/leg).
- `contracts/parity-contract.md` Layer 2 — byte-freeze is the acceptance instrument.
- C-004: NO second adapter class (no `IndentedRender`); NO Protocol signature change.
- Alternatives already REJECTED in research D2 — do not relitigate: Protocol `indent`
  param (stub churn), named second adapter (violates one-adapter-per-port).

## Branch Strategy

- **Strategy**: {{branch_strategy}}
- **Planning base branch**: degod-follow-ups
- **Merge target branch**: degod-follow-ups

## Subtasks & Detailed Guidance

### Subtask T016 – `RealRender` constructor indent param

- **Purpose**: The generic seam capability that absorbs the status override.
- **Steps**: In `src/specify_cli/agent_tasks_ports.py`:
  ```python
  class RealRender:
      def __init__(self, console: Console | None = None, indent: int | None = None) -> None:
          self._console = console or Console()
          self._indent = indent
      def json_envelope(self, payload: Mapping[str, object]) -> str:
          return json.dumps(payload, indent=self._indent)
  ```
  (`json.dumps(payload, indent=None)` ≡ `json.dumps(payload)` — byte-identical; keep the
  existing byte-parity comment, updated.) Update/extend the ports module's unit tests
  (find them: `grep -rn "RealRender" tests/`) with: default → compact bytes, `indent=2` →
  indented bytes.
- **Files**: `src/specify_cli/agent_tasks_ports.py`, its test file.

### Subtask T017 – Delete `_StatusRender`; status ports use `RealRender(indent=2)`

- **Steps**:
  1. In `tasks.py`: delete the `_StatusRender` class (:1222–1235); in `_default_status_ports` (:1238–1245) replace `render=_StatusRender(console=console)` with `render=RealRender(console=console, indent=2)`.
  2. Sweep references: `grep -rn "_StatusRender" src/ tests/` — re-point any test that patches/imports it (this is a DELETED symbol, the sanctioned re-point case; record each in the Activity Log).
  3. The status byte case (indent=2) from WP01 must pass unchanged — that IS the acceptance.
- **Files**: `tasks.py`, affected tests.

### Subtask T018 – Route the 3 shared-helper emission sites

- **Purpose**: `_find_mission_slug` (byte case for old line 508), `_output_result` (546), `_output_error` (559) now live in `tasks_shared.py` (WP02).
- **Steps**: Give each helper a `render: Render | None = None` keyword (default-param idiom: `render = render or _tasks.RealRender()` — note `RealRender` must be a `tasks.py` binding; add it) and replace `print(json.dumps(x))` with `print(render.json_envelope(x))`. Do NOT change any payload construction. Existing callers pass nothing (default) — signatures grow only the optional kwarg (allowed: keyword-only, default preserves behavior; NFR-001 is judged on BYTES, which the freeze suite pins).
- **Files**: `src/specify_cli/cli/commands/agent/tasks_shared.py`, `tasks.py` (binding).

### Subtask T019 – Route the remaining 9 compact sites

- **Purpose**: The in-`tasks.py` sites (D3 map): mark-status :2477, list-tasks :2805, map-requirements :3349/:3474/:3488/:3585/:3665, validate-workflow :3863, list-dependents :4557 (lines will have drifted — re-locate by pattern, not number).
- **Steps** (squad-corrected — the "ports in reach" branch applies to ZERO of these sites; none has a `ports: TasksPorts` local, and `_MapReqState`/`_MarkStatusState` carry no render/ports field):
  1. ALL 6 family-glue sites (`_ms_report_none_resolved` :2477; `_mr_unknown_wp_gate` :3350, `_mr_gate_offenders` :3474/:3488, `_mr_stale_gate` :3585, `_mr_emit_output` :3665) use the **local default-param seam**: `render = RealRender()` inside the emitting helper, then `print(render.json_envelope(payload))`. Do **NOT** add a render/ports field to any State dataclass — that structural change would break WP06/WP08's verbatim-move property.
  2. The 3 port-less small bodies (`list_tasks` :2805, `validate_workflow` :3863, `list_dependents` :4557) use the same local seam.
  3. Zero payload changes anywhere.
- **Notes**: After this subtask: `grep -n "json.dumps" src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_shared.py` → only non-emission uses may remain (expect ZERO; the docstring mention at old :1225 dies with `_StatusRender`).

### Subtask T020 – Parity guard + ceiling ratchet

- **Steps**: Full parity guard; `_CEILING` lowered (net deletions); mypy strict on ALL touched src+test files together; ruff.

## Test Strategy

```bash
PWHEADLESS=1 pytest tests/specify_cli/cli/commands/agent/test_tasks_json_bytes.py \
  tests/specify_cli/cli/commands/agent/test_tasks_cli_contract.py \
  tests/specify_cli/cli/commands/agent/test_tasks_cli_contract_coord.py \
  tests/architectural/test_tasks_command_surface.py -q -p no:cacheprovider
PWHEADLESS=1 pytest tests/tasks/ tests/specify_cli/cli/commands/agent/ -q -p no:cacheprovider
python -m mypy --strict src/specify_cli/agent_tasks_ports.py src/specify_cli/cli/commands/agent/tasks.py src/specify_cli/cli/commands/agent/tasks_shared.py <touched tests>
```

## Risks & Mitigations

- **Byte drift from separator confusion**: NEVER add `separators=`; the freeze suite catches any slip instantly — run it after EACH subtask, not just at the end.
- **A test constructs `_StatusRender` directly** → sanctioned re-point (deleted symbol), logged.
- **Kwarg addition changes a helper's behavior for some caller** → keyword-only with default; byte suite + full targeted surface adjudicate.

## Review Guidance

- `grep -rn "_StatusRender" src/ tests/` → empty.
- `grep -n "json.dumps" tasks.py tasks_shared.py` → zero emission calls.
- Byte-freeze fixtures UNMODIFIED (diff the fixture file — must be untouched).
- One adapter: no new Render subclasses anywhere.

## Activity Log

> Append at the END, chronological. Format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`

- 2026-07-02T12:53:55Z – system – Prompt created.
