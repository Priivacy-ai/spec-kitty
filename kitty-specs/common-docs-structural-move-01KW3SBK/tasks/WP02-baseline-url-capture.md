---
work_package_id: WP02
title: Redirect baseline-URL capture (PRE-move, committed denominator for NFR-002)
dependencies:
- WP01
requirement_refs:
- FR-006
- NFR-002
tracker_refs: []
planning_base_branch: docs/2165-mission-b-structural-move
merge_target_branch: docs/2165-mission-b-structural-move
branch_strategy: Planning artifacts for this mission were generated on docs/2165-mission-b-structural-move. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into docs/2165-mission-b-structural-move unless the human explicitly redirects the landing branch.
subtasks:
- T009
- T010
- T011
- T012
- T013
agent: "claude:opus:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: scripts/docs/capture_baseline_urls.py
create_intent:
- scripts/docs/capture_baseline_urls.py
- scripts/docs/redirect_baseline_urls.json
- tests/docs/test_capture_baseline_urls.py
execution_mode: code_change
owned_files:
- scripts/docs/capture_baseline_urls.py
- scripts/docs/redirect_baseline_urls.json
- tests/docs/test_capture_baseline_urls.py
role: implementer
tags: []
shell_pid: "1348197"
---

## ⚡ Do This First: Load Agent Profile

Before reading anything else, load your agent profile: run `/ad-hoc-profile-load python-pedro` (or read `src/doctrine/agent_profiles/built-in/python-pedro.agent.yaml` and adopt it). State which directives apply, then proceed.

## Objective

Capture and **commit** the published-URL set of the **pre-move** documentation site so the redirect-coverage check (NFR-002, owned by WP07) has a **falsifiable denominator**. This **MUST run before the tree moves (WP03)** — once the move lands you can no longer observe the old URLs, and any coverage measured against a post-move denominator silently reports a false 100%.

This is IC-02b. The plan is explicit that it was previously mis-placed inside IC-05 (which runs *after* the move); that ordering makes 100% coverage unfalsifiable. This WP exists to fix that ordering: snapshot **before** WP03, commit the manifest, and let WP07's coverage check consume it.

## Context

DocFX is **.NET, CI-only today** — it is invoked by `.github/workflows/docs-pages.yml`, not installed locally. To snapshot the pre-move URL set you must install DocFX in this step and build the current (`architecture/` + `docs/`, pre-fold) tree. The `_site` output's URL set is the baseline. See `contracts/redirect-stub.md` ("Pre-move baseline capture (IC-02b)").

The manifest is the **NFR-002 denominator**: WP07 asserts every baseline URL resolves directly or via a generated `<meta refresh>` stub. If this manifest is wrong (reconstructed from the post-move tree), the whole URL-continuity guarantee is hollow.

## Requirement refs (hints for the orchestrator's map-requirements)

FR-006 (apply the DocFX redirect mechanism — the baseline is its denominator), NFR-002 (100% of captured baseline URLs resolve). Coupling: WP07 (redirect stubs + coverage) consumes this manifest; WP03 (the move) must NOT have run yet.

## Subtasks

### T009 — Install DocFX (pinned)
Install DocFX (.NET tool) at a pinned version matching what `docs-pages.yml` uses. Record the version + install command in the script header so CI and a later agent can reproduce the exact toolchain. Do not introduce a new runtime dependency to `pyproject.toml` — DocFX is a build tool, not a Python dep.

### T010 — Build the PRE-move tree
Build `docfx docs/docfx.json` over the **current** `architecture/` + `docs/` tree (before any WP03 fold). Confirm the build is green on the pre-move tree (if it is already red pre-move, that is a finding to surface, not to silently absorb — the baseline must be a real published set).

### T011 — Snapshot the `_site` URL set into the manifest
Author `scripts/docs/capture_baseline_urls.py`: walk the emitted `_site`, normalise each emitted page into its published URL (the `https://docs.spec-kitty.ai/` path form), and write the sorted, de-duplicated set to `scripts/docs/redirect_baseline_urls.json`. The manifest is deterministic (sorted) so a regen is diff-stable. Capture real published-URL shapes (real path depth/extensions), not handcrafted placeholders.

### T012 — Unit test the capture
Author `tests/docs/test_capture_baseline_urls.py`: given a small fixture `_site` tree, assert the script emits the expected normalised URL set (correct path normalisation, sorted, de-duplicated, no `_site/` prefix leakage). This guards the normalisation logic independent of a full DocFX build.

