# Research — Chain-B consent bypass (`Priivacy-ai/spec-kitty#3167`)

**Mission:** `chain-b-consent-bypass-3167-01KZ63HK`
**Baseline:** `upstream/main` `abca7ec96` (2026-08-03T13:46), measured 2026-08-04
**Interpreter:** `/home/jeroennouws/dev/sk-missions/3167/.venv/bin/python` (3.11.15), pytest 9.0.3,
`pytest_timeout` + `xdist` importable.

Every claim below carries the file and line that establishes it. Where a claim could not be
established, it says so and names the command that would settle it.

> **CORRECTED 2026-08-04 after the post-specify adversarial squad.** Two findings in this document
> were wrong and are marked inline below: **§3a's premise** (the gate sits on the *retired* drain,
> which has no production caller) and **§4** (the docstring it called false is true — "the drain" is a
> bound term meaning `delivery/selection.py`). §1's importer count was also wrong. The corrections and
> their evidence are in `analysis-report.md`; the errors are left visible rather than edited away,
> because how they were made is the point. The mission was re-specified as a result.

---

## 1. The two chains

**Chain A — the declared consent seam.** `sync/consent.py:694 consented_project_uuids` answers
*"which of these `project_uuid`s consent to hosted sync?"*. It is keyed on **the data's own project
identity**, never on the checkout. ~~It has **12 importer sites**~~ — **CORRECTED: 8 real call sites**
(`delivery/consent_gate.py:156`, `delivery/selection.py:100`, `sync/__init__.py:369`,
`sync/background.py:296`, `sync/body_upload.py:111`, `sync/emitter.py:2008`,
`sync/local_commit.py:203`, `sync/runtime.py:242`), measured with
`git grep -c 'consented_project_uuids(' -- src/` excluding `sync/consent.py`. The original "12" mixed
call sites with docstring mentions and did not even match its own list of 11 —
`saas_client/egress_consent.py:24`, `tracker/egress_consent.py:26` and `invocation/propagator.py:113`
are prose, and both `egress_consent` modules reach consent indirectly through `sync/__init__.py:369`,
already counted. A before/after comparison against a wrong "before" measures nothing.

**Chain B — the checkout routing chain.** `sync/routing.py:255 is_sync_enabled_for_checkout`
answers *"is sync enabled for the checkout I am standing in?"* via
`resolve_checkout_sync_routing_readonly`, returning `routing.effective_sync_enabled`.

**The repository already states, in its own source, that Chain B is the wrong question for egress.**
`sync/body_upload.py:66-84` — the docstring of the canonical replacement — says verbatim:

> **This replaces `is_sync_enabled_for_checkout(repo_root)`, and both halves of that call were
> wrong.** […] a checkout answers "where am I standing", never "may this project's documents leave",
> and the two differ in exactly the monorepo/worktree/`cd` situations the 2026-07-27 incident
> occurred in.

## 2. The fresh-clone mechanism, in the codebase's own words

`#3167`'s "a fresh clone drains what Chain A denies" is **confirmed**, and the mechanism is named at
`sync/body_upload.py:78-82`:

> The routing chain also honours the repo-slug-keyed `[sync.repo_defaults]` record, which FR-019
> condemns because it is keyed on a mutable git remote — **a fresh clone or a re-`git init` inherits
> a decision nobody made about it.**

So the bypass is not a missing null-check. Chain B has a **structural** grant path (repo-slug →
`[sync.repo_defaults]`) that Chain A does not, and any site still on Chain B inherits it.

## 3. FINDING — the two sites named in the issue are not equivalent, and only one is an egress boundary

This is the mission's central research result. The issue frames `#3167` as *"finish the migration at
the two remaining enforcement sites"*, which implies one change applied twice. It is not.

### 3a. `sync/batch.py:338` — ~~a genuine egress bypass~~ **the RETIRED drain. Premise wrong.**

> **WRONG — corrected 2026-08-04.** The claim below that this gate sits on "the path that POSTs queued
> events to SaaS" is **false**. `batch_sync`/`sync_all_queued_events` have **zero production callers**;
> `sync/__init__.py:61-66` records the journal dispatcher (`delivery/dispatcher.py`) as the **sole**
> event drain, `tests/architectural/test_egress_consent_boundary.py:577-586` allowlists
> `sync/batch.py` as `UNREACHABLE` (E15, "ungated, but unreachable"), and
> `tests/sync/test_no_queue_drain_constructed_3030.py` is a standing AST guard against re-wiring it.
> The gate **is** broken — a squad lens POSTed a non-consenting project's payload through it — but only
> by calling `batch_sync` directly, which is the construction that guard exists to prevent. Broken gate,
> dead path. **I traced what the function does and never asked whether anything calls it.** Everything
> below about the *shape* a per-event fix would need remains accurate and is retained for the record;
> it is no longer this mission's work. See `analysis-report.md` §1.

