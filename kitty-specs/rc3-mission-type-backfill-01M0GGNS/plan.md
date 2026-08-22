# Implementation Plan: M0 — mission_type backfill migration

**Branch**: `pr/rc3-mission-type-backfill` | **Date**: 2026-08-21 | **Spec**: [spec.md](./spec.md)
**Input**: Mission spec (finalized; squad #1 + squad #2 folded; operator decision "B" applied)

## Summary

Ship a dedicated, idempotent `spec-kitty migrate backfill-mission-type` command that mints a
**profile-resolving** canonical `mission_type` into every legacy `mission`-only `meta.json`
under `kitty-specs/`, so the upcoming M3 (per-type hard-fail on profile-less types) + M5
(legacy-`mission` resolution dropped) changes are non-breaking. The write side is new; the
census gate is the existing `spec-kitty doctor mission-type --fail-on <states>` (reused, R-2),
with the release-safety predicate corrected to `legacy-key-only,typeless,error`. The writer's
write-vs-skip decision is keyed on **`MissionTypeProfileRepository`** — the same
activation-independent, id-matched, cross-layer profile authority M3 §B consumes — so the
backfill agrees with M3's tolerance by construction (NOT with the audit's pre-M3
activation-based `resolved` split).

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: typer (CLI); `charter.mission_type_key.canonical_mission_type_key`;
`charter.mission_type_profile_repository.MissionTypeProfileRepository` (`.for_project(repo_root)
.get(key)` — the M3-tolerance authority); `specify_cli.core.paths.load_meta_fail_closed` /
`MissionMetaReadError`; `specify_cli.sync.dossier_pipeline.trigger_feature_dossier_sync_if_enabled`.
**Storage**: `kitty-specs/<mission>/meta.json` (JSON, canonical sorted-key form).
**Testing**: pytest (unit + CLI + cross-authority agreement + gate regression).
**Target Platform**: Linux/macOS/Windows CLI.
**Project Type**: single (CLI tool).
**Performance**: the `MissionTypeProfileRepository` is built **once per run** (not per mission),
mirroring the audit's resolve-once NFR posture; full `kitty-specs/` walk well under 2 s.
**Constraints**: pure/fail-closed reads; never overwrite an existing `mission_type`; never
manufacture an M3-breaker; ruff + mypy clean; complexity ≤15; no legacy terminology.
**Scale/Scope**: one new ~180-line domain module, one new CLI command (~60 lines), 3 test files.

## Constitution Check

*GATE: passes.*

- **Single canonical authority** — canonicalizer, the M3-tolerance profile repository, and the
  census gate are all reused, not re-implemented. The `registered ∧ roster` composition the
  earlier draft would have duplicated is **dropped** (writer keys on the profile repo instead),
  so no roster-helper duplication is introduced.
- **Layer rules** — new module in `src/specify_cli/migration/` imports only downward
  (`charter.*`); precedent: `migration/rewrite_shims.py` imports `charter.missions`. No
  `migration → cli` import; the cross-authority test lives in the test layer (R-3).
- **Tiered rigour** — the detection + resolve-before-write decision is core → high rigour
  (per-branch unit tests); the CLI glue is thin → CLI-surface tests.
- **ATDD-first** — every AC has a named test authored red-first; AC-5 is the predicate-correctness
  regression that fails against the rejected predicate.
- **Terminology** — "Mission" in prose; `mission`/`mission_type` only as literal field names.

## Project Structure

```
src/specify_cli/migration/backfill_mission_type.py         # NEW — domain module
src/specify_cli/cli/commands/migrate_cmd.py                # EDIT — add backfill-mission-type command
tests/specify_cli/migration/test_backfill_mission_type.py  # NEW — unit (detection, resolve-before-write, idempotency, partition, non-string, error-isolation)
tests/specify_cli/cli/commands/test_migrate_backfill_mission_type.py  # NEW — CLI (flags, --json shape, exit codes, unknown-slug structured error, needs-manual diagnostic)
tests/specify_cli/test_backfill_mission_type_gate_agreement.py        # NEW — cross-authority + gate red→green + AC-5 unactivated-built-in regression
```

**Structure Decision**: single-project layout; new module peers `backfill_topology.py`.

## Design

### Module `backfill_mission_type.py` (single-field structure from `backfill_topology.py`)

