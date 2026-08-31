# Implementation Plan: Synthesized DRG Stale-Refresh Fix

**Branch**: `fix/2681-synthesized-drg-stale` | **Date**: 2026-07-16 | **Spec**: `kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/spec.md`
**Input**: Feature specification from `/kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/spec.md`

**Note**: This template is filled in by the `/spec-kitty.plan` command. See `src/doctrine/missions/software-dev/command-templates/plan.md` for the execution workflow.

## Summary

A synthesized-DRG project can become permanently stuck reporting
`synthesized_drg: stale`, because `_compute_synthesized_drg`
(`src/specify_cli/charter_runtime/freshness/computer.py`) compares the
synthesis manifest's `created_at` — deliberately frozen on no-op runs by the
#1912/#1913 clean-tree fix — against the synced bundle's raw mtime, which
advances on any ordinary git operation even without content change. Once the
frozen timestamp falls behind, no prescribed remediation can catch it up,
because the only write that would refresh it is the exact no-op write
#1912/#1913 correctly suppresses.

The fix replaces that timestamp comparison with a content-identity check,
mirroring the existing `charter_source`/`charter_hash` pattern: a new
substantive (non-volatile) `bundle_content_hash` field on `SynthesisManifest`,
produced by one shared helper (`charter.bundle.compute_bundle_content_hash`,
per-file `hash_content` over the four synced-bundle files) and persisted by
every manifest writer through **one canonical finalizer**
(`manifest.finalize_manifest`), is compared at read time against a freshly
recomputed hash. Equal → `fresh`; differ, or a pre-fix manifest lacking the
field → `stale`, self-healing in exactly one remediation run (the new
non-volatile line survives the no-op-stable text diff).

