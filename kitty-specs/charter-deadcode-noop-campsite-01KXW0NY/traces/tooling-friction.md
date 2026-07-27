# Tooling Friction Log

> Log every place the tooling fought you so it can feed the tooling-gap backlog.

**Prompting questions**
- What tooling or command did you have to work around?
- What blocked you unexpectedly, and how long did it take to unblock?
- Was this a known issue or something discovered fresh?

**Mission tooling touched:** `spec-kitty agent mission {branch-context,create}`, `charter context`,
`spec-kitty agent decision {open,resolve,verify}`, `spec-kitty spec-commit`, arch dead-code gates
(`test_no_dead_modules`/`test_no_dead_symbols`/`test_ratchet_baselines`), the preflight →
`charter synthesize` no-op path (the subject under test).

---

## Entries

<!-- YYYY-MM-DD — 1-3 sentences: what happened, why it slowed you down. -->

- 2026-07-19 — **Decision Moment Protocol assumes a mission already exists.** The genuine open
  question (item-3 bundle-vs-split) had to be asked *before* `mission create` (no slug to mint a
  `decision_id` against), so the resolved decision was recorded post-hoc via `decision open`+`resolve`
  after create rather than pre-question as the protocol prescribes. Fresh friction, low cost, but the
  specify protocol and the "genuine questions can precede the mission" reality are misaligned.

- 2026-07-19 — **`branch-context`/`create` echo `merge_target_branch = <current feature branch>`
  pre-mission**, not `main`. Harmless once you know it, but it is exactly the `primary`/`merge`
  footgun the charter warns about — a naive read would think the PR targets the feature branch. The
  real contract (PR → `main`, operator merges) had to be asserted from doctrine, not the helper JSON.

- 2026-07-19 — **Checkout masks the #2373 reproduction.** A *local, uncommitted*
  `.git/info/exclude` entry (`.kittify/doctrine/`) hides the doctrine churn this mission must fix,
  while the committed `.gitignore` tracks those artifacts. `git status` clean here is a false
  negative — a real environment footgun that would silently defeat red-first repro. Pinned as a
  spec landmine (FR-007) so implementation reproduces in a doctrine-tracked checkout.

- 2026-07-19 — **Smoothed (positive):** `spec-commit` on a `coord`-topology mission from an
  unprotected feature branch committed `spec.md` directly with no deadlock and no coord-worktree
  dance — the recent implement-loop/commit-hardening work (#2570/#2662 lineage) appears to have paid
  off here. Noted so the assess step can confirm the friction is genuinely retired, not just masked.

- 2026-07-19 — **Post-`spec-commit` residual untracked state** (`decisions/`, `status.events.jsonl`,
  `tasks/`, modified `meta.json`) leaves `git status` non-clean after a "clean" spec commit. Expected
  (coord/primary partition routes lifecycle artifacts separately), but a fresh agent could misread it
  as a dirty tree or a failed commit. Minor orientation friction.

- 2026-07-19 — **Verified vs stale memory:** the "finalize-tasks clobbers issue-matrix" caution in
  local memory was stale — `scaffold_issue_matrix` has guarded existence since #1312 (`3bd688758`).
  Confirmed empirically: issue-matrix md5 identical before/after `finalize-tasks`. Also: this
  idempotency is NOT in the 3.2.6 changelog (predates the cycle) despite being a real user-facing
  friction-reducer — a documentation gap worth surfacing.
