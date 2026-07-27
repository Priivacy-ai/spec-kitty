# Phase 0 Research — tasks-py-degod-wave2-01KWH9EQ

All findings verified live against the working tree (branch `degod-follow-ups`, base
`381db8d5f`) on 2026-07-02. Each decision lists rationale + alternatives considered.

## D1 — Seam-bridge idiom (carry-forward "confirm before WP1": CONFIRMED)

- **Decision**: Relocated code routes every patched/infra call through a lazy in-function
  import: `from specify_cli.cli.commands.agent import tasks as _tasks` then
  `_tasks.<attr>(...)`.
- **Rationale**: This is the LIVE canonical idiom of the designated template —
  `mission_create.py` (3 occurrences: lines 76, 204, 439), `mission_finalize.py` (13
  occurrences, post-tasks squad recount), always inside function bodies, never module
  scope (cycle-safe).
  Registration in `mission.py` uses `app.command(name=...)(fn)` (lines 319–326), not
  decorators in the shim. Because the call goes through the `tasks` module attribute,
  `@patch("...agent.tasks.<sym>")` keeps INTERCEPTING — including for symbols that are
  themselves relocated, as long as `tasks.py` retains a module-level binding and the
  relocated caller routes via `_tasks.<attr>`.
- **Alternatives considered**: bare module-level re-exports (REJECTED — squad-proven to
  preserve importability but not interception); mass patch re-pointing (RESERVED for
  cases where routing through `_tasks` is unreasonable, decided per WP with the seam
  checklist).

## D2 — Render indent unification (FR-006 design)

- **Decision**: `RealRender` gains a constructor parameter (`indent: int | None = None`),
  `json_envelope` becomes `json.dumps(payload, indent=self._indent)`; `_default_status_ports`
  constructs `RealRender(console=console, indent=2)`; `_StatusRender` is DELETED.
- **Rationale**: Keeps the `Render` Protocol signature frozen (no stub churn), keeps ONE
  production adapter (spec C-004 — a named `IndentedRender` second adapter would be a
  second production adapter for the same port), byte-identical (`json.dumps(payload,
  indent=None)` ≡ `json.dumps(payload)`).
- **Alternatives considered**: (a) add `indent` param to the Protocol method — rejected:
  Protocol-breaking, forces every stub/fake to change; (b) move `_StatusRender` into
  `agent_tasks_ports.py` as `IndentedRender` — rejected: violates one-adapter-per-port
  (C-004), keeps the subclass split-brain the FR exists to remove.
- **Byte-compat evidence**: `RealRender.json_envelope` is `return json.dumps(payload)` —
  DEFAULT separators `(', ', ': ')` — and all 12 compact inline sites also call
  `json.dumps(...)` with no separators arg. Identical bytes. (The spec's word "compact"
  means "non-indented", not `separators=(',',':')` — worth knowing when authoring the
  byte-freeze fixtures.)

## D3 — Emission-site correction (spec census refinement)

- The status `indent=2` "site" at tasks.py:1235 is the `_StatusRender.json_envelope`
  METHOD BODY; the actual print is `print(ports.render.json_envelope(result))` at
  tasks.py:4117 — i.e. **status already routes through the Render port**. FR-006 is
  purely collapse-the-subclass; FR-005's routing work applies to the 12 direct
  `print(json.dumps(...))` sites only.
- Site → subcommand map (research delegate R5, verified):

