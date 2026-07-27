# Implementation Plan: Fix sync strict-JSON ingress-skip auth

**Branch**: `fix/sync-strict-json-auth` | **Date**: 2026-06-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `kitty-specs/sync-strict-json-auth-01KWA6KN/spec.md`
**Tracker**: [Priivacy-ai/spec-kitty#2254](https://github.com/Priivacy-ai/spec-kitty/issues/2254)

## Summary

`test_mission_create_json_strict_when_sync_skips_ingress` is red on `main` because the test
seeds its encrypted shared-only `StoredSession` at `$HOME/.spec-kitty/auth`, but production
auth storage was intentionally moved to `$SPEC_KITTY_HOME/auth` by commit `a75174917`
(#2171/#2182, 2026-06-26). The subprocess therefore loads no session → is unauthenticated →
`final_sync` emits `sync.server_auth_failure`, and the direct-ingress-skip diagnostic
(`direct ingress skipped` / `direct_ingress_missing_private_team`) never fires because
`resolve_private_team_id_for_ingress` returns silently when `session is None`.

**Approach (from [research.md](./research.md), FR-001 resolved): fix the TEST seeding, not
production.** Production behavior is correct. Re-pin the test's seed directory to the same
`SPEC_KITTY_HOME`-derived `auth/` directory the subprocess reads, correct the stale docstrings,
and preserve every existing assertion — especially the diagnostic-fired stderr guard (C-002),
which is the non-vacuous proof that the genuine ingress-skip path executed.

## Technical Context

**Language/Version**: Python 3.11+
**Primary Dependencies**: pytest (test harness); `specify_cli.auth.secure_storage.FileFallbackStorage` (AES-256-GCM, scrypt key from `hostname:uid`); `specify_cli.auth.session.StoredSession`; `specify_cli.sync` (`_team`, `batch`, `background`, `diagnostics`); `specify_cli.paths` runtime-root resolution (`SPEC_KITTY_HOME`).
**Storage**: Encrypted session file on disk at `$SPEC_KITTY_HOME/auth/session.json` (production); test seeds via the same encryptor into an isolated home.
**Testing**: `pytest tests/sync/test_strict_json_stdout.py -n0` (slow/subprocess test); full `tests/sync/` for regression; serial real-port pass where applicable.
**Target Platform**: Linux/macOS dev + CI (POSIX `FileFallbackStorage` path).
**Project Type**: single (CLI library).
**Performance Goals**: N/A — correctness fix; the test is a subprocess smoke (~45s) and must stay deterministic.
**Constraints**: No production auth change; no SaaS-protocol change; no weakening of the diagnostic-fired assertion (C-002); ruff + mypy clean with no new suppressions; deterministic across `-n0` and parallel runs (NFR-001).
**Scale/Scope**: One test module (`tests/sync/test_strict_json_stdout.py`), seeding helpers `_build_isolated_home` / `_seed_shared_only_session` + their docstrings, plus — after live verification expanded scope (FR-005, see research.md "Live-verification update") — a small production classification fix in `src/specify_cli/sync/diagnostics.py` and its unit/contract tests in `tests/sync/test_final_sync_diagnostics.py`. No auth/path/session-resolution code changed (C-003).

## Charter Check

*GATE: charter present (`.kittify/charter/charter.md`); context loaded in compact mode.*

- **DIR-012** (assign tracker issue to HiC): attempted; blocked by fork-permission limitation (`MOES-Media` can't be assignee on upstream) — recorded in tracers, not satisfiable as written. ✅ acknowledged.
- **DIR-013** (open an issue for pre-existing failures before proceeding): satisfied — #2254 is exactly that issue, filed before this mission. ✅
- **DIR-010/011** (ASCII slug sanitization regression coverage): not applicable — this mission touches no identifier/slug sanitization. ✅
- Terminology canon: no `feature*` aliases introduced; test/docs prose uses canonical terms. Will run the terminology guard before pushing if any prose changes. ✅

No charter violations. No Complexity Tracking entries needed.

## Project Structure

### Documentation (this mission)

```
kitty-specs/sync-strict-json-auth-01KWA6KN/
├── plan.md              # This file
├── spec.md              # Committed
├── research.md          # Phase 0 — root-cause determination (FR-001)
├── checklists/requirements.md
├── decisions/DM-01KWA6Q7…md   # Deferred CI-trigger-scope decision
├── tracers/             # tooling-friction, approach, design-decisions
└── tasks/               # (created by /spec-kitty.tasks)
```

### Source Code (repository root)

```
tests/sync/test_strict_json_stdout.py    # THE fix surface: _build_isolated_home / _seed_shared_only_session + docstrings
# Read-only context (NOT modified):
src/specify_cli/auth/secure_storage/file_fallback.py   # default_store_dir() — production read path
src/specify_cli/paths/windows_paths.py                 # get_runtime_root() honors SPEC_KITTY_HOME
src/specify_cli/sync/_team.py                           # resolve_private_team_id_for_ingress (skip diagnostic)
src/specify_cli/sync/background.py, batch.py, diagnostics.py  # final_sync auth gate + classification
```

**Structure Decision**: Single-project layout. The seeding fix is confined to the one test module;
the auth/path production change that *caused* the drift (#2182) is correct and stays untouched. Live
verification (FR-005) additionally surfaced a benign-ingress-skip **misclassification** that is fixed
in `src/specify_cli/sync/diagnostics.py` (classification only) — see research.md "Live-verification
update". No auth/path/session-resolution code is modified (C-003).

## Implementation Concern Map

### IC-01 — Re-pin test session seeding via the PRODUCTION resolver

- **Purpose**: Make the test seed its encrypted shared-only `StoredSession` into the directory production actually reads, so the subprocess loads it, authenticates, and exercises the genuine direct-ingress-skip path.
- **Approach (revised per post-plan squad):** the seed directory must be derived from the **production resolver evaluated under the subprocess env** — i.e. call `default_store_dir()` / `get_runtime_root().base / "auth"` with `SPEC_KITTY_HOME` set, **not** a hand-reconstructed `Path(env["SPEC_KITTY_HOME"]) / "auth"` string. Anchoring to the resolver means any future change to `default_store_dir()` the test fails to mirror produces a RED seed-vs-read mismatch instead of silent re-drift.
- **Relevant requirements**: FR-002, FR-003, FR-004, FR-005 (test side), C-002, NFR-001, NFR-004.
- **Affected surfaces**: `tests/sync/test_strict_json_stdout.py` — `_build_isolated_home` (compute `auth_dir` via the production resolver under the subprocess env and pass to seeder), `_seed_shared_only_session` (seed at that dir), and the stale docstrings at lines ~244-262 (they claim `Path.home()/".spec-kitty"/"auth"`).
- **Sequencing/depends-on**: none.
- **Risks**: Must not weaken the diagnostic-fired assertion (C-002). The fix's sufficiency rests on the `_team` WARNING reaching subprocess stderr via the CLI's own logging config — **carry the bug OPEN until a live `pytest … -n0` run confirms the genuine path fired (§4 live-evidence)**, not just a green exit. Keep AES/scrypt same-machine decryption intact (seeding via the production encryptor guarantees this).

### IC-02 — Non-vacuous regression lock (drift-class kill + negative auth pin)

- **Purpose**: Lock in the corrected behavior and kill the drift *class* — without a fakeable assertion.
- **Approach (revised per post-plan squad — the proposed path-equality assertion was vacuous):**
  1. The drift-class kill is achieved by IC-01's resolver-anchored seeding (seed dir = production resolver output), so seed-vs-read can't silently diverge again. Do NOT add a tautological `auth_dir == Path(env["SPEC_KITTY_HOME"]) / "auth"` assertion (it can't fail).
  2. Add a **negative pin**: assert `"no valid access token"` / `"Not authenticated"` is **absent** from stderr. This upgrades "a skip diagnostic appeared" into "the session loaded and *that is why* the genuine skip fired" — distinguishing the real path from any future regression that re-breaks session loading.
- **Relevant requirements**: FR-006, NFR-001, C-002.
- **Sequencing/depends-on**: IC-01.
- **Risks**: Keep assertions at the contract level (session loaded → genuine diagnostic fires; auth-failure absent), not coupled to incidental path string layout.

### IC-03 — CI-trigger blind-spot decision (research-gated, likely defer to #2034)

- **Purpose**: Resolve deferred decision `01KWA6Q7…`: whether to broaden the path-filtered `integration-tests-sync` trigger so this class of drift can't hide, or defer to #2034.
- **Relevant requirements**: FR-007, C-004.
- **Affected surfaces**: `.github/workflows/ci-quality.yml` (only if adopted in-mission) OR a documented decision deferring to #2034.
- **Sequencing/depends-on**: independent of IC-01/02; decided with the user after research (research.md recommends deferring to #2034 to keep this fix tight).
- **Risks**: Scope creep (§2 domain-matched-folds-only). Broadening triggers can inflate routine PR CI cost (C-004).
