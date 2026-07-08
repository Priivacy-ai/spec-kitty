# Tracer: tooling friction

Append friction encountered during the mission; assess at close (feeds the next mission's tooling-gap backlog / #2095).

> **Note:** these tracer files were seeded LATE (at implement start, 2026-07-08), not at planning.
> The planning surfaces (`/specify`, `/plan`, `/tasks`) do not prompt or enforce the
> `mission-tracer-files` procedure — a process gap worth surfacing on its own.

- **[implement] TOOLING MISS — no model-discipline default/guidance in the dispatch surface.**
  Neither `spec-kitty agent action implement` nor the `spec-kitty-implement-review` skill
  provides a default or nudge for implementer-vs-reviewer model routing, so the orchestrator
  defaulted implementer subagents to **opus** (the expensive tier) instead of the disciplined
  **sonnet-implement / opus-review** split. Required manual operator correction (twice). The
  `--agent <tool>:<model>:...` string is cosmetic — it does not gate the actual dispatched
  subagent model, so nothing enforces alignment. **Recommendation:** default the implementer
  model to a cheaper tier (or surface the recommended routing in the claim output / skill),
  and/or validate that the dispatched model matches the `--agent` identity. Operator flagged
  this explicitly.
- **[implement] Claim did not generate the WP06 prompt file** on first `agent action implement`
  (silent — no prompt written to `/tmp/spec-kitty-prompts/<hash>/`), yet the WP moved to
  `in_progress` and took the lease. Re-claim was then blocked by the existing lease
  (`already claimed by ...`), forcing a `move-task --to planned --force` + re-claim to recover.
  Prompt generation should be atomic with the claim (or fail loudly if it can't write the prompt).
- **[implement] Re-claiming an `in_progress` WP with a different `--agent` identity is a silent
  no-op resume** — it does NOT update the recorded identity. To change the recorded model
  identity you must reset the WP to `planned` and re-claim. Non-obvious.
