# Tasks: Relocate Built-In Doctrine to packs/built-in

**Mission**: relocate-builtin-doctrine-packs-01KYT87F | **Branch**: feat/relocate-builtin-doctrine-packs
Phase 1 (missions/ deferred to Phase 1b; loader/schema convergence + kernel = Phase 2).

## ⚠️ Pre-implement checklist (before any /spec-kitty.implement)
1. **`/spec-kitty.analyze`** must run first — `implement` is tool-gated on `analysis-report.md` (blocking).
2. ✅ **DIR-012 anchor**: [#3090](https://github.com/Priivacy-ai/spec-kitty/issues/3090) — filed as *prerequisite-to* #2467 (KEYSTONE).
3. ✅ **Phase 1b follow-on**: [#3091](https://github.com/Priivacy-ai/spec-kitty/issues/3091) — deferred `missions/` relocation tracked.

**Lane parallelism note**: `lanes.json` places WP04 (lane-d) and WP05 (lane-e) in the same `parallel_group` (a wave barrier); WP06's hard edge is WP03+WP04 only. WP06 may start once WP04 finishes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Finalize occurrence-map dispositions (files()/string/`__file__`/kernel sweep; confirm missions DEFER) | WP01 | |
| T002 | Capture graph-identity baseline (full projection) BEFORE any move | WP01 | |
| T003 | Enumerate exact move-set manifest (9 built-in dirs + 14 fragments) + 2 payload `.py` whitelist | WP01 | |
| T004 | Create `src/doctrine/pack_paths.py` `resolve_pack_root(tier)` (env→editable→installed→fail-closed) | WP02 | |
| T005 | `PackRootNotFound`; lazy `files("doctrine")`; layer-clean (C-004) | WP02 | |
| T006 | Two-layout + symlinked-checkout resolver test matrix | WP02 | |
| T007 | `git mv` 9 `<kind>/built-in/` → `packs/built-in/<kind>/` (flatten) | WP03 | |
| T008 | `git mv` 14 `*.graph.yaml` → `packs/built-in/` | WP03 | |
| T009 | `.gitignore` audit; verify move-set == manifest, no dual-home | WP03 | |
| T010 | Repoint `built_in_graph_source()` → resolver, fail-closed (drop `__file__` fallback) | WP04 | |
| T011 | Repoint 9 repository `built_in_dir` defaults; drop dead Traversable guards | WP04 | [P] |
| T012 | Repoint `specify_cli` hardcoded string (module-level import — #2986) + enumerated readers | WP04 | |
| T013 | `pyproject` wheel `force-include` packs + sdist `include packs/**` | WP05 | [P] |
| T014 | Packaging parity test (wheel+sdist exact path-set) + clean-venv import | WP05 | |
| T015 | Extend `clean-install-verification` CI job with `doctor doctrine` assertion | WP05 | |
| T016 | Repoint `_doctrine_root()` detection + write-target to flattened home | WP06 | |
| T017 | Repoint `extractor.py` `_PATH_KIND_PATTERNS` + content walks | WP06 | |
| T018 | Update 5 regen-parity tests; verify `regenerate-graph` round-trips | WP06 | |
| T019 | Full-projection identity assertion vs baseline | WP07 | |
| T020 | Three-part `src/doctrine` guard + per-repo exists-and-non-empty assertion | WP07 | |
| T021 | Overlay behavioral test (tier override, `_tag_source` origin, additive edges) | WP07 | |
| T022 | Full doctor-health gate (org_drg + glossary packs + skipped_profiles) | WP07 | |
| T023 | Update `test_builtin_graph_seam` + `test_wheel_packaging` (flattened) + `test_no_dead_doctrine_paths` | WP08 | |
| T024 | Live-ref sweep + docs retrieval-index/completion-manifest regen (ADR snapshots immutable) | WP08 | |
| T025 | Migration note + CHANGELOG; flag CLAUDE.md stale #1624 | WP08 | |

## Work Packages

### WP01 — Content inventory & baseline fixture capture (IC-01)
Goal: authoritative move/stay inventory + the pre-move graph-identity fixture. **Must run first** — the fixture must be captured before WP03 moves anything. Priority: P1. Independent test: `graph-identity.baseline.json` exists with 324 nodes/892 edges as full projections; occurrence-map has 0 unclassified readers. Subtasks: T001–T003. Deps: none. ~180 lines.

### WP02 — Shared pack-root resolver (IC-02)
Goal: `resolve_pack_root(tier)` — the single resolution seam, editable + installed + fail-closed. Priority: P1. Independent test: two-layout matrix (editable + clean-venv wheel + symlink) green. Subtasks: T004–T006. Deps: WP01. ~220 lines.

### WP03 — Content relocation (git mv, flatten) (IC-03)
Goal: relocate the 9 `<kind>/built-in/` dirs (flattened) + 14 fragments to `packs/built-in/`. Priority: P1. Independent test: move-set == manifest, every path a `git` rename (`-M` → R), no dual-home, gitignore clean. (NOT "tree loads" — the graph does not load until WP04 repoints the loader.) Subtasks: T007–T009. Deps: WP01, WP02. ~170 lines.

### WP04 — Seam repointing (IC-04)
Goal: repoint the loader, 9 repositories, and the `specify_cli` string reader through the resolver. Priority: P1. Independent test: `load_built_in_graph()` returns 324/892 from `packs/built-in`; no `files("doctrine.<kind>")` content anchors remain. Subtasks: T010–T012. Deps: WP02, WP03. ~240 lines.

### WP05 — Packaging (wheel + sdist) + CI (IC-05) — parallel to WP04
Goal: ship `packs/built-in/` in wheel+sdist; extend the clean-install CI job. Priority: P1. Independent test: built wheel+sdist carry exact path-set; clean-venv `doctor doctrine` resolves. Subtasks: T013–T015. Deps: WP03. ~200 lines.

### WP06 — Graph-regeneration surface repoint (IC-08)
Goal: repoint `_doctrine_root()` + `extractor.py` to the flattened home so `regenerate-graph` works; fix 5 regen-parity tests. Priority: P1. Independent test: `spec-kitty doctrine regenerate-graph` round-trips to identical fragments. Subtasks: T016–T018. Deps: WP03, WP04. ~230 lines.

### WP07 — Parity, guards & overlay behavior (IC-06)
Goal: the non-fakeable proofs — full-projection identity, three-part guard, loud-failure, overlay behavior, full doctor. Priority: P1. Independent test: all green post-move. Subtasks: T019–T022. Deps: WP04, WP05, WP06. ~250 lines.

### WP08 — Breaking tests, docs & CHANGELOG (IC-07)
Goal: update the tests the move breaks; migration note + CHANGELOG; docs regen. Priority: P2. Independent test: full suites green; docs freshness passes. Subtasks: T023–T025. Deps: WP04, WP05, WP06. ~230 lines.

**Dependency DAG**: WP01 → WP02 → WP03 → {WP04 ∥ WP05} → WP06 → WP07; WP08 after WP04/WP05/WP06.
**MVP**: WP01–WP04 (content moved + resolving from packs/built-in). **Parallel**: WP04 ∥ WP05.
