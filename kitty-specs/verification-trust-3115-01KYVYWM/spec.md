# Mission Specification: Verification Trust — make our own verification honest

**Mission Branch**: `kitty/mission-verification-trust-3115-01KYVYWM`
**Created**: 2026-07-31
**Revised**: 2026-07-31 (post-specify adversarial squad — four lenses; see
`notes/post-spec-squad-findings.md`. The CLI half of the first issue is re-scoped from a
global-state hunt to a **measured console render-width defect**; the base commit is corrected from
the stale `9189cf2b36` to `bb2020fea9`.)
**Revised again**: 2026-07-31 (post-**plan** adversarial squad — three lenses; see
`notes/post-plan-squad-findings.md`. **The `_isolated_home` convergence requirement is CUT from this mission by operator decision** — see
the boxed note below. **C-005 is STRUCK.** The mutant-plugin contract
in C-003 is corrected: `PYTHONPATH` alone does not load a plugin, and a plugin fixture loses to a
conftest fixture.)
**Status**: Draft
**Base commit**: `bb2020fea9` — every red-first demonstration, every baseline and every "before"
measurement in this spec is taken at this commit, not at `9189cf2b36` (see NFR-009).

**Issues in scope**: #3115 (shard-parallel test-isolation flakiness, with the folded `pytest.ini`
timeout gap) and #3113 (egress-boundary guard misses all-positional transport calls). #3030 is
carried as a third matrix row because FR-009 below is the first thing that can answer its landing
pass's own self-declared-unproven claim. Both scoped issues follow up `#3098` / `#3030`.

---

