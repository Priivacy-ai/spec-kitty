---
work_package_id: WP08
title: Frozen Corpus Fixture + Non-Vacuous Ratchet
dependencies:
- WP03
requirement_refs: []
subtasks:
- T037
- T038
- T039
- T040
phase: Phase 4 - Chokepoint (sequential, alone, last-among-detector-work)
history:
- at: '2026-08-14T02:50:21Z'
  actor: system
  action: Prompt authored during tasks-authoring pass (not run via /spec-kitty.tasks)
agent_profile: ''
authoritative_surface: tests/architectural/
create_intent:
- tests/fixtures/bare_prose_corpus_baseline.json
- tests/architectural/test_bare_prose_corpus_ratchet.py
execution_mode: code_change
model: ''
owned_files:
- tests/fixtures/bare_prose_corpus_baseline.json
- tests/architectural/test_bare_prose_corpus_ratchet.py
role: ''
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP08 – Frozen Corpus Fixture + Non-Vacuous Ratchet

## ⚡ Do This First: Load Agent Profile

Use `/ad-hoc-profile-load`, or select via `spec-kitty agent profile list` for an
`implement`-typed WP on `tests/architectural/`.

---

## ⚠️ THIS WP IS A DECLARED CHOKEPOINT — READ BEFORE STARTING

The corpus ratchet is a declared shared CI gate. Per tasks.md's "Parallelism &
Chokepoints" section, this WP runs alone, **after every other implementation WP**
(WP02, WP03, WP05, WP06 must all have landed first) — snapshotting before the detector
reaches its final shipped shape bakes in a stale signature (plan.md's own IC-06 risk
note).

---

## Objectives & Success Criteria

Implement IC-06 (plan.md): commit the 9-spec baseline signature and the shrink-only,
**non-vacuous** ratchet test (charter Standing Order 5: concrete floor + self-mutation
test + shrink-only allowlist — "a gate-unmask cannot self-validate").

Success: all four assertions below pass in the committed test module, using a signature
re-verified against the then-current corpus, not copy-pasted from spec.md's plan-time
figure unverified.

## Context & Constraints

- Read plan.md's "The False-Positive Fixture (FR-005 / Story 4 AC3, SC-006)" section in
  full — it specifies the exact fixture shape and all four required assertions
  literally.
- Read `tests/architectural/_baselines.yaml` and
  `tests/architectural/test_ratchet_baselines.py` directly as the precedent for the
  shrink-only, committed-fixture pattern — reuse its shape (growth fails, shrinkage
  warns, per-PR edit policy requires a `# justification:` comment on growth) but adapt
  from a bare count to a **signature** (per-spec `flagged_ids` list), since a bare count
  cannot distinguish "same 9 specs still flagged" from "9 different specs now flagged."
- **Non-vacuity is load-bearing (PLAN-VERIFY-001, charter's
  `architectural-gate-non-vacuity` doctrine)**: the shrink-only subset checks alone are
  vacuous against a fully-collapsed, always-empty detector — it would pass both
  trivially. Assertions (3) and (4) below exist specifically to close that gap; do not
  skip them.
- This is deliberately **not** a live-scored percentage re-run at CI time — never
  recompute "9/368" in the test; only ask whether the flagged *set* grew and is still
  non-empty where it should be.
- **ATDD/C-011 applicability (mirrors WP02's own disclosure)**: this WP is test-only —
  it ships a new CI gate, not a production implementation. Charter C-011's literal
  "failing-first ATDD test as a separate commit before implementation" form does not
  apply in its usual shape here, because there is no separate production code change to
  pin RED against. T040's self-mutation ("teeth") test is this WP's load-bearing
  substitute: it must be run once and observed **failing** (stubbed detector → ratchet
  test fails) before this WP is marked done — the same red-then-green evidence C-011
  asks for, applied to the gate itself rather than to a production behaviour change.

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `pr/bare-prose-requirements-uncounted`;
  completed changes must merge back into `pr/bare-prose-requirements-uncounted`
  (base `op/3394-requirement-citation-scope` @ `ab15225ea`).
- **Planning base branch**: `pr/bare-prose-requirements-uncounted`.
- **Merge target branch**: `pr/bare-prose-requirements-uncounted`.

## Subtasks & Detailed Guidance

### Subtask T037 – Snapshot the fixture

- **Purpose**: A committed, re-verified baseline signature.
- **Steps**: Run the live, fully-wired `find_bare_prose_requirement_ids` against
  `kitty-specs/*/spec.md`; snapshot the 9 flagged specs' per-spec detector signatures
  into `tests/fixtures/bare_prose_corpus_baseline.json` — a JSON array of
  `{"spec_path": "kitty-specs/.../spec.md", "flagged_ids": ["FR-021", ...]}` entries.
  Re-verify against the then-current corpus at this WP's execution time (not
  spec.md's plan-time figure, copy-pasted unverified).

### Subtask T038 – Shrink-only assertions (1) and (2)

- **Purpose**: The base ratchet shape.
- **Steps**: In `tests/architectural/test_bare_prose_corpus_ratchet.py`: (1) every spec
  **not** in the fixture has an empty live result; (2) every spec **in** the fixture has
  a live `flagged_ids` result that is a subset of (or equal to) its recorded set — never
  a superset.

### Subtask T039 – Concrete-floor assertion (3)

- **Purpose**: Close the vacuity gap (1)+(2) leave open.
- **Steps**: For each of the 9 fixture specs, assert the LIVE result is **non-empty**
  (`assert live_ids`, not only the subset check).

### Subtask T040 – Self-mutation teeth test, assertion (4)

- **Purpose**: Prove the gate itself is load-bearing.
- **Steps**: Same module (or a sibling
  `test_bare_prose_corpus_ratchet_teeth.py`): monkeypatch/stub
  `find_bare_prose_requirement_ids` to always return an empty result, and assert the
  ratchet test above then **fails** (not errors, not skips).

## Test Strategy

- `pytest tests/architectural/test_bare_prose_corpus_ratchet.py -q` (and its teeth-test
  sibling if split into a separate file).
- This test walks the full `kitty-specs/*/spec.md` corpus at run time — confirm it does
  not require network access or write to the corpus.

## Risks & Mitigations

- A vacuous, always-passing gate — this is exactly why T039/T040 exist; do not land
  this WP with only T038's two assertions.
- Snapshotting at the wrong point (before WP05/WP06 land the final shipped shape) —
  mitigated by this WP's own sequencing (last, after all other implementation WPs).

## Review Guidance

- Confirm all four assertions are present and each is independently testable (a
  reviewer should be able to see T040's teeth test actually fail when run against a
  deliberately-stubbed detector).
- Confirm the fixture was re-verified at this WP's execution time, not copied from
  spec.md.

## Activity Log

- 2026-08-14T02:50:21Z – system – Prompt created.
