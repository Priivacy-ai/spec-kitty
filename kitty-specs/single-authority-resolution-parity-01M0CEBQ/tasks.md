# Tasks — Single-Authority Resolution Parity

**Mission**: `single-authority-resolution-parity-01M0CEBQ` (M1 of the charter-resolution program) · Closes #3490, #3426, #2981
**Branch strategy**: planning base `spec/charter-resolution-parity` → merge target `spec/charter-resolution-parity` (single_branch topology; one PR to `main` at completion). Execution worktrees are allocated per computed lane from `lanes.json`.

Subtask rows below are **reference rows** (event-sourced completion via `spec-kitty agent tasks mark-status`), not checkboxes.

## Subtask Index

| ID | Description | WP | Parallel |
|----|-------------|----|----------|
| T001 | Red: nested org `*.tactic.yaml` dropped by the loader (fails pre-fix) | WP01 | |
| T002 | Red: nested org `*.agent.yaml` dropped by the loader (fails pre-fix) | WP01 | [P] |
| T003 | Create `doctrine/discovery_recursion.py` shared recursion authority (C-001, C-006) | WP01 | |
| T004 | `base.BaseDoctrineRepository._project_scan` → recursive via authority | WP01 | |
| T005 | Delete redundant `_project_scan` rglob overrides in styleguides + assets repos | WP01 | |
| T006 | `agent_profiles.repository._load`: org+project `recursive=True` via authority | WP01 | |
| T007 | Green + NFR-002 flat-layout byte-identical assertion | WP01 | |
| T008 | Red: nested org `*.styleguide.yaml` not resolved by `charter activate` (#3426) | WP02 | |
| T009 | Red: nested org `*.tactic.yaml` not resolved by the activation resolver | WP02 | [P] |
| T010 | `kind_vocabulary._org_scan_dirs`: flat org dir recursive from authority | WP02 | |
| T011 | `kind_vocabulary._layer_scan_dirs`: recursive from authority | WP02 | |
| T012 | Retire the `#3426` residual docstring; note pack_manager already-recursive parity | WP02 | |
| T013 | Green + loader↔resolver discovery parity for the exercised kinds | WP02 | |
| T014 | Red: `_singular_kind("glossary_packs")` returns wrong token (drift, fails open) | WP03 | |
| T015 | Red: `_infer_kind` blind to `glossary_packs` (drifted `_KIND_TO_PROPERTY`) | WP03 | [P] |
| T016 | Add derived `CHARTER_ACTIVATABLE_*` authority (10 kinds incl anti_pattern) in `artifact_kinds` | WP03 | |
| T017 | Collapse `activations._SINGULAR_TO_PLURAL_KIND` / `_PLURAL_TO_SINGULAR_KIND` onto authority (leave `_ALLOWED_KINDS` — documented non-goal) | WP03 | |
| T018 | Collapse `_activation_render._singular_kind` inverse + `_KIND_TO_PROPERTY` onto authority | WP03 | |
| T019 | Green + round-trip + 10-kind (incl anti_pattern) assertions | WP03 | |
| T020 | Red: `--include glossary_pack:<id>` raises "Unsupported selector kind" | WP04 | |
| T021 | Red: `--include anti_pattern:<id>` raises "Unsupported selector kind" | WP04 | [P] |
| T022 | Add `glossary_pack` renderer (via `service.glossary_packs`) to `_render_doctrine_artifact_include` | WP04 | |
| T023 | Make `anti_pattern` a recognized selector kind (standard not-found, never unsupported) | WP04 | |
| T024 | Green + every charter-activatable kind is a recognized selector kind (S1) | WP04 | |
| T025 | Extend totality gate: discover string-keyed kind maps + validate keys; exempt `_KIND_TO_NODE_KIND` from totality | WP05 | |
| T026 | Add behavioral loader↔resolver recursion-parity check (per kind, nested fixture) | WP05 | |
| T027 | C-002 negative test: `.provenance/*.yaml` + `.md` never captured by loader or resolver | WP05 | [P] |
| T028 | Falsifiability proof: reintroduce a divergence → gate reddens & names kind; restore → greens | WP05 | |
| T029 | Golden-count STOP verification: assert no cascade/DRG golden count moved (C-004) | WP05 | |

---

## Work Packages

### WP01 — Shared recursion authority + loader unification
- **Goal**: Make org/project doctrine discovery unconditionally recursive on the **loader** side, driven by one new doctrine-layer authority; delete the two redundant subclass overrides and the third `agent_profiles` divergence.
- **Priority**: P1 (foundation for the recursion stream). **MVP**.
- **Independent test**: author a `*.tactic.yaml` and `*.agent.yaml` one directory deep in an org root; the loader discovers both (parity with built-in); flat-layout output unchanged.
- **Requirements**: FR-001, NFR-001, NFR-002, C-001, C-002, C-006.
- **Subtasks**: T001, T002, T003, T004, T005, T006, T007
- **Dependencies**: none.
- **Risks**: `rglob` capturing unintended files → mitigated by kind-specific globs (C-002); NFR-002 asserted directly.
- **Est. prompt size**: ~420 lines.

### WP02 — Resolver recursion parity (kind_vocabulary)
- **Goal**: Make the **charter-activation resolver** derive recursion from the same authority so a nested org styleguide (or any kind) activates — closing the #3426 list-vs-activate asymmetry.
- **Priority**: P1.
- **Independent test**: a nested org `*.styleguide.yaml` resolves via `charter activate`; resolver discovery set equals loader discovery set for the exercised kinds.
- **Requirements**: FR-002, FR-003.
- **Subtasks**: T008, T009, T010, T011, T012, T013
- **Dependencies**: WP01 (imports the recursion authority).
- **Risks**: precedence/dedup order of flat-vs-legacy entries must be preserved (existing regression covers multi-root precedence) — do not reorder returned entries beyond the recursive-flag change.
- **Est. prompt size**: ~400 lines.

### WP03 — Derived kind-vocabulary authority + collapse
- **Goal**: Add one derived charter-activatable plural↔singular authority (10 kinds incl `anti_pattern`) and collapse the four hand copies, fixing the two drifted `_activation_render` maps.
- **Priority**: P1 (foundation for the vocabulary stream).
- **Independent test**: `_singular_kind("glossary_packs") == "glossary_pack"`; `_infer_kind` finds a `glossary_packs` artifact; the derived authority round-trips for all 10 kinds.
- **Requirements**: FR-004, FR-005.
- **Subtasks**: T014, T015, T016, T017, T018, T019
- **Dependencies**: none.
- **Risks**: adding `anti_patterns` to `_KIND_TO_PROPERTY` is inert-safe (`getattr(service, ..., None)`); C-004 — vocab helpers touch no DRG golden counts (verified in WP05).
- **Est. prompt size**: ~440 lines.

### WP04 — `--include` selector widening (FR-006)
- **Goal**: Make every charter-activatable kind a recognized `--include` selector kind — `glossary_pack` renders, `anti_pattern` resolves to a standard not-found — eliminating the "Unsupported selector kind" error for legitimate kinds.
- **Priority**: P2.
- **Independent test**: `--include glossary_pack:<id>` renders; `--include anti_pattern:<id>` returns a not-found (not "unsupported kind").
- **Requirements**: FR-006.
- **Subtasks**: T020, T021, T022, T023, T024
- **Dependencies**: WP03 (derives the recognized-selector-kind set from the shared vocabulary authority).
- **Risks**: `anti_pattern` has no artifact files — recognized-but-not-found is the intended semantics (SC-003), not a full render.
- **Est. prompt size**: ~320 lines.

### WP05 — Parity/totality gate (fail-loud + falsifiable)
- **Goal**: Extend the totality gate to cover string-keyed kind maps and add a behavioral loader↔resolver recursion-parity check plus the C-002 negative test and the falsifiability proof — and verify **zero** golden-count movement (C-004).
- **Priority**: P1 (durability guarantee — the join of both streams).
- **Independent test**: gate green when loader/resolver agree and maps consistent; reintroducing a `recursive=False` divergence reddens the gate and names the kind; `.provenance/*.yaml`/`.md` never captured.
- **Requirements**: FR-002, FR-007, NFR-003.
- **Subtasks**: T025, T026, T027, T028, T029
- **Dependencies**: WP01, WP02, WP03.
- **Risks**: the behavioral parity fixture must exercise every kind with a non-empty glob; the golden-count check must run against the mission base to prove no ripple.
- **Est. prompt size**: ~460 lines.

---

## Dependency graph & waves

```
Wave 1 (parallel):   WP01        WP03
                       │           │
Wave 2 (parallel):   WP02        WP04
                       └────┬──────┘
Wave 3:                   WP05   (depends WP01, WP02, WP03)
```

- **MVP**: WP01 (loader parity) — the core defect; WP02 completes the activation-side fix.
- **Parallelization**: WP01∥WP03 (disjoint files: doctrine loaders vs artifact_kinds+charter vocab); WP02∥WP04.
- **C-004 STOP gate**: WP05 T029 must show zero golden-count change vs base — if any count moves, STOP (belongs to M2/#3572 or M5/#2829).
