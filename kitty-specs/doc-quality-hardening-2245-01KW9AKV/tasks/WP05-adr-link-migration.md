---
work_package_id: WP05
title: ADR link repair (Lane C)
dependencies: []
requirement_refs:
- FR-008
tracker_refs: []
planning_base_branch: design/doc-quality-hardening-2245
merge_target_branch: design/doc-quality-hardening-2245
branch_strategy: Planning artifacts for this mission were generated on design/doc-quality-hardening-2245. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doc-quality-hardening-2245 unless the human explicitly redirects the landing branch.
subtasks:
- T015
- T016
- T017
phase: Lane C
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "155909"
history:
- at: '2026-06-30T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
- at: '2026-06-30T00:00:00Z'
  actor: system
  action: Re-scoped post-rebase (ccd278061 retired byte-invariance gate). Dropped T018/T019, adr_link_migration.py module, reconciliation-ADR amendment, and transform-coupling guard. Plain link repair only.
agent_profile: python-pedro
authoritative_surface: docs/adr/
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/adr/1.x/2*.md
- docs/adr/2.x/2*.md
- docs/adr/3.x/2*.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP05 – ADR link repair (Lane C)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Scope Note (post-rebase 2026-06-30)

Upstream commit `ccd278061` retired the byte-identity ADR invariance gate. **This WP is now a plain link repair.** There is no byte-invariance waiver, no `adr_link_migration.py` shared-transform module to build, no reconciliation-ADR amendment, and no WP05↔WP06 transform-coupling constraint. Apply the link fixes directly to the ADR bodies. WP06 (census widen) is independent — it edits only `test_adr_content_invariance.py` and has no dependency on this WP.

---

## Objectives & Success Criteria

Repair every broken inline body link in dated ADR bodies under `docs/adr/`. There are two link classes:

1. **Docs-internal rewrites** — links that pointed to directories renamed by the Common Docs move (PR #2225): `docs/development/→docs/guides/`, `docs/how-to/→docs/guides/`, `docs/engineering_notes/→docs/plans/engineering-notes/`; plus nested-`adr/` path-segment removal and cross-era sibling depth fixes within `docs/adr/`.
2. **`kitty-specs/` delinks** — links from dated ADR bodies into `kitty-specs/` mission directories (published ADRs must not depend on transient mission-state paths). Replace each with a stable reference (merged-PR/commit URL or superseding canonical doc) or remove the link, leaving plain prose.

**DoD — count-independent (CRITICAL)**. After repair, ALL of the following must return zero matches:

```bash
# No kitty-specs body links remain in any dated ADR:
grep -rE '\]\([^)]*kitty-specs/' docs/adr/

# No moved-dir body links remain in any dated ADR:
grep -rE '\]\([^)]*docs/(development|how-to|engineering_notes)/' docs/adr/
```

Zero output from both commands is the acceptance criterion. Do not mark this WP done if either grep produces output. The 27-link count is a planning estimate; the live grep output is the ground truth.

Additional checks:
- Every rewritten docs-internal target exists on disk under `docs/`. For any rewritten link whose target does not exist, investigate (wrong era depth, renamed again) — do not commit a link to a non-existent file.
- `ruff` and `mypy` report zero issues on any new/changed code (no new Python module is expected for this WP, but if a helper script is used to apply the rewrites, clean it up before committing).
- All new prose in amended ADR bodies passes `tests/architectural/test_no_legacy_terminology.py`.

This WP does **NOT** edit `tests/docs/test_adr_content_invariance.py` — that is WP06's responsibility.

---

## Context & Constraints

### Why this WP exists

The Common Docs structural move (PR #2225, Mission B) relocated documentation directories without updating ADR body links. The existing live-tree body-link gate (`check_dead_body_links` in `relative_link_fixer.py`) currently excludes `docs/adr/` from its scan (`EXCLUDE_PREFIXES`). Once WP02 removes that exclusion (the terminal gate-flip), every unfixed ADR-body link will fail CI. This WP clears that debt so WP02 can flip the gate green.

The byte-invariance gate (`TestContentInvariance`) was retired upstream by `ccd278061` before this WP was implemented — ADR bodies are now freely editable without any waiver or comparator update. This is a plain find-and-replace operation.

### Owned-files boundary

`owned_files` covers dated ADR files only (`docs/adr/*/2*.md`). This deliberately excludes:

- `docs/adr/**/README.md` — owned by WP07 (Lane D1).
- `docs/adr/3.x/adr-connector-auth-binding-separation.md` and `docs/adr/3.x/adr-github-app-installation-authority.md` — the two non-dated ADRs; census expansion is WP06's responsibility. This WP does not touch them.

### No new module required

The previous plan called for a `scripts/docs/adr_link_migration.py` shared-transform module (decision D-4). That decision is moot — the byte-invariance comparator no longer exists, so there is no second consumer of the transform. Apply the rewrites directly:

- For the **moved-dir class**, `scripts/docs/relative_link_fixer.py --fix` may handle the common prefix rewrites if its fix mode covers them. Verify before using; if it covers the moved-dir set, prefer it over a hand-written script.
- For the **depth/nested-adr class** and **delink class**, apply edits directly to the ADR files (targeted `sed`, Python one-liner, or manual edit for the small delink set).

No new file under `scripts/docs/` needs to be committed for this WP.

### Constraints to honor

- **C-003**: Do not create a new link-checker module.
- **C-004**: All new prose passes `tests/architectural/test_no_legacy_terminology.py` (run before committing).
- **NFR-004**: `ruff` + `mypy` zero issues on any new/changed code.
- **No `test_adr_content_invariance.py` edits**: Census widen is WP06's surface.

### Reference documents

- `kitty-specs/doc-quality-hardening-2245-01KW9AKV/spec.md` — FR-008, Scope Change section
- `kitty-specs/doc-quality-hardening-2245-01KW9AKV/plan.md` — IC-03 (post-rebase), R-F3 lane split
- `scripts/docs/relative_link_fixer.py` — the gate; `--fix` mode may help with moved-dir rewrites

---

## Branch Strategy

- **Strategy**: Planning artifacts were generated on `design/doc-quality-hardening-2245`; completed changes must merge back into `design/doc-quality-hardening-2245`.
- **Planning base branch**: `design/doc-quality-hardening-2245`
- **Merge target branch**: `design/doc-quality-hardening-2245`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T015 — Enumerate broken ADR links (authoritative live set)

- **Purpose**: Establish the ground truth for what needs fixing before touching any file.

- **Steps**:
  1. Run the two authoritative grep commands and save output:
     ```bash
     grep -rEl '\]\([^)]*kitty-specs/' docs/adr/
     grep -rEl '\]\([^)]*docs/(development|how-to|engineering_notes)/' docs/adr/
     ```
     Also run:
     ```bash
     grep -rE '\.\./[123]\.x/adr/' docs/adr/
     ```
     to enumerate nested-`adr/` candidates.
  2. For each file, open it and record the specific links that need repair. Build a working list grouped by class: `moved_dir`, `nested_adr`, `cross_era`, `delink`.
  3. For each `kitty-specs/` link, identify whether a stable GitHub URL (merged PR, issue, or commit) exists. Record the replacement in your working list.
  4. Record the enumerated set in the Activity Log before proceeding to T016/T017.

- **Notes**: The 27-link count is a planning estimate. The live grep output is the ground truth. Do not assume a fixed number — report what you find.

---

### Subtask T016 — Apply docs-internal rewrites (moved-dir and depth classes)

- **Purpose**: Fix links whose target directories were renamed by the Common Docs move, and fix incorrect `../` depths within `docs/adr/`.

- **Files to modify**: Dated ADR files identified in T015 that contain moved-dir or depth-class broken links.

- **Steps**:
  1. **Moved-dir class** (prefix rewrites):
     - `docs/development/` → `docs/guides/`
     - `docs/how-to/` → `docs/guides/`
     - `docs/engineering_notes/` → `docs/plans/engineering-notes/`
     
     Try `python scripts/docs/relative_link_fixer.py --fix` over the ADR tree first. If its fix mode covers these prefix rewrites, use it. If not, apply a targeted `sed` or Python one-liner:
     ```bash
     find docs/adr -name "2*.md" | xargs sed -i \
       's|\]\(docs/development/|\](docs/guides/|g' \
       's|\]\(docs/how-to/|\](docs/guides/|g' \
       's|\]\(docs/engineering_notes/|\](docs/plans/engineering-notes/|g'
     ```
     Verify each rewritten target exists on disk before committing.
  
  2. **Nested-`adr/` class**: Replace `../2.x/adr/X` with `../2.x/X` (and similarly for 1.x). Apply targeted sed or direct file edit.
  
  3. **Cross-era depth class**: For each cross-era link with wrong `../` depth, compute the correct depth relative to the file's era directory and apply the fix.
  
  4. After applying all docs-internal rewrites, verify targets on disk:
     ```bash
     # For each rewritten link, check the target exists
     python -c "
     import re, pathlib
     adr_root = pathlib.Path('docs/adr')
     for f in adr_root.rglob('2*.md'):
         body = f.read_text()
         for m in re.finditer(r'\]\(([^)]*)\)', body):
             link = m.group(1)
             if link.startswith('http') or link.startswith('#') or link.startswith('mailto'):
                 continue
             target = (f.parent / link).resolve()
             if not target.exists():
                 print(f'{f}: dead link -> {link}')
     "
     ```
  
  5. Run the moved-dir grep to confirm zero matches:
     ```bash
     grep -rE '\]\([^)]*docs/(development|how-to|engineering_notes)/' docs/adr/
     ```

- **Notes**: Do not edit `README.md` files or non-dated ADR files (those belong to WP07 or WP06 respectively).

---

### Subtask T017 — Delink `kitty-specs/` ADR links

- **Purpose**: Remove all links from dated ADR bodies that point into `kitty-specs/` mission directories.

- **Files to modify**: Dated ADR files identified in T015 that contain `kitty-specs/` links.

- **Steps**:
  1. For each `kitty-specs/` link (working list from T015):
     - If a stable GitHub URL exists (merged PR, issue, or commit for the referenced mission output), replace the Markdown link with the stable URL.
     - If no stable URL exists (purely historical context), remove the link and leave the link text as plain prose: `[spec.md](kitty-specs/...)` becomes `spec.md` or appropriate prose.
     - Do NOT redirect a `kitty-specs/` link to remain a relative link — these must be delinked, not redirected.
  2. Verify all `kitty-specs/` links are gone:
     ```bash
     grep -rE '\]\([^)]*kitty-specs/' docs/adr/
     ```
     Must return empty output.
  3. Run terminology guard before committing any prose edits:
     ```bash
     pytest tests/architectural/test_no_legacy_terminology.py
     ```

- **Notes**: Commit T017 separately from T016 (delink changes are semantically distinct from path-prefix rewrites).

---

## Test Strategy

### DoD grep-to-zero (authoritative)

After T016 and T017, run:

```bash
grep -rE '\]\([^)]*kitty-specs/' docs/adr/
grep -rE '\]\([^)]*docs/(development|how-to|engineering_notes)/' docs/adr/
```

Both must return empty. This is the completion criterion — not a fixed link count.

### Terminology guard

```bash
pytest tests/architectural/test_no_legacy_terminology.py
```

Run before committing any prose edits to ADR bodies.

### On-disk link resolution

After T016, verify every rewritten docs-internal link target exists on disk. A quick Python check or targeted `relative_link_fixer.py --check` invocation against the ADR tree confirms there are no new dead links introduced.

---

## Risks & Mitigations

| Risk | Likelihood | Mitigation |
|------|-----------|------------|
| Rewritten target does not exist on disk | Medium | Verify each target exists after T016; investigate depth/rename before committing. |
| `kitty-specs/` replacement URL is wrong or stale | Medium | Verify each GitHub URL manually; prefer the merged-PR link (permanent). |
| `README.md` files accidentally edited | Low | `owned_files` glob `2*.md` excludes READMEs; double-check before committing. |
| Non-dated ADR files accidentally edited | Low | `owned_files` glob `2*.md` excludes `adr-*.md` files; confirm before committing. |
| Terminology guard fails on amended prose | Low | Run `pytest tests/architectural/test_no_legacy_terminology.py` before committing T017. |

---

## Review Guidance

Reviewers using `/spec-kitty.review` should verify:

1. **Grep-to-zero (both commands)**: Both of the following return empty:
   ```bash
   grep -rE '\]\([^)]*kitty-specs/' docs/adr/
   grep -rE '\]\([^)]*docs/(development|how-to|engineering_notes)/' docs/adr/
   ```
2. **No dead docs-internal links**: Every rewritten target exists on disk under `docs/`.
3. **No `test_adr_content_invariance.py` edits**: The test file is WP06's surface. Confirm it was not touched.
4. **Owned-files boundary**: No `README.md` files edited (WP07); no non-dated `adr-*.md` files edited (WP06).
5. **No new Python module committed**: No `scripts/docs/adr_link_migration.py` or equivalent (not needed post-rebase).
6. **Terminology guard**: `pytest tests/architectural/test_no_legacy_terminology.py` green on any amended prose.

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

**When adding an entry**:

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Format**:

```
- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action description>
```

**Initial entry**:

- 2026-06-30T00:00:00Z – system – Prompt created.
- 2026-06-30T00:00:00Z – system – Re-scoped post-rebase (ccd278061 retired byte-invariance): dropped T018/T019 (reconciliation-ADR amendment), adr_link_migration.py module, and transform-coupling guard. WP now plain link repair only; WP06 dependency removed.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP05 --to <status>` to change WP status.
- 2026-06-30T17:39:55Z – claude:sonnet:python-pedro:implementer – shell_pid=8739 – Assigned agent via action command
- 2026-06-30T17:46:13Z – claude:sonnet:python-pedro:implementer – shell_pid=8739 – handoff: 19 docs-internal links fixed (development/→guides/, engineering_notes/→plans/engineering-notes/, how-to/→guides/), 34 link-markup instances delinked for 12 kitty-specs/ logical refs; both acceptance greps empty; all fixed link targets verified on disk; 19 files changed
- 2026-06-30T17:46:56Z – claude:opus:reviewer-renata:reviewer – shell_pid=47013 – Started review via action command
- 2026-06-30T17:54:31Z – user – shell_pid=47013 – Moved to planned
- 2026-06-30T17:59:32Z – claude:sonnet:python-pedro:implementer – shell_pid=101791 – Started implementation via action command
- 2026-06-30T18:10:02Z – claude:sonnet:python-pedro:implementer – shell_pid=101791 – FORCE-OVERRIDE rationale: lane-hygiene guard false-positive. The flagged kitty-specs files are byte-identical to the planning branch (git diff design..HEAD -- kitty-specs/ = 0 lines); guard trips on commit-history not content, due to the planning-branch rebase leaving the lane's merge-base at the pre-rebase commit. WP05 code change is the legit 20-file ADR link repair (0 dead links). Override is safe.
- 2026-06-30T18:11:20Z – claude:opus:reviewer-renata:reviewer – shell_pid=155909 – Started review via action command
- 2026-06-30T18:14:45Z – user – shell_pid=155909 – guard false-positive: kitty-specs is status/coord churn + cross-mission dirs from base-refresh merge, not WP05's surface (docs/adr). Cycle-1 re-review PASSED: full docs/adr on-disk scan = 0 dead links (123 md files, 151 links); both DoD greps empty; 3 cycle-1 nested-adr/cross-era fixes correct (prompts ADR ../2.x/ at L170-171; defer-391 sibling-relative no stale adr/ segment); delinks preserve display text; terminology guard 3 passed; no test_adr_content_invariance/README/non-dated edits; all 20 changed files dated 3.x ADRs
