# Paula Patterns — Pre-Refactor Test-Smell & Coverage Audit (Mission B, write-side adoption)

**Author:** paula-patterns (profile-loaded; lens: recurring patterns / anti-patterns / test smells;
DIR-001 owning-boundary, DIR-003 decision-documented, DIR-030 test-quality-gate, DIR-032 conceptual
alignment).
**Date:** 2026-06-17
**Branch / HEAD:** `feat/write-side-context-factory-adoption` @ `1447efdce` (stacked on Mission A;
factory write-half fields verified present per `write-site-inventory.md`).
**Scope:** the 8 adopted write sites + their tests, inspected on HEAD. Goal: find the pre-existing
test smells / coverage gaps / anti-patterns to fix **BEFORE** the adoption so behavior-preservation
is *provable by deletion* and the existing tests don't fight the swap.

---

## Executive summary (the one-paragraph framing)

The adoption flips four 0-reader fragment fields to load-bearing by **deleting** hand-rolled
re-derivations (`.parent.parent` walks, `coord_branch or _current_branch`, placement joins). For that
to be *verification-by-deletion* (NFR-003), the deleted behavior must be pinned by **topology-true,
form-INdependent** characterization tests on HEAD. It mostly is **not**. The two genuinely good
topology-true tests (`test_worktree_topology.py` lock-root flip, `test_status_transition.py` contract
suite) **pin the wrong thing for adoption**: the first asserts the *private helper by name* (breaks on
deletion), the second always passes `repo_root=repo` and so **bypasses every arm the adoption changes**
— including the one latent bug FR-004 is supposed to fix. The single highest-risk finding is that the
**flattened-topology `destination_ref` divergence (write-side `_current_branch`=git HEAD vs factory
`target_branch`) — the bug FR-004 claims to fix — has ZERO witnessing test**, so the adoption would land
a *correctness change* dressed as a no-op with nothing to prove it either way (NFR-004 churn risk).
Add the characterization tests below FIRST.

---

## Findings table

