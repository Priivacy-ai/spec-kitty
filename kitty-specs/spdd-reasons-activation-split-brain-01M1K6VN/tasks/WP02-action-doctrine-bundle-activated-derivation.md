---
work_package_id: WP02
title: action_doctrine_bundle.py + delivery_table.py re-derivation from activated_*
dependencies: []
requirement_refs:
- FR-006
- FR-007
- FR-008
- FR-014
- NFR-001
- NFR-002
planning_base_branch: fix/spdd-reasons-activation-split-brain-3838
merge_target_branch: fix/spdd-reasons-activation-split-brain-3838
branch_strategy: Planning artifacts for this mission were generated on fix/spdd-reasons-activation-split-brain-3838. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/spdd-reasons-activation-split-brain-3838 unless the human explicitly redirects the landing branch.
subtasks:
- T006
- T007
- T008
- T009
- T010
history: []
agent_profile: implementer-ivan
authoritative_surface: src/charter/activation/
create_intent:
- tests/charter/test_action_doctrine_bundle_activation.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/activation/action_doctrine_bundle.py
- src/charter/activation/context_renderers/delivery_table.py
- tests/charter/test_action_bundle_delivery.py
- tests/charter/test_action_doctrine_bundle_activation.py
role: implementer
tags: []
tracker_refs: []
---

# WP02 — Re-derive `_load_action_doctrine_bundle`'s directive allowlist and traversal roots from `activated_*`

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Re-derive `_load_action_doctrine_bundle`'s `project_directives`/`selected_tactics`/`selected_paradigms`
(currently sourced from the stale `governance.charter.selected_*` via `_load_doctrine_selection`) from
`pack_context.activated_directives`/`.activated_tactics`/`.activated_paradigms` instead — preserving the
org-pack `required_<kind>` union (a confirmed-legitimate, separate concept) by unioning it onto the
`activated_*`-derived set — while keeping the three-state (`None`/`frozenset()`/non-empty) distinction
alive through every consumption site in `delivery_table.py` (Decision Record 2, FR-006/007/008/014).

## Context

Two independently-proven defects live in this function (spec Decision Record 2), both reading the same
stale `governance.charter.selected_*` section `is_spdd_reasons_active` (WP01) reads:

1. **Silent exclusion** (`delivery_table.py`'s `_classify_artifact_urns`): `if node.kind is
   NodeKind.DIRECTIVE and project_directives and artifact_id not in project_directives: continue` — a
   bare truthiness test. When the stale `project_directives` is non-empty, it drops ANY directive not in
   that stale set, even one genuinely `activated_*` and DRG-reachable.
2. **Silent under-seeding** (closure-widening `start_urns`/`roots`): on THIS REPO's OWN dogfood charter,
   `selected_directives`/`selected_tactics`/`selected_paradigms` are all `[]`, so `start_urns` is empty —
   the requires/suggests closure-widening these fields exist to provide contributes nothing, despite
   dozens of genuinely-activated tactics/paradigms/directives.

**Already-parameterized — no new plumbing needed.** `_load_action_doctrine_bundle`'s real signature
(confirmed by reading the live file) already has `pack_context: PackContext | None = None` as a parameter,
populated by `_resolve_action_bundle` via `_PackContext.from_config(repo_root)` before the call. This WP
only changes what the function *does* with the parameter it already has.

**Live citations (re-verified against the file for this WP, not copied from plan.md without checking):**
in `src/charter/activation/action_doctrine_bundle.py`'s `_load_action_doctrine_bundle`:
```python
doctrine_selection = _load_doctrine_selection(repo_root)
...
project_directives = {_normalize_directive_id(d) for d in doctrine_selection.selected_directives}
selected_tactics = {t for t in doctrine_selection.selected_tactics if t}
selected_paradigms = {p for p in doctrine_selection.selected_paradigms if p}
...
ids_by_slot = _classify_artifact_urns(
    resolved.artifact_urns, merged, project_directives, selected_tactics, selected_paradigms,
)
...
roots = (
    action_urn,
    *(f"directive:{d}" for d in project_directives),
    *(f"tactic:{t}" for t in selected_tactics),
    *(f"paradigm:{p}" for p in selected_paradigms),
)
```
and in `src/charter/activation/context_renderers/delivery_table.py`'s `_classify_artifact_urns`:
```python
def _classify_artifact_urns(
    artifact_urns: frozenset[str] | set[str], merged: DRGGraph,
    project_directives: set[str],
    selected_tactics: set[str] | None = None, selected_paradigms: set[str] | None = None,
) -> Mapping[str, tuple[str, ...]]:
    ...
    selected_tactics = selected_tactics or set()
    selected_paradigms = selected_paradigms or set()
    start_urns = {f"directive:{directive_id}" for directive_id in project_directives}
    start_urns.update(f"tactic:{tactic_id}" for tactic_id in selected_tactics)
    start_urns.update(f"paradigm:{paradigm_id}" for paradigm_id in selected_paradigms)
    ...
    if node.kind is NodeKind.DIRECTIVE and project_directives and artifact_id not in project_directives:
        continue
```

**Cross-WP semantic chokepoint (read before implementing):** WP01/WP02/WP03 all encode the SAME rule —
`None` (key absent) means "all built-ins," never an empty set. WP02's own twist: `project_directives` is
declared `set[str]` (not `Optional`) in `_classify_artifact_urns`'s signature today, and both
`start_urns`'s comprehension AND `roots`'s generator expressions iterate it/`selected_tactics`/
`selected_paradigms` **unconditionally, with no `None`-guard anywhere**. If `pack_context.activated_directives`
is `None` and you assign it straight into `project_directives` without converting it first, `roots`'s
`*(f"directive:{d}" for d in project_directives)` raises `TypeError: 'NoneType' object is not iterable`
before `_classify_artifact_urns` (and its own `or set()` lines) is ever reached. **Convert `None` to a
concrete value ONCE, at the point of assignment in `_load_action_doctrine_bundle`, before any consumption
site iterates it** — for all three of `project_directives`, `selected_tactics`, `selected_paradigms` alike,
to the catalog-backed "all built-ins" default (`load_doctrine_catalog().directives`/`.tactics`/`.paradigms`
— import from `charter.activation.catalog`, already used one file over in `resolver.py`'s WP03 edit for the
identical field, so this catalog enumeration is proven available and zero-argument). Do **not** convert
`None` to an explicit empty set for tactics/paradigms — that is the exact "softer failure" (silent
under-seeding) this WP exists to close, relocated rather than fixed. Once you do this, `delivery_table.py`'s
own `selected_tactics or set()` / `selected_paradigms or set()` lines (lines shown above) become
dead/defense-in-depth — you may remove them or leave them as a documented no-op guard; either way, state
your choice in the PR description. The exclusion guard's own change (separately) is `is not None`, never
bare truthiness — this correctly treats an explicit `frozenset()` as "exclude everything" per FR-014, which
the early-conversion step preserves distinctly from "all built-ins" by never overwriting an explicit
`frozenset()` with the catalog default.

**Existing out-of-scope test this fix must keep GREEN (verified live, currently passing):**
`tests/charter/test_activation_consumers.py::test_context_bundle_none_path_matches_no_filter_at_all`
(one of four `*_none_path_matches_no_filter_at_all` sibling tests in that file, covering
`resolve_references_transitively`, `_resolve_transitive_reference_graph`, `_check_drg_cross_kind_refs`, and
this WP's own `_load_action_doctrine_bundle`) asserts that calling `_load_action_doctrine_bundle` with
`pack_context=None` produces `directive_ids` byte-identical to calling it with a `PackContext` whose
`activated_directives=None` — i.e. "wholly-absent `pack_context`" and "`PackContext` present but its
field is `None`" are the SAME "no filter at all" state, both resolving to the full catalog-derived set.
This file is not in this WP's (or any WP's) `owned_files` and needs NO code change — it already encodes
the correct convention — but a naive reading of "keep today's degrade-gracefully behavior" for the
`pack_context is None` branch (empty sets) would silently break it. T009 step 1 above is written to keep
this test green by construction; T010 re-runs it explicitly as a named gate, not merely via the generic
baseline-diff.

**One-PR-shape / baseline-capture note**: same as WP01 — this mission ships as one PR; capture your OWN
baseline in your own workspace before touching any file (identical command, see WP01's Context section),
independently of whether WP01/WP03 have already captured theirs in their own workspaces.

### Marker discipline (verified live — SK-144/#3241)

- `tests/charter/test_action_bundle_delivery.py` (existing, edited in this WP): already carries
  `pytestmark = [pytest.mark.fast]` (confirmed by reading the live file) — **no marker change needed**;
  you are only changing four call sites' arguments (T007), not the file's test-selection surface.
- `tests/charter/test_action_doctrine_bundle_activation.py` (NEW, this WP): use
  `pytestmark = [pytest.mark.fast]` — **correcting plan.md section (j)'s table**, which listed `fast,
  doctrine` for this file by analogy with WP01's sibling family. The REAL local convention for this
  file's actual sibling family (`test_action_bundle_delivery.py`, `test_action_doctrine_bundle_org_fragment.py`,
  `test_action_bundle_tension_arbiters.py` — all under `tests/charter/`, all action-bundle-concern files)
  is `pytest.mark.fast` alone, with no `doctrine` marker anywhere in that family (verified by reading all
  three live files for this WP). Collection is unaffected either way: both `fast-tests-charter` and
  `doctrine-charter-tests.yml` select by the `fast` marker plus `tests/charter/` path membership, not by
  the `doctrine` marker — but match the real sibling-family convention rather than a different family's,
  per repo Code Style's "use canonical/existing conventions" discipline.

### `__all__` / C-007 disposition

- `action_doctrine_bundle.py` already declares `__all__ = ["_ActionDoctrineBundle",
  "_load_action_doctrine_bundle", "_resolve_action_bundle"]` (confirmed live) — unaffected by this WP's
  change (you are changing what the existing, already-exported `_load_action_doctrine_bundle` reads, not
  adding a new public symbol). If you factor the "convert `None` to catalog default" logic into a small
  private helper (e.g. `_catalog_default_or_activated(...)`), keep it un-exported (leading underscore, not
  added to `__all__`) with `_load_action_doctrine_bundle` as its real in-module caller — that already
  satisfies `test_no_dead_symbols.py`.
- `delivery_table.py` already declares `__all__ = ["_Gate", "_classify_artifact_urns", "action_bundle_bucket",
  "action_bundle_gate"]` (confirmed live) — unaffected; you are changing the guard's truthiness test, not
  its signature or exported surface.

## Subtask T006: Baseline capture

**Purpose**: Capture this WP's own pre-mission baseline (section g), in this WP's own workspace, before any
functional change.

**Steps**: Run the exact command from WP01's Context section
(`pytest tests/charter/ tests/architectural/test_charter_offering_does_not_import_activation.py
tests/architectural/test_no_dead_symbols.py -q`); save the full failing node-id list.

**Files**: none changed
**Validation**: Baseline list captured and classified per CLAUDE.md's three categories.

## Subtask T007: Red-first tests — FR-007, FR-008, FR-014, plus this WP's own tactics/paradigms-absent fixture

**Purpose**: Commit four red-first regression tests before any implementation change (C-011): the
directive-allowlist silent-drop (FR-007), this repo's own dogfood closure-starvation shape (FR-008), the
explicit-empty-`activated_directives`-excludes-everything case (FR-014), and the plan-added
`activated_tactics`/`activated_paradigms`-absent sibling fixture (plan.md section (a) item 3, required
because none of FR-007/008/014 exercise a `None` `activated_tactics`/`activated_paradigms` case).

**Steps**:
1. Create `tests/charter/test_action_doctrine_bundle_activation.py` with `pytestmark = [pytest.mark.fast]`.
2. **FR-007** — construct a fixture DRG + charter where a directive is genuinely `activated_*` and reached
   by the DRG walk from the action node, but is NOT a member of a non-empty, disjoint
   `governance.charter.selected_directives` (e.g. `activated_directives` includes `DIRECTIVE_038`,
   `selected_directives = ["DIRECTIVE_010"]`, both reachable). Assert `_load_action_doctrine_bundle`'s
   resulting bundle's `directive_ids` includes `DIRECTIVE_038`.
   **Why RED on `main` today**: `project_directives` is built from `doctrine_selection.selected_directives`
   only (the `_normalize_directive_id` comprehension shown in Context) — `activated_directives` is never
   consulted for this decision on `main`. `_classify_artifact_urns`'s exclusion guard
   (`project_directives and artifact_id not in project_directives`) then drops `DIRECTIVE_038` because
   `"DIRECTIVE_038" not in {"DIRECTIVE_010"}` — verified by reading the live guard, not assumed.
3. **FR-008** — reproduce this repo's own live dogfood shape: `selected_directives`/`selected_tactics`/
   `selected_paradigms` all `[]`, `activated_*` non-empty and DRG-reachable. Assert the closure-widening
   `roots`/`start_urns` are non-trivially populated from `activated_*` (not merely that the function does
   not crash — assert specific expected URNs are present).
   **Why RED on `main` today**: with `selected_*` all `[]`, `project_directives`/`selected_tactics`/
   `selected_paradigms` (the stale-derived sets) are all empty sets on `main`, so `roots`'s three generator
   expressions produce zero directive/tactic/paradigm URNs regardless of what `activated_*` says —
   `start_urns` is correspondingly empty, so the requires/suggests closure widening contributes nothing.
4. **FR-014** — construct a fixture with an EXPLICIT `activated_directives: []` (present, empty — distinct
   from absent) on the `pack_context`, and a DRG-reachable directive. Assert the exclusion filter delivers
   ZERO directives from that check (not all of them).
   **Why this must fail on a NAIVE fix, not necessarily on `main` as-is**: this pins the three-state
   distinction itself. A naive re-derivation that assigns `pack_context.activated_directives` straight into
   `project_directives` and lets `frozenset()` fall through the bare-truthiness guard unchanged would
   deliver ALL DRG-reached directives (the guard's `project_directives and ...` short-circuits False on an
   empty/falsy set, meaning "no filter") — the OPPOSITE of "nothing activated." Write this test now, before
   implementation, so a partially-correct T009 (guard fixed but early-conversion point missed, or vice
   versa) is caught immediately.
5. **New sibling fixture (plan.md section (a) item 3)** — `activated_tactics`/`activated_paradigms`
   **absent** (`None`, not `[]`) on the `pack_context`; exercise `_load_action_doctrine_bundle` end-to-end
   through `roots`'s construction and `_classify_artifact_urns`. Assert (a) no `TypeError`, and (b)
   `roots`/`start_urns` contain a `tactic:<id>`/`paradigm:<id>` URN for **every** ID in
   `load_doctrine_catalog().tactics`/`.paradigms` (124 tactic URNs / 13 paradigm URNs on this repo's own
   built-in catalog, per the mission brief's confirmed direct-call count) — the catalog-derived "all
   built-ins" outcome, NOT parity with today's pre-fix behavior.
   **Why this MUST fail on `main` (not just "should"), stated precisely**: on `main`, an absent
   `activated_tactics`/`activated_paradigms` never even reaches this decision — `selected_tactics`/
   `selected_paradigms` come from `_load_doctrine_selection`'s stale `selected_*` reads, which (for a
   project whose `activated_tactics`/`.paradigms` are genuinely unconfigured/absent) are naturally also
   empty/unauthored — so `roots`/`start_urns` carry ZERO tactic/paradigm URNs on `main` for this fixture's
   shape. The "one URN per catalog ID" assertion fails against that empty result. **A fixture that instead
   asserted "no worse than today" (e.g. "roots is non-empty" or "roots has at least as many URNs as
   before") would pass on BOTH the buggy `main` behavior and a correct catalog-widened fix, proving
   nothing** — this is the exact severity-4 bug-preserving-test defect class that HALTed this mission's
   plan phase twice (`PLAN-FRESH-001`/`PLAN-FRESH2-001`). Do not weaken this assertion to a vaguer form.

**Files**: `tests/charter/test_action_doctrine_bundle_activation.py` (new, ~220-260 lines)
**Validation**: `pytest tests/charter/test_action_doctrine_bundle_activation.py -v` — all four cases RED
against the unmodified `action_doctrine_bundle.py`/`delivery_table.py`.

## Subtask T008: Update `test_action_bundle_delivery.py`'s four `set()` call sites to `None` (PLAN-GOV-001)

**Purpose**: This existing file calls `_classify_artifact_urns` directly at four sites passing a bare
`set()` literal for `project_directives`, asserting today's bare-truthiness "empty set == no filter"
behavior. Under the corrected `is not None` guard (T009), an explicit `set()` now means "exclude
everything" (FR-014) — these four sites must pass `None` instead to preserve their ORIGINAL intent ("no
project-directive scoping applied").

**Steps**:
1. Open `tests/charter/test_action_bundle_delivery.py`. Confirm (re-verify, do not trust this count without
   checking) the four bare-`set()` call sites — as read live for this WP, they are at the lines calling
   `context._classify_artifact_urns(resolved.artifact_urns, graph, set())` (one occurrence) and
   `context._classify_artifact_urns(resolved.artifact_urns, filtered, set())` (three occurrences across the
   file). **Do NOT touch** the separate call at `project_directives={"some-other-directive"}` — that one
   intentionally asserts explicit-scope exclusion behavior and is unrelated to this WP's fix (it already
   uses a non-empty set, not the "no filter" sentinel).
2. Change each of the four bare-`set()` call sites to pass `None` instead of `set()`.
3. Run the file's existing test suite — all four should remain GREEN (their intent — "no project-directive
   scoping applied, the directive IS delivered" — is unchanged; only the correct sentinel value for that
   intent changes from `set()` to `None` under the corrected three-state guard).

**Files**: `tests/charter/test_action_bundle_delivery.py` (~4 line edits)
**Validation**: `pytest tests/charter/test_action_bundle_delivery.py -v` — all tests green both before and
after this edit is combined with T009's guard change (run it again after T009 to confirm).

## Subtask T009: Implementation — re-derive from `activated_*`, three-state-preserving

**Purpose**: Turn T007's four red tests GREEN; land the actual fix.

**Steps**:
1. In `_load_action_doctrine_bundle` (`action_doctrine_bundle.py`), replace the
   `doctrine_selection.selected_*`-derived assignments with:
   ```python
   directives_arg = pack_context.activated_directives if pack_context is not None else None
   project_directives = (
       {_normalize_directive_id(d) for d in directives_arg}
       if directives_arg is not None
       else set(load_doctrine_catalog().directives)
   )
   ```
   (illustrative shape only — design the actual conditional however reads cleanest, e.g. a small private
   helper; the REQUIRED behavior is: a wholly-absent `pack_context` (`pack_context is None`) MUST be
   treated IDENTICALLY to a supplied `PackContext` whose `activated_directives` is `None` — both collapse
   to the SAME "no filter configured" state and resolve to the catalog default (ALL built-in directive
   ids), never empty sets. There is no separate "`pack_context is None` → degrade-gracefully empty sets"
   branch; that would silently narrow a wholly-absent activation input to "nothing activated," the exact
   defect class this mission exists to eliminate, and it collides with the already-green
   `test_context_bundle_none_path_matches_no_filter_at_all` regression test (`tests/charter/
   test_activation_consumers.py`, see Context section) which asserts `pack_context=None` and
   `pack_context` with `activated_directives=None` produce byte-identical `directive_ids`.
   `activated_directives == frozenset()` (an EXPLICIT, present `PackContext` with an empty set) → empty
   set (explicit exclude-everything, preserved distinctly — this is the one state that stays empty, and
   only reachable when a real `PackContext` is supplied); `activated_directives` non-empty → that set,
   normalized via `_normalize_directive_id` exactly as before. Apply the identical shape to
   `selected_tactics`/`selected_paradigms` from `pack_context.activated_tactics`/`.activated_paradigms`,
   with `load_doctrine_catalog().tactics`/`.paradigms` as the default for BOTH the wholly-absent-
   `pack_context` case and the present-but-`None`-field case alike (never an empty set for either — see
   the Context section's chokepoint note).
2. Preserve the org-pack `required_<kind>` union — **precise finding from reading
   `org_pack_discovery.py` in full for this WP**: `_load_doctrine_selection(repo_root)` (the function
   `_load_action_doctrine_bundle` currently calls) already internally unions every org pack's
   `required_<kind>` onto the project-authored `selected_<kind>` fields (see its docstring: "UNIONs every
   org pack's `required_<kind>` into the matching `selected_<kind>` field") via the module-level helper
   `_read_org_required_selections(repo_root) -> dict[str, list[str]]`, keyed by
   `_REQUIRED_KIND_FIELDS = ("directives", "tactics", "paradigms", "styleguides", "toolguides",
   "procedures", "agent_profiles", "mission_step_contracts")` — `_read_org_required_selections` IS listed
   in `org_pack_discovery.py`'s own `__all__`, so it is a legitimate, already-public-within-`charter.activation`
   import target, not a reach into a private internal. Since `doctrine_selection` (the
   `_load_doctrine_selection(repo_root)` return value) is used in `_load_action_doctrine_bundle` for
   NOTHING except the three project-authored `selected_directives`/`.selected_tactics`/`.selected_paradigms`
   reads this WP is replacing (confirmed by reading the full function body — no other use of
   `doctrine_selection` exists), **replace the `_load_doctrine_selection(repo_root)` call entirely** with a
   direct `_read_org_required_selections(repo_root)` call, and union its `"directives"`/`"tactics"`/
   `"paradigms"` entries onto the `activated_*`-derived set from step 1 (not onto the retired `selected_*`
   set) — this is Decision Record 2's confirmed-legitimate, separate concept and must not regress (spec
   User Story 2 Scenario 3 / FR-006's own explicit instruction). An explicitly-empty
   `activated_directives: []` must still receive the org-required union on top (spec Edge Cases) — do not
   conflate "explicitly empty" with "skip the union step." If, once you actually make this edit, you find
   another use of `doctrine_selection` you missed, keep `_load_doctrine_selection` for that other use and
   union `_read_org_required_selections` alongside it instead of removing the call — note the deviation
   from this prompt's assumption in the PR description if so.
3. In `delivery_table.py`'s `_classify_artifact_urns`, change the exclusion guard from
   `if node.kind is NodeKind.DIRECTIVE and project_directives and artifact_id not in project_directives:`
   to `if node.kind is NodeKind.DIRECTIVE and project_directives is not None and artifact_id not in
   project_directives:` — the `is not None` form correctly treats an explicit `frozenset()`/`set()` as
   "exclude everything" while `None` (should never reach here after step 1's early conversion, but keep the
   guard correct regardless) would mean "no filter." Since step 1 never lets `None` reach this function
   (it always converts to a concrete set before calling `_classify_artifact_urns`), this guard change is
   defense-in-depth for correctness-by-construction, not the load-bearing fix — the load-bearing fix is
   step 1's early conversion.
4. Remove or annotate as dead/defense-in-depth the `selected_tactics = selected_tactics or set()` /
   `selected_paradigms = selected_paradigms or set()` lines in `_classify_artifact_urns` (per Context's
   note) — state your choice in the PR description.
5. Run T007/T008's tests — all must now be GREEN. Re-run the baseline diff (T006's captured baseline vs.
   post-implementation) — no newly-red node-id outside this mission's own intentionally-flipped tests.

**Files**: `src/charter/activation/action_doctrine_bundle.py` (~30-50 line change),
`src/charter/activation/context_renderers/delivery_table.py` (~5-10 line change)
**Validation**: `pytest tests/charter/test_action_doctrine_bundle_activation.py
tests/charter/test_action_bundle_delivery.py -v` — all green.

## Subtask T010: Final gate re-run

**Purpose**: Confirm `test_no_dead_symbols.py` and the full scoped charter/architectural gate set stay
green against the finished diff.

**Steps**:
1. `pytest tests/charter/ tests/architectural/test_charter_offering_does_not_import_activation.py
   tests/architectural/test_no_dead_symbols.py -q` — diff against T006's baseline.
2. **Named collision gate (do not rely on step 1's baseline-diff alone to catch this):** explicitly
   re-run `pytest tests/charter/test_activation_consumers.py -k none_path_matches_no_filter_at_all -v`
   and confirm all FOUR `*_none_path_matches_no_filter_at_all` tests are GREEN, in particular
   `test_context_bundle_none_path_matches_no_filter_at_all` (this WP's own consumer,
   `_load_action_doctrine_bundle`). This file is out of `owned_files` and untouched by this WP's diff, but
   T009's `pack_context is None` handling can silently flip it red if the catalog-default collapse
   (Context section) is not implemented exactly as specified — verify it live, do not assume the generic
   node-id diff would surface it clearly enough on its own.
3. `ruff check src/charter/activation/action_doctrine_bundle.py
   src/charter/activation/context_renderers/delivery_table.py tests/charter/test_action_doctrine_bundle_activation.py
   tests/charter/test_action_bundle_delivery.py` and the `--select TID251` pass on the same paths.
4. Commit the implementation (T009's changes) as a separate commit from T007/T008's red-first test commits,
   per C-011. T008's four-call-site edit may be folded into either the red-first commit (it is a test-only
   change preserving intent) or the implementation commit — your call; state which you chose in the PR
   description.

**Files**: none new (verification only)
**Validation**: All commands pass/report zero violations.

## Definition of Done

- `tests/charter/test_action_doctrine_bundle_activation.py` exists with four red-first-then-green cases
  (FR-007, FR-008, FR-014, and the plan-added tactics/paradigms-absent sibling fixture), `pytest.mark.fast`.
- `tests/charter/test_action_bundle_delivery.py`'s four `set()` call sites now pass `None`; all its
  existing tests remain green.
- `_load_action_doctrine_bundle` derives `project_directives`/`selected_tactics`/`selected_paradigms` from
  `pack_context.activated_*` with the org-required union preserved on top.
- `_classify_artifact_urns`'s exclusion guard is `is not None`, never bare truthiness.
- `None` is converted to a concrete (catalog-default or explicit-empty) value once, at assignment in
  `_load_action_doctrine_bundle`, before any consumption site iterates it.
- `test_no_dead_symbols.py` and the C-004 gate both pass.

## Risks

- **Truthiness collapse in either file**: the single highest-risk mistake is leaving ANY `x or set()` /
  bare `if project_directives:` shortcut anywhere in the changed code paths — grep the diff for `or set()`
  and bare truthiness on all three re-derived values before declaring T009 done.
- **Missing the early-conversion point**: converting `None` inside `_classify_artifact_urns` instead of at
  the `_load_action_doctrine_bundle` assignment site would leave `roots`'s generator expressions (in the
  CALLER, before `_classify_artifact_urns` is ever invoked) still exposed to a raw `None`, reintroducing the
  `TypeError` risk T007's sibling fixture exists to catch.
- **Org-required union onto the wrong base**: unioning `required_<kind>` onto the retired `selected_*` set
  instead of the new `activated_*`-derived set would silently regress FR-006's own explicit requirement —
  re-read Decision Record 2's Scenario 3 before finalizing.
- **`pack_context is None` treated as a separate "degrade-gracefully empty sets" branch**: this is the
  same narrowing-of-`None` defect class this mission exists to eliminate, just relocated from a field-level
  read to the whole-argument level. It would flip the already-green, out-of-`owned_files`
  `tests/charter/test_activation_consumers.py::test_context_bundle_none_path_matches_no_filter_at_all` red
  (and, by the same logic, is a live risk for its three siblings covering the other consumers) because that
  test asserts `pack_context=None` and `pack_context` with `activated_directives=None` must produce
  identical output. `pack_context is None` MUST collapse to the same catalog-default path as
  `activated_directives is None` — see Context section and T009 step 1. T010 step 2 re-runs this test
  explicitly as a named gate.

## Reviewer Guidance

- Confirm the tactics/paradigms-absent fixture (T007 step 5) actually fails when run against the
  pre-implementation code — ask for the RED-run output.
- Confirm `pack_context is None` resolves to the SAME catalog-default outcome as a supplied `PackContext`
  whose `activated_directives`/`activated_tactics`/`activated_paradigms` are `None` — not a separate
  empty-set branch — by reading the diff's actual conditional, and confirm
  `tests/charter/test_activation_consumers.py`'s four `*_none_path_matches_no_filter_at_all` tests were
  actually re-run green (T010 step 2), not merely assumed covered by the generic baseline diff.
- Confirm the org-required union is unioned onto the `activated_*`-derived base, not the retired
  `selected_*` set, by reading the diff's actual assignment order.
- Cross-check this WP's `None`-handling against WP01's and WP03's for the identical semantic rule (the
  cross-WP chokepoint) — do not approve in isolation.
- Confirm the four `set()` → `None` edits in `test_action_bundle_delivery.py` did not silently change any
  assertion's expected outcome — only the input sentinel value should change.

Implementation command: `spec-kitty agent action implement WP02 --agent claude`
