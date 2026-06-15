# spec-kitty standalone invocation

This host should read Spec Kitty's canonical standalone-invocation skill pack at:

**`src/doctrine/skills/spec-kitty/SKILL.md`**

That file teaches:
- When to call `spec-kitty dispatch "<request>"` for standalone governed work.
- How to read `governance_context_text` from the response and inject it as binding governance context.
- That `spec-kitty dispatch` only OPENS the Op — after doing the work, the agent
  MUST close it with the real outcome:
  `spec-kitty profile-invocation complete --invocation-id <id> --outcome <done|failed|abandoned>`.
  Failed work closes as `failed`; `spec-kitty doctor ops` reports and sweeps orphans.

This command is available alongside the `/spec-kitty.*` mission-step commands in this directory. Use them for standalone invocations that are not part of a running mission workflow.

For the shipped trail contract and SaaS read-model policy, see [`docs/trail-model.md`](../../docs/trail-model.md).
