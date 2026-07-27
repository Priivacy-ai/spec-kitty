# Phase 0 Research: Rename Ceremony Commit to Status Commit

**Mission**: `rename-ceremony-to-status-commit-01KSPN6C`
**Date**: 2026-05-28

A terminology rename has narrow research surface. This file consolidates the four research items the plan needed to resolve before producing design artifacts.

---

## R1. Glossary schema for the canonical + deprecated entries

**Decision**: Follow the existing `.kittify/glossaries/spec_kitty_core.yaml` schema. Add **one** canonical entry for `status commit` with `status: active`. Add **two** deprecated entries — one for `ceremony commit`, one for `status-writing operation` — each with `status: deprecated` and a definition pointing to the canonical term.

**Rationale**: The schema already supports `status: deprecated` (5 prior entries: `main repo`, `main repository`, `main repository root`, plus 2 others) and the optional `synonyms_to_avoid: [...]` field. No schema invention required, and the existing graph-native term-checker (`charter lint`) consumes the same fields.

**Alternatives considered**:

- *Add a `replaced_by:` cross-link field* — could be added later by a separate mission, not required now. Skipped to avoid scope creep.
- *Encode all variants under one `synonyms_to_avoid` list on the canonical entry only* — rejected because deprecated entries also need their own definitions ("DEPRECATED phrase. Use 'status commit' instead.") so a future deprecation grep against the YAML file can find both forms by surface key.

---

## R2. Config-flag live state — does `vcs.allow_ceremony_commits_on_target_branch` exist?

**Decision**: **No code-side rename required.** The proposed flag does not exist in live code.

**Rationale**: At spec time and again at plan time, `grep -rn "allow_ceremony_commits_on_target_branch\|allow_status_commits_on_target_branch" src/` returned zero hits. The only mention is in the F-09 findings doc (`docs/engineering_notes/finding/2026-05-24-mission-01KSAF14-orchestration-findings.md`) where the name appears as a **proposed follow-up**, not as a shipped flag. Therefore the rename touches one prose line in that doc and zero lines of Python code.

**Alternatives considered**:

- *Preemptively introduce both names with a compat alias* — rejected. There is no flag to alias. Introducing the flag itself is a separate mission.
- *Leave the F-09 doc alone* — rejected. The doc would be the only place in the codebase that uses the old name pattern, and we want the post-rename grep to return zero hits.

---

## R3. Active-source occurrence discovery

**Decision**: 12 active-source files contain at least one forbidden term occurrence. Total occurrences = 25 (23 "ceremony" + 2 "status-writing"). All 12 files are inventoried in [occurrence_map.yaml](occurrence_map.yaml) with file path, line number, surrounding context, and replacement text.

**Rationale**: Grep results from plan time:

- `grep -rn 'ceremony' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'` → 23 lines across 11 files.
- `grep -rn 'status-writing' src/ tests/ docs/ --include='*.py' --include='*.md' --include='*.yaml'` → 2 lines in 1 file (`src/specify_cli/git/commit_helpers.py`).

**Two files cited in issue #1325 are already clean** at plan time and need no edits:

- `tests/git_ops/test_safe_commit_helper_integration.py` — issue claimed function name + docstring at lines 105-106 still mention "ceremony"; plan-time grep shows zero hits. Already renamed in a prior commit.
- `src/specify_cli/git/commit_helpers.py` lines 70 / 122 / 130 / 137 / 155 — issue claimed these had "ceremony"; plan-time grep shows lines 70/126/134 now use "status commit" (canonical) and the test-mode comment + error string at lines 141/159 use the partial "status-writing" variant that this mission reconciles.

**Alternatives considered**: None — the issue's enumeration is partially stale, so the live grep is authoritative.

---

## R4. Doctrine prose: workflow-sense versus commit-class occurrences

**Decision**: Each occurrence is classified as `commit_class` (replace with "status commit") or `workflow_sense` (semantic rewrite that conveys the actual meaning, typically "the full mission workflow" or "all phases"). Decision `01KSPP3SSZ5GKHTTB1C9EJQ13V` resolved this strategy.

**Rationale**: Mechanical substitution in `src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md` would produce nonsense ("full status commit"). The doctrine prose talks about the full ceremony — meaning the specify/plan/tasks/implement/review/merge sequence — not a single auto-commit. A blanket substitution would break the doctrine's pedagogy.

Classification at plan time (full per-occurrence rationale lives in `occurrence_map.yaml`):

| Source line | Sense | Replacement strategy |
|---|---|---|
| `SKILL.md:9` "run the full ceremony" | workflow_sense | "run the full mission workflow" |
| `SKILL.md:269` "spawn the full-ceremony" | workflow_sense | "spawn the full mission workflow" |
| `SKILL.md:343` "after ceremony" | workflow_sense | "after the mission workflow runs" |
| `SKILL.md:366` "parts of the ceremony" | workflow_sense | "parts of the mission workflow" |
| `procedures/README.md:15` "Feature merge ceremony" | workflow_sense | "Feature merge workflow" |
| `guidelines.md:26` "inflating them with ceremony" | workflow_sense | "inflating them with workflow overhead" |
| `_baselines.yaml:17` "no ceremony" | workflow_sense | "no extra workflow steps" |
| `architecture-review.md:481` "degrades to ceremony" | workflow_sense | "degrades to performative gesture" (idiomatic English; "ceremony" used pejoratively here) |
| `3-2-publication-checklist.md:210` "specify/plan/tasks ceremony" | workflow_sense | "specify/plan/tasks workflow" |
| `reflections/README.md:12` "ceremony surfaces" | commit_class | "status commit surfaces" |
| `F-09 findings doc` 5 occurrences | mixed (see occurrence_map.yaml) | mostly commit_class — the finding is literally about commits; one workflow_sense line |
| `commit_helpers.py:141, 159` (status-writing) | commit_class | "status commit" |
| `e2e/conftest.py` 6 occurrences | tests_fixtures (commit_class) | identifier renames |
| `doctrine/procedures/conftest.py:48 + test_models.py:31` (mission-merge-ceremony ID) | tests_fixtures (workflow_sense) | "mission-merge-workflow" |

**Alternatives considered**:

- *Strict substitution* — rejected for the prose-nonsense reason above.
- *Defer each rewording to implement phase* — rejected because spreading the rewording decisions across implementation WPs risks inconsistent voice and makes the bulk-edit guardrail diff review brittle.

---

## Open Questions

None. All four research items resolved before Phase 1.
