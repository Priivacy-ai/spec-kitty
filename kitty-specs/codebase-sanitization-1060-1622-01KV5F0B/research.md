# Research — Internal `--feature` & `status_service` sanitization

## R1. #1622 wire-or-retire — RESOLVED (decision 01KV5F16HBCX6A99J9AY97B3T5)

**Decision:** Neither wire nor retire. #1622 is **already resolved in code**;
this mission carries it as a verify-only task.

**Rationale (PR #1614 archaeology + import-graph review on `upstream/main`
`b995cd99c`):**

- PR #1614 ("Refactor coordination status event-log contracts", merged
  2026-06-02, closes #1612/#1613) introduced an explicit contract layer:
  `EventLogReadContract` / `EventLogWriteContract` and the helpers
  `read_event_log` / `append_event_log` /
  `merge_append_preserving_coordination_event_log_bytes` /
  `wp_lane_actor_from_events`.
- Mission 01KTPKST WP09 (commit `be932d19a`, approved 2026-06-09) then performed
  the dead-symbol burn-down for #1622:
  - **Deleted** `append_event_log_batch` and `read_wp_lane_actor` — the only 2 of
    the original "5 dead" with zero callers anywhere (verified: absent from the
    entire tree today).
  - **De-exported** `StatusReadSource`, `EventLogWriteTarget`,
    `StatusContractError` from `status_service.__all__`, definitions retained,
    because they are **load-bearing live internals**:
    - `StatusReadSource` is the `.source` field type of `EventLogReadContract`
      and drives `read_event_log` dispatch.
    - `EventLogWriteTarget` is the `.target` field type of
      `EventLogWriteContract` and drives `_validate_write_contract`.
    - `StatusContractError` is raised throughout `read_event_log` /
      `append_event_log` and is imported by live tests in
      `tests/specify_cli/coordination/test_status_transition.py`.
- The exported contract facade has **live (non-test) callers**:
  `coordination/status_transition.py`, `coordination/transaction.py`,
  `status/store.py`, `status/event_log_merge.py`,
  `cli/commands/agent/workflow.py`.

**Conclusion:** the "5 dead symbols" premise in #1622 was a stale,
pre-#1614-rebase research assumption. Re-deleting the 3 retained symbols would
break the live facade and its tests. The mission's own closeout (renata, randy,
alphonso — unanimous) already recorded "do NOT re-delete; no code change."

**Action:** verify the resolved state (grep proof) and close #1622 with the
re-classification "FR-013 delivered 2/5 deletions; other 3 retained-because-live
+ de-exported." No edit to `status_service.py`.

## R2. `--feature` alias declaration shape (workstream 1)

The hidden alias is not a single string — it is plumbed through three layers in
each in-scope command:

1. **Option declaration**:
   `feature: Annotated[str | None, typer.Option("--feature", hidden=True, help="(deprecated) Use --mission")] = None`
2. **Local threading**: the `feature` value is passed into helpers as
   `explicit_feature=feature`.
3. **Resolution**: `resolve_selector(canonical_value=mission, alias_value=feature, *, canonical_flag="--mission", alias_flag="--feature", …)`
   (`src/specify_cli/cli/selector_resolution.py`). The resolver emits a
   one-shot deprecation warning and enforces "canonical wins; conflicting values
   error."

**Removal recipe for an in-scope command:** delete the `feature` parameter,
drop the `alias_value`/`alias_flag` arguments at the `resolve_selector` call
(or switch to the mission-only resolution path `resolve_mission_handle`), and
remove now-dead `explicit_feature` plumbing. `resolve_selector` itself is
**retained** (FR-008) — it remains in service for the out-of-scope user-facing
commands. (`_legacy_aliases.hidden_feature_option` was initially assumed
retained, but the adversarial squad found it had zero `src/` callers — it is
**removed** under FR-009/WP05.)

**In-scope `--feature` footprint (grep on `upstream/main`):**

| Command module | `--feature` occurrences |
|----------------|------------------------|
| `agent/tasks.py` | 12 |
| `agent/status.py` | 9 |
| `agent/workflow.py` | 4 |
| `agent/context.py` | 2 |
| `charter/lint.py` | 2 |
| `materialize.py` | 2 |
| `validate_encoding.py` | 2 |
| `validate_tasks.py` | 2 |
| `verify.py` | 2 |
| `agent/mission.py` | 1 |

(`agent/workflow.py` also imports `merge_append_preserving_coordination_event_log_bytes`
from `status_service` — that import is unrelated to the alias and stays.)

## R3. First-party caller impact (FR-003) — minimal

`git grep -- '--feature' src/doctrine/` returns only:
- `skills/spec-kitty-implement-review/SKILL.md:121` — prose note; refers to the
  out-of-scope `implement`/`review` commands. **No change.**
- `skills/spec-kitty-runtime-next/SKILL.md:349` — prose note; refers to the
  out-of-scope `next` command. **No change.**
- `tactics/built-in/occurrence-classification-workflow.tactic.yaml:40` —
  `agent bulk-edit validate --feature …` example; `agent bulk-edit` is **not**
  in the in-scope cluster. **No change** (optional hygiene update to `--mission`
  deferred with the rest of #1060).

No first-party SOURCE template/skill passes `--feature` to an in-scope command,
so FR-003 has no required edits. Generated agent dirs (`.claude/`, `.codex/`, …)
are not hand-edited; they regenerate from `src/doctrine/` via upgrade.

## R4. Gate flip (FR-004)

`tests/contract/test_terminology_guards.py::test_no_visible_feature_alias_in_cli_commands`
currently passes any `--feature` option as long as it carries `hidden=True`. The
flip: add an **in-scope cluster allow-list inversion** — for the 10 in-scope
command files, fail if a `--feature` Typer option is present at all (hidden or
visible); the global "hidden-only" rule continues to govern the out-of-scope
files. Implement as a focused new assertion (or parametrized case) so the
existing global rule is untouched for deferred commands. Land the red test
before the removal (ATDD-First, charter C-011).

## R5. Test footprint

~30 test files reference `--feature`. During implementation, identify those that
invoke an **in-scope** command with `--feature` and update them to `--mission`
(or, for the de-aliasing regression, assert the option is now rejected).
Out-of-scope command tests are untouched (their alias still works).
