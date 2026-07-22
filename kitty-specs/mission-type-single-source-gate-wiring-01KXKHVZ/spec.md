# Mission Specification: Mission-Type Single-Source + Gate Wiring

**Mission slug**: `mission-type-single-source-gate-wiring-01KXKHVZ`
**Mission type**: software-dev
**Status**: Draft
**Epic**: #2652 (specify_cli/missions retirement — activation-driven availability, single canonical mission-type source)
**Tracker issues**: #2669, #2667, #2666, #2668 (all OPEN, milestone 3.2.x)
**Continues**: PR #2664 / issue #2651 (mission_type as a first-class DRG node + cross-grain integrity gate + lazy resolver seam)

---

## Purpose

PR #2664 landed the cross-grain integrity gate and a lazy resolver seam, but a post-merge
adversarial squad (paula + debbie + pedro) found the gate is **sound but narrower than advertised**
and that the mission-type roster is still hand-maintained in several places. This mission delivers the
four filed follow-ups as one coherent bundle so that:

1. A **newly-shipped mission type** is picked up everywhere automatically (no hand-edited roster drift).
2. A **malformed doctrine index** fails loudly instead of silently degrading a governance grain to empty
   (which can make the integrity gate pass falsely).
3. The **cross-grain duplicate scan** becomes load-bearing outside pytest — it runs from a real runtime
   surface (`spec-kitty doctor doctrine`) and a CI structural gate.
4. A **private path accessor** reached through `# noqa: SLF001` bypasses becomes a public seam.

The binding design authority is the ADR spine: doctrine **offers**, a charter **activates**, the runtime
**consumes** only activated elements
([`docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md`](../../docs/adr/3.x/2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md)),
and the enduring-verification adjudication that cross-grain disjointness belongs in a doctrine-integrity gate
over real content, not a swallowed eager resolver raise
([`docs/adr/3.x/2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md`](../../docs/adr/3.x/2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md)).

### Guiding principle (charter)

**Single canonical authority; chase unification, not parity.** Every occurrence of "the set of built-in
mission types" must derive from ONE source (the doctrine `mission_types/*.yaml` tree via
`MissionTypeRepository`) rather than a hand-kept literal guarded by a drift test. The one deliberate
exception — the version-pinned migration roster — is an operator-confirmed decision (see C-004).

---

## Domain Language

| Term | Canonical meaning | Avoid |
|------|-------------------|-------|
| **Mission type** | A doctrine-owned workflow definition (`software-dev`, `documentation`, `research`, `plan`) shipped as `src/doctrine/missions/mission_types/<id>.yaml`. | "feature type", "project type" |
| **Roster** | Any in-code enumeration of the built-in mission-type set (a tuple, frozenset, or list literal). | — |
| **Source of truth** | `MissionTypeRepository` reading `mission_types/*.yaml`; loud-fails on id≠filename-stem or invalid schema. | a hand-maintained literal |
| **Action grain** | The union, across every action a mission type defines, of the doctrine artifacts scoped to that action (`actions/<action>/index.yaml`). | — |
| **Type grain** | The mission-type-scoped governance selection (`governance-profile.yaml` `selected_*`). | — |
| **Cross-grain double declaration** | An artifact URN declared in BOTH the type grain and the action grain — the cross-grain collision the integrity gate raises on. | — |
| **Integrity gate / scan** | `scan_builtin_cross_grain_duplicates` — enumerates every shipped mission type and unions its grains, raising `CrossGrainDoubleDeclarationError` on collision. | — |

---

## User Scenarios & Testing

Actors here are **Spec Kitty maintainers**, **mission-runtime agents**, and **CI**.

### Scenario 1 — A maintainer ships a fifth mission type (single-source, #2669)

- **Trigger**: A maintainer adds `src/doctrine/missions/mission_types/analysis.yaml` (a new built-in type).
- **Happy path**: Every roster-dependent surface — charter enumeration, default activation set, the
  synthesizer interview mapping, the allowed-types guard, and the rc35 migration's written set — reflects
  `analysis` **without any additional hand edit** to a literal list.
- **Rule that must hold**: There is exactly one place a built-in mission type is declared (its
  `mission_types/*.yaml` file); no code path re-declares the set.
- **Exception**: If the maintainer ships a YAML whose `id` ≠ filename stem, or an invalid schema,
  `MissionTypeRepository` raises immediately (loud fail), and every derived surface fails loud too — no
  surface silently omits or mis-registers the type.

### Scenario 2 — A broken action index no longer hides a collision (#2667)

