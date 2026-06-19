---
work_package_id: WP01
title: Reproducible untrusted→FS sink audit (read-only inventory)
dependencies: []
requirement_refs:
- FR-003
- FR-004
tracker_refs: []
planning_base_branch: automation/sonar-security-20260619
merge_target_branch: automation/sonar-security-20260619
branch_strategy: Planning artifacts for this mission were generated on automation/sonar-security-20260619. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into automation/sonar-security-20260619 unless the human explicitly redirects the landing branch.
subtasks:
- T001
- T002
- T003
- T004
- T005
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1204819"
history:
- at: '2026-06-19T12:26:42Z'
  actor: claude
  note: WP authored from plan IC-02 (FR-004/FR-003).
agent_profile: python-pedro
authoritative_surface: tests/architectural/untrusted_path_audit/
create_intent:
- tests/architectural/untrusted_path_audit/audit.py
- tests/architectural/untrusted_path_audit/RULESET.md
- tests/architectural/untrusted_path_audit/inventory.md
- tests/architectural/untrusted_path_audit/audited-surfaces.md
execution_mode: code_change
model: claude-opus-4-8
owned_files:
- tests/architectural/untrusted_path_audit/audit.py
- tests/architectural/untrusted_path_audit/RULESET.md
- tests/architectural/untrusted_path_audit/inventory.md
- tests/architectural/untrusted_path_audit/audited-surfaces.md
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your assigned agent profile so your identity,
governance scope, and boundaries are active for this work package:

- Run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it).
- Acknowledge the profile's initialization declaration before proceeding.

## Objective

Produce a **reproducible** audit that enumerates every untrusted-segment→filesystem
sink in `src/specify_cli`, each tagged with exactly one disposition. This is a
WP that adds only audit tooling under `tests/architectural/untrusted_path_audit/`
(no changes to `src/`). Its inventory is the input to WP02, WP03, and WP04.
(IC-02; FR-004, FR-003)

## Context

- Untrusted path segments (`mission_slug`, `feature_slug`, `wp_id`, and anything
  read from `status.events.jsonl` / `meta.json` / frontmatter / CLI args) must
  pass the canonical seam before any FS sink. PR #2036 closed several; the squad
  review found more (e.g. the `meta.json` write-path bypass — see WP02).
- Canonical seam: `assert_safe_path_segment` & `safe_mission_slug` in
  `src/specify_cli/core/paths.py`; `ensure_within_any` in
  `src/specify_cli/core/utils.py`.
- Pre-identified candidates (from the plan; NOT exhaustive): `events/decision_log.py:99`,
  `coordination/surface_resolver.py:433-434`, `missions/_read_path_resolver.py:438`,
  `dossier/drift_detector.py:211,233`, `migration/mission_state.py:1053`,
  `review/cycle.py:225`, `review/arbiter.py:387,483,520`,
  `post_merge/review_artifact_consistency.py:59`, plus the already-known
  `status/store.py`, `status/views.py`, `status/lifecycle.py`.

## Subtasks

### T001 — Define + commit the reproducible audit ruleset
- Write, under `tests/architectural/untrusted_path_audit/`, an audit ruleset that a
  reviewer can re-run. It must record:
  - **Seed-set** of untrusted source symbols/fields (`mission_slug`, `feature_slug`,
    `wp_id`, `snapshot.mission_slug`, `meta.get("mission_slug")`, event-record reads, CLI args).
  - **Sink predicate**: `open`/`read_text`/`read_bytes`/`write_text`/`write_bytes`/
    `mkdir`/`shutil.copy|move|rmtree`/`unlink` and `Path(...) / <segment>` joins.
- Implement as a small committed script (`untrusted_path_audit/audit.py` using `ast`)
  with the ruleset documented in `untrusted_path_audit/RULESET.md`. The script must
  make the count machine-checkable (T004). Keep it dependency-light and ruff/mypy-clean.
  (Use a non-`test_` filename so pytest does not collect it as a test.)
- The matcher MUST follow at least **one hop of local-variable aliasing**: a seed
  segment assigned to a local then joined to a path (`slug = meta.get("mission_slug"); ... root / slug`)
  counts as a sink — not only inline literal `Path(...) / mission_slug` joins.
- `RULESET.md` MUST include a "known false-negative classes" section stating exactly
  what the ruleset does NOT trace (e.g. cross-function flow), so the reviewer judges
  residual risk rather than assuming zero.

### T002 — Run the audit; enumerate every sink
- Execute the ruleset over `src/specify_cli`. Capture every matching call site as a
  row: `file:line | untrusted source | sink op`.
- Include the pre-identified candidates; do not assume the list is complete — let the
  ruleset surface others.

### T003 — Classify each sink with a disposition
- For every row assign exactly one disposition:
  - `routed-through-seam` — already passes `assert_safe_path_segment`/`safe_mission_slug`/`ensure_within_any` (cite the seam call).
  - `unreachable` — the call chain cannot carry an untrusted segment (name the chain/why).
  - `trusted-source` — the segment provably originates from `feature_dir.name` or another derived/trusted value.
- **Named-untrusted rule**: a segment that IS `mission_slug`, `feature_slug`, or `wp_id` (spec Domain Language) may **never** be classified `trusted-source` — it is untrusted by definition. Such a row is either `routed-through-seam` (cite the seam) or `unreachable` (cite the chain). Misclassifying one is an SC-003 failure.
- Rows needing a NEW fix are those currently lacking a seam call but reachable with an untrusted segment → mark `routed-through-seam (TODO)` and route to WP02 (status/) or WP03 (other packages).

