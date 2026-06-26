# Implementation Plan: Teardown-Surface Hardening + Retrospective Durable Home

**Branch**: `fix/3.2.3-coord-surface-regressions` | **Date**: 2026-06-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/retrospective-durable-home-01KVYM1W/spec.md`
**Tracker**: #2119 (driver) · #1890 folded · parent #1878 · cluster #1716/#1868 · RELATE #2125 · #2123 (DONE-by-merge #2129, regression-reference)

## Summary

Harden one surface — the coordination/lane **teardown path** and the **terminal-artifact placement**
it destroys — as **ONE slice in one spec / one ADR / one teardown bounded-context**.
Re-home `retrospective.yaml` onto the durable PRIMARY mission folder via a new `RETROSPECTIVE` artifact
kind (the write-surface twin of the planning-read SSOT), consolidate the **six** divergent home-resolution
sites (5 coord-aware resolvers + 1 hardcoded payload) onto one primary-anchored authority — modeled on the
topology-blind `primary_feature_dir_for_mission` gated by `is_primary_artifact_kind`, NOT the topology-aware
`resolve_status_surface` — extract one shared coordination-teardown seam with a **persist-before-destroy**
invariant (persist OUTSIDE the best-effort swallow), repoint the phantom recovery command (#1890), and sweep
adjacent dead code. One ADR records the placement + teardown contract.

The **lane-worktree exact-set (#2123)** is **DONE-by-merge (#2129)** and out of code scope (regression-reference).
**All sequencing-gate PRs have merged** to the base (`upstream/main e36547461`: #2121, #2129, #2133, #2114,
#2134, #2135), so there is **no open-PR gate** — the whole mission plans as ONE slice. #2133's decomposition
relocated the merge-path teardown into `merge/executor.py:795` but **left the `--abort` teardown in
`cli/commands/merge.py:270`**; the three live teardown sites span two packages + `mission_type`, so the FR-004
seam lives in `coordination/`. (A separate #2115/Ray-port planning-read-surface effort is owned by other
maintainers and is OUT of #2119 scope — neither dependency nor foundation.)

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: existing `specify_cli` surfaces — `src/mission_runtime/artifacts.py`
(`MissionArtifactKind`@`:24` / `_PRIMARY_ARTIFACT_KINDS`@`:85` / `is_primary_artifact_kind`@`:220`, shared
package), `missions/_read_path_resolver` (**`primary_feature_dir_for_mission`@`:1212`** — the topology-blind
placement primitive, STAYS handle-blind; FR-011 canonicalizes in its CALLERS, **reusing the existing
`_canonicalize_bare_modern_handle`@`:418` / `_canonicalize_handle`@`:467` identity machinery, NOT reinvented**;
seam-internal canonicalization is infinite recursion, `:418`→`:454`; `resolve_status_surface` is read-side
only, NOT the write exemplar; the READ entry point `resolve_planning_read_dir`@`:1244` calls the blind
primitive at `:1306` and is where WP01 adds the canonicalization),
`retrospective/*`, `post_merge/retrospective_terminus.py`,
`runtime/next/_internal_runtime/retrospective_terminus.py`, `cli/commands/merge.py`,
`cli/commands/mission_type.py`. No new third-party dependency.
**Storage**: filesystem — `kitty-specs/<slug>/retrospective.yaml` (tracked, git); coordination state in `.worktrees/`.
**Testing**: `pytest` with **live coordination-topology fixtures** — a real materialized coord worktree
that genuinely diverges from primary (coord surface lacks `meta.json`/`lanes.json`). Stubbed-resolver /
bare-slug / flattened fixtures are rejected (NFR-002). Destroy-step fault injection for the
persist-before-destroy proof; an enumerating structural test for the single-authority claim; a repo-wide
grep-guard for the phantom string.
**Target Platform**: Linux/macOS dev + CI.
**Project Type**: single (CLI).
**Performance Goals**: N/A (correctness mission).
**Constraints**: `maxCC ≤ 15` (ruff C901) on every touched function; no resolver primitive invented;
retro home stays PRIMARY-partition tracked (not `.kittify`); **no open-PR gate** — all sequencing PRs
(#2121/#2129/#2133/#2114/#2134/#2135) have merged to the base (`e36547461`).
**Scale/Scope**: ~8 source modules, 1 handle-safe-seam canonicalization (FR-011 foundation), 1 new kind
member, 6 home-resolution sites, 1 shared seam extraction (landing in `coordination/`, since the 3 live
teardown sites span `merge/executor.py` + `cli/commands/merge.py` + `mission_type.py`), the filename hoist
(8 literals + 2 `.tmp` f-strings across 6 `.py` files), **11 FRs (1 struck)**, 1 ADR.
**WP count: ~7 in ONE slice** (FR-011 foundation WP first).

## Charter Check

*GATE: surface-authority / SSOT discipline (compact charter).* This mission extends the existing
kind-aware artifact-surface partition by exactly one member (`RETROSPECTIVE`) and adopts the existing
authority — it does **not** invent a parallel resolver (unification-not-parity). The FR-011 (#2136)
handle-safety work likewise **reuses the existing `_canonicalize_bare_modern_handle` / `_canonicalize_handle`
identity machinery in the CALLERS of the blind `primary_feature_dir_for_mission` primitive** (the READ leg
`resolve_planning_read_dir:1306` + the WRITE sites; the primitive stays blind — seam-internal canon is
recursion, `:418`→`:454`; no parallel identity resolver, no silent fallback — WP07/C-009), strengthening the
single PRIMARY authority rather than forking it. Consistent with the
read-twin SSOT (#1716/#2106) and the kind-aware placement ADR (#2101/#2090). No conflict. PASS.

## Project Structure

### Source Code (repository root) — touched surfaces

```
src/mission_runtime/
  artifacts.py                                       # IC-01: + RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS (enum@:24, partition@:85, gate is_primary_artifact_kind@:220) (shared pkg)
src/specify_cli/
  missions/_read_path_resolver.py                    # IC-00 (FR-011/#2136): caller-canonicalize bare handle in resolve_planning_read_dir's PRIMARY leg@:1306 (reuse _canonicalize_bare_modern_handle@:418/_canonicalize_handle@:467; no-silent-fallback). primitive primary_feature_dir_for_mission@:1212 STAYS handle-blind (seam-internal canon = infinite recursion: :418 calls the primitive at :454). IC-01: placement authority (model on the blind @:1212, NOT resolve_status_surface)
  retrospective/writer.py                            # IC-02: site#1 record-home@:48 -> authority; FR-010 const (LEAVE _legacy_record_path@:52)
  post_merge/retrospective_terminus.py               # IC-02: site#2 resolver@:68 -> authority
  retrospective/lifecycle_events.py                  # IC-02: sites#3-5 emitter@:336,:411,:480 -> authority
  merge/executor.py                                  # IC-03/04: teardown@:795 (in _phase_cleanup_worktrees_and_branches@:717) -> shared seam; persist OUTSIDE swallow@:805
  cli/commands/merge.py                              # IC-03/04: --abort teardown@:270 (swallow@:271) -> shared seam (#2133 left this in cli/, did NOT move to merge/)
  cli/commands/mission_type.py                       # IC-03/04/05/07/09: teardown@:910 (helper@:904), dead helpers@:78,:313, comments@:642 & :607
  coordination/                                      # IC-03: NEW shared teardown seam lives here (near CoordinationWorkspace; spans 2 pkgs + mission_type)
  coordination/surface_resolver.py + cli/commands/_coordination_doctor.py   # IC-06: phantom-command repoint (#1890), 8 sites (post-#2135; doctor.py now zero)
src/runtime/next/_internal_runtime/
  retrospective_terminus.py                          # IC-02: site#6 _record_path_str payload@:76 (hardcoded .kittify) -> authority; FR-010 hoist (shared boundary)
src/doctrine/skills/spec-kitty-mission-system/SKILL.md         # IC-06: 8th phantom site@:509 (SOURCE, not generated .agents/ copy)
architecture/3.x/adr/2026-06-25-1-terminal-artifact-durable-home-teardown.md  # IC-08: ADR
```

## Implementation Concern Map

| IC | Concern | FRs | Notes |
|----|---------|-----|-------|
| IC-00 | **FOUNDATION (#2136) — caller-canonicalization (the primitive STAYS blind):** canonicalize a bare `mid8`/`slug` handle to `<slug>-<mid8>` **in the CALLER**, NOT inside `primary_feature_dir_for_mission`@:1212. That primitive is handle-blind by contract (docstring @:1213) and MUST stay so — folding canonicalization in is **infinite recursion** (`_canonicalize_bare_modern_handle`@:418 calls the primitive at @:454). Route (a) the READ leg `resolve_planning_read_dir`'s PRIMARY-partition branch @:1306 and (b) the WRITE sites (FR-001/003, owned by WP03) through `_canonicalize_bare_modern_handle`@:418 / `_canonicalize_handle`@:467 BEFORE the blind compose, mirroring the live exemplars @:1204/:1208/:820; preserve no-silent-fallback (`MissionSelectorAmbiguous`, WP07/C-009) + back-compat legs. | FR-011 | Extends the handle-equivalence matrix (`tests/missions/test_surface_resolution_equivalence.py`) THROUGH the read seam: bare-`mid8` ≡ bare-`slug` ≡ `<slug>-<mid8>`; ambiguous → raises. NO parallel resolver (C-006). **WP01 owns the READ leg; WP03 owns the WRITE leg — disjoint files. Precedes IC-01/IC-02.** |
| IC-01 | `RETROSPECTIVE` kind + primary-anchored placement authority (model on the topology-blind **`primary_feature_dir_for_mission`@:1212**, gated by `is_primary_artifact_kind`@:220 — **NOT** `resolve_status_surface`; the WRITE callers canonicalize their handle first per IC-00) | FR-002 | Builds on the caller-canonicalized read/write legs (IC-00); single set-membership (enum@:24, partition@:85). Unit assert `RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS`. |
| IC-02 | Consolidate ALL **6** retro-home sites onto the authority: `writer.py:48`, `post_merge/retrospective_terminus.py:68`, `lifecycle_events.py:336/:411/:480`, `runtime/next/.../retrospective_terminus.py:76` `_record_path_str` payload | FR-001, FR-003 | Enumerating structural test (GREP/AST, no hardcoded count, 7th-site fails); live-coord behavioral test asserts `".worktrees" not in resolved.parts`. LEAVE `writer.py:52`. |
| IC-03 | Extract ONE shared teardown seam from the 3 live `CoordinationWorkspace.teardown(` sites (post-#2133 base): `merge/executor.py:795` (cleanup phase `_phase_cleanup_worktrees_and_branches`@:717) + `cli/commands/merge.py:270` (`--abort` helper) + `mission_type._teardown_coordination_worktree`@:904 (call@:910). Sites span TWO packages + `mission_type` → seam lives in **`coordination/`**, not `merge/`. | FR-004 | Behavior-preserving extraction; **anti-rename: zero teardown call sites outside the seam**; precursor for IC-04. |
| IC-04 | Persist-before-destroy in the seam (persist -> flatten -> destroy), **persist OUTSIDE the best-effort `except Exception` swallow** (`executor.py:805`, `merge.py:271`, `mission_type.py:921`), both merge + discard; discard persist hooks ahead of `mission_type.py:676` | FR-005 | Destroy-**step** fault-injection proof. **UPDATE** #2133's `test_phase_cleanup_coord_teardown_failure_is_non_fatal` (`tests/merge/test_executor_coverage.py:616`) to the persist-before-destroy contract (DIR-041 — never delete-to-green). |
| IC-06 | Phantom `agent worktree repair` -> `doctor workspaces --fix`, all **8** sites (`_coordination_doctor.py`×4 @:220/:293/:338/:345, `surface_resolver.py`×3 @:109/:119/:782, SOURCE `SKILL.md`×1 @:509) + **count-agnostic** grep-guard | FR-007 (#1890) | Independent; line-disjoint. Post-#2135 the former 5 `doctor.py` strings relocated to `_coordination_doctor.py` (collapsed to 4); `doctor.py` now zero. The grep-guard fails closed regardless of count. SKILL.md site is SOURCE doctrine, not `.agents/`. |
| IC-07 | Tidy (**split**): (a) remove 2 dead helpers `mission_type.py:78,:313` (prove 0 callers); (b) hoist filename const | FR-008/010 | **FR-010 may be its OWN WP** (8 literals + 2 `.tmp` f-strings across 6 `.py` files, shared-package boundary). FR-008 local. |
| IC-08 | ADR "Terminal-Artifact Durable Home + Topology-Aware Teardown Contract" | — | Two bindings (both UNCHANGED); records the decision; precedents #2101/#2090, #1716. |
| IC-09 | Fix two stale `mission_type.py` comments — `:642` ("Same path as merge.py:1568" — `merge.py` is now 575 lines post-#2133; `:1568` no longer exists) and `:607` (stale `f"{raw}-"` prefix-match prose, landmine left by #2129's de-prefixing) | FR-009 | Re-point `:642` at the real teardown region (`merge/executor.py` cleanup phase + `cli/commands/merge.py:270`). |

**Sequencing (ONE slice, no open-PR gate):** **IC-00 (FR-011 handle-safe seam) is the FOUNDATION** — it
precedes IC-01 (kind/authority) and IC-02 (consolidation), which build on the now-handle-safe
`primary_feature_dir_for_mission`; IC-03/04 (teardown seam + persist-before-destroy) follow via
`dependencies`; IC-06 (#1890), IC-07 (tidy + filename hoist), IC-09 (stale comments) are line-disjoint and
parallelizable. All teardown-touching work is against the
**already-merged** base: #2133 relocated the merge-path teardown into `merge/executor.py:795` (cleanup phase)
but left the `--abort` teardown at `cli/commands/merge.py:270`, so the FR-004 seam unifies three live sites
spanning `merge/executor.py` + `cli/commands/merge.py` + `mission_type.py` and therefore lives in
`coordination/`. FR-005 **updates** #2133's no-persist test (`tests/merge/test_executor_coverage.py:616`).
(#2135 doctor.py decomposition merged — FR-007's grep-guard is count-agnostic and move-invariant. #2114 and
#2134 are merged NON-ISSUES — no overlap. #2115/Ray-port is OUT of scope, owned by other maintainers.)

## Test Discipline (NFR-002 — the keystone)

- **Live coord divergence:** every FR-001/003 + FR-005 behavioral test builds a real
  coord-topology mission whose coordination surface lacks `meta.json`/`lanes.json` (genuine divergence). The
  FR-001/003 test MUST assert **`".worktrees" not in resolved.parts`** — asserting merely `kitty-specs in
  parts` is the #1771 false-green (it passed flat) and is rejected. A stub/bare-slug/flattened fixture is
  also rejected. The former FR-006 prefix-sibling fixture is removed (done-by-#2129).
- **Destroy-step fault injection (FR-005):** force the **destroy** step to raise (persist runs OUTSIDE the
  best-effort swallow); assert the retrospective already exists at its durable home — on both the merge path
  and the `mission_type.py` close/`--discard` path. **UPDATE** `tests/merge/test_executor_coverage.py:616`
  `test_phase_cleanup_coord_teardown_failure_is_non_fatal` to this contract; never delete-to-green (DIR-041).
- **Anti-rename routing (IC-03):** assert **zero `CoordinationWorkspace.teardown(` call sites exist outside
  the new seam** (a rename leaving the duplications is rejected), enumerated over the live three-site topology
  (`merge/executor.py:795`, `cli/commands/merge.py:270`, `mission_type.py:910`).
- **Enumerating structural test (FR-003):** derive the retro-home resolution call-site set by **GREP/AST
  (a hardcoded count is forbidden)** and assert each routes through the authority; a re-introduced
  independent resolution (a 7th site) fails the test.
- **Grep-guard (FR-007):** **count-agnostic** repo-wide test fails if `agent worktree repair` survives anywhere
  (currently 8 sites, incl. the SOURCE `src/doctrine/.../SKILL.md`); fails closed regardless of site count.
- **Unit (FR-002):** assert `RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS`.
- **Handle-equivalence matrix (FR-011 / #2136, the foundation keystone):** extend
  `tests/missions/test_surface_resolution_equivalence.py` so a bare-`mid8` handle, a bare-`slug` handle, and a
  pre-resolved `<slug>-<mid8>` handle ALL resolve through `primary_feature_dir_for_mission` to the SAME
  canonical PRIMARY dir (no handle-blind divergence); an **ambiguous** handle MUST raise
  `MissionSelectorAmbiguous` (no silent pick — WP07/C-009); the `meta.json`-present and unresolvable-handle
  back-compat legs of `_canonicalize_bare_modern_handle` MUST stay unchanged.
- **Regression-reference (former SC-004):** sibling-survival on prefix-discard is satisfied on the base by
  #2129; a regression test MAY lock it but is not a deliverable.

## Phase 0 / Phase 1 outputs

- `research.md` — design decisions (placement authority, teardown seam, slice split, ADR scope) — all
  resolved by the 3-lens discovery; no open NEEDS CLARIFICATION.
- `data-model.md` — entities: `RETROSPECTIVE` kind, the placement authority, the teardown seam contract.
- `contracts/` — the placement-authority + persist-before-destroy teardown contract.
- ADR — `architecture/3.x/adr/2026-06-25-1-terminal-artifact-durable-home-teardown.md`.

## Complexity / Risk

- **Highest risk:** IC-04 persist-before-destroy ordering on the merge path (the seam must persist before
  the `merge/executor.py` cleanup-phase teardown, and **persist must sit OUTSIDE the best-effort
  `except Exception` swallow** so a persist failure is not absorbed) — mitigated by destroy-step fault
  injection. The seam builds on the already-merged (maxCC-clean) `merge/executor.py`, easing the ceiling.
- **Seam-placement risk:** the 3 live teardown sites span TWO packages (`merge/executor.py` +
  `cli/commands/merge.py`) plus `mission_type.py` — #2133 left the `--abort` teardown in `cli/`, it did NOT
  migrate into `merge/`. The seam therefore lives in `coordination/` (near `CoordinationWorkspace`); placing
  it in `merge/` would force `mission_type`/`cli` to reach across a package that owns neither call site.
- **Foundation read-seam blast-radius risk (IC-00 / FR-011):** the fix changes the caller, NOT the
  primitive — `primary_feature_dir_for_mission`@:1212 stays handle-blind by contract (seam-internal
  canonicalization is infinite recursion, @:418→@:454). The canonicalization is added in
  `resolve_planning_read_dir`'s PRIMARY leg @:1306 (WP01) and the WRITE sites (WP03); that read seam feeds
  planning reads/status/merge/accept, so it is high-leverage but contained. Mitigated by (a) reusing the
  EXISTING `_canonicalize_bare_modern_handle` machinery that the live exemplars @:820/:1204/:1208 already
  invoke — so the behavior is proven, not novel; (b) leaving the blind primitive's body and its ~40 callers'
  contract unchanged — a canonical `<slug>-<mid8>` or already-resolvable handle is a no-op, and the
  `meta.json`-present / unresolvable-handle short-circuit legs of the helper stay no-ops; (c) the
  no-silent-fallback contract (ambiguous → raise), guarded by the extended equivalence matrix. Run the full
  `tests/missions/` + `tests/integration/` suites before PR
  (the seam feeds planning reads, status, merge, and acceptance).
- **No sequencing gate:** all gate PRs (#2121/#2129/#2133/#2114/#2134/#2135) have merged — the whole mission
  plans as one slice. FR-007's grep-guard is count-agnostic (move-invariant across #2135's relocation).
- **False-green risk:** the #1771 trap — mitigated by the live-coord-divergence discipline (NFR-002).
