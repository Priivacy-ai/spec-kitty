# Domain Model

Audience: agentic-framework-core-team. Updated: 2026-09-06.

| Concept | Meaning | Authority / Invariant |
| --- | --- | --- |
| Upgrade intent | Preview/apply, project/CLI, target and worktree selection | One interpretation before startup writes |
| Compatibility verdict | Installed/project schema and invocation compatibility | Existing compat planner; not a write manifest |
| Target validity | Current-to-requested version policy | Existing version validator, not lexical ordering |
| Repair assessment | Ordered owner-produced intended operations and conflicts | Existing provider/installer authority; no duplicate path catalog |
| Physical effect | Scope, path, operation, reason, ownership and preconditions | Deduplicate shared paths without dropping owners |
| Managed surface | Runtime/command/skill/profile/config/manifest | Exact ownership proof; unknown customizations preserved |
| Mission identity | Historical immutable ID and creation context | Recover original evidence, never generate replacement for known mission |
| Event history | Authoritative transitions, annotations and review evidence | Byte-preserve in scoped snapshot repair |
| Snapshot | Materialized mission/WP state | Canonical replay, with review/provenance preserved |

Assessment precedes mutation. Human and JSON are projections of assessment;
neither renderer invents policy. Application rechecks ownership/preconditions.
Mission-state repair is a separate consent boundary, not a repair-plan side effect.
