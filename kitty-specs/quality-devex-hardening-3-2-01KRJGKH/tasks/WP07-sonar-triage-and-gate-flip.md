---
work_package_id: WP07
title: Sonar hotspot non-regex triage + push-time Sonar restoration
dependencies:
- WP04
- WP05
- WP06
requirement_refs:
- FR-003
- FR-004
- FR-013
planning_base_branch: fix/quality-check-updates
merge_target_branch: fix/quality-check-updates
branch_strategy: Planning artifacts for this mission were generated on fix/quality-check-updates. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into fix/quality-check-updates unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
- T038
- T039
agent: "claude:opus:reviewer-renata:reviewer"
shell_pid: "1155493"
history:
- at: '2026-05-14'
  actor: planner
  event: created
agent_profile: python-pedro
authoritative_surface: .github/workflows/ci-quality.yml
execution_mode: code_change
mission_id: 01KRJGKH4DJCSF277K9QV3WBE7
mission_slug: quality-devex-hardening-3-2-01KRJGKH
owned_files:
- .github/workflows/ci-quality.yml
- kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP07.md
- tests/agent/cli/commands/test_sync.py
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

## Objective

Triage the remaining 5 non-regex Sonar security hotspots (loopback `127.0.0.1` × 4 in auth/sync callback paths; review-lock signal safety × 1) and flip the push-time Sonar gate. The flip is the final acceptance for FR-004 (#825) and is gated on Sonar status = OK on `main`.

Pedro note: this WP is partly outside Python-implementer specialization (the CI yaml change is infra). Coordinate the workflow flip with the infra reviewer; the hotspot triage is in Pedro's scope (rationale wording for safe-by-design findings + any small code fix).

## Context

### Hotspots to resolve

From `work/findings/595-sonar-coverage-debt.md`:

1. **Loopback `http://127.0.0.1` (4 hotspots)** — in the auth callback server and sync callback paths. Sonar flags any literal loopback URL as a potential information-disclosure / SSRF risk. In this codebase, the loopback URLs are intentional: the OAuth callback server is local-only by design.
2. **Review-lock signal safety (1 hotspot)** — Sonar flags signal-handler installation in `review/lock.py` (or similar) as potentially unsafe. Triage on its merits — either fix or document.

### Workflow current state

`.github/workflows/ci-quality.yml::sonarcloud` line 1976:

```yaml
if: always() && (github.event_name == 'schedule' || github.event_name == 'workflow_dispatch')
```

The header comment block above the job says:
> Temporarily limited to schedule/manual runs while #825 tracks the existing project-wide Sonar quality gate backlog.

Both the conditional and the comment block must be updated.

## Doctrine Citations

This WP applies:

- [`secure-design-checklist`](../../../src/doctrine/tactics/shipped/secure-design-checklist.tactic.yaml) — applied to the review-lock signal-safety hotspot if a code fix is needed (security-sensitive surface).

## Branch Strategy

- Planning / base branch: `fix/quality-check-updates`.
- Final merge target: `fix/quality-check-updates`.

## Subtasks

### T035 — Draft `127.0.0.1` loopback hotspot rationales for operator to apply

**Purpose**: Resolve 4 non-regex hotspots. Sonar UI write access lives with the operator; the implementer drafts rationales for operator-led application.

**Steps**:

1. Identify each `127.0.0.1` hotspot via:
   ```bash
   bash work/snippets/sonarcloud_branch_review.sh Priivacy-ai_spec-kitty main | grep -B1 -A2 "127.0.0.1"
   ```
2. For each hotspot, read the surrounding code:
   - `src/specify_cli/auth/loopback/callback_server.py`
   - `src/specify_cli/sync/...` (whichever callback variant Sonar flagged)
3. Author a rationale (one paragraph per hotspot) for the safe-by-design call:
   - The OAuth callback server binds to `127.0.0.1` by design — that is the entire point of the loopback flow (RFC 8252 §7.3). The server accepts only the one-time authorization code; it does not expose any other endpoint or accept any other data.
   - The bound port is ephemeral and the server lifetime is short (only during the auth flow).
   - There is no information-disclosure risk because the address is `localhost`, accessible only from the same host.
4. Append the drafted rationales to `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/sonar-hotspot-rationales.md` under a `## Loopback (127.0.0.1) hotspots` heading. WP04 created the file for regex rationales; this WP appends.
5. Hand off to operator: WP07's commit message includes a "Sonar handoff:" block listing each hotspot ID and the rationale file path.

**Validation**:

- All 4 loopback hotspots have draft rationales in `sonar-hotspot-rationales.md`.
- The handoff block is in the commit message.

### T036 — Triage review-lock signal-safety hotspot

**Purpose**: Resolve the remaining hotspot.

**Steps**:

1. Identify the file via:
   ```bash
   bash work/snippets/sonarcloud_branch_review.sh Priivacy-ai_spec-kitty main | grep -i "signal\|lock"
   ```
2. Read the flagged code. Sonar flags signal-handler installation that:
   - Calls non-async-signal-safe functions from the handler.
   - Installs handlers in unexpected scopes.
   - Does not restore previous handlers on cleanup.
3. Determine if a code fix is warranted:
   - If the handler calls non-AS-safe functions (e.g. `logging.warning`, file writes), fix: defer to a flag set in the handler, then process on the main path. If the file lies outside WP07's `owned_files`, halt and surface to operator for scope expansion or coordination with the file's owning WP.
   - If the handler is correct, append a safe-by-design rationale to `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/sonar-hotspot-rationales.md` under `## Review-lock signal safety`.
4. The operator applies the Sonar UI annotation.

**Validation**:

- The hotspot is either fixed in code AND has a regression test, OR has a documented rationale in `sonar-hotspot-rationales.md` for operator application.

### T037 — Verify Sonar gate is OK on `main`

**Purpose**: Pre-flip verification. The trigger flip cannot land unless the gate is already green.

**Steps**:

1. Run:
   ```bash
   bash work/snippets/sonarcloud_branch_review.sh Priivacy-ai_spec-kitty main | head -20
   ```
2. Confirm:
   ```
   === Quality Gate ===
   status: OK
   ```
3. Confirm every gate condition:
   - `new_reliability_rating: OK`
   - `new_security_rating: OK`
   - `new_maintainability_rating: OK`
   - `new_coverage: OK` (i.e. ≥ 80 % per the threshold)
   - `new_duplicated_lines_density: OK`
   - `new_security_hotspots_reviewed: OK` (i.e. 100 %)
4. If any condition is `ERROR`, do NOT proceed to T038. Re-coordinate with the relevant upstream WP (likely WP05 for coverage; T035/T036 for hotspots).
5. Save the verification output as WP07 evidence (`kitty-specs/quality-devex-hardening-3-2-01KRJGKH/sonar-pre-flip-verification.txt`).

**Validation**:

- Sonar `status: OK` on `main`.
- Every condition `OK`.

### T038 — Flip `.github/workflows/ci-quality.yml::sonarcloud` trigger to `always()`

**Purpose**: Restore push-time Sonar.

**Steps**:

1. Open `.github/workflows/ci-quality.yml`.
2. Locate the `sonarcloud:` job (around line 1944 per current main).
3. Update the `if:` line:
   ```yaml
   # BEFORE
   if: always() && (github.event_name == 'schedule' || github.event_name == 'workflow_dispatch')

   # AFTER
   if: always()
   ```
4. Remove the temporary header comment block:
   ```yaml
   # DELETE these lines:
   # Temporarily limited to schedule/manual runs while #825 tracks the existing
   # project-wide Sonar quality gate backlog. PRs skip Sonar entirely to keep
   # review latency low, and pushes skip it so main can report test/build health.
   # ---------------------------------------------------------------------------
   ```
5. Commit and push.
6. Trigger a `main` push (e.g. via this WP's PR merge) and verify the next `CI Quality` workflow run shows the `sonarcloud` step as `success`, not `skipped`.

**Files**: `.github/workflows/ci-quality.yml` (modified, ~5 line change).

**Validation**:

- `if: always()` condition is in place.
- Deferral comment block is removed.
- Next push run shows `sonarcloud` step `success`.

### T039 — Glossary fragment for "Sonar quality gate"

**Purpose**: FR-013.

**Steps**:

1. Author `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP07.md`:
   - **`Sonar quality gate`**: "The SonarCloud project-level pass/fail evaluation for `Priivacy-ai_spec-kitty` on the new-code window. Aggregates six conditions (reliability rating, security rating, maintainability rating, new coverage, new duplicated lines density, new security hotspots reviewed). Reports `OK` or `ERROR` per condition + a top-level status. Pulled via the public REST API at `https://sonarcloud.io/api/qualitygates/project_status`; the helper `work/snippets/sonarcloud_branch_review.sh` formats this for terminal use." Confidence 0.95. Status active.
2. Stage and commit.

**Files**: `kitty-specs/quality-devex-hardening-3-2-01KRJGKH/glossary-fragments/WP07.md` (new, ~15 lines).

## Test Strategy

- This WP has no new behavior tests. The `function-over-form-testing` discipline does not extend to CI yaml or Sonar UI rationale.
- The "test" is the next-push verification at T038.

## Definition of Done

- [ ] Each non-regex Sonar hotspot (5 total) has a Sonar UI review (safe-by-design rationale or code-fix). `new_security_hotspots_reviewed` = 100 %.
- [ ] Sonar gate status `OK` on `main` (verified via the REST helper).
- [ ] `.github/workflows/ci-quality.yml::sonarcloud` runs on push events to `main`; deferral comment block removed.
- [ ] Next push to `main` produces a successful `sonarcloud` job run (verified via `gh run view`).
- [ ] `glossary-fragments/WP07.md` carries "Sonar quality gate" entry.

## Risks

- **Race condition**: another mission merges between gate-verification and trigger-flip and re-introduces gate-failing code. Mitigation: re-run the Sonar verification immediately before pushing the trigger-flip commit; if gate has regressed, coordinate with the merge-triggering mission's owner.
- **Sonar UI access**: if Pedro cannot apply rationales directly in Sonar, record them in `sonar-hotspot-rationales.md` and coordinate with a Sonar admin.
- **`_auth_doctor.render_report` (CC 53, deliberate linearity)**: if Sonar's maintainability rating fails because of this function, escalate per spec C-003 — do NOT refactor without auth-maintainer sign-off. Resolution path: per-file Sonar rationale annotation.

## Reviewer Guidance

When reviewing this WP, check:

1. Every hotspot has a Sonar review — none remain unreviewed.
2. Loopback rationales cite RFC 8252 §7.3 (or equivalent) and explicitly state "localhost-only, ephemeral, single-use".
3. Sonar status `OK` on `main` BEFORE the workflow trigger flip lands.
4. The workflow change is the minimal `if:` flip + comment-block deletion — no unrelated workflow modifications.
5. No `_auth_doctor.render_report` refactor was attempted (constraint C-003).

## Implementation command

```bash
spec-kitty agent action implement WP07 --agent claude
```

## Activity Log

- 2026-05-14T10:21:39Z – claude:sonnet:python-pedro:implementer – shell_pid=1149274 – Started implementation via action command
- 2026-05-14T10:29:41Z – claude:sonnet:python-pedro:implementer – shell_pid=1149274 – HALT at T037: gate ERROR on two conditions. T035: 4 loopback encrypt-data hotspot rationales drafted (IDs: AZ12J6Ty_lKMvCuaCZvj, AZ12J6Ty_lKMvCuaCZvk, AZ0QUf1nmOedRvCFo5GK, AZ1ZVYN5Ubbqgtr7cvkz) — operator must apply in Sonar UI. T036: no signal-safety hotspot found in TO_REVIEW queue; documented. T037: new_coverage=58.9%/80% ERROR, new_security_hotspots_reviewed=0%/100% ERROR — T038 NOT executed, gate flip held. T039: glossary fragment WP07.md committed. Item A: test_strict_exits_0_on_success fixed (commit 80f71fe14, mirrors PR #1035 pattern). Three operator options for coverage gap in sonar-pre-flip-verification.txt.
- 2026-05-14T10:30:47Z – claude:opus:reviewer-renata:reviewer – shell_pid=1155493 – Started review via action command
- 2026-05-14T10:33:13Z – claude:opus:reviewer-renata:reviewer – shell_pid=1155493 – APPROVED with operator handoff: in-scope completed work (4 loopback hotspot rationales drafted for Sonar UI application; review-lock hotspot documented as N/A with template for future use; gate verification + gap analysis written to sonar-pre-flip-verification.txt; glossary fragment landed; Item A pre-existing test_strict_exits_0_on_success failure fixed via PR #1035 pattern mirror in commit 80f71fe14 — 5 sibling failures correctly left in place as out-of-mandate); T038 trigger flip HELD per documented halt condition (Sonar gate ERROR: new_coverage 58.9% vs 80%, new_security_hotspots_reviewed 0% pending operator UI action). Operator handoff: three options for unblocking T038 are in sonar-pre-flip-verification.txt — (A) defer T038 to follow-up coverage WP, (B) renegotiate Sonar threshold, (C) baseline reset (Pedro recommends against). WP07 can be reopened post-operator-decision for the trigger flip + a final mission-merge commit.
