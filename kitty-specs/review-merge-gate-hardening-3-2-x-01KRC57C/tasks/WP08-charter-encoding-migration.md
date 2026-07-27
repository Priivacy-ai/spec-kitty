---
work_package_id: WP08
title: Charter-content encoding migration flow
dependencies:
- WP06
requirement_refs:
- FR-026
- FR-027
planning_base_branch: fix/3.2.x-review-merge-gate-hardening
merge_target_branch: fix/3.2.x-review-merge-gate-hardening
branch_strategy: Planning artifacts for this mission were generated on fix/3.2.x-review-merge-gate-hardening. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/3.2.x-review-merge-gate-hardening unless the human explicitly redirects the landing branch.
subtasks:
- T039
- T040
- T041
- T042
- T043
agent: "claude:opus:reviewer:reviewer"
shell_pid: "510172"
history:
- at: '2026-05-12'
  actor: planner
  event: created
agent_profile: implementer-ivan
authoritative_surface: src/specify_cli/cli/commands/migrate/charter_encoding.py
execution_mode: code_change
mission_id: 01KRC57CNW5JCVBRV8RAQ2ARXZ
mission_slug: review-merge-gate-hardening-3-2-x-01KRC57C
owned_files:
- src/specify_cli/cli/commands/migrate/__init__.py
- src/specify_cli/cli/commands/migrate/charter_encoding.py
- tests/migrate/test_charter_encoding_migration.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else below, load the assigned agent profile so your behavior, boundaries, and governance scope match the role:

```
/ad-hoc-profile-load implementer-ivan
```

The profile establishes your identity (Implementer Ivan), primary focus (writing and verifying production-grade code), and avoidance boundary (no architectural redesign; no scope expansion beyond what this WP authorizes). If the profile load fails, stop and surface the error — do not improvise a role.

## Objective

Add `spec-kitty migrate charter-encoding` that scans every existing mission's charter content for non-UTF-8 encodings, normalizes-or-fails-loud per file via the WP06 chokepoint, and produces a JSON-stable summary report. Idempotent (NFR-006). Prevents apparent regressions on legacy artifacts when WP06's chokepoint goes live in operator workflows.

This WP satisfies FR-026, FR-027, NFR-006 in [`../spec.md`](../spec.md).

## Context

WP06 introduces a chokepoint that fails loudly on non-UTF-8 charter content. The risk: existing missions on `main` may contain charter files authored on Windows in cp1252 (rare but possible). If WP06 ships and an operator opens such a mission, they get `CHARTER_ENCODING_AMBIGUOUS` and call it a regression.

WP08's migration preempts this: it walks every existing mission's charter content, runs the WP06 chokepoint on each file, and either auto-normalizes (with provenance) or surfaces the file for manual repair. Running this once before the WP06 chokepoint reaches operator paths means legacy content is compliant.

The migration is **idempotent** — re-running on an already-normalized corpus is a no-op (NFR-006). Safe to run in CI.

## Branch Strategy

- **Planning/base branch**: `fix/3.2.x-review-merge-gate-hardening`
- **Final merge target**: `main` (after PR review)
- **Execution worktree**: assigned by `spec-kitty implement WP08`. WP08 depends on WP06; that must land first.

## Subtasks

### T039 — Create migrate subcommand

