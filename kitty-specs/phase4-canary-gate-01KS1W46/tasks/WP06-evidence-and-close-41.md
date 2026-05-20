---
work_package_id: WP06
title: Evidence Collection and Close e2e#41
dependencies:
- WP05
requirement_refs:
- C-006
- FR-011
- FR-012
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T028
- T029
- T030
- T031
- T032
- T033
agent: "claude:sonnet-4-6:reviewer:reviewer"
shell_pid: "65704"
history:
- date: '2026-05-20'
  event: created
agent_profile: implementer
authoritative_surface: kitty-specs/phase4-canary-gate-01KS1W46/tasks/
execution_mode: planning_artifact
owned_files:
- kitty-specs/phase4-canary-gate-01KS1W46/tasks/WP06-evidence-and-close-41.md
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

Collect all required evidence metadata, post the evidence comment to
`Priivacy-ai/spec-kitty-end-to-end-testing#41` using the exact template
from `kitty-specs/phase4-canary-gate-01KS1W46/contracts/e2e-41-evidence-comment-template.md`,
and close the issue.

**Note**: PR #42 and PR #44 are already merged to e2e `main`. The "merge PR #42"
step from start-here.md Phase 5 is a **no-op** — do not attempt it again (Constraint C-006).

---

## Context

After WP05 produces 4/4 green, this WP assembles the evidence package and
closes the gate issue. The comment must satisfy every field in the template
contract before closing.

---

## Subtask T028: Gather Environment Metadata

**Purpose**: Collect the exact CLI, SaaS, and events version strings for the comment.

```bash
# CLI version and SHA
CLI_VERSION=$(/Users/robert/.local/bin/spec-kitty --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+rc[0-9]+')
echo "CLI version: $CLI_VERSION"

# Git tag and commit for installed CLI
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty
CLI_TAG="v${CLI_VERSION}"
CLI_SHA=$(git rev-parse "${CLI_TAG}^{commit}" 2>/dev/null || echo "unknown")
echo "CLI tag: $CLI_TAG, SHA: $CLI_SHA"

# SaaS Fly image
FLY_IMAGE=$(flyctl status -a spec-kitty-dev --json 2>/dev/null \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Image','unknown'))" 2>/dev/null \
  || flyctl status -a spec-kitty-dev 2>/dev/null | grep -i image | head -1)
echo "Fly image: $FLY_IMAGE"

# SaaS git SHA (from last Deploy run)
SAAS_SHA=$(gh run list --repo Priivacy-ai/spec-kitty-saas \
  --workflow Deploy --branch main --limit 1 \
  --json headSha --jq '.[0].headSha' 2>/dev/null || echo "unknown")
echo "SaaS SHA: $SAAS_SHA"

# Events version (from /health/ response)
EVENTS_VERSION=$(curl -sS --max-time 5 https://spec-kitty-dev.fly.dev/health/ \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('spec_kitty_events','?'))")
echo "Events version: $EVENTS_VERSION"
```

T028 and T029 can run concurrently.

---

## Subtask T029: Take Post-Run Health Snapshot

**Purpose**: Capture the final health state at the time of evidence collection.

```bash
echo "=== /health/ ===" && curl -sS --max-time 5 https://spec-kitty-dev.fly.dev/health/ | python3 -m json.tool
echo "=== /health/ready/ ===" && curl -sS --max-time 5 https://spec-kitty-dev.fly.dev/health/ready/ | python3 -m json.tool

# Final drain counts
flyctl ssh console -a spec-kitty-dev -C "sh -lc 'cd /code && /code/.venv/bin/python manage.py shell <<PYEOF
from apps.sync.models import BatchIntakeItem
infra = BatchIntakeItem.objects.filter(state=\"terminal_failed\", last_failure_class=\"infra\").count()
br = BatchIntakeItem.objects.filter(state=\"terminal_failed\", last_failure_class=\"business_rule\").count()
print(f\"terminal_failed_count={infra}\")
print(f\"business_rule_rejected_count={br}\")
PYEOF'"
```

Record: `terminal_failed_count=<N>`, `business_rule_rejected_count=22`.

---

## Subtask T030: Bundle Evidence Tarball

**Purpose**: Create a portable evidence archive.

```bash
cd /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty-end-to-end-testing

RC_TAG="v${CLI_VERSION}"
EVIDENCE_DIR="artifacts/sync_identity_boundary/runs"

tar czf /tmp/sync-identity-boundary-evidence-$(date +%Y%m%d-%H%M).tar.gz \
  "$EVIDENCE_DIR"/run-{1,2,3,4}.json \
  artifacts/sync_identity_boundary/latest.json

echo "Evidence bundle: /tmp/sync-identity-boundary-evidence-*.tar.gz"
ls -lh /tmp/sync-identity-boundary-evidence-*.tar.gz
```

---

## Subtask T031: Post Evidence Comment to e2e#41

**Purpose**: Post the evidence comment using the exact template from the contracts directory.

Read the template first:
```bash
cat /Users/robert/spec-kitty-dev/spec-kitty-20260518-205752-xgdiSS/spec-kitty/kitty-specs/phase4-canary-gate-01KS1W46/contracts/e2e-41-evidence-comment-template.md
```

