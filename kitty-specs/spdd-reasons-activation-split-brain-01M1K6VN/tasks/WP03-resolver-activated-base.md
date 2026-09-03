---
work_package_id: WP03
title: resolver.py directive-base + paradigm-base re-derivation from activated_*
dependencies: []
requirement_refs:
- FR-011
- FR-012
- FR-013
- NFR-001
- NFR-002
planning_base_branch: fix/spdd-reasons-activation-split-brain-3838
merge_target_branch: fix/spdd-reasons-activation-split-brain-3838
branch_strategy: Planning artifacts for this mission were generated on fix/spdd-reasons-activation-split-brain-3838. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/spdd-reasons-activation-split-brain-3838 unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
history: []
agent_profile: implementer-ivan
authoritative_surface: src/charter/activation/
create_intent:
- tests/charter/test_resolver_activation_parity.py
execution_mode: code_change
model: ''
owned_files:
- src/charter/activation/resolver.py
- tests/charter/test_resolver_activation_parity.py
role: implementer
tags: []
tracker_refs: []
---

# WP03 — Re-derive `resolve_project_governance`'s directive base and paradigm list from `activated_*`

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `implementer-ivan`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Invert `_resolve_directive_base`'s current priority (charter-authored `selected_directives`, when
non-empty, silently overrides and never consults `activated_*`) so `PackContext.activated_directives`
becomes the *base*, with `selected_directives` unioned onto it — never substituting for it. Add an
equivalent `activated_paradigms`-derived base to `resolve_project_governance` (today there is NO
`activated_*` read for paradigms at all). This is Decision Record 3's fold-in — a third, independently
found instance of the same defect class, discovered during adversarial spec review (FR-011/012/013).

## Context

**Live citations, re-read in full for this WP (not copied from plan.md without checking):**

`_resolve_directive_base` (`src/charter/activation/resolver.py`) already reads
`PackContext.from_config(repo_root).activated_directives` — but only inside the `else` branch reached when
`doctrine.selected_directives` is EMPTY:

```python
if doctrine.selected_directives:
    missing = sorted(d for d in doctrine.selected_directives if d not in valid_ids)
    if missing:
        raise GovernanceResolutionError([...])
    return list(doctrine.selected_directives), "charter"

from charter.activation.pack_context import PackContext  # noqa: PLC0415
activated_directives = PackContext.from_config(repo_root).activated_directives
if activated_directives is None:
    base = sorted(doctrine_catalog.directives)
    diagnostics.append(f"No activated directive set configured; using built-in catalog default ({len(base)} directives).")
    return base, "catalog_fallback"
return sorted(activated_directives), "activation"
```

When `doctrine.selected_directives` is non-empty — the ordinary case for any project that selected
directives at charter-bootstrap — it is returned VERBATIM at the `return list(doctrine.selected_directives),
"charter"` line, and `activated_directives` is never consulted at all. This is a **full override**, not the
softer exclude/under-seed failure WP02 fixes.

`resolve_project_governance` (same file) does, unconditionally:
```python
selected_paradigms = list(doctrine.selected_paradigms)
_validate_paradigm_selection(selected_paradigms, doctrine_catalog)
```
— there is no `PackContext.activated_paradigms` read anywhere in this function today.

