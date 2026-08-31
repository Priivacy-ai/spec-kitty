# Data Model & Landmines

Mostly small fixes + one rebase. The "data model" is the surfaces changing and the landmines constraining them.

## Surfaces changing

| Surface | Change | IC | Kind |
|---------|--------|----|----|
| `src/specify_cli/review/pre_review_gate.py` | `is_consumer_repo` seam + `_is_spec_kitty_source_repo` (rebase clean) | IC-01 | product |
| `src/specify_cli/cli/commands/agent/tasks_move_task.py` | `_PRE_REVIEW_CONSUMER_REPO_REASON` calm branch (**--3way**) | IC-01 | product |
| `tests/review/test_pre_review_gate_engine.py` / `..._integration.py` | red-first tests (rebase clean) | IC-01 | test |
| `src/specify_cli/sync/daemon.py` | `_daemon_start_skip_reason` honors disable envs (`:1038`) | IC-02 | product |
| `tests/sync/test_daemon_sync_disable_env.py` | repro flips green | IC-02 | test |
| `tests/sync/conftest.py` | copy the #2794 `_isolate` sync-toggle fixture | IC-03 | test |
| `src/charter/evidence/orchestrator.py` | `isinstance` guard @ `:95-96` + docstring `:82` | IC-04 | product-ish (clears 3 reds) |
| `tests/charter/test_bundle_contract.py` | seed `charter.yaml` in `_init_fixture` | IC-05 | test |
| `tests/adversarial/test_distribution.py` | skip-when-logged-out env-guard (`:237`) | IC-05 | test |
| `tests/runtime/test_resolve_by_urn.py` | clear `resolver.__warningregistry__` | IC-06 | test |
| `.github/workflows/ci-quality.yml` | add `platform` to loader-coverage `if:` (`:1290-1293`) | IC-06 | CI |

## Invariants (must hold at close)

- **INV-1**: every remaining red on the `regression (blocking)` + `fast-tests-charter` jobs is fixed or an
  `xfail(strict)` carrying a tracking-issue ref (NFR-001).
- **INV-2 (behavior-preserving)**: with neither disable env set, the daemon spawns exactly as before; in
  spec-kitty's own repo the pre-review gate behaves exactly as before.
- **INV-3 (no re-derive)**: #2534 ships the ready branch's intent, not a fresh design.
- **INV-4 (scope fence)**: #2795/#2367-A, #2573a-deep, #2598, and the `url_list`→charter.yaml re-wire are OUT.

## LANDMINES (pin before any WP cuts code)

### LM-1 — #2534 rebase is the risk, not the fix
3 of 4 files apply clean; `tasks_move_task.py` conflicts on **positional drift only** (its two hunks target
byte-identical text moved ~110 lines). **Sequence:** (a) confirm the repro still fires on current main; (b)
`git apply --3way` (or hand-place two hunks whose target text is unchanged); (c) if it genuinely fights,
**port-the-intent** per research §1 — NEVER re-derive a different fix (C-002/INV-3). The `except` branch lives at
`tasks_move_task.py:1025-1029` on main; the constant goes near `:754-771`.

### LM-2 — #2807 orchestrator: guard the shape, do NOT re-wire url_list
`config["charter"]` is a **path string** post-#2773; `synthesis_inputs`/`url_list` has no live config home. The
fix is a 2-line `isinstance` guard returning `()` — NOT re-plumbing url_list into charter.yaml (that is scope
expansion → its own deferred issue, C-005/INV-4). This single fix clears 3 reds (phase3, orchestrator, e2e).

### LM-3 — #2573b: honor the env without breaking the unset path
Add the disable-env check anywhere before the spawn block in `_daemon_start_skip_reason`; when neither env is
truthy it must return `None` (fall through unchanged). Reuse `is_truthy` + the two-var grammar from the
pre-review-gate (`_PRE_REVIEW_GATE_DISABLE_ENV_VARS`) so both call sites agree. INV-2.

