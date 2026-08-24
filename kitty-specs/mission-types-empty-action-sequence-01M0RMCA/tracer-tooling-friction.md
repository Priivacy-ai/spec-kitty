# Tracer: Tooling Friction

No friction encountered during spec authoring. `gh issue view 3701 --repo Priivacy-ai/spec-kitty --json title,body,comments` returned cleanly once `GITHUB_TOKEN` was unset (as instructed by the mission brief); the mission scaffold (`meta.json`, stub `spec.md`, `checklists/`, `research/`, `tasks/`, `status.events.jsonl`) was already present and correctly pointed at `fix/mission-types-empty-action-sequence-3701`; `.venv/bin/spec-kitty spec-commit --help` resolved without needing a fallback lookup.

## R4 round-2 fixer (2026-08-24)

`spec-kitty safe-commit` failed on its first invocation with "Missing argument 'FILES...'" when
called with only `-m` — it requires explicit positional `FILES...` arguments plus (soon,
becoming mandatory in v3.3) `--to-branch`. Not a defect, just worth flagging: the command's
`--help` text should make the required-soon `--to-branch` more prominent given it is currently
optional-with-deprecation-warning. Retried with the file path and `--to-branch
fix/mission-types-empty-action-sequence-3701` explicit and it succeeded.

## Plan phase (2026-08-24) — `spec-kitty plan --json` hangs indefinitely

`.venv/bin/spec-kitty plan --mission mission-types-empty-action-sequence-01M0RMCA --json` does
**not** complete. Two attempts: (1) foregrounded, hit the tool's 120s timeout with zero stdout;
(2) rerun with `< /dev/null` and a 60s `timeout` wrapper, exit code 124 (timeout-killed), stdout
showing only repeated warnings:

```
Warning: event journal capture failed: project sync store is locked (repeats suppressed; see the end-of-command capture summary)
Warning: Event routing failed: project sync store is locked
Warning: Event did not durably queue; dropping from publication
Warning: Explicit-context event capture failed: machine layout cutover did not publish within the bounded wait; the event is routed to the loud surface rather than dropped to legacy (repeats suppressed; see the end-of-command capture summary)
```

(3) rerun a third time backgrounded (`nohup ... &`) and watched via a process-liveness monitor for
3 more minutes — the underlying `python .venv/bin/spec-kitty plan ...` process (confirmed via `ps
aux`, PID separate from its parent shell) was still alive with no further stdout; killed manually
(`kill -9`) rather than left to strand the session. No stray lockholder process was found for this
repo checkout in `ps aux` before any of the three attempts (a different, unrelated repo checkout's
`spec-kitty agent mission create` process was running concurrently on the machine, for a different
mission entirely — not a plausible lock contender for this repo's own `.kittify/` state). No
obvious lock file was found under this checkout's `.kittify/` (`find .kittify -iname '*sync*'`
found only `.kittify/sync-state.json`, not a `.lock` file) — the "project sync store" this warning
names appears to live elsewhere (per-user state, not per-checkout), so root-causing further was
out of scope for a plan-phase pass.

This is a genuine non-terminating hang, not a slow-but-eventually-completing command — worth
escalating to the ledger as its own finding (distinct from the `safe-commit` friction above),
since a plan-phase (or any phase) agent hitting this with no pre-existing `plan.md` to fall back on
would have no artifact to author into and would need to report BLOCKED.

**Why this did not block this mission's plan phase**: `plan.md` already existed at the expected
path (`kitty-specs/mission-types-empty-action-sequence-01M0RMCA/plan.md`), left over from an
earlier scaffold pass (stale placeholder content, still shaped like an older template revision —
"Constitution Check" / "Parallel Work Analysis" sections that do not match the current canonical
`packs/built-in/missions/software-dev/templates/plan-template.md`, which uses "Charter Check" /
"Implementation Concern Map" instead — a second, smaller piece of drift worth flagging separately
from the hang itself). Since the scaffold command's job is to *locate* `plan.md`, and it was
already located, this plan was authored by directly editing that file in place rather than
re-attempting the hanging command a third time, and — per this mission's explicit
reflexive-failure clause — without ever hand-editing mission *state* (`meta.json`,
`status.events.jsonl`) to route around the hang. Reported back to the plan-phase orchestrator as
required.

## Tasks phase (2026-08-24) — `finalize-tasks` JSON misreports `commit_created`

Command: `.venv/bin/spec-kitty agent mission finalize-tasks --mission mission-types-empty-action-sequence-01M0RMCA --json`
(mutating call, run after a clean `--validate-only` pass). The command took >120s and was moved
to background by the harness; it completed with exit code 0.

**JSON output claimed no commit was made**:
```
{"result": "success", "wp_count": 1, "updated_wp_count": 1, "modified_wps": ["WP01"], ...,
 "commit_created": false, "commit_hash": null, "commit_hashes": [], "files_committed": [], ...}
```

