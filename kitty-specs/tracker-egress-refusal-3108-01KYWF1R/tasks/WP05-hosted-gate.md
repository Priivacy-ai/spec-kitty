---
work_package_id: WP05
title: 'The hosted gate: Channel 2 as a narrowing conjunct (lands alone)'
dependencies:
- WP04
requirement_refs:
- C-002
- C-011
- C-016
- FR-004
- FR-016
- NFR-005
planning_base_branch: bundle-c-tracker-refusal-3108
merge_target_branch: bundle-c-tracker-refusal-3108
branch_strategy: Planning artifacts for this mission were generated on bundle-c-tracker-refusal-3108. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into bundle-c-tracker-refusal-3108 unless the human explicitly redirects the landing branch.
created_at: '2026-08-01T00:20:00+00:00'
subtasks:
- T028
- T029
- T030
- T031
phase: Stage 5 - The hosted gate
history:
- at: '2026-08-01T00:20:00Z'
  actor: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: python-pedro
authoritative_surface: src/specify_cli/tracker/saas_client.py
create_intent: []
execution_mode: code_change
model: claude-sonnet-5
owned_files:
- src/specify_cli/tracker/saas_client.py
role: implementer
tags: []
task_type: implement
tracker_refs:
- '3108'
---

# Work Package Prompt: WP05 – The hosted gate: Channel 2 as a narrowing conjunct (lands alone)

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and
behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`

---

## Objective

Swap the hosted tracker chokepoint at `SaaSTrackerClient._request` from calling
`project_egress_refusal(self._project_root)` directly to calling

```python
tracker_egress_verdict(self._project_root, destination=EgressDestination.HOSTED_SERVICE)
```

so that a committed `tracker: {egress: refused}` **refuses** at the hosted destination while a
committed `tracker: {egress: permitted}` **grants nothing** there — and Channel 1 (hosted-sync
consent) remains a hard prerequisite, byte-for-byte unchanged.

**This is the highest-consequence edit in the Mission and the one with the least new value.** It
changes no verdict for any Channel-1 state. Every existing refusal string must reproduce
byte-identically. A Mission that closes the local gap while perturbing the shipped `#3030` hosted
gate has traded one leak for another.

## Owned files — a hard boundary

You may write **exactly one file**:

- `src/specify_cli/tracker/saas_client.py`

You may **not** edit any test file, any other source file, `CHANGELOG.md`, or any dossier file.
Other work packages own them and **one live agent per file** is a standing rule of this Mission.
In particular:

| File | Owner | What you do with it |
|---|---|---|
| `tests/sync/tracker/test_tracker_egress_refusal_3108.py` | WP01 | **Run it. Never edit it.** It holds the US5 pins this WP flips. |
| `tests/sync/tracker/test_saas_client_consent_gate_3030.py` | pre-existing, unowned | **Run it. Never edit it.** It is the detection signal for a perturbed hosted gate. |
| `src/specify_cli/tracker/egress_verdict.py` | WP03 | Import from it. Never edit it. |
| `src/specify_cli/tracker/local_service.py` | WP04 | Never touch it. |

If a pin this WP needs does not exist in a file you do not own, **stop and report it** — do not
author it yourself.

## What you may assume is already true (dependencies)

WP05 depends on **WP04**, and transitively on WP01, WP02 and WP03. Therefore:

- `src/specify_cli/tracker/egress_verdict.py` exists and exports `EgressDestination` (a closed
  two-member enum: `LOCAL_SUBPROCESS`, `HOSTED_SERVICE`) and
  `tracker_egress_verdict(root: Path | None, *, destination: EgressDestination)` returning a verdict
  value object with at least `refused: bool`, `refusing_channels`, `destination`, the Channel-1
  state, the Channel-2 state plus raw value, `message: str` and ordered remedies.
- The verdict function **never raises** (NFR-003) — including for `root=None`, an unreadable file, an
  unparseable file, a non-mapping `tracker:` block, and a mapping or a list **at the `egress` key**.