- **Trigger**: A doctrine author writes `actions/implement/index.yaml` with `directives: "a-string"`
  (a scalar where a list is required), or a syntactically-broken YAML, or a top-level scalar.
- **Happy path (fixed behavior)**: `load_action_index` raises a structured `ActionIndexError` naming the
  file, the offending key, and the found type — instead of silently coercing to an empty grain.
- **Rule that must hold**: *Present ⇒ must be well-formed; absent ⇒ empty.* A file that is present but
  cannot be read as a valid `ActionIndex` is an error; only a genuinely-missing file yields the silent
  empty fallback.
- **Effect**: The cross-grain union can no longer pass falsely by silently dropping a malformed action's
  contribution.

### Scenario 3 — A colliding governance config fails loud outside pytest (#2666)

- **Trigger**: A maintainer runs `spec-kitty doctor doctrine` (or CI runs the structural gate) against a
  built-in tree where an artifact URN is declared in both the type grain and an action grain.
- **Happy path**: The command reports the collision, marks the doctrine report **unhealthy**, and exits
  non-zero (RC=1); `--json` output carries a structured finding. CI's structural gate fails.
- **Rule that must hold**: The cross-grain scan has at least one real `src/` caller, so the collision
  surfaces without running the pytest suite.
- **Boundary (out of scope this mission)**: Project/org override collisions require a multi-root
  action-index engine that `action_grain.py` explicitly declares out of scope; that coverage is tracked
  as a follow-up (see Out of Scope).

### Scenario 4 — The built-in-root accessor is a public seam (#2668)

- **Trigger**: A charter module needs the shipped missions root
  (`src/doctrine/missions`).
- **Happy path**: It calls the public `builtin_missions_root()` accessor on
  `MissionTypeProfileRepository`; no `# noqa: SLF001` private-name bypass remains.
- **Rule that must hold**: Behavior is byte-for-byte unchanged (pure refactor); only
  `MissionTypeProfileRepository` is promoted — the 11 sibling doctrine repositories with the same private
  method are untouched.

### Edge cases