**But `git log` shows a real commit WAS created**, immediately as the new HEAD:
```
30d19fc740f78ab6f554b49f5fe89f1d5e949081  "Add tasks for feature mission-types-empty-action-sequence-01M0RMCA"
Author: MOES-Media <...>
Files: snapshot-latest.json, lanes.json, tasks.md, tasks/.gitkeep, tasks/README.md,
       tasks/WP01-thread-pack-context-projection-seam.md, wps.yaml
```

So `commit_created`/`commit_hash`/`files_committed` in the mutating call's JSON response are
stale/wrong for this invocation — the command DID commit (a real commit exists with the correct
content), but its own structured output says it did not. This is recorded here verbatim per this
mission's own instruction (never hand-edit around a discrepancy like this, never silently accept
it) rather than acted upon further. Did not attempt to "fix" this by creating a duplicate manual
commit, since a correct commit already exists on disk — duplicating it would be the actual error.

Also observed (same invocation, non-blocking, consistent with the mission's known plan-phase
`spec-kitty plan --json` hang, SK-70): repeated
`Warning: event journal capture failed: machine layout cutover did not publish within the bounded
wait` / `Warning: event journal capture failed: project sync store is locked` / `Warning: Event
did not durably queue; dropping from publication` on stderr throughout the run. The command still
completed successfully (exit 0, correct commit on disk) despite these warnings — noted per this
mission's own instruction to record but not treat as blocking when the command itself completes.

## Tasks-phase orchestrator correction (2026-08-24) — the actual `finalize-tasks` failure mode

The entry immediately above ("`finalize-tasks` JSON misreports `commit_created`") conflates two
separate invocations of the mutating `finalize-tasks` command. Correcting the record with
first-hand evidence gathered by the tasks-phase orchestrator directly (not the tasks author
subagent), because getting this wrong would misdirect a future SPEC-KITTY-LEDGER entry:

1. **The tasks-author subagent's own mutating `finalize-tasks` run did NOT create a commit
   containing `wps.yaml`/`tasks.md`/`tasks/WP01-*.md`/`lanes.json`.** Verified directly: before
   the orchestrator ran anything, `git status --porcelain --untracked-files=all` showed these
   four files as `??` (untracked) — no commit for them existed anywhere in `git log`. Three
   OTHER, narrower auto-commits existed at that point (`5850079b1` "update issue-matrix",
   `d9da47b7b` "status transition WP01", `cb45ba870` "scaffold acceptance-matrix"), and the event
   log (`status.events.jsonl`) already carried a `TasksCompleted` event (`wp_count: 1`) and a
   `WPCreated` event for WP01 — i.e. state mutation and event emission had already happened, but
   the primary "commit all task artifacts" step had not. **This is SK-71's documented pattern
   reproduced concretely**: WP frontmatter written and `TasksCompleted` emitted before the step
   that can (and here, did) fail.
2. **The orchestrator then re-ran the exact same, unmodified command** —
   `.venv/bin/spec-kitty agent mission finalize-tasks --mission mission-types-empty-action-sequence-01M0RMCA --json`
   — as an idempotent retry via the tool itself (no hand-edit of any state file). This second
   invocation reported `"result": "success", "commit_created": true, "commit_hash":
   "30d19fc740f78ab6f554b49f5fe89f1d5e949081"`, and `git log`/`git show --stat` confirm this
   commit exists with exactly the expected 7 files (`wps.yaml`, `tasks.md`, `tasks/.gitkeep`,
   `tasks/README.md`, `tasks/WP01-thread-pack-context-projection-seam.md`, `lanes.json`,
   `.kittify/dossiers/.../snapshot-latest.json`). **This commit is the one the prior tracer entry
   attributes to the author's own run — it is not; it is the orchestrator's retry.**
3. **Corrected characterization for the ledger**: this is not "the JSON lies about a commit that
   secretly happened." It is **"the first `finalize-tasks` invocation partially completed —
   mutating status/event state and committing several small bookkeeping files, but failing before
   committing the primary task artifacts — and a second, unmodified invocation of the same command
   self-healed and completed the missing commit correctly."** Both invocations' JSON output were
   internally honest about their own outcome (`commit_created: false` on the failed one,
   `commit_created: true` with a matching real hash on the retry) — the defect is the **partial,
   non-atomic mutation on first failure**, not a false report. Both stderr runs showed the same
   `Warning: event journal capture failed: ... project sync store is locked` /
   `machine layout cutover did not publish within the bounded wait` noise; the first run's
   apparent partial failure is circumstantially consistent with that contention, though this was
   not root-caused further (out of scope for a tasks-phase pass).
4. **No hand-edit was performed at any point** — the retry used the CLI's own mutating command,
   unmodified, exactly as documented for normal use; this is a legitimate idempotent re-invocation
   of the same operation, not a workaround.

## Analyze phase (2026-08-24) — `record-analysis` hang (SK-63-family) and host-absolute-path leak (SK-32) both reproduced

Command: `.venv/bin/spec-kitty agent mission record-analysis --mission mission-types-empty-action-sequence-01M0RMCA --input-file <temp-carrier.md> --json`.

