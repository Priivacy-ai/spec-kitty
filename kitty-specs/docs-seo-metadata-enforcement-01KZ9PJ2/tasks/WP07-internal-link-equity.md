---
work_package_id: WP07
title: Internal link equity for high-intent pages
dependencies: []
requirement_refs:
- FR-009
- NFR-009
tracker_refs: []
planning_base_branch: feat/docs-seo-metadata-enforcement
merge_target_branch: feat/docs-seo-metadata-enforcement
branch_strategy: Planning artifacts for this mission were generated on feat/docs-seo-metadata-enforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/docs-seo-metadata-enforcement unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
- T038
agent: "claude:opus-5:reviewer-renata:reviewer"
shell_pid: "63540"
history:
- at: '2026-08-05T19:58:15Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/index.md
create_intent: []
execution_mode: code_change
model: claude-opus-5
owned_files:
- docs/index.md
- docs/guides/install-spec-kitty.md
- docs/guides/getting-started.md
- docs/api/slash-commands.md
- docs/api/index.md
role: curator
tags: []
task_type: implement
---

# Work Package Prompt: WP07 – Internal link equity for high-intent pages

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `curator-carla`
- **Role**: `curator`

## Objective

Put the two highest-intent pages — the install guide and the slash-command reference — **one click** from where readers actually land, without disturbing the navigation shape a prior mission deliberately chose.

## ⚠️ Do not modify `docs/toc.yml`

`docs/toc.yml` opens with a comment recording a prior mission's design:

> Exactly 2 top-level zone entries. Each zone has <=6 unexpanded top-level (immediate-child) entries … (FR-003, FR-015, NFR-003, C-005)

Zone 1 ("Using Spec Kitty") currently holds **exactly 6** immediate children — at the documented cap. Adding either page as a top-level entry would breach it.

Per decision `01KZ9Q2E397AB1WJYZMAP0A0VB`, one-click depth is achieved through `docs/index.md` body links and guide cross-links instead. **`docs/toc.yml` is not in this WP's owned files and must not be edited.**

A caution worth internalising: a search of `tests/` and `scripts/` found **no automated enforcement** of the zone count or the ≤6 cap. The constraint is advisory prose. Nothing in CI will stop you from breaching it — which is a reason to respect it deliberately, not a licence to ignore it.

## Context

**Current state, measured**:
- Neither `guides/install-spec-kitty.md` nor `api/slash-commands.md` is referenced from `docs/toc.yml`.
- `docs/index.md` links `guides/getting-started.md` but neither high-intent page directly.
- Both pages are two-to-three clicks deep behind intermediate index pages.

**Both pages already have excellent titles and descriptions** — this was verified live and is recorded in [`research.md`](../research.md) R-001. This WP is purely about reachability, not metadata.

**Existing link gates you must satisfy** (both already run in `docs-freshness.yml`):
- `scripts/docs/relative_link_fixer.py --check` — relative body-link correctness
- `scripts/docs/related_validator.py --strict` — `related:` frontmatter edge validity

## Subtasks

### T035 — Add one-click links from the documentation home

**Purpose**: `docs/index.md` is where readers land. A link here is the definition of one-click depth (NFR-009).

**Steps**:
1. Read `docs/index.md` in full before editing. It currently reads, around line 25:
   > New here? [Get started](guides/getting-started.md) walks you through installing Spec Kitty and running your first mission end to end — about 30 minutes, no prior Spec Kitty knowledge required.
2. Add direct links to **both** high-intent pages:
   - `guides/install-spec-kitty.md`
   - `api/slash-commands.md`
3. Write them as genuine prose for a reader with an actual intent, not a bare link dump. The install link should read as the answer to "how do I install this"; the slash-command link as the answer to "what commands are there". Someone scanning the home page should find their answer without reading the whole document.
4. Keep the existing getting-started link — it serves a different intent (guided walkthrough) than the install reference.
5. Use repo-relative Markdown links matching the file's existing convention.

**Files**: `docs/index.md`

**Validation**:
- [ ] Both pages linked directly from `docs/index.md`
- [ ] Links read as prose serving a reader intent, not a list
- [ ] Existing getting-started link preserved
- [ ] Link style matches the surrounding file

### T036 — Add cross-links from topically relevant guides

**Purpose**: Link equity comes from *relevant* pages, not just the home page. A link from an unrelated page is noise.

**Steps**:
1. Add reciprocal cross-links where they genuinely help a reader:
   - `guides/getting-started.md` → the install guide (a reader partway through setup wants the full install reference)
   - `guides/install-spec-kitty.md` → the slash-command reference (a reader who just installed wants to know what to type)
   - `api/index.md` → `api/slash-commands.md`, if not already prominent
2. Check what already exists before adding. `guides/install-spec-kitty.md` already carries a `related:` frontmatter list; extend it rather than duplicating intent in prose.
3. **Do not add links that do not serve a reader.** Gratuitous cross-linking for "SEO" degrades the docs and is not what FR-009 asks for.