Then construct and post the comment (replace all `<PLACEHOLDER>` values):

```bash
unset GITHUB_TOKEN
gh issue comment 41 --repo Priivacy-ai/spec-kitty-end-to-end-testing --body "$(cat <<EOF
## Auth identity-boundary canary — 4/4 pass evidence

### Environment

- **CLI**: \`spec-kitty-cli==${CLI_VERSION}\`, tag \`${CLI_TAG}\`, commit \`${CLI_SHA}\`
- **SaaS**: Fly image \`${FLY_IMAGE}\`, git SHA \`${SAAS_SHA}\`
- **Events package**: \`spec-kitty-events==${EVENTS_VERSION}\`

### Health snapshot (taken immediately before four-run protocol)

- \`/health/\` → 200, \`spec_kitty_events: ${EVENTS_VERSION}\`
- \`/health/ready/\` → 200
- \`terminal_failed_count\`: 0 (infra)
- \`business_rule_rejected_count\`: 22 (historical, unchanged)

### Four-run protocol results

| Run | Outcome | Scenario 1 | Scenario 2 | Scenario 3 | Scenario 4 |
|-----|---------|-----------|-----------|-----------|-----------|
| 1   | PASS    | pass      | pass      | pass      | pass      |
| 2   | PASS    | pass      | pass      | pass      | pass      |
| 3   | PASS    | pass      | pass      | pass      | pass      |
| 4   | PASS    | pass      | pass      | pass      | pass      |

### Evidence paths

- \`artifacts/sync_identity_boundary/runs/run-1.json\`
- \`artifacts/sync_identity_boundary/runs/run-2.json\`
- \`artifacts/sync_identity_boundary/runs/run-3.json\`
- \`artifacts/sync_identity_boundary/runs/run-4.json\`

### Integrity statement

No manual SaaS queue mutation, Fly DB edits, daemon record surgery, local
queue deletion, event replay, or ingress-cap override was used at any point
during or between the four runs.
EOF
)"
```

Verify the comment was posted:
```bash
unset GITHUB_TOKEN
gh issue view 41 --repo Priivacy-ai/spec-kitty-end-to-end-testing --comments \
  | tail -40
```

---

## Subtask T032: Close e2e#41

**Purpose**: Close the MVP blocker canary issue now that evidence is attached.

```bash
unset GITHUB_TOKEN
gh issue close 41 --repo Priivacy-ai/spec-kitty-end-to-end-testing \
  --comment "Closing: 4/4 canary evidence attached above. Identity-boundary gate complete."
```

---

## Subtask T033: Verify #41 is Closed

**Purpose**: Confirm the issue state.

```bash
unset GITHUB_TOKEN
gh issue view 41 --repo Priivacy-ai/spec-kitty-end-to-end-testing \
  --json state,closedAt \
  | python3 -m json.tool
```

**Expected**: `"state": "CLOSED"` with non-null `closedAt`.

---

## Definition of Done

- [ ] T028: CLI version, tag, SHA, SaaS image, events version all captured
- [ ] T029: Health snapshot shows /health/ready/ = 200, terminal_failed_infra = 0, business_rule = 22
- [ ] T030: Evidence tarball created at `/tmp/sync-identity-boundary-evidence-*.tar.gz`
- [ ] T031: Evidence comment posted to e2e#41 with all template fields populated
- [ ] T032: e2e#41 closed with final comment
- [ ] T033: e2e#41 state = CLOSED confirmed

---

## Risks

| Risk | Mitigation |
|------|-----------|
| PR #42 merge attempt | Skip — already merged (C-006) |
| GitHub token scope errors | `unset GITHUB_TOKEN` per CLAUDE.md |
| Missing run-N.json files | T030 catches this |
| Template fields incomplete | Verify all `<PLACEHOLDER>` strings are replaced before posting |

---

## Reviewer Guidance

- Confirm the comment body matches the template contract with no missing fields
- Verify #41 is CLOSED (not just commented)
- Evidence tarball must exist and contain all 4 run JSON files

---

## Branch Strategy

Planning branch: `main`. Merge target: `main`.
Run `spec-kitty agent action implement WP06 --agent claude` to start this WP.

## Activity Log

- 2026-05-20T05:26:11Z – claude:sonnet-4-6:implementer:implementer – shell_pid=64426 – Started implementation via action command
- 2026-05-20T05:27:49Z – claude:sonnet-4-6:implementer:implementer – shell_pid=64426 – Deferred: all subtasks pending WP04 canary pass. Result document: wpwp06-*-result.md.
- 2026-05-20T05:28:00Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=65704 – Started review via action command
- 2026-05-20T05:28:20Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=65704 – Review passed: deferral correctly documented with gate condition. No out-of-scope actions. Constraints respected (C-006, C-007). Re-execute when WP04 single-run canary passes.
- 2026-05-20T11:47:32Z – claude:sonnet-4-6:reviewer:reviewer – shell_pid=65704 – Re-activating: blockers #1141 and #1182 closed; rc16 published
