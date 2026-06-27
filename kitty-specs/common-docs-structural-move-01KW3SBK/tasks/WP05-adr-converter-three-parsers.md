---
work_package_id: WP05
title: ADR converter + 3 parsers (table/bold-inline/dash-bullet) + content-invariance check
dependencies:
- WP03
requirement_refs:
- FR-002
- FR-003
- C-002
- NFR-001
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T027
- T028
- T029
- T030
- T031
- T032
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/adr_converter.py
create_intent:
- scripts/docs/adr_converter.py
- tests/docs/test_adr_converter.py
execution_mode: code_change
owned_files:
- scripts/docs/adr_converter.py
- tests/docs/test_adr_converter.py
role: implementer
tags: []
shell_pid: "1581114"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Build the **ADR converter** that turns a legacy-header ADR into a bare-`status` YAML-frontmatter ADR, with **THREE header parsers** (markdown-table, bold-inline, **dash-bullet**) and a **content-invariance check** (body-minus-header byte-identical). This is the IC-04a tooling slice — the **execution** over all 117 ADRs is WP06. Build the tool + its test here; prove it on representative fixtures of all three dialects.

## Context

`contracts/content-invariance.md` is the authority. **Live census: 70 bold-inline / 46 table / 1 dash-bullet = 117.** The spec's "~12 table / ~34 bold" was wrong and **missed the dash-bullet format entirely** — without a 3rd parser branch, that ADR converts **status-less**, the ratchet (`title`/`status`/`date` required) blocks, and the conversion is stuck. **A 3rd parser branch is REQUIRED.**

**⚠️ The dash-bullet ADR's canonical file is at `architecture/3.x/adr/2026-04-15-2-explicit-empty-charter-selections-remain-empty.md`.** The `architecture/2.x/adr/2026-04-15-2-…` path is a **symlink** into 3.x (back-compat shim) — read the **canonical 3.x real file** for the fixture bytes; do not read through the symlink (and never convert the symlink itself — WP06 dereferences + drops all such shims). architecture/ contains **71 back-compat symlinks** (24 in `2.x/adr/`, 47 in `adrs/`) — WP06 handles them; WP05 just needs the real-file fixture.

**Target frontmatter** (directive `042-common-docs.directive.yaml`, ratchet `ADR_FRONTMATTER_REQUIRED_KEYS = ("title","status","date")`): bare `status` carrying MADR vocabulary (`Proposed`/`Accepted`/`Deprecated`/`Superseded`). `status` is the **sanctioned exception** to the bare-`status` prohibition (pages use `doc_status`; ADRs use `status`).

**Content-invariance method** (false-green-proof):
1. Pre-image: strip the original header block (one of the 3 dialects) + the leading title line; retain the decision body verbatim.
2. Post-image: strip the new YAML frontmatter **by reusing `_inventory.parse_frontmatter`** (do NOT fork a second frontmatter parser).
3. Assert `bytes(pre_body) == bytes(post_body)` — byte-identical, not re-rendered, not normalised.

**Dash-bullet boundary:** the header ends at the last consecutive `- Status:`/`- Date:`/`- Deciders:`-style bullet at the top of the file; the body begins at the first non-bullet, non-blank line after it. Bullets *inside the body* are body, not header.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-002 (preserve all 117), FR-003 (3 parsers + content-invariance + bare `status`), C-002 (no decision-content mutation), NFR-001 (0 lost, 0 content-altered).

## Subtasks

### T027 — Parser 1: markdown-table header
Parse the table dialect (`| Status | Accepted |` style). Extract `title`, `status`, `date` (+ any deciders). Return a structured header + the body-start offset. 46 ADRs use this dialect.

### T028 — Parser 2: bold-inline header
Parse the `**Status:** Accepted` / `**Date:** …` dialect. 70 ADRs use this — the dominant format. Extract the same fields + body-start offset.

