---
work_package_id: WP06
title: Glossary Show CLI, Backlink Annotations, and Gitignore
dependencies:
- WP03
requirement_refs:
- C-002
- C-005
- FR-009
- FR-011
planning_base_branch: feat/glossary-save-seed-file-and-core-terms
merge_target_branch: feat/glossary-save-seed-file-and-core-terms
branch_strategy: Planning artifacts for this feature were generated on feat/glossary-save-seed-file-and-core-terms. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/glossary-save-seed-file-and-core-terms unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
- T032
history:
- date: '2026-04-23'
  event: created
authoritative_surface: src/specify_cli/cli/commands/glossary.py
execution_mode: code_change
mission_slug: glossary-drg-surfaces-and-charter-lint-01KPTY5Y
owned_files:
- src/specify_cli/cli/commands/glossary.py
- src/specify_cli/template/renderer.py
- .gitignore
- tests/specify_cli/cli/commands/test_glossary_show.py
tags: []
---

# WP06 — Glossary Show CLI, Backlink Annotations, and Gitignore

**Mission**: glossary-drg-surfaces-and-charter-lint-01KPTY5Y  
**Branch**: `main` (planning base) → `main` (merge target)  
**Execute**: `spec-kitty agent action implement WP06 --agent <name>`

**⚠ Dependency**: WP03 must be approved and merged before this WP starts. `GlossaryEntityPageRenderer` and `TermNotFoundError` from `src/specify_cli/glossary/entity_pages.py` must be importable.

## Objective

Three deliverables:
1. `spec-kitty glossary show <term>` CLI command — renders an entity page to the terminal
2. `<!-- glossary:<term-id> -->` HTML comment anchors injected into artifact rendering so entity pages can build backlinks
3. `.gitignore` entry ensuring entity pages are never committed

## Context

### Existing `glossary.py` CLI

`src/specify_cli/cli/commands/glossary.py` already has `list`, `conflicts`, and `resolve` subcommands registered on `app = typer.Typer(...)`. Add `show` alongside them.

### `template/renderer.py`

`src/specify_cli/template/renderer.py` is responsible for rendering WP/ADR/step contract templates into Markdown output. Inspect it to find where term references appear in rendered text — the goal is to inject a `<!-- glossary:<term-id> -->` HTML comment anchor when a term from the glossary appears.

This is a lightweight annotation. The comment is invisible to all standard Markdown renderers and does not affect existing output in any way (C-005).

### Gitignore

The entity page output path is `.kittify/charter/compiled/glossary/`. This path should be gitignored. Check whether `.kittify/charter/compiled/` is already in `.gitignore` (likely is); if so, add a comment noting it covers entity pages too. If not, add the specific path.

---

## Subtask T029 — `glossary show` Subcommand

**File**: `src/specify_cli/cli/commands/glossary.py`

**Purpose**: Add a `show` command that generates the entity page for a named term and renders it in the terminal.

```python
@app.command()
def show(
    term: str = typer.Argument(..., help="Term surface name or glossary URN (e.g. 'deployment-target' or 'glossary:deployment-target')"),
    repo_root: Path = typer.Option(
        None,
        envvar="SPEC_KITTY_REPO_ROOT",
        help="Repository root (auto-detected if not set)",
    ),
) -> None:
    """Render the entity page for a glossary term."""
    from specify_cli.glossary.entity_pages import GlossaryEntityPageRenderer, TermNotFoundError
    from specify_cli.repo import find_repo_root  # or equivalent auto-detection helper

    if repo_root is None:
        repo_root = find_repo_root(Path.cwd())

    # Normalize term: if not a URN, try both "glossary:<term>" and bare term
    term_id = term if term.startswith("glossary:") else f"glossary:{term}"

    renderer = GlossaryEntityPageRenderer(repo_root)
    try:
        page_path = renderer.generate_one(term_id)
    except TermNotFoundError:
        # Try bare term as fallback
        try:
            page_path = renderer.generate_one(term)
        except TermNotFoundError:
            console.print(f"[red]Term not found:[/red] {term}")
            console.print("[dim]Run `spec-kitty glossary list` to see available terms.[/dim]")
            raise typer.Exit(1)

    content = page_path.read_text(encoding="utf-8")
    from rich.markdown import Markdown
    console.print(Markdown(content))
```

Inspect `glossary.py` for the existing `console` object and `find_repo_root` pattern — use the same helper used by `list` and `conflicts`.

---

## Subtask T030 — Backlink Anchor Injection in `renderer.py`

**File**: `src/specify_cli/template/renderer.py`

