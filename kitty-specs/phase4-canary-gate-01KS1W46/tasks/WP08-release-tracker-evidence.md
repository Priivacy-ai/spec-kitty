---
work_package_id: WP08
title: Release Tracker Evidence Comment
dependencies:
- WP07
requirement_refs:
- C-007
- FR-014
- FR-015
planning_base_branch: main
merge_target_branch: main
branch_strategy: 'Planning branch: main. Merge target: main.'
subtasks:
- T040
- T041
- T042
- T043
agent: claude
history:
- date: '2026-05-20'
  event: created
agent_profile: implementer
authoritative_surface: kitty-specs/phase4-canary-gate-01KS1W46/
execution_mode: planning_artifact
owned_files:
- kitty-specs/phase4-canary-gate-01KS1W46/**
role: implementer
tags: []
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load implementer
```

Read the entire prompt before acting.

---

## Objective

Post the release-tracker evidence comment to `Priivacy-ai/spec-kitty#1038` using
the exact template from `contracts/issue-1038-evidence-comment-template.md`.

**Critical constraint (FR-015, C-007)**: Do NOT close #1038. The release decision belongs to the operator.

---

## Context

`#1038` is the Teamspace MVP release tracker. It receives evidence but stays open until the operator decides to close it. This is the final step of the Phase 4 gate.

After posting, the full report from start-here.md "Final Answer Expected From You" must be provided.

---

## Subtask T040: Bundle Teamspace Log Tarball

**Purpose**: Create a portable archive of the Teamspace canary evidence.

```bash
cd /tmp
tar czf teamspace-mvp-canary-evidence-$(date +%Y%m%d-%H%M).tar.gz \
  teamspace-canary-run-1.log \
  teamspace-canary-run-2.log \
  teamspace-canary-run-3.log \
  teamspace-canary-run-4.log \
  teamspace-canary-run-1.xml 2>/dev/null || \
tar czf teamspace-mvp-canary-evidence-$(date +%Y%m%d-%H%M).tar.gz \
  teamspace-canary-run-*.log

TEAMSPACE_BUNDLE=$(ls -t /tmp/teamspace-mvp-canary-evidence-*.tar.gz | head -1)
echo "Teamspace bundle: $TEAMSPACE_BUNDLE"
```

---

## Subtask T041: Gather Final Environment Metadata

**Purpose**: Collect current metadata for the #1038 comment.

```bash
# CLI
CLI_VERSION=$(/Users/robert/.local/bin/spec-kitty --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+rc[0-9]+')
CLI_TAG="v${CLI_VERSION}"
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty
CLI_SHA=$(git rev-parse "${CLI_TAG}^{commit}" 2>/dev/null || echo "unknown")

# Events
EVENTS_VERSION=$(curl -sS --max-time 5 https://spec-kitty-dev.fly.dev/health/ \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('spec_kitty_events','?'))")
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-events
EVENTS_TAG=$(git describe --tags --exact-match 2>/dev/null || git tag --sort=-creatordate | head -1)
EVENTS_SHA=$(git rev-parse HEAD)

# SaaS
FLY_IMAGE=$(flyctl status -a spec-kitty-dev 2>/dev/null | grep -i image | head -1 | awk '{print $NF}')
SAAS_SHA=$(gh run list --repo Priivacy-ai/spec-kitty-saas --workflow Deploy --branch main --limit 1 \
  --json headSha --jq '.[0].headSha' 2>/dev/null || echo "unknown")

# Drain counts
DRAIN_COUNTS=$(flyctl ssh console -a spec-kitty-dev -C "sh -lc 'cd /code && /code/.venv/bin/python manage.py shell <<PYEOF
from apps.sync.models import BatchIntakeItem
print(BatchIntakeItem.objects.filter(state=\"terminal_failed\", last_failure_class=\"infra\").count())
print(BatchIntakeItem.objects.filter(state=\"terminal_failed\", last_failure_class=\"business_rule\").count())
PYEOF'" 2>/dev/null)

echo "CLI: $CLI_VERSION / $CLI_TAG / $CLI_SHA"
echo "Events: $EVENTS_VERSION / $EVENTS_TAG / $EVENTS_SHA"
echo "SaaS image: $FLY_IMAGE / SHA: $SAAS_SHA"
echo "Drain: $DRAIN_COUNTS"
```

---

## Subtask T042: Post Evidence Comment to #1038

**Purpose**: Post the #1038 evidence comment. Do NOT close the issue.

Read the template:
```bash
cat /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty/kitty-specs/phase4-canary-gate-01KS1W46/contracts/issue-1038-evidence-comment-template.md
```

Post (fill all placeholders with values from T041):

```bash
unset GITHUB_TOKEN
gh issue comment 1038 --repo Priivacy-ai/spec-kitty --body "$(cat <<EOF
## Canary evidence - post planning#16 auth boundary hardening

### Environment

- **CLI**: \`spec-kitty-cli==${CLI_VERSION}\`, tag \`${CLI_TAG}\`, commit \`${CLI_SHA}\`.
- **Events**: \`spec-kitty-events==${EVENTS_VERSION}\`, tag \`${EVENTS_TAG}\`, commit \`${EVENTS_SHA}\`.
- **SaaS**: Fly image \`${FLY_IMAGE}\`, git SHA \`${SAAS_SHA}\`, \`/health/\` 200, \`/health/ready/\` 200.
- **Drain counts**: \`terminal_failed_infra=0\`, \`terminal_failed_business_rule=22\`.

### Canary results

- **Identity-boundary canary**: 4/4 pass across all four consecutive runs.
  Evidence attached on Priivacy-ai/spec-kitty-end-to-end-testing#41 (now closed).
- **Teamspace MVP canary suite**: 4/4 pass.
  Logs: \`/tmp/teamspace-canary-run-{1..4}.log\`

### Evidence bundle

- Identity-boundary runs: \`spec-kitty-end-to-end-testing/artifacts/sync_identity_boundary/runs/run-{1..4}.json\`
- Teamspace logs: \`${TEAMSPACE_BUNDLE}\`

### Integrity statement

No manual SaaS queue mutation, event replay, DB cleanup, daemon record surgery,
local queue deletion, or ingress-cap override was used at any point during this
gate run.
EOF
)"
```

---

## Subtask T043: Verify #1038 Remains Open

**Purpose**: Confirm the issue was NOT accidentally closed.

```bash
unset GITHUB_TOKEN
gh issue view 1038 --repo Priivacy-ai/spec-kitty \
  --json state,closedAt \
  | python3 -m json.tool
```

**Expected**: `"state": "OPEN"`, `"closedAt": null`.

If `"state": "CLOSED"`: This is a critical error. The operator must be notified.

---

## Final Report

After T043 passes, provide the "Final Answer Expected From You" report from start-here.md:

```
## Final Report

**Workspace**: /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS

**CLI RC installed**: spec-kitty-cli==<VERSION>, tag <TAG>, commit <SHA>

**SaaS image verified**: <FLY_IMAGE>, git SHA <SAAS_SHA>
  - /health/: 200 (spec_kitty_events: <EVENTS_VERSION>)
  - /health/ready/: 200
  - terminal_failed_infra: 0
  - business_rule_rejected: 22

**Events issues #29/#31 disposition**: Both closed 2026-05-19 (superseded by #32/#33 + 5.1.0)

**PR #42 disposition**: Already merged to e2e main at a1a7518 (no-op)

**e2e#41 disposition**: CLOSED — 4/4 canary evidence attached
  Evidence: artifacts/sync_identity_boundary/runs/run-{1..4}.json

**#1038 comment**: Evidence posted; issue remains OPEN (operator closes)
  Bundle: /tmp/teamspace-mvp-canary-evidence-*.tar.gz

**Commands/tests run**:
  - gh issue view (blockers): #1141 CLOSED ✓, #1182 CLOSED ✓
  - Fix substance audit: behavioral change confirmed + test coverage confirmed
  - pipx install spec-kitty-cli==<VERSION> ✓
  - Boundary imports: specify_cli.sync.owner, specify_cli.sync.preflight ✓
  - SaaS preflight: /health/ 200, /health/ready/ 200, infra terminal_failed=0 ✓
  - Canary --single: 4/4 pass ✓
  - Canary four-run: 4 × "outcome":"pass" ✓
  - Teamspace MVP suite: 4 × pytest pass ✓

**#1141 new fix assessment**: <one-line note on whether scenario 4 held cleanly or showed any residual behavior>

**Residual blockers**: None
```

---

## Definition of Done

- [ ] T040: Teamspace log tarball created
- [ ] T041: All environment metadata collected
- [ ] T042: Evidence comment posted to #1038 with all template fields
- [ ] T043: #1038 confirmed OPEN (not closed)
- [ ] Final report provided

---

## Risks

| Risk | Mitigation |
|------|-----------|
| Accidentally closing #1038 | T043: verify OPEN after comment |
| Token scope errors | `unset GITHUB_TOKEN` per CLAUDE.md |
| Teamspace log files missing | T040: ls /tmp/teamspace-canary-run-*.log before bundling |
| Template placeholders not all replaced | Review comment body before posting |

---

## Reviewer Guidance

- Confirm #1038 is OPEN after the comment
- Verify all `<PLACEHOLDER>` strings are replaced in the comment
- The "no mutation" statement must be present verbatim

---

## Branch Strategy

Planning branch: `main`. Merge target: `main`.
Run `spec-kitty agent action implement WP08 --agent claude` to start this WP.
