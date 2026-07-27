# Quickstart / Verification: Single Mission-Surface Resolver

How a reviewer confirms the consolidation is correct and safe.

## 1. Equivalence gate green (SC-001, the deletion safety gate)

```bash
PWHEADLESS=1 python -m pytest tests/ -k "resolver_equivalence or surface_equivalence" -p no:cacheprovider -q
```
Expect: the differential test passes — every entry point agrees on dir-or-typed-error
across the (topology × handle-class) matrix, including the `<slug>-<mid8>` class
(proves FR-009/T1 isn't a false-green).

## 2. Load-bearing guard (SC-002)

```bash
PWHEADLESS=1 python -m pytest tests/architectural/ -k "single_resolver or surface_bypass" -p no:cacheprovider -q
```
Then prove it bites: temporarily add a `repo_root / KITTY_SPECS_DIR / mission_slug` join
in an audited file → the guard FAILS; revert → passes.

## 3. Coord-empty hard-fail with the two-path message (SC-006)

Create a mission with a materialized-but-empty coord worktree; resolve its surface.
Expect: `STATUS_READ_PATH_NOT_FOUND` whose message names BOTH collapse/flatten AND
recreate/populate. NO silent primary fallback. (And: a *no-coord* mission still resolves
to primary — the create→first-write window is not a hard-fail.)

## 4. Typed-error pass-through (SC-003, #2010 bug #15)

Reproduce bug #15 (a read-path-not-found / ambiguous handle through `next`):
```bash
PWHEADLESS=1 python -m pytest tests/ -k "typed_error_passthrough or next_error_code" -p no:cacheprovider -q
```
Expect: `STATUS_READ_PATH_NOT_FOUND`/`MISSION_AMBIGUOUS_SELECTOR` preserved (not
`MISSION_NOT_FOUND`).

## 5. No raw-bypass remains (SC-005)

```bash
python tests/architectural/<surface-resolution-audit>.py
```
Expect: 0 `raw-bypass` rows; `status_transition.py` coord predicates migrated; the C-002
topology-ratchet allowlist entry for it drained (#1900).

## 6. No regression / gates

```bash
PWHEADLESS=1 python -m pytest tests/status tests/architectural tests/specify_cli/cli/commands -p no:cacheprovider -q
ruff check . ; mypy --strict <changed files>
```
Expect: pre-existing suites green; ruff + mypy --strict 0 on changed code.

## 7. Shim retirement (FR-007/T6)

```bash
rg -n "from .*feature_dir_resolver import" src/ | wc -l   # → 0 after migration
```
Expect: `missions/feature_dir_resolver.py` retired; all callers on the canonical module
(migration classified via the scoped occurrence_map.yaml).
