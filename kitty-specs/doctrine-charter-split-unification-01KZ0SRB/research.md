# Phase 0 Research & Decisions — Doctrine-Charter Split Single-Path Authority

Consolidated from the pre-spec (planner-priti / paula-patterns / architect-alphonso) and post-plan
(paula-patterns / planner-priti / python-pedro) adversarial squads. Every anchor below is verified against
live code on `feat/doctrine-charter-split-unification` (base `8466727eb`).

## D1 — Charter path/read authority already has its home; FR-001 is near-empty

`charter/bundle.py` already defines **and exports** `CHARTER_YAML` (`:35`) and `CHARTER_MD` (`:48`) in
`__all__` (`:467`), and `charter/context.py` already imports them (pre-deduped by #3146). **Decision:** FR-001
does **not** get its own lane — it folds into the first IC-01 WP as a confirm/guard; the four surface repoints
(FR-002/003/004/006) start in parallel immediately (file-disjoint, no shared new symbol to wait on). The
durability comes from the FR-016 gate (D6), not from a front-loaded constant WP.

## D2 — No genuine write-scope collisions (file granularity)

`lanes.json write_scope` is an **explicit per-file path list**, not a directory glob → lanes collide only on
the *same path*. Verified false alarms: (a) the IC-02 emitter is `charter/compiler.py:441`
(`write_compiled_charter`), **not** `synthesize_pipeline.py` — so IC-02 (emitter) and IC-04 (FR-008 edge in
`synthesize_pipeline.py:68`) are **distinct files**; (b) FR-016/FR-008 gates are **new test files**;
(c) `src/charter/**` and `src/specify_cli/retrospective/**` call `load_meta` **zero** times, so IC-03 is fully
file-disjoint from IC-01/IC-02/IC-04. **Decision:** the per-file "fold the repoint into the surface WP"
discipline holds; cross-IC lanes parallelize safely.

## D3 — FR-005 (retrospective → charter.yaml governance): no layer inversion; one omit-mechanism fix

`GovernanceConfig` (`charter/schemas.py:135`) composes nested pydantic sub-models and imports peers **within**
the charter layer. **Decision:** re-author a pure-data `RetrospectiveGovernance` sub-model **into**
`charter/schemas.py` (bool / `Literal` / nested permissions — zero `specify_cli` import; the existing
`specify_cli.retrospective.policy.RetrospectivePolicy` is **not** imported upward). Emitter (FR-005b) stays
in-layer via `charter.sync.load_governance_config` (`sync.py:233`) feeding `write_compiled_charter`
(`compiler.py:441`/`:601`). Resolver (FR-005c) is a **downward** import: `specify_cli/retrospective/{policy,mode,gate}.py`
imports `charter.charter_yaml_io.load_charter_yaml` + `charter.bundle`, reads `governance.retrospective` as a
dict, and feeds it as highest-precedence through the existing `_apply_block_to_policy` (`policy.py:381`).
**Refinement (must fold):** the omit-when-empty pruner `_prune_optional_empties` (`schemas.py:346`) is
**list-only** (`isinstance(value, list) and not value`) — it will **not** omit an empty `retrospective`
dict/None, leaking a default block into every `charter.yaml` and breaking NFR-005 byte-stability. Extend the
pruner to drop an allowlisted key whose value is `None`/empty-dict (or model the field `| None` with a
None-drop branch). Ship a byte-stability regression test.

## D4 — FR-007 (meta.json fail-closed): reuse core/paths; keep the import function-local

`core/paths.py` already owns `MissionMetaReadError` (`:506`) and `_load_meta_fail_closed` (`:638`, which lazily
imports `load_meta` inside the function at `:655` to break the pre-existing `core/paths ↔ mission_metadata`
cycle). **Decision:** promote `_load_meta_fail_closed` to a public `load_meta_fail_closed` in `core/paths`
(or have `mission_metadata` delegate to it) — **one home, no second authority**. **Guard:** the `load_meta`
import MUST stay function-local during promotion, or the cycle re-forms.

**Two `load_meta` definitions hazard:** there are **two** distinct functions — `mission_metadata.py:275`
(`load_meta(feature_dir)`) and `task_utils/support.py:599` (`load_meta(meta_path: Path)`), different
signatures. The FR-007 **caller census** (110 `load_meta(` sites across ~55 files) MUST disambiguate which
function each site targets, or routing mis-wires the `task_utils` callers. This is a census acceptance
criterion.

## D5 — IC-03 sub-slicing (census + reader-publish + parallel routing lanes)

Routing ~dozens of files in one lane is an unreviewable diff. **Decision:** (1) census artifact (D4, gating),
(2) publish the public reader in `core/paths`+`mission_metadata`, then (3) parallel routing lanes sub-sliced by
subsystem (coordination+migration / merge+status+dashboard+cli / mission_runtime+runtime). The
`mission_runtime+runtime` lane turns the two red `test_mission_status_aggregate::TestLoadCoordUnavailableFailsClosed`
tests green via `lifecycle_phase.py` (C-004 owns these reds). Preserve deliberately-silent callers
(`load_meta_or_empty`, `on_malformed="none"`).

## D6 — FR-016 anti-regression gate: AST census + understated allowlist + doctrine-scope decision

**Decision:** detection is **AST path-construction literals** (a `.kittify/charter/charter.{yaml,md}` string
inside a `Path(...)` construction / const assignment), **not** raw text grep (else it floods on ~161
docstring/prose mentions). The frozen **shrink-only allowlist** is the right mechanism (a hard zero is
unshippable). The plan's stated allowlist (`upgrade/migrations/**` + C-003 prose readers) is **understated** —
real path-builders also live at `invocation/empty_charter.py:60` (`_CHARTER_BUNDLE_PATH`),
`charter_runtime/lint/checks/org_layer.py:291`, `doctrine/versioning.py:190,451`,
`doctrine/spdd_reasons/activation.py:49`. **Open decision the WP must make:** does the gate police
`src/doctrine/**` (then allowlist `versioning.py`/`activation.py`) or scope to `charter/`+`specify_cli/`?
The WP runs a full AST census to seed the allowlist so FR-016 lands green, and lands **after** IC-01 repoints
+ FR-005c resolver (sink ordering).

## D7 — FR-010 packs out-of-tree mechanism: hatchling build hook; the spike MUST run

`packs/` is a repo-root `doctrine`-sibling; a naive `force-include ../../packs` escapes the project root and
hatchling refuses it. `_resolve_built_in` (`pack_paths.py:195`, step 3) expects `files("doctrine").parent /
"packs" / "built-in"` (a site-packages sibling — the monorepo wheel already achieves this via root
`force-include`). The doctrine wheel's `kernel` dependency is a **real import-closure need** (`resolver.py:32`,
`missions/primitives.py`, `shared/schema_utils.py` all `from kernel...`). **Decision:** use a hatchling custom
build hook (`hatch_build.py` implementing `BuildHookInterface.initialize`, injecting a computed absolute
`force_include` for the sibling `packs/`). **Guard (must fold):** the FR-010 closure test proves manifest
**shape** only (C-002 forbids CI building the nested wheel), so WP acceptance MUST include an **actually
executed** `hatch build` of the nested doctrine wheel with the built wheel showing `packs/built-in/` as a
`doctrine` sibling — recorded here — else the groundwork is inert.