- `root=None` at `HOSTED_SERVICE` with Channel 2 absent answers with text **byte-identical to
  `UNDETERMINED_PROJECT_REFUSAL`**, and WP03 pins those bytes. `self._project_root` on
  `SaaSTrackerClient` is `Path | None`, so `_request` can pass `None`.
  **Do not carry forward the claim that `_request` is the only site that can** — it is true today
  and **false once WP06 lands**, because the doctor renderer resolves its root with
  `locate_project_root(Path.cwd())` (the call its sibling makes at `sync.py:1786`), which returns
  `None` outside a checkout, at **both** destinations. WP03 specifies both `root=None` cells for
  exactly that reason. Nothing in your swap depends on the exclusivity claim; it is dropped so it
  does not get repeated into a guard or a docstring.
- The three local gates in `local_service.py` already call `tracker_egress_verdict` with
  `destination=EgressDestination.LOCAL_SUBPROCESS`, so the verdict function has already been
  exercised end to end by the local path before you touch the shipped hosted gate.
- The acceptance suite `tests/sync/tracker/test_tracker_egress_refusal_3108.py` already contains the
  **US5** cells, authored red-first by WP01 against the un-gated tree.

## Requirements this WP satisfies

Quoted or tightly paraphrased from `spec.md`.

**FR-016 — The hosted path keeps Channel 1 exactly and gains Channel 2 as a narrowing conjunct.**
> "I want `tracker/saas_client.py`'s chokepoint at `_request` (`:329-331`) to consult
> `tracker_egress_verdict(self._project_root, destination=EgressDestination.HOSTED_SERVICE)` instead
> of `project_egress_refusal` directly. **The destination literal is unconditional** — there is no
> branch, no provider read and no configuration under which `_request` can ask about anything else,
> which is what makes the hosted half of FR-004 structural rather than conventional. The Channel-1
> half of the verdict must produce **byte-identical** refusal text to today's for the three measured
> outcomes (absence → refused; recorded `false` → refused; recorded `true` → gate passes to the token
> check), including the `root=None` case, which must reproduce `UNDETERMINED_PROJECT_REFUSAL`
> exactly. `SaaSTrackerService` and every other line of `saas_client.py` are untouched, the gate
> stays **before** `_fetch_access_token_sync()`, and `TrackerEgressRefusedError` keeps its identity
> and base class."

**FR-004 — Polarity follows the destination, and the destination is a parameter, not a derivation.**
At `HOSTED_SERVICE` Channel 2 is **narrowing only**: it may refuse, it may not grant, and Channel 1
remains a hard prerequisite — because the hosted tracker path **does not talk to Jira; it talks to
spec-kitty's hosted service**, which holds the connector and relays (`saas_client.py:247` resolves
`_base_url` from `resolve_runtime_target().resolved_server_url`; every endpoint is
`/api/v1/tracker/…` with a bearer token and `X-Team-Slug`).

**C-002** — "Any implementation in which a tracker key can widen egress **to spec-kitty's hosted
service** is out of contract"; and "any implementation that computes the destination from a
configuration read is out of contract, regardless of the answers it happens to give."

**C-016** — Delivered: permit hosted sync / refuse tracker (US1), and refuse-or-never-record hosted
sync / permit the local tracker (US2). **Not delivered:** a SaaS tracker binding without hosted-sync
consent. Channel 1 remains a hard prerequisite there **by design**, and WP08 states it in the upgrade
note as a decided limitation. Your job is to make that limitation true in code, not to soften it.

**NFR-005** — `ruff check` and `mypy --strict` clean on new code, no blanket suppressions.
`mypy --strict` carries extra weight here: the `EgressDestination` parameter is the mechanism by
which FR-004's polarity becomes type-checked, so a `mypy` failure on the destination argument is a
**contract** failure, not a lint failure.

**Success criteria touched**: SC-005, SC-005a, SC-016. SC-010's hosted half (a fault refuses at both
destinations) rides on the same swap.

---

## Measured hazards — carried verbatim, not summarised

### H-A. WP05 must land alone. That is a *necessity*. Landing it after the local gate is a *preference*.

From `plan.md` Stage 5, which separates the two claims because a previous revision fused them and
made the preference look load-bearing and the necessity look optional:

- **Necessity — alone.** "Its detection signal is a byte-comparison against the shipped `#3030`
  refusal strings. A co-landing change makes any difference unattributable. **Unprovable
  otherwise:** SC-016's byte-identical claim for the three measured Channel-1 outcomes plus
  `root=None`." Restated in IC-06: "a red in
  `tests/sync/tracker/test_saas_client_consent_gate_3030.py` must be attributable to the swap and to
  nothing else."
- **Preference — after Stage 4.** "It is the shipped `#3030` gate, the highest-consequence edit in
  the Mission and the one with the least new value. Doing it against a verdict function already
  exercised by the local path is safer, but **nothing technical forbids the reverse order**."

Practically: your change set contains **`src/specify_cli/tracker/saas_client.py` and nothing else**.
Do not fold in a docstring fix elsewhere, a lint cleanup, or a "while I was here". Stage with
explicit paths.

### H-B. The hosted red cannot be an HTTP count.

From `plan.md` *Open Items* 3 and the Red-First table:

> "`_request` raises at `_fetch_access_token_sync()` before any HTTP is attempted, so **'0 HTTP
> attempts' is already green on the base** for a `jira` binding with a committed
> `tracker: {egress: refused}`. **Reading adopted:** the red-first pin for the SaaS half is the
> **exception type and message** (`TrackerEgressRefusedError` naming Channel 2, versus today's
> `No valid access token`); the HTTP count is retained as a supporting non-vacuity assertion, proven
> to bind by US5 sc3's control."

So when you observe the red in T028, **quote the exception type and the message text**. An
observation that reports "0 HTTP attempts" as the red is no measurement — it was already true.

### H-C. `destination` is passed as a literal, unconditionally, and is structurally incapable of anything else.

`saas_client._request` passes `HOSTED_SERVICE`. It must **never** be derived. The reason is measured:

```
PRECONDITION on-disk provider : 'beads'
SUBJECT backend class         : SaaSTrackerService
SUBJECT in-memory cfg.provider: 'jira'
SUBJECT on-disk cfg.provider  : 'beads'   <-- what a config-reading verdict() would have seen
CONTROL (disk=jira) backend   : SaaSTrackerService
NEGATIVE CONTROL              : TrackerServiceError raised for 'beads' (the probe discriminates)
```

`TrackerService._resolve_saas_backend_for_provider` (`service.py:84-98`) substitutes
`TrackerProjectConfig(provider=provider)` **in memory** when `--provider <saas>` is passed and never
rewrites the file. Three operator-reachable commands take that path, all with `allow_unbound=True`:
`list-tickets --provider` (`cli/commands/tracker.py:998-1007` → `service.py:220` →
`saas_client.py:613` → `_request`), `issue-search --provider` (`tracker.py:369-386` →
`service.py:214`), `map list --provider` (`tracker.py:942-963` → `service.py:210`).

A config-derived destination reads `beads` on all three, applies the **local** half, and turns
`tracker.egress: permitted` into an **affirmative grant to spec-kitty's hosted service with Channel 1
absent** — reopening `#3030`'s P0 boundary through the very key introduced to protect it, for exactly
the operator US2 exists to serve. **No branch. No provider read. No `if`. One literal.**

### H-D. Import form is load-bearing on guard G5.

`EgressDestination` is imported **under its own name**:

```python
from specify_cli.tracker.egress_verdict import EgressDestination, tracker_egress_verdict
```

An aliased import (`import … as ED`, or `from specify_cli.tracker import egress_verdict as ev`) makes
the `destination` argument an `Attribute` on the alias, and WP07's guard G5 reports non-literal — a
**false red**. Loud rather than silent, but a lost afternoon for anyone who has not been told.

### H-E. `from X import f` rebinds by value — and this WP moves the patch target.

C-007, measured at `bb2020fea`: `project_egress_refusal` is bound **by value** into its consumers
(`tracker/saas_client.py:34`, `saas_client/client.py:23`). After patching
`specify_cli.tracker.egress_consent.project_egress_refusal`,
`TSC.project_egress_refusal is TE.project_egress_refusal` → **`False`**.

The hosted path therefore has **two patch targets that apply at different times, because this WP
deletes the first**:

| Path | Target **before** your swap | Target **after** your swap |
|---|---|---|
| hosted (`saas_client._request`) | `specify_cli.tracker.saas_client.project_egress_refusal` | `specify_cli.tracker.saas_client.tracker_egress_verdict` |

