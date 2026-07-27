---
work_package_id: WP08
title: Terminology-exemption policy doc
dependencies: []
requirement_refs:
- FR-013
tracker_refs: []
planning_base_branch: design/doc-quality-hardening-2245
merge_target_branch: design/doc-quality-hardening-2245
branch_strategy: Planning artifacts for this mission were generated on design/doc-quality-hardening-2245. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into design/doc-quality-hardening-2245 unless the human explicitly redirects the landing branch.
subtasks:
- T024
- T025
phase: Lane D2
assignee: ''
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "73776"
history:
- at: '2026-06-30T00:00:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: doctrine-daphne
authoritative_surface: docs/development/terminology-exemptions.md
create_intent:
- docs/development/terminology-exemptions.md
execution_mode: code_change
model: ''
owned_files:
- docs/development/terminology-exemptions.md
- tests/contract/test_terminology_guards.py
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP08 – Terminology-exemption policy doc

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `doctrine-daphne`
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

- Write `docs/development/terminology-exemptions.md` documenting the terminology-guard exemption policy that is already coded in `tests/contract/test_terminology_guards.py` at lines 63–152.
- Add a comment in `tests/contract/test_terminology_guards.py` linking to the new policy doc (FR-013 requirement: "linked from the guard test's comment").
- Confirm that the exemptions in the test are intentional — this is a documentation task, not a code-behavior change. Do NOT modify any scan root, scan target, or guard logic unless a review returns with explicit evidence that the policy is wrong.
- Keep the terminology test suite green.

**Success criteria:**

- `docs/development/terminology-exemptions.md` exists, is discoverable (linked from the guard test), and documents all three exemption categories with clear rationale.
- `tests/contract/test_terminology_guards.py` contains a comment pointing to the policy doc.
- `pytest tests/contract/test_terminology_guards.py` passes with zero failures.
- `pytest tests/architectural/test_no_legacy_terminology.py` passes with zero failures (C-004).
- No scan-root, scan-target, or behavioral change in the guard test (only a doc-link comment is added).

---

## Context & Constraints