| Line(s) | Subcommand | Leg | Trigger | Format |
|---|---|---|---|---|
| 508 | all (via `_find_mission_slug`) | error | missing/empty `--mission` | compact |
| 546 | `add-history` + others (via `_output_result`) | success | generic success | compact |
| 559 | all (via `_output_error`) | error | generic error / diagnostic dict | compact |
| 1235→4117 | `status` | success | `status --json` | indent=2 via `_StatusRender` |
| 2477 | `mark-status` | error | no task IDs resolved | compact |
| 2805 | `list-tasks` | success | `list-tasks --json` | compact |
| 3349–3350 | `map-requirements` | error | unknown WP IDs | compact |
| 3474 | `map-requirements` | error | malformed requirement ref | compact |
| 3488 | `map-requirements` | error | unknown spec IDs | compact |
| 3585 | `map-requirements` | error | stale/invalid frontmatter refs | compact |
| 3665 | `map-requirements` | success | `map-requirements --json` | compact |
| 3863 | `validate-workflow` | success | `validate-workflow <id> --json` | compact |
| 4557 | `list-dependents` | success | `list-dependents --json` | compact |

## D4 — Byte-freeze suite design (FR-005 pre-step)

- **Decision**: NEW `test_tasks_json_bytes.py` reusing the existing in-process
  `typer.testing.CliRunner` machinery with a NEW sibling fixture
  `fixtures/tasks_cli/json/byte_contracts.json` mapping case → `{argv, exit_code,
  expected_stdout}`; assertion is `result.stdout == expected_stdout` (byte equality).
- **Rationale**: the existing harness's `_shape()` collapses values/ordering — structurally
  sound but byte-blind (squad CRITICAL). Reusing the runner keeps the suite in the `fast`
  shard; a separate fixture file avoids overloading `envelopes.json` semantics.
