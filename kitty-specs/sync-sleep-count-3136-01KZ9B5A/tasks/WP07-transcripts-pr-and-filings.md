---
work_package_id: WP07
title: Constraint-enforcement transcripts, the draft PR and its non-gating CI observation, the filed gaps, and the window release
dependencies:
- WP02
- WP03
- WP04
- WP05
requirement_refs:
- FR-005
- NFR-006
- C-002
- C-003
- C-004
- C-006
- C-008
- C-010
planning_base_branch: feat/sync-sleep-count-3136
merge_target_branch: feat/sync-sleep-count-3136
branch_strategy: Planning artifacts for this mission were generated on feat/sync-sleep-count-3136. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/sync-sleep-count-3136 unless the human explicitly redirects the landing branch.
subtasks:
- T037
- T038
- T039
- T040
- T041
- T042
- T043
history: []
agent_profile: debugger-debbie
authoritative_surface: pyproject.toml
create_intent: []
execution_mode: code_change
owned_files:
- .github/workflows/ci-quality.yml
- ruff.toml
- pyproject.toml
- tests/architectural/test_no_legacy_terminology.py
role: investigator
tags: []
tracker_refs: []
---

# Work Package Prompt: WP07 – Constraint-enforcement transcripts, the draft PR and its non-gating CI observation, the filed gaps, and the window release

## ⚡ Do This First: Load Agent Profile

Before reading another line of this prompt, load the profile you execute under. Do not paraphrase it from this
file; load it.

```bash
/ad-hoc-profile-load debugger-debbie
```

- **Profile**: `debugger-debbie` · **Role**: `investigator` · **Agent**: `claude`

**If `/ad-hoc-profile-load` is unavailable in your surface**, use the CLI equivalents and say which one you
used:

```bash
./.venv/bin/spec-kitty agent profile show debugger-debbie
# fallback, if the id does not resolve — find it in the catalog, never guess:
./.venv/bin/spec-kitty agent profile list --all
```

Loading the profile, not naming it, is the point. State the initialization declaration and name the directives
you apply (DIR-001, DIR-003, DIR-030, DIR-032). This WP is **measurement, filing and handoff** — it implements
nothing; Debbie's read-only instinct is right for `src/`. The four owned files are owned so their *invariance*
can be proved; the only things this WP writes are notes, tracker issues and a draft PR.

---

## Objective

WP07 is the mission's **terminal verification**. It produces, in one place, the evidence that four
previously-unenforced constraints are actually enforced; opens the **draft** pull request and records a
deliberately **non-gating** CI observation beside it; files the gaps this mission's instruments do not cover;
and releases the `C-001` `tests/sync` window WP01 acquired.

| Ref | What WP07 must produce |
|---|---|
| `C-002` | Proof `ruff format` was never run — with a twin that makes the proof non-vacuous |
| `C-003` | The `#3130` / `#3193` leak `ERROR`s named out-of-scope wherever a suite count is reported |
| `C-004` | Proof `saas_client.py` changed **only** by the declared alias seam and the jitter resolution |
| `C-006` | The register of what is settled and **not** re-opened, versus what is newly filed |
| `C-008` | Proof the CI shard composition is unchanged — with a **loud sibling** so the silence is real |
| `C-010` | The terminology guard, run before push, `EXIT=0`, quoted |
| `NFR-006` / `SC-012` | Lint clean **and** no config escape hatch added |
| `FR-005` | The filed boundary of what the shipped mechanism gate does *not* reach |

**Start command**

```bash
spec-kitty implement WP07
```

**Never merge. Never un-draft without the operator's explicit go.**

---

## Context

**Dependencies.** `WP02` (alias seam + 24 retargets), `WP03` (census + control fixture), `WP04` (ADR + lockfile
regen) and `WP05` (gate + baseline key + ratchet registration) must all be `approved` or `done` first. That is
not ceremony: **every filing below is defined relative to what the shipped predicate covers**, so filing before
WP05 lands files a gap against a gate that does not yet exist.

### ⚠️ ENVIRONMENT — read before the first command; it has already cost this mission three times

**NEVER run a bare `uv run`.** It re-solves against the tracked `.python-version` (which reads `3.11.15` while
the venv and CI are `3.12`) and **destroys `.venv`** — dropping `pytest`, `ruff` and `mypy`. Not a style
preference, not hypothetical:

- **Proof**: `uv sync --dry-run --python 3.12` reports `Would uninstall 70 packages`.
- **Three occurrences in this mission**: once during planning; once in the post-plan pass where a bare `uv run`
  reached the shell by accident and recreated `.venv` at 3.11.15; and **once to the orchestrator immediately
  after it had committed the warning**. Writing the warning down has already failed to prevent the failure. The
  two sanctioned forms are the only forms.

```bash
# Form 1 (preferred) — direct, no resolver involvement.
./.venv/bin/python -m pytest ...
./.venv/bin/ruff check .
# Form 2 — uv-driven, extras pinned so the toolchain survives the resolve.
uv run --python 3.12 --extra test --extra lint python -m pytest ...
# Recovery, if a bare `uv run` already happened:
uv sync --python 3.12 --extra test --extra lint   # restores 3.12.13 / pytest 9.0.3 / ruff 0.15.12 / mypy 1.20.2
```

