---
affected_files: []
cycle_number: 2
mission_slug: doctrine-consumer-surface-missions-extraction-01KZ6G6H
reproduction_command:
reviewed_at: '2026-08-04T20:40:29Z'
reviewer_agent: unknown
verdict: rejected
wp_id: WP04
---

# WP04 Review — cycle 2 (reviewer-renata, independent re-review)

Verdict: **changes requested** — one blocking item.

Context: cycle 1 rejected on three issues. `ed3377e32` fixes all three at the code
level, and I verified each by execution rather than by reading any report or prior
review. The primitive, the three-way convergence, the exception translation,
`doctrine_package_dir()`'s byte-identity, `__all__`, the AST gate and its two
non-vacuity proofs are all correct. There are no regressions anywhere I looked.

The one blocking item is that the **highest-severity of the three cycle-1 fixes is
not pinned by any test** — the exact failure mode that let it ship undetected the
first time. Cycle-1's Issue 3 closed with "Issues 1 and 2 are both one focused unit
test away from having been caught." Issue 2's pin was built correctly (verified
below). Issue 1's was not.

All commands below were run in the lane worktree with
`uv run --extra test --project . python -m pytest … -q -p no:cacheprovider`.
The tree was restored and `git diff --exit-code` confirmed clean after every mutation.

---

## Blocking

### Issue 1 (cycle 2) — the wheel-layout fix is unpinned: reverting it leaves 264/264 green

`src/kernel/paths.py:83`:

```python
_MISSION_ASSETS_SIBLING_PATTERN = PurePosixPath("*") / _MISSION_ASSETS_DIR_NAME
```

Reverting this to the cycle-1 defect verbatim
(`PurePosixPath("src") / "*" / _MISSION_ASSETS_DIR_NAME`) and re-running

```
tests/kernel  tests/doctrine/test_pack_root_resolver.py
tests/doctrine/test_built_in_location_authority.py
tests/charter/test_missions_root_authority.py
tests/architectural/test_kernel_no_doctrine_import.py
```

gives **264 passed, 4 skipped** — byte-identical to the unmutated baseline. Not one
test moves.

Neither `_MISSION_ASSETS_SIBLING_PATTERN` nor `_MISSIONS_ROOT_SIBLING_PATTERN` is
referenced by any test in the repository (`grep -rn … tests/` → no matches).

The new `TestWheelShapedAnchor` class does test a wheel-shaped anchor, but it hands
`resolve_installed_sibling` a pattern **written inside the test**
(`PurePosixPath("*") / "missions"`). It proves the primitive behaves correctly
*given* the right pattern; it never proves `kernel.paths` *passes* the right one —
and the pattern the caller passes was the entire defect. By the same standard the
gate's own docstring applies to `test_kernel_does_not_import_doctrine` ("a gate that
cannot fail on the one real violation it is nominally guarding is worse than no
gate"), this test cannot fail on the violation it was written for.

The bug is real, not hypothetical. Against a synthetic wheel tree
(`<tmp>/site-packages/kernel/paths.py`, `<tmp>/site-packages/doctrine/missions/software-dev/templates/plan-template.md`),
with `kernel.paths.__file__` monkeypatched to the synthetic anchor and
`SPEC_KITTY_TEMPLATE_ROOT` unset:

```
constant '*/missions'      -> <tmp>/site-packages/doctrine/missions
constant 'src/*/missions'  -> RAISED FileNotFoundError: Cannot locate package mission assets.
```

For contrast, Issue 2's fix **is** correctly pinned — I verified it. Moving the bare
`root` candidate in `_resolve_env_root` back ahead of the
`_MISSION_ASSETS_CHECKOUT_GLOB_PATTERN` glob reds
`tests/kernel/test_paths.py:208::test_template_root_checkout_root_normalizes_to_doctrine_missions`
with the checkout root returned instead of `src/doctrine/missions`. The decoy
fixture (`docs/templates/index.md`) does exactly the job it was added for. That is
the standard Issue 1 needs to meet.

