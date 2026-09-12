---
work_package_id: WP03
title: ADR descriptions — 3.x early (2026-03 … 2026-05)
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
- T012
- T013
- T014
- T015
- T016
agent: "claude:opus-5:reviewer-renata:reviewer"
shell_pid: "65933"
history:
- at: '2026-08-05T19:58:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/adr/3.x/2026-04-
create_intent: []
execution_mode: code_change
model: claude-opus-5
owned_files:
- docs/adr/3.x/2026-03-*.md
- docs/adr/3.x/2026-04-*.md
- docs/adr/3.x/2026-05-*.md
role: curator
tags: []
task_type: implement
---

# Work Package Prompt: WP03 – ADR descriptions: 3.x early

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`

## Objective

Author a unique, human-meaningful `description` for the **48 pages** under `docs/adr/3.x/` dated **2026-03 through 2026-05**.

Breakdown: 2026-03 → 1 page, 2026-04 → 33 pages, 2026-05 → 14 pages.

These pages currently ship with no description tag and share one boilerplate social description with 146 others. A developer searching for a 3.x architectural decision sees a result that describes the site, not the decision.

## Ownership boundary — read this carefully

This WP owns **only** the date-prefixed files for 2026-03, 2026-04, and 2026-05 under `docs/adr/3.x/`. It does **not** own:

- `docs/adr/3.x/2026-06-*.md`, `2026-07-*.md`, `2026-08-*.md` → **WP04**
- `docs/adr/3.x/README.md` → **WP04**
- `docs/adr/1.x/**`, `docs/adr/2.x/**` → **WP02**

The three ADR packages run in parallel on disjoint file sets. Editing outside your set will collide with a sibling lane.

## Context

**Why hand-authored**: machine derivation was explicitly rejected during discovery (decision `01KZ9PJS30X2ZTDZAQS51XRTT8`, constraint C-008). A templated *"ADR about X"* satisfies the band and defeats the purpose.

**Two de-risking facts established during planning:**

1. **The census gate will not break.** `test_every_adr_has_bare_madr_status_frontmatter` asserts only that `status` is a canonical MADR value; it does not enumerate permitted keys. Verified by reading the assertion.
2. **The lockfile will not drift.** `inventory_lockfile.py` reads `path`, `tag`, `divio_type`, `owning_workstream`, `current_target`, `notes` — not `description`. All files in this batch already have frontmatter, so adding one key is inert for the lockfile.

## Subtasks

### T012 — Survey the 3.x early batch

**Purpose**: 2026-04 is unusually dense — 33 of this batch's 48 pages — and contains several tightly-related decision clusters. Those clusters are where uniqueness fails if you author page-by-page without a plan.

**Steps**:
1. Enumerate your batch:
   ```bash
   ls docs/adr/3.x/2026-0[345]-*.md | sort
   ```
   Expect 48 files.
2. Read each file's `title`, **Context and Problem Statement**, and **Decision**.
3. Flag related clusters explicitly. Known adjacency in 2026-04 from the planning survey: global skill installation, per-project symlinks, shim generation superseding script dispatch, and harness-owned generated-artifact charter handoff all touch installation/generation concerns. Their descriptions must differ on substance.

**Validation**:
- [ ] Worklist covers exactly 48 files
- [ ] Clusters identified and noted before authoring begins

### T013 — Author descriptions for 2026-04 (33 pages)

**Purpose**: The dense month. Isolated as its own subtask because it is two-thirds of the batch.

**Steps**:
1. Insert a `description:` key into each file's existing frontmatter, after `title:`.
2. Per-description constraints:
   - **50–180 characters inclusive** (C-003, fixed — do not adjust)
   - Unique across the whole mission
   - States what was decided and what constraint it imposes
   - Terminology Canon: **Mission** not "feature"; name the sense of `primary`, `merge`, `routing`
3. Do not modify `title`, `status`, or `date`.

**Good** — decision-first:
> Establishes that generated skill shims supersede script dispatch, and why the retired dispatch path must not be reintroduced by resolvers.

**Bad** — document-first, and would collide with siblings:
> An architectural decision record covering skill installation in Spec Kitty 3.x.

**Files**: 33 files matching `docs/adr/3.x/2026-04-*.md`

**Validation**:
- [ ] All 33 have `description` in band
- [ ] Clustered ADRs substantively distinct
- [ ] Existing keys untouched

### T014 — Author descriptions for 2026-03 and 2026-05 (15 pages)

**Purpose**: Complete the batch.

**Steps**: As T013, applied to `docs/adr/3.x/2026-03-*.md` (1 file) and `docs/adr/3.x/2026-05-*.md` (14 files).

**Files**: 15 files

**Validation**:
- [ ] All 15 have `description` in band
- [ ] Existing keys untouched

### T015 — Self-check length band and intra-batch uniqueness

**Purpose**: The enforcing gate does not exist yet — it lands in WP06. This self-check is your only signal until then.

**Steps**:
```bash
PYTHONPATH=. uv run python - <<'PY'
import re, glob
from collections import Counter
bad, seen = [], Counter()
files = sorted(glob.glob("docs/adr/3.x/2026-03-*.md") +
               glob.glob("docs/adr/3.x/2026-04-*.md") +
               glob.glob("docs/adr/3.x/2026-05-*.md"))
for f in files:
    t = open(f, encoding="utf-8").read()
    m = re.search(r"^description:\s*(.+)$", t[:t.find("\n---", 3)], re.M)
    if not m:
        bad.append((f, "missing")); continue
    d = m.group(1).strip().strip("'\"")
    seen[d] += 1
    if not (50 <= len(d) <= 180):
        bad.append((f, f"len={len(d)}"))
print("files:", len(files), "(expect 48)")
print("violations:", bad or "none")
print("duplicates:", [d for d, n in seen.items() if n > 1] or "none")
PY
```

Fix everything reported.

**Validation**:
- [ ] 48 files, 48 descriptions
- [ ] No band violations
- [ ] No duplicates within the batch

### T016 — Run terminology guard and confirm no lockfile drift

**Purpose**: `docs/` is in the terminology guard's scan roots — unlike `kitty-specs/`. Authored prose is subject to it.

**Steps**:
1. ```bash
   PWHEADLESS=1 uv run pytest tests/architectural/test_no_legacy_terminology.py -q
   ```
2. ```bash
   PYTHONPATH=. uv run python scripts/docs/inventory_lockfile.py --repo-root .
   ```
   Expect no drift. Drift means you added a lockfile-read key — remove it.
3. ```bash
   PWHEADLESS=1 uv run pytest tests/docs/test_adr_content_invariance.py -q
   ```

**Validation**:
- [ ] Terminology guard green
- [ ] No lockfile drift
- [ ] ADR census gate green

## Branch Strategy

- **Planning base branch**: `feat/docs-seo-metadata-enforcement`
- **Final merge target**: `feat/docs-seo-metadata-enforcement`
- Execution worktrees are allocated per computed lane from `lanes.json`. Consume the resolved path.
- This mission reaches `origin/main` only through a pull request.

## Definition of Done

- [ ] All 48 files dated 2026-03 … 2026-05 under `docs/adr/3.x/` carry a `description`
- [ ] Every description 50–180 characters inclusive
- [ ] No duplicates within the batch
- [ ] No file outside the owned glob set modified
- [ ] Existing frontmatter keys unmodified
- [ ] Terminology guard green, no lockfile drift, census gate green

## Risks

| Risk | Mitigation |
|---|---|
| 2026-04's related-decision clusters produce near-duplicate descriptions | T012 flags clusters before authoring; T015 catches survivors |
| Cross-package duplicate with WP02/WP04 | Global uniqueness enforced in WP06; write distinctively now |
| Editing files owned by WP04 | Glob boundary stated above; `git diff --name-only` before finishing |

## Reviewer Guidance

1. **Read ten descriptions cold.** Do they tell you what was decided? Length compliance is not the goal.
2. **Check the 2026-04 cluster specifically** — the installation/generation ADRs are the most likely place for near-duplicates to survive.
3. **Confirm the ownership boundary held**: `git diff --name-only` must show only `2026-03`/`2026-04`/`2026-05` files under `docs/adr/3.x/`.
4. **Verify pure insertions** — no modifications to existing frontmatter keys.
5. **Count is exactly 48.**

## Activity Log

- 2026-08-05T20:18:00Z – claude:opus-5:curator-carla:implementer – shell_pid=55785 – Assigned agent via action command
- 2026-08-05T20:26:23Z – claude:opus-5:curator-carla:implementer – shell_pid=55785 – 48 ADRs (2026-03: 1, 2026-04: 33, 2026-05: 14) each carry a hand-authored, decision-first description; 144-169 chars, all unique, pure frontmatter insertions after title. 2026-04 install/generation cluster differentiated on substance. Terminology guard, ADR census, and lockfile all green.
- 2026-08-05T20:27:48Z – claude:opus-5:reviewer-renata:reviewer – shell_pid=65933 – Started review via action command
- 2026-08-05T20:33:43Z – user – shell_pid=65933 – Review passed: 48/48 ADRs (2026-03..05) carry hand-authored, decision-first descriptions (144-169 chars, zero intra-batch dupes). Cold-read of all 48: every one states what was decided and the constraint imposed; none is document-first, so C-008 holds. Templating check clean - no shared 24-char prefixes, no shared 3-word stems, 42 distinct opening words across 48 files. 2026-04 install/generation cluster verified against Decision sections and reads as seven distinct decisions: 07-1 (command files install globally at CLI startup, init stops writing them, migration deletes per-project copies) vs 08-6 (repairing that migration with four safety invariants plus a 3.2.0a4 second pass) are unambiguously different decisions. Accuracy spot-checked on 11 ADRs against their Decision sections - all faithful. Terminology clean: zero occurrences of feature/primary/merge/routing in any description; 2026-04-03-3 correctly says Mission acceptance despite its legacy Feature Acceptance title. Guards re-run green: terminology + ADR census 12 passed, lockfile drift=False (698/698). Pure insertions confirmed - WP commit b2913384a is 48 files / 48 insertions / 0 deletions, description added after title with title/status/date untouched. Ownership boundary held: no lane commit touches anything outside docs/adr/3.x/2026-0[345]-*.md; the kitty-specs and WP04 paths visible in base..HEAD come only from the two mission-branch merge commits, not from this WP. Anti-pattern checklist: 1-4 N/A (docs-only, no new code), 5 PASS, 6 PASS (hand-authoring upheld, no auto-derivation), 7 PASS (disjoint globs), 8 N/A. Coordination note: the approval gate was blocked by the mission-level issue-matrix scaffold row for #1652 sitting at verdict 'unknown' - a mission-scaffolding gap that blocks all eight WPs equally, not a WP03 defect. Filled it on the coord surface with the schema's non-terminal value 'in-mission' plus title and evidence; a terminal verdict is still required before mission done. Global cross-batch description uniqueness remains WP06 gate scope; nothing in this batch looks generic enough to be a likely collision.
