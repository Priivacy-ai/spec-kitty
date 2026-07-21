---
work_package_id: WP01
title: Relation vocabulary + NodeKind foundation
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
- FR-004
- FR-012
- FR-014
planning_base_branch: doctrine/drg-missing-links-analysis
merge_target_branch: doctrine/drg-missing-links-analysis
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-missing-links-analysis. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-missing-links-analysis unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
phase: Phase 1 - Foundation
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "72136"
shell_pid_created_at: "1784640444.101025"
history:
- at: '2026-07-21T11:08:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/doctrine/drg/models.py
create_intent:
- tests/doctrine/drg/test_models.py
execution_mode: code_change
model: ''
owned_files:
- src/doctrine/drg/models.py
- src/doctrine/artifact_kinds.py
- tests/doctrine/drg/test_models.py
- tests/doctrine/drg/test_nodekind_artifactkind.py
- tests/doctrine/drg/test_kind_mapping_totality.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Relation vocabulary + NodeKind foundation

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` (implement) and `authoritative_surface` (`src/doctrine/drg/models.py` — DRG domain model work).

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete.
- **Report progress**: As you address each feedback item, update the Activity Log.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Objectives & Success Criteria

This is the foundation work package — every other WP in this mission depends on it landing first (Constraint C-006, step 1 of the migration order). Nothing here removes `opposed_by` yet; this WP is purely additive.

Done means:
- `Relation.IN_TENSION_WITH`, `Relation.RECONCILES_TENSION`, `Relation.REJECTS` exist with the exact string values `"in_tension_with"`, `"reconciles_tension"`, `"rejects"`.
- A `RELATION_DESCRIPTIONS: dict[Relation, str]` registry exists in the same module, with a real (not placeholder) human-readable description for each of the three new relations — this text is what WP08 will later mirror into `docs/architecture/doctrine-relationships.md` verbatim, so write it carefully now; you will not get a second pass without creating an ownership conflict with WP08.
- `NodeKind.ANTI_PATTERN = "anti_pattern"` exists, and the corresponding `ArtifactKind` member exists in `src/doctrine/artifact_kinds.py`.
- `DRGNode` has a `tags: list[str] = Field(default_factory=list)` field.
- `DRGNode._validate_urn` accepts `anti_pattern:<id>` URNs (prefix must match `kind.value`, same rule as every other kind).
- All new/changed branches have focused tests (NFR-005).

## Context & Constraints

- Read `kitty-specs/doctrine-tension-edges-01KY1WPC/spec.md` (FR-001/002/003/004/012, Key Entities section) and `data-model.md` (this WP implements exactly the "Relation" and "NodeKind"/"DRGNode" sections there) before starting.
- `docs/architecture/doctrine-relationships.md` is the FR-012/NFR-004 doc-parity target — WP08 builds a check that this doc must match `RELATION_DESCRIPTIONS` verbatim. You are not responsible for editing that doc in this WP, but the description text you write here is load-bearing for that later check — write real prose, not a stub.
- Do **not** wire `ANTI_PATTERN` into `_SINGULAR_TO_PLURAL`, `_SINGULAR_TO_PER_KIND_FIELD`, `_SINGULAR_TO_PLURAL_KIND`, or `PackContext` — that is WP04's job (`src/charter/drg.py`, `src/charter/activations.py`, `src/charter/pack_context.py`). Touching those files here would create an ownership conflict.
- Do **not** touch `opposed_by`, `Contradiction`, or any built-in `*.yaml` artifact content — that is WP02 (adds new edges) and WP03 (removes the old field), both sequenced after this WP.

## Branch Strategy

- **Strategy**: single_branch — no coordination/lanes topology; planning and merge-target branch are the same branch.
- **Planning base branch**: `doctrine/drg-missing-links-analysis`
- **Merge target branch**: `doctrine/drg-missing-links-analysis`

> These fields are populated automatically by `spec-kitty agent mission tasks`. Do NOT change them manually.

Implementation command: `spec-kitty agent action implement WP01 --agent <name>` (no dependencies — starts immediately).

## Subtasks & Detailed Guidance

### Subtask T001 – Add the three new `Relation` enum members

- **Purpose**: These are the vocabulary every other WP builds on. Nothing downstream can be authored (WP02) or checked (WP04/WP05/WP06) until these exist.
- **Steps**:
  1. Open `src/doctrine/drg/models.py`. Find `class Relation(StrEnum)` (currently ends with `REFINES = "refines"` around line 88).
  2. Add three new members after `REFINES`:
     ```python
     IN_TENSION_WITH = "in_tension_with"
     RECONCILES_TENSION = "reconciles_tension"
     REJECTS = "rejects"
     ```
  3. Extend the class docstring with a short paragraph distinguishing these three from each other and from the existing relations, following the style already used for `SPECIALIZES_FROM`/`DELEGATES_TO`/`ENHANCES`/`OVERRIDES`/`REFINES` (each gets 2-4 sentences explaining what it is and, critically, what it is NOT — e.g. `IN_TENSION_WITH` is symmetric and must not be confused with `REPLACES`/supersession; `REJECTS` is directional and distinct from `REPLACES`; `RECONCILES_TENSION` only resolves a pair when BOTH sides are linked).
- **Files**: `src/doctrine/drg/models.py`
- **Parallel?**: No — do this first, everything else in this WP references these members.
- **Notes**: Exact string values matter — `data-model.md`, `contracts/tension-finding.md`, and every downstream WP's tests reference `"in_tension_with"`, `"reconciles_tension"`, `"rejects"` literally.

### Subtask T002 – Add the `RELATION_DESCRIPTIONS` registry

- **Purpose**: Single canonical authority (charter principle) for relation semantics — this is the ONE seam that both a future `describe(relation)` call site and WP08's doc-parity check read from. Do not duplicate this mapping anywhere else.
- **Steps**:
  1. In the same module, after the `Relation` class, add:
     ```python
     RELATION_DESCRIPTIONS: dict[Relation, str] = {
         Relation.IN_TENSION_WITH: "...",
         Relation.RECONCILES_TENSION: "...",
         Relation.REJECTS: "...",
     }
     ```
  2. Write real description text for each — one or two sentences, human-readable, suitable for a reference doc. Ground them in spec.md's own language (Key Entities section) rather than inventing new phrasing:
     - `IN_TENSION_WITH`: symmetric, non-transitive; two co-valid artefacts that compete; stored as one canonical edge.
     - `RECONCILES_TENSION`: an active artefact bridges both sides of a tension pair; resolves the pair only when both sides are linked.
     - `REJECTS`: directional; a good artefact names a rejected anti-pattern/smell, distinct from tension (not a competing equal) and from supersession.
  3. Scope is deliberately the three new relations only (Assumption A2 in spec.md) — do not attempt to backfill descriptions for the other 12 existing relations in this WP.
- **Files**: `src/doctrine/drg/models.py`
- **Parallel?**: No — same file as T001, do immediately after.
- **Notes**: This text becomes the source of truth WP08 mirrors into `docs/architecture/doctrine-relationships.md`. If you write something vague here ("relates two things somehow"), WP08's parity check will pass trivially and miss the point of NFR-004 (doc content must actually be useful, not just present).

### Subtask T003 – Add `ANTI_PATTERN` to `NodeKind`

- **Purpose**: `rejects` targets need a first-class kind that is never mistaken for an active paradigm (D2, already resolved in spec.md's Resolved Decisions).
- **Steps**:
  1. In `class NodeKind(StrEnum)` (currently ends with `MISSION_TYPE = "mission_type"`), add: `ANTI_PATTERN = "anti_pattern"`.
  2. Confirm `DRGNode._validate_urn`'s existing logic (`prefix != self.kind.value` check) requires no change — it's generic over `kind.value`, so `anti_pattern:<id>` URNs are accepted automatically once the enum member exists. Verify this with a quick manual test rather than assuming.
- **Files**: `src/doctrine/drg/models.py`
- **Parallel?**: Yes, relative to T004/T005 (different declarations, same file — fine to draft together, just don't let edits collide).
- **Notes**: D2's spec text also mentions a "smell" alias — this mission folds that into `tags` (T004), not a second enum member. Do not add `SMELL` as a separate `NodeKind`.

### Subtask T004 – Add `tags` field to `DRGNode`

- **Purpose**: Pydantic v2's `BaseModel` defaults to `extra="ignore"` — an authored `tags: [smell]` marker in a graph fragment (WP02) would silently vanish on load without this field. Confirmed by reading the current model: no `tags` field exists today.
- **Steps**:
  1. Add `tags: list[str] = Field(default_factory=list)` to `DRGNode`, alongside the existing `provenance: str | None = None` field.
  2. Confirm it does not interact with the URN validator (it shouldn't — it's an unrelated field).
- **Files**: `src/doctrine/drg/models.py`
- **Parallel?**: Yes, relative to T003/T005.
- **Notes**: This is the home for finer-grained marking (`smell` vs `anti_pattern`) within the single `ANTI_PATTERN` kind — WP02 will use it, WP04's validator may check it.

### Subtask T005 – Add the `ArtifactKind` member

- **Purpose**: `ArtifactKind` (`src/doctrine/artifact_kinds.py`) is a separate enum from `NodeKind` used by the activation/cascade machinery; `src/charter/cascade.py::_kind_of` resolves via `ArtifactKind(prefix)`, so this member must exist for anti-pattern URNs to resolve correctly there (verified by reading `cascade.py` — no other code change is needed in that file once this member exists).
- **Steps**:
  1. Open `src/doctrine/artifact_kinds.py`, find `class ArtifactKind(StrEnum)`, add the corresponding member (match the existing naming convention in that file exactly — check whether other members use the singular kind string or a different casing before adding `ANTI_PATTERN`/`"anti_pattern"`).
- **Files**: `src/doctrine/artifact_kinds.py`
- **Parallel?**: Yes.
- **Notes**: Do NOT touch `_SINGULAR_TO_PLURAL`/`_SINGULAR_TO_PER_KIND_FIELD` in `src/charter/drg.py` or `_SINGULAR_TO_PLURAL_KIND` in `src/charter/activations.py` or `PackContext` — WP04 owns those files and that wiring.

### Subtask T006 – Foundation tests

- **Purpose**: NFR-005 — every new branch/helper needs a focused test in the same PR.
- **Steps**:
  1. Create `tests/doctrine/drg/test_models.py` (new file) covering: all three new `Relation` values match their expected strings; `RELATION_DESCRIPTIONS` has exactly the three new relations as keys with non-empty string values; `DRGNode(urn="anti_pattern:example", kind=NodeKind.ANTI_PATTERN, tags=["smell"])` constructs without error and round-trips `tags` through a dict/JSON dump-and-reload; a URN with a mismatched prefix (e.g. `kind=NodeKind.ANTI_PATTERN, urn="directive:example"`) still raises the existing `ValueError`.
  2. Run `tests/doctrine/drg/test_nodekind_artifactkind.py` and `tests/doctrine/drg/test_kind_mapping_totality.py` — these likely assert some form of "every `NodeKind` has a corresponding mapping/handling somewhere." Extend their expectations to include `ANTI_PATTERN` rather than letting them fail or, worse, silently pass because they iterate over a hardcoded list that doesn't yet include it. Read what they actually assert before editing — do not guess.
- **Files**: `tests/doctrine/drg/test_models.py` (new), `tests/doctrine/drg/test_nodekind_artifactkind.py`, `tests/doctrine/drg/test_kind_mapping_totality.py`
- **Parallel?**: No — run after T001-T005 land.
- **Notes**: A totality/mapping test failing after you add a new enum member is a *useful* signal that some other lookup table needs the new member too — read the failure message rather than routing around it.

## Test Strategy

- Run `.venv/bin/pytest tests/doctrine/drg/ -q` after implementing. All three edited/new test files must pass.
- Run `.venv/bin/ruff check src/doctrine/drg/models.py src/doctrine/artifact_kinds.py` and `.venv/bin/mypy` on the same — zero issues (repo standard, no suppressions).

## Risks & Mitigations

- **Risk**: Writing placeholder description text in T002 (e.g. "TBD") that then ships to WP08 as the canonical text. **Mitigation**: treat T002's text as final, reviewer-facing prose, not a stub — this is explicitly called out above.
- **Risk**: `test_kind_mapping_totality.py` or `test_nodekind_artifactkind.py` has a hardcoded list of kinds that silently stays "complete" without `ANTI_PATTERN`, masking a real gap. **Mitigation**: read what each test actually asserts; if either iterates `NodeKind` members directly it will already exercise the new member — if either uses a hardcoded literal list, that list must be updated.

## Review Guidance

- Confirm the `Relation` docstring addition follows the existing per-relation explanatory style (not just three bare enum lines with no prose).
- Confirm `RELATION_DESCRIPTIONS` text is genuinely descriptive (a reviewer should be able to explain each relation to a colleague using only this text) — this directly gates whether WP08 can succeed later.
- Confirm no file outside `owned_files` was touched (especially: no `_SINGULAR_TO_PLURAL`/`PackContext`/`opposed_by`/`*.graph.yaml` edits in this WP).

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-07-21T11:08:12Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP01 --to <status>` to change WP status.
- 2026-07-21T13:01:32Z – claude:sonnet:python-pedro:implementer – shell_pid=65317 – Assigned agent via action command
- 2026-07-21T13:26:41Z – claude:sonnet:python-pedro:implementer – shell_pid=65317 – Ready for review: Relation.IN_TENSION_WITH/RECONCILES_TENSION/REJECTS + RELATION_DESCRIPTIONS + NodeKind.ANTI_PATTERN/ArtifactKind.ANTI_PATTERN + DRGNode.tags landed. tests/doctrine/drg/ 226 passed; ruff+mypy clean on changed files. Flagged for reviewer: added anti_pattern to _NON_AUGMENTATION_ELIGIBLE_KINDS (artifact_kinds.py, in-owned-file) and added one .get()-defaulted exemption to test_kind_mapping_totality.py's _EXEMPT_GET_PARTIALS (executor.py::_ARTIFACT_TO_NODE_KIND) -- both required to keep ArtifactKind internally total; verified via .get() call-site read, not guessed.
- 2026-07-21T13:27:26Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=72136 – Started review via action command
- 2026-07-21T13:39:16Z – user – shell_pid=72136 – Review passed. Verified against WP01 acceptance criteria (T001-T006) via independent diff inspection, not implementer self-report. Diff touches exactly the 5 owned_files -- no opposed_by/Contradiction/*.yaml artifact/PackContext/charter-drg-wiring content touched. T001: three Relation members added with exact string values + real per-relation docstring prose. T002: RELATION_DESCRIPTIONS has exactly the 3 new relations, non-placeholder, distinct, grounded in data-model.md's own language. T003: NodeKind.ANTI_PATTERN added; _validate_urn needs no change (verified generic over kind.value). T004: DRGNode.tags added, round-trips dict/JSON. T005: ArtifactKind.ANTI_PATTERN added + correctly folded into _PLURALS/_PATTERNS/_NON_AUGMENTATION_ELIGIBLE_KINDS (verified live: plural='anti_patterns', CHARTER_KIND_TOKENS stays at 9); charter/cascade.py::_kind_of needed no change (generic ArtifactKind(prefix) lookup, confirmed by reading it). T006: test_models.py (15 tests) + extensions to test_nodekind_artifactkind.py/test_kind_mapping_totality.py -- the totality guard is a real AST scan of all of src/, genuinely flagged executor.py::_ARTIFACT_TO_NODE_KIND as newly non-total; independently confirmed executor.py:320 reads it via .get(kind) (not table[kind]) with None falling through to 'unresolved', so the exemption is legitimate. Bulk-edit gate: read occurrence_map.yaml (target='opposed_by', code_symbols=manual_review); confirmed neither touched file contains 'opposed_by'/'Contradiction' on base or HEAD -- the real code_symbols sites are src/doctrine/{directives,paradigms,tactics}/models.py, untouched here. WP01's touches are purely additive foundation work, not an opposed_by-removal shortcut. Independent verification: .venv/bin/pytest tests/doctrine/drg/ -q -> 226 passed; ruff check (5 files) -> clean; mypy (2 files) -> no issues. Also unblocked an unrelated mission-level gate: issue-matrix.md had all 5 spec.md-referenced issues at placeholder 'unknown' (blocked approval of any WP in this mission, not a WP01 defect); filled evidence-backed verdicts from spec.md text + live gh issue state and committed separately -- flagging as a mission-planning gap (no WP owns issue-matrix.md) for operator awareness. No background processes left running.
