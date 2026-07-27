# Phase 0 Research: Phase 3 Charter Synthesizer Pipeline

**Mission**: `phase-3-charter-synthesizer-pipeline-01KPE222`
**Phase**: 0 (outline & research)
**Status**: Complete. No `[NEEDS CLARIFICATION]` markers remain in `plan.md` or `spec.md`.

This document resolves every open planning question raised in `plan.md` so that Phase 1 design artifacts (`data-model.md`, `contracts/`, `quickstart.md`) can derive from confirmed positions rather than raw user input.

---

## R-0-1 · Interview-answer surfaces → artifact-kind mapping

### Decision

Drive target selection from a **static mapping table** kept in `src/charter/synthesizer/interview_mapping.py`. The table binds each interview-question identifier (and/or interview section) to one or more `(artifact_kind, slug_template)` pairs, plus an optional `requires_nonempty_answer` flag that gates target emission.

Concretely (illustrative — authoritative table lives in the code, not this doc):

| Interview section / question | Drives targets (kind : slug-template) | Gate |
|---|---|---|
| `mission-type` | `directive:mission-type-scope-directive` | always |
| `language-scope` | `styleguide:language-style-<lang>` (one per answered language) | per-language answer present |
| `testing-philosophy` | `tactic:testing-philosophy-tactic`, `styleguide:testing-style-guide` | nonempty |
| `neutrality-posture` | `directive:neutrality-posture-directive` | nonempty |
| `selected-paradigms` | no direct target (paradigms remain shipped-layer-only per C-005) | — |
| `selected-directives` | per-directive URN → `tactic:how-we-apply-<directive-id>` | per selection |
| `selected-tactics` | per-tactic URN → `styleguide:how-we-apply-<tactic-id>` | per selection |
| `risk-appetite` | `directive:risk-appetite-directive` | nonempty |
| `local-support-declarations` | no synthesis target — these are user-authored doctrine files, resolved via existing `LocalSupportDeclaration` paths | — |

### Rationale

- A static table is inspectable, greppable, and trivially unit-testable (table-driven tests, one row per entry).
- Code-level selection logic stays separate from orchestration; `interview_mapping.py` has no side effects, returns a list of `SynthesisTarget`s.
- Keeps the mapping *extensible without orchestration churn*: adding a new interview question → new row in the table + its fixture; no orchestrator touches.

### Alternatives considered

- **Dynamic inference from interview schema metadata**: attractive but currently the interview schema (`src/charter/interview.py`) does not tag questions with artifact-kind hints. Retrofitting the schema would be a scope expansion. Rejected for this tranche; leaves a clean upgrade path later.
- **Adapter-owned target selection**: adapters proposing their own targets. Rejected — it's the orchestrator's job to stay deterministic, and adapter-owned selection leaks prompt-shaping / product decisions into the generation step. Violates KD-3's seam-narrowness invariant.

### Test coverage

- `tests/charter/synthesizer/test_interview_mapping.py` — one test per row, plus negative tests for: nonexistent section, empty answer with `requires_nonempty_answer=True`, unknown selection URN.

---

## R-0-2 · Canonical on-disk layout — split between `.kittify/doctrine/` (content) and `.kittify/charter/` (bookkeeping)

### Decision

Synthesized **content** lives under `.kittify/doctrine/`; synthesis **bookkeeping** lives under `.kittify/charter/`. This matches the trees that existing consumers already recognise:

- `DirectiveRepository`, `TacticRepository`, `StyleguideRepository` each resolve `project_root/<artifact-subdir>/*.<kind>.yaml` via the existing repository glob. `DoctrineService._project_dir(artifact)` returns `project_root / artifact`, so pointing `project_root` at `.kittify/doctrine/` is all the wiring that is needed.
- `src/charter/_drg_helpers.py` already reads the project DRG overlay from `.kittify/doctrine/graph.yaml` (verified on current `main`). No loader change is needed for the project graph.

Directory layout:

