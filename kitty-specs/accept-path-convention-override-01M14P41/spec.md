# Mission Specification: Accept path-convention portability

**Mission Branch**: `fix/accept-path-convention-override`
**Created**: 2026-08-28
**Status**: Draft
**Input**: #3016 — `spec-kitty accept` hardcodes the `src/` source-root convention and fails every mission in a repo whose real layout differs (Django `apps/`, Go `internal/`), prescribing the fabrication of an empty `src/`.

## Context

`spec-kitty accept` evaluates a mission type's declared `paths:` block (e.g. software-dev's
`workspace: src/`, `tests: tests/`) against the repository. These values are fixed doctrine
constants with **no per-project value channel**, so a repo whose real source root is `apps/`
or `internal/` reports the convention directory as a blocking `path_violations` entry — and
its remediation historically told the operator to `mkdir -p src/`, an empty dir that only
silences the gate.

The **companion honesty mission** (#3730/#3085, merged as PR #3783) already fixed the
*output* half: the remediation now surfaces `accept --lenient` and no longer prescribes the
fake-green `mkdir`, while deliberately keeping path conventions **blocking by default**. This
mission fixes the *portability* half: it supplies the missing **value** channel so an operator
declares their real layout once and accept honors it — **without** reverting that
blocking-by-default policy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Declare a real source layout once (Priority: P1)

An operator whose repository uses a non-`src/` source root (Django `apps/`, Go `internal/`)
declares their layout once in `.kittify/config.yaml` under `project.path_conventions`, and
`spec-kitty accept` honors it — the mission is accepted with the working tree untouched, with
no fabricated directory and without disabling unrelated gates via `--lenient`.

**Why this priority**: This is the defect #3016 reports. Without it, accept is unusable for an
entire class of idiomatic project layouts (every one of the 84 missions in a Django repo fails
identically). It is the MVP: a single mission accepting under a declared override delivers the value.

**Independent Test**: In a repo with real code in `apps/` and no `src/`, declare
`project.path_conventions.workspace: apps/`, run `accept` on a software-dev mission, and observe
a pass with a clean `git status` and no `--lenient`.

**Acceptance Scenarios**:

1. **Given** a software-dev mission in a repo with `apps/` (no `src/`) and
   `project.path_conventions: {workspace: apps/, tests: tests/}` in `.kittify/config.yaml`,
   **When** the operator runs `spec-kitty accept`, **Then** there is no `src/` path violation and
   the accept readiness reflects the declared layout.
2. **Given** the same repo **without** the override key, **When** `accept` runs, **Then** it
   still reports the `src/` convention as a blocking violation (blocking-by-default preserved) and
   names the honest levers (`project.path_conventions` and `accept --lenient`), never a bare `mkdir`.
3. **Given** an override declaring `workspace: apps/` but where `apps/` does **not** exist in the
   repo, **When** `accept` runs under strict mode, **Then** it still emits a blocking `path_violations`
   entry for the declared `apps/` directory — the override changes *which* directory is expected, it
   does **not** stop enforcing it. (This is the non-fakeable discriminator: an implementation that
   silently demotes conventions to advisory would wrongly pass this and is thereby caught.)
4. **Given** an override that targets the artifact-routed key `deliverables` (whose default value,
   e.g. `contracts/`, equals a mission artifact token and therefore resolves on `feature_dir`),
   **When** config is read, **Then** the override for that key is **rejected/ignored with a clear
   message** — `deliverables` (and any key whose default value is a mission artifact token) is
   **outside** the override vocabulary, because overriding it would silently flip the token's
   resolution surface from `feature_dir` to `project_root` and drop the mission-surface artifact check.
5. **Given** an override key that the mission's own `paths:` block does **not** declare (e.g. `data:`
   on a software-dev mission), **When** config is read, **Then** the override does **not** introduce a
   new required path — it warns/ignores (remap-only: an override re-routes an existing declared key,
   it never adds a new blocking surface).

