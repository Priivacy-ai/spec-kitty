---
work_package_id: WP04
title: ADR descriptions — 3.x late (2026-06 … 2026-08 + README)
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
- T017
- T018
- T019
- T020
- T021
agent: "claude:opus-5:reviewer-renata:reviewer"
shell_pid: "65933"
history:
- at: '2026-08-05T19:58:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/adr/3.x/2026-06-
create_intent: []
execution_mode: code_change
model: claude-opus-5
owned_files:
- docs/adr/3.x/2026-06-*.md
- docs/adr/3.x/2026-07-*.md
- docs/adr/3.x/2026-08-*.md
- docs/adr/3.x/README.md
role: curator
tags: []
task_type: implement
---

# Work Package Prompt: WP04 – ADR descriptions: 3.x late

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`

## Objective

Author a unique, human-meaningful `description` for the **47 pages** under `docs/adr/3.x/` dated **2026-06 through 2026-08**, and add `title` + `description` frontmatter to `docs/adr/3.x/README.md` — **48 files total**.

Breakdown: 2026-06 → 22 pages, 2026-07 → 22 pages, 2026-08 → 3 pages, README → 1 file.

## ⚠️ The README trap — read before touching `README.md`

`docs/adr/3.x/README.md` currently has **no frontmatter at all**. This makes it different from every other file in this mission's ADR work.

**Add `title` and `description` ONLY.**

Do **not** add `tag`, `divio_type`, `owning_workstream`, `current_target`, or `notes`. Those are exactly the keys `scripts/docs/inventory_lockfile.py` reads. Adding any of them will drift the page-inventory lockfile and trip `INVENTORY-LOCKFILE-DRIFT` — a recurring CI failure in this repository. The other 47 files in this batch already have frontmatter, so they are inert for the lockfile; the README is not.

This trap was found during planning by reading the lockfile's emitted fields. It is the single most likely way this WP breaks CI.

## Ownership boundary

This WP owns **only**:
- `docs/adr/3.x/2026-06-*.md`, `2026-07-*.md`, `2026-08-*.md`
- `docs/adr/3.x/README.md`

It does **not** own `2026-03`/`2026-04`/`2026-05` files (→ **WP03**) or `docs/adr/1.x/**` and `docs/adr/2.x/**` (→ **WP02**). The three packages run in parallel on disjoint sets.

## Context

**Why hand-authored**: machine derivation was explicitly rejected during discovery (decision `01KZ9PJS30X2ZTDZAQS51XRTT8`, constraint C-008).

**The census gate will not break**: `test_every_adr_has_bare_madr_status_frontmatter` asserts only that `status` is a canonical MADR value and does not enumerate permitted keys. Verified by reading the assertion. Note the census predicate covers dated `YYYY-MM-DD-*` files and promoted `adr-*` files — README files are not census ADRs, which is why the README has no `status` requirement.

## Subtasks

### T017 — Survey the 3.x late batch

**Purpose**: 2026-06 and 2026-07 are the mission-machinery months — coordination, resolvers, DRG edges, write-side seams. Several decisions are adjacent and will produce near-duplicate descriptions unless planned.

**Steps**:
1. Enumerate:
   ```bash
   ls docs/adr/3.x/2026-0[678]-*.md docs/adr/3.x/README.md | sort
   ```
   Expect 48 files.
2. Read each file's `title`, **Context and Problem Statement**, and **Decision**.
3. Flag adjacency clusters. Known from the planning survey: mission-resolver port, write-branch resolution primary anchor, DRG-edges-as-relationship-authority, and glossary-as-first-order-doctrine-artefact all touch authority/resolution concerns.

**Validation**:
- [ ] Worklist covers exactly 48 files
- [ ] Clusters identified before authoring

### T018 — Author descriptions for 2026-06 (22 pages)

**Steps**:
1. Insert `description:` into each file's existing frontmatter, after `title:`.
2. Constraints:
   - **50–180 characters inclusive** (C-003, fixed)
   - Unique across the whole mission
   - States what was decided and what constraint it imposes
   - Terminology Canon: **Mission** not "feature". This batch is dense in the overloaded terms `primary`, `merge`, and `routing` — the canon requires naming the sense, never the bare word. Descriptions for `write-branch-resolution-primary-anchor` and similar must be explicit about which sense of `primary` they mean.
3. Do not modify `title`, `status`, or `date`.

**Files**: 22 files matching `docs/adr/3.x/2026-06-*.md`

**Validation**:
- [ ] All 22 have `description` in band
- [ ] Overloaded terms disambiguated, not used bare
- [ ] Existing keys untouched

### T019 — Author descriptions for 2026-07 and 2026-08 (25 pages)

**Steps**: As T018, applied to `2026-07-*.md` (22 files) and `2026-08-*.md` (3 files).

**Files**: 25 files

**Validation**:
- [ ] All 25 have `description` in band
- [ ] Existing keys untouched

### T020 — Add frontmatter to `docs/adr/3.x/README.md`

**Purpose**: The one file in this mission that needs frontmatter created rather than extended. See the trap warning above.

**Steps**:
1. The file currently begins:
   ```markdown
   # 3.x ADRs

   Architectural Decision Records for the 3.x track (starting 3.0.0, released 2026-03-30).
   ```
2. Prepend a frontmatter block containing **exactly two keys**:
   ```yaml
   ---
   title: <a descriptive title>
   description: <50-180 characters describing what this index offers a reader>
   ---
   ```
3. **Nothing else.** No `tag`, no `divio_type`, no `owning_workstream`, no `status`, no `date`.
4. Immediately verify no lockfile drift:
   ```bash
   PYTHONPATH=. uv run python scripts/docs/inventory_lockfile.py --repo-root .
   ```
   If this reports drift, you added a lockfile-read key. Remove it and re-run.

**Files**: `docs/adr/3.x/README.md`

**Validation**:
- [ ] Frontmatter contains exactly `title` and `description`
- [ ] Lockfile reports no drift immediately after this edit
- [ ] Body content unchanged

### T021 — Self-check, terminology guard, and lockfile drift check

**Steps**:
1. Band, presence, uniqueness:
   ```bash
   PYTHONPATH=. uv run python - <<'PY'
   import re, glob
   from collections import Counter
   bad, seen = [], Counter()
   files = sorted(glob.glob("docs/adr/3.x/2026-06-*.md") +
                  glob.glob("docs/adr/3.x/2026-07-*.md") +
                  glob.glob("docs/adr/3.x/2026-08-*.md") +
                  glob.glob("docs/adr/3.x/README.md"))
   for f in files:
       t = open(f, encoding="utf-8").read()
       if not t.startswith("---"):
           bad.append((f, "no frontmatter")); continue
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
2. Terminology guard:
   ```bash
   PWHEADLESS=1 uv run pytest tests/architectural/test_no_legacy_terminology.py -q
   ```
3. Lockfile and census:
   ```bash
   PYTHONPATH=. uv run python scripts/docs/inventory_lockfile.py --repo-root .
   PWHEADLESS=1 uv run pytest tests/docs/test_adr_content_invariance.py -q
   ```

**Validation**:
- [ ] 48 files, 48 descriptions, no band violations, no duplicates
- [ ] Terminology guard green
- [ ] No lockfile drift
- [ ] Census gate green

## Branch Strategy

- **Planning base branch**: `feat/docs-seo-metadata-enforcement`
- **Final merge target**: `feat/docs-seo-metadata-enforcement`
- Execution worktrees are allocated per computed lane from `lanes.json`. Consume the resolved path.
- This mission reaches `origin/main` only through a pull request.

## Definition of Done

- [ ] All 47 dated files (2026-06 … 2026-08) carry a `description`
- [ ] `docs/adr/3.x/README.md` has frontmatter with **exactly** `title` and `description`
- [ ] Every description 50–180 characters inclusive
- [ ] No duplicates within the batch
- [ ] No file outside the owned glob set modified
- [ ] Terminology guard green, **no lockfile drift**, census gate green

## Risks

| Risk | Mitigation |
|---|---|
| **README frontmatter drifts the lockfile** — the highest-probability CI break in this WP | T020 restricts to two keys and verifies drift immediately, not at the end |
| Overloaded terms (`primary`, `merge`, `routing`) used bare in authored prose | T018 calls this out; terminology guard catches survivors |
| Adjacent 2026-06/07 decisions produce near-duplicates | T017 flags clusters before authoring |
| Editing files owned by WP03 | Glob boundary stated; `git diff --name-only` before finishing |

## Reviewer Guidance

1. **Check `README.md` frontmatter first.** Exactly two keys. Anything more is a lockfile hazard and must be rejected even if CI happens to be green at review time.
2. **Read ten descriptions cold** — do they say what was decided?
3. **Grep the diff for bare overloaded terms**: `primary`, `merge`, `routing` used without naming the sense.
4. **Confirm the ownership boundary**: `git diff --name-only` shows only `2026-06`/`2026-07`/`2026-08` files and `README.md`.
5. **Verify pure insertions** for the 47 dated files — no modifications to existing keys.
6. **Count is exactly 48.**

## Activity Log

- 2026-08-05T20:18:15Z – claude:opus-5:curator-carla:implementer – shell_pid=55785 – Assigned agent via action command
- 2026-08-05T20:26:54Z – claude:opus-5:curator-carla:implementer – shell_pid=55785 – 49 files in batch: 47 dated ADRs (2026-06..08) got a new description, 2026-07-14-1 already carried a compliant one, README.md got exactly title+description. All 49 descriptions 50-180 chars, unique, pure insertions. Lockfile drift=False; terminology + ADR census guards green.
- 2026-08-05T20:28:03Z – claude:opus-5:reviewer-renata:reviewer – shell_pid=65933 – Started review via action command
- 2026-08-05T20:33:55Z – user – shell_pid=65933 – Review passed: 49-file batch verified. 2026-07 holds 23 files (not 22 as the prompt stated), and 2026-07-14-1-canonical-cli-console-seam.md is confirmed byte-for-byte untouched with its pre-existing 178-char description, so 47 newly described + 1 pre-existing + 1 README = 49. README.md frontmatter is exactly ['description','title'] per scripts.docs._inventory.parse_frontmatter; inventory_lockfile.py exits 0 with drift=False (698/698 generated/committed). Implementer commit 852c9cb6d touches 48 files, all inside the owned glob (2026-06/07/08 + README), zero deletions, every dated file a single-line insertion immediately after title; the only non-description added lines are the README's own frontmatter fence and title key. Descriptions are hand-authored and decision-specific: no duplicates, no shared 24-char prefixes, no shared 3-word openers, lengths 130-180. Overloaded terminology handled correctly: 2026-06-24-2 names 'repository-root checkout' and 'mission Target Ref, not the protected Primary Branch'; 2026-06-05-1 uses 'local lane consolidation' and 'publish layer' and avoids bare 'merge' entirely; 2026-07-30-1 names 'the lane-consolidation sense'; 2026-06-24-1/2026-06-25-1 say 'PRIMARY partition'/'PRIMARY-partition kinds'. Grep of added descriptions for primary/merge/routing returned only those sense-named hits and zero bare uses. Adjacency cluster is genuinely differentiated (MissionResolver Protocol + AST allowlist vs meta.json write-branch anchor vs DRG edges/559-entry graph.yaml migration vs GLOSSARY_PACK + executable ASSET gate). Accuracy spot-checked against the Decision sections of 2026-07-08-1, 2026-06-24-2, 2026-07-26-1, 2026-07-21-1, 2026-07-30-1, 2026-08-04-1 and 2026-06-30-1 - all faithful. Guards green: tests/architectural/test_no_legacy_terminology.py + tests/docs/test_adr_content_invariance.py, 12 passed.
