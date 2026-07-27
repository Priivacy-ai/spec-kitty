---
work_package_id: WP05
title: Gate-binding schema on the review contract
dependencies:
- WP04
requirement_refs:
- FR-005
- FR-006
- NFR-004
planning_base_branch: feat/doctrine-controlled-transition-gates
merge_target_branch: feat/doctrine-controlled-transition-gates
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-controlled-transition-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-controlled-transition-gates unless the human explicitly redirects the landing branch.
subtasks:
- T020
- T021
- T022
- T023
- T024
- T025
phase: Phase 3 - Binding
history:
- at: '{{TIMESTAMP}}'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/missions/
create_intent:
- tests/specify_cli/mission_step_contracts/test_gate_binding_schema.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/missions/step_contracts.py
- src/doctrine/missions/built_in_step_contracts/review.step-contract.yaml
- tests/specify_cli/mission_step_contracts/test_gate_binding_schema.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP05 – Gate-binding schema on the review contract

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (`implement`) and `authoritative_surface` (`src/doctrine/missions/`). `python-pedro` or `implementer-ivan` fit — this is pydantic-model + YAML doctrine work.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
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

Add a **versioned, `extra`-forbidding gate-binding schema** to the doctrine step-contract model
and author the first binding on the `for_review` transition. A gate binding is a
**relationship/configuration on an existing artefact** (the content-vs-relationship principle,
C-001 / WP01's ADR) — a field on `MissionStepContract`, NOT a new activatable `gate` ArtifactKind.
This delivers **FR-005** (versioned schema + inert `handler_kind` discriminator) and **FR-006**
(bindings ride the existing `mission_step_contract` kind).

**Done when:**

- `MissionStepContract` (`src/doctrine/missions/step_contracts.py:86`) carries a **contract-level**
  `gates: list[GateBinding] = Field(default_factory=list)`, preserving its
  `ConfigDict(extra="forbid", frozen=True, populate_by_name=True)` (`step_contracts.py:96`).
- A `GateBinding` pydantic model exists with `on_transition`, `handler`, `handler_kind`
  (default `"mission_step_contract"`, `Literal["mission_step_contract","asset"]`), `schema_version`,
  `fail_open` (default `True`), and optional `provenance` — frozen + `extra="forbid"`.
- `review.step-contract.yaml` authors the `for_review` binding whose `handler` is the WP04 registry
  key `"spec-kitty-pre-review"`.
- `MissionStepContract.save()` (`step_contracts.py:206`) does NOT inject `gates: []` into
  previously-clean contracts on re-save (byte-stable round-trip).
- `tests/specify_cli/mission_step_contracts/test_gate_binding_schema.py` proves validation,
  `extra="forbid"` rejection, `handler_kind: asset` inert round-trip, save byte-stability, and
  back-compat — authored **red-first**.
- `mypy --strict` + `ruff` clean; complexity ≤ 15/function; new-code coverage ≥ 90%.

**Explicit non-goals (GUARD):**

- **No `src/doctrine/schemas/*.schema.yaml` and no `doctor` update.** Step-contracts are pydantic
  `extra="forbid"` self-validating — the model *is* the schema. There is no
  `mission-step-contract.schema.yaml`, and adding one is out of scope (confirmed by the post-plan
  squad, C-C P4 / punt-check). Do NOT create schema-doc surfaces.
- **No loader, no join, no resolution.** `load_gate_bindings` / `resolve_active_gate_bindings` are
  WP06. This WP only defines the schema, authors the binding, and guarantees save-stability.
- `handler_kind: asset` is **inert** in half A — validated and byte-stable round-tripped, but
  never executed. Do NOT add asset-execution logic (that is Mission D / #2599, half B).

## Context & Constraints

- **Charter first.** Read `.kittify/charter/charter.md`. Bound by ATDD-first, canonical-sources,
  single-canonical-authority. Load `spec-kitty charter context --action implement`.
- **Mission docs.** `spec.md` (FR-005, FR-006, User Story 3, NFR-004), `plan.md` (IC-04),
  `data-model.md` §3 (`GateBinding` field table + validation invariants),
  `contracts/gate-binding-schema.md` (the authoritative schema, valid/rejected examples,
  half-B round-trip example, save byte-stability section).
- **Code anchors (cite these; verify before editing).**
  - `MissionStepContract` model: `src/doctrine/missions/step_contracts.py:86`; its config
    `extra="forbid", frozen=True, populate_by_name=True` at `:96`; fields `id/schema_version/
    action/mission/steps` at `:98-102`; the `validate_unique_step_ids` after-validator at `:104`.
  - `save()`: `src/doctrine/missions/step_contracts.py:206` does
    `contract.model_dump(mode="json", exclude_none=True)`. `[]` is not `None`, so a naive re-save
    injects `gates: []` into clean contracts — T022 must change this.
  - The review contract to author: `src/doctrine/missions/built_in_step_contracts/review.step-
    contract.yaml` (currently `schema_version: "1.0"`, `id: review`, `action: review`,
    `mission: software-dev`, 7 steps, no `gates`).
- **`GateBinding` field rules (from `data-model.md` §3 / `contracts/gate-binding-schema.md`).**

  | Field | Type | Default | Rule |
  |---|---|---|---|
  | `on_transition` | `str` | required | `"<from_lane>-><to_lane>"` edge key; both sides valid lanes |
  | `handler` | `str` | required | WP04 registry key AND the `mission_step_contract` candidate for the join |
  | `handler_kind` | `Literal["mission_step_contract","asset"]` | `"mission_step_contract"` | inert in half A; `asset` round-trips byte-stable, never executed |
  | `schema_version` | `str` | required | versioned; unversioned/malformed → loud reject |
  | `fail_open` | `bool` | `True` | unresolved/inactive binding → advisory (never hard-fail) |
  | `provenance` | `str \| None` | `None` | optional marker; round-trips byte-stable |

- **Schema-version convention (T020).** Adding a field to a frozen `extra="forbid"` model is a
  deliberate versioned evolution (FR-005). Follow the repo's step-contract `schema_version`
  convention — bump the contract's `schema_version` where the convention requires it, and set the
  per-binding `schema_version` (the YAML authors `"1.0"` per the contract examples). Verify the
  existing convention (grep other `*.step-contract.yaml` and any `schema_version` handling) before
  choosing the bump — do NOT invent a scheme.
- **Save byte-stability (T022, NFR-004).** Keep `model_dump(mode="json", exclude_none=True)` on
  `save()` and add a **targeted post-dump `data.pop("gates", None)`** for an empty `gates` — do NOT
  reach for a broad `exclude_defaults=True` (it would also drop `MissionStepContractStep.optional=
  False` and other legitimate defaults = regression). The goal is: a contract that never declared
  `gates` re-saves byte-identical, with no `gates: []` line appearing. Back it with the all-built-ins
  byte-golden (T024/T025).
- **C-009 allowlist check (T025).** Confirm no C-009 top-level-key allowlist gates the review
  contract's keys. `tests/specify_cli/mission_step_contracts/test_documentation_composition.py:44`
  is **documentation-only** (it describes composition, it does not enforce a key allowlist) — read
  it to confirm, and confirm nothing else rejects the new top-level `gates` key at load. If a real
  allowlist is found, that is a surface this WP must extend (flag it in the Activity Log).
- **Complexity / typing.** Python 3.11+, `mypy --strict`, `ruff`, ≤ 15 complexity. No `# noqa` /
  `# type: ignore`. Hoist repeated literals (the edge string, the handler name, `"mission_step_
  contract"`) to constants if they recur ≥ 3 times (Sonar S1192).
- **Tracker:** WP05 = epic #2535 (IC-04 schema slice). Depends on **WP04** (the binding's `handler`
  references a registry key WP04 introduces).

## Branch Strategy

- **Strategy**: single mission branch
- **Planning base branch**: `feat/doctrine-controlled-transition-gates`
- **Merge target branch**: `feat/doctrine-controlled-transition-gates`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

Work in the WP05 execution workspace from `spec-kitty implement WP05`. WP05 depends on `[WP04]`
(must be `approved`/`done`). Run tests with `PYTHONPATH=$(pwd)/src`.

## Subtasks & Detailed Guidance

### Subtask T020 – Add contract-level `gates: list[GateBinding]` to `MissionStepContract`

- **Purpose (FR-005/FR-006):** Give the review contract a home for gate bindings on the
  runtime-wired, activation-filtered `mission_step_contract` surface.
- **Steps:**
  1. Add `gates: list[GateBinding] = Field(default_factory=list)` to `MissionStepContract`
     (`step_contracts.py:86`), keeping `extra="forbid", frozen=True`.
  2. Ensure the field is **contract/action-level**, NOT per-`MissionStepContractStep` — a gate
     binds an *action's* transition, not an individual step (`data-model.md` §3).
  3. Apply the `schema_version` bump per the repo convention (see Context) — reconcile with the
     `schema_version: str = Field(alias="schema_version")` field at `:99`.
- **Files:** `src/doctrine/missions/step_contracts.py`.
- **Parallel?:** No — T021 defines the element type.
- **Notes:** Do not weaken `extra="forbid"`. Absent `gates` must default to `[]` so the 15 existing
  contracts load unchanged (T025).

### Subtask T021 – `GateBinding` model

- **Purpose (FR-005, C-002):** The versioned, explicit, `extra`-forbidding binding with the
  half-B-ready `handler_kind` discriminator.
- **Steps:**
  1. Define `GateBinding(BaseModel)` in `step_contracts.py` with
     `model_config = ConfigDict(frozen=True, extra="forbid")`.
  2. Fields per the table above: `on_transition: str`, `handler: str`,
     `handler_kind: Literal["mission_step_contract","asset"] = "mission_step_contract"`,
     `schema_version: str`, `fail_open: bool = True`, `provenance: str | None = None`.
  3. `handler_kind="asset"` must **validate and round-trip inertly** — accepted, byte-stable, never
     executed. `handler_kind` outside the `Literal` set → loud reject.
- **Files:** `src/doctrine/missions/step_contracts.py`.
- **Parallel?:** No.
- **Notes:** `schema_version` is **required** (no default) so an unversioned binding is rejected
  loudly (US3 AS3). `provenance` optional and byte-stable (NFR-004).

### Subtask T022 – `save()` `exclude_defaults` (no `gates: []` into clean contracts)

- **Purpose (NFR-004):** Adding the field must NOT churn the 15 existing contracts on re-save.
- **Steps:**
  1. Keep `save()` as `model_dump(mode="json", exclude_none=True)` (`step_contracts.py:206`) and do a
     **targeted post-dump `data.pop("gates", None)`** when `gates` is empty. Do NOT switch to a broad
     `exclude_defaults=True` — it would also drop legitimate defaults like
     `MissionStepContractStep.optional=False` (and any default `schema_version`), which is a
     regression.
  2. Verify a contract that DOES declare a non-default `gates` list still serializes it intact (the
     pop only fires on empty), and that all previously-emitted keys survive for every built-in.
- **Files:** `src/doctrine/missions/step_contracts.py`.
- **Parallel?:** No — T024 asserts this.
- **Notes:** The acceptance is byte-identity: load a clean contract → save → assert no `gates:`
  line appears and the file is byte-stable.

### Subtask T023 – Author the `for_review` binding in `review.step-contract.yaml`

- **Purpose (FR-005):** Ship the first real binding, keyed to the reference edge.
- **Steps:**
  1. Add a top-level `gates:` block to `src/doctrine/missions/built_in_step_contracts/review.step-
     contract.yaml` (alongside `steps:`, at contract level):
     ```yaml
     gates:
       - on_transition: "in_progress->for_review"
         handler: "spec-kitty-pre-review"
         handler_kind: "mission_step_contract"
         schema_version: "1.0"
         fail_open: true
         provenance: "built-in"
     ```
  2. `handler` MUST match the WP04 `GATE_REGISTRY` key exactly (`"spec-kitty-pre-review"`).
- **Files:** `src/doctrine/missions/built_in_step_contracts/review.step-contract.yaml`.
- **Parallel?:** No.
- **Notes:** Only `software-dev` ships a `review` contract — this is the ONLY built-in contract that
  gets a binding in half A. Do NOT add `gates` to any other built-in contract.

### Subtask T024 – `test_gate_binding_schema.py`

- **Purpose (ATDD red-first):** Lock schema validation, inert-asset round-trip, and save
  byte-stability.
- **Steps (author RED first):**
  1. **Schema validation:** a valid binding (minimal: `on_transition`, `handler`,
     `schema_version`) loads with `handler_kind` defaulting to `"mission_step_contract"` and
     `fail_open` to `True`.
  2. **`extra="forbid"` rejection:** an unknown key (e.g. `retries: 3`) → `ValidationError`; a
     missing `schema_version` → `ValidationError`; an invalid `handler_kind: "webhook"` →
     `ValidationError` (use the rejection examples in `contracts/gate-binding-schema.md`).
  3. **`handler_kind: asset` inert round-trip:** load a binding with `handler_kind: "asset"` +
     `provenance: "org:acme-security-pack"`, serialize, and assert **byte-stable** and that no
     asset execution is attempted (there is no executor to call — assert the model is inert data).
  4. **Save byte-stability:** load an existing clean contract (e.g. a non-review built-in), call
     `save()`, and assert the serialized bytes contain no `gates:` line and match a captured golden.
  5. **`for_review` binding present:** load `review.step-contract.yaml` and assert its single
     `gates` entry has `handler == "spec-kitty-pre-review"` and
     `on_transition == "in_progress->for_review"`.
- **Files:** `tests/specify_cli/mission_step_contracts/test_gate_binding_schema.py`.
- **Parallel?:** Written first (red), then green.

### Subtask T025 – Back-compat + C-009 allowlist check

- **Purpose (FR-006, back-compat):** Existing contracts must still load with `gates` absent; no
  hidden allowlist may reject the new key.
- **Steps:**
  1. Add a test loading every built-in `*.step-contract.yaml` (or a representative set) and assert
     each loads cleanly with `gates == []` when absent — no `ValidationError`.
  2. Read `test_documentation_composition.py:44` and confirm it is documentation-only (it does not
     enforce a top-level-key allowlist over the review contract). Grep for any real allowlist
     mechanism (`allow`/`allowed_keys`/`extra=`) around the contract loader. Record the finding in
     the Activity Log: "no C-009 allowlist covers the review contract" (or, if one exists, extend
     it and note it).
- **Files:** `tests/specify_cli/mission_step_contracts/test_gate_binding_schema.py`.
- **Parallel?:** With T024.
- **Notes:** This is the guard against the "self-validates but a sibling allowlist silently drops
  it" trap.

## Test Strategy (mandatory — ATDD red-first)

- **Location:** `tests/specify_cli/mission_step_contracts/test_gate_binding_schema.py`.
- **Red-first:** author T024/T025 assertions before the model changes; confirm they fail on the
  missing `gates` field / `GateBinding` symbol, then implement T020–T023 to green.
- **Run:**
  ```bash
  PYTHONPATH=$(pwd)/src pytest tests/specify_cli/mission_step_contracts/test_gate_binding_schema.py -q
  PYTHONPATH=$(pwd)/src pytest tests/specify_cli/mission_step_contracts/ -q   # composition suites stay green
  mypy --strict src/doctrine/missions/step_contracts.py
  ruff check src/doctrine/missions/step_contracts.py
  ```
- **Coverage:** ≥ 90% new-code coverage on the `GateBinding` model + the `save()` change, including
  every rejection branch (unknown key, missing version, bad `handler_kind`).
- **Doctrine prose guard (touching `src/doctrine/`):** run
  `pytest tests/architectural/test_no_legacy_terminology.py` before pushing.

## Risks & Mitigations

- **`save()` regression** — a broad `exclude_defaults` would over-prune meaningful defaults
  (`MissionStepContractStep.optional=False`, default `schema_version`). *Mitigation:* use the
  **targeted post-dump `data.pop("gates", None)`** (T022), backed by the all-built-ins byte-golden
  (T024.4/T025) + a positive test that a non-default field survives.
- **Frozen-model evolution churn** — bumping `schema_version` incorrectly breaks existing loads.
  *Mitigation:* follow the repo convention (verify by grep), and T025 loads all built-ins.
- **Hidden allowlist** silently dropping the new key. *Mitigation:* T025's explicit allowlist grep
  + the `test_documentation_composition.py:44` read.
- **Handler-name drift** between the YAML and WP04's registry key. *Mitigation:* T024.5 asserts the
  exact `"spec-kitty-pre-review"` string; keep the WP04 constant as the single source.

## Review Guidance

- Confirm `gates` is contract-level (not per-step), `extra="forbid"` preserved, `GateBinding`
  frozen + `extra="forbid"`.
- Confirm all three rejection branches (unknown key, missing `schema_version`, bad `handler_kind`)
  are tested and loud.
- Confirm the `handler_kind: asset` round-trip is byte-stable AND that no asset execution is
  attempted (inert).
- Confirm `save()` emits no `gates: []` into clean contracts (byte-golden).
- Confirm the `review.step-contract.yaml` binding `handler` matches WP04's registry key exactly.
- Confirm the C-009 allowlist finding is recorded; confirm NO schema.yaml / doctor surface was
  added.
- `mypy --strict` + `ruff` clean, complexity ≤ 15, new-code coverage ≥ 90%.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Initial entry**:

- {{TIMESTAMP}} – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP05 --to <status>` to change WP status.
