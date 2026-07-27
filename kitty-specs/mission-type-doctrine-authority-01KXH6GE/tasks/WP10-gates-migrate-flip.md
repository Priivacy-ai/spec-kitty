---
work_package_id: WP10
title: Adapt + flip the dossier gate reader onto the doctrine tree
dependencies:
- WP09
- WP03
- WP05
requirement_refs:
- FR-007
- NFR-001
- NFR-002
- NFR-003
- NFR-004
tracker_refs:
- '883'
planning_base_branch: mission/883-mission-type-governance-profiles
merge_target_branch: mission/883-mission-type-governance-profiles
branch_strategy: Planning artifacts for this mission were generated on mission/883-mission-type-governance-profiles. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into mission/883-mission-type-governance-profiles unless the human explicitly redirects the landing branch.
subtasks:
- T052
- T053
- T054
- T055
- T056
- T057
- T058
agent: "claude:sonnet:python-pedro:implementer"
shell_pid: "1783597"
shell_pid_created_at: "1784089370.39"
history:
- at: '2026-07-14T21:00:00Z'
  actor: claude
  action: Generated via /spec-kitty.tasks (IC-07b, Lane D detachable — adapter + flip + delete copies)
agent_profile: python-pedro
authoritative_surface: src/specify_cli/dossier/
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/dossier/manifest.py
- src/specify_cli/dossier/indexer.py
- src/specify_cli/sync/namespace.py
- src/doctrine/missions/repository.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

`/ad-hoc-profile-load python-pedro` (role: implementer). Then read: [plan.md](../plan.md) §IC-07 (the
adapter + flip + delete detail), [spec.md](../spec.md) FR-007 / NFR-004 / SC-005,
[data-model.md](../data-model.md) "ExpectedArtifactManifest adapter",
[contracts/resolution-and-enforcement.md](../contracts/resolution-and-enforcement.md) C4, and the ADR
dossier-migration steps 3–5.

## Objective

Flip the dossier gate reader onto the **doctrine** tree behind a `ConfigResult → ExpectedArtifactManifest`
adapter, delete the `specify_cli/missions/*/expected-artifacts.yaml` copies, and prove reduced dependence
(NFR-004, SC-005) — user-invisibly, guarded by a **transitional** dossier-parity scaffold deleted at this
WP's end. This is a **detachable, non-blocking** lane; its final flip **may defer to slice 2 on deep
drift** (reconciliation from WP09 still lands; the deferral is recorded, never silent). It also populates
the `ResolvedMissionType.expected_artifacts` slot (out-of-map into WP03's file, sequential behind the WP03 dep).

## Context

- `repository.get_expected_artifacts:304` returns `ConfigResult` (there is **no `from_dict`** today); the
  six consumer sites expect `ExpectedArtifactManifest`. The named adapter cost is
  `ExpectedArtifactManifest.model_validate(config_result.parsed)` **plus cache preservation**.
- Reader flip target: `dossier/manifest.py:178` (`load_manifest`). Consumer sites to update:
  `dossier/indexer.py:77,130,307,359` + `sync/namespace.py:98`.
- **~29 `load_manifest` assertions** in `tests/dossier/test_manifest.py` shift the moment the reader flips
  — the reconcile-before-flip edge (WP09) + a transitional dossier-parity scaffold keep them green through
  the swap; the scaffold is deleted at the end (NFR-001 → NFR-005).
- Ordering is **strict**: reconcile (WP09) → parity scaffold green → flip → delete copies → delete scaffold.
  **Never delete a copy before the parity scaffold is green.**

## Subtask guidance

- **T052 — adapter + cache.** Add the `ConfigResult → ExpectedArtifactManifest` adapter
  (`model_validate(config_result.parsed)`) in the reader path; preserve the existing manifest cache
  semantics (cache the adapted model, not the raw `ConfigResult`).
- **T053 — transitional parity scaffold.** Add a transitional test proving software-dev's resolved
  required-artifact set is **unchanged** across the swap (reads WP09's reconciled doctrine tree). This is
  the swap-invisibility guard (NFR-001) — mark it clearly transitional; it is deleted in T058.
- **T054 — flip the reader.** Flip `load_manifest:178` to read the **doctrine** tree via
  `repository.get_expected_artifacts` through the adapter. Only after T053 is green.
- **T055 — update consumers.** Update the 5 consumer sites (`indexer.py:77,130,307,359`,
  `namespace.py:98`) to the adapted model. Update the ~29 `test_manifest.py` assertions to the new
  behaviour (not compat-shielded — C-002).
- **T056 — delete copies.** Delete `src/specify_cli/missions/*/expected-artifacts.yaml` (reconcile-before-
  flip is satisfied by WP09). **Deletions — not create_intent.** Grep-prove **0** readers reference the
  `specify_cli` copies (NFR-004/SC-005). If deep drift blocks a clean flip, **defer this deletion to slice
  2** and record the deferral explicitly (never silent) — the WP09 reconciliation still stands.
- **T057 — populate the slot.** Populate `ResolvedMissionType.expected_artifacts` in
  `charter/mission_type_profiles.py` (WP03's file) so the bundle carries gates from the now-canonical
  doctrine tree. This is a **justified out-of-map, sequential** edit behind the WP03 dep — coordinate and
  note it in the PR body.
- **T058 — delete scaffold + gates.** Delete the transitional dossier-parity scaffold (T053). `ruff` +
  `mypy` clean; complexity ≤ 15.

## Branch Strategy

Planning artifacts were generated on `mission/883-mission-type-governance-profiles`. This WP branches from
the mission base during `/spec-kitty.implement` and merges back into
`mission/883-mission-type-governance-profiles`. It depends on WP09 (reconcile) and WP03 (the bundle slot).
**This lane is non-blocking for WP12** — the join must not wait on it.

## Definition of Done

- [ ] `ConfigResult → ExpectedArtifactManifest` adapter added; manifest cache preserved.
- [ ] Transitional dossier-parity scaffold added (T053) AND deleted (T058) — **0** survives (NFR-005).
- [ ] `load_manifest:178` reads the doctrine tree; 5 consumer sites + ~29 `test_manifest.py` assertions
      updated to the new behaviour.
- [ ] `specify_cli/missions/*/expected-artifacts.yaml` deleted **or** the flip/deletion deferred to slice 2
      with the deferral explicitly recorded (never silent); **0** readers reference the deleted copies
      (NFR-004/SC-005).
- [ ] `ResolvedMissionType.expected_artifacts` slot populated (out-of-map into WP03's file, noted).
- [ ] `ruff` + `mypy` clean; complexity ≤ 15.

## Risks

- **Deleting a copy before parity is green** — strictly forbidden; T053 must be green before T054/T056.
- **Cache regression** — cache the adapted model, not the raw `ConfigResult`.
- **Silent deferral** — if the flip defers on deep drift, record it (NFR-004); never silent.
- **Merging the parity scaffold** — it is transitional; delete it in T058.

## Reviewer guidance (reviewer-renata, opus)

- Confirm the reconcile-before-flip ordering held (WP09 landed; scaffold green before flip/delete).
- Grep for any surviving reader of `specify_cli/missions/*/expected-artifacts.yaml` (expect 0, unless a
  recorded slice-2 deferral).
- Confirm the transitional scaffold is gone at HEAD and the adapter caches the adapted model.
- Confirm the `expected_artifacts` slot edit into WP03's file is minimal, sequential, and noted out-of-map.

## Activity Log

- 2026-07-15T04:22:59Z – claude:sonnet:python-pedro:implementer – shell_pid=1783597 – Assigned agent via action command