### T029 — Parser 3: dash-bullet header (the missed dialect)
Parse the `- Status: …` / `- Date: …` dialect, applying the dash-bullet boundary rule above. This is the 3rd branch the spec missed; without it the conversion is stuck on at least 1 ADR. Add the named fixture (shaped from the **canonical real file** `architecture/3.x/adr/2026-04-15-2-explicit-empty-charter-selections-remain-empty.md` — NOT the `2.x/adr/` symlink) to the test.

### T030 — Frontmatter emitter (bare `status`, MADR vocabulary)
Emit YAML frontmatter with bare `status` (`Proposed`/`Accepted`/`Deprecated`/`Superseded`), `title`, `date`. Do NOT use `doc_status` (that is for pages). Preserve the original decision body verbatim after the frontmatter block. Use `ruamel.yaml` (already vendored) — no new dependency.

### T031 — Content-invariance check (reuse `_inventory.parse_frontmatter`)
Implement `invariant(pre, post)`: strip pre-image header (via the 3 parsers) + title line; strip post-image frontmatter via **`_inventory.parse_frontmatter`** (reused, not forked); assert byte-identity of the remaining bodies. A re-render comparison is a false-green — assert raw bytes.

### T032 — Test the converter on all 3 dialects + invariance
Author `tests/docs/test_adr_converter.py`: a fixture per dialect (table, bold-inline, dash-bullet) → converts to bare-`status` frontmatter + passes the invariance check; a **mutation fixture** (body byte changed) → invariance check goes RED (proves it is not a false-green); a status-less malformed input → parser surfaces a clear error (not a silent status-less emit). Use realistic ADR-shaped fixtures (real dated filenames, real header bytes).

## Surfaces & Loci

| Surface | Role | Notes |
|---------|------|-------|
| `scripts/docs/adr_converter.py` | new | 3 parsers + emitter + invariance check |
| `_inventory.parse_frontmatter` | reused | post-image frontmatter strip (do NOT fork) |
| `scripts/docs/anti_sprawl_ratchet.py` `ADR_FRONTMATTER_REQUIRED_KEYS` | contract | `("title","status","date")` — the bare-`status` keys the emitter must satisfy |
| `tests/docs/test_adr_converter.py` | new | fixture per dialect + mutation-fixture (false-green-proof) |
| `architecture/3.x/adr/2026-04-15-2-explicit-empty-charter-selections-remain-empty.md` | fixture source (**canonical real file**) | the 1 dash-bullet ADR the spec missed; `2.x/adr/` path is a symlink into 3.x |

**Parser census (live):** 70 bold-inline / 46 table / 1 dash-bullet = 117.

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-002 (preserve all 117) | T032 (count guard in WP06) |
| FR-003 (3 parsers + content-invariance + bare `status`) | T027, T028, T029, T030, T031 |
| C-002 (no decision-content mutation) | T031, T032 |
| NFR-001 (0 lost, 0 altered) | T031, T032 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP03 (the move lands the era trees under `docs/`). Parallel-eligible with WP07/WP08/WP09 (disjoint surfaces). WP06 consumes this tool.

## Definition of Done

- [ ] Three parsers (table, bold-inline, **dash-bullet**) each extract `title`/`status`/`date` + a body-start offset.
- [ ] Frontmatter emitter writes **bare `status`** (MADR vocabulary), never `doc_status`, body verbatim.
- [ ] Content-invariance check reuses `_inventory.parse_frontmatter` for the post-image strip and asserts **raw-byte** body identity (not a re-render).
- [ ] `tests/docs/test_adr_converter.py`: a fixture per dialect green; a **mutation fixture RED** (false-green-proof); a malformed input surfaces a clear error.
- [ ] **No reference/runtime break introduced**: this WP only adds a script + test; it does not move or rewrite any ADR (WP06 runs the conversion).
- [ ] `ruff` + `mypy` clean on the new script + test; no new dependency.

## Risks & Reviewer Guidance

