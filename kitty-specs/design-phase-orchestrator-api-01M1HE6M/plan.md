# Implementation Plan: Design-Phase Orchestrator-API Verbs

**Branch**: `feat/design-phase-orchestrator-api-3837` | **Date**: 2026-09-02 | **Spec**: `kitty-specs/design-phase-orchestrator-api-01M1HE6M/spec.md`
**Input**: Feature specification from `kitty-specs/design-phase-orchestrator-api-01M1HE6M/spec.md`, enlarged by operator ruling `reviews/spec.ruling.md` (SPEC-FRESH2-001).

**Note**: This plan folds the operator ruling's scope enlargement (FR-014 seam
extraction, required for FR-013's event/lifecycle parity) directly into the
work-package breakdown — it does not merely acknowledge the ruling.

## Summary

`spec-kitty orchestrator-api` (`src/specify_cli/orchestrator_api/commands.py`)
today exposes 10 WP-implementation-loop verbs but nothing for the design
phases. This mission adds 11 new verbs — `specify`, `plan`, `tasks`,
`check-prerequisites`, `record-analysis`, `open-decision`, `resolve-decision`,
`defer-decision`, `cancel-decision`, `design-status`, `answer-decision` — plus
a `CONTRACT_VERSION` bump to `1.4.0`. Ten of the eleven verbs are additive
callers of existing service functions (`agent_feature.create_mission` /
`setup_plan` / `finalize_tasks`, `mission_check_prerequisites`,
`record_analysis`, `decisions/service.py`'s four pure functions, a new
read-only design-phase reduction). The eleventh, `answer-decision` (FR-013),
depends on a NEW shared seam (FR-014) extracted from
`src/specify_cli/cli/commands/next_cmd.py`'s `--answer` handling — per
operator ruling SPEC-FRESH2-001, `answer-decision` MUST reproduce the SAME
lifecycle-pairing, mission-event-log, and issuance-lifecycle side effects the
real CLI performs, reached through a shared module, never inlined or
duplicated into the orchestrator-api layer. This plan sequences the seam
extraction (WP02) strictly before `answer-decision` (WP08), per spec
constraint C-005.

## Technical Context

**Language/Version**: Python 3.11+ (repo standard).
**Primary Dependencies**: `typer` (verb registration, matching the existing
10 verbs), no new third-party dependency — the mission reuses
`agent_feature.*`, `decisions/service.py`, `mission_check_prerequisites.py`,
`mission_record_analysis.py`, `runtime_bridge.py`/`decision.py`, and the
existing `envelope.py`/`policy.py` orchestrator-api primitives.
**Storage**: Filesystem artifacts already owned by the host CLI —
`kitty-specs/<slug>/{spec.md,plan.md,tasks/,analysis-report.md}`,
`decisions/index.json`, `mission-events.jsonl`, `kitty-ops/lifecycle.jsonl`,
the run-snapshot store read via `_internal_runtime.engine._read_snapshot`. No
new storage layer.
**Testing**: `pytest`, targeted directories (see Gate Set below), not the
full `tests/` suite per-WP.
**Target Platform**: Same as the rest of the CLI — Linux/macOS/Windows,
Python 3.11+, no new platform constraint.
**Project Type**: Single project (existing `spec-kitty` CLI monorepo layout;
no web/mobile split applies).
**Performance Goals**: Matches existing orchestrator-api verbs — in-process,
sub-2s typical, no new subprocess or network call introduced (NFR-004
explicitly forbids introducing an out-of-process wrap for `record-analysis`).
**Constraints**: NFR-001 (zero behavior change to the 10 existing verbs),
NFR-002 (no silent success), NFR-004 (artifact-verified, time-bounded success
for `record-analysis`), NFR-005 (envelope/policy parity), C-001 (no
`spec-kitty-events`/`spec-kitty-tracker` touch), C-005 (FR-014 before FR-013,
behaviour-preserving).
**Scale/Scope**: 11 new verbs, 1 new shared seam module, 1 doc file, 1 skill
reference doc, 1 changelog entry, 1 contract-version bump. No schema/glossary
change identified (see "Generated artifacts" below).

## Constitution / Charter Check

*GATE: read `.kittify/charter/charter.md` before Phase 0; re-checked at each
work package.*

- **Single canonical authority** — every new verb calls the SAME service
  function the host CLI already calls (no parallel reimplementation); FR-014
  exists specifically so `answer-decision` does not duplicate `next_cmd.py`'s
  lifecycle/event-log logic. PASS.
- **Architectural alignment (shared-package boundaries)** — this repo's
  `CLAUDE.md` "Shared Package Boundary" section states runtime code lives at
  `src/runtime/next/_internal_runtime/` (canonical) and that
  `src/specify_cli/next/` is a deprecated shim; the charter's "Internal
  Runtime Boundary" section states mission-runtime behavior used by
  `spec-kitty next` is CLI-owned, in-repo code. See "FR-014 Target Module
  Decision" below for how this plan reconciles that guidance against what
  the actual tree contains. PASS (with the concrete module decision
  recorded).
- **ATDD-first** — every WP in this plan is gated on a RED-then-GREEN commit
  pair (see "ATDD-First Discipline" below). PASS (planned).
- **Domain-driven splits + tiered rigour** — MORE rigour is applied to
  FR-013/FR-014 (the seam is core, load-bearing behavior parity) than to the
  thin-shim verbs (FR-001–FR-003, FR-006–FR-009). PASS.
- **Glossary & terminology adherence** — no `feature`-prohibited terminology
  introduced; new verb names (`specify`, `plan`, `tasks`,
  `check-prerequisites`, `record-analysis`, `open-decision`,
  `resolve-decision`, `defer-decision`, `cancel-decision`, `design-status`,
  `answer-decision`) all use `mission`, matching the existing 10 verbs'
  convention. PASS.
- **C-002 (no server-side analysis reasoning)** — `record-analysis` is a thin
  caller of the existing `record_analysis`/`write_analysis_report` write
  path (see § (j)); it persists an analysis verdict the caller already
  computed, it does not compute or reason about the analysis itself. PASS.
- **C-003 (OriginFlow-bounded decision-verb scope)** — the four decision
  verbs (`open-decision`/`resolve-decision`/`defer-decision`/
  `cancel-decision`, WP05) are gated by the `OriginFlow` guard (Mechanism A,
  see Work Package Breakdown), keeping their scope to OriginFlow-issued
  decisions only, matching C-003's bound. PASS.

No constitution violations requiring the Complexity Tracking table below —
left empty deliberately.

---

## (a) FR-014 Seam Extraction — Target Module Decision

**Functions to extract** (all currently defined in
`src/specify_cli/cli/commands/next_cmd.py`, called from its `--answer`
handling path at approximately lines 244, 251, 263 per the spec's own
citations — confirmed against the checkout: `_pair_previous_lifecycle_record`
call at `next_cmd.py:244`, `decide_next` call at `next_cmd.py:248-250`,
`_emit_mission_next_invoked` call at `next_cmd.py:251-258`,
`_write_issuance_lifecycle_record` call at `next_cmd.py:263-269`):