### User Story 2 - Portability for every mission type (Priority: P2)

A project that runs research, plan, or documentation missions (not only software-dev) gets the
same override behavior, because the override resolves at the one shared path-validation seam
rather than being special-cased per type.

**Why this priority**: Closes the defect class by construction (Directive 043). All four mission
types declare `paths:` and flow through the same validator; a software-dev-only fix would leave the
identical latent trap in the other three and re-invite the "property-of-type-not-project" bug.

**Independent Test**: Declare an override, run `accept` on a research mission whose declared
`paths:` don't match the repo, and observe the override is honored identically to software-dev.

**Acceptance Scenarios**:

1. **Given** any of the four built-in mission types and a matching `project.path_conventions`
   override, **When** `accept` runs, **Then** the override supersedes that type's doctrine default
   for the overridden keys.
2. **Given** an override that names a key outside the canonical set
   `{workspace, tests, deliverables, documentation, data}`, **When** config is read, **Then** the
   unknown key is rejected/warned consistently with how `MissionConfig` already validates path keys.
3. **Given** a research mission (which applies a `path_prefix` to deliverables) **and** a
   `project.path_conventions` override, **When** `accept` resolves paths, **Then** the composition
   order is deterministic and specified — either the override composes with `path_prefix` in the
   documented order, **or** the spec records that a project override and research's `path_prefix` do
   not meaningfully co-occur for the same key (with the reason). The behavior must be pinned by a test,
   not left implicit.

### User Story 3 - Optional-artifact list stops drifting (Priority: P3)

The accept gate's "optional artifacts missing" signal reflects the mission type's *declared*
optional artifacts rather than a hardcoded Python list that has already drifted — folded in as an
in-seam cleanup of the same "property hardcoded at the type level that should be read from config"
defect class #3016 names (tracker #3785).

**Why this priority**: Cheap, in-radius SSOT cleanup (Directive 044) surfaced by the #3783 review
squad. Not the headline defect, so it rides P3.

**Independent Test**: A mission type whose `artifacts.optional` differs from the historical
hardcoded list (`quickstart, data-model, research, contracts`) reports optional-missing entries that
match its declaration, including `checklists/`.

**Acceptance Scenarios**:

1. **Given** a mission whose `artifacts.optional` includes an entry absent from the old hardcoded
   list, **When** `accept` computes missing optional artifacts, **Then** that entry is considered.
2. **Given** `contracts/`, **When** the #3785 cleanup lands, **Then** its blocking-vs-warning
   severity is **unchanged** from the #3783 settlement (guard: this mission does not re-litigate it).

### Edge Cases

- **Empty / malformed `path_conventions` block**: an **empty map** is a no-op (byte-for-byte current
  behavior, NFR-004); a non-string, **empty/blank, absolute, or `..`-traversing** value, an unknown key,
  or a present-but-not-a-mapping section must **fail closed** with a clear message naming the offending
  key — never silently ignore a malformed override, and never crash accept with a raw traceback (the
  accept gate renders it as a blocking verdict). Malformed **whole-file** YAML stays lenient (`{}`).
- **Partial override**: overriding only `workspace` leaves `tests`/`documentation`/`deliverables`
  resolving against their doctrine defaults; the composition is per-key, not all-or-nothing.
- **Override names a directory that also does not exist**: the override changes *which* directory is
  expected, not the blocking policy — a declared-but-absent directory still blocks by default.
- **Artifact-tagged tokens** (e.g. `deliverables: contracts/` resolved on `feature_dir`) must keep
  routing through the feature-dir arm after an override is applied to the repo-root arm.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Read project path-convention override | As an operator, I want a `project.path_conventions` map in `.kittify/config.yaml` read through a single typed reader so my declared layout is available to the accept path check. | High | Open |
