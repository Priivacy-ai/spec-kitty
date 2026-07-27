---
work_package_id: WP11
title: Frontmatter backfill TOOLING + the new 50–180 description length gate + related-edge derivation
dependencies:
- WP04
requirement_refs:
- FR-010
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T065
- T066
- T067
- T068
- T069
- T070
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/frontmatter_backfill.py
create_intent:
- scripts/docs/frontmatter_backfill.py
- scripts/docs/description_length_check.py
- tests/docs/test_frontmatter_backfill.py
- tests/docs/test_description_length_gate.py
execution_mode: code_change
owned_files:
- scripts/docs/frontmatter_backfill.py
- scripts/docs/description_length_check.py
- tests/docs/test_frontmatter_backfill.py
- tests/docs/test_description_length_gate.py
role: implementer
tags: []
shell_pid: "1558429"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Build the **frontmatter-backfill tooling**: the `tag → doc_status` mapping + the backfill tool, the **new 50–180 `description` length gate** (none exists today), and the `related`-edge derivation. This is IC-05e-1 — the **tooling**; the per-page authoring of ~580 `description`/`related` values is WP12. **FR-010 is derivation + authoring, NOT a mechanical drift-close** — the inventory has **0** `doc_status`, **0** `description`, **0** `related` (there is nothing to "sync"; it must be authored).

## Context

The plan (IC-05 FR-010 sub-slice) + data-model `Doc page` entity are the authority. The page-lifecycle key is **`doc_status`** (`draft|active|deprecated|superseded`) — distinct from FR-003's bare ADR `status`. **Bare `status` is prohibited for pages** (directive 042; collides with WP-lane status).

- **(a) `tag → doc_status` mapping** — derive each page's `doc_status` from its live `tag` (internal 419 / current 133 / archival 14 / migration 14). Define the table explicitly: e.g. `current → active`, `internal → active|draft` (by signal), `archival → deprecated`, `migration → active`. One-time derivation, not a guess-per-page.
- **(b) `description` length gate** — `scripts/docs/` has only `seo_postprocess.py`, which *emits* but does not *validate* length. **Add a new 50–180 length gate** (`scripts/docs/description_length_check.py`). NFR-003.
- **(c) `related` edges** — derive cross-page `related:` edges from existing in-body links where possible (NFR-004 = 0 dangling, enforced by R2/`related_validator.py`); otherwise flag for authoring (WP12).

**Existing deps only** — `ruamel.yaml` for frontmatter; stdlib. No new dependency.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-010 (backfill `doc_status` + per-page frontmatter), NFR-003 (description length 50–180 + the gate), NFR-004 (related edges resolvable, 0 dangling). Tooling here; authoring in WP12; lockfile regen in WP13.

## Subtasks

### T065 — Define the `tag → doc_status` mapping table
Author the explicit mapping from the live `tag` vocabulary (internal/current/archival/migration) to `doc_status` (`draft|active|deprecated|superseded`). Document the per-tag rule + the `internal → active|draft` disambiguation signal. This is a deterministic derivation, recorded in the tool + a doc comment, not a per-page guess.

