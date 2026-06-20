# Mission-surface-resolution audit ruleset (WP01 / FR-003)

This ruleset is **reproducible**: a reviewer re-runs

```bash
python tests/architectural/surface_resolution_audit/audit.py
```

and the script re-walks `src/specify_cli` and `src/mission_runtime`,
re-discovers the callsite set, and fails closed (non-zero exit) if the live
tree no longer matches `inventory.md`. The machine job is to make bypass
under-counting impossible; the **disposition** of each row is a human
judgement recorded in `inventory.md`.

---

## Context: what this audit is for

The mission collapses the coord-vs-primary **selection** resolvers to one
canonical owner (`coordination/surface_resolver.resolve_status_surface_with_anchor`).
This audit enumerates every mission-surface-resolution callsite, classified so
WP06 (collapse), WP07 (shim migration), and WP08 (guard) know exactly what to
target and what to guard.

---

## Canonical resolvers (what "routed-through-resolver" cites)

These are the blessed entry points. A callsite routed through any of these is
classified `routed-through-resolver` (cite the one it uses):

| Resolver | Location | What it does |
|----------|----------|--------------|
| `resolve_mission_read_path` | `missions/_read_path_resolver.py` | Coord-aware, mid8-aware, ambiguity-structured-error. Single canonical read primitive. |
| `candidate_feature_dir_for_mission` | `missions/_read_path_resolver.py` (re-exported via `missions/feature_dir_resolver.py`) | Thin wrapper over `resolve_mission_read_path`; derives mid8 from slug. |
| `resolve_status_surface` | `coordination/surface_resolver.py` | Returns canonical `status.events.jsonl` path; thin wrapper over `resolve_status_surface_with_anchor`. |
| `resolve_status_surface_with_anchor` | `coordination/surface_resolver.py` | Single-pass; returns `(surface_path, primary_anchor)`. The canonical surface authority. |
| `resolve_feature_dir_for_slug` | `missions/feature_dir_resolver.py` | Coord-aware dir-only resolver without existence assertion. |
| `resolve_feature_dir_for_mission` | `missions/feature_dir_resolver.py` | Routes through `resolve_action_context` for full topology resolution. |

---

## Topology-blind-by-design primitive

`primary_feature_dir_for_mission` (`missions/_read_path_resolver.py:410`) is a
**sanctioned** topology-blind primitive: it intentionally targets the
PRIMARY checkout, bypassing the coord worktree. Callers use it because:

- `meta.json` ONLY lives on the primary checkout — reading through the
  coord-aware resolver returns the coord worktree dir (which has no `meta.json`)
  and causes topology classification to flip based on whether the coord worktree
  exists (the #1589/#1821 split-brain). Documented at C-GUARD-3a in the
  `mission_runtime/resolution.py` comments.
- Planning-phase reads (finalize-tasks, merge-target resolution) must be
  CWD-invariant and anchored on the primary checkout.

Callers of `primary_feature_dir_for_mission` are classified
`topology-blind-by-design`, NOT `raw-bypass`. The function itself
(`_read_path_resolver.py:438`) is similarly classified — it IS the primitive
definition, it asserts `assert_safe_path_segment` at line 437, and it lives in
the blessed path-constructor module.

---

## Seed-set (what callsites are tracked)

The audit tracks two classes:

1. **Resolver/topology-blind calls WITHIN the canonical seam source files**
   (`RESOLVER_SOURCE_STEMS` in `audit.py`):
   - `specify_cli/missions/_read_path_resolver.py`
   - `specify_cli/missions/feature_dir_resolver.py`
   - `specify_cli/coordination/surface_resolver.py`
   - `specify_cli/coordination/status_transition.py`
   - `specify_cli/status/aggregate.py`
   - `mission_runtime/resolution.py`

   These are tracked to verify the seam implementations remain internally correct.

2. **Raw-bypass path joins in ALL files**: `<path-expr> / KITTY_SPECS_DIR / <slug>`
   where `<slug>` is a name in `SLUG_NAMES`. These are FR-001 targets.

The 144 downstream callers that legitimately call a blessed resolver outside
the seam files are NOT tracked row-by-row — they are summarized in
`inventory.md` § "Routed caller summary". The bypass scanner still runs
codebase-wide so no hidden raw join can escape.

---

## Raw-bypass detection predicate

A callsite is a **raw-bypass** join when:
1. A `<path-expr> / <slug>` `BinOp` appears where the `<slug>` is a name in
   `SLUG_NAMES`: `mission_slug`, `feature_slug`, `slug`, `mission_slug_formatted`.
2. The left subtree of the join recursively contains a reference to
   `KITTY_SPECS_NAMES`: `KITTY_SPECS_DIR`, `kitty_specs_dir`, `_KITTY_SPECS_DIR`,
   or the string literal `"kitty-specs"`.

The matcher recurses the left operand so `root / KITTY_SPECS_DIR / mission_slug`
(three-level join) is caught as well as `specs / mission_slug`.

---

## Known false-negative classes (what this matcher does NOT trace)

1. **Cross-function / inter-procedural flow.** Taint is computed per-file; a slug
   passed into a function as an argument is not tracked to the callee.
2. **More than one alias hop.** `a = slug; b = a; root / KITTY_SPECS_DIR / b`
   (two hops) is not followed.
3. **Container/collection flow.** A slug stored in a list/dict and later popped
   into a join is not traced.
4. **f-strings / `os.path.join` / `str` concatenation.** Only `pathlib` `/`
   joins are matched.
5. **`Path(...)` constructed from an untrusted full string** (not a join) —
   e.g. `Path(user_slug)` — is not detected.
6. **Callers outside `RESOLVER_SOURCE_STEMS`** that call a blessed resolver.
   These are `routed-through-resolver` by construction; the "Routed caller
   summary" in `inventory.md` enumerates them.

---

## Disposition vocabulary (exactly one per row)

| Disposition | Meaning |
|-------------|---------|
| `routed-through-resolver` | Goes through a canonical blessed resolver (cite which one); or uses a validated seam (e.g. `_validate_segment`) before the join. |
| `topology-blind-by-design` | Deliberately primary-only; the coord surface cannot serve this read (e.g. `meta.json` reads). NAME the reason. |
| `raw-bypass` | Composes `KITTY_SPECS_DIR / slug` directly, bypassing all resolvers. FR-001 target. |

---

## Anti-undercount proof

The seed-set is data (`SLUG_NAMES` / `KITTY_SPECS_NAMES` / `_RESOLVER_SOURCE_STEMS`
in `audit.py`), not a hard-coded file list. Adding `"filename"` to `SLUG_NAMES`
and re-discovering surfaces additional joins outside the known set — proving the
matcher generalises. The experiment is reproducible by temporarily extending
`SLUG_NAMES` in `audit.py` and re-running.

The `KNOWN_CANDIDATE_FILES` tripwire in `audit.py` asserts that every expected
seam file appears in the discovered rows or inventory. Temporarily removing
`missions/_read_path_resolver.py` from `KNOWN_CANDIDATE_FILES` and deleting
its rows from `inventory.md` causes the audit to exit non-zero —
demonstrating the anti-undercount guard fires correctly.