### D7 spike result

- **Status: RESOLVED — hatchling custom build hook, executed and verified (WP12).** The primary mechanism
  (hatchling `BuildHookInterface.initialize` custom build hook, `src/doctrine/hatch_build.py`) **worked** — no
  fallback was needed. `spec-kitty-kernel` (`src/kernel/pyproject.toml`) was minted with **zero** first-party
  dependencies, and `src/doctrine/pyproject.toml` now declares `spec-kitty-kernel>=1.0.0,<2.0.0`.

- **Executed commands** (real, not simulated — run from this worktree, `.venv` with `hatchling`/`hatch` pip-installed
  as dev tooling only, not project dependencies):
  ```bash
  cd src/kernel && hatch build -t wheel     # -> dist/spec_kitty_kernel-1.0.0-py3-none-any.whl
  cd src/doctrine && hatch build -t wheel   # -> dist/spec_kitty_doctrine-1.0.0-py3-none-any.whl
  ```

- **Two real-build findings the spike surfaced (both fixed in-mission, not deferred):**
  1. **`packages = ["src/doctrine"]` / `packages = ["src/kernel"]` matched nothing.** Both nested
     `pyproject.toml` files were originally copy-pasted from the repo-root shape, which resolves `packages`
     relative to the *repo root* (where `src/doctrine` is a real subdirectory). But each nested pyproject's own
     project root **is** `src/doctrine/` (respectively `src/kernel/`) — there is no `src/doctrine/src/doctrine/`
     subtree under it — so the first executed `hatch build -t wheel` for doctrine produced a wheel containing
     `packs/` **but zero `doctrine/*.py` files** (verified via `unzip -l`: only `packs/**` and
     `*.dist-info/**` present, no top-level `doctrine/` entry at all).
  2. **A blanket `sources = {"" = "doctrine"}` rename (the first fix attempt) broke D7 itself.** hatchling's
     `get_distribution_path` applies the `sources` remap to *every* computed distribution path, including
     entries added via a build hook's dynamic `force_include` — so the packs `force_include` entry
     (`"<abs packs path>" -> "packs"`) got the same rename applied and landed at `doctrine/packs/...` (nested
     *under* doctrine) instead of as a sibling. Verified via `unzip -l`: `doctrine/packs/built-in/*.yaml`
     present, plain `packs/*` absent.
  3. **Final fix:** no `packages`/`sources`/`include` at all in either nested pyproject's `[wheel]` table.
     `hatch_build.py`'s hook force-includes every top-level child of `self.root` under `doctrine/<name>`
     (skipping `pyproject.toml`, `hatch_build.py`, `dist`, `__pycache__`, `.git`) *and* the repo-root `packs/`
     under `packs`, with fully explicit destination paths that bypass hatchling's `sources` rename machinery
     entirely (both entries flow through the same `force_include` dict, so there is no rename to collide).
     `src/kernel/pyproject.toml` uses the simpler `sources = {"" = "kernel"}` + `include = ["**/*"]` form
     (no packs-equivalent sibling, so no force_include collision risk there).

