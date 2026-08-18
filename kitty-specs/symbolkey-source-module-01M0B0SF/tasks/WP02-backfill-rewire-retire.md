---
work_package_id: WP02
title: Backfill + helper rewire + parse retirement + completeness/integrity guards (ATOMIC)
dependencies:
- WP01
requirement_refs:
- C-003
- C-004
- FR-002
- FR-003
- FR-004
- FR-005
- FR-006
- FR-007
- NFR-001
- NFR-002
planning_base_branch: remediation/symbolkey-source-module-3552
merge_target_branch: remediation/symbolkey-source-module-3552
branch_strategy: Planning artifacts for this mission were generated on remediation/symbolkey-source-module-3552. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into remediation/symbolkey-source-module-3552 unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
- T012
- T013
- T014
history:
- at: '2026-08-18T18:20:00+00:00'
  actor: claude
  note: WP created by /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: tests/architectural/test_no_dead_symbols.py
create_intent: []
execution_mode: code_change
owned_files:
- tests/architectural/test_no_dead_symbols.py
- tests/architectural/_refresh_dead_symbol_hashes.py
- tests/architectural/test_refresh_dead_symbol_hashes.py
role: implementer
tags: []
tracker_refs: []
---

## ⚡ Do This First: Load Agent Profile

Load your profile: `/ad-hoc-profile-load python-pedro` (or `spec-kitty agent profile show python-pedro` + `spec-kitty charter context --action implement --json`). ATDD; `mypy --strict` + zero new suppressions; complexity ≤ 15; realistic test data; never green-wash a red.

## Objective

Make `source_module` the single canonical provenance source: backfill it onto every content-tier
allowlist entry, rewire the refresh helper to read it, delete the machine comment-parse surfaces,
and add the completeness + integrity guards that replace what the deletion removes — **all in one
commit**. This is the heart of #3552.

## ⚠️ ATOMICITY (C-004) — this is ONE WP, ONE lane, ONE commit

`ruff` line-length is **164** (`pyproject.toml`). Many content-tier allowlist lines already sit at
164; appending `source_module="…"` overflows → E501, so a large fraction of entries must reflow to
multi-line. The **minimal atomic co-commit set is T007 + T008 + T009**, because:
- reflow (T007) shifts `Call.lineno`, redding the still-live `test_every_content_tier_entry_has_parseable_provenance_comment` unless it is deleted in the same commit (T009); and
- T009 deletes `_PROVENANCE_COMMENT_RE`, which the helper still imports (T008 removes that import) — so T009 without T008 reds collection with an `ImportError`.

**Batch the entire WP into a single commit.** Subtasks are event-sourced (`mark-status` per Txxx) and
auto-commit; committing per-subtask produces a red intermediate commit even on one lane. Do the whole
change, verify green (T014), then commit once. `decide()` and the `NEEDS_MODULE_PATH` outcome are
**unchanged** — provenance-only; a live collision still correctly escalates (confirm, do not rewrite).

> **⚠️ Never `ast.unparse` this file.** `ast.unparse` strips **all** comments, destroying the
> `# module::Name` audit comments FR-004/SC-004 mandate keeping. The backfill must be a **targeted
> textual splice** (use AST only to locate each `SymbolKey(...)` call's column offsets, then insert
> the kwarg by string manipulation, exactly as `_refresh_dead_symbol_hashes.py::_apply` overwrites a
> hash in place). For reflow of over-length calls, use a **comment-preserving formatter** (`ruff format`
> — it reflows long calls to canonical multi-line form and keeps comments), never `ast.unparse`.

## Context

- Allowlist source: `tests/architectural/test_no_dead_symbols.py` — content-tier entries are
  `SymbolKey("Name","hash")` (no `module_path=`) with a `# module::Name` provenance comment
  (2 formats today: trailing 192, preceding 146). Collision-tier entries already carry `module_path=`.
- Helper: `tests/architectural/_refresh_dead_symbol_hashes.py` — `AllowlistEntry.module_path`
  currently recovers from the comment via `_recover_provenance` (~L237) / `_comments_by_row` (~L183).
  `parse_allowlist_entries` calls `_recover_provenance` (~L276). `Outcome.UNRECOVERABLE` (~L88) is the
  generic fail-closed branch.
