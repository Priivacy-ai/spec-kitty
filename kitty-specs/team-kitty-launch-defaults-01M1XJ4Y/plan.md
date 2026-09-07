# Implementation Plan: Team Kitty launch defaults for the CLI

**Branch**: `feat/team-kitty-launch-defaults` | **Date**: 2026-09-07 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/spec.md`

Planning interrogation complete: two plan Decision Moments resolved
(`01M1XMCXWJNG6J8HF4YRQRSF6T` authentication is the switch;
`01M1XMHB8FWZJR23540JXM6817` `[team_kitty] server_url`, no alias), Engineering
Alignment confirmed by the operator. Research record: [research.md](research.md).

## Summary

Make a launch build of the CLI work with Team Kitty out of the box while
removing the last of the retired "sync" vocabulary. Concretely: one target
authority gains a packaged default and a Team Kitty config key with visible
provenance; the hosted enable flag, its gate, and the owned-checkout refusal
are deleted so authentication state is the only switch; two opt-outs get
honest names; a one-time interactive sign-in hint replaces "not enabled"
refusals; and the retirement runs through the bulk-edit occurrence map. The
Zeitgeist moment path itself is untouched (research R1).

## Technical Context

**Language/Version**: Python 3.11+ (repo `pyproject.toml`; CI matrix 3.12)
**Primary Dependencies**: typer, rich, tomli/tomli-w (config.toml), `spec_kitty_events` (moment codec, pinned), stdlib `urllib` in `zeitgeist_client`; no additions
**Storage**: runtime state root files (`SPEC_KITTY_HOME`: stored session, credential TOML store, new sign-in-hint marker, `config.toml`); no database
**Testing**: pytest (`make test-fast` baseline + targeted files), real-git fixtures, recording HTTP stubs (threaded `http.server`), public-CLI subprocess acceptance, `tests/architectural/` in full
**Target Platform**: macOS/Linux developer machines and CI; Windows-critical job for the env/config surfaces
**Project Type**: single Python CLI package (`src/specify_cli`, siblings `src/kernel`, `src/charter`, `src/runtime`, `src/mission_runtime`)
**Performance Goals**: unauthenticated commands add 0 network time; authenticated lane move with unreachable relay completes within the existing 10 s fan-out bound, typically < 1 s (NFR-001)
**Constraints**: zero hosted requests when unauthenticated (NFR-002); byte-identical machine output with/without session except contracted fields (NFR-003); no credential in any output (NFR-004); red-first evidence for every change (NFR-005); layer chain `kernel <- charter <- {glossary, runtime, mission_runtime} <- specify_cli` untouched
**Scale/Scope**: ~12 source modules, ~10 test modules, 3 docs pages, 1 ADR, 1 migration var list, 1 skill; ~40 retired-identifier occurrences in live code/docs (archives excluded)

## Constitution Check

Charter: `.kittify/charter/charter.md` (loaded via `charter context --action plan`).

| Gate | Verdict | Evidence |
|---|---|---|
| Single canonical authority | PASS | target: `auth/server_target.py` only; visibility: `_auth_saas_target.py` only; gate removal deletes a second reading rather than adding one (C-001) |
| Architectural alignment / layer rules | PASS | all edits inside `specify_cli`; no new cross-layer import |
| ATDD-first / red-first | PASS | contracts/acceptance.md A1–A11 each name an entry point on the base |
| Terminology canon | PASS | new names use Team Kitty vocabulary; `[sync]` and `SYNC_*` retired; `docs/context/team-kitty.md` is the term authority |
| Decision documentation (DIRECTIVE_003) | PASS with action | D-5 reversal ADR is WP01, lands before the target-authority change (WP02 → WP01); independent lanes (WP05, WP06) may start in parallel (C-005) |
| Bulk-edit guardrail (DIRECTIVE_035) | PASS | `occurrence_map.yaml` present, all 8 categories, archives excepted |
| Smallest viable diff / locality | PASS | no refactor of the moment path; the readiness coordinator gains one marker, nothing else |
| Adversarial squad cadence | PLANNED | post-tasks anti-laziness squad before implement; pre-merge squad before hand-off |
| Mission hygiene / tracker | DONE at planning close-out | #1621, #3980, #2875, #2695 claimed (assignee + comment naming this mission); issue-matrix rows and verdicts in WP10 (C-006) |
| Supply-chain safety | N/A, recorded | no dependency change (research §Supply-chain) |

Re-check after Phase 1 design: no new violations; Complexity Tracking stays empty.

## Project Structure

### Documentation (this mission)

```
kitty-specs/team-kitty-launch-defaults-01M1XJ4Y/
├── plan.md                 # this file
├── research.md             # R1–R10 + supply-chain record
├── data-model.md           # HostedTarget, AuthenticationState, SignInHintMarker, opt-outs
├── quickstart.md           # manual verification script
├── occurrence_map.yaml     # bulk-edit classification (approved by operator before implement)
├── contracts/
│   ├── target-resolution.md
│   ├── auth-visibility.md
│   ├── moment-path.md
│   ├── environment-and-config.md
│   └── acceptance.md
└── tasks.md                # /spec-kitty.tasks output (not created here)
```

### Source Code (repository root)

```
src/specify_cli/
├── auth/
│   ├── config.py                 # DEFAULT_HOSTED_SAAS_URL; get_saas_base_url returns env|None
│   └── server_target.py          # packaged default, [team_kitty] server_url, source reporting
├── cli/commands/
│   ├── _auth_saas_target.py      # source name incl. packaged default; used by login too
│   ├── _auth_login.py            # prints target line before the flow
│   ├── _auth_logout.py           # resets the sign-in hint marker
│   ├── tracker.py                # gate removed; logged-out → sign-in guidance
│   ├── mission_type.py           # --from-ticket gate removed
│   └── agent/
│       ├── tasks.py              # --skip-pre-review-gate help text; SPEC_KITTY_SKIP_PRE_REVIEW_GATE
│       ├── tasks_move_task.py    # delete OWNED_SYNC_UNSUPPORTED preflight; opt-out re-keyed
│       └── tasks_mark_status.py  # delete OWNED_SYNC_UNSUPPORTED preflight
├── core/
│   ├── env.py                    # two named opt-out accessors; SYNC_DISABLE_ENV_VARS deleted
│   ├── saas_sync_config.py       # DELETED
│   └── secret_redaction.py       # allowlist follows
├── readiness/coordinator.py      # gate removed; sign-in hint marker
├── status/adapters.py            # import gate → SPEC_KITTY_NO_MOMENT_HANDLERS
├── tracker/
│   ├── feature_flags.py          # DELETED (re-export)
│   └── saas_readiness.py         # gate #1 removed; MISSING_HOST_CONFIG removed
├── upgrade/migrations/m_3_2_8_provision_kitty_env.py   # var lists
└── completion.py                 # help text