- **Anti-patterns excluded**: `len()==N` golden counts (CT5 #2076); handcrafted
  placeholder data (charter/testing-principles — production-shaped fixtures).

## D5 — LOC gate form (FR-011)

- **Decision**: plain per-file ceiling in a NEW `tests/architectural/test_tasks_command_surface.py`:
  read `tasks.py`, `assert len(splitlines()) <= _CEILING`, with a self-mutation proof
  (synthetic source over the ceiling → detector fires). `_CEILING` starts at the current
  4569 and RATCHETS DOWN per relocation WP, finishing at `min(achieved, 1400)`.
- **Rationale + carry-forward disposition**: CT1 (#2072) `composite_key` keying is N/A —
  it exists for line-keyed allowlist entries that drift with edits; a whole-file scalar
  ceiling has no per-line keys. Recording this rationale here so the carry-forward is
  honored by reasoning, not cargo-culted. No LOC-gate precedent exists in
  `tests/architectural/` (verified); nearest patterns: count-ceiling
  (`test_integration_boundary.py`) and single-file read+assert.

## D6 — AST dumps gate pattern (FR-007)

- **Decision**: walk `ast.parse` trees over the directory glob
  `src/specify_cli/cli/commands/agent/*.py` (all siblings, incl. future ones — closes
  move-next-door evasion) flagging: `json.dumps` attribute calls, `from json import
  dumps` (+aliased), `import json as <alias>` usage, and name-rebinding
  (`x = json.dumps`). Allowlist: none at ship time (0 sites); any later exception is a
  shrink-only frozenset of repo-relative paths. Non-vacuity: one synthetic-offender
  theater test per evasion form (the `test_commit_target_kind_guard.py` pattern).
- **Precedents**: `test_protection_resolver_call_sites.py` (walk + report + allowlist),
  `test_commit_target_kind_guard.py` (theater tests, composite-key allowlists).
- **Docstring safety**: AST call-node inspection is inherently immune to the
  tasks.py:1225 docstring mention (it is a string, not a call node).

## D7 — Patched-symbol seam inventory (exact, supersedes all squad approximations)

`grep -rE "patch\(['\"].*agent\.tasks\." tests/ | wc -l` → **367 sites**;
distinct-symbol breakdown (sums to exactly 367):

| Symbol | Sites | Defined in tasks.py? |
|---|---|---|
| `locate_project_root` | 66 | no (imported) |
| `_find_mission_slug` | 65 | YES (482) |
| `_ensure_target_branch_checked_out` | 48 | YES (446) |
| `get_mission_type` | 26 | no |
| `feature_status_lock` | 21 | no |
| `commit_for_mission` | 16 | no |
| `get_main_repo_root` | 15 | no |
| `locate_work_package` | 13 | no |
| `emit_status_transition_transactional` | 13 | no |
| `_emit_sparse_session_warning` | 13 | YES |
| `_validate_ready_for_review` | 12 | YES |
| `_check_unchecked_subtasks` | 12 | YES |
| `read_events_transactional` | 9 | no |
| `emit_history_added` | 9 | no |
| `get_auto_commit_default` | 6 | no |
| `console` | 5 | module attr |
| `bootstrap_canonical_state` | 5 | no |
| `resolve_workspace_for_wp` | 3 | no |
| `get_feature_target_branch` | 3 | no |
| `_wp_branch_merged_into_target` | 2 | YES |
| `subprocess` | 2 | stdlib import |
| `get_status_read_root` | 2 | no |
| `emit_error_logged` | 1 | no |

(23 distinct symbols by this prefix form; `monkeypatch.setattr` adds ~37 more sites over
a similar symbol set — WP seam checklists enumerate per family from this table.)

- **Routing rule** (from D1): relocated code calls EVERY symbol in this table via
  `_tasks.<attr>`; `tasks.py` retains a module-level binding for each (import or
  re-export of the relocated def). This preserves all 367 patch targets without mass
  re-pointing. Direct (bare-name) calls are permitted only for symbols NOT in this table
  and NOT patched via `monkeypatch.setattr`.

## D8 — Boyscout facts (FR-009/FR-010 inputs)

- All 34 current tasks-domain test files (15 in `tests/tasks/`, 19 matching
  `tests/specify_cli/cli/commands/agent/test_tasks*`) carry `pytestmark` and are
  gate-selected (`fast`/`git_repo`/`integration`) — the obligation is
  maintain-and-evidence for the mission's NEW files, not fixing existing ones.
- `_gate_coverage_baseline.json` currently holds 4 orphan paths, none in the tasks
  domain (#2295 defines the wider quarantine floor).
- Repo-wide: 257/26,612 tests selected by no marker gate; no `-m unit`/`-m contract`
  gate exists (2026-07-02 census, posted to #2034).

## D7a — Post-tasks squad corrections (2026-07-02)

- `_get_latest_review_cycle_verdict` and `_self_review_fallback_option_error` are **NOT
  defs in tasks.py** — Wave 1 extracted them to `tasks_parsing_validation.py` (:288/:250);
  `tasks.py` re-imports them (:148/:150). The shared move-set is therefore **~28**, not
  ~30, and the WP02 mypy fold re-points/normalizes the re-export rather than moving a def.
- The coord-harness ratchet is single-file with a `total==0 → 100.0` vacuous fallback —
  the FR-012 re-point is a coverage-plumbing rewrite (see parity-contract Layer 3, rev 2).
- WP04's glue emission sites have NO `ports` local and the State dataclasses carry no
  render field — all 6 glue sites + 3 small bodies use the local `RealRender()`
  default-param seam (never State-threading, which would break verbatim moves).

## D9 — Campsite folds (pre-plan squad; recorded in spec)

- #2306: `test_untrusted_path_containment` inventory off-by-one (`tasks.py:1325`→actual
  `:1326`, sink `_mt_warn_worktree_kitty_specs`) — 1-line pre-fix + row moves with the
  move_task family.
- `test_tasks.py:26` attr-defined (`_get_latest_review_cycle_verdict` import) — re-point
  in the WP relocating that symbol; `test_tasks.py:1028` redundant-cast — 1-line removal
  in the first WP touching the file.

## D10 — Wave 1 friction watch-list

Inherited in `tracers/tooling-friction.md`: strict-mypy src+tests together; typer pin
before fixture work; FR-token de-tokenization when descoping; status bookkeeping commits
between WPs; coord-branch artifact writes; latest-rejected review-artifact merge gate;
expect #2031 stale-assertion analyzer false-positive storms at every WP merge.