### T066 — Build the backfill tool (`frontmatter_backfill.py`)
Author `scripts/docs/frontmatter_backfill.py`: for each page, derive `doc_status` via T065's table from the page's `tag`; carry `updated`/`version_tag`/`divio_type`/`owning_workstream` from the 580-row inventory snapshot; stub `description`/`related` for WP12 authoring (or carry where derivable). The tool is idempotent (re-runnable; generated == committed feeds WP13's lockfile).

### T067 — Build the 50–180 `description` length gate
Author `scripts/docs/description_length_check.py`: validate every page's `description` is present and 50–180 chars (NFR-003). This gate does NOT exist today — it is net-new. Exit non-zero on a missing/out-of-range description. Wire-ready for CI (WP14 flips the rulers; this gate joins the freshness suite).

### T068 — Derive `related` edges from in-body links
Implement the `related`-edge derivation: where a page's in-body Markdown links point at other `docs/` pages, derive `related:` edges (NFR-004 = 0 dangling). Non-derivable edges are flagged for WP12 authoring. The derivation must produce only resolvable edges (a dangling edge fails R2).

### T069 — Test the tooling
Author `tests/docs/test_frontmatter_backfill.py` (the `tag→doc_status` table is correct per tag; the tool is idempotent; carried inventory fields land) and `tests/docs/test_description_length_gate.py` (a 49-char description → RED; a 181-char → RED; a 50–180 → green; a missing description → RED). Use realistic page-shaped fixtures.

### T070 — Verify + suite green
Run both new test files green. Run `ruff`/`mypy` on the two new scripts + tests (zero issues, no new ignores). Confirm the backfill tool does not yet author per-page `description`/`related` (that is WP12) — it provides the deterministic `doc_status` + the gate + the derivation.

## Surfaces & Loci

| Surface | Role | Notes |
|---------|------|-------|
| `scripts/docs/frontmatter_backfill.py` | new | `tag→doc_status` derivation + inventory-field carry + idempotent |
| `scripts/docs/description_length_check.py` | new | **net-new** 50–180 gate (none exists; `seo_postprocess.py` only emits) |
| `scripts/docs/related_validator.py` | reused | R2 — the derivation must produce only resolvable edges |
| `docs/development/3-2-page-inventory.yaml` | read-only | the 580-row snapshot to carry fields from |
| `tests/docs/test_frontmatter_backfill.py`, `test_description_length_gate.py` | new | table correctness + boundary tests |

**`tag → doc_status` table:** `current→active`, `internal→active\|draft` (by signal), `archival→deprecated`, `migration→active`. Live tag counts: internal 419 / current 133 / archival 14 / migration 14.

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-010 (backfill `doc_status` + per-page frontmatter — tooling) | T065, T066 |
| NFR-003 (description 50–180 + the gate) | T067, T069 |
| NFR-004 (related resolvable, 0 dangling) | T068 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP04 (the re-sectioned tree the pages live in). WP12 runs the authoring; WP13 regenerates the lockfile; WP14 flips the gates blocking.

## Definition of Done

- [ ] `tag → doc_status` mapping table defined explicitly (per-tag rule + `internal` disambiguation), recorded in code + comment.
- [ ] `scripts/docs/frontmatter_backfill.py` derives `doc_status`, carries inventory fields, idempotent.
- [ ] `scripts/docs/description_length_check.py` — the **net-new 50–180 length gate** (none existed) — exits non-zero on missing/out-of-range.
- [ ] `related`-edge derivation produces only **resolvable** edges (NFR-004); non-derivable flagged for WP12.
- [ ] Tests green: `tag→doc_status` correctness + idempotence + length-gate boundaries (49/181 RED, 50–180 green).
- [ ] **No reference/runtime break introduced**: tooling only; no per-page content authored (WP12); no lockfile regen (WP13).
- [ ] `ruff` + `mypy` clean; no new dependency.

## Risks & Reviewer Guidance

- **Reviewer (FR-010 framing):** confirm this is treated as **derivation + tooling**, not a mechanical drift-close — the inventory has 0 of these fields; there is nothing to "sync".
- The **length gate is net-new** — confirm it actually validates (the existing `seo_postprocess.py` only emits). Boundary tests (49/181) prove it bites.
- A `related` derivation that emits a dangling edge fails R2 once blocking — the derivation must produce only resolvable edges.

## Activity Log

- (populated at implement time)
- 2026-06-27T14:35:43Z – claude:opus:python-pedro:implementer – shell_pid=1518600 – Assigned agent via action command
- 2026-06-27T14:58:44Z – claude:opus:python-pedro:implementer – shell_pid=1518600 – frontmatter tooling: tag→doc_status table (580 rows), backfill tool, 50-180 length gate (49/181 RED), related derivation (dangling impossible by construction), 20 tests, ruff/mypy 0
- 2026-06-27T14:58:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=1558429 – Started review via action command
- 2026-06-27T15:04:18Z – user – shell_pid=1558429 – Review passed: tag->doc_status sound (current/migration->active, archival->deprecated per directive 042 vocab; internal via current_target; counts sum to 580: internal 419/current 133/archival 14/migration 14), length gate non-vacuous inclusive 50-180 (49/181 RED, 50/180 green, missing/blank RED, --strict exits 1 default 0), related dangling-impossible by construction (only resolvable .md under docs root written; unresolved flagged never emitted), tooling-only (WP11 commit defc39a47 touches only the 4 owned files; no per-page authoring), ruff/mypy --strict 0, 20 tests green. IC verdicts: (a) updated via git log %cs SOUND as fallback (existing frontmatter wins) caveat WP12: git-mv structural move resets committer date to the move commit so prefer authored updated where content-freshness matters; (b) internal/current_target signal is DEGENERATE (current_target is 1:1 with tag==current; 0/419 internal are current targets so ALL 419 internal collapse to draft, active branch never fires on real data) -- accepted as safe conservative tooling default (draft won't publish as active; WP12 refines per-page) but WP12 MUST decide uniform-draft vs a real discriminator (path-based adr/ vs engineering-notes/, or marker); (c) divio key carried as type: CORRECT, matches inventory_lockfile.py _FM_DIVIO_TYPE='type'.
