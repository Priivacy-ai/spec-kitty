---
work_package_id: WP01
title: Ratchet baseline + meta-test + Cat-7 per-category refactor + Cat-7 shrinkage 10→7
dependencies: []
requirement_refs:
- C-004
- C-006
- FR-110
- FR-111
- FR-112
- FR-113
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-slice-f-multi-context-extensibility-01KRX5C8
base_commit: 6751931773c7894e057b0b902337c37cea9fc079
created_at: '2026-05-18T12:12:50.872499+00:00'
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
- T007
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "2216643"
history: []
agent_profile: python-pedro
authoritative_surface: tests/architectural/
execution_mode: code_change
owned_files:
- tests/architectural/_baselines.yaml
- tests/architectural/test_ratchet_baselines.py
- tests/architectural/test_no_dead_modules.py
- src/doctrine/templates/repository.py
- src/specify_cli/glossary/prompts.py
- src/specify_cli/glossary/rendering.py
- tests/doctrine/templates/test_repository.py
- tests/agent/glossary/test_prompts.py
- tests/agent/glossary/test_rendering.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope your governance context to Python implementation before reading anything else. This loads the implementer identity, action-scoped doctrine, and Python-specific style/tool guides.

---

## Objective

Lay the burn-down foundation Slice F depends on: introduce `tests/architectural/_baselines.yaml` + a meta-test that fails on allowlist growth and warns on shrinkage, refactor `test_no_dead_modules._ALLOWLIST` into per-category frozensets so growth in Cat-7 is distinguishable from auto-discovery categories, and prove the model works in the same PR by shrinking Cat-7 from 10 entries to 7 via three concrete deletions (`doctrine.templates.repository`, `specify_cli.glossary.prompts`, `specify_cli.glossary.rendering`).

This WP **blocks Lane C and Lane D** (RR-1): new modules introduced by org-DRG, CharterScope, and workflow registry must not be permitted to grandfather themselves into the Cat-7 baseline. The meta-test must exist BEFORE Lane C/D start so any Cat-7 growth is visible as a `_baselines.yaml` diff in the same PR.

---

## Context

Per **HiC §5a.2 (binding, C-004)** the burn-down policy becomes a charter-pinned rule, not an advisory note. The architect's debrief HIGH-2 finding identified five mutable allowlists with no CI-enforced monotonic-shrinkage rule:

- `test_no_dead_modules._ALLOWLIST` (101 entries, Cat 7 = 10 grandfathered orphans)
- `test_migration_chain_integrity._KNOWN_LINE_JUMPS` (4 entries)
- `test_runtime_charter_doctrine_boundary._BASELINE_ALLOWLIST` (0 entries, capped at 2 by C-004)
- `test_auth_transport_singleton._ALLOWED_DIRECT_HTTPX_FILES` (2 entries — NO CHANGE per C-005)
- `test_compat_shims._ADAPTER_FILES` (3 entries)

The ratchet-coherence-audit §4 Gap-A6 proposed the cleanest fix: a baseline file + meta-test comparator. PRs that legitimately grow must edit the baseline, which makes growth reviewable in the PR diff.

Concrete Cat-7 shrinkage targets per spec §1.5 and DM-01KRX6N0YAFBY7MTJC0CN3D3E4:

1. `src/doctrine/templates/repository.py` — Mission 057's `CentralTemplateRepository`, 3+ years orphaned (architect's DELETE recommendation, MED-4 #1)
2. `src/specify_cli/glossary/prompts.py` — 3+ years orphaned (Q5 resolution)
3. `src/specify_cli/glossary/rendering.py` — same disposition (Q5 resolution)