"A recipe naming only the first is **correct on the base and inert on the delivered tree** — which is
the shape of a mutation that silently lies." If you write any probe or mutation while measuring,
patch the **deciding module's** name (`specify_cli.tracker.saas_client.…`), never the defining
module's, and report the per-site split.

### H-F. `saas_client/egress_consent.py:92` is a second definition, not a re-export.

C-008, measured: different `id`, different `__module__` from `tracker/egress_consent.py:147`. This WP
adds **no third definition**; the `saas_client/` package is **not touched**. Recorded because
conflating a second definition with a re-export produces a patch-site table that is wrong for one of
the two.

---

## Standing rules — binding on every measurement you take

These are quoted from `spec.md` C-011 and `plan.md` *Measurement rules*. They are not advice.

- **Revalidate every line citation before you trust it (C-011).** Every `file.py:NNN` in this
  prompt was taken at the measurement base **`bb2020fea`** — recorded as `measurement_base_sha` in
  `wps.yaml`, so the drift diff is derivable rather than transcribed:
  `git diff --stat bb2020fea..<your base> -- <the paths you cite>`. Implementation runs on a **later**
  base. Re-derive every citation **by symbol name (`grep`), never by line number**, *before* any step
  that depends on it. **A line that moved is bookkeeping. A symbol that moved *semantically* — a
  changed signature, a relocated gate, a changed default, a new caller — is a re-plan trigger**, and
  the correct response is to stop and re-plan, not to patch the citation and continue. Four drifts
  were already found at `bb2020fea` itself, which is the evidence that this is necessary rather than
  ceremonial.
- **Never pipe a suite whose exit status you intend to trust.** `pytest … | tail` reports `tail`'s
  status and buffers until exit. **Quote the `N passed` line.** An **empty output file is no
  measurement**.
- **A killed run is neither a pass nor a fail.** Re-run it narrowed; do not explain it.
- **Measure in a `git worktree` pinned to a commit — and set `PYTHONPATH=$WT/src`.** The editable
  install hard-codes the **main checkout's** src path, so a worktree run otherwise imports the live
  tree and any "identical results" conclusion is a tautology.
- **Read the failure text, not the tally.**
- **Print the input count alongside any "all checks passed"** — a gate that ran on zero files passes
  vacuously.
- **Red first, and make the red the consequence.** Assert the bytes, not a boolean.
- **Include a positive control that must pass.**
- **Any assertion of absence must establish why the thing would otherwise have happened.**
- **Control your diagnostic** — run any probe against a case whose answer you already know before
  trusting it.
- **Mutations as pytest plugins via `PYTHONPATH`, never source edits**, and never source edits during
  a verification run.
- **Five recorded ways a mutation silently lies** — check each: (1) the architecture moved and the
  patched gate became a redundant second → all-green reads as "your pin is fine"; (2) the reds are
  `TypeError`s from a changed signature, not assertion failures; (3) the mutant hard-codes a value the
  tests **vary** → no-ops for exactly the tests most likely to catch the defect; (4) the branch is
  unreachable on the local interpreter and **live on CI's** (3.11/3.12 vs 3.14) → zero binds means
  *your environment differs*, not *the code is dead*; (5) **`from X import f` rebinds by value** →
  patching the defining module leaves the *deciding* module inert; patch every name a symbol is
  reachable by and report the per-site split.
- **Explicit-path staging.** `git add <paths>`, never `git add -A` — 13 files were lost to a stray
  `add -A` in this lineage.
- **`ruff format` is NOT clean on this repo** (`line-length = 164`); only `ruff check` is meaningful.
  New code must pass `ruff` and `mypy --strict` with no blanket suppressions.
