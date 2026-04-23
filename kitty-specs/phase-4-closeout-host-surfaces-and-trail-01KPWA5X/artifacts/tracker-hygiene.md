# Tracker Hygiene Runbook — Phase 4 Closeout

**Mission**: `phase-4-closeout-host-surfaces-and-trail-01KPWA5X`
**Mission ID**: `01KPWA5X6617T5TVX4C7S6TMYB`
**Baseline commit**: `eb32cf0a` on `origin/main` (2026-04-23)
**Target branch**: `main`
**Status**: Pending merge. This runbook is executed by the release owner at the time the mission PR is merged to `main`.

## Purpose

Execute the GitHub tracker updates FR-014 requires as part of the mission's Definition of Done:
- Close `#496` (Phase 4 host-surface breadth follow-on).
- Close `#701` (Phase 4 trail follow-on).
- Update `#466` (Phase 4 tracker) — Phase 4 follow-on shipped.
- Cross-link `#534` to `#499` and `#759` as Phase 5 glossary-foundation unblocker.
- Verify `#461` (umbrella roadmap) stays OPEN.
- (Optional) Retitle `#496` to reflect delivered scope.

**Auth note**: per project CLAUDE.md, organisation-repo `gh` commands may require unsetting `GITHUB_TOKEN` to use keyring authentication. Prefix each command with `unset GITHUB_TOKEN && ...`.

## Pre-flight Checklist

Before executing the hygiene actions, confirm:

- [ ] The mission PR has been merged to `main` (record the PR number below).
- [ ] `docs/host-surface-parity.md` exists on `main` with all 15 surfaces listed.
- [ ] `docs/trail-model.md` on `main` contains the new subsections (Mode Enforcement, Correlation Links, SaaS Read-Model Policy, Tier 2 Deferred, Host surfaces).
- [ ] `src/specify_cli/invocation/projection_policy.py` exists on `main`.
- [ ] `CHANGELOG.md` on `main` has the Tranche A + Tranche B unreleased entries.

**Merge PR number**: `#<PR_NUMBER>` (fill in at execution time).

## Commands (copy-paste at merge time)

### 1. Close `#496` (Tranche A delivery)

```bash
unset GITHUB_TOKEN && gh issue close 496 --comment "Closed by mission phase-4-closeout-host-surfaces-and-trail-01KPWA5X (merge PR #<PR_NUMBER>).

Host-surface breadth rollout complete:
- 15 supported host surfaces audited and at parity (inline or pointer).
- Matrix promoted to docs/host-surface-parity.md.
- Coverage test in tests/specify_cli/docs/test_host_surface_inventory.py.
- Dashboard Feature → Mission Run user-visible rename shipped (FR-003).
- README Governance layer subsection shipped."
```

Verify: `unset GITHUB_TOKEN && gh issue view 496 --json state,closedAt`

### 2. Close `#701` (Tranche B delivery)

```bash
unset GITHUB_TOKEN && gh issue close 701 --comment "Closed by mission phase-4-closeout-host-surfaces-and-trail-01KPWA5X (merge PR #<PR_NUMBER>).

Trail follow-on deliverables:
- Correlation contract: append-only artifact_link / commit_link events on invocation JSONL; --artifact (repeatable) + --commit (singular) on profile-invocation complete. See ADR-001.
- Mode of work runtime-derived and recorded on started event; enforced at Tier 2 promotion boundary. See ADR-002.
- SaaS read-model policy: typed projection_policy.py module with POLICY_TABLE covering all (mode, event) pairs. See ADR-003.
- Tier 2 SaaS projection decisively deferred; evidence remains local-only in 3.2.x. See ADR-004.

Decisions recorded as ADRs in kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/decisions/.
Operator docs updated in docs/trail-model.md."
```

Verify: `unset GITHUB_TOKEN && gh issue view 701 --json state,closedAt`

### 3. Update `#466` (Phase 4 tracker)

```bash
unset GITHUB_TOKEN && gh issue comment 466 --body "Phase 4 follow-on (mission phase-4-closeout-host-surfaces-and-trail-01KPWA5X) has shipped on main.

Delivered in this closeout:
- #496 host-surface breadth rollout — CLOSED
- #701 trail follow-on — CLOSED
- docs/trail-model.md updated with Mode of Work enforcement, Correlation Links, SaaS Read-Model Policy table, and Tier 2 SaaS Projection deferral.
- docs/host-surface-parity.md is the new authoritative matrix.

Remaining deferred: #534 spec-kitty explain (blocked on Phase 5 glossary foundation; see #499 and #759)."
```

Leave `#466` OPEN if other Phase 4 scope remains. Close only if this was the last open child.

### 4. Cross-link `#534` to Phase 5 unblockers

```bash
unset GITHUB_TOKEN && gh issue comment 534 --body "Deferral confirmed by Phase 4 closeout (mission phase-4-closeout-host-surfaces-and-trail-01KPWA5X).

\`spec-kitty explain\` requires DRG glossary addressability to produce fully-cited answers. Phase 5 glossary foundation shipped as #759; further glossary addressability work is tracked in #499. This issue remains blocked on those until a fully-cited explain surface is achievable.

See ADR-004-tier2-saas-deferral.md (same mission) for the closeout's decisive-deferral pattern."
```

Do NOT close `#534`. Verify: `unset GITHUB_TOKEN && gh issue view 534 --json state` → state remains OPEN.

### 5. Verify `#461` (umbrella roadmap) stays open

```bash
unset GITHUB_TOKEN && gh issue view 461 --json state,title
```

Expected: `state=OPEN`. If unexpectedly closed, reopen:
```bash
unset GITHUB_TOKEN && gh issue reopen 461 --comment "Keeping umbrella roadmap open for subsequent phases."
```

### 6. (Optional) Retitle `#496`

```bash
unset GITHUB_TOKEN && gh issue edit 496 --title "[Phase 4] Host-surface breadth rollout — delivered"
```

Skip if the operator prefers to preserve the original issue title for historical clarity.

## Completion Record (fill at execution time)

| # | Issue | Action | Executed at (ISO-8601) | Verified |
|---|-------|--------|------------------------|----------|
| 1 | #496 | Closed with delivery comment | | [ ] |
| 2 | #701 | Closed with delivery comment | | [ ] |
| 3 | #466 | Commented: Phase 4 follow-on shipped | | [ ] |
| 4 | #534 | Cross-linked to #499 / #759 (state=OPEN) | | [ ] |
| 5 | #461 | Verified OPEN | | [ ] |
| 6 | #496 | (optional) Retitled | | [ ] |

**Executed by**: `<operator GitHub handle>`
**Merge commit SHA**: `<fill in>`

## Post-Execution PR Description Line

Add this line to the mission PR description once all actions are executed:

```
Tracker hygiene: closes #496, closes #701; comments on #466, #534; keeps #461 open. Full runbook and record in kitty-specs/phase-4-closeout-host-surfaces-and-trail-01KPWA5X/artifacts/tracker-hygiene.md.
```

## Notes

- This file serves as both the pre-merge runbook and the post-merge audit record.
- All tracker actions are scheduled for the merge event — they do NOT run during mission implementation.
- `Closes #496` in WP05's commit message (`356d5f1c`) will auto-close `#496` on PR merge if GitHub detects the reference, but the manual close comment above is still preferred for the rich delivery description.
