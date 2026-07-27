# Phase 0 — Research

**Mission**: `charter-ux-and-org-pack-vocabulary-01KSAF14`
**Date**: 2026-05-23
**Companion document**: `research/mission-brief.md` (Researcher Robbie's code-grounded brief)

This file consolidates the *decisions* drawn from the brief. The brief is the evidence; this is the resolution.

---

## R-1. Field name: `enhances` vs `augments`

**Decision**: `enhances`.

**Rationale**: Issue #1291 — the canonical inbound source of this requirement — uses `enhances` throughout its acceptance criteria and example YAML. The Human-in-Charge said "augments" verbally at handoff, but the issue is the immutable contract; aligning the field name with the issue avoids glossary drift. DIR-032 (conceptual alignment) is satisfied by adding a glossary entry that names `enhances` as the canonical term and `augments` as a colloquial synonym.

**Alternatives considered**: `augments` (HiC's verbal phrasing — rejected for divergence from issue), `extends` (overloaded by base/extension terminology — rejected).

## R-2. `Relation` enum policy

**Decision**: Add two new values: `ENHANCES = "enhances"` and `OVERRIDES = "overrides"`. **Retain** the existing `REPLACES = "replaces"` value as-is; do not rename.

**Rationale**:
- `REPLACES` already has DRG fragments in the wild (`tests/integration/test_*` fixtures, possibly committed `.kittify/doctrine/graph.yaml` files in downstream projects). Renaming forces a coordinated migration we do not need.
- Auto-emit from declarative fields uses `ENHANCES` / `OVERRIDES` exclusively; pack authors never write `REPLACES` by hand for the new fields.
- `OVERRIDES` and `REPLACES` are semantically near-identical but represent different intents: `OVERRIDES` is "declared replace via schema field"; `REPLACES` is "graph-level edge declaring replacement". Both are valid; collapsing them is a future refactor outside this mission's scope.

**Alternatives considered**: Rename `REPLACES → OVERRIDES` (rejected — breaks existing DRG payloads); alias `OVERRIDES → REPLACES` at the StrEnum level (rejected — Pydantic StrEnum aliasing is brittle and obscures intent in dumps).

## R-3. Vocabulary cutover style (`shipped → built-in`)

**Decision**: Straight cutover with CHANGELOG breaking-change entry. No deprecation window.

**Rationale**:
- Pre-3.2.0 stable release; no public consumer guarantees against the `"shipped"` label.
- Filesystem directories already use `built-in/` — the codebase is asymmetric, not internally consistent. Deprecation window would prolong asymmetry.
- The architectural regression test FR-016 enforces the cutover at the public CLI surface; a dual-emit period would require either dropping that test or making it look the other way, both of which weaken the contract.
- CHANGELOG entry is required by DIR-009 either way.

**Alternatives considered**: Dual-emit for one minor version (rejected — maintenance overhead without consumer benefit); silent rename without CHANGELOG (rejected — breaks DIR-009).

## R-4. Preflight invocation scope

**Decision**: Introduce a manual `spec-kitty charter preflight` command **and** opt-in hooks from the following high-blast-radius entry points: `spec-kitty next`, `spec-kitty implement`, dashboard launch (`dashboard serve`/`dashboard start`).

**Rationale**:
- Running preflight on every CLI invocation produces noise and breaks NFR-001 (<300 ms warm).
- The launch-blocker scenarios from #1100 all involve agents reaching for governed context — `next`, `implement`, and the dashboard cover those paths.
- Other commands (`status`, `lint` themselves) already report freshness via FR-005; they don't need to invoke preflight, only consume its result.

**Alternatives considered**: Hook into every command (rejected for NFR-001); only manual command (rejected because users won't remember to run it).

## R-5. Bulk-edit gate scope for FR-015

**Decision**: Standard `occurrence_map.yaml` with all 8 categories populated. Each Python identifier rename is a `code_symbols` row; each test-fixture YAML change is `tests_fixtures`; each docstring/comment touch is `code_symbols` (action: `update-in-place`); each public JSON key change is `serialized_keys` (action: `rename-and-changelog`).

**Rationale**: The `spec-kitty-bulk-edit-classification` skill is binding when `change_mode: bulk_edit`. Skipping or partial categorisation would block `implement`.

**Alternatives considered**: Per-wave partial occurrence map (rejected — bulk-edit gate requires complete classification before first WP starts).

## R-6. Mutually exclusive `overrides` / `enhances`

**Decision**: Cross-field Pydantic validator on each affected model. Error message: `"overrides and enhances are mutually exclusive on <kind> <id>"`. Pack validator (`spec-kitty doctrine pack validate`) surfaces the error with file context.

**Rationale**: Allowing both fields is semantically incoherent — an artifact cannot simultaneously replace and augment a built-in. Catching it at model construction time prevents downstream DRG corruption.

**Alternatives considered**: Soft-warning instead of error (rejected — the merge logic would have to pick a winner, which is exactly the ambiguity the fields were introduced to remove); silent precedence (`overrides` wins) (rejected — magic).

## R-7. Unknown-target validation for `overrides` / `enhances`

**Decision**: Hard error from `spec-kitty doctrine pack validate` when `enhances: <id>` or `overrides: <id>` references an ID not present in `src/doctrine/<kind>/built-in/`. Error category: `unknown_target`. Error message: `"<kind> <id> declares <field>: <target_id>, but no built-in <kind> with that id exists"`.

**Rationale**: #1291 acceptance criterion 3 is explicit ("emits an error, not an advisory, when `enhances` references an unknown ID"). Catching it at pack-validate time prevents the org pack from shipping a dangling reference.

**Alternatives considered**: Advisory only (rejected — fails the acceptance criterion); cross-pack target allowed (rejected — out of scope per spec).

## R-8. Existing fixture compatibility

**Decision**: Add the new fields as `Optional[str] = None` on every affected Pydantic model. Pre-existing fixture YAMLs without `overrides`/`enhances` continue to load with the field set to `None`. NFR-004 (zero fixture failures) is satisfied by construction.

**Rationale**: `extra="forbid"` is preserved; only the known field set widens.

## R-9. Schema vocabulary in advisory text

**Decision**: When the same-ID collision happens but neither field is declared, the advisory text changes from `"artifact id 'X' overrides a shipped tactic"` to `"artifact id 'X' will field-merge into the built-in tactic — declare 'enhances: X' to suppress this advisory, or 'overrides: X' to declare a full replacement"`.

**Rationale**: ADR `2026-05-16-1-doctrine-layer-merge-semantics.md` ratified field-merge as the actual behaviour. The old advisory wording ("overrides") is factually wrong (no replacement happens unless ALL fields are present). Reworded advisory matches the merge ADR and uses the new vocabulary.

---

End of Phase 0 research.