The post-plan adversarial squad found three blockers, all folded here, and
re-verification against live code surfaced a fourth writer site
(`_fresh_doctrine`, raw `hashlib`) and a backward-compat break in
`verify_manifest_hash` for existing v2 manifests. The single-finalizer
extraction closes BLOCKER-1 (`project_drg.apply_post_condition` dropping the
field) and BLOCKER-2 (raw-dict/instance divergence) **by construction**
(structural C-006, not test-enforced parity). Because adding the field is NOT
behavior-inert on the model alone (it desyncs the fresh-seed raw-`hashlib`
writer and breaks `verify_manifest_hash` for v2 manifests), the finalizer and
both backward-compat shims land in the schema WP (WP01). See `research.md` for
the full fact table and decisions, `data-model.md` for the schema/finalizer
contracts.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI), pydantic (`SynthesisManifest` model), ruamel.yaml (manifest/bundle YAML I/O), pytest (tests)
**Storage**: YAML files on the local filesystem — `.kittify/charter/synthesis-manifest.yaml` (the manifest gaining the new field), `.kittify/charter/{governance,directives,references,metadata}.yaml` (the bundle files hashed); no database, no network storage
**Testing**: pytest, red-first. Reader: `tests/specify_cli/charter_freshness/test_computer.py`. Write-side integrity + no-op-stability: `tests/architectural/test_no_op_stable_writes.py`, `tests/charter/synthesizer/test_write_pipeline.py`, `tests/charter/synthesizer/test_manifest.py`, `tests/charter/synthesizer/test_orchestrator_resynthesize.py`. Built-in-only / post-condition: `tests/integration/test_charter_synthesize_built_in_only.py`. Backward-compat: `tests/specify_cli/upgrade/test_charter_bundle_v2_migration.py`, `tests/doctrine/test_versioning.py`. Integration freshness: `tests/integration/test_charter_status_freshness.py`
**Target Platform**: Cross-platform CLI (Linux, macOS, Windows 10+) — pure Python file hashing/YAML, no platform-specific code
**Project Type**: Single Python CLI package (`spec-kitty-cli`); touches two existing subtrees (`src/charter/synthesizer/`, `src/charter/bundle.py`; `src/specify_cli/charter_runtime/freshness/`) plus one existing CLI helper (`src/specify_cli/cli/commands/charter/_fresh_doctrine.py`) — no new top-level package or service
**Performance Goals**: Freshness compute (the `charter status`/preflight gate) completes <2s wall-clock on a representative project (NFR-002); added work is four `hash_content` calls over small YAML files — negligible, same cost profile as the existing `charter_hash` comparison
**Constraints**:
  - No-op-stable clean tree preserved for both `synthesize` and `resynthesize` (C-001/NFR-001) — the new field is NON-volatile (deterministic under fixed content → no-op runs recompute the same value → skip-write holds after the one-time self-heal)
  - Single canonical READ authority (`_compute_synthesized_drg`, C-005) and single canonical WRITE authority — one shared helper + one `finalize_manifest` finalizer at every persist site (C-006), structural not test-enforced
  - `built_in_only` and `missing` sub-states/gating byte-for-byte unchanged (C-002/FR-004/FR-006)
  - No new manual remediation step; `synthesize`/`resynthesize` themselves clear genuine staleness (C-004/FR-003) — ruled out a strict schema-version cutover (would crash `resynthesize`'s unguarded manifest load on pre-fix manifests)
  - Adding the field must preserve existing-manifest integrity: `verify_manifest_hash` shim required so unmigrated v2 manifests still verify
  - Canonical terminology ("Mission" not "Feature") in all new user-facing text (C-003)
**Scale/Scope**: Localized fix — one new helper + constant, one new manifest field + widened literal + one finalizer + one verify shim, four writer/persist-site updates, one reader comparison-block replacement (~25 lines), two contract-doc corrections (FR-007). No new CLI surface, no new command, no migration script (additive-only field).

## Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Charter loaded from `.kittify/charter/charter.md` (v1.3.0).

| Charter rule | Applies how | Status |
|---|---|---|
| **Single canonical authority** (DIRECTIVE_044) | C-005/C-006: one read authority (`_compute_synthesized_drg`), one write authority (shared `compute_bundle_content_hash` + one `finalize_manifest` at every persist site). The finalizer extraction eliminates the duplicated raw-dict hash logic that caused BLOCKER-1/2 — unification by construction, not parity. | **PASS** |
| **ATDD-first / red-first** (C-011, binding) | C-011 planning-base-red-first is scoped to the WPs that deliver **user-observable behavior**: WP02 (writer) and WP03 (reader) are self-contained planning-base-red→green — WP02's writer-side tests (`bundle_content_hash` populated + BLOCKER-1 field-survival) are RED before the writer conversion and GREEN after, **independent of the reader**; WP03's reader tests (AS-1 fresh-survives-mtime, AS-5 #2681 full repro) are RED on the still-mtime reader and GREEN on the content-hash reader. **WP01 (infra: new optional field + pure helper + `finalize_manifest` refactor + verify-shim generalization) and WP04 (docs/verification) deliver NO user-observable runtime behavior → planning-base-red-first is N/A** — on WP01's base the new symbols don't exist (a test referencing them is unrunnable, not a clean assertion-RED) and v2 `verify_manifest_hash` is trivially GREEN, so WP01 uses INTERNAL red-green-refactor (green-preserving regression + new-symbol unit coverage + the intra-WP verify-shim TDD cycle, incl. a discriminating per-field tamper fixture); WP04's gate is the full regression suite + the NFR guards. This is correct scoping of C-011 to behavior WPs, NOT the mission-level dilution the `/analyze` gate rejects. | **Binding — planning-base-red→green in WP02/WP03; WP01 (infra) + WP04 (docs) = N/A** |
| **DIR-041 realistic test data** | The future-dated `2099-…` sentinel never reaches the defective branch and is NOT the guard (NFR-006). WP03 (reader) uses a realistic past-dated `created_at` + a `bundle_content_hash` computed via the **real** WP01 helper, and adds the missing AS-2 (genuine content change → stale) test. | **PASS — WP03** |
| **Architectural alignment / LD-3** | The reader calls the new `charter.bundle` helper via a LAZY import (matching computer.py's existing lazy `charter.bundle`/`charter.synthesizer.manifest` imports) — no new eager cross-package import on the `spec-kitty next` hot path (NFR-002/003). | **PASS** |
| **Domain-driven splits + tiered rigour** | Core logic (reader comparison, manifest schema, finalizer, shared hash helper) gets full unit coverage; glue is not over-tested. | **PASS** |
| **Terminology canon** | No new `Feature` wording; the two FR-007 doc edits (WP03 internal docstring, WP04 external contract) are canon-reviewed in WP04. | **PASS** |
| **Campsite cleaning** | The finalizer extraction IS a domain-matched tidy-first: it removes duplicated raw-dict hash logic across four sites (net simplification), directly enabling the field addition. No unrelated god-surface cleanup pulled in. | **PASS** |
| **Mission tracer files** | Three tracer files seeded at tasks-authoring time (`tracer-approach.md`, `tracer-design-decisions.md`, `tracer-tooling-friction.md`); appended during implementation; assessed at close (WP04). | **Seeded — assessed in WP04** |
| **DIR-003 / Tracker assignment** | MOES-Media fork cannot assign upstream Priivacy-ai #2681 to the HiC — best-effort caveat per the cross-fork contributor model; attempted where the tracker permits, skipped-with-note otherwise. | **Best-effort caveat, not a blocker** |
| **Git & workflow (DIRECTIVE_045)** | Lands as a draft cross-fork PR (MOES-Media → Priivacy-ai:main); no direct protected-branch push. | **PASS — enforced at merge** |

No violations require a Complexity Tracking justification. Re-checked post-design: no new authority, no new external dependency, no schema-breaking change — Charter Check still passes.

## Project Structure

### Documentation (this mission)

```
kitty-specs/synthesized-drg-stale-refresh-01KXN8KZ/
├── plan.md              # This file
├── research.md          # Phase 0 — decision record + live-code fact table (23 facts)
├── data-model.md        # Phase 1 — schema change + finalizer/helper/verify-shim contracts
├── quickstart.md        # Phase 1 — reproduce/fix/verify walkthrough
├── contracts/
│   └── synthesized-drg-freshness-rule.md   # Corrected FR-007 contract text
└── tasks.md             # Phase 2 (/spec-kitty.tasks — NOT created here)
```

### Source Code (repository root)

```
src/
├── charter/
│   ├── bundle.py                          # WP01: + compute_bundle_content_hash() (fail-safe None on OSError+UnicodeDecodeError) + BUNDLE_CONTENT_HASH_FILES (pure/unwired helper)
│   └── synthesizer/
│       ├── manifest.py                    # WP01: + bundle_content_hash field; widen schema_version Literal["2","3"] (default kept "2");
│       │                                  #       + finalize_manifest(); verify_manifest_hash _raw_field_names-subset shim
│       │                                  # WP02: bump schema_version default → "3" (out-of-map one-line edit)
│       ├── write_pipeline.py              # WP02 promote(): compute bundle hash + finalize_manifest; _VOLATILE_MANIFEST_FIELDS UNCHANGED
│       ├── resynthesize_pipeline.py       # WP02 _rewrite_manifest(): thread repo_root + compute bundle hash + finalize_manifest
│       ├── project_drg.py                 # WP02 apply_post_condition(): preserve bundle_content_hash via model_copy + finalize (BLOCKER-1)
│       └── orchestrator.py                # invocation context for promote + apply_post_condition (no signature change expected)
└── specify_cli/
    ├── charter_runtime/freshness/
    │   └── computer.py                    # WP03 _compute_synthesized_drg(): mtime→content-hash swap; remove dead manifest_exists/bundle_ts;
    │                                      #   correct module docstring (FR-007 internal)
    └── cli/commands/charter/
        └── _fresh_doctrine.py             # WP01 _fresh_seed_manifest_text(): route raw-hashlib self-hash through finalize_manifest (fact #15)

# consumed unchanged: src/charter/hasher.py (hash_content — used by the new helper)

tests/
├── charter/test_bundle_content_hash.py                       # WP01 (NEW): helper unit tests — happy path, missing-file→None, non-UTF-8→None (C1)
├── charter/synthesizer/test_manifest.py                      # WP01: finalize_manifest parity + verify_manifest_hash shim (absent-key + tamper)
├── integration/test_charter_synthesize_fresh.py              # WP01: production fresh-seed verify_manifest_hash pin
├── charter/synthesizer/test_write_pipeline.py                # WP02: promote writes bundle_content_hash + no-op stability
├── charter/synthesizer/test_orchestrator_resynthesize.py     # WP02: writer-side field==helper (synth+resynth) + writer-recompute + BLOCKER-1 fixtures
├── integration/test_charter_synthesize_built_in_only.py      # WP02: apply_post_condition preserves bundle_content_hash (BLOCKER-1 non-vacuous)
├── specify_cli/charter_freshness/test_computer.py            # WP03: red-first #2681 AS-1/AS-2/AS-5 + preserved-branch pins
├── integration/test_charter_status_freshness.py              # WP03: AS-5 e2e + tighten in {"fresh","stale"} → == "fresh"
├── charter/synthesizer/test_performance_envelopes.py         # WP04: NFR-002 (<2s freshness compute) perf guard
├── architectural/test_no_op_stable_writes.py                 # kept green (WP02) — no-op-stable guard with the new field
├── specify_cli/upgrade/test_charter_bundle_v2_migration.py   # kept green (WP01) — v2 manifests still verify after the field
└── doctrine/test_versioning.py                               # kept green (WP01) — v2 migration/verify backward-compat

kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/
└── charter-status-json.md                 # FR-007 external contract: "Staleness computation" corrected
```

**Structure Decision**: Single Python CLI package, no new module boundary.
Writer + finalizer live in `src/charter/` (next to the existing
manifest/`compute_manifest_hash` machinery); the reader stays in
`src/specify_cli/charter_runtime/freshness/`, calling the shared helper
lazily — mirroring the existing `charter_hash`/`_charter_hash_of` split.

## Complexity Tracking

*No Charter Check violations were identified; this section is intentionally empty.*

## Implementation Concern Map / Work-Package Outline

> **Note**: Implementation concerns are NOT work packages and are NOT executable units.
> `/spec-kitty.tasks` translates these into executable WPs. Below is the decomposition:
> **FOUR** strictly-sequential WPs (single-branch topology, shared files → strict
> ordering). Per the post-tasks `/analyze` finding, tests are folded into the WP that
> makes them green so **the behavior WPs — WP02 (writer) and WP03 (reader) — are
> self-contained planning-base-red→green** (their red-first tests are RED on the WP's
> base and GREEN on the WP's final commit). **WP01 (infra) and WP04 (docs/verification)
> deliver no user-observable runtime behavior → C-011 planning-base-red-first is N/A**
> for them (WP01 uses internal red-green-refactor; WP04's gate is regression + NFR
> guards). This scopes C-011 to the behavior WPs — NOT the mission-level dilution the
> earlier 5-WP split introduced (a pure red-tests WP whose tests stayed red until later
> WPs).

### WP01 — Manifest schema + hash infra (infra WP — C-011 planning-base-red-first N/A)

- **Purpose**: Deliver a manifest that can carry the new content-identity
  field and stay self-consistent, plus the pure content-hash helper — with
  the field addition's two backward-compat breaks (`verify_manifest_hash`
  for existing v2 manifests; the fresh-seed raw-`hashlib` writer) fixed in
  the SAME WP so the WP is green on its own final commit.
- **Scope**: add `bundle_content_hash: str | None = None` (NON-volatile) +
  widen `schema_version` → `Literal["2","3"]` KEEP default `"2"`; extract
  `finalize_manifest`; generalize `verify_manifest_hash`'s legacy fallback
  to the per-field `_raw_field_names`-subset recipe (raw
  `hashlib.sha256(canonical_yaml(subset))`, NOT a pop-list, NOT
  `compute_manifest_hash`); add the PURE UNWIRED
  `charter.bundle.compute_bundle_content_hash(repo_root) -> str | None` +
  `BUNDLE_CONTENT_HASH_FILES` (per-file `hash_content` then combine digests);
  reroute `_fresh_seed_manifest_text` through `finalize_manifest` (stays
  `"2"`). Reader + the three constructor writers UNTOUCHED.
- **C1 fail-safe (from `/analyze`)**: `compute_bundle_content_hash` returns
  `None` (→ reader maps to `stale`, never a crash) when the charter dir is
  missing OR any of the four files is missing/unreadable — the read guard
  MUST catch **both `OSError` AND `UnicodeDecodeError`** (a non-UTF-8 bundle
  file raises `UnicodeDecodeError`, a `ValueError` subclass NOT caught by
  `OSError`).
- **Intra-WP TDD + green-preserving regression** (NOT planning-base-red — the
  new symbols don't exist on WP01's base; v2 verify is GREEN there): (a)
  verify-shim absent-key (v2 manifest with `built_in_only` but no
  `bundle_content_hash` still verifies — the green-preserving-regression half,
  momentarily red intra-WP when the field lands, green once the shim does);
  (b) **DISCRIMINATING** tamper (a manifest that CARRIES `bundle_content_hash`
  on disk but whose stored `manifest_hash` was computed EXCLUDING it, then
  tampered → verify RAISES — the fixture that actually proves per-field vs
  pop-list; a finalize_manifest-built tamper does NOT discriminate); (c)
  finalizer parity; (d) production fresh-seed verify (real `_fresh_seed`
  output passes `verify_manifest_hash`); (e) helper unit tests incl.
  missing-file→`None` and **non-UTF-8→`None`**.
- **Owned files**: `manifest.py`, `bundle.py`, `_fresh_doctrine.py`,
  `test_manifest.py`, `test_charter_synthesize_fresh.py`, + a NEW
  `tests/charter/test_bundle_content_hash.py` (create_intent).
- **Sequencing/depends-on**: none (first).
- **Risks**: the shim must be per-field gated (not a fixed pop-list) or it
  weakens tamper detection; keep the v2-migration/versioning suites green.

### WP02 — Writer wiring (self-contained red→green, reader-INDEPENDENT)

- **Purpose**: Make every persist site write a correct non-`None`
  `bundle_content_hash` via the one finalizer — provable without the reader
  fix (the WP's red tests assert on the manifest FIELD, not on freshness
  state), so WP02 is green on its own final commit.
- **Scope**: bump the model `schema_version` default `"2"`→`"3"` ATOMICALLY
  with converting `promote` + `_rewrite_manifest` to build instances routed
  through `finalize_manifest` (dropping the hardcoded `"2"` dicts, SAME
  commit); `apply_post_condition` → `model_copy(update={built_in_only})` +
  `finalize_manifest` (BLOCKER-1 field passthrough); wire
  `compute_bundle_content_hash` into both real writers; thread `repo_root`
  into `_rewrite_manifest`.
- **Out-of-map edit**: a ONE-LINE bump of the `schema_version` default in
  `manifest.py` (WP01 owns that file) — documented with rationale; NOT
  listed in WP02 `owned_files`.
- **Per-WP red→green tests** (RED on WP02 base, GREEN on WP02 final,
  reader-independent): (a) after `synthesize` AND `resynthesize`, load
  manifest → `bundle_content_hash is not None and ==
  compute_bundle_content_hash(repo_root)`; (b) BLOCKER-1 non-vacuous (extend
  `_seed_manifest` with a `bundle_content_hash` param, seed a REAL non-`None`
  hash + `built_in_only=False` + a project graph, call
  `apply_post_condition(has_project_graph=False)` — drives the mutation
  branch past the fast-path early-return — assert the field SURVIVES +
  `verify_manifest_hash` passes); (c) writer-recompute (edit a bundle file's
  CONTENT, re-run `synthesize` → the manifest's `bundle_content_hash` CHANGES
  to match — reader-independent writer half of SC-003). Keep no-op-stable
  guards green.
- **Owned files**: `write_pipeline.py`, `resynthesize_pipeline.py`,
  `project_drg.py`, `test_write_pipeline.py`,
  `test_orchestrator_resynthesize.py`,
  `test_charter_synthesize_built_in_only.py`.
- **Sequencing/depends-on**: WP01.
- **Risks**: `_VOLATILE_MANIFEST_FIELDS` must stay unchanged; the default
  bump + literal-removal must land in ONE commit (fact #17).

### WP03 — Reader swap (self-contained red→green)

- **Purpose**: Make freshness reflect content-identity; unblock #2681. The
  WP's red tests are RED on the still-mtime reader (WRONG verdict) and GREEN
  on the content-hash reader.
- **Scope**: rewrite `_compute_synthesized_drg` comparison (`:411-441`) to
  stored-vs-current `bundle_content_hash` (`None` either side → `stale`);
  remove dead `manifest_exists` (`:352`) + `bundle_ts` (`:412`); preserve
  `built_in_only`/`missing`/legacy-seed/`synced_bundle`-not-fresh precedence
  + the parse-failure early-return; fix the module docstring (FR-007
  internal).
- **Per-WP red→green tests** (RED on WP03 base = still-mtime reader, GREEN on
  WP03 final = content-hash reader): AS-1 (fresh survives mtime
  perturbation — the load-bearing unambiguous red pin); AS-5 (#2681 full
  repro, BOTH `synthesize`+`resynthesize` — the canonical #2681 red);
  AS-2 (content change → `stale`); the genuine-content-change remediation
  e2e (fresh → edit `governance.yaml` CONTENT → `stale` → `synthesize` →
  `fresh`; repeat via `resynthesize` — the full SC-003/AS-3 proof); tighten
  the flaky `test_charter_status_freshness` (`in {"fresh","stale"}` →
  `== "fresh"`); preserved-branch pins.
- **Owned files**: `computer.py`, `test_computer.py`,
  `test_charter_status_freshness.py`.
- **Sequencing/depends-on**: WP02.
- **Risks**: do not touch the preserved branches — the pins catch a regress.

### WP04 — Contract doc + full regression + NFR verification (closeout)

- **Purpose**: Close the published-contract drift and gate the mission.
  **Delivers no new runtime behavior → C-011 red-first is N/A**; its gate is
  the full regression suite + the NFR guards (state this explicitly so
  `/analyze` does not misread it as a diluted behavior WP).
- **Scope**: update the external contract doc
  `kitty-specs/charter-ux-and-org-pack-vocabulary-01KSAF14/contracts/charter-status-json.md`
  (FR-007 external half — reviewer-attested, no automated pin possible for a
  `kitty-specs/` prose doc); NFR-002 perf test (<2s) in
  `test_performance_envelopes.py`; NFR-003 audit (no new manual step/dep);
  full regression (no-op-stable guards green, `mypy --strict`, `ruff`,
  coverage); issue-matrix close-out (pre-settled verdicts from spec.md
  Related Issues: #2681=fixed; #1914/#2157/#2373=out-of-scope; #2009=not-
  related; #1912/#1913=preserved-invariant — annotate, don't shoehorn);
  DIR-003 caveat (MOES-Media can't assign upstream — best-effort); assess
  the three tracer files.
- **Owned files**: `test_performance_envelopes.py` (the external contract doc
  is real work but un-declarable in `owned_files` — the `kitty-specs/` gate).
- **Sequencing/depends-on**: WP01–WP03.
- **Risks**: none beyond ordinary regression — verification, not new logic.

### Requirement → WP traceability (no orphans)

| Req | WP(s) | Req | WP(s) |
|-----|-------|-----|-------|
| FR-001 | WP02 (write), WP03 (read) | NFR-001 | WP01 (non-volatile), WP02, WP04 |
| FR-002 / AS-2 | WP03 (test + read) | NFR-002 | WP04 |
| FR-003 | WP02 (writer recompute), WP03 (remediation e2e) | NFR-003 | WP04 |
| FR-004 | WP03 (preserve + pin) | NFR-004 | all |
| FR-005 / AS-5 | WP02 (write), WP03 (read + repro) | NFR-005 | WP01, WP02, WP03, WP04 |
| FR-006 | WP03 (preserve + pin) | NFR-006 | WP03 |
| FR-007 | WP03 (docstring), WP04 (contract) | C-001 | WP01, WP02, WP04 |
| AS-1 | WP03 (test + read) | C-002 | WP03 |
| AS-3 | WP02 (writer), WP03 (remediation e2e) | C-003 | WP04 |
| AS-4 (self-heal) | WP01 (non-volatile diff), WP02 | C-004 | WP02, WP03 |
| AS-6 | WP03 (preserve + pin) | C-005 | WP01 (finalizer + helper), WP02 (writer), WP03 (reader) |
| pre-fix-manifest edge | WP01 (verify shim), WP02, WP03 | C-006 | WP01 (finalizer), WP02 (single writer) |
