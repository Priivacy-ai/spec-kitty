---
work_package_id: WP03
title: spec-kitty docs query CLI
dependencies:
- WP01
requirement_refs:
- FR-002
- FR-003
- FR-004
- NFR-002
planning_base_branch: feat/agent-knowledge-canonical-homes
merge_target_branch: feat/agent-knowledge-canonical-homes
branch_strategy: Planning artifacts for this mission were generated on feat/agent-knowledge-canonical-homes. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/agent-knowledge-canonical-homes unless the human explicitly redirects the landing branch.
subtasks:
- T011
- T012
- T013
- T014
- T015
history:
- at: '2026-07-22T14:56:33Z'
  actor: claude
  event: created
agent_profile: python-pedro
authoritative_surface: src/specify_cli/cli/commands/
create_intent:
- src/specify_cli/cli/commands/docs.py
- tests/docs/test_docs_query_cli.py
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/cli/commands/docs.py
- tests/docs/test_docs_query_cli.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Adopt its directives/tactics; state which you applied in your handoff note.

## Objective

Add `spec-kitty docs query "<term>" [--json] [--divio-type <t>] [--section <anchor>]`, a new `docs`
Typer sub-app (`src/specify_cli/cli/commands/docs.py`) modeled EXACTLY on the glossary query surface.
It loads the WP01 index once and filters in-memory (NFR-002), returning matching pages as stable JSON.

Read `contracts/cli-contract.md` (authoritative behavior) and `data-model.md` (Module-layering table +
the `DocsIndexStore` query model) first. Mirror `src/specify_cli/cli/commands/glossary.py` for the
CLI/JSON shape.

**Import rule (load-bearing):** import `DocsQueryEntry`, `Anchor`, `DocsIndexStore` from the packaged
`specify_cli.docs.index_model` (`src→src`). **NEVER import `scripts.*`** — `scripts/` is not in the
wheel, so the installed CLI would `ModuleNotFoundError`. There is NO "local mirror" of the schema.

## Branch Strategy

Planning base + merge target: **`feat/agent-knowledge-canonical-homes`** (coord topology). Worktree per
lane via `spec-kitty implement WP03`. **Depends on WP01** — implement only after WP01 is `approved`.

## Subtasks

### T011 — `DocsIndexStore`

- `DocsIndexStore` lives in the packaged `specify_cli.docs.index_model` (WP01 owns it). In `docs.py`,
  import it and `DocsQueryEntry`/`Anchor` from there — do NOT redefine or mirror the schema (single owner,
  no drift). If `DocsIndexStore.query` is not already provided by WP01, that is a WP01 gap — flag it, do
  not fork a copy here.
- `query(term, *, divio_type=None, section=None) -> list[Entry]`: case-insensitive substring over
  `title` + each anchor `text`/`slug` + `abstract`; optional `divio_type` equality filter; optional
  `section` = has-anchor-with-that-slug filter. Preserve path-sorted order. For each match, return only
  the anchors that matched the term/`--section` (FR-003).
- No per-query filesystem walk (NFR-002) — filter the in-memory list.

### T012 — `docs query` command

- `app = typer.Typer(...)`; `@app.command("query")` with `term: str` positional + `--json` flag +
  `--divio-type` + `--section` options.
- `--json`: build `list[dict]` and `print(json.dumps(output, indent=2))` (use `print`, NOT Rich
  `console`, to avoid markup). Empty result → `print("[]")` and `return` (exit 0).
- Human path: a Rich `Table` (path / title / divio_type / matching anchors).
- `--divio-type` validates against `DivioType`; an invalid value → Typer `BadParameter` (exit 2).

### T013 — Register the sub-app

- In `src/specify_cli/cli/commands/__init__.py`, next to the `glossary` registration (~line 208), add
  `app.add_typer(docs_module.app, name="docs", help="Common Docs retrieval commands")` with the matching
  import. This is a one-line out-of-map edit — record the rationale in the handoff note (the file is
  WP03's `authoritative_surface` neighbor; no other WP owns it).

### T014 — Error handling

- Missing `docs/` tree or missing index file → a clear message on stderr + non-zero exit, NO Python
  traceback (catch + `typer.Exit(1)` with an actionable message: run the generator).
- Invalid `--divio-type` → usage error (exit 2) as above.

### T015 — Tests (each case pins a distinct contract row — no fakeable fixtures)

- `tests/docs/test_docs_query_cli.py` via Typer's `CliRunner` against a **module-local** fixture index
  (do not share a `conftest.py` fixture with WP01/WP02):
  - match → correct JSON element shape (path/title/matching anchors/abstract/divio_type), exit 0;
  - **FR-003 discriminating case (renata, BLOCKING)**: a fixture page with **≥2 anchors** where the term
    matches exactly **one** → assert the result's `anchors` contains ONLY that one (a single-anchor
    fixture would pass a wrong "return all anchors" impl — do not use one). Add the "matched on
    title/abstract only → `anchors` empty" case.
  - no match → `[]`, exit 0; **empty/whitespace TERM → usage error exit 2**;
  - `--divio-type` filter; `--section` filter;
  - invalid `--divio-type` → exit 2 **and no Python traceback**;
  - missing index/tree → non-zero exit, actionable message, **no traceback** (distinct from no-match);
  - **contract row 7 (renata, BLOCKING)**: default human path (no `--json`) → a table renders and piped
    output contains **no Rich markup/control tokens**;
  - **NFR-002 structural guard (renata)**: assert the query path performs **no filesystem walk after
    `DocsIndexStore.load()`** (e.g. spy/monkeypatch `rglob`/`open` and assert zero calls during
    `query()`), NOT only a wall-clock `<1s` smoke. Keep a live-tree smoke as a soft ceiling.
- Run `PWHEADLESS=1 uv run pytest tests/docs/test_docs_query_cli.py -q` — green.

## Definition of Done

- [ ] `spec-kitty docs query` behaves per every row of `contracts/cli-contract.md`.
- [ ] JSON via `print(json.dumps)`, empty → `[]` exit 0; filters + error paths correct.
- [ ] Sub-app registered next to `glossary`; rationale for the `__init__.py` edit recorded.
- [ ] `uv run ruff check` + `uv run mypy` clean on touched files; complexity ≤15.
- [ ] Tests green (foreground, `uv run`); live-tree query `<1s`.

## Reviewer guidance

Verify JSON uses `print` not Rich (pipe the output — no markup leak); empty→`[]`/exit 0; no-tree error
has no traceback; `--divio-type` validated against `DivioType`; the `__init__.py` registration is the
only out-of-map edit and is one line. Confirm no per-query filesystem walk (index loaded once).

## Risks

- Rich `console.print_json` leaking markup into piped output → use `print(json.dumps)`.
- Duplicating WP01's dataclasses instead of importing → schema drift; prefer import.
- Swallowing the missing-index case into an empty `[]` (hiding a real error) → distinguish "no match"
  (→`[]` exit 0) from "no index" (→error exit).
