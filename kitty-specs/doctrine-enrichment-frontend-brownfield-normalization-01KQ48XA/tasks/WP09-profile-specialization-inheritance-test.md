---
work_package_id: WP09
title: Profile Specialization Tactic Inheritance Test
dependencies:
- WP06
- WP07
- WP08
requirement_refs:
- FR-008
planning_base_branch: feature/doctrine-enrichment-bdd-profiles
merge_target_branch: feature/doctrine-enrichment-bdd-profiles
branch_strategy: Planning artifacts for this feature were generated on feature/doctrine-enrichment-bdd-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feature/doctrine-enrichment-bdd-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T032
- T033
- T034
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "106942"
history:
- timestamp: '2026-04-26T08:49:24Z'
  lane: planned
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/doctrine/
execution_mode: code_change
owned_files:
- tests/doctrine/test_profile_inheritance.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

This WP requires Python test writing. Python Pedro applies TDD (write tests that fail first) and runs the full quality gate (pytest, ruff, mypy) before handoff.

---

## Objective

Add a **generic** acceptance test asserting that for any profile P that `specializes-from` a base profile B, `repo.resolve_profile(P)` includes every tactic reference that B declares. The test must:

1. Pass with zero specialization pairs in the fixture (empty repo case — NFR-004)
2. Catch breakage if the union-merge mechanism stops propagating tactic references
3. Not hardcode any specific profile ID or tactic ID

**Why `resolve_profile()` not `load_all()`**: `tactic-references` is in `_LIST_FIELDS` in `src/doctrine/agent_profiles/repository.py`. The `_union_merge` function propagates tactic refs from base to specialist via union semantics at resolution time. Specialist profiles that have no `tactic-references` of their own automatically inherit the base's refs. Specialist profiles that DO declare their own `tactic-references` get both their own AND the base's (via union). The test should use `resolve_profile()` to verify this propagation works — using `load_all()` (raw profiles) would produce false violations for profiles that correctly inherit without explicit declaration.

**Critical prerequisite reading before coding**:
- Read `tests/doctrine/test_profile_inheritance.py` for existing fixtures (particularly the `inheritance_repo` fixture pattern and how `resolve_profile` is used in existing tests)
- Read `src/doctrine/agent_profiles/repository.py`, specifically `_LIST_FIELDS` (line 134) and `_union_merge` (line 151)
- Read `src/doctrine/agent_profiles/profile.py` for the profile model's `specializes_from` and `tactic_references` fields

---

## Subtask T032 — Write the generic tactic inheritance test

**File**: `tests/doctrine/test_profile_inheritance.py` (add to existing file) or a new sibling `tests/doctrine/test_tactic_inheritance.py`

**Before writing**: Read the existing `test_profile_inheritance.py` to understand the fixture pattern. The test below is a sketch — adapt to match the actual fixture and API shape.

**Test to add**:

```python
@pytest.mark.doctrine
@pytest.mark.fast
def test_resolved_specialist_profiles_include_base_tactic_references(
    shipped_profile_repo,  # use the fixture name from existing tests — check test_profile_inheritance.py
) -> None:
    """
    Generic invariant: for every profile P that specializes-from base B,
    repo.resolve_profile(P) must include every tactic reference that B declares.

    tactic-references is in _LIST_FIELDS so resolve_profile() propagates base
    tactic refs into the resolved specialist via union merge. This test verifies
    that propagation works — it is a regression guard for the _LIST_FIELDS union
    mechanism, not a documentation-completeness assertion.

    The test does NOT hardcode any specific profile IDs or tactic IDs.
    It passes with zero specialization pairs (empty fixture).
    """
    profiles = shipped_profile_repo.load_all()

    violations: list[str] = []
    for profile_id, profile in profiles.items():
        base_id = getattr(profile, "specializes_from", None)
        if not base_id or base_id not in profiles:
            continue

        base = profiles[base_id]
        base_tactic_ids = {
            ref.id if hasattr(ref, "id") else str(ref)
            for ref in (getattr(base, "tactic_references", None) or [])
        }
        if not base_tactic_ids:
            continue

        # Resolve the specialist — union merge should include base tactic refs
        resolved = shipped_profile_repo.resolve_profile(profile_id)
        resolved_tactic_ids = {
            ref.id if hasattr(ref, "id") else str(ref)
            for ref in (getattr(resolved, "tactic_references", None) or [])
        }

        for missing_id in base_tactic_ids - resolved_tactic_ids:
            violations.append(
                f"resolve_profile('{profile_id}') is missing tactic '{missing_id}' "
                f"from base '{base_id}' — check _LIST_FIELDS union merge"
            )

    assert not violations, (
        f"Found {len(violations)} tactic inheritance violation(s):\n"
        + "\n".join(f"  - {v}" for v in violations)
    )
```

