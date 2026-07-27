# Contract: Fresh Workflow Smoke

## Local-Only Smoke

Must cover:

- init or project setup
- specify
- plan
- tasks
- implement/review or a bounded equivalent fixture path
- merge
- PR creation or PR-ready branch evidence

Rules:

- Must not require hosted auth, tracker, SaaS, or sync.
- Must run against the current prerelease line from this repository.
- Must record command sequence and outcome in release evidence.

## SaaS-Enabled Smoke

Must cover the same lifecycle shape where practical, with hosted/sync coverage added where current CLI surfaces support it.

Rules for this computer:

- Every hosted auth, tracker, SaaS, or sync command path must set `SPEC_KITTY_ENABLE_SAAS_SYNC=1`.
- Evidence must state which commands used the flag.
- If auth or hosted state blocks the smoke, record the blocker and either file/reference an issue or mark it as a stable-release blocker.

## Failure Handling

Each smoke failure must lead to one of:

- narrow fix inside this mission
- linked GitHub issue with repro
- explicit stable `3.2.0` blocker decision

## Evidence Format

Recommended fields:

```json
{
  "mode": "local-only",
  "commands": ["..."],
  "result": "pass",
  "evidence": "path or issue link",
  "notes": "bounded fixture path used for implement/review"
}
```
