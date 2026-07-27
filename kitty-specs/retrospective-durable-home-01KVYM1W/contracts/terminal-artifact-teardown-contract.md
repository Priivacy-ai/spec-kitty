# Contract: Terminal-Artifact Placement + Topology-Aware Teardown

Binding contract for IC-00..IC-05. Enforced by the tests named per clause.

## C0 — Handle-safe PRIMARY entry points (FR-011 / #2136, the foundation)

- The PRIMARY callers of the topology-blind primitive `primary_feature_dir_for_mission`
  (`src/specify_cli/missions/_read_path_resolver.py:1212`) MUST canonicalize a bare `mid8`/`slug` handle to the
  canonical `<slug>-<mid8>` dir **in the caller**, BEFORE the blind compose: the READ leg
  `resolve_planning_read_dir`'s PRIMARY-partition branch (`:1306`, WP01) and the WRITE sites (FR-001/003, WP03).
  Today they feed the primitive a raw handle (it does the raw literal compose at `:1240`, handle-blind by
  contract — docstring `:1213`).
- **The primitive MUST stay handle-blind** — canonicalizing inside it is infinite recursion
  (`_canonicalize_bare_modern_handle`@`:418` calls the primitive at `:454`). The caller-side pattern mirrors the
  live exemplars `:1204`/`:1208`/`:820`.
- The canonicalization MUST reuse the existing `_canonicalize_bare_modern_handle` (`:418`) /
  `_canonicalize_handle` (`:467`) identity machinery — **NO parallel/bespoke resolver** (C-006).
- **No-silent-fallback:** an ambiguous handle MUST raise `MissionSelectorAmbiguous`, never silently pick one
  (WP07 / C-009). The `meta.json`-present and unresolvable-handle back-compat legs MUST stay unchanged.
- **Ownership:** WP01 owns the READ leg (`resolve_planning_read_dir:1306`, inside `_read_path_resolver.py`);
  WP03 owns the WRITE leg (the 6 retrospective placement sites) — disjoint `owned_files`. The blind primitive
  body is NOT edited.
- **Tests:**
  - *Handle-equivalence matrix (NFR-005 / SC-007):* extend `tests/missions/test_surface_resolution_equivalence.py`
    so bare-`mid8`, bare-`slug`, and pre-resolved `<slug>-<mid8>` resolve through the READ seam
    (`resolve_planning_read_dir`, PRIMARY kind) to the SAME canonical PRIMARY dir; an ambiguous handle raises
    `MissionSelectorAmbiguous`.
  - *Back-compat no-op:* a canonical / already-resolvable handle and an unresolvable handle behave exactly as
    before (the short-circuit legs are untouched).

## C1 — Terminal-artifact placement (FR-001/002/003)

- `retrospective.yaml` resolves to the durable PRIMARY home `kitty-specs/<slug>/` for **every topology**,
  via membership of `RETROSPECTIVE` in `_PRIMARY_ARTIFACT_KINDS` and the single placement authority.
- **Placement authority exemplar:** modeled on **`primary_feature_dir_for_mission`**
  (`src/specify_cli/missions/_read_path_resolver.py:1212`, topology-blind) gated by **`is_primary_artifact_kind`**
  (`src/mission_runtime/artifacts.py:220`). **NOT** `resolve_status_surface` (topology-aware → reproduces the
  coord-routing bug; it is the read-side exemplar only, C-004).
- **No site** resolves the home independently. The authoritative resolution set is exactly the **6 sites** in
  `data-model.md` (5 coord-aware resolvers + 1 hardcoded payload string). `writer.py:60` `_legacy_record_path`
  is excluded (load-bearing `.kittify` back-compat read).