- Parse surfaces to delete (paula's verified list): `_PROVENANCE_COMMENT_RE` (`test_no_dead_symbols.py:1435`),
  `_content_tier_entry_lines`/`_comments_by_line` (`:1440-1481`), `test_every_content_tier_entry_has_parseable_provenance_comment` (`:1484-1513`),
  `_comments_by_row` (`_refresh_dead_symbol_hashes.py:183-194`), `_recover_provenance` + its call (`:237-251`, `:276`),
  `AllowlistEntry.module_path` comment branch (`:132-141`).
- Blast radius: `test_refresh_dead_symbol_hashes.py` builds `AllowlistEntry` via a local `_entry()`
  helper passing `provenance_module=`/`kwarg_module_path=`, and asserts on `Outcome.UNRECOVERABLE`.
  Its two #3560 tests (`test_decide_escalates_content_tier_entry_needing_collision_tier`,
  `..._escalates_end_to_end`) assert `NEEDS_MODULE_PATH` is correct — they MUST stay green.

## Subtasks

### T007 — Backfill script (targeted textual splice; reuse the real module reader; ruff-format reflow) and run it
Write a one-shot script (ephemeral — do NOT commit it; keep it in scratch). It MUST:
1. Source each content-tier entry's module by reusing the existing **module** reader — `_recover_provenance` (or `_PROVENANCE_COMMENT_RE.group("module")` + its trailing/preceding candidate logic) in `_refresh_dead_symbol_hashes.py`. **Do not** rely on `_content_tier_entry_lines`/`_comments_by_line` for the module — they return `(lineno, bare_name)` / `{line: comment}`, not the module; and do not hand-roll a second regex (that re-derives the banned parser and risks missing the `preceding` format, 146 entries). Call this before T008/T009 delete it.
2. Insert `source_module="<module>"` as a kwarg into each content-tier `SymbolKey(...)` call via a **targeted textual splice** — use AST to locate the call's column offsets, then string-insert (mirror `_refresh_dead_symbol_hashes.py::_apply`). **Never `ast.unparse`** (it strips the `# module::Name` audit comments this mission keeps).
3. Reflow over-length (>164) calls by running **`ruff format`** on the file after the splice — it produces canonical multi-line calls and **preserves comments**. Do not hand-roll multi-line formatting.
4. **Assert** the module reader's own allowlist-scoped count equals the number of entries backfilled — abort on mismatch (makes SC-001 a mechanical gate; never hardcode a count).
5. Run it; verify `git diff`: correct module per symbol (spot-check `preceding`-format entries), collision-tier entries untouched, every `# module::Name` comment still present.

