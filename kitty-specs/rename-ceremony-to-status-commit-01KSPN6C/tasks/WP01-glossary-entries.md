---
work_package_id: WP01
title: Glossary Canonical + Deprecated Entries
dependencies: []
requirement_refs:
- FR-006
- FR-007
tracker_refs: []
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
base_branch: kitty/mission-rename-ceremony-to-status-commit-01KSPN6C
base_commit: 6a553f0a7841a3e2c17652192160cd11af4bfcfa
created_at: '2026-06-01T07:33:50.996058+00:00'
subtasks:
- T001
- T002
- T003
- T004
phase: Phase 1 - Foundation
agent: claude
shell_pid: '52951'
history:
- at: '2026-05-28T07:11:05Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: .kittify/glossaries/
execution_mode: code_change
owned_files:
- .kittify/glossaries/spec_kitty_core.yaml
role: implementer
tags: []
task_type: implement
---

# Work Package Prompt: WP01 — Glossary Canonical + Deprecated Entries

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

Scope governance context to terminology curation before reading anything else. This WP is a YAML edit governed by glossary conventions — load the curator profile so the doctrine guardrails apply.

---

## Objective

Anchor the canonical term `status commit` in `.kittify/glossaries/spec_kitty_core.yaml`. Mark both legacy terms — `ceremony commit` and `status-writing operation` — as deprecated. Follow the established schema (5 prior `status: deprecated` entries already exist in the file).

This is the **foundation** for the regression guard. Future term-checkers that consume the glossary will look up the canonical term and reject the deprecated ones by surface key.

## Context

- **Spec anchors**: [FR-006](../spec.md#functional-requirements) (canonical entry definition exact), [FR-007](../spec.md#functional-requirements) (both legacy terms deprecated).
- **Data model**: [data-model.md](../data-model.md) lists exact field values for all three entries.
- **Schema precedent**: 5 existing deprecated entries in the file (e.g., `main repo`, `main repository`, `main repository root`) follow this pattern:
  - `surface: <legacy term>`
  - `definition: "DEPRECATED … Use '<canonical>' instead."`
  - `status: deprecated`
  - `confidence: 1.0`
- **Schema fields supported**: `surface`, `definition`, `confidence`, `status`, `synonyms_to_avoid` (optional), `see_also` (optional).
- **File location**: `.kittify/glossaries/spec_kitty_core.yaml` (this is the only file you touch in this WP).
- **Insertion order**: Entries are sorted alphabetically by `surface`. Insert each new entry in alphabetical position:
  - `ceremony commit` lands between existing `catastrophic backtracking` and `change mode`.
  - `status commit` lands between existing entries — search for entries starting with "s" and place alphabetically.
  - `status-writing operation` lands alphabetically just after `status commit`.

## Subtask Detail

### T001 — Add canonical `status commit` entry

Insert into `.kittify/glossaries/spec_kitty_core.yaml`:

```yaml
  - surface: status commit
    definition: An auto-commit created by spec-kitty to record workflow state changes (task status transitions, lane metadata, WP claims). Status commits target lane branches, not protected branches.
    confidence: 0.95
    status: active
    synonyms_to_avoid: [ceremony commit, ceremony, ceremony write, status-writing operation, status-writing command]
```

Place alphabetically — find the section where surface names beginning with `s` are listed and insert between adjacent entries.

### T002 — Add deprecated `ceremony commit` entry

Insert alphabetically (between `catastrophic backtracking` and `change mode`):

```yaml
  - surface: ceremony commit
    definition: "DEPRECATED. Replaced by `status commit`. This term obscures intent and is forbidden in active source. See the canonical `status commit` entry."
    confidence: 1.0
    status: deprecated
```

### T003 — Add deprecated `status-writing operation` entry

Insert alphabetically (just after the new `status commit` entry):

```yaml
  - surface: status-writing operation
    definition: "DEPRECATED. Replaced by `status commit`. This phrasing landed during a partial rename; it is forbidden in active source. See the canonical `status commit` entry."
    confidence: 1.0
    status: deprecated
```

### T004 — Verify glossary loads and contains all three entries

Run from the lane workspace root:

```bash
python -c "
import ruamel.yaml
y = ruamel.yaml.YAML(typ='safe')
data = y.load(open('.kittify/glossaries/spec_kitty_core.yaml'))
surfaces = {t['surface']: t for t in data['terms']}
assert surfaces['status commit']['status'] == 'active', 'canonical entry missing or wrong status'
assert surfaces['ceremony commit']['status'] == 'deprecated', 'ceremony commit entry missing or wrong status'
assert surfaces['status-writing operation']['status'] == 'deprecated', 'status-writing operation entry missing or wrong status'
print('Glossary OK: 3 new entries present with correct statuses.')
"
```

Expected output: `Glossary OK: 3 new entries present with correct statuses.`

## Branch Strategy

- Planning base branch: `main`
- Final merge target: `main`
- Execution workspace: allocated per lane in `lanes.json` after `finalize-tasks`. Do not branch manually.
- Resolve lane via `spec-kitty agent context resolve --action implement --wp WP01 --mission rename-ceremony-to-status-commit-01KSPN6C --json` and use the returned `workspace_path`.

## Test Strategy

- The verification script in T004 is the test. No new pytest needed for this WP.
- Run existing glossary-loader tests if any: `pytest tests/ -k glossary` (best-effort — no specific test currently asserts on these new surfaces).
- WP06 (regression guard) will assert the new entries are present via a separate test in a later WP.

## Definition of Done

- [ ] `.kittify/glossaries/spec_kitty_core.yaml` contains exactly one `surface: status commit` entry with `status: active`.
- [ ] File contains a `surface: ceremony commit` entry with `status: deprecated`.
- [ ] File contains a `surface: status-writing operation` entry with `status: deprecated`.
- [ ] The verification command from T004 prints `Glossary OK: 3 new entries present with correct statuses.`
- [ ] `ruff check .` passes (YAML is not linted by ruff but the run gates wider repo health).
- [ ] No other files modified.

## Risks & Reviewer Guidance

- **Risk**: Implementer uses a YAML dumper that rewrites the entire file (loses key order, comments). Mitigation: edit the file by hand in a text editor, or use ruamel.yaml round-trip mode (not safe-load + dump).
- **Reviewer check 1**: Diff should be additive — only three new entries, no changes to existing entries.
- **Reviewer check 2**: New entries appear in alphabetical position by `surface`.
- **Reviewer check 3**: Verification script from T004 passes.

## References

- Spec: [../spec.md](../spec.md) — FR-006, FR-007
- Plan: [../plan.md](../plan.md) — Phase 1 data model section
- Data model: [../data-model.md](../data-model.md) — full field values
- Occurrence map: [../occurrence_map.yaml](../occurrence_map.yaml) — `glossary_edits` section

## Activity Log

- 2026-06-01T07:36:37Z – claude – shell_pid=52951 – Ready for review
