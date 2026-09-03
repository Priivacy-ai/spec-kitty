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

## Union/Exclusion Boundary Audit (operator ruling, tasks phase R4 — binding acceptance requirement)

Three consecutive review rounds each found a distinct instance of ONE class of defect: an absent or
un-normalized identifier silently collapsing to a wrong value instead of the correct one, at a union or
exclusion boundary, with no fixture pinning the failure. The operator ruling
(`reviews/tasks.ruling.md`) requires this WP's acceptance to state the invariant explicitly and enumerate
**every** union/exclusion boundary this WP's files touch — not only the two boundaries where findings
happened to land — confirming for each whether it canonicalizes its inputs or fails loud.

**The invariant** (binding for every boundary below): every directive, tactic and paradigm identifier is
canonicalized at the moment it enters a union, and every union and exclusion boundary either canonicalizes
its inputs or fails loud. An identifier whose form cannot be canonicalized is an error, never a
silently-excluded entry. Absent input resolves to the documented catalog default, never to an empty set.

**A precondition fact, verified live and load-bearing for every boundary below**: directives have a
genuine stem-vs-canonical distinction (`_normalize_directive_id`, `profile_resolution.py:203-216`, folds a
stem like `024-locality-of-change` to `DIRECTIVE_024`) because built-in directive files are authored with a
numeric-prefixed filename stem (`packs/built-in/directives/024-locality-of-change.directive.yaml`) whose
`id:` field is the DIFFERENT canonical form (`id: DIRECTIVE_024`). **Tactics and paradigms have NO such
distinction** — verified live by reading every built-in tactic/paradigm file's `id:` field (e.g.
`packs/built-in/tactics/adversarial-qa-handoff.tactic.yaml`'s `id: adversarial-qa-handoff`,
`packs/built-in/paradigms/atomic-design.paradigm.yaml`'s `id: atomic-design`) — the filename stem AND the
canonical `id:` field are the SAME slug string for every built-in tactic/paradigm, and no
`_normalize_tactic_id`/`_normalize_paradigm_id` function (or any sibling) exists anywhere in `src/`
(grepped live, zero results). This is a fact this WP's fixes below rely on, not an assumption of symmetry
with directives — a tactic/paradigm id is already in its one and only canonical form the moment it is
authored, so "canonicalize" is a no-op for those two kinds; "fails loud" reduces to whatever validation
already exists for catalog membership (out of scope for this WP — see WP03's own boundary list for where
paradigm-membership validation lives).

Boundaries, enumerated:

