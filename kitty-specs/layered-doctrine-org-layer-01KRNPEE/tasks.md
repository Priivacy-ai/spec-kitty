# Tasks: Layered Doctrine Resolution — Org Layer

**Mission**: `layered-doctrine-org-layer-01KRNPEE`  
**Branch**: `feat/org-doctrine-layer` → `feat/org-doctrine-layer`  
**Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)  
**Total WPs**: 9 | **Total subtasks**: 50

---

## Subtask Index

| ID | Description | WP | Parallel |
|---|---|---|---|
| T001 | Add `load_graph_or_dir(path)` to `doctrine/drg/loader.py` | WP01 | |
| T002 | Export `load_graph_or_dir` from `doctrine/drg/__init__.py` | WP01 | [P] |
| T003 | Update `_drg_helpers.load_validated_graph()` to use `load_graph_or_dir` for shipped + project | WP01 | |
| T004 | Update all hardcoded `graph.yaml` call sites in charter synthesizer pipeline | WP01 | |
| T005 | Unit tests for `load_graph_or_dir` (single file, directory, empty, mixed invalid) | WP01 | [P] |
| T006 | Add `org_dir: Path \| None` parameter to `BaseDoctrineRepository.__init__` | WP02 | |
| T007 | Add `_apply_org_overrides()` method with provenance tagging | WP02 | |
| T008 | Update `_load()` to invoke org override step between shipped and project | WP02 | |
| T009 | Update all 8 repository subclasses to accept and pass `org_dir` | WP02 | |
| T010 | Unit tests for three-layer merge (all collision scenarios, bad-file resilience) | WP02 | [P] |
| T011 | Add `org_roots: list[Path]` to `DoctrineService.__init__` and `_org_dir()` helper | WP03 | |
| T012 | Pass `org_dir` through all 8 repository property factories in `DoctrineService` | WP03 | |
| T013 | Update `charter/compiler.py` and `reference_resolver.py` to use `load_graph_or_dir` | WP03 | [P] |
| T014 | Add `_resolve_org_root(repo_root) -> Path \| None` helper to `_drg_helpers.py` | WP03 | |
| T015 | Unit tests for `DoctrineService` with `org_roots` (empty, single, fallback) | WP03 | [P] |
| T016 | Define `OrgDoctrineSource` Protocol and `FetchResult` dataclass | WP04 | |
| T017 | Implement `GitSource` (subprocess git, SSH/GIT_TOKEN auth) | WP04 | [P] |
| T018 | Implement `HttpsBundleSource` (requests download, tarball extraction, atomic write) | WP04 | [P] |
| T019 | Implement `ApiSource` (per-type GET endpoints, DRG extensions, version endpoint) | WP04 | [P] |
| T020 | Implement `snapshot.py` atomic write + `pack-manifest.yaml` generation | WP04 | |
| T021 | Unit tests for all source types and snapshot atomicity | WP04 | [P] |
| T022 | Implement `DoctrineOrgConfig` Pydantic model + `load/save_doctrine_org_config()` | WP05 | |
| T023 | Wire `DoctrineOrgConfig.local_path` into `DoctrineService` factory call sites | WP05 | |
| T024 | Implement `spec-kitty doctrine` command group + `fetch` subcommand in `doctrine.py` | WP05 | |
| T025 | Add `pack validate` and `pack assemble` CLI stubs to `doctrine.py` (implementations in WP06) | WP05 | [P] |
| T026 | Integration tests for config load/save and `doctrine fetch` end-to-end (mocked sources) | WP05 | [P] |
| T027 | Implement `pack_validator.py` — `validate_pack(pack_dir) -> ValidationResult` | WP06 | |
| T028 | Implement `pack_assembler.py` — `assemble_pack(inputs, output_dir) -> AssemblyResult` | WP06 | |
| T029 | Fill in `pack validate` subcommand implementation in `doctrine.py` | WP06 | |
| T030 | Fill in `pack assemble` subcommand implementation in `doctrine.py` | WP06 | |
| T031 | Unit tests for `pack_validator.py` (valid, schema error, duplicate ID, dangling DRG) | WP06 | [P] |
| T032 | Unit tests for `pack_assembler.py` (single pack, clean merge, ID conflict, DRG conflict) | WP06 | [P] |
| T033 | Add provenance `"source"` field to `charter context --json` output (`context.py`) | WP07 | |
| T034 | Route `context.py` DRG loading through `_drg_helpers.load_validated_graph()` | WP07 | [P] |
| T035 | Add `spec-kitty doctor doctrine` subcommand to `doctor.py` | WP07 | [P] |
| T036 | Add `OrgOverridesBuiltinCheck` advisory to `charter lint` in `charter.py` | WP07 | [P] |
| T037 | Integration tests: provenance in JSON, doctor listing, lint advisory | WP07 | [P] |
| T038 | Write `docs/how-to/create-an-org-doctrine-pack.md` (pack authoring guide, incl. org-charter.yaml) | WP08 | |
| T039 | Write `docs/migration/doctrine-local-overlay-to-org-layer.md` (migration guide) | WP08 | [P] |
| T040 | Write `docs/explanation/org-doctrine-layer.md` (three-layer model + charter composition) | WP08 | [P] |
| T041 | Update `docs/toc.yml` and verify cross-references from existing doctrine docs | WP08 | |
| T042 | Implement `OrgCharterPolicy` model + `apply_org_charter_pre_fill()` + `load_org_charter_policies()` | WP09 | |
| T043 | Charter interview pre-fill injection in `interview.py` (non-destructive; no `charter.py` changes needed) | WP09 | |
| T044 | Extend `pack_validator.py` to validate `org-charter.yaml` schema when present | WP06 | [P] |
| T045 | Extend `pack_assembler.py` to merge `org-charter.yaml` files across input packs | WP06 | [P] |
| T046 | Add org charter governance elements to `charter context --json` with source attribution | WP07 | [P] |
| T047 | Add `OrgCharterDeviationCheck` advisory to `charter lint` (policy field deviations) | WP07 | [P] |
| T048 | Extend `doctor doctrine` per-pack listing with org-charter.yaml policy counts | WP07 | [P] |
| T049 | Add `org-charter.yaml` section to pack authoring guide and explanation doc | WP08 | [P] |
| T050 | Unit tests for `OrgCharterPolicy` model, load/merge, interview pre-fill, charter context inclusion | WP09 | [P] |

