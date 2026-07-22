---
work_package_id: WP06
title: Binding loader, resolution join, mission-type ownership
dependencies:
- WP05
requirement_refs:
- FR-007
- FR-008
- NFR-003
- NFR-005
planning_base_branch: feat/doctrine-controlled-transition-gates
merge_target_branch: feat/doctrine-controlled-transition-gates
branch_strategy: Planning artifacts for this mission were generated on feat/doctrine-controlled-transition-gates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/doctrine-controlled-transition-gates unless the human explicitly redirects the landing branch.
subtasks:
- T026
- T027
- T028
- T029
- T030
- T031
phase: Phase 3 - Binding
history:
- at: '{{TIMESTAMP}}'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: "python-pedro"
authoritative_surface: src/specify_cli/review/gate_bindings.py
create_intent:
- src/specify_cli/review/gate_bindings.py
- tests/review/test_gate_bindings.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/review/gate_bindings.py
- tests/review/test_gate_bindings.py
role: "implementer"
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP06 – Binding loader, resolution join, mission-type ownership

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (`implement`) and `authoritative_surface` (`src/specify_cli/review/gate_bindings.py`). `python-pedro` or `implementer-ivan` fit.

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

Build the **binding loader** and the **pure resolution join** that connect a doctrine gate binding
(WP05) to the charter-activation machinery, resolving **which** named handler(s) fire on a lane
edge. This is the mechanism that mechanically closes the doctrine-controlled gate: the DRG carries
**no** binding payload (`src/doctrine/drg/models.py:292-311` — a `DRGNode` has only
`urn/kind/label/provenance/tags`), so bindings are loaded separately and **joined** against the
activated-URN set. Delivers **FR-007** (explicit binding-resolution join + loader), **FR-008**
(lane-edge → (mission, action) → contract ownership + mission-type axis), **NFR-003** (non-vacuous
resolution), **NFR-005** (bounded loads).

**Done when:**

- `src/specify_cli/review/gate_bindings.py` exists with:
  - `load_gate_bindings(repo_root, mission, action)` — the named loader (the `mission` param is
    **mandatory**).
  - a mission-type resolver (`st.mission_slug` → `meta.json`) and the lane-edge → (mission, action)
    → contract mapping table.
  - `resolve_active_gate_bindings(...)` — a **pure function** (activated `mission_step_contract`
    URN set ⋈ contract bindings → active bindings for the edge).
- The no-contract / no-binding path surfaces a **visible `NO_COVERAGE` warning distinguishable
  from "handler not activated"** — never a silent skip.
- Per-transition loads are **bounded** (NFR-005): one graph load + one binding load, no
  per-candidate re-resolution.
- `tests/review/test_gate_bindings.py` proves non-vacuous resolution (positive + negative-control),
  a **mandatory non-`software-dev` negative control**, mission-type resolution, and bounded loads
  — authored **red-first**.
- `mypy --strict` + `ruff` clean; complexity ≤ 15/function; new-code coverage ≥ 90%.

