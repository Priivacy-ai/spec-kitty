---
work_package_id: WP09
title: Cross-Mission Summary Reducer + CLI
dependencies:
- WP02
- WP03
requirement_refs:
- FR-025
- FR-026
- FR-027
- NFR-003
- NFR-004
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T042
- T043
- T044
- T045
- T046
- T047
agent: "claude:sonnet:implementer:implementer"
shell_pid: "20232"
history:
- at: '2026-04-27T08:18:00Z'
  actor: claude
  action: created
authoritative_surface: src/specify_cli/retrospective/
execution_mode: code_change
mission_slug: mission-retrospective-learning-loop-01KQ6YEG
owned_files:
- src/specify_cli/retrospective/summary.py
- src/specify_cli/retrospective/cli.py
- tests/retrospective/test_summary_tolerance.py
- tests/retrospective/test_summary_cli.py
priority: P1
status: planned
tags: []
---

# WP09 — Cross-Mission Summary Reducer + CLI

## Objective

Streaming reducer over a project's retrospective corpus + the operator-facing `spec-kitty retrospect summary` CLI command. Tolerant to malformed / missing / legacy / in-flight / terminus_no_retrospective records. Emits both Rich and JSON; Rich and JSON MUST be informationally equivalent.

## Spec coverage

- **FR-025** CLI surface emits Rich + JSON.
- **FR-026** minimum pattern catalog (not-helpful, missing terms, missing edges, over/under-inclusion, acceptance rates, skip count, no-retro count).
- **FR-027** rich/brief/skipped/missing/malformed tolerance.
- **NFR-003** ≤200-mission corpus < 5 s on a developer laptop.
- **NFR-004** 100% tolerance: malformed records skipped with a structured reason, never abort.

## Context

- Source-of-truth contracts are in [`../contracts/cli_surfaces.md`](../contracts/cli_surfaces.md) (CLI), [`../data-model.md`](../data-model.md) (`SummarySnapshot`, `MalformedSummaryEntry`), and [`../research.md`](../research.md) R-008 (reduction strategy).
- Streaming, single-thread reducer is sufficient for the 200-mission scale.

## Subtasks

### T042 — `summary.py` reducer + `SummarySnapshot` model

In `src/specify_cli/retrospective/summary.py`:

```python
def build_summary(
    *,
    project_path: Path,
    since: datetime | None = None,
    limit_top_n: int = 20,
) -> SummarySnapshot: ...
```

The reducer:

1. Globs `project_path/.kittify/missions/*/retrospective.yaml` (one stat call per match).
2. Per record, attempts schema-validating load via WP02's reader.
3. Builds the `SummarySnapshot` per `data-model.md`.
4. For top-N counts, sort descending by count, ties broken by URN/key string.

`SummarySnapshot` and `MalformedSummaryEntry` are defined in `summary.py` (or imported from a shared location if `data-model.md` shapes are placed elsewhere).

### T043 — Streaming corpus reader

The reader avoids loading the entire corpus into memory at once. For a 200-mission corpus this is just defensive — but it makes future scaling easier.

