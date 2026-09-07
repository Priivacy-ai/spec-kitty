# Contract: acceptance evidence

Every row is red-first on the merge-base through the named entry point and green at head. Blast radius per CLAUDE.md §Test policy plus `tests/architectural/` in full (cross-cutting env/config change).

| ID | Scenario | Entry point | Evidence |
|---|---|---|---|
| A1 | fresh install, no config, no session, interactive `status` | public `spec-kitty` subprocess, isolated `SPEC_KITTY_HOME`, pty | completes; one hint on stderr; second run: no hint; JSON run: no hint |
| A2 | `auth login` with nothing configured | subprocess against a recording stub OAuth server | request lands on the packaged default host; target line printed with `packaged default` |
| A3 | target matrix (contracts/target-resolution.md) | `resolve_server_target` unit + `auth status` subprocess | every cell resolves and prints the expected source; split-brain still fails closed |
| A4 | owned checkout lane move | real repo + `--owned-checkout` + recording relay stub | exactly one `event.publish`; attrs identical to worktree case |
| A5 | unauthenticated full cycle | recording stub for SaaS + relay | 0 requests across specify → review incl. readiness |
| A6 | `auth logout` then lane move | same stub | 0 requests after logout; hint marker reset |
| A7 | tracker command / `--from-ticket` logged out | subprocess | exit non-zero with sign-in guidance; no "not enabled" text anywhere in the tree |
| A8 | retired names present in env and config | subprocess | no effect; `[sync]` table ignored |
| A9 | opt-outs | unit | pre-review gate skipped only by its own name; handler registration suppressed only by its own name |
| A10 | vocabulary | `git grep` over live src/docs/templates | zero occurrences of retired identifiers outside the occurrence-map exceptions |
| A11 | gates | `tests/architectural/` full | at or below baselines; terminology guard green |