**GUARD (BLOCKER — #1 anti-laziness finding, post-plan squad R-F1):** The **mission-type-blind
loader** is the mission's top risk. Only `software-dev` ships a `review` action contract
(`research` → gathering/methodology/output/scoping/synthesis; `documentation` →
accept/audit/design/discover/generate/publish/validate — verified). All missions share the 9-lane
FSM and hit `for_review`, so a loader that drops the `mission` param resolves research /
documentation / consumer WPs to **no gate silently** = mission-type-axis coupling that every
software-dev fixture passes green while it is broken. **The non-`software-dev` negative-control
test (T031) is MANDATORY, not optional.**

## Context & Constraints

- **Charter first.** Read `.kittify/charter/charter.md`. Bound by ATDD-first, canonical-sources
  (mirror `filter_graph_by_activation`, do not reimplement it), architectural-gate discipline. Load
  `spec-kitty charter context --action implement`.
- **Mission docs.** `spec.md` (FR-007, FR-008, NFR-003, NFR-005, User Story 1 + edge cases,
  Assumptions), `plan.md` (IC-04 risks — the mission-type-blind loader is called the *blocker*),
  `data-model.md` §5 (the three-step join, the sequence diagram, the no-contract path), §6
  (lane-edge → (mission, action) → contract table + precedence),
  `contracts/transition-gate-hook.md` (resolution invariants).
- **Code anchors — MIRROR the executor's activation pattern, do NOT ride the graph.**
  - `MissionStepContractRepository.get_by_action(mission, action)` —
    `src/doctrine/missions/step_contracts.py:160` — keys on `(mission, action)` and returns the
    contract or `None`. This is why `mission` is mandatory.
  - The activation-filter usage to mirror: `src/specify_cli/mission_step_contracts/executor.py:179`
    (`load_validated_graph(context.repo_root)`) → `:181-183`
    (`self._resolve_pack_context(...)` then `filter_graph_by_activation(graph, pack_context)`).
  - `_resolve_pack_context`: `executor.py:259-282` — `PackContext.from_config(repo_root)`
    (`src/charter/pack_context.py:184`) with **fail-CLOSED** on `OrgPackEnvVarUnsetError` /
    `OrgPackSubdirEscapeError` (`executor.py:275`), `None` on other errors. Copy this discipline.
  - `filter_graph_by_activation`: `src/charter/drg.py:433` — returns a copy of the graph limited to
    activated artifacts; `mission_step_contract` nodes survive only when their owning mission type
    is activated.
  - `_candidate_urn` shape: `executor.py:315` — how a candidate name resolves to a URN;
    `_ARTIFACT_TO_NODE_KIND` at `executor.py:31` maps `ArtifactKind.MISSION_STEP_CONTRACT →
    NodeKind.MISSION_STEP_CONTRACT`. Mirror the candidate→URN shape to test handler resolution.
  - `DRGNode`: `src/doctrine/drg/models.py:292-311` — **carries no binding payload**. This is the
    reason the loader and the join are separate: the graph gates *whether* the contract's bindings
    fire (via URN activation), the loader supplies *what* the bindings are.
  - Mission-type field: WP-lane events carry `mission_slug`
    (`src/specify_cli/status/models.py:313`); resolve mission type from the mission's `meta.json`
    (the `spk-runtime` identity model, CLAUDE.md "Mission Identity Model"). `WPStateSnapshot`
    carries a `mission_type` at `status/models.py:663` — verify whether it is populated at the hook
    boundary; if not, read `meta.json`. Do NOT hardcode `"software-dev"`.
- **The three-step join (from `data-model.md` §5, FR-007).**
  1. **Activated URN set** — `PackContext.from_config(repo_root)` (fail-closed on env/escape) →
     `filter_graph_by_activation(load_validated_graph(repo_root), pack)` → the surviving
     `mission_step_contract` node URNs. The review contract's own URN being among the survivors is
     what gates whether its bindings fire at all.
  2. **Binding set** — `load_gate_bindings(repo_root, mission, action)` → the review contract's
     `gates` (or the distinguishable no-contract / no-binding `NO_COVERAGE` warn).
  3. **Retain** — keep bindings whose **owning review contract's URN**
     (`mission_step_contract:<mission>/review` — the URN of the contract `get_by_action(mission,
     action)` located) is in the **activated** `mission_step_contract` URN set AND whose
     `on_transition` matches the current lane edge. The survivors are the active bindings for the
     edge. The `b.handler` is **NOT** a DRG candidate — it is resolved separately by a plain
     `GATE_REGISTRY[b.handler]` dict lookup (KeyError on miss, WP04), never joined against the
     activated URN set.
- **Lane-edge → (mission, action) → contract table (FR-008, `data-model.md` §6).** Half A gates
  **only** `in_progress->for_review` → `(<resolved mission>, review)` →
  `review.step-contract.yaml` `.gates`. The schema admits `for_review->in_review` and
  `in_review->approved` but the mission does not require gating them.
- **Precedence (FR-008).** More than one activated binding on one edge → **all** fire (no
  last-wins); dispatch order is a **stable sort** by `(declaration_index_within_step, handler)`.
  Expose the ordering so WP09's dispatch and WP08's aggregation consume a deterministic list.
- **Complexity / typing.** Python 3.11+, `mypy --strict`, `ruff`, ≤ 15/function. Keep
  `resolve_active_gate_bindings` a **pure** fn (inputs in, list out, no I/O) so it stays testable
  and ≤ 15; the loader/resolver does the I/O. No `# noqa` / `# type: ignore`. Hoist the edge string
  and the `review` action literal to constants (Sonar S1192).
- **Tracker:** WP06 = epic #2535 (IC-04 join slice). Depends on **WP05** (loads the `gates` field
  WP05 adds; joins against activation).

