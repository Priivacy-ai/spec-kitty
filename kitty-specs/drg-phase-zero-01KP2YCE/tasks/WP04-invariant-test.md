---
work_package_id: WP04
title: Invariant Regression Test
dependencies:
- WP00
- WP03
requirement_refs:
- FR-007
- FR-010
- NFR-003
- NFR-004
- NFR-005
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T023
- T024
- T025
- T026
- T027
agent: "claude:opus-4-6:reviewer:reviewer"
shell_pid: "90548"
history:
- date: '2026-04-13'
  author: claude
  action: created
  note: Initial WP generation from /spec-kitty.tasks
authoritative_surface: tests/charter/
execution_mode: code_change
owned_files:
- tests/charter/test_context_parity.py
- tests/charter/fixtures/accepted_differences.yaml
tags: []
---

# WP04: Invariant Regression Test

## Objective

Prove that `build_context_v2()` resolves the same governance artifacts (by URN) as the canonical `build_charter_context()` from `src/charter/context.py` for all shipped (profile, action, depth) combinations. This tests **artifact reachability parity**, not rendered-text parity. Rendered-text parity (guidelines, reference filtering, section formatting) is a Phase 1 concern when callers are switched to `build_context_v2`. This test gates Phase 1.

## Context

**The oracle**: `src/charter/context.py::build_charter_context()` is the canonical legacy path. It is the sole parity baseline. Do NOT compare against `src/specify_cli/charter/context.py` -- that is a legacy compatibility surface (rerouted in WP00).

**Test matrix**:
- **Profiles**: All shipped profiles from `src/doctrine/agent_profiles/shipped/` (~10 profiles). If profiles don't influence context assembly today (they don't -- current `build_charter_context` has no profile parameter), the test degenerates to action-only and documents this.
- **Actions**: `specify`, `plan`, `implement`, `review` (4 actions with indices). `tasks` is tested for DRG output only (no legacy baseline exists since there was no tasks action index before WP02).
- **Depths**: 1, 2, 3

**Matrix size**: 4 actions x 3 depths = 12 (with profile degeneration). Well within the 60s CI budget.

**Accepted-differences ledger**: `tests/charter/fixtures/accepted_differences.yaml`. Empty by default. Every entry must name the exact case, reason, and follow-up issue. No "expected drift" entries. If > 10% of matrix entries have differences, Phase 0 is not done.

## Branch Strategy

- **Planning/base branch**: `main`
- **Merge target**: `main`
- Execution worktrees allocated per computed lane from `lanes.json`.

## Detailed Guidance

### T023: Create test matrix generator

**Purpose**: Generate the full set of (profile, action, depth) test cases.

**Steps**:
1. In `tests/charter/test_context_parity.py`, create a fixture or helper that generates the matrix:
   ```python
   ACTIONS = ["specify", "plan", "implement", "review"]
   DEPTHS = [1, 2, 3]
   
   def generate_test_matrix() -> list[tuple[str | None, str, int]]:
       """Generate (profile, action, depth) tuples for parity testing."""
       profiles = _load_shipped_profile_ids()  # From agent_profiles/shipped/
       if not profiles or not _profiles_affect_context():
           # Profile dimension is degenerate in Phase 0
           return [(None, action, depth) for action in ACTIONS for depth in DEPTHS]
       return [(p, a, d) for p in profiles for a in ACTIONS for d in DEPTHS]
   ```
2. `_load_shipped_profile_ids()` reads `src/doctrine/agent_profiles/shipped/*.agent.yaml` and extracts IDs
3. `_profiles_affect_context()` checks whether `build_charter_context` or `build_context_v2` actually vary output by profile. In Phase 0, this returns False.
4. Document the degenerate case: "Profile dimension is degenerate in Phase 0 because neither build_charter_context nor build_context_v2 consumes profile input for context assembly. Phase 4 will make this dimension meaningful."

**Files**: `tests/charter/test_context_parity.py`

### T024: Implement artifact-reachability comparison logic