For each mission directory found, also locate the corresponding `kitty-specs/<slug>/status.events.jsonl` (resolve the slug via the mission's `meta.json`). Read proposal-lifecycle events (`retrospective.proposal.{generated,applied,rejected}`) to compute proposal acceptance metrics.

### T044 — Tolerance handling

Five categories of input must be handled without crashing:

- **rich** — full record with findings and proposals.
- **brief** — completed record with empty findings (status=completed, all lists empty).
- **skipped** — status=skipped with skip_reason.
- **missing** — no `retrospective.yaml` for this mission. Distinguish:
  - `legacy` (mission `created_at` is before this tranche's release tag — for now, document this heuristic; the actual timestamp can be filled in at landing).
  - `in_flight` (mission has not reached terminus yet — detect via mission's status snapshot).
  - `terminus_no_retrospective` (mission reached terminus but no retrospective event seen).
- **malformed** — file exists but fails YAML parse or schema. Build a `MalformedSummaryEntry(mission_id_or_None, path, reason)` and continue.

The malformed list is always reported in the snapshot. The default Rich rendering shows malformed counts; `--include-malformed` shows detail.

### T045 — `cli.py` `retrospect summary` subcommand wiring

In `src/specify_cli/retrospective/cli.py`:

```python
app = typer.Typer(name="retrospect", help="Retrospective operator surface")

@app.command("summary")
def summary_cmd(
    project: Annotated[Path | None, typer.Option("--project")] = None,
    json_only: Annotated[bool, typer.Option("--json")] = False,
    json_out: Annotated[Path | None, typer.Option("--json-out")] = None,
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 20,
    since: Annotated[str | None, typer.Option("--since")] = None,
    include_malformed: Annotated[bool, typer.Option("--include-malformed")] = False,
) -> None: ...
```

Register the new top-level `retrospect` typer app under the spec-kitty CLI entry point. This requires a one-line edit in the CLI registry — note this insertion if it lands outside `owned_files` and confirm with reviewer.

### T046 — Rich + JSON renderers

Rich rendering: a clean Rich layout with sections (Counts, Top Not-Helpful, Top Missing Terms, Top Missing Edges, Top Over/Under-Inclusion, Proposal Acceptance, Top Skip Reasons, Malformed). Show the JSON-equivalent fields.

JSON envelope per contract:

```json
{
  "schema_version": "1",
  "command": "retrospect.summary",
  "generated_at": "2026-04-27T11:35:00+00:00",
  "result": { ... }  // SummarySnapshot.model_dump()
}
```

Informational equivalence test: total counts in Rich equal counts in JSON; top-N entries match.

### T047 — Tests: corpus tolerance + 200-mission perf bound

In `tests/retrospective/test_summary_tolerance.py` and `tests/retrospective/test_summary_cli.py`:

- Fixture corpus mixing rich, brief, skipped, missing (legacy), missing (in_flight), missing (terminus_no_retrospective), and malformed → assert each appears in the right count and `malformed[]` carries structured reasons.
- 200-mission fixture (auto-generated in a fixture builder): summary completes in < 5 s.
- `--since 2026-01-01` filters out earlier missions.
- `--limit 5` truncates top-N sections.
- `--json` output passes a schema check.
- Empty project (no missions) → exit 0 (or 1 per contract — confirm against `cli_surfaces.md`; that path returns exit 1 if neither `.kittify/` nor `kitty-specs/` exists).

For the perf test, generate the fixture once per test session (use `pytest` fixtures); allow generous slack to avoid CI flakiness.

## Definition of Done

- [ ] Reducer handles all five tolerance categories.
- [ ] Top-N sections in `SummarySnapshot` exist and are sorted deterministically.
- [ ] Rich and JSON outputs are informationally equivalent.
- [ ] 200-mission perf bound met.
- [ ] No abort on any malformed record.
- [ ] `mypy --strict` passes.
- [ ] Coverage ≥ 90%.
- [ ] No changes outside `owned_files` except the one-line CLI registry edit.

## Risks

- **CLI entry-point registration**: may live in a place outside `owned_files`. Document the single-line edit and run existing CLI tests.
- **Top-N tie-breaking**: deterministic order matters for tests; use stable sort with a secondary key.

## Reviewer guidance

- Run `spec-kitty retrospect summary --help` and verify the help body matches the contract.
- Walk all five tolerance categories with their fixture rows.
- Confirm Rich/JSON equivalence via a comparison test.

## Implementation command

```bash
spec-kitty agent action implement WP09 --agent <name>
```

## Activity Log

- 2026-04-27T10:37:08Z – claude:sonnet:implementer:implementer – shell_pid=20232 – Started implementation via action command
- 2026-04-27T10:55:37Z – claude:sonnet:implementer:implementer – shell_pid=20232 – Ready for review: cross-mission summary reducer + retrospect summary CLI; 36 tests / mypy strict / 200-mission perf ~1.5s; 3-line registry edit in cli/commands/__init__.py
