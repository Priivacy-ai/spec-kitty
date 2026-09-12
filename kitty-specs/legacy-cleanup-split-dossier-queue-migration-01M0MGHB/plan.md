# Implementation Plan: Legacy Cleanup — Split Dossier Queue Migration

**Branch**: `refactor/dossier-emitters-canonical-only-1058` | **Date**: 2026-08-22 | **Spec**: [`spec.md`](./spec.md)
**Input**: Mission specification from `kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/spec.md`

**Note**: This plan fills in the canonical `/spec-kitty.plan` scaffold
(`packs/built-in/missions/software-dev/templates/plan-template.md`). Every
scaffold section is resolved below; sections that don't have direct scaffold
headings (seam identification, gate set, campsite scope, sentinel design,
etc. — required by this mission's dispatch brief) are added as clearly
labeled subsections rather than silently omitted.

## Summary

PR #1056 fixed Sonar findings in the dossier event migration but left a
boundary smell: `src/specify_cli/dossier/events.py` still hand-maintains a
~24KB, 653-line-file-local Pydantic mirror of types that the external
contract package `spec-kitty-events` (installed 6.1.0, pinned
`>=6.0.0,<7.0.0`) already owns and ships, two of the four dossier emitters
(`emit_artifact_indexed`, `emit_artifact_missing`) still carry a
`*args`/`**kwargs` legacy-argument bridge (`_consume_legacy_values`), and
`src/specify_cli/sync/emitter.py`'s `_PAYLOAD_RULES` table hand-maintains
four dossier validation rules instead of delegating to the canonical
`spec_kitty_events.conformance.validate_event()`. This mission (a) deletes
the local mirror and imports the canonical types, (b) removes the two
emitters' legacy bridge while promoting the one live keyword-argument shape
it currently carries (`dossier_pipeline.py`'s calls) to explicit parameters,
(c) delegates dossier payload validation to `validate_event()` behind a
reconciling sentinel in `_PAYLOAD_RULES`, and (d) adds a construction-time
AST guard so positional calls to the four emitters cannot silently regrow.
The queue-drain half of issue #1058 is confirmed superseded by mission #3293
and is explicitly out of scope (per spec.md Clarifications, session
2026-08-22) — this mission does not touch `sync/queue.py` or
`sync/migrate_journal.py`.

## Technical Context

**Language/Version**: Python 3.11+ (repo-wide requirement, charter §Technical Standards).
**Primary Dependencies**: `pydantic` (canonical types now imported, not
re-declared), `spec-kitty-events` 6.1.0 (external contract package, already
pinned `>=6.0.0,<7.0.0` — no version bump), `jsonschema` (direct dependency,
used transitively by `validate_event(strict=True)`), `typer`/`rich` (unused
by this mission's touched surface — no CLI command signatures change).
**Storage**: N/A — this mission does not touch persistence; the append-only
event journal and offline queue (`sync/queue.py`) are explicitly out of
scope.
**Testing**: `pytest`, targeted at `tests/dossier/` (including
`test_snapshot_emit.py`, which FR-006 requires rewriting — see
"Mission-Specific Design Decisions" below), `tests/sync/test_events_namespace.py`,
`tests/sync/test_events.py`, `tests/sync/test_dossier_pipeline.py`, `tests/sync/test_diagnose.py` (new
regression test closing FR-011's `diagnose.py` gap — see below),
and `tests/architectural/` (new guard test + `test_shared_package_boundary.py`),
per NFR-003 and the charter's "Run only the affected test packages" rule.
Full `pytest tests/` reserved for pre-merge/post-merge validation only.
**CI shard routing (plan-review remediation, closes PLAN-VERIFY-001)** —
corrected against live `.github/workflows/ci-quality.yml`, superseding any
prior "fast-doctrine"/"slow" shard naming: these tests are actually
collected by `integration-tests-core-misc`, `arch-adversarial`, and
`fast-tests-sync`/`integration-tests-sync`; none of these jobs enforces a
local `--cov-fail-under` floor. See the corrected "Test shards with
coverage" row in "Gate Set" below for the full routing table and job
citations.
**Target Platform**: Linux/macOS/Windows CLI (no platform-specific code
touched).
**Project Type**: Single Python package (`specify_cli`) — no web/mobile
split applies.
**Performance Goals**: N/A — this is an internal type/validation refactor
with no new hot path; existing `<2s` CLI operation budget is unaffected
since no new I/O or computation is introduced (emitters still build one
payload object and hand it to `fire_dossier_event`).
**Constraints**: NFR-001 (no net-new dependency, no version-constraint
change), NFR-002 — scoped to `emitter.py::_validate_payload`: validation
failures stay visible via the existing `[yellow]Warning: ...]` +
drop-not-queue contract; `diagnose.py::_validate_payload` (FR-011) carries
its own, equally binding NFR-002 contract, not "print a warning" but
"surface the violation in `DiagnoseResult.errors`" — see the "`diagnose.py`
coordinated fix" section below — C-001 (queue-drain out of scope), C-002 (no
transitional deprecated wrapper).
**Scale/Scope**: 3 production source files
(`src/specify_cli/dossier/events.py`, 653 lines;
`src/specify_cli/sync/emitter.py`, 2,671 lines — only ~90 of which
(`_PAYLOAD_RULES` dossier entries + `_validate_payload`) are touched;
`src/specify_cli/sync/diagnose.py` — a second, independent consumer of the
same module-level `_PAYLOAD_RULES` dict, requiring a small coordinated
change, added by plan-review remediation (closes PLAN-ARCH-001; now traced
to spec.md FR-011, added in the PLAN-FRESH-001 remediation round) — see
"FR-006/FR-007 sentinel shape" below), plus
`src/specify_cli/sync/dossier_pipeline.py` (535 lines) is read-only evidence
(its call sites do not change, see FR-004 analysis below) and
`src/specify_cli/dossier/drift_detector.py` (one already-keyword-only call
site, read-only evidence for FR-008). 6 existing test files touched/
extended or verified (`test_events.py`, `test_dossier_pipeline.py`,
`test_snapshot_emit.py`, `test_diagnose.py` touched with real changes;
`test_emitter_adapter.py`, `test_events_namespace.py` verified as needing
zero changes), 1 new guard test file added.

**Full `_PAYLOAD_RULES` consumer inventory (plan-review remediation, closes
PLAN-ARCH-004)** — `grep -rn "_PAYLOAD_RULES" src/ tests/`, re-run live
during this remediation pass; every hit classified so Phase 3
(FR-006/FR-007) is not "ready to implement" until each row below is
accounted for:

| Consumer | Classification | Why |
|---|---|---|
| `src/specify_cli/sync/emitter.py` (`_validate_payload`, `VALID_EVENT_TYPES`) | needs-code-change | This mission's own FR-006/FR-007 target; the sentinel branch is added here. |
| `src/specify_cli/sync/diagnose.py` (`_validate_payload` free function, import at `diagnose.py:51`) | needs-code-change | Second, independent shape-sensitive consumer — `rules.get("required", set())`/`rules.get("validators", {})` with no shape guard; crashes on any dossier event once the sentinel lands, unless fixed (see "FR-006/FR-007 sentinel shape" below). |
| `tests/dossier/test_snapshot_emit.py::test_emit_rule_wires_canonical_validator_for_hash_fields` | needs-test-rewrite | Directly subscripts `_PAYLOAD_RULES["MissionDossierSnapshotComputed"]["validators"]` / `[...ParityDriftDetected"]["validators"]`; raises `TypeError: 'object' object is not subscriptable` once those two keys hold the sentinel. |
| `tests/sync/test_diagnose.py` | needs-test-rewrite (addition) | Zero existing tests in this file exercise `diagnose_events()`/`diagnose.py::_validate_payload` against a dossier event type (grepped: zero `dossier` hits) — a new regression test is required to close this coverage gap. |
| `tests/contract/test_handoff_fixtures.py` (`test_fixture_payload_passes_emitter_rules`) | read-only-safe | Iterates only the 8 non-dossier `FIXTURE_EVENTS` types (`WPStatusChanged`, `WPCreated`, `WPAssigned`, `MissionCreated`, `MissionClosed`, `HistoryAdded`, `ErrorLogged`, `DependencyResolved` — enforced by its own sibling `test_all_event_types_covered`); never looks up a dossier key, so the sentinel value is never dereferenced here. |
| `tests/status/test_actor_boundary_normalize.py` | read-only-safe | Looks up only `_PAYLOAD_RULES["WPStatusChanged"]`/`["WPCreated"]` — non-dossier keys, dict-shaped before and after this mission. |
| `tests/status/test_sync_lane_mapping.py` | read-only-safe | Looks up only `_PAYLOAD_RULES["WPStatusChanged"]` — non-dossier, dict-shaped before and after. |
| `tests/contract/test_identity_contract_matrix.py` | not a real consumer | The one grep hit here is a source comment (`# must match emitter._PAYLOAD_RULES validator`), not a runtime read of the dict — no action needed. |

## Constitution Check

*GATE: Charter alignment, evaluated against `.kittify/charter/charter.md`
(this project has no separate `constitution.md`; the charter is the binding
governance document per `AGENTS.md`/`CLAUDE.md`). Re-checked after Phase 1
design below — no new gaps found.*

| Charter clause | Alignment |
|---|---|
| Architectural alignment / Shared Package Boundaries (`DIRECTIVE_001`, "Architecture: Shared Package Boundaries") | PASS — this mission's entire point is closing a Shared-Package-Boundary violation (a hand-copied mirror of an external contract package's types). No vendoring is added; `spec-kitty-events` stays consumed as a normal pinned PyPI dependency (see "Contract Movement" below). |
| Single canonical authority (`DIRECTIVE_044`) | PASS — after this mission, `LocalNamespaceTuple`/`ArtifactIdentity`/`ContentHashRef`/`ProvenanceRef`/the four `MissionDossier*Payload` types have exactly one owning source (`spec_kitty_events`), not two. |
| ATDD-first (C-011) | PASS by construction — see "Red-First / ATDD Test Mapping" below; every FR gets a named test that fails on revert, added/asserted red-first per WP. |
| Campsite cleaning (Standing Order #2) | Addressed explicitly below ("Campsite-Clean Scope") — conclusion: no separate campsite-clean step is needed; the mission's own FR-001..FR-010 scope already covers the touched surface. |
| Mission tracer files (Standing Order #3) | Already seeded at spec phase (`tracer-approach.md`, `tracer-design-decisions.md`, `tracer-tooling-friction.md`); this plan phase appended entries during scaffolding friction (see tracer files); implementation phase will append further. |
| Architectural gate discipline (Standing Order #5) | FR-008's AST guard is designed with a concrete floor (0 positional call sites in `src/`) + a self-mutation positive control (planted violation) — see "FR-008 Guard Test Design" below, matching `test_shared_package_boundary.py`'s established pattern in this repo. |
| Red-main & release discipline / Pre-existing Failure Reporting Rule (Standing Order #9, charter §Pre-existing Failure Reporting Rule) | Addressed below ("Baseline Red Policy") — concrete baselining procedure stated before any change lands. |
| Terminology Canon (C-004) | PASS — this plan uses "Mission"/"mission" throughout; no `feature*` alias is introduced (existing code's internal parameter name `mission_slug` is already canonical; no `--feature`-style flag exists on this surface). |
| Git & workflow discipline (Standing Order #7, `DIRECTIVE_045`) | PASS — `single_branch` topology, one PR to `main`, operator merges; no direct push planned (see tracer-design-decisions.md topology history). |

No violations requiring the Complexity Tracking table below to carry real
entries (see that section).

## Project Structure

### Documentation (this mission)

```
kitty-specs/legacy-cleanup-split-dossier-queue-migration-01M0MGHB/
├── spec.md                 # Already committed (455 lines, Clarifications binding)
├── plan.md                 # This file
├── tracer-approach.md      # Seeded at spec phase, appended at plan phase
├── tracer-design-decisions.md   # Seeded at spec phase, appended at plan phase
├── tracer-tooling-friction.md   # Seeded at spec phase, appended at plan phase
└── tasks.md / tasks/       # Phase 2 output — NOT created by this plan phase
```

**No `research.md`, `data-model.md`, `quickstart.md`, or `contracts/` are
created for this mission**, and that is a deliberate scope decision, not an
omission:
- `research.md` — not needed. All ambiguity the issue/dispatch brief carried
  was already resolved and recorded as binding decisions in spec.md's
  `## Clarifications` section (session 2026-08-22, 8 verified Q/A pairs).
  There is no open research question left for Phase 0 to answer.
- `data-model.md` — not needed. This mission does not introduce a new data
  model; it *deletes* a locally-duplicated one and imports the canonical
  external one verbatim. The "Key Entities" section of spec.md already
  states the after-state precisely (including the FR-006/FR-007 sentinel
  reconciliation), and this plan's "Mission-Specific Design Decisions"
  section below makes the sentinel's concrete shape and the FR-004
  parameter-promotion contract explicit — that is this mission's entire data
  surface.
- `quickstart.md` — not applicable. This is an internal refactor of two
  existing library modules with no new CLI command, flag, or user-facing
  workflow to walk through.
- `contracts/` — not applicable in the "new API contract" sense this
  directory exists for. The one contract this mission touches
  (`spec-kitty-events`'s public types and `validate_event()` signature) is
  an *existing, external, already-versioned* contract this mission consumes
  read-only (see "Contract Movement" below) — it is not a contract this
  mission defines or changes, so there is nothing to place in `contracts/`.

### Source Code (repository root)

```
src/specify_cli/
├── dossier/
│   ├── events.py            # FR-001..FR-005: mirror deletion, bridge removal,
│   │                        #   kwarg promotion, last_known_ref drop
│   └── drift_detector.py    # READ-ONLY evidence: existing call site (line 419)
│                            #   already 100% keyword-only; zero lines change
├── sync/
│   ├── emitter.py            # FR-006/FR-007: _PAYLOAD_RULES sentinel +
│   │                         #   is_dossier_delegate() + _validate_payload
│   │                         #   delegation branch + corrected type annotation
│   ├── diagnose.py           # FR-011 (plan-review remediation, closes
│   │                         #   PLAN-ARCH-001): is_dossier_delegate()-
│   │                         #   guarded branch in diagnose.py::_validate_payload
│   └── dossier_pipeline.py   # READ-ONLY evidence: existing call sites prove
│                             #   FR-004's promoted kwargs are sufficient;
│                             #   zero lines change here

tests/
├── dossier/
│   ├── test_events.py         # FR-009: re-point 7 mirror-type imports to
│   │                          #   spec_kitty_events; FR-010: preserve
│   │                          #   test_preserves_legacy_positional_order unmodified
│   ├── test_emitter_adapter.py  # No changes (verified: no mirror-type import)
│   └── test_snapshot_emit.py  # plan-review remediation (closes PLAN-ARCH-002):
│                               #   rewrite test_emit_rule_wires_canonical_
│                               #   validator_for_hash_fields against the new
│                               #   ConformanceResult delegation behavior
├── sync/
│   ├── test_events_namespace.py  # No changes (verified: no mirror-type import)
│   ├── test_dossier_pipeline.py  # FR-004: add new real-call regression
│   │                              #   test(s) asserting AC1/AC2 content;
│   │                              #   existing plain-Mock-patched tests
│   │                              #   stay as-is for their own (unrelated) purpose
│   └── test_diagnose.py          # FR-011 (plan-review remediation, closes
│                                  #   PLAN-ARCH-001's coverage gap): new
│                                  #   dossier-event regression test(s) through
│                                  #   diagnose_events()
└── architectural/
    ├── test_shared_package_boundary.py  # No changes (spec.md Clarifications:
    │                                    #   import-based gate; not this mission's
    │                                    #   job to strengthen it — see "Why the
    │                                    #   Mirror Survived" below)
    └── test_dossier_emitter_positional_guard.py  # NEW: FR-008 AST guard test
```

**Structure Decision**: Single-project layout (spec-kitty's existing
`src/specify_cli/` package structure). No new top-level directory, no new
package. Every touched file already exists at the path shown; the one new
file is a single new test module under the existing
`tests/architectural/` convention (matching the AST-based guard-test pattern
already established there — see `test_shared_package_boundary.py` and
`tests/architectural/test_guard_capability_call_sites.py` as direct
precedent for both the detection technique and the "positive control"
regression shape).

---

## Seam Identification (binding requirement of this mission's dispatch brief)

**This mission lands entirely on the CLI + sync seam.** No kernel surface
(`src/kernel/`), no doctrine surface (`src/doctrine/`, `src/charter/`), and
no mission-step-contract/action-index surface is touched.

- `src/specify_cli/dossier/events.py`, `src/specify_cli/sync/emitter.py`,
  and `src/specify_cli/sync/diagnose.py` are all CLI-owned business logic
  under `src/specify_cli/` — the "Internal Runtime Boundary" the charter
  describes as "CLI-owned implementation code, not an external shared
  dependency." **`sync/diagnose.py` is added to this list by plan-review
  remediation (closes PLAN-ARCH-001, PLAN-ARCH-004; now traced to spec.md
  FR-011)**: it is a second,
  in-seam consumer of `emitter.py`'s module-level `_PAYLOAD_RULES` dict
  (imported directly at `diagnose.py:51`, not re-implemented), so it shares
  the same seam as `emitter.py` itself — the FR-006/FR-007 sentinel change
  is not contained to `emitter.py` alone.
- No new module is created outside these three existing modules
  (`specify_cli.dossier.events`, `specify_cli.sync.emitter`,
  `specify_cli.sync.diagnose`) plus one new test module under the existing
  `tests/architectural/` convention. There is no new seam to name — this
  mission tightens an existing one.
- **No CLI command reaches past a service into kernel internals** — this
  mission does not touch any `typer.Option`/command surface at all; the
  functions changed (`emit_artifact_indexed`, `emit_artifact_missing`, the
  `_PAYLOAD_RULES`/`_validate_payload` pair in `emitter.py`, and the
  coordinated `is_dossier_delegate()`-guarded branch added to
  `diagnose.py::_validate_payload`) are internal library functions called
  by `dossier_pipeline.py`, `drift_detector.py`, and — for `diagnose.py`
  — `diagnose_events()`, itself the entry point for the `spec-kitty sync
  diagnose` CLI command; that command's own `typer` surface is unchanged,
  only the internal validation helper it calls gains a new branch.
  `fire_dossier_event` (the sync boundary these emitters hand off to) is
  unchanged.
- Dossier→sync inversion is preserved: `events.py`'s module docstring notes
  "the dossier->sync edge is inverted through emitter_adapter
  (`tests/architectural/test_dossier_sync_boundary.py`)" — this mission does
  not add a new import from `dossier/` into `sync/` internals or vice versa
  beyond the existing `fire_dossier_event` call; `test_dossier_sync_boundary.py`
  is unaffected and not in this mission's touched-file list.

## Generated Artifacts (binding requirement of this mission's dispatch brief)

**Nothing generated is touched.** Verified, not assumed:
- `src/specify_cli/dossier/events.py` and `src/specify_cli/sync/emitter.py`
  are hand-written Python source with no `# GENERATED`/codegen header, no
  entry in any schema-generation script, and no downstream `spec-kitty
  upgrade` migration references them as a generated-asset source (grepped:
  neither path appears in `packs/built-in/` template trees nor in any
  `upgrade/migrations/` generator). They are ordinary library modules
  maintained by hand, exactly like the tests that exercise them.
- The JSON schemas this mission's new validation path reads
  (`spec_kitty_events.schemas.load_schema(...)`) are generated *inside the
  external `spec-kitty-events` package*, not in this repository — this
  mission consumes them read-only via the installed package; it does not
  regenerate, vendor, or hand-edit them.
- No doctrine artifact (glossary, action index, mission-step contract) is
  generated or hand-edited by this mission.

## Contract Movement (binding requirement of this mission's dispatch brief)

**No contract moves.** Each contract surface this mission is adjacent to is
explicitly preserved, per the charter's "Architecture: Shared Package
Boundaries" section:

- **`spec-kitty-events` package contract**: consumed as an external contract
  package (charter: "`spec-kitty-events` ... true external package
  dependenc[y] for the Spec Kitty CLI. Treat like normal third-party Python
  libraries"). This mission imports more of its public surface
  (`LocalNamespaceTuple`, `ArtifactIdentity`, `ContentHashRef`,
  `ProvenanceRef`, the four `MissionDossier*Payload` classes,
  `conformance.validate_event`) than it did before, but **does not change
  the version constraint** — `pyproject.toml:80` stays
  `spec-kitty-events>=6.0.0,<7.0.0`, already satisfied by the installed
  6.1.0 (verified live: `spec_kitty_events.__version__ == "6.1.0"`, and
  every symbol this mission needs is already importable at the package top
  level or from `spec_kitty_events.conformance` — confirmed by direct
  interpreter introspection during this planning phase). NFR-001 is
  satisfied by construction, not by a promise to be careful.
- **Does not vendor `spec-kitty-events` source**: this mission *deletes*
  vendored-shape duplication (the local mirror), moving strictly in the
  direction the charter requires ("Do not vendor their source into the CLI
  package").
- **Doctrine schemas / mission step contracts / action indices /
  orchestrator-api surface**: none of these exist on the touched surface;
  none are read, written, or referenced by any file this mission changes.
  No statement of preservation is needed beyond noting they are simply not
  in play.
- **spec-kitty-events#50**: an open, unmerged, non-draft PR against the
  *external* package adding fixture files. Per spec.md Clarifications, this
  mission is explicitly NOT coupled to it — the installed 6.1.0 already
  enforces every constraint #50's fixtures exercise
  (`manifest_step: minLength: 1`, `artifact_count: minimum: 0`, both
  verified directly against the installed schemas/models during
  specification). This mission writes its own regression tests against the
  already-installed `validate_event()` rather than gating on #50 merging.

---

## Mission-Specific Design Decisions

### Why the local mirror survived the existing boundary gate (align with spec, do not re-litigate)

`tests/architectural/test_shared_package_boundary.py`'s `_forbidden_imports()`
walks the AST for `ast.Import`/`ast.ImportFrom` nodes matching a banned
*module prefix* (`spec_kitty_runtime`, `specify_cli.spec_kitty_events`).
`dossier/events.py`'s six mirror classes import nothing from
`spec_kitty_events` at all — they are independently hand-written Pydantic
models that happen to duplicate field names, so an import-based gate has
structurally nothing to flag. **This plan does not propose strengthening
that gate.** Per spec.md's Clarifications, this is a documented,
already-adjudicated known-gap, not a gate bug: a shape-similarity detector
is a fundamentally broader, false-positive-prone class of check (it would
need to reason about "these two independently-written classes happen to
look alike," which is a much harder and noisier problem than "this import
statement names a banned module") and is out of scope here. This mission's
FR-001 closes the *instance* of the gap; a general-purpose shape-similarity
gate is explicitly not this mission's job (locality of change /
`DIRECTIVE_024` — see charter's change-scope reconciliation section).

### FR-006/FR-007 sentinel shape (concrete design — left to planning by spec.md's Key Entities section)

**Problem**: `_validate_payload`'s single generic code path
(`emitter.py:2549-2572`) treats every `_PAYLOAD_RULES[event_type]` value
uniformly as `{"required": set[str], "validators": dict[str, Callable]}`.
FR-006 (delegate the 4 dossier types to `validate_event()`) and FR-007 (keep
the four dossier keys physically present and recognized in
`_PAYLOAD_RULES`/`VALID_EVENT_TYPES`) must both hold without the generic
loop misinterpreting the new dossier value shape.

**Concrete sentinel design**: introduce a single frozen marker instance,
module-level in `emitter.py` next to `_PAYLOAD_RULES`:

```python
_DOSSIER_VALIDATE_EVENT_DELEGATE = object()  # sentinel: see is_dossier_delegate() below

_DOSSIER_EVENT_TYPES = frozenset({
    "MissionDossierArtifactIndexed",
    "MissionDossierArtifactMissing",
    "MissionDossierSnapshotComputed",
    "MissionDossierParityDriftDetected",
})
```

**Predicate-unification (plan-review remediation, round 2, closes
PLAN-FRESH-002)**: a single public predicate wraps the sentinel's identity
check, defined once, module-level in `emitter.py`, alongside the sentinel:

```python
def is_dossier_delegate(rules: object) -> bool:
    """True if *rules* is the dossier validate_event() delegation sentinel."""
    return rules is _DOSSIER_VALIDATE_EVENT_DELEGATE
```

Every consumer that needs to recognize the sentinel — `emitter.py`'s own
`_validate_payload` below, and (per FR-011's coordinated fix, see
"`diagnose.py` coordinated fix" below) `diagnose.py::_validate_payload` —
calls this one predicate rather than re-implementing the `is` comparison
independently. Only `is_dossier_delegate()`'s own body references
`_DOSSIER_VALIDATE_EVENT_DELEGATE` directly; no other call site anywhere in
this mission's diff does.

Each of the four dossier entries in `_PAYLOAD_RULES` becomes:

```python
"MissionDossierArtifactIndexed": _DOSSIER_VALIDATE_EVENT_DELEGATE,
"MissionDossierArtifactMissing": _DOSSIER_VALIDATE_EVENT_DELEGATE,
"MissionDossierSnapshotComputed": _DOSSIER_VALIDATE_EVENT_DELEGATE,
"MissionDossierParityDriftDetected": _DOSSIER_VALIDATE_EVENT_DELEGATE,
```

(all four keys point at the *same* sentinel object — there is nothing
per-event-type to carry in the dict value once delegation is the whole
story; the event-type string itself is passed through to
`validate_event(payload, event_type, strict=True)` at call time, so no
per-key data is lost).

`VALID_EVENT_TYPES = frozenset(_PAYLOAD_RULES.keys())` (`emitter.py:897`)
is **unchanged** — the four dossier keys never leave `_PAYLOAD_RULES`, so
FR-007's unknown-event-type rejection check
(`if event_type not in VALID_EVENT_TYPES:`, `emitter.py:2514`) keeps working
identically for dossier and every other event type.

`_validate_payload` gains an explicit early-return branch, ahead of the
generic `rules["required"]`/`rules["validators"]` access:

```python
def _validate_payload(self, event_type: str, payload: dict[str, Any]) -> bool:
    rules = _PAYLOAD_RULES.get(event_type)
    if rules is None:
        return True
    if is_dossier_delegate(rules):
        return self._validate_dossier_payload(event_type, payload)
    # ... existing generic required/validators loop, unchanged ...
```

(Round-2 plan-review remediation, closes PLAN-FRESH-002: this sample now
calls the shared `is_dossier_delegate()` predicate defined above instead of
a raw `rules is _DOSSIER_VALIDATE_EVENT_DELEGATE` identity comparison, so
`emitter.py::_validate_payload` and `diagnose.py::_validate_payload` share
one predicate rather than each open-coding the sentinel check.)

`_validate_dossier_payload` is a small new private method that performs the
lazy local import (matching this file's existing convention — e.g.
`Event as EventModel` imported locally inside `_validate_event`,
`emitter.py:2477` — there is no module-scope `spec_kitty_events` type import
anywhere in `emitter.py` today, so this has no existing module-scope sibling
to sit "alongside"; it establishes its own lazy-import call site consistent
with the file's pattern), calls `validate_event(payload, event_type,
strict=True)`, and translates `ConformanceResult.valid` into the existing
`bool` contract — printing `.model_violations`/`.schema_violations` in the
warning instead of the current generic message:

```python
def _validate_dossier_payload(self, event_type: str, payload: dict[str, Any]) -> bool:
    from spec_kitty_events.conformance import validate_event

    result = validate_event(payload, event_type, strict=True)
    if not result.valid:
        violations = [str(v) for v in (*result.model_violations, *result.schema_violations)]
        _console.print(f"[yellow]Warning: {event_type} payload invalid: {'; '.join(violations)}[/yellow]")
    return result.valid
```

Why a sentinel object rather than e.g. a magic string or a dict with a
`"__delegate__": True` marker key: an `object()` sentinel is unambiguous
under `is` identity comparison (no accidental collision with a real
`{"required": ..., "validators": ...}` dict that happens to contain a
similarly-named key), costs nothing, and needs no new imported type. This
mirrors the same "unambiguous marker, `is`-compared" idiom already used
elsewhere in this codebase for private module-level sentinels.

**Corrected type annotation (plan-review remediation, closes
PLAN-ARCH-003)**: `_PAYLOAD_RULES` carries an explicit module-level
annotation today (`emitter.py`: `_PAYLOAD_RULES: dict[str, dict[str, Any]] =
{` — cite by symbol, `_PAYLOAD_RULES`'s own definition, rather than a line
number, since line numbers drift). Once four keys hold the `object()`
sentinel instead of a `dict[str, Any]`, that annotation is violated —
`CLAUDE.md`'s Code Style section requires new code to "pass ruff and mypy
with zero issues and zero warnings" as a repo contribution bar independent
of `mypy --strict`'s CI-advisory-only status. This mission updates the
annotation in the same commit as the sentinel:

```python
_PAYLOAD_RULES: dict[str, dict[str, Any] | object] = {
```

(A narrower `Literal`/sentinel-aware type alias was considered and rejected
as unnecessary ceremony for a private module-level dict with exactly one
non-dict sentinel value; `dict[str, Any] | object` is honest about the
actual union without inventing new public API surface.)

**`diagnose.py` coordinated fix (plan-review remediation, closes
PLAN-ARCH-001 and the `diagnose.py` half of PLAN-ARCH-004; traced to
spec.md FR-011 as of the round-2 PLAN-FRESH-001 remediation)**: the sentinel
design above was verified only against `emitter.py::_validate_payload`. A
repo-wide `grep -rn "_PAYLOAD_RULES" src/ tests/` (re-run during this
remediation pass — see the consumer inventory table under "Technical
Context / Scale/Scope" above) surfaces a second, independent,
shape-sensitive consumer of the same module-level dict:
`src/specify_cli/sync/diagnose.py`, imported at `diagnose.py:51`
(`from .emitter import _PAYLOAD_RULES, VALID_AGGREGATE_TYPES`) and consumed
by its own free function `diagnose.py::_validate_payload` (distinct from,
but shape-compatible today with, the emitter's method): `rules =
_PAYLOAD_RULES.get(event_type)` then `rules.get("required", set())` /
`rules.get("validators", {})`, with no shape guard and no surrounding
`try/except`. Its caller, `_validate_event()` — called from
`diagnose_events()`, the entry point for the production `spec-kitty sync
diagnose` CLI command — invokes it unconditionally whenever `event_type in
_PAYLOAD_RULES` (`diagnose.py:215`). Once the four dossier keys point at
`_DOSSIER_VALIDATE_EVENT_DELEGATE`, any dossier event sitting in the local
offline queue (the normal case for any active mission using dossier
tracking) crashes `diagnose_events()` with an uncaught `AttributeError:
'object' object has no attribute 'get'`.

Fix mechanism: `diagnose.py::_validate_payload` imports the
`is_dossier_delegate()` predicate already defined module-level in
`emitter.py`, alongside the sentinel (see "FR-006/FR-007 sentinel shape"
above — `emitter.py::_validate_payload` itself now also calls this exact
predicate, per the round-2 PLAN-FRESH-002 remediation, so both consumers
share one definition and only the predicate's own body references
`_DOSSIER_VALIDATE_EVENT_DELEGATE` directly). `diagnose.py::_validate_payload`
calls this predicate before doing any `rules["required"]`/`rules.get(...)`
access, and delegates to
`spec_kitty_events.conformance.validate_event()` the same way
`emitter.py::_validate_dossier_payload` does — folding the returned
`ConformanceResult`'s violations into `diagnose.py`'s existing `errors:
list[str]` accumulator (its established per-event error-reporting shape)
rather than the emitter's `_console.print` warning path, since
`diagnose.py`'s contract is "return structured errors," not "print a
warning." Concretely:

```python
def _validate_payload(event_type, payload, errors):
    rules = _PAYLOAD_RULES.get(event_type)
    if rules is None:
        return
    if is_dossier_delegate(rules):
        from spec_kitty_events.conformance import validate_event

        result = validate_event(payload, event_type, strict=True)
        if not result.valid:
            errors.extend(
                str(v) for v in (*result.model_violations, *result.schema_violations)
            )
        return
    # ... existing generic required/validators loop, unchanged ...
```

Regression test (closes the coverage gap): add a new test to
`tests/sync/test_diagnose.py` (already an existing file in this repo, not
previously in this mission's touched-test scope; no existing test in it
exercises a dossier event type — grepped: zero `dossier` hits) that runs
`diagnose_events()` against a dossier-typed event dict, both valid and
invalid payload, asserting (a) no crash and (b) the invalid case reports a
real violation string in `DiagnoseResult.errors` via the `ConformanceResult`
translation path. This is this mission's ATDD red-first proof for FR-011
(the `diagnose.py` coordinated fix, spec.md FR-011 as of the round-2
PLAN-FRESH-001 remediation) — see the new FR-011 row in "Red-First / ATDD
Test Mapping" below.

**`test_snapshot_emit.py` rewrite required (plan-review remediation, closes
PLAN-ARCH-002)**:
`tests/dossier/test_snapshot_emit.py::test_emit_rule_wires_canonical_validator_for_hash_fields`
(currently at `test_snapshot_emit.py:220-228`) directly subscripts
`_PAYLOAD_RULES["MissionDossierSnapshotComputed"]["validators"]` and
`_PAYLOAD_RULES["MissionDossierParityDriftDetected"]["validators"]`,
asserting the wired validator callable `is _is_canonical_snapshot_hash`.
Once FR-006 replaces those two entries with the sentinel, this raises
`TypeError: 'object' object is not subscriptable` at test-run time — this
test is physically inside `tests/dossier/`, already in this mission's
NFR-003 test scope, so it is not new test-surface, only a required rewrite.
This test must be rewritten (not merely re-verified) to assert against the
new delegation behavior instead of a validator-callable wiring that no
longer exists for these two event types — e.g. construct a
`MissionDossierSnapshotComputed` / `MissionDossierParityDriftDetected`
payload with a malformed `snapshot_hash`/`expected_hash`/`actual_hash` value
and assert it surfaces as a violation via
`EventEmitter._validate_dossier_payload`'s `ConformanceResult` translation
(the same real-violation-detail assertion shape as the FR-006 row in
"Red-First / ATDD Test Mapping" below), rather than asserting a specific
validator function `is` the dict value.

### FR-004 raise/report/refuse contract (walked through precisely)

**Before this mission**: `emit_artifact_indexed(mission_slug, artifact_key,
artifact_class, relative_path, content_hash_sha256, size_bytes, *args,
..., **kwargs)`. `dossier_pipeline.py:101-114` calls it with
`step_id=step_id, required_status=artifact.required_status` as keyword
arguments; these are **not** explicit parameters — they land in `**kwargs`
and are consumed by `_consume_legacy_values(args, kwargs, names=("wp_id",
"step_id", "required_status"), defaults={...})`.

**If the bridge were deleted naively** (just remove `*args`/`**kwargs`
without adding explicit parameters): `dossier_pipeline.py`'s call would
raise `TypeError: emit_artifact_indexed() got an unexpected keyword argument
'step_id'` — Python's own call-binding, unconditional, not
tool-dependent. But `_emit_artifact_events` (`dossier_pipeline.py:96-137`)
wraps *each* emitter call in its own `try: ... except Exception as e:
logger.warning(...)` — so that `TypeError` would be caught, logged as a
warning, and the pipeline would silently continue with `events_emitted`
under-counted. This is exactly the "silent success" failure mode the
charter names as this repo's dominant defect class.

**FR-004's actual contract, in order**:
1. Promote `wp_id`, `step_id`, `required_status` (defaults `None`, `None`,
   `"optional"`) to explicit keyword-only parameters of
   `emit_artifact_indexed`, and `reason_detail`, `blocking` (defaults
   `None`, `True`) to explicit keyword-only parameters of
   `emit_artifact_missing` — in the *same commit* that removes
   `*args`/`**kwargs`, since the function only has one signature at any
   commit boundary (this is why FR-001/FR-002 mirror-deletion and
   FR-003/FR-004 bridge-removal are sequenced as adjacent, not
   interleaved-with-other-files, phases below).
2. With the promotion in place, `dossier_pipeline.py`'s existing keyword
   calls bind directly to real parameters — no `TypeError`, no `**kwargs`
   catch-all needed at all. The bridge's removal becomes *invisible* to
   every existing production caller, by construction, not by luck.
3. Only a *removed* keyword name (e.g. a hypothetical future caller passing
   `foo=1`) now raises `TypeError` — which is the intended, visible failure
   mode for a genuinely unsupported argument, exactly matching FR-005's
   parallel contract for the dropped `last_known_*` parameters.
4. **Test bar (binding, per FR-004 in spec.md; corrected — plan-review
   remediation, closes PLAN-VERIFY-002)**: the regression test(s) proving
   this must not rely on `tests/sync/test_dossier_pipeline.py`'s *existing*
   `@patch("specify_cli.dossier.events.emit_artifact_indexed")` /
   `@patch("specify_cli.dossier.events.emit_artifact_missing")` decorators
   as-is — verified during this planning phase that both use a plain
   `MagicMock` (no `autospec=True`, no `spec=`), which would accept *any*
   keyword argument silently and therefore would NOT go red if the
   parameter promotion were reverted. **An `autospec=True`/`spec=`-mocked
   test alone is not sufficient**: it proves only that
   `dossier_pipeline.py`'s keyword call *binds* to the real signature —
   because `_emit_artifact_events` wraps both calls in a broad `except
   Exception`, a mock that merely records "was I called without raising"
   cannot exercise or verify AC1 (diagnostics folding into
   `context_diagnostics`/`step_id`, `events.py`'s
   `diagnostics.setdefault("artifact_key", ...)`/`("required_status", ...)`)
   or AC2 (the `blocking` short-circuit, `events.py`'s `if not blocking: ...
   return None` inside `emit_artifact_missing`), both of which live inside
   the function bodies a mock replaces. The binding test bar is therefore:
   (a) at least one new test must call the real, unmocked
   `emit_artifact_indexed`/`emit_artifact_missing` end-to-end (via
   `_emit_artifact_events`/`sync_feature_dossier`, with only unrelated
   collaborators such as `Indexer`/`ManifestRegistry` mocked) and assert on
   the returned/fired payload's `context_diagnostics`/`step_id` fields
   (AC1) and on the emit/no-emit outcome via `_emit_artifact_events`'s
   `events_emitted` return-value count or an equivalent captured-event
   assertion (AC2); (b) an `autospec=True`/`spec=emit_artifact_indexed`/
   `spec=emit_artifact_missing`-mocked test may be added *in addition*, as
   a narrower supplementary check, but if so it must assert on a
   try/except-surviving observable (`events_emitted` count or
   `mock_emit.call_args`), never merely that the outer call did not raise —
   see "Red-First / ATDD Test Mapping" below for the exact test names and
   revert-behavior this plan commits to.

### FR-005 dormant-field handling

`MissionDossierArtifactMissingPayload.last_known_ref` is canonically typed
`Optional[ProvenanceRef]` (verified live:
`ske.MissionDossierArtifactMissingPayload.model_fields['last_known_ref'].annotation
== typing.Optional[spec_kitty_events.dossier.ProvenanceRef]`).
`ProvenanceRef`'s fields (`source_event_ids`, `git_sha`, `git_ref`,
`actor_id`, `actor_kind`, `revised_at`) share zero names with the local
mirror's `ContentHashRef` shape (`algorithm`, `hash`, `size_bytes`,
`encoding`) that `last_known_content_hash_sha256`/`last_known_size_bytes`
currently construct. `ProvenanceRef.model_config = {"frozen": True, "extra":
"forbid"}` (verified live) — constructing it with a `ContentHashRef`-shaped
dict raises `pydantic.ValidationError` (`extra_forbidden` on all three
input keys). Grepped (this plan, live): zero call sites anywhere in `src/`
or `tests/` pass `last_known_content_hash_sha256=`.

**Decision (per spec.md, executed here)**: drop
`last_known_content_hash_sha256`/`last_known_size_bytes` and the
`ContentHashRef`-construction branch (`events.py:476-481`) from
`emit_artifact_missing` entirely. **If this stops being dormant** — a future
caller passes either removed parameter name — Python's own call-binding
raises `TypeError: emit_artifact_missing() got an unexpected keyword
argument 'last_known_content_hash_sha256'` immediately at the call site,
visible and uncatchable-by-accident (though still subject to a broad
`except Exception` at the *caller's* call site if one exists, same caveat
as FR-004). `mypy --strict` would also flag this statically but is CI's
`[INFO]`-labeled advisory step only (`continue-on-error: true`,
`ci-quality.yml:901-908`, confirmed live during this planning phase) — it is
NOT the enforced mechanism. **The enforced mechanism this mission adds**:
a regression test asserting `inspect.signature(emit_artifact_missing)` has
no `VAR_KEYWORD` parameter kind (mirrors SC-002's identical check and
FR-008's AST-guard pattern), running inside the enforced pytest CI jobs —
see "Red-First / ATDD Test Mapping" below.

### FR-008 guard test design

Modeled directly on this repo's own established AST-guard idiom
(`tests/architectural/test_shared_package_boundary.py`'s
`_forbidden_imports()` + planted-violation positive control, and
`tests/architectural/test_guard_capability_call_sites.py`'s per-symbol
allowlist pattern) — new file
`tests/architectural/test_dossier_emitter_positional_guard.py`:

1. A detector function walks `ast.parse()` over every `*.py` file under
   `src/` (using the same `_PRODUCTION_ROOTS`-style scoping as
   `test_shared_package_boundary.py`), finds `ast.Call` nodes whose `func`
   resolves (by simple name match — these are module-level functions, not
   methods, so no attribute-chain resolution is needed) to one of
   `emit_artifact_indexed`, `emit_artifact_missing`,
   `emit_snapshot_computed`, `emit_parity_drift_detected`, and flags any
   such call whose `node.args` (positional arguments) is non-empty.
2. **Clean-tree assertion**: run the detector against the real `src/` tree
   — expect zero violations. Verified during this planning phase (read
   `dossier_pipeline.py:101,126,175,230` and `drift_detector.py:419`
   directly): all 5 real call sites in `src/` are already 100%
   keyword-argument. This assertion is expected to pass on day one and stay
   passing through this mission's own changes (FR-004's parameter promotion
   does not turn any existing keyword call into a positional one).
3. **Positive control (self-mutation, per charter "a gate-unmask cannot
   self-validate")**: write a throwaway fixture file into `tmp_path`
   containing a planted positional call, e.g.
   `emit_artifact_indexed("m", "k", "c", "p", "h", 1)` (six bare positional
   arguments, matching spec.md's Acceptance Scenario), run the same detector
   against *that* fixture, and assert it reports exactly one violation. This
   is the proof the detector actually fires rather than vacuously passing
   because nothing in `src/` happens to trip it — mirrors
   `test_shared_package_boundary.py`'s `planted.py`/`clean.py` pair
   structure exactly.
4. **Red-first proof this guard is load-bearing** (spec.md Acceptance
   Scenario 3): reverting/gutting the detector to always return "no
   violations" must make at least one test in this new file fail — the
   positive-control assertion in step 3 *is* that test; no additional
   scaffolding needed beyond it.

### Baseline Red Policy (binding requirement of this mission's dispatch brief)

Before treating any test failure encountered during implementation as
pre-existing: `main` (and this mission's branch, forked from a recent
`main`) carries 23 known-red tests + 2 errors per issue #3284, and issue
#3283 documents a shared test-venv lock that can time out (an environment
symptom, not a code defect). This mission's concrete baselining procedure:

1. **Before the first functional change lands** (i.e., as the first action
   of implementation, before any WP's code edit), run the mission's full
   targeted test surface — `tests/dossier/`,
   `tests/sync/test_events_namespace.py`,
   `tests/sync/test_dossier_pipeline.py`, `tests/architectural/` — against
   the pre-mission commit (this branch's current HEAD, which has no
   functional changes yet) and record the exact red/error set (test IDs,
   not just counts).
2. Cross-reference that recorded set against issue #3284's known 23+2. Any
   test red in step 1 that is **not** in #3284's set is new information
   discovered by this mission, not caused by it — per the charter's
   Pre-existing Failure Reporting Rule, this requires opening a **new**
   GitHub issue (command run, failure summary, and why it's judged
   pre-existing rather than mission-introduced) before continuing, not a
   silent shrug or a silent "known baseline" assumption.
3. **After each phase's commit** (see Phasing below), re-run the same
   targeted surface and diff against the step-1 baseline. Only newly-red
   tests **beyond** the recorded baseline are this mission's own regressions
   to fix before proceeding to the next phase.
4. This baselining step itself is evidence to append to
   `tracer-tooling-friction.md` (actual baseline test IDs / counts observed)
   during implementation, per the mission tracer files' "append during
   implementation" contract.

### Gate Set (binding requirement of this mission's dispatch brief)

Selected from the actually-enforced CI gate table given in this mission's
dispatch brief — **no other table used**:

| Gate | Applies to this mission? | Why |
|---|---|---|
| Commit message linting (commitlint) | **Yes** — every commit | Applies unconditionally to every commit this mission makes. |
| Markdown style lint | **Yes** — for tracer-file/plan.md edits only | This mission edits `.md` planning artifacts (this plan, tracer files); no other `.md` (docs, changelog prose) is touched by the functional WPs. |
| Architecture/docs consistency tests | **Yes** | `tests/architectural/` is directly in this mission's touched-test set (new guard test + `test_shared_package_boundary.py` verification), and the plan itself documents an architecture decision (the Shared Package Boundary closure). |
| Template/compat regression tests | **No** | No template path (`packs/built-in/`), agent-directory, or upgrade-migration file is touched by this mission. |
| Generated doctrine schemas up to date | **No** | Confirmed above ("Generated Artifacts") — no schema source is touched; the schemas this mission reads live inside the external `spec-kitty-events` package. |
| Contextive glossary files up to date | **No** | No new/renamed domain term is introduced; existing vocabulary (`namespace`, `artifact_id`, `validate_event`, etc.) is reused as-is from the already-canonical external package. |
| Banned-API lint gate (TID251) | **Yes** — always | Applies unconditionally. |
| Typer 0.26 JSON error surface | **No** | No CLI command / Typer surface is touched by this mission (see "Seam Identification" — no `typer.Option` changes). Included in the enforced-gate CI run regardless (repo-wide), but this mission's diff cannot regress it. |
| `patch()` target string validation | **Yes** | `tests/sync/test_dossier_pipeline.py`'s existing (and this mission's new) tests use `@patch("specify_cli.dossier.events.emit_artifact_indexed")`-style string targets; this gate validates those strings resolve. |
| Bandit security scan + pip-audit CVE scan | **Yes** — always | Applies unconditionally; no new dependency is added (NFR-001) so no new CVE surface is expected, but the scan still runs. |
| `uv.lock` up to date with `pyproject.toml` | **No** | NFR-001 — no dependency change, so `pyproject.toml` is untouched and `uv.lock` needs no update. Still verified as a no-op check, not skipped. |
| Test shards with coverage — **corrected (plan-review remediation, closes PLAN-VERIFY-001)** | **Yes** — always | Applies unconditionally, but the shard names and coverage-floor claim in an earlier draft of this row ("fast-doctrine", "slow") named jobs that do not exist for this mission's surface — re-verified live against `.github/workflows/ci-quality.yml`. Actual routing: `tests/dossier/**` and `tests/architectural/**` share the same "misc" path-filter group (`ci-quality.yml:353`, `:376`) and are collected by `integration-tests-core-misc`'s `misc` shard (job at `:1863`, paths list at `:1953`); `tests/architectural/**` is *also* always-on-collected by the separate `arch-adversarial` 3-shard job (`:2034-2067`); `tests/sync/**` (including the new `tests/sync/test_diagnose.py` regression test) routes to `fast-tests-sync`/`integration-tests-sync`/`integration-tests-sync-real-port` (`:1105`, `:2451`, `:2490`). **None of these four jobs carries a `--cov-fail-under` floor** (verified: no such flag appears in any of their pytest invocations) — they only upload a coverage XML artifact consumed by SonarCloud's separate, project-wide new-code-coverage Quality Gate (its own row below), which is a materially weaker guarantee than a per-shard pytest floor. The only jobs in this repo with an actual `--cov-fail-under` threshold are `kernel-tests`/`mission-loader-coverage` (90%, `:1456`), `fast-tests-charter` (55%, `:2309`), and `fast-tests-agent` (10%) — none of which collect this mission's touched tests; no kernel-package (`src/kernel/`) code is touched by this mission's diff either way, so the 90% kernel floor remains unaffected but also does not protect this mission's own new tests. |
| Mission loader coverage gate (≥90%) | **No** | No mission-loader code (`src/specify_cli/missions/` loader machinery) is touched. |
| SonarCloud Scan + Quality Gate | **Yes** — always | Applies unconditionally; this mission's own diff should not introduce new Sonar findings (Sonar Expectations in `CLAUDE.md` apply — complexity ceiling 15, no repeated literals, no empty except handlers — the new `_validate_dossier_payload` helper and guard-test detector are written with this in mind). |
| `clean-install-verification` (protect-main.yml required check) | **Yes** — always | Required check named by `protect-main.yml`; applies unconditionally to any PR against `main`. |

**Explicitly NOT enforced gates, not to be cited as blocking**: `make lint`
(ruff) and `mypy --strict` in CI are `[INFO]` **advisory only**
(`continue-on-error: true`, confirmed live at `ci-quality.yml:901-908` for
mypy during this planning phase). This plan does not claim either as an
enforced gate — this is the exact misstatement spec.md's own round-2 fix
already had to correct once (see spec.md FR-005's own callout); this plan
does not regress it. (Both are still run locally/pre-push per repo
convention as *good practice*, just not as a CI merge gate.)

### Campsite-Clean Scope (binding requirement of this mission's dispatch brief)

**Conclusion: no separate campsite-clean step is needed.** This mission IS
itself a cleanup mission, and its own FR-001 through FR-010 already cover
the domain-matched debt on the touched surface:

- The local Pydantic mirror (the primary debt item) is FR-001/FR-002 — the
  mission's core functional work, not a preceding tidy step.
- The legacy `*args`/`**kwargs` bridge is FR-003/FR-004 — likewise core
  functional work.
- The dead `last_known_*` parameters are FR-005 — core functional work.
- The hand-maintained `_PAYLOAD_RULES` dossier entries are FR-006/FR-007 —
  core functional work.

Read through both touched files end-to-end during this planning phase
looking for *other*, unrelated debt (Sonar-flagged complexity, duplicated
literals, dead branches) in the specific functions this mission touches —
found none beyond what FR-001..FR-010 already targets. `_snapshot_legacy_diagnostics`
and `emit_snapshot_computed`/`emit_parity_drift_detected` (the two emitters
with no bridge) are explicitly out of scope per spec.md Clarifications and
were not found to carry any separate opportunistic-cleanup candidate either
— they are left untouched, matching Locality of Change (`DIRECTIVE_024`).
Splitting a preceding "campsite" commit out of FR-001..FR-010 here would
create artificial diff churn (touching the same lines twice across two
commits) with no behavior-preserving tidy-up left to front-load — so the
honest answer, per Standing Order #2's own framing, is that this mission's
functional scope *is* the campsite-clean scope; see Phasing below for how
the commits are still sliced for reviewability (by FR-cluster, not by
tidy-vs-functional).

### Tracer Files

Already seeded at spec phase (`tracer-approach.md`, `tracer-design-decisions.md`,
`tracer-tooling-friction.md`) — **not recreated**. This plan phase appended:
the `spec-kitty plan --json` scaffold's own non-fatal event-routing warnings
and this planning session's git-worktree-isolation friction (both real
tooling friction encountered while producing this plan) to
`tracer-tooling-friction.md`, and this document's own FR-006/FR-007
sentinel-shape decision is cross-referenced there rather than duplicated.
During implementation, each WP appends: tooling friction as hit (e.g. any
surprise in running the targeted pytest surface, `safe-commit` behavior per
WP commit), and design decisions as made (e.g. the exact `ast.Call`
detection helper shape if it differs from this plan's sketch, any
adjustment to the sentinel's concrete identifier name). At mission close,
the tracer files are assessed per Standing Order #3's "assess at close"
step (handled by the review/close phase, not this plan).

### PR Shape

**Estimated diff size** (rough LOC, counting adds + deletes across the
touched surface identified above):

| File | Estimated LOC changed |
|---|---|
| `src/specify_cli/dossier/events.py` | ~180 (delete ~140 lines of mirror classes + `_consume_legacy_values`; ~40 lines of signature/import changes across both bridged emitters) |
| `src/specify_cli/sync/emitter.py` | ~100 (delete ~70 lines of 4 hand-maintained dict entries; add ~50 lines: sentinel, `_DOSSIER_EVENT_TYPES`, `is_dossier_delegate()`, `_validate_dossier_payload`, branch in `_validate_payload`, corrected `_PAYLOAD_RULES` type annotation) |
| `src/specify_cli/sync/diagnose.py` (FR-011; plan-review remediation, closes PLAN-ARCH-001) | ~15 (import `is_dossier_delegate`; early-return branch in `diagnose.py::_validate_payload` mirroring `emitter.py`'s branch, folding `ConformanceResult` violations into the existing `errors` accumulator) |
| `tests/dossier/test_events.py` | ~10 (import re-point only, FR-009) |
| `tests/sync/test_events.py` (FR-006/FR-007; tasks-review remediation, closes TASKS-DECOMP-001) | ~30-50 (new SC-005 invalid-dossier-payload test against `EventEmitter._validate_payload()`, plus a small FR-007 `VALID_EVENT_TYPES` membership regression, per WP02/T012) |
| `tests/sync/test_dossier_pipeline.py` | ~80-120 (new FR-004 regression test(s): a real, unmocked end-to-end test asserting AC1/AC2 payload/behavior content, plus an optional supplementary `autospec=True` test) |
| `tests/dossier/test_snapshot_emit.py` (plan-review remediation, closes PLAN-ARCH-002) | ~15 (rewrite `test_emit_rule_wires_canonical_validator_for_hash_fields` to assert against the `ConformanceResult` delegation behavior instead of subscripting `_PAYLOAD_RULES[...]["validators"]` directly) |
| `tests/sync/test_diagnose.py` (FR-011; plan-review remediation, closes PLAN-ARCH-001's coverage gap) | ~40-60 (new regression test(s) driving a dossier event, valid and invalid payload, through `diagnose_events()`) |
| `tests/architectural/test_dossier_emitter_positional_guard.py` (new) | ~150-200 (detector + clean-tree assertion + positive-control fixture + docstring) |
| `tests/dossier/test_emitter_adapter.py`, `tests/sync/test_events_namespace.py` | 0 (verified no change needed, FR-009) |

**Total estimate: roughly 620-750 LOC changed across 9 files with a real
diff** (recomputed directly from the table's own per-file row ranges above —
summing each row's low end gives ~620, summing each row's high end gives
~750) (3 source files — `events.py`, `emitter.py`, `diagnose.py` — plus 6
test files touched, including 1 brand-new file,
`test_dossier_emitter_positional_guard.py`; 2 further test files verified
to need zero changes). This still fits comfortably in **one PR, reviewable
in a single sitting** — the default one-PR-per-mission shape for
spec-kitty. Recommendation only (per the collaboration model, the
orchestrator/operator makes the final call, not this plan unilaterally):
**do not split this PR.** The changes are tightly coupled (mirror deletion
and bridge removal touch the same ~150 contiguous lines of `events.py`;
the sentinel and its consuming branch are two halves of one mechanism in
`emitter.py`) — splitting would create intermediate commits/PRs that are
either not independently green (mirror half-deleted while bridge still
references it) or artificially reordered in a way that obscures the
FR-006/FR-007 reconciliation's single coherent story. Sequential WP commits
within the one PR (see Phasing) already give reviewers bite-sized,
independently-diffable units without the overhead of multiple PRs for a
~620-750 LOC mission.

---

## Phasing

Architecture-level phase/work-package sequencing (tasks.md's WP breakdown,
produced by the next phase, will refine this into concrete WP files —
this section states the *dependencies*, not the final WP numbering).

1. **Phase 0 — Baseline.** Run the targeted test surface against the
   pre-change commit; record the red/error set; cross-reference against
   issue #3284; file a new issue for any surplus red found (see "Baseline
   Red Policy"). No code change in this phase — establishes the
   before-picture every later phase's regression check diffs against.
   *No preceding campsite-clean step follows this phase* — per "Campsite-
   Clean Scope" above, there is none distinct from the phases below.

2. **Phase 1 — FR-001/FR-002: mirror deletion + `Literal` remap.** Delete
   `LocalNamespaceTuple`, `ArtifactIdentity`, `ContentHashRef`, and the four
   `MissionDossier*Payload` classes from `dossier/events.py`; import their
   canonical equivalents from `spec_kitty_events`; confirm
   `_normalize_artifact_class`/`_LEGACY_ARTIFACT_CLASS_MAP` still runs ahead
   of every `ArtifactIdentity(...)` construction site so legacy
   `artifact_class="other"` inputs remap to `"runtime"` before hitting the
   now-`Literal`-constrained canonical field (no behavior change — this
   remap already runs today; only the type it feeds changes). This phase
   *must* happen in the same commit as (or strictly before, on the same
   file) any signature change in Phase 2, since both edit the same emitter
   function bodies — sequencing them as adjacent phases within one file
   avoids a broken intermediate state.

3. **Phase 2 — FR-003/FR-004/FR-005: bridge removal + kwarg promotion +
   `last_known_ref` drop.** Delete `_consume_legacy_values` and the
   `*args`/`**kwargs` parameters from `emit_artifact_indexed` and
   `emit_artifact_missing`; promote `wp_id`/`step_id`/`required_status` and
   `reason_detail`/`blocking` to explicit keyword-only parameters with their
   current defaults (see "FR-004 raise/report/refuse contract" above); drop
   `last_known_content_hash_sha256`/`last_known_size_bytes` and the
   `ContentHashRef`-construction branch from `emit_artifact_missing` (FR-005).
   Depends on Phase 1 (same functions, same file, and FR-005's rationale
   depends on the canonical `ProvenanceRef` type already being in scope from
   Phase 1's import). `emit_snapshot_computed`/`emit_parity_drift_detected`
   and `_snapshot_legacy_diagnostics` are untouched in this phase (per
   spec.md Clarifications — they never had the bridge).

4. **Phase 3 — FR-006/FR-007: `validate_event` delegation with sentinel
   reconciliation, plus its full coordinated blast radius (plan-review
   remediation folds PLAN-ARCH-001/002/003 into this single phase).** In
   `sync/emitter.py`: add the sentinel, add `is_dossier_delegate()`, add
   the 4 dossier entries pointing at the sentinel, add
   `_validate_dossier_payload`, add the early-return branch in
   `_validate_payload` (now calling `is_dossier_delegate(rules)` rather
   than a raw `is` comparison, per round-2 remediation closing
   PLAN-FRESH-002), and correct `_PAYLOAD_RULES`'s type annotation to
   `dict[str, dict[str, Any] | object]` (closes PLAN-ARCH-003) (see
   "FR-006/FR-007 sentinel shape" above). **In the same commit** — not a
   follow-up phase, since an intermediate commit that lands the sentinel
   alone would leave `diagnose.py` crashing on any dossier event and
   `test_snapshot_emit.py` red: update
   `src/specify_cli/sync/diagnose.py::_validate_payload` to call the same
   `is_dossier_delegate()` predicate before any dict-shaped access and
   delegate to `validate_event()` (FR-011; closes PLAN-ARCH-001); add the
   new dossier-event regression test(s) to `tests/sync/test_diagnose.py`
   (FR-011); and rewrite
   `tests/dossier/test_snapshot_emit.py::test_emit_rule_wires_canonical_validator_for_hash_fields`
   to assert against the `ConformanceResult` delegation behavior instead of
   a specific validator-callable wiring (closes PLAN-ARCH-002). Independent
   of Phases 1-2 (different files, no shared symbols) — could in principle
   run in parallel, but sequenced after Phase 2 in one PR for a simpler
   linear reviewable commit history (charter §Code Quality "Linear" PR
   requirement) and because Phase 5's guard test benefits from both emitter
   signatures and the validation delegation being final before it asserts
   against the real tree.

5. **Phase 4 — FR-008: guard test.** Add
   `tests/architectural/test_dossier_emitter_positional_guard.py` (detector +
   clean-tree assertion + positive-control fixture). Depends on Phases 1-3
   only in the sense that it asserts against their *result* (zero positional
   call sites in the final `src/` tree) — technically could be written
   first as a red-first ATDD test *before* Phases 1-3 land, since the real
   call sites are already 100% keyword today (verified) and this guard's
   clean-tree assertion would already pass pre-mission. Recommendation:
   write this test in Phase 4 anyway, after the emitter signature changes
   are final, so its positive-control fixture's planted call matches the
   *post-mission* signatures (avoids the fixture going stale if a parameter
   name changes later).

6. **Phase 5 — FR-009/FR-010: test import re-pointing.** Re-point
   `tests/dossier/test_events.py`'s 7 mirror-type imports to
   `spec_kitty_events` (FR-009); confirm
   `test_preserves_legacy_positional_order` (FR-010) needs literally zero
   edits and still passes (its regression coverage is `emit_snapshot_computed`'s
   never-bridged, never-touched-by-this-mission positional order). Depends
   on Phase 1 (the types must exist at the new import location before the
   test file can import them from there) — this is necessarily the last
   phase, since it validates the end-state of every prior phase.

Each phase's commit is followed by the Phase-0-established targeted-test-surface
re-run and baseline diff (see "Baseline Red Policy" step 3) before proceeding.

---

## Red-First / ATDD Test Mapping (charter C-011, binding per-change)

| FR | Test (name / description) | Fails when reverted because |
|---|---|---|
| FR-001 | `tests/dossier/test_events.py::TestWirePayloadModelsRejectExtras::test_extras_rejected` (post-FR-009 import re-point) + isinstance checks added to `TestEmitArtifactIndexed`/`TestEmitArtifactMissing` asserting the emitted payload's runtime type is the `spec_kitty_events`-owned class | Reverting FR-001 restores the local mirror classes; the imported-from-`spec_kitty_events` identity check fails because the payload would be an instance of the local mirror class, not the canonical one. |
| FR-002 | `tests/dossier/test_events.py::TestEmitArtifactIndexed::test_legacy_other_class_maps_to_runtime` (existing test, re-verified against the canonical `Literal`-typed `ArtifactIdentity`) | Reverting the pre-construction remap (while keeping the canonical `Literal` type) makes `ArtifactIdentity(artifact_class="other")` raise `pydantic.ValidationError` instead of the test's expected `artifact_class == "runtime"` outcome. |
| FR-003 | The FR-008 guard test's clean-tree assertion, plus a new/updated unit test asserting `inspect.signature(emit_artifact_indexed)`/`inspect.signature(emit_artifact_missing)` have no `VAR_POSITIONAL` parameter kind | Reverting FR-003 restores `*args: object`, which reintroduces a `VAR_POSITIONAL` parameter — the signature assertion goes red immediately, independent of any call-site behavior. |
| FR-004 | **Binding test bar (plan-review remediation, closes PLAN-VERIFY-002)**: (a) at least one **new, unmocked** test in `tests/sync/test_dossier_pipeline.py` (e.g. `test_emit_artifact_indexed_keyword_promotion_preserves_diagnostics` / `test_emit_artifact_missing_blocking_short_circuit_survives_bridge_removal`) calling the real `emit_artifact_indexed`/`emit_artifact_missing` end-to-end — via `_emit_artifact_events`/`sync_feature_dossier`, with only unrelated collaborators (e.g. `Indexer`, `ManifestRegistry`) mocked — asserting directly on the returned/fired payload's `context_diagnostics` (contains `artifact_key`, `required_status`) and `step_id` fields (AC1), and on the blocking-driven emit/no-emit outcome via `_emit_artifact_events`'s `events_emitted` return-value count or an equivalent captured-event assertion (AC2); (b) an **additional**, supplementary `autospec=True`/`spec=emit_artifact_indexed`/`spec=emit_artifact_missing` test MAY also pin the signature-binding property, but if used must assert on a try/except-surviving observable (`events_emitted` count or `mock_emit.call_args`), never merely that the outer call did not raise — NOT the existing plain-`MagicMock` `@patch` decorators, which were verified during this planning phase to accept any keyword and therefore would NOT go red on a reverted promotion | Reverting FR-004's parameter promotion (while FR-003 still deletes `**kwargs`) makes `dossier_pipeline.py`'s `step_id=`/`required_status=`/`blocking=` keyword calls raise `TypeError` at the real call boundary, caught and swallowed by `_emit_artifact_events`'s per-artifact `except Exception`. The real-call test in (a) goes red because the call never actually completed — `context_diagnostics`/`step_id` are never populated, or the blocking short-circuit's expected `events_emitted` count no longer matches — which is the only test shape that can observe AC1/AC2's in-function behavior, since an `autospec` mock alone replaces the function body those acceptance criteria live inside; if used, the supplementary `autospec=True` mock in (b) still enforces the real signature and raises the same `TypeError` through the mock, so it also goes red, but only because it asserts on `events_emitted`/`call_args`, not merely on "no exception propagated." |
| FR-005 | **New** test asserting `inspect.signature(emit_artifact_missing)` has no `VAR_KEYWORD` parameter kind, plus a direct call with only the surviving parameters | Reverting FR-005 (re-adding `last_known_content_hash_sha256`/`last_known_size_bytes` as explicit params, or re-adding `**kwargs`) either changes the signature shape the `inspect.signature` assertion checks, or (if `**kwargs` returns) fails the same `VAR_KEYWORD` assertion FR-003's sibling check performs. |
| FR-006 | **New** test driving a hand-constructed invalid dossier payload (e.g. missing `namespace`) through `EventEmitter._validate_payload()`, asserting it returns `False` **and** the captured warning text contains a real field/violation identifier sourced from `ConformanceResult` (not the old generic "field has invalid value" string) — this is SC-005 made concrete. **Plus (plan-review remediation, closes PLAN-ARCH-002)**: a rewrite of `tests/dossier/test_snapshot_emit.py::test_emit_rule_wires_canonical_validator_for_hash_fields` asserting the same delegation behavior instead of subscripting `_PAYLOAD_RULES[...]["validators"]` directly. (The `diagnose.py` coordinated fix and its regression test are FR-011's own row below, not FR-006's, as of the round-2 PLAN-FRESH-001 remediation.) | Reverting FR-006 (restoring the 4 hand-maintained dict entries) makes the warning text revert to the old generic format — the assertion on real-violation-detail content in the warning string fails; the rewritten `test_snapshot_emit.py` assertion also fails because the subscripted validator-callable wiring it now asserts against no longer exists. |
| FR-007 | **New** test (or extension of an existing `_validate_event`-level test) confirming all four dossier event-type strings are still members of `VALID_EVENT_TYPES` and that an unknown/typo'd event type is still rejected via the existing unknown-event-type branch, unaffected by the sentinel | Reverting FR-007 (e.g. accidentally dropping a dossier key from `_PAYLOAD_RULES` while doing FR-006) removes it from `VALID_EVENT_TYPES`, and the membership assertion fails. |
| FR-008 | The guard test's own positive-control assertion (planted 6-positional-argument call must be flagged) | Gutting the detector to always report "no violations" is precisely what the positive control exists to catch — it is the test's own red-first proof, not a separate revert scenario. |
| FR-009 | Collection-time failure of `tests/dossier/test_events.py` itself (an `ImportError` if the import re-point is reverted while FR-001 has already deleted the mirror classes) | Once FR-001 lands, reverting FR-009 alone (pointing imports back at `specify_cli.dossier.events`) makes the import statement fail at collection — the whole test file goes red as a collection error, which is maximally visible. |
| FR-010 | `tests/dossier/test_events.py::TestEmitSnapshotComputed::test_preserves_legacy_positional_order` (existing, unmodified) | This test already fails today if `emit_snapshot_computed`'s positional parameter order is disturbed (that is PR #1056's original regression coverage) — this mission's commitment is that nothing in Phases 1-5 touches that function's signature, so the test's continued passing (re-verified, not re-authored) is FR-010's own proof. |
| FR-011 (added round-2 remediation, closes PLAN-FRESH-001) | **New** test in `tests/sync/test_diagnose.py` driving a dossier-typed event (valid and invalid payload) through `diagnose_events()`, asserting (a) no crash and (b) the invalid case reports a real `ConformanceResult`-sourced violation in `DiagnoseResult.errors` | Reverting FR-011 (dropping the `is_dossier_delegate()`-guarded branch from `diagnose.py::_validate_payload` while FR-006's sentinel stays in `_PAYLOAD_RULES`) makes `diagnose.py::_validate_payload` once again treat the dossier keys as plain dicts — the test's "no crash" assertion catches the resulting uncaught `AttributeError: 'object' object has no attribute 'get'` this FR exists to prevent. |

---

## Complexity Tracking

*No Constitution/Charter Check violations were found above — this table is
intentionally empty of real entries, and that emptiness is itself the
Complexity Tracking gate's expected result for this mission.* Both touched
functions (`_validate_payload`, and the two bridged emitters after
promotion) are checked against the repo's Sonar complexity ceiling
(`ruff` `C901`/Sonar `S3776`, max-complexity 15, per `CLAUDE.md` §Sonar
Expectations) during implementation; no design decision above requires
exceeding it — `_validate_dossier_payload` is a small, single-purpose new
method (delegate + translate + format warning), and the promoted-parameter
emitter signatures do not add branching, only additional named parameters.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| *(none)* | — | — |

## Parallel Work Analysis

**Not applicable — this mission is a single sequential work stream, not
parallelized across multiple agents/developers.** The ~620-750 LOC estimate
(see "PR Shape", corrected by plan-review remediation to include
`diagnose.py` and its coordinated tests, and by tasks-review remediation to
include `tests/sync/test_events.py`) and the tight file-level coupling
between phases (Phase 1 and Phase 2 both edit the same ~150 contiguous
lines of `events.py`; Phase 3 is the only phase touching different files —
`emitter.py`, `diagnose.py`, and their coordinated tests, landing atomically
in one commit per "FR-006/FR-007 sentinel shape" above — and is still
sequenced serially per "Linear" PR history discipline) make this a poor
candidate for
parallel-agent decomposition — splitting it would create more merge/rebase
overhead than it would save. The Phasing section above is the complete
dependency graph; no "Wave 1 / Wave 2" parallel structure applies. tasks.md
(next phase) will materialize Phases 0-5 above as sequential work packages
with `dependencies` frontmatter encoding the same ordering (Phase N+1
depends on Phase N where stated above).
