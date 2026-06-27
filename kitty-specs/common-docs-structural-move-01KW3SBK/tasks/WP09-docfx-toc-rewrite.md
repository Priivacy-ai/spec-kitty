---
work_package_id: WP09
title: docfx.json globs + every toc.yml → 13-section structure; DocFX build green
dependencies:
- WP03
requirement_refs:
- FR-007
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T054
- T055
- T056
- T057
- T058
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: docs/docfx.json
create_intent: []
execution_mode: code_change
owned_files:
- docs/docfx.json
- docs/**/toc.yml
- docs/llms.txt
- docs/index.md
role: implementer
tags: []
shell_pid: "1468138"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Rewrite `docs/docfx.json` content/exclude globs and **every** `toc.yml` to the 13-section Common Docs structure so the DocFX build stays green (FR-007). This is the `serialized_keys` slice of IC-05 — a deliberate, reviewed config rewrite (the occurrence map classifies `serialized_keys: manual_review`). It also coordinates the #648 site-generation contract (define the structure, do not build the site-gen).

## Context

`occurrence_map.yaml` `serialized_keys` is the authority: `docfx.json` content/exclude globs and every `toc.yml` `href` are serialized values pointing at doc paths; FR-007 requires rewriting them to the 13-section layout. The `moves:` entry for `docs/docfx.json`/`docs/llms.txt` marks them as **rewritten in place** (not relocated). The shim-registry.yaml *keys* are NOT touched (only its file location was a runtime concern — WP01/WP03).

**Category disjointness (bulk overlap):** WP08 owns the prose/path-literal references under `docs/**/*.md`; **WP09 owns only the serialized config** (`docfx.json` globs, `toc.yml` href, `llms.txt` entries, `docs/index.md` nav). The two are category-disjoint; sequenced after WP03. Flag the `docs/**` co-tenancy to the orchestrator as expected bulk overlap.

**The 13 sections:** `index`, `context`, `architecture`, `adr`, `plans`, `api`, `configuration`, `integrations`, `security`, `guides`, `operations`, `migrations`, `changelog`. Each section carries its own `index.md` (the ratchet floor; WP14 flips it blocking).

## Requirement refs (hints for the orchestrator's map-requirements)

FR-007 (rewrite `docfx.json` content globs + every `toc.yml` so the DocFX build stays green). Coordinate #648 (the structure this defines is the site-gen contract — do not build site-gen).

## Subtasks

### T054 — Rewrite `docs/docfx.json` content + exclude globs
Re-point the content/exclude globs to the 13-section layout (drop `architecture/`-root globs; add the new sections). Confirm no glob still references a removed `architecture/` path. The shim-registry keys are untouched.

### T055 — Rewrite every `toc.yml` href to the 13 sections
Enumerate every `toc.yml` under `docs/` and rewrite each `href` to the new locations. A `toc.yml` pointing at a moved path is a broken nav entry. Ensure the top-level TOC reflects all 13 sections.

### T056 — Update `docs/llms.txt` + `docs/index.md` nav
Re-point `llms.txt` entries and `docs/index.md` navigation to the 13-section homes (the single-entry-point requirement, SC-001). `docs/index.md` is the one root entry; confirm it links each section's `index.md`.

### T057 — DocFX build green on the post-move tree
Run `docfx docs/docfx.json` over the moved tree (DocFX installed in WP02). Confirm the build is green — no missing-file errors, no dangling TOC hrefs. This is the FR-007 acceptance.

### T058 — Verify + coordinate #648
Confirm the build is green and every section is reachable from `docs/index.md`. Record the 13-section structure as the #648 site-generation contract (coordinate only — do not build the site-gen).

## Surfaces & Loci

| Surface | Occurrence-map category | Edit |
|---------|-------------------------|------|
| `docs/docfx.json` | `serialized_keys: manual_review` | content/exclude globs → 13 sections |
| `docs/**/toc.yml` | `serialized_keys` | every `href` → new locations |
| `docs/llms.txt` | `moves:` (rewritten in place) | entries → 13-section homes |
| `docs/index.md` | nav | single entry point linking all 13 section `index.md` |

The 13 sections: `index`, `context`, `architecture`, `adr`, `plans`, `api`, `configuration`, `integrations`, `security`, `guides`, `operations`, `migrations`, `changelog`. shim-registry **keys** untouched.

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-007 (rewrite `docfx.json` globs + every `toc.yml`; DocFX build green) | T054, T055, T056, T057 |
| SC-001 (single entry point) | T056 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP03 (the move). Category-disjoint from WP08/WP12 under `docs/**` (serialized config only).

## Definition of Done

- [ ] `docs/docfx.json` content/exclude globs rewritten to the 13 sections; no glob references a removed `architecture/` path.
- [ ] **Every** `toc.yml` `href` re-pointed; no dangling nav entry.
- [ ] `docs/llms.txt` + `docs/index.md` re-pointed; `docs/index.md` is the single entry point linking all 13 sections (SC-001).
- [ ] **DocFX build green** on the post-move tree (FR-007 acceptance).
- [ ] **Redirect/back-compat in place so no reference breaks**: every TOC/glob/nav target resolves to a real moved file; the redirect stubs (WP07) cover the old published URLs.
- [ ] Category disjointness held (no prose-reference or frontmatter edits — those are WP08/WP12).

## Risks & Reviewer Guidance

- **Reviewer (FR-007 focus):** a green DocFX build is the gate — confirm no `toc.yml` href or `docfx.json` glob points at a moved/removed path.
- **Bulk overlap with WP08/WP12** — confirm WP09 touched only serialized config, not prose references or frontmatter fields.
- A missing section `index.md` will trip the anti-sprawl ratchet once WP14 flips it blocking — verify each section has one.

## Activity Log

- (populated at implement time)
- 2026-06-27T13:37:55Z – claude:opus:python-pedro:implementer – shell_pid=1421969 – Assigned agent via action command
- 2026-06-27T13:57:31Z – claude:opus:python-pedro:implementer – shell_pid=1421969 – docfx.json+toc+llms+index → 13-section layout (serialized-keys); empty globs/dangles are cross-WP-pending (adr←WP06, ops←WP04); DocFX build-green deferred to assembled-tree CI (no dotnet local)
- 2026-06-27T13:59:02Z – claude:opus:reviewer-renata:reviewer – shell_pid=1468138 – Started review via action command
- 2026-06-27T14:05:34Z – user – shell_pid=1468138 – Review passed: 13-section docfx/toc/llms/index, category-clean (4 owned files only, no prose/frontmatter bleed; index.md frontmatter de-version is owned entry-page identity, not WP12 doc_status backfill), all dangles cross-WP-pending (adr<-WP06, operations<-WP04, configuration/integrations/security/guides/api<-WP10 scaffold), DocFX build-green honestly deferred to assembled-tree CI; IC-01 guides/api verdict: REAL occurrence-map gap - FR-009 mandates Divio->guides/+api/+architecture/ but moves: spine omits tutorials/how-to->guides, reference->api, explanation->architecture (120 Divio files orphan, guides/api stay empty). NOT a WP09 defect (WP09 correctly built spec-mandated target config); operator to file IC-01 occurrence-map correction.
