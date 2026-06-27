---
work_package_id: WP07
title: Redirect-stub generator + redirect map + coverage-vs-baseline + docs-pages.yml wiring
dependencies:
- WP02
- WP03
requirement_refs:
- FR-006
- NFR-002
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T040
- T041
- T042
- T043
- T044
- T045
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/redirect_stub_generator.py
create_intent:
- scripts/docs/redirect_stub_generator.py
- scripts/docs/redirect_map.yaml
- tests/docs/test_redirect_stub_generator.py
execution_mode: code_change
owned_files:
- scripts/docs/redirect_stub_generator.py
- scripts/docs/redirect_map.yaml
- tests/docs/test_redirect_stub_generator.py
- .github/workflows/docs-pages.yml
role: implementer
tags: []
shell_pid: "1501867"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Build the **redirect-stub generator** (Mission A's D4 mechanism), the **redirect map** (derived from `occurrence_map.yaml` `moves:`), and the **coverage check** against WP02's committed baseline-URL manifest (NFR-002), and **wire the generator into `.github/workflows/docs-pages.yml`** between the DocFX build and the artifact upload. This is IC-05a.

## Context

`contracts/redirect-stub.md` is the authority. DocFX on GitHub Pages has **no native redirect**, so every moved/deleted URL is preserved by a generated **`<meta http-equiv="refresh">` stub** emitted at the old path into `_site`.

**Redirect map provenance (avoids multi-writer):** the redirect map is **derived from `occurrence_map.yaml` `moves:`** (which already enumerates every old→new path-pair) plus the per-file expansion of each directory move. WP07 **solely owns** `scripts/docs/redirect_map.yaml` and generates it from the move spine — the move WPs (WP03/WP04/WP06/WP10) do **not** hand-append to it; they ensure their moves are represented in `moves:`. This keeps the map single-writer.

**Coverage denominator:** WP02's committed `scripts/docs/redirect_baseline_urls.json` (the **pre-move** URL set). A baseline URL is covered iff it resolves directly OR a stub exists at that path pointing to a live target. **Contract: `uncovered == []`** — 100% (NFR-002). A non-empty uncovered set is a CI failure.

**CI wiring:** add a step to `.github/workflows/docs-pages.yml` that runs `redirect_stub_generator.py` **after** the `Build documentation` (`docfx docfx.json`) step and **before** `Upload artifact` (`actions/upload-pages-artifact@v3`), so stubs land in `_site` before publish; the coverage check runs in the same job and fails the build on any uncovered baseline URL.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-006 (the DocFX redirect mechanism + per-move stubs + coverage), NFR-002 (100% of captured baseline URLs resolve). Consumes WP02's baseline manifest; depends on WP03 (the moves to redirect from).

## Subtasks

### T040 — Derive the redirect map from `occurrence_map.yaml` `moves:`
Generate `scripts/docs/redirect_map.yaml` (`{old_path: new_path}`) from the `moves:` spine, expanding directory pairs to per-file old→new URLs (including the pinned `era_less_pinned` ADR filenames and the `relocate-with-alias` CHANGELOG). The map is single-writer (WP07-owned), derived deterministically — a regen is diff-stable.

### T041 — `generate(redirect_map, site_dir) -> emitted_stubs`
Implement the generator: for each `old_path → new_path`, emit a stub at `old_path` inside `_site` with a `<meta http-equiv="refresh" content="0; url=<new_path>">` page (client-side redirect — the only primitive on static GitHub Pages). A stub MUST resolve to a live `new_path` (no stub may point at a 404).

### T042 — `check_coverage(baseline, redirect_map, site_dir) -> uncovered[]`
Implement the coverage check: a baseline URL (from WP02's manifest) is covered iff it resolves directly OR a stub exists at that path pointing to a live target. Return the uncovered set; assert `uncovered == []`. Each uncovered entry is a dead public URL → CI failure.

### T043 — Test the generator + coverage
Author `tests/docs/test_redirect_stub_generator.py`: a fixture move-map + fixture `_site` → stubs emitted at the right old paths with correct `<meta refresh>` targets; a stub pointing at a missing target → flagged (no-404 invariant); a baseline URL with no stub and no direct resolution → appears in `uncovered` (coverage RED). Use realistic published-URL shapes.

### T044 — Wire into `docs-pages.yml` (between build + upload)
Add the generator step to `.github/workflows/docs-pages.yml` **after** `Build documentation` and **before** `Upload artifact`, plus the coverage-check step (fails the job on any uncovered baseline URL). Name the exact steps. Do not reorder the existing build/upload steps.

### T045 — Verify coverage == 100% against the committed baseline
Run the coverage check against WP02's committed baseline manifest + the WP03 moves' redirect map: confirm `uncovered == []`. (If WP06/WP10 moves are not yet landed at run time, document the partial coverage and the dependency — the full 100% is asserted once WP10's shadow-tree redirects land; WP14's dry-run is the final whole-tree gate.)

## Surfaces & Loci

| Surface | Role | Notes |
|---------|------|-------|
| `scripts/docs/redirect_stub_generator.py` | new | `generate()` + `check_coverage()` |
| `scripts/docs/redirect_map.yaml` | new (single-writer) | derived from `occurrence_map.yaml` `moves:` |
| `scripts/docs/redirect_baseline_urls.json` | consumed | WP02's committed pre-move denominator |
| `.github/workflows/docs-pages.yml` | edited | stub step **between** `Build documentation` + `Upload artifact` |
| `tests/docs/test_redirect_stub_generator.py` | new | emit + no-404 + coverage-RED-on-gap |

Stub primitive: `<meta http-equiv="refresh" content="0; url=<new_path>">` (only redirect available on static GitHub Pages). Contract: `uncovered == []`.

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-006 (DocFX redirect mechanism + per-move stubs + CI wiring) | T040, T041, T044 |
| NFR-002 (100% baseline coverage) | T042, T043, T045 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Depends on WP02 (baseline) + WP03 (the moves). WP10 (shadow trees) also feeds redirect entries — coordinate via `moves:`.

## Definition of Done

- [ ] `scripts/docs/redirect_map.yaml` derived (single-writer) from `occurrence_map.yaml` `moves:`, per-file expanded, diff-stable.
- [ ] `generate()` emits `<meta refresh>` stubs at old paths into `_site`; **no stub points at a 404**.
- [ ] `check_coverage()` returns `uncovered`; asserts `== []` against WP02's committed baseline manifest.
- [ ] `tests/docs/test_redirect_stub_generator.py` green (emit correctness + no-404 + coverage-RED-on-gap).
- [ ] `docs-pages.yml` runs the generator **between build and upload**, plus the coverage gate (fails on uncovered).
- [ ] **Redirect/back-compat in place so no URL breaks**: this WP IS the URL-continuity mechanism — every baseline URL resolves directly or via a stub.
- [ ] `ruff` + `mypy` clean on the new script + test; no new dependency.

## Risks & Reviewer Guidance

- **Reviewer (NFR-002 focus):** confirm the coverage check uses WP02's **pre-move** baseline (not a post-move reconstruction) — otherwise the 100% is unfalsifiable.
- **Multi-writer redirect map** is the design hazard — confirm WP07 solely owns `redirect_map.yaml` and derives it from `moves:`; move WPs must not hand-edit it.
- **Stub → 404** is a silent dead-link — the no-404 invariant must be tested.
- CI step ordering matters: stubs must land in `_site` **before** upload.

## Activity Log

- (populated at implement time)
- 2026-06-27T13:37:51Z – claude:opus:python-pedro:implementer – shell_pid=1421969 – Assigned agent via action command
- 2026-06-27T14:24:17Z – claude:opus:python-pedro:implementer – shell_pid=1421969 – redirect-stub generator + coverage gate: redirect_map single-writer from moves:, 165/168 covered (3 WP-pending), no stub→404, 11 tests incl RED-on-gap, CI inject+verify wired, ruff/mypy 0
- 2026-06-27T14:24:41Z – claude:opus:reviewer-renata:reviewer – shell_pid=1501867 – Started review via action command
- 2026-06-27T14:29:22Z – user – shell_pid=1501867 – Review passed: redirect_map single-writer diff-stable, only docs/3x published (verified), no stub->404, coverage non-vacuous (165/168, 3 legit WP-pending), RED-on-gap proven, CI inject+verify between build+upload, ruff/mypy 0