| # | Smell / gap | file:line | Fix-first action (refactor OR characterization test to ADD) | De-risks | Severity | Class |
|---|-------------|-----------|-------------------------------------------------------------|----------|----------|-------|
| **S-1** | **Latent-bug FR-004 fix has NO witnessing test.** No test exercises the flattened-topology `destination_ref` arm where the write side picks `_current_branch(repo_root)` = git `HEAD` and the factory picks `meta.target_branch`. Every `_current_branch` grep-hit in `tests/` is an unrelated helper/mock. The reduction-census §6 names this the "decisive NFR-004 finding"; the suite is blind to it. | prod: `coordination/status_transition.py:291`; tests: **absent** | **ADD** a topology-true before/after test: real repo, mission with NO `coordination_branch`, operator CWD on a **lane branch ≠ target_branch** (detached/off-target HEAD); assert (a) pre-adoption write target == HEAD branch (witness the bug), (b) post-adoption == `meta.target_branch` (CWD-invariant), (c) on-disk status-event topology identical otherwise. This is the FR-004 "before/after on-disk-target idempotency" test the plan (D-2) *names but does not yet have*. | FR-004, NFR-004, NFR-006 | **CRITICAL** | coverage gap (latent-bug unguarded) |
| **S-2** | **`MissionStatus.load(surface=...)` consumer test directly CONTRADICTS FR-006.** `test_mission_status_load_consumes_carried_fragment` asserts the `surface=` param is consumed AND spies `resolve_status_surface` to assert call-count == 0. FR-006 / reduction-census §5 want this param **deleted**. The test will turn RED the instant FR-006 lands and reads as a contract ("FR-005 / #1821") — an implementer will treat it as a blocker and may abandon FR-006. | `tests/architectural/test_execution_context_parity.py:2099-2156` | **DECIDE + REFACTOR FIRST (pre-refactor):** confirm the `surface=` read-param is genuinely dead (census §5: only `agent/status.py:163,199` call `load`, neither passes `surface=`), then **delete this test in the same change that deletes the param**, OR convert it to assert the param is *gone* (negative contract). Do NOT leave it to fight FR-006 mid-mission. Also: it is a mock-spy (assertion-of-implementation) — replace with a behavioral read-dir assertion if retained. | FR-006 | **HIGH** | this-test-will-fight-the-adoption |
| **S-3** | **Three tests hard-code `PromptSourceFragment` / `prompt_source` — FR-006 deletes it.** The mission_runtime public-surface ratchet lists `"PromptSourceFragment"`; the parity suite constructs it and runs `test_promptsource_fragment_parity`; the fragment-unit test constructs it. All break on the FR-006 retirement. | `tests/architectural/test_mission_runtime_surface.py:59` (`_PUBLIC_SURFACE`); `tests/architectural/test_execution_context_parity.py:1461,1779-1801`; `tests/mission_runtime/test_context_fragments.py:21,171,180` | **REFACTOR FIRST (same change as FR-006):** remove `"PromptSourceFragment"` from `_PUBLIC_SURFACE`, delete `test_promptsource_fragment_parity` + `_PROMPT_SOURCE_FRAGMENT`, drop the `PromptSourceFragment` import/construction from `test_context_fragments.py`. These are pure surface-retirement edits — pin them in the FR-006 WP so the deletion is atomic, not a follow-on red. | FR-006 | **HIGH** | this-test-will-fight-the-adoption |
| **S-4** | **Lock-root flip tests assert the PRIVATE helper by name.** `test_emit_lock_root_*` / `test_lifecycle_lock_root_*` call `_feature_status_lock_root` / `_repo_root_for_lock` directly. FR-001 deletes those helpers (routes to `workspace.primary_root`). Even though these are *good* real-git topology tests, they form-couple to the helper symbol and will break/need rewrite on deletion. | `tests/specify_cli/coordination/test_worktree_topology.py:277-386` | **STRENGTHEN-FIRST:** before deleting the helpers, add a parallel **behavioral** assertion that does NOT name the helper — assert the *observable* lock-root invariant (two processes anchored on one mission via primary-CWD and coord-worktree-CWD acquire the **same** lock path) through the public `emit_status_transition` / lifecycle entry points. Then the private-helper tests can be retired with the public invariant still green (verification-by-deletion stays honest). | FR-001, NFR-001, SC-002 | **HIGH** | form-coupled / will-break-on-deletion |
| **S-5** | **`destination_ref` / `status_write_dir` parity tests only exercise the FLATTENED/lane arm — never the COORD arm.** `parity_repo` builds a `-lane-a` worktree and a `meta.json` with **no `coordination_branch`**. So `test_branchref_fragment_parity` and `test_status_surface_fragment_parity` prove read==read CWD-invariance but **never witness the coord-topology value** of the two fields the write path adopts. The write path's whole risk (C-007: status WRITE must stay on coord authority, never collapse to `primary_root`) is untested at the fragment level. | `tests/architectural/test_execution_context_parity.py:392-399` (lane-only fixture); `:1595-1627`, `:1632-1645` (parity tests) | **ADD** a **coord-topology** parity fixture (real `.worktrees/<slug>-coord` worktree + `coordination_branch` in `meta.json`) and assert: `status_write_dir` resolves to the **coord** feature dir (NOT `primary_root`); `destination_ref.kind == COORDINATION`; read==write resolve the *same* surface/target. This is the NFR-001 read==write equivalence gate (plan D-5) — it does not exist yet for the coord arm. | FR-003, FR-004, C-007, NFR-001 | **HIGH** | coverage gap (coord arm) |
| **S-6** | **No submodule topology fixture anywhere in the adopted surfaces (NFR-002).** NFR-002 mandates real-submodule fixtures for these surface-specific write behaviors. `resolve_canonical_root` has a submodule test (`test_resolve_canonical_root_submodule.py`), but **none of the write-site / parity / status_transition tests** construct a submodule. The adoption's "same root across primary/coord/submodule" claim (US-1, NFR-001) is unprovable for the submodule class. | (absence) — adopted-surface tests: `tests/specify_cli/coordination/test_status_transition.py`, `tests/architectural/test_execution_context_parity.py`, `tests/specify_cli/coordination/test_worktree_topology.py` | **ADD** one submodule-topology characterization test (reuse the `test_resolve_canonical_root_submodule.py` construction) that drives an adopted write path (lock-root or status emit) from a submodule checkout and asserts the resolved root == the canonical superproject root. Parameterize the NFR-001 equivalence test over {primary, coord, submodule}. | NFR-001, NFR-002 | **MEDIUM-HIGH** | coverage gap (topology class) |
| **S-7** | **R4 `store.py::_find_mission_specs_root` has ZERO direct test coverage.** The `MissionIdResolver` ancestor-scan (`candidate`/`two_up` walk) FR-001 rewrites is exercised only incidentally. Deleting it cannot be verified by a targeted green test. | prod: `status/store.py:119-130`; tests: **none** (grep `_find_mission_specs_root` / `MissionIdResolver` → ∅) | **ADD** a characterization test for `MissionIdResolver.resolve()` across the three feature-dir shapes the scan handles (`kitty-specs/<slug>`, deeper-nested, loose dir) on a topology-true fixture, so the `.parent`/`two_up` deletion → `workspace.primary_root` swap has a deletion-proof. | FR-001 | **MEDIUM** | coverage gap (untested surface) |
| **S-8** | **FR-008 lanes-dir write is tested only through MOCKED `require_lanes_json` / `write_lanes_json`.** Merge-preflight tests `monkeypatch.setattr(merge_mod, "require_lanes_json", lambda ...)`; `lane_test_utils` writes lanes.json to a plain dir. No test exercises **where** `lanes.json` lands under real coord topology (C-LANES-1: it must land on the COORDINATION branch). FR-008 routes the lanes-dir through `status_surface`/`resolve_lanes_dir`; the placement is unverified. | `tests/merge/test_merge_preflight_mission_branch.py:67,659,700,750`; `tests/lane_test_utils.py:23-24` | **ADD** a topology-true test: real coord worktree, assert `resolve_lanes_dir(<coord feature dir>)` resolves to the coord surface and the `lanes.json` write lands there (not the primary checkout). Pin the C-LANES-1 placement before FR-008 reroutes it. | FR-008, C-007 | **MEDIUM** | coverage gap (mocked-away placement) |
| **S-9** | **Private-helper non-topology smoke tests on the lock-root resolvers.** `test_feature_status_lock_root_falls_back_to_feature_dir` and `test_lifecycle_helpers_normalize_lock_roots_and_actors` assert the private helper on **non-git tmp_path dirs** (no `.worktrees/`, no ULID, no registry) — synthetic fixtures that exercise only the `parent.name != KITTY_SPECS_DIR` short-circuit, not the real topology. They also break on the FR-001 helper deletion (form-coupling). | `tests/status/test_emit.py:302-306`; `tests/status/test_work_package_lifecycle.py:460-466` | **REFACTOR/RETIRE** with S-4: fold the meaningful fallback assertion into the public behavioral test; delete the private-helper smoke tests when the helper is deleted. Do not preserve them by re-pointing at a new private name (that just re-couples). | FR-001 | **MEDIUM** | form-coupled / synthetic-fixture |
| **S-10** | **`test_status_lock_is_held_during_pipeline` couples to internal collaborator names + call ordering.** Wraps `_derive_from_lane`, `_store.append_event_verified`, `_reducer.materialize` and asserts `observed == ["derive","append","materialize"]` (assertion-of-implementation). It also passes `repo_root=lock_root`, so it never exercises `_feature_status_lock_root`'s walk. Low adoption-break risk (the explicit `repo_root` passthrough survives FR-001), but it is a form-coupled ordering assertion that drifts if the pipeline helpers are renamed. | `tests/status/test_emit.py:~390-444` | **DEFER (note only):** not on the adoption's critical path (repo_root passthrough is preserved). Flag for boy-scout: replace the call-order assertion with an outcome assertion (event persisted under lock). Do not block Mission B on it. | FR-001 (peripheral) | **LOW** | assertion-of-implementation (defer) |
| **S-11** | **P1 placement test form-couples to the literal join string.** `assert feature_dir == worktree_path / "kitty-specs" / f"test-feature-{TEST_MID8}"` pins the exact `wt / KITTY_SPECS_DIR / dir` shape FR-002 reroutes through the factory projection. It is a *value* assertion (good), so it survives **iff** FR-002 preserves the value — which is the point — but it gives false confidence if the projection silently changes the dir name. | `tests/git_ops/test_worktree.py:100-105` | **STRENGTHEN (light):** keep the value assertion; ADD an assertion that the placement came from the factory projection (e.g. the resolved `feature_dir` equals `ArtifactPlacementFragment`/`resolve_placement_only` for the same inputs) so FR-002 is proven to *route*, not just coincidentally match. Uses full ULID already (`TEST_MISSION_ID`, good). | FR-002 | **LOW-MEDIUM** | form-coupled value (acceptable, strengthen) |

