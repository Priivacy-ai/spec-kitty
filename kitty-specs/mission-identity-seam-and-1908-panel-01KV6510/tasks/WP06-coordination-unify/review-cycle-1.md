# WP06 Review — Cycle 1 — REJECTED (name drift on the live coordination surface)

Reviewer: reviewer-renata. Verdict: **REJECT**. One blocking defect — a byte-level
name drift in the coordination composers — plus a pre-existing regression test it breaks.
The seam-delegation design and most of the implementation are sound; the fix is small
and targeted.

## BLOCKING — Issue 1: NNN-prefix name drift in ALL FOUR coordination composers (HIGH CARE)

The WP's own Definition of Done requires byte-identical names "no coord-worktree churn".
The delegation is NOT byte-identical for a `mission_slug` that still carries an `NNN-`
prefix while the `mid8` is supplied separately — which is exactly what the live
coordination READ / transaction path does (it reads `mission_slug` verbatim from
`meta.json` and passes it, with a separate `mid8`, to the composers).

The WP01 seam's `mission_dir_name` calls `strip_numeric_prefix(...)`. The pre-WP06
coordination composers did **not** strip. So for `mission_slug="060-test"`, `mid8="01COORD0"`:

| composer | OLD (correct, on-disk) | NEW (WP06, drifted) |
|----------|------------------------|---------------------|
| `workspace._compose_mission_dir` | `060-test-01COORD0` | `test-01COORD0` |
| `workspace.worktree_path` (dir)  | `060-test-01COORD0-coord` | `test-01COORD0-coord` |
| `workspace.branch_name`          | `kitty/mission-060-test-01COORD0` | `kitty/mission-test-01COORD0` |
| `transaction._mission_specs_dir_name` | `060-test-01COORD0` | `test-01COORD0` |
| `status_transition._transaction_dir_name` | `060-test-01COORD0` | `test-01COORD0` |

This orphans the coord worktree, mis-routes the transaction/kitty-specs dir, and breaks
status reads — the precise HIGH-CARE failure the WP prompt says to reject on.

### Reproducing test (pre-existing #1589 guard) goes PASS -> FAIL

`tests/status/test_bootstrap.py::TestBootstrapCoordinationBranchPersistence::test_coordination_branch_persists_seed_events`
- PASSES on base branch (`mission/...-01KV6510`).
- FAILS on this lane with `BookkeepingWorktreeMissing` because
  `git worktree add ... kitty/mission-test-01COORD0` cannot find the on-disk
  `kitty/mission-060-test-01COORD0` branch.

This test (the slug is `060-test` + `mid8=01COORD0`) is the live counter-example to the
implementer's claim that "callers pass formatted `<slug>-<mid8>` or bare human slugs
(never `NNN-`)". `mission create` does pre-strip (verified), but the coordination
read/transaction surface does not — it consumes `meta.json.mission_slug` verbatim.

### Why the byte-identical test did not catch it

`tests/specify_cli/coordination/test_coord_dir_seam.py` uses
`_FORMATTED_SLUGS = ("foo-01KV6510", "foo", "my-feature-01KV6510", "my-feature")` and a
comment asserting "no NNN- prefix — the 083+ model never stores NNN-prefixed mission dirs".
That assumption is the defect: the coordination path can and does carry an NNN- slug. The
oracle excluded the very rows that drift.

### How to fix (implementer to decide the seam contract)

The four coordination composers (T025/T026/T027) must produce **byte-identical** names to
their pre-WP06 bodies for an `(NNN-slug, separate mid8)` input. Options:
1. Pre-strip nothing in these composers: delegate to a seam primitive that does NOT strip
   `NNN-` (the prior `_compose_mission_dir` semantics) — i.e. the seam needs a strip-free
   compose for the coordination grammar, OR
2. Have these call sites pass the already-stripped human slug consistently (but that risks
   the read-path resolving a different on-disk name than what `mission create` wrote — must
   be proven against existing coord worktrees).

Whichever path: **extend the byte-identical oracle to include NNN-prefixed slugs**
(e.g. `("060-test", "01COORD0")`) so the drift can never reappear, and keep
`test_coordination_branch_persists_seed_events` green.

NOTE: `missions/_create.coordination_branch_name` (T039) is fine — `mission create` strips
the prefix before composing (`core/mission_creation.py:320-321`), so its delegation IS
byte-identical for every real input; its oracle row `057-foo` passes. The drift is confined
to the coordination read/transaction composers.

## Non-blocking observations (verified, do NOT need rework)

- **No surviving second algorithm.** The 4 grep residuals are all genuinely benign:
  `status_transition.py:125` `endswith("-coord")` is a topology predicate; two `[:8]`
  hits (`status_transition.py:264`, `surface_resolver.py:370`) are in comments/docstrings
  stating they are NOT used; `workspace.py:173` `kitty/mission-{...}` wraps the seam's
  `mission_dir_name` (seam owns the grammar). No fake-delegation wrapper.
- **mypy +0 new.** Under the CI invocation `mypy --strict src/specify_cli src/charter
  src/doctrine`, ZERO errors in any of the 7 owned files (33 pre-existing tree-wide, all
  unrelated). The `[no-any-return]` errors that appear when checking `coordination/` +
  `missions/` in isolation are a `follow_imports="skip"` config artifact, not a defect.
- **ruff clean** on all owned files.
- `coordination/` + `missions/` suites: 283 passed. The break is in `tests/status/`.
- `surface_resolver._coord_mid8` (T028): correctly resolves declared `mission_id` first,
  with `mid8_from_slug` as final fallback (preserves the read-path test). Verified.
- `feature_dir_resolver.py` (owned, unmodified): already re-exports the canonical primitive
  and has no local compose algorithm; its slug-only `resolve_feature_dir_for_slug` uses the
  sanctioned `mid8_from_slug` fallback (no mission_id available). Correct, no action needed.
- `test_no_dead_symbols.py` transient redness (cross-lane WP03/04/05 wiring) is NOT a WP06
  defect — noted for post-merge validation only.