## Branch Strategy

- **Strategy**: single mission branch
- **Planning base branch**: `feat/doctrine-controlled-transition-gates`
- **Merge target branch**: `feat/doctrine-controlled-transition-gates`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

Work in the WP06 execution workspace from `spec-kitty implement WP06`. WP06 depends on `[WP05]`
(must be `approved`/`done`). Run tests with `PYTHONPATH=$(pwd)/src`.

## Subtasks & Detailed Guidance

### Subtask T026 – `load_gate_bindings(repo_root, mission, action)` via the repository

- **Purpose (FR-007):** Read a contract's `gates` off the runtime-wired `MissionStepContract`
  surface — the DRG carries no binding payload, so bindings load separately.
- **Steps:**
  1. Implement `load_gate_bindings(repo_root: Path, mission: str, action: str) ->
     list[GateBinding]` that delegates to `MissionStepContractRepository.get_by_action(mission,
     action)` (`step_contracts.py:160`) — the same repository the executor uses (`executor.py:160`)
     — and returns `contract.gates` (WP05's field), or a distinguishable empty/no-contract signal
     (see T029).
  2. The **`mission` param is mandatory** — do NOT provide a default or drop it. `get_by_action`
     keys on `(mission, action)`; a mission-blind call is the blocker this WP exists to prevent.
- **Files:** `src/specify_cli/review/gate_bindings.py`.
- **Parallel?:** No — T027/T028/T029 build on it.
- **Notes:** Construct the repository the way the executor does (project_dir under
  `.kittify/doctrine/mission_step_contracts`, plus built-ins) so both built-in and project-layer
  contracts are visible.

### Subtask T027 – Mission-type resolution + lane→(mission, action)→contract map

- **Purpose (FR-008):** Resolve the mission type from identity (never hardcoded) and map the WP-lane
  edge to its owning `(mission, action)` and contract.
- **Steps:**
  1. Implement `resolve_mission_type(st)` reading `st.mission_slug` → the mission's `meta.json`
     mission-type field (or `WPStateSnapshot.mission_type` at `status/models.py:663` if populated at
     the boundary — verify). Never hardcode `"software-dev"`.
  2. Implement the lane-edge → owning action map: `in_progress->for_review` → action `review` (the
     only half-A gated edge, C-006). Encode `for_review->in_review` and `in_review->approved` as
     schema-admitted-but-not-required per §6 (map them to `review` too, but half A does not gate
     them).
  3. Compose: `(resolved mission, review)` → `load_gate_bindings(repo_root, mission, "review")`.
- **Files:** `src/specify_cli/review/gate_bindings.py`.
- **Parallel?:** No.
- **Notes:** This is the mission-type axis. A `(research, review)` / `(documentation, review)` /
  `(consumer-custom, review)` resolves to **no contract** → T029's distinguishable warn.

### Subtask T028 – `resolve_active_gate_bindings` PURE function (activated-URN ⋈ bindings)

- **Purpose (FR-007, NFR-003, NFR-005):** The join that decides which bindings are active — pure,
  testable, deterministic.
- **Steps:**
  1. Signature (design intent per `data-model.md` §5): `resolve_active_gate_bindings(
     activated_msc_urns: frozenset[str], bindings: list[GateBinding], edge_key: str,
     owning_contract_urn: str) -> list[GateBinding]` — inputs in, active-binding list out,
     **no I/O**.
  2. Retain a binding iff `b.on_transition == edge_key` AND `owning_contract_urn ∈
     activated_msc_urns` — where `owning_contract_urn` is the **owning review contract's URN**
     (`mission_step_contract:<mission>/review`, the URN of the contract `get_by_action(mission,
     action)` located). **The activation gate is the owning contract's URN, NOT the handler.** The
     `b.handler` is resolved separately by a plain `GATE_REGISTRY[b.handler]` dict lookup (KeyError
     on miss) — it is NOT a `_candidate_urn`/DRG candidate and is NOT a `mission_step_contract`
     candidate resolved against the activated URN set.
  3. Return the survivors **stable-sorted** by `(declaration_index, handler)` (§6 precedence).
  4. The **caller** (the loader/resolver, later consumed by WP09) computes `activated_msc_urns` by
     MIRRORING the executor pattern: `PackContext.from_config` (fail-closed) →
     `filter_graph_by_activation(load_validated_graph(repo_root), pack)` → the surviving
     `mission_step_contract` URNs. **Mirror the pattern — do NOT ride the graph for the binding
     payload** (the DRG carries none, `drg/models.py:292-311`); load bindings separately (T026) and
     join here.
- **Files:** `src/specify_cli/review/gate_bindings.py`.
- **Parallel?:** No.
- **Notes:** Keep this fn pure so its full positive/negative matrix (T031) runs without any graph or
  filesystem. The impure orchestration (graph load, contract load) lives in the resolver that calls
  it, not inside it — this keeps both ≤ 15 complexity.

### Subtask T029 – No-contract / no-binding path → distinguishable `NO_COVERAGE` warn

- **Purpose (FR-008, FR-012, NFR-003):** The mission-type-axis coupling guard. A missing contract
  or a contract with no matching binding must be **visible and distinguishable** from "handler not
  activated" — never a silent skip.
- **Steps:**
  1. When `load_gate_bindings` finds **no `(mission, review)` contract** (research / documentation /
     consumer): surface a `NO_COVERAGE` warn whose reason names the missing-contract cause, e.g.
     `no gate binding for (<mission>, review->for_review)`.
  2. When a `software-dev` contract exists but has **no matching `for_review` binding**: surface a
     separately-worded `NO_COVERAGE` warn (no-binding cause).
  3. Both are **distinct branches, separately worded**, and both distinct from the "handler
     resolved but not activated" advisory (which comes from the join returning an empty `active`
     list with the binding present). Three distinguishable outcomes — model them so a test can tell
     them apart (e.g. a small result type / enum reason, not a bare boolean).
