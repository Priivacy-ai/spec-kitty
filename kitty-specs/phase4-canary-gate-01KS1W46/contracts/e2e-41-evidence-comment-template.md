# Contract: e2e#41 Evidence Comment Template

**Used by**: WP06
**Target issue**: `Priivacy-ai/spec-kitty-end-to-end-testing#41`

All fields marked `<REQUIRED>` must be populated before posting. The comment
must be posted verbatim (with placeholders replaced); no fields may be omitted.
After posting, close the issue immediately. Do not close before posting.

---

## Comment Body (verbatim, fill placeholders)

```markdown
## Auth identity-boundary canary — 4/4 pass evidence

### Environment

- **CLI**: `spec-kitty-cli==<VERSION>`, tag `<TAG>`, commit `<SHA>`
- **SaaS**: Fly image `<FLY_IMAGE>`, git SHA `<SAAS_SHA>`
- **Events package**: `spec-kitty-events==<EVENTS_VERSION>`

### Health snapshot (taken immediately before four-run protocol)

- `/health/` → 200, `spec_kitty_events: <EVENTS_VERSION>`
- `/health/ready/` → 200
- `terminal_failed_count`: 0 (infra)
- `business_rule_rejected_count`: 22 (historical, unchanged)

### Four-run protocol results

| Run | Outcome | Scenario 1 | Scenario 2 | Scenario 3 | Scenario 4 |
|-----|---------|-----------|-----------|-----------|-----------|
| 1   | PASS    | pass      | pass      | pass      | pass      |
| 2   | PASS    | pass      | pass      | pass      | pass      |
| 3   | PASS    | pass      | pass      | pass      | pass      |
| 4   | PASS    | pass      | pass      | pass      | pass      |

### Evidence paths

- `artifacts/sync_identity_boundary/<RC_TAG>-attempt<N>/runs/run-1.json`
- `artifacts/sync_identity_boundary/<RC_TAG>-attempt<N>/runs/run-2.json`
- `artifacts/sync_identity_boundary/<RC_TAG>-attempt<N>/runs/run-3.json`
- `artifacts/sync_identity_boundary/<RC_TAG>-attempt<N>/runs/run-4.json`

### Integrity statement

No manual SaaS queue mutation, Fly DB edits, daemon record surgery, local
queue deletion, event replay, or ingress-cap override was used at any point
during or between the four runs.
```

---

## Validation Checklist (WP06 must verify before posting)

- [ ] `<VERSION>` matches `spec-kitty --version` output
- [ ] `<TAG>` matches the git tag on the installed SHA
- [ ] `<SHA>` is at or after `cc5e1ca983adff4a45489ce7afe11ad3a3a26e30`
- [ ] `<FLY_IMAGE>` matches `flyctl status -a spec-kitty-dev` image field
- [ ] `<SAAS_SHA>` matches the SHA of the deployed SaaS image
- [ ] `/health/ready/` was 200 at the time of the snapshot
- [ ] `terminal_failed_count` (infra) is 0
- [ ] `business_rule_rejected_count` is still 22
- [ ] All 16 scenario cells show `pass`
- [ ] Evidence JSON files exist on disk and contain `"outcome": "pass"`
- [ ] No `pkill`, `flyctl ssh console`, or queue-file deletion was run between runs
