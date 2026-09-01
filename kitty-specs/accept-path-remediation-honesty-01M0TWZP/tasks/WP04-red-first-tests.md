---
work_package_id: WP04
title: Red-first tests including the FR-007 repro fixture
dependencies:
- WP01
- WP02
- WP03
requirement_refs:
- FR-007
- NFR-001
- NFR-002
planning_base_branch: fix/accept-path-remediation-honesty-3730
merge_target_branch: fix/accept-path-remediation-honesty-3730
branch_strategy: Planning artifacts for this mission were generated on fix/accept-path-remediation-honesty-3730. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/accept-path-remediation-honesty-3730 unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
phase: Phase 1 - Implementation
history:
- timestamp: '2026-08-25T00:00:00Z'
  agent: system
  action: Prompt generated via tasks phase authoring
agent_profile: python-pedro
authoritative_surface: tests/specify_cli/acceptance/
create_intent:
- tests/specify_cli/acceptance/test_accept_contracts_path_repro.py
execution_mode: code_change
model: ''
owned_files:
- tests/specify_cli/acceptance/test_accept_contracts_path_repro.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Deliver the single, named, runnable fixture that reproduces both #3085 defects (the
wrong-path-reported defect and the double-reporting contradiction) against a real, on-disk
mission layout invoked through real entry points — not hand-built result objects — satisfying
the maintainer's binding triage requirement (#3085, 2026-08-02: "add a focused repro/
acceptance fixture ... before implementation"). Depends on WP01+WP02+WP03 all landing first
so this fixture asserts against the fully post-fix world.

## Context