| FR-002 | Resolve override ahead of doctrine defaults | As an operator, I want the override merged over the mission type's declared `paths:` values before path resolution so my layout wins for the keys I declare. | High | Open |
| FR-003 | Accept a non-`src` repo honestly | As an operator in an `apps/`/`internal/` repo, I want `accept` to pass on my real layout with no fabricated directory and without `--lenient`. | High | Open |
| FR-004 | All-four-mission-types by construction | As an operator, I want the override honored for software-dev, research, plan, and documentation missions via the one shared validator, not per-type code. | High | Open |
| FR-005 | Go-layout coverage (#2330 Item 1) | As an operator in a Go repo (`internal/`, colocated tests), I want the declared layout honored so accept stops demanding `src/`+`tests/`. | Medium | Open |
| FR-006 | Optional-artifact list from config (#3785) | As an operator, I want `accept`'s missing-optional-artifact computation to read `mission.config.artifacts.optional` (with token→file/dir resolution) instead of a hardcoded, drifted list; the caller must fetch the mission before `_missing_artifacts` and fall back gracefully when `mission is None`. | Medium | Open |
| FR-007 | Validate override keys | As an operator, I want two key cases handled distinctly: (a) a key outside `valid_path_keys` (a typo) → reject with a clear message; (b) a valid key the mission's own `paths:` does not declare, or an artifact-routed key (`deliverables`) → warn/ignore (remap-only, no new required path, no routing flip). | Medium | Open |
| FR-008 | Fail closed on malformed override section | As an operator, I want a `project.path_conventions` that is present-but-not-a-mapping, or carries non-string/null values, to fail closed with an actionable message naming the offending key. (Absent key ⇒ empty override; whole-file-unreadable `config.yaml` stays lenient to match co-resident readers — scope fail-closed to the section shape, not the file.) | Medium | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Blocking-by-default preserved | With no override declared, `accept` on a layout mismatch produces the pre-mission result pinned at assertion granularity: the **exact** `path_violations` payload **and** the full `format_errors()` remediation string (naming both honest levers — `project.path_conventions` and `accept --lenient`). A "non-empty violations" assertion is insufficient. Regression anchored beside `test_acceptance_support.py::test_lenient_downgrades_path_conventions_to_warning`. | Reliability | High | Open |
| NFR-002 | Bounded config access | The override adds at most **one** config read per accept run and **no** per-key filesystem re-read; verified structurally, not by latency timing. | Performance | Medium | Open |
| NFR-003 | Complexity gate held | Whichever seam absorbs the override composition (`validate_mission_paths` and/or `evaluate_path_conventions`) stays ≤15 cyclomatic/cognitive (C901 / S3776). The override MUST compose into the resolved path map **before** the per-key resolution loop (or via an extracted `_resolve_required_paths` helper) — a new loop branch is forbidden (current `validate_mission_paths` complexity is 12/15, margin 3). | Maintainability | High | Open |
| NFR-004b | Single-seam invariant | `validate_mission_paths` MUST retain exactly one production caller (`evaluate_path_conventions`); a second caller that bypasses the override is a regression. A guard test asserts the single-caller topology. | Maintainability | Medium | Open |
| NFR-004 | Backward-compatible config | An existing `.kittify/config.yaml` with no `project.path_conventions` key loads and behaves exactly as before (no migration required). | Compatibility | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Value channel only — no policy change | This mission MUST NOT change the blocking policy or introduce advisory-by-default; doing so would revert the merged honesty mission (#3783). It supplies only a value override. | Technical | High | Open |
| C-002 | Project layout is project state | The fix MUST live in project config, not in mission-type doctrine `mission.yaml` values (a project's layout is not shared doctrine shipped to all consumers). | Technical | High | Open |
| C-003 | Do not touch `contracts/` severity | The #3785 fold MUST NOT re-open the `contracts/` blocking-vs-warning question settled by #3783. | Technical | High | Open |
| C-004 | One typed section reader | The config read MUST be a single new typed project-config section reader modeled on `charter_runtime/preflight/config.py`; do NOT inline a raw `YAML()`/`ruamel` load at the accept seam (Directive 044). | Technical | Medium | Open |
| C-005 | Extract then reuse the path-key authority | `valid_path_keys` today is a function-local literal inside `MissionConfig.model_post_init` (`mission.py:183`), not an importable symbol. The mission MUST first extract it to a shared module/class constant, then reuse it for override-key validation — not re-declare it. | Technical | Medium | Open |
| C-006 | Record the precedence decision | One ADR in `docs/adr/3.x/` MUST record: the precedence order (project override → doctrine default → blocking-by-default + `--lenient`); the deliberate non-reversal of #3783; the value↔artifact-token routing coupling and why `deliverables` is excluded from the override vocabulary (C-010); and layout auto-detection (#2744) as the deliberate next step. Authored inside the seam-wiring WP, not a standalone action-WP. | Process | High | Open |
| C-007 | Arch-gate re-pin budgeted | Any new public symbol / `PathValidationResult` field / `__all__` change MUST refresh the dead-symbol / shard-orphan / golden-count arch-gate pins in the same PR (as #3783 did). | Technical | Medium | Open |
| C-008 | Single upstream merge point | The override MUST merge into `declared`/`mission.config.paths` **upstream of both** consumers of `declared[key]` — the `_prefix_required_path` resolution AND the artifact-token membership check (`paths.py:~199` and `~:224`) — as one composition step. Merging only into the post-prefix `required_paths` silently breaks artifact-token→`feature_dir` routing. This is the concrete enforcement of C-001. | Technical | High | Open |
| C-009 | #3783 tests are load-bearing | The #3783 path-convention / lenient regression tests encode the settled honesty contract. This mission's coverage MUST be additive; it MUST NOT delete or weaken an existing #3783 assertion. Any edit to one requires explicit justification that it is not a contract revert. | Technical | High | Open |
| C-010 | Remap-only, repo-layout keys | The override vocabulary is restricted to repo-layout keys and EXCLUDES any key whose default value is a mission artifact token (concretely `deliverables`, whose value `contracts/` routes to `feature_dir` — `paths.py:~224` decides routing from `declared[key]`, so overriding it would flip the surface). An override MUST only remap a key the mission already declares; it MUST NOT introduce a new required path. This is the concrete guard on the value↔artifact-token coupling. | Technical | High | Open |
| C-011 | Reader reads the subkey, not the block | The typed reader MUST read `project.path_conventions` specifically; it MUST NOT model the whole `project:` block with `extra=forbid`, or it would reject the existing identity fields (`uuid`/`slug`/`node_id`/`build_id`) and fail every real repo. | Technical | Medium | Open |

### Key Entities

- **Project path-convention override**: a per-project map (`project.path_conventions`) keyed by the
  canonical path vocabulary, declaring the repo's real directory for each convention. Project state,
  not doctrine.
- **Mission path convention (doctrine default)**: the mission type's declared `paths:` values; the
  fallback when no override is declared for a key.
- **Resolved required-path set**: the composed result of the doctrine default overridden by the
  project override, then (for research) the `path_prefix` applied — precedence
  `doctrine default ← project override ← research prefix`. The override merges into `declared`
  **before** both the prefix step and the artifact-token membership check (see C-008), so an override
  never bypasses artifact→`feature_dir` routing. Where a project override and research `path_prefix`
  target the same key, the composition order is specified and tested (US2 scenario 3), or documented as
  non-co-occurring.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A software-dev mission in a Django-style `apps/` repo (no `src/`) with a declared
  override is accepted with a clean working tree — no directory created, `--lenient` not passed.
- **SC-002**: With no override key present, a layout mismatch still produces a blocking path
  violation under strict accept (0 behavioral change vs. pre-mission) — proven by a regression test.
- **SC-003**: All four built-in mission types honor a declared override for the overridden keys,
  demonstrated by at least one non-software-dev mission test.
- **SC-004**: `accept`'s missing-optional-artifact set is derived from `mission.config.artifacts.optional`
  (with correct token→file/dir resolution) for a mission whose declaration differs from the historical
  hardcoded `[quickstart, data-model, research, contracts]`. Software-dev's declared `checklists/`
  (present in `mission.yaml`, omitted by the hardcoded list) is now included; `contracts/` severity is
  unchanged; the `mission is None` path falls back safely. A test reads a real `mission.yaml` to pin
  the per-type declarations rather than assuming them.
- **SC-005**: The seam(s) absorbing the override composition (`validate_mission_paths` and/or
  `evaluate_path_conventions`) keep cyclomatic/cognitive complexity ≤15 after the change
  (ruff C901 / Sonar S3776 clean), with the merge composed before the per-key loop.
- **SC-006** (non-fakeable discriminator): With an override declaring `apps/` but `apps/` **absent**
  from the repo, strict `accept` still emits a blocking `path_violations` entry for `apps/` — proving
  the override changes the expected directory without disabling enforcement (catches a silent
  advisory-demotion implementation).
- **SC-007**: A malformed / empty / non-string `project.path_conventions` block causes `accept` to fail
  closed with an actionable error message and no traceback.

## Assumptions & Sequencing (guidance for plan/tasks)

**Assumptions to pin with tests, not prose** (post-spec squad):
- Each of the four built-in mission types declares a `paths:` block and flows through the single
  `evaluate_path_conventions → validate_mission_paths` seam (verified: one production caller today).
- Software-dev `artifacts.optional` includes `checklists/` and `research.md` in **both** `mission.yaml`
  trees (`packs/built-in/…` and `src/specify_cli/missions/…`); the hardcoded `_missing_artifacts` list
  omits `checklists/` — that is the #3785 drift SC-004 closes.
- The regression anchor for NFR-001/SC-002 already exists at
  `tests/cross_cutting/misc/test_acceptance_support.py::test_lenient_downgrades_path_conventions_to_warning`.

**Natural work-package decomposition** (post-plan brownfield squad; honest terminal states, no
action-not-a-diff WP). The reader and its wiring are **unified** into one anchor — a reader reviewed
alone trips the dead-symbol gate (its only `src/` caller is in the wiring):
- **WP01 — Reader + precedence merge + seam wiring [ANCHOR]** (FR-001, FR-002, FR-003, FR-007, FR-008,
  NFR-001, NFR-003, NFR-004b, C-001, C-004, C-005 extraction, C-006 ADR here, C-007 re-pin, C-008,
  C-010, C-011): typed reader (fail-closed section validation authored, not inherited) + `VALID_PATH_KEYS`
  extraction + merge at `paths.py:199` + read override in `evaluate_path_conventions`. `done` = software-dev
  accepts on `apps/`; no-override regression pins exact payload + `format_errors()`; SC-006 green.
- **WP02 — All-four-types + Go coverage [TEST-ONLY]** (FR-004, FR-005, US2, incl. artifact-routed-key
  rejection + `path_prefix` composition ACs, NFR-004b single-caller guard placed OUTSIDE
  `tests/architectural/`): depends WP01; strictly test-only (no seam edits).
- **WP03 — #3785 optional-artifact SSOT fold [SEVERABLE, P3]** (FR-006, C-003, C-009, SC-004):
  `acceptance/__init__.py` (call-site reorder + `None` fallback); parallel to WP02 after WP01.
  **Split-tripwire:** if FR-006 forces any `contracts/` dedup/severity change or grows beyond the
  `_missing_artifacts` signature + call-site reorder, split #3785 to its own mission.

**Out of scope (separate tickets):** layout auto-detection via `manage.py`/`go.mod` signals; mission-type-aware
accept relaxation for research plan/tasks/WP shape (#2744). Closes #3016; folds #2330 Item 1.