> ### ⚠ SCOPE CUT — the `_isolated_home` convergence is **not** in this mission
>
> **Cut by operator decision after the post-plan adversarial squad, 2026-07-31.** This is a
> deliberate removal, not an omission. its record is retained in the note below so its
> number is never reused and so nothing downstream reads the gap as an accident. The implementing
> work package (WP08) is likewise removed from `plan.md`, which carries the same note.
>
> **Why.** All three lenses independently measured the 22 `_isolated_home` definitions and found a
> **name collision, not a duplicated seam**: seven incompatible fixture shapes; three victim files
> that pin **no home at all** (and those three are the `#3115` victims, so a root owner pinning
> `SPEC_KITTY_HOME` would change behaviour in exactly the files FR-002/FR-003 just fixed);
> contradictory `SPEC_KITTY_ENABLE_SAAS_SYNC` policies documented as load-bearing **in opposite
> words at their own sites** (`tests/sync/test_body_drain_consent_3030.py:51-54`, *"leaving it set
> here keeps these tests honest about what they prove"*, versus
> `tests/specify_cli/sync/test_local_commit_consent_3030.py:78-82`, *"deleted rather than set …
> leaving the developer's own export in place would prove nothing either way"*); three different
> fixture return contracts (14 × `-> None`, 7 × `-> Iterator[None]`, 1 × `-> Path`); and one
> **class-method** fixture (`tests/specify_cli/identity/test_identity_value_faults_3030.py:294-297`,
> `def _isolated_home(self, …)`) that a root-conftest
> owner cannot replace without changing fixture resolution. The counted acceptance it specified
> was also the wrong instrument: collected counts do not move when a fixture *body* changes, so the
> acceptance was satisfiable by a deletion that made isolation strictly worse.
>
> **Where it went.** A follow-up issue against `Priivacy-ai/spec-kitty` carries it, inheriting the
> **measured equivalence-class evidence**, which lives in
> [`notes/post-plan-squad-findings.md`](notes/post-plan-squad-findings.md) ("The convergent finding
> — the convergence cut from scope"). The successor issue number is recorded on `#3115`'s matrix row at
> mission close. Nothing else in this mission depends on it: FR-009 is driven by the FR-001
> width falsifier, not by the seam.
>
> **What this cut does *not* license.** The three `COLUMNS` sets that WP02 was to hand to WP08 are
> **left in place** — measurement F2 shows they are *live* outside `TERM=dumb` (see FR-002). They
> are not reassigned to another work package.
> **Why the retired number is not written anywhere in this file.** The requirements sequence below
> jumps straight from FR-007 to FR-009. **That gap is this cut, and it is deliberate.** The number
> cannot be named here — not even struck through, not even in prose — because
> `parse_requirement_ids_from_spec_md` (`src/specify_cli/requirement_mapping.py:16,104-117`) scans
> the **entire document** for `\b(?:FR|NFR|C)-\d+\b` and treats every hit as a live functional
> requirement that `_validate_requirement_mapping`
> (`src/specify_cli/cli/commands/agent/mission_finalize.py:605-630`) then demands be mapped to a
> work package. The tooling has no concept of a cut requirement, so naming the number would have
> forced either a false mapping or a permanently red gate. **The number is named in full, with all
> its evidence, in [`notes/post-plan-squad-findings.md`](notes/post-plan-squad-findings.md) and in
> `plan.md`** — neither of which the gate parses. It is retired and deliberately not reused.
>
> **The full tombstone text.** The cut requirement previously occupied a row in the requirements table.
> That row is removed rather than struck through, because a struck row is still parsed as a live
> functional requirement by `_validate_requirement_mapping`
> (`src/specify_cli/cli/commands/agent/mission_finalize.py:605`), which requires every functional
> requirement id in the spec to map to a work package and has no concept of a cut one. Retaining
> the row would have forced a false mapping. **The number it held is retired and deliberately not
> reused**, so its absence from the sequence reads as a decision rather than an accident.
>
> Verbatim: **This requirement is removed from the mission by operator decision, taken 2026-07-31 after the post-plan adversarial squad. The number is retained, and deliberately not reused, so that its absence reads as a decision rather than an accident.** No work package implements it; WP08 is removed from `plan.md`; no `_isolated_home` definition is added, moved or removed by this mission. **What it said**: hoist 22 `_isolated_home` definitions across 22 files to a single root- or package-scoped owner, with a counted acceptance (22 before, M after). **Why it was cut**: three lenses independently measured the 22 and found a **name collision, not a duplicated seam** — seven incompatible shapes; three files pinning **no home at all**, and those three are the `#3115` victims, so a root owner pinning `SPEC_KITTY_HOME` would change behaviour in exactly the files FR-002/FR-003 fix; contradictory `SPEC_KITTY_ENABLE_SAAS_SYNC` policies documented as load-bearing in **opposite words** at their own sites (`tests/sync/test_body_drain_consent_3030.py:51-54` vs `tests/specify_cli/sync/test_local_commit_consent_3030.py:78-82`); three return contracts (14 `-> None`, 7 `-> Iterator[None]`, 1 `-> Path`); a **class-method** fixture (`tests/specify_cli/identity/test_identity_value_faults_3030.py:294-297`) a root conftest cannot replace without changing fixture resolution; five callers of `reset_coalesce_strategy()`, a constraint this spec never named; and a counted acceptance that is the **wrong instrument** — collected counts do not move when a fixture *body* changes, so the acceptance was satisfiable by a deletion that made isolation strictly worse. The red-first clause was also internally contradictory: a test asserting "defined at most once" cannot pass at any M > 1, which the plan explicitly allowed. **Where it went**: a follow-up issue against `Priivacy-ai/spec-kitty`, inheriting the measured equivalence-class evidence in `notes/post-plan-squad-findings.md`; the successor number is recorded on `#3115`'s matrix row at mission close. **Nothing depends on it**: FR-009 is driven by the FR-001 width falsifier, not by the seam.
>

## Problem

**Our own verification lies to us.** Four defects, one theme: in each case the mechanism that is
supposed to tell us whether the code is correct returns an answer that is not about the code.

- **`#3115`, CLI half** — a suite that is green in isolation and red on CI, whose red text is a
  *production-shaped assertion* (`<uuid> is in the journal but ... did not name it`) rather than a
  harness error. **Measured cause: the console renders at 80 columns, the uuid folds across two
  lines, and a substring assertion stops matching.** The journal is populated and the command is
  correct; the *rendering surface* is what differs between a green run and a red one.
- **`#3115`, sync half** — one test whose failure has a separately-verified mechanism
  (`AssertionError: Expected 'sleep' to be called once. Called <n> times.`), where a `@patch` of
  `saas_client.time.sleep` reaches the **stdlib** module object and therefore counts sleeps made by
  any live thread in the worker.
- **`#3113`** — a guard whose job is to turn a new ungated sender into a red build, with a known
  evasion, and a bite-test that only exercises the one call shape its author had in mind. The
  guard's green covers less than it claims, and its own negative control cannot tell us so.
- **The `pytest.ini` timeout gap** — a suite that **hangs** where it should fail. A hang is not a
  measurement; it is the absence of one, wearing the appearance of a slow job.

The consequence is the reason this bundle is the critical path. **Every downstream verdict about
this codebase inherits this evidence** — including "the merged `#3030` consent fix is fine". The
`#3030` landing pass already demonstrates it: commit `578a659162` ("harden #3030 sync CLI tests
against cross-worker scope-cache pollution") states in its own message *"Could not force a live
reproduction of the reported empty-journal CI failure locally … this is defensive hardening of a
credible process-global per the maintainer's lead, not a confirmed-necessary fix."* That is an
honest commit and a correct piece of reporting — and it is also, by this repo's own standing rule,
**not a fix**: *a fix that cannot be shown to fail before it is applied is not a fix.*

The squad's measurement now says something sharper than "unproven". `4f8e4ca781` (on PR `#3098`'s
branch; the fold-merge landed the same content as `578a659162`) hardened the token-manager global,
CI stayed red on the same tests, **and the width mechanism explains why**: the reset was aimed at a
global that was never the cause. That is the misattribution this mission exists to stop producing.

### The measured cause of the CLI half — stated so it is not re-derived

Measured on base `bb2020fea9`, single file, single process, no xdist, no ordering plugin:

| Run | Environment | Count line |
|---|---|---|
| baseline | none | `4 passed in 54.45s` |
| falsifier | `TERM=dumb FORCE_COLOR=1` | `1 failed, 3 passed in 57.54s` (×3, deterministic) |
| control | falsifier `+ TTY_COMPATIBLE=0` | `4 passed in 52.78s` |
| discriminator | `TERM=dumb` alone | `4 passed` — so `FORCE_COLOR` is required |

The chain, each link readable in installed source (`rich` 15.0.0):

1. `rich.console.Console.is_terminal` returns `True` whenever `FORCE_COLOR` is set to a non-empty
   value, unless `TTY_COMPATIBLE` or `force_terminal` decides first.
2. `Console.is_dumb_terminal` is `is_terminal and TERM.lower() in ("dumb", "unknown")`.
3. `Console.size` returns `ConsoleDimensions(80, 25)` from the `if self.is_dumb_terminal:` branch,
   which sits **above** the `COLUMNS` read. The victim tests set `COLUMNS` to `220`/`240`
   (`tests/cli/commands/test_sync_status_per_project_3030.py:83`,
   `tests/cli/commands/test_sync_doctor_per_project_3030.py:72`, and the `240` case in
   `tests/specify_cli/cli/commands/charter/test_activation_layout.py:111`) and **it is never
   consulted**.
4. The `Project` column is `overflow="fold"` (`src/specify_cli/cli/commands/sync.py:1440`) — a
   deliberate choice, documented at `sync.py:1430-1436`, so a project identity is never ellipsized
   into a prefix the operator cannot pass to `sync purge`. At width 80 a 36-character uuid folds
   across two lines and **stops being a contiguous substring**, so
   `assert uuid in out` fails.

**Decisive evidence:** the local falsifier's assertion repr is **byte-identical to CI's**, 240
characters, for both victim files, and CI's own rendered `Queue` row measures exactly 80 characters.
That is measurement, not inference. **The journal is populated** — 14 events retained, all four rows
present, counts 7/4/2/1 — so the issue's *"reads an EMPTY journal"* premise is falsified.

Two corrections that constrain the remedy, both load-bearing:

- **Whitespace normalisation does not repair the assertion.** The fold puts the rest of the table
  row *between* the two uuid fragments, so no amount of newline-stripping or whitespace-collapsing
  rejoins them. "Flatten the output" is a forbidden remedy (C-009), and FR-004 exists to prove it
  rather than assert it.
- `SILENT` / `OPTED_OUT` pass at width 80 only **incidentally**, via an un-tabled warning paragraph
  that reprints the identity outside the folding table. `CONSENTED` has no such paragraph, which is
  why exactly one of three loop iterations fails, and always the first. A remedy that makes the
  other two "still pass" has demonstrated nothing.

### The principal known unknown — stated as a limit of what this mission verifies

**What makes rich's `is_terminal` true on the CI runner is unidentified.** The workflow sets no
`FORCE_COLOR`, no `TERM` and no `TTY_COMPATIBLE` (verified: zero hits across `.github/workflows/`).
`is_dumb_terminal` is the only surviving route to *exactly* 80 columns — the only explicit width
assignment anywhere in the tree is `tests/specify_cli/cli/commands/_help_snapshot.py`'s
monkeypatch-scoped `10_000` — but the trigger on the runner has not been named. Nothing was tested
under xdist.

**This is not in scope to chase (operator decision).** It is recorded here, and must be carried into
the PR's limits section, because it bounds the claim this mission can make: the mission proves that
a pinned render surface makes the assertions width-invariant and that the un-pinned surface
reproduces CI's exact failure text. It does **not** prove what set the runner's terminal state.

### Why this class is expensive out of proportion to its size

Cleared or leaked global state makes the system **refuse**, and a narrowed console makes it *look
like it refused*. Either way the tests that break are the ones asserting **success** — positive
controls — and the text they fail with reads as a domain verdict rather than a harness artefact. On
a consent codebase, `<uuid> is in the journal but doctor did not name it` reads as *"the report is
dropping projects"*, which sends the reader into `delivery/status_report.py` and `consent.py` after
a defect that is not there. The friction record has this shape four separate times now, from four
directions (a closed asyncio loop turning publishes into caught "send failed"; an exhausted
`time.monotonic` list making the consent chain refuse; `reset_adapters()` in a teardown; and now an
80-column console folding an identifier). It is the single most expensive misattribution shape this
codebase produces.

### One known-good instance of the *other* class — kept because the sync half needs it

`tests/specify_cli/invocation/test_propagator_consent_gate_3030.py`'s `wiring` fixture called
`reset_adapters()` in teardown, leaving the **process** with no consent resolver. Deterministic in
plain alphabetical order (`tests/specify_cli/invocation/` sorts before
`tests/specify_cli/saas_client/`); the `#3030` sweeps missed it only because they ran
`-p no:randomly` with a favourable root ordering. Fixed by *restoring* the default handlers rather
than clearing: **a fixture that mutates process-global state must restore what it found, and "reset
to empty" is only safe for state nothing outside the fixture reads — a registry is by definition not
that** (C-002). It is retained here as the **control case** for FR-006's harness: a diagnostic is
run against an answer you already know before it is trusted.

### What the deliverable is, and is not

The deliverable is **not** "make CI green once". A green shard proves only that this run's dynamic
worker assignment and this runner's terminal state were benign. The deliverable is five things,
each mapped to the FRs that own it:

| # | Deliverable | Owned by |
|---|---|---|
| 1 | A cheap, deterministic, committed reproducer for the CLI half | FR-001 |
| 2 | The render surface pinned **structurally**, at the conftest layer, plus a guard so a future test cannot reintroduce a narrow surface silently | FR-002, FR-003, FR-004 |
| 3 | The sync half diagnosed on its own evidence, and `578a659162`'s self-declared-unproven token-manager hardening resolved either way | FR-005, FR-006, FR-007, FR-009, FR-010 (**the convergence was cut — see the scope-cut note**) |
| 4 | The egress guard's negative control measured in *shapes*, and any tightening keyed on a structural property rather than an author-chosen word | FR-013 … FR-015 |
| 5 | A non-terminating loop that reds by name and by count instead of burning the job's wall clock | FR-016 … FR-018 |

### Critical path — the dependency chain, stated forwards

The post-specify squad found the previous version of this chain stated backwards (the reproducer
was listed as an input to the search that produces it). Restated:

- **CLI half**: **FR-001** (falsifier: two environment variables, one file, one process) →
  **FR-002** (conftest render-surface seam) → **FR-003** (width guard) → **FR-004** (the forbidden
  remedy proved forbidden). FR-001 is now cheap enough that nothing downstream is hostage to it.
- **Sync half**: **FR-006** (narrowed inventory of the `tests/sync/` cone — needs no culprit and
  survives a failed hunt) → **FR-005** (attribution for the `sleep`-count test) → **FR-007**
  (guard, scoped to FR-006's inventory, **not** to FR-005's answer) → **FR-009**
  (token-manager verdict) → **FR-011** (shard proof). **FR-010** (stall policy) is the exit valve
  for this leg and blocks nothing else.
- **FR-009 is on the critical path** because its discriminating case needs FR-002's pinned width, and
  because — with the convergence cut — FR-009 is now the package that both *measures* the token-manager reset
  and *applies* the resulting docstring at the five `578a659162` sites. Nothing else is live in those
  files.
- **The convergence is cut** (see the scope-cut note above). It is on no chain and blocks nothing.
- **`#3113`** (FR-013 → FR-014 → FR-015) and the **timeout gap** (FR-016 → FR-017 → FR-018) are
  independent of both halves of `#3115` and of each other.

### Operator decisions recorded (scope additions and refusals)

1. **Re-scope the `#3115` CLI half to the measured cause.** The enumerated pairwise polluter search
   across both shard cones was offered and **declined** — the null result it would produce is not
   worth the wall-clock now that the cause is measured.
2. **Keep a narrowed isolation requirement for the sync half.** It is a genuinely different
   mechanism with its own verified explanation.
3. **Do not chase the `is_terminal` trigger on the runner.** Recorded above as the mission's
   principal known unknown and carried into the PR's limits section.
4. **The timeout work rides `#3115`'s matrix row**, with `evidence_ref` naming FR-016 … FR-018. No
   synthetic issue row is invented for it.
5. **Cut the `_isolated_home` convergence from this mission** and file a follow-up issue
   carrying the measured equivalence-class evidence. Taken after the **post-plan** squad, on three
   independent lenses' converging measurement that the 22 fixtures are a name collision rather than
   a duplicated seam. See the scope-cut note above and
   `notes/post-plan-squad-findings.md`.
6. **Strike C-005.** `pytest-randomly` is not installed at `bb2020fea9`, so C-005 forbade a flag that
   is already a no-op and made FR-001's determinism criterion trivially satisfiable — green for the
   wrong reason, in the mission built to eliminate that. Tombstoned below; FR-001 gains a criterion
   that can fail.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The CLI shard failure can be made to happen on demand, in one command (Priority: P1)

A maintainer on their own machine sets two environment variables, runs one test file, and sees CI's
exact failure text, before any fix exists.

**Why this priority**: Everything else in the CLI half is unfalsifiable without it. `578a659162` is
the proof: a credible fix was written and shipped and nobody could say whether it did anything. This
story is what converted the rest of the CLI half from persuasion into measurement — and it is now
cheap enough that no other work waits on it.

**Independent Test**: On base commit `bb2020fea9`, run
`TERM=dumb FORCE_COLOR=1 pytest tests/cli/commands/test_sync_status_per_project_3030.py` with output
captured to a file; the count line reads `1 failed, 3 passed` (that file collects **4**) and the
failure text is ``<uuid> is in the journal but `status` did not name it``. With the seam in place the
identical command reads `4 passed`. Run independently against
`tests/cli/commands/test_sync_doctor_per_project_3030.py`, which collects **12**, so its own count
line is `1 failed, 11 passed` — **not** `1 failed, 3 passed`.

> **Planning-time correction (post-plan remediation, not a squad finding).** The `1 failed, 3 passed`
> / `4 passed` figures recorded throughout the earlier draft were attributed to the *doctor* file.
> Re-measured with `pytest --collect-only -q` on a tree level with `bb2020fea9`:
> `test_sync_status_per_project_3030.py` collects **4**, `test_sync_doctor_per_project_3030.py`
> collects **12** (unchanged under `-m "fast and not windows_ci"`). The four-test count line belongs
> to the **status** file. FR-001 therefore requires each file's **collected count** to be stated
> beside its own count line (NFR-008); a count line that does not reconcile against the collected
> count is not evidence.

**Acceptance Scenarios**:

1. **Given** the base commit and a clean checkout, **When** the reproducer runs, **Then** at least
   one of the affected tests fails with the **discriminating** assertion text —
   the per-file text above — and **not** a `TypeError`,
   collection error, fixture error or empty output file.
2. **Given** the same command, **When** it is run three times in a row, **Then** it fails all three
   times, on the same node-id, with the **same assertion text byte-for-byte** and the **same
   collected count**, all three quoted. **This clause alone cannot fail** — `pytest-randomly` is not
   installed at `bb2020fea9` (`importlib.util.find_spec("pytest_randomly")` → `None`; absent from
   `pyproject.toml:102-113` and from every workflow), so nothing randomises order and repetition is
   trivially stable. **The falsifiable criterion is scenario 2b.**
2b. **Given** the reproducer, **When** the failing case is selected **alone by node-id**
   (`TERM=dumb FORCE_COLOR=1 pytest '<file>::<node-id>'`), **Then** it still reds with the same
   assertion text and the run's collected count is **1**. A red that only appears when the file's
   siblings run first is order-dependent, falsifies "two environment variables and one file", and
   fails C-004. This is the clause that can go the other way, and it is the one that carries the
   determinism claim.
3. **Given** the reproducer, **When** it is inspected, **Then** it uses **one process and one file**,
   depends on no xdist worker assignment (which is work-stealing and therefore not reproducible),
   and quotes the run's own `plugins:` header line so the ordering-plugin state is a **stated
   measurement** rather than an assumption (C-005 is struck; see the Constraints table).
4. **Given** the fix applied, **When** the reproducer runs unchanged, **Then** the `N passed` line
   is quoted as the evidence — never the exit code of a pipeline.
5. **Given** the reproducer, **When** anyone proposes `Queue 0 event(s)` as the red's signature,
   **Then** it is rejected: that row is rendered unconditionally from `OfflineQueue().size()`
   (`sync.py:5182-5185`) and these tests seed the journal, never the offline queue, so the string
   appears on the **green** path too.

---

### User Story 2 - The render surface is pinned, and a narrow one cannot come back silently (Priority: P1)

The tests stop asking the ambient environment how wide the terminal is. A single conftest seam pins
the surface, and a guard reds if any live `CliConsole` is narrower than the longest identifier a
test asserts on.

**Why this priority**: `COLUMNS` is not a fix — it is the thing that was already there and was never
read. A per-test width patch is the 23rd copy of a seam that should have one owner. The durable
shape is the one the repo already uses two doors down: `tests/conftest.py:307-329`
(`_plain_cli_console_seam` — set, yield, restore in `finally`).

**Independent Test**: With the seam in place, run the FR-001 falsifier: `4 passed`. Remove the seam
(one-line skip via a plugin, not a source edit), re-run: `1 failed`. Both directions, one commit.

**Acceptance Scenarios**:

1. **Given** the seam, **When** it is read, **Then** it pins the render surface **explicitly** —
   both `width` and `height`, or `TTY_COMPATIBLE=0`, or `force_terminal=False` — and it does
   **not** set `COLUMNS`.
2. **Given** `rich.console.Console.size`, **When** the seam's shape is justified, **Then** the
   justification cites the measured trap: setting `width` **alone** does not work, because the
   explicit-size early return requires `self._width is not None and self._height is not None`, so a
   width-only console still falls into the `is_dumb_terminal` branch and returns `(80, 25)`.
   Measured under `TERM=dumb FORCE_COLOR=1 COLUMNS=220`: no width → `(80, 25)`; `width=220` alone →
   `(80, 25)`; `width=220, height=50` → `(220, 50)`; `TTY_COMPATIBLE=0` → `(220, 25)`.
3. **Given** the seam, **When** the test window ends, **Then** it restores what it found in a
   `finally`, per C-002 and the `_plain_cli_console_seam` precedent.
4. **Given** the golden `--help` fixtures, **When** the seam lands, **Then** they are unaffected or
   deliberately reconciled: `CliConsole.set_plain`'s docstring states that width and wrapping are
   left to Rich's env detection *because* those fixtures depend on `COLUMNS`, and
   `tests/specify_cli/cli/commands/_help_snapshot.py` already pins its own console independently.
5. **Given** the width guard, **When** a future test constructs a `CliConsole` narrower than the
   longest identifier under assertion, **Then** the guard reds naming that console and that width —
   it does not widen anything (H8: the guard **detects and fails; it does not repair**).

---

### User Story 3 - The `sleep`-count failure is diagnosed on its own evidence (Priority: P1)

The one sync-cone failure is investigated as a separate defect with a separately-verified mechanism.
(The seam-convergence half of this story — "hoisted to one owner instead of copied into a 23rd file"
— was **cut with the convergence**; see the scope-cut note. Acceptance scenario 5 is struck accordingly.)

**Why this priority**: The issue asserts a *"common shape"* between this failure and the CLI ones.
The CLI ones now have a measured cause that has nothing to do with globals, so the "common shape"
sentence is falsified as an explanation and must not be inherited as a finding. This test's own
mechanism is documented in the victim file already (`tests/sync/tracker/test_saas_client.py:36-46`).

**Independent Test**: Enumerate live threads at the start and end of
`TestRetryBehaviors::test_429_respects_retry_after` in a session that also runs a daemon-spawning
sibling file; assert the count and the recorded `sleep` call count move together, or report that
they do not.

**Acceptance Scenarios**:

1. **Given** `@patch("specify_cli.tracker.saas_client.time.sleep")`, **When** the patch target is
   resolved, **Then** the attribution states that `saas_client.py:19` is a bare `import time`, so the
   patch lands on the **stdlib `time` module object**, is process-wide, and its call recorder counts
   `time.sleep` calls from **any live thread in the worker** during the patch window.
2. **Given** the hypothesis "a leaked module-global retry/backoff value", **When** it is evaluated,
   **Then** it is recorded as **structurally impossible** and not funded: `saas_client.py` has
   exactly two module-level names, `_SESSION_EXPIRED_MESSAGE` (`:36`) and `_UNAUTHENTICATED_CATEGORY`
   (`:39`), and the backoff is local variables inside `_poll_operation`
   (`delay`/`cap`/`total_timeout`, `:466-468`).
3. **Given** the leaked-thread hypothesis, **When** a candidate source is named, **Then** it is
   `src/specify_cli/sync/daemon.py` — threads started at `:587`, `:767` and `:828`, sleep loops at
   `:584` and `:1382` — and **not** `SaaSTrackerClient._poll_operation`, which nothing in the tree
   threads.
4. **Given** the investigation, **Then** "the two symptoms have two different causes" is an
   explicitly permitted and, on the present evidence, expected outcome. Adopting the issue's
   *"common shape"* sentence as the finding is explicitly **not** permitted.
5. ~~**Given** the `_isolated_home` fixture, **When** the isolation seam is changed, **Then** the
   change lands in **one** owner and the count of definitions is reported before and after.~~
   **STRUCK — cut with the convergence** (operator decision, post-plan squad). No work package in this
   mission changes the isolation seam, and no `_isolated_home` definition is added, moved or
   removed. The follow-up issue carries it.

---

### User Story 4 - The egress guard's negative control tests the shape nobody thought of (Priority: P1)

The boundary guard states the positional-argument evasion as a limit, its bite-test exercises the
positional form **twice** — once with a URL-ish parameter name and once without — and any tightening
of the matcher is keyed on structure, not on a word the author happened to choose.

**Why this priority**: This guard is what turns a new ungated sender into a red build. The deeper
problem is not the hole, it is that **a negative control which only tests the shape you thought of
is not a negative control.** It reports "the scanner is not blind" while being blind — and the
squad found the mandated bite-test would have certified exactly that: `poster(url, body, hdrs)`
passes only because the parameter is *literally named* `url`, which is already in `_URL_ARG_NAMES`
(`test_egress_consent_boundary.py:197`) and which `_attr_tail` returns verbatim for a bare `Name`
(`:266-272`). `#3113`'s own defect, reproduced inside its own fix.

**Independent Test**: Add two positional-form source strings to the scanner's shape-coverage
parametrisation. On the current matcher **both** fail (the scanner returns no sink). After the
change, the **second** — the one whose first argument is *not* a `_URL_ARG_NAMES` identifier — is
the adoption gate.

**Acceptance Scenarios**:

1. **Given** `def go(poster, url, body, hdrs): return poster(url, body, hdrs)` and
   `def relay(post, u, payload, meta): return post(u, payload, meta)`, **When** the scanner runs on
   them **before** the change, **Then** it returns **no** sink for either — the hole, demonstrated
   rather than argued.
2. **Given** a proposed tightening, **When** its rule is read, **Then** it is decidable **without
   consulting any author-chosen identifier**: the callee is a bare `ast.Name` whose `id` resolves to
   a **parameter of the enclosing `FunctionDef`** — an injected transport. `_classify` already has
   the bare-`Name` branch to hang it on (`:316`).
3. **Given** a tightening that *cannot* be expressed without consulting an author-chosen identifier
   (e.g. "≥3 positional args whose first looks like a URL"), **Then** it is **rejected regardless of
   its false-positive count**. C-006 forbids the guard being *callee*-name-shaped; keying on an
   *argument* name is the same failure in a different subject.
4. **Given** the structural tightening, **When** it is measured over the whole of `src/`, **Then**
   sites, files and false positives are reported **before** adoption, and the sites it newly adds
   are reported **separately** from the pre-existing ones. A zero delta is written down as *"the only
   demonstrated bite is the synthetic case"* rather than passing as a success.
5. **Given** the guard's module docstring, **When** the completeness-limits list is read, **Then**
   the all-positional / no-`headers=` transport call appears as its own numbered limit (the list
   currently runs 1-7 and ends at multi-sink-per-file), in the same voice as its neighbours.
6. **Given** the changed guard, **When** the whole architectural suite runs, **Then** the sink and
   allowlist counts in `tests/architectural/_baselines.yaml` are reconciled deliberately — a changed
   count is either an intended ratchet move with a written justification or a regression.

---

### User Story 5 - A non-terminating loop fails instead of hanging (Priority: P2)

A drain that never terminates produces a red naming the defect and the iteration count, not a job
that burns its wall clock and reports a timeout.

**Why this priority**: Measured during `#3030`: a mutant produced **1,603 retried empty selections**
and the suite reported nothing until the run was forced with `--timeout-method=signal`. The first
attempt to measure it was itself killed mid-session, producing no summary and therefore no verdict.
**A pin whose failure mode is a hang is not a pin.**

**Independent Test**: Load a pytest plugin (via `PYTHONPATH`, per C-003) that makes
`_run_dispatch_batches` fail to make progress; run the two loop-driving tests; assert each ends with
an assertion naming the recorded batch count, and **not** with `Failed: Timeout`.

**Acceptance Scenarios**:

1. **Given** a deliberately non-terminating test, **When** the fast selection runs on the base
   commit, **Then** the session does not terminate on its own — the defect, demonstrated.
2. **Given** the same after the change, **Then** the session ends **and** the output contains a
   summary line naming the hanging test. A run that is killed with no summary does **not** satisfy
   this: it is the same "empty output is not a failure" trap one layer down.
3. **Given** the non-terminating-loop plugin mutant, **When** the loop-driving tests in
   `tests/delivery/test_dispatch_window_consent_3030.py` run under it, **Then** they red **on the
   counter, naming the count** — and specifically not on `Failed: Timeout (>Ns) from
   pytest-timeout`. A red whose text is the timeout means the counter did not bind.
4. **Given** the full fast selections after the change, **When** they run on CI, **Then** the
   regression clause enumerates **which jobs inherited the new default and which did not run at
   all**, with each job's collected count, and quotes the maximum observed per-test duration
   alongside the chosen value.

---

### User Story 6 - The `/tmp` root-walk artifact stops costing an hour per developer (Priority: P3)

A developer whose machine has a repo-root marker at or above `/tmp` gets a message naming the
offending directory, not a mysterious consent-gate failure.

**Why this priority**: Low severity, cheap, and squarely on the mission's theme — it is a *local
verification result that is about the machine rather than about the code*. The issue is emphatic
that production routing must not be changed for it.

**Independent Test**: Create a `.kittify/` (or `.git/`) directory at an ancestor of the pytest tmp
root, run the affected test, and assert it does not fail with a bare consent assertion but with a
message naming that ancestor.

**Acceptance Scenarios**:

1. **Given** an ancestor of `tmp_path` carrying a repo-root marker, **When**
   `test_unresolvable_routing_does_not_consent_to_sync` runs, **Then** the outcome names the
   ancestor path that resolved as a repo root, so the developer knows what to delete.
2. **Given** the same environment, **When** the suite runs, **Then** the invariant itself — *routing
   that cannot be determined denies* — is still pinned by a test that does **not** depend on the
   filesystem walk-up at all, so a hostile machine cannot silently remove coverage of the
   requirement.
3. **Given** a normal CI machine, **When** the suite runs, **Then** the walk-up test runs and
   passes; it is not skipped there.

---

### Edge Cases

- **`Queue 0 event(s)` is not a red.** It is rendered unconditionally from `OfflineQueue().size()`
  (`sync.py:5182-5185`); these tests seed the journal, never the offline queue, so it appears on the
  green path. Struck from every red-first clause and every success criterion in this spec.
- **Two of three loop iterations already pass at width 80.** `SILENT`/`OPTED_OUT` pass
  *incidentally*, via an un-tabled warning paragraph that reprints the identity outside the folding
  table; `CONSENTED` has no such paragraph. So "the other two still pass" is not evidence of
  anything, and a remedy is only demonstrated by the `CONSENTED` iteration.
- **Flattening the output looks like it should work and does not.** The fold interleaves the rest of
  the table row between the two uuid fragments. C-009 forbids it; FR-004 proves it.
- **The seam pins width but not height.** Rich's explicit-size early return needs both; a width-only
  console still returns `(80, 25)` on a dumb terminal. Measured, and the most likely way this fix
  ships broken and green.
- **The width guard itself renders nothing.** A guard that inspects zero consoles passes vacuously
  (NFR-008); it must report the number of consoles inspected and the longest asserted identifier it
  compared against — **and it must assert it saw the two *named* singletons**, because a non-zero
  inspected count is satisfiable by the three deliberately-sized specials alone.
- **The width pin overwrites the deliberately-sized consoles.** `CliConsole._instances` holds three
  specials — `list_cmd.py:26` (200), `glossary.py:46` (120), `docs.py:43` (120, documented as
  load-bearing at `docs.py:40-42`). A blanket walk breaks all three. Pin the singletons; exempt
  anything constructed with an explicit `width=`.
- **Two consoles are constructed inside functions**, `helpers.py:234` and `logging_bootstrap.py:92`,
  so they come into existence *after* a setup-time walk and are never pinned. This is a **stated
  gap**, named in the seam's docstring and in the guard's output — not something a non-zero inspected
  count is allowed to hide.
- **`COLUMNS` is dead on the failing path and live on the passing one.** Under `CliRunner` in the
  default environment `is_terminal` is False, the `is_dumb_terminal` early return does not fire, and
  `COLUMNS` **is** read — `test_activation_layout.py:111` passes `COLUMNS=240` and is live today. So
  the pinned width must be **≥ 240**, and the existing `COLUMNS` sets are **left alone**; "provably
  dead" was true only of the failing path.
- **The sync leak guard becomes the polluter** by snapshotting state in a way that instantiates it.
  Its positive control must include a run where nothing leaks and nothing is flagged.
- **A newly-added global timeout reds a legitimately slow unmarked test.** That is a finding about
  the value, not about the test; raise the value or mark the test, and record which. 46 tests carry
  `slow` (defined in `pytest.ini` as ">30 seconds") against about 15 `@pytest.mark.timeout` sites,
  and `testpaths = tests` means an `addopts` default caps **every** invocation of this ini.
- **The guard tightening changes the sink count** and the ratchet in `_baselines.yaml` fails in a
  *different file*. Expected; reconcile deliberately.
- **A `no tests ran` shard passes.** `fast-tests-cli` carries `|| test $? -eq 5`
  (`ci-quality.yml:1545`), so an empty collection is a green job. Any claim about a shard must quote
  the collected count.
- **A shard that never ran looks like a shard that passed.** `fast-tests-sync` is gated on
  `needs.changes.outputs.sync` (`ci-quality.yml:1101`) and was **skipped** on run `30622853036`. A
  test-only branch can get a green `fast-tests-cli` and no sync shard at all.

## Requirements *(mandatory)*

### Functional Requirements

| ID | Title | Requirement, red-first demonstration, and acceptance | Priority | Status |
|----|-------|------------------------------------------------------|----------|--------|
| FR-001 | A committed, documented reproducer for the `#3115` CLI failure | A reproducer is **committed to the repo** — `scripts/repro_3115_render_width.sh` plus a section in `docs/development/testing-parallel.md` — not described in a PR comment. **Red first**: on base `bb2020fea9`, `TERM=dumb FORCE_COLOR=1` over a **single victim file in a single process** (`tests/cli/commands/test_sync_doctor_per_project_3030.py`, and independently `tests/cli/commands/test_sync_status_per_project_3030.py`) exits non-zero with the **discriminating** assertion text — which differs between the two files and must be quoted **per file, verbatim from source**, never normalised: ``<uuid> is in the journal but `status` did not name it`` (backticks, `test_sync_status_per_project_3030.py:154`) and `<uuid> is in the journal but doctor did not name it` (**no delimiters at all**, `test_sync_doctor_per_project_3030.py:174`). A `TypeError`, a fixture error, a collection error or an **empty output file** do **not** satisfy this (five recorded ways a red lies; an empty output file is *no measurement*). `Queue 0 event(s)` is **explicitly excluded** as a signature — it renders on the green path. **Collected counts are stated beside every count line** (NFR-008): at `bb2020fea9`, `test_sync_status_per_project_3030.py` collects **4** (so its red count line is `1 failed, 3 passed`) and `test_sync_doctor_per_project_3030.py` collects **12** (so its red count line is `1 failed, 11 passed`). A count line that does not reconcile against its file's collected count is not evidence. **Green after**: the identical command on the fix branch quotes its `N passed` line **with the collected count**. **Determinism — restated so it can fail** (post-plan squad, F3): repetition alone is *not* the criterion, because `pytest-randomly` is **not installed** at `bb2020fea9` (`importlib.util.find_spec("pytest_randomly")` → `None`; absent from `pyproject.toml:101-113` and from every workflow), so nothing randomises order and "three runs, same node-id" is trivially satisfied. The reproducer must additionally red **when the failing case is selected alone by node-id**, with the same assertion text and a collected count of **1** — a red that needs its file-siblings to run first is order-dependent and fails C-004. Both measurements are reported. **Independence**: no xdist, no dependence on file order; the run's own `plugins:` header line is quoted so the ordering-plugin state is measured rather than assumed. **Control**: the same command with `TTY_COMPATIBLE=0` added passes on the base commit, which is what distinguishes "the width is the cause" from "this file is just broken". | High | Open |
| FR-002 | The render surface is pinned structurally, at the conftest layer | A conftest seam pins the CLI render surface for the affected cones, in the shape `tests/conftest.py:307-329` (`_plain_cli_console_seam`) already establishes: set, `yield`, restore in `finally` (C-002). It pins the surface **explicitly** — both `width` **and** `height`, or `TTY_COMPATIBLE=0`, or `force_terminal=False` — and **must not** set `COLUMNS`, which `rich.console.Console.size` never reads once `is_dumb_terminal` is true (C-012). **The pinned width must be ≥ 240** (post-plan squad, F2): `tests/specify_cli/cli/commands/charter/test_activation_layout.py:111` passes `env={"COLUMNS": "240"}` and is **live** — under `CliRunner` in the default environment `is_terminal` is False, the `is_dumb_terminal` early return does **not** fire, and `COLUMNS` *is* consulted; an explicit size below 240 would narrow that test's render surface. The docstring states both the measured trap values (taken at 220) and the shipped value. **Reach, bounded explicitly** (post-plan squad, F1): `CliConsole._instances` (`src/specify_cli/cli/console.py:49`) also holds three **deliberately-sized specials** — `cli/commands/charter/list_cmd.py:26` (`width=200`), `cli/commands/glossary.py:46` (`width=120`), `cli/commands/docs.py:43` (`width=120`, stated load-bearing at `docs.py:40-42`). A blanket `size = (W, H)` walk overwrites all three. The seam pins **only the two singletons** `console` / `err_console` (`console.py:126-127`), or equivalently exempts any instance constructed with an explicit `width=`. **Stated gap, not an invisible one**: two further consoles are constructed *inside functions* — `cli/helpers.py:234` and `cli/logging_bootstrap.py:92` — and therefore come into existence **after** the seam's setup-time walk. They are **not** pinned; the seam's docstring names them as an accepted gap, and FR-003's guard reports them as such. **Red first**: with the seam disabled by a plugin (never a source edit, C-003, whose corrected loading and neutralisation contract binds here), the FR-001 falsifier reds with the FR-001 text; with it enabled, the same command greens — both directions on one commit, both count lines quoted with their collected counts. **Acceptance**: the seam's docstring records the measured width-alone trap (`width=220` alone → `ConsoleDimensions(80, 25)`; `width=220, height=50` → `(220, 50)`), cites the house precedent `tests/specify_cli/cli/commands/_help_snapshot.py` (which pins `10_000 × 100` for exactly this reason), and names the `#3115` victim files it covers. **Blast-radius check**: the golden `--help` snapshot tests, `tests/specify_cli/cli/commands/test_doctor_cli_surface_golden.py` **and `tests/specify_cli/cli/commands/charter/test_activation_layout.py`** are run before and after with their collected counts quoted; any change in outcome is reconciled, not absorbed. | High | Open |
| FR-003 | A durable guard: no `CliConsole` renders narrower than the identifiers under assertion | A guard (`tests/architectural/test_cli_console_render_width.py`) fails when any live `CliConsole` instance would render narrower than the **longest identifier any test asserts on** — the 36-character project uuid being the current maximum. It uses `CliConsole._instances` (the same weak set `set_all_plain` walks, `console.py:49`) so it reaches the singletons **and** the deliberately-distinct specials. **Red first**: with the FR-002 seam disabled, the guard reds naming the console, its measured `size.width`, and the identifier length it was compared against. **Positive control**: with the seam in place, the guard passes **and asserts it saw the *named* singletons** — `specify_cli.cli.console.console` and `specify_cli.cli.console.err_console` (`console.py:126-127`), identified by object identity, not merely a non-zero count (post-plan squad, F1: a non-zero count is satisfiable by the three deliberately-sized specials alone while both singletons are absent from the weak set). It additionally prints: the number of consoles inspected; the longest asserted identifier length; the **exempted** explicitly-sized specials by `module:line` with their widths (`list_cmd.py:26` 200, `glossary.py:46` 120, `docs.py:43` 120); and the **two function-constructed consoles it cannot reach** (`helpers.py:234`, `logging_bootstrap.py:92`) as a **named gap**. A guard that inspected zero consoles — or that inspected some but not the two singletons — passes vacuously (NFR-008). **It detects and fails; it does not repair** — a guard that widens the console it is watching silences what it guards (H8). **Rot control**: if `CliConsole._instances` or the seam is renamed, moved or deleted, the guard fails loudly rather than silently inspecting nothing. | High | Open |
| FR-004 | The forbidden remedy is proved forbidden, not asserted | "Normalise the whitespace and the assertion passes" is the obvious wrong fix and must be closed with a measurement, not a sentence. **Acceptance**: the 80-column captured output from FR-001 is committed as a fixture; a test asserts that after **full whitespace collapse** (`re.sub(r"\s+", " ", out)`) the uuid is *still* not a substring, and reports the **number of characters the fold interleaved between the two fragments**. **Capture provenance is part of the fixture, not of a PR comment** (post-plan squad): each committed capture carries the exact command that produced it, the commit it was taken at, the `TERM` / `FORCE_COLOR` / `TTY_COMPATIBLE` / `COLUMNS` values in force, and the **observed `Console.size` tuple** at capture time. A capture with no provenance is a recollection, and a fixture nobody can re-derive is the same shape as a gate that prints like a pass. **In-file positive anchor** (post-plan squad): "the uuid is not a substring" is satisfied just as well by a capture that lost the uuid altogether, so the test must additionally assert that **both uuid fragments *are* present**, that **their concatenation equals the uuid**, and that the **interleaved character count is > 0**. **Red first**: the same test against a control capture taken at the pinned width finds the uuid present, so the assertion is shown to discriminate rather than to be trivially true. C-009 records the rule; this FR is its evidence. | High | Open |
| FR-005 | The `sleep`-count failure is diagnosed on its own evidence | `tests/sync/tracker/test_saas_client.py::TestRetryBehaviors::test_429_respects_retry_after` is investigated as a **separate** defect from the CLI failures, whose measured cause is render width and therefore cannot be shared. **Given mechanism, not to be re-derived**: `saas_client.py:19` is a bare `import time`, so `@patch("specify_cli.tracker.saas_client.time.sleep")` resolves the **stdlib** module object; the mock is process-wide and its call recorder counts sleeps from **any live thread in the worker** during the patch window. The victim file's own docstring documents this class at `tests/sync/tracker/test_saas_client.py:36-46`. **Two legs closed in advance and not to be funded**: (a) "a leaked module-global retry/backoff value" is **structurally impossible** — `saas_client.py` has exactly two module-level names, `_SESSION_EXPIRED_MESSAGE` (`:36`) and `_UNAUTHENTICATED_CATEGORY` (`:39`), and the backoff is local variables at `:466-468`; (b) the leaked-thread hypothesis points at `src/specify_cli/sync/daemon.py` (threads `:587`, `:767`, `:828`; sleep loops `:584`, `:1382`), **not** at `_poll_operation`, which nothing threads. **A floor is recorded before FR-010's budget starts** (post-plan squad): either the symptom is **observed red locally**, with its failure text quoted verbatim (`AssertionError: Expected 'sleep' to be called once. Called <n> times.`) and the selection and collected count that produced it; **or** an explicit written statement that it **could not be reproduced locally**, listing every selection tried with each one's collected count and outcome. Without that floor the non-converging branch is closable on self-reported hours alone, which is not a measurement. **Acceptance**: a written attribution naming (i) a leaked live thread and its start site, or (ii) a specific other mechanism, supported by a reproduction that **shows the call count moving** — the count before, the count after, both quoted. **Each excluded mechanism carries a named exclusion measurement** — the command, the collected count, and the observed call count — not an argument. Explicitly permitted: "the two symptoms have two different causes". Explicitly **not** permitted: adopting the issue's *"common shape"* sentence as the finding. | High | Open |
| FR-006 | A narrowed inventory of process-global mutable state and thread-spawning seams in the `tests/sync/` cone | A committed artefact at **`docs/development/process-global-inventory-3115.md`** — deliberately **outside `kitty-specs/`**, which `src/specify_cli/policy/commit_guard.py:84-89` refuses from implementation branches (C-010). Scope is the `tests/sync/` cone only; the CLI cone is out of scope because its failure has a measured non-global cause. Each entry carries **four mandatory values**: (1) module and symbol; (2) `reset seam: <name>` / `no reset seam` / `not reachable`; (3) who calls that seam, or `nobody`; (4) **whether `test_429_respects_retry_after`'s outcome depends on it** — `depends` / `does not depend` / `undetermined`, with the evidence. **Acceptance**: the count of modules scanned is stated, and a **per-bucket count** is given for each of the four values (e.g. "31 modules scanned; 12 `no reset seam`; 4 `depends`; 9 `undetermined`") — a grep-shaped deliverable with no dependence column is closable without doing the work. **This FR needs no culprit and survives a failed hunt**: it is the map, and FR-010's deferral inherits it. | High | Open |
| FR-007 | Structural isolation for the sync cone: the polluter reds, not the victim | An autouse guard in `tests/sync/conftest.py` snapshots the globals and the live-thread set that **FR-006's inventory** marks reachable, and **fails the test that leaves them dirty**, naming the symbol (or the thread's `name` and target) and the node-id. Scoped to FR-006's inventory, **not** to FR-005's answer, so it ships whether or not the attribution converges (H4). **Red first**: a deliberately-leaking probe — which must mutate exactly one inventoried entry and nothing else, and **may not be a purpose-written file that satisfies the criterion by construction**. **The contradiction this FR previously carried is resolved here** (post-plan squad): the plan named exactly such a purpose-written file, which this clause forbids. The order of preference is binding — **(1)** bite a **real inventoried leak** surfaced by FR-006: an existing test in the `tests/sync/` cone that FR-006's inventory marks as leaving an inventoried entry dirty, named by node-id, failed by the guard **on that test**; **(2)** only if FR-006's inventory surfaces no such test, a synthetic probe is permitted, and then the limitation is recorded **in FR-015's exact voice** — *"the only demonstrated bite is the synthetic case"*, written verbatim in the probe's docstring and in the work package's transition note. **The designated control-your-diagnostic case is run first**, before the guard's verdict on anything else is trusted: `tests/specify_cli/invocation/test_propagator_consent_gate_3030.py`'s `wiring` fixture (the known `reset_adapters()` leak, whose answer is already known); its outcome is quoted. The **probe**, not a later victim, carries the failure. **Positive control**: a clean selection is not flagged, and the guard reports **how many tests it inspected and which inventory entries it did not watch**, with the reason (H8, NFR-008). **It detects and fails; it does not repair.** **Rot control**: if a watched symbol is renamed, moved or deleted, the guard fails loudly rather than silently watching nothing. **Restore, do not clear** (C-002). | High | Open |
| FR-009 | The already-landed `reset_token_manager()` hardening is resolved either way | `578a659162` / `4f8e4ca781` shipped as self-declared unproven hardening. FR-001 and FR-002 now make that claim cheap to test, and the width finding already supplies a strong prior: the reset was aimed at a global that was not the CLI cause. **Acceptance**: either the reproducer shows the token-manager reset is load-bearing (record the measurement, both directions), or it shows it is not, in which case it is **kept with its docstring corrected** to say it is defence-in-depth rather than the fix — a comment that describes a fix that never fired is the same shape as a gate that prints like a pass. Deleting it is acceptable only if it is shown inert **and** FR-006's inventory shows nothing reads the singleton on that path. **Red first, and it must discriminate**: the FR-001 falsifier already reds *with* the reset in place, so the measurement is what removing it does. With `reset_token_manager()` neutralised by a plugin (never a source edit — C-003's corrected contract binds: hook-level neutralisation, `-p <module>` loading, per-site split, and a loud failure if the patched symbol was never called), run (a) the FR-001 falsifier and (b) the same file at the pinned width, and quote all four count lines with their **collected counts** and their assertion texts. The reset is load-bearing **only if** case (b) turns red with a named assertion; an unchanged colour in both cases is the finding — recorded as "not load-bearing", not explained away — and a red that is a `TypeError` or a fixture error satisfies nothing (NFR-007). **A null verdict from a run whose mutant suppressed zero calls is a finding about the mutant, not about the reset**: the run claiming "not load-bearing" must report a **non-zero suppressed count** at the patched sites. **Per-site split, measured** (post-plan squad): all five `578a659162` files import `reset_token_manager` **function-locally, inside the fixture body, from the defining module** `specify_cli.auth.manager` — `test_sync_doctor_per_project_3030.py:62`, `test_sync_status_per_project_3030.py:73`, `test_sync_migrate_backfills_h4.py:57`, `test_sync_purge_3030.py:83`, `test_sync_doctor_consent_health_3030.py:70` — so a plugin patching `specify_cli.auth.manager.reset_token_manager` binds at all five and the fifth rot mode does not bite there. Two other sites bind **eagerly by value via the package name** at module import — `tests/auth/integration/conftest.py:22` and `tests/auth/test_websocket_provisioning.py:28`, both `from specify_cli.auth import reset_token_manager` — and are **deliberately unpatched**; the report names them as such, **never as zero**. **This FR now also applies its own verdict** (the convergence was cut, and with it the package that was to apply its verdict): the corrected docstring lands at the five sites in the same work package that measured it, which is what keeps those five files under one live agent (C-007). This FR is what closes `#3030`'s matrix row. | Medium | Open |
| FR-010 | A stated search budget, and a blocking exit clause | The sync-half investigation is bounded: **at most 6 agent-hours and at most 3 candidate mechanisms** measured after FR-006's inventory is complete, stated in the PR as hours spent and mechanisms tried. **On exhaustion**, `#3115` resolves `deferred-with-followup` against a narrowed successor issue that inherits FR-006's inventory and the harness's **negative** result (which mechanisms were excluded and by what measurement) — so bounded, finished work (`#3113`, the timeout gap, the whole CLI half) is not held hostage to an open-ended hunt. **Blocking exit clause**: a green shard **may not** close the sync half while the `sleep`-count cause is unidentified. The only permitted terminal states for that leg are (a) cause identified with a both-directions reproduction, or (b) explicit `deferred-with-followup` with the successor issue number recorded. "Recorded as unproven" plus a green shard is **not** a permitted closure — that is the exact path that produced `578a659162`. | High | Open |
| FR-011 | Proof under a shard matching CI, stated in full, quoting the job | The affected tests pass under a shard **matching CI's configuration**. **The affected tests are the 13 node-ids enumerated in `plan.md`, not a count** (post-plan squad): each of the 13 has its outcome **quoted from the run's own report**, and any node-id absent from the collected set is **named and explained** (marker-deselected, swallowed by one of the four `--ignore`s, or renamed since the issue was written), with an absence closable as a **deliberate exclusion only by naming it as one**. The claim states: worker count **quoted from the run's own xdist header** (`gw0..gwN`) rather than inferred from the runner label; `--dist loadfile`; marker selection `-m "fast and not windows_ci"`; the exact file and `--ignore` selection from `.github/workflows/ci-quality.yml`; whether `--cov` was on; and the **collected test count**. **Any claim about CI quotes the *job* conclusion, never the workflow's**: `fast-tests-sync` is gated on `needs.changes.outputs.sync` (`ci-quality.yml:1101`) and was skipped entirely on run `30622853036`, and `fast-tests-cli` tolerates `exit 5` (`:1545`) — so a green workflow is compatible with the sync shard never having run and with the CLI shard having collected nothing. A claim that does not name the job and its conclusion (`success` / `skipped` / `failure`) and its collected count is not a measurement. `tests/sync` and `tests/cli` sessions are **not** run in parallel on one machine (NFR-004; 16 recorded false reds). | High | Open |
| FR-012 | The `/tmp` root-walk artifact: pinned invariant plus a precondition that names the offender | `tests/sync/test_sync_consent_default_deny.py::test_unresolvable_routing_does_not_consent_to_sync` currently depends on `locate_project_root`'s walk-up finding no `.git`/`.kittify` marker anywhere above `tmp_path` — and on `SPECIFY_REPO_ROOT` being unset, which it never asserts (that env var is tier-1 authoritative in `core/paths.py`). **Decision (taken here, not left open)**: (a) the **invariant** — routing that cannot be determined denies — gets a pin that does not depend on the filesystem at all (force the resolution seam to yield "unresolvable" and assert `is_sync_enabled_for_checkout()` is `False`), so coverage of the requirement cannot be removed by a hostile machine; (b) the existing walk-up test keeps its cwd-based form and gains an **asserted precondition** that reports the first ancestor carrying a marker and the value of `SPECIFY_REPO_ROOT`. **Red first**: with a marker planted above the tmp root, the current test fails on the bare consent assertion; after the change it fails naming the offending ancestor, and the new filesystem-independent pin passes in both environments. **C-001 binds**: no production routing change. | Medium | Open |
| FR-013 | The positional transport call is a **stated** limit of the egress guard | `tests/architectural/test_egress_consent_boundary.py`'s module docstring lists completeness limits 1-7 (getattr-by-string, empty registries, dynamic import, subprocess, at-rest, bare `.put`, multi-sink-per-file). The all-positional / no-`headers=` transport call is added as the next numbered limit, in the same voice: what the shape is, why AST matching cannot see it, and what does catch it (review, and the file-keyed allowlist if the sink lands in an unlisted file). **The cross-reference is one-directional**: this docstring cites `kitty-specs/journal-project-consent-3030-01KYKWQS/egress-inventory.md`; that file is a **closed mission's dossier** and is **not edited** by this mission (C-010). **Acceptance**: the limit list has grown by exactly one numbered entry, the count before (7) and after (8) is stated, and a meta-test asserts the entry exists so a future docstring trim reds. | High | Open |
| FR-014 | The guard's bite-test grows **two** positional-form cases, and the second is the gate | `test_scanner_detects_each_sink_shape` currently exercises the kwargs form only (`poster(url, data=body, headers=hdrs, timeout=5.0)`). **Two** positional cases are added: **(A)** `def go(poster, url, body, hdrs): return poster(url, body, hdrs)`, whose first argument name *is* in `_URL_ARG_NAMES` (`:197`); and **(B)** `def relay(post, u, payload, meta): return post(u, payload, meta)`, whose names are **outside** that set. **The adoption gate is (B).** A matcher that passes (A) and fails (B) is blind in exactly the way `#3113` is about, because `_attr_tail` returns `node.id` verbatim for a bare `Name` (`:266-272`) — so (A) alone certifies a blind matcher. **Red first**: on `bb2020fea9` both (A) and (B) fail with `scanner went blind to transport-call`; the failure text is quoted for each. **Acceptance**: after FR-015 both pass; **or**, if FR-015's measurement forbids tightening, each is committed as `pytest.xfail(reason=..., strict=True)` naming FR-013's stated limit. **`strict=True` is mandatory** (C-011): `pytest.ini` sets no `xfail_strict` and `pyproject.toml:183-192` forbids a `[tool.pytest.ini_options]` block, so a non-strict `xfail` that starts passing reports `XPASS` and the run stays green — the FR's stated pinning mechanism would not exist. A silent deletion of either case is a spec violation. **Generalisation to record in the file**: *a negative control that only tests the shape you thought of is not a negative control* — every rule in the sink vocabulary carries a bite-test case per **shape** it claims to cover, not one per rule. | High | Open |
| FR-015 | Tighten the AST matcher on a **structural** property, at a measured zero false-positive cost | `_transmits_a_body` (`:295-306`) requires `headers` **and** a body keyword, so an all-positional call is invisible. The tightening measured first is the **sink-shaped** one: *the callee is a bare `ast.Name` whose `id` resolves to a **parameter of the enclosing `FunctionDef`*** — transport injected as a parameter. This is decidable from the AST with **no author-chosen word**, and `_classify` already has the bare-`Name` branch to hang it on (`:316`). **A tightening that cannot be expressed without consulting an author-chosen identifier — including `_URL_ARG_NAMES` — is rejected regardless of its false-positive count**: C-006 forbids the guard being *callee*-name-shaped, and keying on an *argument* name is the same failure in a different subject. **Order is binding**: the `src/`-wide false-positive count is taken **FIRST**, before any matcher edit; the scanner change is funded **only if** it returns **zero**. **Measured already, at `bb2020fea9`, and stated here so it is not re-derived** (post-plan squad, F4): the minimal rule that catches the adoption-gate case (B) yields **5 false positives** over `src/`, arising at five sites, each a **callee** that is a same-named `Callable`-typed parameter of its enclosing function (all dependency-injected lookups, none a transport): `locate_work_package` in `_resolve_wp_bearing_fields` (`mission_runtime/resolution.py:617`), `resolve_workspace_for_wp` in `_resolve_wp_bearing_fields` (`:628`), `behind_commits_touch_only_planning_artifacts` in `_check_branch_currency` (`cli/commands/agent/tasks_parsing_validation.py:628`), `resolve_workspace_for_wp` in `_validate_worktree_state` (`:831`), and `build_queue_scope` in `_build_legacy_scope` (`sync/preflight.py:752`) — **corrected post-implementation (analysis pass 8, re-derived independently by the orchestrator).** The earlier list said *"four named enclosing functions — `resolve_workspace_for_wp`, `locate_work_package`, `behind_commits_touch_only_planning_artifacts`, `get_wp_lane`"*, which was wrong twice: those are **callees, not enclosing functions**, and **`get_wp_lane` is not among the five** — it occurs at `mission_runtime/resolution.py:752` with only **2** positional arguments, below the >=3 threshold the adoption-gate case sets. The unnamed fifth was `build_queue_scope`. **Worth recording as this mission's own thesis landing on its own review loop**: WP10's implementer *and* its independent reviewer both reported the five as reproducing byte-for-byte, including `get_wp_lane`. Both started from this list and searched for these names rather than deriving the set from the predicate — and the two `:752`s in different files (`resolution.py` and `sync/preflight.py`) made the mismatch look like a match. The count of **5** was right throughout and is unaffected, so the decline decision never depended on it; what was wrong is the attribution a future package revisiting the tightening would have inherited — against **211 candidate sites across 116 files** in total. **Corrected post-implementation (WP10 review)**: this figure previously read *"211 candidate sites across 13 files"*. The site count is right and reproduces, but the **file count was wrong** — `13` was transcribed from the callee-agnostic precedent quoted later in this same acceptance clause (*"25 sites / 13 files / 0 FPs"*) onto the FR-015 figure. Re-derived independently by the WP10 implementer and its reviewer: the predicate as implemented (**nearest**-enclosing function) measures **203 sites / 112 files**, and scoped to **any** enclosing function it measures **211 sites / 116 files**, the extra 8 being calls in nested and closure scopes. Both are honest measurements of slightly different rules; neither pairs with 13. The 5 named false positives reproduce byte-for-byte under both, so the decline decision never depended on this. On that measurement the expected outcome is **the matcher is left alone and FR-014 lands as two `strict=True` xfails**. The implementing package **re-runs and quotes the count itself** (it may not cite this paragraph as its measurement) but starts from the non-adoption expectation. **And the tightening is a scanner restructure, not a branch edit**: the predicate needs enclosing-scope information that `_classify(node: ast.Call)` (`:309`) does not carry — it is reached from a flat `ast.walk(tree)` at `:347` — so adopting it means threading the enclosing `FunctionDef`'s parameter set through the walk. That cost is paid only against a zero count. **Acceptance**: sites, files and false positives over the whole of `src/` are reported **before** adoption, the way the callee-agnostic rule itself was adopted (25 sites / 13 files / 0 FPs); the sites the tightening **newly adds** are reported **separately** from the pre-existing ones; and a **zero delta is written down as "the only demonstrated bite is the synthetic case"**, not claimed as a success. If false positives are non-zero the matcher is left alone, the number is recorded in the docstring next to FR-013's limit, and FR-014 lands as two `strict=True` xfails. Either outcome is a pass for this FR; an unmeasured tightening is not. Any change to the sink/allowlist counts is reconciled against `tests/architectural/_baselines.yaml`. | Medium | Open |
| FR-016 | A default per-test timeout with an explicitly stated method and a stated blast radius | `pytest.ini` registers the `timeout` marker and sets **no timeout in `addopts`**, so a non-terminating test hangs the job. A default is added **with the method stated explicitly** rather than left to pytest-timeout's platform default. **Why a global default and not per-test marks**: marks cover only what someone remembered to mark, and the failure class here is *the loop nobody anticipated* — "registering a marker that nothing applies is the same shape as an allowlist with no enforcement". Existing explicit `@pytest.mark.timeout(...)` marks (about 15 sites, including `timeout(600)` on `test_dogfood_corpus_backfilled` and `timeout(120)` on the charter e2e golden path and `tests/stress/test_concurrent_emits.py`) **override** the ini default. **Blast radius, stated because `testpaths = tests`**: an `addopts` default caps **every** invocation of this ini, and 46 tests are marked `slow` (defined in `pytest.ini` as ">30 seconds") against only ~15 timeout sites — the opt-in selections that run them are ones FR-017's regression clause structurally cannot observe. **So the value is derived one of two ways, and which is used must be stated**: (a) from `--durations` output covering **every selection that inherits the ini**, including the `slow`/`stress`/`e2e` opt-ins; **or** (b) the flag is **scoped to the fast job command lines** in `.github/workflows/ci-quality.yml` rather than placed in `addopts`, in which case the ini is unchanged and the blast radius is the enumerated job list. **`--cov` must be accounted for**: both fast shard commands carry it (`ci-quality.yml:1132`, `:1543`); it installs a per-thread trace function, changes thread scheduling, and **inflates the `--durations` output this value is derived from** — so the measurement states whether coverage was on, and if it was, the value is justified against the coverage-on numbers. **Acceptance**: the chosen value, the chosen method, the chosen derivation (a) or (b), the coverage state, and the measured maximum unmarked-test duration are all stated, with a floor of 4× that maximum. | High | Open |
| FR-017 | The timeout backstop produces a *named red*, not a killed job — and its regression is enumerated | **Red first**: a deliberately non-terminating `fast` test hangs the selection on `bb2020fea9`. **Green after**: the same selection ends **and prints a summary line naming that test**. This is what discriminates the usable configuration from the useless one: pytest-timeout's thread method killed a `#3030` session mid-run and produced **no summary and therefore no verdict**, while the signal method reds the test with a traceback. A run that ends with empty output does **not** satisfy this FR. The Windows job (`ci-windows.yml`) has no `SIGALRM`, so state what method it gets and what its failure mode is rather than assuming parity. **Regression clause, enumerated rather than aggregate**: the first full CI run after the change lists **every job that inherited the new default**, with each job's conclusion and **collected count**, and separately lists **every selection that did not run at all** (path-filtered, skipped, or opt-in-only — `fast-tests-sync` is gated on `needs.changes.outputs.sync`, `ci-quality.yml:1101`). Zero tests newly red attributable to the timeout; any that do are listed with their durations and either marked or the value raised. "Nothing newly red" over a set that did not run is not a result. | High | Open |
| FR-018 | Termination is asserted by a counter, never by the timeout | The two loop-driving tests in `tests/delivery/test_dispatch_window_consent_3030.py` (`test_no_non_consented_event_ever_enters_the_live_dispatch_window`, `test_the_window_is_filled_with_consented_events_not_wasted_on_denied_ones`) drive `_run_dispatch_batches`' 413-halving/regrowth loop through `_RecordingIngress` with **no bound**, so non-termination hangs them. They gain a hard cap on the recorded batch count that reds naming the count, mirroring `DISPATCH_CALL_CAP = 25` in `tests/delivery/test_nfr002_loop_permanence_3030.py` — the shape `#3030` already adopted for exactly this reason. **Red first is a consequence, not a threshold flip**: a **non-terminating-loop plugin mutant** — importable via `PYTHONPATH=scripts/mutants` **and loaded with `-p <module>`**, neutralising at hook level, never a source edit and never a same-named fixture (C-003's corrected contract); asserting its own binding, reporting the per-site split, and failing loudly if the symbol it patched was never called — makes the batch loop fail to make progress, and each test must red **on the counter, naming the count** — and specifically **not** on `Failed: Timeout (>Ns) from pytest-timeout`. A red whose text is the timeout means the counter did not bind and does **not** satisfy this FR. Merely setting the cap below the legitimate batch count proves the assertion fires, not that it fires *on the defect*; both measurements are reported, and the mutant one is the acceptance. **Rule recorded in the file**: *any assertion about termination needs a counter; the timeout is a backstop for the harness, not a substitute for the pin.* | High | Open |