---

## Work Packages

### WP01 — Multi-file DRG Loading

**Priority**: P0 (infrastructure prerequisite)  
**Estimated prompt size**: ~320 lines  
**Dependencies**: none  
**Enables**: WP02 (needs `load_graph_or_dir`)

**Goal**: Introduce `load_graph_or_dir()` as the single entry point for DRG graph loading,
and update all existing call sites in `charter/` and `charter/synthesizer/` to use it.
After this WP, any DRG directory can contain either a single `graph.yaml` or multiple
`*.graph.yaml` fragment files, and all existing tests pass unchanged.

**Included subtasks**:
- [x] T001 Add `load_graph_or_dir(path)` to `doctrine/drg/loader.py`
- [x] T002 Export `load_graph_or_dir` from `doctrine/drg/__init__.py`
- [x] T003 Update `_drg_helpers.load_validated_graph()` to use `load_graph_or_dir`
- [x] T004 Update all hardcoded `graph.yaml` call sites in charter synthesizer pipeline
- [x] T005 Unit tests for `load_graph_or_dir`

**Parallel opportunities**: T002 and T005 can start after T001. T004 is independent of T003.

**Risks**: The synthesizer pipeline has multiple `graph.yaml` references; missing one site
causes silent single-file fallback. Tests must cover the synthesizer paths.

---

### WP02 — BaseDoctrineRepository Org Layer

**Priority**: P0 (infrastructure prerequisite)  
**Estimated prompt size**: ~360 lines  
**Dependencies**: WP01  
**Enables**: WP03

**Goal**: Extend `BaseDoctrineRepository` with a third loading tier (`org_dir`) between
shipped and project. Provenance tracking (`_provenance: dict[str, str]`) is added so that
each resolved artifact carries a source layer tag. All 8 repository subclasses are updated
to accept and forward the `org_dir` parameter.

**Included subtasks**:
- [ ] T006 Add `org_dir: Path | None` to `BaseDoctrineRepository.__init__`
- [ ] T007 Add `_apply_org_overrides()` with provenance tagging
- [ ] T008 Update `_load()` to invoke org override step
- [ ] T009 Update all 8 repository subclasses to pass `org_dir`
- [ ] T010 Unit tests for three-layer merge

**Parallel opportunities**: T010 can start alongside T009 once T007-T008 are done.

**Risks**: `_include_item()` (language-scope filter) must run after org merge; incorrect
ordering causes org artifacts to skip language filtering. The `_merge()` field-level merge
must NOT apply across layers (full-replace within a layer only applies at the item level,
not the field level — existing `_merge()` is field-level for project override of shipped,
which is preserved; org override of shipped is also full-replace at the item level).

---

### WP03 — DoctrineService Org Roots

**Priority**: P0 (infrastructure prerequisite)  
**Estimated prompt size**: ~280 lines  
**Dependencies**: WP02  
**Enables**: WP05, WP07

