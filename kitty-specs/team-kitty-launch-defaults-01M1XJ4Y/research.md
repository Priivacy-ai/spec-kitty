# Research: Team Kitty launch defaults for the CLI

**Mission**: team-kitty-launch-defaults-01M1XJ4Y · **Date**: 2026-09-07
**Ground truth read**: spec-kitty `d6e8fe423`, EXPERIMENTAL-zeitgeist `9b6553e`,
EXPERIMENTAL-spec-kitty-saas `93e2ad2`; model recorded in
`docs/context/team-kitty.md` (PR #3982).

Every item below is a Decision / Rationale / Alternatives record. No
`[NEEDS CLARIFICATION]` markers remain in `plan.md`.

## R1 — The moment path is not gated by the enable flag

- **Decision**: Treat the Zeitgeist moment path as already launch-ready; the
  mission changes nothing on it except deleting the owned-checkout refusal.
- **Rationale**: `status/emit.py::_saas_fan_out` → `status/adapters.py::fire_saas_fanout`
  → `status/zeitgeist_bridge.py` → `zeitgeist_client/transport.py::offer` reads
  no flag; the only import-time gate is `SPEC_KITTY_SYNC_MINIMAL_IMPORT`
  (`adapters.py:364`). Credential resolution (`zeitgeist_client/resolution.py`)
  returns `None` without a session, so an unauthenticated machine performs
  zero network calls ("team admission is the gate").
- **Alternatives**: Re-gating moments behind a new flag — rejected; Zeitgeist
  doctrine has no client opt-in, and the operator confirmed authentication is
  the switch.

## R2 — What the flag actually gates today

- **Decision**: Delete `core/saas_sync_config.py` (`is_saas_sync_enabled`,
  `sync_active`, `saas_sync_disabled_message`, `SAAS_SYNC_ENV_VAR`) and its
  re-export `tracker/feature_flags.py`; make each consumer auth-driven.
- **Consumers (all verified by grep)**: `readiness/coordinator.py:237-249`
  (first gate of the startup nag), `cli/helpers.py:262-276` (calls the
  coordinator), `cli/commands/tracker.py:406,417` (command group + issue
  search exit 1 with the "not enabled" message), `tracker/saas_readiness.py:132-135,267`
  (gate #1 of the readiness ladder), `cli/commands/mission_type.py:293`
  (`--from-ticket`), `cli/commands/agent/tasks_move_task.py:359-372` and
  `tasks_mark_status.py:182-188` (`OWNED_SYNC_UNSUPPORTED`), plus the
  env registry (`core/env.py`), `core/secret_redaction.py`,
  `upgrade/migrations/m_3_2_8_provision_kitty_env.py`, `completion.py:186`.
- **Rationale**: Issue #1621 requires hosted readiness without the flag;
  #2875/#2695 show the flag-plus-logged-out combination fails closed.
- **Alternatives**: Keep `=0` as an escape hatch — rejected by the operator
  (Decision Moment `01M1XM48ZBSJHA3CRSJ45TPY4P`).

## R3 — `OWNED_SYNC_UNSUPPORTED` has no live rationale

- **Decision**: Delete the two preflight refusals; owned checkouts publish
  moments like any checkout.
- **Rationale**: The guard landed in `1fe51a47e` (2026-09-02), a week after
  the sync transport surfaces were removed (`66038e2a5`, 2026-08-25); its
  commit message carries no rationale. With the flag unset an owned
  checkout already reaches `fire_saas_fanout` and publishes. Admission, not
  checkout kind, is the gate.
- **Alternatives**: Skip fan-out with a warning for owned checkouts —
  rejected (Decision Moment `01M1XKZMZH44PGGM0WWW6GRGVV`).

## R4 — Target authority and the D-5 reversal

- **Decision**: `auth/server_target.py::resolve_server_target` becomes the
  single place that knows the packaged default `https://team.spec-kitty.ai`
  (promoted from `auth/config.py::EXAMPLE_HOSTED_SAAS_URL` to
  `DEFAULT_HOSTED_SAAS_URL`), reads `config.toml [team_kitty] server_url`
  (the `[sync]` table is no longer read), and reports its source as one of
  `environment | configuration | packaged_default`. `get_saas_base_url`
  stops raising on an unset env var. A new ADR in `docs/adr/3.x/` records
  the reversal of D-5 ("no hardcoded hosted domain fallback").
- **Rationale**: D-5 was scoped to the opt-in gate (PR #3249) that no longer
  exists; the SaaS PRD (`docs/prds/go-to-market-team-kitty-adoption-prompting.md`)
  names this exact decision as open and requiring its own record; the
  OpenAPI contract already defaults its server to `team.spec-kitty.ai`.
- **Precedence**: env > configuration > packaged default; env-vs-config
  disagreement keeps today's fail-closed `ServerTargetSplitBrain`
  (`_classify_override`) — the packaged default is "no opinion" and never a
  party to a disagreement.
- **Alternatives**: Keep `[sync].server_url` as an alias — rejected without
  deprecation (Decision Moment `01M1XMHB8FWZJR23540JXM6817`).

## R5 — Target visibility already has a seam

- **Decision**: Extend, do not duplicate. `cli/commands/_auth_saas_target.py::print_saas_target`
  already prints the endpoint and `saas_source_name(target)` for `auth status`
  and `auth whoami`; add the `packaged_default` source name, and print the
  same line from `auth login` before the flow starts.
- **Rationale**: C-001 canonical authority.

## R6 — One-time sign-in hint

- **Decision**: The readiness coordinator keeps its single nag hook
  (`cli/helpers.py::_render_nag_if_needed`, stderr-only, JSON-safe) and gains
  a per-machine "sign-in hint shown" marker under the runtime state root
  (same root as the stored session and the readiness snooze state), reset by
  `auth logout`. Interactive only; `OutputPolicy.NON_INTERACTIVE` emits
  nothing new (the existing structured `logged_out_on_connected_teamspace`
  stderr line stays for connected-team cases).
- **Rationale**: Decision Moment `01M1XJ5SYYW8JFK67GFX6H5WXS`; #1091 requires
  machine output to stay deterministic.
- **Alternatives**: Blocking prompt — rejected; no hint — rejected.

## R7 — Opt-outs get honest names

- **Decision**: `SPEC_KITTY_SKIP_PRE_REVIEW_GATE` (read by
  `agent/tasks_move_task.py:1208-1210` in place of `first_set_sync_disable_env`)
  and `SPEC_KITTY_NO_MOMENT_HANDLERS` (read by `status/adapters.py:364`).
  `core/env.py::SYNC_DISABLE_ENV_VARS` and `first_set_sync_disable_env` are
  replaced by two single-purpose accessors; `tests/specify_cli/core/test_env.py`
  and the per-test isolation fixtures that import the tuple follow.
  `spk-run-implement-review/SKILL.md` and `docs/api/environment-variables.md`
  are updated.
- **Rationale**: FR-011, C-002 (Team Kitty vocabulary, no `SYNC_`).

## R8 — Logged-out degrade (#2875, #2695)

- **Decision**: With the flag gone, the remaining fail-closed sites are the
  tracker command group and `--from-ticket`, which must fail with the
  sign-in guidance (`_auth_recovery.py` structured message) instead of the
  "not enabled" message; local mission commands must never consult hosted
  state. No `SAAS_SYNC_UNAUTHENTICATED` code path exists on `main` any more
  (grep: zero hits), so #2695's fatal path is already gone; the mission
  claims both issues and proves the degrade with the recording stub.
- **Alternatives**: none.

## R9 — Test doubles and acceptance surface

- **Decision**: Reuse `tests/zeitgeist_client/test_resolution.py`'s gateway
  fakes for unit red-first; add one recording relay/SaaS stub (HTTP server in
  a thread, counts requests by path) shared by the zero-egress and
  owned-checkout acceptance tests; drive first-run, `auth login` target, and
  `auth status` through the public `spec-kitty` subprocess with an isolated
  `SPEC_KITTY_HOME`, mirroring `tests/integration/test_spec_kitty_home_cli.py`.
- **Rationale**: NFR-002/NFR-005 demand observed zero requests and
  red-first through pre-existing entry points.

## R10 — Cross-cutting gates

- **Decision**: Because `core/env.py`, `pyproject.toml`-adjacent config and
  `.kitty.env` provisioning change, run `tests/architectural/` in full
  (golden-count, no-legacy-terminology, dead-symbol, layer rules, env
  contract tests) in addition to targeted suites; the CI producer environment
  needs no change because it carries no session or token.

## Supply-chain security check

No dependency is added, upgraded, or removed. Registry authenticity,
freshness, lifecycle-script discipline, and Node LTS awareness are therefore
not exercised by this mission; recorded here so the check is not silent.
Adversarial challenge on dependency decisions: **deferred_with_rationale** —
there is no dependency decision to contest. The pre-tasks adversarial squad
covers design findings instead (plan §Squad).