- **One live agent per file.**
- **Known pre-existing failures — do not chase, do not fix in-PR, do not retry to green:**
  `tests/architectural/test_tid251_enforcement.py` (4 tests);
  `test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out`;
  two `test_safe_commit_cmd::…_3033`;
  `test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed`;
  `test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock, fails under load).
  `ModuleNotFoundError: No module named 'typer'` in subprocess daemon tests is environmental.

---

## Subtasks, in execution order

### T028 — Pin the base, revalidate the citations, and observe the red

1. **Record the actual base SHA.** Every citation in this dossier was taken at `bb2020fea`;
   implementation is on a later base. Run
   `git diff --stat bb2020fea..<base> -- src/specify_cli/tracker/` and re-derive the cited lines
   **by symbol name (`grep`), never by line number**. A citation whose line moved is a bookkeeping
   fix; a **symbol that moved semantically** — a changed signature, a relocated gate, a changed
   default — is a **re-plan trigger**, not something to patch in passing.

2. **Confirm the shipped shape.** In `src/specify_cli/tracker/saas_client.py`, locate `_request` and
   confirm it currently reads:

   ```python
   refusal = project_egress_refusal(self._project_root)
   if refusal is not None:
       raise TrackerEgressRefusedError(refusal)

   access_token = _fetch_access_token_sync()
   ```

   Confirm the module-level import `from specify_cli.tracker.egress_consent import
   project_egress_refusal` and that `TrackerEgressRefusedError` is a `SaaSTrackerClientError`
   subclass (itself a `RuntimeError`) carrying `error_code="project_consent_denied"`.

3. **Record the Stage-0 number for the hosted gate suite, on its own.** Run, unpiped, exit status
   trusted:

   ```
   pytest tests/sync/tracker/test_saas_client_consent_gate_3030.py -q
   ```

   **Quote the `N passed` line.** This file's count is otherwise folded invisibly into the 519 of
   `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py`, and Stage 5's exit criterion cites
   *this* number, not that one.

4. **Observe the red — and make sure it is the right red.** Run WP01's US5 cells from
   `tests/sync/tracker/test_tracker_egress_refusal_3108.py` (do **not** edit that file):

   - **US5 sc1** — `jira` binding, hosted-sync consent **granted**, committed
     `tracker: {egress: refused}`, `spec-kitty tracker sync push`. On the pre-swap tree this must
     fail, and **the red is the exception type and message**: today it reaches
     `No valid access token`; the required behaviour is `TrackerEgressRefusedError` whose message
     names **Channel 2**. **Quote the failure text.** Do not report "0 HTTP attempts" as the red —
     that is already green on the base (H-B).
   - **US5 sc4 / SC-005a** — on-disk `provider: beads`, committed `tracker: {egress: permitted}`,
     hosted-sync consent **absent**, `spec-kitty tracker list-tickets --provider jira`.

     **SC-005a is GREEN BEFORE AND AFTER. It is not one of your reds, and an earlier draft of this
     step said otherwise.** Measured: `_request` calls `project_egress_refusal(self._project_root)`
     at `saas_client.py:329-331` — **before** `_fetch_access_token_sync()` at `:333` — and
     `SaaSTrackerService` constructs its client with a **non-`None`** `project_root=repo_root`
     (`saas_service.py:110`). So on the **pre-swap** tree, with Channel 1 absent, this cell
     **already refuses, already at 0 HTTP, already naming Channel 1**. It does not reach the token
     check. **Confirm that, quote it, and record it as green-before.**

     **What the cell is worth, stated exactly, so you do not go looking for a red that does not
     exist.** It reds **only on a destination-as-derivation implementation** — one that reads
     `beads` off disk, applies the **local** half of FR-004, and **grants**. Its evidentiary value
     is therefore **contingent on the guards** (WP07's G5 pinning every call site's `destination` to
     a literal member, G6 pinning the verdict body free of provider reads), **not** on a
     red-then-green transition. Your obligation is that it is **still green after your swap, for the
     same reason and with the same wording** — which is a real obligation, because a config-derived
     `verdict()` would flip it. **The specific pin you observe red-then-green is US5 sc1**, whose
     red is the exception type and message.
   - **US5 sc3 — the positive control that must pass, before and after:** `jira` binding, hosted-sync
     consent **granted**, **no** tracker key → the gate passes and the call fails later at
     `No valid access token`. Without it, the zero-HTTP counts in the refusing members are vacuous.
   - **SC-005a's positive control** — on-disk `provider: jira`, Channel 1 **granted**, no tracker key,
     same `list-tickets --provider jira` command → reaches `No valid access token`.

   If any of these cells is absent from WP01's file, **stop and report**. Do not author them.

**Exit for T028:** base SHA recorded; citations re-derived by symbol; the `N passed` line for
`test_saas_client_consent_gate_3030.py` quoted; the US5 sc1 red quoted **as an exception type and
message**; the two positive controls confirmed green on the pre-swap tree; the interpreter version
recorded beside every count.

---

### T029 — The swap, and nothing else in the file

In `src/specify_cli/tracker/saas_client.py`:

1. **Replace the module-level import.** Remove
   `from specify_cli.tracker.egress_consent import project_egress_refusal` **only if `grep` confirms
   no other use of the name survives in this file**; add

   ```python
   from specify_cli.tracker.egress_verdict import EgressDestination, tracker_egress_verdict
   ```

   under its own name — never aliased (H-D).

2. **Replace the gate body in `_request`**, keeping its **position unchanged** — still the first
   thing `_request` does, still **before** `_fetch_access_token_sync()`:

   ```python
   verdict = tracker_egress_verdict(
       self._project_root,
       destination=EgressDestination.HOSTED_SERVICE,
   )
   if verdict.refused:
       raise TrackerEgressRefusedError(verdict.message)
   ```

   The `destination` argument is an **unconditional literal**. There is no branch, no provider read,
   and no configuration under which `_request` can ask about anything else (H-C).

3. **`TrackerEgressRefusedError` keeps its identity and base class**, including
   `error_code="project_consent_denied"` and every other constructor argument the current raise site
   supplies. Existing callers already handle `SaaSTrackerClientError` — `tracker/origin.py` converts
   it to `OriginBindingError`, `saas_service.py` to `TrackerServiceError` — and a refusal must keep
   degrading along the paths the codebase already has.

4. **Do not touch anything else.** `SaaSTrackerService`, the endpoint constants, the retry
   behaviour, the header merge, the `httpx` client construction, the operation poller — **every other
   line of the file is untouched.** `git diff` on this file must show one import change and one
   statement-block change.

5. **`self._project_root` is `Path | None`.** Pass it through unchanged. Do not coerce, do not
   default, do not `or Path.cwd()`. The verdict answers `None` as `HOSTED_SERVICE` with Channel 2
   absent, producing text byte-identical to `UNDETERMINED_PROJECT_REFUSAL`. (A `or Path.cwd()`
   here would silently answer about **whatever directory the process happens to be in** — which is
   the exact class of defect `UNDETERMINED_PROJECT_REFUSAL` exists to refuse.)

**Exit for T029:** `git diff --stat` shows exactly one file changed; `git diff` shows only the import
line and the gate block; `mypy --strict src/specify_cli/tracker/saas_client.py` clean with no
`# type: ignore` added.

