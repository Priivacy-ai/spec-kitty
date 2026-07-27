---
work_package_id: WP03
title: Repair 5 canonical-CHANGELOG body links
dependencies: []
requirement_refs:
- FR-006
tracker_refs: []
planning_base_branch: design/doc-quality-hardening-2245
merge_target_branch: design/doc-quality-hardening-2245
branch_strategy: Planning artifacts for this mission were generated on design/doc-quality-hardening-2245. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doc-quality-hardening-2245 unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
phase: Lane B1
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "42449"
history:
- at: '2026-06-30T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: docs/changelog/CHANGELOG.md
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/changelog/CHANGELOG.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – Repair 5 canonical-CHANGELOG body links

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
- **You must address all feedback** before your work is complete.

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`, ````bash`

---

## Objectives & Success Criteria

Fix exactly five broken body links in `docs/changelog/CHANGELOG.md`. The gate
(`check_dead_body_links`) resolves links **file-relative** — bare repo-root-relative
paths written inside `docs/changelog/CHANGELOG.md` are resolved from
`docs/changelog/`, producing wrong paths. Every broken target must be rewritten as
a `../`-prefixed path that resolves from `docs/changelog/`. No other content changes.

**DoD**: all five links resolve on disk from `docs/changelog/`; root `CHANGELOG.md`
untouched (WP04 owns regeneration); `pytest tests/docs/test_relative_link_fixer.py`
stays green.

---

## Context & Constraints

**Spec**: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/spec.md` (FR-006)
**Plan**: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/plan.md` (IC-02)
**Research**: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/research.md` (R-03)
**Contract**: `kitty-specs/doc-quality-hardening-2245-01KW9AKV/contracts/changelog-sync-contract.md`

**F4 (critical squad finding)**: `EXCLUDE_PREFIXES` currently hides these broken links.
When WP02 removes `docs/changelog/` from `EXCLUDE_PREFIXES`, every bare repo-root-relative
path in the CHANGELOG body becomes a gate failure. This WP must fix them before that flip.

**C-003**: Do not extend `relative_link_fixer.py` here — WP03 edits only
`docs/changelog/CHANGELOG.md`.
**C-004**: Edited prose must pass `tests/architectural/test_no_legacy_terminology.py`.

---

## Branch Strategy

- **Strategy**: coord
- **Planning base branch**: `design/doc-quality-hardening-2245`
- **Merge target branch**: `kitty/mission-doc-quality-hardening-2245-01KW9AKV`

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T009 – Repair the 5 broken body links

- **Purpose**: Rewrite each broken target as a `../`-relative path resolving from
  `docs/changelog/`.

- **Verified broken links and correct replacements**:

  | Current broken target | Correct `../`-relative target | Notes |
  |---|---|---|
  | `docs/development/local-overrides.md` | `../guides/local-overrides.md` | Relocated during Common Docs move |
  | `docs/migration/shared-package-boundary-cutover.md` | `../migration/shared-package-boundary-cutover.md` | Path unchanged; missing `../` prefix |
  | `architecture/2.x/adr/2026-04-25-1-shared-package-boundary.md` | `../adr/3.x/2026-04-25-1-shared-package-boundary.md` | ADR promoted to `docs/adr/3.x/` |
  | `docs/architecture/05_ownership_map.md` | `../architecture/05_ownership_map.md` | Path unchanged; missing `../` prefix |
  | `docs/upgrading-to-0-11-0.md` | *(absent — remove link markup)* | File does not exist; strip `[…](…)` to plain text |

- **Steps**:
  1. Grep to locate each occurrence: `grep -n "local-overrides\|shared-package-boundary\|2026-04-25-1-shared\|05_ownership_map\|upgrading-to-0-11" docs/changelog/CHANGELOG.md`
  2. Edit each occurrence surgically. Do not reflow surrounding prose.
  3. For `docs/upgrading-to-0-11-0.md`: run `find . -name "upgrading-to-0-11-0.md"` first. If found, repoint to the correct `../`-relative path. If absent, strip the link markup and leave the text as plain prose. Check both occurrences (≈ lines 3704 and 3770) — the second may already be plain text; only repair `[…](…)` forms.

- **Files**: `docs/changelog/CHANGELOG.md`
- **Parallel?**: No — T010 depends on T009.
- **Notes**: There are exactly **five broken links** (per FR-006). If you find more or fewer, stop and document the discrepancy.

---

### Subtask T010 – Verify repaired links resolve on disk

- **Purpose**: Confirm no dangling references remain before declaring T009 done.

- **Steps**:
  1. For each repaired link, verify the target exists from the repo root:
     ```bash
     ls docs/guides/local-overrides.md
     ls docs/migration/shared-package-boundary-cutover.md
     ls docs/adr/3.x/2026-04-25-1-shared-package-boundary.md
     ls docs/architecture/05_ownership_map.md
     ```
     Each must exit 0.
  2. Confirm `docs/upgrading-to-0-11-0.md` link markup is removed — no `[…](docs/upgrading-to-0-11-0.md)` remains in the file.
  3. Run the gate in its current scoped mode: `python scripts/docs/relative_link_fixer.py --check` — must exit 0 (no new failures introduced).

- **Files**: `docs/changelog/CHANGELOG.md` (read-only in this subtask)
- **Parallel?**: No — runs after T009.
- **Notes**: The gate currently excludes `docs/changelog/`; the on-disk check here is the only safety net until WP02 flips the scope.

---

## Test Strategy

No new test file for WP03 (documentation-only edit). Run after T009+T010:

```bash
python scripts/docs/relative_link_fixer.py --check          # must exit 0
pytest tests/docs/test_relative_link_fixer.py -q            # must stay green
pytest tests/architectural/test_no_legacy_terminology.py -q # must pass
```

---

## Risks & Mitigations

- **Risk**: Line numbers shift between prompt-write time and implementation.
  **Mitigation**: Always use `grep -n` to locate broken targets; never jump to
  a hardcoded line number.
- **Risk**: `docs/upgrading-to-0-11-0.md` exists under an unexpected path.
  **Mitigation**: Run `find . -name "upgrading-to-0-11-0.md"` before removing the link.
- **Risk**: Long bullet at line ~2120 accidentally reformatted.
  **Mitigation**: Use targeted string-replace edits; do not reflow or re-wrap.

---

## Review Guidance

1. Confirm exactly five link targets changed — diff line count.
2. For each new `../`-relative target: `ls <docs/changelog/../target>` exits 0.
3. Confirm `docs/upgrading-to-0-11-0.md` link markup is stripped (target absent) or repointed (target found).
4. Confirm root `CHANGELOG.md` is not in the diff.
5. `pytest tests/docs/test_relative_link_fixer.py -q` green.
6. `pytest tests/architectural/test_no_legacy_terminology.py -q` green.

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

**Format**: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <brief action>`

