---
work_package_id: WP01
title: Record the D-5 reversal ADR
dependencies: []
requirement_refs:
- C-005
- FR-001
planning_base_branch: feat/team-kitty-launch-defaults
merge_target_branch: feat/team-kitty-launch-defaults
branch_strategy: Planning artifacts for this mission were generated on feat/team-kitty-launch-defaults. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/team-kitty-launch-defaults unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 0 - Governance
history:
- at: '2026-09-07T10:00:36Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: architect-alphonso
authoritative_surface: docs/adr/3.x/
create_intent:
- docs/adr/3.x/2026-09-07-1-packaged-hosted-target-default.md
execution_mode: code_change
model: ''
owned_files:
- docs/adr/3.x/2026-09-07-1-packaged-hosted-target-default.md
- docs/adr/3.x/README.md
- docs/adr/3.x/index.md
- docs/architecture/launch-readiness-future.md
- docs/architecture/index.md
role: implementer
tags: []
task_type: implement
tracker_refs: []
---

# Work Package Prompt: WP01 – Record the D-5 reversal ADR

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter (or any user-defined profile), and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `architect-alphonso`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## ⚠️ IMPORTANT: Review Feedback

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check the `review_ref` field in the event log (via `spec-kitty agent tasks status` or the Activity Log below).
- **You must address all feedback** before your work is complete. Feedback items are your implementation TODO list.
- **Report progress**: As you address each feedback item, update the Activity Log explaining what you changed.

---

## Review Feedback

*[If this WP was returned from review, the reviewer feedback reference appears in the Activity Log below or in the status event log.]*

---

## Markdown Formatting

Wrap HTML/XML tags in backticks: `` `<div>` ``, `` `<script>` ``
Use language identifiers in code blocks: ````python`,````bash`

---

## Read Before Anything Else

- `docs/context/team-kitty.md` — the hosted model. "Sync" is a retired transport; the live thing is Zeitgeist. Never phrase code, docs, tests, or commit messages in sync vocabulary.
- `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/spec.md`, `plan.md` (Implementation Concern Map), `research.md`, `data-model.md`, `contracts/*.md`, `occurrence_map.yaml`.
- `.kittify/charter/charter.md` §Quality standing orders: red-first through the pre-existing entry point (DIRECTIVE_041), campsite-clean the surfaces you touch first, canonical sources only, terminology canon.
- Test policy in `CLAUDE.md`: `make test-fast` baseline plus the test files of every module you touch; `tests/architectural/` in full when you touch `core/env.py`, `tests/conftest.py`, or any registry.

## Objectives & Success Criteria

- An accepted ADR exists that authorizes a packaged hosted target for the CLI, states the precedence and provenance contract, and explains why decision D-5 ("no hardcoded hosted domain fallback") no longer applies.
- The ADR is indexed and passes every docs gate; the "coming soon" launch-readiness page is superseded and points at the live model.
- WP02 may not start until this WP is approved (C-005).

## Context & Constraints

