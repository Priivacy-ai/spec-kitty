# Implementation Plan: Custom Mission Guard Failure Blocking Inert

**Branch**: `fix/custom-mission-guard-3704` (STACKED on `fix/org-tier-expected-artifacts-3703`,
PR #3708 — see Baseline section; do not diff, rebase, or commit against `main`) | **Date**:
2026-08-24 | **Spec**: `kitty-specs/custom-mission-guard-failure-blocking-inert-01M0STY0/spec.md`
**Input**: Feature specification from
`kitty-specs/custom-mission-guard-failure-blocking-inert-01M0STY0/spec.md` (544 lines, AC-1..AC-9,
FR-001..FR-012, NFR-001..NFR-004, C-001..C-005)

**Note**: This plan is traceable to the spec, not a re-litigation of it — the spec already
resolved layering, field shape, and call-site enumeration. Where this plan makes a choice the
spec left open, it is called out explicitly under "Design decisions left to this plan" at the
end.

## Summary

Two convergent defects (issue #3704, corroborated by ledger SK-78/SK-79) make a custom mission
family's guard evaluation permanently vacuous: (1) `evaluate_guards_strict`
(`src/runtime/next/runtime_bridge_cores.py:684`) only dispatches through the 4-key
`_GUARD_TABLES` (lines 676-681); any family outside it either raises
`UnregisteredMissionFamilyError` (caught by 2 of 3 call sites) or degrades straight to `[]`
(`evaluate_guards`, line 699) — so a custom family's manifest is never consulted at all; (2) even
where a manifest IS reached, `_presence_filenames_for`
(`src/runtime/next/runtime_bridge_io.py:841`) unions `required_always` + every
`required_by_step` + `optional_always` with no `blocking:` filter and no org-tier lookup, so a
`blocking: false` entry gates as hard as `blocking: true` (i.e., not at all) and an org-authored
manifest at `<org_root>/missions/<type>/expected-artifacts.yaml` is never reached.

The fix is data-driven, not code-registration: no new `_GUARD_TABLES` entry (this is the
already-decided ADR from `rc3-charter-gate-predicate-inversion-01M0GGT1`,
`docs/adr/3.x/2026-08-21-1-charter-gate-predicate-inversion.md`). Instead, the I/O layer
(`runtime_bridge_io.py`) resolves each family's `blocking:`-filtered, step-scoped artifact name
set via `required_artifacts_for` (`src/specify_cli/runtime/resolver.py:634`, currently orphaned —
excluded from `__all__`, zero production callers) during the same presence-gathering pass that
already builds the family-scoped `present_artifacts` set, threads it onto a new
`ArtifactPresenceSnapshot.blocking_artifact_names: frozenset[str] | None` field, and
`evaluate_guards_strict` — still living in the stdlib-only leaf module
`runtime_bridge_cores.py` — becomes a pure consumer: `None` means "no manifest anywhere, keep
raising `UnregisteredMissionFamilyError`", a real `frozenset` (possibly empty) means "manifest
resolved, evaluate genuinely by set comparison against `present_artifacts`". `required_artifacts_for`
and `_presence_filenames_for` both gain org-tier awareness (via `resolve_org_expected_artifacts`,
already in this branch's history from PR #3708), and `repo_root` is threaded down all 3 real call
sites that currently drop it on the floor (FR-004's numbered list).

## Technical Context

**Language/Version**: Python 3.11+ (charter floor; `sys.stdlib_module_names` gate requires 3.11+)
**Primary Dependencies**: none new — reuses `charter.missions.MissionTemplateRepository`,
`charter.org_expected_artifacts.resolve_org_expected_artifacts` (already merged via #3703/#3708),
`charter.drg.org_pack_config.resolve_org_roots`, `doctrine.missions.step_projection.project_artifact_name_set`,
Pydantic (`ExpectedArtifactManifest`, `extra="forbid"`)
**Storage**: N/A (filesystem manifest reads only, no new persistence)
**Testing**: pytest, existing markers (`fast`, `architectural`); named regression files below
**Target Platform**: spec-kitty CLI runtime (`src/runtime/next/`, `src/specify_cli/runtime/`,
`src/doctrine/missions/`) — no platform-specific code
**Project Type**: single project (spec-kitty monorepo, `src/` + `tests/`)
**Performance Goals**: N/A — no hot-path/latency requirement stated; guard evaluation is a
per-`next`-call filesystem stat + manifest parse, already the existing cost shape
**Constraints**: `runtime_bridge_cores.py` MUST stay a zero-dependency stdlib+`runtime.next.decision`
leaf (live gate: `tests/architectural/test_bridge_cores_import_boundary.py`) — this is the
single hardest constraint on the design, see "Seam and module placement" below
**Scale/Scope**: 4 source files touched in `src/` (`runtime_bridge_cores.py`,
`runtime_bridge_io.py`, `runtime_bridge.py`, `runtime_bridge_composition.py`) + 2 in
`src/specify_cli/runtime/resolver.py` + `src/doctrine/missions/step_projection.py` is
**read, not edited** (see FR-006 rationale below — the fix bypasses `project_artifact_name_set`
for the blocking signal, it does not change it)

## Constitution / Charter Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Single canonical authority** (charter Governing Principles): satisfied — no second
  guard-dispatch table is added; `_GUARD_TABLES` stays the sole code-registration authority for
  the 4 built-in families, and `required_artifacts_for` becomes the sole manifest-blocking
  authority for everyone else, reusing (not duplicating) `resolve_org_expected_artifacts`.
- **Architectural alignment / module seams**: satisfied by construction — see "Seam and module
  placement" below; this is the plan's central design constraint, not a passing mention.
- **Domain-driven splits + tiered rigour**: `runtime_bridge_cores.py` (core evaluation) gets MORE
  rigour (kept pure, stdlib-only, gate-enforced) than `runtime_bridge_io.py` (I/O glue, where the
  manifest-consulting complexity is pushed).
- **ATDD-first (C-011)**: addressed per-WP below, red-first against
  `fix/org-tier-expected-artifacts-3703`, never `main`.
- **Glossary/terminology**: no new domain terms introduced (`blocking_artifact_names` is a field
  name, not a glossary concept); Contextive gate check under Generated Artifacts below.

No constitution violations requiring a Complexity Tracking entry — this is an additive,
in-seam bugfix with no new project/module boundary.

## Seam and module placement

**Seam**: kernel-adjacent runtime bridge (`src/runtime/next/`), plus its two upstream data
sources (`src/specify_cli/runtime/resolver.py`, org-tier `src/charter/org_expected_artifacts.py`
already merged). Not doctrine, not CLI surface, not sync.

**Exact files and functions** (all line numbers verified live against source, matching the
spec's own citations exactly):

| File | Function/field | Change |
|---|---|---|
| `src/runtime/next/runtime_bridge_cores.py` | `_ArtifactPresenceSnapshotLike` Protocol (line 354) | add `blocking_artifact_names -> frozenset[str] \| None` read-only `@property`, alongside existing `legacy_step_id`/`wp_advance_ready` properties |
| `src/runtime/next/runtime_bridge_cores.py` | `evaluate_guards_strict` (line 684, dispatch miss at line 693) | after `_GUARD_TABLES.get(...)` misses, branch on `snapshot.blocking_artifact_names is None` (FR-002/FR-006) |
| `src/runtime/next/runtime_bridge_io.py` | `_presence_filenames_for` (line 841) | gains `repo_root: Path \| None = None`; also consults org tier via `resolve_org_expected_artifacts` (FR-004 item shape) |
| `src/runtime/next/runtime_bridge_io.py` | `ArtifactPresenceSnapshot` dataclass (line 900) | new field `blocking_artifact_names: frozenset[str] \| None = None` |
| `src/runtime/next/runtime_bridge_io.py` | `gather_artifact_presence` (line 931) | gains `repo_root: Path \| None = None`, forwards it; computes and threads `blocking_artifact_names` (FR-006) |
| `src/runtime/next/runtime_bridge.py` | `_check_cli_guards` (line 751) | gains `repo_root: Path \| None = None`, forwards to `gather_artifact_presence` |
| `src/runtime/next/runtime_bridge.py` | `_dn_dependency_gate` (line 1538; `repo_root = ctx.repo_root` local at line 1549) | forward the already-live local `repo_root` at both `_check_cli_guards` call sites (line 1608, line 1643) — currently dropped |
| `src/runtime/next/runtime_bridge_composition.py` | `_check_composed_action_guard` (line 429) | gains `repo_root: Path \| None = None`, forwards to `gather_artifact_presence` |
| `src/runtime/next/runtime_bridge_composition.py` | `_dispatch_via_composition` (line 502, already REQUIRES `repo_root` as kw) → call site (line 626) | stop dropping `repo_root` when calling `_rb._check_composed_action_guard(...)` |
| `src/specify_cli/runtime/resolver.py` | `_load_expected_artifact_manifest` (line 555) | gains `repo_root: Path \| None = None`, org-aware (FR-008), mirrors `ManifestRegistry.load_manifest`'s FR-008/WP05 parameter shape exactly (`src/specify_cli/dossier/manifest.py:193-233`); **also (FR-010)** wraps its `ExpectedArtifactManifest.model_validate(...)` call in `try/except pydantic.ValidationError`, re-raising `ManifestSchemaError` (imported from `specify_cli.dossier.manifest`, precedented by `specify_cli.sync.namespace`/`specify_cli.sync.dossier_pipeline`'s existing imports of the same type across this sibling-package seam) for both the built-in and the new org-tier branch — closes the uncaught-crash risk the org-tier branch above introduces for schema-invalid manifests |
| `src/specify_cli/runtime/resolver.py` | `required_artifacts_for` (line 634) | gains `repo_root: Path \| None = None`, forwards to `_load_expected_artifact_manifest`; added to `__all__` (lines 46-57); stale WP04b comment (lines 58-66) updated/removed (FR-007, campsite item) |
| `src/doctrine/missions/step_projection.py` | `project_artifact_name_set` (line 128) | **NOT edited.** Confirmed by reading the function in full: it already drops the `blocking` flag by design (flattens `required_always`/`required_by_step`/`optional_always` into one `artifact_key -> path_pattern` dict with no filter) — that is a *different*, still-needed projection (feeds `resolve_configured_artifact_name`/`_presence_filenames_for`'s presence *set*). FR-006 explicitly routes the blocking signal through `required_artifacts_for` instead, which already has its own independent `blocking`-filtering logic (`resolver.py:634-654`, `[spec.path_pattern for spec in specs if spec.blocking]`). No change to this module is required or should be made — its presence in the blast-radius list (per the mission brief) is read-only context, not an edit target. |

**FR-006's layering rule, stated as a hard constraint this plan protects by construction**: the
manifest-consulting logic (calling `required_artifacts_for`, which itself imports
`charter.missions` — non-stdlib) MUST live in `runtime_bridge_io.py`. It MUST NEVER be called
from inside `runtime_bridge_cores.py`. The reason is not stylistic — it is a live, currently
GREEN gate: `tests/architectural/test_bridge_cores_import_boundary.py`, an AST-walk (`ast.walk`,
catches in-function and in-`try` imports, not just module-level ones) that asserts
`src/runtime/next/runtime_bridge_cores.py` imports nothing but stdlib
(`sys.stdlib_module_names`) and `runtime.next.decision`. This plan's design keeps that gate green
**by construction**: `evaluate_guards_strict` only ever reads `snapshot.blocking_artifact_names`
(data already computed and handed to it) — it is never a caller of `required_artifacts_for` or
any manifest-loading function. This plan does not touch, weaken, or relax
`test_bridge_cores_import_boundary.py` in any way; the file is read-only for this mission. Every
WP whose diff touches `runtime_bridge_cores.py` MUST re-run
`uv run pytest tests/architectural/test_bridge_cores_import_boundary.py -v` as part of its own
green verification (not deferred to a later WP or to CI alone).

## Generated artifacts

This mission does **not** touch any generated artifact. Checked explicitly, not assumed:

- **Doctrine schemas** (`src/doctrine/schemas/`, generated from Pydantic models under
  `src/doctrine` by `scripts/generate_schemas.py`, verified in CI by the always-on
  `[ENFORCED] Verify generated doctrine schemas are up to date` step,
  `.github/workflows/ci-quality.yml:653`, running `uv run python scripts/generate_schemas.py
  --check`): grepped `scripts/generate_schemas.py` for `ExpectedArtifactManifest` and
  `ArtifactPresenceSnapshot` — neither appears. `ArtifactPresenceSnapshot` is a plain
  `@dataclass(frozen=True)` in `runtime_bridge_io.py`, not a Pydantic model under `src/doctrine`,
  and this mission does not touch `ExpectedArtifactManifest`'s own model definition (only calls
  the existing `required_artifacts_for`/`_load_expected_artifact_manifest` functions that already
  consume it). No regeneration command applies; the freshness gate runs (always-on) and is
  expected to pass trivially with zero schema drift.
- **Contextive glossary files** (checked by `[ENFORCED] Check Contextive glossary files are
  up-to-date`, `ci-quality.yml:848`): no new domain term is introduced. `blocking_artifact_names`
  is an internal field/parameter name, not user-facing domain vocabulary requiring a glossary
  entry. No regeneration needed.
- **Agent command copies**: this mission adds no new CLI command, slash command, or agent-facing
  surface — it changes internal guard-evaluation plumbing only. No agent command template is
  touched, so no agent-command-copy regeneration applies.

## Contract-moves check

Does this plan move doctrine schemas, mission step contracts, action indices, the
orchestrator-api surface, or the vendored `spec-kitty-events` package? **No.**

FR-006 adds a new field, `blocking_artifact_names: frozenset[str] | None`, to
`ArtifactPresenceSnapshot` — a plain internal dataclass in `runtime_bridge_io.py` — with a
matching read-only `@property` on the structural `_ArtifactPresenceSnapshotLike` Protocol in
`runtime_bridge_cores.py`. This is analyzed as **additive, backward-compatible, and purely
internal**, not a contract move requiring versioning or `spec-kitty-events` coordination,
because:

1. `ArtifactPresenceSnapshot` is a `@dataclass(frozen=True)` with a default (`= None`) for the
   new field — every existing construction call site (test fixtures included) continues to
   compile unchanged; nothing is removed or retyped.
2. The `_ArtifactPresenceSnapshotLike` Protocol gains one additional required property. Its two
   real implementers are `ArtifactPresenceSnapshot` itself (gains the matching field in the same
   commit) and test doubles/mocks under `tests/`, both internal to this repo — the spec's Key
   Entities section states this explicitly ("both existing consumers are internal to this
   repo").
3. Neither type crosses a process boundary, is serialized to JSON/YAML, or is part of the
   orchestrator-api's external HTTP/JSON surface, doctrine's step-contract schema, or the
   vendored `spec-kitty-events` package's event payloads. It is an in-process Python
   dataclass/Protocol pair.

No coordinated `spec-kitty-events` release is needed. This conclusion is stated here as a design
record, not deferred — if a reviewer at a later gate finds a cross-process consumer this plan
missed, that is a plan-phase finding to raise, not a silent reversal.

## Blast radius to downstream workspaces

The Contract-moves check above is correct as far as it goes — `ArtifactPresenceSnapshot` /
`blocking_artifact_names` itself never crosses a process boundary — but that is one hop short of
the full picture, so this section follows the causal chain one hop further, to the field these
internal types feed.

1. **The internal dataclass stays internal, confirmed.** `ArtifactPresenceSnapshot` and
   `blocking_artifact_names` are referenced only inside `runtime_bridge_io.py`/
   `runtime_bridge_cores.py` and their own test files (`tests/runtime/test_bridge_cores.py`,
   `tests/runtime/test_bridge_composition.py`,
   `tests/architectural/test_bridge_cores_import_boundary.py`) — never by
   `orchestrator_api/commands.py` (which uses an unrelated `GateDecision` type) or any
   `spec_kitty_events`-adjacent code. No finding on that narrow claim.
2. **But `evaluate_guards_strict`'s new branch writes its verdict into an already-external
   field.** The new `is None` branch's failure strings populate `Decision.guard_failures: list[str]`
   (`src/runtime/next/decision.py:94`), and `Decision.guard_failures` IS already part of
   `spec-kitty next --json`'s literal external stdout contract:
   `_print_decision()` (`src/specify_cli/cli/commands/next_cmd.py:899-905`) calls
   `decision.to_dict()` and dumps it via `json.dumps(...)` under `--json`; the human-readable path
   (`next_cmd.py:1056-1057`) prints `decision.guard_failures` directly too. So while
   `blocking_artifact_names` never crosses a process boundary, the value it drives DOES — this
   mission changes `guard_failures`'s CONTENT for any custom mission family with a declared
   manifest, not its schema (the field already exists, already typed `list[str]`, already
   serialized).
3. **Concrete downstream risk (this is NFR-002's own point, restated with the mechanism named).**
   Before this mission, `guard_failures` for any family outside `_GUARD_TABLES` was
   unconditionally `[]` — silently "always passing" from any external caller's point of view
   (CI pipelines, the orchestrator-api-operator integration pattern, or a downstream workspace
   such as team-kitty-missions/muster-missions running a custom mission family). After this
   mission, a custom family with a declared manifest will, for the first time, emit real failure
   strings and a `blocked` `Decision.kind` at exactly the steps NFR-002 describes. A downstream
   consumer that has been treating `guard_failures == []` as "this custom family always passes"
   will start seeing real blocks after this mission ships — the change is real and
   operator-visible, "not silently absorbed," per NFR-002.

This documentation obligation is not left unowned: see WP04 in "ATDD-first per WP" and "Phasing /
work-package shape" below, which now carries it as an explicit deliverable.

## SPEC-FRESH-001 preservation — `None` vs `frozenset()` invariant

The `None`-vs-`frozenset()` distinction on `ArtifactPresenceSnapshot.blocking_artifact_names` is
load-bearing and this plan's phased design protects it explicitly, not incidentally:

- **`None`** — "no manifest reachable at any tier" — is determined by `gather_artifact_presence`
  (`runtime_bridge_io.py:931`), reusing the exact tier-checking logic FR-004/FR-005 already run
  for `_presence_filenames_for` (built-in `MissionTemplateRepository.default().get_expected_artifacts(...)
  is None` AND org-tier `resolve_org_expected_artifacts(...) is None`). This determination happens
  ONCE per `gather_artifact_presence` call and is the single source for the field's `None` state
  — never re-derived or inferred elsewhere (e.g., never inferred from an empty list, which would
  silently reopen the exact collapse this mission fixes).
- **A real `frozenset` (including `frozenset()`)** — "a manifest resolved; these are its
  `blocking: true` filenames for this step" — is produced by wrapping
  `required_artifacts_for(step, mission_type, repo_root=...)`'s `list[str]` result in
  `frozenset(...)`. `required_artifacts_for` itself does NOT distinguish "no manifest" from
  "manifest, nothing blocking" (both return `[]`, by its own existing docstring at
  `resolver.py:634-654`) — this plan does not ask it to. `gather_artifact_presence` alone owns
  the `None`-vs-`frozenset` branch; `required_artifacts_for`'s job stays narrowly "give me the
  blocking filenames when a manifest exists," unchanged in its own return contract.

**Function responsible for `None` determination**: `gather_artifact_presence`
(`runtime_bridge_io.py:931`), via its own manifest-reachability check (mirroring
`_presence_filenames_for`'s existing `config is None` / org-tier-equivalent check,
`runtime_bridge_io.py:891-892`).
**Function responsible for producing the real (possibly empty) `frozenset`**:
`required_artifacts_for` (`resolver.py:634`), called by `gather_artifact_presence` once
reachability is confirmed, its `list[str]` wrapped in `frozenset(...)` at the call site in
`gather_artifact_presence` — not inside `required_artifacts_for` itself, which keeps returning
`list[str]` for its own existing unit-tested contract
(`tests/specify_cli/runtime/test_configured_artifact_name.py`).

`evaluate_guards_strict` (`runtime_bridge_cores.py:684`) is the sole consumer of the distinction:
`snapshot.blocking_artifact_names is None` → raise `UnregisteredMissionFamilyError` (FR-002
outcome 1); a real frozenset → evaluate via `snapshot.present_artifacts` ⊇
`snapshot.blocking_artifact_names` set comparison (FR-002 outcomes 2/3). This plan's new code
never collapses these two states into a shared "empty means nothing" branch anywhere — the one
new `if ... is None` check in `evaluate_guards_strict` is the only place either state is
inspected, and it inspects `is None` explicitly, not falsiness (`frozenset()` is falsy in Python
and MUST NOT be tested with a bare `if not snapshot.blocking_artifact_names:` — that would
silently reintroduce SPEC-FRESH-001's exact collapse).

## Upgrade/migration chain

This mission does **not** touch the upgrade/migration chain. Confirmed, not assumed: the blast
radius (`src/runtime/next/*`, `src/specify_cli/runtime/resolver.py`,
`src/doctrine/missions/step_projection.py` [read-only]) has zero overlap with
`src/specify_cli/upgrade/` or any of the ~30 `tests/upgrade/test_*_migration*.py` /
`tests/migrate/` / `tests/migration/` files enumerated by a repo-wide search for migration
surfaces. No migration is added, and no existing migration needs updating for this change (the
new `blocking_artifact_names` field has a default and requires no data migration — see NFR-002
Reflexivity, which is about runtime behavior at the *next* evaluation, not a persisted-state
migration).

## Gate set for this mission

**ENFORCED (applies, with reason):**

- **commitlint** — applies to every commit on this repo regardless of file scope; this mission's
  commits (campsite-clean, per-WP ATDD-red, per-WP implementation) all use conventional-commit
  format via `spec-kitty safe-commit`.
- **markdown lint** (`ci-quality.yml:731`) — applies because this plan and the 3 tracer files are
  markdown; changed-file-scoped, so it lints exactly the files this mission authors.
- **architecture/docs consistency** (`ci-quality.yml:795`, "on changed markdown") — applies for
  the same reason; this mission's markdown changes (plan.md, tracer files) must stay consistent
  with any architecture claims they make (they should not, since they're planning artifacts, but
  the gate is changed-file-scoped so it will run).
- **doctrine schema freshness** (`ci-quality.yml:653`, always-on job) — applies because it is
  always-on, not path-filtered; expected to pass trivially (see Generated Artifacts above — zero
  schema drift from this mission's changes).
- **Contextive glossary** (`ci-quality.yml:848`) — applies for the same always-on reason; expected
  to pass trivially (no new domain terms, see Generated Artifacts above).
- **TID251 banned-API lint** (`ci-quality.yml:883`) — applies repo-wide to any Python this mission
  writes; this mission introduces no banned-API usage (no new subprocess/os.system/etc. calls).
- **Typer JSON error surface** (`ci-quality.yml:896`) — applies repo-wide; this mission does not
  touch any Typer CLI command surface, so it is expected to pass trivially, but the gate itself
  still runs and is not skippable.
- **`patch()` target validation** (`ci-quality.yml:940`) — applies to this mission's own new/edited
  tests, which will use `unittest.mock.patch`/monkeypatch on the functions this plan changes
  (e.g. patching `resolve_org_expected_artifacts`, `required_artifacts_for`); every patch target
  must resolve to a real importable path.
- **Bandit security scan** (`ci-quality.yml:914`) — applies repo-wide; no new security-sensitive
  pattern (no subprocess, no eval, no unsafe deserialization) is introduced by this mission.
- **pip-audit CVE scan** (`ci-quality.yml:929`) — applies repo-wide; this mission adds zero new
  dependencies.
- **`uv.lock` freshness** (`ci-quality.yml:3915`, NFR-005) — applies repo-wide; since no
  dependency changes, `uv.lock` stays untouched and the check passes trivially.
- **Coverage-floored shards**: **the kernel and mission-loader TOTAL-coverage floors do not
  apply, but a THIRD, DIFFERENT-MECHANISM floor — the `diff-coverage` job's 90% DIFF-coverage
  floor — DOES apply and DOES enforced-gate 4 of this mission's 5 blast-radius files.** Verified
  directly against `tests/architectural/_gate_coverage.py` and the workflow files it models, not
  assumed. The first grep pass here only searched for the literal pytest-cov flag string
  `cov-fail-under` and missed `diff-cover`'s bare `--fail-under` flag (no `cov-` prefix) — that
  narrow-grep gap is corrected below.
  - **(a) The kernel 90% TOTAL-coverage floor does not apply.** (`module-kernel.yml:58`,
    `--cov=src/kernel`, `--cov-fail-under` via its own Python enforcement step) measures
    `src/kernel` only. This mission's blast radius has zero files under `src/kernel`.
  - **(b) The mission-loader 90% TOTAL-coverage floor does not apply.**
    (`ci-quality.yml:1437-1456`, job `mission-loader-coverage`,
    `--cov=src/specify_cli/mission_loader --cov-fail-under=90`) measures
    `src/specify_cli/mission_loader` only — a different package this mission does not touch. That
    job DOES run whenever this mission's changes land (its trigger condition includes
    `needs.changes.outputs.next == 'true'`, and this mission's files fall under the `next`
    change-filter, `ci-quality.yml`'s `changes` job, paths `src/specify_cli/runtime/**` and
    `src/runtime/next/**`), but it is measuring an unrelated package's pre-existing coverage, not
    this mission's diff — expected to pass unaffected.
  - **(c) The `diff-coverage` job's 90% DIFF-coverage floor DOES apply and IS ENFORCED for 4 of
    5 blast-radius files.** The `diff-coverage` job (`.github/workflows/ci-quality.yml:3283`,
    runs on every PR unless labeled `pr:deferred`/`pr:skip-ci`) has an enforced step, "diff-coverage
    (critical-path, enforced)" (`ci-quality.yml:3333`), that builds a `critical_paths` shell array
    (`ci-quality.yml:3345-3367`) which literally includes `'src/runtime/next/*'`
    (`ci-quality.yml:3366`), then runs `uv run diff-cover ... --compare-branch=origin/${{
    github.base_ref }} --fail-under=90 --include "${critical_paths[@]}"`
    (`ci-quality.yml:3391-3394`). This directly, by name, diff-coverage-gates every new/changed
    line in 4 of this mission's 5 blast-radius files — `runtime_bridge_cores.py`,
    `runtime_bridge_io.py`, `runtime_bridge.py`, `runtime_bridge_composition.py` (all under
    `src/runtime/next/`) — at a 90% floor on every PR, sourced from the union of uploaded
    coverage XMLs (primarily `fast-tests-next`'s `--cov=src/runtime/next`). This is a real,
    enforced gate, not advisory: the step has no `|| true`/continue-on-error escape, so
    `diff-cover`'s own non-zero exit when new/changed lines fall under 90% coverage fails the
    step (and the job) outright — distinct from the separate `exit 1` at `ci-quality.yml:3388`,
    which only fires when no coverage reports were uploaded at all. Only
    `src/specify_cli/runtime/resolver.py` is NOT in `critical_paths` (it matches no entry in the
    array) and therefore escapes this specific job, falling instead to the "diff-coverage
    (full-diff, advisory)" step (`ci-quality.yml:3396`, non-blocking `|| true`) — the plan's
    original "no floor applies" claim is correct for that one file only, not for the other four.
    The repo's own architectural model (`tests/architectural/_gate_coverage.py:409-410`
    `_CRITICAL_PATHS_RE`, `:574-575` `_diff_cover_critical_paths()`, `:717`
    `diff_cover_critical_paths` field) explicitly tracks this job's critical-path array as a
    first-class CI gate, confirming it is not an obscure or incidental job.
  - **Net effect on tasks/implement**: this mission's `src/runtime/next/*` files ARE
    coverage-gated (enforced, 90% diff), even though neither total-coverage floor applies. Each
    WP touching those files must budget test coverage for its own new/changed lines to avoid
    failing this gate — e.g. WP01's new `blocking_artifact_names is None` branch in
    `evaluate_guards_strict`, WP02's org-tier branches in `_presence_filenames_for`/
    `gather_artifact_presence`, and WP03's `repo_root`-threading call sites in
    `runtime_bridge.py`/`runtime_bridge_composition.py`. `resolver.py` changes remain outside
    this specific job's scope (advisory full-diff step only), but the WPs still write thorough
    tests for it per ATDD-first discipline regardless.

**ADVISORY-ONLY (non-gating), stated explicitly, never "CI will catch it":**

- **`ruff`** — advisory-only in CI on this repo; `make lint` is local discipline only. This
  mission runs `make lint` locally before each WP's commit, but a ruff finding does not block CI
  and is never treated as "CI will catch it."
- **`mypy`** — same: advisory-only in CI, local discipline only via `make lint`. Given this
  mission adds/changes `Path | None = None` parameters and a `frozenset[str] | None` field/
  Protocol property, type-checking locally (`make lint` or `uv run mypy src/runtime/next
  src/specify_cli/runtime/resolver.py`) is worth doing anyway for correctness, but its absence
  from CI enforcement is stated here explicitly, not assumed.

**NOT a PR gate on this repo:**

- **SonarCloud Quality Gate** — does not run on pull requests on this repo (verified 2026-08-22,
  per task brief). Not listed as a gate for this mission.

**Per-WP pytest invocation** (never "we'll run the tests" — see WP table in Phasing below for the
concrete file scope per WP; the shared pattern every WP follows):

```
uv run pytest <WP's specific test file(s)> -v
uv run pytest tests/architectural/test_bridge_cores_import_boundary.py -v   # only for WPs touching cores.py
uv run pytest tests/runtime/test_bridge_parity.py -v                        # regression, every WP touching bridge*.py
uv run pytest tests/runtime/next/test_pertype_presence_gate.py tests/runtime/next/test_cli_guard_family.py -v
uv run pytest tests/specify_cli/runtime/test_configured_artifact_name.py -v # NFR-001 byte-compat
uv run pytest tests/specify_cli/next/test_runtime_bridge_composition.py -v
```

**Coverage budget note**: every WP above touches `src/runtime/next/*`, which the `diff-coverage`
job's enforced 90% diff-coverage floor covers (see "Gate set for this mission" § "Coverage-floored
shards" above) — running the tests above is necessary but not sufficient; each WP's new/changed
lines in those files need ≥90% coverage from that run, not just a passing exit code.

## Baseline

`main` (and therefore this stacked branch, since it descends from `main` via
`fix/org-tier-expected-artifacts-3703`) carries ~23 known-red tests + 2 errors (issue #3284,
already discharging the charter's Pre-existing Failure Reporting Rule for that known set), and a
shared test-venv lock that can time out (issue #3283).

**This mission's true baseline for red/green comparison is the STACKED PARENT
`fix/org-tier-expected-artifacts-3703`, not `main`.** The spec's own NFR-003 states this
explicitly: *"Because this mission is stacked (see Clarifications), red-verification MUST use
`planning_base_branch = fix/org-tier-expected-artifacts-3703`, not `main`"* (spec.md, NFR-003
row). Diffing or red-verifying against `main` would spuriously attribute #3703/PR #3708's ~47
commits (the org-tier path anchor) to this mission.

**Concrete mechanism, per WP, before its first change lands**: each WP re-runs its own narrow
test file scope on `fix/org-tier-expected-artifacts-3703` FIRST (before writing its ATDD-red
test), to establish the true-red baseline for those specific files on the actual parent, e.g.:

```
git fetch origin fix/org-tier-expected-artifacts-3703
uv run pytest tests/runtime/next/test_pertype_presence_gate.py tests/runtime/next/test_cli_guard_family.py \
    tests/runtime/test_bridge_parity.py tests/runtime/test_bridge_cores.py \
    tests/specify_cli/runtime/test_configured_artifact_name.py \
    tests/specify_cli/next/test_runtime_bridge_composition.py -v
# (run against fix/org-tier-expected-artifacts-3703 HEAD, not main, not this branch)
```

Any red found in that narrow scope that is NOT already inside #3284's known ~23-failures-+2-errors
set is a **fresh finding**, not accepted baseline. Per the charter's Pre-existing Failure
Reporting Rule, a new pre-existing failure obliges filing a GitHub issue before being treated as
accepted baseline — **only the operator authorizes that filing**; this authoring session does
not file one. If a WP hits this, it stops and flags the finding in its own commit/report rather
than silently treating it as "probably fine" or working around it.

## Campsite-clean scope (charter Standing Order #2)

**FIRST commit/WP, sequenced tidy-first, behaviour-preserving, folding ONLY domain-matched
debt from the blast-radius files:**

**Folded in** (this mission's own FR-007 already requires it, so it is not scope creep — it is
inside the touched-file set by construction):
- The stale comment at `src/specify_cli/runtime/resolver.py:58-66`, which currently reads
  *"Neither has a runtime caller under src/ outside this module until WP04b wires
  `required_artifacts_for` into the live per-type presence gate... adding either to `__all__`
  before that caller exists reds `tests/architectural/test_no_dead_symbols.py`"* — once this
  mission's own WP wires `required_artifacts_for` into `gather_artifact_presence` (its first real
  cross-module caller), this comment becomes false. FR-007 explicitly requires updating/removing
  it and adding `required_artifacts_for` back to `__all__` (lines 46-57) in the SAME WP that adds
  the caller — not deferred, not left stale. This is domain-matched debt inside the exact file
  this mission already edits for its functional change (`resolver.py`), so it satisfies
  Locality of Change (no new file added) and is licensed by Boy Scout Rule (fixes
  touched-area breakage/staleness this mission itself creates).

**Deferred** (explicitly, with reason — not silently dropped):
- Any broader cleanup of `runtime_bridge.py`/`runtime_bridge_composition.py` beyond the
  `repo_root`-threading this mission's FR-004 requires (e.g., other TODOs or long functions in
  those files unrelated to guard dispatch) — deferred because Locality of Change forbids growing
  the file set or scope beyond what FR-004/FR-006 require; nothing else in those files is
  domain-matched to *this* mission's fix (guard evaluation / manifest reach), so touching it would
  be grab-bag cleanup, not a legitimate campsite item.
- `_presence_filenames_for`'s own long docstring/logic is NOT restructured beyond adding the
  `repo_root` parameter and org-tier branch — C-002 explicitly forbids re-attempting step-scoping
  there, and no other cleanup is domain-matched.

**Sequencing**: this campsite-clean item (resolver.py comment + `__all__`) is folded into the
SAME WP that adds `required_artifacts_for`'s first real caller (Part 2 / WP touching
`gather_artifact_presence`), landing as a distinct commit that immediately FOLLOWS that WP's
functional implementation commit (or is combined into the same commit) — never before it. The
commit order within that WP is: (1) the functional commit that wires `required_artifacts_for`
into `gather_artifact_presence`, giving it its first real caller, then (2) the campsite-clean
commit (stale-comment removal + `__all__` restoration). Reversing that order — landing the
campsite-clean commit first — would add `required_artifacts_for` to `__all__` with zero callers
at that commit and red `tests/architectural/test_no_dead_symbols.py`, the exact failure the
stale comment itself warns about. Cleaning any earlier than the caller existing would be
premature (nothing true to point at yet); leaving it any later than immediately-after would
leave the now-false claim live past its falsification point.

## ATDD-first per WP (charter C-011)

Every WP below needs a failing-first ATDD test as a SEPARATE commit BEFORE its implementation
commit. **Red-first verification for every WP anchors on `fix/org-tier-expected-artifacts-3703`
(the stacked parent), never `main`** — restated per WP here, not just once in Baseline, since a
reviewer working WP-by-WP needs it locally without cross-referencing.

| WP | Extends/adds test file(s) | Red-first anchor |
|---|---|---|
| WP00 (campsite-clean, folded into WP02) | N/A — behaviour-preserving comment/`__all__` change; its commit lands immediately AFTER (or combined with) WP02's functional commit that adds `required_artifacts_for`'s first real caller, never before it; verified by `tests/architectural/test_no_dead_symbols.py` staying green (it would RED if `required_artifacts_for` were added to `__all__` before that caller exists — see "Sequencing" above) | `fix/org-tier-expected-artifacts-3703` |
| WP01 — FR-006 snapshot field + cores.py branch | Extends `tests/runtime/test_bridge_cores.py` (new cases for `evaluate_guards_strict`'s `blocking_artifact_names is None` branch) and `tests/runtime/next/test_pertype_presence_gate.py` (extends `TestCustomFamilyPresenceGateFailsClosedBothDirections`, AC-9's two-family distinguishability case) | `fix/org-tier-expected-artifacts-3703` |
| WP02 — FR-004/FR-008 org-tier threading into `_presence_filenames_for`/`required_artifacts_for`/`_load_expected_artifact_manifest`; FR-010 schema-error handling in the same function | Extends `tests/specify_cli/runtime/test_configured_artifact_name.py` (org-tier cases mirroring `ManifestRegistry.load_manifest`'s existing FR-008/WP05 test shape, plus FR-010's schema-invalid-manifest cases asserting `ManifestSchemaError` for both tiers) and `tests/runtime/next/test_pertype_presence_gate.py` (AC-4/AC-5/AC-6 org-tier + whole-file-replacement scenarios) | `fix/org-tier-expected-artifacts-3703` |
| WP03 — FR-003 call-site convergence (`_check_cli_guards`, `_check_composed_action_guard`, both `_dn_dependency_gate` sites, `_dispatch_via_composition`'s dropped `repo_root`) | Extends `tests/runtime/next/test_cli_guard_family.py` (AC-1/AC-2/AC-8) and `tests/runtime/test_bridge_parity.py` (regression: `test_non_software_dev_missing_artifact_owned_by_composed_guard` stays green, NFR-004) | `fix/org-tier-expected-artifacts-3703` |
| WP04 — NFR-001/AC-3/AC-7/AC-9 full regression sweep + `TestTypelessMissionFamily`/`TestIssue3627WpIterationUnregisteredFamilyDegrades` stay green + NFR-002 documentation deliverable | Runs (does not necessarily extend) `tests/runtime/test_bridge_parity.py::test_coverage_floor_is_met`, `tests/specify_cli/next/test_runtime_bridge_composition.py::TestCustomMissionComposition`, full byte-compat suite; also lands a CHANGELOG.md entry and/or an operator-facing note in tracer-design-decisions.md documenting the `spec-kitty next --json` `guard_failures` behavior change per NFR-002 (see "Blast radius to downstream workspaces" above) — no test file, but a required non-test deliverable of this WP | `fix/org-tier-expected-artifacts-3703` |

## Phasing / work-package shape

The spec's own User Story framing is explicit and this plan reflects it accurately rather than
inventing independence it denies: *"Part 1 alone (real dispatch) has nothing to evaluate without
Part 2's manifest reach, and Part 2 alone (manifest reach) has no consumer without Part 1's
dispatch fix."* Concretely:

- **Part 1** (US1: FR-001/002/003 — dispatch) needs `snapshot.blocking_artifact_names` to exist
  and be populated to have anything to branch on in `evaluate_guards_strict` — that population is
  Part 2's job (FR-006, in `runtime_bridge_io.py`).
- **Part 2** (US2: FR-004/005/006/007/008 — org-tier presence + `blocking:` filtering) produces a
  correctly-filtered `frozenset`, but nothing reads it as a pass/fail signal until Part 1's
  `evaluate_guards_strict` branch exists.

They are therefore **NOT independently shippable WPs** in the sense of "either could merge alone
and be useful" — but they ARE independently *testable* (per each User Story's own "Independent
Test" framing) and can be built as ordered, dependent WPs within the single PR, sequenced so each
has a real (not synthetic) consumer/producer by the time it lands:

1. **WP00 — campsite-clean** (resolver.py stale comment + `__all__`, folded into the WP that adds
   the real caller — see below; listed first here for sequencing clarity, but its commit lands
   immediately AFTER — or combined with — WP02's functional commit that adds the real caller,
   never before it).
2. **WP01 — FR-006's snapshot field + Protocol property + `evaluate_guards_strict`'s branch**,
   built first with the field populated by a **minimal, test-only** stub inside
   `gather_artifact_presence` (not the full org-aware resolution yet) so WP01's own ATDD tests can
   exercise the `None`-vs-`frozenset` branch in `runtime_bridge_cores.py` in isolation, satisfying
   FR-006's own Independent Test framing without waiting on WP02's org-tier plumbing. This keeps
   the import-boundary gate concern (the hardest constraint) isolated to its own reviewable WP.
3. **WP02 — FR-004/005/007/008**: org-tier-aware `_presence_filenames_for`/`required_artifacts_for`/
   `_load_expected_artifact_manifest`, replacing WP01's stub with the real resolution inside
   `gather_artifact_presence`. Folds in WP00's campsite-clean commit immediately after this WP's
   functional commit (the `__all__`/stale-comment fix becomes truthful exactly here, since this
   WP is where `required_artifacts_for` gets its first real caller) — the campsite-clean commit
   is never the first commit of this WP.
4. **WP03 — FR-003 convergence**: thread `repo_root` through all 3 real call sites
   (`_check_cli_guards`, `_dn_dependency_gate`'s two call sites, `_check_composed_action_guard`,
   `_dispatch_via_composition`'s dropped forward) so the org-tier reach from WP02 is genuinely
   live end-to-end (AC-8), not just reachable in a unit test that calls the leaf function
   directly.
5. **WP04 — full regression/NFR sweep**: NFR-001 byte-compat, AC-3/AC-7/AC-9, coverage-floor
   (`test_coverage_floor_is_met`), and the frozen-template e2e walk
   (`TestCustomMissionComposition`) all stay green; AC-10 end-to-end demonstration at the
   conventional `<org_root>/missions/<type>/` layout (only reachable now that this branch is
   stacked on #3708's path fix, per the operator's stacking rationale in spec.md's
   Clarifications). **Also owns NFR-002's documentation deliverable**: a CHANGELOG.md entry
   and/or an operator-facing note in tracer-design-decisions.md stating that
   `spec-kitty next --json`'s `guard_failures`/`Decision.kind` output for custom mission
   families with a declared manifest changes content (a family that previously always emitted
   `guard_failures == []` can now emit real failure strings and a `blocked` decision) — see
   "Blast radius to downstream workspaces" above for the mechanism.

This sequencing is presented as informational input to the tasks phase, not a final WP cut — the
tasks phase may re-slice WP boundaries, but MUST preserve this dependency order (WP01's snapshot
field before WP02's real population before WP03's call-site threading before WP04's full sweep)
since the spec denies true parallelism between Part 1 and Part 2.

## Project Structure

### Documentation (this mission)

```
kitty-specs/custom-mission-guard-failure-blocking-inert-01M0STY0/
├── spec.md                        # already exists, spec phase PASSED
├── plan.md                        # this file
├── tracer-tooling-friction.md     # seeded at planning (flat path, not traces/)
├── tracer-approach.md             # seeded at planning (flat path, not traces/)
├── tracer-design-decisions.md     # seeded at planning (flat path, not traces/)
├── reviews/                       # spec-phase review trail (existing)
├── checklists/, research/, tasks/ # existing scaffold dirs
└── status.events.jsonl            # existing
```

### Source Code (repository root) — Structure Decision

Single project (this repo IS the tooling, no web/mobile split applies). No new top-level
directory is created; every change lands inside the existing `src/runtime/next/`,
`src/specify_cli/runtime/`, and (read-only reference) `src/doctrine/missions/` trees, with
matching test additions inside the existing `tests/runtime/`, `tests/specify_cli/runtime/`,
`tests/specify_cli/next/`, and `tests/architectural/` trees — see the Seam and module placement
table above for the exact file list. No new file is added by this mission (Locality of Change);
every change is an edit to an existing file.

## Complexity Tracking

No constitution/charter violations requiring justification — this is an in-seam, additive,
backward-compatible bugfix with no new project structure, no new dependency, and no relaxed gate.

## Design decisions left to this plan (spec was silent or this plan chose among options)

The spec is unusually prescriptive (exact file:line citations, exact function signatures, exact
call-site enumeration for FR-004's 3 sites) — this plan found only a small number of places where
it had genuine room to choose:

1. **WP boundary cut** (how many WPs, and the WP00-campsite-fold-into-WP02 sequencing): the spec
   states the Part1/Part2 coupling constraint but does not mandate a specific WP count or
   ordering beyond that constraint. This plan chose a 5-WP shape (WP00 folded into WP02) that
   isolates the import-boundary-sensitive change (WP01) into its own small, easily re-reviewed
   unit, and defers the harder org-tier plumbing to WP02. A different valid cut could merge WP01
   into WP02 directly; this plan's choice trades one extra WP for a smaller, more auditable single
   diff against the hardest gate (`test_bridge_cores_import_boundary.py`).
2. **WP01's test-only stub for `blocking_artifact_names`** before WP02 lands the real org-tier
   resolution: the spec does not require staging the field's population in two steps — this is
   this plan's own choice to let WP01's ATDD tests exercise `evaluate_guards_strict`'s new branch
   without depending on WP02's not-yet-written org-tier code, consistent with each User Story's
   own "Independent Test" framing. An alternative (build both in one WP) is also spec-compliant;
   this plan's staging is a testability/reviewability preference, not a spec requirement.
3. **Exact wording of the Contract-moves-check conclusion** (additive/internal, no
   `spec-kitty-events` coordination needed): the spec strongly suggests this reading (Key
   Entities: "both existing consumers are internal to this repo") but does not use the words
   "contract move" itself — this plan makes that classification explicit, as the task instructed,
   rather than leaving it implicit.

No spec contradiction was found. The one place worth flagging for the review squad: the spec's
own blast-radius framing names `doctrine/missions/step_projection.py` as an in-scope file, but
this plan's analysis concludes it should NOT be edited (see the Seam and module placement table's
final row) — `project_artifact_name_set` is a different, still-correct projection that FR-006
deliberately routes around rather than modifies. This plan treats "blast radius" as "read to
understand," not "necessarily edited," and flags this reading for adversarial-squad scrutiny
since it is the one place this plan actively did NOT touch a file the mission brief listed.
