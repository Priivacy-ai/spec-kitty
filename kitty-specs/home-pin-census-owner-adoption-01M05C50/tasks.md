# Work Packages: SPEC_KITTY_HOME Pin Census — Owner Adoption (C-011 / #3121)

**Inputs**: Design documents from `/kitty-specs/home-pin-census-owner-adoption-01M05C50/`
**Prerequisites**: plan.md (required), spec.md (user stories)

**Tests**: The acceptance tests already exist (`test_spec_kitty_home_pin_census.py`,
`test_sync_status_drain_blockers.py`). No new tests are authored; the fix must satisfy the
existing gate and the ratchet-bite proof is an executed validation step, not a committed test.

**Organization**: One work package (single-file test-isolation refactor). Subtasks `Txxx` roll
up into `WP01`.

## Subtask Format: `[Txxx] [P?] Description`

- **[P]** indicates the subtask can proceed in parallel. This mission is sequential.
- Record completion with `spec-kitty agent tasks mark-status <Txxx> --status done`.

## Path Conventions

- **Single project**: `tests/` (test-only change).

---

## Work Package WP01: Adopt canonical `SPEC_KITTY_HOME` owner in the drifting test (Priority: P1) 🎯 MVP

**Goal**: Make `test_queue_get_drain_blocked_counts_persists_through_drain_round_trip` request
the exempt `canonical_home` fixture and drop its own `SPEC_KITTY_HOME` `setenv`, so the census
gate greens with no frozen-artefact edits and the ratchet still bites.
**Independent Test**: `pytest tests/architectural/test_spec_kitty_home_pin_census.py` (all green)
+ `pytest tests/cli/commands/test_sync_status_drain_blockers.py` (all green), with `git status`
showing only the one test file changed; plus the ratchet-bite proof (inject → red, remove → green).
**Prompt**: `/tasks/WP01-adopt-canonical-home-owner.md`
**Requirement Refs**: FR-001, FR-002, FR-003, NFR-001, NFR-002, NFR-003, C-001, C-002, C-003, C-004, C-005

### Included Subtasks

T001 Refactor `test_queue_get_drain_blocked_counts_persists_through_drain_round_trip` in
`tests/cli/commands/test_sync_status_drain_blockers.py`: request `canonical_home`, delete the
`monkeypatch.setenv("SPEC_KITTY_HOME", str(tmp_path / "home"))` line, drop now-unused
`tmp_path`/`monkeypatch` params, add `del canonical_home` per repo idiom, and update the
docstring to attribute isolation to the canonical owner.
T002 Verify acceptance: run the census suite (expect 0 failures), the affected behaviour test
(expect 0 failures), `ruff` + `mypy` on the edited file (0 issues), and confirm `git status`
shows only the one file changed with no `tests/architectural/` census/anchor diff.
T003 Ratchet-bite proof: inject a spurious `setenv("SPEC_KITTY_HOME", str(tmp_path/"home"))`
in a throwaway test, confirm the census suite goes RED, then remove it and confirm GREEN.

### Implementation Notes

- `canonical_home` (`tests/conftest.py:372`) returns `None`; the idiom is
  `def test_...(canonical_home: None) -> None:` with `del canonical_home  # the ONE
  SPEC_KITTY_HOME owner (R1a #3121) pins the home` as the first body line.
- The owner sets the identical `<tmp_path>/home` and mkdirs it → the layout record is still
  absent → LEGACY. Behaviour is preserved; do NOT alter the test's assertions or its
  `begin_cutover`/`publish_project_only` flow.
- **Do not** touch `members.json`, the anchor yaml, `_home_pin_exempt.py`, census `R1a.yaml`,
  or the baseline (C-001). Do not weaken any census test (C-002).

### Parallel Opportunities

- None (single file, sequential).

### Dependencies

- None (starting and only package).

### Risks & Mitigations

- *Owner semantics divergence* → validated equivalent during research; T002 re-verifies.
- *Residual pin still counts* → T001 deletes the `setenv`; the owner never overrides a
  self-pinning test.
- *Gate-dulling* → T003 red-injection proof is mandatory (NFR-001).

---

## Dependency & Execution Summary

- **Sequence**: WP01 (single package): T001 → T002 → T003.
- **Parallelization**: none.
- **MVP Scope**: WP01 is the entire mission.

---

## Requirements Coverage Summary

| Requirement ID | Covered By Work Package(s) |
|----------------|----------------------------|
| FR-001 | WP01 |
| FR-002 | WP01 |
| FR-003 | WP01 |
| NFR-001 | WP01 (T003) |
| NFR-002 | WP01 |
| NFR-003 | WP01 (T002) |
| C-001..C-005 | WP01 |

---

## Subtask Index (Reference)

| Subtask ID | Summary | Work Package | Priority | Parallel? |
|------------|---------|--------------|----------|-----------|
| T001 | Adopt `canonical_home`, drop own `setenv` | WP01 | P1 | No |
| T002 | Verify census + behaviour test + lint/type + clean diff | WP01 | P1 | No |
| T003 | Ratchet-bite proof (inject → red, remove → green) | WP01 | P1 | No |
