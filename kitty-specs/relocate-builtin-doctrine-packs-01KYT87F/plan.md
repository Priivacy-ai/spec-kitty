# Implementation Plan: Relocate Built-In Doctrine to packs/built-in

**Branch**: `feat/relocate-builtin-doctrine-packs` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/relocate-builtin-doctrine-packs-01KYT87F/spec.md`

## Summary

Relocate the built-in doctrine artefact *contents* (the 9 `<kind>/built-in/` dirs, **flattened** to
`packs/built-in/<kind>/`, + the 14 `*.graph.yaml` fragments) from `src/doctrine/**` to a top-level
`packs/built-in/**`; introduce one shared `resolve_pack_root(tier)` path seam; repoint the loader,
the per-kind repositories, **and the graph-regeneration surface** (extractor + `_doctrine_root()`);
ship in both wheel and sdist; and prove behavior-preservation by **full-projection graph identity**
(URNs + labels + tags + edge `when`/`reason`, not cardinality). **Phase 1 = relocate + repoint +
shared path resolver + regeneration repoint.** Deferred per the two adversarial squads: the
**`missions/` tree** (Phase 1b — kernel/`__file__`-layer readers can't route through the doctrine
resolver, C-004), loader/schema convergence + `kernel` extraction + schema relocation (Phase 2 /
C-002-C-003), and the dead `#1624` fold (already closed upstream).

## Technical Context

**Language/Version**: Python 3.11+ (DIR-002)
**Primary Dependencies**: hatchling (build/packaging), `importlib.resources` (resolution), pydantic + ruamel.yaml + jsonschema (existing doctrine deps); pytest / mypy --strict / ruff (DIR-005/006)
**Storage**: Filesystem — doctrine pack content as `.yaml/.yml/.md/.json/.template/.csv` data files (no database)
**Testing**: pytest — golden-fixture graph-identity parity; three-part filesystem/resolved-path/anchor guard; behavioral overlay tests; **two-layout install matrix** (editable checkout + clean-venv wheel); architectural guards (`test_layer_rules`, `test_builtin_graph_seam`, `test_wheel_packaging`); `test_no_legacy_terminology`
**Target Platform**: Cross-platform CLI — Linux / macOS / Windows (DIR-001)
**Project Type**: single (Python `src/` monorepo + a new top-level `packs/` data root)
**Performance Goals**: N/A — relocation is behavior-preserving; graph-load parity (324/892) is the bar, not throughput
**Constraints**: Content-only (no `.py` moves, C-001); graph **identity** preserved (NFR-001); loader/schema convergence deferred (C-002); schemas **stay** in `src/doctrine/schemas/` (C-003, kernel-coupled); layer direction `doctrine <- charter` preserved (C-004); wheel **and** sdist parity (FR-007)
**Scale/Scope**: ~600 data files across 9 `built-in/` kind dirs + 14 `*.graph.yaml` fragments + move-dispositioned template trees; ~10 content repositories + the enumerated readers repointed through one shared resolver

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **DIR-002 (Python 3.11+)**: ✅ no new runtime; pure relocation.
- **DIR-004 (PyPI distribution)**: ⚠️ load-bearing — the top-level `packs/` is outside `src/**`, so both the wheel (`force-include`) and the sdist `include` must be extended or installed distributions lose all built-in doctrine. Gated by FR-007 / NFR-002 (build-and-inspect both artifacts).
- **DIR-005 (tests for new behavior)**: ✅ golden fixture, three-part guard, overlay tests, two-layout matrix all ATDD-first (red before green).
- **DIR-006 (mypy --strict / ruff, no new suppressions)**: ✅ NFR-004.
- **DIR-009 (breaking change → CHANGELOG)**: ✅ FR-012 (migration note + CHANGELOG); the pack-path change is consumer-visible.
- **C-004 layer direction (`doctrine <- charter <- specify_cli`)**: ✅ the shared resolver stays in the doctrine layer; must not import upward. Preserved by `test_layer_rules`.
- **Terminology Canon**: ✅ "Mission" not "feature"; guarded by `test_no_legacy_terminology`.

**No unjustified violations.** The one risk (DIR-004 packaging) is a named, gated requirement, not an exception.

## Project Structure

### Documentation (this mission)

```
kitty-specs/relocate-builtin-doctrine-packs-01KYT87F/
├── plan.md                 # This file
├── research.md             # Phase 0: resolver-strategy + packaging decisions
├── data-model.md           # Phase 1: entities (pack root, content inventory, graph-identity fixture)
├── quickstart.md           # Phase 1: how to verify the relocation locally
├── occurrence_map.yaml     # Phase 1: FR-002 content inventory (every reader, move/stay)
├── contracts/
│   ├── resolve-pack-root.md    # the shared resolver contract (editable + installed)
│   └── packaging-parity.md     # wheel+sdist parity contract
└── tasks.md                # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
packs/                                  # NEW top-level data root (shipped in wheel + sdist)
└── built-in/                           # the relocated built-in pack (base tier)
    ├── <kind>/…                        # 9 moved kind dirs: agent_profiles, directives, procedures,
    │                                   #   tactics, paradigms, styleguides, toolguides, assets, glossary_packs
    ├── *.graph.yaml                    # 14 moved DRG fragments
    └── …                               # move-dispositioned template trees (per occurrence_map.yaml)

src/doctrine/                           # CODE STAYS HERE
├── drg/loader.py                       # built_in_graph_source() repointed → packs/built-in
├── <kind>/repository.py                # each built_in_dir default repointed via shared resolver
├── pack_paths.py (NEW)                 # resolve_pack_root(tier): editable + installed resolution
└── schemas/                            # STAYS (C-003, kernel-coupled validation infra)

src/kernel/                             # UNTOUCHED (C-002)
src/specify_cli/, src/charter/          # readers with literal src/doctrine paths repointed (per inventory)

tests/
├── doctrine/drg/test_builtin_graph_seam.py   # UPDATED (name assertion) — FR-010
├── doctrine/test_wheel_packaging.py          # UPDATED (paths + legacy inversion) — FR-010
├── doctrine/test_pack_relocation_identity.py # NEW golden-fixture parity — NFR-001
├── doctrine/test_pack_root_resolver.py       # NEW two-layout matrix — FR-006
└── architectural/…                            # layer/packaging guards extended
```

**Structure Decision**: Single Python project. Introduce a top-level `packs/` data root (sibling to
`src/`) shipped as package data; the doctrine code remains under `src/doctrine`. A new
`src/doctrine/pack_paths.py` owns `resolve_pack_root(tier)` — the single resolution seam.

## Complexity Tracking

*No Charter Check violations requiring justification.* The DIR-004 packaging concern is handled as a
first-class requirement (FR-007/NFR-002), not a complexity exception.

## Implementation Concern Map

> Concerns are architectural areas, not work packages. `/spec-kitty.tasks` translates them into WPs.

### IC-01 — Content inventory, disposition & baseline fixture capture

- **Purpose**: (a) Enumerate **every** reader — `files("doctrine*")`, literal `src/doctrine/...` strings, **and `Path(__file__)`-relative** idioms (the last are invisible to a files()/string sweep) — across doctrine, `specify_cli`, `charter`, `kernel`, each marked move/stay. (b) **Capture the pre-move golden fixture** (full-model projection — nodes `(urn,label,tags)`, edges `(source,relation,target,when,reason)`) BEFORE any move.
- **Relevant requirements**: FR-002; NFR-001; feeds FR-001/FR-004/FR-013; C-002 (missions defer), C-003 (schemas stay).
- **Affected surfaces**: `occurrence_map.yaml`; `graph-identity.baseline.json`; sweeps incl. `kernel/paths.py`.
- **Sequencing/depends-on**: none (**first** — the fixture MUST be captured here, before IC-03; a naive IC→WP order that captures it in IC-06 would baseline the *moved* graph and silently pass).
- **Risks**: an unclassified reader → silent partial move; the two `.py` asset payloads (assets/built-in, toolguides/built-in) must be whitelisted so a "no .py" guard doesn't false-positive.

### IC-02 — Shared pack-root resolver

- **Purpose**: `resolve_pack_root(tier)` in `src/doctrine/pack_paths.py` — one seam that locates `packs/built-in/` in an **editable checkout** (repo-root `packs/`) and an **installed distribution**, and org/project roots for their tiers.
- **Relevant requirements**: FR-005, FR-006; NFR-005.
- **Affected surfaces**: new `src/doctrine/pack_paths.py`; consumed by loader + repositories.
- **Sequencing/depends-on**: IC-01 (dispositions define what resolves where).
- **Risks**: `packs/built-in/` is **not** a Python package → `files("doctrine")` cannot address it; resolver must not import upward (C-004). Editable-vs-wheel duality is the crux.

### IC-03 — Content relocation (git mv)

- **Purpose**: `git mv` the move-set (9 kind dirs + 14 fragments + move-dispositioned template trees) `src/doctrine/** → packs/built-in/**`, preserving history.
- **Relevant requirements**: FR-001; C-001.
- **Affected surfaces**: `packs/built-in/**`, `src/doctrine/**`.
- **Sequencing/depends-on**: IC-01 (move-set), IC-02 (resolver ready to point at new home).
- **Risks**: partial move; `.gitignore` swallowing the new tree; git-history loss if copied not moved.

### IC-04 — Seam repointing

- **Purpose**: Repoint `built_in_graph_source()`, every content repository's `built_in_dir` default, every moved-tree reader, and the literal `src/doctrine/agent_profiles/built-in` string in `specify_cli` to resolve via IC-02.
- **Relevant requirements**: FR-003, FR-004; NFR-005.
- **Affected surfaces**: `src/doctrine/drg/loader.py`, `src/doctrine/<kind>/repository.py` (×~10), enumerated readers in `specify_cli`/`charter`.
- **Sequencing/depends-on**: IC-02, IC-03.
- **Risks**: a missed reader (esp. non-`files()` string paths) reads an empty dir → silent degradation.

### IC-05 — Packaging (wheel + sdist)

- **Purpose**: Ship `packs/built-in/` in **both** the monolith wheel (hatch `force-include`) and the sdist (`include` extended beyond `src/**`); remove the moved content's `src/doctrine` package-data globs.
- **Relevant requirements**: FR-007; NFR-002; DIR-004.
- **Affected surfaces**: root `pyproject.toml` `[tool.hatch.build.targets.{wheel,sdist}]`.
- **Sequencing/depends-on**: IC-03.
- **Risks**: sdist silently drops `packs/` (outside `src/**`); build-green-but-empty (cf. the pre-spec empty-wheel finding).

### IC-06 — Parity assertions, guards & overlay behavior

- **Purpose**: Assert graph identity against the IC-01 fixture (full projection incl. `when`); three-part src/doctrine guard; behavioral overlay tests (tier override, `_tag_source` origin, additive edges); **full** doctor gate (`skipped_profiles==[]` + no `org_drg` errors + no skipped glossary packs); per-repository "resolved dir exists **and non-empty**" loud-failure assertion.
- **Relevant requirements**: NFR-001, NFR-006, FR-008, FR-009; SC-001/002/003.
- **Affected surfaces**: new `test_pack_relocation_identity.py`, `test_pack_root_resolver.py` (two-layout + symlink matrix), guard test, overlay test.
- **Sequencing/depends-on**: fixture captured in IC-01; assertions run after IC-04/IC-05.
- **Risks**: cardinality/triple-only checks are gameable (must use full projection); a missed repoint returns `[]` build-green unless the non-empty assertion exists.

### IC-07 — Breaking tests, docs, CHANGELOG

- **Purpose**: Update `test_builtin_graph_seam.py` (`name == "doctrine"` → new home) and `test_wheel_packaging.py` (path expectations + legacy-absent inversion); sweep live (non-ADR) references + regen docs retrieval-index/completion-manifest; `.gitignore` audit; migration note + CHANGELOG.
- **Relevant requirements**: FR-010, FR-011, FR-012; DIR-009.
- **Affected surfaces**: the two tests; live docs; `docs/migrations/`; `CHANGELOG.md`; `.gitignore`.
- **Sequencing/depends-on**: IC-04, IC-05.
- **Risks**: touching immutable ADR snapshots (must not); missing a CI-only terminology/retrieval-index gate.

### IC-08 — Graph-regeneration surface repoint

- **Purpose**: Repoint `_doctrine_root()` (detection + write-target, `specify_cli/cli/commands/doctrine.py`) and `extractor.py`'s `_PATH_KIND_PATTERNS` (hardcoded `src/doctrine/<kind>/built-in/…$` regexes) + content walks to the **flattened** `packs/built-in/<kind>/` home, so `spec-kitty doctrine regenerate-graph` still works. Update the regen-parity tests (`test_graph_sharding_equality`, `test_sharding_silent_degrade`, `migration/test_extractor(_projection)`, `test_path_ref_resolver`).
- **Relevant requirements**: FR-013 (High — daphne blocker); FR-010.
- **Affected surfaces**: `src/doctrine/drg/migration/extractor.py`, `specify_cli/cli/commands/doctrine.py`, the 5 regen-parity tests.
- **Sequencing/depends-on**: IC-03 (move done), IC-02 (resolver). **Not severable** — a frozen regeneration surface violates the "fragments are generated, not hand-maintained" invariant.
- **Risks**: flatten drops the inner `built-in/` level the regex patterns assume — patterns must be rewritten, not root-swapped.

> **Dropped**: former #1624 fold — already CLOSED upstream (fixed by `tooling-stability-guard-coherence-01KTRC04`; `merge.py:387`/`models.py` already typed). Flag CLAUDE.md's stale Deferred Items list in the PR.
> **CI**: extend the existing `clean-install-verification` job (`.github/workflows/ci-quality.yml`) with a post-install `spec-kitty doctor doctrine --json` assertion (CI-facing half of NFR-002), mirroring the shared-package-boundary WP09.
> **Tracker (DIR-012)**: file a sub-issue under **#2467** framed *prerequisite-to* (not part-of) the pack-split keystone, before implementation starts.