- **Final wheel contents (`unzip -l dist/spec_kitty_doctrine-1.0.0-py3-none-any.whl`), confirmed real, not a
  manifest-shape assertion:**
  ```
  doctrine/__init__.py, doctrine/resolver.py, ... (89 doctrine/*.py files total)
  packs/built-in/action.graph.yaml, packs/built-in/agent_profile.graph.yaml, ... (276 packs/built-in/* entries)
  spec_kitty_doctrine-1.0.0.dist-info/{METADATA,WHEEL,RECORD}
  ```
  Top-level wheel entries: exactly `doctrine/`, `packs/`, `spec_kitty_doctrine-1.0.0.dist-info/` — `packs/` is a
  true sibling of `doctrine/`, not nested under it (`doctrine/packs` count: 0). `METADATA` shows
  `Requires-Dist: spec-kitty-kernel<2.0.0,>=1.0.0`, confirming FR-010's dependency declaration made it into the
  built wheel's metadata, not just the source pyproject.toml.

- **Functional install-and-import closure proof (beyond manifest shape):** built both wheels, `pip install`ed
  `spec_kitty_kernel-1.0.0-py3-none-any.whl` then `spec_kitty_doctrine-1.0.0-py3-none-any.whl` into a scratch
  venv (`python3.11 -m venv`), then ran:
  ```python
  import doctrine, kernel                       # both import cleanly from site-packages
  import doctrine.resolver as resolver          # exercises `from kernel.paths import ...` (the real import-closure need)
  from doctrine.pack_paths import resolve_pack_root
  p = resolve_pack_root("built-in")             # the actual production function pack_paths._resolve_built_in feeds
  assert p.name == "built-in" and p.parent.name == "packs"   # PASSED
  ```
  `resolve_pack_root("built-in")` resolved to `<venv>/lib/python3.11/site-packages/packs/built-in` — i.e. the
  installed-wheel resolution tier (`files("doctrine").parent / "packs" / "built-in"`) succeeded against the
  real, installed, non-editable site-packages layout produced by these two wheels. This is the strongest
  available evidence short of a PyPI-published kernel package.

- **No fallback invoked.** D10's WP12 fallback-governance note (HiC decision required if a fallback is used) is
  **not triggered** — the primary build-hook mechanism worked after the two real-build fixes above, both of
  which are packaging-shape corrections to the nested pyproject.toml files, not scope changes to the D7
  mechanism itself.