**Goal**: Add `org_roots: list[Path]` to `DoctrineService`. Wire `org_dir` into all 8
repository property factories. Add `_resolve_org_root()` helper to `_drg_helpers.py`.
Update `compiler.py` and `reference_resolver.py` to use `load_graph_or_dir` for their
inline DRG loading (removing the duplicated shipped-graph-only loads).

**Included subtasks**:
- [ ] T011 Add `org_roots: list[Path]` to `DoctrineService.__init__` and `_org_dir()` helper
- [ ] T012 Pass `org_dir` through all 8 repository factories
- [ ] T013 Update `compiler.py` and `reference_resolver.py` to use `load_graph_or_dir`
- [ ] T014 Add `_resolve_org_root(repo_root) -> Path | None` to `_drg_helpers.py`
- [ ] T015 Unit tests for `DoctrineService` with `org_roots`

**Parallel opportunities**: T013 and T015 can proceed after T011.

**Risks**: `DoctrineService` is instantiated in multiple places; all factory call sites must
be found and updated to pass `org_roots` (currently `[]`; actual value wired in WP05 after
config loading is in place).

---

### WP04 — OrgDoctrineSource Protocol and Implementations

**Priority**: P1  
**Estimated prompt size**: ~420 lines  
**Dependencies**: none (parallel with WP01–WP03)  
**Enables**: WP05

**Goal**: Define the `OrgDoctrineSource` Protocol and `FetchResult` dataclass. Implement
`GitSource`, `HttpsBundleSource`, and `ApiSource`. Implement `snapshot.py` with the atomic
write pattern and `pack-manifest.yaml` generation.

**Included subtasks**:
- [ ] T016 Define `OrgDoctrineSource` Protocol and `FetchResult` dataclass
- [ ] T017 Implement `GitSource`
- [ ] T018 Implement `HttpsBundleSource`
- [ ] T019 Implement `ApiSource`
- [ ] T020 Implement `snapshot.py` atomic write + `pack-manifest.yaml`
- [ ] T021 Unit tests for all source types and snapshot atomicity

**Parallel opportunities**: T017, T018, T019 are fully parallel after T016. T021 is parallel
with all three implementations.

**Risks**: Git subprocess error handling is tricky (non-zero exit codes, stderr on stdout).
The API source must handle 404 for optional endpoints gracefully. Tarball extraction must
handle both `.tar.gz` and `.zip` formats from `HttpsBundleSource`.

---

### WP05 — Config Model and `doctrine fetch` Command

**Priority**: P1  
**Estimated prompt size**: ~340 lines  
**Dependencies**: WP03, WP04  
**Enables**: WP06

**Goal**: Implement `DoctrineOrgConfig`, integrate it with the existing `.kittify/config.yaml`
loader, wire the config-resolved org root into `DoctrineService` factory call sites, and
implement the `spec-kitty doctrine` command group with `fetch`, `pack validate` stub, and
`pack assemble` stub.

**Included subtasks**:
- [ ] T022 Implement `DoctrineOrgConfig` + `load/save_doctrine_org_config()`
- [ ] T023 Wire `DoctrineOrgConfig.local_path` into `DoctrineService` factory sites
- [ ] T024 Implement `doctrine` command group + `fetch` subcommand
- [ ] T025 Add `pack validate` and `pack assemble` CLI stubs to `doctrine.py`
- [ ] T026 Integration tests for config and `doctrine fetch`

**Parallel opportunities**: T025 and T026 can proceed after T024.

**Risks**: Config file loading must be backward-compatible (projects without a `doctrine.org`
block must continue to work). `DoctrineService` factory call sites are scattered; a grep
of `DoctrineService(` is required to find all of them.

---

### WP06 — `doctrine pack validate` and `doctrine pack assemble`

**Priority**: P2  
**Estimated prompt size**: ~400 lines  
**Dependencies**: WP05  
**Enables**: WP08

**Goal**: Implement `pack_validator.py` (schema validation, DRG consistency, ID uniqueness,
advisory warnings for shipped overrides) and `pack_assembler.py` (multi-pack merge, conflict
detection, `--conflicts-out` option). Fill in the CLI implementations in `doctrine.py`'s
`pack validate` and `pack assemble` subcommands.

**Included subtasks**:
- [ ] T027 Implement `pack_validator.py` — `validate_pack(pack_dir) -> ValidationResult`
- [ ] T028 Implement `pack_assembler.py` — `assemble_pack(inputs, output_dir) -> AssemblyResult`
- [ ] T029 Fill in `pack validate` subcommand implementation
- [ ] T030 Fill in `pack assemble` subcommand implementation
- [ ] T031 Unit tests for `pack_validator.py`
- [ ] T032 Unit tests for `pack_assembler.py`
- [ ] T044 Extend `pack_validator.py` to validate `org-charter.yaml` schema when present
- [ ] T045 Extend `pack_assembler.py` to merge `org-charter.yaml` across input packs

