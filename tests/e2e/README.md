# E2E Tests for Mission Collaboration CLI

## Overview

End-to-end tests for mission collaboration features against real SaaS dev environment.

Tests verify all 5 success criteria from feature 040:
1. **0 warnings when focus differs** - Concurrent development without false positives
2. **100% collision detection, < 500ms latency** - Real-time collision detection
3. **< 30s handoff, 0 lock releases** - Organic handoffs without explicit locks
4. **100% replay success, < 10s latency** - Offline work replay
5. **Adapter equivalence** - Verified in contract tests (WP07, WP08, WP09)

## Prerequisites

### SaaS Dev Environment

Tests require a running SaaS dev environment with:
- Mission API deployed (`/api/v1/missions`)
- Event batch ingestion endpoint (`/api/v1/events/batch/`)
- Health check endpoint (`/health`)

### Environment Variables

Set the following environment variables:

```bash
export SAAS_DEV_URL=https://dev.spec-kitty-saas.com
export SAAS_DEV_API_KEY=<dev-api-key>
```

**Note**: Test API keys should have full permissions to:
- Create missions
- Create participants
- Submit events
- Delete missions (cleanup)

## Running Tests

### Run all E2E tests:

```bash
pytest tests/e2e/test_collaboration_scenario.py -v
```

### Run specific test:

```bash
pytest tests/e2e/test_collaboration_scenario.py::test_collision_detection -v
```

### Run full scenario test (slow):

```bash
pytest tests/e2e/test_collaboration_scenario.py::test_full_scenario -v
```

### Skip E2E tests:

If environment variables are not set, tests will automatically skip with message:
```
SKIPPED [1] tests/e2e/test_collaboration_scenario.py:38: SAAS_DEV_URL and SAAS_DEV_API_KEY required for E2E tests
```

## Test Descriptions

### test_concurrent_development

**Success Criterion #1**: 0 warnings when focus differs

Simulates two developers working in parallel on different work packages:
- Participant A: focus=wp:WP01, drive=active
- Participant B: focus=wp:WP02, drive=active
- Verifies: No collision warnings (different focus targets)

### test_collision_detection

**Success Criterion #2**: 100% collision detection, < 500ms latency

Simulates two developers attempting to work on same work package:
- Participant A: focus=wp:WP01, drive=active
- Participant B: focus=wp:WP01, drive=active (collision!)
- Verifies: ConcurrentDriverWarning emitted within 500ms

### test_organic_handoff

**Success Criterion #3**: < 30s handoff, 0 lock releases

Simulates work handoff between developers:
- Participant A: Activates WP01, then switches to WP02 (implicit release)
- Participant B: Claims WP01 after A switches
- Verifies: No collision after implicit release, handoff < 30s

### test_offline_replay

**Success Criterion #4**: 100% replay success, < 10s latency

Simulates offline work and reconnection:
- Participant C: Joins online, works offline (4 commands)
- Events queued locally during offline period
- Reconnects and replays queued events
- Verifies: All events accepted, replay < 10s

### test_full_scenario

Combined scenario running all success criteria sequentially.

### test_adapter_equivalence_reference

**Success Criterion #5**: Adapter equivalence

Reference test documenting that adapter equivalence is verified in:
- `tests/specify_cli/adapters/test_gemini.py` (WP07)
- `tests/specify_cli/cli/commands/test_mission_collaboration.py` (WP08, WP09)

## Troubleshooting

### "Mission API not found" (404)

Ensure SaaS dev environment has mission API deployed at `/api/v1/missions`.

### "Unauthorized" (401)

Check that `SAAS_DEV_API_KEY` is valid and not expired.

### "Timeout" errors

Verify SaaS dev environment is reachable:
```bash
curl -I $SAAS_DEV_URL/health
```

### High latency (> 500ms collision detection)

Check network latency to SaaS dev environment:
```bash
ping dev.spec-kitty-saas.com
```

If latency is consistently high, adjust test thresholds or use local dev environment.

## Performance Benchmarks

Expected test execution times (with SaaS dev environment):

| Test | Expected Time | Notes |
|------|---------------|-------|
| test_concurrent_development | < 5s | 2 joins + 4 commands |
| test_collision_detection | < 3s | 2 joins + 3 commands |
| test_organic_handoff | < 30s | Includes handoff timing |
| test_offline_replay | < 15s | Includes replay timing |
| test_full_scenario | < 60s | Sequential execution |
| test_adapter_equivalence_reference | < 1s | No-op test |

**Total suite**: < 2 minutes

## CI/CD Integration

For CI/CD pipelines, set environment variables as secrets:

```yaml
# GitHub Actions example
env:
  SAAS_DEV_URL: ${{ secrets.SAAS_DEV_URL }}
  SAAS_DEV_API_KEY: ${{ secrets.SAAS_DEV_API_KEY }}

steps:
  - name: Run E2E tests
    run: pytest tests/e2e/ -v
```

**Note**: E2E tests are optional in CI. If secrets not set, tests will skip gracefully.
