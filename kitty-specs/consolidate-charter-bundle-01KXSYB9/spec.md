# Mission Specification: Consolidate the Compiled Charter Bundle

**Mission Branch**: `feat/consolidate-charter-bundle`
**Created**: 2026-07-18
**Status**: Draft
**Input**: GitHub issue #2773 (under epic #2519 "Charter authoring & lifecycle robustness"), reshaped after an operator direction change (2026-07-18) recorded in [ADR 2026-07-18-1](../../docs/adr/3.x/2026-07-18-1-charter-yaml-authoring-authority-and-extractor-retirement.md). Scope: consolidate the four bundle files into one `charter.yaml` **and** invert charter authority so `charter.yaml` is the authoritative structured source and `charter.md` a curated companion — delivered as one coherent branch/PR.

## Context

Charter state is compiled from a hand-authored `charter.md` into four on-disk artifacts under `.kittify/charter/`: `governance.yaml`, `directives.yaml`, `metadata.yaml` (the "derived triad", produced by `sync.py::sync()`), and `references.yaml` (produced by `compiler.py`, and also the config↔references ID-parity authority in `consistency_check.py`).

This split is a standing drift/stopgap generator, and `charter.md` is **dual-owned** (hand-authored prose AND regenerated from an interview template by `compiler.py:421` — the #2772 clobber). A 4-lens grounding squad, a thesis/antithesis dialectic, and a neutral empirical trace (2026-07-18; captured in `research/charter-authority-inversion-assessment.md`) established:

- **`config.yaml activated_*` is the sole activation authority.** `answers.yaml` is provenance-only (zero runtime impact by design). The #2519 "disjoint activation ledgers" concern is largely a mislabel.
- **The "AI/hybrid extractor" is a phantom** — `extractor.py:807 extract_with_ai` returns `{}` with zero callers; the prose→triad extraction is 100% deterministic regex scraping.
- **`charter.md` prose is display-only for governance** — every governance/directive prose read flows into agent-facing display text; runtime governance/directive loaders read the **triad YAML**, not prose. The one behavioral prose read (doctrine language-scoping, `language_scope.py:103`) is an orthogonal tier-3 fallback whose authoritative source is `references.yaml`.
- Therefore seeding `charter.yaml` from the triad is a **deterministic, lossless yaml→yaml fold**; the inversion's cost is a governance/authoring-UX + schema-shape decision, not a data-migration hazard.

**Decision (ADR 2026-07-18-1):** `charter.yaml` becomes the project **charter** — the authoritative structured source for active doctrine. Per the charter's canonical purpose (ADR 2026-07-15-1 "charter activates doctrine"), it holds governance + directives + the resolving catalog **and the project activation state + overrides**, pack-shaped (same vocabulary as `src/charter/packs/default.yaml`) and overlaying that layer-0 default pack. The activation state (`activated_*`) **relocates out of `.kittify/config.yaml` into `charter.yaml`**, and the activation engine (`commit_plan`/`merge_defaults`/`PackContext.from_config`) is re-pointed. `charter.md` becomes a hand-authored curated companion (never resolving, never clobbered); the prose→triad extractor is retired. `charter.yaml` is **git-tracked** and authorable. The full inversion is delivered in **this** mission, on one branch, PRed as a consistent whole — no intermediate PR ships a half-inverted state. Fenced OUT (C-008): the broader ADR 2026-07-15-1 runtime-gating/DRG-node restructure.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One authoritative structured charter.yaml (Priority: P1)

As a charter/doctrine maintainer, I want a single compiled `charter.yaml` with first-class *authorable* fields (governance knobs, directive declarations, the resolving/artifact-ID catalog, and a reference to activation state) so charter state has one structured source of truth instead of four split files.

**Why this priority**: The keystone. Every other story consumes it.

**Independent Test**: Compile the bundle; assert one `charter.yaml` is produced whose structured sections carry governance/directives/catalog; assert the manifest's derived set and content-hash input set both equal `{charter.yaml}`.

**Acceptance Scenarios**:

1. **Given** a compiled charter tree, **When** the bundle is built, **Then** `charter.yaml` is the single bundle-derived artifact and its structured sections hold governance + directives + the artifact-ID catalog + an activation reference.
2. **Given** the manifest, **When** its `derived_files` and content-hash input set are compared, **Then** they are identical (`{charter.yaml}`) — the historic 4-vs-3 mismatch is structurally impossible.

### User Story 2 - Freshness, parity, and resolving read charter.yaml (Priority: P1)

As the freshness / ID-parity / resolving code paths, I want to read charter state from the single `charter.yaml`, so a mutation is reflected reliably and there is no split-brain between a "hash file" and a "parity file".

**Why this priority**: Closes the epic's core defect (silently-drifting freshness) and moves parity authority off `references.yaml`.

**Independent Test**: Point freshness content-hash and config↔charter parity at `charter.yaml`; assert no legacy split file is read at resolve time; assert a mutation flips the freshness signal with no permanent-stale dead-end.

**Acceptance Scenarios**:

1. **Given** a compiled `charter.yaml`, **When** freshness is computed, **Then** the content hash is over `charter.yaml` only and a mutation changes it (no permanent-stale from a missing non-derived file).
2. **Given** a compiled `charter.yaml`, **When** config↔charter ID-parity runs, **Then** the available-artifact-ID catalog is read from `charter.yaml` and `references.yaml` is not consulted.
3. **Given** the consolidation, **When** the #2758 fail-closed preflight + #2759 references-parity read conditions are evaluated, **Then** they are moot/removed.

### User Story 3 - charter.md is a curated companion, never clobbered (Priority: P1)

As a charter maintainer, I want `charter.md` to be a hand-authored curated rationale companion that no generate/compile path ever overwrites and that is never a charter-resolving input.

**Why this priority**: Eliminates the #2772 P0 clobber (folded into this mission) and enforces the "prose never resolves" invariant.

**Independent Test**: Run `charter generate`/refresh against a curated `charter.md`; assert the prose is untouched; assert no runtime governance/resolving decision reads `charter.md` content.

**Acceptance Scenarios**:

1. **Given** a curated `charter.md`, **When** `charter generate --force` (or any compile/refresh) runs, **Then** the curated prose is preserved (the `compiler.py:421` clobber writer is removed/guarded).
2. **Given** the inverted model, **When** the codebase is grepped for governance/resolving reads of `charter.md` content, **Then** none feed a decision — `charter.md` is display/companion only.

### User Story 4 - Retire the prose→triad extractor (Priority: P1)

As the governance/directive loaders, I want to read structured fields from `charter.yaml` directly, so the brittle deterministic prose→triad regex extractor and the `sync()` backward scrape can be deleted (deterministic-first).

**Why this priority**: The real deterministic-first win — removes the brittle heading-classify/`[:50]`-title/bullet-regex scrape that silently drops or mangles knobs on innocuous prose edits.

**Independent Test**: Re-point `load_governance_config`/`load_directives_config` to `charter.yaml`; delete `extractor.py` `SECTION_MAPPING` + the backward scrape; assert governance/directive resolution is behavior-preserving via the existing regression nets.

**Acceptance Scenarios**:

1. **Given** the inverted model, **When** governance/directive config is loaded, **Then** it comes from `charter.yaml` structured fields, not from a prose scrape.
2. **Given** the retirement, **When** the repo is grepped, **Then** the prose→triad `SECTION_MAPPING` extractor and the `sync()` backward scrape are deleted, and the display prose-consumers are re-pointed.

### User Story 5 - Legacy projects migrate fail-loud (Priority: P1)

As an operator upgrading a project (with the four split files on disk), I want a mandatory, idempotent, one-pass migration to `charter.yaml`, and until it runs I want charter operations to fail loudly with an actionable remediation — never silently honoring a retired split file.

**Why this priority**: Fail-loud is binding governance (no silent fallback). The migration is a deterministic yaml→yaml fold (triad + references catalog → charter.yaml).

**Independent Test**: On a legacy fixture (four files, no `charter.yaml`), assert charter ops fail loud with one actionable message; run the migration; assert `charter.yaml` is produced, the four files retire, and a second run reports zero changes.

**Acceptance Scenarios**:

1. **Given** a pre-mission project, **When** a charter operation runs, **Then** it fails loudly with a single actionable "run the migration" message and does not read the legacy files.
2. **Given** the same project, **When** the migration runs, **Then** it emits `charter.yaml` from the legacy YAML deterministically, retires the four files, and is idempotent.

### User Story 6 - No behavioral prose reads remain (Priority: P2)

As the doctrine language-scoping path, I want the tier-3 `charter.md` free-text language fallback (`language_scope.py:103`) migrated to the structured source (`references.yaml`/`charter.yaml`), so `charter.md` prose is not a behavioral input anywhere.

**Why this priority**: Closes the one orthogonal behavioral prose read the empirical trace found; makes "charter.md never resolves" literally true. Lower priority — it is a degraded last-resort fallback today.

**Independent Test**: Remove the `charter.md` tier-3 branch; assert language scoping resolves from the structured source; assert no `charter.md` read feeds `applies_to_languages_match`.

**Acceptance Scenarios**:

1. **Given** the migration, **When** doctrine language-scoping resolves active languages, **Then** it reads the structured source and never `charter.md` prose.

### User Story 7 - charter.yaml owns activation (Priority: P1)

As the project charter, I want to hold the project's active-doctrine declaration (`activated_*` / `activated_kinds` / `mission_type_activations`) and overrides directly — pack-shaped, overlaying the layer-0 `default.yaml` — so "what doctrine is active" is owned by the charter, per its canonical purpose, not split into `.kittify/config.yaml`.

**Why this priority**: The operator-confirmed core of the inversion (ADR 2026-07-18-1). Aligns the charter with its canonical "charter activates doctrine" purpose (ADR 2026-07-15-1) and unifies local + pack-provisioned activation.

**Independent Test**: Relocate `activated_*` into `charter.yaml`; re-point `commit_plan`/`merge_defaults`/`PackContext.from_config`; assert activation resolution + parity + DRG-filter behavior is unchanged (existing suites green) and `.kittify/config.yaml` no longer carries `activated_*`.

**Acceptance Scenarios**:

1. **Given** a project, **When** a doctrine element is activated/deactivated via the CLI, **Then** the change is written to `charter.yaml`, not `.kittify/config.yaml`.
2. **Given** `charter.yaml` with flat activation keys, **When** activation is resolved by `PackContext.from_config`, **Then** the three-state semantics are preserved (absent→default-pack fallback, `[]`→fail-closed, populated→exact) and `default.yaml` seeds absent keys.
3. **Given** the relocation, **When** the activation-parity + DRG-filter suites run, **Then** they pass unchanged (behavior-preserving).

### Edge Cases

- Partial/corrupt legacy state (some of the four files missing) → migration fails loud with a clear diagnostic, no partial migrate.
- Corrupt/unreadable `charter.yaml` → fail-closed verification error (preserve the `ReferenceCatalogError` #2530 semantics, re-homed onto `charter.yaml`).
- CRLF/BOM differences in `charter.yaml` across platforms → normalized by the #2732 content-identity recipe; hash stable.
- `merge_defaults` second activation writer (bypasses `commit_plan`) → the read-path parity stays writer-agnostic (reads `charter.yaml` + `config.yaml` directly).
- A curated `charter.md` edited between compiles → never scraped, never clobbered; freshness keys off `charter.yaml`, not `charter.md`.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Authorable structured `charter.yaml` | As a maintainer, I want one `charter.yaml` with first-class authorable governance/directive/catalog/activation-reference fields. | High | Open |
| FR-002 | Manifest derived-set == hash-set | As the manifest, I want `derived_files` + `derivation_sources` + content-hash set to all equal `{charter.yaml}` (schema-version bump). | High | Open |
| FR-003 | Freshness reads `charter.yaml` | As the freshness read-path, I want the content hash over `charter.yaml`, reflecting mutations, no permanent-stale. | High | Open |
| FR-004 | Parity reads `charter.yaml` | As ID-parity, I want the artifact-ID catalog read from `charter.yaml`; `references.yaml` no longer the authority. | High | Open |
| FR-005 | Re-point resolving consumers | As resolver/compiler/context/CLI-status/state-contract, I want to read `charter.yaml` instead of the four files. | High | Open |
| FR-006 | Retire the prose→triad extractor | As governance/directive loaders, I want structured reads from `charter.yaml`; delete `extractor.py` `SECTION_MAPPING` + `sync()` backward scrape. | High | Open |
| FR-007 | charter.md curated companion, never clobbered | As a maintainer, I want `charter.md` hand-authored, never written by a generate/compile path (remove the `compiler.py:421` clobber), never a resolving input — folds #2772. | High | Open |
| FR-008 | Re-point display prose-consumers | As the context/compact renderers, I want the display prose-consumers (`_extract_policy_summary`, `render_critical_section_bodies`, section anchors) sourced coherently, with no governance decision reading `charter.md` prose. | Medium | Open |
| FR-009 | Migrate the language tier-3 fallback | As doctrine language-scoping, I want the `charter.md` free-text fallback migrated to the structured source, removing the last behavioral prose read. | Medium | Open |
| FR-010 | Mandatory fail-loud migration | As an operator, I want an idempotent one-pass migration (legacy four files → `charter.yaml`); fail loud until migrated, no silent fallback. | High | Open |
| FR-011 | Retire the four files + moot stopgaps | As a maintainer, I want the four files removed from emission/manifest/gitignore, and the now-moot #2758 preflight + #2759 references-parity read removed, tests updated. | Medium | Open |
| FR-012 | Relocate activation into `charter.yaml` | As the project charter, I want `activated_*` / `activated_kinds` / `mission_type_activations` to live in `charter.yaml` (pack-shaped), not `.kittify/config.yaml`, so the charter owns "what doctrine is active". | High | Open |
| FR-013 | Re-point the activation engine | As `commit_plan` / `merge_defaults` / `PackContext.from_config`, I want to read/write the activation state from `charter.yaml`; `config.yaml` retains only non-doctrine config; activation-parity + DRG-filter behavior is preserved. | High | Open |
| FR-014 | charter.yaml activation with default.yaml fallback | As the activation resolver, I want `charter.yaml`'s flat activation resolved by `PackContext.from_config` with `default.yaml` as the absent-key fallback/seed (existing three-state semantics preserved). (Multi-tier org⊆team⊆repo accumulation is forward-intent, C-008.) | High | Open |
| FR-015 | config.yaml charter pointer | As the resolver, I want to locate the active `charter.yaml` via a single `charter:` pointer in `.kittify/config.yaml`, so a charter swap (experiment / local redirect / cross-project) is a one-line change; a pointer to a missing/unreadable file fails loud (no fallback). | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Content-identity preserved | The single-file hash MUST compose with the #2732 content-identity recipe (per-file BOM-strip/CRLF normalization, write-side manifest stamps, `built_in_only` normalization, fresh-seed early-exit). Measurable: existing content-identity tests pass unchanged; an unchanged `charter.yaml` yields a byte-identical hash across runs/platforms. | Reliability | High | Open |
| NFR-002 | No hot-path subprocess | Default freshness read spawns ZERO synthesis/regenerate subprocess. Measurable: a subprocess/call-count spy over a default `compute_freshness` read asserts 0 spawns. | Performance | High | Open |
| NFR-003 | Deterministic idempotent migration | Migration is a deterministic yaml→yaml fold (no prose parsing) and idempotent one-pass. Measurable: a second run reports 0 file changes and exits success. | Reliability | High | Open |
| NFR-004 | Lint/type/complexity clean | ruff + mypy --strict clean, zero new suppressions; complexity ≤15 per function; ≥3× literals hoisted. Measurable: `ruff check` + `mypy --strict` on the diff report 0 new issues. | Maintainability | High | Open |
| NFR-005 | No half-inverted ship | No intermediate commit/PR leaves the system in a half-inverted state (charter.yaml authoritative but consumers/extractor inconsistent). Measurable: the full suite is green at the mission's single PR head; WPs are sequenced tidy-first within the one branch. | Reliability | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | charter.yaml authoritative; charter.md companion | `charter.yaml` is the authoritative structured source; `charter.md` is a hand-authored curated companion — never a resolving input, never clobbered. (Inverts the pre-2026-07-18 fence per ADR 2026-07-18-1.) | Technical | High | Open |
| C-002 | Layer boundary preserved | `src/charter/` (incl. `commit_plan`) stays pure charter and MUST NOT import `specify_cli`. Freshness read-path parity stays in `specify_cli.charter_runtime`. | Technical | High | Open |
| C-003 | Fail-loud, no silent fallback | Retiring the four files MUST fail loud on an un-migrated project; no `None`→default or read-legacy-file fallback in resolver/parity/freshness. | Technical | High | Open |
| C-004 | Canonical manifest schema (bump once) | Reuse the canonical `CharterBundleManifest` typed contract with a single schema-version bump + migration; do not hand-roll a parallel manifest. | Technical | High | Open |
| C-005 | charter.yaml owns activation | The project activation state (`activated_*` / `activated_kinds` / `mission_type_activations`) relocates OUT of `.kittify/config.yaml` INTO `charter.yaml`; the activation engine (`commit_plan` in `activation_engine.py`, `merge_defaults`) and `PackContext.from_config` read/write `charter.yaml` (flat activation keys); `default.yaml` supplies the absent-key fallback/seed (layer-0). `config.yaml` keeps only non-doctrine config (incl. `org_packs`) **plus a one-line `charter:` pointer** to the active charter (the resolver locates `charter.yaml` via it; a charter swap is a one-line change — supports experimentation / local redirects / cross-project charters and minimizes multi-user merge conflicts). `answers.yaml` stays provenance-only. | Technical | High | Open |
| C-008 | ADR 2026-07-15-1 runtime-gating fenced OUT | This mission advances the activation-surface/ownership axis only. The broader ADR 2026-07-15-1 restructure — runtime activation-gating and first-class DRG nodes for `mission_type`/`gate`/`asset` — is OUT of scope. Local-only/personal doctrine is assumed to activate via the same pack-shaped mechanism; the local-override mechanism is a separately-tracked gap. | Technical | High | Open |
| C-006 | One branch, one PR, no half-inverted ship | The full inversion lands on `feat/consolidate-charter-bundle`, PRed as a consistent whole, sequenced tidy-first. | Process | High | Open |
| C-007 | Foldables assessed at plan | #2554 (bdd-scenario-lifecycle parity warning) and #2373 (build_charter_context dirty-tree render side-effect) are foldability candidates evaluated at plan-time, not committed scope. | Process | Low | Open |

### Key Entities

- **`charter.yaml`**: the project **charter** — a single git-tracked, *authorable*, pack-shaped structured artifact. Sections: governance knobs, directive declarations, the references/artifact-ID catalog (derived-but-committed projection kept honest by parity + freshness), and **the project activation state + overrides** (`activated_*` / `activated_kinds` / `mission_type_activations`). Overlays the layer-0 `default.yaml` pack. Governance/directives/activation are authored; the catalog is a derived projection.
- **`.kittify/config.yaml`**: retains **non-doctrine** config (agents, tooling) + a single `charter:` **pointer** to the active charter file (the resolver's indirection point; enables one-line charter swaps / redirects / cross-project charters and reduces multi-user merge conflicts) after activation relocates to `charter.yaml`.
- **`src/charter/packs/default.yaml`**: the shipped layer-0 default charter pack `charter.yaml` overlays.
- **`charter.md`**: hand-authored curated rationale companion. Never a resolving input; never written by a generate/compile path.
- **`CharterBundleManifest`** (`src/charter/bundle.py`): typed derivation contract; single schema-version bump; `tracked_files`/`derived_files`/`derivation_sources`/hash-set point at `charter.yaml`.
- **Consolidation migration**: `upgrade/migrations/` step folding the legacy four files → `charter.yaml`, deterministic + idempotent + fail-loud.
- **Retired: the prose→triad extractor** (`extractor.py` `SECTION_MAPPING`) + `sync()` backward scrape.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: After any charter mutation (activate/deactivate/recompile), the freshness signal reflects the change 100% of the time in the test matrix — zero silently-fresh and zero permanent-stale outcomes.
- **SC-002**: Zero runtime governance/resolving reads consult a retired split file OR `charter.md` prose — a `src/` grep shows the four filenames only in migration code, and no governance decision reads `charter.md`.
- **SC-003**: A legacy project surfaces exactly one actionable migration prompt (not a dead-end), migrates deterministically, and a re-run reports zero changes.
- **SC-004**: The manifest's content-hash input set is `{charter.yaml}` (a field distinct from `derived_files`, which is empty), and `_validate`'s tracked∩derived invariant is preserved; the #2758/#2759 stopgap code paths are removed.
- **SC-005**: The #2732 content-identity guarantees are intact — the content-identity suite passes unchanged; an unchanged `charter.yaml` hashes identically across runs/platforms.
- **SC-006**: `charter generate`/refresh never overwrites a curated `charter.md` (folds #2772); a regression test pins prose survival.
- **SC-007**: The prose→triad `SECTION_MAPPING` extractor + `sync()` backward scrape are deleted; governance/directive loaders read `charter.yaml`.
- **SC-008**: The project activation state lives in `charter.yaml` (not `.kittify/config.yaml`); `commit_plan`/`merge_defaults`/`PackContext.from_config` read/write it there; the existing activation-parity + DRG-filter test suites pass unchanged (behavior-preserving relocation); `charter.yaml` overlays `default.yaml`.

## Assumptions

- `charter.yaml` is emitted/authored via the compile pipeline; initially seeded from the triad, becoming the authoring surface as the extractor retires.
- The migration lives in the established `upgrade/migrations/` framework, gated by the manifest schema-version bump.
- Downstream SaaS/tracker consumers read charter state only through the CLI surfaces being re-pointed (verified in a plan-time code-state scout).
- The `ReferenceCatalogError` fail-closed semantics (#2530) are preserved, re-homed onto `charter.yaml`.

## Out of Scope

- Broader **#2519** authoring/charter-init surface beyond this consolidation + inversion.
- Any change to the eager FSM hot-path or runtime resolver *signature*.
- **ADR 2026-07-15-1 runtime-gating restructure** — runtime activation-gating and first-class DRG nodes for `mission_type`/`gate`/`asset` (C-008). This mission relocates the activation *surface* only.
- **The local doctrine-override mechanism** — assumed to activate via the same pack-shaped mechanism; the mechanism itself is a separately-tracked gap (this mission designs `charter.yaml` to be compatible, not the override engine).
- **Collapsing the two activation writers into one** — both `commit_plan` and `merge_defaults` are re-pointed to `charter.yaml` (FR-013), but unifying them into a single validated writer (removing the `merge_defaults` `commit_plan` bypass) stays a separate #2519 item.
- **#2554 / #2373** unless explicitly folded at plan-time (C-007).

## Related Issues

- Parent epic: **#2519**.
- Closes: **#2773**; folds/closes **#2772** (charter.md non-destructive refresh — subsumed by FR-007).
- Governing decision: **ADR 2026-07-18-1**; aligns with **ADR 2026-07-15-1** (activation axis).
- Delivered by PR #2781 (now CLOSED): #2758, #2759 (their stopgaps are removed here).
- Foldability candidates (assess at plan): #2554, #2373.