---

### T030 — Prove byte-identity for the three Channel-1 outcomes plus `root=None` (SC-016)

The point of this subtask is that the swap **changed nothing an existing operator can observe**.

1. **Run the shipped hosted-gate suite, unpiped:**

   ```
   pytest tests/sync/tracker/test_saas_client_consent_gate_3030.py -q
   ```

   **Quote the `N passed` line and assert it equals the number recorded in T028 step 3.** Any red
   here, or any change in count, is R-09 firing: the swap perturbed the shipped `#3030` gate. Do not
   edit that file to make it pass — investigate the swap.

2. **Byte-compare the refusal strings across the swap.** Write a throwaway probe under your
   scratchpad directory (**not** committed, **not** under `tests/`) that, for each of the four
   measured cases, captures `str(exc)` from `_request` on the pre-swap tree and on the post-swap tree
   and compares the bytes:

   | Case | Pre-swap behaviour | Required post-swap behaviour |
   |---|---|---|
   | project-local consent **absent** | refused, `error_code=project_consent_denied`, no HTTP | **byte-identical** refusal text |
   | committed `sync: {enabled: false}` | refused, `error_code=project_consent_denied`, no HTTP | **byte-identical** refusal text |
   | committed `sync: {enabled: true}` | gate passes → `No valid access token` | **unchanged** — gate passes to the token check |
   | `self._project_root is None` | `UNDETERMINED_PROJECT_REFUSAL` | **byte-identical** to `UNDETERMINED_PROJECT_REFUSAL` |

   Measure the pre-swap side in a **`git worktree` pinned to the base commit with
   `PYTHONPATH=$WT/src`** — otherwise the editable install imports your live tree and "identical
   results" is a tautology.

   **The third row is the positive control.** Without it, rows 1, 2 and 4 are indistinguishable from
   a probe that never reached the code. **Control your diagnostic:** before trusting the comparison,
   run it against a case whose answer you already know (deliberately corrupt one expected string and
   confirm the probe reports a difference).