**Example**:
```
- 2026-01-12T10:00:00Z – system – Prompt created
- 2026-01-12T10:30:00Z – claude – Implementation complete, ready for review
```

**Why this matters**: The acceptance system reads the LAST entry as current state.
Append only — never prepend or insert in the middle.

**Initial entry**:

- 2026-06-30T00:00:00Z – system – Prompt created.

---

### Updating Status

Use `spec-kitty agent tasks move-task WP03 --to <status>` to change WP status.
- 2026-06-30T17:39:48Z – claude:sonnet:python-pedro:implementer – shell_pid=8739 – Assigned agent via action command
- 2026-06-30T17:45:41Z – claude:sonnet:python-pedro:implementer – shell_pid=8739 – 5 links repaired in docs/changelog/CHANGELOG.md: 3 links on line 2120 (local-overrides, shared-package-boundary-cutover, ADR 2026-04-25-1), 1 on line 2321 (05_ownership_map) — all rewritten to ../-relative; upgrading-to-0-11-0 link markup stripped (file absent). All 4 disk targets verified. Gate + test_relative_link_fixer + terminology guard green.
- 2026-06-30T17:46:06Z – claude:opus:reviewer-renata:reviewer – shell_pid=42449 – Started review via action command
- 2026-06-30T17:49:41Z – user – shell_pid=42449 – Review passed (reviewer-renata): 5 broken CHANGELOG body links repaired (FR-006). 4 ../-relative targets resolve on disk from docs/changelog/; 5th (upgrading-to-0-11-0.md) absent so link markup stripped to plain text. Root CHANGELOG.md untouched (WP04 owns regen). C-003 respected; C-004 terminology guard green. Gate --check exit 0; test_relative_link_fixer + test_no_legacy_terminology green (29 passed). Lane-c sole-owned.