- **Files:** `src/specify_cli/review/gate_bindings.py`.
- **Parallel?:** No.
- **Notes:** This is the anti-silent-skip contract. A single generic "no gate" message that
  collapses the three causes is a **review-blocking** defect — the wording must let an operator (and
  T031) distinguish "no contract for this mission type" from "handler not activated."

### Subtask T030 – Bounded loads (NFR-005)

- **Purpose:** One graph load + one binding load per transition; no per-candidate re-resolution.
- **Steps:**
  1. Structure the resolver so `load_validated_graph` + `filter_graph_by_activation` run **once**,
     and `load_gate_bindings` runs **once**, per transition — computed before the retain loop.
  2. The retain step (T028) is pure set-membership on the precomputed activated-URN set — no
     per-node re-resolution, no per-candidate re-load.
- **Files:** `src/specify_cli/review/gate_bindings.py`.
- **Parallel?:** With T028.
- **Notes:** T031 asserts this with call-count spies (see below).

### Subtask T031 – `test_gate_bindings.py` (non-vacuous + non-software-dev negative control)

- **Purpose (NFR-003, FR-008 blocker):** Prove the join is non-vacuous, mission-type-aware, and
  bounded — with the MANDATORY non-`software-dev` negative control.
- **Steps (author RED first):**
  1. **Positive arm (non-vacuous):** a `software-dev` review contract with a `for_review` binding,
     where the contract's **own** URN (`mission_step_contract:software-dev/review`, from
     `get_by_action("software-dev","review")`) is a member of a **real** activated
     `mission_step_contract` URN set → `resolve_active_gate_bindings` returns that binding. Assert
     resolution against the **REAL activated review-contract URN** — NOT a fabricated handler-URN
     mock (that is the vacuous trap NFR-003 forbids). A test that would pass against an **empty**
     graph is rejected in review (NFR-003). Assert the returned list is non-empty AND that the same
     inputs with the **owning-contract** URN removed from the activated set return **empty** (the
     negative-control arm).
  2. **Negative control on a NON-`software-dev` mission (MANDATORY):** with a `research` (or
     `documentation`) mission — which has **no** `review` action contract — assert
     `load_gate_bindings(repo_root, "research", "review")` yields the **distinguishable
     `NO_COVERAGE` warn** (no-contract cause), NOT a silent empty skip and NOT the "handler not
     activated" wording. This is the R-F1 blocker guard — it MUST fail if the loader ever drops the
     `mission` param.
  3. **Mission-type resolution:** assert `resolve_mission_type` reads the mission type from
     `meta.json` / snapshot and does not hardcode `software-dev` (feed a non-software-dev slug and
     assert the resolved type).
  4. **Bounded-loads assertion (NFR-005):** spy/monkeypatch `load_validated_graph`,
     `filter_graph_by_activation`, and `load_gate_bindings` (or the repository `get_by_action`) and
     assert each is called **exactly once** per resolution — no per-candidate re-load.
  5. **Distinguishability:** assert the three reason strings (no-contract, no-binding,
     not-activated) are pairwise distinct.
