# Implementation Plan: Bundle-Freshness Content-Identity — Missing-File Robustness + Directive-Activation Visibility

**Branch**: `gk/2758-2759` (single_branch, stacked on `fix/2681-synthesized-drg-stale` / PR #2732) | **Date**: 2026-07-17 | **Spec**: [spec.md](./spec.md)
**Input**: `kitty-specs/bundle-freshness-hash-input-and-activation-01KXR0M1/spec.md` (bundles #2758 + #2759)

## Summary

(1) **Remove `references.yaml`** from the `synthesized_drg` hash input set (closes #2758). (2) **Add a
digest of the resolved directive set** (`[] if activated_directives is None else
resolve_config_activated_roots(...).directives`) — the sole activation input that varies `graph.yaml`
(closes #2759 for directive activation). The directive resolution is produced by a **shared charter-side
helper extracted from `_synthesis.py`**, called by BOTH the synthesizer and `compute_bundle_content_hash`,
so the fingerprint attests the graph by construction. Paradigms are inert for the graph and are NOT in the
identity. Reader/`promote`/`resynthesize` route through the single recipe → no reader/activate edits.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: `charter.compiler.resolve_config_activated_roots` (shared seam),
`charter.pack_context.PackContext` (the `activated_directives is None` three-state), `charter.hasher.hash_content`
**Storage**: `.kittify/config.yaml`; `.kittify/charter/{governance,directives,metadata}.yaml`; `synthesis-manifest.yaml`; `.kittify/doctrine/graph.yaml` (attested object)
**Testing**: pytest — `tests/charter/**`, `tests/specify_cli/charter_freshness/**`, `_synthesis`/pack-manager; red-first ATDD.
**Performance**: < 2s per `charter status/activate/deactivate/synthesize`; the `bundle→compiler` import is **function-local** (NFR-001); the per-`charter status` `load_doctrine_catalog()` cost is bounded by the < 2s envelope (NFR-002).
**Constraints**: never-raise recipe (catch resolver exceptions); no schema bump (C-012); one recipe + one directive-resolution authority (C-005); dead-symbol gate (C-007).
**Scale/Scope**: extract 1 shared helper; behavior-preserving refactor of 1 synthesizer call site; 1 recipe edit; focused tests.

## Charter Check

- **ATDD-first (C-011)** — red-first per WP. PASS (planned).
- **Single canonical authority (C-005)** — one hash recipe; one directive-resolution helper called by both
  the synthesizer and the hash (replaces the round-rejected `_load_default_pack`/8-key/paradigm variants). PASS by construction.
- **Architectural integrity (DIR-001)** — helper in `charter.compiler`; synthesizer (`specify_cli`) consumes
  it (allowed direction); hash (`charter.bundle`) consumes it **via a function-local import** (NFR-001, no
  init reorder / hot-path regression). PASS.
- **Dead-symbol gate (C-007)** — the public helper has two real callers → satisfies `test_no_dead_symbols`. PASS.
- **Fail-posture (NFR-003)** — `compute_bundle_content_hash` catches resolver exceptions
  (`UnknownArtifactIdError`/`CharterPackConfigError`/parse) → `None` → recoverable stale; never crashes. PASS (planned).

No violations → Complexity Tracking empty.

## Project Structure

```
src/charter/
├── compiler.py          # PRIMARY: extract resolve_synthesis_graph_directives(repo_root) -> list[str]
│                        #          = [] if PackContext.from_config(repo_root).activated_directives is None
│                        #            else resolve_config_activated_roots(repo_root).directives   (shared helper)
├── bundle.py            # PRIMARY: compute_bundle_content_hash appends the directive digest (function-local
│                        #          import of the helper); BUNDLE_CONTENT_HASH_FILES drops references.yaml;
│                        #          catch resolver exceptions -> None
└── hasher.py            # consumed

src/specify_cli/cli/commands/charter/
└── _synthesis.py        # REFACTOR (behavior-preserving): selected_directives + drg_nodes source from the
                         # shared helper (was inline _synthesis.py:76-107); selected_paradigms unchanged (inert)

src/specify_cli/charter_runtime/freshness/
└── computer.py          # NO change — routes through the recipe; _BUNDLE_FILES (synced_bundle) untouched (C-003)
```

**Structure Decision**: single-project CLI. Delta = shared helper in `charter.compiler`, behavior-preserving
`_synthesis.py` refactor, and the `bundle.py` recipe edit.

## Resolved Open Questions (binding decisions)

- **OQ-1 (one recipe change) → swap.** Keep the triad; replace `references.yaml` with the directive digest.
  One migration stale (FR-007). Triad stays (detects "charter recompiled, graph not re-synthesized").
- **OQ-2 (what activation is in the identity) → resolved directives ONLY.** Not directives+paradigms
  (paradigms inert — nothing in `synthesizer/` consumes `selected_paradigms`; a paradigm-only change leaves
  `graph.yaml` byte-identical → including it = false-stale + version-coupling, squad-verified). Not the
  8-key superset, not `_load_default_pack`.
- **OQ-3 (remediation) → `spec-kitty charter synthesize`; no code change.** Document `fresh` ≠
  `references.yaml`/interview-answer currency.
- **OQ-4 (fail-posture) → catch resolver exceptions.** `resolve_config_activated_roots` raises
  `UnknownArtifactIdError` (a `ValueError`) on a drifted stem in ANY resolved kind; `compute_bundle_content_hash`
  MUST catch `(UnknownArtifactIdError, CharterPackConfigError, ValueError, OSError, UnicodeDecodeError)` →
  `None` → recoverable stale (never crash `charter status`; this crash path did not exist pre-mission).
  Red-first drifted-stem + malformed-config tests; `synthesize` surfaces the actionable error (FR-005).
- **OQ-5 (extraction + serialization) → extract directive resolution, hash sorted.** Extract
  `_synthesis.py:76-79` into `charter.compiler.resolve_synthesis_graph_directives(repo_root)`; refactor
  `_synthesis.py` so `selected_directives` + `drg_nodes` (lines 84,101-107) source from it (behavior-preserving;
  guard with `test_synthesize_path_parity`); leave `selected_paradigms = config_roots.paradigms` inline (inert,
  unchanged). In `bundle.py`, append `hash_content("directives=" + ",".join(sorted(directives)))` as one digest.
- **OQ-6/OQ-7 → DISSOLVED** (directives-only mirrors the synthesizer; absent→`[]` correct by construction;
  no `_load_default_pack`; no narrow-accessor problem).

## Data Model / Contract

`compute_bundle_content_hash(repo_root) -> str | None`:
1. Per-file digests for `{governance, directives, metadata}.yaml` (unchanged; missing/unreadable → `None`).
2. **Directive digest**: `hash_content("directives=" + ",".join(sorted(resolve_synthesis_graph_directives(repo_root))))`
   inside a `try/except (UnknownArtifactIdError, CharterPackConfigError, ValueError, OSError, UnicodeDecodeError)` → `None`.
3. Combine: `hash_content("\n".join(file_digests + [directive_digest]))`.
`BUNDLE_CONTENT_HASH_FILES` → the triad; `references.yaml` removed; `computer._BUNDLE_FILES` untouched (C-003).
See [data-model.md](./data-model.md) for the behavior + remediation matrix.

## Implementation Concern Map

> Concerns are NOT WPs. `/spec-kitty.tasks` maps these to strictly-linear WPs for single_branch.

### IC-01 — Shared directive resolver (single authority)

- **Purpose**: extract the synthesizer's resolved directive list (absent→`[]`) into one public
  `charter.compiler` helper; refactor `_synthesis.py` to consume it, behavior-preserving.
- **Requirements**: FR-002, FR-004, C-004, OQ-5.
- **Surfaces**: `src/charter/compiler.py` (new helper + `__all__`), `_synthesis.py` (call site 76-107; paradigms unchanged).
- **Depends-on**: none.
- **Risks**: byte-for-byte preserve for the synthesizer — guard with `test_synthesize_path_parity` + a red-first
  test pinning absent→`[]`.

### IC-02 — Content-identity recipe (swap references.yaml → directive digest; fail-safe)

- **Purpose**: drop `references.yaml` from `BUNDLE_CONTENT_HASH_FILES`; fold the IC-01 digest into
  `compute_bundle_content_hash` via a **function-local** compiler import; wrap the resolver read to catch
  resolver exceptions (OQ-4).
- **Requirements**: FR-001, FR-004, FR-005, FR-007, C-002, C-003, NFR-001/003, OQ-1/3/4.
- **Surfaces**: `src/charter/bundle.py`. NOT `computer._BUNDLE_FILES`.
- **Depends-on**: IC-01.
- **Risks**: the landed `test_synthesized_drg_stale_when_a_bundle_file_is_missing` expectation flips → update
  as the #2758 red→green.

### IC-03 — Freshness behavior acceptance + migration + perf

- **Purpose**: prove #2758 self-heals; directive activate/deactivate → stale (RED-on-base/GREEN); paradigm &
  tactic stay `fresh`; drifted-stem → recoverable stale (no crash); no-op stable; legacy-`None` (FR-003) and
  recipe-migration (FR-007) self-heal as distinct anchors; malformed-config → actionable error; `charter
  status` < 2s (envelope reaching the graph-hash branch); gates green. Confirm reader/`promote`/`resynthesize`
  bake and `project_drg` preserves.
- **Requirements**: US1/US2 all AC, SC-001..005, FR-003/006.
- **Surfaces**: `tests/specify_cli/charter_freshness/**`, `tests/charter/**`; assert `charter status` output
  (state + remediation); ids derived from the resolver / monkeypatched.
- **Depends-on**: IC-02.
- **Risks**: the paradigm/tactic-stays-`fresh` guard must perform a real config byte-change; the perf test must
  reach the new catalog-load branch.

## Complexity Tracking

*(none — Charter Check passes with no violations)*
