# Quickstart: Implement Review Retrospect Reliability

## Environment

Run Spec Kitty commands for this mission with sync disabled unless deliberately testing hosted sync behavior:

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=0 <command>
```

## Planning Artifacts

```bash
SPEC_KITTY_ENABLE_SAAS_SYNC=0 uv run spec-kitty agent mission check-prerequisites \
  --mission implement-review-retrospect-reliability-01KQQSCW \
  --json
```

## Focused Test Targets

Review-cycle boundary:

```bash
uv run pytest tests/review/test_cycle.py -q
```

Rejection transition:

```bash
uv run pytest tests/integration/review/test_reject_from_in_review.py -q
```

Fix-mode pointer loading:

```bash
uv run pytest tests/agent/test_workflow_feedback_pointer_2x_unit.py -q
```

Next routing:

```bash
uv run pytest tests/next/test_finalized_task_routing.py -q
```

Retrospective missing record:

```bash
uv run pytest tests/cli/test_agent_retrospect_missing_record.py -q
```

## Required Smoke Flow

1. Create or load a temporary mission fixture with finalized tasks.
2. Move a WP into review.
3. Reject it with a review feedback file.
4. Verify the artifact frontmatter and canonical pointer.
5. Verify fix-mode can load that pointer.
6. Approve or complete the WP.
7. Verify `spec-kitty next` routes from task/WP state.
8. Verify `agent retrospect` has a first-class path on the completed mission.

## Acceptance Checks

Before mission acceptance, run the targeted tests above plus any directly impacted existing tests:

```bash
uv run pytest tests/review tests/integration/review tests/status/test_transitions.py tests/status/test_emit.py tests/next tests/cli/test_agent_retrospect_synthesize.py -q
```

If a verification command touches hosted auth, tracker, SaaS sync, or sync finalization, document why sync is in scope and run the command with the environment requested for that verification.