1. `_pair_previous_lifecycle_record` — defined at `next_cmd.py:333`.
2. `_emit_mission_next_invoked` — defined at `next_cmd.py:863`.
3. `_write_issuance_lifecycle_record` — defined at `next_cmd.py:430`.

**Confirmed against the actual tree**: `src/runtime/next/` exists at the repo
root and contains `_internal_runtime/` (verified: `ls src/runtime/next/` and
`ls src/runtime/next/_internal_runtime/`, both present). `CLAUDE.md`'s
"Shared Package Boundary" section text is accurate as far as it goes — but it
describes the boundary for the DAG-advancement *engine* (internalized from
the retired `spec-kitty-runtime` PyPI package: `_internal_runtime/engine.py`,
`planner.py`, `lifecycle.py` — the last of which is workflow-STATE lifecycle,
i.e. `next_step`/`provide_decision_answer`/`start_mission_run` re-exports,
**not** issuance/lifecycle-*record* I/O). Grepping
`src/runtime/next/_internal_runtime/` for `lifecycle_record`/`issuance`
returns **zero matches** — there is no existing natural home there for the
three functions being extracted.

**Where the three functions' real dependencies already live** (verified by
reading `next_cmd.py:333-475` and `next_cmd.py:863-905`):

- `_pair_previous_lifecycle_record` and `_write_issuance_lifecycle_record`
  call primitives from `specify_cli.invocation.lifecycle`
  (`read_lifecycle_records`, `find_latest_unpaired_started`,
  `write_paired_completion`, `make_canonical_action_id`, `write_started`) and
  `specify_cli.mission_metadata.resolve_mission_identity` — this is the
  **existing, correctly-layered "issuance lifecycle record" store**
  (`src/specify_cli/invocation/lifecycle.py`, module docstring: "Profile-
  invocation lifecycle store (WP05 / issue #843)... written by `spec-kitty
  next`"). It already IS the persistence layer; nothing new needs inventing
  there.
- `_emit_mission_next_invoked` calls `specify_cli.mission_v1.events.emit_event`
  to write the `MissionNextInvoked` entry into `mission-events.jsonl` — a
  **different persistence layer** from the issuance-lifecycle-record store
  above (confirmed: `mission_v1/events.py`'s module docstring: "Events are
  written to `<feature_dir>/mission-events.jsonl`"; entirely separate file,
  separate schema, separate module).

**Decision: one seam module with three functions, not a split along the
persistence-layer boundary.** Although the three functions write to two
distinct stores, all three are *next-invocation orchestration* — the same
class of "what `spec-kitty next --answer` does around the DAG advance call,"
which is exactly FR-014's own title ("shared next-invocation
lifecycle/event-log seam"). Splitting into two modules (one for lifecycle-
record pairing, one for event-log emission) would not track any real
architectural seam — both are thin next-cmd-specific orchestration wrappers
(resolving `mission_id`/`feature_dir`, handling best-effort failure) around
already-correctly-layered primitives (`specify_cli.invocation.lifecycle`,
`specify_cli.mission_v1.events`). One module keeps the three functions
co-located as "the three side effects FR-013/SC-007(c)/SC-008 require
together," matching how the spec itself always refers to them as a triad.

**Target module: new file `src/runtime/next/next_invocation_lifecycle.py`**
(top-level under `src/runtime/next/`, a sibling of `runtime_bridge.py` and
`decision.py` — NOT under `_internal_runtime/`, which is reserved for
internalized former-`spec-kitty-runtime`-package internals per that
directory's own module docstrings).

Why this location and not the alternatives:

- **Not `src/specify_cli/orchestrator_api/`**: that would be exactly the
  "inline into the orchestrator-api layer" the operator ruling explicitly
  rejected (spec.ruling.md, Rationale point 4: "Inlining would put
  orchestrator-api code in reach of CLI-layer helpers... and would duplicate
  logic that then drifts from the CLI's own copy").
- **Not a new top-level package**: this repo's charter "Internal Runtime
  Boundary" section is explicit that mission-runtime behavior used by
  `spec-kitty next` lives inside this repo's existing runtime home, not a new
  boundary; a new top-level package would need its own ADR-level
  justification this mission does not need to invent.
- **Not `_internal_runtime/`**: that subpackage's own module docstrings
  (`lifecycle.py:1-11`) state it is "Internalized from spec-kitty-runtime
  0.4.3... The three callables below are the canonical lifecycle entry points
  used by the CLI" — i.e. it is a closed set of DAG-engine re-exports
  (`next_step`, `provide_decision_answer`, `start_mission_run`), not an
  extension point for next-command-layer orchestration helpers.
- **`src/runtime/next/` top level, alongside `runtime_bridge.py` /
  `decision.py`, IS the right precedent for the MODULE'S placement**: both
  of those top-level modules already freely import from `specify_cli.*`
  domain modules — confirmed: `decision.py:33` imports
  `specify_cli.mission_metadata.mission_identity_fields`,
  `decision.py:188` imports `specify_cli.mission_v1.events.read_events` (the
  READ counterpart of the very `emit_event` call `_emit_mission_next_invoked`
  needs to call), `runtime_bridge.py:319` imports
  `specify_cli.mission_metadata.resolve_mission_identity` (the exact function
  `_pair_previous_lifecycle_record`/`_write_issuance_lifecycle_record`
  already use). This establishes clean precedent for `runtime.next → specify_cli`
  imports (the direction the seam module itself needs). It does NOT, by
  itself, establish precedent for the reverse direction WP08 introduces —
  `orchestrator_api/commands.py` importing FROM `runtime.next`. That
  precedent exists elsewhere and separately: `next_cmd.py` (a CLI-layer
  command module, the same architectural tier as `orchestrator_api/commands.py`)
  already imports `runtime.next` directly today — confirmed:
  `next_cmd.py:51` (module-level `from runtime.next._runtime_pkg_notice
  import maybe_emit_runtime_pkg_notice`), `next_cmd.py:67` (inside
  `decide_next`, `from runtime.next.decision import decide_next as
  _decide_next`), `next_cmd.py:195` (`from runtime.next.runtime_bridge
  import MissionNotFoundError as _MissionNotFoundError`, inline import),
  `next_cmd.py:817` (`from runtime.next.runtime_bridge import
  MissionNotFoundError`), `next_cmd.py:984` (`from
  runtime.next._internal_runtime.engine import _read_snapshot`). This is the
  real, on-point
  precedent for a CLI-layer module calling into `runtime.next`. As of this
  plan, `orchestrator_api/commands.py` has **zero** such imports (confirmed:
  `commands.py:32-66`'s import block contains no `runtime.next` (or bare
  `src/runtime/`) reference) — WP08 introduces the first one, following
  `next_cmd.py`'s established pattern rather than inventing a new one.
  Together, these two precedents cover both edges the seam's placement
  needs: `runtime.next` modules already import `specify_cli.*` freely (the
  module's own placement), and a CLI-layer command module already imports
  `runtime.next` directly (the calling direction WP08 needs).
- **`answer-decision` (FR-013) will import `runtime_bridge.py` and
  `decision.py` from this same `src/runtime/next/` top level anyway** (for
  `answer_decision_via_runtime`, `decide_next_via_runtime`, `decide_next`) —
  co-locating the seam module alongside them means orchestrator-api's
  FR-013 implementation makes ONE set of imports from ONE package
  (`runtime.next`) for both the engine calls and the lifecycle/event-log
  seam, rather than reaching into two different layers.

**Extracted function names** (module-level, public — these are now a shared
contract, not private `_`-prefixed CLI helpers):

```
src/runtime/next/next_invocation_lifecycle.py
    pair_previous_lifecycle_record(agent, mission_slug, result, repo_root, *, effective_root=None) -> None
    emit_mission_next_invoked(agent, result, mission_slug, repo_root, decision, *, effective_root=None) -> None
    write_issuance_lifecycle_record(agent, mission_slug, repo_root, decision, *, effective_root=None) -> None
```

Signatures are carried over verbatim from the current `next_cmd.py`
functions (same parameters, same best-effort/fail-closed semantics) so the
extraction is a pure move, not a redesign.

**SC-008 shared regression test helper (pinned contract, WP02 deliverable,
reused unmodified in shape by WP08)**: the three signatures above are the
extracted seam's own contract. The shared TEST helper that verifies their
side effects needs its own, separate, named contract so WP02 (authored
first) and WP08 (extends it) build compatible scaffolding rather than merely
similar scaffolding — the exact SC-008 drift failure mode this test exists
to prevent. WP02 authors a module-level helper:

```
assert_lifecycle_seam_effects(feature_dir, repo_root, mission_slug, run_action) -> None
```

- `run_action` is a zero-arg callable that performs the action under test —
  a `next_cmd` `--answer` invocation in WP02's own test, an
  orchestrator-api `answer-decision` call in WP08's extension — the helper
  itself is agnostic to which caller invoked the seam.
- After calling `run_action()`, the helper reads `mission-events.jsonl` via
  `specify_cli.mission_v1.events.read_events` and asserts a
  `MissionNextInvoked` entry was appended (the `_emit_mission_next_invoked`
  side effect).
- It also reads the issuance-lifecycle-record store via
  `specify_cli.invocation.lifecycle.read_lifecycle_records` and asserts
  both (a) the previous `started` record was paired to a completion record
  (the `_pair_previous_lifecycle_record` side effect) and (b) a NEW
  `started` record was written (the `_write_issuance_lifecycle_record` side
  effect).
- It raises (via a plain `assert`, consistent with this repo's pytest-native
  style) on the first missing/mismatched effect, rather than returning a
  bool, so a failing case points directly at which of the three seam
  functions regressed.

WP02's task file must land this helper (in the shared test module, see § (e)
Gate Set item 3 below) as the deliverable WP08 is contractually bound to
import and reuse — not re-derive — for its own extension.

---

## (b) Seam / Layering Statement (every WP)

| WP | Seam | New/changed modules |
|----|------|----------------------|
| WP01 (campsite) | N/A (behaviour-preserving cleanup only, in touched files) | none new |
| WP02 (FR-014) | CLI ↔ runtime boundary | NEW `src/runtime/next/next_invocation_lifecycle.py`; `next_cmd.py` becomes a thin caller |
| WP03 (FR-001–003) | CLI (orchestrator-api verb layer) → existing `agent_feature.*` service layer | `orchestrator_api/commands.py` only |
| WP04 (FR-004/005) | CLI (orchestrator-api verb layer) → existing `mission_check_prerequisites.py`/`mission_record_analysis.py` service layer | `orchestrator_api/commands.py` only |
| WP05 (FR-006–009/012) | CLI (orchestrator-api verb layer) → existing `decisions/service.py` pure functions | `orchestrator_api/commands.py` only |
| WP06 (FR-010) | CLI (orchestrator-api verb layer) → new narrow read-only reduction, in-file | `orchestrator_api/commands.py` only (a private reduction helper, not a new engine) |
| WP07 (FR-011) | CLI (orchestrator-api envelope layer) | `orchestrator_api/envelope.py` only |
| WP08 (FR-013) | CLI (orchestrator-api verb layer) → runtime engine (`runtime_bridge.py`/`decision.py`) AND runtime seam (`next_invocation_lifecycle.py`, WP02's output) | `orchestrator_api/commands.py` only |
| WP09 (docs) | Documentation only | `docs/api/orchestrator-api.md`, `host-boundary-rules.md`, `CHANGELOG.md` |

**Binding statement for every WP**: no CLI command (`next_cmd.py`,
`orchestrator_api/commands.py`, or any new CLI-layer helper) reaches past a
service/engine layer into kernel internals — `src/kernel/` is not touched by
this mission at all (see "(i) `__all__`" below). Every new orchestrator-api
verb calls the SAME service function the host CLI calls for the equivalent
operation (`agent_feature.create_mission`/`setup_plan`/`finalize_tasks`,
`mission_check_prerequisites`'s underlying assembly function,
`record_analysis`, `decisions/service.py`'s four functions,
`runtime_bridge.answer_decision_via_runtime` + `decision.decide_next`) —
never CLI-command-layer code in `next_cmd.py`/`lifecycle.py`/`decision.py`
(the host-CLI command modules) directly, **except** through the FR-014 seam,
which is the one, explicit, reviewed crossing point built precisely so
neither side reaches into the other's layer uncontrolled.

---

## (c) Generated Artifacts

This mission touches **no generated artifact**. Confirmed:

- `docs/api/orchestrator-api.md` — hand-authored reference doc. Verified: no
  generator (`scripts/`, `src/`) writes this path (grep across `src/`,
  `scripts/`, `.github/` for the literal path returns zero generator hits;
  only cross-reference index files — `docs/development/3-2-page-inventory.yaml`,
  `docs/development/3-2-docs-retrieval-index.yaml` — mention it as a
  catalogued doc, not as a build target), and it carries no `GENERATED
  FILE`/`DO NOT EDIT` marker.
- `src/charter/offering/skills/spec-kitty-orchestrator-api-operator/references/
  host-boundary-rules.md` — same: hand-authored skill reference, no generator
  writes it, no DO-NOT-EDIT marker.
- No doctrine schema changes: this mission adds CLI verbs and one runtime
  module; it does not touch `src/doctrine/` artifact schemas, mission-type
  YAML, or step-contract definitions.
- No Contextive glossary changes: the new verb names
  (`specify`/`plan`/`tasks`/`check-prerequisites`/`record-analysis`/
  `open-decision`/`resolve-decision`/`defer-decision`/`cancel-decision`/
  `design-status`/`answer-decision`) are all either literal re-uses of
  existing host-CLI command names (`specify`, `plan`, `tasks`,
  `check-prerequisites`, `record-analysis`, `open`/`resolve`/`defer`/
  `cancel`-decision already exist as `decision_app` subcommands) or
  self-explanatory compounds following the existing `list-ready`/
  `mission-state`/`start-review` orchestrator-api naming convention
  (`design-status`, `answer-decision`) — none introduces new DOMAIN
  terminology requiring a glossary entry. If the WP09 docs pass or an
  adversarial squad disagrees on any one term, that is a narrow, addressable
  finding at that point-cut, not a structural gap in this plan.

If any WP author later discovers a doctrine schema or glossary dependency
this plan missed, name the regenerating command
(`spec-kitty charter sync` / the Contextive glossary tool) explicitly in that
WP rather than silently working around it.

---

## (d) Contract-Moves Statement

The orchestrator-api contract surface itself moves: this mission adds 11
verbs to the 10 that exist today. Versioning discipline:

- `CONTRACT_VERSION` bumps `1.3.0` → `1.4.0` (FR-011), additive-only — the
  same discipline `envelope.py`'s own inline changelog documents for
  1.2.0 ("added read-only `resolve-workspace`... Purely additive") and 1.3.0
  ("`transition` accepts structured `--review-result-json`"). This mission's
  bump follows that exact precedent: a new changelog comment line above
  `CONTRACT_VERSION = "1.4.0"` in `src/specify_cli/orchestrator_api/envelope.py:28`
  naming the 11 new verbs.
- `MIN_PROVIDER_VERSION` (`envelope.py:29`, currently `"0.1.0"`) is
  **unchanged** — already ruled on in spec Clarification 4; this is a
  routine additive minor bump, not a breaking provider-compatibility change.
- `spec-kitty-events` is confirmed a real external PyPI dependency (per the
  charter's "External Contract Packages" section: "`spec-kitty-events` and
  `spec-kitty-tracker` are true external package dependencies... Do not
  vendor their source into the CLI package"), **not vendored** in this repo.
  This mission does **not** touch `spec-kitty-events` (C-001) — grep
  confirms zero references to it in `orchestrator_api/` or `envelope.py`
  today, and none of the 11 new verbs, the FR-014 seam, or the
  `CONTRACT_VERSION` bump introduces one. Stated plainly, not left implicit:
  no `spec-kitty-events` package release, version bump, or compatibility
  change is required or in scope for this mission.

---

## (e) Gate Set

**Active gates for this mission:**

1. `make lint` (ruff) — advisory in CI, mandatory local discipline per
   `CLAUDE.md` ("New code MUST pass `ruff` and `mypy` with zero issues").
2. `mypy --strict` on touched files (charter Testing Requirements section).
3. Targeted pytest shards:
   - `tests/specify_cli/orchestrator_api/` — all new verb tests land here
     (new files per WP, e.g. `test_specify_plan_tasks_verbs.py`,
     `test_check_prerequisites_record_analysis.py`,
     `test_decision_verbs.py`, `test_design_status.py`,
     `test_answer_decision.py`), plus the four existing files
     (`test_commands_fail_closed.py`, `test_fail_message_preserved.py`,
     `test_transition_subtask_gate.py`, `test_typed_error_fail_closed.py`)
     re-run to confirm NFR-001 (zero change to the 10 existing verbs).
     Directory placement alone does not select the five new files into
     either job that collects this directory: `fast-tests-core-misc`'s
     specify-cli-rest shard runs `-m "fast and not windows_ci and not
     regression"` (`ci-quality.yml:1793`) and `integration-tests-core-misc`'s
     mirrored shard runs `-m 'not windows_ci and (git_repo or integration or
     architectural) and not timing and not regression'`, so each new file
     must carry an explicit `pytestmark` matching the existing four files'
     convention — `pytest.mark.fast` for pure in-process verb tests, or
     `[pytest.mark.integration, pytest.mark.git_repo]` for any that do real
     git-repo/fixture-mission I/O, mirroring `test_transition_subtask_gate.py`
     (`pytestmark = [pytest.mark.integration, pytest.mark.git_repo]`) against
     the other three's `pytestmark = [pytest.mark.fast]`.
   - `tests/specify_cli/cli/commands/test_next_answer_effective_root.py`,
     `test_next_fail_closed.py`, `test_next_owned_commit_guard.py`,
     `test_next_typed_error_passthrough.py` — the existing `next_cmd.py`
     `--answer` test surface, re-run against WP02's refactor to confirm
     behaviour preservation (C-005).
   - A NEW shared regression test module (WP02 authors first, WP08 extends —
     see "(a)/SC-008" and the ATDD table below) — location
     `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py` (moved
     off the originally-considered `tests/specify_cli/cli/commands/`
     location; see item 4 below for why, and § Project Structure /
     § Parallel Work Analysis for the consistent restatement). This matches
     the existing convention for testing other `src/runtime/next/` top-level
     modules — `tests/specify_cli/next/test_runtime_bridge.py` and
     `test_runtime_bridge_dispatch.py` already test `runtime_bridge.py`
     from this same directory — and it exercises both the CLI caller and,
     once WP08 lands, the orchestrator-api caller. Directory placement
     alone does not select a test into either coverage-emitting job (see
     item 4 below): both `fast-tests-next` and `integration-tests-next`
     additionally filter collection by pytest marker, and the sibling
     precedent files carry an explicit `pytestmark` rather than relying on
     location (`test_runtime_bridge.py:19` — `pytestmark =
     pytest.mark.fast`; `test_runtime_bridge_dispatch.py:29` — `pytestmark
     = [pytest.mark.unit, pytest.mark.fast]`). WP02's shared test module
     does real file I/O (mission-events.jsonl, the issuance-lifecycle-record
     store) driven through `next_cmd --answer` against real fixture
     missions — this does not qualify as `fast` under this repo's own
     definition (`pytest.ini:25`, "no subprocess/git overhead"), so it must
     instead carry `pytestmark = pytest.mark.integration` (add
     `pytest.mark.git_repo` too if the fixture-mission setup ends up doing
     a real `git init`, matching the `test_runtime_bridge_composition.py` /
     `test_next_output_preservation.py` precedent for other fixture-mission,
     real-file-I/O tests in this same directory) so
     `integration-tests-next`'s `-m '... and (git_repo or integration)'`
     filter selects it.
   - `tests/architectural/` — targeted run of `test_shared_package_boundary.py`
     (verified: it enforces *negative import* boundaries for retired
     packages via AST scan across `src/{specify_cli,runtime,charter,doctrine,
     kernel}`, not internal module placement — the new
     `next_invocation_lifecycle.py` file does not import anything retired,
     so this is a regression check, not expected to need new assertions) and
     `test_runtime_charter_doctrine_boundary.py` (adjacent boundary
     coverage, cheap to include given WP02 adds a new `src/runtime/next/`
     module).
4. **`diff-coverage` (critical-path, ENFORCED, 90% floor)** — **APPLIES**.
   `ci-quality.yml`'s `diff-coverage` job (`ci-quality.yml:3358` step
   "diff-coverage (critical-path, enforced)") lists `'src/runtime/next/*'`
   as a `critical_paths` entry (`ci-quality.yml:3391`) and runs
   `diff-cover ... --fail-under=90 --include "${critical_paths[@]}"`
   (`ci-quality.yml:3422-3425`); `diff-coverage` is itself a required member
   of the blocking `quality-gate.needs` list (`ci-quality.yml:4276,4281`).
   WP02's new `src/runtime/next/next_invocation_lifecycle.py` is therefore
   subject to a hard 90%-of-changed-lines floor. The job consumes coverage
   XML produced by `--cov=src/runtime/next`, which only two jobs emit:
   `fast-tests-next` (`ci-quality.yml:1430`, scans `tests/next/
   tests/specify_cli/next/ tests/runtime/`) and `integration-tests-next`
   (`ci-quality.yml:2757-2794`, same three-path scope). A test asserting
   the new module's behavior only counts toward this gate if it is
   collected from one of those three roots — this is why item 3 above moved
   the SC-008 shared regression test to `tests/specify_cli/next/` rather
   than `tests/specify_cli/cli/commands/` (which is scanned only by the
   `slow-tests` job's `--cov=specify_cli --cov=charter --cov=doctrine`,
   `ci-quality.yml:3063-3066`, never `src/runtime/next`). Directory
   placement is necessary but not sufficient: both coverage-emitting jobs
   additionally filter collection by pytest marker — `fast-tests-next` runs
   `-m "fast and not windows_ci"`; `integration-tests-next` runs `-m
   '${{ matrix.shard }} and not windows_ci and (git_repo or integration)'`
   (`ci-quality.yml:2794`), where the shard half of that expression is
   auto-applied by `tests/conftest.py::_apply_shard_markers` but
   `git_repo`/`integration` is not. WP02's task file must therefore also
   mark the new module `pytestmark = pytest.mark.integration` (add
   `pytest.mark.git_repo` too if it needs a real git repo fixture) — the
   real-file-I/O shape of this test (event log + lifecycle-record store
   reads/writes) does not qualify as `fast` per `pytest.ini:25`'s
   definition, so an unmarked or `fast`-marked module would land in the
   right directory but stay invisible to both coverage-emitting jobs and
   the diff-coverage gate would then see zero coverage for the new lines.
5. **Kernel coverage ≥90%** — does **NOT** apply. Verified against
   `.github/workflows/module-kernel.yml` (`--cov=src/kernel`, floor 90.0)
   and `ci-quality.yml`'s `kernel-tests` job (`ci-quality.yml:1085-1090`):
   the job's own trigger is gated on the `kernel` changes-filter group
   (`src/kernel/**`, `tests/kernel/**` only, `ci-quality.yml:443-445`) —
   this mission touches neither path, so the job does not even run for this
   mission's PR, and the coverage floor itself is scoped exactly to
   `src/kernel/`, which this mission does not touch at all. Both the
   trigger and the scope correctly exclude this mission — unlike items 6
   and 10 below.
6. **Mission-loader coverage ≥90%** — **RUNS**, not "does not apply."
   Correction from an earlier draft of this item: the `mission-loader-coverage`
   job's own `if:` condition (`ci-quality.yml:1451-1454`) is
   `needs.changes.outputs.next == 'true' || ...core_misc... || ...platform...`,
   and this mission's `next` changes-filter output is TRUE — WP02 adds
   `src/runtime/next/next_invocation_lifecycle.py`, which matches the
   `next` filter group's own `'src/runtime/next/**'` pattern
   (`ci-quality.yml:305`). The job therefore runs. Its coverage floor
   (`--cov=src/specify_cli/mission_loader --cov-fail-under=90`,
   `tests/unit/mission_loader/ tests/integration/test_mission_run_command.py`,
   `ci-quality.yml:1461-1467`) is scoped to a package this mission does not
   touch, so it is **expected to pass trivially** (unchanged absolute
   coverage of an untouched package) — same "runs, applies, passes
   trivially" shape as item 11 (Contextive) below, not a "does not apply"
   case.
7. `commitlint` (`commitlint.config.cjs` present at repo root) — standard
   commit-message gate, applies to every commit this mission makes.
8. Markdown lint (`.markdownlint-cli2.jsonc` present) — applies to
   `docs/api/orchestrator-api.md` and `host-boundary-rules.md` edits (WP09).
9. Architecture/docs consistency — WP09's doc updates are cross-checked
   against the actual verb behavior landed in WP03–WP08 (not written from
   the spec alone).
10. Doctrine schema freshness — **RUNS**, not "does not apply." Correction
    from an earlier draft of this item: the "[ENFORCED] Verify generated
    doctrine schemas are up to date" step (`ci-quality.yml:656`, `uv run
    python scripts/generate_schemas.py --check`) lives inside the `lint`
    job, which has **no path filter at all** — it is `if:
    !contains(labels, 'pr:deferred') && !contains(labels, 'pr:skip-ci')`
    only (`ci-quality.yml:618`), unconditional on every PR, by deliberate
    design (the step's own inline comment: "a freshness gate behind a
    paths filter is the same silence #2957 is about"). It therefore runs
    on this mission's PR regardless of path. It is **expected to pass
    trivially**: this mission touches no Pydantic schema model under
    `src/charter/offering/` (see "(c) Generated Artifacts") — its
    unchanged in-memory regeneration will match the committed schema
    files. Same "runs, applies, passes trivially" shape as items 6 and 11.
11. Contextive glossary — **RUNS** (the check step at `ci-quality.yml:851`
    is gated on the diff touching `src/specify_cli/**`, among other paths,
    `ci-quality.yml:863-869` — this mission's changes match) but is
    **expected to pass trivially**: no `docs/context/*.md` or
    `.kittify/traceability/contextive-map.yaml` change is needed, because no
    new domain terminology is introduced (see "(c) Generated Artifacts").
    Applicability (does this gate execute) and outcome (does it pass) are
    distinct — this item is about the latter.
12. TID251 banned-API — applies repo-wide per `pyproject.toml`'s ruff config
    (enforced across the entire `tests/` tree); any new test using a banned
    API needs an inline `# noqa: TID251 — <justification>`, not a blanket
    exemption.
13. Typer JSON error surface — the existing pattern
    (`_fail(cmd, error_code, message, ...)` → structured envelope, never a
    bare Typer/Click traceback) already covers `orchestrator_api/commands.py`
    verbs uniformly because every new verb is added to the SAME `app =
    typer.Typer(...)` instance and reuses the SAME `_fail`/`_emit`/
    `make_envelope` helpers (confirmed by reading the `start-review` verb as
    the pattern precedent, `commands.py:1380-1465`) — no new gate machinery
    is needed for the 11 new verbs; `tests/specify_cli/orchestrator_api/
    test_commands_fail_closed.py` and `test_typed_error_fail_closed.py`
    extend to cover them (NFR-002/SC-004).
14. `patch()` target validation — **ENFORCED**. `ci-quality.yml:943`'s
    "[ENFORCED] Validate patch() target strings (closes #394)" step runs
    `scripts/check_patch_targets.py`, in the same always-on `lint` job as
    the TID251/Bandit/pip-audit steps items 12/15/16 cite. New test code in
    WP02–WP08 using `unittest.mock.patch(...)` must use a resolvable dotted
    target string (patch the name at its point of use, not at its
    definition site) to pass this gate.
15. Bandit — repo-wide security-lint gate; applies to new code the same as
    everywhere else; no new subprocess/eval/pickle usage is introduced by
    this mission (NFR-004 explicitly keeps `record-analysis`'s wrap
    in-process).
16. `pip-audit` — repo-wide dependency-audit gate; no new dependency is added
    by this mission (see next line), so no new finding surface is expected.
17. `uv.lock` freshness — **no dependency change expected.** This mission
    adds zero new third-party packages (typer/pytest/etc. are already
    dependencies); `uv.lock` should be byte-identical before/after except for
    routine `pyproject.toml` version-string housekeeping if any (none
    planned). If a WP author finds a lock diff, that is a signal something
    unplanned happened and should be flagged, not silently committed.

**Explicitly excluded from this mission's active gate set**: **SonarCloud
does NOT run on pull requests** — verified against
`.github/workflows/ci-quality.yml`'s `sonarcloud` job comment block:
"Temporarily limited to schedule/manual runs while #825 tracks the existing
project-wide Sonar quality gate backlog. PRs skip Sonar entirely to keep
review latency low, and pushes skip it so main can report test/build
health." Do not list SonarCloud as a PR gate for this mission's WPs.

---

## (f) Baseline

`main` carries ~23 known-red tests tracked as issue #3284 (NFR-003), and a
shared test-venv lock that can time out under concurrency (issue #3283, per
NFR-003's cross-reference). Before WP01 (the campsite-clean WP) makes its
first change, baseline the targeted test directories listed in the Gate Set
above (`tests/specify_cli/orchestrator_api/`,
`tests/specify_cli/cli/commands/test_next_*.py`,
`tests/architectural/test_shared_package_boundary.py`,
`test_runtime_charter_doctrine_boundary.py`) against the pre-mission commit
on `feat/design-phase-orchestrator-api-3837` (the mission's own base, per
this repo's `CLAUDE.md` "Test-run baseline-red gotcha" section) — this
distinguishes issue #3284's pre-existing reds from anything this mission
introduces. Every WP prompt must re-state which reds (if any) were
pre-existing at that WP's start. No new issue is opened for #3284's
pre-existing failures — cite #3284 explicitly in any WP that observes one of
its reds.

---

## (g) Campsite-Clean Scope (WP01)

Distinct, behaviour-preserving FIRST work package, folding ONLY
domain-matched debt in the three files this mission is about to touch:
`next_cmd.py`, `orchestrator_api/commands.py`, `envelope.py`.

Findings from a quick pass at plan time:

- `next_cmd.py` is a large module (900+ lines) with several long, deeply
  commented functions (`decide_next`, `_handle_answer`) directly adjacent to
  the three functions FR-014 extracts. One of the three DOES carry live
  debt: `_pair_previous_lifecycle_record` (`next_cmd.py:333-429`) contains an
  un-investigated type suppression at `next_cmd.py:424` —
  `phase=phase,  # type: ignore[arg-type]` inside its `write_paired_completion(...)`
  call. The other two (`_emit_mission_next_invoked`, `_write_issuance_lifecycle_record`)
  are clean — narrowly scoped, individually documented, and covered by the
  existing `test_next_answer_effective_root.py` /
  `test_next_owned_commit_guard.py` surface. Because these three functions
  are being promoted to a public, module-level API (see § (a)), WP01 folds a
  one-line investigation/fix of `next_cmd.py:424`'s suppression: either
  narrow `phase`'s type so the suppression is no longer needed, or — if
  `write_paired_completion`'s `phase` parameter is genuinely typed narrower
  than the local `phase: str` this function computes and a real narrowing is
  non-trivial — replace the bare `# type: ignore[arg-type]` with a
  justification comment per this repo's `CLAUDE.md` code-style rule
  ("narrowly-scoped, individually-justified suppressions... must carry an
  inline rationale"). WP01's own task file must record which of the two it
  did; carrying the suppression forward silently is not acceptable now that
  the function becomes public surface. The module-level size of
  `next_cmd.py` itself is a pre-existing characteristic not localized to the
  functions this mission moves, so it is NOT folded in here (would violate
  Locality of Change / turn WP01 into a grab-bag).
- `orchestrator_api/commands.py` and `envelope.py`: both already pass
  `ruff`/`mypy` clean at the point this mission opens (spot-checked: no
  `# noqa`/`# type: ignore` in the functions this mission's WPs will extend
  — `start-review`, the envelope helpers, `CONTRACT_VERSION`'s changelog
  block).

**Conclusion**: one domain-matched debt item WAS found (the `next_cmd.py:424`
type suppression above) and is folded into WP01. WP01 is therefore scoped
to: (1) the `next_cmd.py:424` fix/justification, (2) the baseline-red
snapshot from "(f)" above, and (3) if the WP01 author's own closer read
(which has more time than this plan-time pass) finds any further genuine,
narrowly-scoped debt item directly in one of the three files' touched
functions, fold it there with a one-line rationale — do not invent filler
cleanup to justify the WP's existence. State explicitly in WP01's own task
file exactly what was found and fixed, rather than silently skipping the
standing order.

---

## (h) ATDD-First Discipline (all WPs)

Every WP below lands as (at minimum) two commits: a FAILING test commit
first, then an implementation commit. Because this mission's topology is
`single_branch`, `planning_base_branch` == the feature branch itself
(`feat/design-phase-orchestrator-api-3837`, confirmed via `spec-kitty plan
--json`'s `planning_base_branch` field). The reviewer verifies:

- **RED** on `planning_base_branch` — i.e., checking out the feature branch
  at the commit immediately BEFORE a WP's implementation commits land, the
  WP's own new test(s) fail (or do not exist yet / fail to import), proving
  they exercise real, not-yet-built behavior.
- **GREEN** on the WP's final commit — the same test(s) pass once the WP's
  implementation commit(s) land on top.

This applies to every WP (WP01 through WP09) including the docs WP (WP09's
"test" is the markdown-lint + doc-consistency check, which must fail against
the pre-WP09 doc state and pass after).

---

## (i) `__all__` (charter C-007-equivalent)

Does **NOT** apply to this mission's touched surface. This mission's Scope
Notes and this plan's WP breakdown touch `src/specify_cli/orchestrator_api/`,
`src/specify_cli/cli/commands/next_cmd.py`, and the NEW
`src/runtime/next/next_invocation_lifecycle.py` — **no file under
`src/charter/` or `src/kernel/` is touched**. (The one `src/charter/`
reference in this mission's scope,
`src/charter/offering/skills/spec-kitty-orchestrator-api-operator/references/
host-boundary-rules.md`, is a markdown skill-reference doc, not a Python
module — the `__all__` rule applies to modules, not doc files.) Stated
explicitly per the task instructions, rather than silently ignored.

---

## (j) SK-93 Implementation Approach (FR-005 / `record-analysis` / NFR-004)

`record-analysis` does NOT trust the exit/return behavior of the underlying
`record_analysis` call. Concrete mechanism:

1. **Call-start timestamp**: capture `now_utc_iso()` (the same clock helper
   `mission_v1/events.py` and `analysis_report.py` already use) immediately
   before invoking the underlying write path.
2. **Bypass the unbounded dossier-sync trigger, call the write path
   directly**: per NFR-004(b)'s explicitly offered mitigation, `record-analysis`
   calls `write_analysis_report`/`commit_for_mission`
   (`src/specify_cli/analysis_report.py`) directly rather than going through
   `record_analysis`'s full wrapper — `record_analysis`'s own
   `trigger_feature_dossier_sync_if_enabled` call
   (`mission_record_analysis.py:384-388`) is wrapped only in
   `contextlib.suppress(Exception)`, which bounds a *raised* exception but
   not a *hang*. `record-analysis` either (a) excludes that trigger call
   entirely by calling `write_analysis_report` directly instead of the full
   `record_analysis` wrapper, or (b) if `record_analysis`'s other
   preflight/validation logic (dirty-worktree check, placement resolution,
   empty-body check — the early-exit branches at
   `mission_record_analysis.py:228-292`) is worth reusing rather than
   reimplementing, wraps the ENTIRE `record_analysis` call in an explicit,
   enforced timeout (e.g. a thread-based or signal-based bound) at the
   orchestrator-api layer. The WP04 implementer decides between (a)
   and (b) based on how much of `record_analysis`'s preflight logic is
   reusable without the dossier-sync tail; either satisfies NFR-004(b). This
   plan does not pre-decide between them — that is an implementation-detail
   call for WP04, not an architecture decision this plan needs to freeze.
3. **Re-read and correlate**: after the write path returns (or the timeout
   fires), re-read `kitty-specs/<slug>/analysis-report.md` off disk. Report
   `success: true` only if BOTH (a) the re-read `verdict` field matches the
   value THIS call submitted, AND (b) the re-read `generated_at` frontmatter
   timestamp (`analysis_report.py:505-524`) is later than the call-start
   timestamp from step 1. A verdict-string match alone is never sufficient
   (Edge Cases, spec.md).
4. **Testing** (SC-005's three sub-tests, all landing in WP04's test file):
   - (a) *swallowed-exception-but-written*: mock the underlying write call to
     raise, but have the artifact genuinely written (fresh `generated_at`,
     matching verdict) before the mocked raise — assert `success: true` (the
     SK-93 regression guard).
   - (b) *hang-but-written*: mock the underlying write call to block
     indefinitely (e.g. `threading.Event` never set) — assert
     `record-analysis` still returns within its enforced time bound, with
     `success` determined by the re-read, not by waiting for the mocked call.
   - (c) *stale-but-coincidentally-matching-verdict*: pre-seed
     `analysis-report.md` on disk with a verdict equal to the NEW
     submission's verdict but a `generated_at` BEFORE the call-start
     timestamp, and have the mocked underlying write path fail before
     reaching `write_analysis_report` (one of the early-exit branches) —
     assert `success: false` (the SPEC-VERIFY-001 regression guard named in
     SC-005(c)).

---

## (k) Tracer Files

Physically created (not placeholders) at:

- `kitty-specs/design-phase-orchestrator-api-01M1HE6M/tracer-design-decisions.md`
- `kitty-specs/design-phase-orchestrator-api-01M1HE6M/tracer-approach.md`
- `kitty-specs/design-phase-orchestrator-api-01M1HE6M/tracer-tooling-friction.md`

See those files directly; `tracer-design-decisions.md`'s first entry is the
FR-014 seam-extraction/target-module decision from section (a) above.

---

## (l) PR Shape Assessment

This repo's default is ONE PR per mission (`.kittify/charter/charter.md`'s
git/workflow discipline section; `spec-kitty accept`→`merge` assumes one
mission branch), and spec constraint C-004 explicitly requires it for THIS
mission ("Single PR, no follow-up issues... The PR body must carry `Closes
#3837`").

**My assessment: the resulting single PR is at the edge of reviewable-in-one-
sitting, but C-004 is a binding spec constraint, not a plan-phase choice — I
am not overriding it.** Reasoning for the record (for the orchestrator/
operator to weigh, not a decision I am making unilaterally):

- **WP count**: 9 WPs (see breakdown below), one of which (WP02, the seam
  extraction) has real blast radius — it changes a load-bearing CLI command
  module (`next_cmd.py`) that every `spec-kitty next --answer` invocation
  runs through, plus a brand-new runtime module.
- **Estimated diff size**: WP02 (seam extraction + shared regression test) is
  the highest-risk, highest-review-cost WP — a refactor of live control-loop
  code, not additive surface work. WP03–WP07 and WP09 are additive/thin
  (new Typer commands following an established 1:1 pattern, a version bump,
  and docs) — individually low-risk, but 6 WPs' worth of new verb code
  land in the same `commands.py` file, which will produce a large single-file
  diff even though each verb is individually simple. WP08
  (`answer-decision`) is the highest-STAKES WP (SC-007/SC-008's full
  event-log/lifecycle-record parity requirement) even though its own diff is
  moderate, because its correctness depends on WP02 already being correct.
- **Net read**: the blast-radius-heavy WP (WP02) and the highest-stakes WP
  (WP08) are a small fraction of the total diff, but they are also the two
  places a reviewer must slow down and cross-check against live event-log/
  lifecycle-record output — exactly the part of a large PR that's easy to
  skim past when it's bundled with 6 other "just another additive verb"
  diffs.
- **Recommendation** (for the operator, not self-authorized): if PR review
  bandwidth allows, consider asking the reviewing squad to explicitly
  sequence its own read of the single PR — WP02 and WP08 first and in
  isolation, the additive verb WPs (WP03–WP07) second, docs (WP09) last —
  rather than a single linear top-to-bottom diff read. This achieves most of
  the benefit of a per-WP-PR split (isolated scrutiny of the highest-risk
  pieces) without violating C-004's single-PR requirement. I am NOT
  recommending an actual PR split, because C-004 is explicit and binding;
  this is a review-ORDER recommendation within the one PR, not a scope
  recommendation for the operator to overrule C-004.

---

## Work Package Breakdown

| WP | Covers | Depends on | Can run in parallel with |
|----|--------|------------|---------------------------|
| WP01 | Campsite-clean (g) + baseline-red snapshot (f) | — | — (must land first; tiny) |
| WP02 | FR-014 — extract `next_invocation_lifecycle.py` seam; `next_cmd.py` call sites become thin callers; shared regression test (SC-008), landed at `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py` with `pytestmark = pytest.mark.integration` (add `pytest.mark.git_repo` if the fixture-mission setup does a real `git init`) so `diff-coverage`'s enforced `src/runtime/next/*` gate (Gate Set item 4) has real coverage to evaluate | WP01 | WP03, WP04, WP05, WP06 (all independent of the seam) |
| WP03 | FR-001/FR-002/FR-003 — `specify`/`plan`/`tasks` verbs (thin shims over `agent_feature.create_mission`/`setup_plan`/`finalize_tasks`) | WP01 | WP02, WP04, WP05, WP06 |
| WP04 | FR-004/FR-005 — `check-prerequisites`/`record-analysis`, including the NFR-004 artifact-verification mechanism (j) | WP01 | WP02, WP03, WP05, WP06 |
| WP05 | FR-006–FR-009/FR-012 — `open-decision`/`resolve-decision`/`defer-decision`/`cancel-decision` + `OriginFlow` guard (Mechanism A) | WP01 | WP02, WP03, WP04, WP06 |
| WP06 | FR-010 — `design-status` (narrow read-only reduction, per Clarification 6 — does NOT delegate to `resolve_next_workflow_action` or `decide_next`) | WP01 | WP02, WP03, WP04, WP05 |
| WP07 | FR-011 — `CONTRACT_VERSION` bump to 1.4.0 + changelog comment | WP03, WP04, WP05, WP06, WP08 (must name every verb landed so far) | — (naturally lands after the verb WPs; see note below) |
| WP08 | FR-013 — `answer-decision` (Mechanism B), full event/lifecycle parity (SC-007); extends WP02's shared `tests/specify_cli/next/test_next_invocation_lifecycle_seam.py` (not a new/rewritten test file, and keeps WP02's `pytestmark`) with the orchestrator-api path | **WP02 (hard dependency — cannot start until the seam exists)** | WP03, WP04, WP05, WP06 (independent of those) |
| WP09 | SC-006 — `docs/api/orchestrator-api.md`, `host-boundary-rules.md` Boundary Decision Matrix, `CHANGELOG.md` | WP03, WP04, WP05, WP06, WP07, WP08 (documents the landed behavior, not the planned behavior) | — (naturally lands last) |

**Sequencing summary**: WP01 first (tiny, unblocks everything). WP02
(seam) and WP03/WP04/WP05/WP06 (independent additive verbs) can then run in
parallel — WP02 does NOT block the additive verbs, only WP08. WP08
(`answer-decision`) waits on WP02 specifically (C-005's binding sequencing:
FR-014 before FR-013), not on WP03–WP06. WP07 (contract-version bump) is its
own tiny WP rather than folding into the last-landing verb WP, because it
needs to name ALL 11 new verbs in its changelog comment and is trivial to
review in isolation — it naturally lands after WP03–WP06 and WP08 are known-
complete (their verb names are fixed), but has no functional dependency
forcing a specific WP to carry it. WP09 (docs) lands last, documenting
actual landed behavior rather than the plan's prediction of it.

This ordering and the FR-014-before-FR-013 dependency are recorded here so
the tasks-phase author does not have to re-derive them from the spec's
Clarification 7 / C-005 text.

## Project Structure

### Documentation (this mission)

```
kitty-specs/design-phase-orchestrator-api-01M1HE6M/
├── plan.md                        # This file
├── tracer-design-decisions.md     # FR-014 seam decision + future design decisions
├── tracer-approach.md             # WP sequencing approach
├── tracer-tooling-friction.md     # Friction log
└── tasks/                         # Phase 2 output (tasks phase, not this plan)
```

### Source Code (repository root)

```
src/
├── runtime/next/
│   └── next_invocation_lifecycle.py   # NEW (WP02) — the FR-014 shared seam
├── specify_cli/
│   ├── cli/commands/next_cmd.py       # MODIFIED (WP02) — call sites become thin callers
│   └── orchestrator_api/
│       ├── commands.py                # MODIFIED (WP03–WP06, WP08) — 11 new @app.command verbs
│       └── envelope.py                # MODIFIED (WP07) — CONTRACT_VERSION 1.3.0 → 1.4.0
├── charter/offering/skills/spec-kitty-orchestrator-api-operator/references/
│   └── host-boundary-rules.md         # MODIFIED (WP09) — Boundary Decision Matrix rows

docs/
├── api/orchestrator-api.md            # MODIFIED (WP09) — 11 new verb sections
└── changelog/CHANGELOG.md             # MODIFIED (WP09)

tests/
├── specify_cli/orchestrator_api/      # NEW test modules per WP03–WP06,WP08 + existing 4 re-run
├── specify_cli/next/
│   └── test_next_invocation_lifecycle_seam.py   # NEW (WP02, extended WP08) — SC-008 shared
│                                                 # regression test; placed here (matching the
│                                                 # existing test_runtime_bridge.py /
│                                                 # test_runtime_bridge_dispatch.py precedent for
│                                                 # other src/runtime/next/ modules) AND marked
│                                                 # `pytestmark = pytest.mark.integration` (add
│                                                 # `pytest.mark.git_repo` if it needs a real git
│                                                 # repo fixture) — directory alone does not select
│                                                 # it into fast-tests-next / integration-tests-next;
│                                                 # both jobs also filter by marker, and this test's
│                                                 # real file I/O is not `fast`-eligible. Correct
│                                                 # placement + marker together make it count toward
│                                                 # the enforced diff-coverage src/runtime/next/*
│                                                 # gate (Gate Set item 4)
└── specify_cli/cli/commands/
    └── test_next_*.py                 # existing — re-run for behaviour preservation (C-005)
```

**Structure Decision**: Single-project layout (existing spec-kitty CLI
monorepo). No new top-level package. The only new module is
`src/runtime/next/next_invocation_lifecycle.py` (WP02); every other change
extends an existing file.

## Complexity Tracking

*No constitution violations identified — table intentionally empty.*

## Parallel Work Analysis

### Dependency Graph

```
WP01 (campsite-clean, baseline-red)
  │
  ├──> WP02 (FR-014 seam) ──────────────────┐
  ├──> WP03 (FR-001–003)                    │
  ├──> WP04 (FR-004/005)                    │
  ├──> WP05 (FR-006–009/012)                │
  └──> WP06 (FR-010)                        │
                                             ▼
                                        WP08 (FR-013, depends on WP02)

WP03,WP04,WP05,WP06,WP08 all complete ──> WP07 (FR-011 contract bump)
WP03,WP04,WP05,WP06,WP07,WP08 all complete ──> WP09 (docs)
```

### Work Distribution

- **Sequential work**: WP01 first; WP08 strictly after WP02; WP07 after all
  verb WPs (WP03–WP06, WP08); WP09 last.
- **Parallel streams**: WP02, WP03, WP04, WP05, WP06 are mutually independent
  once WP01 lands — up to 5 concurrent WP lanes.
- **Agent assignments**: WP02 touches `next_cmd.py` + new
  `runtime/next/next_invocation_lifecycle.py` — no other WP touches either
  file, so no ownership conflict with WP03–WP06/WP08 (all of which touch only
  `orchestrator_api/commands.py`, additively, in non-overlapping functions).
  WP03–WP06 and WP08 all land in `orchestrator_api/commands.py` — tasks phase
  should sequence their merges (not necessarily their implementation) to
  avoid same-file merge conflicts, per this repo's ownership-map-leeway
  standing order (no-overlap is the real guard, not strict file exclusivity).

### Coordination Points

- **Sync schedule**: WP08 cannot open/merge before WP02 is merged (hard
  functional dependency — `answer-decision` imports
  `next_invocation_lifecycle.py`, which does not exist until WP02 lands).
- **Integration tests**: the SC-008 shared regression test
  (`tests/specify_cli/next/test_next_invocation_lifecycle_seam.py`, marked
  `pytestmark = pytest.mark.integration` — see Gate Set item 4 and
  § Project Structure for why this location and marker, not
  `tests/specify_cli/cli/commands/` or an unmarked/`fast`-marked module) is
  written RED against the CLI
  path in WP02 (proving the seam is behaviour-preserving for `next_cmd.py`),
  then EXTENDED (not rewritten) by WP08 to add the orchestrator-api
  `answer-decision` path — both paths exercised by the same shared
  fixture/helper, so a regression in EITHER caller fails the same test file.
