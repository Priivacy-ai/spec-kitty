# Plan Review — Runtime Risk & Failure Modes
**Reviewer**: debugger-debby (runtime/behavioral-risk specialist)
**Mission**: tooling-stability-guard-coherence-01KTRC04
**Branch**: `fixups/code-engine-stabilization`
**Date**: 2026-06-10

---

## Verdict

**PROCEED with mitigations.** The spec and plan are structurally sound. Two real failure windows exist
(mid-strangle operator wedge; self-hosting breakage) — both are manageable with cheap, explicit mitigations
the plan does not yet call out. The remaining three risk questions are either low-severity or have adequate
coverage already. No blocking issues.

---

## Prioritised Risks

### RISK-1 — Mid-strangle operator wedge (HIGH severity / HIGH confidence)

**What:** IC-02 converts ~15 callers incrementally. During conversion, `_is_protected_branch_exception`
still exists and the old prefix channel is still live. The plan says "delete the prefix channel only after
conversion + green suite" — correct discipline. But the plan is silent on what happens if a caller is
converted to pass `CommitTarget` (and therefore has its prefix privilege removed from the old path)
*before* the new `core/commit_guard.py` policy module's capability check is wired end-to-end.

**Concrete failure mode:** the upgrade command's commit message is
`"chore: apply spec-kitty upgrade changes (v3.2 -> v3.3)"` — currently passes through the prefix exception
at `safe_commit` step 6. If the upgrade caller is converted to pass `CommitTarget` (no message) and the new
`evaluate(CommitTarget, protection_state, capability)` is not yet wired, the commit hits `is_protected=True`,
no capability, no old prefix → `ProtectedBranchRefused`. Result: `spec-kitty upgrade` silently fails to
auto-commit on any `main`-branch consumer project. Blast radius = **operator papercut** (upgrade reports
"please commit manually"), not a wedged mission, but it will confuse operators and burn trust in the
tooling stability this mission is trying to establish.

**Cheapest mitigation (does not require spec change):**
In IC-02, enforce a strict intra-IC ordering: wire `evaluate()` and all three capability grants (upgrade /
merge-bookkeeping / release-flow) into the new policy module AND update `safe_commit` to consume it
**atomically in the same commit** before converting any caller. Never convert a caller in a commit that
precedes the capability path being live. The #1355 import-boundary ratchet will catch any partial state
post-IC-02. Add an explicit IC-02 task note: "capability grants wired BEFORE first caller conversion commit."

---

### RISK-2 — Self-hosting hazard: broken guard wedges this mission's own WP commits (HIGH severity / HIGH confidence)

**What:** This repo dogfoods spec-kitty. The `safe_commit` path being refactored is the exact path used
by `spec-kitty agent tasks status`, `record-analysis`, and merge bookkeeping on this mission's own WPs.
If a mid-IC-02 commit lands a broken guard (e.g., `_is_protected_branch_exception` deleted before the
capability path is live, or a regression in `ProtectedBranchRefused` detection), all subsequent WP
status commits on this branch fail.

**Recovery complexity:** fixing the guard is itself a commit that must go through the broken guard. The
editable-install lag is NOT a safety net here — the installed version and the in-tree version are the same
checkout (`src/specify_cli` is editable).

**Cheapest mitigation:**
1. IC-01 ATDD suite catches most regressions before they're committed — this is already in the plan
   and is the primary net. Trust it.
2. One additional cheap escape hatch: document (in the IC-02 task file) that if the guard breaks
   mid-implementation, the `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS=1` env var bypasses the guard
   entirely (it already exists in `assert_not_protected_branch`). This is the recovery escape hatch; it
   does NOT need to be a new mechanism.
3. Do NOT delete `_is_protected_branch_exception` in a WIP commit. Delete it only in the IC-09 closure
   commit after IC-01 suite is green end-to-end.

---

### RISK-3 — Findings-carrier migration: verdict re-read on old reports (MEDIUM severity / MEDIUM confidence)

**What:** `check_analysis_report_current` (called by `workflow.py::_require_current_analysis_report`
and the implement gate) reads the frontmatter but only checks `artifact_type` and `input_artifacts` —
it does NOT currently read `verdict`. The verdict in the current frontmatter is `infer_verdict()` output
(prose-based). After IC-05, `write_analysis_report` will compute verdict from the structured
`analysis-findings/v1` carrier instead.

**Key finding:** the implement gate does NOT check `verdict == "ready"` — it only checks freshness
(`ok=True`). So a legacy report with `verdict: unknown` does NOT wedge implement. The `unknown` verdict
is a UX papercut (e.g., dashboards or review prompts that surface the verdict field), not a blocking
gate failure. The C-FIND-2 contract correctly says "legacy reports → `verdict: unknown` + remediation
hint."

**Residual risk:** if any future consumer (IC-05 introduces schema validation) re-reads an existing
report and applies *strict* schema validation rather than the legacy-fallback path, it would reject
reports that lack the `analysis-findings/v1` carrier. The plan says "missing/malformed → loud failure"
(C-FIND-1/C-FIND-2). The IC-05 implementer must ensure the "loud failure" is gated on attempting to
**re-use** the verdict (i.e., `record-analysis` write path), NOT on the `check_analysis_report_current`
freshness-check read path. Freshness check must remain schema-lenient.

