---
cycle_number: 1
verdict: rejected
wp_id: WP04
mission_slug: docs-ia-onboarding-overhaul-01KY02JB
---

**Issue 1** (factual accuracy in `docs/context/ops-vs-missions.md`, "Decision rule" section, last
paragraph): the claim "a mission action never opens a `kitty-ops/*.jsonl` Op record" is
overbroad and contradicted by the actual code. `spec-kitty next` (via
`src/specify_cli/cli/commands/next_cmd.py::_write_issuance_lifecycle_record`) calls
`specify_cli.invocation.lifecycle.write_started`, which appends a `ProfileInvocationRecord` to
`kitty-ops/lifecycle.jsonl` (see `LIFECYCLE_LOG_RELATIVE_PATH = Path("kitty-ops") /
"lifecycle.jsonl"` in `src/specify_cli/invocation/lifecycle.py`). That file matches the literal
glob `kitty-ops/*.jsonl` written in the doc, so a reader who runs `spec-kitty next` and then
`ls kitty-ops/` will find a `.jsonl` file there — directly contradicting the doc's "never opens"
claim as worded.

The narrower point the page is trying to make is still correct and worth keeping: `next` does
NOT create a standalone *per-invocation* Op record (no `OpStartedEvent`/`OpCompletedEvent` pair,
no new `kitty-ops/<invocation_id>.jsonl` file, no `ops-index.jsonl` entry) — those are the
`writer.py`/`executor.py` primitives that only `dispatch` uses. `next` instead appends
`started`/`completed` pairs of a *different* record type (`ProfileInvocationRecord`) to one
shared, append-only `kitty-ops/lifecycle.jsonl` log.

**Fix**: reword the last sentence of that paragraph to state precisely what does and doesn't
happen, e.g.: "...but a mission action never opens a standalone per-invocation
`kitty-ops/<invocation_id>.jsonl` Op record (the `dispatch`-only mechanism in
`src/specify_cli/invocation/writer.py`/`executor.py`). Instead, `spec-kitty next` appends
paired `started`/`completed` lifecycle records — a different schema
(`ProfileInvocationRecord`) — to one shared `kitty-ops/lifecycle.jsonl` log
(`src/specify_cli/invocation/lifecycle.py`)." Ground the correction in those two files as cited
here.

This is the only accuracy problem found. Everything else in this WP checks out:
- `docs/context/mission-types.md` accurately reflects all 4 `mission.yaml` files (purposes,
  phases, artifacts, gates) — spot-checked against `src/specify_cli/missions/{software-dev,
  research,documentation,plan}/mission.yaml` line by line.
- The rest of `ops-vs-missions.md`'s claims about `dispatch` (Op record path
  `kitty-ops/<invocation_id>.jsonl`, `ActionRouter` routing, synchronous no-LLM-call behavior,
  `profile-invocation complete` closing via `ProfileInvocationExecutor.complete_invocation()`,
  `doctor ops` sweep) verified accurate against `dispatch.py`, `executor.py`, and `writer.py`.
  The "same governed-context model" claim also checks out — `src/runtime/next/prompt_builder.py`
  calls the same `build_charter_context()` used by the invocation executor.
- Both pages carry valid `type: explanation` frontmatter and are cross-linked to each other.
- `scripts/docs/relative_link_fixer.py --check` passes (0 dead bare-relative body links).
- WP04's own commit (`0345455d7`) touches only its two owned files
  (`docs/context/ops-vs-missions.md`, `docs/context/mission-types.md`) — no scope creep.
- The `toc.yml`/`context/index.md` linking gap is correctly flagged in the Activity Log per the
  WP prompt's own DoD wording (toc.yml already reserves a Core Concepts slot; WP04 correctly did
  not edit `toc.yml` or `context/index.md`, both outside its `owned_files`). Note for mission
  tracking: no WP currently appears to own updating `context/index.md`'s body to actually link
  these two new pages (WP10's scope is terminology sweep + Divio coverage + follow-up issue, not
  nav wiring) — worth flagging at the mission level so FR-004/FR-005's "linked from a
  core-concepts index" acceptance criterion doesn't fall through the cracks, but this is not a
  WP04-owned fix.

Please fix Issue 1's sentence in `docs/context/ops-vs-missions.md` and resubmit.