`_is_checkout_sync_enabled_for_batch()` (`sync/batch.py:335-341`, call site `:1070`) gates the
retired queue-backed drain. It calls `is_sync_enabled_for_checkout()` with **no argument**, so
`start=None` resolves from the process cwd. In a daemon that outlives any `os.chdir`,
cwd is not the project whose events are being drained.

**Why a call swap will not do.** Chain A's entry point takes a `project_uuid`, and the drain handles
a *batch* of events belonging to potentially different projects. The two existing precedents both do
**per-row** resolution, not one boolean:

| Precedent | Location | How it resolves identity |
|---|---|---|
| body queue drain | `sync/background.py:280 _consenting_body_project_uuids` | each task's **stored** `project_uuid`, once per distinct project, fails closed |
| daemon publish | `sync/runtime.py:196 event_project_consents_to_publish` | the **event's own** identity via `resolve_event_project_uuid` |

`sync/background.py:284-286` names the defect the batch site still has, exactly:

> A cwd-derived answer is the defect: in a daemon, a monorepo of worktrees, or any agent session
> that `cd`s between checkouts, it authorizes project B and uploads project A.

**And the hazard to design against is already written down.** `sync/runtime.py:227-229`:

> Membership in the returned subset is checked for *this* uuid rather than the subset being
> non-empty. Equivalent only while exactly one candidate is passed; **the day anyone batches
> envelopes through here, one consenting project would otherwise authorize every other project in
> the batch.**

The drain *is* that batching caller. So the correct shape is: resolve each queued event's
`project_uuid`, ask Chain A once per distinct uuid, and **withhold non-consenting events
individually** — never "the batch is allowed because some project in it consents".

**Feasibility is established, not assumed.** `resolve_event_project_uuid`
(`sync/project_identity.py`, reached at `sync/runtime.py:237`) resolves a `project_uuid` from an
event dict — described at `sync/runtime.py:208` as "T011's single chain, the same resolution the
journal's stored column uses". The drain's rows are event dicts from the `queue` table
(`sync/queue.py:651`, drained by `drain_queue` at `sync/queue.py:1570`). Identity is reachable
per event via the same resolver the publish seam already uses.

**Note on the event queue schema:** unlike `body_upload_queue`, which carries a dedicated
`project_uuid TEXT NOT NULL` column (`sync/queue.py:1031`), the event `queue` table
(`sync/queue.py:651`) does not — event identity is resolved from the envelope/payload via the
dotted-path mechanism (`NAMESPACE_PROJECT_UUID = "namespace.project_uuid"`, `sync/queue.py:55`,
resolver documented at `:325-326`). **Consequence:** per-event resolution is a read of the event
body, not a column select, so the cost is per-row deserialization the drain already performs.

### 3b. `sync/runtime.py:106` — auto-start, and the code explicitly forbids conflating it with consent

`:106` sits inside the **sync auto-start** decision (*"should the daemon start itself?"*), not an
egress gate. `sync/runtime.py:139-148` `_read_project_auto_start` states the boundary in binding
terms:

> `sync.auto_start` is NOT consent and must never be unified with `sync.enabled`. […] It answers
> "should the daemon start itself?" — a runtime convenience. `sync.enabled` answers "may this
> project's data leave the machine?". **Collapsing the two would let an autostart preference grant
> hosted-sync consent, which is the class of mistake `#3030` exists to close.**
>
> (Backticks added 2026-08-04: the source reads bare, and quoting it bare here minted a mandatory
> issue-matrix row for `#3030` that this mission cannot resolve. The merge gate reads the multi-file
> `discover_issue_references`, not the `spec.md`-only detector originally run.)

And `runtime.py`'s *actual* egress boundary is already on Chain A: `event_project_consents_to_publish`
at `:196`, the single predicate behind both daemon publish seams.

**So `#3167`'s premise is half right.** Starting a daemon is not egress; every publish through it is
independently gated at `:196`. Whether `:106` should *additionally* consult consent is a
defence-in-depth question, not a bypass closure — and routing it onto Chain A means answering "which
project?" at a point where only a checkout root is in scope, which is the very derivation
`body_upload.py:73-76` condemns.

**This is a scope decision for the spec, escalated rather than absorbed — see §6, D-M5a-1.**

## 4. ~~A documented-but-false claim~~ — **WITHDRAWN. The claim is true; I mis-read a bound term.**