**`~/.local/bin/*` resolves to an unrelated checkout.** Prepend `./.venv/bin` to `PATH` for the whole session,
and **quote every `command -v` line into the notes** — a transcript with no resolved paths is not evidence that
the tool you ran is the tool you think you ran.

```bash
export PATH="$PWD/.venv/bin:$PATH"
command -v python pytest ruff mypy spec-kitty
python -V; pytest --version; ruff --version; mypy --version
```

### This WP's ownership is unusual — it owns four files it must NOT edit

A reader who sees `owned_files` will expect edits. There are none. **The deliverable is invariance**, and
ownership exists so exactly one WP is accountable for proving it.

| Owned file | Why it is owned | What "delivered" looks like |
|---|---|---|
| `.github/workflows/ci-quality.yml` | `C-008` — the fix must survive the existing shard composition, not be enabled by changing it (`fast-tests-sync` selection, four `--ignore=` entries, marker expression, `-n auto --dist loadfile`; verified at `:1161-1172`) | `git diff 98198e980 -- .github/workflows/ci-quality.yml` **empty**, reported beside a **non-empty** `git diff --stat` sibling from the same invocation |
| `ruff.toml` | `NFR-006` / `SC-012` — lint clean **without suppression** | diff reported **as diff text**; no added `per-file-ignores` entry, no widened `exclude` |
| `pyproject.toml` | same | same |
| `tests/architectural/test_no_legacy_terminology.py` | `C-010` — an owned deliverable per the plan's Charter Check row 5 | the guard **runs**, `EXIT=0`, transcript quoted; the file unchanged |

**The escape hatch `SC-012` closes**: instead of an inline `# noqa`, an implementer adds a `per-file-ignores`
entry or widens `exclude` — green lint, zero added inline suppressions, and exactly what `CLAUDE.md` prohibits.
`ruff check .` cannot see it. Both files **already carry** a `per-file-ignores` block (measured: `grep -c
per-file-ignores ruff.toml` → `1`, `pyproject.toml` → `1`), so an existence check proves nothing. The check must
be **diff-shaped**.

### The notes are out-of-map planning writes — the warning you will see is deliberate

`owned_files` may not contain any path under `kitty-specs/` (the mission-parsing validator hard-rejects it), so
this WP's three note files are **declared out-of-map planning writes**:

```
kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/constraint-enforcement-3136.md   (SC-016 transcripts; exactly ONE writer — this WP)
kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/ci-observation-3136.md           (draft PR + the non-gating observation)
kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/c001-window-3136.md              (RELEASE half only; WP01 wrote ACQUIRE)
```

Expect a **non-fatal** `code_change WP does not own any files under src/ or tests/` warning — it is deliberate.
Do **not** "fix" it by flipping `execution_mode` to `planning_artifact`; that collects this WP into the single
canonical planning lane and contradicts the plan's lane split.

### Measurement discipline — this WP is nothing but measurement

Every rule below has already been broken somewhere in this programme.

1. **Never pipe a suite whose exit status you need** — piping loses it. Redirect, then quote the `N passed` / `N
   failed` line **verbatim** out of the file.
2. **Print the input count for every derivation**: N in, M out, and why each of the N−M dropped. "46 sites" is
   not a measurement; "116 in, 46 out under `<predicate>`, 70 dropped because …" is.
3. **`-ra`, never `-rf`** (`-rf` hides errors). Count `^ERROR tests/`, **not** `^ERROR `.
4. **Control every probe against a known answer, and show the control.** A grep returning 0 is indistinguishable
   from a grep pointed at the wrong path.
5. **Report distributions, not scalars**, for anything that varies between runs.
6. **A killed or timed-out run is neither a pass nor a failure** — say exactly that.
7. **A cited `file:line` is not evidence that the line says what the citation claims — open it.** This programme
   has had docstring prose cited as a pinning assertion through **eight** references, and a fixture claimed to
   reach a site it cannot. Open every line you cite; say you did.
8. **`C-003`**: the `#3130` / `#3193` leak `ERROR`s are out of scope. Name them as pre-existing and excluded
   wherever a suite count appears; never count them as this mission's failures.

---

### Subtask T037 — the `C-002` / `C-004` / `C-008` transcripts, each with a criterion that can fail

**Purpose**

Three constraints R1 left checked by nothing, whose R2 replacements each perished for a specific reason.
Re-capture each so it can **actually fail**.

- **`C-004` perished** because "`git diff … saas_client.py` is empty" is **false by construction** under R-1:
  the alias seam *is* a change to that file. Binding form: the file changed **only** by (a) the FR-010 alias
  definitions plus call-site rerouting at `:439`, `:481`, `:484`, `:515`, `:518`, and (b) the
  `_poll_jitter_multiplier` resolution at `:104-106` — with **delay values, call cardinality and raise
  conditions unchanged**.
