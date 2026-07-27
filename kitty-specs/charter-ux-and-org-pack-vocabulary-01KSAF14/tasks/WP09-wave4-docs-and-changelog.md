---
work_package_id: WP09
title: 'Wave 4: docs + CHANGELOG + ADR cross-references (FR-015 f, FR-017)'
dependencies:
- WP07
requirement_refs:
- FR-015
- FR-017
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T051
- T052
- T053
- T054
agent: "claude:opus-4-7:reviewer-renata:reviewer"
shell_pid: "1256135"
history:
- by: claude
  at: '2026-05-23T13:30:00+00:00'
  action: generated
agent_profile: curator-carla
authoritative_surface: docs/
execution_mode: planning_artifact
mission_id: 01KSAF14K8FZ56MHYT45EGWHHC
mission_slug: charter-ux-and-org-pack-vocabulary-01KSAF14
owned_files:
- docs/**
- CHANGELOG.md
- README.md
priority: P1
role: curator
tags: []
---

## ⚡ Do This First: Load Agent Profile

Invoke `/ad-hoc-profile-load` with argument `curator-carla` before reading further. This WP is curation work — documentation, CHANGELOG, ADR cross-references — and benefits from Carla's preservation-first lens.

## Objective

Migrate the `shipped` vocabulary in user-facing documentation, schema descriptions, and README excerpts per `occurrence_map.yaml` `docs` rows. Land the CHANGELOG breaking-change entry (FR-017). Verify the three ADRs written in earlier waves cross-reference back to `2026-05-16-1-doctrine-layer-merge-semantics.md`.

## Branch strategy

- Planning base branch: `main`
- Merge target branch: `main`
- Execution worktree: allocated by `finalize-tasks`.

## Context

- `kitty-specs/.../occurrence_map.yaml` — `docs` (under `user_facing_strings`) and `historical_preservation` rows
- `kitty-specs/.../spec.md` — FR-015 part f, FR-017
- ADRs from WP01 / WP05 / WP07 — verify cross-references
- Constraint: do NOT touch `CHANGELOG.md` entries for past releases (historical). The new entry goes under the next-release header.

## Subtask details

### T051 — Migrate `docs/` markdown + schema descriptions + README excerpts

**Files**: `docs/**/*.md`, `src/doctrine/schemas/*.schema.yaml` (only the `description:` text, not field names), `README.md`

Sweep per occurrence_map. Replace `shipped` (as doctrine layer label) with `built-in` in:
- Operator-facing prose in `docs/operations/`, `docs/explanation/`, etc.
- Schema YAML `description:` strings (already partially correct on disk — verify each).
- README sections that explain doctrine layers.

DO NOT touch:
- `CHANGELOG.md` entries dated before today (historical).
- `architecture/3.x/adr/*` files predating this mission (frozen — they record what was true at the time).
- `kitty-specs/*/spec.md` for committed missions other than this one (frozen).

### T052 — CHANGELOG entry for FR-017

**Files**: `CHANGELOG.md`

Add an entry under the next-release header (or create an "Unreleased" header if none exists):

```markdown
### Breaking changes

- **`shipped` → `built-in` vocabulary rename.** Public CLI JSON surfaces that
  previously emitted `"shipped"` as a doctrine layer label now emit `"built-in"`.
  This aligns user-facing terminology with the on-disk `built-in/` directory
  layout that already existed. Affected commands:
  - `spec-kitty charter status --json`
  - `spec-kitty charter lint --json`
  - `spec-kitty charter preflight --json` (new in this release)
  - `spec-kitty agent profile list --json`
  - `spec-kitty doctrine pack validate --json`

  External tooling that pattern-matched the string `"shipped"` MUST be updated.
  No deprecation period: the rename is mechanical and the architectural test
  `tests/architectural/test_no_shipped_layer_label.py` prevents regression.

  Related: ADR `architecture/3.x/adr/2026-05-DD-3-shipped-to-built-in-cutover.md`.
```

### T053 — Final acceptance grep

Per `occurrence_map.yaml::acceptance_check`:

```bash
grep -rn '"shipped"\|'\''shipped'\''' src/ tests/ docs/ 2>/dev/null \
  | grep -v -E "(\\.mypy_cache|CHANGELOG\\.md|architecture/.*/adr/|kitty-specs/)" \
  | wc -l
```

**Expected**: 0.

If non-zero: investigate every match. Either:
- Migrate it (if in scope).
- Add it to the occurrence_map's `historical_preservation` block (if it should be preserved).
- Open a follow-up issue if it represents drift that arrived during this mission.

Document the final count in the WP completion notes.

### T054 — Cross-reference 3 new ADRs

**Files**: `architecture/3.x/adr/2026-05-DD-1-*.md`, `2026-05-DD-2-*.md`, `2026-05-DD-3-*.md`

Verify each ADR contains a "Related ADRs" or "Cross-references" section pointing to:
- `architecture/3.x/adr/2026-05-16-1-doctrine-layer-merge-semantics.md`
- The other two ADRs from this mission (each ADR references the other two).

If any cross-reference is missing, add it. The intent: a future reader landing on any of the four ADRs can navigate the full decision chain without leaving the directory.

## Definition of Done

- [ ] `docs/`, README, and schema descriptions clean of `shipped` as layer label.
- [ ] CHANGELOG has the breaking-change entry with all 5 affected commands.
- [ ] Acceptance grep returns 0.
- [ ] All 3 new ADRs cross-reference each other and `2026-05-16-1`.

## Risks

- **Schema description prose**: schema YAML files can mention "shipped" both as the noun ("the shipped artifact") and as the layer label. Use judgement — only the layer-label usage is in scope.
- **CHANGELOG conflict**: another mission may be staging a CHANGELOG entry. Coordinate at merge time.

## Reviewer guidance

1. Verify no historical text (past CHANGELOG entries, frozen ADRs, frozen missions) was modified.
2. Verify the CHANGELOG entry is under the right release header.
3. Verify cross-references work — click each link mentally.

## Activity Log

- 2026-05-24T10:08:09Z – claude:opus-4-7:curator-carla:curator – shell_pid=1205645 – Started implementation via action command
- 2026-05-24T10:17:34Z – claude:opus-4-7:curator-carla:curator – shell_pid=1205645 – Ready for review: docs/README/schema descriptions renamed, CHANGELOG entry added, ADR cross-ref audit recorded
- 2026-05-24T10:18:02Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1256135 – Started review via action command
- 2026-05-24T10:19:52Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1256135 – Review passed: 16 docs files migrated (shipped->built-in as layer label), CHANGELOG breaking-change + Added entries land under [Unreleased] with all 5 affected commands + new charter preflight command, no frozen surfaces touched (past CHANGELOG entries, pre-mission ADRs, other missions' specs all intact), ADR cross-ref audit recorded for mission-merge phase. T053 grep returns 7 matches all confirmed out-of-WP09-scope: 4 in src/+tests/ owned by WP07 lane-g (not yet merged into mission branch), 1 in docs/development/ historical analysis doc, 2 additional collision-warnings test occurrences in lane-g.
- 2026-05-24T11:46:55Z – claude:opus-4-7:reviewer-renata:reviewer – shell_pid=1256135 – Moved to done
