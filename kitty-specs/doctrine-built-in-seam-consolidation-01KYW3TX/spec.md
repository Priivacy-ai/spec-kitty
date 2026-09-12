# Mission Specification: Built-In Doctrine Seam Consolidation

**Mission**: `doctrine-built-in-seam-consolidation-01KYW3TX`
**Type**: software-dev (structural / tech-debt)
**Status**: Draft
**Purpose (TL;DR)**: Give built-in doctrine one fail-closed place to live on disk and prove the
`packs/built-in` move is complete, so the platform can never silently load an empty doctrine set.

> Research + design basis: this mission was scoped by a research squad (architect-alphonso,
> paula-patterns, researcher-robbie, reviewer-renata) and an architecture design pass. The full
> synthesis, the closed PR #3117 CI-failure ownership split, and the source issues are captured in
> `research.md` / the mission `notes/`. This is **Mission 1 of 2**; the sibling
> `charter-pack-usage-journey` mission (#3104/#3105/#3118) is out of scope here.

## User Scenarios & Testing *(mandatory)*

The "users" of built-in doctrine location are the **runtime** (which loads doctrine artefacts to
build governance context), the **developers** who add or move readers of that content, and the
**operators** who read error guidance when something is misconfigured.

### User Story 1 - One fail-closed place to find built-in doctrine (Priority: P1)

The platform relocated built-in doctrine content from `src/doctrine/<kind>/built-in/` to
`packs/built-in/<kind>/`, but on-disk location is currently re-derived independently at ~25 call
sites through five mechanisms — one of which (`DoctrineService._built_in_dir`) still encodes the old
nested shape and **fails open**: given a real root it points at a now-empty directory and loads
**zero** artefacts with no error. A single authority must own "where does built-in kind K live", and
asking for a missing/misconfigured root must **fail loudly**, never yield an empty doctrine set.

**Why this priority**: this is the load-bearing correctness risk. A silent empty-doctrine load
produces governance with no directives while every graph-shaped test stays green — the exact
failure the closed relocation PR surfaced.

**Acceptance**:
1. **Given** any built-in artefact kind that ships content, **when** the runtime resolves its
   on-disk root, **then** it resolves through exactly one authority and lands inside
   `packs/built-in/<plural>/`.
2. **Given** a caller that supplies no explicit root (every production caller), **when** doctrine
   loads, **then** it loads the shipped built-in artefacts (behaviour unchanged from today).
3. **Given** the built-in pack root cannot be located, **when** resolution runs, **then** it raises
   a named error (`PackRootNotFound`) rather than returning an empty set.
4. **Given** a developer adds a new module that computes a built-in path by hand, **when** CI runs,
   **then** an architectural gate fails and names the offending site.

### User Story 2 - The relocation is provably, completely done (Priority: P1)

The product relocation is essentially complete, but a residue of readers, test fixtures, and
operator-facing strings still point at the emptied `src/doctrine/<kind>/built-in/` paths. Some fail
loudly (the glossary gate); one passes **vacuously** on an empty set (a latent false-green); and one
shipped error message directs operators to a dead path. The move must be finished and a guard must
prevent a future relocation from silently regressing.

**Why this priority**: partial completion is what made the relocation feel unbounded; the residue is
small and finite once inventoried, and one item (the false-green) actively hides breakage.

**Acceptance**:
1. **Given** the shipped test suite, **when** it runs, **then** the 7 relocation-owned failures
   (the glossary-gate ERRORs and the org-pack collision test) pass, resolved at the correct root.
2. **Given** a test that loads shipped built-in artefacts, **when** the root is misconfigured or
   empty, **then** the test **fails** (anti-vacuity), rather than passing on an empty set.
3. **Given** an operator following a shipped error message, **when** they open the named path,
   **then** the path exists (`packs/built-in/<kind>/`), not a dead `src/doctrine/<kind>/built-in/`.

### User Story 3 - Activation vocabulary and context surface have one source (Priority: P2)

The charter activation-key vocabulary is hand-restated in several places and has **already drifted**:
a live migration path is missing `activated_glossary_packs`, so it would silently drop glossary-pack
activation. Separately, a de-god of the context module left a large private re-export shim with no
removal ticket, and relocated artefact YAMLs carry stale provenance strings. These are the same
"authority re-derived at the point of use" defect and are cleaned up so the surface has one source.

**Why this priority**: the migration drift is a real (if narrow) data-loss path; the shim and
provenance items are lower-severity hygiene that the same root cause predicts.

**Acceptance**:
1. **Given** a project migrated by the finalize path, **when** the activation vocabulary is applied,
   **then** `activated_glossary_packs` is carried (no silent drop), and a guard test asserts the
   vocabulary lists are set-equal to the single derived authority.
2. **Given** the context module, **when** the re-export shim is retired, **then** test imports
   resolve from their leaf homes and no production behaviour changes.
3. **Given** relocated artefact YAMLs, **when** provenance strings are swept (after confirming they
   are not runtime-resolved), **then** they name the current `packs/built-in/<kind>/` paths.

### Edge Cases

- A test that legitimately needs a synthetic built-in tier must still be able to inject one — via the
  supported `SPEC_KITTY_PACKS_ROOT` override, not a raw nested-path parameter.
- Three of the twelve `ArtifactKind` members have **no** `packs/built-in/<plural>/` content dir:
  `mission_step_contract` (a Python package resource under `missions/`), `template` (resolved via the
  template catalog / `missions/` tree), and `anti_pattern` (a graph-only node). The single seam must
  **refuse** all three explicitly (a named, gated, *derived* carve-out), not paper over them with a
  second silent mechanism nor let `built_in_dir(template)` resolve to a non-existent directory.
- Architectural guard tests that name the old `src/doctrine/<kind>/built-in` path as a **forbidden
  pattern** are correct and must be left intact (not "repointed").

## Requirements *(mandatory)*

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Provide the single callable authority for built-in **kind** location, `built_in_dir(kind)` in the pack-paths module, returning `resolve_pack_root("built-in") / kind.plural` with the plural derived from the canonical `ArtifactKind` — not string literals. | Draft |
| FR-001b | Provide the companion authority for callers that need the built-in **root** itself (not a kind dir) — `built_in_root()` in the pack-paths module wrapping `resolve_pack_root("built-in")` — so root-needing readers (DRG loader/extractor, the reference-pointer walk, the `doctrine regenerate-graph` resolver) route through the seam instead of calling `resolve_pack_root("built-in")` directly. | Draft |
| FR-002 | Route **all** production readers of built-in location through FR-001/FR-001b, including the **variable-indirected** per-kind joins (`x = resolve_pack_root("built-in"); x / plural`) in the charter catalog and the pack validator, plus the per-kind repository defaults and the inline charter join sites; after this, no production module derives a built-in path except the two pack-paths authorities. | Draft |
| FR-003 | Remove the fail-open path: drop the `built_in_root` parameter (and the nested-shape `_built_in_dir`) from the doctrine service so a wrong/empty built-in shape is unconstructable; production behaviour is unchanged (every production caller passed `None`) — including removing the now-invalid `built_in_root=None` keyword from all ~7 production construction sites and the shipped skill-template examples. | Draft |
| FR-004 | Resolution of a missing/unlocatable built-in pack root fails closed with the named `PackRootNotFound` error; no code path returns an empty artefact set in its place. | Draft |
| FR-005 | `built_in_dir` refuses every non-file-based kind — the **derived complement** of "kinds with a `packs/built-in/<plural>/` content dir", i.e. `{mission_step_contract, template, anti_pattern}` — with a named, explanatory error, so those kinds cannot silently resolve to a non-existent directory (a fail-open). The set is derived, not hand-listed: a NEW content-dir SSOT attribute on `ArtifactKind` in `src/doctrine/artifact_kinds.py` (a `has_built_in_content_dir` property or `_BUILT_IN_CONTENT_KINDS` frozenset naming the 9 content-dir kinds) is the single source; the complement is computed as `ArtifactKind` members minus that attribute. The existing `_NON_AUGMENTATION_ELIGIBLE_KINDS` (`{TEMPLATE, ASSET, ANTI_PATTERN}`) is NOT reused — it carries `asset` (which has a content dir) and omits `mission_step_contract` (relocating step-contracts/templates is deferred to #3091; `anti_pattern` is graph-only). | Draft |
| FR-006 | Remove the vestigial nested-`/built-in` dual-read fallbacks in the charter catalog, compiler, and kind-vocabulary scanners, and the duplicated CWD ancestor-walk resolver (an intentional behaviour delta — see NFR-001 note), so exactly one location contract remains. | Draft |
| FR-007 | Resolve the 7 relocation-owned CI failures at the correct root: the glossary-gate fixture and the org-pack collision test load built-in content from `packs/built-in/` (the collision test via the no-explicit-root path). | Draft |
| FR-008 | Repoint the remaining stale relocation readers surfaced by the inventory (the false-green profile-inheritance fixture and any `parents[N]/src/doctrine` test that appends a relocated `<kind>/built-in`) to `packs/built-in/`. | Draft |
| FR-009 | Repoint shipped operator-facing error strings that name dead `src/doctrine/<kind>/built-in/` paths to the current `packs/built-in/<kind>/` locations. | Draft |
| FR-010 | Unify the charter activation-key vocabulary onto the single derived authority (`YAML_KEY_MAP`), replacing the hand-written literal copies; **fix the live drift** so the finalize migration carries `activated_glossary_packs`. | Draft |
| FR-011 | Retire the context module's private re-export shim: re-point test imports to their leaf modules and delete the re-export block, with no change to the module's public surface. | Draft |
| FR-012 | Sweep stale `src/doctrine/<kind>/built-in/` provenance strings inside relocated artefact YAMLs to `packs/built-in/<kind>/`, **after** confirming those fields are descriptive (not runtime-resolved); if any is runtime-resolved, treat it as a real reader under FR-008. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | No production behaviour change from the seam consolidation. **Exception, called out intentionally:** retiring the CWD-ancestor-walk resolver (FR-006) changes `doctrine regenerate-graph` root-resolution semantics for an operator standing in a checkout different from the installed module — a deliberate unification delta, not a regression. | Built-in doctrine graph identity unchanged (node/edge counts and full projection identical before/after); the full architectural suite passes; the CWD-walk delta is documented in the WP evidence. | Draft |
| NFR-002 | The single-authority invariant is CI-enforced, not conventional. | An architectural gate (in its OWN file, not folded into `test_no_dead_doctrine_paths.py` — cf. #3039) fails when any `src/` module outside the pack-paths authorities constructs a built-in **path join** — a `resolve_pack_root("built-in") / …` join **including the variable-indirected form** (`x = resolve_pack_root("built-in"); x / …`) or a `<path> / "built-in"` filesystem join — and names the offending site. The gate flags **joins only**; bare `"built-in"` string literals used as layer/provenance markers (~20 legitimate sites) are exempt, and a bare `resolve_pack_root("built-in")` root call is permitted (it IS the seam via FR-001b). | Draft |
| NFR-003 | Location resolution is fail-closed. | For every kind that HAS a `packs/built-in/<plural>/` content dir (the 9), the authority resolves inside it; the derived complement `{mission_step_contract, template, anti_pattern}` raises. The positive gate asserts existence **through `resolve_pack_root(...)`** (which handles the packaged-resource path — cf. #3036), not a raw repo-relative `.exists()`, so it survives the future wheel-split; a missing root raises; a positive anti-vacuity check asserts the shipped `agent_profiles` set is non-empty. | Draft |
| NFR-004 | No new lint/type regressions. | `ruff` and `mypy` pass with zero new issues on all changed modules. | Draft |
| NFR-005 | The carve-out cannot silently grow. | The complement is computed from the single content-dir SSOT attribute on `ArtifactKind` (`src/doctrine/artifact_kinds.py`), not a literal set in `pack_paths.py`; the per-kind coverage gate carries an explicit `#3091` marker for the **derived** complement set `{mission_step_contract, template, anti_pattern}`. Adding a fourth exempt kind (or a kind gaining a content dir) requires editing exactly that one SSOT attribute plus the marked, derived assertion — it cannot drift silently. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | `mission_step_contracts` is a **deliberate carve-out**: not relocated in this mission (that is #3091 / missions Phase-1b); it stays package-resource-resolved and the seam refuses it explicitly. | Active |
| C-002 | Out of scope — do NOT pull in: #3104/#3105/#3118 (the sibling `charter-pack-usage-journey` mission), #3101 wheel-split, #3102 doctrine/charter path-filtered CI, #3091 missions Phase-1b relocation, and the 34 pre-existing/unrelated CI reds (sync-3030 cluster, review-cycle, #2804/#3086 merge-gate, charter-cli 3045, charter-widen, #3092, and the accept-snapshot forgotten-regen). | Active |
| C-003 | This mission builds on `feat/relocate-builtin-doctrine-packs` (the closed relocation PR #3117's branch), preserving the verified move + landing folds; its work and the relocation land together as one PR to `main`. Because that PR's diff completes and merges the relocation, this mission's PR **also `Closes #3090`** (the relocation issue, still OPEN after #3117 was closed unmerged) — alongside #3119/#3106/#3116/#3120. | Active |
| C-004 | Cross-mission ordering: FR-010's migration-drift fix must land **before** the sibling mission's charter-resolver retarget (shared resolver surface + activation-store trust). | Active |
| C-005 | Bulk-edit discipline (DIRECTIVE_035): the same-string cross-file repoints (FR-008/009/012) are governed by an `occurrence_map.yaml` authored during plan; classify every occurrence before editing. | Active |
| C-006 | Do not "repoint" the architectural guard tests that name the old path as a forbidden pattern; those literals are correct. | Active |
| C-007 | Preserve the ability to inject a synthetic built-in tier in tests via the supported `SPEC_KITTY_PACKS_ROOT` override; only the nested-path parameter is removed. | Active |

### Key Entities

- **Built-in pack root** — `packs/built-in/`, the single on-disk home for shipped doctrine data,
  resolved fail-closed by `resolve_pack_root("built-in")`.
- **Built-in kind directory** — `packs/built-in/<plural>/`, owned by the new `built_in_dir(kind)`
  authority (plural derived from `ArtifactKind`).
- **Activation-key vocabulary** — the `activated_<plural>` config keys; single derived authority
  `YAML_KEY_MAP` (from `CHARTER_KIND_TOKENS`).
- **Carve-out kind** — `mission_step_contract`, resolved via package resource, refused by the seam.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Built-in on-disk location is resolved by exactly **one** authority; a CI gate proves no
  other `src/` module derives it (the gate exists and passes; the previously ~25 hand-join sites
  route through the authority).
- **SC-002**: A misconfigured/empty built-in root **fails loudly** in 100% of cases — no code path
  returns an empty doctrine set as a substitute (fail-closed + anti-vacuity gates pass).
- **SC-003**: The 7 relocation-owned test failures pass, and **zero** relocation readers remain on a
  dead `src/doctrine/<kind>/built-in/` path (excluding the intentional forbidden-pattern guards).
- **SC-004**: The built-in doctrine graph identity is unchanged (no behaviour drift).
- **SC-005**: A project migrated by the finalize path carries `activated_glossary_packs` (the live
  drift is closed), enforced by a set-equality guard test.
- **SC-006**: The 34 pre-existing/unrelated CI reds and the deferred issues (#3101/#3102/#3091,
  #3104/#3105/#3118) are untouched by this mission's diff.

## Assumptions

- The product relocation is essentially complete (every shipped repository already self-resolves via
  `resolve_pack_root`); the remaining work is consolidation + finishing readers, not re-moving data.
- Dropping the `built_in_root` parameter touches ~14 coupled test files (the "~60" figure was a
  conflation with a different, already-flat repository-level parameter that is **not** changed).
- The org-pack collision "regression" is stale test setup (`built_in_root=src/doctrine`), not a
  product bug; the collision pipeline is intact.