- **Tests:**
  - *Unit (FR-002):* assert `RETROSPECTIVE in _PRIMARY_ARTIFACT_KINDS`.
  - *Behavioral (live-coord-divergence, FR-001/003):* a real coord-topology mission (coord surface lacks
    `meta.json`/`lanes.json`) produces a retrospective; assert **`".worktrees" not in resolved.parts`** (NOT
    merely `kitty-specs in parts` — that passed flat in #1771 and is an insufficient false-green) and that it
    lands at `kitty-specs/<slug>/retrospective.yaml`, NOT under `.worktrees/<slug>-coord/`. A
    stub/bare-slug/flattened fixture is rejected (NFR-002).
  - *Enumerating structural (FR-003):* derive the resolution-site set by **GREP/AST (a hardcoded count is
    forbidden)** and assert every site routes through the authority; a re-introduced independent resolution
    (incl. a 7th site, or the `runtime/next/.../retrospective_terminus.py:76` `_record_path_str` payload) fails
    (anti-rename-vacuous).
  - *Payload parity:* the emitted lifecycle-event payload path equals the actual write home (no longer the
    hardcoded `.kittify/missions/<id>/` string).

## C2 — Persist-before-destroy teardown (FR-004/005)

- Teardown is a single shared seam executing **persist → flatten → destroy**, on BOTH the merge path and
  the `close --discard` path. Extracted from the 3 live (post-#2133) `CoordinationWorkspace.teardown(` call
  sites: `merge/executor.py:795` (merge cleanup phase `_phase_cleanup_worktrees_and_branches`@:717),
  `cli/commands/merge.py:270` (**`--abort`** helper), `mission_type.py:910` (close/`--discard`, helper
  `_teardown_coordination_worktree`@:904). The sites span TWO packages + `mission_type`, so the seam lives in
  **`src/specify_cli/coordination/`**, NOT `merge/` (#2133 left the `--abort` teardown in `cli/`).
- **Swallow-isolation:** all 3 sites wrap `CoordinationWorkspace.teardown` in a **swallowing
  `except Exception`** (`executor.py:805`, `merge.py:271`, `mission_type.py:921`). The seam MUST run
  **persist OUTSIDE that swallow** — a persistence failure must never be absorbed by the destroy best-effort
  handler.
- **Anti-rename routing:** **zero `CoordinationWorkspace.teardown(` call sites exist outside the new seam**
  (a rename leaving the 3 duplications is rejected).
- **Invariant:** destroy never precedes persist.
- **Tests:**
  - *Destroy-step fault injection (injected at the destroy step):* force the **destroy** step to raise; assert
    `kitty-specs/<slug>/retrospective.yaml` already exists — on the merge path AND the `mission_type.py`
    close/`--discard` path. This **UPDATES** #2133's
    `tests/merge/test_executor_coverage.py:616` `test_phase_cleanup_coord_teardown_failure_is_non_fatal` to the
    persist-before-destroy contract (never delete-to-green, DIR-041).
  - *Anti-rename routing:* a structural test asserts no `CoordinationWorkspace.teardown(` call site survives
    outside the seam.
  - *No-regression (flattened):* a flattened/single-branch mission's teardown is byte-identical to before (NFR-003).

## C3 — Lane-worktree exact-set (FR-006 / #2123) — STRUCK, DONE-by-merge (#2129), regression-reference only

- Teardown removes EXACTLY the mid8-anchored lane-worktree names from `lanes.json` for this mission —
  **already shipped on the base by #2129**: `_remove_lane_worktrees` (`mission_type.py:970`) removes by exact
  name via `_expected_lane_worktree_dir_names` (`:950`); `_verify_discard_complete` (`:777`) is exact-name +
  sibling-safe. No prefix-match survives. **No #2119 code change is in scope** (#2123 stays OPEN on the tracker;
  #2129 closed twin #2127).
- **Invariant:** no `<slug>-*` prefix match; a sibling mission's worktree is never touched.
- **Tests (regression-reference only, not a deliverable):**
  - *Sibling survival:* sibling `<slug>-<mid8>-sibling` carrying uncommitted work survives the target's
    `--discard`; the target's worktrees are gone; exit 0; no spurious abort on the sibling.

## C4 — Recovery guidance (FR-007 / #1890)

- No runtime or doc string references `spec-kitty agent worktree repair`; recovery guidance names
  `spec-kitty doctor workspaces --fix`. On the current base (post-#2135) the **8 sites** are:
  `cli/commands/_coordination_doctor.py` ×4 (`:220, :293, :338, :345`),
  `coordination/surface_resolver.py` ×3 (`:109, :119, :782`), and the SOURCE doctrine
  `src/doctrine/skills/spec-kitty-mission-system/SKILL.md` ×1 (`:509`, the SOURCE under
  `src/doctrine/`, NOT a generated `.agents/` copy). `cli/commands/doctor.py` now has ZERO (#2135 relocated the
  former 5 `doctor.py` strings into `_coordination_doctor.py`, collapsing to 4).
- **Tests:** a **count-agnostic** repo-wide grep-guard fails if the phantom string survives anywhere.

## C5 — Tidy (FR-008/009/010)

- The two dead worktree helpers (`_list_active_worktrees` @ `mission_type.py:78`,
  `_print_active_worktrees` @ `:313`) are removed (a test/grep proves zero live callers BEFORE deletion).
- The two stale `mission_type.py` comments are corrected: `:642` ("Same path as merge.py:1568" — `:1568` no
  longer exists post-#2133; re-point at `merge/executor.py` cleanup phase + `cli/commands/merge.py:270`) and
  `:607` (stale `f"{raw}-"` prefix-match prose, landmine left by #2129's de-prefixing).
- `retrospective.yaml` exists as exactly one named constant — the hoist spans **8 string literals + 2 `.tmp`
  f-strings across 6 `.py` files** (re-censused; the earlier "13 files / 47 occurrences" conflated docstrings
  and prose) crossing the **shared-package boundary** (`src/runtime/next` + `src/mission_runtime`-adjacent), so
  it is its **OWN WP**; consume via the public import surface.
- **Tests:** zero-caller proof; a single-definition assertion for the filename constant.

## Non-goals (explicit)

- No change to `retrospective.yaml` schema/content.
- No change to read-side retrospective access (`resolve_status_surface` — C-004).
- No split of `_run_lane_based_merge_locked` (separate debt; C901 passes).
- No fold of the atomic-YAML write duplication (RELATE #2125).
- **No fold of the read-surface residual cluster #2138 / #2139 / #2140** (decision-event payload slug-as-
  `mission_id`; dual `target_branch` reader w/ silent `main` fallback; `is_committed` spec-read coord-unaware) —
  recommended as a separate follow-on mission or parked under #1868/#1716. NOT #2119 FRs.
- FR-011 canonicalizes only the `primary_feature_dir_for_mission` PRIMARY seam; the STATUS-partition /
  topology-aware leg and any residual #2122 entry-point work outside that seam are NOT in scope.
