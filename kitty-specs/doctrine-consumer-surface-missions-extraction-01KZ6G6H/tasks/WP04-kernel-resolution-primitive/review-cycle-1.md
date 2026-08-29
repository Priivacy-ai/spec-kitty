---
affected_files: []
cycle_number: 1
mission_slug: doctrine-consumer-surface-missions-extraction-01KZ6G6H
reproduction_command:
reviewed_at: '2026-08-04T18:27:19Z'
reviewer_agent: reviewer-renata
verdict: rejected
wp_id: WP04
---

# WP04 Review — cycle 1 (reviewer-renata)

Verdict: **changes requested**. The primitive itself, the three-way convergence, the
exception translation, `doctrine_package_dir()`'s byte-identity, `__all__`, and the AST
gate are all correct and well-argued — I verified each by execution, not by reading the
report. Three blocking items remain, all in the *sibling-path pattern* the callers hand
to the primitive, plus the absence of any direct test coverage that would have caught
them. WP05 will repoint exactly these constants, so the shape has to be right before it
builds on top.

Everything below was reproduced in the lane worktree with
`uv run --extra test --project . …`.

---

## Blocking

### Issue 1 — `_MISSION_ASSETS_SIBLING_PATTERN = "src/*/missions"` makes the installed-wheel leg unresolvable

`src/kernel/paths.py`:

```python
_MISSION_ASSETS_SIBLING_PATTERN = PurePosixPath("src") / "*" / _MISSION_ASSETS_DIR_NAME
```

In a wheel install there is no `src/` directory: `[tool.hatch.build.targets.wheel]
packages = ["src/kernel", …, "src/doctrine", …]` maps `src/doctrine` → `doctrine`, so the
installed layout is `site-packages/{kernel,doctrine}/…`. The pattern therefore matches at
no ancestor and at no site-packages level, and `get_package_asset_root()` raises
`FileNotFoundError` where it previously returned `site-packages/doctrine/missions` via
`importlib.resources.files("doctrine") / "missions"`.

Reproduced against a synthetic site-packages tree
(`site-packages/kernel/paths.py`, `site-packages/doctrine/missions/software-dev/templates/plan-template.md`,
`site-packages/packs/built-in`):

```
pattern 'src/*/missions'     -> RAISED SiblingPathNotFound
pattern '*/missions'         -> <site-packages>/doctrine/missions
pattern 'packs/built-in'     -> <site-packages>/packs/built-in
```

`*/missions` also resolves correctly from the real editable checkout (ancestor `src/`
matches `src/doctrine/missions`), so the `src/` segment buys nothing and costs the wheel
leg. Two consequences beyond the outright failure:

- A wheel installed into a venv that happens to sit *inside* any directory containing
  `src/*/missions` resolves to that source tree instead of the installed package. The old
  `files("doctrine")` lookup was immune to this.
- Contract `contracts/kernel-resolution-primitive.md` step 3 ("Installed wheel") is
  required to work for the converged call sites; for this one it cannot.

This is masked today only because `kernel.paths.get_package_asset_root()` has exactly one
production consumer — `src/charter/activation/catalog.py:185` (`_get_package_asset_root().parent`),
reached as the *third* fallback inside `resolve_doctrine_root()` after two earlier steps
that succeed in both editable and wheel layouts. `specify_cli.runtime.home.get_package_asset_root()`
is a separate, untouched implementation, which is why the CLI and the distribution tests
stay green. Masked is not fixed, and WP05 shifts which fallbacks fire.

**Fix**: choose a pattern that is valid in both layouts (`*/missions` satisfies both from
the `src/kernel/paths.py` anchor), and add a test that pins the wheel-shaped anchor
(see Issue 3).

### Issue 2 — `_resolve_env_root` regresses the documented `SPEC_KITTY_TEMPLATE_ROOT=<checkout root>` shape

Old candidate order (base branch):

```
root/missions, root/src/doctrine/missions, root.parent.parent/doctrine/missions, root, root/src/specify_cli/missions
```

New order:

```
[root/missions, root] + sorted(root.glob("src/*/missions")) + (root.name == "missions" ? sorted(root.parent.parent.glob("*/missions")) : [])
```

Bare `root` moved from 4th to 2nd — ahead of the `src/*/missions` glob that replaces the
old candidates 2 and 3. Combined with the widened `_looks_like_missions_root` (old:
required a *mission-type-named* subdirectory; new: any `*/templates/*.md`), the real
repository root now passes the sniff on `docs/templates/index.md` and short-circuits.