**Files**: `docs/guides/getting-started.md`, `docs/guides/install-spec-kitty.md`, `docs/api/index.md`

**Validation**:
- [ ] Each added link serves an identifiable reader intent
- [ ] No duplicate links within a page
- [ ] `related:` frontmatter extended rather than duplicated in prose where applicable

### T037 — Satisfy the relative-link and related-edge validators

**Purpose**: New links are subject to two existing gates. Breaking them would trade one CI failure for another.

**Steps**:
1. ```bash
   PYTHONPATH=. uv run python scripts/docs/relative_link_fixer.py --check --repo-root .
   ```
2. ```bash
   PYTHONPATH=. uv run python scripts/docs/related_validator.py --strict --repo-root .
   ```
3. Fix anything reported. A `related:` entry must point at a real page; a relative link must resolve from its own file's location.
4. Also run the structural lint, since index completeness is one of its checks:
   ```bash
   uv run python packs/built-in/assets/docs_structural_lint.py \
     --styleguide packs/built-in/styleguides/common-docs.styleguide.yaml
   ```

**Validation**:
- [ ] Relative-link gate green
- [ ] Related-edge validator green
- [ ] Structural lint green

### T038 — Verify click depth against the built site

**Purpose**: Prove NFR-009 rather than assert it.

**Steps**:
1. Confirm from the source that both target pages are reachable by exactly one link traversal from `docs/index.md`:
   ```bash
   grep -nE "install-spec-kitty|slash-commands" docs/index.md
   ```
   Both must appear.
2. Confirm `docs/toc.yml` is unmodified:
   ```bash
   git diff --stat docs/toc.yml
   ```
   Must be empty.
3. If a local DocFX build is available, verify the rendered home page contains both hrefs:
   ```bash
   grep -oE 'href="[^"]*(install-spec-kitty|slash-commands)[^"]*"' docs/_site/index.html
   ```
   If .NET is not available locally, note that CI verifies this and record the source-level evidence instead.

**Validation**:
- [ ] Both pages linked from the home page source
- [ ] `docs/toc.yml` diff is empty
- [ ] Rendered evidence captured, or its absence explained

## Branch Strategy

- **Planning base branch**: `feat/docs-seo-metadata-enforcement`
- **Final merge target**: `feat/docs-seo-metadata-enforcement`
- Execution worktrees are allocated per computed lane from `lanes.json`. Consume the resolved path.
- This mission reaches `origin/main` only through a pull request.

## Definition of Done

- [ ] `docs/index.md` links both the install guide and the slash-command reference directly
- [ ] Links read as prose serving a reader intent
- [ ] Relevant guide cross-links added, none gratuitous
- [ ] `docs/toc.yml` **unmodified**
- [ ] Relative-link, related-edge, and structural-lint gates all green
- [ ] Click-depth evidence recorded

## Risks

| Risk | Mitigation |
|---|---|
| Editing `docs/toc.yml` and breaching a prior mission's design | File excluded from owned set; T038 asserts an empty diff |
| New relative links break the link gate | T037 runs both validators explicitly |
| Gratuitous cross-linking degrades the docs | T036 requires each link serve an identifiable intent; reviewer checks |
| `related:` edits break the edge validator | T037 covers it; extend existing lists rather than inventing new ones |

## Reviewer Guidance

1. **`git diff --stat docs/toc.yml` must be empty.** This is the prior mission's design boundary and the first thing to check.
2. **Read the added prose as a first-time visitor.** Does the home page now answer "how do I install this" and "what commands exist" without scrolling the whole page? If the links read as an SEO dump, reject.
3. **Check each cross-link serves a reader**, not a link-count target.
4. **Confirm both link validators pass** — new links are the most common way these gates go red.
5. **Verify no metadata was changed** on the two target pages; their titles and descriptions were already correct and are out of scope here.

## Activity Log

- 2026-08-05T20:18:45Z – claude:opus-5:curator-carla:implementer – shell_pid=55785 – Assigned agent via action command
- 2026-08-05T20:25:21Z – claude:opus-5:curator-carla:implementer – shell_pid=55785 – docs/index.md now links guides/install-spec-kitty.md and api/slash-commands.md as intent-shaped prose; cross-links added getting-started->install (Step 1 + related:) and install->slash-commands (Verification + related:); api/index.md already prominent, unchanged; docs/toc.yml untouched; all four gates green
- 2026-08-05T20:25:55Z – claude:opus-5:reviewer-renata:reviewer – shell_pid=63540 – Started review via action command
- 2026-08-05T20:36:03Z – user – shell_pid=63540 – Review passed (reviewer-renata verified on merits; transition deferred to orchestrator because the mission-level issue-matrix gate blocked it). Full reviewer evidence recorded in the review transcript.
