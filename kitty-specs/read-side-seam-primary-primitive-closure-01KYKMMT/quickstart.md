# Quickstart: verifying Read-Side Seam: Placement-Authority Closure

How to check this mission's work locally. **Never run the full `tests/architectural/`
suite** — it destabilises the session (C-008). Run the named gates only; CI owns the
exhaustive sweep.

Inside a lane worktree always prefix with `uv run` (a bare `python`/`pytest` imports the
primary checkout's `src`, not the lane's).

## 0. Orient

```bash
# from the repository root
git rev-parse --abbrev-ref HEAD          # expect fix/read-side-seam-primary-primitive-closure
spec-kitty agent tasks status --mission read-side-seam-primary-primitive-closure-01KYKMMT
```

## 1. Census (re-derive, never trust a written count)

```bash
# how many real call sites does a primitive have? per-file import ALIASES resolved,
# definition module excluded. The alias pass is load-bearing: `import X as _p` + `_p(...)`
# yields the call name `_p`, which a literal-name match silently misses.
uv run python - <<'PY'
import ast, pathlib
targets = {"primary_feature_dir_for_mission", "resolve_feature_dir_for_mission",
           "candidate_feature_dir_for_mission", "resolve_planning_read_dir"}
counts, files = {t: 0 for t in targets}, {t: set() for t in targets}
for f in pathlib.Path("src").rglob("*.py"):
    if f.name == "_read_path_resolver.py":       # definition module
        continue
    tree = ast.parse(f.read_text(encoding="utf-8"))
    # per-file alias map: local binding -> canonical target name
    alias = {}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom):
            for a in n.names:
                if a.name in targets:
                    alias[a.asname or a.name] = a.name
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            fn = n.func
            local = fn.id if isinstance(fn, ast.Name) else getattr(fn, "attr", None)
            name = alias.get(local, local if local in targets else None)
            if name in targets:
                counts[name] += 1; files[name].add(str(f))
for t in sorted(targets):
    print(f"{t}: {counts[t]} sites / {len(files[t])} files")
PY
```

Compare against the ledger's per-primitive counts — they must agree (NFR-008, SC-007).

**Authority note for WP08's irreversible delete.** This recipe is a *cross-check*, not the
authority. Attribute-style and dynamic references still escape any single-pass AST counter, so
for the go/no-go on deleting the public wrapper use the gate's own alias-resistant whole-tree
scanner (`tests/architectural/_placement_whole_tree_scan.py`, consumed by
`test_no_read_side_bypass.py`) as the authority, and treat a disagreement between the two as a
stop rather than a rounding error.

## 2. The named gates (targeted only)

```bash
PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest \
  tests/architectural/test_no_read_side_bypass.py \
  tests/architectural/test_resolution_authority_gates.py \
  tests/architectural/test_gate_read_literal_ban.py \
  tests/architectural/test_coord_read_residuals_closeout.py \
  tests/architectural/test_trio_seam_only.py \
  tests/architectural/test_no_write_side_rederivation.py \
  -q
```

Do **not** pipe `pytest`/`mypy` through `| tail` — it masks the exit code. Report exit
codes.

## 3. Step 1 (delegation) — what to expect

After the delegation lands and **before** any call site changes:

```bash
# the two census floors must NOT move — no call site changed
uv run pytest tests/architectural/test_resolution_authority_gates.py -q
```

Any other divergence must be **attributed** (anchoring / backfill recovery / husk /
raising). The single accepted behavioural delta is the seam's bare-slug backfill recovery,
which must be pinned by a test rather than absorbed (FR-003).

## 4. Equivalence and the edge cases

The decisive fixtures (see `research.md` R-01) — a real git repo with a `meta.json`
declaring topology, then compare the blind composition against
`placement_seam(root, handle).read_dir(<PRIMARY kind>)` for composed, bare and mid8 handles:

| Fixture | Expect |
|---|---|
| flat / no coord | equal |
| coord + materialized worktree | equal (a COORD kind resolves to coord) |
| coord + **husk** (no `meta.json`) | equal; the *kind-blind* resolver returns the husk |
| coord branch **deleted** | equal, no raise for a PRIMARY kind; a COORD kind raises |
| **backfilled** (bare primary / composed coord) | **differs — the seam recovers the existing dir; the blind composition returns a non-existent path** |

Build fixtures under the session scratchpad, not a bare `/tmp` path, and remove any
throwaway worktree afterwards.

## 5. Behaviour preservation

```bash
# the mission's own suites plus the surfaces the migration touches
PWHEADLESS=1 SPEC_KITTY_SYNC_MINIMAL_IMPORT=1 uv run pytest \
  tests/merge/ tests/specify_cli/coordination/ tests/specify_cli/status/ -q
uv run ruff check <changed files>
uv run python -m mypy --strict src/specify_cli src/charter src/doctrine   # project mode = what CI runs
```

Project-mode `mypy` is authoritative; a single-file `mypy <file>` spuriously reports `Any`
for cross-package imports and must not be used to justify a cast.

## 6. Documentation deliverable

```bash
PYTHONPATH=. uv run python scripts/docs/check_docs_freshness.py --ci   # expect 0 errors
PWHEADLESS=1 uv run pytest tests/docs/ tests/architectural/test_no_legacy_terminology.py -q
# the frozen stores must be untouched-green (proof neither was edited)
PWHEADLESS=1 uv run pytest tests/architectural/test_glossary_pack_parity.py \
  tests/architectural/test_glossary_pack_no_regression.py -q
```

Regenerate the two gated registries (page inventory + docs retrieval index) after adding the
page; the curated explanation index/TOC are judgement, `docs/architecture/index.md` is
mandatory.

## 7. Baseline reds — classify, never green-wash

Some failures are **pre-existing** on this mission's base. Before treating any red as
yours, reproduce it on the **true mission base** (`git merge-base HEAD upstream/main`) in an
isolated worktree under the session scratchpad, and run only the specific node-ids. A lane
tip is **not** a valid baseline — it already contains the mission's own changes.