**Parallel opportunities**: T031 and T032 can proceed alongside T029-T030 after T027-T028.

**Risks**: The validator needs the shipped DRG to check that org DRG edge URNs exist in the
merged artifact set. It must load the shipped DRG via `load_validated_graph()` (from WP01)
without a project root (pass `None`).

---

### WP07 — Provenance, `doctor doctrine`, and `charter lint`

**Priority**: P1 (can run after WP03, parallel with WP05-WP06)  
**Estimated prompt size**: ~360 lines  
**Dependencies**: WP03  
**Enables**: WP08

**Goal**: Surface provenance in `charter context --json`. Add `spec-kitty doctor doctrine`
subcommand. Add `OrgOverridesShippedCheck` advisory to `charter lint`. Route `context.py`'s
inline DRG loading through `_drg_helpers.load_validated_graph()`.

**Included subtasks**:
- [ ] T033 Add `"source"` field to `charter context --json` output
- [ ] T034 Route `context.py` DRG loading through `load_validated_graph()`
- [ ] T035 Add `spec-kitty doctor doctrine` subcommand (built-in + org packs + project; git-version support)
- [ ] T036 Add `OrgOverridesBuiltinCheck` advisory to `charter lint`
- [ ] T037 Integration tests for provenance, doctor, lint advisory
- [ ] T046 Add org charter governance elements to `charter context --json`
- [ ] T047 Add `OrgCharterDeviationCheck` advisory to `charter lint`
- [ ] T048 Extend `doctor doctrine` per-pack listing with org-charter.yaml policy counts

**Parallel opportunities**: T034, T035, and T036 are independent of each other after setup.
T037 requires all three to be complete.

**Risks**: The `charter lint` check must source provenance from `DoctrineService`; a shared
service instance must be available in the lint context. The `doctor doctrine` subcommand
must handle the case where `pack-manifest.yaml` is absent (org configured but `fetch` not
yet run).

---

### WP08 — User Guidance Documentation

**Priority**: P2  
**Estimated prompt size**: ~300 lines  
**Dependencies**: WP06, WP07  

**Goal**: Write three user-facing documents: a pack authoring guide (for teams wrapping
existing governance systems), a migration guide (for users coming from `.kittify/doctrine/`
local overlays or deprecated constitution-era paths), and an explanation of the three-layer
resolution model. Update `toc.yml`.

**Included subtasks**:
- [ ] T038 Write `docs/how-to/create-an-org-doctrine-pack.md`
- [ ] T039 Write `docs/migration/doctrine-local-overlay-to-org-layer.md`
- [ ] T040 Write `docs/explanation/org-doctrine-layer.md`
- [ ] T041 Update `docs/toc.yml` and verify cross-references
- [ ] T049 Add `org-charter.yaml` authoring section to pack authoring guide and explanation doc

**Parallel opportunities**: T038, T039, and T040 are independent. T049 can run alongside T040. T041 requires all of T038–T040 and T049.

**Risks**: Migration guide must be accurate about which paths are deprecated and what the
correct current-state paths are; verify against WP05 and WP07 implementation before finalizing.
The explanation doc must match the final behavior (especially provenance output format from WP07).

---

### WP09 — Org Charter Composition

**Priority**: P2  
**Estimated prompt size**: ~360 lines  
**Dependencies**: WP05, WP07  
**Enabled by**: FR-025, FR-026, FR-027, FR-028, FR-029

**Goal**: Implement `OrgCharterPolicy` model and `load_org_charter_policies()` so the charter
interview pre-fills from org charter defaults and `charter context` includes org charter
governance elements with source attribution. Advisory lint for charter policy deviations is
also added here.

**Included subtasks**:
- [ ] T042 Implement `OrgCharterPolicy` model + `apply_org_charter_pre_fill()` + `load_org_charter_policies()`
- [ ] T043 Charter interview pre-fill injection in `interview.py` (non-destructive; no `charter.py` changes)
- [ ] T046 Add org charter governance elements to `charter context --json` with source attribution
- [ ] T050 Unit tests for `OrgCharterPolicy` model, load/merge, interview pre-fill, context inclusion

**Parallel opportunities**: T043 and T050 can proceed in parallel after T042. T046 is in WP07 and requires this WP to be merged first (WP07 must execute after WP09 for T046).

**Risks**: The charter interview (`charter.py` + `charter/interview.py`) is a complex
interactive flow; pre-fill must not silently overwrite answers a user has already given.
Charter context output shape must be backward-compatible — new org charter fields are additive
in the JSON output, never replacing existing fields.