**Named deliverable (not folded anonymously into "add tests")**: a new test file —
`tests/specify_cli/acceptance/test_accept_contracts_path_repro.py` (matching spec.md's
Independent Test paragraph's own suggested filename shape). This is not optional or
substitutable by the per-WP revert tests already written in WP01/WP02/WP03 — it is the single
integration-level fixture a reviewer can run standalone to prove both defects existed and are
fixed, per User Story 4.

**Concrete construction**: build a real, on-disk `software-dev` mission layout under
`tmp_path` — a real `kitty-specs/<slug>/` directory tree with `spec.md`/`plan.md`/`tasks.md`
present and `contracts/` **absent** — mirroring `software-dev/mission.yaml`'s actual declared
conventions (`artifacts.optional` includes `contracts/`, `paths.deliverables` also declares
`contracts/` — the same dual declaration that produces the #3085 defect). Invoke
`validate_mission_paths` and `collect_feature_summary` (or the `accept` CLI command via
`CliRunner`) **directly** — never a hand-built `PathValidationResult`/`AcceptanceSummary`
stand-in. This is FR-007's explicit constraint: reverting WP1-WP2's code changes must
necessarily flip this fixture's own pass/fail result, which is only guaranteed if the fixture
exercises the real functions against real on-disk state, not a mock.

The fixture's docstring must name: this mission
(`accept-path-remediation-honesty-01M0TWZP`), both source issues (#3730, #3085), and the two
specific functions under test (`validate_mission_paths`, `collect_feature_summary`) —
satisfying the triage comment's "owner/dependency links" requirement without requiring a
reviewer to read the implementation diff first.

**Three assertions, one fixture** (both defects, per Story 4's Acceptance Scenarios):

1. The reported missing-path/suggestion string equals the resolved
   `kitty-specs/<slug>/contracts/` path, not the bare `contracts/` token (fails pre-WP1,
   passes post-WP1).
2. `"contracts"` (normalized) appears in exactly one of `AcceptanceSummary.optional_missing` /
   the rendered `path_violations` — never both (fails pre-WP2, passes post-WP2).
3. A `--json`-mode assertion (CLI invocation with `--json`) that independently asserts
   "exactly one of `optional_missing`/`path_violations`" **on the parsed JSON payload's own
   `optional_missing`/`path_violations` keys** — the same property Assertion 2 checks on the
   `AcceptanceSummary` object, applied directly to the JSON dict's own values (FR-002 Edge Case
   / Scenario 4 of User Story 2). This is deliberately NOT "assert the JSON matches the
   object-level result": since `AcceptanceSummary.to_dict()`
   (`acceptance/__init__.py:430,432`) is a direct read of the same `optional_missing`/
   `path_violations` attributes Assertion 2 already reads, a JSON-vs-object comparison would
   pass identically whether or not WP2's dedup fix is present (both sides would be wrong the
   same way on a revert) — it would not be a genuine red-first test for FR-002/Scenario 4. By
   computing the exactly-one-of check directly on the JSON dict's own keys, Assertion 3
   becomes independently falsifiable and flips red→green in lockstep with Assertion 2 on a
   WP2 revert, since both now read the same underlying fields but each is its own check.
   Note: the JSON key is `optional_missing`
   (`AcceptanceSummary.to_dict()`, `acceptance/__init__.py:430`), not `missing_optional` —
   spec.md's own Acceptance Scenario 4 uses `missing_optional` as loose prose, but the actual
   field/key to assert on is `optional_missing`. This naming slip in spec.md is out of scope
   to fix here (spec.md is gated PASSED); just use the correct field name in the test.

   **>>> DEVIATION FROM plan.md (TASKS-FRESH-002) <<<**
   plan.md's "Assertions" list, item 3 (plan.md's WP4 subsection, lines 723-726), reads
   **verbatim**:

   > 3. A `--json`-mode assertion (CLI invocation with `--json`) confirming
   >    `optional_missing` and `path_violations` in the JSON payload reflect the same
   >    single-severity resolution as the console/summary-object path — no format-specific
   >    drift (FR-002 Edge Case / Scenario 4 of User Story 2).

   That is a **JSON-vs-object comparison**: check that the JSON payload's values match
   Assertion 2's `AcceptanceSummary`-object-level result. **This WP's Assertion 3, above,
   deliberately does NOT do that.** Instead it asserts directly on the parsed JSON payload's
   own `optional_missing`/`path_violations` keys ("exactly one of the two is non-empty"),
   independent of the object-level result. Reason: a literal JSON-vs-object comparison is
   structurally non-falsifiable here — `AcceptanceSummary.to_dict()`
   (`acceptance/__init__.py:430,432`) is a direct read of the same attributes Assertion 2
   already reads, so the two sides would be wrong identically on a WP2 revert and the
   comparison would never go red (TASKS-VERIFY-001, confirmed). Per this mission's CRITICAL
   CONSTRAINT, plan.md is not edited to match this correction — this note is the flag so a
   reviewer diffing plan.md's literal Assertions-item-3 text against this WP file's Assertion
   3 (above) sees the difference and its rationale without opening plan.md, and reads this as
   a deliberate, tracked correction rather than unflagged drift from the settled plan.md
   contract.

**Reversibility check** (part of this WP's own validation, not a separate step): confirm by
inspection/local `git stash` of WP1+WP2's diff that this fixture's first two assertions flip
from pass to fail — this is what makes it a genuine repro, not incidental new coverage.
Assertion 3 flips from pass to fail on the same pre-WP2 revert as Assertion 2 (T015 covers
both explicitly). Record the confirmation in this WP's implementation notes handed to review.

**This WP has no single "revert test" of its own in the WP1/2/3 sense** — it *is* the
verification layer; its own correctness is validated by the reversibility check rather than a
further meta-test.

## ⚡ Subtask T013: Build the real on-disk `software-dev` mission layout and invoke real entry points

**Purpose**: Establish the fixture's foundation — a genuine mission directory tree and direct
calls into `validate_mission_paths`/`collect_feature_summary` (or the `accept` CLI), with no
hand-built result stand-ins.

**Steps**:
1. Create `tests/specify_cli/acceptance/test_accept_contracts_path_repro.py`.
2. Write the module/test docstring naming: mission slug
   `accept-path-remediation-honesty-01M0TWZP`, issues `#3730` and `#3085`, and the functions
   under test `validate_mission_paths` and `collect_feature_summary`.
3. Under `tmp_path`, construct a real `software-dev`-shaped mission tree:
   - A repo root (`project_root`) with whatever minimal structure `collect_feature_summary`
     needs to run without erroring on unrelated checks (check existing acceptance test
     fixtures in `tests/specify_cli/acceptance/test_acceptance_cores.py` or similar for the
     established fixture-building convention — reuse existing test helpers/fixtures if
     present rather than reinventing).
   - `kitty-specs/<slug>/` containing real `spec.md`, `plan.md`, `tasks.md` files (minimal
     valid content is fine).
   - `kitty-specs/<slug>/contracts/` **absent** (the directory must not exist on disk).
4. Load or construct a real `Mission`/`MissionConfig` for `software-dev` (use the actual
   canonical loader, e.g. `get_mission_for_feature` or the equivalent used elsewhere in the
   test suite — per C-003, this must resolve against
   `src/specify_cli/missions/software-dev/mission.yaml`, the canonical runtime tree, not
   `packs/built-in/missions/`).
5. Invoke `validate_mission_paths(mission, project_root, feature_dir=feature_dir)` directly
   for the path-level assertion, AND `collect_feature_summary(...)` (or the `accept` CLI via
   `CliRunner.invoke`) directly for the summary-level assertions — both real entry points, no
   hand-built `PathValidationResult`/`AcceptanceSummary`.

**Files**: `tests/specify_cli/acceptance/test_accept_contracts_path_repro.py` (new).

**Validation**: The fixture setup itself runs without error against pre-fix code (only the
assertions in T014 should fail pre-fix, not the setup/invocation).

---

## ⚡ Subtask T014: Implement the three assertions

**Purpose**: Encode both #3085 defects plus the `--json` consistency check as concrete,
checkable assertions.

**Steps**:
1. **Assertion 1 (wrong-path defect)**: from the `validate_mission_paths` call's
   `PathValidationResult`, assert the reported missing-path/suggestion string equals the
   resolved `kitty-specs/<slug>/contracts/` path (matching WP1's `resolved` computation for
   this fixture's directory layout), and does **not** equal or contain only the bare
   `contracts/` token.
2. **Assertion 2 (double-reporting defect)**: from the `collect_feature_summary` (or CLI)
   call's `AcceptanceSummary`, assert `"contracts"` (normalized — strip slashes/whitespace)
   appears in exactly one of `AcceptanceSummary.optional_missing` / the rendered
   `path_violations` text — never both.
3. **Assertion 3 (`--json` internal consistency, independently falsifiable)**: invoke the
   `accept` CLI with `--json` (via `CliRunner`) on the same fixture and parse the JSON payload.
   Assert, directly on the parsed dict's own `optional_missing` and `path_violations` keys —
   **not** by comparing them to Assertion 2's object-level result — that `"contracts"`
   (normalized) appears in exactly one of the JSON's `optional_missing` / `path_violations`
   lists, never both. This mirrors Assertion 2's check but computes it independently from the
   JSON payload's own values, so Assertion 3 can genuinely fail on its own (e.g. if a WP2
   revert leaves `"contracts"` in both JSON fields simultaneously) rather than being
   structurally guaranteed to pass whenever Assertion 2 passes.
4. Ensure all three assertions are in the same test file (per FR-007's "one fixture,
   both defects" framing), whether as one test function or several closely-related ones in the
   same module — the key requirement is they share the same on-disk fixture construction and
   real entry-point invocation, not hand-built stand-ins.

**Files**: `tests/specify_cli/acceptance/test_accept_contracts_path_repro.py`.

**Validation**: Run the file against current (post-WP1/WP2/WP3) code — all three assertions
pass (SC-004: "passes on post-fix code").

---

## ⚡ Subtask T015: Perform and record the reversibility check

**Purpose**: Prove this is a genuine repro (fails on pre-fix code), not incidental new
coverage that happens to pass — the binding part of FR-007/SC-004.

**Steps**:
1. Confirm, by inspection of WP1's and WP2's diffs (or via a local `git stash` of those
   changes if still applied to the working tree, or by temporarily reverting the relevant
   lines), that Assertion 1 (T014) fails against pre-WP1 code — the reported string is the
   bare token, not the resolved path.
2. Confirm Assertion 2 (T014) fails against pre-WP2 code (with WP1 applied but WP2 not) —
   `"contracts"` appears in both `optional_missing` and `path_violations` simultaneously.
3. Confirm Assertion 3 (T014) **also** fails against the same pre-WP2 state checked in step 2
   — the parsed `--json` payload's own `optional_missing` and `path_violations` keys both
   contain `"contracts"` simultaneously. This is the assertion that makes Assertion 3 a
   genuine red-first test rather than one structurally guaranteed to pass whenever Assertion 2
   passes (TASKS-VERIFY-001): since Assertion 3 now checks the JSON payload's own fields
   directly instead of comparing to Assertion 2's result, it must be confirmed to fail on its
   own against this pre-fix state, not merely assumed to fail because Assertion 2 does.
4. Record this confirmation explicitly in this WP's implementation notes/PR description handed
   to review — state which assertion was checked against which pre-fix state and the observed
   failure mode (e.g. "Assertion 1 failed pre-WP1 with reported string `'contracts/'` instead
   of `'kitty-specs/<slug>/contracts/'`; Assertion 2 failed pre-WP2 with `'contracts'` present
   in both `optional_missing` and `path_violations`; Assertion 3 failed pre-WP2 with the same
   `'contracts'` duplication present in both keys of the parsed `--json` payload"). Do not
   merely assert "reversibility checked" without the concrete before/after evidence.
5. Do not modify WP1/WP2/WP3's already-landed code as part of this check — this is a read-only
   verification (inspection, or a scratch local revert that is not committed), not a
   remediation step.

**Files**: none (verification/documentation activity — record findings in the WP's
implementation notes, not a new test file).

**Validation**: The recorded before/after evidence for all three assertions, demonstrating
genuine red-to-green transitions tied to WP1's and WP2's specific changes respectively (with
Assertion 3 flipping alongside Assertion 2 on the same pre-WP2 state, per step 3).

## Definition of Done

- T013-T015 all recorded via `spec-kitty agent tasks mark-status <Txxx> --status done`
  (event-sourced status).
- `test_accept_contracts_path_repro.py` exists, is runnable standalone
  (`pytest tests/specify_cli/acceptance/test_accept_contracts_path_repro.py -v`), and passes
  on current (post-WP1/WP2/WP3) code.
- The fixture invokes `validate_mission_paths` and `collect_feature_summary` (or the `accept`
  CLI) directly against a real on-disk mission layout — confirmed by reading the test file, no
  hand-built `PathValidationResult`/`AcceptanceSummary` stand-in anywhere in it.
- The reversibility check (T015) is performed and its before/after evidence is recorded in
  this WP's implementation notes.
- The fixture's docstring names the mission slug, both issues (#3730, #3085), and both
  functions under test.
- The three SC-005 pinned tests remain green, unmodified (NFR-002) — this WP adds a new test
  file and does not touch any existing test.
- `ruff`/`mypy` clean on the new test file; the `patch()` target-string validation CI gate
  (`ruff check src tests --select TID251` and the `patch()` target-string check) passes if the
  fixture uses any `unittest.mock.patch` — verify any patch target string references a real,
  currently-importable symbol.
- Full baseline re-run: `pytest tests/specify_cli/acceptance/ tests/specify_cli/cli/commands/test_accept_warnings_render.py tests/agent/test_validators_unit.py tests/characterization/test_trio_json_envelope.py -q`
  completes with 0 failed, with the passed count now >= 180 (accounting for this WP's new test
  file), per plan.md's "Baseline honesty" section — this is the mission's final gate before
  FR-007's fixture is complete, so this re-run confirms the full committed accountability
  surface, not just the three named pinned tests above.

## Risks

- **Fixture setup complexity**: building a real on-disk mission layout with a genuinely
  loadable `Mission`/`MissionConfig` can be more involved than a hand-built stand-in — this is
  the explicit cost FR-007 accepts in exchange for genuine reversibility. Reuse existing
  fixture-building helpers from `tests/specify_cli/acceptance/` rather than reinventing from
  scratch, to reduce this risk.
- **C-003 canonical-tree confusion**: the fixture must load `mission.yaml` from
  `src/specify_cli/missions/software-dev/mission.yaml` (the tree `accept` actually reads at
  runtime), not `packs/built-in/missions/` (the doctrine-resolver tree, which carries an
  identical-looking but non-authoritative copy). Use the same loader/helper the production
  code path uses (e.g. via `get_mission_for_feature`), not a manual YAML read, to avoid
  accidentally pointing at the wrong tree.
- **spec.md's `missing_optional` vs. `optional_missing` naming slip**: spec.md's Acceptance
  Scenario 4 prose says "`missing_optional`" but the actual field/JSON key is
  `optional_missing` — use the correct field name in the test; do not propagate the prose slip
  into the assertion.
- **owned_files overlaps (full accounting, re-derived from `wps.yaml` live)**: this WP's single
  owned file (`tests/specify_cli/acceptance/test_accept_contracts_path_repro.py`) falls inside
  the `tests/specify_cli/acceptance/**` glob both WP01 and WP02 also own. Deliberate — WP01,
  WP02, WP03, and WP04 form a strict linear dependency chain (WP01→WP02→WP03→WP04) and are
  never worked concurrently, so the no-overlap convention for parallel-write collisions does
  not apply. No overlap with WP03 (WP03 owns `tests/specify_cli/cli/commands/**` and
  `tests/agent/test_validators_unit.py`, neither of which this WP touches).

## Reviewer Guidance

- Confirm the fixture genuinely does not hand-build a `PathValidationResult`/
  `AcceptanceSummary` anywhere — this is FR-007's explicit, checkable constraint.
- Confirm the reversibility check's before/after evidence is concrete (actual observed
  values), not a bare assertion that it was "checked."
- Confirm the fixture's docstring is legible as a repro of the exact #3085 defects without
  reading the implementation diff (Scenario 3 of User Story 4) — read it cold and see if the
  mission/issue/function context is discoverable.
- Confirm this WP did not touch any of WP1/WP2/WP3's already-landed production code — it is
  purely additive (one new test file).
- Confirm Assertion 3 computes its exactly-one-of check directly on the parsed `--json`
  payload's own `optional_missing`/`path_violations` keys, and does **not** compare the JSON
  output to Assertion 2's object-level result — a comparison-based check would be structurally
  guaranteed to pass regardless of WP2's correctness, since `to_dict()` is a direct read of
  the same object attributes Assertion 2 already reads (TASKS-VERIFY-001). Confirm T015
  recorded Assertion 3 genuinely failing against the pre-WP2 state, not merely assumed to fail
  because Assertion 2 does.
- Confirm the `--json` assertion (Assertion 3) genuinely parses the CLI's JSON output rather
  than re-deriving expected values independently of what the CLI actually emits.

---

Run `spec-kitty agent action implement WP04 --agent claude` to begin implementation.