```
MISSION_TYPE_KEY   = "mission_type"
LEGACY_MISSION_KEY = "mission"
# reason strings hoisted to module constants (Sonar S1192)

MissionTypeBackfillAction = Literal["wrote", "skip", "needs_manual_resolution", "error"]

@dataclass MissionTypeBackfillResult:
    feature_dir: Path
    slug: str
    action: MissionTypeBackfillAction
    mission_type: str | None       # resolving key written (action="wrote")
    legacy_value: str | None       # raw legacy value seen (reporting / needs-manual)
    reason: str | None
    dossier_warning: str | None = None   # parity with backfill_identity (F5 / squad-2)

def _profile_resolves(repo: MissionTypeProfileRepository, key: str) -> bool:
    return repo.get(key) is not None        # M3 §B tolerance — activation-independent, id-matched

def backfill_mission_mission_type(feature_dir, *, repo, dry_run=False) -> MissionTypeBackfillResult:
    #  try:
    #   1. no meta.json                          → skip("meta.json not found")
    #   2. load_meta_fail_closed; MissionMetaReadError → error("corrupt json: …")
    #   3. MISSION_TYPE_KEY in meta              → skip("mission_type already present")   # AC-2a byte-identical
    #   4. raw = meta.get(LEGACY_MISSION_KEY)
    #      not isinstance(raw, str) or canonical_mission_type_key(raw) is None → skip("no legacy mission value")  # AC-6, typeless-equiv
    #   5. key = canonical_mission_type_key(raw)
    #      not _profile_resolves(repo, key)      → needs_manual_resolution("no governance profile resolves for '<key>' at any layer")  # AC-4, R-4
    #   6. dry_run? no-write : meta[MISSION_TYPE_KEY]=key; canonical sorted-key write        # AC-2b
    #      → wrote
    #  except Exception as exc: return error(str(exc))   # FR-005 — one bad mission never aborts the walk

def backfill_mission_type_repo(repo_root, *, dry_run=False, mission_slug=None) -> list[MissionTypeBackfillResult]:
    #  build MissionTypeProfileRepository.for_project(repo_root) ONCE
    #  walk kitty-specs/ (sorted); mission_slug given but absent → raise <structured error> (AC-9, NOT silent [])
    #  per mission → backfill_mission_mission_type(...); after: rehash wrote∧¬dry_run via
    #  trigger_feature_dossier_sync_if_enabled (failures → result.dossier_warning, never abort)
```

Notes:
- **Detection (R-3, squad-2 MAJOR-3)**: the `isinstance(raw, str)` guard is mandatory —
  `canonical_mission_type_key` does `raw.strip()` and would `AttributeError` on `{"mission":123}`;
  the audit guards identically. Reproduced from `charter.mission_type_key` only (no CLI import).
- **Predicate (operator B / R-4)**: `MissionTypeProfileRepository.get(key)` — activation-independent.
  Built-in types (`software-dev`/`research`/…) always resolve via shipped profiles, so an
  unprovisioned legacy repo backfills cleanly (this is the whole point of choosing profile-
  resolution over `registered ∧ roster`).
- **Structured unknown-slug error (AC-9, squad-2 MAJOR-4)**: reuse an existing structured error
  (e.g. `specify_cli.mission.MissionNotFoundError`) or define a small module-local one; raise it
  from the repo-walk. Do NOT copy the sibling `logger.warning(...); return []` false-green.
- **Error isolation (FR-005)**: a broad per-mission `except Exception → error("…")` so a single
  malformed mission classifies `error` and never aborts the walk (mirrors the audit's
  `classify_mission_type`).

### CLI command `migrate backfill-mission-type` (in `migrate_cmd.py`)

Option surface mirrors `backfill-identity` (`--json`, `--dry-run`, `--mission SLUG`). `--json`
schema (stable across dry-run/live, AC-7): `{dry_run, summary:{total, wrote, skip,
needs_manual_resolution, error}, results:[{slug, action, mission_type, legacy_value, reason,
dossier_warning}]}`. Exit (FR-007/AC-8): non-zero iff `error>0`; `--dry-run` always 0; clean live 0.
When `needs_manual_resolution>0`, print an actionable diagnostic listing those slugs and clarifying
the fix is "a valid mission type whose governance profile resolves (built-in/org/project), or
activate/author that type" — NOT necessarily a typo (squad-2 BLOCKER-1). Unknown `--mission` slug →
structured error + exit non-zero (FR-008/AC-9).

### Census gate (R-2, R-5) — reused, no code change

- Completeness: `doctor mission-type --fail-on legacy-key-only`.
- Release-safety: `doctor mission-type --fail-on legacy-key-only,typeless,error` (corrected — the
  activation-dependent `unknown`/`activated-unresolvable` states are excluded; they are
  M3-tolerated activation-misses). Documented in changelog/PR + the residual `unknown`-typo gap
  flagged to M3.

## ATDD acceptance tests (named, authored red-first)

