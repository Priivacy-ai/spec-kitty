# Tasks: M3 — Gate on the declared entity, not a coarse set

Derived from `plan.md` (POST-PLAN squad folded). Six work packages, single_branch, sequential.
The ADR (`docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md`) is the shared foundation (WP01);
every code WP lands its red-by-design reversal referencing it.

## Work packages

### WP01 — Policy-reversal ADR + design-decision resolution (foundation)
- **Depends**: —
- **Requirements**: FR-016, C-002
- **Deliverable**: the ADR names all four red-by-design tests + resolves the custom-family gate, memoization, path_pattern authority, node-URN predicate, and pin-and-defer decisions. (Authored at plan; WP01 verifies completeness + issue-matrix.)
- **Owns no tracker issue** (issue-verdict must not flag it as an orphan).

### WP02 — Action gate: node-URN membership + vocabulary fold (surface A, #3596)
- **Depends**: WP01
- **Requirements**: FR-001, FR-002, FR-003, FR-004, FR-007, FR-008, FR-015, NFR-001; AC-1, AC-2, AC-3, AC-7, AC-8
- **Red-first**: reverse `tests/charter/test_every_load_delivery.py::test_json_non_bootstrap_action_is_explicitly_ruled_out` + `tests/charter/test_context_schema_version_ledger.py::test_non_bootstrap_action_carries_stamped_version`; NEW single-load-count test; AC-2 node-membership companion.
- **Tracker**: #3596 + **file the `_KNOWN_ACTIONS`-fold ticket before implement** (assign HiC).

### WP03 — Governance-slot: layered per-type probe (surface B, #3598)
- **Depends**: WP01
- **Requirements**: FR-005, FR-006, NFR-002; AC-4, AC-5, AC-6
- **Red-first**: AC-4 typo hard-fail; reverse `tests/charter/test_mission_type_profiles.py::test_project_with_overrides_does_not_hard_fail_for_unknown_type` seeding a real per-type `governance-profile.yaml`; AC-5 layered fixtures.
- **Tracker**: #3598

### WP04 — Artifact filename seam: relocate + resolver + call-site conversion (surface C green, #3599)
- **Depends**: WP01
- **Requirements**: FR-009, FR-010, C-001, NFR-003; AC-9, AC-12
- **Green characterization**: AC-9 load-bearing (patch `path_pattern` → output changes); AC-12 specific-raise pins. Relocate `ExpectedArtifactManifest` (4 consumers + `TYPE_CHECKING`); consume `get_expected_artifacts` read-only.
- **Tracker**: #3599

### WP05 — Live per-type gate + stray-spec.md delete (surface C behavioral, #3597)
- **Depends**: WP04
- **Requirements**: FR-011, FR-012, FR-013; AC-10, AC-11
- **Red-first**: AC-10 `gather_artifact_presence(mission_family="<custom>")` fail-closed both directions; reverse `tests/git_ops/test_worktree.py::test_creates_empty_spec_when_no_template` (AC-11).
- **Tracker**: #3597

### WP06 — CLI guard family: resolve actual family (surface D, #3407)
- **Depends**: WP01 (sequencing-only)
- **Requirements**: FR-014, NFR-003; AC-13, AC-14
- **Red-first**: AC-13 latent-defect pin (`_check_cli_guards("review", <plan dir + unapproved WP>)`); AC-14 software-dev unchanged; verify `get_mission_type` == `_GUARD_TABLES` family key per built-in.
- **Tracker**: #3407

## Dependency summary
- WP01 → (WP02, WP03, WP04, WP06)
- WP04 → WP05