### T004 — Emit the audit record with a completeness check
- Write `untrusted_path_audit/inventory.md` (the table). The script MUST assert BOTH:
  1. **Count consistency**: emitted row count == inventory row count (no manually dropped rows); a row with no disposition fails (SC-003).
  2. **Known-candidate presence (anti-undercount tripwire)**: the inventory MUST contain a row for every pre-named candidate — `events/decision_log.py`, `coordination/surface_resolver.py`, `missions/_read_path_resolver.py`, `dossier/drift_detector.py`, `migration/mission_state.py`, `review/cycle.py`, `review/arbiter.py`, `post_merge/review_artifact_consistency.py`, `status/store.py`, `status/views.py`, `status/lifecycle.py`, `aggregate.py:_find_meta_path`, AND a row for the FR-009 `mission_metadata.py` `meta.json` slug source tagged `routed-through-seam (TODO)`. The script self-test FAILS if any is absent. (Defeats a thin/circular audit.)
- **Anti-overfit check**: adding one new untrusted source symbol to the seed-set and re-running MUST surface its sinks — prove the ruleset is general, not hard-coded to the known list.

### T005 — Document aggregate.py + hand off
- Record that `status/aggregate.py._validate_mission_slug` already raises
  `InvalidMissionSlug` (grammar guard), and disposition its composed-path reads
  (`_find_meta_path` glob, etc.) — fix-needed vs trusted (FR-003).
- Produce the **audited-surface inventory** (the list WP04's guard anchors on) as a
  stable artifact (`untrusted_path_audit/audited-surfaces.md`, or a machine-readable
  list the WP04 guard can import).

## Branch Strategy

Planning/base and merge target are both `automation/sonar-security-20260619` (this
mission rides PR #2036; it is flattened — no coordination branch). Execution
worktrees are allocated per computed lane from `lanes.json` at implement time.

## Definition of Done

- [ ] Ruleset + script committed under `tests/architectural/untrusted_path_audit/`; re-running reproduces the same inventory.
- [ ] Every sink row carries exactly one disposition with rationale (SC-003); no named untrusted source (`mission_slug`/`feature_slug`/`wp_id`) is `trusted-source`.
- [ ] Emitted count == inventory rows (machine-checked) AND every known candidate + the FR-009 `meta.json` row is present (machine-asserted).
- [ ] aggregate.py raise-guard documented; composed-path reads dispositioned (FR-003).
- [ ] Audited-surface inventory produced for WP04.
- [ ] No `src/` production code modified (audit tooling only).

## Risks / Reviewer guidance

- **Risk**: false positives (trusted `feature_dir.name` mistaken as untrusted) — the
  disposition step must distinguish source provenance, not just pattern-match the sink.
- **Reviewer**: re-run the committed ruleset; confirm the count check; spot-check 3
  dispositions against the code; confirm the `meta.json` write-path bypass (WP02/FR-009)
  appears as a `routed-through-seam (TODO)` row.

## Activity Log

- 2026-06-19T12:53:53Z – claude:opus:python-pedro:implementer – shell_pid=1161318 – Assigned agent via action command
- 2026-06-19T13:06:26Z – user – shell_pid=1161318 – WP01 audit tooling complete; advancing through valid lane chain
- 2026-06-19T13:06:28Z – user – shell_pid=1161318 – WP01 audit tooling complete; advancing through valid lane chain
- 2026-06-19T13:07:01Z – claude:opus:python-pedro:implementer – shell_pid=1161318 – Audit tooling complete (committed 102f98ec9); ruff/mypy/audit gates green. --force: lone blocker is an untracked WP05 artifact in the planning repo, not WP01-owned.
- 2026-06-19T13:07:28Z – claude:opus:python-pedro:implementer – shell_pid=1161318 – Audit tooling complete (102f98ec9); ruff/mypy/audit gates green; lone blocker is foreign WP05 artifact
- 2026-06-19T13:09:31Z – claude:opus:python-pedro:implementer – shell_pid=1161318 – Flattened mission: kitty-specs status lives on planning branch by design; kitty-specs-on-lane guard is a known false-positive here (#1716). WP01 impl complete on lane-a 102f98ec9.
- 2026-06-19T13:09:33Z – claude:opus:reviewer-renata:reviewer – shell_pid=1204819 – Started review via action command
- 2026-06-19T13:13:46Z – user – shell_pid=1204819 – Review passed (reviewer-renata). --force: flattened-mission kitty-specs-on-lane guard false-positive (#1716) -- only auto-committed status.events.jsonl/status.json flagged, not WP01 audit artifacts. Independent audit.py re-run: EXIT 0 'AUDIT OK: 35 inventory rows (34 AST-discovered); TODO(fix)=13 safe=10 trusted=4 unreachable=8'. Tripwire mutations all bite: del events/decision_log.py:99->EXIT1 undercount; del FR-009 mission_metadata.py:328->EXIT1; flip store.py:184->EXIT1 SC-003. Tree clean after revert. One-hop aliasing verified (synthetic + real migration/mission_state.py:1049). Spot-checked dispositions vs src/: FR-009 mission_metadata.py routed-through-seam(TODO); views.py:266 TODO + views.py:92 reducer-sanitized seam (precise 2-site discrimination); store.py:184 _is_safe_slug seam; surface_resolver.py:429/434 unreachable raise-payload. All 12 known candidates genuinely AST-discovered. ruff+mypy clean. Scope: 4 audit files only, no src/. Set issue-matrix #2036->in-mission (multi-WP; fixes land WP02-04; terminal verdict due at mission done).