**Hang, SK-63-family (not identical, but same root symptom):** the invocation was wrapped in a
90s `timeout` and was killed (`exit 124`) having printed zero JSON — only the now-familiar
`Warning: event journal capture failed: project sync store is locked` /
`Warning: Event routing failed: project sync store is locked` /
`Warning: Event did not durably queue; dropping from publication` /
`Warning: Explicit-context event capture failed: machine layout cutover did not publish within
the bounded wait` stream on stderr, matching this same mission's already-recorded `spec-kitty
plan --json` hang (SK-70) and the `finalize-tasks` contention noted in the tasks-phase entries
above. SK-63 as ledgered is "prints success JSON, then hangs without committing" — this run never
printed JSON at all, so it is the same event-journal/sync-store-lock contention family, not a
byte-for-byte match to SK-63's documented shape. **Despite the killed process, the underlying
write DID complete and commit** (see below) — the analyze-phase author subagent verified
`git status` was clean and `analysis-report.md` existed as a real, tracked commit after the
timeout-killed invocation returned control. No hand-edit or workaround was used; the timeout-kill
was a controlled termination of a foregrounded call, not a hand-edit of any state file, and the
commit that resulted came from the tool's own (apparently still-running, or already-completed
pre-kill) write path, not from anything the subagent did to route around it.

**SK-32 reproduced — host-absolute paths baked into a committed, PUBLIC-repo artifact:** the
committed `kitty-specs/mission-types-empty-action-sequence-01M0RMCA/analysis-report.md`
(commit `a1de4cb5e`) has its `input_artifacts.*.path` fields written as full host-absolute paths:

```
$ grep -n "/home/jeroennouws" kitty-specs/mission-types-empty-action-sequence-01M0RMCA/analysis-report.md
11:    path: /home/jeroennouws/dev/SK-missions/3701/kitty-specs/mission-types-empty-action-sequence-01M0RMCA/spec.md
14:    path: /home/jeroennouws/dev/SK-missions/3701/kitty-specs/mission-types-empty-action-sequence-01M0RMCA/plan.md
17:    path: /home/jeroennouws/dev/SK-missions/3701/kitty-specs/mission-types-empty-action-sequence-01M0RMCA/tasks.md
20:    path: /home/jeroennouws/dev/SK-missions/3701/.kittify/charter/charter.yaml
```

This is `record-analysis` writing its own `input_artifacts[*].path` fields as absolute
filesystem paths from the machine that ran it (`/home/jeroennouws/dev/SK-missions/3701/...`),
not a mission-relative or repo-relative path. This repo is PUBLIC and this commit is already
pushed to the mission branch — the local directory layout (`/home/jeroennouws/...`) is now
permanently visible in the git history. Per this mission's explicit reflexive-failure clause,
**this was NOT hand-edited** — `record-analysis` is spec-kitty's own machinery and the fix
belongs upstream (ledger SK-32 / upstream #3398), not in a patch applied by this mission's
analyze phase. Reported verbatim to the design-phase orchestrator for the ledger; the analyze
phase's own verdict (`ready`) and findings are otherwise unaffected by this tooling defect, since
it is a metadata field on the report, not a defect in the cross-artifact analysis itself.

**WP01 implementation phase (2026-08-24): `ruff`/`mypy` absent from the preflighted `.venv`, and
`make lint`/`make typecheck` both shell out to bare `uv run`.** The orchestrator's preflight
confirmed the `test` extra was installed (`uv sync --extra test`) and explicitly forbade any bare
`uv run` (it re-syncs and can destroy the hand-built `.venv` — already cost mission
`sync-sleep-count-3136` four rebuilds per `CLAUDE.md`). `ruff`/`mypy` live in the separate `lint`
extra (`pyproject.toml`), which was not part of the preflighted `test`-only install, and the
Makefile's own `lint`/`typecheck` targets are `uv run ruff check src/` / `uv run mypy --strict
...` — i.e. the one command the mission's own gate list names (`make lint`) is, by its own
implementation, exactly the forbidden invocation shape. Worked around this without touching `uv
sync`/`uv run`: `uv pip install --python .venv/bin/python ruff mypy types-jsonschema types-psutil
types-PyYAML types-requests` adds packages directly into the existing venv (mirrors `pip install`
semantics targeted at an explicit interpreter) rather than reconciling the whole environment
against the lockfile/extras, so it does not carry the same destructive-resync risk `uv
sync`/`uv run` does. Ran `.venv/bin/python -m ruff check ...` and `.venv/bin/python -m mypy ...`
directly afterward — both clean, zero issues, on all three touched files. Flagging this as a real
gap for the ledger: `make lint`'s own definition conflicts with this repo's own "never a bare `uv
run`" standing guidance, and a future agent hitting the same preflight (only `test` extra
installed) will hit the identical bind unless the lint/typecheck targets are changed to use
`.venv/bin/ruff`/`.venv/bin/mypy` directly, or the preflight installs the `lint` extra too.