Executed both versions against this checkout with `SPEC_KITTY_TEMPLATE_ROOT=<worktree root>`:

```
OLD -> …/lane-b/src/doctrine/missions
NEW -> …/lane-b                        # the checkout root itself
```

That is the shape `README.md:201` (`export SPEC_KITTY_TEMPLATE_ROOT="$(pwd)"`),
`docs/api/environment-variables.md:38`, `tests/conftest.py:789` and
`tests/test_isolation_helpers.py:112` all use. `src/charter/activation/catalog.py:185` then takes
`.parent` of it, so a wrong answer here becomes a wrong doctrine root.

`tests/kernel/test_paths.py::…::test_template_root_checkout_resolves_doctrine_missions`
(~line 180) exists precisely to pin this and asserts `== missions`. It stays green only
because its synthetic `tmp_path` checkout contains no `*/templates/*.md` decoy one level
under the root, which the real repository does. Per the repo's own realistic-test-data
discipline, that fixture is the reason the regression is invisible, not evidence there
isn't one.

**Fix**: order the bare-`root` candidate after the glob (as the base did), and/or tighten
the sniff so an arbitrary `*/templates/*.md` does not qualify a directory as a missions
root. The generic-by-glob approach is right; only the ordering and the looseness are
wrong. Extend the existing test so its fixture carries the decoy.

### Issue 3 — `src/kernel/sibling_paths.py` has no direct test coverage

There is no `tests/kernel/test_sibling_paths.py`. The new module's behaviour is exercised
only transitively through three callers' pre-existing tests, and the following legs have
no assertion anywhere:

- the `env_override` branch as a primitive-level contract,
- the wheel-shaped anchor (`site-packages/<pkg>/<mod>.py`) — the leg Issue 1 breaks,
- `_first_match`'s sorted-multi-match determinism (the whole reason globs were introduced),
- `SiblingPathNotFound`'s `sibling_relative_path` / `anchor_file` attributes,
- `MissionsRootNotFound` — the new fail-closed path in `default_missions_root()` is never
  reached by any test.

Charter Code Review Checklist ("Tests added for new functionality") and the repo's Sonar
expectation ("every new branch/helper needs tests in the same PR") both apply. Concretely:
Issues 1 and 2 are both one focused unit test away from having been caught.

---

## Non-blocking — fold if cheap, otherwise file as follow-up

### 4. Step 3 of the primitive is unreachable dead code, and one test is mislabelled

`resolve_installed_sibling` documents a 4-step order, but step 3 probes
`anchor.parent.parent`, which is *always* a member of `anchor.parents` — so step 2's loop
has already tried that exact directory. Verified for
`/x/site-packages/kernel/paths.py`, `/a/b/c/d/e.py`, `/r/src/doctrine/missions/repository.py`:
`parent.parent in parents == True` in every case. Instrumenting `_first_match` during a
real `get_package_asset_root()` call shows the ancestor walk answering at the repo root
and step 3 never consulted.