src/charter/offering/skills/spk-run-implement-review/SKILL.md   # opt-out guidance
docs/adr/3.x/2026-09-07-1-packaged-hosted-target-default.md      # NEW: D-5 reversal
docs/api/environment-variables.md                                # table
docs/context/team-kitty.md                                       # "what the flag gates" section rewritten
CHANGELOG.md                                                     # entry

tests/
├── auth/test_server_target.py                       # precedence matrix, source
├── specify_cli/core/test_env.py                     # new accessors
├── specify_cli/cli/commands/test_auth_*.py          # visibility lines, logout reset
├── readiness/                                       # hint once, non-TTY clean
├── specify_cli/cli/commands/agent/                  # owned-checkout moves publish
├── zeitgeist_client/                                # existing fakes reused
├── integration/test_launch_defaults_acceptance.py   # NEW: A1–A8 via public CLI + recording stubs
└── architectural/                                   # full run (cross-cutting)
```

**Structure Decision**: single-package CLI; every change lands in existing modules except one new ADR and one new acceptance test module. No new package, no new layer edge.

## Implementation Concern Map

| ID | Concern | Requirements | Owned surfaces | Notes |
|---|---|---|---|---|
| IC-01 | Record the D-5 reversal | C-005 | new ADR in `docs/adr/3.x/`, `docs/adr` README index | must merge before IC-02 lands; states packaged default, precedence, why D-5 no longer applies |
| IC-02 | Target authority: packaged default, `[team_kitty]` key, source | FR-001, FR-002, FR-003, FR-012 | `auth/config.py`, `auth/server_target.py`, `saas_client/auth.py`, `tests/auth/test_server_target.py` | `[sync]` never read; split-brain unchanged; `MISSING_HOST_CONFIG` removed by IC-04 once this lands |
| IC-03 | Target visibility | FR-004, NFR-004 | `_auth_saas_target.py`, `_auth_login.py`, `_auth_status.py` tests | one printer; JSON fields `target.url`/`target.source`; redaction test |
| IC-04 | Delete the gate and the owned-checkout refusal | FR-007, FR-008, FR-009, FR-010, FR-012 | `core/saas_sync_config.py` (delete), `tracker/feature_flags.py` (delete), `tracker/saas_readiness.py` (gate #1 + `MISSING_HOST_CONFIG`), `tasks_move_task.py`, `tasks_mark_status.py`, `mission_type.py`, `tracker.py`, `cli/helpers.py` | red-first: owned-checkout move publishes; tracker logged-out → guidance |
| IC-05 | Named opt-outs | FR-011, C-002 | `core/env.py`, `status/adapters.py`, `agent/tasks.py`, `tasks_move_task.py:1208`, isolation fixtures, `spk-run-implement-review/SKILL.md`, `tests/specify_cli/core/test_env.py` | keep `--skip-pre-review-gate` flag; env accessor per name |
| IC-06 | Readiness: always evaluated, one-time hint, logged-out degrade | FR-005, FR-006, FR-010, FR-013, NFR-003 | `readiness/coordinator.py`, `readiness/render.py`, `readiness/hint_state.py`, `cli/helpers.py`, `_auth_logout.py` | marker under runtime state root; non-TTY unchanged; #2875/#2695 evidence |
| IC-07 | Provisioning, redaction, registry follow | FR-014, FR-012 | `m_3_2_8_provision_kitty_env.py`, `secret_redaction.py`, `completion.py`, `docs/api/environment-variables.md` | never seed retired names; never invent values |
| IC-08 | Vocabulary sweep under the occurrence map | C-002, C-003, SC-005 | live `src/`, `docs/` (non-archive), skills, `CHANGELOG.md`, `docs/context/team-kitty.md` | archives untouched; `git grep` witness A10 |
| IC-09 | Acceptance and gates | NFR-001, NFR-002, NFR-005, SC-001–SC-006 | `tests/integration/test_launch_defaults_acceptance.py` (new), recording stubs, `tests/architectural/` full | A1–A11 in contracts/acceptance.md |
| IC-10 | Tracker hygiene and issue matrix | FR-011 (spec), C-006 | `issue-matrix.json`, GitHub claims on #1621/#3980/#2875/#2695 | references #3154, #3892, #3277 without closing |

## Sequence: target resolution and the hint

```mermaid
flowchart TD
    A[any hosted caller] --> B{SPEC_KITTY_SAAS_URL set?}
    B -- yes --> C{config [team_kitty] server_url set and different?}
    C -- yes --> X[fail closed: split-brain naming both]
    C -- no --> E[source = environment]
    B -- no --> D{config [team_kitty] server_url set?}
    D -- yes --> F[source = configuration]
    D -- no --> G[source = packaged_default: https://team.spec-kitty.ai]
    E & F & G --> H[auth login / auth status print target + source]
```

Alt text: environment wins, configuration second, packaged default last; only an environment-versus-configuration disagreement fails closed; every path prints its provenance.

## Parallel Work Analysis

### Dependency Graph

```
IC-01 ADR ──► IC-02 target ──► IC-03 visibility
                    │
IC-05 opt-outs ─────┼──► IC-04 gate + guard deletion ──► IC-06 readiness/hint ──► IC-09 acceptance ──► IC-10 hygiene
                    │
IC-07 provisioning ─┘         IC-08 vocabulary sweep (after IC-04/IC-05 settle the names)
```

### Work Distribution

- **Sequential**: IC-01 before IC-02 (governance); IC-02 before IC-03 (needs `source`); IC-04/IC-05 before IC-08 (names must exist before the sweep); IC-09 last.
- **Parallel streams**: {IC-02→IC-03}, {IC-05}, {IC-07} can start together; IC-04 and IC-06 share `readiness/coordinator.py` and `cli/helpers.py`, so they are one lane or strictly ordered.
- **Ownership**: no two lanes own the same file; `readiness/*` + `cli/helpers.py` belong to the IC-04/IC-06 lane; `core/env.py` + `status/adapters.py` + `agent/tasks*.py` opt-out lines belong to IC-05; `tasks_move_task.py` is split by hunk between IC-04 (preflight deletion) and IC-05 (line 1208 re-key) — assign both to one lane to avoid overlap.

### Coordination Points

- Consolidation via `spec-kitty merge` into local `main` after every lane is approved; then compaction and rebase; the PR opens from the PR-bound mission branch `feat/team-kitty-launch-defaults` targeting `main` (the mission was created PR-bound on that branch; no `issue-<n>` rename).
- Integration evidence: A1–A11 run on the consolidated branch; `tests/architectural/` full; terminology guard.
- Squads: post-tasks anti-laziness pass (fakeable DoDs), pre-merge cross-base sweep.

## Complexity Tracking

No constitution violations to justify.