**Cheapest mitigation:** add to IC-05 AC: "the `check_analysis_report_current` read path must
NOT require the `analysis-findings/v1` carrier to return `ok=True`; schema validation applies only
to the `record-analysis` write path." This is a one-line AC addition.

---

### RISK-4 — Capability spoofing: in-process construction of GuardCapability (LOW severity / HIGH confidence)

**What:** anything in-process can construct `GuardCapability(release_flow)` (once that enum exists).
The plan is aware of this; the spec frames it as "re-express prefix privileges as capabilities."

**Threat model assessment:** the realistic threat for this codebase is an LLM agent following a
misleading prompt, not an adversarial attacker. For that model the design is adequate:
- A correctly-behaving agent gets the capability from the calling surface (upgrade/merge/release code),
  not from constructing it ad-hoc from a string.
- An LLM agent cannot easily construct `GuardCapability.RELEASE_FLOW` without importing it and knowing
  the enum name — that's a higher bar than crafting a `"release: "` prefix string, which is the
  current attack vector.
- The #1355 import-boundary ratchet structurally prevents guard internals from leaking to rim callers.

**Verdict:** the design is not theater for the actual threat model. The plan's framing (caller identity,
not message content) is correct. No additional mitigation needed. If adversarial containment becomes a
requirement, that's a separate hardening mission.

---

### RISK-5 — SC-6 protected-target e2e: hermetic testing gap (MEDIUM severity / MEDIUM confidence)

**What:** SC-6 requires "a fresh mission on a protected-target repo completes specify → plan → tasks →
finalize-tasks with planning artifacts committed to their resolved destination." This requires:
1. A test repo whose `main` is a protected branch (i.e., `remote.HEAD` resolves to `main` or there is
   a config-driven protected-branch set).
2. The planning commands actually calling `ArtifactPlacementFragment` resolution.
3. The `--to-branch` in the finalize-tasks path being the resolved destination, not a hardcoded string.

**Hermetic concern:** the protected-branch detection uses `_remote_default_branch()`, which calls
`git remote show origin` or `git symbolic-ref refs/remotes/origin/HEAD`. In a hermetic test repo with
no remote, neither returns anything, so `protected_branches()` returns only `{"main", "master"}`.
A test that puts the planning branch as `main` will trigger the guard correctly. BUT: the
`_is_spec_kitty_project` check also gates the guard — a freshly-created test repo without a `.kittify`
directory bypasses the guard entirely. The E2E test must ensure the test fixture has `.kittify/`.

**Also:** the `--to-branch` flow relies on `ArtifactPlacementFragment` being resolved and threaded
through the planning commands. Until IC-04 lands, this threading does not exist and the e2e will
fail at the "finalize-tasks reads the SAME resolution" step. IC-04 must complete BEFORE SC-6 can
be validated. The plan already sequences this correctly (IC-04 depends on IC-02).

**Cheapest mitigation:** in IC-04's AC, explicitly require the hermetic E2E fixture to:
(a) have `.kittify/` present, and (b) assert that `finalize-tasks` uses the same `destination_ref` as
`specify` (not a separately re-resolved one). The fixture can be a tmp-dir git repo; no remote needed.

---

## Items Already Well-Handled (no action needed)

- **ATDD-first discipline (NFR-005):** IC-01 before IC-02 is the right ordering. The existing
  `allow_protected_branch_in_test_mode` escape hatch means tests won't be broken by the guard mid-conversion.
- **Strangler ordering for prefix-channel deletion:** plan is clear — delete only after all callers
  converted and IC-01 suite green. Sound.
- **DRG ripple risk (IC-08):** inventory-first + STOP-and-escalate is the correct mitigation for an
  unknown-size consumer graph. No additional mitigation needed.
- **`assert_not_protected_branch` dual call in safe_commit_cmd.py:** currently the CLI calls BOTH
  `assert_not_protected_branch` (line 164) and `safe_commit` (which also checks at step 6). This
  redundancy is harmless pre-IC-02, and IC-02's caller conversion will clean it up. Not a risk.

---

## Summary Table

| Risk | Severity | Confidence | Status |
|------|----------|------------|--------|
| RISK-1 Mid-strangle operator wedge | HIGH | HIGH | Mitigate in IC-02 task: wire capability grants before first caller conversion |
| RISK-2 Self-hosting guard breakage | HIGH | HIGH | Mitigate: document `SPEC_KITTY_ALLOW_PROTECTED_BRANCH_COMMITS` as escape hatch; defer prefix-channel deletion to IC-09 |
| RISK-3 Legacy report `unknown` verdict at gates | MEDIUM | MEDIUM | Mitigate in IC-05 AC: freshness-check path must not require `analysis-findings/v1` carrier |
| RISK-4 GuardCapability spoofing | LOW | HIGH | No action — adequate for the actual threat model |
| RISK-5 SC-6 e2e hermetic gap | MEDIUM | MEDIUM | Mitigate in IC-04 AC: fixture must have `.kittify/`, assert shared destination_ref |