3. **Re-run the US5 cells** from WP01's acceptance file and confirm the red-then-green transition:

   - **US5 sc1** now raises `TrackerEgressRefusedError` naming Channel 2 — quote the message.
   - **US5 sc2** — `jira`, Channel 1 **absent**, committed `tracker: {egress: permitted}` — still
     refuses with **0** HTTP attempts, the message names **Channel 1**, *and additionally states that
     a tracker grant is recorded and does not apply to the hosted destination*. This is the FR-005
     "reported no-op" clause: `permitted` at `HOSTED_SERVICE` grants nothing and must be **reported**
     as granting nothing, never silently dropped.
   - **US5 sc3** — still green, still reaching `No valid access token`.
   - **US5 sc4 / SC-005a** — **still** refuses naming **Channel 1**, with **0** HTTP attempts,
     together with its positive control (on-disk `jira`, Channel 1 granted, no key → `No valid
     access token`). **Green before, green after.** What you are proving here is that the swap did
     not turn it into a grant — not that it changed.
   - **US5 sc5 — SC-010's hosted half, end to end.** WP01 authors **one** representative near-miss
     cell in the acceptance file: `jira`, Channel 1 granted, committed `tracker: {egress: refuse}`
     (the singular). Re-run it and confirm it flips **red → green**: refuses at `HOSTED_SERVICE`
     **without raising anything but `TrackerEgressRefusedError`**, with a fault message naming the
     key, quoting `refuse` **verbatim**, and naming **both** legal values `refused` and `permitted`.
     Quote the message.

     **The remaining fourteen probed values are NOT re-asserted here, and that is a decision, not an
     omission.** You own **no test file** — `wps.yaml` gives you `saas_client.py` and nothing else —
     so a step telling you to "confirm SC-010's hosted half" across the whole probed set would be a
     step you can only discharge by authoring a pin in a file this WP's own escalation rule forbids
     you to touch. The full 15-value coverage is discharged **at the unit level by WP03's
     fault-wording pins, which run for BOTH destinations** (WP03 T019 step 3, over every near-miss
     in the probed set), plus **your swap**, which is what makes `HOSTED_SERVICE`'s transport
     consult that verdict at all. US5 sc5 is the end-to-end sample that proves the two are joined.
     **If US5 sc5 is absent from WP01's file, stop and report** — do not author it.

