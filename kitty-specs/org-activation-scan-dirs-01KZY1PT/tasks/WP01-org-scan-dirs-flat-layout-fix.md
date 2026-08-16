---
work_package_id: WP01
title: _org_scan_dirs flat-layout fix, red-first
dependencies: []
requirement_refs:
- FR-001
- FR-002
- FR-003
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
- T006
history: []
authoritative_surface: src/charter/kind_vocabulary.py
create_intent:
- tests/charter/test_org_scan_dirs_activation_regression.py
execution_mode: code_change
owned_files:
- src/charter/kind_vocabulary.py
- tests/charter/test_kind_vocabulary_scan_roots.py
- tests/charter/test_org_scan_dirs_activation_regression.py
tags: []
---

## Objective

Make `charter.kind_vocabulary._org_scan_dirs` (`src/charter/kind_vocabulary.py:200-209`)
scan the flat org-pack layout (`<root>/<plural>`) that every real org pack uses, in
addition to the legacy `<root>/<plural>/built-in` layout it already scans — closing the
defect where activating an org pack's own artifact by its own config-stem silently fails
to survive `filter_graph_by_activation`. Prove the fix with a red-first regression test at
the activation-filter level (FR-002) and extend the existing unit-level coverage (FR-003).

## Context

This is the **entire mission**: one work package, one PR, topology `single_branch`,
target `main`. There is no WP02 and none should be created — `spec.md`'s C-001 bounds the
production change to `src/charter/kind_vocabulary.py` (the ~5 LOC `_org_scan_dirs` body)
and confines test changes to exactly the two files this WP owns. Do not touch
`_built_in_scan_dir` or `_layer_scan_dirs` in the same file — they sit next to
`_org_scan_dirs` but are not broken and are not the cited defect; touching them is
explicitly forbidden by C-003 (`RECONCILE_CHANGE_SCOPE_TENSIONS`, Locality of Change wins
— see spec.md Clarifications and plan.md's Campsite-Clean Scope section).

**The defect** (spec.md, verified at checkout HEAD `ab0a0b9b5b5e6803775e45bebd66d1cc8d3b68dc`):
`_org_scan_dirs` scans only `<org_root>/<plural>/built-in/` — a layout no real org pack
uses. Three independent sources agree the real layout is flat
(`<org_root>/<plural>/`, no `built-in/` segment): the live doctrine loader
(`DoctrineService._org_dirs`, `src/doctrine/service.py:47-55`, and
`BaseDoctrineRepository._load`'s non-recursive glob, `src/doctrine/base.py:356-373`), the
pack-layout guide (`docs/guides/how-to/governance/create-an-org-doctrine-pack.md:58`), and
the recognised-artifact-dirs contract (`_RECOGNISED_ARTIFACT_DIRS`,
`src/specify_cli/doctrine/snapshot.py:38-50`). Because `_org_scan_dirs` only looks under
`built-in/`, a flat-layout org pack contributes zero scan directories, so
`resolve_artifact_urn` raises `UnknownArtifactIdError`; that exception is caught and
swallowed by `_resolve_activated_urns_for_kind` (`src/charter/drg.py:379-380`,
`except UnknownArtifactIdError: continue`), so the org artifact's URN never enters the
resolved-URN set and `_node_is_activated`'s step-3 gate (`src/charter/drg.py:467-473`)
drops the node from the filtered graph — silently. `charter activate` reports success
while quietly failing to do the one thing the operator asked for.

**The fix** (FR-001, ~5 LOC): add a second, ordered-first scan entry for the flat
`<root>/<plural>` layout (`recursive=False`, matching the live loader) while keeping the
existing `<root>/<plural>/built-in` entry (`recursive=True`) — additive, not a layout
swap. When a same-config-stem file exists under both directories, the flat entry wins
because `resolve_artifact_urn` is first-match-wins over `_scan_roots`'s output and the
flat entry is ordered first (FR-001's precedence rule, spec.md Acceptance Scenario 4).

**Write scope is disjoint from every other open PR by construction**: this mission has
exactly one WP, and `owned_files` above is the complete, final file set — no other WP,
in this mission or any other, claims any of these three paths.

## Red-First Discipline (binding sequencing — plan.md's own step-by-step order)

Per Standing Order #4 (test remediation & bug-fix discipline), charter `C-011`
(ATDD-First Discipline), and spec.md's `C-004`, FR-002's regression test MUST be shown
red against the pre-fix `_org_scan_dirs` body **before** the fix lands. This is an
ordering constraint on this WP's own commits, not a separate review-time check. Follow
plan.md's "Red-First Discipline (WP Sequencing)" section exactly — reproduced here so you
do not have to re-derive it:

1. Author the FR-002 activation-filter-level regression test (Subtask T001) against the
   **pre-fix** `src/charter/kind_vocabulary.py`.
2. Run it and confirm red (Subtask T002). The expected pre-fix failure is,
   unconditionally, the assertion that the org directive's node is **absent** from
   `filter_graph_by_activation`'s output graph. Because FR-002 constrains this test to the
   full `activate()` → `filter_graph_by_activation()` round trip (never a direct
   `resolve_artifact_urn()` call), a raised `UnknownArtifactIdError` can **never** be the
   observed failure here: `_resolve_activated_urns_for_kind`
   (`src/charter/drg.py:371-381`) calls `resolve_artifact_urn` inside a
   `try`/`except UnknownArtifactIdError: continue` (`:379-380`) that swallows the
   exception before it can propagate out of `filter_graph_by_activation`. If your test
   observes an `UnknownArtifactIdError` instead of a missing-node assertion failure, the
   test is not exercising the round trip FR-002 requires — fix the test, not your
   expectation of the error type. (A `resolve_artifact_urn`-raises assertion is legitimate
   only for FR-003's unit-level test in Subtask T005, which calls `resolve_artifact_urn`
   directly per spec.md Acceptance Scenario 2 — that is a distinct, separate assertion,
   not part of FR-002's own red-first attribution.)
3. Apply the FR-001 fix to `_org_scan_dirs`, **including** the `_scan_roots` docstring
   update (Subtask T003 — this is part of the fix commit, not a separate task; see
   Campsite-Clean note below).
4. Re-run the same FR-002 test unmodified and confirm green (Subtask T004).
5. Extend `TestOrgScanDirsHelper` with FR-003's 5 new cases without deleting existing
   coverage; confirm green (Subtask T005).
6. Run the full gate set (Subtask T006) before considering the WP done.

Record both the red run and the green run (SC-001) — either as captured command output in
your own working notes, or as two distinct commits (a red-evidencing commit followed by
the fix commit). Never a single commit that adds an already-green test.

## Baseline Capture (repeat before authoring the fix)

plan.md's "Known-Red Baseline" section already recorded that
`tests/charter/test_kind_vocabulary_scan_roots.py`, run pre-fix and scoped to
`-m "fast and not windows_ci and not timing"`, was fully green — **14 passed, no
failures, no errors** — confirming none of #3284's (~23 untracked full-suite failures) or
#3283's (shared test-venv lock capacity signal) noise touches this surface. Before
authoring the fix (i.e., between Subtask T002 and T003), **repeat that scoped baseline
run** — the same file, plus the new FR-002 module once it exists from T001/T002:

```bash
pytest tests/charter/test_kind_vocabulary_scan_roots.py tests/charter/test_org_scan_dirs_activation_regression.py -m "fast and not windows_ci and not timing"
```

This makes any red you see *after* the fix commit attributable to the fix itself, never
misattributable to #3284/#3283's pre-existing baseline red on `main`.

### Subtask T001: Author the FR-002 red-first regression test

**Purpose**: Prove the defect at the level a real operator experiences it — the
`activate()` → `filter_graph_by_activation()` round trip — before any fix exists.

**Steps**:
1. Create `tests/charter/test_org_scan_dirs_activation_regression.py` (new file — this is
   the "new test module" C-001 explicitly permits; do not fold this into
   `test_activation_filtered_drg.py`, `test_drg_filtering.py`, `test_drg_activation_gate.py`,
   `test_org_activations_resolution.py`, or `test_org_activations_reach_context.py` — see
   plan.md's Test Placement Decision for why each was considered and rejected).
2. Add `pytestmark = pytest.mark.fast` at module level (matches the convention in sibling
   org-pack fixture files `test_org_activations_resolution.py:37` and
   `test_org_activations_reach_context.py:35`; `tests/charter/conftest.py` auto-marks
   everything `fast` anyway, but be explicit rather than relying on the hook silently).
3. Build a fixture org pack under `tmp_path`, flat layout:
   `<org_root>/directives/<org-directive-stem>.directive.yaml` — no `built-in/` segment.
4. Add a root-level `<org_root>/<org-directive-stem>.graph.yaml` declaring the org
   directive as a DRG node. This is **test-fixture data only, not a change to
   `_drg_helpers.py`** (C-002) — `filter_graph_by_activation` only ever operates on nodes
   already present in the merged graph, and DRG nodes come from `*.graph.yaml` fragments,
   never synthesized from `*.directive.yaml` files, so without this fixture file the test
   cannot observe the node at all, fixed or not.
5. Register the fixture org root and run the full `charter activate directive
   <org-directive-stem>` round trip for the org directive's **own** config-stem (or the
   equivalent programmatic `plan_activation`/`commit_activation` call) — not a direct
   `resolve_artifact_urn` call. Note that `CharterPackManager.activate()`'s own
   artifact-availability check (`_resolve_org_layer_dir`, `src/charter/pack_manager.py`)
   is an independent resolution path that already checks the flat `<root>/<plural>`
   layout first and is unaffected by this mission's `_org_scan_dirs` fix — a successful
   `charter activate` call by itself proves nothing about step 6 below; step 6's graph
   assertion is what actually exercises the fix.
6. Name the mechanism that merges the org pack's `*.graph.yaml` DRG fragment (added in
   step 4) into the graph `filter_graph_by_activation` operates on: call
   `charter._drg_helpers.load_validated_graph(repo_root, org_root=<org_root>)` — passing
   `org_root` **explicitly** — to obtain that merged graph. This is required because
   `load_validated_graph`'s own `org_root` fallback, `_resolve_org_root`
   (`src/charter/_drg_helpers.py:39-51`), is a permanent no-op that always returns
   `None` by design (the charter layer cannot import `specify_cli`'s config
   resolution); omitting the explicit `org_root` argument silently drops the org DRG
   node from the merged graph entirely, regardless of whether the `_org_scan_dirs` fix
   has landed. `action_doctrine_bundle.py:165` is, as of this writing, the only call
   site anywhere in `src/` that ever passes a non-`None` `org_root=` into
   `load_validated_graph` — this test must independently wire it. Two distinct,
   self-contained alternatives exist here — do not combine them into one:
   **(1)** build the merged graph by hand —
   `doctrine.drg.loader.merge_layers(doctrine.drg.loader.load_built_in_graph(),
   doctrine.drg.loader.load_graph_or_dir(org_root))` — bypassing `load_validated_graph`
   entirely, which sidesteps the `org_root` fallback problem by construction (it never
   calls `_resolve_org_root` at all); this is a hand-reproduction of
   `load_validated_graph`'s own internal implementation (`src/charter/_drg_helpers.py`),
   not an instance of any test file's pattern; **OR (2)** call
   `load_validated_graph(repo_root, org_root=<org_root>)` directly — the primary
   instruction already given above — while optionally also patching
   `charter._drg_helpers.load_built_in_graph`, in the style
   `tests/charter/test_merged_graph_on_live_path.py` uses (that file always calls
   `load_validated_graph(tmp_path)` itself and only patches `load_built_in_graph` to
   substitute a fixture built-in layer), and do this only if you also want to substitute
   a fixture built-in layer in place of the real shipped one. Then pass the resulting
   graph into `filter_graph_by_activation` and assert the org directive's node is
   present in its output.
7. Add a second test method covering spec.md Acceptance Scenario 5: activating both the
   org stem and an unrelated built-in stem, in either order, both leave the org node
   present; activating **only** the unrelated built-in stem (never the org stem) does
   **not** surface the org node — this is the per-artifact-ID gate's by-design
   selectivity, not something this mission changes, and the test should assert it stays
   that way (a negative assertion, not a bug to fix).

**Which test proves which scenario**: this subtask's primary test method proves spec.md
User Story 1 Acceptance Scenario 1 (round-trip presence via the full `activate()` →
`filter_graph_by_activation()` path). The second method proves Acceptance Scenario 5
(order-independence plus the selectivity negative-case).

**Files**: `tests/charter/test_org_scan_dirs_activation_regression.py` (new, ~80-150
lines: fixture construction + 2 test methods).

**Validation**: File collects under pytest; do not run it green yet — proceed to T002.

### Subtask T002: Run and confirm red

**Purpose**: Produce the red-first evidence C-004/Standing Order #4 require before any
fix commit exists.

**Steps**:
1. Run: `pytest tests/charter/test_org_scan_dirs_activation_regression.py -v`
2. Confirm the primary test (Acceptance Scenario 1) fails with an assertion that the org
   directive's node is **absent** from `filter_graph_by_activation`'s output — not an
   `UnknownArtifactIdError` (see Red-First Discipline above for why that error type cannot
   be the observed failure for this round-trip-shaped test).
3. Capture the failing output (paste into your own working notes, or commit this test
   file alone first as a distinct red-evidencing commit before the fix commit).

**Files**: none (evidence-only step).

**Validation**: A recorded red run exists, attributable specifically to the missing flat
scan entry.

### Subtask T003: Apply the FR-001 fix + `_scan_roots` docstring update

**Purpose**: Close the defect with the minimal, spec-pinned change.

**Steps**:
1. In `src/charter/kind_vocabulary.py`, edit `_org_scan_dirs` (`:200-209`) to return, for
   every configured org root:
   - **First**, `<root>/<kind.plural>` (flat) if it exists, with `recursive=False` —
     matching `DoctrineService._org_dirs` / `BaseDoctrineRepository`'s non-recursive org
     glob (`src/doctrine/base.py:25`, `:159`).
   - **Then**, `<root>/<kind.plural>/built-in` (legacy) if it exists, with
     `recursive=True` — unchanged from today (mirrors `_built_in_scan_dir`'s and the
     built-in layer's `rglob`, `src/doctrine/base.py:182`).
   - Neither directory existing is not an error — return fewer entries, never raise.
   - Ordering matters: the flat entry must come first in the returned list so
     `resolve_artifact_urn`'s first-match-wins semantics make the flat file win on a
     same-config-stem collision between the two directories (FR-001's precedence rule,
     spec.md Acceptance Scenario 4).
2. In the same file, update `_scan_roots`'s docstring (`:158-160`) — it currently states,
   present-tense, that `org_roots` "preserves the legacy package-shaped root contract
   where each root contributes `<root>/<plural>/built-in>` -- this nested layout is still
   live for org packs." This goes stale the moment the fix lands. Rewrite it to describe
   **both** the flat and legacy entries `org_roots` now contributes. This docstring edit
   is part of this fix commit — it is not a separate task and not scope creep (it is the
   same file, the same function's immediate caller, directly caused by this change — see
   plan.md's Campsite-Clean Scope section). Do **not** touch `_built_in_scan_dir` or
   `_layer_scan_dirs` in this file — C-003 forbids it; they are not broken and are not the
   cited defect.
3. No new import is needed — `pathlib.Path` is already imported in this file.

**Files**: `src/charter/kind_vocabulary.py` (~5 LOC behavioral change in
`_org_scan_dirs`, plus a docstring-only edit in `_scan_roots`).

**Validation**: `ruff check src/charter/kind_vocabulary.py` and
`mypy --strict src/charter/kind_vocabulary.py` are clean, no new suppressions (C-005,
SC-004). Do not run the test suite as "done" yet — proceed to T004.

### Subtask T004: Re-run FR-002 test, confirm green

**Purpose**: Prove the fix actually closes the defect the red run in T002 demonstrated.

**Steps**:
1. Run: `pytest tests/charter/test_org_scan_dirs_activation_regression.py -v` again,
   unmodified from T001/T002.
2. Confirm both test methods pass: the org directive's node is now present in
   `filter_graph_by_activation`'s output (Acceptance Scenario 1), and the
   order-independence / selectivity assertions from Acceptance Scenario 5 hold.
3. Record this green run (SC-001) alongside the red run from T002 — either in your own
   working notes, or as this WP's fix commit following a distinct red-evidencing commit.

**Files**: none (evidence-only step).

**Validation**: FR-002's test is green, proving SC-001 and SC-002.

### Subtask T005: Extend `TestOrgScanDirsHelper` with FR-003's 5 new cases

**Purpose**: Pin the new `_org_scan_dirs` contract at the unit level, covering every
changed branch of the ~5 LOC fix.

**Steps**:
1. In `tests/charter/test_kind_vocabulary_scan_roots.py`, extend `TestOrgScanDirsHelper`
   (currently 3 methods at `:125-135`: `test_none_org_roots_returns_empty_list`,
   `test_missing_org_built_in_dir_skipped`, `test_existing_org_built_in_dir_returned`) —
   **do not delete any of the three existing methods**. The pre-existing
   `test_existing_org_built_in_dir_returned` case (legacy shape) must still pass
   unmodified in behavior (still returns the legacy dir); only its assertion about what
   *else* is returned may change if a flat dir is also present in that fixture.
2. Add 5 new test methods:
   - **Flat-only**: only `<root>/<plural>` exists → returns one entry, `recursive=False`.
     Include, as part of this same case, a direct call to
     `resolve_artifact_urn(ArtifactKind.DIRECTIVE, <org-directive-stem>,
     doctrine_root=doctrine_root, org_roots=[org_root])` against a fixture that has
     **only** the flat `<org_root>/directives/<stem>.directive.yaml` present (no
     `built-in/` directory anywhere under `org_root`), asserting it returns the org
     directive's URN and does **not** raise `UnknownArtifactIdError` — this is the
     proof of spec.md User Story 1 Acceptance Scenario 2 (a flat-only fixture, no
     legacy directory in play at all), distinct from the "Same-config-stem
     precedence" case below, which requires both directories present and proves
     Acceptance Scenario 4.
   - **Legacy-only**: only `<root>/<plural>/built-in` exists → returns one entry,
     `recursive=True` (this is effectively the pre-existing behavior; add as a distinct
     explicit case per spec.md FR-003's enumeration even if it overlaps the existing
     `test_existing_org_built_in_dir_returned`).
   - **Both present**: both directories exist → returns both entries, flat first — this is
     the proof of spec.md User Story 1 Acceptance Scenario 3 (artifacts under both the
     flat directory and the legacy `built-in/` subdirectory are found; the fix is
     additive, not a replacement that trades one phantom layout for a different single
     layout).
   - **Neither present**: neither directory exists → returns `[]` (no exception).
   - **Same-config-stem precedence**: a same-stem artifact file exists under both
     `<root>/<plural>/<stem>.directive.yaml` (`id: DIRECTIVE_FLAT`) and
     `<root>/<plural>/built-in/<stem>.directive.yaml` (`id: DIRECTIVE_LEGACY`) — call
     `resolve_artifact_urn(ArtifactKind.DIRECTIVE, <stem>, doctrine_root=doctrine_root,
     org_roots=[org_root])` and assert it returns `directive:DIRECTIVE_FLAT`, never
     `directive:DIRECTIVE_LEGACY`, and never a result that depends on incidental scan
     order (FR-001's precedence rule, spec.md Acceptance Scenario 4).
3. Use `tmp_path` fixtures in the existing style already used by `TestOrgScanDirsHelper`
   and the sibling `TestBuiltInScanDirHelper` class — no new fixture infrastructure
   (`monkeypatch.setattr` where needed, not `unittest.mock.patch`, per the `patch()`
   target-validation gate's expected idiom).
4. No new marker needed — the file already carries module-level
   `pytestmark = [pytest.mark.unit, pytest.mark.fast]` (`:35`); new methods inherit both.

**Which test proves which scenario**: these 5 cases prove spec.md FR-003 directly and
User Story 2's Acceptance Scenarios 1-2 collectively (the extended class is green
post-fix, and — combined with T002's captured red run of the FR-002 module — demonstrates
the red-before/green-after pattern C-004 requires, even though FR-003's own cases are
authored and run only in the green, post-fix state since they pin the *new* contract, not
a regression of pre-existing behavior). The "Flat-only" case's embedded direct
`resolve_artifact_urn` call additionally proves User Story 1's Acceptance Scenario 2
(flat-only fixture, no-raise); the "Same-config-stem precedence" case proves Acceptance
Scenario 4 (both directories present) — these are two distinct scenarios and must not be
conflated.

**Files**: `tests/charter/test_kind_vocabulary_scan_roots.py` (extended, ~120-180 new
lines across 5 methods).

**Validation**: `pytest tests/charter/test_kind_vocabulary_scan_roots.py -v` — all 8
methods in `TestOrgScanDirsHelper` (3 existing + 5 new) pass; no existing test in the file
regresses (SC-003).

### Subtask T006: Run the full gate set

**Purpose**: Confirm the WP is mergeable against every gate that actually applies to this
diff shape, before opening the PR.

**Steps**:
1. Run the `fast-tests-charter` shard's own test scope locally:
   ```bash
   pytest tests/charter tests/specify_cli/charter_freshness tests/specify_cli/charter_lint tests/specify_cli/charter_preflight -m "fast and not windows_ci and not timing" --cov=charter --cov-fail-under=55
   ```
2. Confirm diff-coverage: every changed line/branch in
   `src/charter/kind_vocabulary.py` (flat-present, legacy-present, both-present,
   neither-present, same-stem-precedence branches) is exercised by FR-002 and FR-003
   together — `src/charter/*` is on the CI `diff-coverage` job's critical-path allowlist
   with a 90%-on-changed-lines floor; this is the binding coverage bar for this diff, not
   the 55% module-level floor above.
3. Run `ruff check src/charter/kind_vocabulary.py tests/charter/test_kind_vocabulary_scan_roots.py tests/charter/test_org_scan_dirs_activation_regression.py` and
   `mypy --strict src/charter/kind_vocabulary.py` — advisory in CI (`continue-on-error:
   true`) but a house rule here: zero issues expected, no new suppressions (C-005).
4. Run `ruff check src tests --select TID251` — enforced, no `continue-on-error`; expected
   clean (no raw `hashlib.sha256`, no direct `click.exceptions.*` catches anywhere near a
   directory-existence check).
5. Confirm Bandit and pip-audit have nothing new to report (enforced via CI's
   outcome-check, not this diff's own step to run locally unless tooling is available) —
   a directory-existence check and list-append introduce no plausible medium+ finding, and
   no dependency changes, so both should be clean/no-op for this diff.
6. Confirm `uv.lock` is untouched — this diff makes no `pyproject.toml`/dependency change.
7. Confirm doctrine-schema-freshness and Contextive-glossary-freshness checks pass
   trivially — no schema source and no new domain term are introduced by this diff (see
   plan.md's "Nothing Generated, No Contract Movement" section).
8. Markdown-lint and the Typer-JSON error-surface gate do not apply to this diff (no
   `kitty-specs/**` prose change beyond planning artifacts already exempted, no CLI
   surface touched). SonarCloud does not run on PRs today (schedule/`workflow_dispatch`
   only) — do not treat its absence as a gap.
9. Ensure commit messages are conventional-commit-shaped (commitlint is advisory,
   `continue-on-error: true`, but is a house rule per CLAUDE.md).

**Files**: none (validation-only step).

**Validation**: All items in Definition of Done below are checked off.

## Definition of Done

- [ ] FR-002's regression test (`tests/charter/test_org_scan_dirs_activation_regression.py`)
      was run and observed **red** against the pre-fix `_org_scan_dirs` body, with the
      failure being a missing-node assertion (not `UnknownArtifactIdError`) — evidence
      recorded (T002).
- [ ] The scoped baseline (`tests/charter/test_kind_vocabulary_scan_roots.py` +
      `tests/charter/test_org_scan_dirs_activation_regression.py`,
      `-m "fast and not windows_ci and not timing"`) was re-run immediately before the fix
      commit, confirming no #3284/#3283 noise is present on this surface.
- [ ] `_org_scan_dirs` (`src/charter/kind_vocabulary.py:200-209`) returns the flat entry
      (`recursive=False`) ordered first, then the legacy `built-in` entry
      (`recursive=True`) where each exists; neither existing returns `[]`, never raises
      (FR-001).
- [ ] `_scan_roots`'s docstring (`:158-160`) is updated to describe both entries
      `org_roots` now contributes, as part of the fix commit.
- [ ] `_built_in_scan_dir` and `_layer_scan_dirs` in the same file are untouched (C-003).
- [ ] FR-002's regression test re-run and observed **green** post-fix, unmodified from
      its red-run form (T004).
- [ ] `TestOrgScanDirsHelper` in `tests/charter/test_kind_vocabulary_scan_roots.py`
      covers flat-only, legacy-only, both-present, neither-present, and
      same-config-stem-precedence, plus all 3 pre-existing methods still pass unmodified
      in behavior (FR-003, SC-003).
- [ ] `fast-tests-charter` shard's scope (`tests/charter
      tests/specify_cli/charter_freshness tests/specify_cli/charter_lint
      tests/specify_cli/charter_preflight`, `-m "fast and not windows_ci and not
      timing"`) is green.
- [ ] Diff-coverage on `src/charter/kind_vocabulary.py`'s changed lines meets the 90%
      critical-path floor (every branch of the fix exercised by FR-002 + FR-003).
- [ ] `ruff check` and `mypy --strict` are clean on all three owned files, zero new
      suppressions (C-005, SC-004).
- [ ] `ruff check src tests --select TID251` is clean.
- [ ] No `_drg_helpers.py` or other #3384-owned production code was touched (C-002).
- [ ] Only the three files in `owned_files` were modified — no other production or test
      file changed.
- [ ] Both the red run (T002) and green run (T004) are recorded, either as captured
      output or as a red-then-green commit pair (never a single commit adding an
      already-green test).

## Non-Goals / Deferred Follow-Ups (recorded, not implemented here)

- **VC-001 (named-diagnostic check for the D1 collapse path)** and **VC-002
  (`<org_root>/drg` alternative-location check)** — both contingent on issue #3384
  landing (a sibling mission's fix, `org-pack-drg-root-graph-guard`, out of scope here).
  This mission records these as verification criteria for a *later* pass, gated on
  #3384's merge — it does **not** implement a change to make either true, and neither is
  a subtask or Definition-of-Done item for this WP. See spec.md's "Contingent
  Verification Criteria" table (VC-001, VC-002) for the full text.
- **The `compiler.py` / `consistency_check.py` `resolve_artifact_urn` consumers.**
  plan.md's "The Seam" and "Nothing Generated, No Contract Movement" sections note that
  these two consumers observe a real behavior change from this fix (a flat-layout org
  pack's own stem stops crashing `charter synthesize`, and stops being reported as an
  unresolved parity gap) but are deliberately **not** covered by this WP's tests — C-001
  confines test changes to the two owned test files, and neither consumer is named by any
  FR/C in spec.md. Do not add coverage for them in this WP.
- **The typo/unknown-stem swallow** (`src/charter/drg.py:379-380`,
  `except UnknownArtifactIdError: continue`) remains unfixed — a genuinely absent or
  misspelled activation stem is still silently skipped after this fix. Separate, larger
  defect class; not addressed here (spec.md Edge Cases, Out of Scope).
- **`_built_in_scan_dir` / `_layer_scan_dirs` refactor.** Not touched, per C-003 — see
  Context above.

## Risks

- **Recursive-flag mismatch.** The flat entry must be `recursive=False` to match the live
  loader's non-recursive org glob (`src/doctrine/base.py:25`, `:159`); a recursive flat
  scan would silently accept a layout the live loader does not, reopening a smaller
  version of this same source-of-truth divergence. Mitigated by T005's flat-only test
  method asserting the exact `(Path, bool)` tuple, not just directory presence.
- **Red run misattributed as `UnknownArtifactIdError`.** If T001's test is written as (or
  accidentally collapses to) a direct `resolve_artifact_urn` call rather than the full
  `activate()` → `filter_graph_by_activation()` round trip, the observed red would be the
  wrong shape and would not prove FR-002. Mitigated by the explicit round-trip
  requirement restated in Red-First Discipline above and cross-checked against spec.md
  Acceptance Scenario 1's own wording ("the full `activate()` →
  `filter_graph_by_activation()` round trip, not a direct `resolve_artifact_urn` call").
- **Scope creep into neighboring helpers.** `_built_in_scan_dir` / `_layer_scan_dirs` sit
  in the same file and are structurally similar; Boy Scout Rule instincts could pull
  toward "tidying" them. C-003 forbids this explicitly — resist it.
- **Ordering regression.** If the fix's list-building accidentally puts the legacy entry
  before the flat entry, the same-stem precedence test (T005) will catch it, but be
  deliberate about ordering when writing the fix in T003.
- **Graph-merge never wired to `org_root`.** `charter._drg_helpers.load_validated_graph`'s
  `org_root` argument defaults to `_resolve_org_root`, a permanent no-op that always
  returns `None`; the only call site anywhere in `src/` that ever passes a real
  `org_root=` is `action_doctrine_bundle.py:165`. If T001 builds the graph passed into
  `filter_graph_by_activation` without explicitly wiring `org_root=<org_root>` (or the
  equivalent `merge_layers` construction), the org pack's `*.graph.yaml` DRG node never
  enters the graph at all — pre-fix **or** post-fix — so the test stays red after the fix
  lands, for a reason unrelated to `_org_scan_dirs`, and T002's red run would be red for
  the wrong reason. Mitigated by T001 step 6's explicit naming of the mechanism. Relatedly,
  `charter activate`'s own artifact-availability check (`pack_manager.py`'s
  `_resolve_org_layer_dir`) already tolerates the flat layout today via an independent
  resolution path — a successful `charter activate` call by itself is not evidence that
  the `_org_scan_dirs` fix under test did anything; only the graph assertion is.

## Reviewer Guidance

- Verify the red-first evidence (T002) is real: either two distinct commits (a
  red-evidencing test-only commit, then the fix commit) or explicit command output
  recorded in the PR description / commit message showing the pre-fix failure and its
  exact assertion shape (missing node, not `UnknownArtifactIdError`).
- Confirm `_org_scan_dirs`'s returned list orders the flat entry first and that
  `resolve_artifact_urn`'s first-match-wins semantics genuinely produce the flat file's
  URN on a same-stem collision (T005's precedence test) — don't just check "both
  directories scanned," check the *order* and the *precedence outcome*.
- Confirm `_built_in_scan_dir` and `_layer_scan_dirs` have zero diff — C-003 is a hard
  constraint, not a preference.
- Confirm the `_scan_roots` docstring update landed and accurately reflects the new
  two-entry contract, not just the flat addition in isolation.
- Confirm no file outside `owned_files` changed, and no commit touches
  `src/charter/_drg_helpers.py` or any other #3384-owned surface (C-002).
- Confirm the PR body or WP notes record the deferred VC-001/VC-002/consumer-coverage
  items above as explicit non-goals, not silently dropped.

## Implementation Command

```bash
spec-kitty agent action implement WP01 --agent <name>
```

## Activity Log

- 2026-08-13T23:31:59Z – user – Red-first verified empirically: 21 passed -> revert -> 7 failed/14 passed -> restore -> 21 passed; ruff, mypy --strict, TID251 clean