- **C-002 confirmed intact:** the repo-root `pyproject.toml`'s `packages` list is unchanged (still lists
  `src/kernel`, `src/doctrine`, `src/charter`, ...); grepped every `.github/workflows/*.yml` for `hatch build` /
  `python -m build` lines containing `src/doctrine` — none found (both existing `python -m build` invocations,
  in `release.yml` and `ci-quality.yml`, run from the repository root and build `spec-kitty-cli`, never `cd
  src/doctrine`). `hatch build`/`hatch` itself is dev-only tooling installed into the local `.venv` for this
  spike's verification and is not a declared project dependency anywhere.

## D8 — Sequencing (dependency DAG, no cycles)

`FR-005a→FR-005b→FR-005c`; `FR-007 census→publish reader→{routing lanes}`; `packs-spike→FR-010`;
`{IC-01 repoints, FR-005c}→FR-016 (sink)`; `FR-012→FR-014 (#3102 closeout)`. Free parallel first-wave:
the 4 IC-01 repoints, FR-008, FR-009 kernel pyproject, FR-012/FR-013 CI hygiene, FR-011 ADR (soft-after
FR-008). Critical path (depth): the IC-02 chain. Width long-pole: IC-03 routing. FR-015 is a **timeboxed
investigation with a deferred issue-matrix verdict**, not a code WP (default defer-with-reason).

## D10 — Post-tasks squad corrections (reviewer-renata + debugger-debbie)

- **WP01 reclassified (blocking fix):** `context.py:249` is a **legitimate C-003 prose-presence gate**, not a
  residual to retire. It already keys authority on `charter.yaml` (renders when present, precedence) while
  keeping `charter.md` as a readable secondary (md-only still renders; comment `:207-220` documents a strict
  yaml-only gate regresses **26** `-k charter` fixtures). FR-002 reframed to **scope + pin** (four-cell
  characterization + precedence assertion + comment clarification); **no** behaviour change, **no** fixture
  migration, **no** fake red. The genuine residual *authority*-presence readers are FR-003/004/006.
- **WP04 is a characterization pin, not a red:** `_status_collectors.py:72-87` already resolves the md-only
  shape today → the test is green-first (pin), not ATDD-red. The "declare unsupported → error" escape is a
  support-scope **product decision routed through the HiC/issue-matrix**, not implementer-unilateral.
- **WP07/09 census anti-omission:** the NFR-003 "full census" is self-referential (iterates the WP07 census),
  so an omitted `load_meta(` site leaks yet passes. Require a **grep-count reconciliation** (row-count ==
  every `load_meta(` occurrence; each row classified + tagged with which of the two defs it targets — D4). The
  WP09 contract is driven from that reconciled set and fails on a new unclassified site. (Repo memory:
  occurrence-map undercount trap.)
- **#3140 verdict timing:** the issue-matrix verdict finalizes on **WP09** (fail-closed lands there), not WP07;
  WP08/WP09 carry `tracker_refs: ['3140']`; WP07's row stays `(pending)` until 08/09 land.
- **WP11 gate non-vacuity:** each allowlist entry carries an inline justification (no blanket globs); the
  self-mutation proof injects the literal into a **non-allowlisted** module (and adding a file to the allowlist
  must not be a way to green a real violation).
- **WP12 D7 fallback governance:** invoking any packs-mechanism fallback (esp. deferring functional
  packs-carry) is an **HiC decision recorded in the issue-matrix**; if deferred, SC-005 is re-scoped in writing
  and the closure test's packs assertion is not silently dropped (it becomes an explicit kernel-dep-only state).
- **WP13 ADR scope:** claim "zero `specify_cli` **import** entanglement, per WP10's AST gate" — not a blanket
  "zero entanglement".
- **WP14 not-skipped guard:** add a mechanical assertion that the parity test does **not** skip (both fixture
  paths exist / CI `-rs` skip-report), so "ran green" is enforced, not eyeballed; FR-013 repoints **both**
  `REFERENCE_PATH` and `AGENT_REFERENCE_PATH`.
- **WP05 red timing:** case (a) "emit `governance.retrospective`" is the committed-first red; case (b)
  "no-config → byte-identical `charter.yaml`" goes red only **after** the schema field lands (the NFR-005
  pruner guard), not before.

## D9 — Tracker hygiene (DIR-012 + coord issue-matrix)

Each folded issue (#3150, #3140, #3149, #3107, #3102) gets an issue-matrix row (coord worktree) **and** a
DIR-012 HiC assignment + mission-naming tracker comment when its owning WP starts. Memory: WP approval
hard-fails until each row's verdict is filled in the coord worktree — `tasks-finalize` seeds the rows.