> **WRONG — withdrawn 2026-08-04.** "The drain" is bound in this repo to `delivery/selection.py`,
> which **is** on Chain A, so the docstring is **true as written**. Spelled out verbatim at
> `sync/__init__.py:343-344` ("the same funnel the drain (``delivery/selection.py``) and the emitter
> use") and `tracker/egress_consent.py:26-27`. `FR-008` would have rewritten a correct docstring, and
> the natural rewrite would then have asserted coverage for a module with no live caller —
> *manufacturing* the very defect class User Story 4 existed to remove. The real residual is a
> terminology one: "the drain" has three referents (`delivery/selection.py` dispatch selection,
> `sync/background.py:280` body upload, `sync/batch.py` the retired event drain) and no glossary
> entry — the overload class `docs/context/orchestration.md#routing` already governs for "routing".

`sync/runtime.py:203-205` asserts that Chain A is

> the same seam the capture gate, **the drain**, the body upload and the LocalCommit flush use, so no
> second representation of consent is created (C-003).

The body upload, capture gate and LocalCommit flush do walk Chain A (§1). **The drain does not** —
`sync/batch.py:338` walks Chain B. So the source claims a unification that is not in place, and a
reader auditing C-003 compliance by reading that docstring would conclude the drain is covered.

**Deliverable regardless of scope outcome:** the claim is corrected, or made true. It must not be
left asserting a coverage that does not exist.

## 5. Existing coverage — what would have caught this, and why it did not

**UNVERIFIED — settle before planning work packages.** Establish, with the input count quoted:

```bash
.venv/bin/python -m pytest tests/sync -k 'batch and (consent or drain)' --collect-only -q > /tmp/c.txt 2>&1; tail -5 /tmp/c.txt
git grep -ln '_is_checkout_sync_enabled_for_batch\|is_sync_enabled_for_checkout' -- tests/
```

Per the standing rule, any assertion that coverage is absent must establish why it would otherwise
have been present — so this is a collection count, not an impression.

## 6. Open questions and risks — these feed `tasks` directly

| ID | Question | Why it cannot be settled inside implementation |
|---|---|---|
| **D-M5a-1** | Does `runtime.py:106` change at all? Options: **(a)** leave Chain B with a comment naming why auto-start is not an egress boundary and pointing at `:196`; **(b)** add a consent consult as defence-in-depth, accepting a checkout-derived "which project"; **(c)** remove the routing consult entirely and let `:196` be the sole gate. | §3b: the code carries a binding statement that auto-start and consent must not be unified. Picking (b) trades against it. **Operator/architect call.** |
| **R-1** | Per-event filtering changes drain semantics: a batch may now be *partially* withheld. What happens to withheld rows — left queued, or marked? Leaving them queued risks an unbounded retry loop for a project that will never consent. | Design decision with a durable-state consequence; needs the spec, not an implementer's judgement. |
| **R-2** | `_is_checkout_sync_enabled_for_batch` wraps in `except Exception: return False` (fails closed, correct). Per-event resolution must preserve fail-closed **per event**, not collapse to "drain nothing on any error" if that would starve consenting projects. | Two defensible readings; the fail-closed rule says deny, the starvation risk says isolate. Spec must choose explicitly. |
| **R-3** | The batch site is reached from a daemon. Any test must not depend on cwd, or it will pass for the wrong reason — the exact defect under test. | Test-design constraint to carry into every work package. |
| **R-4** | This mission owns `tests/sync/conftest.py`, `tests/sync/test_runtime.py`, `tests/sync/test_lifecycle_readiness.py` — the FR-007 leak-guard host plus 3 of M3's 12 pinned leaks (`tests/sync/_leak_guard.py:420, :442, :452`). Edits here move M3's baseline. | Cross-mission hazard H1. Already resolved by serialisation (this mission lands before M3's WP01, operator decision D3=a), but every work-package brief must name it. |

## 7. Standing rules carried into every work package of this mission

- Never pipe a suite whose exit status you intend to trust — redirect, quote the `N passed` line.
- Pin the interpreter: `.venv/bin/python -m pytest`. Quote `sys.executable` and the `plugins:` header
  for anything load-bearing.
- **Red first**, and make the red *the consequence* (an event that leaves) — not a boolean flip.
- Include a **positive control that must pass**: a consenting project's events still drain. A fix
  that withholds everything satisfies every refusal assertion and is the failure mode
  `Priivacy-ai/spec-kitty#3174` documents elsewhere in this program.
- Any assertion of absence must establish why the thing would otherwise have happened.
- Do not run `tests/sync` and `tests/cli` sessions concurrently — real daemons, `pgrep`/port scans,
  16 recorded false reds. `pgrep -af 'run_sync[_]daemon'` before every measurement (ports 9400-9402);
  put reaps in a **script file**, never a bare `pkill -f`.
- Explicit-path staging: `git add <paths>`, never `git add -A`.
- Cite issues as `owner/repo#NNNN` — a bare `#NNNN` in `spec.md`, `plan.md`, `research.md` or
  `tasks/*.md` mints a mandatory issue-matrix row this mission cannot resolve.
- File follow-up issues for anything out of scope rather than absorbing it.
