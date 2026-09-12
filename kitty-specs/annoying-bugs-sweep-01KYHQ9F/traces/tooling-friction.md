# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

---

## Entries

### 2026-07-27

`spec-kitty next --mission annoying-bugs-sweep-01KYHQ9F` reported `not_started` even though the
mission event log contained `SpecifyCompleted` and `PlanStarted`. The actionable blocker came from
`spec-kitty agent mission setup-plan`, which correctly identified the placeholder `plan.md`.

The documented `spec-kitty agent tasks status --feature` and
`agent mission branch-context --mission` flags are removed in this installed CLI; the current
surfaces use `--mission` for task status and `setup-plan --mission` for branch context.