### Non-Functional Requirements

| ID | Title | Requirement | Category | Priority | Status |
|----|-------|-------------|----------|----------|--------|
| NFR-001 | Every shard claim states its distribution — including coverage | Any measurement over a shard states: worker count (numeric, **quoted from the run's own xdist `gw0..gwN` header**, never inferred from the runner label), `--dist` mode, marker selection, file selection including `--ignore` entries, **whether `--cov` was on** (both fast shard commands carry it — `ci-quality.yml:1132`, `:1543` — and a per-thread trace function changes thread scheduling and inflates `--durations`), and the collected test count. A distribution-dependent claim whose distribution is unstated is not a measurement. **Interpreter and plugin registry are part of the distribution** (added post-WP10, analysis pass 9): every shard or suite claim also states `sys.executable` and quotes the run's own `plugins:` header. Two interpreters are reachable here — `.venv/bin/python` (pytest 9.0.3, nine `pytest11` entry points including `timeout` and `xdist`) and bare `python3` (`/usr/bin/python3`, pytest 9.1.1 from user-site, only `anyio` and `respx`). `pytest-timeout` and `xdist` are absent from the latter, so a timeout or shard claim measured there is not weaker evidence, it is **no evidence**. The mission was bitten by omitting this: an implementer/reviewer pair measured the same commit on different interpreters and the divergence sat unnoticed in their quoted plugin headers. | Evidence | High | Open |
| NFR-002 | Every worktree measurement states its import path | Any measurement taken in a `git worktree` states `PYTHONPATH=$WT/src` or a dedicated venv created inside the worktree. `.venv/.../_editable_impl_spec_kitty_cli.pth` holds the **absolute path of the main checkout**, so a worktree using the main `.venv` imports the live tree — which makes the isolation *look* performed and manufactures sameness conclusions. Conclusions of **difference** are largely unaffected; conclusions of **sameness** taken without this are void. | Evidence | High | Open |
| NFR-003 | No piped exit statuses; the count line is the evidence | No suite whose exit status is to be trusted is piped. Full output goes to a file and the tail of the file is read, or `${PIPESTATUS[0]}` is checked explicitly. Claims quote `N passed, M failed`, never "exit 0". **An empty output file is no measurement.** A killed run is neither a pass nor a fail — re-run it narrowed; do not explain it, and check elapsed time against the `timeout` value before attributing it. | Evidence | High | Open |
| NFR-004 | Sweeps are serialised on one machine | `tests/sync` and `tests/cli` sessions are never run in parallel on one machine: they spawn real daemons and `pgrep`/port-scan, so sibling sessions reap each other's (16 recorded false reds). Fan out the coding, serialise the sweeps. This binds FR-007's guard design too: its probe runs must be sequential or explicitly partitioned by `SPEC_KITTY_HOME` and port range. | Reliability | High | Open |
| NFR-005 | The reproducer is cheap enough to be used | The FR-001 reproducer completes in **under 2 minutes** on a developer machine (measured at ~57s on the base commit), and its documented command is a single line. A reproducer nobody runs is documentation, not a tool. | Usability | Medium | Open |
| NFR-006 | The guards' **coverage** is the invariant; cost changes their shape, never their reach | The FR-003 and FR-007 guards' added wall-clock over the `fast-tests-sync` and `fast-tests-cli` selections is measured and reported (before/after, same worker count, same coverage state). If the added cost exceeds **5%**, the response is to change the guard's **implementation** (cheaper snapshot, per-module rather than per-test) — **not** to narrow what it watches. Any reduction in watched surface is a spec change requiring a written justification and an updated FR-006 count, because a guard scoped down to fit a budget is the "mechanism reporting success for having done nothing" shape with a performance excuse. | Performance | Medium | Open |
| NFR-007 | Read the failure text, not the tally | Every red quoted in this mission's evidence is quoted with its **assertion text**. A tally moving is not evidence; `TypeError`s from a changed signature are not evidence of the defect under test. This binds the reproducer's exclusion list and FR-018's mutant equally. | Evidence | High | Open |
| NFR-008 | Every "all checks passed" prints its input count | Any gate, probe, guard or harness result reported here states how many inputs it processed — consoles inspected, tests inspected, modules scanned, candidate mechanisms measured. A gate that ran on zero inputs passes vacuously — and `fast-tests-cli` tolerates `exit 5` (no tests collected) as success (`ci-quality.yml:1545`), so this is a live hazard on this very shard. | Evidence | High | Open |
| NFR-009 | Every baseline states the commit it was taken at, and its lane merges the mission branch first | Every baseline, "before" measurement and red-first demonstration states **the commit it was taken at** and **its lane's merge-base against the mission branch**. Any lane **merges the mission branch — `kitty/mission-<slug>` — into its worktree before its first measurement, and never the planning/target branch.** **Measured on WP01**: an implementer read this clause and merged `feat/verification-trust-3115` instead. Both branches carry the dossier, so the merge dragged `kitty-specs/` commits onto the lane and `move-task --to for_review` refused — *"kitty-specs/ changes are not allowed on lane branches"* (`src/specify_cli/policy/commit_guard.py:84-89`). Recovered with `git restore --source kitty/mission-<slug> --staged --worktree -- kitty-specs/` and a commit, which is the remedy the tool itself prints. **If the lane is already at the mission-branch tip, no merge is needed and none should be made** — check `git rev-list --count HEAD..kitty/mission-<slug>` first and record the number. This mission's own orchestrator reproduced the friction record's first entry — *"cut from a commit predating the mission's own acceptance pins, so the lane reported a clean 0-failure baseline"* — by creating the mission at `9189cf2b36`, **7 commits behind** `Priivacy-ai/main`. Corrected to `bb2020fea9`; the 7 commits are charter-pack and `context.py` decomposition work touching none of this mission's files (the egress guard, `_baselines.yaml`, `pytest.ini`, `console.py`, `sync.py` and all seven victim test files are byte-identical across the gap, and `rich` is unchanged), and the falsifier was **re-run** on the new base rather than inferred to still hold. A baseline whose commit is unstated is void. | Evidence | High | Open |
| NFR-010 | Lane `for_review` transitions are taken one at a time | The pre-review gate's serialisation lock **degrades to no lock after 5 seconds** (`src/specify_cli/review/pre_review_gate.py:256` — `_LOCK_ACQUIRE_TIMEOUT_DEFAULT = 5.0`; the "fallback-to-run" rationale is at `:275-279`), and gate runs over this mission's suites take about two minutes — so a second lane transitioning concurrently runs its suite anyway, recreating the 16 recorded false reds from parallel `tests/sync` + `tests/cli` sessions. The orchestrator takes lane `for_review` transitions **serially**, and any gate red is **re-measured serially** before it is believed. | Process | High | Open |

### Constraints

| ID | Title | Constraint | Category | Priority | Status |
|----|-------|------------|----------|----------|--------|
| C-001 | No production routing change for the `/tmp` artifact | The `/tmp`-root-walk failure is a machine-specific artefact that reproduces on pristine `upstream/main` and passes on CI. Harden the test's precondition or document it; **do not** change `locate_project_root` / `resolve_checkout_sync_routing_readonly` for it. | Technical | High | Open |
| C-002 | Fixtures restore, they do not clear | Any fixture touching process-global state — including the FR-002 render seam — restores the value it found, in a `finally`. `reset`-to-empty is permitted only for state nothing outside the fixture reads; a registry is by definition not that. Applies to every fixture this mission adds or edits. | Technical | High | Open |
| C-003 | No source edits during a verification run; mutations are pytest plugins, **loaded and neutralising at hook level** | **Corrected by the post-plan squad (M1, CRITICAL). The previous wording — "plugins loaded via `PYTHONPATH`" — specified a mutant that is silently inert, i.e. the exact rot mode this mission exists to guard against.** Mutations and blinding are pytest plugins, never source edits, and never while a verification run is in flight. **(1) Loading**: the module lives in `scripts/mutants/`, one file per mutant named for its work package, is made importable with `PYTHONPATH=scripts/mutants` **and is loaded with `-p <module>` (or `PYTEST_PLUGINS=<module>`)**. `PYTHONPATH` alone does **not** load a pytest plugin — a `PYTHONPATH`-only mutant does nothing and reads as a passing gate. **(2) Neutralisation site**: at **hook level** — `pytest_configure` for import-time and session-level seams, `pytest_fixture_setup` to intercept a named fixture's setup — and **never** by defining a same-named fixture in the plugin: a plugin fixture **loses** to a conftest fixture for items under that conftest's directory, so a same-named autouse fixture in a plugin is a guaranteed no-op. (Probed with a known-answer baseline: a hook-level plugin produced a named red, `AssertionError: seam was off`; the same-named-fixture form did not bind at all.) **(3) Self-proof**: every mutant asserts its own binding, reports the **per-site split** across every name the symbol is reachable by (an aggregate cannot distinguish "both sites mutated" from "one mutated, one inert" — fifth rot mode), and **fails loudly if the symbol it patched was never called** during the session. A zero suppressed count is a finding about the mutant, not about the code, and no verdict may be drawn from such a run. **(4) Reporting**: every run under a mutant quotes the mutant's own binding/suppression report alongside its count line. Binds FR-002's seam-disabling, FR-009's `reset_token_manager()` neutralisation, FR-017's hanging-test mutant and FR-018's non-terminating-loop mutant. | Technical | High | Open |
| C-004 | The reproducer may not depend on the scheduler | `--dist loadfile` assignment is dynamic and work-stealing; a reproducer that depends on a particular assignment is not reproducible by construction. FR-001 satisfies this by construction (one process, one file, two environment variables) and must not regress into a file-order or worker-order recipe. | Technical | High | Open |
| ~~C-005~~ | **TOMBSTONE — STRUCK** (`-p no:randomly` prohibition) | **Struck by operator decision, post-plan squad (F3). The number is retained and not reused.** It read: *"`-p no:randomly` may not be used to obtain a colour."* **Why struck**: `pytest-randomly` is **not installed** at `bb2020fea9` — not importable (`importlib.util.find_spec("pytest_randomly")` → `None`), absent from `pyproject.toml:101-113`'s `test` extra, and absent from every workflow. So C-005 forbade a flag that is already a **no-op**, and — worse — it made FR-001's determinism criterion *trivially satisfied because nothing randomises order*: green for the wrong reason, in the mission built to eliminate exactly that. **What replaces it**: (a) FR-001 gains a criterion that **can** fail (the red must reproduce with the failing case selected alone by node-id, collected count 1); (b) any run that disables or fixes ordering states the plugin, the seed and the reason; (c) any determinism claim names a way it could have gone the other way. The `#3030` recollection that motivated C-005 (*"that sweep ran `-p no:randomly` and did not hit the poisoning worker assignment"*, from `#3115`'s own issue body) is retained as a **lesson about favourable orderings**, not as a live constraint on this tree. Whether `pytest-randomly` was ever installed on the tree that sweep ran against is **not established by this mission** and is not chased. | Technical | — | **Struck (operator decision, post-plan squad)** |
| C-006 | The egress guard must not regress to name-keying, and must not cry wolf | Any change to the egress guard keeps it **sink-shaped rather than name-shaped** — and this covers *argument* names as well as callee names (`_URL_ARG_NAMES` is an author-chosen vocabulary, and keying on it is the `RETIRED_DRAIN_NAMES` failure mode with a different subject). Zero measured false positives over `src/`, or no change. | Technical | High | Open |
| C-007 | One live agent per file; explicit-path staging | Each brief names the files other agents hold. `git add <paths>`, never `git add -A`; `git status --short` before every commit; never `reset` / `checkout --` / `stash` / `rebase` on a shared branch — report instead. 13 files were lost to a shared index on `#3030`. | Process | High | Open |
| C-008 | `ruff format` is not run | The repo is not clean under `ruff format` (`line-length = 164`); running it reflows other people's committed work. Only `ruff check` is meaningful. | Process | High | Open |
| C-009 | Output flattening is a forbidden remedy for the fold | No fix for the `#3115` CLI half may work by normalising, collapsing or stripping whitespace from rendered output before asserting on it. The fold interleaves the rest of the table row **between** the two uuid fragments, so no whitespace transformation rejoins them (FR-004 proves this rather than asserting it) — and a "flattening" fix that appeared to work would be doing so for some other reason, unmeasured. Equally forbidden: removing `overflow="fold"` from the Project column, which exists deliberately so a project identity is never ellipsized into a prefix the operator cannot pass to `sync purge` (`sync.py:1430-1436`). | Technical | High | Open |
| C-010 | No `kitty-specs/` writes from lane branches, and no writes into a closed mission's dossier | `src/specify_cli/policy/commit_guard.py:84-89` refuses any staged path under `kitty-specs/` from an implementation branch. Every artefact this mission requires a **lane** to write lands outside it — `docs/development/process-global-inventory-3115.md`, `scripts/repro_3115_render_width.sh`, `docs/development/testing-parallel.md`. Additionally, `kitty-specs/journal-project-consent-3030-01KYKWQS/egress-inventory.md` belongs to a **closed** mission and is **not edited**: FR-013's cross-reference is one-directional. | Process | High | Open |
| C-011 | Any `xfail` this mission adds carries `strict=True` | `pytest.ini` sets no `xfail_strict` and `pyproject.toml:183-192` forbids a `[tool.pytest.ini_options]` block, so the default is non-strict. A non-strict "pinned hole" that starts passing reports `XPASS` and the run stays green — the pin's stated mechanism does not exist. Every `xfail` added by FR-014 (or anywhere else in this mission) passes `strict=True` explicitly. | Technical | High | Open |
| C-012 | `COLUMNS` may not be used to pin a render width | `rich.console.Console.size` reads `COLUMNS` **only after** the `if self.is_dumb_terminal:` early return, so on the failing path it is never consulted. Any width pin uses an explicit size (**both** dimensions), `TTY_COMPATIBLE`, or `force_terminal` — never `COLUMNS`, and never `width=` alone. **The converse is also constrained** (post-plan squad, F2): `COLUMNS` is *not* dead on the **non-dumb** path. Under `CliRunner` in the default environment `is_terminal` is False, the early return does not fire, and `COLUMNS` **is** consulted — `tests/specify_cli/cli/commands/charter/test_activation_layout.py:111` passes `env={"COLUMNS": "240"}` and is live today. Two consequences bind: **(a) the pinned width must be ≥ 240**; **(b) the existing `COLUMNS` sets in the victim files are left in place** (`tests/cli/commands/test_sync_status_per_project_3030.py:83`, `tests/cli/commands/test_sync_doctor_per_project_3030.py:72`, and `test_activation_layout.py:111`). They are inert only on the *failing* path; removing them is a behaviour change on the passing one. No requirement in this mission removes or annotates them, and no work package may. | Technical | High | Open |

### Key Entities

- **Render surface** — the effective `(width, height)` a `CliConsole` resolves at render time. Not an
  environment variable: `rich` decides it from `force_terminal` / `TTY_COMPATIBLE` / `FORCE_COLOR` /
  `TERM` / an explicit both-dimension size, and consults `COLUMNS` last. The unit FR-002 pins.
- **Fold** — `overflow="fold"` wrapping a cell across lines rather than ellipsizing it. Deliberate
  (an ellipsized project identity is unusable), and the reason a narrow surface breaks substring
  assertions rather than merely making the output ugly.
- **Process-global** — module-level mutable state whose lifetime is the worker process: singletons,
  registries, caches, import-time-bound paths, memo sets, **live threads**, `os.environ`, and the
  CWD. The unit FR-006 enumerates, scoped to the `tests/sync/` cone.
- **Leak guard** — the autouse fixture that fails the polluter rather than the victim. Its value is
  attribution, not prevention, and it **detects and fails; it does not repair**.
- **Bite-test** — a guard's own negative control: a synthetic source that the guard must flag. Its
  coverage is measured in *shapes*, not in rules — and a shape whose only case uses a vocabulary word
  the matcher already knows is not a shape, it is a tautology.
- **Backstop vs. pin** — a timeout is a property of the harness (it bounds wall clock); a counter is
  a property of the code under test (it bounds iterations). Only the second can be an assertion
  about termination.
- **Job conclusion vs. workflow conclusion** — a workflow is green when its path-filtered jobs are
  *skipped*. Only a named job's own conclusion, with its collected count, is evidence.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A maintainer with no prior context reproduces the `#3115` CLI failure on their own
  machine, from `docs/development/testing-parallel.md`, in **one command** and under **2 minutes**,
  on base commit `bb2020fea9` — and the failure text they see is
  the per-file assertion text quoted verbatim from each source file (see FR-001 — they differ), byte-comparable to CI's 240-char
  repr. `Queue 0 event(s)` is **not** accepted as evidence of the red.
- **SC-002**: The same command on the fix branch passes, three consecutive runs, with the `N passed`
  line **and the collected count** quoted each time; the failing case additionally reds when selected
  **alone by node-id** on the base commit (collected count 1) — the clause that can fail; and the
  same command with the FR-002 seam disabled by a **hook-level plugin loaded with `-p <module>`**
  (C-003) still reds, with the plugin's own **non-zero** suppressed-site report quoted, so the seam
  is shown to be the thing that changed.
- **SC-003**: The measured mechanism is written down at the seam and reproduced from installed
  source: `is_dumb_terminal` precedes the `COLUMNS` read; `width=` alone yields
  `ConsoleDimensions(80, 25)`; `width=` + `height=` yields the requested size; `TTY_COMPATIBLE=0`
  restores the `COLUMNS` path. All four measured values are quoted.
- **SC-004**: With the seam disabled, the FR-003 width guard reds naming the console, its measured
  width and the identifier length; with the seam in place it passes **and asserts it saw the two
  named singletons `console` and `err_console` by identity** (`console.py:126-127`) — not merely a
  non-zero count — and prints the number of consoles inspected, the longest asserted identifier
  length, the exempted explicitly-sized specials by `module:line`, and the two function-constructed
  consoles (`helpers.py:234`, `logging_bootstrap.py:92`) as a **named gap**.
- **SC-005**: The whitespace-collapsed 80-column capture **still** does not contain the uuid, and the
  number of interleaved characters between the two fragments is stated; the same assertion against a
  pinned-width capture finds the uuid, proving the test discriminates.
- ~~**SC-006**~~: **STRUCK — cut with the convergence** (operator decision, post-plan squad). It read:
  *"`grep -c "def _isolated_home" tests/` reports 22 before and M after, with M stated and every
  retained definition enumerated with a one-line reason."* The number is retained and not reused. The
  count is unchanged by this mission and is **not** a success criterion of it; the follow-up issue
  inherits the measurement. The **negative** criterion that replaces it: `grep -c "def _isolated_home"
  tests/` reports **22 before and 22 after** — this mission adds, moves and removes none of them, and
  a diff that changes that count is a scope violation.
- **SC-007**: The `sleep`-count attribution names a mechanism and shows the recorded call count
  moving — the count before and the count after, both quoted — or the sync half exits via FR-010's
  `deferred-with-followup` with the successor issue number and the excluded mechanisms recorded. A
  green shard alone closes neither.
- **SC-008**: A deliberately-leaking probe is failed **by the FR-007 guard, on the probe**, in a run
  where a clean selection of the same files is not flagged; the guard reports the number of tests it
  inspected **and** the inventory entries it did not watch.
- **SC-009**: All the `#3115` affected tests — **13 cases across 7 files**, **enumerated by node-id
  in `plan.md`'s WP for FR-011**, not left as a count — pass under
  `--dist loadfile -m "fast and not windows_ci"` over the exact CI selection, with the worker count
  quoted from the run's own `gw` header, the coverage state stated, and the collected count stated,
  run twice. **Each of the 13 outcomes is quoted from the run's own report.** Any enumerated node-id
  that is **absent from the collected set** is named and explained — deselected by the marker,
  swallowed by one of the four `--ignore`s, or renamed since the issue was written — and an absence
  may be closed as a deliberate exclusion only by naming it as one. A shard-level `13 passed` with no
  per-node-id reconciliation does not satisfy this, because `|| test $? -eq 5` makes an empty
  collection a green job.
- **SC-010**: Every CI claim in the PR names the **job** (`fast-tests-cli`, `fast-tests-sync`), its
  conclusion (`success` / `skipped` / `failure`) and its collected count. A claim that
  `fast-tests-sync` passed is rejected if that job's conclusion was `skipped`.
- **SC-011**: The egress guard's shape-coverage test contains **two** positional-form cases; **both**
  fail on `bb2020fea9` with `scanner went blind to transport-call`; after the change either both pass
  or both are `xfail(..., strict=True)` naming the stated limit. The docstring limit list has grown
  from 7 entries to exactly 8.
- **SC-012**: The `src/`-wide count is taken **before** any matcher edit, and reports sites / files /
  false positives, with **newly-added sites separately from pre-existing ones**. The tightening is
  adopted **only** at false positives = 0. **The measurement already taken** (post-plan squad, F4)
  says the count is **5 false positives** across four named enclosing functions, against **211
  candidate sites in 116 files** (corrected — see FR-015; the earlier `13` was the callee-agnostic precedent's file count, transcribed by mistake) — so the expected, and fully acceptable, outcome is **no tightening**
  plus two `xfail(..., strict=True)` cases. The implementing package re-measures and quotes its own
  numbers; it does not cite the plan's. A zero delta is recorded verbatim as "the only demonstrated
  bite is the synthetic case".
- **SC-013**: A non-terminating `fast` test causes the fast selection to end with a **summary line
  naming it**, where the same test hangs the selection on `bb2020fea9`.
- **SC-014**: Under the non-terminating-loop plugin mutant, both loop-driving tests in
  `tests/delivery/test_dispatch_window_consent_3030.py` red **on the counter, naming the count**, and
  neither reds with `Failed: Timeout`.
- **SC-015**: The timeout change's regression report enumerates every job that inherited the new
  default with its conclusion and collected count, **and** every selection that did not run, with the
  reason. Zero tests newly red attributable to the timeout; the chosen value, method, derivation and
  coverage state are all quoted.
- **SC-016**: On a machine with a repo-root marker planted above the pytest tmp root, the
  `/tmp`-artifact test names the offending ancestor, and the fail-closed invariant is still pinned by
  a filesystem-independent test that passes there.
- **SC-017**: Every measurement in the PR body satisfies NFR-001 through NFR-003 and NFR-009 —
  distribution and coverage state stated, worktree import path stated, count line quoted rather than
  an exit code, and the commit each baseline was taken at plus the lane's merge-base stated.
- **SC-018**: The PR's limits section states, in the mission's own words, that **what makes rich's
  `is_terminal` true on the CI runner is unidentified and was not chased**, and that nothing here was
  tested under xdist.

## Out of scope — explicitly

- **The `_isolated_home` convergence.** **Cut by operator decision after the post-plan
  squad** — see the scope-cut note at the top of this spec. This mission
  adds, moves and removes **no** `_isolated_home` definition; the count stays at 22. A follow-up
  issue carries it with the measured equivalence-class evidence
  (`notes/post-plan-squad-findings.md`). Listed here, and not merely deleted, because "converge the
  22 fixtures" is the single most likely thing an implementer would do helpfully and wrongly on this
  mission's file set.
- **Removing or annotating the three `COLUMNS` sets** in
  `tests/cli/commands/test_sync_status_per_project_3030.py:83`,
  `tests/cli/commands/test_sync_doctor_per_project_3030.py:72` and
  `tests/specify_cli/cli/commands/charter/test_activation_layout.py:111`. The earlier draft had them
  removed as "provably dead". They are **not** dead: they are inert on the *failing* path only, and
  `COLUMNS` is consulted on the passing one (C-012, post-plan squad F2). They stay exactly as they
  are, and the removal is **not** reassigned to any other requirement or work package.
- **Chasing the `is_terminal` trigger on the CI runner.** Offered to the operator and not selected.
  Recorded as the mission's principal known unknown (above) and carried into the PR's limits section.
- **The enumerated pairwise polluter search across both shard cones.** Offered to the operator and
  declined in favour of the measured cause. The null result it would produce is not worth the
  wall-clock. FR-006's narrowed inventory replaces it for the sync cone only.
- **The known pre-existing failures listed in `standing-rules.md`.** Do not chase, do not fix in-PR,
  do not retry to green: `tests/architectural/test_tid251_enforcement.py` (4 tests, proven
  pre-existing on `origin/main` in a pinned worktree);
  `test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out`;
  the two `test_safe_commit_cmd::…_3033`;
  `test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed`;
  `test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock, fails under load); and
  subprocess daemon tests reporting `ModuleNotFoundError: No module named 'typer'` (a user-site
  install interacting with `HOME` isolation — environmental). If one of these appears in a run, name
  it as pre-existing and move on.
- **Production routing changes for the `/tmp` root-walk artifact** (C-001). The resolver's walk-up
  behaviour is not modified. Neither is `SPECIFY_REPO_ROOT`'s precedence.
- **Removing or weakening `overflow="fold"`** on the Project column, or any other rendering change
  made to satisfy a test. The column is deliberate (C-009).
- **Everything else in the `#3030` follow-up backlog.** `#3113` and `#3115` (with the timeout gap
  folded in) are the whole scope. Not in scope: the remaining open `#3030` FRs, the `ConsentedBatch`
  work, the at-rest pooling inventory (limit 7 of the egress inventory / C-006 there), or any new
  egress-path enumeration.
- **Re-architecting the CI shard topology.** Port-range or `SPEC_KITTY_HOME` partitioning per shard,
  the `|| test $? -eq 5` tolerance in `fast-tests-cli`, the `needs.changes` path filter that can skip
  `fast-tests-sync` entirely, and the lane/gate friction recorded in the `#3030` tracer are all
  follow-up candidates, not this mission.
- **Fixing the `#3030` mission's other recorded fixture hazards** — notably the filename-token guard
  in `tests/sync/conftest.py` and the three `test_runtime.py` tests it silences. That change is known
  to be *armed*: replacing the token guard with a marker reds those three, and the natural remedy
  would undo `#3030`'s T028. It needs its own mission with that trap written into its spec.

## Open questions

Only two, and both are genuinely undecidable from the material rather than deferred:

1. **What the `sleep`-count failure's mechanism actually is.** The patch target's process-wide reach
   is settled (FR-005), and two candidate legs are closed in advance — a module-global backoff is
   structurally impossible, and `_poll_operation` is not threaded. What remains is which live thread,
   started where, is sleeping inside the patch window. FR-005 requires an answer supported by a
   moving call count; FR-010 bounds how long it may be pursued. Explicitly permitted: two symptoms,
   two causes.
2. **Whether `_transmits_a_body` can be tightened on the structural property at zero false-positive
   cost.** The answer is a measurement over `src/` (FR-015), and both outcomes are acceptable
   deliverables. Deciding it here without the count would be exactly the unmeasured adoption the
   guard's own history warns against.

Deliberately **not** left open, because the material decides them:

- *What causes the `#3115` CLI reds* — **decided by measurement**: the console renders at 80 columns
  via `rich`'s `is_dumb_terminal` branch, and the folded uuid stops being a contiguous substring. The
  previous version of this spec left this open and enumerated a candidate-global surface; that
  enumeration is **removed**, not annotated, because it would send implementers hunting a global that
  the measurement has excluded.
- *What triggers that on the runner* — **open, and deliberately not this mission's work.** Stated as
  a limit rather than an open question, because it is not a question this mission's plan answers.
- *Global timeout vs. per-test marks* — decided: **both, with a division of labour.** The default
  (in `addopts`, or scoped to the fast job command lines — FR-016 chooses and states which) is the
  harness backstop, because marks cover only what someone remembered to mark and the failure class is
  the loop nobody anticipated; the counting cap is the actual pin (FR-018), because a timeout is a
  wall-clock statement, not a statement about termination — 1,603 retried empty selections is a
  defect at iteration 3, not at second 30.
- *Harden or document the `/tmp` artifact* — decided: **harden, with the invariant separately pinned**
  (FR-012). A note alone costs the next developer the same hour; a bare skip would let a hostile
  machine silently delete coverage of a consent invariant, which is this codebase's worst documented
  shape.

## Follow-up candidates *(out of scope — record, do not absorb)*

- **The 22 `_isolated_home` fixtures — the successor issue.** Cut from this mission by
  operator decision. The successor must be scoped as an **equivalence-class analysis first**, not a
  convergence: the measured classes are seven incompatible shapes, three return contracts
  (14 `-> None`, 7 `-> Iterator[None]`, 1 `-> Path`), one class-method fixture
  (`tests/specify_cli/identity/test_identity_value_faults_3030.py:294-297`), two contradictory and
  independently-documented `SPEC_KITTY_ENABLE_SAAS_SYNC` policies
  (`tests/sync/test_body_drain_consent_3030.py:51-54` sets it; thirteen files delete it, e.g.
  `tests/specify_cli/sync/test_local_commit_consent_3030.py:78-82`), five callers of
  `reset_coalesce_strategy()`, and three files that pin **no home at all**. It also inherits the
  instrument problem: a **collected-count** acceptance cannot see a fixture *body* change, so the
  successor needs a behavioural acceptance (per-file env-state assertions), not a `grep -c`. Full
  evidence: `notes/post-plan-squad-findings.md`. **Related, and inherited from the same cut**: the
  render-width seam must precede any such convergence, because it is the only guard that would catch
  a hoist changing the victim files' render surface.
- **`egress_allowlist_files: 28` in `tests/architectural/_baselines.yaml:368` is count-anchored**, so
  a *substitution* — one allowlist entry removed and another added — passes the ratchet silently.
  Real, **pre-existing**, and outside this mission's scope. The durable shape is a content hash or a
  set comparison rather than a count.
- **What sets `is_terminal` on the CI runner.** The mission's principal known unknown. A successor
  investigation would start by printing `Console().is_terminal`, `is_dumb_terminal`, `size` and the
  relevant environment from inside a `fast-tests-cli` step.
- **`fast-tests-cli` tolerates `exit 5`** (`|| test $? -eq 5`, `ci-quality.yml:1545`). A selection
  that collects nothing is a green job — the "mechanism reporting success for having done nothing"
  shape, in CI configuration. A collected-count floor would close it.
- **`fast-tests-sync` is path-filtered** (`needs.changes.outputs.sync`, `ci-quality.yml:1101`), so a
  test-only branch can merge with that shard never having run. A required-check or an always-run
  smoke selection would close it.
- **`tests/sync/conftest.py`'s filename-token guard** (`("consent", "capture_gate")`) still enumerates
  *names*; a future per-project pin in a file matching neither token is silently granted consent by
  its own conftest. The durable shape is a marker the test declares. **Armed**: fixing it reds three
  `test_runtime.py` tests whose natural remedy would undo `#3030`'s T028. Needs its own mission.
- **Post-planning WPs have no lane**, so the lane-staleness gate fires inapplicably and the
  pre-review regression gate skips while printing `no_coverage — skipping the gate cheaply`. Either
  register such WPs in `lanes.json` or fall back to diffing `owned_files` against the merge base.
- **The pre-review regression gate's 300s cap and its 5-second serialisation fallback**
  (`src/specify_cli/review/pre_review_gate.py:256`) — the cap is below the runtime of the suites this area touches, and the
  lock degrading to "run anyway" is what recreates the parallel-session false reds. NFR-010 works
  around it here; the fix belongs upstream.
- **CI sharding `tests/sync` and `tests/cli` onto one runner** would reproduce the daemon-reaping
  false reds; a port-range or `SPEC_KITTY_HOME` partition per shard is the prerequisite.
- **`getattr(obj, "name", None)` is invisible to `tests/architectural/test_no_dead_symbols.py`** —
  the same AST blind spot `#3113` is an instance of, in a second guard.
