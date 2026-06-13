# Quickstart / Validation Scenarios — 01KV0S99

Each scenario is an acceptance check (ATDD: author the failing test first, NFR-005).

## A — Post-mission lifecycle

1. **Follow-up recording (FR-001):** on a merged mission, run
   `spec-kitty mission follow-up <id> --commit <sha>` → a `FollowUpRecorded` event is
   appended, attributed to `mission_id`, and the follow-up appears in the mission
   status/history view. Re-running with the same `<sha>` is an idempotent no-op (no
   duplicate event).
2. **Follow-up by PR:** `--pr <n>` records a PR follow-up; mutually exclusive with `--commit`.
3. **Re-open (FR-002):** `spec-kitty mission reopen <id> --reason "residual fix"` →
   `MissionReopened` appended (actor + reason), `merged_*` cleared. **Assert
   `derive_mission_lifecycle` now reports the `reopened`/actionable surface_state** (driven by
   the event, with WP lanes still terminal/untouched) — the load-bearing check, since clearing
   `merged_*` alone does not change classification. A subsequent merge re-stamps `merged_*` and
   the mission leaves `reopened`.
4. **Fail-closed re-open (NFR-004):** re-opening a mission whose branch/worktree is gone
   exits non-zero with a structured error + remediation; no event, no metadata change.
5. **WP reducer unaffected:** `status.json` WP snapshot is identical before/after the new
   lifecycle events (reducer skips them).

## B — Unified dispatch

6. **Canonical (FR-004):** `spec-kitty dispatch "<request>" --profile <p>` opens a governed
   Op identical to the legacy path; `--json` envelope carries the close contract.
7. **Alias parity (NFR-001/FR-005):** `do`/`ask`/`advise` produce byte/contract-identical Op
   records + JSON envelopes + exit codes vs `dispatch` (mode mapping preserved:
   do/ask/dispatch→task_execution, advise→advisory). Pinned by parity tests.
8. **C-002 no-break:** `spec-kitty do --profile <p> "<request>"` works at every commit in the
   change (no broken window).
9. **Propagation (FR-006):** assert `dispatch` appears in the canonical SOURCE skill
   `src/doctrine/skills/spec-kitty.advise/SKILL.md` and that `.kittify/command-skills-manifest.json`
   is refreshed (hash updated via the skills install path); skill-routing prose names `dispatch`
   + the retained aliases. No hand-edited agent copies (C-004).

## C — DRG curation

10. **Stale ref (FR-008):** `java-conventions.styleguide.yaml` references `java-jenny` (real),
    not `java-implementer` (gone); no phantom `agent_profile:java-implementer` node after regen.
11. **Orphan triage (FR-009/C-003):** orphan count reduced via wired edges; remaining orphans
    documented with per-orphan rationale; no valid doctrine artifact bulk-deleted.
12. **Deterministic regen (NFR-003):** `spec-kitty doctrine regenerate-graph --check` exits 0;
    regenerating twice is byte-identical; orphan-count regression test pins the reduced count.

## Regression / closure

13. **No-regression (SC-5):** `pytest tests/architectural/` and the full `invocation` +
    `status` suites pass (exit 0); `spec-kitty do --profile <p> "<req>"` still opens a governed
    Op (governed-Op flow intact); existing mission-lifecycle derivation unchanged for
    non-reopened missions.
14. **Honest closure (SC-1..4):** #1810 + #1804 + #1802 + #1863 reach terminal verdicts in
    issue-matrix.md (no `in-mission`/`unknown` rows at merge).
