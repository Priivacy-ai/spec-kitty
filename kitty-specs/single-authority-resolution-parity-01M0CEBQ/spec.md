# Mission Specification: Single-Authority Resolution Parity

**Mission Branch**: `spec/charter-resolution-parity`
**Created**: 2026-08-19
**Status**: Draft
**Input**: First mission of the charter-resolution program (rolls up to reach epic #3530 and fail-loud epic #3410). Closes #3490, #3426, #2981.

## Overview

Doctrine authored in an **org pack** or a **project overlay** silently under-loads or drops out of charter activation, while the equivalent **built-in** doctrine loads completely. Two independent causes produce the same fake-green symptom (clean checks, missing content):

1. **Recursion divergence.** Built-in doctrine discovery scans subdirectories recursively; org/project discovery does not. Worse, the component that *loads* doctrine and the component that *resolves* it for charter activation each decide recursion independently, so they disagree per kind.
2. **Hand-restated kind vocabulary.** The plural↔singular doctrine-kind mapping is copied by hand in several places; two copies have drifted and fail open (rendering the wrong token, blinding kind inference), and the copies escape the existing consistency gate.

This mission makes org/project doctrine load as completely as built-in, makes the loader and resolver agree **by construction**, derives the kind vocabulary from a **single authority**, and adds a **parity/totality gate** so any future divergence fails loudly instead of silently.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Nested org/project doctrine is discovered and activated (Priority: P1)

An operator authors doctrine (a tactic, styleguide, agent-profile, etc.) inside a subdirectory of an org pack or project overlay — mirroring how the built-in corpus organizes its own content.

**Why this priority**: This is the core defect (#3490, #3426). Today the operator gets a green run and silently missing governance — measured as a 71% undercount for tactics and dropped org styleguides. Without this, authored doctrine cannot be trusted to take effect.

**Independent Test**: Author an org pack and a project overlay with a `*.tactic.yaml` and a `*.agent.yaml` nested one directory deep; run discovery/activation; assert the nested artifacts are discovered, listed, and activatable — matching the built-in tier's behavior for the same shape.

**Acceptance Scenarios**:

1. **Given** an org pack whose tactic lives in a nested subdirectory, **When** doctrine is loaded, **Then** the nested tactic is discovered (parity with built-in), not dropped.
2. **Given** an org pack whose styleguide lives in a subdirectory, **When** `charter activate` runs, **Then** the styleguide activates (closes #3426) instead of being silently skipped.
3. **Given** a `.provenance/*.yaml` sidecar and a `.md` file in the same nested directory, **When** doctrine is loaded, **Then** those non-artifact files are **not** captured (recursion is kind-specific).

### User Story 2 - Loader and resolver can never silently disagree (Priority: P1)

A maintainer changes doctrine discovery behavior and must be unable to leave the loader and the activation resolver out of sync.

**Why this priority**: The structural root cause of #3490/#3426 is that two authorities decide recursion independently. A one-time fix that does not bind them will re-drift. The gate is what makes the fix durable.

**Independent Test**: Reintroduce a divergence (make one component non-recursive for one kind) and assert the parity gate fails; restore and assert it passes.

**Acceptance Scenarios**:

1. **Given** the loader and resolver in agreement, **When** the parity gate runs, **Then** it passes.
2. **Given** a deliberately reintroduced recursion divergence for any kind, **When** the gate runs, **Then** it fails loudly and names the diverging kind.
3. **Given** a kind-map authority keyed by string (which previously escaped the consistency gate), **When** an entry is added or removed inconsistently, **Then** the gate fails.

### User Story 3 - One consistent kind vocabulary end to end (Priority: P2)

An operator activates or `--include`s a doctrine kind and the system uses one consistent plural↔singular vocabulary, with no kind silently mislabeled, dropped, or unrunnable.

**Why this priority**: #2981 — the hand-copied kind map drifted two kinds behind and fails open, hard-erroring an operator's `--include` stanza and blinding kind inference for `glossary_packs`/`anti_patterns`.

**Independent Test**: For every charter-activatable kind, assert the derived map round-trips plural↔singular and that an `--include <kind>` stanza resolves to a runnable selector.

**Acceptance Scenarios**:

1. **Given** any charter-activatable kind, **When** its plural and singular forms are resolved, **Then** they agree via the single derived authority (no drifted copy).
2. **Given** a `--include glossary_pack` or `--include anti_pattern` stanza, **When** activation runs, **Then** it resolves rather than erroring on an unknown selector.

### Edge Cases

- A same-id artifact authored in a nested directory that **collides** with a flat one of the same kind → the overlay/dedup rule applies and emits a collision warning (no silent overwrite).
- A kind whose built-in tier already scanned recursively via a bespoke override → after unification the override is redundant and removed without changing discovered output.
- An operator authors a doctrine kind that is loadable but not charter-activatable (e.g. a project-tier `procedure`) → discovery is unchanged; activation vocabulary is unaffected (node-emission for such kinds is out of scope — see C-004).

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Recursive org/project discovery (loader) | As an operator, I want doctrine of every kind authored in a nested org/project subdirectory to be discovered with the same recursion as built-in, so that nothing I author silently under-loads. | High | Open |
| FR-002 | Loader/resolver discovery parity | As a maintainer, I want the charter-activation resolver to discover exactly the doctrine paths the loader does, for every kind, so that the two cannot disagree. | High | Open |
| FR-003 | Nested org artifacts activate | As an operator, I want an org styleguide (or any kind) authored in a subdirectory to activate via `charter activate`, so that subdirectory layout is not a silent trap (closes #3426). | High | Open |
| FR-004 | Single derived kind-vocabulary authority | As a maintainer, I want the plural↔singular kind map derived from one authority with the hand-restated copies collapsed onto it, so that copies cannot drift. | High | Open |
| FR-005 | Preserve the anti_pattern kind entry | As a maintainer, I want the charter-activatable kind map to retain the `anti_patterns` entry (10 kinds), so that existing behavior is preserved rather than dropped by a strict derivation. | Medium | Open |
| FR-006 | Runnable selector for every activatable kind | As an operator, I want the `--include` selector vocabulary to accept every charter-activatable kind including `glossary_pack` and `anti_pattern`, so that a correctly-derived stanza resolves instead of erroring. | Medium | Open |
| FR-007 | Parity/totality gate (fail-loud) | As a maintainer, I want a gate that fails loudly when the loader and resolver recursion sets diverge, or when any kind-map authority (including string-keyed ones) is inconsistent, so that this class of drift cannot silently return. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Load-completeness parity | For an identical nested directory shape, the set of artifacts discovered at the org/project tier equals the set discovered at the built-in tier for every kind (measured parity = 100%; the tactic undercount drops from 71% to 0%). | Correctness | High | Open |
| NFR-002 | No discovery regression | Every doctrine artifact discoverable before this mission remains discoverable after; flat-layout activation output is byte-identical. | Reliability | High | Open |
| NFR-003 | Falsifiable gate coverage | The parity/totality gate covers 100% of the recursion authorities and kind-map authorities, including string-keyed maps; a deliberately reintroduced divergence reddens the gate (proven both directions on one commit). | Correctness | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Unconditional recursion (decision) | Org/project doctrine discovery is **unconditionally recursive**, matching built-in; recursion is not a per-kind flag. | Technical | High | Open |
| C-002 | Kind-specific globs | Recursion must remain kind-specific (e.g. `*.tactic.yaml`), so non-artifact sidecars (`.provenance/*.yaml`) and `.md` files are never captured. | Technical | High | Open |
| C-003 | Preserve 10-kind map (decision) | The charter-activatable kind map retains the `anti_patterns` entry (10 kinds), not the strict 9-kind `CHARTER_KIND_TOKENS` derivation. | Technical | High | Open |
| C-004 | No cascade-reach change | This mission does **not** change cascade reach and must produce no golden-count ripple; the DRG read-path bridge (#3572), cascade completeness (#2829), delivery/reach (#3488/#3489/#3176), and project-tier node emission (#3038) are out of scope. | Technical | High | Open |
| C-005 | Zero new suppressions | New code passes `ruff` and `mypy --strict` with zero suppressions; no `# noqa`/`# type: ignore`/per-file-ignore additions. | Technical | High | Open |
| C-006 | Layer boundary preserved | The shared recursion/vocabulary authority lives in the doctrine layer; `charter` must not import `specify_cli`. | Technical | High | Open |

### Key Entities

- **Doctrine artifact**: a governance unit with a `kind`, `id`, `tier` (built-in / org / project), and filesystem path.
- **Recursion authority**: the single policy both the loader and the activation resolver read to decide subdirectory scanning.
- **Kind-vocabulary map**: the plural↔singular doctrine-kind mapping, derived from one canonical source rather than hand-restated.
- **Parity/totality gate**: the automated check binding loader↔resolver recursion agreement and kind-map consistency, covering string-keyed maps.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator authoring a tactic (or any kind) in a nested org-pack subdirectory sees it discovered and activatable — **0 silent drops** (baseline: 71% tactic undercount).
- **SC-002**: The loader and resolver agree on discoverable doctrine for **100% of kinds**; a reintroduced divergence fails the gate and names the kind.
- **SC-003**: A `charter activate --include glossary_pack` (or `anti_pattern`) stanza **resolves** rather than erroring on an unknown selector.
- **SC-004**: **No regression** — every doctrine artifact discoverable before the mission remains discoverable; flat-layout activation output is unchanged.

## Assumptions

- The house "derive from a single authority" pattern already exists on `main` (`PROJECT_KIND_DIRS`, `ORG_PLURAL_TO_SINGULAR_KIND` / `_derive_plural_to_singular`) and is the model to follow; #2981's WP08 precedent is already landed — do not redo it.
- Making discovery unconditionally recursive is safe because globs are kind-specific; nested non-artifact files do not match.
- No coordination topology is required (topology: single_branch); planning artifacts land on `spec/charter-resolution-parity`, which later opens one PR to `main`.

## Technical Context *(non-normative — informs planning, not acceptance)*

Seams surfaced by the charter-resolution investigation (against `main` @ post-#3534), to orient `/spec-kitty.plan`:

- **Recursion divergence (loader):** `doctrine/base.py::_project_scan` (glob) vs `_load_built_in_items` (rglob); `agent_profiles/repository.py::_load` (a third, separate divergence site — does not inherit the base); redundant `rglob` overrides in `styleguides/repository.py` and `assets/repository.py`.
- **Recursion divergence (resolver):** `charter/kind_vocabulary.py::_org_scan_dirs` / `_layer_scan_dirs` emit `recursive=False`.
- **Kind-map duplicators (#2981):** `charter/activations.py` (`_SINGULAR_TO_PLURAL_KIND`, `_PLURAL_TO_SINGULAR_KIND`), `charter/_activation_render.py` (`_singular_kind`, `_KIND_TO_PROPERTY`), and `charter/synthesizer/project_drg.py::_KIND_TO_NODE_KIND` (string-keyed → escapes `tests/doctrine/drg/test_kind_mapping_totality.py`).
- **Gate:** extend `test_kind_mapping_totality.py` (or a sibling) to cover string-keyed maps and add loader↔resolver recursion parity.

This section is guidance; the normative contract is the FR/NFR/C tables above.
