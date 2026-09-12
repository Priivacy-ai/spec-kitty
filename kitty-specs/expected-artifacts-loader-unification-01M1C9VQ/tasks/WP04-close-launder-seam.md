---
work_package_id: WP04
title: Close the Launder Seam
dependencies:
- WP02
- WP03
requirement_refs:
- FR-009
- FR-010
planning_base_branch: fix/expected-artifacts-loader-unification
merge_target_branch: fix/expected-artifacts-loader-unification
branch_strategy: Planning artifacts for this mission were generated on fix/expected-artifacts-loader-unification. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/expected-artifacts-loader-unification unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
phase: Phase 3 - Integration
history:
- timestamp: '2026-08-31T00:00:00Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
authoritative_surface: src/runtime/next/runtime_bridge_composition.py
create_intent:
- tests/runtime/next/test_composed_guard_launder.py
execution_mode: code_change
mission_id: 01M1C9VQZ28CFRW741WRADS6SZ
owned_files:
- src/runtime/next/runtime_bridge_composition.py
- tests/runtime/next/test_composed_guard_launder.py
tags: []
tracker_refs: []
wp_code: WP04
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer-ivan
```

---

## Objective

Close the #3412 launder **by construction** at the composed-action guard: a
malformed org manifest for a custom mission family must propagate
`MalformedManifestError` through the real guard entry point and NEVER be degraded
to `[]` (FR-009, FR-010). This is the cross-WP integration proof that the
end-to-end silent-green is gone — it consumes WP03's org-raise and WP02's
runtime-bridge re-point. **This WP is essentially test-only:** the `:504` handler
is ALREADY pinned to `UnregisteredMissionFamilyError` and gather is ALREADY
outside the try, so the behavioral fix lands in WP03 and T015 goes GREEN purely
from that propagation. WP04's real deliverables are the red-first integration
regression (T015), a durability lock test that keeps `:504` pinned (T016), a
one-line explanatory comment at `:504`, and an absent-path characterization
(T017).

## Context & Constraints

- **The seam** (`src/runtime/next/runtime_bridge_composition.py`, ~lines 486-510):
  `gather_artifact_presence(...)` is called at **`:486`, OUTSIDE** the try; the
  `try: evaluate_guards_strict(...)` opens at `:502`; `except
  UnregisteredMissionFamilyError: return []` is at `:504`. `repo_root` is threaded
  to the composed guard at `:637-638`, so the launder is live-reachable in prod.
- **Why it works structurally.** A `MalformedManifestError` raised inside
  `gather_artifact_presence` (via `_presence_filenames_for` →
  `_expected_artifacts_manifest_resolves` → the authority) fires at `:486`,
  OUTSIDE the `:502-504` try — so it propagates regardless of the `:504` handler,
  and it fires BEFORE the `blocking_artifact_names` None-vs-`frozenset` decision
  (`cores.py:724`). That is why C-002 (tri-state, #3729) and C-003 (guard-table
  short-circuit, `cores.py:721-723`) are untouched.
- **Do NOT** broaden the `:504` handler, add an `except MalformedManifestError:
  return []`, or otherwise catch-and-green the malformed type. Do NOT touch the
  tri-state or the guard-table short-circuit.
- **Red-first hygiene (C-004/D8):** T015 is `@pytest.mark.regression`, issue-pinned
  #3412, RED on `upstream/main`. T017's absent-path test is characterization.
- See `contracts/guard-seam-invariant.md` for the full invariant set.

**The exact launder chain on `upstream/main`** (spec §Confirmed Failure
Mechanism — the two-stage launder this WP closes):

> corrupt *org* custom-family manifest → `org_expected_artifacts._read_yaml_mapping`
> swallows `YAMLError`→`None` (`org_expected_artifacts.py:109-116`) →
> `_resolve_org_manifest_mapping`→`None` (`runtime_bridge_io.py:983`) →
> `_expected_artifacts_manifest_resolves`→`False` (`:998-1004`) →
> `blocking_artifact_names=None` (`:1158`) → `evaluate_guards_strict` raises
> `UnregisteredMissionFamilyError` (`runtime_bridge_cores.py:724-725`) → **caught at
> `runtime_bridge_composition.py:504` → `return []`** (silent green).

WP03 breaks stage one (the reader now raises `MalformedManifestError` instead of
swallowing to `None`); this WP guarantees stage two cannot re-launder it — the
raised type is distinct, fires at gather-time (`:486`, outside the `:502-504`
try), and the `:504` handler stays pinned so it never treats malformed as
"unregistered family".

## Subtasks & Detailed Guidance

### T015 — [RED] Integration regression: malformed org manifest propagates through the composed guard

**Purpose.** Prove the launder is closed at the real entry point, not just at the
reader.

**Steps.**
1. Construct a CUSTOM mission family plus a broken ORG `expected-artifacts.yaml`
   (real YAML-syntax error), threaded through the REAL composed-action guard
   entry point `_dispatch_via_composition` (`repo_root` threaded at
   `composition.py:637-638`) — NOT a unit-level reader call.
2. Assert the guard raises `MalformedManifestError` and the result is **NEVER
   `[]`**.
3. Mark `@pytest.mark.regression`; cite #3412; reference
   `contracts/guard-seam-invariant.md` in the docstring.
4. **Verify RED on `upstream/main`** — today the corrupt manifest laundered to
   `None` → `UnregisteredMissionFamilyError` → caught at `:504` → `return []`.

**Files.** `tests/runtime/next/test_composed_guard_launder.py` (new).

**Validation.** RED on base, GREEN after T016 (plus WP02/WP03 landed).

### T016 — Durability lock on the `:504` pin + explanatory comment (FR-009/FR-010)

**Purpose.** IMPORTANT REFRAME: `composition.py:502-504` is **already**
`except _cores.UnregisteredMissionFamilyError:` ONLY, and `gather_artifact_presence`
is **already** at `:486` OUTSIDE the try (verified in live code). There is NO
production `except`-broadening to fix — T015 goes GREEN purely from WP03's reader
raise propagating past the already-pinned `:504`. This subtask instead LOCKS that
pin so a future broadening re-reddens the suite, and documents why.

**Steps.**
1. Confirm (do not change) that `:504` catches `UnregisteredMissionFamilyError`
   only and that the malformed raise fires at gather-time (`:486`, outside the
   `:502-504` try), so it propagates before the None-vs-`frozenset` decision
   (`cores.py:724`) — no tri-state / guard-table touch (C-002/C-003).
2. Add a durability lock test (`test_504_handler_is_pinned_to_unregistered_only`)
   asserting the `:504` handler stays pinned to `UnregisteredMissionFamilyError`
   only — i.e. broadening it (adding `MalformedManifestError`) would re-redden
   T015. This is the by-construction proof for FR-010.
3. Add a one-line CODE COMMENT at `:504` stating the handler must NEVER catch
   `MalformedManifestError` (else #3412 re-opens); this is the only production
   edit in the WP.
4. If any intermediate frame between gather and the handler swallows the error,
   fix that frame — but per the live-code audit none does.

**Files.** `src/runtime/next/runtime_bridge_composition.py` (comment only);
`tests/runtime/next/test_composed_guard_launder.py` (durability lock test).

**Validation.** T015 green (from WP03 propagation, no handler change needed); the
durability lock test passes and would fail if `:504` were broadened; a corrupt
custom-family manifest surfaces `MalformedManifestError`, NOT
`UnregisteredMissionFamilyError` (Invariant I3).

### T017 — Durability characterization: absent-family still tolerant-green

**Purpose.** Prove the fix narrows the handler without breaking the legitimate
tolerant-green path, and document that broadening `:504` re-reddens T015.

**Steps.**
1. Add a characterization test: a custom family with NO manifest on any tier still
   returns `[]` via the unregistered-family path (absence unchanged).
2. Document (test docstring + PR note) that adding `MalformedManifestError` to the
   `:504` handler re-reddens T015 — this is the durability proof
   (`test_504_handler_is_pinned_to_unregistered_only` contract).
3. Tag characterization (NOT `@regression`).

**Files.** `tests/runtime/next/test_composed_guard_launder.py`.

**Validation.** Absent-family returns `[]`; the durability note is present; the
tri-state (#3729) and guard-table short-circuit (#3386/#3397/#3407) are untouched.

## Branch Strategy

Planning artifacts were generated on `fix/expected-artifacts-loader-unification`.
During `/spec-kitty.implement` the execution workspace (worktree) is allocated
per-lane from `lanes.json` by `resolve_workspace_for_wp` — do not reconstruct the
path. Completed changes merge back into `fix/expected-artifacts-loader-unification`
unless the human redirects. WP04 is the integration point — sequence it after WP02
(runtime-bridge re-point) and WP03 (org fail-loud) are both merged into the lane
base. Final PR targets upstream as a DRAFT — the operator merges.

## Definition of Done

- T015 was RED on `upstream/main` and is GREEN after (green comes from WP03's
  reader raise propagating past the already-pinned `:504` — no handler change);
  carries `@pytest.mark.regression`, cites #3412.
- `composition.py:504` still catches `UnregisteredMissionFamilyError` only (a
  one-line explanatory comment added); malformed manifests propagate and are never
  degraded to `[]`. A durability lock test keeps the pin.
- A corrupt custom-family manifest surfaces `MalformedManifestError`, not
  `UnregisteredMissionFamilyError` (I3).
- T017 proves absent-family still returns `[]`; the durability note documents that
  broadening `:504` re-reddens T015.
- Tri-state (#3729) and guard-table short-circuit (#3386/#3397/#3407) untouched.
- `ruff` + `mypy` zero-new; ≤15 complexity.

## Risks

- **Green regression = landing defect.** If T015 is not RED on base, the test is
  not exercising the real launder — re-check the entry point and `repo_root`
  threading (`:637-638`).
- **Intermediate swallow.** A `try/except` between gather and the handler could
  eat the malformed error before it reaches `:504` — audit the call chain
  end-to-end.
- **Accidental tri-state touch.** Any change near `cores.py:721-724` risks C-002/
  C-003 — keep the fix at the `:504` handler and the gather-time raise only.

## Reviewer Guidance

- Independently confirm T015 is RED on `upstream/main` through
  `_dispatch_via_composition`, and that the failure mode on base is `return []`.
- Verify the raise originates at gather-time (`:486`), outside the try, and that
  no frame between gather and `:504` swallows it.
- Confirm the `:504` handler type is unchanged in breadth (single type) and that
  the durability note is present.
- Confirm no edits near the tri-state / guard-table short-circuit.