4. **The HOSTED bind counter becomes non-zero — that is your swap's doing, and only yours.**
   WP01 installed a second delegating wrapper on **`specify_cli.tracker.saas_client.tracker_egress_verdict`**
   and asserted it non-zero in every US5 cell. Before your swap that name does not exist and the
   counter is 0; the import line in T029 step 1 is what creates it. **Bind it under exactly that
   name and do not rename it** (`from X import f` rebinds by value — a differently-spelled binding
   leaves WP01's counter reading 0 forever, which is indistinguishable from a gate never entered).
   Confirm the counter is non-zero in the US5 cells and **report the per-site split** (C-007): the
   local name in `local_service` and the hosted name here are **two different objects**, and a probe
   that patches one says nothing about the other.

**Exit for T030:** `test_saas_client_consent_gate_3030.py` green at its T028 number, quoted; the
four-row byte-comparison table filled in with actual bytes and its positive control passing; the US5
cells observed red-then-green with their failure texts quoted — **except SC-005a, recorded green
before and green after**; the hosted bind counter non-zero in the US5 cells, with the per-site split
reported.

---

### T031 — Quality gates, blast-radius check, and staging

1. **Quality gates (NFR-005, IC-11):**
   - `ruff check src/specify_cli/tracker/saas_client.py` — clean. **No blanket `# noqa`**, no
     per-file ignore additions.
   - `mypy --strict src/specify_cli/tracker/saas_client.py` — clean, **no `# type: ignore` added to
     achieve it**. A `mypy` error on the `destination` argument is a **contract** failure, not a lint
     failure.
   - Do **not** run `ruff format` and do not treat a formatting diff as evidence — `ruff format` is
     not clean on this repository (`line-length = 164`).
   - Complexity: `_request` must not gain a branch. The verdict call plus one `if verdict.refused:`
     replaces the existing `refusal is not None` check one-for-one; net branch count unchanged.

2. **Blast-radius re-measurement, each with its prediction** (a re-measurement without a prediction
   has no control; an **unpredicted** movement is a **stop-and-attribute event**):

   | Suite | Prediction |
   |---|---|
   | `tests/sync/tracker/test_saas_client_consent_gate_3030.py` | **unchanged** at its T028 number |
   | `tests/sync/tracker/ tests/agent/cli/commands/test_tracker.py` | **unchanged** (baseline `519 passed` at `bb2020fea`; re-derive at your base) |
   | `tests/specify_cli/` | **unchanged** (baseline `35 passed` at `bb2020fea`) |

   Run each **unpiped** and **quote the `N passed` line**. Then run the new acceptance suite **twice
   — alone, and inside a full `tests/sync/tracker/` run**. A discrepancy between the two is
   cross-test pollution (the `#3115` class), not this Mission — it is a finding to **report**, not to
   chase to green.

3. **Confirm the land-alone necessity holds.** `git status` and `git diff --stat` must show
   **`src/specify_cli/tracker/saas_client.py` and nothing else**. Stage with explicit paths:

   ```
   git add src/specify_cli/tracker/saas_client.py
   ```

   **Never `git add -A`.**

4. **Do not chase the known pre-existing failures** listed in the Standing rules above. If you
   encounter a *new* pre-existing failure, **file it as an issue before treating it as baseline**
   (charter Pre-existing Failure Reporting Rule), and confirm it by running the same test against the
   merge-base with `PYTHONPATH=<worktree>/src`.

---

## Exit criterion for WP05

Copied from `plan.md` Stage 5, and it is the bar this WP is judged against:

> **Exit criterion for Stage 5:** `tests/sync/tracker/test_saas_client_consent_gate_3030.py`
> **green with its `N passed` quoted, N being the number recorded for that file alone at Stage 0**.
> And **SC-005a** green — on-disk `provider: beads` + `egress: permitted` + Channel 1 absent +
> `list-tickets --provider jira` → refused, 0 HTTP, message naming Channel 1 — together with its
> positive control (on-disk `jira`, Channel 1 granted, no tracker key → `No valid access token`),
> **both in `tests/sync/tracker/test_tracker_egress_refusal_3108.py`**, the acceptance file, because
> both run end to end through the CLI and the pairing is only meaningful in one file against one
> trip-wire. **The specific pin observed red-then-green: US5 sc1, whose red is the exception type and
> message, never the HTTP count.**

Plus: the change set is one file; `ruff check` and `mypy --strict` clean; the four-row byte-identity
comparison passes with its positive control.

## What to report back

1. The base SHA, and the outcome of the citation revalidation (bookkeeping fixes vs. re-plan
   triggers).
2. The `N passed` line for `test_saas_client_consent_gate_3030.py` **before** and **after**, quoted.
3. The **US5 sc1 red**, quoted as an exception type and message, and its green counterpart. **And an
   explicit statement that SC-005a was green before and after**, with both quotes, and that its
   value is contingent on guards G5/G6 rather than on a transition.
3b. The **hosted bind counter** non-zero in the US5 cells, with the **per-site split** reported
   (`specify_cli.tracker.saas_client.tracker_egress_verdict` versus
   `specify_cli.tracker.local_service.tracker_egress_verdict` — two objects, patched separately).
4. The four-row byte-identity table with actual results, including the positive control.
5. The three blast-radius suite counts against their predictions, and any unpredicted movement with
   its attribution.
6. Confirmation that `git diff --stat` shows exactly one file.
7. Any hazard you judged not to apply, and why.