- **`C-008` perished** the other way: `git diff … → no output` is also what a bad ref, a wrong working directory
  or a mistyped path produces. It needs a **loud sibling**.
- **`C-002` perished** because `grep -rc 'ruff format' <wp-notes>` = 0 is satisfied by writing **no notes at
  all** — an empty or absent file passes. It needs a twin that makes the file non-empty by construction.

**Steps**

1. Create `notes/constraint-enforcement-3136.md` and write the `command -v` / `--version` block into it
   **first**, so it is non-empty before any grep runs against it.
2. `C-008`, both halves **from one invocation**, redirected:

```bash
{
  echo "### C-008 — silent half (must be EMPTY)"
  git diff 98198e980 -- .github/workflows/ci-quality.yml
  echo "### C-008 — LOUD sibling, same invocation (must be NON-EMPTY)"
  git diff --stat 98198e980 -- src/specify_cli/tracker/saas_client.py
} > /tmp/c008.txt 2>&1
```

   Quote both blocks with their byte counts. **If the loud half is empty the silent half proves nothing** — stop
   and diagnose the ref, not the workflow file.
3. `C-004`: `git diff 98198e980 -- src/specify_cli/tracker/saas_client.py > /tmp/c004.diff 2>&1`, then
   adjudicate **hunk by hunk**. Read the permitted-hunk lines **semantically, not literally**: three new
   module-scope definitions shift every later line, so `:439`/`:481`/`:484`/`:515`/`:518` are the **pre-fix**
   anchors — state both sets. **Any changed line outside the two permitted regions fails the criterion.**
4. `C-004` behaviour half: quote WP02's recorded evidence that the delay values (`[0.9, 2.0, 4.4]`, `3.0`,
   `5.0`, `2.0`), the cardinalities (`n=3`, `n=1`, `n=1`, `n=1`) and the raise conditions are unchanged. Only
   run `tests/sync` inside the `C-001` window (you hold it until T043); redirect and quote if you do.
5. `C-002`, both halves:

```bash
NOTES=kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/constraint-enforcement-3136.md
test -s "$NOTES" && echo "NON-EMPTY: $(wc -l < "$NOTES") lines"
grep -c 'command -v' "$NOTES"                                              # twin: must be >= 1
grep -rc 'ruff format' kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/   # must be 0
git diff --stat 98198e980 -- src/ tests/ > /tmp/c002-stat.txt 2>&1
```

   Then state, per file in `/tmp/c002-stat.txt`, whether its touched-line count is explicable by the declared work.
   A reformat shows up as a large touched-line count in files with no reason to change.