**Purpose**: When rendering artifact content (WP files, ADR templates, step contracts), inject `<!-- glossary:<term-id> -->` HTML comment anchors so that `GlossaryEntityPageRenderer._load_backlinks()` can discover them during entity page generation.

**Approach** (lightweight, non-breaking):

1. Inspect `renderer.py` to understand how it renders content. Find where term references from the glossary might appear.
2. Add a helper:
```python
def _annotate_glossary_refs(content: str, term_surfaces: dict[str, str]) -> str:
    """
    Inject <!-- glossary:<term-id> --> after first occurrence of each known term surface.
    term_surfaces: { surface_lower -> term_id }
    Does not modify the visible content.
    """
    import re
    for surface_lower, term_id in sorted(term_surfaces.items(), key=lambda x: -len(x[0])):
        # Case-insensitive match for whole word
        pattern = re.compile(r'\b' + re.escape(surface_lower) + r'\b', re.IGNORECASE)
        # Add annotation after first match only
        annotated = pattern.sub(
            lambda m: m.group(0) + f'<!-- glossary:{term_id} -->',
            content,
            count=1,
        )
        content = annotated
    return content
```

3. Call `_annotate_glossary_refs()` at the point where final rendered content is produced, if a glossary index is available. If loading the glossary index fails or is slow, skip annotation silently (C-005).

4. If loading the full term surfaces dict from `GlossaryStore` is expensive, cache it per render session.

**Important**: This annotation is additive and invisible. It must never cause existing rendering to fail or change visible output. Wrap the annotation call in a `try/except` that logs a debug warning and returns the original content unchanged on any error.

---

## Subtask T031 — Gitignore

**File**: `.gitignore`

**Steps**:
1. Search `.gitignore` for `.kittify/charter/compiled/` or `.kittify/charter/`.
2. If the path is already covered, add a comment: `# covers .kittify/charter/compiled/glossary/ entity pages`.
3. If not covered, add:
```
# Generated glossary entity pages — never commit
.kittify/charter/compiled/glossary/
```

Verify with `git check-ignore -v .kittify/charter/compiled/glossary/test.md` after the change.

---

## Subtask T032 — Tests

**File**: `tests/specify_cli/cli/commands/test_glossary_show.py` (new)

**Scenarios**:

1. **Success — term found**: Mock `GlossaryEntityPageRenderer.generate_one()` to write a fixture Markdown file. Invoke `show "deployment-target"` via Typer's `CliRunner`. Assert exit code 0. Assert Markdown content was printed to stdout.

2. **Failure — term not found**: Mock `generate_one()` to raise `TermNotFoundError`. Assert exit code 1. Assert error message includes the term name. Assert "Run `spec-kitty glossary list`" hint appears.

3. **URN input**: Pass `"glossary:deployment-target"` as the term argument. Assert `generate_one()` is called with exactly that URN (not double-prefixed).

4. **Bare term normalized**: Pass `"deployment-target"` without the `glossary:` prefix. Assert `generate_one()` is first called with `"glossary:deployment-target"`.

**Run**: `cd src && pytest tests/specify_cli/cli/commands/test_glossary_show.py -v`

---

## Branch Strategy

- **Planning base branch**: `main` (post WP03 merge)
- **Merge target**: `main`
- **Execution workspace**: Allocated by `spec-kitty agent action implement WP06 --agent <name>`.

---

## Definition of Done

- [ ] `spec-kitty glossary show <term>` exits 0 and renders Markdown for a known term
- [ ] `spec-kitty glossary show <unknown>` exits 1 with clear error + list hint
- [ ] Both bare term and `glossary:` URN forms are accepted
- [ ] `renderer.py` injects `<!-- glossary:<term-id> -->` annotations without breaking existing rendering
- [ ] Annotation injection is wrapped in `try/except` — never raises
- [ ] `.gitignore` covers `.kittify/charter/compiled/glossary/`
- [ ] All 4 test scenarios pass: `pytest tests/specify_cli/cli/commands/test_glossary_show.py`
- [ ] `ruff check src/specify_cli/cli/commands/glossary.py` passes

---

## Reviewer Guidance

1. Confirm the `show` command uses the same `repo_root` auto-detection helper as `glossary list` — do not add a new mechanism.
2. Confirm annotation injection in `renderer.py` is in a `try/except` and changes no visible output on success (only adds HTML comments).
3. Verify `.gitignore` change with `git check-ignore` before approving — do not accept untested gitignore changes.
4. Confirm the `show` command does not leave `.md.tmp` files on disk on success or failure.