---

## Recurring anti-patterns in the surfaces (the boundary view)

- **A-1 — The `repo_root=` escape hatch hides the adopted arms.** Both `test_status_transition.py`
  (every `_request` passes `repo_root=repo`) and the emit lock tests pass `repo_root` explicitly. That
  parameter **short-circuits** the exact re-derivation arms (`_repo_root_for_feature`,
  `_feature_status_lock_root`, `_current_branch`) the adoption deletes. Net effect: the most thorough
  suites in the mission **cannot witness the swap**. Pre-refactor remedy: the new characterization tests
  (S-1, S-5, S-6) must drive the paths **without** an explicit `repo_root`, forcing the derivation arm
  to run, so deletion is observable.
- **A-2 — Second-parallel-factory duplication is asserted, not consolidated.** The byte-identical
  W9≡W10 lock-root bodies (`emit.py:388-424` ≡ `work_package_lifecycle.py:55-89`) each have their own
  near-identical test (`test_emit_lock_root_*` ≡ `test_lifecycle_lock_root_*`). The duplication is
  mirrored in the tests. FR-001/D-4 collapse both to `workspace.primary_root`; the *shared* behavioral
  invariant (S-4) should be asserted once, not twice-by-helper-name.
- **A-3 — `parent.parent` fallback degradation is the only well-tested arm.** The registry-unavailable
  `feature_dir.parent.parent` fallback has clean real-trigger tests
  (`test_*_lock_root_degrades_to_parent_parent_when_registry_unavailable`). After FR-001 routes to
  `workspace.primary_root`, confirm the fragment preserves an equivalent fail-closed fallback — else the
  adoption silently drops a degradation path the tests currently guard. Verify the fragment's behavior on
  the non-git `kitty-specs` dir before deleting these.

