# Research — Mission-Type Single-Source + Gate Wiring

The design is locked by the spec + operator decisions; this file consolidates the confirmed decisions and
the pre-spec squad's verified facts (paula-patterns + python-pedro, verified against HEAD `4e1e8ed34`). No
open `[NEEDS CLARIFICATION]` remain.

## D-1 — Where the canonical accessor lives (layer)

- **Decision:** A cached, module-level accessor in the **doctrine** layer, next to `MissionTypeRepository`
  (e.g. `builtin_mission_type_ids() -> tuple[str, ...]` + a frozenset convenience), wrapping
  `MissionTypeRepository.default().ids()`.
- **Rationale:** `charter → doctrine` is the legal import direction (already used lazily in
  `action_grain.py`/`mission_type_profiles.py`); doctrine must NOT import charter, so the authority cannot
  live in charter. `MissionTypeRepository.default()` already resolves its own root via `importlib.resources`,
  so the accessor needs no charter-side root.
- **Alternatives considered:** (a) keep the literals + a drift-guard test — rejected: that is *parity*, not
  *unification* (charter Governing Principle / gotcha 6). (b) compute at charter import time — rejected:
  reintroduces import-time filesystem I/O into hot charter modules (NFR-001).

## D-2 — Avoiding import-time I/O in charter

- **Decision:** Charter consumers call the accessor **lazily inside function bodies** (function-local import,
  the existing `# noqa: PLC0415` cycle-guard convention), never at module top-level. `@functools.cache` on
  the accessor bounds it to ≤1 scan/process.
- **Rationale:** `pack_context._read_activated_mission_types` already reads its constant inside a function,
  so swapping the module constant for a call there is a natural fit. NFR-001 forbids any new import-time
  `mission_types/` read.

## D-3 — Frozenset vs sorted-list per consumer

- **Decision:** Accessor exposes both an ordered (sorted tuple) form and a frozenset form. Roster B
  (`_BUILTIN_MISSION_TYPE_IDS`) uses the frozenset form (its return type is `frozenset[str]` and callers do
  frozenset equality); Rosters A/C/D/E use whichever matches (A tuple/iteration, C list, D frozenset+sentinels,
  E dict-keys+alias).
- **Rationale:** `MissionTypeRepository.ids()` returns a sorted list; consumers need different container
  types. One accessor, two thin projections, avoids re-globbing per shape.

## D-4 — Canonical order

- **Decision:** The accessor returns **sorted** (lexicographic) order. `CANONICAL_MISSION_TYPES` was a
  deliberate software-dev-first tuple, but the squad found **zero functional src consumers** depend on that
  order (all set-membership/iteration). Adopting sorted order is a safe simplification; an AC audit-confirms
  no order-dependent consumer.
- **Rationale:** Avoids inventing a bespoke ordering authority; the source-of-truth ordering is the file set.

## D-5 — `load_action_index` fail-loud boundary (#2667)

- **Decision (operator):** *Present ⇒ must be well-formed; absent ⇒ empty.* A present-but-invalid index
  raises a co-located `ActionIndexError(ValueError)` — covering (1) non-mapping root, (2) non-list
  artifact-kind field value, (3) syntactically-unparseable YAML. A genuinely-missing file keeps the silent
  fallback; an intentionally-empty-but-well-formed index is empty content (no raise).
- **Rationale:** Fully closes the FR-013 false-pass class (a broken index silently dropping a grain). The
  operator chose the broad line (including unparseable YAML) over the issue's narrower "parseable" wording.
- **Exception shape:** Mirror `MissionTypeRepository._load`'s `ValueError` phrasing — name the path, the
  offending key, and the found type. Doctrine-layer convention is a named `*Error(ValueError)` co-located
  with the module (cf. `MissionTypeNotAnArtifactKind`, `OrgPackSchemaError`).

## D-6 — Runtime surface for the scan (#2666)

- **Decision:** Wire `scan_builtin_cross_grain_duplicates` into `doctrine_check()`
  (`src/specify_cli/cli/commands/doctor.py`), catching `CrossGrainDoubleDeclarationError` → unhealthy report
  + RC=1 + structured `--json` finding; add a CI structural gate. Re-add the symbol to `__all__` in
  `action_grain.py`, coupled with this src caller (C-003).
- **Rationale:** `doctor doctrine` already runs `report.healthy → exit_code` and has a `--json` path plus a
  "loud findings" renderer (`_render_unsanctioned_override_findings`) to mirror. The dead-symbol gate
  (`test_no_dead_symbols.py`) only passes once a real src importer exists — hence the coupling.
- **Boundary:** Project/org override collision coverage needs the multi-root action-index engine that
  `action_grain.py` declares out of scope → tracked follow-up, not this mission.

## D-7 — Migration live-read (#2669 Roster C, C-004)

- **Decision (operator):** The rc35 migration reads `MissionTypeRepository.default().ids()` at `apply()`
  time.
- **Trade-off (recorded in design-decisions tracer):** The squad's alternative was a frozen literal + a
  drift-guard test, preserving historical migration determinism. The operator chose the live-read: a project
  replaying rc35 after a 5th type ships will now get the 5th type written. Accepted deliberately for
  automatic new-type pickup and single-source coherence.

## D-8 — #2668 scope

- **Decision:** Promote only `MissionTypeProfileRepository`'s accessor. The 11 sibling doctrine repos have
  the same private `_default_built_in_dir` but call it intra-class with no bypass — leave them (C-005).
- **Rationale:** Only this class has cross-class `# noqa: SLF001` consumers; a cross-repo sweep is unrelated
  scope.