**Mission context:** The Common Docs structural move (PR #2225) relocated ADRs and archival records into `docs/adr/`, `docs/plans/engineering-notes/`, `docs/plans/initiatives/`, and `docs/plans/notes/`. The terminology-guard test at `tests/contract/test_terminology_guards.py` was updated at that time to exempt these relocated subtrees. The exemptions are implemented and correct — but they are undocumented. A future maintainer seeing `"docs/adr/"` in `FORBIDDEN_SCAN_ROOTS` (line 69) has no in-repo explanation for why. This WP creates that explanation.

**The live exemptions to document (from `test_terminology_guards.py:63-152`):**

1. **`docs/adr/`** (lines 69–74 and 127–137): ADRs are immutable historical decision records. After the common-docs move relocated them from the previously-unscanned `architecture/` tree, their byte-invariant bodies legitimately carry era-correct wording (e.g. `--feature`, main-centric workflow language). They must not be scanned.
2. **`docs/changelog/CHANGELOG.md` — Unreleased section only** (lines 139–151): Both CHANGELOG files are scanned, but only the portion above the first `## [x.y.z]` version heading. Historical version sections legitimately carry era-correct terminology and must not be flagged.
3. **`docs/plans/engineering-notes/`, `docs/plans/initiatives/`, `docs/plans/notes/`** (lines 75–83 and 127–137): These are archival records of completed initiative designs and historical engineering notes relocated from the unscanned `architecture/` tree. They are retained for provenance but are not live first-party docs. The active `docs/plans/*.md` planning pages stay scanned.

**Scope boundary:** This WP owns `docs/development/terminology-exemptions.md` (create) and `tests/contract/test_terminology_guards.py` (add comment only). Lane A's FR-003 reads the exemption policy but does not write here. Lane D (this WP) is the sole owner of any edit to `test_terminology_guards.py`.

**Marker/shard discipline (from plan.md):** `tests/contract/test_terminology_guards.py` is marked `contract + fast`. The new policy doc is a Markdown file — no marker needed.

**Relevant spec references:**

- FR-013 — confirm and document the exemption policy; write to a named file; link from the guard test.
- C-004 — all new prose passes `tests/architectural/test_no_legacy_terminology.py`.
- SC-006 — terminology-exemption policy is documented and linked.
- plan.md IC-04 — Lane D owns `test_terminology_guards.py`; Lane A's FR-003 reads it read-only.

**Prerequisite:** None — WP08 starts immediately in parallel with WP01, WP03, WP05, WP07.

**Supporting docs:** `kitty-specs/doc-quality-hardening-2245-01KW9AKV/plan.md`, `spec.md` (FR-013, C-004, SC-006), `tests/contract/test_terminology_guards.py`.

---

## Branch Strategy

- **Strategy**: flat/single_branch
- **Planning base branch**: design/doc-quality-hardening-2245
- **Merge target branch**: design/doc-quality-hardening-2245

> These fields are populated automatically by `spec-kitty agent mission tasks`.
> Do NOT change them manually unless you are certain the branch topology has changed.

---

## Subtasks & Detailed Guidance

### Subtask T024 – Write docs/development/terminology-exemptions.md

- **Purpose**: Create the single in-repo home for the terminology-guard exemption policy so maintainers understand why certain paths are excluded from the scan and what the intended invariants are.
- **Steps**:
  1. Read `tests/contract/test_terminology_guards.py` lines 1–152 in full before writing. The policy doc must accurately reflect what the code does, not what you expect it to do.
  2. Create `docs/development/terminology-exemptions.md`. Required sections: an introduction sentence linking it to `tests/contract/test_terminology_guards.py`, then one section per exemption category, then a "What stays scanned" section, then a brief "Changing an exemption" guidance.

  3. Key content requirements:
     - Each exemption entry must explain **why** (historical/immutable nature, era-correct wording, archival vs live), not just **what** is exempt.
     - The Unreleased-only CHANGELOG handling must be explained: historical version sections carry era-correct terminology; only the `[Unreleased]` section is scanned.
     - A "What stays scanned" section prevents the reader from concluding that all of `docs/` is exempt — it isn't. The active `docs/plans/*.md` pages, `docs/api/`, `docs/guides/`, etc. remain live first-party surfaces that are scanned.
     - A brief "Changing an exemption" section notes that both the doc and the test must be kept in sync.
  4. Run the terminology guard on the new file itself:
     ```bash
     pytest tests/architectural/test_no_legacy_terminology.py -q
     ```
     The new file lives in `docs/development/`, which is a live scanned surface. Do not write any forbidden terminology in the policy doc body itself.

- **Files**: `docs/development/terminology-exemptions.md` (CREATE — listed in `create_intent`).
- **Parallel?**: T024 runs first within WP08; T025 depends on the file existing.
- **Notes**: This is a documentation-and-confirmation task. Do not speculate about what the policy should be — document what `test_terminology_guards.py` actually implements. If you discover an exemption in the test that appears wrong, note it in the Activity Log and flag it for review rather than silently adjusting the policy doc to cover it up.

---

### Subtask T025 – Link policy doc from test_terminology_guards.py

- **Purpose**: Satisfy FR-013's "linked from the guard test's comment" requirement so readers of the test can immediately find the policy rationale without searching.
- **Steps**:
  1. Open `tests/contract/test_terminology_guards.py`. Identify the module-level docstring (lines 1–14) and the `FORBIDDEN_SCAN_ROOTS` constant definition (around lines 63–83).
  2. Add a doc-link comment. The best location is a single line at the top of `FORBIDDEN_SCAN_ROOTS` or appended to the module docstring. For example, after the existing module docstring closing `"""` add:

     ```python
     # Exemption policy: docs/development/terminology-exemptions.md
     ```

     Or, if the `FORBIDDEN_SCAN_ROOTS` constant has a leading comment block, add the link there. Use whichever location makes the connection clearest to a reader of the test.
  3. The comment must be a comment, not a code change. Do NOT:
     - Add, remove, or reorder entries in `FORBIDDEN_SCAN_ROOTS`.
     - Modify `_live_doc_scan_targets()` or any scan logic.
     - Change `AGENT_DOC_GLOBS`, `DOCTRINE_SKILL_GLOBS`, or `CLI_COMMAND_GLOBS`.
     - Alter any `FORBIDDEN_SCAN_ROOTS` entry content.
  4. Run the full contract+fast suite to confirm nothing broke:
     ```bash
     pytest tests/contract/test_terminology_guards.py -q
     ```
  5. Also run the broader terminology gate:
     ```bash
     pytest tests/architectural/test_no_legacy_terminology.py -q
     ```

- **Files**: `tests/contract/test_terminology_guards.py` (add comment only — no logic change).
- **Parallel?**: Runs after T024 (the file must exist before it can be linked).
- **Notes**: The `test_grep_guards_do_not_scan_historical_artifacts` test at line 468 asserts that `FORBIDDEN_SCAN_ROOTS` entries are not embedded in `AGENT_DOC_GLOBS`. A comment line does not affect that test. Confirm by running the suite.

---

## Risks & Mitigations

- **Risk: Accidentally modifying scan-root behavior** — any change to `FORBIDDEN_SCAN_ROOTS`, `_live_doc_scan_targets()`, or the glob constants changes what the guard scans and may red-or-green-wash other WPs' work.
  - **Mitigation**: T025 adds exactly one comment line. Diff carefully before committing. Run `pytest tests/contract/test_terminology_guards.py` and confirm all existing tests remain green.
- **Risk: Policy doc uses forbidden terminology** — the new file lives in `docs/development/`, a scanned live surface. Writing e.g. `--feature` or `--mission-run` as a live usage example would fail the very test this WP supports.
  - **Mitigation**: Use backtick-quoted examples and write in the past tense or passive voice when referencing removed CLI flags. Run `pytest tests/architectural/test_no_legacy_terminology.py` after writing the doc.
- **Risk: Incomplete policy coverage** — if the doc omits an exemption that exists in the test, a future maintainer may re-introduce a scan that was intentionally blocked.
  - **Mitigation**: Read `test_terminology_guards.py` lines 1–152 before writing. Cross-check every entry in `FORBIDDEN_SCAN_ROOTS` and every `startswith(...)` clause in `_live_doc_scan_targets()` against the policy doc.
- **Risk: Under-scoped "what stays scanned" section** — omitting this makes the doc feel like a blanket `docs/` exemption.
  - **Mitigation**: Explicitly enumerate the active live surfaces that are scanned (e.g. `docs/api/`, `docs/guides/`, `docs/development/`, `docs/plans/*.md`).

---

## Review Guidance

Reviewer (`reviewer-renata` profile) should check:

1. **Policy doc exists** at `docs/development/terminology-exemptions.md` and is non-trivial (not a stub).
2. **All three exemption categories are covered**: `docs/adr/`, CHANGELOG Unreleased-only, and `docs/plans/{engineering-notes,initiatives,notes}/`.
3. **Each exemption has a rationale** — not just "this is exempt" but "this is exempt because it is byte-invariant ADR content relocated from the unscanned architecture/ tree."
4. **A "What stays scanned" section exists** and names concrete live surfaces.
5. **Guard test unchanged in behavior**: `git diff tests/contract/test_terminology_guards.py` shows only a single comment line added. No constant, no logic, no glob is modified.
6. **Guard test references the policy doc**: the comment is present and points to the correct path.
7. **Both test suites pass**:
   ```bash
   pytest tests/contract/test_terminology_guards.py -q
   pytest tests/architectural/test_no_legacy_terminology.py -q
   ```
8. **SC-006 satisfied**: policy file exists and is linked from the guard test.
9. **No scan-root change**: the reviewer should explicitly verify `FORBIDDEN_SCAN_ROOTS` is byte-for-byte identical to the base branch version except for any comment addition.
10. **Machine-check for "documented + linked" (objective backstop)**: a `fast`-marked test in `tests/contract/test_terminology_guards.py` (WP08 owns this file) asserts all three conditions: (a) `docs/development/terminology-exemptions.md` exists on the filesystem, (b) the path `docs/development/terminology-exemptions.md` appears as a literal string reference inside `tests/contract/test_terminology_guards.py` itself, and (c) `docs/development/terminology-exemptions.md` contains all three exemption tokens — `docs/adr/`, `docs/plans/engineering-notes/` (or the plans subdirs), and `Unreleased`. This converts "policy documented + linked" from review judgment to a pinned machine check.

---

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

Append entries at the END in chronological order. Format: `- YYYY-MM-DDTHH:MM:SSZ – <agent_id> – <action>`. Timestamp must be current UTC (`date -u "+%Y-%m-%dT%H:%M:%SZ"`). Never prepend or insert in the middle — the acceptance system reads the LAST entry as current state.

**Initial entry**:

- 2026-06-30T00:00:00Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task WP08 --to <status>` to change WP status.
- 2026-06-30T17:40:17Z – claude:sonnet:python-pedro:implementer – shell_pid=8739 – Assigned agent via action command
- 2026-06-30T17:50:27Z – claude:sonnet:python-pedro:implementer – shell_pid=8739 – handoff: policy doc written (docs/development/terminology-exemptions.md), guard-test link added above FORBIDDEN_SCAN_ROOTS, verification test green (16 contract + 3 arch = 19 passed), terminology guard green, ruff + mypy exit 0, pre-existing missing type annotations fixed as campsite
- 2026-06-30T17:52:42Z – claude:opus:reviewer-renata:reviewer – shell_pid=73776 – Started review via action command
- 2026-06-30T17:55:59Z – user – shell_pid=73776 – Review passed: policy doc docs/development/terminology-exemptions.md is substantive (covers all 3 exemptions — docs/adr/ immutability, Unreleased-only CHANGELOG, docs/plans/{engineering-notes,initiatives,notes}/ archival — each with rationale, plus 'what stays scanned' narrowness invariant + update guidance); guard test links it via comment above FORBIDDEN_SCAN_ROOTS; new @pytest.mark.fast verification test asserts existence+path-link+3 tokens. FORBIDDEN_SCAN_ROOTS and _live_doc_scan_targets byte-identical to base (NO scan-root behavior change). 13 return-type annotations are pure typing (mypy clean, exit 0). contract guards 16 passed; test_no_legacy_terminology 3 passed (C-004). FR-013/SC-006 met.
