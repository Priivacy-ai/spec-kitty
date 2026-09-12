# Residual ledger — Mission `sync-sleep-count-3136-01KZ9B5A`

Items found during implementation that are **out of the finding WP's scope** and cannot be folded into
it. Operator direction bars `gh issue create`, so nothing here has been filed; each entry carries its
evidence and the reason it could not be folded.

Append-only. Each entry names the WP that found it.

## ID allocation — read this before appending (added 2026-08-07 by the orchestrator)

**The authoritative copy of this ledger is on `feat/sync-sleep-count-3136`.** That is the mission target
branch. The copies on the **coord** branch/worktree and on the lane branches are **stale** — coord
still stands at `RL-016`. Do not read them to pick an ID, and do not append to them; port your entry
to `feat/` instead, as WP04 did. (`move-task` refuses `kitty-specs/` changes on lane branches, so
porting is the sanctioned route, not a workaround.)

### Correction (2026-08-07, WP07 cycle 2) — this header's second clause had gone false

As originally written this paragraph also said `feat/` was *"the copy that travels to the PR"*. **Once
PR #3252 existed, both halves of that sentence stopped being simultaneously true**, and the drift is
exactly what this header was written to prevent:

- The PR is a **`pr/sync-sleep-count-3136`** branch composed from the lanes, **not** `feat/` — see
  `RL-045`. So `feat/` is not the copy that travels.
- Fixes landed **directly on the PR branch** (`bf68b101b`, `RL-048`'s RESOLVED addendum plus the
  `C-002` re-assessment), putting the PR copy **64 lines ahead** of `feat/` while the header still
  named `feat/` authoritative. No ID collision resulted — the harm was latent, not realised — because
  the block allocator held: `RL-040`…`RL-049` were already fully taken, so the ahead-copy minted no
  new id.

**The rule, restated so both clauses are true at once:**