**Key implementation notes**:
- Use the existing fixture (check `test_profile_inheritance.py` for the name — likely `inheritance_repo` for tmp_path or a `shipped_profile_repo` for the real shipped dir)
- If no `shipped_profile_repo` fixture exists for the shipped profiles, create one using `AgentProfileRepository()` with the default shipped dir
- `tactic_references` may be `None`, an empty list, or a list of objects with `.id` — handle all three
- `specializes_from` may be `None` or absent — use `getattr(..., None)` safely
- The test should call `resolve_profile()` for the specialist, NOT use the raw profile from `load_all()`

---

## Subtask T033 — Verify test passes with zero specialization pairs

Create a temporary fixture test to confirm the empty-fixture behavior:

```python
@pytest.mark.doctrine
@pytest.mark.fast
def test_tactic_inheritance_passes_with_no_specialization_pairs(tmp_path: Path) -> None:
    """NFR-004: test must pass even when no profiles have specializes-from."""
    from doctrine.agent_profiles.repository import AgentProfileRepository

    shipped = tmp_path / "shipped"
    shipped.mkdir()

    # Create two profiles with no specialization relationship
    (shipped / "base.agent.yaml").write_text(
        """profile-id: base
name: Base
roles: [implementer]
purpose: Base agent
specialization:
  primary-focus: base work
tactic-references:
  - id: some-tactic
    rationale: base uses this
""",
        encoding="utf-8",
    )
    (shipped / "standalone.agent.yaml").write_text(
        """profile-id: standalone
name: Standalone
roles: [implementer]
purpose: Standalone agent with no specialization
specialization:
  primary-focus: standalone work
""",
        encoding="utf-8",
    )

    repo = AgentProfileRepository(shipped_dir=shipped)
    profiles = repo.load_all()

    # Run the same logic as the main test
    tactic_refs_by_profile = {}
    for pid, p in profiles.items():
        tactic_refs = getattr(p, "tactic_references", None) or []
        tactic_refs_by_profile[pid] = {
            ref.id if hasattr(ref, "id") else str(ref) for ref in tactic_refs
        }

    violations = []
    for pid, p in profiles.items():
        base_id = getattr(p, "specializes_from", None)
        if not base_id or base_id not in profiles:
            continue
        base = profiles[base_id]
        base_tactic_ids = {
            ref.id if hasattr(ref, "id") else str(ref)
            for ref in (getattr(base, "tactic_references", None) or [])
        }
        if not base_tactic_ids:
            continue
        resolved = repo.resolve_profile(pid)
        resolved_tactic_ids = {
            ref.id if hasattr(ref, "id") else str(ref)
            for ref in (getattr(resolved, "tactic_references", None) or [])
        }
        for mid in base_tactic_ids - resolved_tactic_ids:
            violations.append(f"resolve_profile('{pid}') missing '{mid}' from '{base_id}'")

    assert not violations  # no specialization pairs → no violations
```

**After writing**: Run this test independently to confirm it passes green.

---

## Subtask T034 — Verify test catches union-merge regression

With `resolve_profile()`, the normal case (specialist has no `tactic-references`) PASSES — union merge propagates the base tactic. The failure case this test must detect is a **regression** where `tactic-references` is accidentally removed from `_LIST_FIELDS`, causing the specialist to override (rather than union) the base's tactic refs.

The test fixture simulates this regression directly:

```python
@pytest.mark.doctrine
@pytest.mark.fast
def test_tactic_refs_are_union_merged_not_overridden(tmp_path: Path) -> None:
    """
    Regression guard: when a specialist adds its own tactic-references,
    resolve_profile() must union-merge with the base's tactic-references,
    not replace them.

    If tactic-references is removed from _LIST_FIELDS, the specialist's
    explicit tactic list replaces the base's, and the resolved profile
    would be missing the base's tactic. This test catches that regression.
    """
    from doctrine.agent_profiles.repository import AgentProfileRepository

    shipped = tmp_path / "shipped"
    shipped.mkdir()

    (shipped / "base.agent.yaml").write_text(
        """profile-id: base-impl
name: Base Implementer
roles: [implementer]
purpose: Base
specialization:
  primary-focus: base
tactic-references:
  - id: base-tactic
    rationale: base declares this
""",
        encoding="utf-8",
    )
    (shipped / "specialist.agent.yaml").write_text(
        """profile-id: specialist-impl
name: Specialist
roles: [implementer]
purpose: Specialist
specializes-from: base-impl
specialization:
  primary-focus: specialist work
tactic-references:
  - id: specialist-tactic
    rationale: specialist adds this
""",
        encoding="utf-8",
    )

    repo = AgentProfileRepository(shipped_dir=shipped)
    profiles = repo.load_all()
    resolved = repo.resolve_profile("specialist-impl")

    resolved_tactic_ids = {
        ref.id if hasattr(ref, "id") else str(ref)
        for ref in (getattr(resolved, "tactic_references", None) or [])
    }

    # Both base-tactic AND specialist-tactic must be present (union, not override)
    assert "base-tactic" in resolved_tactic_ids, (
        "base-tactic must be in resolved specialist profile — "
        "check that tactic-references is in _LIST_FIELDS"
    )
    assert "specialist-tactic" in resolved_tactic_ids, (
        "specialist-tactic must be in resolved specialist profile"
    )
```

---

## Quality Gate

After all three tests are written:

```bash
# Run only doctrine tests
pytest -m doctrine -q

# Run specifically the new test file/function
pytest tests/doctrine/test_profile_inheritance.py -v -m doctrine

# Run quality gates
ruff check tests/doctrine/test_profile_inheritance.py
mypy tests/doctrine/test_profile_inheritance.py --ignore-missing-imports
```

**Validation checklist**:
- [ ] Main test (T032) passes on the actual shipped profiles after WP06-WP08 are merged
- [ ] Empty-fixture test (T033) passes
- [ ] Failure-detection test (T034) passes (finds exactly 1 violation)
- [ ] `pytest -m doctrine -q` fully green
- [ ] No ruff or mypy errors in new test code
- [ ] No hardcoded profile IDs or tactic IDs in the main test (T032)

---

## Branch Strategy

Depends on WP06, WP07, WP08. All profiles must be complete before this test can pass against the shipped set.

```bash
spec-kitty agent action implement WP09 --agent claude
```

---

## Definition of Done

- 3 test functions added to `tests/doctrine/`
- Main test (generic invariant) passes against the full shipped profile set
- Empty-fixture test passes (NFR-004)
- Failure-detection test catches a missing tactic reference
- Full doctrine test suite green, no ruff/mypy errors

## Reviewer Guidance

- Verify the main test (T032) does NOT contain any string literals naming specific profiles or tactics
- Verify the empty-fixture test (T033) passes independently with a clean fixture
- Verify the failure-detection test (T034) fails if the violation logic is removed (i.e., the test would not pass vacuously)
- Confirm `@pytest.mark.doctrine` and `@pytest.mark.fast` are applied to all three tests
- Run `pytest tests/doctrine/ -m doctrine -v` to see all doctrine tests pass

## Activity Log

- 2026-04-26T12:58:50Z – claude:sonnet:python-pedro:implementer – shell_pid=106942 – Started implementation via action command
- 2026-04-26T13:05:27Z – claude:sonnet:python-pedro:implementer – shell_pid=106942 – 3 generic inheritance tests added; all pass including empty-fixture and union-merge regression guard; 1166 doctrine tests green
- 2026-04-26T13:05:36Z – claude:sonnet:python-pedro:implementer – shell_pid=106942 – Review passed: 3 generic tests — shipped invariant (no hardcoded IDs), empty-fixture (NFR-004 green), union-merge regression guard. All 1166 doctrine tests pass.
- 2026-04-26T13:10:41Z – claude:sonnet:python-pedro:implementer – shell_pid=106942 – Done override: Feature merged to feature/doctrine-enrichment-bdd-profiles (squash merge commit 7383936b2)
