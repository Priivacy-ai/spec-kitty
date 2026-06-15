# Research — Mission-identity naming seam & #1908 panel hardening

## R1. The naming seam already exists — this is consolidation + bug-fix, not greenfield

`src/specify_cli/lanes/branch_naming.py` is already the de-facto seam:
- compose: `mission_branch_name` (L148), `mission_branch_name_required` (L208),
  `lane_branch_name` (L340)
- parse/detect: `mid8_from_slug` (L116), `parse_mission_slug_from_branch` (L455),
  `parse_lane_id_from_branch` (L512), `is_mission_branch`/`is_lane_branch`/
  `is_legacy_branch` (L390/405/413)
- convention (docstring L6-18): `kitty/mission-<slug>-<mid8>[-lane-<id>]`; legacy
  `kitty/mission-<NNN>-<slug>`.

**Decision:** treat `branch_naming.py` as the single authority. The work is (a)
fix the idempotency/heuristic bugs *inside* it, (b) add the missing worktree
dir-name grammar (the filesystem twin), and (c) route the two outliers that
bypass it (merge preflight, worktree allocator f-string) through it. Add a
round-trip/property test (NFR-003).

## R2. Call-site map (what's already routed vs. the outliers)

| Surface | Where | Status |
|---|---|---|
| compose mission branch | `lanes/compute.py:349` → `mission_branch_name(...)` writes `lanes.json.mission_branch` | ✅ routed (but composer has #1949 bug) |
| parse mid8 | `mission_runtime/resolution.py:110`, `runtime/next/runtime_bridge.py:172/2399`, `acceptance/__init__.py:672`, `agent/context.py:76` | ✅ all call `mid8_from_slug` (but it has #1918 bug) |
| **merge preflight** (#1978) | `src/specify_cli/merge/preflight.py` `_check_mission_branch` | ❌ reconstructs `kitty/mission-{slug}`, drops `-{mid8}` → must read `lanes.json.mission_branch` / use the seam |
| **worktree dir-name** (#1899) | `lanes/worktree_allocator.py:127` `repo_root/".worktrees"/f"{mission_slug}-{lane_id}"` | ❌ name-guessing f-string (the seam's own L234 comment forbids this) → add `worktree_dir_name()` to the seam + route |

## R3. The two bugs inside the seam

- **#1949 (compose double-append):** `mission_branch_name`/`mission_branch_name_required`
  (L148/208, dual-era logic ~L321) append `-{mid8}` even when `mission_slug`
  already ends in `-{mid8}` → composes a branch that is never created. Fix:
  idempotent compose (strip/detect an already-embedded mid8 before appending).
- **#1918 (parse false-positive):** `mid8_from_slug` (L116) dual-era heuristic
  treats any trailing 8-char Crockford-base32 segment as a mid8 → a modern slug
  whose last hyphen-segment is coincidentally 8 such chars resolves a wrong mid8.
  Fix: tighten the heuristic (e.g. require the mid8 to match the recorded
  `mission_id` prefix when available, or decline on ambiguity).

**Round-trip invariant (NFR-003):** `parse(compose(slug, mid8)) == (slug, mid8)`,
and `compose` is idempotent when `slug` already carries `mid8`. Property test over:
embedded-slug, non-embedded-slug, coincidental-8-char-tail, legacy-NNN.

## R4. Cluster B sites (discrete, independent)

- **#1915:** `lanes/worktree_allocator.py::_merge_dependency_lane_tips` (def L223,
  callers L136/L176) loops `git merge` over dep lanes; a later-dep conflict
  triggers `git merge --abort` which only rolls back the conflicting merge — an
  earlier clean dep merge commit survives. Fix: make the multi-dep merge atomic
  (snapshot HEAD/ref before the loop; on any conflict reset to the snapshot).
- **#1917:** `cli/commands/implement.py::_validate_base_ref` (def L215, caller
  L1158) runs `git rev-parse --verify <base_ref>` without a `--` separator → a
  `--base=--flag` value is parsed as an option. Fix: insert `--` before the value.
- **#1916:** `acceptance/__init__.py` — the readiness/`--no-commit` path triggers
  `identity.project.ensure_identity` (mints/persists `.kittify/config.yaml`),
  dirtying the tree; `_filter_accept_owned_project_config` (L581, caller L1080) is
  the PR-#1908 stopgap that excludes that write from the dirty check. Fix: move
  `ensure_identity` off the readiness path to a write-authorized boundary, then
  retire the stopgap filter. (`ensure_identity` def: `identity/project.py:299`;
  legitimate write-boundary callers exist in init/tracker/sync.)

## R5. Sequencing (dogfooding)

This mission's own slug `mission-identity-seam-and-1908-panel-01KV6510` ends in
its mid8 (`01KV6510`), so its own `spec-kitty merge` exercises #1978. Sequence:
fix the seam (R3) → #1978 (merge preflight uses the seam) **early**, so the
mission can merge itself; otherwise merge manually (spec C-005). Cluster B
(#1915/#1917/#1916) is independent and can run in parallel lanes.