### LM-4 — #2809: the fixture already exists — copy, don't invent
`_isolate_pre_review_gate_sync_toggles` (autouse, #2794) lives at `agent/conftest.py:51-70` but is package-scoped.
Copy it verbatim into `tests/sync/conftest.py` (minimal blast radius). Do not author a novel mechanism.

### LM-5 — #2812 loader anomaly is a 1-line workflow guard; do NOT split
Root cause is a filter/guard mismatch: the job gates on `next||core_misc` but `mission_loader/**` maps to
`platform`. Add `|| needs.changes.outputs.platform == 'true'` to the job `if:`. It is well-rooted — do NOT
split to its own issue (C-005 was a guard against ballooning, which did not happen). Note `platform` feeds
other jobs — keep the change to the one `if:`.

### LM-6 — test_upgrade auth-env: env-guard over blanket xfail
`test_upgrade_updates_templates` reds on the category-2 `logged_out_on_connected_teamspace` artifact. Prefer a
skip-when-logged-out env-guard (mirror the charter-mission auth-skip) rather than a bare xfail (NFR-002).

## Post-plan squad amendments (2026-07-19)

Two lenses (paula-patterns / reviewer-renata) verified the decomposition SOUND (disjoint owned_files; IC-04's
guard confirmed to clear all 3 reds; IC-01 rebase profile exact; IC-02 sole spawn gate). Additive acceptance
sharpeners folded here:

### LM-7 — #2809 collides with #2782 (same test, divergent RCA) — red-first BEFORE assuming the fix
`test_strict_json_stdout::test_mission_create_json_strict_when_sync_skips_ingress` is ALSO tracked under
**#2782** with a **contradictory root cause** (#2809: a leaked `SPEC_KITTY_SYNC_*` toggle disables sync → fix =
env-reset fixture; #2782: sync *attempts a connection* → connection-refused). It is already
`@pytest.mark.regression`-quarantined (`tests/sync/test_strict_json_stdout.py:743`), routed to the NON-blocking
`regression visibility` gate. **WP03 MUST red-first verify the env-reset fixture actually flips THIS test
red→green on current main.** If the live failure is #2782's connection-refused path, the fixture will NOT green
it → escalate/reconcile (do NOT blind-xfail to mute a possible product question). Reference #2782 in the WP; on
success, decide whether to strip the `@regression` marker.

### LM-8 — `tests/sync/conftest.py` EXISTS — append, not create; and it widens the fixture's blast radius
The file is a ~5 KB pre-existing conftest that does NOT hold the fixture — WP03 **edits/appends**, never
overwrites. Hoisting an autouse `delenv` into the whole `tests/sync/` package makes it apply to the daemon /
real-port tests, which are **not** HOME-isolated (CLAUDE.md — run serial `-n0`). No test relies on *inheriting*
the disable env (they self-set, e.g. `_daemon_harness.py:103`), so risk is low — but **WP03 acceptance must run
the serial daemon/orphan-sweep tests (`-n0`), not just `test_strict_json_stdout`**, to prove the autouse fixture
doesn't perturb harness ordering.

### LM-9 — IC-04 e2e: run the FULL golden-path to green, don't infer from crash-clearance
`test_charter_epic_golden_path` currently dies **at** the synthesize step — nothing past it has ever executed.
The `isinstance` guard clears the crash, but **WP04 acceptance must run the full e2e green**; any post-synthesize
assertion is unverified today.

### LM-10 — resolve edit sites by SYMBOL, not the research line numbers
Research/plan line refs drift slightly from HEAD (e.g. the `except` at `:1210` vs research's `:1025-1029`).
Symbols are all verified present. Every WP resolves by symbol (`_daemon_start_skip_reason`,
`_mt_pre_review_gate_verdict`, `load_url_list_from_config`), not by line number.

### LM-11 — WP02 (#2573b) is INDEPENDENT of the WP03 fixture
#2573b's repro sets its own env; it does NOT consume the WP-A/WP03 fixture. The "shared enabler" framing in the
spec is overstated — keep WP02 and WP03 as independent lanes with no cross-dependency. (Post-tasks squad VERIFIED
the WP02×WP03 `tests/sync/` interaction is safe: the autouse `delenv` runs at setup, the daemon test's own
`setenv` runs in the body afterward; the fixture's docstring documents exactly this contract.)

### LM-12 — WP06 is a whack-a-field: the loader-coverage gate has TWO bound sites (post-tasks HIGH)
The mission-loader-coverage gating decision lives in `.github/workflows/ci-quality.yml` twice: the job `if:`
(~`:1292`) AND the SSOT `JOB_GROUPS["mission-loader-coverage"]` (~`:3958`), bound by the FR-011 parity gate
`tests/architectural/test_workflow_coherence.py::test_job_groups_table_equals_parsed_if_gating_live`. WP06 MUST add
`platform` to **both** (they're both in ci-quality.yml, which WP06 owns) and run `test_workflow_coherence.py` — else
the parity gate reds, self-inflicting a new CI red. The earlier "keep it to the one `if:`" guidance was wrong.