### T008 — Rewire the helper (and kill the dangling imports)
- Add a `source_module: str | None` field to `AllowlistEntry` (drop/rename the now-obsolete `provenance_module`; keep `kwarg_module_path`). Populate it from the AST via a new `_source_module_kwarg` helper mirroring the existing `_module_path_kwarg`. Update the class docstring.
- `AllowlistEntry.module_path` returns `self.source_module` (delete the comment-recovered branch).
- Delete `_recover_provenance` + its call in `parse_allowlist_entries`, and delete `_comments_by_row`.
- **Delete now-dangling imports** (else `F401`/`ImportError`): the `_PROVENANCE_COMMENT_RE` import from `test_no_dead_symbols` (`_refresh_dead_symbol_hashes.py:54-55`) and `import io`/`import tokenize` (`:45-46`, used only by `_comments_by_row`).
- Update every `AllowlistEntry(...)` construction site (incl. the `_entry()` fixture in T013) so no `provenance_module` reference survives (whack-a-field: don't leave a second provenance field alive).

### T009 — Delete the test-side parse surfaces (same commit as T007/T008)
Delete `_PROVENANCE_COMMENT_RE`, `_content_tier_entry_lines`/`_comments_by_line`, and `test_every_content_tier_entry_has_parseable_provenance_comment` from `test_no_dead_symbols.py`. Also delete the now-orphaned `import re` (`:57`, used only by the regex) and `import tokenize` (`:58`, used only by `_comments_by_line`). Keep the `# module::Name` comment TEXT on the entries (human audit).

### T010 — Reword `Outcome.UNRECOVERABLE` + stale docstrings (keep the branch)
- Keep the `decide()` `UNRECOVERABLE` branch (generic fail-closed backstop); only reword its comment-specific docstring ("no `source_module` recovered", not "from the comment").
- Reword the stale pre-rewire prose in WP02-owned files: the "Single-source authorities" docstring (`_refresh_dead_symbol_hashes.py:26-39`) and module banner (`:3`); and the provenance-normalization comment block (`test_no_dead_symbols.py:1418-1434`) that documents the very surfaces T009 deletes.

### T011 — Completeness + integrity guards (FR-006 / FR-007)
- **Completeness (FR-006)** `test_every_content_tier_entry_has_source_module`: fails if any allowlist-scoped content-tier `SymbolKey(...)` lacks a `source_module=` kwarg. Replaces the deleted parseable-comment gate; keeps SSOT as the corpus grows.
- **Integrity (FR-007)**: cross-check each `source_module` against the **live importable corpus** — the named module exists and declares the symbol (reuse `classify_collisions`' corpus walk). **Do NOT re-parse the `# module::Name` comment** — that recreates the machine comment-parser SC-004 retires under a new name (whack-a-field). If any comment-adjacent parsing is truly unavoidable, add its symbol name to the T014 grep-ban so it can't be silently cloned.

### T012 — Comment-independent recovery test (FR-005 / SC-002)
Red-first: with `source_module` set, garble/delete the entry's provenance comment and assert the helper's recovered module + refresh decision are unchanged. Show it fails against the pre-rewire (comment-parsing) code and passes after.

### T013 — Fix the blast-radius suite
Update `test_refresh_dead_symbol_hashes.py`'s `_entry()` fixtures (now `source_module=`, no `provenance_module=`) / `UNRECOVERABLE` assertions to the new model. **Confirm** the two #3560 Finding-1 tests still pass asserting `NEEDS_MODULE_PATH` (do not touch their intent).

### T014 — Verify
```bash
uv run ruff check tests/architectural/test_no_dead_symbols.py tests/architectural/_refresh_dead_symbol_hashes.py tests/architectural/test_refresh_dead_symbol_hashes.py
uv run mypy --strict tests/architectural/_refresh_dead_symbol_hashes.py tests/architectural/test_refresh_dead_symbol_hashes.py
PWHEADLESS=1 uv run pytest tests/architectural/test_no_dead_symbols.py tests/architectural/test_refresh_dead_symbol_hashes.py tests/architectural/test_ratchet_baselines.py -q
# SC-004: no machine parse surface remains (extend this ban-list if any new comment reader is introduced)
grep -nE "_recover_provenance|_PROVENANCE_COMMENT_RE|_comments_by_row|_comments_by_line|_content_tier_entry_lines|test_every_content_tier_entry_has_parseable_provenance_comment" tests/architectural/ -r || echo "parse surfaces retired"
```
All green; ratchet baselines unchanged; allowlist cardinality equal pre/post.

**Sonar note (S1192, expected — call out in the PR, do not "fix"):** the backfill repeats each module path as a `source_module="…"` literal across every symbol that module exports (e.g. `specify_cli.dashboard.api_types` ×18, `specify_cli.validators.research` ×17). This is **per-symbol allowlist data, not logic** — non-extractable, exactly like the existing `module_path="doctrine.shared"` ×9 precedent in the collision-tier entries. Do not hoist to constants; note it for Sonar UI hotspot review in the PR body (per the repo's "call out remaining Sonar UI work" standing order).

## Branch Strategy

Planning base and merge target are both `remediation/symbolkey-source-module-3552`. This WP depends on WP01 and branches from WP01's completed base; execution worktree per `lanes.json`. All three owned files are in this one lane (no cross-lane split).

## Definition of Done

- Every content-tier entry carries `source_module=` (FR-003; mechanically asserted, FR-006).
- Helper reads `source_module`; the 6 machine parse surfaces are gone; comment text kept (FR-002/FR-004/SC-004).
- `Outcome.UNRECOVERABLE` branch retained (docstring reworded).
- FR-005 comment-independent test + FR-007 integrity guard green; #3560 tests green.
- ruff + mypy --strict clean; full suites green; ratchet baselines + cardinality unchanged. **No `_baselines.yaml`/ratchet key added (C-003).**

## Reviewer guidance

Verify atomicity (single commit; no red intermediate), that the backfill reused the verified reader (not a re-implemented parser), that `source_module` values are correct per symbol (spot-check the `preceding`-format entries), that `decide()`/`NEEDS_MODULE_PATH` logic is untouched, and that no ratchet baseline moved.