- **Reviewer (merge-blocker focus, C-002):** the invariance check must compare **body-minus-header bytes**, not re-rendered output — confirm the mutation fixture goes RED. A false-green here silently mutates decision content across 117 ADRs.
- The **dash-bullet branch** is the one the spec missed — confirm its boundary rule (header bullets vs body bullets) is correct on the named fixture.
- Reusing `_inventory.parse_frontmatter` (not a forked parser) is a contract requirement — a second parser could disagree with the inventory's view and create drift.

## Activity Log

- (populated at implement time)
- 2026-06-27T13:37:46Z – claude:opus:python-pedro:implementer – shell_pid=1421969 – Assigned agent via action command
- 2026-06-27T13:48:35Z – claude:opus:python-pedro:implementer – shell_pid=1421969 – ADR converter: 3 parsers (incl dash-bullet), invariance reuses _inventory.parse_frontmatter, mutation-RED proven, 18 tests, ruff/mypy 0
- 2026-06-27T13:49:32Z – claude:opus:reviewer-renata:reviewer – shell_pid=1449211 – Started review via action command
- 2026-06-27T13:55:12Z – user – shell_pid=1449211 – Moved to planned
- 2026-06-27T13:56:39Z – claude:opus:python-pedro:implementer – shell_pid=1463724 – Started implementation via action command
- 2026-06-27T14:08:51Z – claude:opus:python-pedro:implementer – shell_pid=1463724 – cycle 2: raw-byte mutation test (load-bearing proven), 19 tests, ruff/mypy 0. --force: kitty-specs-on-lane guard (lane code clean; status-chore divergence only)
- 2026-06-27T14:10:58Z – claude:opus:reviewer-renata:reviewer – shell_pid=1482929 – Started review via action command
- 2026-06-27T14:15:28Z – user – shell_pid=1482929 – Cycle-2 re-review APPROVED by reviewer-renata: prior rejection blocker (raw-byte invariance test-pinning gap) is remediated. New test test_whitespace_only_mutation_drives_invariance_red pins raw-byte invariance with a whitespace-only mutation (mutated.split()==converted.split()); proven load-bearing — under a normalized .split() compare probe ONLY this test goes RED (1 failed/18 passed), word-sub test stays green; probe reverted, production unchanged (cycle-2 diff is test-only, 18 insertions). 19 tests pass, ruff/mypy 0.
- 2026-06-27T14:56:23Z – user – shell_pid=1482929 – Moved to planned
- 2026-06-27T14:56:47Z – claude:opus:python-pedro:implementer – shell_pid=1552831 – Started implementation via action command
- 2026-06-27T15:13:59Z – claude:opus:python-pedro:implementer – shell_pid=1552831 – cycle 3: extended converter (5 dialects, status alias table both ambiguous→Superseded, Date-from-filename); dry-run over 188 real ADRs = 0 hard-errors / 0 invariance fails; 39 tests, ruff/mypy 0
- 2026-06-27T15:14:11Z – claude:opus:reviewer-renata:reviewer – shell_pid=1581114 – Started review via action command
- 2026-06-27T15:19:36Z – user – shell_pid=1581114 – Cycle-3 re-review APPROVED. review-cycle-3.md reopen's 4 required extensions all implemented (commit 4afe5040) and independently verified: (1) colon-outside-bold + (2) dash+bold dialects parse correctly; (3) status alias table — derivable qualifieds strip to MADR root, amended/partially-superseded→Superseded explicit+auditable+fail-closed (Ratified hard-errors), body verbatim (C-002); (4) Date-from-filename fallback (real header wins; no-date+no-filename hard-errors). Independent dry-run over 117 real ADRs: 0 hard-errors, 0 invariance fails (Accepted 93/Superseded 11/Proposed 13; 4 README non-ADRs correctly fail-closed). Raw-byte invariance + whitespace-only mutation test intact. 39 tests green, ruff clean, mypy clean.