**Purpose**: Define how to compare the governance artifacts resolved by each path. This tests reachability (which artifacts are included), not rendering (how they're formatted).

**Steps**:
1. Implement `compare_artifact_reachability(legacy: CharterContextResult, v2_resolved: ResolvedContext) -> ParityResult`:
   ```python
   @dataclass
   class ParityResult:
       profile: str | None
       action: str
       depth: int
       identical: bool
       legacy_artifacts: set[str]   # Artifact URNs extracted from legacy text
       v2_artifacts: set[str]       # Artifact URNs from DRG resolution
       only_in_legacy: set[str]     # Artifacts in legacy but not DRG
       only_in_v2: set[str]         # Artifacts in DRG but not legacy
   ```
2. **Legacy artifact extraction**: Parse the rendered text from `build_charter_context()` to extract artifact identifiers:
   - Directive IDs (e.g., `DIRECTIVE_024` from lines like `    - DIRECTIVE_024: ...`)
   - Tactic IDs (e.g., `tdd-red-green-refactor` from tactic lines)
   - Convert to URN format (`directive:DIRECTIVE_024`, `tactic:tdd-red-green-refactor`)
3. **DRG artifact set**: Use `ResolvedContext.artifact_urns` directly from `resolve_context()` -- these are already URNs.
4. Compare URN sets. This deliberately ignores rendering differences (guidelines, section formatting, reference docs) which are Phase 1 concerns.
5. If URN sets differ, populate `only_in_legacy` and `only_in_v2` for the differences report.

**Files**: `tests/charter/test_context_parity.py`

**Validation**:
- [ ] Comparison extracts artifact IDs correctly from rendered text
- [ ] Identical artifacts with different formatting still pass
- [ ] Differences are clearly reported with set arithmetic

### T025: Create accepted_differences.yaml schema and loader

**Purpose**: Define the exception ledger format and loading logic.

**Steps**:
1. Create `tests/charter/fixtures/accepted_differences.yaml`:
   ```yaml
   schema_version: "1.0"
   entries: []
   ```
2. Implement `load_accepted_differences(path: Path) -> dict[tuple[str | None, str, int], AcceptedDifference]`:
   ```python
   @dataclass(frozen=True)
   class AcceptedDifference:
       profile: str | None
       action: str
       depth: int
       legacy_artifacts: frozenset[str]
       drg_artifacts: frozenset[str]
       reason: str
       follow_up_issue: str | None
       accepted_by: str
       accepted_at: str
   ```
3. The loader returns a dict keyed by `(profile, action, depth)` tuple for O(1) lookup
4. Validate each entry:
   - `reason` must not be empty
   - `reason` must not contain generic phrases like "expected drift" or "known difference"
   - `accepted_by` must not be empty
   - `accepted_at` must be a valid ISO date

**Files**: `tests/charter/fixtures/accepted_differences.yaml`, `tests/charter/test_context_parity.py`

**Validation**:
- [ ] Empty ledger loads without error
- [ ] Entries with missing reason are rejected
- [ ] Entries with "expected drift" reason are rejected
- [ ] Lookup by (profile, action, depth) works

### T026: Implement invariant test with accepted-differences integration

**Purpose**: The main test that runs the full matrix and enforces artifact-reachability parity.

**Steps**:
1. Implement the parametrized test:
   ```python
   @pytest.mark.parametrize("profile,action,depth", generate_test_matrix())
   def test_artifact_reachability_parity(profile, action, depth, tmp_path_with_charter):
       """DRG resolves the same artifact set as canonical build_charter_context."""
       repo_root = tmp_path_with_charter
       
       # Get legacy output (canonical path)
       legacy = build_charter_context(repo_root, action=action, depth=depth, mark_loaded=False)
       
       # Get DRG resolution (artifact URN set, not rendered text)
       v2_resolved = resolve_context(merged_graph, action_urn, depth=depth)
       
       # Compare artifact reachability (URN sets), not rendered text
       result = compare_artifact_reachability(legacy, v2_resolved)
       
       if result.identical:
           return  # Pass
       
       # Check accepted differences
       accepted = load_accepted_differences(ACCEPTED_DIFFS_PATH)
       key = (profile, action, depth)
       if key in accepted:
           diff = accepted[key]
           assert result.only_in_legacy == diff.legacy_artifacts - diff.drg_artifacts
           return  # Accepted difference
       
       # Unregistered difference -> fail with clear message
       pytest.fail(
           f"Artifact reachability violation for ({profile}, {action}, {depth}):\n"
           f"  Only in legacy: {result.only_in_legacy}\n"
           f"  Only in DRG: {result.only_in_v2}\n"
           f"  Register in accepted_differences.yaml if intentional."
       )
   ```
2. Add a test that enforces the threshold gate:
   ```python
   def test_accepted_differences_threshold():
       """Accepted differences must be < 10% of the test matrix."""
       accepted = load_accepted_differences(ACCEPTED_DIFFS_PATH)
       matrix = generate_test_matrix()
       threshold = len(matrix) * 0.10
       assert len(accepted) <= threshold, (
           f"Too many accepted differences ({len(accepted)}/{len(matrix)}). "
           f"Phase 0 is not done if > 10% of matrix has differences."
       )
   ```
3. Add a fixture `tmp_path_with_charter` that sets up a temporary repo root with:
   - `.kittify/charter/charter.md` (copy from project or use fixture)
   - `.kittify/charter/references.yaml` (copy or fixture)
   - `graph.yaml` (from WP02 output)
   - Doctrine shipped artifacts accessible

**Files**: `tests/charter/test_context_parity.py`

**Validation**:
- [ ] Test passes for all matrix entries (or accepted differences are registered)
- [ ] Threshold gate enforces < 10% accepted differences
- [ ] Failure messages are clear and actionable
- [ ] Test runs in < 60s

### T027: Configure CI triggers

**Purpose**: Ensure the invariant test runs on every PR that touches relevant files.

**Steps**:
1. Check the existing CI configuration (likely `.github/workflows/`)
2. Ensure the test file `tests/charter/test_context_parity.py` is picked up by the existing test runner
3. If CI uses path-based triggers, verify that changes to `src/doctrine/`, `src/charter/`, and `src/doctrine/graph.yaml` trigger the test job
4. If CI runs all tests on every PR (common in smaller projects), no additional configuration needed
5. Document the CI trigger configuration in a comment at the top of the test file

**Files**: CI configuration files (if modification needed)

**Validation**:
- [ ] Test runs in CI when doctrine/charter files change
- [ ] Test is included in the standard test suite

## Definition of Done

1. Invariant test passes for 100% of the test matrix
2. Accepted-differences ledger is empty (or < 10% with justified entries)
3. Every accepted difference has: exact case, concrete reason, follow-up issue
4. No "expected drift" entries in the ledger
5. Test runs in CI on relevant file changes
6. Full matrix completes in < 60s
7. mypy --strict clean

## Risks

- **Legacy text parsing fragility**: Extracting artifact URNs from the canonical path's rendered text requires parsing formatted lines. If the rendering format changes, the extraction regex breaks. Mitigate by keeping the extraction simple and testing it against known output.
- **Charter bundle dependency**: The test needs a `.kittify/charter/` directory with valid artifacts. The fixture setup must handle this correctly.
- **Tasks action baseline**: The `tasks` action has no legacy baseline (its action index is new in WP02). Test it for DRG output validity but exclude from parity comparison.
- **Rendered-text gaps not caught**: Phase 0 deliberately does NOT test rendered text (guidelines, reference formatting). A green artifact-reachability test does not guarantee that Phase 1's reroute will produce identical prompts. Phase 1 must add rendered-text assertions.

## Reviewer Guidance

- Verify the comparison logic compares artifact URN sets, not rendered text
- Verify legacy artifact extraction correctly parses directive/tactic IDs from rendered output
- Verify the accepted-differences loader rejects vague reasons
- Verify the threshold gate is enforced (not just advisory)
- Verify the `tasks` action is handled correctly (DRG-only, no parity check)
- Verify the test fixture provides a realistic charter environment

## Activity Log

- 2026-04-13T09:25:35Z – claude:opus-4-6:implementer:implementer – shell_pid=74075 – Started implementation via action command
- 2026-04-13T09:35:31Z – claude:opus-4-6:implementer:implementer – shell_pid=74075 – Invariant test implemented with artifact reachability comparison, 40 tests passing
- 2026-04-13T09:36:01Z – claude:opus-4-6:reviewer:reviewer – shell_pid=90548 – Started review via action command