```
.kittify/
├── doctrine/                                   # synthesized CONTENT (recognised by existing loaders)
│   ├── directives/
│   │   └── <NNN>-<slug>.directive.yaml         # matches DirectiveRepository glob *.directive.yaml
│   ├── tactics/
│   │   └── <slug>.tactic.yaml                  # matches TacticRepository glob *.tactic.yaml
│   ├── styleguides/
│   │   └── <slug>.styleguide.yaml              # matches StyleguideRepository glob *.styleguide.yaml
│   └── graph.yaml                              # project DRG overlay (loader already reads this path)
└── charter/                                    # synthesis BOOKKEEPING (never doctrine content)
    ├── charter.md                              # unchanged — human-authored
    ├── governance.yaml                         # unchanged — derived from charter.md
    ├── directives.yaml                         # unchanged — derived from charter.md
    ├── metadata.yaml                           # unchanged — derived from charter.md
    ├── provenance/
    │   └── <kind>-<slug>.yaml                  # per-artifact provenance sidecars (one per synthesized artifact)
    ├── synthesis-manifest.yaml                 # commit marker (manifest-last)
    └── .staging/                               # ephemeral staging dirs (KD-2)
        └── <runid>/
            ├── doctrine/…                      # staged content, promoted to .kittify/doctrine/
            └── charter/…                       # staged bookkeeping, promoted to .kittify/charter/
```

### Directive ID scheme (tranche-1 default)

Verified against `src/doctrine/directives/models.py` on current `main`: `Directive.id` regex is `^[A-Z][A-Z0-9_-]*$`. Shipped directives use `DIRECTIVE_<NNN>` (normalized by `DirectiveRepository._normalize_id`). Synthesized directive IDs use `PROJECT_<NNN>`: it matches the regex, is disjoint from shipped IDs (no collision), and keeps the filename convention predictable (`DirectiveRepository.save` would derive `<NNN>-<slug>.directive.yaml`, which we emit directly from the synthesizer). The scheme is *not locked* — the regex also accepts `TEAM_TESTING_POLICY`-style semantic IDs; if WP3.2 finds semantic IDs produce cleaner provenance we can swap without a plan change.