| AC | Test (file::name) | Red-first through |
|----|-------------------|-------------------|
| AC-1 | `test_backfill_mission_type.py::test_resolving_candidates_all_written` | `backfill_mission_type_repo` live |
| AC-2a | `::test_already_typed_mission_untouched_byte_identical` | bytes compare after run |
| AC-2b | `::test_written_mission_gains_key_fields_preserved` | JSON-semantic equality + sorted-key form |
| AC-3 | `::test_idempotent_second_run_wrote_zero` | second repo run |
| AC-4 | `::test_nonresolving_value_needs_manual_not_written` | `{"mission":"sofware-dev"}` → needs_manual, key absent, still legacy-key-only |
| AC-5 | `test_..._gate_agreement.py::test_unactivated_builtin_written_and_release_gate_greens` | `{"mission":"research"}`, research NOT activated → written; `--fail-on legacy-key-only,typeless,error` greens (fails vs `registered∧roster`) |
| AC-6 | `test_backfill_mission_type.py::test_non_string_legacy_value_not_candidate_no_crash` | `{"mission":123}` → skip, walk survives |
| AC-7 | `test_migrate_backfill_mission_type.py::test_json_shape_identical_dry_run_and_live` | key-set equality |
| AC-8 | `::test_exit_codes_error_dryrun_clean` | non-zero iff error>0; dry-run 0; clean 0 |
| AC-9 | `::test_unknown_mission_slug_structured_error` | `--mission nope` → exit≠0, structured msg |
| AC-10 | `test_backfill_mission_type.py::test_mixed_repo_partition` | ≥4-mission partition + before→after |
| AC-11 | `test_..._gate_agreement.py::test_completeness_gate_red_then_green` | `doctor mission-type --fail-on legacy-key-only` before/after |
| R-3 | `test_..._gate_agreement.py::test_writer_candidates_equal_audit_legacy_key_only` | cross-authority over corpus incl. blank-type AND non-string (non-vacuous) |
| R-4 | `test_backfill_mission_type.py::test_write_decision_matches_profile_repository` | writer write-set == {legacy-key-only ∧ profile resolves} |

Fixture note: `run_mission_type_audit(repo_root, …)` and `MissionTypeProfileRepository.for_project`
both take an injected root, so synthetic temp repos with `kitty-specs/<slug>/meta.json` drive every
gate/writer assertion red-first (this repo is 410/410 resolved — real fixtures required). Built-in
profiles are read from the shipped dir, so a temp repo need not provision them; a project-layer
custom type needs a synthetic `.kittify/doctrine/mission_types/<t>/governance-profile.yaml`.

## Complexity / correctness tracking

| Concern | Mitigation |
|---------|-----------|
| Per-mission decision CC | flat branch order (skip/skip/skip/needs-manual/write) + broad `except → error`; repo built by caller |
| Unprovisioned/foreign repo | profile-resolution keys on shipped built-in profiles → built-ins resolve without activation; NO silent all-skip (the prior draft's "fail-closed non-zero" claim was FALSE and is dropped) |
| `needs_manual_resolution` UX | actionable FR-007 diagnostic distinguishing "not a valid type / no profile" from "activate the type"; exit stays 0 (gate is the release signal) |
| Sonar S1192 | hoist `MISSION_TYPE_KEY` / `LEGACY_MISSION_KEY` / reason strings to constants |
| Dossier rehash on non-sync consumer | reuse `trigger_feature_dossier_sync_if_enabled` (never raises; short-circuits when no project UUID); failures → `dossier_warning` |

## Parallel Work Analysis

```
WP01 (domain module + unit tests)  ──►  WP02 (CLI command + CLI tests)  ──►  WP03 (gate regression + cross-authority + AC-5 + docs/changelog note)
```

Sequential (single implementer). New test files declare a routed `pytestmark`
(`[pytest.mark.unit, pytest.mark.fast]` for unit/CLI; `regression` for the red-first gate proof)
and avoid `len(x)==int` golden-count sites — the completeness "baselines" for tests under existing
`tests/specify_cli/` dirs reduce to the marker-convention gate + golden-count ceiling; no
`_arch_shard_map.py` / baseline-file edits are needed (those govern only the arch pole roots).

## Out-of-scope confirmations (do not fold)

- Reader convergence of the two `software-dev`-default sites → **M5**.
- Audit-classifier `unknown`/`activated-unresolvable` re-derivation against #3598 → **M3**
  (flagged as coordination; M0 does not edit the shared classifier).
- Manual correction of `needs_manual_resolution` / `typeless` residue → operator / later mission.
- Retiring the legacy `mission` field → later migration.
