# Mission Specification: Legacy Cleanup — Split Dossier Queue Migration

**Mission Branch**: `legacy-cleanup-split-dossier-queue-migration-01M0MGHB`
**Created**: 2026-08-22
**Status**: Draft
**Target Branch**: `refactor/dossier-emitters-canonical-only-1058`
**Mission Type**: software-dev
**Input**: GitHub issue [#1058](https://github.com/Priivacy-ai/spec-kitty/issues/1058) — "Legacy cleanup: split dossier queue migration from live emitter APIs"

## Clarifications

The issue text and the mission's dispatch brief both contain claims that do not match
the current code. Every claim below was independently re-verified by reading the cited
files/lines during specification (2026-08-22), not merely copied from either source.
These are binding operator decisions and verified facts; planning and implementation
MUST treat them as settled, not re-litigate them.

### Session 2026-08-22

- **Q: Issue #1058's plan step 1 targets a queue-drain migration transform in
  `sync/queue.py`. Is that code still there?**
  **A: No — it is gone, superseded by mission #3293.** `_migrate_legacy_dossier_payload`
  has zero hits anywhere in `src/` or `tests/` (grepped). `drain_queue()`
  (`src/specify_cli/sync/queue.py:455-476`) is a plain read/decode of rows already in
  the append-only event journal — it performs no payload transform of any kind, legacy
  or otherwise. The fail-loud gate that now stands in its place,
  `LegacyQueueMigrationRequiredError` (class defined `sync/queue.py:44`), is raised at
  four sites — `default_queue_db_path` (line 247), `resolved_scope_db_path` (line 252),
  `detect_legacy_rows_for_scope` (line 257), `pending_events_for_scope` (line 262) —
  each of which refuses outright rather than silently degrading. The real replacement
  for issue #1058's queue-side intent is `src/specify_cli/sync/migrate_journal.py`
  (980 lines, present and current), which already does the "lift legacy queued rows
  into a clearly named, tested migration module" job the issue asked for.
  **Decision: the queue-drain half of #1058 is OUT OF SCOPE for this mission.** It is
  not implemented here because there is nothing left to split — #3293 already did the
  split, and did it as a wholesale replacement rather than a rename. This mission's PR
  description will close that half of #1058 as superseded-by-#3293 rather than claim to
  implement it. **Do not** add work against `migrate_journal.py`.

- **Q: Which function name is the "legacy positional/keyword compatibility parser"
  issue #1058 calls out?**
  **A: Not `_coerce_legacy_positional_args` — that name does not exist anywhere in this
  repository (grepped, zero hits).** The real symbol, verified by reading
  `src/specify_cli/dossier/events.py`, is `_consume_legacy_values(args, kwargs, *,
  names, defaults)` at lines 288-306. The issue text is imprecise here; use the real
  name in plan/tasks/code.

- **Q: The dispatch brief states all four public dossier emitters
  (`emit_artifact_indexed`, `emit_artifact_missing`, `emit_snapshot_computed`,
  `emit_parity_drift_detected`) carry `*args: object` / `**kwargs: Any` for legacy
  compatibility. Is that accurate?**
  **A: No — only two of the four do.** Verified by reading each signature in
  `src/specify_cli/dossier/events.py`:
  - `emit_artifact_indexed` (lines 340-357) and `emit_artifact_missing` (lines
    424-442) both declare `*args: object, ... **kwargs: Any` and route through
    `_consume_legacy_values`.
  - `emit_snapshot_computed` (lines 506-526) and `emit_parity_drift_detected` (lines
    577-594) declare **no** `*args`/`**kwargs` at all — they take a fixed list of
    positional-or-keyword parameters followed by a bare `*` that makes the remainder
    keyword-only. There is no legacy-argument bridge to remove from these two
    functions; item 2 below (the `*args`/`**kwargs` deletion) applies only to
    `emit_artifact_indexed` and `emit_artifact_missing`.
  - `emit_snapshot_computed` does call a helper named `_snapshot_legacy_diagnostics`
    (lines 317-334), but that helper is not an argument-shape compatibility parser —
    it folds the legacy flat-envelope's `required_artifacts`/`required_present`/
    `optional_artifacts`/`optional_present` counts into the canonical
    `context_diagnostics` free-form dict, because the canonical
    `MissionDossierSnapshotComputedPayload` schema has no top-level fields for them.
    This is intentional, current, in-scope canonical behaviour (the schema's
    documented way of not losing that data), not a legacy-positional bridge. **This
    mission does not remove `_snapshot_legacy_diagnostics`.**

- **Q: Deleting `_consume_legacy_values` and the `*args`/`**kwargs` bridge from
  `emit_artifact_indexed` / `emit_artifact_missing` — is that pure dead-code removal?**
  **A: No — it would break a live, production, in-repo call site if done naively.**
  Verified: `src/specify_cli/sync/dossier_pipeline.py` calls
  `emit_artifact_indexed(..., step_id=step_id, required_status=artifact.required_status,
  ...)` (lines 101-114) and `emit_artifact_missing(..., blocking=artifact.required_status
  == "required", ...)` (lines 126-137). `step_id`, `required_status`, and `blocking` are
  **not** explicit parameters of the current signatures — they are keyword arguments
  that land in `**kwargs` and are consumed by `_consume_legacy_values`. Deleting the
  bridge without promoting these three names to explicit, first-class keyword-only
  parameters would make every one of these calls raise `TypeError: unexpected keyword
  argument`, and `dossier_pipeline.py` wraps each call in a broad `except Exception as e:
  logger.warning(...)` — so the break would present as a silently swallowed warning log,
  not a visible failure. This is exactly the "silent success" failure mode the charter
  singles out as this repo's dominant defect class. **Decision: FR-004 requires
  promoting `wp_id`, `step_id`, `required_status` (defaults `None`, `None`, `"optional"`)
  and `reason_detail`, `blocking` (defaults `None`, `True`) to explicit keyword-only
  parameters as part of removing the bridge — not merely deleting `*args`/`**kwargs`.**

- **Q: Can the canonical `MissionDossierArtifactMissingPayload.last_known_ref` field
  hold the same content-hash data the local mirror's `ContentHashRef`-typed
  `last_known_ref` held?**
  **A: No — the canonical field is a different, incompatible type.** Verified via
  `spec_kitty_events` 6.1.0 model introspection: canonical
  `MissionDossierArtifactMissingPayload.last_known_ref` is typed
  `Optional[ProvenanceRef]`, and `ProvenanceRef` (`spec_kitty_events.dossier`) has
  fields `source_event_ids`, `git_sha`, `git_ref`, `actor_id`, `actor_kind`,
  `revised_at` — no `algorithm`/`hash`/`size_bytes`/`encoding`. `ProvenanceRef`'s
  `model_config` is `{"frozen": True, "extra": "forbid"}`; constructing it with a
  `ContentHashRef`-shaped dict (`algorithm=...`, `hash=...`, `size_bytes=...`) raises
  `pydantic.ValidationError` (`extra_forbidden` on all three fields — reproduced
  directly against the installed package). **Currently dormant**: grepped every call
  site of `emit_artifact_missing` across `src/` and `tests/` — none passes
  `last_known_content_hash_sha256=`, so the local mirror's `last_known` branch
  (`events.py:476-481`) never actually executes today. **Decision: drop the
  `last_known_content_hash_sha256` / `last_known_size_bytes` parameters and the
  `ContentHashRef`-construction branch from `emit_artifact_missing` entirely** rather
  than attempt to map them onto the incompatible canonical field — there is no live
  caller to preserve, and forcing a hash value into `ProvenanceRef` would raise. If a
  future need for "last known content hash on a missing artifact" surfaces, that is an
  upstream `spec-kitty-events` schema question (the field name `last_known_ref` reads
  as if it should carry a content reference), not something to route around locally in
  this CLI.

- **Q: Does `spec_kitty_events.conformance.validate_event(payload, event_type,
  strict=True)` raise on an invalid payload?**
  **A: No.** Read `spec_kitty_events/conformance/validators.py` directly (installed
  6.1.0). `validate_event()` returns a `ConformanceResult` dataclass with a `.valid:
  bool` field plus `.model_violations` / `.schema_violations` tuples describing any
  problems. Per its own docstring, it raises only `ValueError` for an unrecognized
  `event_type` string, or `ImportError` if `strict=True` and the `jsonschema` package is
  unavailable (neither applies to the four dossier event types, which are registered in
  `_EVENT_TYPE_TO_MODEL` / `_EVENT_TYPE_TO_SCHEMA`, and `jsonschema` is a direct
  dependency here). **This corrects an assumption in the mission's dispatch brief.**
  **Decision:** `_validate_payload` (`src/specify_cli/sync/emitter.py:2549`) keeps its
  existing `bool`-return, warn-and-discard contract for the dossier event types — the
  same contract every other entry in `_PAYLOAD_RULES` already has (verified by reading
  `_validate_event`/`_validate_payload`, lines 2469-2572: both call sites of
  `_validate_event` treat a `False` return as "warn and drop this event", never as a
  raise). The dossier `_PAYLOAD_RULES` entries call `validate_event(payload, event_type,
  strict=True)` and translate `.valid` into the existing `True`/`False` return, printing
  `.model_violations` / `.schema_violations` in the warning message instead of the
  current opaque "field has invalid value" message. Making dossier validation raise
  while every sibling event type in the same dict silently warns-and-discards would be
  an inconsistent, unscoped widening of this mission's diff (see `RECONCILE_CHANGE_
  SCOPE_TENSIONS` / `change-apply-smallest-viable-diff` / `DIRECTIVE_024` Locality of
  Change in the charter) — extending fail-loud semantics to the whole `_PAYLOAD_RULES`
  surface is a separate, larger mission if wanted.

- **Q: Why did the 24KB local Pydantic mirror in `dossier/events.py` survive the
  existing shared-package-boundary gate (`tests/architectural/
  test_shared_package_boundary.py`) and the `clean-install-verification` CI job?**
  **A: The gate detects forbidden imports of vendored/retired package names
  (`spec_kitty_runtime`, `specify_cli.spec_kitty_events`), not hand-authored types that
  independently duplicate an external package's shapes.** Read
  `test_shared_package_boundary.py` in full: `_forbidden_imports()` walks the AST for
  `ast.Import`/`ast.ImportFrom` nodes matching a banned module prefix; there is no
  structural-similarity or shape-mirroring check. `dossier/events.py`'s six local
  classes (`LocalNamespaceTuple`, `ArtifactIdentity`, `ContentHashRef`, and the four
  `MissionDossier*Payload` classes, lines 70-209, ~5KB of the file's total 24,210
  bytes / 653 lines) import nothing from `spec_kitty_events` — they are independently
  written Pydantic models with matching field names, so the import-based gate has
  nothing to flag. This is the concrete gap this mission's FR-001 closes; it is not a
  gate bug requiring a separate fix (a shape-similarity gate is a much broader,
  false-positive-prone detector and out of scope here).

- **Q: Should this mission wait for `spec-kitty-events#50` to merge before adopting
  `validate_event()`?**
  **A: No.** `pyproject.toml:80` already pins `spec-kitty-events>=6.0.0,<7.0.0`; the
  installed version is 6.1.0 (`spec_kitty_events.__version__`), which already exports
  `conformance.validate_event()` and all seven canonical dossier types used here.
  `spec-kitty-events#50` is an open, non-draft, unmerged PR (5/5 checks green,
  `reviewDecision` empty, per the operator's readiness probe) that adds fixture files
  exercising `manifest_step` `minLength: 1` and `artifact_count` `minimum: 0` — both
  constraints already present in the installed 6.1.0 JSON schemas (verified directly:
  `load_schema('mission_dossier_artifact_missing_payload')['properties']
  ['manifest_step']` shows `minLength: 1`; the Pydantic model shows `artifact_count:
  int = Field(..., ge=0)`). This mission writes its own regression tests against the
  already-installed `validate_event()` rather than gating on #50.

- **Q: Do all three test files named in the issue (`tests/dossier/test_events.py`,
  `tests/dossier/test_emitter_adapter.py`, `tests/sync/test_events_namespace.py`) need
  their imports re-pointed to `spec_kitty_events`?**
  **A: Only one of the three.** Read each file's import block: `test_events.py`
  (lines 23-35) imports all seven local mirror type names (`ArtifactIdentity`,
  `ContentHashRef`, `LocalNamespaceTuple`, and the four `MissionDossier*Payload`
  classes) plus the four `emit_*` functions from `specify_cli.dossier.events` — this
  one needs its type imports re-pointed to `spec_kitty_events` (FR-009).
  `test_emitter_adapter.py` (lines 1-27) imports only `emit_artifact_indexed` (plus
  adapter/store plumbing unrelated to the mirror) — no mirror type import exists to
  re-point. `test_events_namespace.py` (lines 1-13) imports only the four `emit_*`
  functions — likewise no mirror type import to re-point. Both files' existing imports
  remain correct as-is because the four `emit_*` functions keep living in
  `specify_cli.dossier.events` (only their internal sub-object types move to import
  from `spec_kitty_events`); no edit is required in either file for this reason
  (verify at implementation time that no other change in this mission incidentally
  requires touching them).

- **Q: Is there an existing regression test for the PR #1056 snapshot
  positional-order bug, and does it still apply after this mission?**
  **A: Yes, and it must be preserved unmodified.**
  `tests/dossier/test_events.py::TestEmitSnapshotComputed::test_
  preserves_legacy_positional_order` (lines 317-342) calls `emit_snapshot_computed`
  with ten purely positional arguments in the exact order PR #1056 regressed, and
  asserts the resulting payload's `artifact_count`, `anomaly_count`, and
  `context_diagnostics` land correctly. Because `emit_snapshot_computed` never had the
  `*args`/`**kwargs` bridge this mission removes (see above), its positional parameter
  order is untouched by this mission's changes, and this test's continued passing is
  this mission's live regression coverage for the #1056 bug (FR-010) — it is not being
  migrated or rewritten, only re-verified.

## Overview

PR #1056 (spec-kitty#1047's follow-up) fixed Sonar findings in the dossier event
migration but left a boundary smell: the four live dossier event emitters in
`src/specify_cli/dossier/events.py` still define their own ~5KB Pydantic mirror of
types that `spec-kitty-events` (an external contract package, per the charter's
"Architecture: Shared Package Boundaries" section) already owns and ships, two of
those emitters still carry a `*args`/`**kwargs` legacy-argument compatibility parser,
and `src/specify_cli/sync/emitter.py`'s payload-validation table
(`_PAYLOAD_RULES`) hand-maintains four dossier-event validation rules instead of
calling the canonical `spec_kitty_events.conformance.validate_event()` the package
already ships (installed 6.1.0). This mission closes that boundary gap:
canonicalizes the dossier emitters' internal types and validation, removes the two
emitters' legacy-argument bridge (while preserving the one live production behaviour
it currently carries — see Clarifications), and adds a construction-time guard so
this class of drift cannot silently regrow.

The companion queue-drain half of issue #1058 is confirmed superseded by mission
#3293 and is explicitly out of scope (see Clarifications).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dossier emitter payloads validate against the canonical contract, not a hand-copied mirror (Priority: P1)

As a spec-kitty maintainer, I want the four dossier event emitters
(`emit_artifact_indexed`, `emit_artifact_missing`, `emit_snapshot_computed`,
`emit_parity_drift_detected`) to build and validate their payloads using the
`spec_kitty_events` package's own types and `validate_event()` helper, so that a
future schema change in `spec-kitty-events` is caught by upgrading the pinned
dependency rather than by silently drifting from a local copy that nobody remembers
to update.

**Why this priority**: This is the mission's core deliverable and the charter's
strongest-cited violation (the local mirror is close to precisely what "Architecture:
Shared Package Boundaries" forbids — vendoring an external contract package's shapes).

**Independent Test**: Delete the local mirror classes from `dossier/events.py`, run
`tests/dossier/test_events.py` and `tests/sync/test_events_namespace.py`; they pass
using types imported from `spec_kitty_events`. Separately, corrupt a canonical
dossier payload (e.g. omit a required field) and drive it through
`EventEmitter._validate_payload()`; the event is rejected with a warning
that names the real violation, not a generic message.

**Acceptance Scenarios**:

1. **Given** `dossier/events.py` no longer defines `LocalNamespaceTuple`,
   `ArtifactIdentity`, `ContentHashRef`, or the four `MissionDossier*Payload` classes,
   **When** any of the four emitters is called with valid arguments, **Then** the
   emitted payload's runtime type is the `spec_kitty_events`-owned class (`isinstance`
   check against the imported canonical class succeeds), and the emitted wire payload
   still validates against the canonical JSON schema (`jsonschema.validate` against
   `spec_kitty_events.schemas.load_schema(...)`, as `tests/dossier/test_events.py`
   already does).
2. **Given** an `ArtifactIdentity` is built for a caller that passes the legacy
   `artifact_class="other"` value, **When** `emit_artifact_indexed` or
   `emit_artifact_missing` constructs the canonical (now `Literal`-constrained, no
   `"other"` member) `ArtifactIdentity`, **Then** the artifact still gets classified as
   `"runtime"` (the existing `_normalize_artifact_class` / `_LEGACY_ARTIFACT_CLASS_MAP`
   remap still runs before construction) rather than raising a `pydantic.
   ValidationError`.
3. **Given** `src/specify_cli/sync/emitter.py`'s `_PAYLOAD_RULES` dossier entries now
   delegate to `spec_kitty_events.conformance.validate_event(payload, event_type,
   strict=True)`, **When** a dossier payload is missing a required field (e.g.
   `manifest_step` for `MissionDossierArtifactMissing`), **Then**
   `_validate_payload()` returns `False` (as it does for every other event type
   today) and the printed warning includes the real violation detail from
   `ConformanceResult.model_violations` / `.schema_violations`, not merely "payload
   missing required fields: {...}" with no schema-level detail.
4. **Given** the FR-006 sentinel lands in `_PAYLOAD_RULES`, **When**
   `diagnose_events()` processes a dossier-typed event with a valid and an invalid
   payload, **Then** it does not crash and the invalid case's violation appears in
   `DiagnoseResult.errors` (FR-011).

---

### User Story 2 - Removing the legacy-argument bridge does not silently break the live production call sites (Priority: P1)

As a spec-kitty maintainer, I want `emit_artifact_indexed` and `emit_artifact_missing`
to drop their `*args`/`**kwargs` legacy-positional bridge (`_consume_legacy_values`)
while continuing to accept `wp_id`, `step_id`, `required_status` (indexed) and
`reason_detail`, `blocking` (missing) as first-class keyword-only parameters, so that
`src/specify_cli/sync/dossier_pipeline.py`'s existing keyword calls keep working
exactly as before instead of silently raising `TypeError` that gets swallowed by its
broad `except Exception` handlers.

**Why this priority**: This is the concrete, verified regression risk in the issue's
plan step 2 — the exact "silent success" failure mode the charter calls this repo's
dominant defect class. Getting it wrong ships a silent behaviour regression in a
sync path this repo actively depends on.

**Independent Test**: Run `sync/dossier_pipeline.py`'s artifact-indexing/missing path
end-to-end against a real dossier fixture (existing `tests/sync/test_dossier_pipeline.py`
coverage) after the bridge is removed; `wp_id`/`step_id`/`required_status`/`blocking`
still land in the emitted payload's `context_diagnostics` / gate the event's firing
exactly as before.

**Acceptance Scenarios**:

1. **Given** the `*args`/`**kwargs` bridge and `_consume_legacy_values` are removed
   from `emit_artifact_indexed`, **When** `dossier_pipeline.py` calls it with
   `step_id=step_id, required_status=artifact.required_status` as keyword arguments
   (as it does today, lines 108-109), **Then** the call succeeds (no `TypeError`) and
   the resulting payload's `context_diagnostics` still contains `artifact_key` and
   `required_status`, and `step_id` is still threaded into the payload's `step_id`
   field — this AC fails (regresses) if reverting FR-004's parameter promotion causes
   the call to raise, because that raise is caught by `dossier_pipeline.py`'s
   `except Exception` and silently logged as a warning with `events_emitted` staying
   unchanged, which a plain "does it crash" test would not catch.
2. **Given** the bridge and `_consume_legacy_values` are removed from
   `emit_artifact_missing`, **When** `dossier_pipeline.py` calls it with
   `blocking=artifact.required_status == "required"` (line 132), **Then** the call
   still returns `None` without emitting when `blocking` evaluates `False`, and still
   emits when `blocking` evaluates `True` — this AC fails if `blocking`'s
   short-circuit (`events.py:455-457`) stops being reachable because the keyword no
   longer binds to a real parameter.
3. **Given** `emit_artifact_missing` no longer accepts `last_known_content_hash_sha256`
   / `last_known_size_bytes` (dropped per Clarifications, since the canonical
   `last_known_ref: Optional[ProvenanceRef]` cannot represent a content hash),
   **When** the guard test (FR-008) or a new unit test calls `emit_artifact_missing`
   with only the parameters that survive, **Then** the call succeeds and no attempt is
   made anywhere in `src/` to pass the removed parameters (grep-verified zero call
   sites before this mission begins, and the guard/removal keeps it that way).

---

### User Story 3 - A construction-time guard prevents the positional-call pattern from regrowing (Priority: P2)

As a spec-kitty maintainer, I want an automated test that fails if any production code
calls `emit_artifact_indexed`, `emit_artifact_missing`, `emit_snapshot_computed`, or
`emit_parity_drift_detected` with a positional argument, so that the class of bug PR
#1056 had to patch around (positional-argument shape drift) cannot silently
reintroduce itself in a future edit.

**Why this priority**: Issue #1058 explicitly asks for this ("Add a guard test that
fails if production code calls dossier emitters positionally"); it is the mechanism
that makes User Story 2's fix durable rather than a one-time cleanup.

**Independent Test**: Plant a synthetic positional call to one of the four emitters in
a throwaway fixture file and confirm the guard's detector flags it (a "self-mutation"
positive control, per the charter's "a gate-unmask cannot self-validate" rule); then
confirm the guard passes clean against the real, unmodified `src/` tree.

**Acceptance Scenarios**:

1. **Given** the guard test exists and every real call site in `src/` (5 verified
   call sites: `sync/dossier_pipeline.py` lines 101, 126, 175, 230;
   `dossier/drift_detector.py` line 419) is already 100% keyword-argument, **When**
   the guard test runs against the current `src/` tree, **Then** it passes (reports
   zero violations).
2. **Given** a planted synthetic call such as `emit_artifact_indexed("m", "k", "c",
   "p", "h", 1)` (six bare positional arguments) is written into a throwaway fixture
   file inside the guard test itself, **When** the guard's detector is run against
   that fixture, **Then** it reports the planted call as a violation — this is the
   positive control proving the detector actually fires rather than vacuously passing
   because nothing in `src/` happens to trip it.
3. **Given** the guard is reverted (deleted or its detector logic gutted to always
   return "no violations"), **When** CI runs the full test suite, **Then** at least
   one test fails — this AC is the mission's own "red-first" proof that the guard
   test is load-bearing, not decorative.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | User Story | Priority | Status |
|----|-------|------------|----------|--------|
| FR-001 | Delete the local Pydantic mirror (`LocalNamespaceTuple`, `ArtifactIdentity`, `ContentHashRef`, `MissionDossierArtifactIndexedPayload`, `MissionDossierArtifactMissingPayload`, `MissionDossierSnapshotComputedPayload`, `MissionDossierParityDriftDetectedPayload`; `dossier/events.py:70-209`) and import the equivalents from `spec_kitty_events` (verified importable at package top level, 6.1.0). | As a maintainer, I want the CLI to consume the external contract package's own types instead of a hand-copied mirror, so a schema change there is caught by the dependency, not missed silently. | High | Open |
| FR-002 | Preserve the `_normalize_artifact_class` / `_LEGACY_ARTIFACT_CLASS_MAP` (`"other"` → `"runtime"`) remap ahead of constructing the now-`Literal`-typed canonical `ArtifactIdentity.artifact_class`, so legacy `"other"` inputs are still accepted rather than raising `ValidationError`. | As a maintainer, I want the canonicalization to not break existing callers that still pass `artifact_class="other"`. | High | Open |
| FR-003 | Delete `_consume_legacy_values` (`events.py:288-306`) and the `*args: object` / `**kwargs: Any` parameters from `emit_artifact_indexed` and `emit_artifact_missing` — the only two of the four emitters that carry this bridge (`emit_snapshot_computed` / `emit_parity_drift_detected` never had it; do not touch their signatures or `_snapshot_legacy_diagnostics`). | As a maintainer, I want the internal-only argument-shape parser gone so the emitter surface is canonical-only, matching issue #1058's explicit ask. | High | Open |
| FR-004 | Promote `wp_id`, `step_id`, `required_status` (defaults `None`, `None`, `"optional"`) to explicit keyword-only parameters of `emit_artifact_indexed`, and `reason_detail`, `blocking` (defaults `None`, `True`) to explicit keyword-only parameters of `emit_artifact_missing`, preserving current default values and current behaviour (diagnostics folding, the `blocking` short-circuit at `events.py:455-457`). The regression tests proving this (User Story 2, Acceptance Scenarios 1 and 2 — covering `emit_artifact_indexed` and `emit_artifact_missing` respectively) MUST call `sync_feature_dossier` (or the internal pipeline helper) without mocking `emit_artifact_indexed`/`emit_artifact_missing` with a plain (non-autospec) `Mock` — either exercise the real functions end-to-end, or, if mocking is retained for isolation, use `autospec=True` (or `spec=emit_artifact_indexed` / `spec=emit_artifact_missing`) so a removed/renamed keyword argument still raises `TypeError` through the mock; implementation and review must confirm both new tests actually go red if FR-004's parameter promotion is reverted locally. This non-mock/autospec bar applies to any test proving FR-004, not only the two scenarios named here. | As a maintainer, I want the one live production behaviour the legacy bridge currently carries (`dossier_pipeline.py` lines 101-114, 126-137) preserved exactly, so removing the bridge is not a silent regression. | High | Open |
| FR-005 | Drop the `last_known_content_hash_sha256` / `last_known_size_bytes` parameters and the `ContentHashRef`-construction branch (`events.py:476-481`) from `emit_artifact_missing`, since the canonical `MissionDossierArtifactMissingPayload.last_known_ref` field is typed `Optional[ProvenanceRef]` (incompatible with a content-hash shape) and no call site populates these parameters today. Any future caller passing these removed parameter names is rejected at call time with `TypeError: unexpected keyword argument` before it can reach `dossier_pipeline.py`'s broad `except Exception` wrapping — once `**kwargs` is removed, this is Python's own unconditional call-binding behaviour, not a tool-dependent check. `mypy --strict` would also flag such a call statically, but CI runs mypy as an advisory-only step (`[INFO] Run mypy report (advisory)`, `continue-on-error: true`, `.github/workflows/ci-quality.yml:902-908`) — it is not an enforced CI gate today, so it must not be cited as the mechanism keeping a re-introduction loud. The enforced mechanism this mission adds is a regression test asserting `inspect.signature(emit_artifact_missing)` has no `VAR_KEYWORD` parameter kind (mirroring SC-002's identical check for `emit_artifact_indexed`/`emit_artifact_missing` and FR-008's AST guard-test pattern) — this runs inside the enforced pytest CI jobs (unlike the advisory mypy step), so a future re-addition of `**kwargs` to `emit_artifact_missing` fails CI, not merely local `mypy --strict` discipline or code review. If this data need resurfaces, it must be threaded through as an explicit, typed, keyword-only parameter (never via a re-added `**kwargs`), consistent with FR-004's own promotion pattern. | As a maintainer, I want to not force an incompatible value into a canonical field just to preserve dead parameters. | Medium | Open |
| FR-006 | Replace the four hand-maintained dossier entries in `_PAYLOAD_RULES` (`emitter.py:827-876`) with a code path that calls `validate_event(payload, event_type, strict=True)`, imported as `from spec_kitty_events.conformance import validate_event`, as a local import inside `_validate_payload`'s dossier-delegation branch (`emitter.py:2549`) — matching this file's consistent lazy-import convention for every `spec_kitty_events` type it uses (e.g. `Event as EventModel` imported locally inside `_validate_event` at `emitter.py:2477`; there is no module-scope `spec_kitty_events` type import anywhere in `emitter.py` today, so this import has no existing module-scope sibling to sit "alongside"), translating `ConformanceResult.valid` into the existing `bool` return and surfacing `.model_violations` / `.schema_violations` in the printed warning. `_validate_payload` gains an explicit branch for the four dossier event types ahead of its existing generic `rules["required"]`/`rules["validators"]` access, so the two code paths never both try to interpret the same dict value the same way (concrete post-change shape: see Key Entities). | As a maintainer, I want dossier payload validation to use the canonical, dual-layer (Pydantic + JSON Schema) validator the package ships, instead of four hand-maintained lambda rules that can drift from the real schema. | High | Open |
| FR-007 | Keep the four dossier event-type strings as keys in `_PAYLOAD_RULES` / `VALID_EVENT_TYPES` so `_validate_event`'s unknown-event-type rejection check (`if event_type not in VALID_EVENT_TYPES:`, `emitter.py:2514`, block context `emitter.py:2513-2516`) is unaffected for dossier and every other event type. See Key Entities for how this is reconciled with FR-006's change to what a dossier `_PAYLOAD_RULES` value means. | As a maintainer, I want this change scoped to how dossier payloads are validated, not whether they are recognized at all. | Medium | Open |
| FR-008 | Add an AST-based guard test that fails if any production code (`src/`) calls `emit_artifact_indexed`, `emit_artifact_missing`, `emit_snapshot_computed`, or `emit_parity_drift_detected` with a positional argument, including a planted-violation positive control proving the detector actually fires (per the charter's "a gate-unmask cannot self-validate" rule). | As a maintainer, I want the class of bug PR #1056 patched around (positional-argument drift) to be closed by construction, not by convention. | High | Open |
| FR-009 | Re-point `tests/dossier/test_events.py`'s seven mirror-type imports (`ArtifactIdentity`, `ContentHashRef`, `LocalNamespaceTuple`, and the four `MissionDossier*Payload` classes; lines 23-30) to import from `spec_kitty_events` instead of `specify_cli.dossier.events`; leave the four `emit_*` function imports pointed at `specify_cli.dossier.events` unchanged. `tests/dossier/test_emitter_adapter.py` and `tests/sync/test_events_namespace.py` require no import changes (verified: neither imports any mirror type today). | As a maintainer, I want the test suite to import types from the same place production code now does, so a future drift between "what the test asserts against" and "what production builds" cannot recur. | Medium | Open |
| FR-010 | Preserve `tests/dossier/test_events.py::TestEmitSnapshotComputed::test_preserves_legacy_positional_order` (lines 317-342) unmodified as the live regression coverage for the PR #1056 snapshot positional-order bug. | As a maintainer, I want the #1056 regression to stay covered exactly because `emit_snapshot_computed`'s parameter order is untouched by this mission. | High | Open |
| FR-011 | Coordinate FR-006's `_PAYLOAD_RULES` sentinel change with `src/specify_cli/sync/diagnose.py::_validate_payload` — a second, independent free-function consumer of the same module-level `_PAYLOAD_RULES` dict (imported at `diagnose.py:51`, `from .emitter import _PAYLOAD_RULES, VALID_AGGREGATE_TYPES`), reached unconditionally from `diagnose_events()` (the entry point for the production `spec-kitty sync diagnose` CLI command) whenever `event_type in _PAYLOAD_RULES`. Without this coordination, FR-006's sentinel value breaks `diagnose.py::_validate_payload`'s unguarded `rules.get("required", set())` / `rules.get("validators", {})` calls (`diagnose.py:301-306`), raising an uncaught `AttributeError: 'object' object has no attribute 'get'` on any dossier event sitting in the local offline queue. `diagnose.py::_validate_payload` MUST recognize the FR-006 sentinel (via the same predicate FR-006's `emitter.py::_validate_payload` uses, so both consumers share one definition) before any dict-shaped access, and delegate to `spec_kitty_events.conformance.validate_event()` the same way `emitter.py` does, folding the resulting violations into `diagnose.py`'s existing `errors: list[str]` accumulator. A new regression test in `tests/sync/test_diagnose.py` (already an existing file; zero existing tests in it exercise a dossier event type today — grepped, zero `dossier` hits) MUST drive a dossier-typed event, both valid and invalid payload, through `diagnose_events()`, asserting (a) no crash and (b) the invalid case reports a real `ConformanceResult`-sourced violation in `DiagnoseResult.errors`. | As a maintainer, I want the FR-006 sentinel change to not silently crash the `spec-kitty sync diagnose` command's diagnostic path the first time it encounters a dossier event, since that command reads the exact same `_PAYLOAD_RULES` dict FR-006 changes the shape of. | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | No net-new external dependency | This mission adds no new PyPI dependency and does not change the `spec-kitty-events` version constraint (`pyproject.toml:80`, already `>=6.0.0,<7.0.0`, already satisfied by installed 6.1.0). | Technical | High | Open |
| NFR-002 | Validation failure stays visible, not silent | Scoped to `emitter.py::_validate_payload`: an invalid dossier payload reaching it after this mission still produces a printed `[yellow]Warning: ...` message identifying the event type and the real violation (from `ConformanceResult`), and the event is still dropped (not queued) — consistent with, not weaker than, today's behaviour for every other `_PAYLOAD_RULES` entry. `diagnose.py::_validate_payload` (FR-011) is a separate function with a different, equally binding visibility contract: it does not print a warning — it surfaces the violation by appending it to `DiagnoseResult.errors`, `diagnose.py`'s existing structured-error-reporting shape. Neither contract weakens or contradicts the other; each governs its own function. | Reliability | High | Open |
| NFR-003 | Test suite scope stays bounded | Per-WP validation targets `tests/dossier/`, `tests/sync/test_events_namespace.py`, `tests/sync/test_events.py`, `tests/sync/test_dossier_pipeline.py`, `tests/sync/test_diagnose.py` (FR-011's `diagnose.py` regression coverage), and `tests/architectural/` (for the new guard test and `test_shared_package_boundary.py`); the full `pytest tests/` run is reserved for pre-merge / post-merge validation per the charter's Testing Requirements section. | Process | Medium | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | Queue-drain half of #1058 is out of scope | No change is made to `src/specify_cli/sync/queue.py` or `src/specify_cli/sync/migrate_journal.py`; the mission PR closes that half of #1058 as superseded by #3293 rather than implementing it. | Business | High | Open |
| C-002 | No transitional deprecated wrapper | No deprecated shim/wrapper preserving the old `*args`/`**kwargs` call shape is added — the readiness probe (re-verified: grep of every call site of the four emitters across `src/`) found zero positional call sites and no external (non-in-repo) consumer of these internal functions. | Technical | High | Open |
| C-003 | Baseline before attributing red to this mission | Before treating any test failure as pre-existing, planning/implementation must baseline against issue #3284's known set (23 known-red tests + 2 errors on `main`); anything beyond that set found during this mission's work requires a new GitHub issue per the charter's Pre-existing Failure Reporting Rule, not a silent shrug. | Process | High | Open |
| C-004 | Terminology canon | This spec and all downstream artefacts use "Mission", never "Feature"/"feature*" aliases, per the charter's Terminology Canon. | Technical | Medium | Open |

### Key Entities

- **Dossier event payload types** (`LocalNamespaceTuple`, `ArtifactIdentity`,
  `ContentHashRef`, `ProvenanceRef`, and the four `MissionDossier*Payload` classes):
  after this mission, these are owned exclusively by `spec_kitty_events` (installed
  6.1.0) and merely imported into `specify_cli.dossier.events`; the CLI no longer
  defines a parallel copy.
- **Dossier event emitters** (`emit_artifact_indexed`, `emit_artifact_missing`,
  `emit_snapshot_computed`, `emit_parity_drift_detected`): remain CLI-owned business
  logic in `specify_cli.dossier.events` — they build canonical payloads and hand them
  to `fire_dossier_event`; only their internal type usage and (for two of the four)
  their argument-shape parsing changes.
- **`_PAYLOAD_RULES` dossier entries** (`specify_cli.sync.emitter`): change from four
  hand-maintained `{required, validators}` dicts to a delegation into
  `spec_kitty_events.conformance.validate_event()`, while remaining part of the same
  `_PAYLOAD_RULES` / `VALID_EVENT_TYPES` structure every other event type uses.
  **Reconciling FR-006 and FR-007**: `_validate_payload`'s single generic code path
  (`emitter.py:2549-2572`) treats every `_PAYLOAD_RULES[event_type]` value uniformly
  as `{"required": set[str], "validators": dict[str, Callable]}` — there is no
  existing per-event-type branch, so FR-006 (delegate dossier validation to
  `validate_event()`) and FR-007 (keep the four dossier keys recognized) cannot both
  be satisfied by leaving the generic loop untouched. The plan phase MUST resolve
  this by keeping the four dossier keys physically present in `_PAYLOAD_RULES` (as
  FR-007 and SC-005 both require) and giving each dossier entry's value a
  distinguishable sentinel shape in place of today's `{"required": set[str],
  "validators": dict[str, Callable]}` shape — e.g. `_PAYLOAD_RULES[event_type]` for
  the four dossier types becomes a sentinel value/marker (concrete tag left to
  planning) — with `_validate_payload` gaining an explicit early-return branch that
  recognizes the sentinel and delegates, e.g. `rules = _PAYLOAD_RULES.get(event_type);
  if is_dossier_delegate(rules): return self._validate_dossier_payload(event_type,
  payload)`, ahead of the generic `rules["required"]`/`rules["validators"]` access —
  so the two code paths never both try to interpret the same dict value the same way.
  **This same sentinel shape change also reaches `sync/diagnose.py::_validate_payload`**,
  a second, independent free-function consumer of the identical `_PAYLOAD_RULES` dict
  (imported at `diagnose.py:51`); FR-011 makes that coordination — and its regression
  test in `tests/sync/test_diagnose.py` — an explicit, binding part of this spec rather
  than an unowned side effect of FR-006.
  `VALID_EVENT_TYPES` stays `frozenset(_PAYLOAD_RULES.keys())` (`emitter.py:897`)
  unchanged, since the four dossier keys never leave `_PAYLOAD_RULES`. This
  reconciliation is a binding requirement of this spec, not an open question; only the
  exact sentinel shape is deferred to planning.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: `dossier/events.py` contains zero locally-defined Pydantic model
  classes duplicating `spec_kitty_events` shapes (verified by `grep -c "^class.*BaseModel" src/specify_cli/dossier/events.py` returning `0`, down from the current `7`).
- **SC-002**: `emit_artifact_indexed` and `emit_artifact_missing` have zero
  `*args`/`**kwargs`-style parameters in their signatures (verified by inspecting
  `inspect.signature(...)` — no `VAR_POSITIONAL` / `VAR_KEYWORD` parameter kind), while
  every existing production call site in `src/` continues to pass with no code change
  to the caller.
- **SC-003**: `tests/dossier/test_events.py`, `tests/dossier/test_emitter_adapter.py`,
  `tests/sync/test_events_namespace.py`, and `tests/sync/test_dossier_pipeline.py` all
  pass unmodified in behaviour (only the import-source edit in `test_events.py` per
  FR-009), including `test_preserves_legacy_positional_order` and
  `test_extras_rejected`.
- **SC-004**: The new AST guard test passes clean against `src/` and demonstrably
  fails against a planted positional-call fixture (both directions exercised in the
  test itself, per FR-008 AC2/AC3).
- **SC-005**: `_PAYLOAD_RULES`'s four dossier entries route through
  `spec_kitty_events.conformance.validate_event(..., strict=True)`; a hand-constructed
  invalid dossier payload (e.g. missing `namespace`) run through
  `EventEmitter._validate_payload()` returns `False` and the captured warning
  text contains a real field/violation identifier sourced from `ConformanceResult`,
  not only the field-name-and-generic-message format used today.
- **SC-006**: `diagnose_events()` no longer raises `AttributeError` on a
  dossier-typed queued event; a hand-constructed invalid dossier payload run
  through it reports a real `ConformanceResult`-sourced violation in
  `DiagnoseResult.errors`.