- A mission type with an `actions/` directory whose indexes are all *intentionally empty* (e.g. `plan`)
  resolves to an empty-content grain — that is **empty content, not a malformed index**, and must NOT
  raise (#2667).
- A mission type with **no** `actions/` directory at all degrades to an empty-content mapping (existing
  defensive fallback in `aggregate_action_grain`) — unchanged.
- Re-adding `scan_builtin_cross_grain_duplicates` to `__all__` (#2666) only satisfies the CI dead-symbol
  gate once a genuine `src/` importer exists — the `__all__` change and the `doctor` wiring MUST land in
  the same change (see C-003).
- The single-source accessor must introduce **zero import-time filesystem I/O** into `src/charter/`
  (NFR-001); charter consumers call it lazily inside functions.

---

## Requirements

### Functional Requirements

| ID | Requirement | Status |
|----|-------------|--------|
| FR-001 | Introduce ONE canonical accessor, resident in the **doctrine** layer, that returns the built-in mission-type id set derived from `MissionTypeRepository` (`mission_types/*.yaml`). It exposes both an ordered form (for list/tuple consumers) and a set/frozenset form (for membership consumers). | Draft |
| FR-002 | `CANONICAL_MISSION_TYPES` (Roster A, `charter/mission_type_profiles.py`) is derived from the canonical accessor rather than a hardcoded tuple literal; all its consumers (re-export + tests) resolve through the single source. | Draft |
| FR-003 | `_BUILTIN_MISSION_TYPE_IDS` (Roster B, `charter/pack_context.py`) is derived from the canonical accessor, **preserving frozenset semantics** (the `_read_activated_mission_types` return type and the frozenset-equality contract of its callers/tests). | Draft |
| FR-004 | The rc35 migration roster (Roster C, `m_3_2_0rc35_activate_builtin_mission_types.py`) resolves its written mission-type set from the live `MissionTypeRepository.default().ids()` at `apply()` time (call-time, not import-time). Its tests are updated to assert derivation from the source. | Draft |
| FR-005 | `ALLOWED_MISSION_TYPES` (Roster D, `charter/activations.py`) derives its mission-type members from the canonical accessor and unions the non-mission-type sentinels (`any`, `generic`) explicitly, preserving current membership semantics. | Draft |
| FR-006 | `_MISSION_IDENTIFIER_ANSWERS` (Roster E, `charter/synthesizer/interview_mapping.py`) derives its mission-type keys from the canonical accessor while preserving the existing `software_dev` underscore-alias transform. | Draft |
| FR-007 | `load_action_index` raises a structured, co-located doctrine-layer exception (`ActionIndexError`, a `ValueError` subclass) — naming the index path, the offending key, and the found type — when a **present** index file is not a well-formed `ActionIndex`: a non-mapping root, a non-list value for any artifact-kind field, or a syntactically-unparseable YAML. | Draft |
| FR-008 | A genuinely **missing** action-index file continues to return the silent empty fallback (`ActionIndex(action=action)`); an intentionally-empty-but-well-formed index also returns empty content without raising. | Draft |
| FR-009 | `spec-kitty doctor doctrine` invokes `scan_builtin_cross_grain_duplicates`; on `CrossGrainDoubleDeclarationError` it marks the doctrine report unhealthy, exits RC=1, and emits a structured finding in `--json` output. On success the check is reported healthy and does not change the exit code. | Draft |
| FR-010 | `scan_builtin_cross_grain_duplicates` is re-added to `__all__` in `src/charter/action_grain.py`, justified by the new `src/` runtime caller from FR-009 (both land together). | Draft |
| FR-011 | A CI structural gate asserts the built-in doctrine tree is cross-grain-disjoint (fails when a collision is present), independent of the broad pytest run. | Draft |
| FR-012 | `MissionTypeProfileRepository._default_built_in_dir` is promoted to a public `builtin_missions_root()` accessor (module-level function with the classmethod delegating), and the two `# noqa: SLF001` bypasses (`action_grain.py`, `mission_type_profiles.py`) are removed in favor of the public seam. | Draft |

### Non-Functional Requirements

| ID | Requirement | Threshold / Measure | Status |
|----|-------------|---------------------|--------|
| NFR-001 | The canonical accessor introduces at most one cached import-time filesystem read into the **hot** charter modules, never an unbounded/repeated one. | `charter.mission_type_profiles` and `charter.pack_context` perform zero `mission_types/` reads **of their own** — their roster resolution happens only inside function bodies. But importing either one first runs `charter/__init__.py` (the package init any submodule import executes), which eagerly imports `charter.activations` as part of its public re-export surface; `ALLOWED_MISSION_TYPES` (the C-012 carve-out) is a module-scope value derived from the accessor, so that ONE read is inherited transitively by every hot-module import. The honest bound is therefore **≤1 cached read**, not zero, and — because `builtin_mission_type_ids` carries a process-wide `functools.cache` (NFR-002) — a second import or a second roster access anywhere in the same process triggers **zero further reads** (both bounds verified by `test_charter_import_time_io.py`). **Carve-out (C-012):** the two public value-constant rosters — `activations.ALLOWED_MISSION_TYPES` and `synthesizer.interview_mapping._MISSION_IDENTIFIER_ANSWERS` — are *derived at module scope* via the cached accessor (a single cached scan per process, bounded by NFR-002), because an unowned arch test consumes `ALLOWED_MISSION_TYPES` as a value and it must remain an importable frozenset — and, independently, converting it to a PEP 562 lazy `__getattr__` attribute (which WOULD achieve literal zero) breaks the symbol-level dead-code gate (`test_no_dead_symbols.py`): the gate's `SymbolKey` resolver only spans a static module-scope `Assign`/`AnnAssign`/`ClassDef`/`FunctionDef` binding, so a `__getattr__`-only attribute is undecidable-shaped, has no matching allow-list key, and — having no genuine `src/` caller either — is flagged as a fresh dead-symbol offender. The ≤1-cached-read module-scope literal was kept for this reason. | Draft |
| NFR-002 | Accessor result is stable and cheap for repeated calls. | Repeated calls within a process return an identical value without re-globbing on every call (e.g. cached); one filesystem scan per process at most. | Draft |
| NFR-003 | All new/changed code passes `ruff` and `mypy --strict` with zero new suppressions. | `ruff check .` and `mypy --strict` clean; no added `# noqa`/`# type: ignore`/per-file-ignore beyond the SLF001 bypasses being *removed*. | Draft |
| NFR-004 | Every new branch/helper carries focused tests in the same change. | New-code test coverage for each added helper/branch (Sonar new-code gate); each WP declares its targeted test surface. | Draft |
| NFR-005 | Cyclomatic complexity of any touched function stays ≤ 15. | Ruff `C901` / Sonar `S3776` clean on changed functions. | Draft |
| NFR-006 | Layer boundaries are preserved. | `doctrine` does not import `charter`; `charter` does not import `specify_cli`; `kernel` does not import `doctrine`. The canonical accessor lives in `doctrine`. Verified by `tests/architectural/test_layer_rules.py`. | Draft |

### Constraints

| ID | Constraint | Status |
|----|------------|--------|
| C-001 | No no-canonical-field fallback branches. Rosters must require the canonical source; no `if x is None: <hardcoded fallback>` parity paths (charter Governing Principle; gotcha 6). | Draft |
| C-002 | Delivery order is **#2669 → #2667 → #2666 → #2668**. #2667 (fail-loud) precedes #2666 because the wired gate is partially vacuous over a silently-degraded index until fail-loud lands. #2668 lands last to absorb churn on the two shared lines it edits. | Draft |
| C-003 | FR-010 (`__all__` re-add) and FR-009 (`doctor` wiring) MUST land in the same change — the CI dead-symbol gate (`test_no_dead_symbols.py::test_no_public_symbol_in_all_is_unimported`, arch_shard_1) only passes once a real `src/` importer exists. | Draft |
| C-004 | The rc35 migration reading the live repository (FR-004) is an **operator-confirmed** decision that trades historical migration determinism for automatic new-type pickup; recorded in the design-decisions tracer. (The adversarial squad's alternative was a frozen literal + drift-guard test; the operator chose the live-read.) | Draft |
| C-005 | #2668 is scoped to `MissionTypeProfileRepository` ONLY; the 11 sibling doctrine repositories with the same private `_default_built_in_dir` are left untouched (they have no cross-class bypass). | Draft |
| C-006 | Pre-existing CI-only gates must pass before hand-off: the `arch_shard_1` pole and the terminology guard (`test_no_legacy_terminology.py`); DRG freshness (`spec-kitty doctrine regenerate-graph --check`) if mission-type discovery or the graph changes. | Draft |
| C-007 | No version-number prescription in scope (the PO assigns the release number at merge). | Draft |
| C-008 | ATDD red-first: each work package commits a failing-first test through the pre-existing entry point BEFORE implementation. | Draft |
| C-009 | Only `kernel/paths.py` `_looks_like_missions_root` stays hardcoded — the kernel layer cannot import doctrine (kernel⊄doctrine). Its `specify_cli/runtime/` counterparts (`home.py` `_looks_like_missions_root`, `show_origin.py` `_discover_mission_names` fallback) **were folded onto the accessor** in the landing pass (per operator directive): those live in `specify_cli` (specify_cli→doctrine is legal), and the accessor resolves the *installed* doctrine package via `importlib.resources`, independent of the candidate-path probe — so they are NOT the kernel circular case. `constants.py` `MISSION_TYPE_*` scalars are per-type named aliases (not a roster), doc-comment refreshed. | Draft |
| C-010 | The canonical accessor exposes a **cache-clear + root-injection seam** so the SC-001 synthetic-type test can run without mutating the shared doctrine tree (xdist workers share the repo tree; only HOME is isolated). The test monkeypatches the resolved root and calls `cache_clear()`; production never mutates built-ins mid-process, so the cache is safe there (NFR-002). | Draft |
| C-011 | Retiring Roster A `CANONICAL_MISSION_TYPES` is a **public-API change** (removed from `charter/__init__.__all__`; consumers migrate to the accessor). Roster D `ALLOWED_MISSION_TYPES` stays a module-level **frozenset value** but derived from the accessor (its value contract is preserved — see C-012). Roster D's body-hash baseline in the dead-symbol gate (`test_no_dead_symbols.py`) must be refreshed in the same WP or `arch_shard_1` fails. | Draft |
| C-012 | The public value-constant rosters `activations.ALLOWED_MISSION_TYPES` and `interview_mapping._MISSION_IDENTIFIER_ANSWERS` remain **module-level frozenset values** (derived from the accessor), NOT converted to functions **or to a PEP 562 lazy `__getattr__` attribute** — `ALLOWED_MISSION_TYPES` is imported as a value by the unowned arch test `test_activation_registry_schema.py` (`frozenset(ALLOWED_MISSION_TYPES)`), which stays green by construction, and a `__getattr__`-only attribute has no static `Assign`/`AnnAssign` binding for the symbol-level dead-code gate's `SymbolKey` resolver to span — it resolves undecidable, cannot match the gate's allow-list, and (having no genuine `src/` caller either) is flagged as a fresh offender. This is the NFR-001 carve-out (≤1 cached import-time scan, verified never to repeat). | Draft |

---

## Success Criteria

| ID | Criterion (measurable, technology-agnostic) |
|----|---------------------------------------------|
| SC-001 | Adding one new built-in mission-type definition makes that type appear in every **derivable** roster (the five in scope: Rosters A–E) with no additional edit to their enumeration literals (demonstrated by a test that injects a synthetic type via the accessor's root seam — not by mutating the shared doctrine tree — and asserts universal pickup). The two bootstrap detectors excluded by C-009 are outside this criterion. |
| SC-002 | A present-but-malformed action index causes a loud, named failure at the point of use; a missing index remains silently empty (both demonstrated by tests). |
| SC-003 | A cross-grain collision in the built-in tree is detected by a runtime command (`doctor doctrine`, RC=1) and by a CI gate — without running the broad pytest suite. |
| SC-004 | Zero `# noqa: SLF001` bypasses of `MissionTypeProfileRepository`'s built-in-root accessor remain; the public accessor returns `src/doctrine/missions`. |
| SC-005 | Importing the hot charter modules (`mission_type_profiles`, `pack_context`) triggers **at most one** cached `mission_types/` filesystem read — inherited transitively from the C-012 carve-out via the eager `charter/__init__.py` re-export chain, not a read of their own — and a second import or roster access anywhere in the same process triggers zero further reads (no unbounded/repeated import-time I/O regression). |
| SC-006 | The full targeted test surface plus the `arch_shard_1` pole and terminology guard pass green on the mission branch. |

---

## Key Entities

- **`MissionTypeRepository`** (`src/doctrine/missions/mission_type_repository.py`) — the single source of
  truth; loads `mission_types/*.yaml`, loud-fails on id/stem mismatch or schema error, exposes `.ids()`.
- **Canonical mission-type accessor** (new, doctrine layer) — the one derivation point every roster reads.
- **`load_action_index` / `ActionIndex` / `ActionIndexError`** (`src/doctrine/missions/action_index.py`) —
  the doctrine index loader made fail-loud.
- **`scan_builtin_cross_grain_duplicates`** (`src/charter/action_grain.py`) — the cross-grain integrity scan,
  given a real runtime caller.
- **`doctrine_check` / doctrine health report** (`src/specify_cli/cli/commands/doctor.py`,
  `_doctrine_health.py`) — the runtime surface that consumes the scan.
- **`MissionTypeProfileRepository`** (`src/charter/mission_type_profile_repository.py`) — owner of the
  built-in-root accessor being promoted.

---

## Assumptions

- The four shipped mission types (`software-dev`, `documentation`, `research`, `plan`) are the current
  built-in set; no functional consumer depends on the historical software-dev-first ordering of
  `CANONICAL_MISSION_TYPES` (to be audit-confirmed during implementation; the accessor returns sorted
  order).
- `spec-kitty doctor doctrine` runs in a project context and is the appropriate runtime surface for the
  built-in integrity check; project/org override coverage is deferred (see Out of Scope).
- Re-pinning the two currently-lenient `test_action_index.py` tests to `pytest.raises` is a stale-contract
  re-pin (the old lenient behavior was the bug), not a test deletion.

---

## Out of Scope (tracked follow-ups / explicitly excluded)

- **Project/org-tier override collision coverage** for the cross-grain scan — blocked on a multi-root
  action-index engine that `action_grain.py` explicitly declares out of scope. Track as a follow-up under
  #2652 after this bundle.
- **`kernel/paths.py` bootstrap probe** — layer-forbidden (kernel⊄doctrine); left as-is (C-009). The
  `specify_cli/runtime/` counterparts (`home.py`, `show_origin.py`) were folded onto the accessor in the
  landing pass (C-009) — only the kernel site remains a genuine residual.
- **`pack_context._BUILTIN_ARTIFACT_KINDS`** — a *different* fact (artifact kinds, not mission types) with
  its own guard; NOT folded into this mission's single-source pass.
- **`RESERVED_BUILTIN_KEYS`** (runtime discovery) — a distinct reserved-word concept; not forced into the
  mission-type derivation.
- **`constants.py` `MISSION_TYPE_*` singles** — acknowledged as a latent duplicate; not in scope.
- **Renaming/sweeping the 11 sibling `_default_built_in_dir` methods** — only `MissionTypeProfileRepository`
  is promoted (C-005).
- **Provisioned default charter (#2657) / activation-driven enumeration (#2659)** — the larger epic arc;
  this bundle is the roster-consolidation + gate-hardening slice only.

---

## Dependencies

- Builds on PR #2664 (merged): the cross-grain gate, the lazy resolver seam, and the scan already enumerating
  from `MissionTypeRepository`.
- No external package (`spec-kitty-events`, `spec-kitty-tracker`) contract changes.
- ADR authority: `2026-07-15-1-doctrine-offers-charter-activates-runtime-consumes.md`,
  `2026-07-14-2-doctrine-to-core-mission-type-resolution-unification.md`,
  `2026-05-16-1-doctrine-layer-merge-semantics.md`.
