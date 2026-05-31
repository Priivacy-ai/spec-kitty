# Paula Patterns Synthesis Matrix

The parent LLM synthesizes scout findings. Do not concatenate scout reports.

| Finding | Layered | DDD | EDA | Hexagonal | Contract | Evidence | Release action | Long-term action |
|---|---|---|---|---|---|---|---|---|
|  |  |  |  |  |  |  |  |  |

For each row, decide:

- Shared root cause across lenses.
- Concrete release blocker, if any.
- Smallest safe release fix.
- Deferred architecture issue.
- Tests required before merge.

## Decision Split

Release fix:

- Minimal change that closes the currently observed failure.
- Compatible with existing machine-output contracts unless a breaking change is
  explicitly approved.
- Covered by the smallest release-safe tests.

Long-term architecture fix:

- Boundary, ownership, contract, or state-model repair that deserves its own
  issue or mission.
- Includes non-goals so the follow-up does not absorb the release fix.
- Names the doctrine tactic, directive, or pattern that should govern the work
  when one applies.

## Example: #1343 / #1359 uv-tool Remediation

| Finding | Layered | DDD | EDA | Hexagonal | Contract | Evidence | Release action | Long-term action |
|---|---|---|---|---|---|---|---|---|
| uv-tool remediation kept missing install variants | Review command parsed uv receipts and rendered installer commands | `InstallMethod.UV_TOOL` hid runtime/provenance distinctions | Heuristic detection became mutation authority without verified state | Shell strings stood in for structured argv/env/platform/provenance | One JSON shell string created POSIX/Windows and machine-output risk | #1343 / #1359 review findings | Patch known uv-tool receipt/provenance cases; keep JSON stable | File #1358 for shared `InstalledCliRuntime` and structured remediation planning |
