# Contract: `resolve_merge_retention` (retention resolver)

The single authority that turns tri-state CLI flags + `meta.json` retention into
the effective post-merge cleanup decision. Co-located with
`resolve_merge_target_branch` in `src/specify_cli/core/paths.py`. Consumed by the
executor (once, unlocked) and the dry-run forecast.

## Signature (indicative)

```python
@dataclass(frozen=True)
class RetentionDecision:
    delete_branch: bool
    remove_worktree: bool
    teardown_coordination: bool          # delete_branch AND remove_worktree
    branch_source: str                   # "cli" | "meta" | "default"
    worktree_source: str                 # "cli" | "meta" | "default"
    warnings: tuple[str, ...]
    override_notices: tuple[str, ...]

def read_retention_from_meta(primary_meta_dir: Path) -> tuple[object | None, object | None]:
    """Return (retain_branches_raw, retain_worktrees_raw) from primary meta.json.
    (None, None) when the file is absent; raises MissionMetaReadError when corrupt.
    Raw (not coerced) so the resolver can detect non-boolean values."""

def resolve_merge_retention(
    primary_meta_dir: Path,
    *,
    explicit_delete_branch: bool | None,   # None = flag unset
    explicit_remove_worktree: bool | None, # None = flag unset
) -> RetentionDecision: ...
```

## Behavioral contract

| Case | `explicit_delete_branch` | `meta.retain_branches` | → `delete_branch` | `branch_source` | side-effect |
|------|--------------------------|------------------------|-------------------|-----------------|-------------|
| C1 unset, no policy | `None` | absent / `false` | `True` (default) | `default` | — |
| C2 unset, retain | `None` | `true` | `False` | `meta` | warning: retention honored (names source) |
| C3 unset, malformed | `None` | `""`/`0`/`"false"`/`"true"`/list/obj | `False` | `meta` | warning: malformed value, retained |
| C3b unset, JSON null | `None` | `null` | `True` (default) | `default` | — (see note) |
| C4 explicit keep | `False` | any | `False` | `cli` | — |
| C5 explicit delete, no policy | `True` | absent / `false` | `True` | `cli` | — |
| C6 explicit delete, retain | `True` | `true` | `True` | `cli` | override_notice: explicit delete overrode retention |

**JSON `null` ≡ absent (WP01 decision, review-ratified).** `read_retention_from_meta`
uses `meta.get(key)`, which cannot distinguish a JSON `null` value from an absent
field (both are Python `None`). `null` is the JSON idiom for "no value set" and
never plausibly means "retain"; the canonical write path only ever writes `true`.
So `retain_branches: null` resolves as **absent → default (delete/remove)**, NOT
malformed→retain — keeping the field-absent byte-identical-default invariant
(INV-3) intact. Only genuinely-present non-boolean values (`0`, `""`, `"false"`,
`"true"`, lists, objects) are the malformed→retain (C3) case. A downstream WP must
NOT "fix" `null→retain` believing it a regression — this is deliberate.

The worktree columns are symmetric with `explicit_remove_worktree` /
`retain_worktrees`. `teardown_coordination = delete_branch AND remove_worktree`.
Corrupt `meta.json` propagates `MissionMetaReadError` (caller aborts the merge
with a non-zero exit, mirroring target-branch resolution) — never a fall-through.

## Consumption contract

1. **Executor** (`merge/executor.py`, unlocked `_run_lane_based_merge`, after
   `resolve_mission_identity(primary_meta_dir)`): call once, emit `warnings` +
   `override_notices` to the console (operator-visible), pass resolved
   `delete_branch` / `remove_worktree` / `teardown_coordination` into
   `_run_lane_based_merge_locked` → `_MergeRunState`. The cleanup phase gates:
   - lane worktree removal on `remove_worktree`
   - lane + mission branch deletion on `delete_branch`
   - coord marker-flatten AND coord-worktree destroy on `teardown_coordination`
     (coupled — replaces the two separate `delete_branch` / `remove_worktree` gates
     for the coordination topology only)
2. **Forecast** (`merge/forecast.py`, `run_dry_run_forecast`): call with the same
   primary meta dir + tri-state flags; the payload reports resolved
   `delete_branch` / `remove_worktree` and a `retention` object
   (`{branch_source, worktree_source, warnings}`) instead of echoing raw flags.
3. **Abort** (`cli/commands/merge.py`, `_teardown_coordination_for_abort`): resolve
   the coord decision; skip the coord-worktree destroy + warn when the mission
   requests worktree retention.

## Anti-vacuity (test contract)

- The red-first regression drives the REAL `_run_lane_based_merge` on a
  `coord`-topology mission with `retain_branches: true` / `retain_worktrees: true`,
  NO explicit flags, a NON-planning lane; it asserts the mission branch and a
  non-planning lane branch survive (`git branch --list`) and the lane worktree
  path `.worktrees/<slug>-<mid8>-lane-<id>` survives (`Path.exists()`), explicitly
  NOT the merge scratch worktree. RED on current main, GREEN after enforcement.
- A regression proves the scratch worktree is STILL removed under `retain_worktrees: true`.
- A regression proves `merge --abort` on a `retain_worktrees: true` mission leaves
  the coord worktree present.
