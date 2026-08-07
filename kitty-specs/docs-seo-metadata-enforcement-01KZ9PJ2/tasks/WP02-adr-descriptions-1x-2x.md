---
work_package_id: WP02
title: ADR descriptions — 1.x and 2.x
dependencies: []
requirement_refs:
- FR-004
- NFR-002
- NFR-003
- NFR-004
tracker_refs: []
planning_base_branch: feat/docs-seo-metadata-enforcement
merge_target_branch: feat/docs-seo-metadata-enforcement
branch_strategy: Planning artifacts for this mission were generated on feat/docs-seo-metadata-enforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-seo-metadata-enforcement unless the human explicitly redirects the landing branch.
subtasks:
- T007
- T008
- T009
- T010
- T011
agent: "claude:opus-5:reviewer-renata:reviewer"
shell_pid: "68128"
history:
- at: '2026-08-05T19:58:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/adr/1.x/
create_intent: []
execution_mode: code_change
model: claude-opus-5
owned_files:
- docs/adr/1.x/**
- docs/adr/2.x/**
role: curator
tags: []
task_type: implement
---

# Work Package Prompt: WP02 – ADR descriptions: 1.x and 2.x

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`

## Objective

Author a unique, human-meaningful `description` for each of the **51 pages** under `docs/adr/1.x/` (13) and `docs/adr/2.x/` (38).

These pages currently ship with **no description tag at all**. Their social description is a single boilerplate string — *"Spec Kitty documentation for CLI workflows, governed missions, AI harnesses, and 3.2 upgrades."* — duplicated across all 147 undescribed ADRs. Search engines see 147 pages claiming to be the same thing.

This is authoring work, not code. The quality bar is that a developer reading the description in a search result learns **what was decided**, not that the page is an ADR.

## Context

**Why hand-authored**: machine derivation from headings was explicitly offered and rejected during discovery (decision `01KZ9PJS30X2ZTDZAQS51XRTT8`, constraint C-008). A mechanical *"ADR about X"* template would satisfy the length band while defeating the entire purpose — and would collide with the uniqueness rule anyway.

**Two facts established during planning that de-risk this work:**

1. **The census gate will not break.** `tests/docs/test_adr_content_invariance.py::test_every_adr_has_bare_madr_status_frontmatter` asserts only that `status` is a canonical MADR value. It does **not** enumerate permitted keys and does **not** fail on additional ones. Verified by reading the assertion. Adding `description:` is safe.

2. **The lockfile will not drift.** `scripts/docs/inventory_lockfile.py` emits `path`, `tag`, `divio_type`, `owning_workstream`, `current_target`, `notes` — **not** `description`. Since all 51 of these files already have frontmatter, adding a `description` key produces no lockfile delta. (`INVENTORY-LOCKFILE-DRIFT` is a recurring CI failure in this repo, so this was checked rather than assumed.)

**Existing ADR frontmatter shape**:
```yaml
---
title: 'ADR: MissionResolver Port — One Walk Trunk, Shell-Side DI, No Shared Container'
status: Accepted
date: '2026-07-08'
---
```
You are adding one key. Do not reorder, reformat, or otherwise touch existing keys.

## Subtasks

### T007 — Survey the batch and build an authoring worklist

**Purpose**: Know what you are describing before you describe it. 51 ADRs contain clusters of closely-related decisions whose descriptions will collide unless you plan for it.

**Steps**:
1. Enumerate the batch:
   ```bash
   find docs/adr/1.x docs/adr/2.x -name "*.md" | sort
   ```
   Expect 13 + 38 = 51 files, including `docs/adr/1.x/README.md` and `docs/adr/2.x/README.md`.
2. For each, read the `title` and the **Context and Problem Statement** and **Decision** sections. The description comes from the decision, not the title.
3. Flag clusters of related ADRs — these are your uniqueness hazards. Note them explicitly.

**Validation**:
- [ ] Worklist covers exactly 51 files
- [ ] Related clusters identified and noted

### T008 — Author descriptions for `docs/adr/1.x` (13 pages)

**Purpose**: Describe the 1.x-era decisions.

**Steps**:
1. For each file, insert a `description:` key into the existing frontmatter block. Place it after `title:` for readability.
2. Constraints per description:
   - **50–180 characters inclusive.** 49 and 181 are violations. This band is fixed (C-003) — do not adjust it.
   - Unique across the whole mission, not just this batch.
   - States what was decided and why it matters, in plain language.
   - Terminology Canon applies: **Mission** not "feature"; mind the overloaded terms `primary`, `merge`, `routing` — name the sense.
3. Two READMEs in this batch (`1.x/README.md`, `2.x/README.md`) **do** already have frontmatter — confirm this before editing. If either turns out to have none, add **only** `title` and `description` (see the WP04 trap note).

**Good** — says what was decided:
> Records why explicit base-branch tracking replaced inferred parents, and what must stay true for worktree allocation to remain correct.

**Bad** — says what the document is:
> An architectural decision record about base branch tracking in Spec Kitty.

**Files**: 13 files under `docs/adr/1.x/`

**Validation**:
- [ ] All 13 have `description` in band
- [ ] Existing `title`/`status`/`date` keys untouched
- [ ] No description restates the title

### T009 — Author descriptions for `docs/adr/2.x` (38 pages)

**Purpose**: Describe the 2.x-era decisions.

**Steps**: As T008, applied to the 38 files under `docs/adr/2.x/`.

Pay particular attention to the clusters flagged in T007 — where two ADRs address adjacent concerns, the descriptions must differ on the substance of the decision, not by cosmetic rewording.

**Files**: 38 files under `docs/adr/2.x/`

**Validation**:
- [ ] All 38 have `description` in band
- [ ] Clustered ADRs have substantively distinct descriptions
- [ ] Existing keys untouched

### T010 — Self-check length band and intra-batch uniqueness

**Purpose**: Catch band and duplicate violations before the gate does. The gate does not exist yet (it lands in WP06), so this check is your only signal.

**Steps**:
1. Band and presence:
   ```bash
   PYTHONPATH=. uv run python - <<'PY'
   import re, pathlib
   from collections import Counter
   bad, seen = [], Counter()
   for f in sorted(list(pathlib.Path("docs/adr/1.x").rglob("*.md")) +
                   list(pathlib.Path("docs/adr/2.x").rglob("*.md"))):
       t = f.read_text(encoding="utf-8")
       m = re.search(r"^description:\s*(.+)$", t[:t.find("\n---", 3)], re.M)
       if not m:
           bad.append((str(f), "missing")); continue
       d = m.group(1).strip().strip("'\"")
       seen[d] += 1
       if not (50 <= len(d) <= 180):
           bad.append((str(f), f"len={len(d)}"))
   dupes = [d for d, n in seen.items() if n > 1]
   print("violations:", bad or "none")
   print("duplicates:", dupes or "none")
   print("total described:", sum(seen.values()), "(expect 51)")
   PY
   ```
2. Fix everything reported. Zero violations, zero duplicates.

**Validation**:
- [ ] 51 descriptions found
- [ ] No band violations
- [ ] No duplicates within the batch

### T011 — Run terminology guard and confirm no lockfile drift

**Purpose**: `docs/` **is** in the terminology guard's scan roots — unlike `kitty-specs/`, which is explicitly excluded. Your authored prose is subject to it.

**Steps**:
1. Terminology guard (fast, ~0.1 s):
   ```bash
   PWHEADLESS=1 uv run pytest tests/architectural/test_no_legacy_terminology.py -q
   ```
   Fix any hit. Common traps: "feature" where "Mission" is meant; bare `primary`/`merge`/`routing` without naming the sense.
2. Confirm no lockfile drift:
   ```bash
   PYTHONPATH=. uv run python scripts/docs/inventory_lockfile.py --repo-root .
   ```
   Expect no drift. If it reports drift, you have added a key the lockfile reads — remove it.
3. Re-run the ADR census gate:
   ```bash
   PWHEADLESS=1 uv run pytest tests/docs/test_adr_content_invariance.py -q
   ```

**Validation**:
- [ ] Terminology guard green
- [ ] No lockfile drift
- [ ] ADR census gate green

## Branch Strategy

- **Planning base branch**: `feat/docs-seo-metadata-enforcement`
- **Final merge target**: `feat/docs-seo-metadata-enforcement`
- Execution worktrees are allocated per computed lane from `lanes.json`. Consume the resolved path; do not construct it.
- This mission reaches `origin/main` only through a pull request.

## Definition of Done

- [ ] All 51 pages under `docs/adr/1.x/` and `docs/adr/2.x/` carry a `description`
- [ ] Every description is 50–180 characters inclusive
- [ ] No two descriptions identical within the batch
- [ ] No description is a restatement of its title
- [ ] Existing frontmatter keys unmodified
- [ ] Terminology guard green
- [ ] No inventory-lockfile drift
- [ ] ADR census gate still green

## Risks

| Risk | Mitigation |
|---|---|
| Descriptions collide across the mission's three ADR packages | Uniqueness is enforced globally in WP06; write distinctively now rather than dedupe later |
| Mechanical templating satisfies length while defeating purpose | Reviewer guidance below checks for this specifically |
| Terminology guard hits on authored prose | T011 runs it explicitly; it is ~0.1 s, run it often |
| Accidentally reformatting existing frontmatter | Insert one key; do not rewrite the block |

## Reviewer Guidance

1. **Sample ten descriptions at random and read them cold.** Can you tell what was decided without opening the page? If not, reject — length compliance is not the goal.
2. **Check for templating.** If descriptions share a stem like *"This ADR records…"* across many files, they are mechanical. C-008 requires hand-authoring.
3. **Verify existing keys are untouched** — `git diff` should show pure insertions, no modifications to `title`/`status`/`date`.
4. **Confirm the count is 51**, not "about 51".
5. **Check the two READMEs** were handled and did not gain lockfile-read keys.

## Activity Log

- 2026-08-05T20:17:46Z – claude:opus-5:curator-carla:implementer – shell_pid=55785 – Assigned agent via action command
- 2026-08-05T20:28:26Z – claude:opus-5:curator-carla:implementer – shell_pid=55785 – 51/51 ADR pages under docs/adr/1.x (13) and docs/adr/2.x (38) now carry a hand-authored description. Self-check: violations none, duplicates none, total described 51, length min 149 / max 169 (band 50-180). git diff = 59 pure insertions across 51 files, zero deletions or modifications to existing title/status/date keys. Note: both READMEs had NO frontmatter (planning assumed they did) - added only title + description per the WP04 trap instruction; census gate excludes READMEs and lockfile shows no drift. Guards: terminology 10 passed; inventory_lockfile exit=0 generated=698 committed=698 drift=False; ADR census 2 passed.
- 2026-08-05T20:29:24Z – claude:opus-5:reviewer-renata:reviewer – shell_pid=68128 – Started review via action command
- 2026-08-05T20:34:24Z – user – shell_pid=68128 – Review passed: 51/51 ADRs in docs/adr/1.x (13) + 2.x (38) carry hand-authored, decision-specific descriptions (len 149-169, band 50-180); zero intra-batch duplicates, zero shared 24-char prefixes, only shared 2-word stem is 'Index of' on the two READMEs. Superseded-ADR rewrite verified real: all 8 open with distinct past-tense verbs (Centralised/Rejected/Replaced/Detected/Broke/Recognised/Introduced/Required), no 'Superseded.' prefix; the 7 Proposed ADRs are likewise varied. README deviation verified correct: both READMEs had no frontmatter and gained ONLY title+description (parse_frontmatter -> ['description','title']); confirmed against code that _is_census_adr admits only dated YYYY-MM-DD-* and promoted adr-* (READMEs excluded, no status needed) and that inventory_lockfile reads only version_tag/type/owning_workstream/notes with current_target derived - lockfile exit=0 generated=698 committed=698 drift=False. Diff is 51 files / 59 insertions / 0 deletions with zero ^- lines; sparse-checkout-defense-in-depth.md multi-line quoted title scalar still parses intact via yaml.safe_load. Ownership boundary clean (no 3.x files). Accuracy spot-checked against 5 Decision sections (event-log-merge-semantics, glossary-type-ownership, auto-merge-multi-parent, verify/doctor taxonomy, vendor-events) - all faithful. Terminology clean: 'Mission' used correctly, only overloaded-term hit is the sense-qualified compound 'dependency auto-merge'; 2026-01-26-9 correctly uses canonical 'lane consolidation'. Gates: tests/docs 629 passed, terminology+census 12 passed.
