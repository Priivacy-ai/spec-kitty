---
work_package_id: WP07
title: spec-kitty migrate downstream compatibility subcommand
dependencies:
- WP01
requirement_refs:
- FR-015
planning_base_branch: doctrine/drg-missing-links-analysis
merge_target_branch: doctrine/drg-missing-links-analysis
branch_strategy: Planning artifacts for this mission were generated on doctrine/drg-missing-links-analysis. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/drg-missing-links-analysis unless the human explicitly redirects the landing branch.
subtasks:
- T034
- T035
- T036
- T037
phase: Phase 2 - Compatibility tooling
assignee: ''
agent: "claude:sonnet:reviewer-renata:reviewer"
shell_pid: "91672"
shell_pid_created_at: "1784643696.422909"
history:
- at: '2026-07-21T11:08:12Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/migration/rewrite_opposed_by.py
create_intent:
- src/specify_cli/migration/rewrite_opposed_by.py
- tests/specify_cli/migration/test_rewrite_opposed_by.py
execution_mode: code_change
model: ''
owned_files:
- src/specify_cli/migration/rewrite_opposed_by.py
- src/specify_cli/cli/commands/migrate_cmd.py
- tests/specify_cli/migration/test_rewrite_opposed_by.py
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP07 – spec-kitty migrate downstream compatibility subcommand

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `{{agent_profile}}`
- **Role**: `{{role}}`
- **Agent/tool**: `{{agent}}`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for `task_type: implement` and `authoritative_surface: src/specify_cli/migration/rewrite_opposed_by.py`.

---

## ⚠️ IMPORTANT: Review Feedback

Check the `review_ref` field in the event log before starting if this WP was returned from review. Address all feedback; update the Activity Log as you go.

---

## Objectives & Success Criteria

FR-015, resolved decision (research.md): new `spec-kitty migrate` subcommand, no deprecation window. This is the mitigation for downstream/org-pack `opposed_by` YAML that would otherwise hard-break once WP03's schema change ships. Read `contracts/migrate-opposed-by.md` in full before starting — it is the binding contract.

Done means (per `contracts/migrate-opposed-by.md`):
- `spec-kitty migrate rewrite-opposed-by --pack PATH --dry-run` reports planned rewrites without writing.
- A real run rewrites `opposed_by` entries to `in_tension_with`/`rejects` edges and removes the `opposed_by` key from the source YAML.
- A second run against an already-migrated pack is a no-op (idempotent).
- An entry that can't be unambiguously classified exits non-zero with a clear diagnostic naming the entry — never a raw Pydantic traceback.

## Context & Constraints