---

## Classification roll-up (pre-refactor / strengthen-first vs defer)

**STRENGTHEN-FIRST (must land before the adoption swaps the derivation):**
- **S-1** (CRITICAL) — add the FR-004 before/after divergence test; without it the latent-bug fix is
  unprovable and NFR-004 churn is unbounded.
- **S-2, S-3** (HIGH) — the `surface=` consumer test and the `PromptSourceFragment` references will
  turn RED on FR-006; resolve them **in** the FR-006 change (delete/convert), not after.
- **S-4, S-9** (HIGH/MED) — add the public behavioral lock-root invariant before deleting the
  private helpers, so verification-by-deletion stays honest.
- **S-5** (HIGH) — add the coord-topology parity fixture; the C-007 "status write stays coord" claim
  is untested today.
- **S-6** (MED-HIGH) — add a submodule-topology characterization test; NFR-002 is unmet on the
  adopted surfaces.
- **S-7, S-8** (MED) — add the `store.py` resolver + lanes-dir placement characterization tests so
  R4 / FR-008 deletions have a green deletion-proof.
- **S-11** (LOW-MED) — light strengthen of the P1 placement test to prove routing, not coincidence.

**DEFER (boy-scout / not on the critical path):**
- **S-10** (LOW) — call-order assertion in the lock-held pipeline test; survives the adoption
  (explicit `repo_root`), flag for later outcome-based rewrite.

---

## The single highest-risk "this test will fight the adoption" finding

**S-1 + A-1 combined.** The mission's strongest write-path suite (`test_status_transition.py`) is
*structurally blind* to the adoption because it always supplies `repo_root=repo`, and the **one**
behavior the adoption changes for real — the flattened-topology `destination_ref` (`_current_branch`=git
HEAD → `meta.target_branch`) — has **no test at all**. The result is the worst case for a
"behavior-preserving" adoption: the suite stays green whether the swap is correct *or* silently moves
status events to a different branch. If Mission B lands FR-004 without first adding the S-1
before/after divergence test (and an `repo_root`-free drive path per A-1), the adoption ships an
**unwitnessed correctness change** the spec itself flags as a latent bug (reduction-census §6) — exactly
the live-evidence-over-static-fixed trap. **Add S-1 FIRST; make it RED on HEAD (witness the bug),
GREEN after the swap (witness the fix).**

Secondary: **S-2/S-3** are the literal "tests that fight the deletion" — three architectural ratchets +
a spy test that encode `prompt_source` / `surface=` as *contracts*. They must be retired *atomically*
with FR-006 or an implementer will read them as merge-blockers and back out the retirement.