**Why this blocks rather than defers.** WP05 is explicitly chartered to repoint
these very patterns (`MissionsRootNotFound`'s own docstring says so:
"what actually prevents the wrong answer post-WP05 is WP05 *repointing this module's
pattern*"). Handing WP05 a pattern constant that no test binds, on a WP that already
shipped a wrong value for that same constant once, reproduces the cycle-1 conditions
exactly. The Charter Code Review Checklist ("Tests added for new functionality") and
the repo's Sonar expectation ("every new branch/helper needs tests in the same PR")
both point the same way.

**Fix** — the mechanism is ~10 lines and I confirmed it works. In
`tests/kernel/test_paths.py::TestGetPackageAssetRoot`, build the same synthetic
site-packages tree `TestWheelShapedAnchor._build_site_packages` already builds,
`monkeypatch.setattr(kernel.paths, "__file__", str(fake_anchor))`
(`get_package_asset_root` reads `Path(__file__)` at call time, so this binds),
`monkeypatch.delenv("SPEC_KITTY_TEMPLATE_ROOT", raising=False)`, and assert
`get_package_asset_root() == site / "doctrine" / "missions"`. That test reds on the
reverted constant and greens on the committed one — I ran both directions.

Please give `_MISSIONS_ROOT_SIBLING_PATTERN` in
`src/doctrine/missions/repository.py` the equivalent treatment while you are there;
it is unbound by the same argument and is the constant WP05 will actually edit.

---

## Non-blocking — fold if cheap, otherwise file as follow-up

### 2. The AST gate is blind to dotted string literals, and there is a live instance in scope

Confirmed by execution. `collect_forbidden_vocabulary(_KERNEL_ROOT)` returns exactly:

```
[('kernel/schema_utils.py', 96, "string literal 'doctrine'")]
```

`src/kernel/schema_utils.py:88` is `resource = files("doctrine.schemas")` — verbatim
the `importlib.resources.files("<doctrine>")` shape the gate's own docstring names
as the violation it exists to catch — and it is invisible, because
`_scan_file` tests `node.value in _FORBIDDEN_STRINGS` (exact equality) and
`"doctrine.schemas" != "doctrine"`. Note `_FORBIDDEN_IMPORT_ROOTS` does the dotted
split for `Import`/`ImportFrom` nodes, so `import doctrine.x` *is* caught; only the
string-literal dotted form escapes, which is precisely the shape at issue.

I agree with the assessment that this does not block: SC-002 is scoped to
`src/kernel/paths.py`, and `schema_utils.py` is out of WP04's `owned_files` and
predates it (`fa80fa0f9`, mission `charter-mediated-doctrine-selection-01KRTZCA`).
The gate's "Scope of the claim" paragraph is also literally accurate as written.

But the remedy is in a file WP04 *does* own, so please consider folding:
- make the `ast.Constant` check segment/prefix aware
  (`value == s or value.startswith(s + ".")`), and
- add `("kernel/schema_utils.py", 88)` to `_PRE_EXISTING_EXEMPTIONS`, and
- correct that set's docstring, which currently describes **only** the line-96
  path-segment fallback and so under-reports the debt it defers.

Separately: "Tracked as a follow-up" in that docstring carries no issue handle. Per
the repo's deferral discipline it needs a `Follow-up: #NNNN`. (Cycle 1 raised this
too; it is still absent.)

### 3. New fail-open surface: the ancestor walk is unbounded where the base was not

The base `get_package_asset_root()` (`11f36ea6b`) had **no** walk at all —
`Path(str(importlib.resources.files("doctrine") / "missions"))`, `is_dir()`-checked,
else `FileNotFoundError`. The new implementation walks `anchor.parents` all the way
to `/` with `*/missions`. When the intended install is absent, it therefore no
longer fails closed: it can return an unrelated `<ancestor>/<anything>/missions`
several levels up. Contract step 4 says "never falls back to an arbitrary tree."

This is not speculative — `tests/kernel/test_sibling_paths.py::TestFailClosed`'s own
docstring records it: "a plain word like `missions` can (and, on at least one
development machine, did) collide with an unrelated real directory several levels
above `tmp_path`". The tests were namespaced with a UUID to work around it; the
*runtime* has no such guard. Note the collision surface here is strictly larger than
the one cycle 1 flagged for `src/*/missions`, not smaller.

Bounded in practice — both real layouts match at ancestor depth 1–2, long before
reaching user-controlled parents, and `kernel.paths.get_package_asset_root` has a
single production consumer (`src/charter/activation/catalog.py:16`). Worth either a stop
condition on the walk (e.g. halt at the first ancestor that is a `src`/site-packages
level) or an explicit note in the primitive's docstring naming the trade.

### 4. Cycle-1 item 6's second half is still unaddressed and now undocumented

The docstring half was fixed well — `MissionsRootNotFound` now states plainly that
removing the fallback does not by itself make the post-WP05 world safe. Good.

The eager-evaluation coupling was not addressed and is not noted anywhere.
`src/specify_cli/runtime/home.py:114-117` still builds

```python
dev_roots = (
    MissionTemplateRepository.default_missions_root(),
    Path(__file__).parent.parent / "missions",
)
```