**Purpose**: scaffold a new CLI subcommand `spec-kitty migrate charter-encoding`. Live alongside any existing migrate commands (if there's a `migrate` subgroup) or stand alone.

**Steps**:

1. Inspect the existing CLI surface:
   ```bash
   spec-kitty --help
   spec-kitty migrate --help 2>&1 | head
   ```
2. If `migrate` exists as a typer subgroup, add a new command under it. If not, create a new typer subgroup under `src/specify_cli/cli/commands/migrate/`:
   - `src/specify_cli/cli/commands/migrate/__init__.py` — subgroup entry, exposes `app = typer.Typer()` and registers commands.
   - `src/specify_cli/cli/commands/migrate/charter_encoding.py` — the new command.
3. Register the subgroup in the main CLI entry (likely `src/specify_cli/cli/main.py` or similar).
4. Skeleton:
   ```python
   import typer
   from pathlib import Path

   app = typer.Typer()


   @app.command("charter-encoding")
   def charter_encoding(
       dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without writing."),
       yes: bool = typer.Option(False, "--yes", "-y", help="Apply normalizations without prompting (for CI)."),
       project_root: Path = typer.Option(Path.cwd(), "--project-root"),
   ) -> None:
       """Scan charter content for non-UTF-8 encodings; normalize-or-fail-loud."""
       ...
   ```

**Files**: `src/specify_cli/cli/commands/migrate/__init__.py` (new or existing), `src/specify_cli/cli/commands/migrate/charter_encoding.py` (new)

**Validation**:
- [ ] `spec-kitty migrate charter-encoding --help` shows the command.
- [ ] No regressions to other CLI commands.

### T040 — Implement corpus scan

**Purpose**: walk every existing mission's charter content + global charter; detect encoding per file via the WP06 chokepoint.

**Steps**:

1. Inventory the file patterns per `research.md` R-9:
   - `kitty-specs/*/charter/*.{yaml,md,txt}`
   - `.kittify/charter/*.{yaml,md,txt}`
2. Iterate. For each file:
   ```python
   from charter._io import load_charter_file, CharterEncodingError
   from charter._diagnostics import CharterEncodingDiagnostic

   try:
       content = load_charter_file(file_path)
       action = "already-utf-8" if not content.normalization_applied else "normalized"
   except CharterEncodingError as exc:
       action = "ambiguous"  # surfaced for manual repair
   ```
3. Build an in-memory summary:
   ```python
   summary = {
       "files_inspected": int,
       "already_utf8": list[Path],
       "normalized": list[tuple[Path, str]],  # (path, detected_encoding)
       "ambiguous": list[tuple[Path, str]],   # (path, diagnostic_body)
   }
   ```
4. The chokepoint's `load_charter_file()` writes provenance as a side effect. The migration relies on this; do **not** duplicate provenance writes in WP08.

**Files**: `src/specify_cli/cli/commands/migrate/charter_encoding.py`

**Validation**:
- [ ] Corpus inventory correctly identifies all charter files on the repo at HEAD.
- [ ] No `read_text` calls outside the chokepoint — all reads go through WP06's loader.

### T041 [P] — Interactive mode + `--dry-run` and `--yes` flags

**Purpose**: operator-friendly defaults; CI-friendly automation.

**Steps**:

1. **Default mode (interactive)**: for each file that requires normalization (not `already-utf-8`), prompt:
   ```
   File: kitty-specs/foo-01ABCDEF/charter/charter.yaml
   Detected: cp1252 (confidence 0.93)
   Action: normalize to UTF-8 with provenance record? [y/N/a (yes-all)]
   ```
2. **`--dry-run`**: show what would change, write no files, return exit 0 if no ambiguity, exit non-zero if any ambiguity.
3. **`--yes`**: apply normalizations without prompting; exit non-zero if any file is `ambiguous` (operator must repair manually).
4. Use `typer.confirm()` or `rich.prompt.Confirm` for the prompt; keep output legible on a 80-col terminal.

**Files**: same as T040.

**Validation**:
- [ ] All three modes (interactive default, `--dry-run`, `--yes`) behave per spec.
- [ ] `--dry-run` writes nothing to the filesystem (no provenance, no normalizations).

### T042 — Idempotency check

**Purpose**: NFR-006. Re-running on an already-normalized corpus is a no-op (no new provenance records, no file rewrites).

**Steps**:

1. The chokepoint's natural behavior already satisfies this for normalized files: a pure-UTF-8 file returns with `normalization_applied=False` and writes a provenance record. But a second run would write another provenance record for the same file.
2. **The idempotency rule**: WP08's migration filters out files that pass `already-utf-8` BEFORE invoking the chokepoint. Use a cheap pre-check:
   ```python
   def _is_pure_utf8(path: Path) -> bool:
       try:
           path.read_bytes().decode("utf-8")
           return True
       except UnicodeDecodeError:
           return False
   ```
3. Only invoke `load_charter_file()` on files that fail the pre-check OR have never been recorded in provenance (heuristic: search `.encoding-provenance.jsonl` for the file path).
4. On the second run, all files are pure-UTF-8 (because the first run normalized them); the pre-check skips them; no provenance records written; exit 0.

**Files**: same as T040.

**Validation**:
- [ ] Run migration twice on the same corpus. First run normalizes; second run is a no-op (no new provenance records, no file mtimes changed for already-UTF-8 files).

### T043 — JSON-stable summary report + regression test

**Purpose**: FR-027. The migration emits a machine-readable summary suitable for CI consumption.

**Steps**:

1. At the end of the command, write the summary to stdout as JSON when `--json` is passed (or always; choose based on UX preference). Schema:
   ```json
   {
     "result": "success" | "ambiguous_present" | "error",
     "files_inspected": 42,
     "already_utf8": ["path1", "path2", ...],
     "normalized": [{"path": "p", "encoding": "cp1252", "confidence": 0.93}, ...],
     "ambiguous": [{"path": "p", "diagnostic_body": "..."}, ...],
     "dry_run": false
   }
   ```
2. Exit code:
   - 0 if `result == "success"` (everything pure-UTF-8 or normalized cleanly).
   - non-zero if any `ambiguous` entries (CI must fail).
3. Create `tests/migrate/test_charter_encoding_migration.py`:
   - **Test: legacy cp1252 mission is normalized**.
     - Setup: a tmp mission directory with a cp1252-encoded `charter.yaml`.
     - Run: `spec-kitty migrate charter-encoding --yes --project-root tmp_repo`.
     - Assert: file is now UTF-8; provenance record present; exit 0.
   - **Test: idempotency**.
     - Run the migration twice on the same tmp_repo.
     - Assert: second run writes no new provenance records; exit 0.
   - **Test: ambiguous content surfaces with non-zero exit**.
     - Setup: a synthetic ambiguous file.
     - Run with `--yes`.
     - Assert: exit non-zero; summary lists the file under `ambiguous`.

**Files**: `tests/migrate/test_charter_encoding_migration.py` (new)

**Validation**:
- [ ] JSON summary schema stable across runs.
- [ ] All three tests pass.
- [ ] Removing T042's pre-check breaks the idempotency test — proves it exercises the contract.

## Definition of Done

- [ ] T039–T043 acceptance checks pass.
- [ ] FR-026, FR-027 cited in commits.
- [ ] NFR-006 (idempotency) verified by regression.
- [ ] Glossary entry `charter-content migration` exists (likely already added by WP06 per FR-034 obligation).

## Risks and Reviewer Guidance

**Risk**: operator runs `--yes` in CI on a corpus containing genuinely ambiguous files. Exit non-zero is correct behavior — CI must fail loudly. Do **not** add an "auto-bypass" mode that silently uses `--unsafe`; the operator must explicitly choose `--unsafe` per file or in the loader.

**Risk**: charter content patterns are wider than `*.yaml`, `*.md`, `*.txt`. If the corpus contains e.g. `*.csv` or `*.json` charter snippets, the migration misses them. Mitigation: keep the pattern list explicit and audit-able; widen only with current evidence.

**Reviewer focus**:
- T042: idempotency check — does it actually short-circuit the chokepoint for already-UTF-8 files?
- T043: JSON schema stability; non-zero exit on ambiguous.

## Suggested implement command

```bash
spec-kitty agent action implement WP08 --agent claude --mission review-merge-gate-hardening-3-2-x-01KRC57C
```

## Activity Log

- 2026-05-12T13:28:20Z – claude:sonnet:implementer-ivan:implementer – shell_pid=498389 – Started implementation via action command
- 2026-05-12T13:36:27Z – claude:sonnet:implementer-ivan:implementer – shell_pid=498389 – WP08 ready: migrate subcommand + corpus scan + dry-run/yes flags + idempotency pre-check + JSON summary + regression
- 2026-05-12T13:37:07Z – claude:opus:reviewer:reviewer – shell_pid=510172 – Started review via action command
- 2026-05-12T13:39:40Z – claude:opus:reviewer:reviewer – shell_pid=510172 – Review passed: FR-026/FR-027 + NFR-006 idempotency verified; migrate_cmd.py registration is pure typer plumbing (no logic).