1. **`project_directives` derivation from `pack_context.activated_directives`** (T009 step 1,
   `action_doctrine_bundle.py`) — `directives_arg` entries pass through
   `{_normalize_directive_id(d) for d in directives_arg}`; absent (`None`) converts to
   `set(load_doctrine_catalog().directives)`, never an empty set. **FIXTURE-BACKED this round (analyze-phase
   Finding A1, severity HIGH)**: T009 step 1's illustrative code already showed the normalization
   comprehension, but until this round no T007 fixture actually exercised this specific boundary with a
   stem-form id supplied DIRECTLY via `activated_directives` — every other case either used an
   already-canonical id on this path, or exercised stem-form normalization only via the separate
   org-required-union path (boundary 3, T007 step 6). Now backed by a red-first fixture in T007 step 7
   (`activated_directives: frozenset({"024-locality-of-change"})`, no org-pack involved) proven to fail
   against a T009 implementation that omits `_normalize_directive_id` on this direct-assignment boundary.
   **Caveat, mirroring boundary 4's honesty below**: `_normalize_directive_id` closes the stem-vs-canonical
   *form* gap only. Read live (`profile_resolution.py:203-220`), its final fallback for input matching
   neither `DIRECTIVE_NNN` nor a numeric-prefixed stem is `return raw.upper().replace("-", "_")` — it never
   raises, so a genuinely-unrecognizable (not merely stem-form) id still produces *some* string and enters
   `project_directives`. That manufactured id then flows into `start_urns`/`roots` (boundary 6) as an
   unresolvable `directive:...` URN, which `resolve_transitive_refs` (`drg/query.py`) silently records in
   its `unresolved` list rather than raising (its own docstring: "Raises: Nothing... Unknown start URNs are
   recorded in `unresolved`, per the frozen contract"). This catalog-*membership* validation gap is
   pre-existing in `_normalize_directive_id`'s own contract, predates this mission, and is out of this WP's
   scope to close (no such validation exists for this normalizer on `main` today) — this WP does not
   regress it, but boundaries 1, 3, 5, and 6 below all inherit it via `project_directives`.
2. **`selected_tactics`/`selected_paradigms` derivation from `pack_context.activated_tactics`/
   `.activated_paradigms`** (T009 step 1) — no normalization call (per the precondition fact above, none
   is needed: tactic/paradigm ids have no stem-vs-canonical distinction to fold); absent (`None`) converts
   to `load_doctrine_catalog().tactics`/`.paradigms`, never an empty set (the Context section's chokepoint
   note is explicit that an explicit empty set here would be "the exact softer failure this WP exists to
   close, relocated rather than fixed"). **Already correct by this round's own design** (fixed by the prior
   round).
3. **The org-required union onto `project_directives`** (T009 step 2, `"directives"` entries from
   `_read_org_required_selections`) — **FIXED this round (TASKS-FRESH2-001, severity 4)**: T009 step 2 now
   explicitly instructs normalizing each entry via `_normalize_directive_id` before the union, backed by a
   red-first fixture in T007 step 6 proven to fail against the pre-this-round T009 text. This was the
   literal severity-4 finding this round exists to fix. **Same caveat as boundary 1 above**:
   `_normalize_directive_id` never raises for a genuinely-unrecognizable org-required id — it only closes
   the stem-vs-canonical form gap, not catalog membership; a garbled `required_directives:` entry still
   degrades silently via `resolve_transitive_refs`'s pre-existing "unresolved, never raises" contract, a
   gap in the normalizer's own contract this WP does not regress and is out of scope to close.
4. **The org-required union onto `selected_tactics`/`selected_paradigms`** (T009 step 2, `"tactics"`/
   `"paradigms"` entries from `_read_org_required_selections`) — **out of scope / vacuously satisfied**: per
   the precondition fact above, tactic/paradigm ids have no stem-vs-canonical distinction anywhere in this
   repo's authoring convention, so there is nothing for a normalizer to fold — the raw
   `_read_org_required_selections(...)["tactics"]`/`["paradigms"]` string IS already the canonical id. T009
   step 2's existing instruction to union these two kinds' entries directly (unlike `"directives"`, which
   now normalizes first) is therefore correct as written, not an oversight. (This boundary does not
   currently fail loud for a genuinely-invalid, not-in-catalog tactic/paradigm id — e.g. a typo — but that
   is a catalog-*membership* validation gap, not an identifier-*form*-canonicalization gap the invariant
   above addresses; no such validation exists on `main` today for the pre-existing `selected_tactics`/
   `selected_paradigms` path either, so this WP does not regress anything by leaving it unvalidated.)
5. **`delivery_table.py`'s exclusion guard** (`project_directives is not None and artifact_id not in
   project_directives`) — `artifact_id` comes from the DRG node's own URN (`urn.split(":", 1)[1]`), and DRG
   directive nodes are canonical-only (verified: `load_doctrine_catalog().directives` and every
   `packs/built-in/directives/*.directive.yaml`'s `id:` field are `DIRECTIVE_NNN` form). **Already correct,
   contingent on boundaries 1 and 3 above**: once `project_directives` is fully normalized at every entry
   point that feeds it (both fixed/confirmed above), this guard compares canonical-to-canonical. The guard's
   own `is not None` shape (vs. bare truthiness) is unchanged by this round — it was already fixed by the
   prior round per T009 step 3. **Inherits boundary 1/3's caveat**: "canonical-to-canonical" holds only for
   ids `_normalize_directive_id` actually recognized; a genuinely-unrecognizable id normalizes to a bogus
   string that simply never matches any real `artifact_id` here, so this specific guard neither raises nor
   mis-includes anything on its own — the silent drop happens one step later, inside this same function
   (`_classify_artifact_urns`), which separately builds its own internal `start_urns` from
   `project_directives` and passes them to `resolve_transitive_refs` (see boundary 6).
6. **`start_urns` construction** (`f"directive:{d}"` for `d in project_directives`, plus the
   `f"tactic:{t}"`/`f"paradigm:{p}"` equivalents) and **`roots` tuple construction**
   (`action_doctrine_bundle.py:230-235`) — same reasoning as boundary 5: both consume `project_directives`/
   `selected_tactics`/`selected_paradigms` only after boundaries 1-4's conversions have already run, so by
   construction they only ever see already-canonical (directives) or already-canonical-by-authoring-fact
   (tactics/paradigms) values. **Already correct, contingent on boundaries 1-4 above.** **Caveat**: this
   `roots` tuple (`action_doctrine_bundle.py:230-235`) is a display-only mirror for progressive disclosure,
   not itself passed to `resolve_transitive_refs` — but `_classify_artifact_urns` (boundary 5's file)
   separately re-derives an equivalent `start_urns` set from the same `project_directives` and DOES pass it
   to `resolve_transitive_refs`. If `project_directives` contains a bogus id (see boundary 1/3's caveat:
   `_normalize_directive_id` never raises for a genuinely-unrecognizable input), the resulting
   `directive:<bogus>` start URN matches no real graph node — `resolve_transitive_refs`
   (`src/charter/offering/drg/query.py`) does not raise for this either; per its own docstring, "Unknown
   start URNs are recorded in `unresolved`, per the frozen contract." The bogus directive simply contributes
   nothing to the delivered set, with no error surfaced anywhere in this chain. This is a pre-existing gap
   in `_normalize_directive_id`'s own contract (not new behavior this WP introduces), structurally identical
   to the tactics/paradigms catalog-membership gap boundary 4 above already discloses — out of this WP's
   scope to close.

**Reviewer Guidance addition**: confirm boundaries 1, 2, 5, and 6 above by reading the diff's actual
conversion/assignment order (not merely trusting this table); confirm boundary 3's new normalization call
and its T007-step-6 fixture were actually run RED against the pre-this-round T009 text (ask for the RED-run
output); confirm boundary 4's "vacuously satisfied" claim by spot-checking that no `_normalize_tactic_id`/
`_normalize_paradigm_id` function was silently introduced or silently assumed — this WP does not need one
and should not add one.

## Subtask T006: Baseline capture

**Purpose**: Capture this WP's own pre-mission baseline (section g), in this WP's own workspace, before any
functional change.

**Steps**: Run the exact command from WP01's Context section
(`pytest tests/charter/ tests/architectural/test_charter_offering_does_not_import_activation.py
tests/architectural/test_no_dead_symbols.py -q`); save the full failing node-id list.

**Files**: none changed
**Validation**: Baseline list captured and classified per CLAUDE.md's three categories.

## Subtask T007: Red-first tests — FR-007/FR-008/FR-014, the tactics/paradigms-absent fixture, and the org-required normalization fixture (TASKS-FRESH2-001)

**Purpose**: Commit six red-first regression tests before any implementation change (C-011): the
directive-allowlist silent-drop (FR-007), this repo's own dogfood closure-starvation shape (FR-008), the
explicit-empty-`activated_directives`-excludes-everything case (FR-014), the plan-added
`activated_tactics`/`activated_paradigms`-absent sibling fixture (plan.md section (a) item 3, required
because none of FR-007/008/014 exercise a `None` `activated_tactics`/`activated_paradigms` case), the
stem-form org-required-directive normalization fixture (TASKS-FRESH2-001, required because none of the
other four cases exercise the org-required union path at all), and the direct-path stem-form directive
normalization fixture (analyze-phase Finding A1, severity HIGH, required because none of the other five
cases exercises boundary 1 — the direct `pack_context.activated_directives` assignment — with a stem-form
id; see step 7 below).

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
6. **Org-required stem-form directive normalization (TASKS-FRESH2-001)** — register an org pack (mirror
   `tests/charter/test_action_doctrine_bundle_org_fragment.py`'s `_register_pack` mechanism: write
   `.kittify/config.yaml`'s `doctrine.org.packs: [{name, local_path}]` pointing at a temp org-pack
   directory) whose `org-charter.yaml` declares `required_directives: [001-architectural-integrity-standard]`
   — the same stem-form id `tests/charter/test_answers_inert_and_org_union.py`'s
   `TestOrgRequiredIdFormNormalizedBeforePromotion` class uses and proves is a legitimate org-pack authoring
   shape (read that class live to match its real fixture-construction mechanism, not merely this
   description) — referencing a real, DRG-reachable built-in directive (`DIRECTIVE_001`) available to this
   fixture's DRG. Leave `activated_directives` absent/`None` on the project side, so `project_directives`'s
   only content comes from this org-required union. Assert `_load_action_doctrine_bundle`'s resulting
   bundle's `directive_ids` includes the CANONICAL `DIRECTIVE_001` form, and that `roots`/`start_urns`
   contain `directive:DIRECTIVE_001` — never the raw stem string `001-architectural-integrity-standard` in
   either place.
   **Why this MUST fail on the current (pre-this-round) T009 text**: unioning the raw, un-normalized stem
   string onto `project_directives` means the set contains `"001-architectural-integrity-standard"`, not
   `"DIRECTIVE_001"` — `"DIRECTIVE_001" not in project_directives` is `True`, so `delivery_table.py`'s
   exclusion guard drops the directive from `directive_ids`, and `roots`'s `f"directive:{d}"` construction
   emits the unresolvable stem-form URN instead of the canonical one. The fixture passes once T009 step 2's
   normalization instruction (below) is implemented.
7. **Direct-path stem-form directive normalization (analyze-phase Finding A1, severity HIGH)** — construct a
   fixture supplying a stem-form directive id DIRECTLY via `pack_context.activated_directives` (e.g.
   `activated_directives: frozenset({"024-locality-of-change"})`), **NOT** via org-pack promotion — leave
   any org-pack config absent/unregistered so this fixture's only source of
   `"024-locality-of-change"` is the direct `activated_directives` field itself, referencing a real,
   DRG-reachable built-in directive (`DIRECTIVE_024`, `packs/built-in/directives/024-locality-of-change.directive.yaml`)
   available to this fixture's DRG. Assert `_load_action_doctrine_bundle`'s resulting bundle's
   `directive_ids` contains the canonical `DIRECTIVE_024` form, not the raw stem string
   `024-locality-of-change`, and that `roots`/`start_urns` carry `directive:DIRECTIVE_024` (not
   `directive:024-locality-of-change`).
   **Why this MUST fail on a T009 implementation that omits normalization on this boundary**: this is
   boundary 1 in the Union/Exclusion Boundary Audit below (`project_directives` derivation directly from
   `pack_context.activated_directives`, T009 step 1) — distinct from step 6 above, which only exercises
   stem-form normalization via the SEPARATE org-required-union path (boundary 3). Every other case in this
   file either supplies an already-canonical id on the direct `activated_directives` path (FR-007/FR-008
   use `DIRECTIVE_038`/dogfood-shape ids) or exercises stem-form normalization only via org-pack promotion
   (step 6). A T009 step 1 implementation that dropped `_normalize_directive_id(d)` from the comprehension
   — assigning `directives_arg` straight into `project_directives` unnormalized — would pass every one of
   this file's other five cases untouched, because none of them puts a stem-form id on this specific
   direct-assignment boundary. This fixture closes that gap independently of whether boundary 3's
   (org-required) normalization is correctly implemented.

**Files**: `tests/charter/test_action_doctrine_bundle_activation.py` (new, ~300-340 lines)
**Validation**: `pytest tests/charter/test_action_doctrine_bundle_activation.py -v` — all six cases RED
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

   **MANDATORY normalization step for the `"directives"` entries (TASKS-FRESH2-001 remediation, severity 4
   — read this before writing the union) — apply `_normalize_directive_id` to EACH entry of
   `_read_org_required_selections(repo_root)["directives"]` BEFORE unioning it onto the
   `activated_*`-derived `project_directives` set from step 1, exactly the same way step 1 already
   normalizes `pack_context.activated_directives`'s own entries.** On `main` today, org-required directive
   ids get this normalization "for free" because `_load_doctrine_selection` unions them into
   `selected_directives` BEFORE `_load_action_doctrine_bundle`'s single `_normalize_directive_id`
   comprehension runs over the combined set (`action_doctrine_bundle.py:189`, the exact line this step
   replaces) — removing `_load_doctrine_selection` from the call chain (as this step does) removes that
   free normalization point too, and nothing in the plan text above replaces it. `required_directives:` is
   proven, live, to be legitimately authored in STEM form (not only canonical `DIRECTIVE_NNN`) —
   `tests/charter/test_answers_inert_and_org_union.py::TestOrgRequiredIdFormNormalizedBeforePromotion`
   round-trips `required_directives: [DIRECTIVE_001]`/`[001-architectural-integrity-standard]` through a
   sibling promotion pipeline and asserts both forms are legitimate org-pack authoring shapes — while the
   DRG's `artifact_id` (what `delivery_table.py`'s exclusion guard and `roots`'s `f"directive:{d}"`
   construction compare/emit against) and `load_doctrine_catalog().directives` are canonical-only
   (`DIRECTIVE_NNN`), verified live. Skipping this normalization would union a raw stem-form string into
   `project_directives`, and `delivery_table.py`'s exclusion guard (`artifact_id not in project_directives`)
   would then silently exclude that legitimately org-required, DRG-reachable directive — reproducing
   Decision Record 2's own "silent incorrect exclusion" mechanism via the org-required path, the exact
   defect class this mission exists to close (see the invariant in this WP's Definition of Done). Do this
   normalization for `"directives"` ONLY — do **not** apply `_normalize_directive_id` (a directive-specific
   normalizer) to the `"tactics"`/`"paradigms"` entries; see the Union/Exclusion Boundary Audit section
   below for why that boundary is vacuously satisfied instead.

   The required red-first fixture for this normalization step already exists — see T007 step 6
   (org-required stem-form directive normalization, TASKS-FRESH2-001) for its full construction and the
   "why this MUST fail on pre-this-round T009 text" reasoning; it is not a fresh instruction to add here.
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

- `tests/charter/test_action_doctrine_bundle_activation.py` exists with six red-first-then-green cases
  (FR-007, FR-008, FR-014, the plan-added tactics/paradigms-absent sibling fixture, the org-required
  stem-form normalization fixture (TASKS-FRESH2-001), and the direct-path stem-form normalization fixture
  (analyze-phase Finding A1)), `pytest.mark.fast`.
- `tests/charter/test_action_bundle_delivery.py`'s four `set()` call sites now pass `None`; all its
  existing tests remain green.
- `_load_action_doctrine_bundle` derives `project_directives`/`selected_tactics`/`selected_paradigms` from
  `pack_context.activated_*` with the org-required union preserved on top, and each org-required
  `"directives"` entry is normalized via `_normalize_directive_id` before it joins that union
  (TASKS-FRESH2-001).
- `_classify_artifact_urns`'s exclusion guard is `is not None`, never bare truthiness.
- `None` is converted to a concrete (catalog-default or explicit-empty) value once, at assignment in
  `_load_action_doctrine_bundle`, before any consumption site iterates it.
- `test_no_dead_symbols.py` and the C-004 gate both pass.
- **Union/exclusion boundary invariant (operator ruling, tasks phase R4)**: every directive, tactic and
  paradigm identifier is canonicalized at the moment it enters a union, and every union and exclusion
  boundary either canonicalizes its inputs or fails loud. An identifier whose form cannot be canonicalized
  is an error, never a silently-excluded entry. Absent input resolves to the documented catalog default,
  never to an empty set. Every union/exclusion boundary this WP owns is enumerated, boundary by boundary,
  in the "Union/Exclusion Boundary Audit" section below — the R5a verifier confirms each one individually,
  not in aggregate.

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
