---
work_package_id: WP07
title: Post-move prose triage (stale architecture/symlink claims)
dependencies: []
requirement_refs:
- C-004
- FR-012
tracker_refs: []
planning_base_branch: design/doc-quality-hardening-2245
merge_target_branch: design/doc-quality-hardening-2245
branch_strategy: Planning artifacts for this mission were generated on design/doc-quality-hardening-2245. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doc-quality-hardening-2245 unless the human explicitly redirects the landing branch.
subtasks:
- T022
- T023
phase: Lane D1
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "73776"
history:
- at: '2026-06-30T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/adr/2.x/README.md
create_intent: []
execution_mode: code_change
model: ''
owned_files:
- docs/adr/1.x/README.md
- docs/adr/2.x/README.md
- docs/adr/3.x/README.md
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Post-move prose triage (stale architecture/symlink claims)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
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

## Objectives & Success Criteria

- Produce a complete per-file disposition table for every grep hit matching stale `architecture/`-path or dropped-symlink prose in the `docs/adr/` README files.
- Correct only the genuinely stale prose — confirmed target: `docs/adr/2.x/README.md:13-17` which incorrectly claims 71 back-compat symlinks still exist at `architecture/2.x/adr/<filename>`. Those symlinks were dropped when the Common Docs structural move (PR #2225) removed the `architecture/` tree entirely.
- Fix any other confirmed-stale README/nav prose found within `owned_files` during triage.
- Leave every legitimately era-correct or exempt-immutable hit untouched with a documented rationale.
- All changes pass `tests/architectural/test_no_legacy_terminology.py` (C-004).

**Success criteria:**

- Disposition table exists in the Activity Log covering all ~27 grep hits with a verdict of `fix`, `leave-era-correct`, or `leave-exempt-immutable`.
- No false stale claim remains in non-exempt README/nav files within `owned_files`.
- `pytest tests/architectural/test_no_legacy_terminology.py` passes with zero issues.
- WP02 (terminal gate-flip, Lane A2) can proceed without any prose blocker in `docs/adr/`.

---

## Context & Constraints

**Mission context:** The Common Docs structural move (#2165, PR #2225) relocated hundreds of documentation files, including 119 ADRs, from `architecture/` into `docs/adr/`. That move dropped 71 back-compat symlinks that some README files claimed would exist. This WP trims the residual stale prose — it is a documentation-correctness task, not a content rewrite.

**Scope boundaries — read carefully before touching anything:**

- **The ~25 historical `architecture/<era>/` prose mentions from issue #2227 are INTENTIONAL provenance and mermaid diagram text, NOT stale errors.** They are OUT OF SCOPE for this triage. Do not rewrite historical body references just because they contain the word `architecture/`.
- **Dated ADR bodies (`docs/adr/**/YYYY-MM-DD-*.md`) are owned by Lane C (WP05/WP06).** Do not edit them — their bodies are byte-invariant under C-002, and any edit outside the sanctioned FR-008 waiver breaks `test_adr_content_invariance.py`.
- **Root `CHANGELOG.md` and `docs/changelog/CHANGELOG.md` are owned by Lane B (WP03/WP04).** Do not touch them.
- **Stale `.codex/` path prose (#1644) is OUT OF SCOPE** unless it co-occurs in a file that also has a dead link being fixed. Do not pursue `.codex/` fixes here.
- **Small out-of-map edits to other README files** (e.g. `docs/adr/1.x/README.md`, `docs/adr/3.x/README.md`) are acceptable if confirmed-stale during T022 triage, with a one-line rationale recorded in the disposition table. The no-overlap rule with Lanes B and C is the real guard, not the `owned_files` list.

**Relevant spec references:**

- FR-012 — triage the ~27 hits; give each a disposition; correct stale ones.
- C-004 — all new prose passes `tests/architectural/test_no_legacy_terminology.py`.
- SC-006 — no stale `architecture/`/dropped-symlink claims remain in non-exempt nav/READMEs.
- plan.md IC-04 and R-F3 — Lane D owns `docs/adr/**/README.md`; Lane C owns dated `docs/adr/**/YYYY-MM-DD-*.md`. Lanes are disjoint by filename pattern.

**Prerequisite:** None — WP07 starts immediately in parallel with WP01, WP03, WP05, WP08.

**Supporting docs:** `kitty-specs/doc-quality-hardening-2245-01KW9AKV/plan.md`, `spec.md` (FR-012, C-004, SC-006).

---

## Branch Strategy

- **Strategy**: flat/single_branch
- **Planning base branch**: design/doc-quality-hardening-2245
- **Merge target branch**: design/doc-quality-hardening-2245

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T022 – Triage stale prose hits → produce per-file disposition table

- **Purpose**: Establish ground truth for which prose hits are genuinely stale versus era-correct or immutable, so T023 fixes only the right targets.
- **Steps**:
  1. Run the following grep to enumerate all candidate hits:
     ```bash
     grep -rn --include="*.md" "architecture/" docs/adr/ | grep -v "YYYY-MM-DD"
     ```
     Also check for symlink-specific wording:
     ```bash
     grep -rn --include="*.md" -i "symlink\|back.compat\|back-compat\|compat.*link" docs/adr/
     ```
  2. For each hit, apply the disposition rule:
     - **`fix`** — the file is a README/nav file (not a dated ADR body), and the prose makes a factual claim that is now false (e.g. "symlinks exist at `architecture/2.x/adr/...`" when they do not).
     - **`leave-era-correct`** — the reference is in a dated ADR body (`YYYY-MM-DD-*.md`) describing the historical state at the time of decision. These are byte-invariant (Lane C scope); do NOT edit.
     - **`leave-exempt-immutable`** — the reference is in `kitty-specs/`, `architecture/` (the old tree, if any remnant exists), or any file not in `docs/adr/` README/nav scope. Record with rationale.
  3. For the ~25 `architecture/<era>/` prose hits from issue #2227: classify them `leave-era-correct` or `leave-exempt-immutable` as appropriate. They are INTENTIONAL provenance and mermaid text — do NOT reclassify them as stale without evidence that the file is a live README making a factual present-tense claim.
  4. Record the full disposition table in the Activity Log at the bottom of this file in Markdown table format:

     | File | Line(s) | Snippet | Disposition | Rationale |
     |------|---------|---------|-------------|-----------|
     | `docs/adr/2.x/README.md` | 13-17 | "back-compat symlinks at the old `architecture/2.x/adr/<filename>` paths…" | fix | Symlinks were dropped in PR #2225; `architecture/` tree no longer exists |
     | … | … | … | … | … |

- **Files**: `docs/adr/1.x/README.md`, `docs/adr/2.x/README.md`, `docs/adr/3.x/README.md` (read-only for triage; may extend to other `docs/adr/` READMEs if discovered).
- **Parallel?**: This subtask runs first within WP07; T023 depends on its output.
- **Notes**: The ~27-hit figure in tasks.md is an estimate from the planning phase. Actual count may differ slightly. Document the real count in the disposition table.

---

### Subtask T023 – Fix confirmed-stale prose: dropped-symlink claim and other README hits

- **Purpose**: Apply only the `fix`-verdicted corrections identified in T022.
- **Steps**:
  1. **Mandatory fix — `docs/adr/2.x/README.md:13-17`**: The current text reads (approximately):

     > This folder is canonical for 2.x decisions … back-compat symlinks at the old `architecture/2.x/adr/<filename>` paths point at the new location so existing references in CHANGELOG entries, test snapshots, and shipped docs continue to resolve.

     This claim is false: the 71 symlinks were not retained when PR #2225 moved the files. The `architecture/` tree no longer exists. Correct the claim. Suggested replacement prose (adapt as fits the surrounding context):

     > This folder is canonical for 2.x decisions … The `architecture/` tree was removed by the Common Docs structural move (PR #2225); existing references in CHANGELOG entries and shipped docs that used the old `architecture/2.x/adr/<filename>` paths will need to be updated to the new `docs/adr/2.x/<filename>` paths.

     Do NOT add content that is not accurate. If a simpler correction fits better (e.g. just removing the false symlink claim and leaving the rest), that is acceptable. The goal is truthfulness, not verbosity.

  2. **Other `fix`-verdict hits**: For each other entry in the T022 disposition table with verdict `fix`, apply a minimal correction to the README or nav file. Record what changed in the Activity Log.

  3. **Do not touch**:
     - Any dated ADR body (`YYYY-MM-DD-*.md`) — these are Lane C's scope and byte-invariant.
     - `CHANGELOG.md` or `docs/changelog/CHANGELOG.md` — these are Lane B's scope.
     - `.codex/` path references unless they co-occur with a confirmed-dead link.

  4. Run the terminology guard after edits:
     ```bash
     pytest tests/architectural/test_no_legacy_terminology.py -q
     ```
     All changes must pass with zero failures.

- **Files**: Primarily `docs/adr/2.x/README.md`; any other README files identified with `fix` verdict in T022.
- **Parallel?**: Runs after T022.
- **Notes**: The edits are small and targeted. If the triage in T022 finds zero additional `fix`-verdict hits beyond the confirmed `docs/adr/2.x/README.md:13-17` case, that is a valid outcome — record it.

---

## Risks & Mitigations

- **Risk: Over-correction** — the ~25 historical `architecture/<era>/` prose mentions from #2227 are intentional provenance. Misclassifying them as `fix` would incorrectly rewrite history.
  - **Mitigation**: Apply the disposition rules from T022 strictly. Only fix present-tense factual claims in README/nav files, not past-tense historical references in ADR bodies or mermaid diagrams.
- **Risk: Editing into Lane C's scope** — dated ADR bodies are byte-invariant; any edit breaks `test_adr_content_invariance.py`.
  - **Mitigation**: Never edit files matching `docs/adr/**/YYYY-MM-DD-*.md`. This WP's `owned_files` is limited to README files.
- **Risk: Terminology guard regression** — prose corrections might inadvertently introduce a forbidden term.
  - **Mitigation**: Run `pytest tests/architectural/test_no_legacy_terminology.py` after every edit batch. Fix before committing.
- **Risk: Incomplete triage** — the ~27 estimate may miss hits in nested subdirectory READMEs.
  - **Mitigation**: Run both grep commands from T022 from the repo root and check all `docs/adr/` subdirectory READMEs, not just the three in `owned_files`.

---

## Review Guidance

Reviewer (`reviewer-renata` profile) should check:

1. **Disposition table is complete**: every grep hit from the T022 commands has a row with a clear verdict and rationale — no row says "TBD".
2. **No dated ADR bodies were touched**: `git diff --name-only` must not include any file matching `docs/adr/**/YYYY-MM-DD-*.md`.
3. **No CHANGELOG files were touched**: `git diff --name-only` must not include `CHANGELOG.md` or `docs/changelog/CHANGELOG.md`.
4. **`docs/adr/2.x/README.md:13-17`**: the dropped-symlink claim is corrected and the replacement text is factually accurate.
5. **Terminology guard passes**: `pytest tests/architectural/test_no_legacy_terminology.py` is green.
6. **No false `fix` verdicts on era-correct content**: the ~25 `architecture/<era>/` provenance mentions from #2227 are NOT touched.
7. **SC-006 satisfied**: no stale `architecture/` or dropped-symlink claim remains in non-exempt non-dated README files.
8. **Regression test present (objective SC-006 backstop)**: a `fast`- or `contract`-marked test exists asserting (a) `docs/adr/2.x/README.md` does NOT contain a present-tense symlink claim co-occurring with `architecture/2.x/adr` (e.g. a regex matching `symlink` within a few lines of `architecture/2.x/adr` in present-tense context), and (b) the count of present-tense `architecture/...` symlink claims across all three owned READMEs (`docs/adr/1.x/README.md`, `docs/adr/2.x/README.md`, `docs/adr/3.x/README.md`) is zero. This converts the one mandatory fix from review-judgment to a pinned regression and bounds the otherwise-unbounded hand-triage. The disposition table requirement from items 1–7 above is preserved; this test is the objective backstop. Note: the live `test_no_dangling_back_compat_symlinks` checks filesystem symlinks, NOT prose claims — it provides zero automated gate against stale prose today.

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

Append entries at the END in chronological order. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`. Timestamp must be current UTC (`date -u "+%Y-%m-%dT%H:%M:%SZ"`). Never prepend or insert in the middle — the acceptance system reads the LAST entry as current state.

**Disposition table** (populate during T022):

| File | Line(s) | Snippet | Disposition | Rationale |
|------|---------|---------|-------------|-----------|
| `docs/adr/2.x/README.md` | 13-17 | back-compat symlinks claim | fix | Symlinks dropped in PR #2225; `architecture/` tree no longer exists |
| *(fill remaining rows during T022)* | | | | |

**Initial entry**:

- 2026-06-30T00:00:00Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP07 --to <status>` to change WP status.
- 2026-06-30T17:40:10Z – claude:sonnet:python-pedro:implementer – shell_pid=8739 – Assigned agent via action command
- 2026-06-30T17:47:43Z – claude:sonnet:python-pedro:implementer – shell_pid=8739 – T022 disposition: 10 dated ADR bodies leave-era-correct (C-002 byte-invariant, Lane C), 2 index.md refs leave-exempt (docs/architecture/ resolves OK, not in owned_files); 4 README hits across 3 owned files → fix (present-tense back-compat symlink claims referencing the now-removed architecture/ tree). T023 fixes applied: removed dropped-symlink claims from docs/adr/1.x/README.md:13, docs/adr/2.x/README.md:14-19, docs/adr/3.x/README.md:11-13; replaced with accurate notice that architecture/ tree was removed in PR #2225. Regression test tests/docs/test_adr_readme_prose.py added (@pytest.mark.fast, 2 tests green). Terminology guard (test_no_legacy_terminology.py) green. Sanctioned out-of-map test file per DoD Review Guidance item 8.
- 2026-06-30T17:52:38Z – claude:opus:reviewer-renata:reviewer – shell_pid=73776 – Started review via action command
- 2026-06-30T17:55:07Z – user – shell_pid=73776 – Review passed: scope limited to 3 ADR READMEs + new regression test; no dated ADR bodies or CHANGELOG touched. False present-tense back-compat-symlink claims corrected in docs/adr/1.x, 2.x, 3.x README.md (architecture/ tree removed by PR #2225). ~25 historical architecture/<era>/ mentions in dated ADR bodies correctly left untouched (incl. the symlink prose in the 2026-06-11-1 dated ADR body) and docs/adr/index.md docs/architecture/ refs left exempt. tests/docs/test_adr_readme_prose.py (@pytest.mark.fast, asserts false claim absent + count==0 across 3 READMEs) passes; test_no_legacy_terminology.py (C-004) passes; ruff clean. Minor non-blocking nit: unused module constant _SYMLINK_NEAR_ARCH_RE in the test.
