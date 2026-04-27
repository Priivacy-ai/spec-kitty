---
work_package_id: WP03
title: Quickstart fix and real dogfood smoke
dependencies:
- WP01
- WP02
requirement_refs:
- FR-007
- FR-008
- FR-009
- FR-010
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this feature were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T12
- T13
agent: "claude:opus-4.7:reviewer-renata:reviewer"
shell_pid: "54682"
history:
- action: created
  at: '2026-04-27T05:05:00Z'
  by: tasks
authoritative_surface: kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/
execution_mode: code_change
owned_files:
- kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/quickstart.md
- kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/smoke-v2.md
tags: []
---

# WP-FIX-3 — Quickstart Fix + Real Dogfood Smoke

## Objective

Close findings F-2 and F-5. Fix the predecessor's `quickstart.md` JSON field references so it runs without `KeyError`. Re-run the dogfood smoke from a separate temp repo and **issue a composed action** so the smoke captures paired `started`/`done` trail records — not just a `kind: query` response.

## Context

- F-5 [P5]: predecessor `quickstart.md:47-56` asserts `d["issued_step_id"]`; the runtime `Decision` JSON uses `step_id` for issued steps and `preview_step` for the query path. Running the quickstart literally raises `KeyError`.
- F-2 [P1]: predecessor `evidence/smoke.md` recorded `kind: query` only — no composed action ran. SC-006 / NFR-005 / Scenario 6 require StepContractExecutor dispatch + paired trail records.

This WP edits the predecessor's `quickstart.md` IN PLACE (per spec C-004) and adds a NEW evidence file `smoke-v2.md` alongside the historical `smoke.md`.

## Subtasks

### T12 — Fix `quickstart.md` JSON field references

Edit `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/quickstart.md`. Specifically:

1. Replace the `python3 - <<'PY'` block at lines ~47-56 so it tolerates both `kind: query` (with `preview_step`) and `kind: success` (with `step_id`):

   ```python
   import json
   d = json.load(open("next.json"))
   print("decision_kind:", d.get("kind"))
   step = d.get("step_id") or d.get("preview_step")
   print("step:", step)
   print("mission:", d.get("mission"))
   assert d["mission"] == "documentation", f"expected documentation, got {d['mission']}"
   assert step in {"discover", "audit", "design", "generate", "validate", "publish"}, \
       f"unexpected step: {step}"
   ```

2. Update the surrounding "Expected outcomes" prose to:
   - On a fresh feature_dir, the first `next` returns `kind: query` with `preview_step` (since no action has been issued yet).
   - To trigger an action, the operator runs the issuance command (whichever flag/sequence the runtime uses — read `spec-kitty next --help` and the predecessor smoke transcript).
   - After issuance, the trail directory `~/.kittify/events/profile-invocations/` (or wherever the runtime persists invocation records) contains paired `started`+`done` (or `failed`) entries.

3. Keep the `--project` reminder verbatim. Keep the `--directory` warning + #735 reference verbatim.

Diff size: ≤ 50 lines per spec C-004.

### T13 — Real dogfood smoke that issues an action

Run the smoke from a temp repo OUTSIDE the spec-kitty tree. The smoke MUST:

1. `git init` a fresh temp repo (e.g. via `mktemp -d`).
2. Use `uv --project /private/var/folders/.../spec-kitty` (NEVER `--directory`).
3. Run `spec-kitty agent mission create demo-docs --mission-type documentation --json` → capture stdout.
4. Run `spec-kitty next ... --json` and confirm a non-`query` response (i.e. an action was issued OR follow up with the issuance command if `next` defaults to query). Read the runtime CLI to find how to issue an action — likely a separate flag or follow-up call.
5. After action issuance, list `<temp_repo>/.kittify/events/profile-invocations/` and capture the paired records.
6. Verify: `next.json` (or the issuance response) contains `step_id` (not `preview_step`) for the discovered step, OR `kind: success`.
7. Verify the trail records contain `action: discover` (or whichever first action was issued).
8. Cleanup: `rm -rf` the temp repo.

Capture into `kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/smoke-v2.md`:
- Reference to predecessor `smoke.md` (which is preserved as the F-2 finding evidence).
- Verbatim command sequence.
- Verbatim stdout of `create.json`, `next.json`, action-issuance output.
- Listing of `<temp_repo>/.kittify/events/profile-invocations/` showing paired records.
- Grep proving zero substantive `--directory` uses.
- Closing line: "Closes #502 F-2 / NFR-005 / SC-006."

If you cannot find a way to issue an action via the CLI (e.g. if every `spec-kitty next` returns `kind: query` and there is no documented issuance verb), STOP and report — this is a runtime-API gap that must be escalated, not papered over with a fake "PASS" note.

## Verification

- `quickstart.md` parses as Python (the embedded snippet) and references only existing `Decision` fields (`step_id`, `preview_step`, `mission`, `kind`).
- `evidence/smoke-v2.md` shows action issuance + paired trail records.
- `grep -c "\\-\\-directory" smoke-v2.md` returns 0 substantive uses (inline doc warnings noting NOT to use `--directory` are allowed).

## After Implementation

1. `git add kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/quickstart.md kitty-specs/documentation-mission-composition-rewrite-01KQ5M1Y/evidence/smoke-v2.md`
2. `git commit -m "feat(WP-FIX-3): quickstart fix + real dogfood smoke (#502 F-2, F-5)"`
3. `spec-kitty agent tasks mark-status T12 T13 --status done --mission documentation-mission-composition-fixup-01KQ6N5X`
4. `spec-kitty agent tasks move-task WP-FIX-3 --to for_review --mission documentation-mission-composition-fixup-01KQ6N5X --note "T12-T13 complete; quickstart fields corrected; smoke-v2 shows action issuance + paired trail records"`

## Reviewer Guidance

- Read `quickstart.md` and verify zero references to `issued_step_id`. Verify the assertion uses `d.get("step_id") or d.get("preview_step")`.
- Read `evidence/smoke-v2.md` and verify:
  - `next.json` (or issuance response) contains `step_id` (issued) — not just `preview_step`.
  - Trail records section shows paired `started`/`done` for at least one documentation action.
  - `--project` was used; no substantive `--directory` uses.
  - Temp repo is OUTSIDE the spec-kitty tree.
- If the smoke CANNOT issue an action (e.g. CLI gap), the WP fails and a runtime issue must be filed.

## Activity Log

- 2026-04-27T05:29:16Z – claude:opus-4.7:reviewer-renata:implementer – shell_pid=43317 – Started implementation via action command
- 2026-04-27T05:38:07Z – claude:opus-4.7:reviewer-renata:implementer – shell_pid=43317 – T12-T13 complete; quickstart fields corrected; smoke-v2 shows action issuance + paired trail records (--force: WP03 owned_files include kitty-specs/<predecessor-mission>/quickstart.md and evidence/smoke-v2.md per spec C-004)
- 2026-04-27T05:38:41Z – claude:opus-4.7:reviewer-renata:reviewer – shell_pid=54682 – Started review via action command