This also means the rewritten
`tests/doctrine/test_pack_root_resolver.py::test_installed_resolves_site_packages_sibling`
no longer tests what its name and docstring claim ("step (3) fires", "the shared kernel
primitive … derives the installed-wheel sibling from `Path(__file__).resolve().parent.parent`").
Traced with the same fixture the test builds: probes are
`[<site>/doctrine, <site>]`, resolution comes from the ancestor walk, step 3 is not
reached. Either give step 3 a genuinely different probe than the walk, or drop it and
correct the three docstrings (module docstring, `_resolve_built_in`, and this test) that
assert a distinct installed leg. Note the original `_resolve_built_in` step 3 was *not*
redundant — it used `files("doctrine").parent`, a different path source from the
`__file__` walk. That distinction was lost in the extraction.

### 5. The AST gate's exact-string match misses the shape it was written for

`_scan_file` matches `node.value in _FORBIDDEN_STRINGS` (exact equality). Exact matching
is the right call — substring matching on `"plan"` / `"research"` / `"documentation"`
would be unusably noisy — but it leaves a concrete hole in the same file the gate
exempts: `src/kernel/schema_utils.py:85` is

```python
resource = files("doctrine.schemas")
```

i.e. verbatim the `importlib.resources.files("<doctrine>")` shape the gate's own docstring
names as the violation it exists to catch, uncaught because the literal is
`"doctrine.schemas"` rather than `"doctrine"`. The `_PRE_EXISTING_EXEMPTIONS` docstring
describes only the line-96 path-segment fallback and does not mention this second site,
so the exemption under-reports the debt it is deferring. Consider a segment/prefix-aware
check (`== s`, `startswith(s + ".")`, or `s in value.split("/")`) and name both sites in
the exemption text.

Also: "Tracked as a follow-up" in that docstring carries no issue handle. Per the repo's
deferral discipline a deferral needs a `Follow-up: #NNNN` reference.

### 6. `default_missions_root()`'s fail-closed rationale does not hold as written

The direction is right and the contract does demand fail-closed, but the stated reason —
that `Path(__file__).parent` "no longer contains any data" after WP05 — is not what the
new code protects against. Post-WP05, `src/doctrine/missions/` still exists (the 11 `.py`
logic modules stay there per `occurrence_map.yaml`), so the ancestor walk with
`_MISSIONS_ROOT_SIBLING_PATTERN = "missions"` still matches at ancestor `src/doctrine` and
still returns the data-less package directory. What prevents the wrong answer is WP05
repointing the *pattern*, not the removal of the fallback. Please correct the docstring
and the `MissionsRootNotFound` class docstring so WP05 is not misled into thinking the
fail-closed change already covers it.

Separately, the removal converts a previously non-raising call into a raising one at
`src/specify_cli/runtime/home.py:116`, where `default_missions_root()` is evaluated
*eagerly* while building the `dev_roots` tuple:

```python
dev_roots = (
    MissionTemplateRepository.default_missions_root(),
    Path(__file__).parent.parent / "missions",
)
```

A `MissionsRootNotFound` there propagates out of
`specify_cli.runtime.home.get_package_asset_root()` before the second `dev_roots` entry
(`src/specify_cli/missions`) is ever tried, defeating that function's own fallback. Not
triggerable today, but it is a live coupling worth either lazifying or noting.

### 7. `_looks_like_missions_root` widening

Old: required one of four mission-type-named subdirectories to hold content. New: any
`*/templates/*.md`, `*/command-templates/*.md`, or `mission-steps/*/*/prompt.md`. Removing
the hardcoded vocabulary is the point of the WP and the glob approach is correct, but the
replacement is materially more permissive and is the proximate cause of Issue 2. Worth a
deliberate second look at how loose the sniff should be.

---

## Verified good (by execution, for the record)

- **Resolution order + `.resolve()`**: `anchor_file.resolve()` precedes the `.parents`
  walk (`src/kernel/sibling_paths.py`), matching the contract. Order is env → walk →
  (nominal) installed → fail-closed.
- **`env_override` design choice — sound, and I'd keep it.** The contract's Inputs table
  says the primitive "receives the resolved override value" and "does not know
  environment-variable *names*"; caller-side joining is the natural reading of that, and
  the reasoning is correct on the facts: `SPEC_KITTY_PACKS_ROOT` denotes the packs root
  (joins `built-in` only) while the ancestor walk needs `packs/built-in`, so a single
  shared join semantic would be wrong for one site. This moves knowledge *out* of the
  primitive rather than smuggling it in — the opposite of a leak. Only quibble: the
  parameter name reads like a raw env value; `env_candidate_dir` would be truer. The
  contract's step-1 wording ("joined with `sibling_relative_path`") is looser than the
  Inputs table and should probably be reconciled, but that is a contract-text nit, not a
  code defect.
- **`doctrine_package_dir()` untouched**: `md5sum` of the file tail from
  `def doctrine_package_dir` is identical on base and HEAD
  (`2939317f12151d4e1f285ef4938a6053`); `pack_paths.__all__` unchanged;
  `src/doctrine/drg/migration/extractor.py:33` still imports it and uses it at lines 76
  and 119.
- **Exception translation**: forced `SiblingPathNotFound` from a patched
  `resolve_installed_sibling` — `resolve_pack_root("built-in")` raises `PackRootNotFound`,
  and `built_in_dir(ArtifactKind.from_plural("directives"))` raises `PackRootNotFound`, so
  `pack_validator.py:793`'s `except (PackRootNotFound, BuiltInContentDirNotAvailable)`
  still catches. Exercised, not inferred.
- **`__all__`**: `src/kernel/sibling_paths.py:49` declares
  `__all__ = ["SiblingPathNotFound", "resolve_installed_sibling"]` — both public symbols.
  Charter `charter.md:496` satisfied.
- **Gate is not unpassable**: 18 docstring nodes across `src/kernel/` (5 in `paths.py`)
  mention the forbidden vocabulary and would false-positive without the positional
  exclusion. The exclusion is by position (`ast.Expr(Constant(str))` first in a
  Module/ClassDef/FunctionDef/AsyncFunctionDef body), not by content, and
  `test_walker_ignores_docstrings_and_prose` exercises module docstring + function
  docstring + comments. Load-bearing, and correctly so.
- **Gate is not vacuous**: replaced `sibling_relative_path=_MISSION_ASSETS_SIBLING_PATTERN`
  at `src/kernel/paths.py:141` with `PurePosixPath("doctrine") / "missions"` — gate reds
  with `kernel/paths.py:141 — string literal 'doctrine'`, naming the exact site. Restored;
  `git diff --exit-code` clean. (The implementer's report cites line 143, which is the
  `except` line in the committed file — a mutation there is an `IndentationError`, not a
  gate red. Immaterial to the conclusion, but the cited coordinate is off.)
- **Exemption is genuinely anti-vacuous**: neutralised the `"doctrine"` literal at
  `src/kernel/schema_utils.py:96` — `test_pre_existing_exemption_is_still_a_real_violation`
  reds with "shrink the exemption set instead of leaving a stale, vacuous entry".
  Restored clean. The line-number pin is brittle to edits above line 96, but it fails
  *loud* in both directions (main gate reds at the new line; anti-vacuity test reds at the
  old one), which is the correct trade against a file-level blanket escape. Acceptable as
  built; the noise cost should be paid down by fixing the underlying coupling rather than
  by widening the exemption.
- **No domain vocabulary survives** in `get_package_asset_root()`: no mission-type names,
  no `src/doctrine/missions` or `src/specify_cli/missions` literal. Gate green (5 passed).
- **`tests/charter/test_missions_root_authority.py` passes**, and no consumer of
  `default_missions_root()` catches the old silent-fallback path (see item 6 for the one
  live coupling).
- **No regression in the spot-checked set**: `tests/kernel`,
  `tests/doctrine/test_built_in_location_authority.py`,
  `tests/doctrine/test_pack_root_resolver.py`,
  `tests/charter/test_missions_root_authority.py`,
  `tests/charter/test_context_render_seams.py` → **271 passed, 4 skipped**.
- **ruff clean** on all seven changed files. **mypy**: one error,
  `tests/kernel/test_paths.py:572` (`to_posix` / `PurePosixPath`) — confirmed pre-existing
  by running mypy on the base blob copied in place: same error at its line 546, and
  `to_posix` is untouched by this diff (0 diff hits). Implementer's claim verified.
- **NFR-004**: `tests/architectural/_gate_coverage_baseline.json` is not in this diff.
  Confirmed.
- **Scope**: the two extra test files are justified — both mocked
  `kernel.paths.importlib.resources.files`, a seam this WP legitimately retires, and both
  were repointed rather than deleted. `src/kernel/sibling_paths.py` is covered by
  `authoritative_surface: src/kernel/` and the WP text's explicit "or a new sibling
  module". No scope creep.
- **Issue matrix**: 14/14 rows carry verdicts, none `unknown`. `#3091` is
  `in-mission`/WP05 — correct, non-terminal.
- **Pre-review-gate `.kittify` finding**: environmental, as reported.
  `src/specify_cli/mission.py` is not in this diff at all (`git diff --name-only` lists
  seven files, none of them that one).
- **Bulk-edit glob correction** (`86ba269de`, `src/doctrine/missions/*.py` →
  `manual_review`): I have no objection. The glob's own reason text described an edit
  ("repointed … but not moved"), a narrower `repository.py` exception already said
  `manual_review`, and the `moves:` block still carries the do-not-move intent for the
  data directories. Per `code_symbols: manual_review` I examined each replaced function
  body per site rather than accepting a mechanical change; that examination is what
  produced Issues 1, 2 and item 4.

---

## What I deliberately did not require

- A fix for `kernel/schema_utils.py`'s coupling (both line 85 and line 96). Genuinely
  pre-existing, from `charter-mediated-doctrine-selection-01KRTZCA` WP07, and outside
  WP04's `owned_files`. Exempting it rather than silently weakening the gate was the right
  call.
- Full `tests/architectural/` — CI owns that sweep; I ran the new gate file directly.
- Any change to the contract document itself (the step-1 env wording).
- Substring matching in the gate. The narrowing is documented honestly in the gate's own
  "Scope of the claim" paragraph, and broad substring matching would be worse.