so a `MissionsRootNotFound` would propagate out of
`specify_cli.runtime.home.get_package_asset_root()` before the second entry is
tried, replacing an actionable `FileNotFoundError` with an unrelated exception type
at a function called from `init.py`, `bootstrap.py`, `resolver.py` and three
migrations.

I confirmed it is genuinely **not triggerable**: `repository.py` lives at
`<pkg>/missions/repository.py`, so the ancestor `<pkg>` always matches the bare
`"missions"` pattern in every layout where the module is importable from a real
file. A one-line note in `MissionsRootNotFound`'s docstring is sufficient; no code
change needed.

### 5. Minor: per-ancestor glob replaces a single stat

`_first_match` does `sorted(root.glob(pattern))` at every ancestor where
`_resolve_built_in` previously did one `(ancestor / "packs" / "built-in").is_dir()`.
Equivalent for the literal `packs/built-in` pattern, but `*/missions` lists the whole
directory (one `scandir` + N stats on a large `site-packages`) with no caching.
Negligible at current call volumes; noting it only because this repo has been
perf-sensitive about repeated tree scans.

---

## Verified good (by execution, for the record)

- **Three-way convergence complete.** All three call sites delegate to
  `resolve_installed_sibling`: `kernel/paths.py:170`, `doctrine/pack_paths.py:206`,
  `doctrine/missions/repository.py:139`.
- **`doctrine_package_dir()` untouched.** `md5sum` of the file tail from
  `def doctrine_package_dir` is identical on `11f36ea6b` and HEAD
  (`2939317f12151d4e1f285ef4938a6053`). `src/doctrine/drg/migration/extractor.py:33`
  still imports it; used at lines 76 and 119.
- **Exception translation present at both new boundaries** —
  `SiblingPathNotFound → PackRootNotFound` in `_resolve_built_in`,
  `SiblingPathNotFound → MissionsRootNotFound` in `default_missions_root`, the
  latter now covered directly by
  `TestMissionsRootNotFoundFailClosedPath` (both the classmethod and `default()`).
- **`__all__` declared** in `src/kernel/sibling_paths.py:66`
  (`["SiblingPathNotFound", "resolve_installed_sibling"]`) — charter §496 satisfied.
- **Gate non-vacuity holds.** Unfiltered `collect_forbidden_vocabulary(_KERNEL_ROOT)`
  returns exactly the one exempted site, so
  `test_pre_existing_exemption_is_still_a_real_violation` is a real assertion, not a
  tautology. The docstring-position exclusion is by position, not content.
- **Issue-2 fix is properly pinned** — mutation reds the intended test (see above).
- **No regressions.**
  - `tests/kernel` + `tests/doctrine/test_pack_root_resolver.py` +
    `test_built_in_location_authority.py` + `tests/charter/test_missions_root_authority.py`
    + the new gate → **264 passed, 4 skipped**.
  - `tests/doctrine` (full) + `tests/charter/test_builtin_missions_root.py`,
    `test_canonical_root_resolution.py`, `test_missions_root_authority.py`,
    `test_builtin_reader_relocation.py` → **2590 passed, 8 skipped**.
  - `tests/architectural/test_no_legacy_terminology.py` + `test_layer_rules.py`
    → **27 passed**.
- **NFR-004 clear.** I suspected the new gate file might need shard-map or
  gate-coverage-baseline registration and checked:
  `tests/architectural/test_arch_shard_marker_completeness.py` +
  `test_gate_coverage.py` → **38 passed**. No baseline regeneration required;
  `_gate_coverage_baseline.json` is correctly absent from the diff.
- **ruff clean** on all eight changed files. **mypy clean** on the four changed
  source files (`sibling_paths.py`, `paths.py`, `pack_paths.py`, `repository.py`).
- **Scope.** Seven source/test files plus the new `tests/kernel/test_sibling_paths.py`;
  all within `authoritative_surface: src/kernel/`, `owned_files`, or the WP text's
  explicit "or a new sibling module" allowance. No `kitty-specs/` modification. No
  scope creep.

---

## What I deliberately did not require

- Any fix to `kernel/schema_utils.py` itself — genuinely pre-existing and outside
  `owned_files`. Exempting rather than silently weakening the gate remains the right
  call.
- Substring matching in the gate. Segment/prefix-aware matching (item 2) is the
  narrow correction; broad substring matching on `"plan"`/`"research"` would be
  unusable.
- The full `tests/architectural/` sweep — CI owns that; I ran the specific gates
  that could plausibly be affected.
- Any change to `contracts/kernel-resolution-primitive.md`.