**Files** — Writes `notes/constraint-enforcement-3136.md` (out-of-map). Proves-invariant
`.github/workflows/ci-quality.yml` (owned); reads `src/specify_cli/tracker/saas_client.py` (WP02's).

**Validation** — `C-008` empty half **and** non-empty loud half quoted from one invocation with byte counts;
`C-004` diff quoted with a per-hunk verdict and zero out-of-region lines; `C-002` notes file `test -s` true with
its line count, twin grep ≥ 1, `ruff format` count exactly `0`.

---

### Subtask T038 — `NFR-006` / `SC-012`: lint clean, and the config escape hatch closed

**Purpose**

`ruff check .` green is necessary and **not sufficient**. The failure mode this criterion exists to catch is
adding a `per-file-ignores` entry or widening `exclude` instead of writing an inline `# noqa`. Neither `ruff
check .` nor an existence check on `per-file-ignores` detects it.

**Steps**

1. Baseline: `ruff check .` was green repo-wide at HEAD before this mission (`All checks passed!`, `EXIT=0`),
   so a clean result is meaningful rather than inherited noise. Run it redirected, quoting the last line:

```bash
./.venv/bin/ruff check . > /tmp/ruff.txt 2>&1; echo "EXIT=$?"
tail -1 /tmp/ruff.txt
```

2. Inline-suppression count, diff-level, **with its control**:

```bash
git diff -U0 98198e980 | grep -cE '^\+.*(# noqa|# type: ignore)'   # expected 0
git diff -U0 98198e980 | grep -c '^\+'                             # CONTROL: must be large non-zero
```

   A `0` from an unwired grep looks identical to a `0` from a clean diff. Show both numbers.
3. The config half — **as diff text, not a count**, so a reviewer can read it:

```bash
git diff 98198e980 -- ruff.toml pyproject.toml > /tmp/c012-config.diff 2>&1; wc -l /tmp/c012-config.diff
```

   Quote it in full (expected empty or near-empty), then state in prose: **no `per-file-ignores` entry was
   added** and **no `exclude` was widened**. If it is non-empty for another reason (version bump, dependency),
   name the lines and why they are not suppressions.
4. Name the one legitimate inherited suppression so a reviewer does not flag it: the `# noqa: E402` on the
   `sys.path` insertion idiom for importing a `scripts/` module from a test
   (`test_docs_cli_reference_parity.py:52-56`). It is pre-existing and load-bearing; WP03/WP05 copy it rather
   than adding a new class of suppression. **Open the line before asserting this.**

**Files** — Proves-invariant `ruff.toml`, `pyproject.toml` (both owned). Writes the `NFR-006` / `SC-012` section
of `notes/constraint-enforcement-3136.md`.

**Validation** — `All checks passed!` + `EXIT=0` quoted verbatim; added-suppression count `0` **with its control
shown**; the config diff quoted as text plus the explicit two-clause statement.

---

### Subtask T039 — `C-010`: the terminology guard, run before push and quoted

**Purpose**

The guard runs only in CI's `integration-tests-core-misc` job — **not** in any `fast-tests-*` shard. A
forbidden-term regression in WP04's ADR or WP06's inventory stamp therefore passes every local doctrine run and
reddens only at CI, after the PR is open. Run it **before push**, not at acceptance.

**Steps**

1. Run redirected, capturing the exit status separately from the output:

```bash
./.venv/bin/python -m pytest tests/architectural/test_no_legacy_terminology.py -q -ra -p no:cacheprovider > /tmp/c010.txt 2>&1; echo "EXIT=$?"
```

2. Quote the `N passed` line **verbatim** from `/tmp/c010.txt` plus the `EXIT=` value. Do not paraphrase "it
   passed".
3. Enumerate the prose surfaces covered: WP04's ADR under `docs/adr/3.x/`, WP04's `docs/adr/3.x/README.md` index
   row, WP06's `docs/development/process-global-inventory-3115.md` body stamp, and this mission's notes. Name
   the canonical terms this prose is most likely to trip (`Mission` not `feature`; `status commit` not
   `ceremony`).
4. If red: it is **this mission's** to fix only if the offending term sits on a line this mission added.
   Diff-attribute before fixing; never green-wash a pre-existing offender.

**Files** — Runs but does not modify `tests/architectural/test_no_legacy_terminology.py` (owned); writes the
`C-010` section of `notes/constraint-enforcement-3136.md`.

**Validation** — `EXIT=0` recorded, `N passed` quoted verbatim from the redirected file, covered prose surfaces
enumerated by path.

---

### Subtask T040 — open the DRAFT pull request

**Purpose**

The charter is draft-PR-first and the **operator merges**. R2 left the PR unowned while the CI observation is
*defined in terms of its head SHA* — an observation about an artifact nobody was responsible for creating. This
WP owns it.

**Steps**

1. `unset GITHUB_TOKEN` **first, every time.** The keyring token (`gho_*`) carries the `repo` scope the env var
   lacks; with `GITHUB_TOKEN` set, `gh` fails with "Missing required token scopes" on this org's repos. Verify
   with `unset GITHUB_TOKEN && gh auth status`.
2. Compact history per the charter before opening: **admin/planning commits bunched, code commits by logical
   slice — never one squash**, never an interactive reorder; rebase onto the current upstream base. The
   mission's one commit-boundary constraint must survive the compaction: WP02's guard commit **precedes** its
   alias commit (coupling E). Quote the two `git log --oneline` lines in order — a human reading `git log` is
   that constraint's only verifier.
3. Open a **cross-fork DRAFT** to `Priivacy-ai:main` via the repo's canonical PR-opening path. **Every
   placeholder is resolved — run this literally, do not substitute anything:**

   ```bash
   unset GITHUB_TOKEN
   gh pr create --draft \
     --repo Priivacy-ai/spec-kitty \
     --base main \
     --head MOES-Media:feat/sync-sleep-count-3136 \
     --body-file <path>
   ```

   The fork owner is **`MOES-Media`** and the head branch is **`feat/sync-sleep-count-3136`** — both
   re-derived this session from `git remote -v` (`fork  https://github.com/MOES-Media/spec-kitty.git`) and
   `git branch --show-current`. Re-run those two commands and quote them before opening, in case the
   remote or branch has moved. If your surface routes PR creation through a landing skill, use that skill
   rather than improvising the command — but the owner/base/head values above are the same either way.
4. Record in `notes/ci-observation-3136.md`: PR **number**, **head SHA** at open (`git rev-parse HEAD`), base
   ref, timestamp. The head SHA is the only reproducible handle — this mission's predecessor branch moved twice
   and every branch-name-anchored transcript became unreproducible.
5. Link `#3136` and every issue T042 files.
6. **Do not merge. Do not mark it ready for review.** Un-drafting requires the operator's explicit go; merging
   to the protected branch is the operator's action, never an agent's.

**Files** — Writes `notes/ci-observation-3136.md` (out-of-map). No repository file is modified here.

**Validation** — PR number and head SHA recorded; `gh pr view <n> --json isDraft` → `true`; guard-before-alias
`git log --oneline` excerpt quoted.

---

### Subtask T041 — the CI observation, labelled NON-GATING and unusable as a pass

**Purpose**

`SC-006` was **retired**, not descoped, because it discriminated nothing. Pristine `main` reddens on this class
in **11 of 18** consecutive `fast-tests-sync` jobs — including at `98198e980` — so a single clean run is the
**pre-fix** outcome **39%** of the time. A green shard is evidence of nothing. The mission's evidence is
**structural**: the injection guard (SC-004/SC-005), the mechanism gate (SC-007) and the base-branch red.

**Be precise about what "going green" means — two different claims are in play.**

- The fix targets **three `tests/sync/tracker/` nodes** (plus the fourth census node's assertion). *Those* going
  green in `fast-tests-sync` is achievable and worth observing.
- The **same job** also carries pre-existing `tests/regression` inverted-red markers this mission does not
  touch, and that job is **designed** to be red while open P0s exist.
- Therefore **the whole board going green is not achievable, and this WP must not claim it.** Any sentence of
  the form "CI is green now" is a defect in this artifact.

**Steps**

1. Create `notes/ci-observation-3136.md`. **Its first line must state that it is not evidence.** Suggested
   wording; the substance is binding even if the phrasing changes:

   > **NON-GATING OBSERVATION — this is not evidence of the fix and can never be cited as a pass.** A
   > clean `fast-tests-sync` run is the *pre-fix* outcome ~39% of the time (11 of 18 pristine-`main`
   > jobs red on this class, including at `98198e980`). `SC-006` was retired for exactly this reason.

2. Record, as observation only: the PR number, the **head SHA**, the `fast-tests-sync` outcome, and the pre-fix
   rate `11/18` alongside it, labelled *non-discriminating*.
3. If the job is red, classify every failure before commenting on it: (a) pre-existing known-P0 red, (b)
   CI-environment failure, (c) stale-install false red, (d) attributable to this diff. Only (d) is this
   mission's. Per `C-003`, the `#3130` / `#3193` leak `ERROR`s are category (a).
4. A killed or timed-out run is recorded as **neither a pass nor a failure**, in those words.
5. Report the three targeted nodes' individual outcomes **separately** from the job aggregate, so the two claims
   cannot be conflated by a later reader.
6. **This note must not appear among the acceptance arms** and must not be cited in the PR body as proof. Say so
   inside the note itself.

**Files** — Writes `notes/ci-observation-3136.md` (out-of-map).

**Validation** — first line disclaims evidentiary status; head SHA present; `11/18` present and labelled
non-discriminating; per-node outcomes separate from the job aggregate; the note is absent from the
acceptance-arm list.

---

### Subtask T042 — file the carried gaps, each with a number and one with its magnitude

**Purpose**

`C-009` is **file-don't-absorb**. A gap described in a plan and ticketed nowhere is re-derived from scratch by
the next investigator — or, worse, read as already closed. Every filing goes into a register in
`notes/constraint-enforcement-3136.md`, and **every register row is verified by `gh issue view <n>`**. A bare
issue number is not a disposition.

> **⚠ AMENDED 2026-08-07 by the orchestrator — do NOT run `gh issue create`.**
>
> This subtask was written to file GitHub issues. **The operator has barred issue creation for this
> programme** (2026-08-06): *"we are here to deliver features and fix bugs not keep creating residuals,
> keep issues in a ledger we will go over after a mission has been driven to PR then we will assess if
> anything can be folded into an existing mission (if it couldn't be folded in during dev) before
> creating new issues."* Reading `gh issue view` remains permitted; **creating** does not.
>
> **`C-009` is satisfied, not waived.** `C-009` is *file-don't-absorb* — its purpose is that a gap is
> **durably recorded outside the prose that found it**, so the next investigator neither re-derives it
> nor reads it as closed. `residual-ledger.md` discharges exactly that, and it travels with the PR in
> the governance dossier. What changes is the register's **address**, not its existence.
>
> **Substitute for every filing below:** append an `RL-###` entry to
> `kitty-specs/sync-sleep-count-3136-01KZ9B5A/residual-ledger.md` carrying the same content the issue
> body would have carried — found-by, severity, the measurement with its predicate, and the
> fold-or-file recommendation. Then quote the `RL-###` id and its heading line as the verification, in
> place of the `gh issue view` quote. **Do not invent, guess, or reserve an issue number.** The ledger
> is reviewed for folding after this mission reaches PR; issues are opened then, by the operator's
> decision, for whatever could not be folded.
>
> Everything else in this subtask — the predicates, the `N-in / M-out` discipline, the struck "46",
> the `C-006` register — stands unchanged and is the reason this subtask still has teeth.

**Filing 1 — seam displacement. This one needs its magnitude, and the plan omits it.** A test reassigns
`mock.side_effect` **in-body**, displacing a recorder while `call_count` keeps incrementing. The shipped R-2
predicate reads the `patch()` call's **arguments**, so in-body reassignment is structurally outside it. The
predecessor's `grep -rn 'sleep\.side_effect\s*=' tests/sync/` → 0 hits closed a *different* hazard and is
retired as evidence — it matches attribute assignment only.

**State the magnitude — as `N-in / M-out` under a named predicate, NEVER as a headline number.** The gap
touches sites under `tests/sync/` on a sleep / monotonic / run / post / randbelow recorder, **including
`test_saas_client.py:804` inside a census node**. The plan states the gap without its size and a successor
cannot scope a category — but **no single figure is reproducible here**: the commands below print **52**,
this WP's own Risk 6 records **45 / 46 / 52** across three defensible predicates, and **no predicate in this
prompt yields 46**. An earlier revision headlined "46 sites"; it is struck. **Report `N` in, `M` out, and
state the predicate that produced `M`** — then a successor can re-derive it or argue with it. A bare
magnitude with no predicate is not a measurement:

```bash
# N in — every in-body `.side_effect =` reassignment under tests/sync/
grep -rnE '[A-Za-z_][A-Za-z0-9_.]*\.side_effect[[:space:]]*=' tests/sync/ | grep -vE 'side_effect=' | wc -l
# M out — narrowed to sleep/monotonic/run/post/randbelow recorders
grep -rnE '[A-Za-z_][A-Za-z0-9_.]*\.side_effect[[:space:]]*=' tests/sync/ | grep -vE 'side_effect=' \
  | grep -iE '(sleep|monotonic|run|post|randbelow)' | wc -l
```

Report **N in, M out, and why the N−M dropped** (`mock_http.request`, `mock_force_refresh` and similar non-clock
recorders). Calibrated this session: **116 in-body reassignments total**; the two commands above print **52**;
an `_run`-anchored name filter prints **45**. The band is real and it is a definitional choice — **pin the
predicate you used, print it beside the number, and give a per-file breakdown.** The issue body carries the
predicate, not just the count; a successor who cannot reproduce your `M` will re-derive the category from
scratch. Open `test_saas_client.py:804` and confirm it reads `mock_monotonic.side_effect = [0.0, 301.0]`
before citing it. The issue must carry a **reproduction shape** (a minimal test reassigning `side_effect`
mid-body while `call_count` is read), the reason the old grep was inert, and the reason the new predicate does
not reach it — else it will be re-derived as "already closed by R-2". Building it into the gate is **rejected**:
it needs intra-function dataflow and would push the read-side matcher past the complexity ceiling of 15.

**Filing 2 — the `batch.py` residue, filed with the CORRECT fix shape.** R2's ticket text said the residue
"requires alias seams in four more product modules". That is **false for `batch.py`**, and filing it that way
institutionalises a redundant second seam in a module that already has a working one, against `FR-011`. Measured
and opened this session:

- `src/specify_cli/sync/batch.py:626-641` already exposes `run_final_sync_with_retries(sync_operation, *, sleep:
  Callable[[float], None] | None = None)`, with `sleeper = time.sleep if sleep is None else sleep` at `:641`.
- The `sleeper` parameter is threaded through the helper signatures at `:667-700`; the single actual
  `sleeper(...)` call is `:674`.
- **`src/specify_cli/sync/background.py:467` is the ONE caller that does not thread it** — it reads
  `run_final_sync_with_retries(self._perform_sync)`, with no `sleep=`.
- Three tests in the frozen file already use the seam: `test_final_sync_diagnostics.py:180`, `:207`, `:239`, all
  `sleep=sleeps.append`.

**So the filing must say: thread the existing keyword argument at `background.py:467` — not: add an alias
seam.** File the other frozen product modules separately, one issue each, naming their `file:line` sets and the
seam shape that closes them: `sync/git_metadata.py`, `sync/body_transport.py`, and the `asyncio` reach under
`test_runtime.py`.

**Filing 3 — the exact-list clock stimuli, a `StopIteration` exposure outside the predicate.**
`test_git_metadata.py:218`, `:242`, `:274`, `:522` and `test_saas_client.py:804` are **not** count or equality
assertions — they are exact-list `side_effect` stimuli a concurrent caller exhausts into `StopIteration`. The
R-2 predicate requires the mock be "read by a count or equality assertion", so it **does not reach them**.
`:804` closes incidentally under R-1 because `_monotonic` becomes module-local; the four in
`test_git_metadata.py` do not. Opened this session — the shape difference matters: `:218` is
`mock_time.side_effect = [1.0, 2.0]`, `:242` `[1.0, 4.0]`, `:274` `[1.0, 2.99]` (all **in-body reassignments**,
so they overlap Filing 1), while `:522` is `with patch("specify_cli.sync.git_metadata.time.monotonic",
side_effect=[1.0, 10.0]):` — a **kwarg** form, so it does not. File it as a **named sub-class of the mechanism
with its own read-side form**, so a successor does not read `corruptible_assertions: 0` as covering it.

**Filing 4 — the `[R2-open]` residue the gate ships flagging.** A direct `time.sleep` added to a *different*
module in the same cone is outside arm 4's scope, which is `saas_client.py` only. File it with **widening the
seam check to all of `src/specify_cli/`** as the named follow-up, and include the `[R2-open]` rows the shipped
gate actually flags at WP05's final commit — quote the gate's own output, not the plan's prediction.

**Filing 5 — the newly-found instances with no ticket.** The charter's Pre-existing Failure Reporting Rule
requires an issue before a red counts as accepted baseline. `#3136` covers the sleep-count nodes; these do not
have one: `requests.post` (×9), `asyncio.run_coroutine_threadsafe`, and `test_git_metadata.py:398` (opened:
`assert mock_run.call_args.kwargs.get("cwd") == tmp_path`).

**`C-006` — the register of what is NOT re-opened.** In the same section, record that the following are
**settled and must not be re-litigated**: the mechanism, the named producer (`subprocess.Popen._wait`'s capped
doubling loop), the psutil structural exclusion, and the `restart.py:147` / `daemon.py:1382` falsifications.
What *is* re-opened is exactly the filings above, each by issue number. Two code facts may be re-verified and
nothing else: `saas_client.py:19` and the patch-decorator census.

**Files** — Writes the filings register in `notes/constraint-enforcement-3136.md` (out-of-map) plus tracker
issues.

**Validation** — every filing has an issue number, each verified by `gh issue view <n> --json body,title` with
the verification quoted; Filing 1 carries N-in/M-out plus its predicate; Filing 2's body says "thread the
existing parameter" and **not** "alias seam"; the `C-006` register names all four settled items.

---

### Subtask T043 — release the `C-001` `tests/sync` window, handshake closed

**Purpose**

WP01 **acquired** the window; WP07 **releases** it, so it spans the whole critical path `WP01 → WP02 → WP05 →
WP07`. An unreleased window is the single most likely place for a successor mission to stall, and **a WP that
reports a `tests/sync` result with no corresponding acquisition record has not produced evidence.**

**Steps**

1. Take every remaining `tests/sync` arm **before** releasing. After release this WP may not run `tests/sync`
   again.
2. Append the RELEASE half to `notes/c001-window-3136.md`, closing the handshake with all three fields:
   **holder** (WP01 acquired on the mission's behalf), **acquired-at** (copied verbatim from WP01's ACQUIRE
   record, not re-derived), **released-at** (ISO-8601). **WP01's ACQUIRE half is visible from this
   workspace**: `notes/` is an out-of-map planning write on the mission's primary partition, not a
   lane-local file, so `kitty-specs/sync-sleep-count-3136-01KZ9B5A/notes/c001-window-3136.md` is readable
   here and you copy `acquired-at` character-for-character out of it rather than reconstructing it. If the
   file is not present, **stop** — a missing ACQUIRE record means the handshake was never opened, which is a
   finding, not a reason to invent a timestamp.
3. Also record the sibling mission checked against at acquisition and the arms actually taken inside the window
   (WP02's guard determinism arms; WP07's T037 behaviour half if run). WP03–WP06 took none — they are static AST
   readers that never collect `tests/sync`, which is also why the gate does not violate `C-001`. Confirm no
   `tests/cli` run overlapped the window at any point.

**Files** — Writes `notes/c001-window-3136.md` (out-of-map, RELEASE half only; do not rewrite WP01's ACQUIRE
half).

**Validation** — holder / acquired-at (character-for-character against WP01's record) / released-at present;
arms-taken list present; an explicit statement that no `tests/cli` run overlapped.

---

## Definition of Done

Record the evidence in the WP notes **before** marking anything done:

```bash
spec-kitty agent tasks mark-status T037 --status done --mission sync-sleep-count-3136-01KZ9B5A
spec-kitty agent tasks mark-status T038 T039 --status done --mission sync-sleep-count-3136-01KZ9B5A
spec-kitty agent tasks mark-status T040 T041 T042 T043 --status done --mission sync-sleep-count-3136-01KZ9B5A
```

| Subtask | Evidence that must exist in `notes/` before `mark-status` |
|---|---|
| T037 | `C-008` empty half **and** non-empty loud sibling from one invocation, with byte counts; `C-004` full diff with a per-hunk verdict and zero out-of-region lines; `C-002` notes-file `test -s` + line count + twin grep ≥ 1 + `ruff format` count `0` |
| T038 | `All checks passed!` + `EXIT=0` quoted verbatim; added-suppression count `0` **with its control**; the `ruff.toml` / `pyproject.toml` diff as text plus the two-clause `per-file-ignores` / `exclude` statement |
| T039 | `EXIT=0` and the `N passed` line quoted verbatim from the redirected file; covered prose surfaces enumerated |
| T040 | PR number + head SHA + `isDraft: true`; `git log --oneline` excerpt showing guard-before-alias |
| T041 | `ci-observation-3136.md` whose **first line** disclaims evidentiary status, carrying the head SHA, `11/18` labelled non-discriminating, and per-node outcomes separate from the job aggregate |
| T042 | **(amended 2026-08-07 — ledger, not issues)** Each filing's `RL-###` id **and** its heading line quoted from `residual-ledger.md`; Filing 1's N-in/M-out derivation; Filing 2's "thread the existing parameter" wording; the `C-006` not-re-opened register. **`gh issue create` is barred — an invented or reserved issue number fails this item outright.** |
| T043 | `c001-window-3136.md` with holder / acquired-at / released-at and the arms-taken list |

**NOT done if:** the PR has been un-drafted or merged; the CI observation appears among the acceptance arms or
any artifact says "CI is green now"; **a filing exists as prose without an `RL-###` id in
`residual-ledger.md`** (amended 2026-08-07 — this previously read *"without an issue number"*); the `C-008`
loud sibling is empty; the `C-001` window is still open.

---

## Risks

1. **The silent-diff trap (`C-008`).** `git diff … → no output` is produced by a bad ref, a wrong working
   directory and a mistyped path just as readily as by an unchanged file. *Mitigation*: the loud sibling from
   the **same invocation**, with byte counts for both halves. If the loud half is empty, nothing about the
   silent half has been established.
2. **The empty-notes trap (`C-002`).** `grep -rc 'ruff format' <notes>` = 0 is satisfied by an absent or empty
   file. *Mitigation*: the `command -v` transcript is written into that file first, making it non-empty by
   construction; the twin grep fails loudly if it is not.
3. **The config escape hatch (`SC-012`).** Green lint plus zero inline `# noqa` is fully compatible with an
   added `per-file-ignores` entry. *Mitigation*: diff-shaped check, reported as diff text.
4. **Reading a green shard as proof** — the largest reviewer-side risk here. A clean `fast-tests-sync` is the
   **pre-fix** outcome ~39% of the time. *Mitigation*: the note's first line, the `11/18` label, exclusion from
   the acceptance arms, and separating "the three targeted nodes went green" from "the job went green" — the
   second unachievable while `tests/regression`'s inverted-red markers and open P0s exist.
5. **Filing a gap with the wrong fix shape.** Filing `batch.py` as "needs an alias seam" produces a redundant
   second seam in a module that already exposes `sleep=`, against `FR-011`. *Mitigation*: the
   `background.py:467` / `batch.py:626-641` / `:674` facts are opened and quoted in the issue body.
6. **A magnitude that is probe-dependent.** A headline "46 sites" means nothing without the predicate that
   produced it — and **no predicate in this prompt yields 46**: T042's own commands print **52**, an
   `_run`-anchored filter prints **45**, and the unfiltered in-body total is **116**. *Mitigation*: the
   headline number is struck from T042; the filing carries N-in, M-out, the predicate that produced M, and
   the per-file breakdown. Any bare magnitude in the issue body is a defect.
7. **A bare `uv run` destroying the toolchain mid-transcript** — three occurrences already, one immediately
   after the warning was committed. *Mitigation*: the two sanctioned forms only, with `command -v` and the
   recovery command in the notes.
8. **`C-003` contamination.** The `#3130` / `#3193` leak `ERROR`s are out of scope; counting them as this
   mission's failures — or "fixing" them — is a defect. *Mitigation*: `^ERROR tests/` not `^ERROR `; `-ra` not
   `-rf`; classify before attributing.

---

## Reviewer Guidance

You are verifying **measurement quality**, not code, in this order.

1. **Check the controls before the results.** For every `0` in the notes, find the control showing the probe was
   wired up. A `0` with no control is not a finding. Specifically: is the `C-008` loud sibling non-empty? Does
   the added-suppression grep have a positive control?
2. **Open two cited `file:line`s at random** and confirm they say what the notes claim — this programme has had
   docstring prose cited as a pinning assertion through eight references, and a fixture claimed to reach a site
   it structurally cannot. Candidates: `src/specify_cli/sync/background.py:467` (must be
   `run_final_sync_with_retries(self._perform_sync)`, no `sleep=`) and
   `tests/sync/tracker/test_saas_client.py:804` (`mock_monotonic.side_effect = [0.0, 301.0]`).
3. **Reject any claim that the board is green.** Verify the note separates the three targeted
   `tests/sync/tracker/` nodes from the `fast-tests-sync` aggregate, and that it does not appear among the
   acceptance arms.
4. **Verify each filing by number, not by description.** Run `gh issue view <n>` yourself (after `unset
   GITHUB_TOKEN`). Check Filing 2's body for "thread the existing parameter" and confirm it does **not** propose
   an alias seam; check Filing 1 carries a reproduction shape and its N-in/M-out.
5. **Confirm the four owned files are unchanged**: `git diff 98198e980 -- .github/workflows/ci-quality.yml
   ruff.toml pyproject.toml tests/architectural/test_no_legacy_terminology.py` should be empty. That emptiness
   **is** the deliverable — but only alongside a loud sibling proving the ref resolves.
6. **Confirm the PR is still a draft** (`gh pr view <n> --json isDraft` → `true`) and that no merge occurred.
   Un-drafting needs the operator's explicit go; merging is the operator's action.
7. **Confirm the `C-001` handshake is closed** — holder, acquired-at (matching WP01's record exactly),
   released-at — with an arms-taken list consistent with what the notes report having run.
8. **Check run verdicts**: a killed or timed-out run must be recorded as *neither a pass nor a failure*; calling
   one a pass or a failure is a finding.
