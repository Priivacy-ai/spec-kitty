# Contract: spec-kitty#1038 Evidence Comment Template

**Used by**: WP08
**Target issue**: `Priivacy-ai/spec-kitty#1038`

Post this comment after the Teamspace MVP canary suite passes. Do NOT close
the issue. The operator decides when to close #1038.

---

## Comment Body (verbatim, fill placeholders)

```markdown
## Canary evidence - post planning#16 auth boundary hardening

### Environment

- **CLI**: `spec-kitty-cli==<VERSION>`, tag `<TAG>`, commit `<SHA>`.
- **Events**: `spec-kitty-events==<EVENTS_VERSION>`, tag `<EVENTS_TAG>`, commit `<EVENTS_SHA>`.
- **SaaS**: Fly image `<FLY_IMAGE>`, git SHA `<SAAS_SHA>`, `/health/` 200, `/health/ready/` 200.
- **Drain counts**: `terminal_failed_infra=0`, `terminal_failed_business_rule=22`.

### Canary results

- **Identity-boundary canary**: 4/4 pass across all four consecutive runs.
  Evidence attached on Priivacy-ai/spec-kitty-end-to-end-testing#41 (now closed).
- **Teamspace MVP canary suite**: 4/4 pass.
  Logs: `/tmp/teamspace-canary-run-{1..4}.log`

### Evidence bundle

- Identity-boundary runs: `spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/<RC_TAG>-attempt<N>/runs/run-{1..4}.json`
- Teamspace logs: `/tmp/teamspace-canary-run-{1..4}.log`

### Integrity statement

No manual SaaS queue mutation, event replay, DB cleanup, daemon record surgery,
local queue deletion, or ingress-cap override was used at any point during this
gate run.
```

---

## Validation Checklist (WP08 must verify before posting)

- [ ] `<VERSION>` matches installed CLI version
- [ ] `e2e#41` is confirmed closed before posting
- [ ] Teamspace logs exist at `/tmp/teamspace-canary-run-{1..4}.log`
- [ ] All four Teamspace runs passed (no failures)
- [ ] `terminal_failed_infra` is still 0
- [ ] `business_rule_rejected_count` is still 22
- [ ] Issue is posted but NOT closed
- [ ] `gh auth status` uses keyring token (unset `GITHUB_TOKEN` if needed per CLAUDE.md)