| Question | Answer |
|---|---|
| Which copy is authoritative for **picking an ID**? | **`feat/sync-sleep-count-3136`** — unchanged |
| Which copy **travels to the operator**? | **`pr/sync-sleep-count-3136`** (PR #3252) |
| What keeps them from diverging? | Any entry written on the PR branch **must be ported back to `feat/`** in the same pass. This correction ports `bf68b101b`'s addendum back; the two copies are byte-identical as of this commit |

Verify they have not drifted again:

```bash
diff <(git show feat/sync-sleep-count-3136:kitty-specs/sync-sleep-count-3136-01KZ9B5A/residual-ledger.md) \
     <(git show pr/sync-sleep-count-3136:kitty-specs/sync-sleep-count-3136-01KZ9B5A/residual-ledger.md)
```

**After consolidation this distinction disappears** — `spec-kitty merge` folds the lanes into `feat/`,
at which point `feat/` is both. Until then, two copies exist and both facts above must be stated.

**Do not append the next sequential number.** Several lanes append to this one file from separate
worktrees, and a lane that has not rebased **cannot see which IDs are already taken** — it reads the
max on *its own* commit. That is not hypothetical, and it has now happened twice: WP03 and WP04 both
minted `RL-019` concurrently, and then the orchestrator's own allocator commit collided with WP04 on
three more IDs (see below). There is no allocator in the tooling, so one is imposed here.

**Take your ID from your own reserved block, never from the running maximum:**

| Block | Owner | Notes |
|---|---|---|
| `RL-001` … `RL-022` | **allocated** (WP01–WP03, coord) | Complete and gapless **on coord**. See the duplicate warning below — this range is *not* collision-free against lane-d. Do not reuse. |
| `RL-023` … `RL-029` | WP03 / WP06 remediation | Both are in review; remediation entries land here. |
| `RL-030` … `RL-039` | **WP05** | |
| `RL-040` … `RL-049` | **WP07** | Includes T042's filings, which are ledger entries — **not** GitHub issues (see below). |
| `RL-050` … `RL-059` | **WP04** | Opened 2026-08-07 to resolve the collision below. WP04's three lane-d entries renumber into here. |

### The `RL-017` / `RL-018` / `RL-020` collision — RESOLVED 2026-08-07

**Status: resolved.** `feat/sync-sleep-count-3136` now carries 25 entries with **zero** duplicate IDs
(`grep -oE '^## RL-[0-9]+' | sort | uniq -d` → empty). Kept on the record because the *cause* is the
mission's own subject.

For a period, three IDs existed twice with different content — WP04's in its lane, and the
orchestrator's on the mission branch:

| ID | WP04's entry | the colliding entry |
|---|---|---|
| `RL-017` | `check_docs_freshness.py`'s remediation hint instructs a bare `uv run` | lane worktrees carry the destructive bare `uv run` |
| `RL-018` | the prompt names two generated indexes; there are three | a trailing bare word `patch` mints a phantom target |
| `RL-020` | `move-task` misattributes another WP's notes file | `spec-kitty implement WP03` could not allocate the lane unaided |

**WP04 was not at fault, and the record should say so.** Its entries landed 05:11:16–05:15:10, when the
visible maximum was `RL-016` and its choice was correct. The **orchestrator's** allocator commit
`97e490c33` landed at 05:18:44 and minted `RL-017…RL-022` from *its own branch's* maximum — committing
the exact error the commit existed to prevent, then certifying the range *"no duplicates"*, which was
false. WP04's earlier `RL-019 → RL-020` renumber was also rendered moot: WP03 filed that finding as
`RL-021` and something else took `RL-020`.

**Resolution:** WP04 renumbered its three entries into `RL-050`/`RL-051`/`RL-052` against `feat/` and
ported them there. The other entries keep their IDs. Nothing was deleted.

**The lesson, for whoever appends next.** A gapless, duplicate-free range *on your branch* proves
nothing about the composed tree — and the first correction of this defect got the authoritative surface
wrong as well, telling readers to check coord when coord was the stale copy. Take a reserved block and
never look at a maximum at all.

Leave a gap rather than reuse an ID. A gap costs nothing; a collision silently overwrites another
lane's finding when the branches consolidate.

**T042 note:** operator direction (2026-08-06) bars `gh issue create` for this programme. `C-009`
(*file-don't-absorb*) is satisfied by an `RL-###` entry here, not waived — the register changes
address, not existence, and this file travels with the PR in the governance dossier. **Never invent or
reserve a GitHub issue number.**

## Orchestrator ruling — `DIR-013` vs the issue-creation bar (2026-08-07)

**This has been raised independently by three work packages. Settling it here so it stops being
re-litigated per-WP.**

Charter `DIR-013` (*Pre-existing Failure Reporting Rule*) requires pre-existing failures to be filed
as tracker issues. Operator direction (2026-08-06) bars `gh issue create` for this programme:

> *"we are here to deliver features and fix bugs not keep creating residuals, keep issues in a ledger
> we will go over after a mission has been driven to PR then we will assess if anything can be folded
> into an existing mission (if it couldn't be folded in during dev) before creating new issues."*

**Ruling: the operator direction governs, and `DIR-013` is satisfied — not waived — by an `RL-###`
entry.** The charter's own precedence rule is that the operator's standing instruction wins over a
directive's default; and `DIR-013`'s *purpose* is that a pre-existing failure be durably recorded
outside the transcript that found it, so a successor neither re-derives it nor reads it as closed.
This file discharges exactly that, and it travels with the PR in the governance dossier.

**What is required of you** — the bar removes the `gh` call, not the rigour. Every entry must carry
what the issue body would have carried: found-by, severity, the measurement **with its predicate**,
the reason it could not be folded, and a fold-or-file recommendation. An entry that says less than an
issue would have is a real `DIR-013` violation; an entry that says the same in a different register
is not.

**What is barred:** creating the issue, and inventing or reserving an issue number. `gh issue view`
and `gh issue comment` remain permitted. Filing happens after the mission reaches PR, by the
operator's decision, for whatever could not be folded.

Applies to `RL-005`, `RL-015`, `RL-019` and every successor entry.

---

## RL-001 — `spec-kitty agent action implement` is blocked by missing frontmatter on `analysis-report.md`

**Found by**: WP01 · **Severity**: blocks the sanctioned start command for every WP in this mission

The command the orchestrator brief mandates as the first step refuses:

```
$ spec-kitty agent action implement WP01 --agent claude --mission sync-sleep-count-3136-01KZ9B5A
Branch: feat/sync-sleep-count-3136 (target for this mission)
Error: analysis_report_required: /spec-kitty.analyze must be run before implementation.
  Reason: invalid_analysis_report_frontmatter: File has no frontmatter: /home/jeroennouws/dev/sk-missions/3136/kitty-specs/sync-sleep-count-3136-01KZ9B5A/analysis-report.md
  Run: /spec-kitty.analyze --mission sync-sleep-count-3136-01KZ9B5A
```

Cause confirmed — the file opens directly on a heading, with no YAML frontmatter block:

```
$ head -c 40 kitty-specs/sync-sleep-count-3136-01KZ9B5A/analysis-report.md
# Post-spec adversarial squad — findin
```

The file is a hand-written **adversarial-squad** report, not a `/spec-kitty.analyze` output, so it was
never going to carry the frontmatter the implement gate parses. Two artifacts share one filename and
one gate.

**Why WP01 cannot fold it**: `analysis-report.md` is not in WP01's `owned_files` (`.python-version`,
`uv.lock`), and adding frontmatter to satisfy a gate — rather than running the analyze step the gate
is actually asking for — would be forging the gate's input. Re-running `/spec-kitty.analyze` would
overwrite a squad report the mission's WP prompts cite by line number
(`analysis-report.md:481-483`, `:517`), which would break those citations.

**Effect**: every WP in this mission must work from the repository root without a prepared workspace.
WP01 did so, per explicit operator direction.

---

## RL-002 — `98198e980` is described as "the mission's merge-base" and is not

**Found by**: WP01 · **Severity**: terminological; no command's substance is affected

`tasks/WP01-environment-and-window.md` (T003 step 1) states: *"`98198e980` is the mission's merge-base
and resolves"*. Re-derived:

```
$ git merge-base HEAD main
1aed89411b50203c8dbd9b284d70cc8fefbf32fa

$ git merge-base --is-ancestor 98198e980 main ; echo $?
1                                              # 98198e980 is not on main at all

$ git merge-base --is-ancestor 1aed89411 98198e980 ; echo $?
0                                              # it is a descendant of the real merge base

$ git rev-list --count 98198e980..HEAD
32
```

`98198e980` is the mission's **diff base** on `feat/sync-sleep-count-3136`, 32 commits behind `HEAD`.
It **is** an ancestor of `HEAD` (unlike the sibling-mission case the orchestrator brief warns about),
so every `git diff 98198e980` and `git worktree add … 98198e980` in this mission remains valid. Only
the word is wrong.

**Why WP01 cannot fold it**: the same wording recurs across `spec.md`, `plan.md` and several WP
prompts; rewriting mission planning prose is not WP01's surface, and a partial fix would leave the tree
holding two descriptions. Corrected in place for readers at
`notes/environment-3136.md` § *Base-ref correction*.

---

## RL-003 — WP01's Definition-of-Done prescribes a positive twin that cannot exist on one of its own files

**Found by**: WP01 · **Severity**: the check as literally written is unsatisfiable without contrivance

`tasks/WP01-environment-and-window.md:467-480` (DoD item 5) loops over **both** note files and applies
the same twin:

```bash
for NOTES in …/notes/environment-3136.md …/notes/c001-window-3136.md; do
  grep -c 'command -v' "$NOTES"    # twin: must be >= 1
```

`command -v` is a **toolchain-transcript** token. It belongs in `environment-3136.md` (T001) and has no
reason to appear in `c001-window-3136.md`, which is a window handshake built from `ls`, `pgrep`,
`/proc/<pid>/cwd` and `git worktree list`. Measured:

```
# ORIGINAL measurement — taken 2026-08-06, when environment-3136.md stood at ~230 lines.
# STALE: superseded, retained only to show what was measured and when.
$ grep -c 'command -v' …/notes/environment-3136.md
4
$ grep -c 'command -v' …/notes/c001-window-3136.md
0

# RE-MEASURED 2026-08-07 (WP01 remediation), against the committed state of both files:
$ grep -c 'command -v' …/notes/environment-3136.md
7
$ grep -c 'command -v' …/notes/c001-window-3136.md
0
```

**Why the `4` moved to `7`.** Same root cause as the DoD item 5 blocker: the count was taken at one
moment and the file kept growing underneath it. The three added hits are the DoD item 5 block's own
self-description — it reports `grep -c 'command -v'`, which puts the token into the file being
counted. Current hits are at `:9`, `:23`, `:29`, `:70`, plus the three self-referential ones inside
the item 5 section. **Any count in this ledger that greps a mission note is valid only as of its
stated date** — every such figure here is now timestamped for exactly that reason. The `0` on
`c001-window-3136.md` is unchanged and is the load-bearing half; the RL-003 conclusion does not
depend on the `environment-3136.md` figure at all.

The only ways to make the literal check pass are to paste an irrelevant `command -v` line into the
window file, or to fail the WP on a token the file was never meant to carry. Both are worse than
reporting it.

**WP01's resolution**: the *intent* of the twin — prove the file exists and is the right file **before**
believing a `0` from the negative — is honoured, with a token that is genuinely load-bearing for that
file (`PENDING`, which DoD item 2 independently requires). Both counts are reported honestly in the
WP01 handoff, including the `0`.

**Why WP01 cannot fold it**: `tasks/WP01-environment-and-window.md` is the WP's own prompt; an
implementer editing its acceptance criteria to match what it produced is exactly the failure mode the
criteria exist to prevent. **Successor note for WP05 and WP07**, whose prompts carry the same loop
shape (`WP05-mechanism-gate-and-baseline.md:609-617`, `WP07` T037): use a twin token that the specific
file must contain, not a token copied from a sibling file.

### RL-003b — the same class: Reviewer Guidance item 2 fails any document that *warns* about the bare form

`tasks/WP01-environment-and-window.md:510-512` instructs the reviewer to reject on:

> `grep -n 'uv run\|uv sync' kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/*.md` — every hit must
> carry `--python 3.12 --extra test --extra lint`.

A `grep` cannot distinguish a **command** from **prose about a command**. Applied literally the rule
rejects any document that names the bare form in order to warn against it — including the WP prompts
themselves:

```
$ grep -n 'uv run' kitty-specs/sync-sleep-count-3136-01KZ9B5A/tasks/WP01-environment-and-window.md
83:  **NEVER run a bare `uv run` (or a bare `uv sync`) anywhere in this tree.** …
90:  `uv run` in an implementation transcript is a **defect** …
157: … an accidental bare `uv run` downgrades rather than merely …
497: … It is also what makes an accidental bare `uv run` downgrade …
510: 2. **A bare `uv run` or `uv sync` anywhere** in the transcript or the notes:
```

None of those carry the extras; none is a command. The check also **self-inflates**: a note that
records its own `grep -c 'uv run'` result adds the token to the file it is counting.

**WP01's resolution**: the negative is reported as a line-by-line classification (command vs prose vs
meta) rather than a bare count, so a reader can see that the only two **command** occurrences are both
sanctioned Form 2 / provisioning forms with the extras in full. See
`notes/environment-3136.md` § *Definition-of-Done item 5*.

**Suggested criterion shape for a successor**: anchor on a command position rather than a substring —
e.g. reject a line matching `^\s*(\$ )?(PWHEADLESS=\S+ )?uv (run|sync)\b` that does **not** also match
`--extra test`. That distinguishes commands from prose; a bare substring grep cannot.

---

## RL-004 — `CLAUDE.md` instructs the destructive bare `uv run` form

**Found by**: WP01 · **Severity**: repo-wide; this is the exact command that has destroyed this
mission's venv three times

`CLAUDE.md:589`, verbatim:

> This is enforced, not aspirational: the runnable regression guard lives at
> [`tests/ui/test_dashboard_wp_modal.py`](tests/ui/test_dashboard_wp_modal.py)
> (`PWHEADLESS=1 uv run pytest tests/ui/ -q`), runs headless in CI …

`PWHEADLESS=1 uv run pytest tests/ui/ -q` is a **bare** `uv run` — no `--extra test --extra lint`, no
`--python 3.12`. Per `spec.md:433-438` and `plan.md:172-177` this form uninstalls 70 packages
(`pytest`, `ruff`, `mypy` among them) and, because it honours the tracked `.python-version`, recreates
`.venv` at **3.11.15**. Every agent that reads `CLAUDE.md` — which the file's own header instructs
them all to do — is being handed the destructive form as a copy-paste command.

This is a plausible cause of at least one of this mission's three venv destructions: the warning in the
mission's own prompts does not reach an agent that copies from `CLAUDE.md`.

**Why WP01 cannot fold it**: `CLAUDE.md` is a repository-root governance document, not in WP01's
`owned_files`, and it is outside this mission's declared change set (`C-004` restricts the mission's
production edits to `saas_client.py`'s seam). Editing it from an environment WP would be an unowned
repo-wide change.

**Suggested fix when someone owns it**: `PWHEADLESS=1 ./.venv/bin/python -m pytest tests/ui/ -q`
(sanctioned Form 1), or `PWHEADLESS=1 uv run --python 3.12 --extra test --extra lint python -m pytest
tests/ui/ -q` (sanctioned Form 2).

---

## RL-005 — Charter `Pre-existing Failure Reporting Rule` conflicts with the operator's bar on `gh issue create`

**Found by**: WP01 · **Severity**: governance conflict; unresolvable by an implementer

`.kittify/charter/charter.md:397` (surfaced as `DIR-013` by
`spec-kitty charter context --action implement`), verbatim:

> When an agent encounters pre-existing test failures while working in this repository, the agent MUST
> open a GitHub issue reporting them before treating those failures as accepted baseline context or
> continuing past them.

The operator direction governing this mission bars `gh issue create` outright (reading via
`gh issue view` remains permitted). The two cannot both be satisfied the moment a pre-existing failure
appears.

**Status for WP01: LATENT, not live.** WP01's baseline arm on `98198e980` was **fully green** —
`461 passed, 11 deselected, 1 warning in 66.54s`, `EXIT=0`, `^ERROR tests/` = 0. WP01 therefore
encountered **no pre-existing test failures**, so the rule never triggered and nothing was accepted as
baseline red. **No GitHub issue was filed, and none was owed.**

**The conflict remains live for WP02 and WP07**, which run the same cone on the mission head where a
red is possible. This entry exists so that the WP hitting the first pre-existing red does not have to
rediscover the conflict, and knows to escalate rather than either (a) filing against an explicit
operator bar or (b) silently accepting the red. It needs an operator decision — either an explicit
charter exception for this mission, or someone with filing authority opening the issue from the
finding WP's record.

**Why WP01 cannot fold it**: an implementer cannot amend the charter, and cannot override an explicit
operator bar.


## RL-006 — the bare `uv run` hazard is repo-wide, not a single line (2026-08-06)

`RL-004` scoped the destructive-instruction defect to `AGENTS.md:589` and it was fixed there
(`461f7f05f`). **That fix was incomplete**, and WP01's reviewer caught why: the fixed sentence ends
*"copy-template documented in `docs/development/ui-e2e.md`"*, and that file carried the identical
`PWHEADLESS=1 uv run pytest tests/ui/ -q` at `:37` (inside a fenced block headed *"matching CI
exactly"*) and again at `:109`. The hazard had been moved one hop away and was reached **by following
the link in the sentence that fixed it**. Both sites are now fixed.

**The class is far larger and is NOT this mission's scope.** A repo-wide count of `uv run `
instructions in `*.md`, excluding prose warning against the form, returns **2447** occurrences —
concentrated in `docs/guides/`, `docs/api/` and historical `kitty-specs/` dossiers. Notable live ones
outside this mission's surface include `RELEASE_CHECKLIST.md:89`
(`SPEC_KITTY_ENABLE_SAAS_SYNC=1 uv run pytest tests/ -v`) and six in `docs/development/pr-landing.md`.

Fixed here: only the two sites `AGENTS.md` directly points a reader to, because leaving those makes the
`AGENTS.md` fix a redirect rather than a repair. Everything else is a repo-wide documentation sweep
that deserves its own mission — it is a mechanical edit across hundreds of files with a real
false-positive risk (some `uv run` invocations carry the required `--extra` flags and are correct).

---

## RL-007 — lane auto-rebase uses the *attach* `git worktree add` form on a branch it just failed to find (2026-08-07)

**Observed.** `spec-kitty agent action review WP01` aborted with:

```
LANE_AUTO_REBASE_FAILED: fatal: invalid reference: kitty/mission-sync-sleep-count-3136-01KZ9B5A-lane-a
```

**Root cause — read, not guessed.** In `src/specify_cli/lanes/lifecycle_sync.py`:

- `_resolve_lane_branch` (`:91-123`) tries each computed candidate against `_git_ref_exists`, and when
  **none exists** falls through to `:120-123`, returning `candidates[0]` — a branch name that is known
  **not** to be a ref. (The `_git_stdout` leg above it returns `None` here: the lane worktree does not
  exist, and `:73` deliberately swallows the resulting `FileNotFoundError`.)
- `sync_lane_after_coordination_commit` then reaches `:183-191` and runs

  ```python
  ["git", "worktree", "add", str(worktree_path), lane_branch]     # :186 — no -b
  ```

  `git worktree add <path> <branch>` **checks out an existing commit-ish; it does not create a
  branch.** Handed a non-existent ref it fails with exactly the observed message.

The repo already has both forms, and this call site picked the wrong one:

| Site | Form | Intent |
|---|---|---|
| `lanes/worktree_allocator.py:634` | `worktree add -b <branch> <path> <base>` | **create** a new lane branch |
| `lanes/worktree_allocator.py:661` | `worktree add <path> <existing_branch>` | **attach** — docstring at `:651` says "WITHOUT `-b`" and "existing" |
| `lanes/lifecycle_sync.py:186` | attach form | reached **only** when the branch was not found — so the attach precondition is violated by construction |

**Reproduced** in a throwaway repo (not this checkout): `git worktree add <path> kitty/mission-demo-lane-a`
→ `fatal: invalid reference: kitty/mission-demo-lane-a`; the same call with `-b <branch> <path> main`
succeeds and creates the branch.

**Why it fired on WP01.** WP01 was implemented in the repository-root checkout on
`feat/sync-sleep-count-3136`, not in a lane worktree. `git branch --list 'kitty/*'` shows only the
mission branch, and `.worktrees/` holds only the `-coord` husk — so `-lane-a` was never materialized,
and the first coordination-commit sync found nothing to attach to.

**Does it block WP02? — Partially. Conditional, and the condition is under the operator's control.**

- **No**, on the normal path: `spec-kitty implement WP02` allocates the lane through
  `worktree_allocator.py:634`, which **does** pass `-b` and creates `kitty/…-lane-b` up front. Once
  the ref exists, `_resolve_lane_branch` returns it from the `:117-119` loop instead of falling
  through to `:120-123`. WP02 run this way does not hit RL-007.

  > **⚠️ CORRECTED (WP01 remediation, cycle 3) — this previously read "…and the attach form at `:186`
  > is correct."** That overstates what happens, and understates the conclusion. `spec-kitty implement`
  > allocates the lane **worktree**, not just the branch, so by the time
  > `sync_lane_after_coordination_commit` runs, the guard at `lifecycle_sync.py:183` —
  > `if not (worktree_path / ".git").exists():` — is **False**, and `:186` **never executes at all**.
  > The attach form is not "correct" on this path; it is unreached. That makes the finding *stronger*,
  > not weaker: `:186` is reachable **only** in the state where its own precondition is violated —
  > no branch, and therefore no worktree either. There is no path on which it runs and succeeds.
- **Yes**, if WP02 is worked the way WP01 was — edited directly in the repo-root checkout without
  materializing its lane. Then `-lane-b` never exists and the first coordination commit reproduces
  the identical failure. **This is the likely repeat**, because it is how the mission has been run so far.

**Recommended handling (no code change required):** materialize the lane before any coord commit — run
`spec-kitty implement WP02` and work inside the lane worktree it creates. That avoids RL-007 entirely.

**Proper fix — deliberately NOT taken here.** `lifecycle_sync.py:183-191` should create the branch when
`_resolve_lane_branch` could not resolve one (mirror `worktree_allocator.py:634`: `-b <lane_branch>
<path> <lanes_manifest.target_branch>`), or `_resolve_lane_branch` should return an explicit
"unresolved" signal rather than a name it knows is dead. **Out of scope for WP01:** it is
lane-lifecycle runtime behavior affecting every coord-topology mission, it sits outside WP01's
declared write scope (`.python-version`, `uv.lock`), and per DIR-034 it wants a red-first regression
test before the one-line change. Ledgered rather than fixed.

---

## RL-008 — a vacuous `status.json` sits on the PRIMARY partition beside the real one on coord (2026-08-07)

`spec-kitty agent tasks move-task` reports *"1 unrelated dirty file(s) ignored"*. The file is
`kitty-specs/sync-sleep-count-3136-01KZ9B5A/status.json` on the **primary** checkout. Its entire
content, quoted verbatim:

```
$ stat -c '%s bytes, mtime %y' kitty-specs/sync-sleep-count-3136-01KZ9B5A/status.json
365 bytes, mtime 2026-08-06 03:09:16.669313850 +0200
$ wc -l < kitty-specs/sync-sleep-count-3136-01KZ9B5A/status.json
20
$ cat kitty-specs/sync-sleep-count-3136-01KZ9B5A/status.json
{
  "event_count": 0,
  "last_event_id": null,
  "materialized_at": "",
  "mission_number": "",
  "mission_slug": "",
  "mission_type": "software-dev",
  "summary": {
    "approved": 0,
    "blocked": 0,
    "canceled": 0,
    "claimed": 0,
    "done": 0,
    "for_review": 0,
    "in_progress": 0,
    "in_review": 0,
    "planned": 0
  },
  "work_packages": {}
}
```

> **⚠️ CORRECTED (WP01 remediation, cycle 3).** This entry previously introduced the block with
> *"its entire content is:"* and then quoted `{}`. **That transcript was never run**; the file has
> never been `{}`. It is a **20-line, 365-byte materializer skeleton** — `"event_count": 0`, an
> all-zero `summary`, an empty `"work_packages"` — and its mtime, `2026-08-06 03:09:16 +0200`, is
> **~22 hours older than either remediation commit**, so it predates this work entirely and no edit
> here produced it. The *characterization* below (vacuous, untracked, harmless, a latent mis-read
> hazard) was correct and is confirmed against the real bytes; only the quoted evidence was false, and
> a fabricated `cat` transcript labelled *verbatim* is a defect regardless of whether the conclusion
> it supports happens to hold.

It is **untracked**, so it does not propagate, and the authoritative snapshot is the coord-partition
copy (`.worktrees/…-coord/kitty-specs/…/status.json`, 10 events, `WP01.lane = "for_review"`), which is
correct and complete. Reads went to the right file throughout — `agent tasks status` rendered the
right board.

Recorded because a **vacuous** snapshot — one that parses, and answers every query with a zero or an
empty map rather than failing — on the partition that does **not** own STATUS is a latent mis-read
hazard for any code that resolves the status surface by path existence rather than by topology. It is
the more dangerous shape of the two: `{}` would fail a schema read loudly, whereas this file satisfies
one and reports a mission with no work packages and no events. Not deleted here: it is untracked,
harmless while untracked, and removing files is outside this remediation's fix list.

**Related and more consequential — the WP01 lane was never `in_review`.** The rejected review was
expected to have left WP01 in `in_review`. The coord event log shows it did not:

```
in_progress -> for_review   2026-08-06T22:54:59.639003Z   reason="move-task: planned -> for_review"
```

That is WP01's **last** transition, and `status.json` summarises `"in_review": 0`. The
`spec-kitty agent action review WP01` invocation died in the RL-007 auto-rebase **before** it could
claim the WP, so the claim transition never happened and the lane stayed at `for_review`. A
`move-task WP01 --to for_review` is therefore a no-op and is correctly refused as
`Illegal transition: for_review -> for_review`. **It must not be forced** — forcing would append a
spurious transition to describe a move that did not occur. The desired end state already holds.

---

## RL-009 — the WP02 prose inventory is one occurrence short: `test_saas_client.py:39` (2026-08-07)

**Found by**: WP02 · **Severity**: makes the WP's own predicted post-fix grep counts unreachable

`WP02`'s `### The inventory` states, emphatically, *"**Prose, NOT a retarget — TWO occurrences, not
one.**"*, naming `:559` and `:715`. There is a **third**, and it is a different target string:

```
$ grep -n 'saas_client\.time\.monotonic' tests/sync/tracker/test_saas_client.py
39:    ``@patch("...saas_client.time.monotonic")`` patches the attribute on the
386:  … 9 live decorators …
```

`:39` sits inside `_advancing_clock`'s docstring — the very docstring `T009` **step 5** tells the WP
to *leave alone*. So the instruction set is self-consistent in what to **edit**; what is wrong is the
**count**, and the count is what the acceptance arms are keyed on. Consequences:

- The prompt says a naive `grep -c 'saas_client\.time\.sleep'` returns **15** — correct — but never
  states the companion figure. `grep -c 'saas_client\.time\.monotonic'` returns **10**, not the **9**
  the decorator table implies. Anyone reconciling 9 against 10 will go looking for a missing retarget
  that does not exist.
- Post-fix, `saas_client.time.monotonic` cannot reach `0`: `:39` is frozen by T009 step 5. The
  measured post-fix value is **1**, and no arm in the prompt predicts it.

Not folded: `:39` is correctly left alone, so there is no code change to make. The defect is in the
inventory's arithmetic and in every downstream arm that inherits it. **WP05's arm 4c is unaffected**
(it counts AST `patch()` nodes, and `:39` is a docstring), but any grep-anchored successor arm is.

## RL-010 — retargeting `test_saas_client.py:559` as a string swap makes the docstring assert a falsehood (2026-08-07)

**Found by**: WP02 · **Severity**: the instruction, followed literally, inverts the mission's finding

`T009` step 2 says to update **both** prose occurrences *"for consistency"*, and the `### Cross-lane
note` says `:559`'s *"target string moves in this step"*. Opened, `:559` is the subject of a sentence
that **asserts what that target does**:

```
**The mechanism (FR-005, established, not re-derived)**:
``@patch("specify_cli.tracker.saas_client.time.sleep")`` patches the
**stdlib** ``time`` module's ``sleep`` attribute -- `saas_client.py:19`
is a bare ``import time`` -- so the mock's call recorder is process-wide …
```

Replacing the string with `…saas_client._sleep` yields *"`@patch("…_sleep")` patches the **stdlib**
`time` module's `sleep` attribute … so the mock's call recorder is process-wide"* — which is **false**,
and false in precisely the direction this mission exists to correct. It would leave the codebase
documenting the alias as process-global.

**Resolution taken (stated here because it is a deviation from the literal instruction):** the
paragraph was rewritten rather than string-swapped. The pre-fix hazard is now in the past tense and
the pre-fix string is retained as the *named historical hazard*; a new clause names the post-fix
target `…saas_client._sleep` and why it is unreachable. The site changes, so `WP03` T019 arm F's
`(file, line)` pin still sees a moved site; the sentence is true in both halves.

**Consequence for the predicted counts.** Because `:559` legitimately keeps the pre-fix string as
history, and `:715` is explicitly frozen (T009 step 2's sanctioned option),
`grep -c 'saas_client\.time\.sleep' tests/sync/tracker/test_saas_client.py` lands at **2**, not the
`0` or `1` the prompt predicts. Both survivors are prose; the AST decorator count is **0**. Reported
rather than reconciled by editing prose to satisfy a numeric gate — the failure mode the prompt itself
names as already hit three times.

## RL-011 — WP02's DoD cites `:806`, a base-tree line number that the WP's own edits move (2026-08-07)

**Found by**: WP02 · **Severity**: low, but it is a self-invalidating citation

`T011` requires the corrected docstring to name *"the `pytest.raises` at `:806`"*, and DoD item 6
repeats `:806`. That is the line number on `98198e980`. The correction itself is three lines longer
than the text it replaces, and the `:559` and `:715` prose edits sit above it too, so post-fix the
`pytest.raises` lands at **`:819`** (+13; re-derived, and verified by reading the line back).

Writing `:806` into the shipped docstring would ship a false citation on day one. Resolution: the
docstring names **`:819`** as the live line and `:806` as its pre-fix location on `98198e980`, so the
citation is true and DoD item 6's literal `:806` grep is still satisfiable. Same class as the
self-measuring blocks corrected three times in `notes/environment-3136.md`.

## RL-012 — `spec-kitty implement WP02` fails on a stale recorded planning commit (2026-08-07)

**Found by**: WP02 · **Severity**: blocks the sanctioned start command (distinct from RL-007)

With RL-007 avoided by using the sanctioned `spec-kitty implement WP02 --mission …`, allocation still
failed — on a different mechanism:

```
Error: Workspace allocation failed: cannot auto-merge the recorded planning commit
'4bdcb48f12e07c7ee56a370422cf79983cee5eda' into lane 'lane-b': the merge conflicts.
```

The recorded planning commit is a **stale snapshot** (`2026-08-06 03:43`), while the lane had already
received the current planning artifacts via coord `ab3368840`. Every conflict was `add/add` on
`kitty-specs/` files, with the lane's side newer by `2087` insertions across 18 files. Resolved by
merging with every `kitty-specs/` conflict taken from the lane side; the stale commit contributed only
its 15 unique `kitty-ops/*.jsonl` op-logs. One path
(`kitty-specs/…/status.events.jsonl`) is outside the lane's sparse-checkout cone and had to be
resolved through the index (`git update-index --cacheinfo`) because `git checkout --ours` refuses it.

Not folded: the allocator's choice of recorded planning commit is runtime behaviour, outside WP02's
`owned_files`. Successors on other lanes will hit the same wall.

## RL-013 — a second doc still instructing the destructive bare `uv run` (2026-08-07)

**Found by**: WP02 · **Severity**: same class as RL-004/RL-006, new location

`tests/architectural/_gate_coverage_baseline.json`'s `_comment` field carries a regeneration
instruction in the destructive form:

```
Regenerate with: uv run python -m tests.architectural._gate_coverage --update-baseline
```

An agent regenerating the gate-coverage baseline follows a machine-readable field, not prose, and this
one strips `pytest`/`ruff`/`mypy` and downgrades the interpreter to the tracked `3.11.15`. Not fixed:
the file is outside WP02's `owned_files` and editing it would dirty a ratchet baseline this WP has no
reason to touch. **WP02 did not execute it.**

Also recorded: WP02's prompt cites the baseline as `_gate_coverage_baseline.json` with
`orphan_files: []` / `orphan_test_count: 0` — both figures are **correct**, but the path is
`tests/architectural/_gate_coverage_baseline.json`, not `tests/`.

## RL-014 — the WP02 guard legitimately carries a pre-fix target string; a naive repo-wide gate will trip on it (2026-08-07)

**Found by**: WP02 · **Severity**: cross-lane — a false red waiting for WP05

`tests/sync/tracker/test_sleep_attribution_guard_3136.py` contains
`specify_cli.tracker.saas_client.time.sleep` **three** times: twice in prose, and **once as a live
`patch()` target** —

```python
patch("specify_cli.tracker.saas_client.time.sleep") as stdlib_mock,
```

That is deliberate and load-bearing: it *is* the stdlib-polluted recorder that arm (b) evaluates
against, and `SC-004` arm (b) requires the **literal pre-fix form**. It resolves, so
`check_patch_targets.py` passes it (`All 5058 patch() targets valid.`).

**Warning for WP05.** DoD item 5's *"0 `patch()` target strings equal to any of the three pre-fix
strings"* is scoped to the **two census files**, and T010's AST counter reads exactly those two. If
arm 4c is implemented as a repo-wide or `tests/sync/tracker/`-wide scan, it will count this guard's
live `time.sleep` target and report `1` where it expects `0`. The correct scope is the two census
files; the guard must be exempted by construction, not by editing the guard.

**AMENDED 2026-08-07 (WP02 review). `1` is the AST answer; the shipped gate is a regex and reports `3`.**
The paragraph above was derived with an AST `patch()`-call-node reader. `check_patch_targets.py` — the
gate arm 4c would actually be built on — is **regex-based**, so it also matches the *prose* occurrences
that an AST pass correctly skips. Post-fix, a repo-wide regex over `tests/` finds **three** pre-fix
`time.sleep` targets, not one:

| site | kind | AST sees | regex sees |
|---|---|---|---|
| `tests/sync/tracker/test_sleep_attribution_guard_3136.py:157` | **live `patch()` target** (arm (b)'s deliberate pre-fix form) | ✅ | ✅ |
| `tests/sync/tracker/test_sleep_attribution_guard_3136.py:5` | module-docstring prose | ✖ | ✅ |
| `tests/sync/tracker/test_saas_client.py:562` | docstring prose (`C-004`'s permitted hunk) | ✖ | ✅ |

**WP05: size the exemption against the instrument you actually ship.** An AST-anchored arm 4c must exempt
**1**; a regex-anchored arm 4c must exempt **3**. Choosing the scope without first naming the reader is
how a pass-count gets pinned to the wrong world — the defect this whole mission exists to close.

## RL-015 — `saas_client.py` `mypy --strict` baseline: 2 pre-existing `no-any-return`, NOT filed (2026-08-07)

**Found by**: WP02 · **Severity**: pre-existing baseline, unchanged by this WP

`mypy --strict` is already red on this file, and was red on `98198e980`. Measured both sides this
session:

```
$ <venv>/mypy --strict src/specify_cli/tracker/saas_client.py          # post-WP02
src/specify_cli/tracker/saas_client.py:184: error: Returning Any from function declared to return "str | None"  [no-any-return]
src/specify_cli/tracker/saas_client.py:185: error: Returning Any from function declared to return "str | None"  [no-any-return]
Found 2 errors in 1 file (checked 1 source file)

$ git show 98198e980:src/specify_cli/tracker/saas_client.py > /tmp/wp02-base-saas.py
$ <venv>/mypy --strict /tmp/wp02-base-saas.py                          # base
/tmp/wp02-base-saas.py:162: error: Returning Any from function declared to return "str | None"  [no-any-return]
/tmp/wp02-base-saas.py:163: error: Returning Any from function declared to return "str | None"  [no-any-return]
Found 2 errors in 1 file (checked 1 source file)
```

**Same two errors, same code, same function** — `_current_team_slug_sync`, whose two `return`
statements are `return team.id` (post-fix `:184`) and `return session.teams[0].id` (post-fix `:185`);
`session.teams` is untyped at that boundary, so both returns are `Any`. The `+22` line shift is
exactly WP02's net insertion above them (26 alias-block lines minus T008's 4-line delete). The
criterion is *"no NEW findings"*, and it is **met**: exactly these two and no others.

They were **not fixed** (`:184-185` sit outside `C-004`'s permitted-hunk set) and **not silenced**
(`git diff 98198e980 -- src/ tests/ | grep -cE '^\+.*(# noqa|# type: ignore)'` → **0**, against a
control of 513 added lines).

**Not filed, and that is a governance conflict, not an omission.** DoD item 8 requires these to be
**filed** per the charter's *Pre-existing Failure Reporting Rule*, "with the issue number in the WP
notes". The operator direction governing this mission bars `gh issue create`. This is exactly the
latent conflict WP01 recorded at **`RL-005`**; WP02 is the first WP to actually trigger it, so it is
promoted here from latent to **live**. There is no issue number to hand to WP07 T042 — WP07's filings
register should carry this entry instead, and the operator must either lift the bar or amend the DoD.

**Prompt defect, same class as RL-011.** WP02 cites the two errors at `:162-163` and calls that the
post-WP state. `:162-163` is their **base-tree** location; post-fix they are at `:184-185`. A reviewer
grepping for `:162` in the shipped file will not find them.

## RL-016 — SC-003 Arm 3's mutation set is incomplete: it reddens the backoff node with `StopIteration` (2026-08-07)

**Found by**: WP02 · **Severity**: the arm passes its own count while grading nothing on one of four nodes

`T013` step 3 prescribes exactly two mutations: *"**Duplicate** the `_sleep(...)` call at `:439` and
add a fourth `pending` response to the backoff node's fixture"*, expecting **`4 failed`, each failing
on the call count**, with text naming counts (`4 != 3`, `2 != 1`) and **not** a delay value.

Applied literally, it does produce `4 failed` — but the backoff node's failure is:

```
E   StopIteration
tests/sync/tracker/test_saas_client.py:791: in test_exponential_backoff_intervals
    result = client._poll_operation("op-backoff")
```

**That is a fixture artifact, not the cardinality defect.** The backoff node patches `_randbelow` with
`side_effect=[1000, 2000, 3000]` — **three** values, one per expected poll. A fourth `pending`
response forces a **fourth** iteration, which exhausts the list at
`jitter_basis_points = _randbelow(4000)` and raises before `assert len(sleep_calls) == 3` is ever
evaluated. The node never reaches its count assertion, so for that node the arm grades nothing while
still contributing to the `4 failed` total the DoD checks.

This is precisely the failure mode the WP02 brief warns about — *"Two sibling WPs had to redo a red
that failed on a fixture artifact rather than the defect"* — reproduced by following the prompt
exactly.

**Corrected mutation set (three elements, used for the reported arm 3):**

1. duplicate `_sleep(float(wait_seconds))` (post-fix `:461`) — the three 429 nodes then see
   cardinality 2 where 1 is expected;
2. add a fourth `pending` response to the backoff fixture;
3. **extend `side_effect=[1000, 2000, 3000]` to `[1000, 2000, 3000, 4000]`** so the fourth poll has a
   jitter value and the loop reaches the assertion.

Result, with the arm's own negative control:

```
4 failed
E   assert 4 == 3                                                       <- backoff, the COUNT
E   AssertionError: Expected '_sleep' to be called once. Called 2 times. (x3)
StopIteration present : 0
```

Not folded: the mutation is applied and reverted, never committed, so there is no code change to
carry. The defect is in the prompt's prescribed mutation set, and any successor re-running SC-003
Arm 3 from the prompt text will reproduce the artifact. **`SC-003` Arm 3 should be amended to name the
third mutation.**

## RL-017 — lane worktrees carry the destructive bare `uv run`; the repository root does not (2026-08-07)

**Found by**: WP03 · **Severity**: destroys the venv on contact — four occurrences this mission

`AGENTS.md:589` (reached as `CLAUDE.md`, a symlink) instructs ``PWHEADLESS=1 uv run pytest tests/ui/ -q``
in **lane-b and lane-c** (`grep -c` → 1 each). The repository-root tree has **0**: the fix landed on the
mission branch *after* these lanes were seeded from `98198e980`, so every lane worktree carries the
pre-fix text and will keep instructing the destructive form until it lands there.

The form is not merely discouraged — it **uninstalls 70 packages including `pytest`, `ruff` and
`mypy`**, and it honours `.python-version` (still `3.11.15`) so it also silently downgrades the
interpreter two minor versions away from CI. `spec.md:520-535` records it observed twice; this mission
has now paid for it four times. Recovery is `uv sync --python 3.12 --extra test --extra lint`.

**Not fixed in-lane:** editing `AGENTS.md` inside lane-c would collide at consolidation with the fix
already landed at the repository root, and `AGENTS.md` is not in WP03's `owned_files`. Same class as
RL-004, RL-006 and RL-013; recorded separately because this is the **lane-worktree** instance, which
those three do not cover and which no consolidation step removes on its own.

**WP03 executed no `uv` subcommand of any kind**, before or after this review remediation. Every
command in this WP is `./.venv/bin/python …`.

---

## RL-018 — a trailing bare word `patch` mints a phantom target for the `[ENFORCED]` lint; closed by comment, not by guard (2026-08-07)

**Found by**: WP03 · **Severity**: a live trap for any file that *writes about* `patch()` targets

`check_patch_targets.py`'s extractor is a regex over raw source whose `\s*` **bridges newlines**. A
trailing comment ending in the bare word `patch`, immediately above a line beginning with a quoted
string, is therefore read as a live target:

```python
        ("seam_decorator_cases.py", 34, 2),  # .call_count comparison
        # ... context-manager patch
        ("seam_contextmanager_cases.py", 32, 4),
```

extracts the target `seam_contextmanager_cases.py` and **reddens the enforced job**:
`::error::Broken patch() targets (1 of 5064 checked)`. Reproduced and then fixed inside WP03.

**How it is closed today, stated plainly: by a comment, not by a guard.** The only thing standing
between this repository and a repeat is a prose NB in
`tests/architectural/test_patch_seam_census_control.py` telling the next author not to end a comment
with the word `patch`. Nothing executes it. A convention that lives in a comment is closed for the
person who read the comment and open for everyone else.

**Closing action, named and deliberately NOT attempted here:** replace `extract_targets`'s regex with
an AST reader in `scripts/check_patch_targets.py`, which makes the class unrepresentable — a comment
is not an `ast.Call`. **Do not simply stop the regex bridging newlines.** The bridge is load-bearing
for legitimate multi-line calls:

```python
patch(
    "specify_cli.tracker.saas_client.time.sleep"
)
```

Narrowing `\s*` to `[ \t]*` would silently drop every one of those and weaken an `[ENFORCED]` gate
while appearing to harden it. The rewrite is a behaviour change to a gate WP03 owns but that no
success criterion covers, and it would land unreviewed against its real corpus (5063 targets); it is
therefore named, sized and left for a WP that can grade it.

It is the exact mirror of the `tests/sync/test_dossier_trigger.py:54` AST-only cross-check case, and
independent evidence for NFR-007's AST mandate.

---

## RL-019 — charter DIR-013 vs the operator's bar on filing issues: no trigger in WP03 (2026-08-07)

**Found by**: WP03 · **Severity**: standing conflict, not re-litigated

Charter DIR-013 (`Pre-existing Failure Reporting Rule`) requires opening a GitHub issue before
treating any pre-existing failure as accepted baseline. Operator direction for this mission bars
`gh issue create`. **WP03 encountered no pre-existing failure**, in the original pass or in this
review remediation, so the rule has no trigger here and nothing was suppressed. Recorded so the
absence is on the record rather than inferred from silence. The conflict itself is already
RL-005 and is not re-argued.

---

## RL-020 — `spec-kitty implement WP03` could not allocate the lane unaided (2026-08-07)

**Found by**: WP03 · **Severity**: recurs for every remaining lane in this mission

The sanctioned start command failed with `cannot auto-merge the recorded planning commit … into lane
'lane-c'`, and the lane could only be allocated after a manual merge. The error was actionable and
the supported path was followed.

Recorded because the **cause is structural, not incidental**: the lane branches were seeded from a
commit that predates the recorded planning commit, so the same failure is waiting for every lane not
yet allocated. Same family as RL-012 (the WP02 instance); this entry names the recurrence, which
RL-012 treats as a one-off.

---

## RL-021 — `notes/census-3136.md` asserted a stale restatement at `spec.md:566-567` that is not there (2026-08-07)

**Found by**: WP03 review remediation · **Severity**: would send a later WP to "fix" a non-defect

`notes/census-3136.md` twice recorded that "one stale restatement of the retired parenthetical
survives at `spec.md:566-567`". Read verbatim, that line carries the **corrected** composition —
*"which is **14** pre-fix (13 in `test_saas_client.py` + 1 in `…_origin.py:229`, per `:504`) and
**14** post-fix"* — landed by `91255f6da` ("repair 25 drifted citations and close the last spec
contradiction"). The claim was itself the drifted citation.

**Folded**: both occurrences in the note are struck through and withdrawn in place. Ledgered anyway
because a *recorded, not fixed* finding is exactly the kind of item a later WP picks up and acts on,
and acting on this one means editing a spec line that is already right.

---

## RL-022 — `sleep_seam_patch_sites` is 16 on the composed tree, not the invariant 14: WP05 owns the scoping decision (2026-08-07)

**Found by**: WP03 review remediation · **Severity**: cross-lane — a wrong number waiting for WP05

`spec.md:560-568` restates the retired `sleep_patch_sites: 14` as `sleep_seam_patch_sites`, "invariant
across the change". Measured on the composed lane-c + lane-b tree it is **16**:

```
test_saas_client.py        (_sleep)                          13
test_saas_client_origin.py:229                                1     -> the invariant 14
test_sleep_attribution_guard_3136.py:158  _sleep             +1
test_sleep_attribution_guard_3136.py:157  time.sleep (live)  +1     -> 16
```

**The invariant holds exactly as designed; the +2 is WP02's own guard**, whose `_dual_recorder_window`
patches the alias and the pre-fix stdlib target in the same `with` block on purpose — that dual
recorder *is* SC-004 arm (b)'s instrument, and its live pre-fix target is RL-014's subject.
`seam_patch_nodes` rises by only 1 because both sites share that node.

**WP05 must choose a scope and say which**, not pick a number: **16** unscoped (honest about the tree,
but it grades the mission's own output and rises again with any later guard), or **14** guard-excluded
(the invariant the criterion expresses, but it requires a **declared** exclusion echoed into `--json`
the way `first_party_roots` and `seam_module` already are — **never** a hardcoded filename inside the
census, which is the exact vacuity the instrument exists to prevent).

Same trap as RL-014's amendment: *size the count against the instrument you actually ship, and name
the scope before naming the number.*

## RL-050 — `check_docs_freshness.py`'s own remediation hint instructs the destructive bare `uv run` (2026-08-07)

**Found by**: WP04 · **Severity**: same class as RL-004/RL-006/RL-013, new location — and the worst
placement of the four, because it is emitted *at the moment an agent is under pressure to act*

`scripts/docs/check_docs_freshness.py:827-830`, inside `_docs_index_finding`, builds the
`suggested_action` string attached to every blocking `DOCS-INDEX-DRIFT` error:

```
regenerate the docs index with PYTHONPATH=. uv run python scripts/docs/docs_index.py --write, then commit it
```

**Measurement with its predicate.** The hint is not hypothetical — it fires on the exact workflow this
WP performs. Adding one ADR and regenerating only the two indexes the WP04 prompt names produces:

```
$ SPEC_KITTY_ENABLE_SAAS_SYNC=1 SPEC_KITTY_NO_UPGRADE_CHECK=1 PYTHONPATH=. \
    .venv/bin/python scripts/docs/check_docs_freshness.py --ci --link-check none
EXIT=1
ERROR DOCS-INDEX-DRIFT docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md: present in docs/ tree, absent from committed index
```

The remediation text is delivered together with a blocking failure, which is precisely the context in
which an agent copies a suggested command verbatim rather than auditing it. A bare `uv run` re-solves
against the tracked `.python-version` (`3.11.15`), uninstalls the 3.12 environment, and strips
`pytest` / `ruff` / `mypy`. This Mission has lost `.venv` four times to that form.

**WP04 did not execute the hint.** The index was regenerated with
`PYTHONPATH=. .venv/bin/python scripts/docs/docs_index.py --write` (`exit=0`, `drift=False`).

**Fold-or-file recommendation: FILE, not fold.** `scripts/docs/check_docs_freshness.py` is outside
WP04's `owned_files`, and the fix is a one-string edit that belongs with the repo-wide `uv run` sweep
already tracked as RL-004 / RL-006 / RL-013 rather than as a fourth isolated patch. Recommend folding
all four locations into a single follow-on that also greps for further emitters of the bare form in
`suggested_action` / `_comment` style machine-readable fields, which is where they hide from a prose
review.

## RL-051 — the WP04 prompt names two generated indexes; a new ADR requires three (2026-08-07)

**Found by**: WP04 · **Severity**: prompt defect — makes the WP's own DoD 7 unsatisfiable as written

The WP04 prompt states that `freshen_adr_inventory.py` *"writes **two** index updates in one
command"* (era `README.md` row + `docs/development/3-2-page-inventory.yaml`) and that its
`--check` reporting clean closes BLOCKER-5. DoD 7 then requires
`check_docs_freshness.py --ci` → `EXIT=0`.

**Following the prompt exactly leaves the blocking job red.** With both named indexes regenerated and
`freshen_adr_inventory --check: clean (missing_rows=0 inventory_stale=False)`, the gate still exits
`1` on `DOCS-INDEX-DRIFT` (measurement quoted in RL-050).

A **third** generated artifact exists: `docs/development/3-2-docs-retrieval-index.yaml`, the Common
Docs retrieval index (WP01 / C-001 — deliberately separate from the page inventory). Its drift rule is
`error`-severity and default-on, identical in blocking behaviour to `INVENTORY-LOCKFILE-DRIFT`
(`check_docs_freshness.py:816-831`). `freshen_adr_inventory.py` does **not** write it;
`scripts/docs/docs_index.py --write` does.

**Disposition: FOLDED.** WP04 regenerated it as a declared out-of-map edit (rationale in
`notes/adr-and-lockfile-3136.md` §D-4): a new ADR cannot land without it, so regenerating it is the
completion of T023's stated purpose rather than new scope. The diff is generator-written and contains
exactly one added page block for the new ADR.

**Carry-forward for successors.** Any future WP that adds a page under `docs/` must regenerate **all
three**. Note also that the retrieval index keys on **headings and the first paragraph**, not only
frontmatter — so the WP06 cross-lane hazard the prompt frames as "body-only is safe" is narrower than
stated: a body edit that changes a *heading* also drifts this file.

## RL-052 — `move-task` attributes another WP's out-of-map notes file to the moving WP, and blocks on it (2026-08-07)

**Found by**: WP04 · **Severity**: workflow blocker + data-loss adjacent

> **Renumbered into WP04's reserved block `RL-050`…`RL-059` (2026-08-07).** This entry was first
> filed as `RL-019`, then self-renumbered to `RL-020` to vacate a slot WP03's in-flight notes already
> referenced. Both numbers were superseded: the orchestrator's allocator commit `97e490c33` minted
> `RL-017`…`RL-022` on `feat/sync-sleep-count-3136` from the **coord** maximum, colliding with WP04's
> three lane-d entries, and WP03 ultimately filed its finding as `RL-021`. The allocator header was
> corrected in `7c96cf085`, which opened `RL-050`…`RL-059` for WP04; WP04's three entries moved there
> and the coord entries kept their IDs. Read against `feat/sync-sleep-count-3136` (`7c96cf085`), not
> against this branch's maximum.
>
> **Root cause is structural and remains the finding**: several lanes append sequential IDs to one
> shared ledger, and a lane can only see its *own* maximum. Reserved per-lane blocks fix it; a running
> maximum cannot — which is why the allocator reproduced the very collision it was written to prevent.

`spec-kitty agent tasks move-task WP04 --to for_review` refused with:

```
Blocking: 1 uncommitted file(s) owned by WP04:
Modified files in kitty-specs/:
   M kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/census-3136.md
```

**`census-3136.md` is not WP04's.** It is declared as **WP03's** out-of-map planning write at
`wps.yaml:306`, inside the `# WP03 — IC-04` block. WP04's own declared notes file is
`notes/adr-and-lockfile-3136.md` (`wps.yaml` WP04 block), and WP04's `owned_files` are three paths
under `docs/`. The uncommitted hunks are WP03's own review amendments, self-dated *"AMENDED
2026-08-07 (WP03 review)"*.

**Probable mechanism**: out-of-map planning writes are declared as YAML **comments**, so they are not
machine-readable. The guard appears to treat any dirty file under
`kitty-specs/<mission>/notes/` as owned by the moving WP, which is correct for exactly one WP and
wrong for every other.

**Second-order finding — the content is orphaned.** The dirty blob `b4c10f7ce` exists on **no lane
branch and not in `HEAD`** (checked lane-b/c/d/f and coord; all carry `6bfa746ba` or an empty tree):

```
lane-b/c/f: e69de29bb (absent)   lane-d/coord/HEAD: 6bfa746ba   root worktree: b4c10f7ce
```

55 insertions of WP03 review work exist **only** as an uncommitted file in the repository-root
checkout. This is the exact shape of the incident that destroyed 468 uncommitted lines earlier in this
Mission. WP04 took a read-only backup to scratchpad and **changed nothing**.

**Disposition: FILED, and deliberately not folded.** Committing another WP's in-flight notes under a
WP04 commit would misattribute authorship and could land a half-finished amendment. WP04 proceeded
with `move-task --force`, which is sound here because WP04's own surface is fully committed and its
lane worktree is clean:

```
$ git -C .worktrees/…-lane-d status --short   -> (empty)
$ git cat-file -e HEAD:<each of WP04's 4 files> -> all present
```

**Recommended actions**: (1) WP03's owner commits `census-3136.md` on WP03's lane; (2) the guard
resolves out-of-map declarations from a machine-readable field rather than inferring ownership from
the `notes/` directory, so it stops blocking WP *n* on WP *m*'s file.

---

## RL-023 — a sparse-excluded path that conflicts cannot be resolved by the documented `git checkout --ours` (2026-08-07)

**Found by**: WP06 (filed in WP06 remediation; ID taken from the reserved `RL-023`…`RL-029` block, not
from the running maximum) · **Severity**: workflow trap — the documented recovery command fails, and
its failure mode is a refusal rather than a wrong result, so it is loud but undocumented

During WP06's lane allocation, `spec-kitty implement WP06` auto-merged a stale recorded planning
commit and produced 10 add/add conflicts. Resolving them by the documented route —
`git checkout --ours <path>` — **could not write `status.events.jsonl`**: that path is excluded by the
lane worktree's sparse-checkout rules, so `git checkout` has no worktree file to write and refuses.

**The gap**: the documented conflict-resolution command silently assumes every conflicting path is
present in the worktree. Under sparse-checkout that assumption does not hold, and there is no
documented fallback. WP06 resolved the path **directly in the index** instead, which is correct but is
not written down anywhere an agent under merge pressure would find it.

**Why not folded**: WP06 owns a docs page and a notes file. The conflict-resolution runbook and the
sparse-checkout rules for lane worktrees are neither.

**Recommended action**: document the index-level resolution (`git update-index --cacheinfo` / `git
show :2:<path>`) as the sanctioned fallback for sparse-excluded conflicting paths, or make the lane
worktree's sparse rules include the paths the allocator's auto-merge can conflict on.

---

## RL-024 — the bounded row-id pattern collides with issue `#3030`'s enumeration, and `SC-010` sub-3 depends on it (2026-08-07)

**Found by**: WP06 (filed in WP06 remediation; ID from the reserved `RL-023`…`RL-029` block) ·
**Severity**: bears directly on a **live** acceptance criterion — `SC-010` sub-3 uses exactly this
pattern

`spec.md` bounds the row-id pattern to the real id range (`E1`–`E53`) specifically so that
`E402`/`E501`-style lint codes cannot match it. The bound does not achieve separation, because a
**second, unrelated enumeration occupies the same range**.

**Measured** on `tests/architectural/_baselines.yaml`:

```bash
B=tests/architectural/_baselines.yaml
grep -cE '\bE([1-9]|[1-4][0-9]|5[0-3])\b' "$B"              # → 7   LINES (not matches)
grep -oE '\bE([1-9]|[1-4][0-9]|5[0-3])\b' "$B" | wc -l      # → 12  occurrences
grep -oE '\bE([1-9]|[1-4][0-9]|5[0-3])\b' "$B" | sort -uV   # → 9   E1 E2 E3 E6 E13 E14 E15 E18 E20
```

Seven lines, **nine distinct tokens**, twelve occurrences — all belonging to issue `#3030`'s
egress-boundary enumeration, a different namespace entirely.

**The decisive case, which does not rest on any count**: `E15` names a **retired queue drain** at
`_baselines.yaml:375` *and* a **frozen string constant** in the process-global inventory. Two
enumerations share one range. **No range-bound can separate them** — only a path or context qualifier
can.

**Measurement-labelling note.** An earlier WP06 draft reported this as "seven tokens", sourced from
`grep -c`, which counts **matching lines, not matches**. Corrected here and in
`notes/non-goals-3136.md`. Same class as the mission's other count-under-the-wrong-noun defects.

**Why not folded**: `spec.md` is not owned by WP06.

**Recommended action**: qualify `SC-010` sub-3's pattern by path (exclude
`tests/architectural/_baselines.yaml`) or by context, rather than by numeric range.

---

## RL-025 — `spec.md` repeats the falsified two-name module-surface count (2026-08-07)

**Found by**: WP06 (filed in WP06 remediation; ID from the reserved `RL-023`…`RL-029` block) ·
**Severity**: a stated-as-verified numeric claim that its own cited command does not produce

`spec.md`'s *"Code facts verified directly"* section asserts that
`src/specify_cli/tracker/saas_client.py`'s module-level assignment surface is **two** names, under a
heading stating that everything numeric in it came from a command run on `98198e980`.

**Re-running that command on `98198e980` yields three**, not two — the section's own method (an `ast`
walk of `tree.body` collecting every `Assign`/`AnnAssign` bound to a `Name`) returns
`_SESSION_EXPIRED_MESSAGE` (`:36`), `_UNAUTHENTICATED_CATEGORY` (`:39`) and
`TRACKER_EGRESS_IDENTIFIER_KINDS` (`:51`). Once `FR-010`'s alias seam lands, the surface is **six**
(adding `_sleep`, `_monotonic`, `_randbelow`).

**What survives**: the *conclusion* is unaffected — the third name is a frozen `str` literal, not a
retry/backoff value, so "no leaked module-global retry/backoff value exists in `saas_client.py`" holds.
What is falsified is the **count**, the **enumeration**, and the claim that the measurement is
*exhaustive*.

**Already corrected where WP06 owns the surface**: the same claim in
`docs/development/process-global-inventory-3115.md` carries an explicit correction block, because that
page is in WP06's `owned_files`.

**Why not folded**: `spec.md` is not owned by WP06, and editing another package's authoritative
planning surface to fix a number is precisely the silent-widening this ledger exists to prevent.

**Recommended action**: correct the count and the enumeration in `spec.md`, and mark the section's
"verified directly" claim as re-derived, naming the commit the re-derivation ran on.

---

## RL-030 — `test_no_dead_symbols`'s ratchet disposition is unresolved; WP05 shipped the scoped-arm fallback (2026-08-07)

**Found by**: WP05 · **Severity**: pre-existing inert gate key, now visible rather than silent

`_baselines.yaml` carries `test_no_dead_symbols` in the YAML, absent from `_REQUIRED_TOP_LEVEL_KEYS`
and read by **no** comparison, so its growth fails nothing. Re-derived this session on the composed
tree, by opening the file rather than trusting the citation:

```
$ "$V/bin/python" -c "import yaml,pathlib; d=yaml.safe_load(...); print(len(d))"   -> 12 (pre-WP05)
$ grep -oE 'data\["[a-z_0-9]+"\]' tests/architectural/test_ratchet_baselines.py | sort -u | wc -l -> 10
  _REQUIRED_TOP_LEVEL_KEYS (read from the literal at :123-136)                                 -> 11
```

`plan.md` `[UNVERIFIED]` item 10 names two honest dispositions — register it in **both**
`single_baselines` lists, or remove it from the YAML — and states that choosing needs the owner of
the gate that key governs, which is outside this mission. Adding it to `_REQUIRED` alone is explicitly
**not** an option: that reproduces `test_all_declarations_required`'s defect (required, never read).

**WP05's resolution: the stated fallback, not a silent pick and not a deletion.** The new
reverse-containment arm `test_no_unregistered_baseline_keys_are_added` fires for any key added from
this mission forward. The one pre-existing offender sits in a **closed**
`_GRANDFATHERED_UNREGISTERED_KEYS` frozenset that is pinned by its own equality assertion, so widening
it costs a visible diff in `test_ratchet_baselines.py` rather than a silent one in the YAML. The arm
was proved non-vacuous by adding a throwaway 14th key and observing it red (transcript in
`notes/mechanism-gate-3136.md`).

**Why WP05 cannot fold it**: the decision is about the `__all__` dead-symbol gate's ratchet, not about
this mission's defect class. Its recorded numbers have already drifted unnoticed (YAML
`category_a_slice_f_deferred: 12` against a live `len()` of 9; `category_b_grandfathered_legacy: 193`
against 189), which is itself evidence the key needs an owner rather than a passing guess.

**Recommended action**: the owner of `tests/architectural/test_no_dead_symbols.py` registers it in
both comparison lists (measured **safe today** — both live sizes are *below* the recorded numbers, and
shrinkage warns rather than fails) or removes it from the YAML, then deletes it from
`_GRANDFATHERED_UNREGISTERED_KEYS`, which is the only edit that set permits.

---

## RL-031 — the WP05 prompt's `httpx.Client` and residue figures are pre-WP02 predictions; the composed tree differs (2026-08-07)

**Found by**: WP05 · **Severity**: prompt/plan drift — none of it changed the outcome, but each number was transcribable

The WP05 prompt and `plan.md` `[UNVERIFIED]` item 12 were written before WP02 landed, so every figure
describing the post-fix tree is a prediction. Re-measured with the shipped gate on the composed tree
(lane-e + lane-b + lane-c):

| claim | stated | measured | why it moved |
|---|---|---|---|
| `httpx.Client` reach-through sites | 130 | **131** | WP02's guard-era tree; one site added |
| ... binding `mock_cls` | 114 | **115** | same |
| ... read by a count/equality assertion | 0 | **0** | **holds** — the load-bearing half |
| ... carrying a `side_effect=` **drive** | (not stated) | **3** | `test_origin_integration.py:201,:366,:541` |
| narrowed predicate over `tests/sync/` | 293 | **270** | 24 retargets moved `reach_through` -> `own_module` |
| total dotted `patch()` sites | 664 | **669** | WP02's guard module |
| literal FR-005 predicate | 649 | **654** | same |
| in-class residue | ">= 29 across >= 10 files" | **22 across 5 files** | `plan.md` item 3 already flags this as two deliberately-approximate probes, not the shipped analyzer |

The residue figure is the one worth naming: `plan.md` item 3 says the `9` `mock_post`/`mock_get`
figure is "a lower bound" from a `grep -c` over **five** named files. Measured with the read-side
predicate, only **two** of those five carry a count-or-equality read at all —
`test_batch_error_surfacing.py`, `test_batch_retry_hygiene.py` and
`test_batch_400_no_details_poison_2736.py` bind `mock_post` but only ever set `return_value`, so they
are correctly out of class. The gate is not blind to them; they have nothing to read.

**Disposition**: no action needed on the gate — `frozenset(baseline) == frozenset(flagged)` holds with
an empty symmetric difference, and the smaller residue makes the shrink-to-zero target easier, not
weaker. Recorded so a reviewer grepping for `130` or `29` in the shipped artifacts does not conclude
something is missing.

**Minor, same class**: the WP05 prompt cites `[UNVERIFIED-D]` for the `httpx` item. No `-D` marker
exists anywhere in `plan.md`; the item is plain `[UNVERIFIED]` number 12.

---

## RL-032 — RL-022 resolved: 14, guard-excluded, declared by mechanism rather than by filename (2026-08-07)

**Found by**: WP05 · **Severity**: closes a cross-lane decision RL-022 handed forward

RL-022 recorded `sleep_seam_patch_sites` as **16** on the composed tree against `spec.md:560-568`'s
"invariant 14", and handed WP05 the scoping decision with two options and one prohibition: never a
hardcoded filename inside the instrument.

**Decision: 14, with two-sided recorder nodes excluded.** The exclusion is keyed on the *mechanism*
that makes the guard's pre-fix target legitimate — a node that patches **both** a pre-fix seam target
and its corresponding alias in the same window — implemented as
`test_shared_module_object_patches._two_sided_recorder_nodes`. Another guard built the same way is
exempt for the same structural reason; a file that merely shared a name is not. Both figures are
printed by the arm so the exclusion is visible rather than folded into a total:

```
[WP05 gate] sleep_seam_patch_sites (unscoped)      = 16
[WP05 gate] declared exclusion: two-sided recorder nodes = [('tests/sync/tracker/test_sleep_attribution_guard_3136.py', '_dual_recorder_window')]
[WP05 gate] sleep_seam_patch_sites (scoped)        = 14
```

**16 unscoped was rejected** because it grades the mission's own output: it rises again with any later
guard, so a criterion pinned to it fails *because* someone added an instrument.

**Reader named, per RL-014's amendment.** Arm 4c is built on the **AST** reader
(`patch_seam_census.run_census`), not on `check_patch_targets.py`'s regex. Sized against that reader
the repo-wide exemption is **one** site (`test_sleep_attribution_guard_3136.py:157`); a regex-anchored
arm would have had to exempt **three**, the extra two being docstring prose. Over arm 4c's own scope —
the two retarget files — the exemption is **zero**: the guard is not in that scope, and 0 pre-fix
targets are observed with nothing excluded.

**The exclusion is echoed into the gate's report**, which is where this gate's `--json` equivalent
lives; it is not a silent constant. `_SLEEP_ATTRS` at `patch_seam_census.py:80` remains a *census*
scope decision that is neither overridable nor echoed (the same class as RL-022, one level down) —
this gate does not depend on it, since it keys on patch-target verdicts and read-side assertions
rather than on attribute names, but the census-side gap is unclosed and belongs to WP03's owner.

---

## RL-033 — `spec-kitty implement` is blocked by another WP's in-flight write to the repository-root checkout (2026-08-07)

**Found by**: WP05 · **Severity**: cross-lane serialisation — two agents cannot start concurrently

`spec-kitty implement WP05` refused to allocate the lane for several minutes with:

```
Planning artifacts not committed:
  kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/non-goals-3136.md
```

That file is **WP06's** out-of-map planning write, and it was being edited live in the
repository-root checkout while WP05 tried to start. The check is repository-wide over
`kitty-specs/<mission>/`, so any WP's uncommitted planning artifact blocks **every** other WP's
`implement`, whichever lane it targets.

The suggested remediation (`git add -f <the whole mission directory>`) is worse than the block: it
would have committed another agent's half-written file onto `feat/sync-sleep-count-3136` under this
WP's name. WP05 waited instead and re-ran once WP06 committed.

Same family as **RL-052** (`move-task` attributing another WP's out-of-map notes file to the moving
WP): both come from inferring ownership from the `notes/` directory rather than from a
machine-readable declaration.

**Recommended action**: scope the uncommitted-planning-artifact gate to the artifacts the WP being
started actually declares, and never suggest a whole-directory `git add -f` as its remedy.

Also recorded, for the recurrence count named in **RL-020**: `spec-kitty implement WP05` again could
not auto-merge the recorded planning commit into `lane-e` and needed a manual merge first. The
conflicting files were all under `kitty-specs/`, and the lane HEAD was the **newer** side in every
case (it descends from the planning commit and already carried the `ae6bc0bce` SC-005 correction), so
resolution was "keep ours" throughout. Third lane in a row; the cause is structural, as RL-020 states.

---

## RL-034 — exhaustible `side_effect=` sequences on a shared module object: a real sub-class the gate does not cover (2026-08-07)

**Found by**: WP05 review · **Severity**: uncovered sub-class of the mission's own defect class — one
measured live site, plus four siblings one edit away from it

### What it is

The mechanism-keyed gate (`tests/architectural/test_shared_module_object_patches.py`) requires **both**
halves of its predicate: the patch must reach through to a shared module object, **and** the mock it
binds must be read by a count-or-equality **assertion**. A `side_effect=` *assignment* or *kwarg*
drives a mock but asserts nothing, so it is out of scope by construction.

That scoping is correct for FR-005, but it leaves a genuine hole. A `side_effect=` carrying an
**exhaustible sequence** on a process-global attribute is corruptible in exactly the way this mission
exists to close — it just corrupts by **raising** rather than by miscounting:

```
tests/sync/test_git_metadata.py:522
    with patch("specify_cli.sync.git_metadata.time.monotonic", side_effect=[1.0, 10.0]):
```

`time.monotonic` here is the shared stdlib attribute reached through `git_metadata` (verdict
`reach_through`). The list has exactly two elements for the two calls the code under test makes. Any
concurrent caller in the same pytest-xdist worker consuming one element exhausts it, and the victim
gets `StopIteration` from a call it did not make — a red with no relationship to the code under test,
and one whose *name* changes between runs, which is the symptom that opened this mission.

**This is the same flake class `RL-016` already records**, from the other direction: there, a
three-element `_randbelow` `side_effect=[1000, 2000, 3000]` was exhausted by an extra iteration and
raised `StopIteration` *before* the count assertion was ever evaluated. `RL-016` documents it as a
fixture artifact inside one node; this entry records it as a **property of the patch target**.

### Measurement, with its predicate

Predicate: sites under `tests/sync/` whose `patch()` target resolves to a mechanism verdict
(`reach_through` or `foreign`, from `scripts/check_patch_targets.resolve_patch_target`) **and** whose
`patch()` call carries a `side_effect=` with a literal list. Measured on the composed tree
(lane-e + lane-b + lane-c) with WP03's AST analyzer:

```
kwarg-form side_effect on a mechanism-verdict target, whole tests/sync/ : 1
   tests/sync/test_git_metadata.py:522  specify_cli.sync.git_metadata.time.monotonic  binds=None
```

**One** site. It is small and confined. Four decorator-form siblings patch the same target in the same
class (`:208`, `:230`, `:255`, `:264`); they are not exhaustible today (three bind a plain mock, one
uses `return_value=0.0`), but any of them becoming a `side_effect=[...]` sequence joins this class
without tripping any gate.

Also measured, because an earlier revision of the gate's docstring overstated it: folding drives into
the read half would add **33** rows to the baseline, of which **3** are the `mock_http_cls`
`httpx.Client` sites. Not 131 — the 131-site `httpx.Client` bucket has **zero** read-side assertions
and only those 3 drives.

### Why it could not be folded into WP05

1. **T032 directed the exclusion, and reversing it is the unshippable outcome the WP exists to
   avoid.** Widening the read half to include drives adds 33 baseline rows, 31 of which are ordinary
   `return_value`/sink plumbing with no corruptibility at all. That is the "130-row baseline" failure
   T032 names, at a quarter scale.
2. **The right predicate is a different one.** This sub-class is not "read by an assertion" — it is
   "driven by an *exhaustible* sequence", i.e. a literal-list `side_effect` whose length is finite.
   That is a third half, not a widening of the second, and it needs its own baseline because its
   population and its fix are different (`itertools.cycle`, a callable, or a longer list are all
   fixes that a count-based row cannot express).
3. **It is outside the enforced scope R-1 fixed.** `git_metadata.time.monotonic` is not the
   `saas_client` seam; touching it changes `C-004`'s permitted-hunk set, which the operator did not
   rule.

### Fold-or-file recommendation

**Fold into a follow-up mission, not into a new gate arm here.** Concretely: add a third predicate to
`test_shared_module_object_patches.py` keyed on `ast.keyword(arg="side_effect")` whose value is an
`ast.List` of literals, on a mechanism-verdict target, and freeze its population the same way (it is
**1** today, so the baseline is one row and the shrink-to-zero is a single edit). The fix for the one
live site is to make the sequence non-exhaustible — `side_effect=itertools.cycle([1.0, 10.0])` or a
callable — which also removes the coupling that makes the count meaningful.

Until then the gate's own docstring states this limitation in place, so the next author reads
`flagged_sites` as scoped rather than exhaustive.

### Related limitation, recorded in the same place

The read half joins on `(file, node_id, mock_name)`, so a mock **asserted in a different node** than
the one that patches it is invisible to it. WP02's guard is exactly that shape: `_dual_recorder_window`
patches, `_report` reads. This is why the gate's flagged count must not be read as "every corruptible
assertion in the tree". Recorded in `_read_keys`'s docstring rather than as a separate entry, because
it is a property of the census join WP03 owns, not a defect WP05 introduced.

---

# WP07 block — `RL-040` … `RL-049`

Taken from WP07's **reserved block** per the ID-allocation rule at the head of this file, never from
the running maximum. `RL-040`–`RL-044` are **T042's five filings** (issue-shaped content, ledger
address — `gh issue create` is barred and no issue number is invented or reserved). `RL-045`–`RL-049`
are WP07's own findings.

## RL-040 — seam displacement: an in-body `mock.side_effect` reassignment is structurally outside the shipped predicate (2026-08-07)

**Found by**: WP07 (T042 Filing 1) · **Severity**: medium — a whole mechanism sub-class the shipped
gate cannot reach · **Recommendation**: **file** (cannot be folded — see below)

A test reassigns `mock.side_effect` **in-body**, displacing a recorder while `call_count` keeps
incrementing. The shipped R-2 predicate reads the **arguments of the `patch()` call**, so an
assignment that happens later, inside the function body, is structurally invisible to it.

**The predecessor's evidence is retired.** `grep -rn 'sleep\.side_effect\s*=' tests/sync/` → 0 hits
closed a *different* hazard: it matches attribute assignment on a name ending in `sleep` only.

**Magnitude — `N` in / `M` out under a NAMED predicate, never a headline number.** Measured on the
composed tree this session:

```bash
# N in — every in-body `.side_effect =` reassignment under tests/sync/
grep -rnE '[A-Za-z_][A-Za-z0-9_.]*\.side_effect[[:space:]]*=' tests/sync/ | grep -vE 'side_effect=' | wc -l
# M out — narrowed to sleep/monotonic/run/post/randbelow recorders
grep -rnE '[A-Za-z_][A-Za-z0-9_.]*\.side_effect[[:space:]]*=' tests/sync/ | grep -vE 'side_effect=' \
  | grep -iE '(sleep|monotonic|run|post|randbelow)' | wc -l
```

| Predicate | WP07 prompt's calibration | **Measured, composed tree** |
|---|---|---|
| N in — all in-body reassignments under `tests/sync/` | 116 | **119** |
| M out — the five-recorder name filter above | 52 | **55** |
| `_run`-anchored variant (predicate printed below) | 45 | **48** |

**The `_run`-anchored predicate, printed — this entry's own rule requires it.** Cycle 1 shipped `48`
as a bare magnitude while the entry itself states *"a bare magnitude with no predicate is not a
measurement"*. The predicate is the `M` command with `run` narrowed to `_run`:

```bash
grep -rnE '[A-Za-z_][A-Za-z0-9_.]*\.side_effect[[:space:]]*=' tests/sync/ | grep -vE 'side_effect=' \
  | grep -iE '(sleep|monotonic|_run|post|randbelow)' | wc -l      # -> 48
```

It differs from `M` (55) only in the leading underscore, which drops the seven `run`-substring matches
that are not `_run`-shaped recorders. **Reported here so the number is re-derivable rather than
believed.**

**Every figure is exactly +3, and the +3 is accounted for**: the composed tree contains WP02's new
`tests/sync/tracker/test_sleep_attribution_guard_3136.py`, which contributes 3 rows to `M` (visible in
the per-file breakdown below). The prompt's calibration was taken on a tree without that file. **The
predicate is the measurement; the number is downstream of it.**

**`N − M = 64` dropped**, by recorder name — these are non-clock recorders:

| Dropped recorder | Count |
|---|---|
| `mock_http.request` | 23 |
| `mock_request` | 10 |
| `mock_client.status` | 6 |
| `mock_client.bind_resolve` / `bind_confirm` | 4 + 4 |
| `client.bind_mission_origin` | 4 |
| **`mock_time`** | **3** |
| others (`mock_create`, `resp.json`, `clock.tick`, …) | 10 |

**`mock_time` being dropped is itself a finding**: `test_git_metadata.py:218`, `:242`, `:274` are
in-body clock reassignments that the `M` name filter misses because `mock_time` contains none of
`sleep|monotonic|run|post|randbelow`. They are `RL-042`'s sites. **A successor must not read `M` as
exhaustive.**

**Per-file breakdown of `M` (55):** `test_git_metadata.py` 14, `tracker/test_saas_client.py` 10,
`test_batch_sync.py` 9, `test_offline_replay.py` 6, `tracker/test_sleep_attribution_guard_3136.py` 3,
`test_runtime.py` 2, `test_dossier_pipeline.py` 2, `test_body_transport.py` 2,
`test_batch_error_surfacing.py` 2, then 1 each in `tracker/test_saas_service.py`,
`test_project_identity.py`, `test_event_emission.py`, `test_emitter_origin.py`,
`test_dossier_trigger.py`.

**Reproduction shape** — a minimal test that the shipped predicate passes and the defect still bites:

```python
@patch("mod.time.sleep")           # predicate sees THIS target and judges it
def test_x(mock_sleep):
    mod.work()
    mock_sleep.side_effect = [0.0, 1.0]   # in-body displacement — invisible to the predicate
    mod.work()
    assert mock_sleep.call_count == 2     # graded against a recorder that was swapped mid-test
```

**Opened before citing**: `tests/sync/tracker/test_saas_client.py:817` reads
`mock_monotonic.side_effect = [0.0, 301.0]` — inside the census node
`TestPolling::test_timeout_after_5_minutes`. (The WP07 prompt cites `:804`; that is the **pre-retarget**
line number — see `RL-049`.)

**Why WP07 cannot fold it**: building it into the gate needs **intra-function dataflow** (track a name
from its `patch()` binding through later attribute assignment to the assertion), which pushes the
read-side matcher past the complexity ceiling of **15** that `ruff` `C901` / Sonar `S3776` enforce.
That is a gate-design decision owned by WP03/WP05's surfaces, not a WP07 edit.

---

## RL-041 — the `batch.py` residue: thread the EXISTING keyword argument; do NOT add an alias seam (2026-08-07)

**Found by**: WP07 (T042 Filing 2) · **Severity**: low-medium — one unthreaded caller ·
**Recommendation**: **file**, with the fix shape stated below

R2's ticket text said this residue *"requires alias seams in four more product modules"*. **That is
false for `batch.py`**, and filing it that way would institutionalise a redundant second seam in a
module that already exposes a working one — against **`FR-011`**.

**Opened and quoted this session, on the composed tree:**

- `src/specify_cli/sync/batch.py:628-632` already exposes the injection point:
  ```python
  def run_final_sync_with_retries(
      sync_operation: Callable[[], BatchSyncResult],
      *,
      sleep: Callable[[float], None] | None = None,
  ) -> BatchSyncResult:
  ```
- `batch.py:641`: `sleeper = time.sleep if sleep is None else sleep`
- `batch.py:674`: the single actual call — `sleeper(FINAL_SYNC_RETRY_BACKOFF_SECONDS)`
- `src/specify_cli/sync/background.py:467` is the **one caller that does not thread it**:
  ```python
  def _guarded_final_sync(self) -> None:
      """Run a single sync batch; swallows all exceptions."""
      run_final_sync_with_retries(self._perform_sync)      # <-- no sleep=
  ```
- Three tests already use the seam: `test_final_sync_diagnostics.py:180`, `:207`, `:239`, all
  `sleep=sleeps.append`.

**THE FIX IS TO THREAD THE EXISTING PARAMETER at `background.py:467` — NOT to add an alias seam.**
The injection point exists, is typed, is defaulted and is already exercised by three tests; the only
gap is one call site that does not pass it.

Note the prompt states the signature at `:626-641`; measured, the `def` begins at **`:628`** and `:641`
is the `sleeper = …` line. The span is right; the opening line is two off.

**The other frozen product modules are filed separately** (`RL-043`), each with its own `file:line` set
and seam shape: `sync/git_metadata.py`, `sync/body_transport.py`, and the `asyncio` reach under
`test_runtime.py`. They are **not** the same fix as this one and must not be bundled.

**Why WP07 cannot fold it**: `src/specify_cli/sync/background.py` is outside every WP's `owned_files`
in this mission, and threading a sleep seam into the daemon's final-sync path is a behaviour change to
a cone this mission holds no test evidence for.

---

## RL-042 — exact-list clock stimuli: a `StopIteration` sub-class the read-side predicate does not reach (2026-08-07)

**Found by**: WP07 (T042 Filing 3) · **Severity**: medium — reads as covered when it is not ·
**Recommendation**: **file** as a *named sub-class with its own read-side form*

`test_git_metadata.py:218`, `:242`, `:274`, `:522` and `tracker/test_saas_client.py:817` are **not**
count or equality assertions. They are **exact-list `side_effect` stimuli** that a concurrent caller
exhausts into `StopIteration`. The R-2 predicate requires the mock be *"read by a count or equality
assertion"*, so **it does not reach them**.

**All five opened this session** — and the shape difference is load-bearing:

| Site | Form | In-body? | Overlaps `RL-040`? |
|---|---|---|---|
| `test_git_metadata.py:218` | `mock_time.side_effect = [1.0, 2.0]` | **yes** | yes |
| `test_git_metadata.py:242` | `mock_time.side_effect = [1.0, 4.0]` | **yes** | yes |
| `test_git_metadata.py:274` | `mock_time.side_effect = [1.0, 2.99]` | **yes** | yes |
| `test_git_metadata.py:522` | `with patch("specify_cli.sync.git_metadata.time.monotonic", side_effect=[1.0, 10.0]):` | **no — kwarg form** | **no** |
| `tracker/test_saas_client.py:817` | `mock_monotonic.side_effect = [0.0, 301.0]` | **yes** | yes |

`:817` closes **incidentally** under R-1 because `_monotonic` becomes module-local. **The four in
`test_git_metadata.py` do not** — that module gets no alias seam in this mission.

**File it as a named sub-class of the mechanism with its own read-side form, so a successor does not
read `corruptible_assertions: 0` as covering it.** The census's zero is a statement about *count and
equality* reads; an exhaustible sequence is a third read-side form the census does not model.

**Why WP07 cannot fold it**: extending the read-side form set is a change to WP03's census predicate
and WP05's gate arm — both approved, both outside WP07's `owned_files`.

---

## RL-043 — the residue outside arm 4's `saas_client.py`-only scope; widen the seam check to all of `src/specify_cli/` (2026-08-07)

**Found by**: WP07 (T042 Filing 4) · **Severity**: medium · **Recommendation**: **file** with
"widen the seam check to `src/specify_cli/`" as the named follow-up

A direct `time.sleep` added to a **different** module in the same cone is outside arm 4's scope, which
is **`saas_client.py` only**. Nothing in the shipped gate would notice it.

**The prompt asks for "the `[R2-open]` rows the shipped gate actually flags". Measured: there are
none, because the marker does not exist.**

```bash
grep -rn "R2-open" --include=*.py --include=*.yaml scripts/ tests/     # -> no output
```

`[R2-open]` is a **plan-era artifact** with no referent in the shipped tree. Quoting "the gate's own
output" for it is impossible; the honest substitute is the gate's real flagged set, which is the
**22-row frozen baseline** in `tests/architectural/_baselines.yaml`, derived here rather than restated:

| `resolved_module`.`attr_path` | rows |
|---|---|
| `requests.post` | **12** |
| `subprocess.run` | 6 |
| `asyncio.run_coroutine_threadsafe` | **2** |
| `requests.get` | 1 |
| `time.sleep` | 1 |
| **total** | **22** |

By file: `test_batch_sync.py` 11, `test_git_metadata.py` 6, `test_body_transport.py` 2,
`test_runtime.py` 2, `test_final_sync_diagnostics.py` 1.

**`httpx.Client` corroborates the scoping decision**: the mechanism half alone would flag **131**
`…saas_client.httpx.Client` sites (`test_shared_module_object_patches.py:41,46`, opened), and the
shipped gate flags **0** of them — **zero `httpx` rows appear in the 22 above** — because none is read
by a count or equality assertion. The read-side join is what makes the gate shippable.

The frozen modules needing their own seam decision, each a separate follow-up:
`sync/git_metadata.py` (`subprocess.run`, 6 rows), `sync/body_transport.py` (`requests.post`, 2 rows),
and the `asyncio` reach under `test_runtime.py` (2 rows, `verdict: foreign`).

**Why WP07 cannot fold it**: widening arm 4 beyond `saas_client.py` re-scopes WP05's shipped gate and
would change `C-004`'s permitted-hunk set.

---

## RL-044 — newly-found process-global instances with no tracker item (2026-08-07)

**Found by**: WP07 (T042 Filing 5) · **Severity**: medium — the charter's Pre-existing Failure
Reporting Rule requires a record before a red counts as accepted baseline ·
**Recommendation**: **file**

`#3136` covers the sleep-count nodes. These do **not** have an item, and per the `DIR-013` ruling at
the head of this file the record is this entry:

| Instance | Measured count (composed tree) | Prompt's figure |
|---|---|---|
| `requests.post` reach-through, read by a count/equality assertion | **12** | ×9 |
| `asyncio.run_coroutine_threadsafe` (`verdict: foreign`) | **2** | ×1 (singular) |
| `subprocess.run` reach-through | 6 | not named |
| `requests.get` | 1 | not named |

Derived by loading the shipped baseline and grouping, not by grep:

```bash
./.venv/bin/python -c "
import yaml,collections
d=yaml.safe_load(open('tests/architectural/_baselines.yaml'))
print(collections.Counter((r['resolved_module'],r['attr_path']) for r in d['test_shared_module_object_patches']['rows']))"
```

**`test_git_metadata.py:398` opened and confirmed verbatim**:

```python
assert mock_run.call_args.kwargs.get("cwd") == tmp_path
```

with `@patch("specify_cli.sync.git_metadata.subprocess.run")` at `:392` — a `call_args_read` on a
shared `subprocess` module object.

**Why WP07 cannot fold it**: every one of these sits outside `saas_client.py`, i.e. outside R-1's seam
and outside `C-004`'s permitted hunks.

---

## RL-045 — the mission's code was not on `feat/`; lane consolidation had not run when WP07 opened (2026-08-07)

**Found by**: WP07 · **Severity**: **landing blocker** — a PR opened from `feat/` as the WP prompt
literally instructs would have contained the governance dossier and **none of the fix** ·
**Recommendation**: **fold** — handled in-WP; recorded so the sequencing is not re-derived

`tasks/WP07-…md` T040 instructs `--head MOES-Media:feat/sync-sleep-count-3136`. Measured at WP07 open,
that branch carried no mission code:

```bash
grep -c '^_sleep = time.sleep' src/specify_cli/tracker/saas_client.py   # on feat -> 0
git diff --stat feat/sync-sleep-count-3136..kitty/…-lane-b -- src/ tests/
#  src/specify_cli/tracker/saas_client.py | 42 +-   ... 5 files changed, 511 insertions(+)
```

All seven WPs' output sat on lane branches `lane-b`…`lane-g`; `feat` carried only the dossier and two
prose remediations. **`C-004` measured on `feat` returns an empty diff** — the exact false-pass the
constraint was rewritten to exclude.

**The sequencing is circular, and that is the finding.** `spec-kitty merge` is the mission's terminus
step: `spec-kitty accept` refuses while WP07 is not `done`/`approved`, so consolidation cannot precede
WP07 — yet WP07's own PR is defined against the consolidated tree.

**Resolution taken** (recorded, not improvised): the PR branch was composed per the canonical
pr-landing recipe — branch from `upstream/main`, take content by slice from each lane — **without**
running `spec-kitty merge`, which deletes lane branches and worktrees and would consolidate a mission
whose final WP is still in flight. Full composition table in
`notes/constraint-enforcement-3136.md` §7. Lane consolidation remains the operator's step.

**Review-cycle artifacts: assessed, and NOT required.** The pr-landing guide states *"`spec-kitty
merge` needs the latest WP `review-cycle-*.md` to be `approved`, not `rejected`"*. Measured, the gate
blocks only on an explicit `rejected` verdict; **absence passes**:

```
src/specify_cli/review/artifacts.py:365-375  — latest_review_artifact_verdict(...) returns None when
    no artifact exists; rejected_review_artifact_for_terminal_lane then returns None (no finding).
$ find kitty-specs/sync-sleep-count-3136-01KZ9B5A -name "review-cycle*"     # -> no output
$ spec-kitty merge --mission sync-sleep-count-3136-01KZ9B5A --dry-run       # -> EXIT=0
```

The dry-run runs *"the same review-artifact consistency gate that real merge runs"*
(`merge/forecast.py:190-193`) over all seven WPs and passes. **No review-cycle files were written.**
Writing `approved` verdicts for six WPs WP07 did not review would fabricate governance records; the
verdicts live in the `move-task --note` trail.

---

## RL-046 — integration crossing: upstream's `test_verdict_seam_census` key vs WP05's closed registration guard (2026-08-07)

**Found by**: WP07 · **Severity**: **red on the composed tree** — needs the gate owner's ruling ·
**Recommendation**: **file** — WP07 refuses to decide it unilaterally

```
tests/architectural/test_ratchet_baselines.py:585: test_no_unregistered_baseline_keys_are_added
E   AssertionError: `_baselines.yaml` carries top-level key(s) no comparison reads:
    ['test_verdict_seam_census'].
```

**Neither side is at fault; the collision exists only in composition.** Both halves measured on
pristine `upstream/main`:

```bash
grep -c "test_no_unregistered_baseline_keys_are_added" <pristine>/tests/architectural/test_ratchet_baselines.py  # 0 — WP05's guard, absent upstream
grep -c "^test_verdict_seam_census:" <pristine>/tests/architectural/_baselines.yaml                              # 1 — upstream's key, unseen by WP05
```

WP05 shipped a guard refusing any `_baselines.yaml` top-level key no comparison reads; upstream
(mission `review-cycle-verdict-seam-rebuild-01KZ2W7W`) then added exactly such a key.

**Both available moves are refused here, on WP05's own recorded reasoning**
(`test_ratchet_baselines.py:142-148`, opened): *"choosing between its two honest dispositions … needs
the owner of the gate it governs, which is outside mission `sync-sleep-count-3136-01KZ9B5A`'s scope to
decide unilaterally."*

1. **Register** it in `_REQUIRED_TOP_LEVEL_KEYS` + both `single_baselines` lists → this mission's gate
   starts enforcing a ratchet **owned by another mission**.
2. **Grandfather** it → structurally impossible: `_GRANDFATHERED_UNREGISTERED_KEYS` is pinned by
   **frozenset equality** at `:579` and declared CLOSED/shrink-only, so widening it fails the
   assertion immediately above the one being worked around.

**Owner**: the `test_verdict_seam_census` ratchet's owner (mission
`review-cycle-verdict-seam-rebuild-01KZ2W7W`), jointly with WP05's gate owner. Per `DIR-041`, an
`xfail` or a widened tolerance would mask a real defect and is refused.

---

## RL-047 — pre-existing upstream red: `test_routed_load_meta_floor` (2026-08-07)

**Found by**: WP07 · **Severity**: pre-existing; **not this mission's** · **Recommendation**: **file**
(this entry discharges `DIR-013` per the ruling at the head of this file)

```
tests/architectural/test_inline_meta_read_gate.py:1111: test_routed_load_meta_floor
E   AssertionError: ROUTED_LOAD_META_FLOOR (128) is more than ROUTED_LOAD_META_FLOOR_MARGIN (4)
    below the live routed count (133); tighten the floor.
```

**Command run**: `./.venv/bin/python -m pytest tests/architectural/ -q -ra -p no:cacheprovider -n auto
--dist loadfile` → `2 failed, 1778 passed, 5 skipped, 2 xfailed in 769.03s`.

**Why it is pre-existing** — reproduced on a pristine `upstream/main` worktree (`709a59534`):

```
$ PYTHONPATH=<pristine>/src ./.venv/bin/python -m pytest \
    tests/architectural/test_inline_meta_read_gate.py::test_routed_load_meta_floor -q -ra
PRISTINE_EXIT=1 ... 1 failed in 66.42s
```

Red on the base **and** red on the branch ⇒ not introduced here. Corroboration: `git diff upstream/main
-- tests/architectural/test_inline_meta_read_gate.py` is empty, and every routed site in the failure's
own list is under `src/mission_runtime/` or `src/runtime/next/` — cones this mission never edits.

**Why WP07 cannot fold it**: tightening an upstream floor is the upstream owner's call; "fixing" it
here would be a retry-to-green on someone else's ratchet.

---

## RL-048 — `check_patch_targets.py` reddens on WP05's DOCSTRING: a mission-attributable CI regression (2026-08-07)

**Found by**: WP07 · **Severity**: **HIGH — reddens a CI job, and it is this mission's own doing** ·
**Recommendation**: **file** (two defensible fix shapes, two different owners — see below)

The gate is wired into CI at **`.github/workflows/ci-quality.yml:884`**
(`run: uv run python scripts/check_patch_targets.py`), which defaults to scanning `tests/`.

**Control first — pristine `upstream/main` is GREEN:**

```
$ PYTHONPATH=<pristine>/src:<pristine> ./.venv/bin/python scripts/check_patch_targets.py tests
All 5065 patch() targets valid.                                   EXIT=0
```

**Composed tree is RED:**

```
$ PYTHONPATH=<prwt>/src:<prwt> ./.venv/bin/python scripts/check_patch_targets.py tests
::error::Broken patch() targets (1 of 5087 checked):
  tests/architectural/test_shared_module_object_patches.py:5: cannot import any prefix of 'a.b.c'
EXIT=1
```

**The "target" is prose.** `test_shared_module_object_patches.py:4-5` is docstring text explaining the
mechanism:

> *"``unittest.mock._get_target`` splits a target on the **last** dot and imports the left half, so
> ``patch("a.b.c.attr")`` mutates whatever ``a.b.c`` resolves to."*

**Root cause**: `extract_targets` (`scripts/check_patch_targets.py:70-80`) is a **regex over raw
source** — `_PATCH_TARGET_RE.finditer(source)` — with no AST awareness, so a `patch("…")` literal
inside a string or comment is indistinguishable from a real call.

**The new file is `tests/architectural/test_shared_module_object_patches.py`** — naming it explicitly,
because cycle 1 wrote *"the file is new in this mission"* immediately after mentioning
`scripts/check_patch_targets.py`, which **does** exist upstream and is merely *modified* here. The
gate is old; the docstring it chokes on is new:

```bash
git cat-file -e upstream/main:tests/architectural/test_shared_module_object_patches.py; echo $?  # 128 — absent
git cat-file -e upstream/main:scripts/check_patch_targets.py; echo $?                            #   0 — present
```

So this is **category (d), attributable to this diff**.

**This is the mission's own recurring defect turned on itself**: a text-matching probe grading prose
as code. WP07 hit this class **four times in one work package** — (i) this gate, matching a docstring
`patch("a.b.c.attr")`; (ii) the `SC-012` suppression grep, counting a docstring that asserts the
*absence* of a `# noqa`; (iii) `C-002`'s own grep, matching three WPs' prose asserting the formatter
was never run (`RL-049` item 10); and (iv) WP07's own notes file, which matched `C-002`'s pattern the
moment it **quoted** the three offending lines verbatim — falsifying, in the same paragraph, the
sentence claiming its own count was zero. Caught by re-running the probe after writing, not by
reading.

**Two generalisations, and they are the useful output rather than any single fix:**
1. **Every text-matching probe in this programme needs an is-this-code predicate.** A regex over raw
   source cannot distinguish a call from a sentence about a call, and this codebase writes a great
   many sentences about calls.
2. **A probe must be re-run after the report that quotes it is written.** A report that quotes its own
   probe's matches is part of the probe's input; measuring before writing measures the wrong tree.

**Two fix shapes, deliberately not chosen here:**

| Fix | Owner | Note |
|---|---|---|
| Make `extract_targets` AST-aware (walk `ast.Call` nodes, not regex) | **WP03** (`scripts/check_patch_targets.py`) | the structural fix; also removes the whole false-positive class. WP03 already ships an AST census (`patch_seam_census.py`) — the capability exists |
| Break the literal in WP05's docstring (e.g. ``patch("a.b.c" ".attr")``) | **WP05** (`tests/architectural/test_shared_module_object_patches.py`) | one-line, but leaves the gate able to redden on any future prose |

**Why WP07 cannot fold it**: both files are other WPs' `owned_files` and both are already `approved`;
and choosing between a gate change and a prose change is a design decision, which is outside an
implementer's boundary. **Surfaced in the PR body as the top landing risk rather than worked around.**

### RESOLVED (2026-08-07) — the prose was fixed; the gate's regex was deliberately left alone

The design call was made by the operator: **fix the prose, not the gate.** Row 1 of the table above
(make `extract_targets` AST-aware) was **rejected**, and `RL-018` records why with a measurement —
narrowing the extractor silently drops about a third of an enforced gate's corpus while looking like
hardening. Re-measured on this PR head rather than transcribed: narrowing `\s*` to `[ \t]*` drops
**1681 of 5086** targets. The `\s*` legitimately bridges newlines for multi-line `patch(\n "target")`
calls, so it stays.

**Row 2 of the table above is WRONG as written, and this is the finding.** The suggested shape
``patch("a.b.c" ".attr")`` **does not work** — the regex's capture group closes at the first quote, so
it still mines `a.b.c`, which is still unresolvable (`cannot import any prefix of 'a.b'`) and the gate
is still red. Measured, not reasoned. String-splitting defeats a reader that requires the *whole*
literal; it does not defeat one that stops at the first closing quote.

**Shape actually applied — a brace placeholder**, the technique WP03 already established in
`test_patch_seam_census_control.py` (bind the seam to a name, interpolate it, so the regex meets `{`
and cannot match). The docstring now reads ``patch("{mod}.attr")``; `{` is not a valid first character
for the capture group, so the site mines nothing at all. This is self-enforcing in the right
direction: an author who later writes a concrete dotted path there gets a loud CI red, not a silent
mis-patch. The explanatory value is preserved in full and extended with a note saying why the
placeholder must stay.

**Closure evidence** (`PYTHONPATH=<prwt>/src`, shipped reader, no gate source changed):

```
before : ::error::Broken patch() targets (1 of 5087 checked):
           tests/architectural/test_shared_module_object_patches.py:5: cannot import any prefix of 'a.b.c'   EXIT=1
after  : All 5086 patch() targets valid.                                                                     EXIT=0
```

The corpus drops by exactly 1 — the phantom, and nothing else. Red-first proof: restoring the literal
reproduces the failure verbatim at 5087; reverting is byte-identical
(`sha256 bc6a26922a1179230afbc9c65872fb6a0c1907662b5a8b5e728a8f69fc97a63a`).

**Scope was measured, not assumed, and it is narrower than it looks.** Running `extract_targets` over
all of `tests/` finds **12** prose-sited targets, but only **1** is unresolvable. The other 11 must
**not** be "fixed", for two independent reasons that a blanket sweep would have broken:

1. `tests/architectural/_fixtures/patch_seam_control/seam_decoy_cases.py` carries a resolvable prose
   target **on purpose** — its own docstring says so. It is the control fixture for SC-015.
2. `test_patch_seam_census_control.py`'s **Arm F asserts `regex_only` is non-empty** over
   `tests/sync/`. That set is exactly the five prose sites in that tree. Removing them would fail the
   arm's own non-vacuity assertion. **Making every prose target unmineable would redden the census
   control.**

Generalisation #1 above still stands and is still unfiled: this fix closes one instance, not the
class. The class is closed only by an is-this-code predicate, which is WP03's call, not this one's.

### Ported to `lane-e` (2026-08-07, WP07 cycle 2) — the trap is removed, not just documented

**The fix existed only on `pr/sync-sleep-count-3136`, one branch away from the lane that owns the
file.** `feat/sync-sleep-count-3136` does **not** carry
`tests/architectural/test_shared_module_object_patches.py` at all, so
`spec-kitty merge` — the operator's consolidation step, which the dossier explicitly names as theirs —
would have installed **lane-e's** mineable copy into `feat/` and **reddened the `[ENFORCED]` `lint` job
again**, after the PR had already shown it green. Nothing in the PR body, the notes or this ledger said
so.

Measured before acting:

```bash
git show kitty/…-lane-e:tests/architectural/test_shared_module_object_patches.py | grep -c 'a\.b\.c'   # 2
git show pr/sync-sleep-count-3136:…                                             | grep -c 'a\.b\.c'   # 0
git cat-file -e feat/sync-sleep-count-3136:…                                                          # absent
```

**Route taken: port, not document.** `123e2dab3` on
`kitty/mission-sync-sleep-count-3136-01KZ9B5A-lane-e` applies the identical change. Verified safe
first — the docstring hunk was the **only** delta between lane-e's copy and the shipped copy, so the
port could not drag anything else, and the two blobs are now the **same object**:

```bash
git rev-parse kitty/…-lane-e:tests/architectural/test_shared_module_object_patches.py \
           pr/sync-sleep-count-3136:tests/architectural/test_shared_module_object_patches.py
# -> one sha, twice
```

Docstring only; no assertion, arm or baseline row touched. **Removing the trap beats warning about
it**, and it leaves the lane consistent with what shipped rather than one consolidation away from
contradicting it. No other lane carries the literal (checked `lane-b`…`lane-g`).

Filed inside `RL-048` rather than under a new id for the same reason as the section above: the
`RL-040`…`RL-049` block is **full**, and this is the closure of `RL-048` rather than a new finding.

### C-002 assessment (asked for explicitly; disposition: record, do not touch)

Re-measured on this PR head: `grep -rc 'ruff format' notes/` still returns **3**, and all three are
still WP02/WP04/WP05 prose *asserting the formatter was never run* — `RL-049` item 10 called this
correctly and it reproduces exactly. **An honest WP fails the check; a silent one passes.**

**It reddens nothing on this PR.** `ruff format` appears in **zero** files under `.github/workflows/`,
`scripts/`, or `tests/` — C-002 has no automated enforcement anywhere, matching
`analysis-report.md:195`. It is a spec criterion graded by hand, so there is no CI red to chase and
the unmineable-prose technique was correctly **not** applied to it.

Filed here rather than under a new id because the `RL-040`…`RL-049` block WP07 is using is **full** —
all ten ids are taken, so there is no next free id to take. C-002's substance already lives at
`RL-049` item 10; this is the confirming re-measurement against the composed tree, not a new finding.

---

## RL-049 — WP07 prompt figures and citations that do not survive measurement (2026-08-07)

**Found by**: WP07 · **Severity**: low individually, **high in aggregate** — an agent that transcribes
rather than measures ships six wrong numbers · **Recommendation**: **fold** into the WP prompt at the
next revision

Every item below was re-derived this session; none was transcribed. Consolidated into one entry
because they share a single cause: **figures calibrated on an earlier tree, and citations by
`file:line` that later edits moved.**

| # | Prompt says | Measured | Why it moved |
|---|---|---|---|
| 1 | `C-008` diff base is `98198e980` | produces an **8769-byte** non-empty "silent half" | `upstream/main` moved **70 commits** past the base and edited `ci-quality.yml`. The correct base for a rebased PR branch is `upstream/main`; attribution proves the delta is **byte-identical** to upstream's own |
| 2 | census node stimulus at `test_saas_client.py:804` | **`:817`** | WP02's own retargets moved it — same class as `RL-011` |
| 3 | inherited `# noqa: E402` at `tests/docs/test_docs_cli_reference_parity.py:52-56` | `tests/**architectural**/test_docs_cli_reference_parity.py:**55-56**` | wrong directory **and** wrong lines; the *idiom* claim is correct |
| 4 | added-suppression count "expected 0" | **6 raw / 5 real** | the mission does add 5 narrow inline `# noqa` (4× `E402` bootstrap, 1× `PLC0415`); the 6th is docstring prose. `SC-012` still passes — the **config** diff is 0 lines |
| 5 | magnitudes 116 in / 52 out / 45 `_run`-anchored | **119 / 55 / 48** | exactly **+3** each: WP02's guard file, absent from the calibration tree |
| 6 | Filing 5: `requests.post` ×9, `run_coroutine_threadsafe` (singular) | **×12** and **×2** | counted from the shipped 22-row baseline |
| 7 | `[R2-open]` rows the gate flags | **the marker does not exist in the tree** | plan-era artifact; substitute is the 22-row baseline (`RL-043`) |
| 8 | `batch.py` signature at `:626-641` | `def` at **`:628`**; `:641` is the `sleeper =` line | minor drift; `:674` exact |
| 9 | jitter resolution at `saas_client.py:104-106` | removal spans **`:104-108`** | `:104-106` is def+docstring+return; `:107-108` are the PEP 8 separators |
| **10** | `C-002`: `grep -rc 'ruff␣format' notes/` **must be 0** | **3** | **the criterion is self-defeating.** All three hits are WP02/WP04/WP05 prose *asserting the formatter was never run* (`mechanism-gate-3136.md:218`, `adr-and-lockfile-3136.md:388`, `alias-seam-3136.md:745`, all opened). `C-002` was rewritten to close a *vacuity* hole (an empty notes file passes); the rewrite opened the mirror hole — **an honest WP fails, a silent WP passes**. Restate it as a check on **invocation transcripts**, not on the string. The substantive claim is still true, established by the touched-line distribution instead |

**Confirmed correct and worth recording as such**: the aliases are `ast.Assign` at **`:58-60`**
(verified from the AST, zero `FunctionDef`); all five pre-fix call-site anchors `:439`, `:481`, `:484`,
`:515`, `:518`; `background.py:467`; `batch.py:674`; `test_git_metadata.py:218/:242/:274/:522`;
`test_git_metadata.py:398`; `httpx.Client` **131** sites with the shipped gate flagging **0**; and the
wrapper-vs-assignment asymmetry (**150 vs 153** under a stdlib-only patch; **3 vs 3**, indistinguishable,
in the both-patched window) — re-derived by construction, and stated in the correct direction.

**Why WP07 cannot fold it**: `tasks/WP07-…md` is a planning artifact owned by the planning lane; WP07
edits its own notes, not its own prompt.

---

## Landing addendum (2026-08-08) — maintainer PR-landing pass on #3252

Recorded by the maintainer during the #3252 landing pass, not by a mission WP. Kept outside the
`RL-040`…`RL-049` block (which is full) because it documents a landing-time adjudication, not an
in-mission finding.

**LA-01 — the mission's product half was superseded by #3187 before landing.** The same root-cause
flake was fixed independently on `upstream/main` (commit `958baf531`, issue #3187) with an
**instance `self._sleep` seam**, not the module-local `_sleep` alias R-1 prescribed. Per operator
adjudication the module-local alias, its ATDD guard (`test_sleep_attribution_guard_3136.py`), and the
alias ADR (`docs/adr/3.x/2026-08-06-1-module-local-stdlib-alias-seam.md`) were **dropped** — landing
them would have reverted #3187. See the LANDING RESCOPE banner in `spec.md`.

**LA-02 — RL-046 resolved (gate-owner ruling).** The reverse-containment arm
`test_no_unregistered_baseline_keys_are_added` in `tests/architectural/test_ratchet_baselines.py`
tripped on `main`'s `test_verdict_seam_census` key. Resolution: that key is a self-contained in-file
census (compared against `census/verdict_seam_IC01.yaml`), read by no `test_ratchet_baselines.py`
comparison, so it was added to the CLOSED `_GRANDFATHERED_UNREGISTERED_KEYS` set with a dated
rationale — the correct bin for a key no comparison reads. Registering it in a comparison list (the
arm's default suggestion) would have reproduced the "required, never read" defect this mission warned
about.

**LA-03 — the durable gate landed; the pre-existing reach-through debt is recorded, not fixed.** The
salvaged `test_shared_module_object_patches.py` gate flags ~11 pre-existing reach-through patch sites
on `main` (`git_metadata.subprocess.run`, `body_transport.requests.post`, `batch.time.sleep`,
`asyncio.run_coroutine_threadsafe`). These are recorded as the frozen shrink-only baseline (known
debt, owner `unassigned`), not fixed in this PR. The `saas_client` reach-throughs #3187 left open
(`monotonic`/`randbelow`) WERE closed here by extending #3187's instance seam, so `saas_client` no
longer appears in the flagged set.
