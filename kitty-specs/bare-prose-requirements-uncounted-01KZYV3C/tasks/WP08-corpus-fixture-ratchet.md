---
work_package_id: WP08
title: Frozen Corpus Fixture + Non-Vacuous Ratchet + Reflexivity Close-Out
dependencies:
- WP02
- WP03
- WP05
- WP06
requirement_refs:
- FR-005
- NFR-004
- FR-009
planning_base_branch: pr/bare-prose-requirements-uncounted
merge_target_branch: pr/bare-prose-requirements-uncounted
branch_strategy: Planning artifacts for this mission were generated on pr/bare-prose-requirements-uncounted. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into pr/bare-prose-requirements-uncounted unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
- T040
- T041
- T042
- T043
- T044
phase: Phase 4 - Chokepoint & Closeout (sequential, alone, last)
history:
- at: '2026-08-14T02:50:21Z'
  actor: system
  action: Prompt authored during tasks-authoring pass (not run via /spec-kitty.tasks)
- at: '2026-08-14T00:00:00Z'
  actor: claude
  action: "Fix 1 (issue #3396 fixer pass, ledger SK-24): folded WP09 (Reflexivity — In-Flight Mission Census & PR Description, T041-T044) into this WP — WP09 was execution_mode planning_artifact with owned_files [], which finalize-tasks/compute_lanes cannot represent. WP08 absorbs WP09 because it was already the mission's last chokepoint, sequenced after every implementation WP; the fold requires no new WP-level dependency edges beyond what WP08's own prose already claimed (\"sequenced after WP05 and WP06\") plus WP09's own WP02 dependency, now added explicitly. See tracer-design-decisions.md for the full placement rationale."
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

# Work Package Prompt: WP08 – Frozen Corpus Fixture + Non-Vacuous Ratchet + Reflexivity Close-Out

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

**This WP now carries two objectives, folded together by the Fix 1 restructure (issue
#3396 fixer pass, ledger SK-24) — T037-T040 (this WP's original scope) land first;
T041-T044 (folded from WP09) run last, since the reflexivity census must audit the
*shipped* detector, not an intermediate state.**

**Objective A (T037-T040, original scope) — Frozen Corpus Fixture + Non-Vacuous
Ratchet**: Implement IC-06 (plan.md): commit the 9-spec baseline signature and the
shrink-only, **non-vacuous** ratchet test (charter Standing Order 5: concrete floor +
self-mutation test + shrink-only allowlist — "a gate-unmask cannot self-validate").

**Objective B (T041-T044, folded from WP09) — Reflexivity: In-Flight Mission Census &
PR Description**: Implement Story 6 / FR-009: state plainly what happens to every other
mission currently in flight when this change lands, including confirmation that this
mission's own spec.md does not block. This is the mission's own close-out step.

Success: (A) all four ratchet assertions pass in the committed test module, using a
signature re-verified against the then-current corpus, not copy-pasted from spec.md's
plan-time figure unverified; (B) the implementing PR's description names any currently
in-flight mission (at merge time) whose spec.md would newly block under the shipped
detector, and states the operator-facing remediation.

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
- **T041-T044 constraints, folded from WP09**: this portion audits every implementation
  WP's *shipped* state, so it must run only after WP02, WP03, WP05, and WP06 have all
  landed (see this WP's `dependencies` frontmatter, updated for the fold) — it is the
  mission's last step by design. Read plan.md's "Reflexivity (Story 6 / FR-009)"
  section — it already confirms, at plan time, that this mission's own spec.md contains
  zero bare-prose requirements (every FR/NFR/C row is a proper markdown table row).
  T042 re-confirms that live, against the shipped detector, not the plan-time claim
  alone. Per spec.md: **no code-level grandfathering is proposed** — the remediation
  for any newly-blocking in-flight mission is to rewrite its bare-prose requirements
  into a declared shape.

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

### Subtask T041 – Run the reflexivity census (folded from WP09)

- **Purpose**: FR-009's in-flight mission census, deferred to implementation/close-out
  time since the in-flight set changes daily.
- **Steps**: Run the finished, fully-wired `find_bare_prose_requirement_ids` against
  every `kitty-specs/*/spec.md` belonging to a mission not yet merged at the time this
  subtask executes. Record which ones would newly block.

### Subtask T042 – Re-confirm this mission's own spec.md (folded from WP09)

- **Purpose**: Story 6 AC2.
- **Steps**: Re-run the shipped detector against this mission's own
  `kitty-specs/bare-prose-requirements-uncounted-01KZYV3C/spec.md` and confirm it does
  not block, live — do not rely solely on plan.md's plan-time claim.

### Subtask T043 – Draft the PR description content (folded from WP09)

- **Purpose**: FR-009's operator-facing disclosure requirement.
- **Steps**: Name any newly-blocking in-flight missions found in T041, and state the
  remediation path (rewrite bare-prose requirements into a declared shape — no
  code-level grandfathering).

### Subtask T044 – Final close-out verification (folded from WP09)

- **Purpose**: NFR-003/NFR-004 close-out; confirm the mission's overall test/lint state
  before the PR is marked ready.
- **Steps**: Run the full Targeted Test Surface one final time (never the full
  `pytest tests/`):
```bash
PWHEADLESS=1 pytest \
  tests/specify_cli/test_requirement_mapping.py \
  tests/specify_cli/test_requirement_mapping_coord_surface.py \
  tests/next/ tests/specify_cli/next/ tests/runtime/ \
  tests/architectural/test_bare_prose_corpus_ratchet.py \
  tests/architectural/test_bridge_cores_import_boundary.py \
  -n 8 --dist loadfile -q
```
  Then run `ruff check` and `mypy --strict` on every file this mission touched;
  confirm zero new issues/suppressions.

## Test Strategy

- `pytest tests/architectural/test_bare_prose_corpus_ratchet.py -q` (and its teeth-test
  sibling if split into a separate file).
- This test walks the full `kitty-specs/*/spec.md` corpus at run time — confirm it does
  not require network access or write to the corpus.
- T041-T044 add no new test file; T044's own final targeted-surface run is the "test."

## Risks & Mitigations

- A vacuous, always-passing gate — this is exactly why T039/T040 exist; do not land
  this WP with only T038's two assertions.
- Snapshotting at the wrong point (before WP05/WP06 land the final shipped shape) —
  mitigated by this WP's own sequencing (last, after all other implementation WPs).
- A stale census (T041-T044, run too early, missing a mission that entered the
  in-flight set later) — mitigated by running the census as this WP's own final
  subtasks, as close to actual merge time as the mission's own execution allows.

## Review Guidance

- Confirm all four ratchet assertions are present and each is independently testable (a
  reviewer should be able to see T040's teeth test actually fail when run against a
  deliberately-stubbed detector).
- Confirm the fixture was re-verified at this WP's execution time, not copied from
  spec.md.
- Confirm the PR description actually contains the T041 census results and the T043
  remediation statement — not merely a claim that it was checked.
- Confirm T044's `ruff`/`mypy --strict` run is clean with zero new suppressions.

## Activity Log

- 2026-08-14T02:50:21Z – system – Prompt created.
- 2026-08-14 – claude – Fix 1 (issue #3396 fixer pass): folded WP09's T041-T044
  (Reflexivity — In-Flight Mission Census & PR Description) into this WP per
  operator-authorised restructure. See tracer-design-decisions.md for placement
  rationale.