- D-5 was scoped to the *hosted-SaaS opt-in gate* (PR #3249, `src/specify_cli/auth/config.py` module docstring). That gate is being deleted (WP04); the SaaS PRD `docs/prds/go-to-market-team-kitty-adoption-prompting.md` (in the spec-kitty-saas repo) names the packaged default as an open decision that "needs its own record if chosen". The operator chose it (Decision Moments in `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/decisions/`).
- Precedence and provenance are fixed by `contracts/target-resolution.md`: env `SPEC_KITTY_SAAS_URL` > `config.toml [team_kitty] server_url` > packaged default `https://team.spec-kitty.ai`; env-vs-config disagreement fails closed; the packaged default is "no opinion" and never a party to a disagreement; `[sync].server_url` is removed with no alias.
- ADR conventions: `docs/adr/3.x/README.md` (file naming `YYYY-MM-DD-N-slug.md`, sections, index registration). Read two recent records first, e.g. `docs/adr/3.x/2026-09-06-1-convergence-retirement-and-client-repo-inversion.md`.
- Docs gates: description 50–180 characters, `updated:` date, Divio `type`, audience path from `docs/context/audience/`; `tests/docs/` enforces them.

## Subtasks & Detailed Guidance

### Subtask T001 – Write the ADR

- **Purpose**: Record the architectural decision before any code changes it (DIRECTIVE_003).
- **Steps**:
  1. Create `docs/adr/3.x/2026-09-07-1-packaged-hosted-target-default.md` following the README template: Context and Problem Statement (launch gate #1621, the deleted opt-in gate, the SaaS PRD's open question), Decision Drivers (out-of-the-box sign-in, developer setups pointing at the dev host, no split-brain regressions, honest vocabulary), Considered Options (keep D-5 and require setup; packaged default with env > config > default; packaged default with env only), Decision Outcome (option 2), Consequences (positive: zero-setup launch, visible provenance; negative: a hardcoded production host in the wheel, mitigated by the env override and the provenance line), Confirmation (contracts/acceptance.md A2/A3), Related Decisions (D-5 in `auth/config.py` docstring and PR #3249; the convergence ADR; issue #3980).
  2. State explicitly: "This record supersedes the D-5 opt-in-gate rationale. `[sync].server_url` is not read; there is no alias and no deprecation period."
  3. Frontmatter per the README (title, description within 50–180 chars, `updated: '2026-09-07'`, status Accepted, `type: explanation` if the README asks for a Divio type, audience `docs/context/audience/internal/system-architect.md`).
- **Files**: `docs/adr/3.x/2026-09-07-1-packaged-hosted-target-default.md` (new, ~90–140 lines).
- **Parallel?**: No.
- **Notes**: Cite the three repo heads named in `research.md`; do not paste code.

### Subtask T002 – Register the ADR

- **Purpose**: An unindexed ADR is invisible to the docs site and to `tests/docs/test_adr_*`.
- **Steps**: Add the record to `docs/adr/3.x/README.md` and `docs/adr/3.x/index.md` in the same position and format as the two most recent entries; keep alphabetical/chronological order as those files do. Run `PWHEADLESS=1 .venv/bin/python -m pytest tests/docs/test_adr_content_invariance.py tests/docs/test_adr_readme_prose.py tests/docs/test_adr_converter.py -q`.
- **Files**: `docs/adr/3.x/README.md`, `docs/adr/3.x/index.md`.
- **Parallel?**: No (after T001).

### Subtask T003 – Supersede the "coming soon" page

- **Purpose**: `docs/architecture/launch-readiness-future.md` says launch behavior "is not in effect today" and describes the flag-driven world; #1621 names it explicitly.
- **Steps**:
  1. Add a superseded banner immediately after the frontmatter: this page described pre-launch intent; the launch defaults are now specified by mission `team-kitty-launch-defaults-01M1XJ4Y` and the ADR from T001; the live hosted model is `docs/context/team-kitty.md`. Set `doc_status: deprecated` and bump `updated`.
  2. Retarget its entry in `docs/architecture/index.md` to say it is a deprecated historical record and link the context page.
  3. Do not delete the page (history), and do not rewrite its body.
- **Files**: `docs/architecture/launch-readiness-future.md`, `docs/architecture/index.md`.
- **Parallel?**: Yes.

### Subtask T004 – Run the docs gates

- **Purpose**: Prove the pages pass before review.
- **Steps**: Run `PWHEADLESS=1 .venv/bin/python -m pytest tests/docs/test_docs_seo.py tests/docs/test_description_length_gate.py tests/docs/test_docs_index_freshness.py -q` and fix any finding on your files. `docs/development/3-2-docs-retrieval-index.yaml` is a derived artifact owned by WP08: if the freshness test reds only because the index lacks your pages, regenerate it with `PYTHONPATH=. .venv/bin/python scripts/docs/docs_index.py --write` and record the out-of-map edit with a one-line rationale in the Activity Log (ownership leeway; the file merges trivially).
- **Files**: none new.
- **Parallel?**: No.

## Test Strategy

- `tests/docs/` subset above; `tests/architectural/test_no_legacy_terminology.py` (the ADR must not use "ceremony" or "status-writing").

## Risks & Mitigations

- Writing the ADR as if D-5 were wrong: it was right for its time; say why the premise changed (the opt-in gate is gone, the product launches hosted-first).
- Description-length gate: count characters before committing.

## Review Guidance

- The ADR names precedence, provenance, the removed `[sync]` key, and the no-alias decision verbatim from `contracts/target-resolution.md`.
- Indexes updated in both files; deprecated page carries the banner and still renders.

## Branch Strategy

- **Strategy**: {branch_strategy}
- **Planning base branch**: {planning_base_branch}
- **Merge target branch**: {merge_target_branch}

> These fields are populated automatically by `spec-kitty agent mission finalize-tasks`. Execution worktrees are allocated per computed lane from `lanes.json`; enter the workspace `spec-kitty agent action implement WP01 --agent <name>` resolves for you and never reconstruct the path.

## Working Rules

- Commit the RED test(s) first, then the fix, as separate commits; name the entry point in the commit message.
- Stay inside `owned_files`; an out-of-map edit needs a one-line rationale in the Activity Log and must not touch another WP's owned file.
- Never edit `kitty-specs/**` (other than this mission's own artifacts when a WP says so), `kitty-ops/**`, `docs/adr/**` (accepted records), `docs/archive/**`, `docs/changelog/**` — the occurrence map marks them `do_not_change`.
- No `# noqa`, no `# type: ignore`, no baseline re-freeze. `ruff check`, `ruff format --check`, and `mypy` on every changed source file must be clean.
- Report test commands and counts in the Activity Log. A failure you did not cause is classified per the baseline-red gotcha in `CLAUDE.md`, never "fixed" by weakening a gate.
- Move to review with `spec-kitty agent tasks move-task WP01 --to for_review`, from the workspace the implement command gave you.

## Activity Log

> **CRITICAL**: Activity log entries MUST be in chronological order (oldest first, newest last).

### How to Add Activity Log Entries

1. Scroll to the bottom of this Activity Log section
2. **APPEND the new entry at the END** (do NOT prepend or insert in middle)
3. Use exact format: `- YYYY-MM-DDTHH:MM:SSZ – agent_id – <action>`
4. Timestamp MUST be current time in UTC (check with `date -u "+%Y-%m-%dT%H:%M:%SZ"`)
5. Agent ID should identify who made the change (claude-sonnet-4-5, codex, etc.)

**Initial entry**:

- 2026-09-07T10:00:36Z – system – Prompt created.

---

### Updating Status

Status is managed via `status.events.jsonl`. Use `spec-kitty agent tasks move-task <WPID> --to <status>` to change WP status.