**The fix inverts the priority, mirroring the ALREADY-EXISTING pattern `_resolve_directives_selection`
uses for `directives_cfg.directives`** (project-local additive layer, unioned onto whatever base
`_resolve_directive_base` returns — see that function's own docstring: "the base set... Project-local
directives declared in the `charter.yaml` `directives:` section are then unioned onto that base — they
never replace it"). This WP makes `doctrine.selected_directives`/`.selected_paradigms` behave the SAME
way relative to the `activated_*`-derived base, instead of short-circuiting to replace it.

**Cross-WP semantic chokepoint (read before implementing):** WP01/WP02/WP03 all encode the SAME rule —
`activated_directives is None` (key absent) means "all built-ins," via the catalog fallback — this function
ALREADY has that guard correct for the case it currently reaches (`if activated_directives is None: base =
sorted(doctrine_catalog.directives)`); your job in this WP is to make MORE cases reach that already-correct
guard (by removing the short-circuit), not to rewrite the guard itself. For paradigms, you are adding the
guard fresh — mirror the directive guard's `is None` shape exactly (never `x or set()`/truthiness).

**One-PR-shape / baseline-capture note**: same as WP01/WP02 — capture your own baseline (identical scoped
command, WP01's Context section) in your own workspace before any functional change.

### Marker discipline (verified live — SK-144/#3241)

`tests/charter/test_resolver_activation_parity.py` (NEW, this WP) — use `pytestmark = pytest.mark.fast`.
**Correcting plan.md section (j)'s table**, which listed `fast, doctrine` for this file. The REAL local
convention across every resolver-concern file in `tests/charter/` (`test_resolver.py`,
`test_resolver_tier_axis_via_factory.py`, `test_resolver_activation_gating.py` — all confirmed by reading
the live files for this WP) is `pytest.mark.fast` alone; none of them carry `pytest.mark.doctrine`. As with
WP02, collection is unaffected either way (both `fast-tests-charter` and `doctrine-charter-tests.yml`
select by the `fast` marker + `tests/charter/` path, not by `doctrine`) — this is a sibling-convention
correction, not a functional one.

**Do NOT add these tests to the existing `tests/charter/test_resolver_activation_gating.py`.** That file
(read in full for this WP) is narrowly scoped to `DoctrineService`'s gated-property wrapper (six
"mechanical" gated kinds — directives, tactics, styleguides, toolguides, mission_step_contracts,
glossary_packs — via `getattr(inner, prop)` mock plumbing), a genuinely different `resolver.py` surface
from `_resolve_directive_base`/`resolve_project_governance`/`GovernanceResolution`. Its own module
docstring frames it as "T032 — bare-project equality regression, 6 new gated kinds" — adding FR-012/013's
fixtures there would be a scope mismatch, not a natural extension. A new file keeps both files' concerns
legible.

### `__all__` / C-007 disposition

`resolver.py` already declares `__all__ = ["DEFAULT_TOOL_REGISTRY", "DoctrineService", "GovernanceResolution",
"GovernanceResolutionError", "collect_governance_diagnostics", "resolve_governance_for_profile",
"resolve_project_governance"]` (confirmed live) — unaffected by this WP: `_resolve_directive_base` and the
paradigm-base logic you add are both private helpers (`_`-prefixed), already not in `__all__`, with
`resolve_project_governance` (already `__all__`-listed) as their real in-module caller. If you factor a NEW
private helper (e.g. `_resolve_paradigm_base`, mirroring `_resolve_directive_base`'s shape), it does not
need to be added to `__all__` either — same reasoning. `collect_governance_diagnostics`
(`resolver.py:937-952`, re-exported from `charter/__init__.py`) needs NO separate handling per Decision
Record 3 — it only forwards `resolution.diagnostics`/`exc.issues`, never `.directives`/`.paradigms`
directly, so this WP's fix reaches it as a side effect through `resolve_project_governance`'s corrected
output; do not add a separate test or code path for it.

## Subtask T011: Baseline capture + red-first FR-012/FR-013 tests

**Purpose**: Capture this WP's baseline (section g) and commit FR-012's directive-base-override test and
FR-013's paradigms-zero-fallback test, both RED first against the unmodified `resolver.py` (C-011).

**Steps**:
1. Run the baseline command from WP01's Context section in your own workspace; save the failing node-id
   list.
2. Create `tests/charter/test_resolver_activation_parity.py` with `pytestmark = pytest.mark.fast`.
3. **FR-012** — construct a `tmp_path` charter where `.kittify/config.yaml`'s (or the pointed
   `charter.yaml`'s) `activated_directives` includes a directive (e.g. `DIRECTIVE_038`), and the charter's
   authored `governance.charter.selected_directives` is a DIFFERENT, non-empty, disjoint set (e.g.
   `["DIRECTIVE_010"]`, both present in the catalog/local directive set so the existing validation in
   `_resolve_directive_base` does not reject them as "unavailable"). Assert
   `resolve_project_governance(tmp_path).directives` includes `DIRECTIVE_038`.
   **Why RED on `main` today**: `_resolve_directive_base`'s `if doctrine.selected_directives: ... return
   list(doctrine.selected_directives), "charter"` branch fires first (verified live, the exact line quoted
   in Context above) and returns `["DIRECTIVE_010"]` verbatim — `activated_directives` is never consulted
   because that branch already returned. `DIRECTIVE_038` is absent from the result.
4. **FR-013** — construct a `tmp_path` charter where `activated_paradigms` includes a paradigm (or is an
   explicit `frozenset()` — nothing activated) that is absent from (or contradicted by)
   `governance.charter.selected_paradigms`. Assert `resolve_project_governance(tmp_path).paradigms`
   reflects `activated_paradigms` as the base (not an unconditional `selected_paradigms` passthrough).
   **Why RED on `main` today**: `resolve_project_governance`'s `selected_paradigms = list(doctrine.selected_paradigms)`
   is unconditional (verified live, no `activated_*` read exists anywhere in this function for paradigms) —
   the resolved `paradigms` list is always exactly `doctrine.selected_paradigms`, regardless of
   `activated_paradigms`.
5. Add a Scenario-3-mirroring "no-flip" case for both directives and paradigms: when `selected_*` and
   `activated_*` FULLY AGREE (both select the same set, or both select nothing), the resolved value is
   unchanged from what `main` already produces — this mission does not flip any project whose two sources
   already agree (mirrors User Story 1 Scenario 3 / User Story 3 Scenario 3). This case is expected to be
   GREEN on `main` already (a regression guard against the fix over-correcting), not a red-first case —
   state this explicitly in the test's docstring, same discipline as WP01's T001.

**Files**: `tests/charter/test_resolver_activation_parity.py` (new, ~150-180 lines)
**Validation**: `pytest tests/charter/test_resolver_activation_parity.py -v` — FR-012/FR-013 cases RED
against the unmodified `resolver.py`; the agreement case(s) already GREEN.

## Subtask T012: Implementation — invert the directive-base priority, add the paradigm-base read

**Purpose**: Turn T011's red tests GREEN.

**Steps**:
1. Rewrite `_resolve_directive_base` so the `activated_*`-derived value is computed FIRST as the base
   (reuse the existing `else`-branch logic verbatim — it already correctly implements the three-state
   `is None` guard with catalog fallback and diagnostic), THEN union `doctrine.selected_directives` (when
   non-empty, validated against `valid_ids` exactly as the current `if doctrine.selected_directives:`
   branch already does) onto that base — mirroring `_resolve_directives_selection`'s existing
   base-plus-project-local union shape (dedup via `dict.fromkeys`, diagnostic naming what was added, base
   order preserved, no base id ever dropped). Return the unioned list with a provenance label reflecting
   both sources were consulted (e.g. `"activation+charter"` when both contributed, or keep `"activation"`/
   `"charter"` alone when only one did — your call on the exact label string; the load-bearing behavior is
   the union, not the label spelling. Whatever you choose, keep it distinct from `_resolve_directives_selection`'s
   own `"{base_source}+project_local"` label so a diagnostic reader can tell which union layer added what).
2. Add a NEW paradigm-base resolution (a small private helper mirroring `_resolve_directive_base`'s shape,
   or inlined directly into `resolve_project_governance` — your call) that reads
   `PackContext.from_config(repo_root).activated_paradigms` with the identical three-state guard
   (`is None` → catalog default via `load_doctrine_catalog().paradigms`, sorted; `frozenset()` → `[]`;
   non-empty → `sorted(activated_paradigms)`), then unions `doctrine.selected_paradigms` (when non-empty,
   validated via the EXISTING `_validate_paradigm_selection` call already in `resolve_project_governance`)
   onto that base — never substituting for it. Replace the current unconditional
   `selected_paradigms = list(doctrine.selected_paradigms)` line with this new base-then-union shape.
3. Run T011's tests — both FR-012 and FR-013 cases, plus the agreement-case regression guards, must now be
   GREEN. Re-run the baseline diff.

**Files**: `src/charter/activation/resolver.py` (~40-60 line change: `_resolve_directive_base`'s priority
inversion, a new paradigm-base helper/inline block, `resolve_project_governance`'s paradigm assignment)
**Validation**: `pytest tests/charter/test_resolver_activation_parity.py -v` — all green.

## Subtask T013: Verify the five real consumers reflect the fix with zero consumer-side code changes

**Purpose**: Decision Record 3 names five real call sites of `resolve_project_governance`'s output — this
fix is isolated to `resolve_project_governance`/`_resolve_directive_base` inside `resolver.py`, and every
consumer must reflect the corrected resolution WITHOUT its own code changing (User Story 3 Scenario 4).

**Steps**:
1. Re-confirm (read, do not assume) that none of these five call sites need a code change:
   `src/runtime/next/prompt_builder.py`'s `_legacy_governance_context`;
   `src/charter/activation/context_json.py`'s `_load_project_directives_with_source`/
   `_project_directive_entries_with_source`; `src/charter/activation/compact.py`'s
   `_resolve_governance_summary`; `src/specify_cli/runtime/doctor.py`'s `check_governance_resolution`;
   `src/charter/activation/resolver.py`'s own `collect_governance_diagnostics` (re-exported from
   `src/charter/__init__.py`). Each should already consume `GovernanceResolution.directives`/`.paradigms`/
   `.diagnostics` structurally, with no hardcoded assumption about `_resolve_directive_base`'s internal
   priority order.
2. Run the scoped gate set (`pytest tests/charter/ tests/architectural/test_charter_offering_does_not_import_activation.py
   tests/architectural/test_no_dead_symbols.py -q`) and diff against T011's baseline — no newly-red node-id
   outside this mission's own intentionally-flipped tests.
3. `ruff check src/charter/activation/resolver.py tests/charter/test_resolver_activation_parity.py` and the
   `--select TID251` pass on the same paths.
4. Commit the implementation (T012's changes) as a separate commit from T011's red-first test commit, per
   C-011.

**Files**: none new (verification only, unless step 1 finds an actual consumer-side dependency on the old
priority order — if so, note the deviation from this prompt's assumption in the PR description; do not
silently patch a fifth consumer without flagging it)
**Validation**: All commands pass/report zero violations; five-consumer re-check confirms no code change
needed at any of them.

## Definition of Done

- `tests/charter/test_resolver_activation_parity.py` exists, `pytest.mark.fast`, FR-012/FR-013 committed
  RED first, both GREEN after T012.
- `_resolve_directive_base` no longer short-circuits on non-empty `doctrine.selected_directives`; it
  computes the `activated_*`-derived base first and unions `selected_directives` onto it.
- `resolve_project_governance` reads `PackContext.from_config(repo_root).activated_paradigms` as the
  paradigm base, unioning `doctrine.selected_paradigms` onto it.
- Both the directive and paradigm "already agree" cases are unchanged from `main`'s current behavior
  (verified, not merely asserted).
- The five named consumers require zero code changes; `test_no_dead_symbols.py` and the C-004 gate stay
  green.

## Risks

- **Truthiness collapse**: as with WP01/WP02, any `x or set()`/bare-truthiness shortcut on
  `activated_directives`/`activated_paradigms` anywhere in this WP's diff silently reintroduces the bug
  class. The existing `_resolve_directive_base` `is None` guard is already correct for directives — do not
  accidentally rewrite it into a truthiness form while inverting the priority.
- **Losing the catalog-availability validation**: `_resolve_directive_base`'s existing validation (raising
  `GovernanceResolutionError` for a `selected_directives` id not in `valid_ids`) must still fire for the
  UNIONED `selected_directives`, not be silently dropped when the priority inverts.
- **Label/provenance drift**: changing the `source` string returned alongside the directive list could
  break an unrelated caller that pattern-matches on the exact string `"charter"`/`"activation"`/
  `"catalog_fallback"` — grep `src/` for any such match before finalizing the label choice in T012 step 1.

## Reviewer Guidance

- Confirm FR-012/FR-013 were actually run RED against the pre-fix `resolver.py` (ask for the RED-run
  output).
- Confirm the union in T012 preserves EVERY base id (no base id dropped) — spot-check against
  `_resolve_directives_selection`'s existing union-preservation invariant.
- Cross-check this WP's `None`-handling against WP01's and WP02's for the identical semantic rule (the
  cross-WP chokepoint) — do not approve in isolation.
- Confirm no consumer of `GovernanceResolution`/`resolve_project_governance` needed a code change; if T013
  step 1 found one, confirm it was flagged, not silently patched without discussion.

Implementation command: `spec-kitty agent action implement WP03 --agent claude`