References:
- [spec.md §"Absorbed remediation — HIGH-2 ratchet burn-down model"](../spec.md)
- [plan.md §1.5 Remediation 2](../plan.md)
- [contracts/ratchet-baseline-format.md](../contracts/ratchet-baseline-format.md)
- [data-model.md §7 RatchetBaseline](../data-model.md#7-ratchetbaseline-fr-110-fr-141)
- [decisions/DM-01KRX6N0YAFBY7MTJC0CN3D3E4.md](../decisions/DM-01KRX6N0YAFBY7MTJC0CN3D3E4.md)

---

## ATDD Discipline

Per **C-011** WP01 is the lane-opening WP for Lane A and lands the canonical executable contract as its FIRST deliverable (T001). The meta-test scaffold MUST be committed RED on the WP's planning base (`feat/org-doctrine-layer`) — it cannot pass yet because `_baselines.yaml` does not exist and the per-category refactor has not happened.

Red→green commit pattern (commit each as a separate commit; reviewer verifies the SHA chain):

1. **Commit A (RED, T001):** land `tests/architectural/test_ratchet_baselines.py` with assertions referencing `_baselines.yaml` that does not yet exist. Run pytest — MUST FAIL with `FileNotFoundError` or similar. Commit message MUST include `covers: Scenario 6, AC-6, AC-7` and `expected GREEN at: WP01 final commit`.
2. **Commits B..E (GREEN progression, T002-T007):** create the baseline file, refactor allowlist, delete Cat-7 entries, set Cat-7 baseline to 7.
3. **Commit F (verification):** final commit runs `pytest tests/architectural/test_ratchet_baselines.py tests/architectural/test_no_dead_modules.py -v` exit 0.

ATDD anchors per [atdd-coverage.md](../atdd-coverage.md):

- Scenario 6: `tests/architectural/test_ratchet_baselines.py::test_growing_an_allowlist_above_baseline_fails`
- AC-6: `test_baseline_file_exists_with_required_keys` AND `test_growth_fails_shrinkage_warns`
- AC-7: `tests/architectural/test_no_dead_modules.py::test_category_7_grandfathered_at_most_seven_entries`

---

## Subtasks

### T001 — Land failing-first `test_ratchet_baselines.py` meta-test

**File:** `tests/architectural/test_ratchet_baselines.py` (new)

Author the meta-test that loads `tests/architectural/_baselines.yaml` and compares against each gated test module's allowlist size. Commit this FIRST, RED, on the planning base.

Required tests:

```python
def test_baseline_file_exists_with_required_keys():
    """The baseline YAML must exist with one section per gated test."""
    # asserts presence of: test_no_dead_modules, test_migration_chain_integrity,
    # test_runtime_charter_doctrine_boundary, test_auth_transport_singleton,
    # test_compat_shims, test_example_round_trip, test_all_declarations_required

def test_growing_an_allowlist_above_baseline_fails():
    """For each ratchet, current size MUST be <= baseline; growth fails."""
    # imports each gated test module, inspects allowlist size, compares

def test_growth_fails_shrinkage_warns():
    """Shrinkage emits a pytest warning encouraging baseline edit; never fails."""

def test_category_7_grandfathered_at_most_seven_entries():
    """AC-7 binding: Cat-7 in test_no_dead_modules MUST be <= 7 at mission close."""
```

**Validation:** `pytest tests/architectural/test_ratchet_baselines.py` MUST FAIL on the planning base. Capture the failing output in the commit message.

### T002 — Create `tests/architectural/_baselines.yaml`

**File:** `tests/architectural/_baselines.yaml` (new)

Populate per data-model §7 schema. Initial values are read from HEAD-of-mission-branch readings; Cat-7 starts at `10` and is reduced to `7` in T007 after T004-T006 land.

```yaml
test_no_dead_modules:
  category_1_auto_discovered: <int>
  category_2_schema_generators: <int>
  category_3_external_entry_points: <int>
  category_4_compat_shims: <int>
  category_5_slot_holders: <int>
  category_6_internal_runtime: <int>
  category_7_grandfathered: 10   # will drop to 7 in T007

test_migration_chain_integrity:
  known_line_jumps: 4

test_runtime_charter_doctrine_boundary:
  baseline_allowlist: 0

test_auth_transport_singleton:
  allowed_direct_httpx_files: 2  # C-005 — DO NOT MODIFY this mission

test_compat_shims:
  pure_shim_files: 3

test_example_round_trip:
  legacy_contract_allowlist: 0   # WP03 populates after discovery sweep

test_all_declarations_required:
  charter_without_all: 0         # WP02 populates after sweep
  kernel_without_all: 0          # WP02 populates after sweep
```

Each entry MUST carry a leading `# justification:` comment when set above zero so reviewers see why.

### T003 — Refactor `_ALLOWLIST` into per-category frozensets

**File:** `tests/architectural/test_no_dead_modules.py`

Today the 101-entry `_ALLOWLIST` is a single monolithic frozenset. Refactor into per-category frozensets (one per documented category 1-7 from the Process Gap 2 doc). The meta-test tracks Cat-7 separately so an auto-discovered migration in Cat-1 cannot disguise a Cat-7 regression.

```python
_CATEGORY_1_AUTO_DISCOVERED: frozenset[str] = frozenset({...})
_CATEGORY_2_SCHEMA_GENERATORS: frozenset[str] = frozenset({...})
_CATEGORY_3_EXTERNAL_ENTRY_POINTS: frozenset[str] = frozenset({...})
_CATEGORY_4_COMPAT_SHIMS: frozenset[str] = frozenset({...})
_CATEGORY_5_SLOT_HOLDERS: frozenset[str] = frozenset({...})
_CATEGORY_6_INTERNAL_RUNTIME: frozenset[str] = frozenset({...})
_CATEGORY_7_GRANDFATHERED: frozenset[str] = frozenset({
    "doctrine.templates.repository",         # DELETED in T004; remove after
    "specify_cli.glossary.prompts",          # DELETED in T005
    "specify_cli.glossary.rendering",        # DELETED in T006
    # ... remaining 7 entries (existing Cat-7 minus the three above)
})
_ALLOWLIST: frozenset[str] = (
    _CATEGORY_1_AUTO_DISCOVERED
    | _CATEGORY_2_SCHEMA_GENERATORS
    | _CATEGORY_3_EXTERNAL_ENTRY_POINTS
    | _CATEGORY_4_COMPAT_SHIMS
    | _CATEGORY_5_SLOT_HOLDERS
    | _CATEGORY_6_INTERNAL_RUNTIME
    | _CATEGORY_7_GRANDFATHERED
)
```

The existing `_ALLOWLIST` aggregate remains for backward-compat with the existing dead-modules check; the meta-test introspects the per-category frozensets via `inspect.getmembers` or module-level imports.

### T004 — DELETE `src/doctrine/templates/repository.py` + its test

**Files:**
- `src/doctrine/templates/repository.py` (DELETE)
- `tests/doctrine/templates/test_repository.py` (DELETE if exists)

Run `rg "from doctrine.templates.repository|from doctrine.templates import repository|doctrine\.templates\.repository" src/ tests/` to confirm zero non-test callers (architect's verification at HEAD). The module is Mission 057's `CentralTemplateRepository`, 3+ years orphaned. Delete the file. If a sibling test exists, delete it. Remove the entry from `_CATEGORY_7_GRANDFATHERED`.

**Edge case:** if `src/doctrine/templates/__init__.py` exports the module, prune that export too.

### T005 — DELETE `src/specify_cli/glossary/prompts.py` + its test

**Files:**
- `src/specify_cli/glossary/prompts.py` (DELETE)
- `tests/agent/glossary/test_prompts.py` (DELETE)

Per DM-01KRX6N0YAFBY7MTJC0CN3D3E4: 3+ years orphaned, no operator demand, cleanest Cat-7 burn-down. Verify zero callers in `src/` before deletion. Remove the entry from `_CATEGORY_7_GRANDFATHERED`. If `src/specify_cli/glossary/__init__.py` re-exports anything from this module, prune the re-export.

### T006 — DELETE `src/specify_cli/glossary/rendering.py` + its test

**Files:**
- `src/specify_cli/glossary/rendering.py` (DELETE)
- `tests/agent/glossary/test_rendering.py` (DELETE)

Same disposition as T005. Remove from `_CATEGORY_7_GRANDFATHERED`. Verify zero non-test callers.

### T007 — Set Cat-7 baseline to 7; meta-test GREEN

**Files:** `tests/architectural/_baselines.yaml`, `tests/architectural/test_no_dead_modules.py`

After T004-T006, the per-category Cat-7 frozenset contains 7 entries. Edit `_baselines.yaml`:

```yaml
test_no_dead_modules:
  category_7_grandfathered: 7   # was 10; reduced by deleting doctrine.templates.repository,
                                #          specify_cli.glossary.prompts,
                                #          specify_cli.glossary.rendering
```

Run:

```bash
pytest tests/architectural/test_ratchet_baselines.py tests/architectural/test_no_dead_modules.py -v
```

All MUST pass exit 0. The `test_category_7_grandfathered_at_most_seven_entries` assertion is now satisfied. Capture full architectural sweep result in commit message:

```bash
PWHEADLESS=1 pytest tests/architectural/ -v
```

---

## Definition of Done

The following tests turn GREEN with this WP:

- ✅ `tests/architectural/test_ratchet_baselines.py::test_baseline_file_exists_with_required_keys` (was RED on planning base)
- ✅ `tests/architectural/test_ratchet_baselines.py::test_growing_an_allowlist_above_baseline_fails` (was RED on planning base)
- ✅ `tests/architectural/test_ratchet_baselines.py::test_growth_fails_shrinkage_warns` (was RED on planning base)
- ✅ `tests/architectural/test_ratchet_baselines.py::test_category_7_grandfathered_at_most_seven_entries` (was RED on planning base)
- ✅ `tests/architectural/test_no_dead_modules.py` — full file still passes after refactor (per-category frozensets aggregate to the same effective allowlist minus the three deletions)
- ✅ `pytest tests/architectural/ -v` — full sweep exit 0 (NFR-005)

FR coverage:

- ✅ FR-110 — `_baselines.yaml` exists with per-test, per-category baselines
- ✅ FR-111 — meta-test fails on growth, warns on shrinkage
- ✅ FR-112 — `_ALLOWLIST` refactored into per-category frozensets
- ✅ FR-113 — Cat-7 shrinks from 10 → 7 in the same PR
- ✅ C-004 / C-006 — burn-down policy is enforceable; concrete trajectory proven

AC coverage:

- ✅ AC-6 — `_baselines.yaml` exists; `test_ratchet_baselines.py` fails on growth, warns on shrinkage
- ✅ AC-7 — Cat-7 at most 7 entries (down from 10)

---

## Risks

1. **Refactor breaks the existing `_ALLOWLIST` aggregate** — the test_no_dead_modules check relies on a frozenset. Mitigation: T003 keeps `_ALLOWLIST` as the union of the per-category sets; existing call sites continue to work; only the per-category attributes are new.
2. **A Cat-7 entry has a hidden caller surfaced only via dynamic import** — `rg` cannot catch `importlib.import_module(...)`. Mitigation: T004-T006 grep for both static (`from X import`) and dynamic (`importlib.import_module("X")` / `__import__("X")`) patterns; if a dynamic caller exists, defer the deletion and pick a different Cat-7 candidate from the WIRE-OR-DELETE list.
3. **Lane C/D start before WP01 merges and grandfather new modules into Cat-7** — RR-1 in the plan. Mitigation: this is a sequencing constraint enforced by the lane graph; WP01's merge into the mission branch unblocks Lane C/D, not earlier.
4. **`test_compat_shims._ADAPTER_FILES` shrinks below 3 between WP01 and mission close (some other WP removes one)** — would trigger the WARN path. Mitigation: WARN is informational, not failing; T007 explicitly sets the baseline to the post-deletion size; any subsequent WP that triggers shrinkage edits the baseline downward in the same PR.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011, spec §"Reviewer obligation"):**

```bash
# 1. Verify the meta-test was RED on the planning base:
git checkout feat/org-doctrine-layer
pytest tests/architectural/test_ratchet_baselines.py -v
# EXPECTED: failures because _baselines.yaml does not exist OR per-category attrs missing

# 2. Verify the meta-test is GREEN on the WP's final commit:
git checkout <wp_branch>
pytest tests/architectural/test_ratchet_baselines.py tests/architectural/test_no_dead_modules.py -v
# EXPECTED: exit 0
```

If the meta-test was already green on the planning base, REJECT the WP per spec §"Reviewer obligation" — the RED commit is missing.

**Substantive review checks:**

- Confirm `_CATEGORY_7_GRANDFATHERED` contains exactly 7 entries (was 10) — count by reading the source.
- Confirm `_baselines.yaml::test_no_dead_modules.category_7_grandfathered` equals 7.
- Confirm `rg "from doctrine.templates.repository|from specify_cli.glossary.prompts|from specify_cli.glossary.rendering" src/ tests/` returns 0 matches (other than the deletions themselves).
- Confirm `tests/architectural/test_auth_transport_singleton.py::_ALLOWED_DIRECT_HTTPX_FILES` is UNCHANGED (C-005 binds — auth-transport is descoped).
- Confirm full architectural sweep: `PWHEADLESS=1 pytest tests/architectural/ -v` exit 0 (NFR-005).
- Confirm 23 fixtures pass: `pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py -v` (NFR-001).

**FR-304 commit-message check:** every commit that lands an ATDD test references the scenario/AC it covers and the expected GREEN WP. The T001 RED commit's message should read approximately: "ATDD: ratchet baseline meta-test (RED) — covers: Scenario 6, AC-6, AC-7 — expected GREEN at: WP01 final commit".

## Activity Log

- 2026-05-18T12:12:51Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2194800 – Assigned agent via action command
- 2026-05-18T12:29:22Z – claude:opus-4-7:python-pedro:implementer – shell_pid=2194800 – Lane-A foundation: ratchet baselines + per-category refactor + Cat-7 shrinkage 10->7 (deleted doctrine.templates.repository + glossary.{prompts,rendering} per Q5)
- 2026-05-18T12:30:30Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=2216643 – Started review via action command
