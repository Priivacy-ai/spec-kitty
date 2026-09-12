# Contract: moment publishing under launch defaults

Unchanged wire behavior (`docs/context/team-kitty.md`), restated as the acceptance contract:

1. Every lane transition and lifecycle beat calls `fire_saas_fanout` / `fire_lifecycle_saas_fanout`, from lane worktrees and owned checkouts alike. `OWNED_SYNC_UNSUPPORTED` no longer exists.
2. With `AuthenticationState = unauthenticated`, credential resolution returns `None` before any request; a recording stub observes 0 requests across specify → plan → tasks → implement → review, including readiness.
3. With a resolvable capability, exactly one `POST <relay>/managed/control` (`op: event.publish`) per transition, 750 ms budget, no retry; failures are logged at debug and never surface to the user.
4. An owned-checkout transition produces a moment byte-identical in `kind`, `ref`, and `attrs` to the same transition from a lane worktree (only `session_id` differs).
5. `SPEC_KITTY_NO_MOMENT_HANDLERS=1` registers no handlers at import; it is the only way to suppress the fan-out for an authenticated process and is documented as a test/isolation switch, not an operator feature.