Synthesized tactic and styleguide IDs are kebab-case slugs directly (both models' id regex is `^[a-z][a-z0-9-]*$`), e.g. `how-we-apply-directive-003` for a tactic, `python-testing-style` for a styleguide.

### Rationale

- **Content path matches consumer expectations**. `DoctrineService` already composes `project_root / <artifact>` internally, and the repository globs already expect `*.<kind>.yaml`. Putting content under `.kittify/doctrine/` means zero consumer reshape — only the project-root candidate list in `compiler.py` / `context.py` needs extending.
- **Project DRG path is already wired**. `_drg_helpers.py` reads `.kittify/doctrine/graph.yaml` today; writing there is the natural move.
- **Bookkeeping separation**. Provenance sidecars, commit manifest, and staging directory are not doctrine — they are synthesis artifacts about doctrine. Keeping them under `.kittify/charter/` means doctrine loaders never see them, and `bundle validate` has a clean place to look without walking through doctrine content.
- **Staging single-root**. One staging dir per run (`.kittify/charter/.staging/<runid>/`) with internal `doctrine/` and `charter/` subtrees keeps atomic promote simple: the promote step walks the staged tree and `os.replace`s each file into its mirror location.

### Alternatives considered

- **Everything under `.kittify/charter/`** (the original Phase 3 plan). Rejected — `DoctrineService._project_dir` returns `project_root/<artifact>`, so this would require pointing `project_root` at `.kittify/charter/` and renaming the existing bundle bookkeeping files to avoid collisions. Reshapes consumer expectations that don't need reshaping.
- **Everything under `.kittify/doctrine/`** (content and bookkeeping). Rejected — would require doctrine loaders to skip-list bookkeeping files, leaking synthesis concerns into doctrine loading.
- **Single monolithic `.kittify/doctrine/synthesized.yaml`**. Rejected — breaks `DoctrineService` project-layer expectations, which already look for `directives/`, `tactics/`, `styleguides/` directories.
- **`.kittify/doctrine/drg/graph.yaml`** (subdirectory for the graph). Rejected — the existing loader reads `.kittify/doctrine/graph.yaml` directly; moving the file forces a loader change for no namespacing benefit.
- **Provenance embedded in each artifact YAML** (sidecar avoided). Rejected — provenance evolves independently of artifact schemas and carries metadata (inputs hash, adapter id) that should not pollute artifact-body validation.

### .gitignore implications

- `.kittify/charter/.staging/` is added to `.gitignore` (tracked as a bundle-manifest gitignore requirement via `CharterBundleManifest.gitignore_required_entries`).
- Synthesized content under `.kittify/doctrine/` AND synthesis bookkeeping under `.kittify/charter/` (except `.staging/`) *are committed* by default — they are project-local doctrine + commit-marker audit state the team wants in VCS.

---

## R-0-3 · Provenance storage format

### Decision

**Per-artifact YAML sidecar** at `.kittify/charter/provenance/<kind>-<slug>.yaml`. One file per synthesized artifact. Sidecar lives under the bookkeeping tree (`.kittify/charter/`), not alongside the content file (`.kittify/doctrine/…`), so doctrine loaders never traverse provenance. Sidecar schema is `contracts/provenance.schema.yaml`.

### Rationale

- Per-file granularity makes `resynthesize --topic` surgically simple: regenerate one artifact → rewrite one provenance sidecar. No risk of stomping unrelated entries.
- YAML matches the existing charter bundle conventions (`governance.yaml`, `directives.yaml`, `metadata.yaml`) and reuses the project's `ruamel.yaml` dependency.
- Git diffs are small and readable — reviewers see exactly which artifacts' provenance changed.
- Byte-reproducibility (NFR-006) is achievable because YAML emission with `ruamel.yaml` in canonical mode is deterministic for our field set.

### Alternatives considered

- **Single `provenance.yaml` at top level** (one mapping keyed by artifact URN). Rejected — any resynthesis has to rewrite the whole file, and merge conflicts on this file would be annoying. Per-file sidecars eliminate that.
- **JSONL** (`provenance.jsonl`). Rejected — inconsistent with rest of charter bundle (all YAML), and diff-noisy when entries are reordered.
- **Embedded in artifact YAML frontmatter**. Rejected per R-0-2 rationale — contamination of artifact schema.

---

## R-0-4 · Bundle manifest extension strategy

### Decision

**Additive, backwards-compatible extension of bundle manifest v1.0.0. No schema_version bump.**

Specifically, `CharterBundleManifest` gains two optional fields that bridge the `.kittify/charter/` ↔ `.kittify/doctrine/` split:

- `synthesized_artifacts: list[SynthesizedArtifactDeclaration]` — each entry `{kind, slug, path, provenance_path}` where `path` points into `.kittify/doctrine/<kind-dir>/<filename>.yaml` and `provenance_path` points into `.kittify/charter/provenance/<kind>-<slug>.yaml`. Present when synthesis has run. Absent when it hasn't.
- `synthesis_manifest_path: str | None` — resolves to `.kittify/charter/synthesis-manifest.yaml` when synthesis is committed; `None` otherwise.

Existing `tracked_files`, `derived_files`, `gitignore_required_entries` keep their current semantics. `schema_version` stays at `1.0.0`.

`charter bundle validate` is extended (FR-015):
1. If `synthesis_manifest_path` is present, the manifest must exist, validate against `contracts/synthesis-manifest.schema.yaml`, and every `synthesized_artifacts` entry must have (a) a content file at `path` under `.kittify/doctrine/` with a blake3 hash matching the manifest `content_hash`, and (b) a matching provenance sidecar under `.kittify/charter/provenance/` (and the inverse: no orphan provenance entries).
2. If absent (legacy / never-synthesized project), no new checks run — preserves R-2 mitigation (no behaviour change for legacy projects).

### Rationale

- Additive fields on a Pydantic model do not break v1.0.0 consumers (Pydantic skips unknown fields with `model_config = ConfigDict(extra="ignore")` which the existing manifest already has based on read of `bundle.py`).
- Keeps the schema_version as a semantically meaningful signal reserved for breaking changes.

### Alternatives considered

- **v1.1.0 bump** — correct if the change were breaking. It isn't. Reserving `1.1.0` for a later change (e.g. mandatory synthesis metadata) keeps the signal sharp.
- **Parallel `synthesis-bundle.yaml`** sibling manifest. Rejected — two manifests to keep in sync for no benefit.

---

## R-0-5 · Production-adapter fallback behaviour

### Decision

When `spec-kitty charter synthesize` is invoked and no production adapter can be instantiated (e.g. missing credentials, disabled provider, offline CI without flag):

1. The CLI emits a structured error (exit code nonzero, `rich`-rendered error panel) naming the adapter identifier it attempted, the specific reason it failed to instantiate, and the remediation path (configure credentials / pass `--adapter fixture` for dry runs).
2. **No silent fallback to the fixture adapter.** The fixture adapter is test-only; wiring it into a production run would silently produce non-production artifacts and violate the determinism / provenance contract.
3. `--adapter fixture` is accepted as an *explicit* opt-in flag for smoke testing; provenance stamps `adapter_id=fixture` and `adapter_version=<fixture-commit-hash>`, which makes the test-origin of the output obvious in any later audit.

### Rationale

- FR-013's "no silent fallback" posture applies to adapter selection too, not just topic resolution.
- Making fixture-mode explicit preserves the ability to dry-run the pipeline locally (useful for operators verifying layout before spending model tokens) while never contaminating production runs.

### Alternatives considered

- **Silent fallback to fixture** — rejected (contamination risk).
- **Hard-fail with no opt-in** — rejected; the explicit `--adapter fixture` use-case is real.
- **`--dry-run` that skips adapter calls entirely** — rejected because it would not exercise the stage/promote path and therefore misses real failure modes operators want to catch.

---

## R-0-6 · Content-hash hygiene (blake3 variant + short-hash length)

### Decision

- Use **blake3** (already in the charter package via `src/charter/hasher.py`).
- Full-length hash (256 bit / 64 hex chars) is stored in provenance and manifest entries.
- "Short hash" for fixture file names is the first **12 hex chars** of the blake3 hex digest.

### Rationale

- blake3 is already a runtime dependency; no new libraries.
- 12 hex chars = 48 bits of collision resistance for fixture-local uniqueness, which is more than enough when the fixture space is scoped to `<kind>/<slug>/`. At ~100 fixtures per slug, collision probability is ~10⁻¹¹.
- Full-length hash in provenance / manifest preserves cryptographic collision resistance for audit-grade integrity.

### Normalization rule (KD-4 refinement)

Before hashing, `SynthesisRequest` is normalized:

1. All mapping fields are serialized with **sorted keys**.
2. Sequence fields that are order-insensitive by semantics (e.g. `selected_directives`, `selected_tactics`) are sorted alphabetically by URN before serialization.
3. Numeric fields use repr-stable JSON serialization (no locale-sensitive formatting).
4. Timestamps and run-local ephemeral fields are **excluded** from the hashed envelope (they carry no semantic weight for the fixture lookup).
5. Adapter id + version ARE included in the hash, so the same request routed to two different adapter versions yields two different fixtures — this is the correct behaviour.

Test `test_fixture_adapter.py::test_normalization_invariance` locks rules 1–4 by permuting inputs and asserting identical hashes. Test `test_fixture_adapter.py::test_adapter_version_affects_hash` locks rule 5.

---

## R-0-7 · Existing DRG validator error shape — is it enough?

### Decision

**Yes — existing `src/doctrine/drg/validator.py :: validate_graph()` returns a `list[str]` of error messages that already includes the dangling URN, duplicate edge tuple, or cycle path in the message text.** This is sufficient for structured-error surfacing provided we wrap the validator call in a small helper that parses / re-emits structured errors.

Our wrapper (in `src/charter/synthesizer/project_drg.py`) calls `validate_graph`, and on any non-empty error list raises `ProjectDRGValidationError(errors=[...], merged_graph=...)`. Orchestration catches this and surfaces it to the CLI with full error detail.

We do **not** extend `src/doctrine/drg/validator.py` — preserves KD-1's "no new code under doctrine" constraint.

### Rationale

- The existing validator is battle-tested (live in current main, covers shipped graph of ~38KB). Reusing it directly avoids duplication and preserves the invariant source of truth.
- Wrapper-level structuring is enough for our CLI UX; no validator contract change is needed.

### Alternatives considered

- **Refactor validator to return structured errors** (a list of typed error objects). Rejected — a validator contract change affects every doctrine consumer, not just us, and would expand mission scope significantly. Flagged as a nice-to-have follow-up.

---

## R-0-9 · Consumer-wiring extension for FR-009

### Decision

Extend the project-root candidate list inside both `src/charter/compiler.py::_default_doctrine_service` and `src/charter/context.py::_build_doctrine_service` to prepend `.kittify/doctrine/` before the existing `repo_root/src/doctrine` and `repo_root/doctrine` candidates. Discovery remains the existing "first candidate whose directory exists wins" semantics, so:

- **Legacy project (no `.kittify/doctrine/`)**: falls through to the existing shipped-layer candidates — byte-identical behaviour to 3.x today.
- **Post-synthesis project (`.kittify/doctrine/` exists)**: `DoctrineService` uses it as the project layer, and synthesized artifacts flow into `charter context` via the existing aggregation path.

No change to `DoctrineService`; no change to `_drg_helpers.py`; no change to the doctrine repositories. The entire wiring diff is two small edits to the candidate-list construction.

### Rationale

- Minimises blast radius: the only behavioural change a legacy project can observe is "a `.kittify/doctrine/` directory, if present, becomes the project layer", and legacy projects never had that directory.
- Preserves the "discover by directory presence" pattern that `compiler.py` and `context.py` already use — no new discovery mechanism to reason about.
- Keeps FR-009 testable without a synthesis run: create `.kittify/doctrine/directives/001-foo.directive.yaml`, call `_default_doctrine_service`, assert `DoctrineService` resolves the directive. Tests in `test_charter_compile_project_root.py`.

### Alternatives considered

- **Opt-in flag on `DoctrineService`**. Rejected — adds a configuration surface for a behaviour that is already naturally directory-guarded.
- **Gate on manifest presence** (only recognise `.kittify/doctrine/` when `.kittify/charter/synthesis-manifest.yaml` exists). Rejected — makes `DoctrineService` bundle-aware, crossing a layering boundary the doctrine package has not had to cross before.

### Test coverage

- `tests/charter/synthesizer/test_charter_compile_project_root.py`:
  - `test_legacy_no_kittify_doctrine_unchanged` — asserts byte-identical project_root resolution vs. pre-mission behaviour.
  - `test_kittify_doctrine_present_selected` — asserts `.kittify/doctrine/` wins when present.
  - `test_kittify_doctrine_empty_harmless` — asserts an empty directory yields empty overlays with no shipped-layer contamination.

---

## R-0-8 · Follow-ups flagged for later missions (NOT in scope)

These surfaced during Phase 0 research but are deliberately *not* planned in this tranche.

| ID | Follow-up | Rationale for deferral |
|---|---|---|
| F-0-1 | `charter doctor` extension to detect stale `.staging/` dirs | Not blocking; staging accumulation is a non-functional wart, not a correctness bug. R-7 mitigation is sufficient for now. |
| F-0-2 | Structured-error refactor of `src/doctrine/drg/validator.py` | KD-1 constraint + scope discipline. Nice to have later. |
| F-0-3 | Paradigm / procedure / toolguide / agent_profile synthesis | C-005 explicitly defers these to a later tranche. |
| F-0-4 | Interview schema metadata tagging (question → artifact-kind) | R-0-1 alternative; clean upgrade path; not needed now. |
| F-0-5 | `--adapter` plugin discovery via entry_points | Current tranche wires adapters by name; entry-point discovery is a plugin-ecosystem concern for later. |
| F-0-6 | Free-text `--topic` support | Non-goal per C-004; would require separate design. |
| F-0-7 | Monorepo / cross-repo visibility | ADR-8 (#522), out of scope per C-008. |
| F-0-8 | Pre-Phase-3 project migration tooling | ADR-7 (#523), out of scope per C-007. |

---

## Summary — all planning unknowns resolved

No `[NEEDS CLARIFICATION]` markers remain. Phase 1 may proceed.
