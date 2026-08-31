# Research: Glossary DRG Surfaces and Charter Lint

**Mission**: glossary-drg-surfaces-and-charter-lint-01KPTY5Y  
**Researched**: 2026-04-22 via codebase inspection

---

## 1. ProfileInvocationExecutor hook point (WP5.3)

**Decision**: WP5.3 does not touch `ProfileInvocationExecutor` directly (that's WP5.2's job). The inline observation surface lives in the CLI commands that call `invoke()`.

**How it works**:
- `ProfileInvocationExecutor.invoke()` is synchronous; it does not return conflict events.
- The chokepoint (WP5.2) emits events to `.kittify/events/glossary/{mission_id}.events.jsonl` (or invocation-scoped variant) during the invocation window.
- WP5.3 reads conflict events from that log after `invoke()` returns, filters for `severity == "high"`, and appends an `InlineNotice` block to the CLI output before the terminal prompt returns.
- Entry points: `src/specify_cli/cli/commands/do_cmd.py` and `src/specify_cli/cli/commands/advise.py`.

**Alternatives considered**: Modifying `InvocationPayload` to carry conflict events (rejected: would make WP5.3 tightly coupled to WP5.2's internal types; cleaner to read the event log after the fact).

**Source files**: `src/specify_cli/invocation/executor.py`, `src/specify_cli/cli/commands/do_cmd.py`, `src/specify_cli/cli/commands/advise.py`

---

## 2. Glossary event schema (WP5.3, WP5.4)

**Decision**: The relevant event type is `SemanticCheckEvaluated`. It carries a `conflict` sub-object with severity. The event log is per-mission at `.kittify/events/glossary/{mission_id}.events.jsonl` plus a CLI fallback at `.kittify/events/glossary/_cli.events.jsonl`.

**Shape** (from `src/specify_cli/glossary/events.py`):
```python
SemanticCheckEvaluated:
  mission_id: str
  term: str
  scope: str
  conflicts: list[ConflictRecord]  # each has severity, conflict_type, senses involved
  checked_at: datetime
```

**High-severity filter**: `conflict.severity in {"high", "critical"}` (exact values depend on `src/specify_cli/glossary/conflict.py`).

**Source files**: `src/specify_cli/glossary/events.py`, `src/specify_cli/glossary/conflict.py`

---

## 3. Dashboard tile extension pattern (WP5.4, WP5.6 dashboard)

**Decision**: New tiles follow the same pattern as the existing `handle_charter()` endpoint in `APIHandler`:
1. Add a `TypedDict` response shape to `src/specify_cli/dashboard/api_types.py`
2. Add a handler method to a new `GlossaryHandler` class (or extend `APIHandler`)
3. Register the route in `src/specify_cli/dashboard/handlers/router.py`
4. Add a JS fetch + DOM section in `src/specify_cli/dashboard/static/` or `templates/`

**Existing route count**: 15 GET routes, 2 POST routes. Both new tiles (`/api/glossary-health` and `/api/charter-lint`) fit the existing pattern cleanly.

**Source files**: `src/specify_cli/dashboard/handlers/router.py`, `src/specify_cli/dashboard/handlers/api.py`, `src/specify_cli/dashboard/api_types.py`

---

## 4. `ensure_charter_bundle_fresh` hook point (WP5.5)

**Decision**: `ensure_charter_bundle_fresh` is imported from `charter.sync` (a sibling package). The function signature is called at the top of `charter compile` and other charter commands. WP5.5 hooks entity page generation into this function by:
- Adding a post-bundle hook in `charter.sync.ensure_charter_bundle_fresh()` — OR
- Calling `regenerate_entity_pages(repo_root)` immediately after `ensure_charter_bundle_fresh()` returns in every code path that calls it.

The second option is safer (no modification to `charter` package internals): add a `generate_glossary_entity_pages(repo_root)` call in `src/specify_cli/cli/commands/charter.py` at the call sites of `ensure_charter_bundle_fresh`.

**Output path**: `.kittify/charter/compiled/glossary/<term-id>.md` (gitignored, build artifact).

**Source files**: `src/specify_cli/cli/commands/charter.py` (lines 83+), `charter.sync` (external package)

---

## 5. Merged DRG access pattern (WP5.5, WP5.6)

**Decision**: `DRGGraph` from `doctrine.drg.models` is the graph model. In `charter.py`, the merged DRG is loaded via `_load_merged_drg(repo_root, request)` (private, charter-internal). For WP5.5 and WP5.6, we read the persisted merged DRG from `.kittify/doctrine/` (the output of `charter compile`).

**Query pattern for reverse-walk** (WP5.5): Iterate DRG edges, filter for edge type `vocabulary`, group by `target_node_id` (glossary term URN), collect all `source_node_id` values (WPs, ADRs, steps, etc.).

**Query pattern for orphan detection** (WP5.6): For each node by type, count incoming edges of expected types; nodes with zero incoming edges are orphans.

**Source files**: `src/specify_cli/cli/commands/charter.py` (lines 955–1109), `doctrine.drg.models` (external package)

---

## 6. Existing `glossary` CLI surface (WP5.5)

**Decision**: `spec-kitty glossary show <term>` is a new subcommand added to the existing `app` in `src/specify_cli/cli/commands/glossary.py`. It calls the entity page renderer to produce the page, then renders it to the terminal via Rich's Markdown renderer.

**Existing subcommands**: `list`, `conflicts`, `resolve`  
**New subcommand**: `show <term-id-or-name>`

**Source files**: `src/specify_cli/cli/commands/glossary.py`

---

## 7. Charter lint placement (WP5.6)

**Decision**: `spec-kitty charter lint` lives as a subcommand of the existing `charter` Typer app in `src/specify_cli/cli/commands/charter.py`. The lint engine itself lives in a new module `src/specify_cli/charter_lint/` to keep it testable in isolation.

The `charter_lint` module has no dependency on any CLI framework; it takes a `repo_root: Path` and returns a `DecayReport`. The CLI command in `charter.py` invokes it and handles output formatting.

**Source files**: `src/specify_cli/cli/commands/charter.py` (new `lint` subcommand), new `src/specify_cli/charter_lint/` package

---

## 8. Lint report persistence (WP5.6 → WP5.6 dashboard)

**Decision**: After every `spec-kitty charter lint` run, the report is written to `.kittify/lint-report.json` as a side effect. The dashboard `/api/charter-lint` handler reads this file to power the decay watch tile. If the file does not exist, the tile renders a "no data — run `spec-kitty charter lint`" prompt.

**Rationale**: Avoids running lint on every dashboard refresh (lint is ≤5s but still non-trivial). Operator controls when lint runs.

---

## 9. Fixture strategy for tests

**Decision**: Tests for WP5.6 use a purpose-built in-memory DRG fixture with manufactured decay in each category (one orphan WP, one contradicting ADR pair, one stale synthesized artifact, one broken ref). The fixture is defined in `tests/specify_cli/charter_lint/fixtures.py` as a factory function, not YAML, so it can be parameterized.

Tests for WP5.5 use a minimal DRG fixture with 3 terms and pre-populated `vocabulary` edges to 2 WPs each.