- Model this on `src/specify_cli/migration/backfill_identity.py` (existing one-shot-rewrite precedent in this repo) and wire it the same way `backfill-identity` is wired in `src/specify_cli/cli/commands/migrate_cmd.py` (existing subcommands there use kebab-case names, e.g. `backfill-identity`, `backfill-topology`, `charter-encoding`, `normalize-lifecycle` — follow that convention for `rewrite-opposed-by`).
- Classification rule (from D1/D2, already resolved): an `opposed_by` entry describing a competing-but-valid rule (tension-style) becomes an `in_tension_with` edge; an entry describing rejection of a genuine anti-pattern becomes a `rejects` edge pointing at (or creating) a `NodeKind.ANTI_PATTERN`-marked node. There is no purely mechanical signal distinguishing the two in general — decide the classification heuristic deliberately (e.g. does the target's `kind` in the target pack correspond to something structurally paradigm-like being rejected as bad practice, vs. two peer rules of the same standing competing) and document it in the module docstring, since a future maintainer will need to understand why an entry was classified one way and not the other.
- This WP is fully additive — it operates on *external* org-pack YAML the operator points it at, not this repo's built-in content. It does not need WP02/WP03 to be complete; it only needs WP01's relations to exist as rewrite targets.

## Branch Strategy

- **Strategy**: single_branch — no coordination/lanes topology; planning and merge-target branch are the same branch.
- **Planning base branch**: `doctrine/drg-missing-links-analysis`
- **Merge target branch**: `doctrine/drg-missing-links-analysis`

Implementation command: `spec-kitty agent action implement WP07 --agent <name>` (depends on WP01 only — can start immediately once WP01 merges, in parallel with WP02-WP06).

## Subtasks & Detailed Guidance

### Subtask T034 – Implement the rewrite logic

- **Purpose**: The core classify-and-rewrite engine, independent of CLI wiring.
- **Steps**:
  1. Create `src/specify_cli/migration/rewrite_opposed_by.py`. Read `src/specify_cli/migration/backfill_identity.py` first for the module shape/conventions this repo expects (function naming, how it reads/writes YAML, how it reports what it did).
  2. Implement a function that: scans a target pack's directive/tactic/paradigm YAML sources for `opposed_by` entries; for each, applies the classification rule (see Context & Constraints) to decide `in_tension_with` vs `rejects`; for a `rejects` classification, ensures the target anti-pattern node exists (create if absent, per WP02's node shape) and is marked `kind: anti_pattern`; emits the new edge into the appropriate hand-authored location (mirroring WP02's approach — the new edges are NOT extractor-derivable, so this tool must write them the same way a human would); removes the `opposed_by` key from the source YAML once rewritten.
  3. Return a structured result (list of rewrites performed, or planned if dry-run) rather than just printing — the CLI layer (T035) formats it.
- **Files**: `src/specify_cli/migration/rewrite_opposed_by.py` (new)
- **Parallel?**: No — foundation for T035/T036.

### Subtask T035 – Wire the CLI subcommand

- **Purpose**: Operator-facing entry point.
- **Steps**: In `src/specify_cli/cli/commands/migrate_cmd.py`, add `@app.command(name="rewrite-opposed-by")` following the exact pattern of the existing `backfill-identity`/`backfill-topology`/`charter-encoding`/`normalize-lifecycle` commands (options, help text style, output formatting). Support `--pack PATH`, `--dry-run`, `--json`.
- **Files**: `src/specify_cli/cli/commands/migrate_cmd.py`
- **Parallel?**: No — depends on T034's function signature.

### Subtask T036 – Unclassifiable-entry diagnostic

- **Purpose**: Contract requirement — "exit non-zero with a clear diagnostic ... not a raw Pydantic validation traceback."
- **Steps**: When T034's classification logic can't confidently decide `in_tension_with` vs `rejects` for a given entry, surface a specific, actionable error naming the entry (source file, target ID, why it's ambiguous) and exit non-zero — do not let an unhandled exception from downstream Pydantic validation be the operator's only signal.
- **Files**: `src/specify_cli/migration/rewrite_opposed_by.py`
- **Parallel?**: No — part of T034's implementation, called out separately because it's easy to skip in favor of only handling the happy path.

### Subtask T037 – Tests

- **Purpose**: NFR-005 + the contract's explicit test requirements.
- **Steps**: In new `tests/specify_cli/migration/test_rewrite_opposed_by.py` (module already has `__init__.py` — follow the existing test file conventions in that directory, e.g. `test_backfill_identity.py`):
  1. `--dry-run` against a pack with `opposed_by` entries reports planned rewrites and writes nothing.
  2. A real run rewrites correctly and removes the `opposed_by` key.
  3. A second run against the now-migrated pack is a no-op (idempotency).
  4. An unclassifiable entry produces the T036 diagnostic and a non-zero exit, not a traceback.
- **Files**: `tests/specify_cli/migration/test_rewrite_opposed_by.py` (new)
- **Parallel?**: No — after T034-T036.

## Test Strategy

- `.venv/bin/pytest tests/specify_cli/migration/test_rewrite_opposed_by.py -q`
- `.venv/bin/ruff check` + `.venv/bin/mypy` on `owned_files`.

## Risks & Mitigations

- **Risk**: Landing this WP after WP03 ships, leaving a window where downstream consumers have no migration path. **Mitigation**: this WP only depends on WP01 — schedule it to run in parallel with WP02-WP06, not after WP03.
- **Risk**: A classification heuristic that's an undocumented guess. **Mitigation**: T034 requires documenting the heuristic in the module docstring.

## Review Guidance

- Run `--dry-run` and a real run yourself against a small synthetic pack with a mix of tension-style and rejection-style `opposed_by` entries — confirm the classification matches your own reading of each entry's intent.
- Confirm the idempotency test actually re-runs the command against its own output, not against a hand-crafted "already migrated" fixture that might not match real output shape.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>`

- 2026-07-21T11:08:12Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP07 --to <status>` to change WP status.
- 2026-07-21T13:41:14Z – claude:sonnet:python-pedro:implementer – shell_pid=80649 – Assigned agent via action command
- 2026-07-21T13:55:46Z – claude:sonnet:python-pedro:implementer – shell_pid=80649 – Ready for review: rewrite-opposed-by migration tool, CLI wiring, and tests implemented
- 2026-07-21T14:21:38Z – claude:sonnet:reviewer-renata:reviewer – shell_pid=91672 – Started review via action command
- 2026-07-21T14:27:23Z – user – shell_pid=91672 – Review passed: verified occurrence_map.yaml manual_review exception for migrate_cmd.py/rewrite_opposed_by.py (commit 294c1dfdb, root repo) resolves the earlier bulk-edit BLOCK correctly. Traced the classification heuristic against this repo's own real opposed_by corpus in a sandbox copy: all 3 tension-style raw entries (024<->025 x2, tactic->025) -> in_tension_with, all 8 anti-pattern-rejection entries -> rejects, matching manual reading (docstring's 'two tension-style entries' undercounts raw YAML entries by one but the code behavior is correct -- non-blocking prose nit). Ran a real end-to-end migrate/re-migrate cycle on the sandbox copy: opposed_by keys removed, graph fragments written correctly, second run produced 0 rewrites and byte-identical (md5-matched) graph files -- idempotency confirmed live, not just via the test's own byte-comparison assertion (test_second_run_is_noop genuinely asserts text equality across two real runs). Constructed and ran the T036 unclassifiable case (ambiguous cross-type id collision): non-zero exit, no traceback, clear diagnostic naming the entry, confirmed via both direct call and CliRunner. CLI wiring (migrate_cmd.py rewrite-opposed-by) matches backfill-identity/backfill-topology conventions: kebab-case name, --pack/--dry-run/--json, documented exit codes, _error/typer.Exit pattern. pytest (10/10 pass), ruff check, and mypy --strict all clean on the 3 owned files. Confirmed via git show --stat on the WP's own commit (b9e389940) that only the 3 owned files were touched -- no changes to this repo's built-in opposed_by doctrine content (WP03's surface). Anti-pattern checklist: 1 PASS (migrate_cmd.py is sole production caller) 2 PASS (tests exercise real Pydantic DRGGraph/DRGEdge/DRGNode models + real ruamel round-trip, not synthetic dict fixtures) 3 PASS (one except block has a documented best-effort-registry-build rationale + warning log) 4 PASS (FR-015 covered by dry-run/real-run/idempotency/unclassifiable tests) 5 PASS (no frozen-file touches) 6 PASS (no MUST NOT violated) 7 PASS (migrate_cmd.py shared-file concern resolved via committed occurrence_map.yaml exception) 8 PASS (raise path is documented typer.Exit(1) on classification failure, not a bare crash).
