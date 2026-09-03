# Implementation Plan: SPDD/REASONS activation split-brain

**Branch**: `fix/spdd-reasons-activation-split-brain-3838` | **Date**: 2026-09-03 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/spec.md`

**Note**: This template is normally filled in by `/spec-kitty.plan`. See
`src/doctrine/missions/software-dev/command-templates/plan.md` for the execution workflow. This
plan additionally carries the mission-specific sections (a)–(m) required by this mission's
readiness review, appended after the standard template sections.

## Summary

`is_spdd_reasons_active` (`src/charter/offering/spdd_reasons/activation.py`) and two other
readers (`_load_action_doctrine_bundle` via `action_doctrine_bundle.py`/`delivery_table.py`, and
`resolve_project_governance`/`_resolve_directive_base` in `resolver.py`) all decide activation by
reading `charter.yaml`'s authored, never-resynced `governance.charter.selected_*` section instead
of `PackContext.from_config`'s real `activated_*` authority. This plan rewrites all three readers
to consume `activated_*` (via the INV-2 two-file pointer resolution `PackContext.from_config`
implements), while respecting the `charter.offering -> charter.activation` import ban (C-004) by
giving `activation.py` its own raw, import-free `activated_*` read (Decision Record 1, Option A)
and re-pointing the other two readers — which already receive `pack_context`/call
`PackContext.from_config` — at the correct fields. No schema, write-path, or CLI-surface change;
pure read-path fix (NFR-004/C-002).

## Technical Context

**Language/Version**: Python 3.11+ (repo standard; `ruamel.yaml` already a dependency of both
`activation.py` and `pack_context.py`).
**Primary Dependencies**: `ruamel.yaml` (raw YAML read, no new dependency — matches the module's
existing "narrow compat read" idiom); no new third-party dependency.
**Storage**: N/A — reads `.kittify/config.yaml` / `.kittify/charter/charter.yaml` on disk; no
schema or write-path change (C-002).
**Testing**: `pytest`, scoped per NFR-005 to `tests/charter/` and the two named
`tests/architectural/` files — not a full-repo sweep.
**Target Platform**: Linux/macOS/Windows CLI (spec-kitty's existing target matrix); no
platform-specific behavior introduced.
**Project Type**: Single project (`src/charter/` seam inside the existing spec-kitty monorepo).
**Performance Goals**: `<50ms typical` for `is_spdd_reasons_active` per
`contracts/activation.md`'s existing budget — preserved: the rewrite reads at most two YAML files
(`config.yaml`, and the pointed `charter.yaml` when INV-2's pointer is present), the same file
count `PackContext.from_config` itself reads.
**Constraints**: C-004 (no `charter.offering -> charter.activation` import, non-vacuously
enforced); C-002 (no schema/write-path change); NFR-001 (no new silent-success path).
**Scale/Scope**: Four source modules edited (`activation.py`, `action_doctrine_bundle.py`,
`delivery_table.py`, `resolver.py`), three existing test files triaged, one new parity test file,
plus two contract docs and one glossary doc. No new CLI command, flag, or schema field.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **C-004 layering (hard gate, non-vacuous)**: `tests/architectural/test_charter_offering_does_not_import_activation.py`
  full-AST-walks `src/charter/offering/**` for any absolute or relative import resolving to
  `charter.activation`. The plan's entire design for `activation.py` (section a) exists to keep
  this gate green — no import of `charter.activation.pack_context.PackContext` or any other
  `charter.activation.*` symbol is added to `src/charter/offering/spdd_reasons/activation.py`.
  **PASS by design**, verified at Phase 1 close by re-running the gate.
- **NFR-002 (`test_no_dead_symbols.py`)**: any new helper symbol this mission introduces (a
  parity-test fixture helper, an INV-2-read helper inside `activation.py`, a re-derivation helper
  in `resolver.py`) must have a real `src/` caller or stay out of `__all__` / test-only. Addressed
  per-WP in the phasing section below.
- **Standing Order #2 (campsite cleaning)**: FR-003's `__all__` addition is folded into the WP
  that rewrites `activation.py`'s body rather than opened as its own preceding commit — see
  section (h) for the reasoning.
- **C-011 (ATDD-first)**: every WP below commits its failing-first test before its
  implementation commit — see section (i).

No constitution violations require the Complexity Tracking table below; it is left empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/
├── plan.md              # This file
├── spec.md              # Already authored (Specified)
├── tasks.md             # Phase 2 output (/spec-kitty.tasks — NOT created by this plan)
├── tracer-tooling-friction.md   # Seeded by the orchestrator at tasks/implement time (do not create here)
├── tracer-approach.md           # Seeded by the orchestrator (do not create here)
└── tracer-design-decisions.md   # Seeded by the orchestrator (do not create here)
```

No `research.md`, `data-model.md`, `quickstart.md`, or `contracts/` subdirectory is generated by
this mission's own planning phase: this is a small, code-grounded bug-fix mission whose "contract"
artifacts already exist upstream (`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/`)
and are edited in place (FR-009), not authored fresh.

### Source Code (repository root)

```
src/charter/offering/spdd_reasons/
└── activation.py                       # FR-001/003/004/005: full-body rewrite

src/charter/activation/
├── action_doctrine_bundle.py           # FR-006: re-derive project_directives/selected_tactics/selected_paradigms
├── context_renderers/
│   └── delivery_table.py               # FR-006/014: _classify_artifact_urns three-state-preserving guard
└── resolver.py                         # FR-011: _resolve_directive_base + resolve_project_governance

tests/charter/
├── test_charter_context_spdd_reasons.py         # FR-010 triage (bucket 3: 6 fixture-rewrites)
├── test_activate_resolves_no_answers_edit.py    # FR-010 triage (bucket 3: 1 fixture-rewrite)
├── test_answers_inert_and_org_union.py          # FR-010 triage (assertion-intent review only)
├── test_action_bundle_delivery.py               # WP2 scope: 4 call sites (`_classify_artifact_urns(..., set())`) updated to pass `None`
├── test_spdd_reasons_activation_parity.py       # NEW — FR-002 mandatory parity test
├── test_action_doctrine_bundle_activation.py    # NEW or existing-file addition — FR-007/008/014
└── test_resolver_activation_parity.py           # NEW or existing-file addition — FR-012/013

docs/context/charter.md                                              # FR-009: 3 glossary entries + 1 new entry
kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/
├── activation.md                                                    # FR-009
└── charter-context.md                                               # FR-009
```

**Structure Decision**: Single project, existing `src/charter/` package tree. No new top-level
directory. Test placement mirrors the three existing pinning-test files' location
(`tests/charter/`) and their marker convention (see section j). The two new/extended test files
for FR-007/008/014 and FR-012/013 are placed under `tests/charter/` alongside the resolver's and
action-bundle's existing test coverage — the exact filenames (new files vs. additions to an
existing `test_resolver*.py`/`test_action_doctrine_bundle*.py`) are a tasks-phase decision once
the existing test inventory for those two modules is enumerated; this plan fixes the directory
and marker discipline, not the final filename bikeshed.

## Complexity Tracking

*No Constitution Check violations requiring justification.*

---

## Mission-Specific Design Sections (a)–(m)

### (a) Seam and placement

All four edited modules live on the **charter seam**, split across its two internal packages per
the MAP-GATE topology (C-004):

| File | Package | FR(s) | Change |
|---|---|---|---|
| `src/charter/offering/spdd_reasons/activation.py` | `charter.offering` | FR-001/003/004/005 | Full-body rewrite: replace `_compute_active`/`_governance_selects_pack`/`_directives_select_pack` with a raw, `charter.activation`-import-free `activated_*` read |
| `src/charter/activation/action_doctrine_bundle.py` | `charter.activation` | FR-006 | Re-derive `project_directives`/`selected_tactics`/`selected_paradigms` (lines 189-191) from `pack_context.activated_*` instead of `_load_doctrine_selection`'s `selected_*` |
| `src/charter/activation/context_renderers/delivery_table.py` | `charter.activation` | FR-006/014 | `_classify_artifact_urns`'s exclusion guard becomes three-state-aware (`is not None` instead of bare truthiness); `None` is converted to a concrete value once at assignment in `action_doctrine_bundle.py` (item 3 below) so it never reaches `start_urns`'s comprehension or the exclusion guard as a live sentinel |
| `src/charter/activation/resolver.py` | `charter.activation` | FR-011/012/013 | `_resolve_directive_base` (line 675) and `resolve_project_governance` (line 815, the `selected_paradigms = list(doctrine.selected_paradigms)` at line 848) re-derive their base from `PackContext.activated_directives`/`.activated_paradigms`, unioning `selected_*` on top |
| `docs/context/charter.md` + 2 `contracts/*.md` | docs | FR-009 | Update the stated activation authority |

**How each caller obtains its `PackContext` without violating C-004** — confirmed against the
live signatures read for this plan, not assumed:

1. **`activation.py` (FR-001) — Decision Record 1, Option A.** `charter.offering.spdd_reasons`
   cannot import `charter.activation.pack_context.PackContext` at all (C-004 forbids
   `charter.offering -> charter.activation` in any form, absolute or relative, per the AST-walked
   gate). The rewritten `is_spdd_reasons_active` therefore gets its **own** raw `ruamel.yaml`
   read replicating `PackContext.from_config`'s INV-2 resolution steps 1–4 verbatim (spec
   Decision Record 1):
   - Load `.kittify/config.yaml` (absent file → the FR-004 pin, `False`; malformed YAML →
     propagate, FR-005).
   - Check for a `charter:` string-valued pointer key (mirrors
     `pack_context.resolve_charter_yaml_pointer`'s "only a string is a pointer" rule — a mapping
     `charter:` namespace, e.g. the legacy inline `synthesis_inputs` block, is NOT a pointer).
   - Pointer present → load the pointed `charter.yaml`'s top-level `activated_paradigms`/
     `activated_directives`/`activated_tactics` (dangling/unreadable pointer → raise, mirroring
     `_load_charter_activation_source`'s fail-loud `CharterPackConfigError`, FR-005). Pointer
     absent → read those same three keys directly from `config.yaml` itself (legacy shape).
   - Apply the three-state per-kind semantics verbatim (absent key → `None`/"all built-ins";
     `[]` → explicit empty; non-empty → explicit set), mirroring `_read_list_key`
     (`pack_context.py:609`).
   This is a second, independent implementation of INV-2's *reading* half — not a reimport of
   `PackContext` itself — which is exactly why FR-002's parity test is load-bearing (section b):
   nothing but that test proves the two independent readers stay in agreement.

   **Explicit carve-out, mirroring FR-004's precedent (re-verified against the live
   `compiler.py` for this plan, not assumed from the spec's summary):** this replication
   deliberately tracks `PackContext.from_config`'s raw, unconditional per-kind semantics (absent
   key → `None` → "all built-ins," independent of any other kind's state) — **not**
   `compile_charter`'s full delivered authority. Reading `compiler.py`'s
   `_resolve_config_activated_roots`/`_stems` (the function immediately following the
   `compile_charter` docstring spec.md's Summary quotes) shows it applies an additional
   `project_configured` gate (FR-018, a prior, deliberate fix): once a project has set ANY of the
   seven `activated_<kind>` fields (`_CONFIG_ACTIVATION_FIELDS` — directives, paradigms, tactics,
   styleguides, toolguides, procedures, agent_profiles) anywhere in its activation source, an
   OTHER, still-absent `activated_<kind>` key no longer falls back to "all built-ins" — it
   resolves to `frozenset()` instead. `is_spdd_reasons_active`'s rewrite, as specified by
   FR-001(d) ("applies the existing three-state per-kind semantics... verbatim, matching
   `PackContext._read_list_key`'s contract") and Decision Record 1 (which explicitly scopes the
   replication to `PackContext`'s raw per-ID resolution — the same Decision Record already
   carves `activated_kinds`'s coarse gate out of scope on identical reasoning, "faithful to the
   authority this spec's Summary actually cites"), does **not** apply this gate: on a project
   that has activated some but not all SPDD-relevant kinds, this mission's rewritten function and
   `compile_charter`'s real delivered set can disagree on whether the omitted kind counts as "all
   built-ins" or "nothing." Reopening FR-001/Decision Record 1's chosen replication boundary is
   out of scope for this fix round (this round fixes plan.md's fidelity to the spec it was
   scoped against, not the spec's own scope choices); this plan instead states the gap as an
   explicit, evidence-based carve-out — the same treatment FR-004 gives the absent-config-file
   case — so a future reader (or a later mission, if the `project_configured` gate is judged a
   real gap after all) has a named starting point rather than an implicit, undocumented
   divergence. **No fixture is added to section (b)'s matrix for this carve-out**: the matrix
   pins `PackContext`'s raw semantics per FR-002's own mandate, and a `project_configured`-gate
   fixture would test behavior this mission's chosen replication boundary explicitly does not
   claim to match.
2. **`action_doctrine_bundle.py` (FR-006) — no new plumbing.** Confirmed by reading
   `_load_action_doctrine_bundle`'s real signature (`action_doctrine_bundle.py:142-152`):
   `pack_context: PackContext | None = None` is **already** a parameter, populated by
   `_resolve_action_bundle` via `_PackContext.from_config(repo_root)` (line 136) before the call.
   FR-006 only changes what the function *does* with the parameter it already has — reads
   `pack_context.activated_directives`/`.activated_tactics`/`.activated_paradigms` instead of
   calling `_load_doctrine_selection(repo_root)` (line 185) for the project-authored half. The
   org-pack `required_<kind>` union (Decision Record 2's confirmed-legitimate separate concept)
   is preserved by unioning it onto the `activated_*`-derived set instead of onto
   `_load_doctrine_selection`'s retired `selected_*` output.
3. **`delivery_table.py` (FR-006/014) — same signature, three-state-aware body, ALL consumption
   sites named.** `_classify_artifact_urns` (`delivery_table.py`, function `_classify_artifact_urns`)
   already takes `project_directives: set[str]` positionally from its one caller inside
   `action_doctrine_bundle.py`; no signature change is needed at the call boundary, only the type
   of what flows through it (a `frozenset[str] | None` sentinel-preserving value instead of an
   always-plain `set[str]`). Re-reading the live file for this plan shows the re-derived
   `project_directives` value is consumed at **three** sites, not one, and the design commitment
   below covers all three explicitly:
   - `delivery_table.py`'s `start_urns` set-comprehension (`start_urns = {f"directive:{directive_id}"
     for directive_id in project_directives}`) — unconditional iteration, no `None`-guard today.
   - `delivery_table.py`'s exclusion guard inside `_classify_artifact_urns`'s node loop (today:
     `if node.kind is NodeKind.DIRECTIVE and project_directives and artifact_id not in
     project_directives` — bare truthiness, cannot distinguish `None` from `frozenset()`).
   - `action_doctrine_bundle.py`'s `roots` tuple construction (`roots = (action_urn, *(f"directive:{d}"
     for d in project_directives), ...)`) — the same unconditional iteration over the same value,
     in the caller module.

   **Chosen shape**: mirror the established pattern `resolver.py`'s `_resolve_directive_base`
   already uses for this exact three-state value (see item 4 below) — branch on
   `activated_directives is None` **once**, at the point in `action_doctrine_bundle.py` where
   `project_directives` is assigned from `pack_context.activated_directives` (replacing the
   current `_load_doctrine_selection`-derived assignment per FR-006), and convert `None` to a
   concrete value there (either the built-in catalog default or an explicit empty set, matching
   FR-001(d)'s "None = all built-ins" semantics) **before** the value is ever iterated — never let
   `None` reach `start_urns`'s comprehension, the exclusion guard, or `roots`'s construction as a
   live sentinel. This single early-conversion point replaces the "only the guard changes"
   framing entirely: `start_urns`'s comprehension and `roots`'s construction need no `None`-guard
   of their own because they never receive `None`; the exclusion guard's own change is still
   `is not None` (never bare truthiness) to correctly treat an explicit `frozenset()` — the value
   the early conversion step preserves distinctly from "all built-ins" — as "exclude everything"
   per FR-014.
   - **WP2 test fixture (new, distinct from FR-014's explicit-empty fixture)**: a case with
     `activated_directives` **absent** (`None`, not `[]`) on the `pack_context`, exercising
     `_load_action_doctrine_bundle` and `_classify_artifact_urns` end-to-end, asserting no
     `TypeError` and the "all built-ins" delivery outcome — committed red-first per section (i) so
     this crash path is caught before implementation, not discovered at review/CI time.
   - **`tests/charter/test_action_bundle_delivery.py` (WP2 scope, PLAN-GOV-001)**: this existing
     file calls `_classify_artifact_urns` directly at four sites (the two single-line calls
     `result = context._classify_artifact_urns(resolved.artifact_urns, graph, set())` and
     `delivered = context._classify_artifact_urns(resolved.artifact_urns, filtered, set())`,
     appearing four times across the file) passing a **bare `set()`** literal for
     `project_directives` and asserting the reachable directive IS delivered — i.e. asserting
     today's bare-truthiness "empty set == no filter" behavior. Under the corrected
     `is not None` guard, an explicit empty `set()` now means "exclude everything" (FR-014), which
     would flip all four assertions from delivering the directive to excluding it — breaking four
     currently-green tests that were never intended to test the explicit-empty-excludes-everything
     case. **WP2 must update these four call sites to pass `None` instead of a bare `set()`**,
     preserving each test's original intent ("no project-directive scoping applied" — the
     "all built-ins/no filter" sentinel), which is the correct three-state value for that intent
     under the new semantics. This is distinct from FR-014's own new test, which intentionally
     asserts the opposite (explicit `frozenset()`/`set()` excludes everything) — the two fixture
     values must not be conflated: `None` means "no filter" here, `frozenset()`/`set()` means
     "filter to nothing" in FR-014's test, and both must keep meaning that after this WP.
4. **`resolver.py` (FR-011) — already a direct `PackContext.from_config` caller.**
   `_resolve_directive_base` (`resolver.py:675`) already calls
   `PackContext.from_config(repo_root).activated_directives` (line 730) — but only inside the
   `else` branch reached when `doctrine.selected_directives` is empty (line 716's
   `if doctrine.selected_directives: ... return ... "charter"` short-circuits first). FR-011
   inverts this priority: `activated_directives` becomes the *base*, `selected_directives`
   (when non-empty) is unioned onto it, never substituting for it. `resolve_project_governance`
   (line 848) gains an equivalent `PackContext.from_config(repo_root).activated_paradigms` read
   where today there is none at all.

**C-004 compliance summary**: only `activation.py` needs new plumbing (its own raw read, item 1);
the other three files already hold everything they need (parameter or existing call) and change
only which field they consult. No file under `src/charter/offering/` gains an import of anything
under `src/charter/activation/` — verified against every file this plan edits (`activation.py` is
the only file under `offering/`; the other three are already under `activation/`, the *allowed*
import direction).

### (b) The parity test's design (FR-002) — load-bearing artifact

**File**: `tests/charter/test_spdd_reasons_activation_parity.py` (new; sibling location and
naming convention to the three existing pinning files already read for this plan —
`test_charter_context_spdd_reasons.py`, `test_activate_resolves_no_answers_edit.py`,
`test_answers_inert_and_org_union.py`, all under `tests/charter/`).

**What it compares**: the rewritten `is_spdd_reasons_active(repo_root)`'s boolean output against
a **hand-computed disjunction** of `PackContext.from_config(repo_root)`'s three `activated_*`
fields for the same `repo_root`. The oracle formula MUST NOT use Python's `x or set()` idiom —
that idiom coerces `None` (absent key) through the same falsy path as an *explicit* `[]`,
collapsing two of the three states this section's own semantics (and item 1's four-step
replication above) require staying distinct. The correct, three-state-preserving oracle is:
`pack_context.activated_paradigms is None or PARADIGM_ID in pack_context.activated_paradigms`,
`pack_context.activated_tactics is None or bool({TACTIC_FILL_ID, TACTIC_REVIEW_ID} &
pack_context.activated_tactics)`, and `pack_context.activated_directives is None or
any(_is_directive_038-equivalent match against pack_context.activated_directives)` — i.e. an
absent per-kind key (`is None`) evaluates as "selector satisfied" ("all built-ins" includes the
SPDD-relevant id), matching item 1's stated semantics and the codebase-wide `None` = "all
built-ins" contract (`pack_context.py`'s `_read_list_key`, `drg_activation.py`'s
`_node_is_activated`). This is the same four-selector disjunction `is_spdd_reasons_active`'s own
docstring already states, evaluated independently against `PackContext`'s real fields rather than
against `is_spdd_reasons_active`'s own internals (a test that imported `is_spdd_reasons_active`'s
helper functions to build the comparison would not be a parity test — it would be tautological).

**Fixture matrix** (FR-002's mandate, three states × three kinds × pointer-present/absent):

- **States** (per kind): (1) key absent from the activation source entirely, (2) key present as
  an explicit empty list, (3) key present with a non-empty list containing a SPDD-relevant ID.
- **Kinds**: `activated_paradigms` (with `structured-prompt-driven-development`),
  `activated_tactics` (with `reasons-canvas-fill` and, separately, `reasons-canvas-review`),
  `activated_directives` (with `DIRECTIVE_038`, and a numeric-hint-slug variant
  `038-structured-prompt-boundary` per the Edge Cases matching-logic note).
- **Pointer shapes**: (a) `.kittify/config.yaml` with no `charter:` key, `activated_*` keys
  directly on `config.yaml` (legacy/un-migrated shape); (b) `.kittify/config.yaml` with a
  `charter:` string pointer to a separate `charter.yaml` carrying the `activated_*` keys at its
  top level (this repo's own dogfood shape, INV-2's migrated shape).
- Every fixture combination is constructed via `tmp_path` and asserts
  `is_spdd_reasons_active(tmp_path) == <hand-computed disjunction over PackContext.from_config(tmp_path)>`.
  Fixtures are scoped to "`.kittify/config.yaml` exists" per the spec's own Edge Cases carve-out —
  the absent-config-file case is FR-004's separate, explicitly-excluded pin, not a parity fixture.

**Same-process two-call mutation case** (FR-002, explicit): within one test function, call
`is_spdd_reasons_active(tmp_path)` once, then mutate `.kittify/config.yaml` on disk (e.g. flip
`activated_paradigms` from `[]` to `[structured-prompt-driven-development]`) and call again in
the same process without restarting the interpreter, asserting the second call reflects the
mutation. This is the direct regression test for FR-001(e)'s cache-key fix — whichever of the two
options (composite two-file mtime key, or cache retirement) is chosen at implementation time, this
test is the only one that actually exercises "does a same-process edit invalidate the cache," and
it is written against observable behavior (the returned boolean), not against the cache's internal
dict shape, so it stays valid regardless of which of FR-001(e)'s two options implementation picks.

**How it fails when the two resolutions diverge**: every fixture assertion is a direct
`assert is_spdd_reasons_active(tmp_path) == expected_from_pack_context` — a boolean mismatch on
any single fixture combination fails that specific parametrized case with a clear "fixture X:
expected {bool}, got {bool}" message (via `pytest.mark.parametrize` ids naming the state/kind/
pointer-shape combination), not a single opaque "some assertion failed" smoke result. This is a
fixture-level boolean-mismatch assertion, matching the spec's explicit requirement that this NOT
be a smoke test.

### (c) Generated artifacts

**No generated artifact is touched by this mission.** Verified against the modules read for this
plan: `write_compiled_charter` (cited by the spec, `charter.yaml`'s writer) is not edited by any
FR in this mission; `spec-kitty charter sync` (`sync.py`'s staleness reporter) is not edited;
`compile_charter` (`compiler.py`) is not edited. This mission is a pure read-path fix (C-002/
NFR-004) — every FR changes what an existing function *reads* to decide activation, never what
any command *writes* to `charter.yaml`/`config.yaml`. No `spec-kitty` command needs to be re-run
to regenerate anything as a result of this mission's changes, on this repo's own dogfood
`.kittify/` or any other project's.

### (d) Contracts

**No doctrine schema, mission step contract, or orchestrator-api surface changes.** This mission
touches two Markdown contract *documents* (`contracts/activation.md`, `contracts/charter-context.md`
under FR-009) to correct their prose description of the source of truth — neither is a
machine-validated schema contract (no Pydantic model, no JSON schema, no `mission_step_contract`
artifact is edited). `spec_kitty_events`/`spec_kitty_tracker` are unrelated, unversioned, external
PyPI dependencies per the charter's "External Contract Packages" / Shared Package Boundary
section (`CLAUDE.md`'s "Shared Package Boundary (2026-04-25)") — this mission does not import,
vendor, or otherwise touch either package; a plan implying vendoring or a schema change here would
be severity 5 per the mission brief, and this plan makes neither.

### (e) Migration

Per NFR-004/C-002, this is a **pure read-path fix**: no `charter.yaml`/`config.yaml` schema field
is added, no writer changes its output shape, `write_compiled_charter`'s byte-preservation of the
`governance:` section is untouched, and `spec-kitty charter sync` remains a pure staleness
reporter (confirmed by reading both, not merely cited from the spec). **No migration is required**
for any on-disk charter, including this checkout's own dogfood `.kittify/`.

**Stated behavioral consequence (intended, not a side effect to hide)**: this repo's own
`is_spdd_reasons_active(repo_root)` flips from `False` to `True` the moment this mission's fix
merges to `main` — reproduced live in the spec's Summary (`activated_paradigms`/
`activated_directives`/`activated_tactics` are already non-empty on this repo's dogfood charter;
`governance.charter.selected_*` are `[]`). Consequently, subsequent mission runs against this
checkout will receive SPDD/REASONS bootstrap guidance and REASONS template blocks that are
currently silently stripped. This must be named explicitly in the PR body (NFR-004) so it reads
as the fix working as intended, not as unreviewed scope creep.

### (f) Gate set for this mission

| Gate | In scope? | Reason |
|---|---|---|
| Scoped `pytest` — `tests/charter/` (the three pinning files + new/extended parity, action-bundle, resolver test files) | **Yes** | NFR-005's explicit test-run scope; verifies FR-002/007/008/010/012/013/014 |
| Scoped `pytest` — `tests/architectural/test_charter_offering_does_not_import_activation.py` | **Yes** | C-004/NFR-003; must stay green against this mission's own diff (activation.py's rewrite is the highest-risk file for this gate) |
| Scoped `pytest` — `tests/architectural/test_no_dead_symbols.py` | **Yes** | NFR-002; every new symbol this mission's WPs introduce must resolve here |
| Real invocation, not a paraphrase: `pytest tests/charter/ tests/architectural/test_charter_offering_does_not_import_activation.py tests/architectural/test_no_dead_symbols.py -m "fast and not windows_ci and not timing"` (mirroring `fast-tests-charter`'s own filter for the `tests/charter/` portion) plus an unfiltered pass for the two named architectural files (which carry only the `architectural` marker, not `fast`) — see section (j) for why the marker split matters | **Yes** | This is the actual command, not "we'll run the tests" |
| `make lint` / full `ruff check src tests` | **Advisory only** | CI's own `[INFO] Run ruff report (advisory)` step runs with `continue-on-error: true` and is not part of the `quality-gate` blocking aggregation's hard-fail set beyond posting a PR comment; local discipline (run it, fix warnings) still applies per repo Code Style rules, but it is not a pass/fail gate for this mission |
| `ruff check src tests --select TID251` | **Relevant, enforced** | CI's `[ENFORCED] banned-API lint gate` has no `continue-on-error`; relevant if any new test/code in this mission's diff imports a banned API (e.g. `hashlib` reimplementing a charter hash, or catching `click.exceptions.*` directly) — the raw-YAML read in `activation.py`'s rewrite uses `ruamel.yaml` only, matching existing precedent, so no new banned import is expected, but the gate still runs against the diff |
| Kernel coverage ≥90% | **N/A** | Targets `src/kernel/` only (`kernel-tests` job); this mission edits zero files under `src/kernel/` |
| Mission-loader coverage ≥90% | **N/A** | `mission-loader-coverage` job's `--cov=src/specify_cli/mission_loader` targets `src/specify_cli/mission_loader/` only; this mission edits zero files there |
| `fast-tests-charter`'s own `--cov=charter --cov-fail-under=55` | **In scope (informational for this plan, enforced by CI)** | All four edited `src/` modules are under `src/charter/`; this job's path-gate (`src/charter/**`) fires on this mission's diff regardless |
| Commitlint | **Relevant, enforced** | Applies to every commit message in the PR range; this mission's commits (WP commits + the plan/doc commits) must pass `commitlint.config.cjs` |
| Markdown lint | **Relevant, enforced** | FR-009 edits `docs/context/charter.md` and two `contracts/*.md` files — all Markdown; `markdownlint-cli2` runs against changed Markdown files |
| Architecture/docs consistency (`tests/docs/test_architecture_docs_consistency.py`) | **Check at implementation time** | Not path-gated by a `src/charter/**`-only filter in the excerpt read; include in the scoped run if it collects against this mission's docs edits — deferred to tasks/implementation to confirm collection, not asserted here as definitely firing |
| Doctrine schema freshness | **N/A** | No doctrine schema (Pydantic model / JSON schema) is touched by any FR |
| Contextive glossary check (`scripts/generate_contextive_glossaries.py check`) | **Relevant, enforced** | CI's path filter includes `src/charter/**` (and `.kittify/traceability/**`); this mission edits four files under `src/charter/`, so the check fires on this PR — run it locally before pushing to catch any glossary-generation drift the diff introduces |
| TID251 | **Covered above** (folded into the enforced-lint row) | — |
| Typer JSON error surface | **N/A** | No CLI surface change (Non-Goals: "no new CLI command, flag, or user-facing surface") |
| `patch()` target validation | **Relevant if new tests patch** | FR-002/007/008/012/013's new tests are fixture-based (`tmp_path` + real `PackContext.from_config`/`is_spdd_reasons_active` calls per the Independent Test sections), not mock-patch-based by default; if implementation introduces any `unittest.mock.patch`, target-string validation applies — flagged for implementation-time awareness, not asserted as definitely needed |
| Bandit | **Yes — a real, blocking gate** | Re-verified against the live `.github/workflows/ci-quality.yml`: the `[ENFORCED] Run Bandit security scan` step (`id: bandit`) sets `continue-on-error: true`, but unlike ruff/mypy (genuinely advisory — they only populate a `has_failures` output consumed by the non-blocking `lint-feedback` PR-comment job), a later step in the same `lint` job, `[ENFORCED] Fail job if security checks failed`, explicitly reads `steps.bandit.outcome` and `exit 1`s if it is not `"success"`. `continue-on-error: true` here only lets later artifact-upload steps still run — it does not make Bandit non-blocking. Since `quality-gate`'s own `needs:` list includes `lint`, a Bandit finding fails `lint` and therefore blocks `quality-gate`/merge. Substantive conclusion unchanged: no `src/` change in this mission introduces subprocess/eval/hardcoded-secret patterns Bandit flags, so no findings are expected regardless — but that conclusion now rests on "the gate would catch it if it fired," not on "the gate is informational anyway" |
| pip-audit | **N/A for this mission's diff** | No dependency change (`uv.lock` untouched); pip-audit scans the resolved dependency set, unaffected by a read-path code change |
| `uv.lock` freshness | **N/A** | No dependency added/removed/version-changed by this mission |
| **SonarCloud** | **Excluded — does not run on pull requests** | Per the mission brief's explicit instruction |

### (g) Baseline: distinguishing pre-existing red from introduced red

`main` carries a known-red baseline (issue #3284, per this repo's CLAUDE.md baseline-red-gotcha
section) and a shared test-venv lock that can time out under concurrency (issue #3283, per the
mission brief). This mission's own scoped test set is small enough (`tests/charter/` + two named
`tests/architectural/` files) that the baseline-capture step is cheap and mandatory before the
first functional change lands:

1. **Before any FR-001..014 code change**, on the merge-base commit (this branch's current HEAD,
   which — per the mission brief — is the scaffolded, not-yet-implemented state; equivalently,
   `upstream/main` if this branch has not yet diverged with functional commits), run the exact
   scoped command from section (f):
   ```
   pytest tests/charter/ tests/architectural/test_charter_offering_does_not_import_activation.py \
     tests/architectural/test_no_dead_symbols.py -q
   ```
   Capture the **full list of failing test node-ids** (not a bare count — the charter's own
   baseline-red-gotcha guidance is explicit that a count alone is insufficient), and classify each
   against the three CLAUDE.md categories (pre-existing P0 red / CI-environment-only / stale-install
   false-red) before attributing anything to this mission.
2. **After each WP's implementation commit**, re-run the identical scoped command and diff the new
   failing node-id set against the captured baseline set. Any node-id newly red that was NOT in the
   baseline is this mission's own regression to fix before the WP is considered done. Any node-id
   that was already red in the baseline and remains red (unchanged) is out of scope per C-005 — do
   not attempt to fix it, do not re-file it.
3. The three-bucket triage in FR-010 (kept / flipped / fixture-rewritten) is expected to change
   several of these tests' RED/GREEN status *by design* mid-mission (that is the point of the
   red-first ATDD commits per WP) — the baseline diff is taken against the pre-mission state, not
   re-captured after each WP, so this expected churn is visible as "this mission's own tests
   changing," not confused with a new regression.

### (h) Campsite-clean scope (Standing Order #2)

**FR-003's `__all__` addition is folded into the same WP/commit sequence as FR-001's
`activation.py` rewrite, not opened as a separate preceding campsite-clean commit.** Reasoning:
Standing Order #2's "distinct preceding step" pattern is proportionate to god-surfaces or
pre-existing debt that must be resolved *before* the functional change can safely land on top of
it (e.g. decomposing an over-long function before extending it). `activation.py`'s missing
`__all__` is a single one-line module-level declaration on a ~200-line file this WP is already
rewriting wholesale — there is no meaningful "surface to clean before touching it" distinct from
the rewrite itself; the rewrite *is* the surface. Opening a separate no-op-behavior commit solely
to add `__all__` to a file whose body is about to be fully replaced in the very next commit would
itself be a violation of the "smallest viable diff" tension-reconciliation order (section a's
citation of `RECONCILE_CHANGE_SCOPE_TENSIONS`) — it adds a file-set-preserving but
sequence-inflating step with no independent value. The WP's own ATDD-first ordering (section i)
already gives it a red-test-then-implementation structure; FR-003 is folded into the
implementation commit as a one-line addition alongside the rewrite, not a distinct third commit.

### (i) ATDD-First (C-011, binding)

Every WP below commits its failing-first test as its own commit BEFORE any implementation commit,
each test reproducing the exact RED-on-`main`/GREEN-after-fix shape named in its FR's Independent
Test / Acceptance Scenario:

- **WP1** (FR-001/002/003/004/005): FR-002's parity test (section b) plus FR-004's absent-config
  regression test are committed RED first (both fail against the current `governance:`-reading
  body, which returns `False` for cases the corrected disjunction would flip, and the FR-004 test
  is RED against a *hypothetical* naive parity rewrite per the spec — implementation must confirm
  it is RED against the actual pre-fix body too, or note the discrepancy). Implementation (the
  full-body rewrite + `__all__`) lands as a separate, later commit that turns both GREEN.
- **WP2** (FR-006/007/008/014): FR-007, FR-008, and FR-014's three tests are committed RED first
  (each explicitly stated in the spec as "must fail on `main` before the fix"). The
  `action_doctrine_bundle.py`/`delivery_table.py` re-derivation lands after, turning all three
  GREEN.
- **WP3** (FR-011/012/013): FR-012 and FR-013's tests are committed RED first (explicitly stated
  as failing on `main` today). The `resolver.py` re-derivation lands after.
- **WP4** (FR-010, the triage WP): where FR-010 requires rewriting a test's fixture-construction
  mechanism (bucket 3, the 8 methods across two files), the rewritten fixture + updated assertion
  is itself committed RED first (against the OLD `is_spdd_reasons_active`, per FR-010's own
  explicit instruction), immediately followed by confirmation it goes GREEN once WP1 lands — this
  WP is therefore sequenced to depend on WP1 (see dependency order below), not to run standalone.
- **WP5** (FR-009, docs): no ATDD test applies — SC-005 explicitly states no red-first test should
  be manufactured for the doc updates (reviewed at PR time instead).

### (j) Marker discipline (ledger SK-144 / issue #3241)

CI selects tests by pytest MARKER, independent of directory (`fast-tests-charter` filters
`-m "fast and not windows_ci and not timing"` even though it also path-restricts to
`tests/charter`). Verified against the live marker registry (`pytest.ini`'s
`[pytest] markers =` block — `pyproject.toml` explicitly forbids a second, drift-prone markers
list per its own comment) and the real workflow files:

| Test file | Existing/planned markers | CI job(s) that collect it by marker |
|---|---|---|
| `tests/charter/test_charter_context_spdd_reasons.py` | `pytest.mark.unit` only (no `fast`) — **unchanged by this mission** | `unit-contract-residual` (`ci-quality.yml`, whole-tree `-m "(unit or contract) and not (fast or integration or ...)"`) — NOT `fast-tests-charter`, since it lacks the `fast` marker |
| `tests/charter/test_activate_resolves_no_answers_edit.py` | `pytest.mark.fast, pytest.mark.doctrine` — unchanged | `fast-tests-charter` (`ci-quality.yml`) and `doctrine-charter-tests.yml`'s path-gated fast pass |
| `tests/charter/test_answers_inert_and_org_union.py` | `pytest.mark.unit, pytest.mark.fast, pytest.mark.doctrine` — unchanged | Same as above |
| `tests/charter/test_spdd_reasons_activation_parity.py` (NEW, FR-002) | `pytest.mark.fast, pytest.mark.doctrine` | `fast-tests-charter` + `doctrine-charter-tests.yml` — chosen to match the sibling pinning files' convention so the mandatory parity test is not CI-invisible in the `fast-tests-charter` blocking job |
| New/extended action-doctrine-bundle test (FR-007/008/014) | `pytest.mark.fast, pytest.mark.doctrine` | Same reasoning as above |
| New/extended resolver test (FR-012/013) | `pytest.mark.fast, pytest.mark.doctrine` | Same reasoning as above |
| `tests/architectural/test_charter_offering_does_not_import_activation.py` | `pytest.mark.architectural` (module-level `pytestmark`, confirmed by reading the file) — unchanged | The dedicated architectural-gate CI pole (`-m "... architectural ..."`, `ci-quality.yml`'s `arch_shard_*`/architectural aggregation) |
| `tests/architectural/test_no_dead_symbols.py` | `pytest.mark.architectural` — unchanged | Same architectural-gate pole |

No new marker name is invented; every marker cited above is a real, registered entry in
`pytest.ini`'s `markers =` block, verified by reading it directly for this plan.

### (k) Tracer files

`tracer-tooling-friction.md`, `tracer-approach.md`, and `tracer-design-decisions.md` under this
mission's `kitty-specs/spdd-reasons-activation-split-brain-01M1K6VN/` directory are seeded by the
orchestrator at the appropriate lifecycle point (per Standing Order #3), not authored by this plan
phase. This plan does not create them.

### (l) Write scopes and overlap with concurrently open PRs

This mission's write scope is exactly: `src/charter/offering/spdd_reasons/activation.py`,
`src/charter/activation/action_doctrine_bundle.py`,
`src/charter/activation/context_renderers/delivery_table.py`, `src/charter/activation/resolver.py`,
`tests/charter/*` (three existing pinning files + new/extended parity/action-bundle/resolver test
files), `docs/context/charter.md`, and the two `contracts/*.md` files under
`kitty-specs/spdd-reasons-doctrine-pack-01KQC4AX/contracts/`.

Verified via `gh pr view <n> --json files` for this plan (not trusted from the mission brief's
summary verbatim):

- **PR #3842** (`op/3839-charter-list-json`, OPEN, targets `main`). Real file list confirmed:
  `src/charter/activation/evidence/orchestrator.py`,
  `src/specify_cli/cli/commands/charter/{list_cmd,resynthesize,status,synthesize}.py`,
  `src/specify_cli/core/agent_config.py`, `src/specify_cli/git/protection_policy.py`, plus its own
  spec/kitty-ops/test files. **No file-level overlap** with this mission's edit set — but
  `evidence/orchestrator.py` is inside the same `src/charter/activation/` package subtree this
  mission edits (`action_doctrine_bundle.py`, `resolver.py`, `context_renderers/delivery_table.py`
  all live there too). **Sequencing implication**: no functional merge-conflict risk (disjoint
  files), but if #3842 merges before this mission's PR, any line-number citation this plan or its
  eventual PR body makes against `charter.activation.*` files should already be symbol-based
  rather than line-based for exactly this reason — which every citation in this plan already is
  (e.g. "`resolver.py`'s `_resolve_directive_base`" rather than a bare line number pinned in prose,
  with line numbers given only as re-derived-at-write-time pointers, not load-bearing identifiers).
- **PR #3845** (`feat/dispatch-dry-run-route-only-3840`, OPEN). Real file list confirmed:
  `src/specify_cli/cli/commands/dispatch.py`, `src/specify_cli/invocation/{empty_charter,executor,router}.py`,
  plus its own kitty-specs/test files. **No subtree overlap** with `src/charter/` at all — noted,
  no sequencing action needed.
- **Unpushed mission on `feat/design-phase-orchestrator-api-3837`** (per the mission brief;
  not independently re-verified via `gh` since it is unpushed and has no PR number to query)
  touching `orchestrator_api/commands.py`, `runtime/next/*`, `cli/commands/next_cmd.py` — no
  subtree overlap with this mission's `src/charter/` edit set. Noted, no sequencing action needed.

### (m) Silent success — per-changed-path design commitment (NFR-001)

Restated as a design commitment for every new/changed code path this mission introduces, not
merely a spec requirement to satisfy later:

| Code path | On success | When it cannot determine activation |
|---|---|---|
| `activation.py`'s rewritten `is_spdd_reasons_active`, absent `.kittify/config.yaml` | — | Returns the explicitly-pinned safe default `False` (FR-004), with a code comment stating this is a deliberate carve-out from full parity, not an oversight |
| `activation.py`'s rewritten body, malformed `config.yaml` YAML or a dangling/unreadable `charter:` pointer | — | **Raises** (FR-005), matching `PackContext.from_config`'s `CharterPackConfigError`/YAML-loader-exception behavior — never a silent `False`/`True` |
| `action_doctrine_bundle.py`'s re-derived `project_directives`/`selected_tactics`/`selected_paradigms` | Returns the `activated_*`-derived set (three-state preserved) unioned with org-required ids | An explicitly-empty `activated_directives: []` must exclude everything (FR-014) — never silently collapse to "no filter" via bare truthiness; this is itself the silent-success defect class being closed, not a new one being introduced |
| `delivery_table.py`'s `_classify_artifact_urns` exclusion guard, `start_urns` construction, and `action_doctrine_bundle.py`'s `roots` construction (all three named in section (a) item 3) | Filters/seeds against the three-state-aware set; `None` is converted to a concrete value once at assignment in `action_doctrine_bundle.py`, before any of the three sites iterates it | Same three-state distinction as above — `None` (all built-ins) and `frozenset()` (explicit empty) must never be conflated, at any of the three consumption sites, not only the exclusion guard |
| `resolver.py`'s `_resolve_directive_base`/`resolve_project_governance` | Returns `activated_*`-derived base, unioned with any non-empty `selected_*` | `activated_directives is None` (key absent, unconfigured project) already falls through to the existing catalog-fallback diagnostic (preserved verbatim, not touched by this mission) — this is the pre-existing, non-silent third branch, unchanged |

Every row above either raises or returns an explicitly-named, tested default — no row this mission
adds or changes returns an unexplained silent result for an error/undetermined condition, mirroring
NFR-001's binding statement.

---

## Phasing into Work Packages

Natural WP boundaries implied by the FR table (tasks.md, a later phase, will formalize these into
numbered WPs with dependency metadata — this section states the boundaries and ordering the tasks
phase should follow, not the WPs themselves):

1. **WP1 — `activation.py` rewrite** (FR-001, FR-002, FR-003, FR-004, FR-005). Self-contained: no
   dependency on any other WP. Delivers the parity test (the mission's load-bearing artifact) and
   the corrected single-caller function. **Should land first** — WP4 (the pinning-test triage)
   depends on it for its bucket-3 fixture rewrites to go GREEN.
2. **WP2 — `action_doctrine_bundle.py` + `delivery_table.py`** (FR-006, FR-007, FR-008, FR-014).
   Independent of WP1 (different files, different `PackContext` consumption path — already
   parameterized, no shared code with `activation.py`'s rewrite). Can run in parallel with WP1.
   **Scope also includes `tests/charter/test_action_bundle_delivery.py`** (PLAN-GOV-001): this
   existing file's four direct `_classify_artifact_urns(..., set())` call sites must be updated
   to pass `None` instead, preserving their original "no filter" intent under the new
   `is not None` guard (see section (a) item 3) — distinct from FR-014's own new explicit-empty
   test, and from FR-010's separate three-pinning-file triage in WP4 below.
3. **WP3 — `resolver.py`** (FR-011, FR-012, FR-013). Independent of WP1 and WP2 (different file,
   different consumers). Can run in parallel with both.
4. **WP4 — Triage the three pinning test files** (FR-010). **Depends on WP1**: the bucket-3
   fixture rewrites (8 test methods across two files, per FR-010's precise enumeration) must write
   `.kittify/config.yaml`'s `activated_*` keys and assert against the *rewritten*
   `is_spdd_reasons_active`'s new behavior — committing this WP's red-first tests before WP1's
   implementation commit lands is exactly the ATDD sequencing FR-010 itself specifies (red against
   the OLD function, green after FR-001). This WP is therefore sequenced after WP1's
   implementation commit, not merely after WP1 is "planned."
5. **WP5 — Docs** (FR-009: `contracts/activation.md`, `contracts/charter-context.md`,
   `docs/context/charter.md`'s three glossary entries + new `activated_<kind>` entry). No test
   dependency (SC-005 explicitly exempts it from ATDD); can run any time after WP1–WP3's design is
   settled enough that the doc text accurately describes the final behavior — practically, last,
   so the docs describe the merged shape rather than an interim one.

**Dependency order**: WP1 and WP2 and WP3 are mutually independent and may proceed in parallel;
WP4 depends on WP1's implementation commit; WP5 is sequenced last (describes the final state).

**PR shape**: this mission ships as **one PR**, spec-kitty's default shape. The full diff across
all five WPs is bounded — four `src/` files (one full-body rewrite, three targeted internal
changes to already-parameterized functions), three existing test files with scoped triage edits,
2–3 new/extended test files, and three Markdown doc files — a size a single reviewer can hold in
one sitting given each WP's change is narrowly scoped to a named function/section. This plan does
not find cause to recommend a per-WP-PR split; if the orchestrator/operator's own review-time
judgment at implementation disagrees (e.g. the WP4 triage diff turns out larger than anticipated
once the actual fixture rewrites are written), that split decision belongs to them at that point,
not to this plan.