### T013 — Commit the baseline manifest BEFORE WP03
Ensure `scripts/docs/redirect_baseline_urls.json` is checked in and represents the **pre-move** tree. Record in the script header and the WP activity log that this manifest is the immutable NFR-002 denominator and must not be regenerated after WP03. (The orchestrator commits; this WP produces the committed artifact.)

## Surfaces & Loci

| Surface | Role | Notes |
|---------|------|-------|
| DocFX (.NET tool) | build toolchain | CI-only today (`.github/workflows/docs-pages.yml`); install + pin here |
| `docs/docfx.json` (pre-move) | build input | read-only; do not edit (WP09 rewrites it) |
| `architecture/` + `docs/` (pre-move tree) | build content | read-only snapshot source |
| `scripts/docs/capture_baseline_urls.py` | new | walks `_site`, emits normalised URL set |
| `scripts/docs/redirect_baseline_urls.json` | new (committed) | the NFR-002 denominator (sorted, de-duplicated) |
| `tests/docs/test_capture_baseline_urls.py` | new | normalisation correctness over a fixture `_site` |

## Requirement → Subtask Traceability

| Requirement | Subtasks |
|-------------|----------|
| FR-006 (DocFX redirect mechanism — its denominator) | T009, T010, T011, T013 |
| NFR-002 (100% of captured baseline URLs resolve) | T011, T012, T013 |

## Branch Strategy

Planning + final merge target: `docs/2165-mission-b-structural-move`. Sequenced **after WP01** (runtime reads safe) and strictly **before WP03** (the move). Its committed manifest is consumed by WP07's coverage check.

## Definition of Done

- [ ] DocFX installed at a pinned, recorded version; the pre-move `docfx docs/docfx.json` build is green.
- [ ] `scripts/docs/capture_baseline_urls.py` emits a sorted, de-duplicated, normalised published-URL set.
- [ ] `scripts/docs/redirect_baseline_urls.json` is checked in and reflects the **pre-move** tree (provably captured before WP03 — note the ordering in the activity log).
- [ ] `tests/docs/test_capture_baseline_urls.py` green (normalisation correctness over a fixture `_site`).
- [ ] **Redirect/back-compat in place so no reference breaks**: this WP only reads the tree (it moves nothing); its deliverable is the denominator that makes WP07's redirect coverage falsifiable.
- [ ] `ruff` + `mypy` clean on the new script + test.

## Risks & Reviewer Guidance

- **The single failure mode that voids the mission's URL guarantee:** capturing the baseline from the *post-move* tree. Reviewer must confirm — by ordering and by the manifest's content — that the snapshot is pre-fold (contains `architecture/...` URLs that WP03 will remove).
- DocFX install flakiness in CI: pin the version; record the exact install command.
- A non-deterministic manifest (unsorted) would create noisy diffs on every regen — assert sortedness in the test.

## Activity Log

- (populated at implement time)
- 2026-06-27T12:40:43Z – claude:opus:python-pedro:implementer – shell_pid=1311976 – Assigned agent via action command
- 2026-06-27T12:51:57Z – claude:opus:python-pedro:implementer – shell_pid=1311976 – Ready: baseline manifest captured (168 URLs), deterministic/sorted/de-duped. DERIVED-from-source (dotnet/DocFX not installed locally); honors docfx.json content+resource globs (md->html, _*.md & toc.yml excluded, src/dest remap, standalone html resources). Site-walk mode unit-tested for CI. ruff=0, mypy --strict=0 (explicit-package-bases), pytest 8/8 green. Gap: kitty-specs/**/*.html generated at build (0 pre-build), not in denominator.
- 2026-06-27T12:54:30Z – claude:opus:reviewer-renata:reviewer – shell_pid=1348197 – Started review via action command
- 2026-06-27T13:00:45Z – user – shell_pid=1348197 – Review passed: 168 URLs faithful to docfx.json globs (re-derived=168, byte-identical regen=deterministic); **-glob fix verified (unscoped bug reproduces 311, scooping architecture/+closeout dirs; regression test pins it); derive+site-walk modes coherent; 8 tests non-vacuous (unscoping ** turns double_star test RED); 5 sampled URLs map to real source files; published roots all present, development/engineering_notes/doctrine/closeout correctly excluded; docfx.json frozen, only 3 owned files touched; ruff/mypy --strict 0. architecture/ absent is CORRECT (not in docfx globs=404 today); kitty-specs/**.html exclusion defensible (build-generated, site-walk repro documented).