- **Files:** `tests/review/test_gate_bindings.py`.
- **Parallel?:** Written first (red), then green.
- **Notes:** Prefer real doctrine fixtures for the mission-type arms (the built-in `research` /
  `documentation` contracts genuinely lack a `review` action) so the negative control exercises the
  real coupling, not a mock that could hide it.

## Test Strategy (mandatory — ATDD red-first)

- **Location:** `tests/review/test_gate_bindings.py`.
- **Red-first:** author T031 before `gate_bindings.py` exists; confirm each arm fails for the right
  reason, then implement T026–T030 to green. The non-`software-dev` negative control (T031.2) MUST
  be present and red first.
- **Run:**
  ```bash
  PYTHONPATH=$(pwd)/src pytest tests/review/test_gate_bindings.py -q
  PYTHONPATH=$(pwd)/src pytest tests/review/ tests/specify_cli/mission_step_contracts/ -q
  mypy --strict src/specify_cli/review/gate_bindings.py
  ruff check src/specify_cli/review/gate_bindings.py tests/review/test_gate_bindings.py
  ```
- **Coverage:** ≥ 90% new-code coverage, including all three distinguishable no-coverage/inactive
  branches and the negative-control resolution path.
- **NFR-003 review bar:** a resolution test that would pass against an empty graph is rejected —
  the positive arm must have a genuinely-populated activated set and a paired negative control.

## Risks & Mitigations

- **Mission-type-blind loader (BLOCKER).** *Mitigation:* mandatory `mission` param (T026),
  mission-type resolution from `meta.json` (T027), and the non-`software-dev` negative control
  (T031.2). This is the R-F1 finding — treat any regression toward a mission-blind call as a
  review failure.
- **Vacuous resolution** (a test that passes against an empty graph). *Mitigation:* NFR-003
  positive+negative arms with a populated activated set.
- **Riding the graph for the payload** — assuming the DRG carries bindings. *Mitigation:* the
  loader reads `.gates` off the contract model separately (`drg/models.py:292-311` has no payload);
  the graph only supplies the activated-URN set to join against.
- **Silent no-coverage collapse** — one generic "no gate" message. *Mitigation:* three
  separately-worded branches (T029) + pairwise-distinct assertion (T031.5).
- **Unbounded loads** — re-resolving per candidate. *Mitigation:* one-load structure (T030) +
  call-count spies (T031.4).
- **Pack-context fail-open drift** — swallowing an env/escape misconfig. *Mitigation:* copy the
  `executor.py:275` fail-CLOSED semantics for `OrgPackEnvVarUnsetError` / `OrgPackSubdirEscapeError`
  (distinct from the fail-open handler-execution rule).

## Review Guidance

- **BLOCKER check:** confirm the non-`software-dev` negative control (T031.2) exists, is
  non-vacuous, and asserts the distinguishable no-contract warn — reject the WP if it is missing or
  mocked-away.
- Confirm `load_gate_bindings` requires `mission` (no default) and resolves mission type from
  `meta.json` (not hardcoded).
- Confirm `resolve_active_gate_bindings` is a pure function with a genuine positive + negative
  arm (rejects empty-graph-passing tests, NFR-003).
- Confirm the three no-coverage/inactive reasons are pairwise distinct and separately worded.
- Confirm bounded loads via call-count spies (one graph load + one binding load).
- Confirm the activation pattern is **mirrored** from `executor.py:179-183` (not reimplemented) and
  fail-CLOSED on pack-context misconfig.
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

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP06 --to <status>` to change WP status.
