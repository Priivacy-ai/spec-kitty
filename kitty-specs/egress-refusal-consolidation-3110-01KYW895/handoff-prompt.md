# Bundle B — "one wrapper, one shape" — implementation handoff

You are picking up a spec-kitty mission whose **design phase is complete and whose
implementation phase has not started**. Someone else ran specify → plan → tasks and stopped
deliberately. Your job is to implement it, review it, and land a draft PR.

This document is self-contained. You do not have access to the session that produced the
design. Everything you need is here or in the mission dossier it points at. Where a decision
was taken, its **reasoning** is recorded, not just its conclusion — because a successor who
sees only conclusions re-litigates them.

---

# 0. Read this first — the one thing that will mislead you

The dossier is large and the spec is ~1600 lines. **You are not meant to read all of it to
implement.** The spec carries a `## How to use this document` section stating this explicitly:

> **Implementers work from three contiguous blocks — Edge Cases, Success Criteria, and the
> FR→SC coverage table (~470 self-contained lines). The Requirements tables and the Falsifiers
> section are the justification record, for review time.**

A reviewer measured the honest prediction if that note were absent: *an implementer opens 1571
lines, skims, and works from the Requirements table — the worst of the three surfaces.* Do not
do that. Work from the criteria.

**The single most important standing fact:** every serious defect found across five review
rounds was the same shape — **a proof that could not fail.** A criterion that passes against
unfixed code. A mutation that is inert at the decision point. A CI observation whose confound
reads as a green. When you write evidence, the question is never "did it pass" but **"could
this have failed?"**

---

# 1. State at handoff

| Item | Value |
|---|---|
| **Mission handle** | `egress-refusal-consolidation-3110-01KYW895` |
| **Resume with** | `spec-kitty next --mission egress-refusal-consolidation-3110-01KYW895` |
| **Working clone** | `/home/jeroennouws/dev/sk-missions/3110` |
| **Branch** | `bundle-b-egress-refusal-3110` |
| **Design authored against** | `bb2020fea924d6e5b157974f27a7cab1a77ad259` (upstream/main at 2026-07-31) |
| **HEAD at handoff** | `7ba9604` (14 commits, **all dossier-only**) |
| **Source drift** | **Zero.** No `src/`, `tests/` or workflow file has been modified. |
| **Board** | 7 WPs, **all `planned`**; 0 claimed / in_progress / for_review / approved / done |
| **Lanes** | 6 computed, 26 write-scope entries, **0 collisions** |
| **Remotes** | `origin` = MOES-Media fork, `upstream` = Priivacy-ai |

**Detecting drift:** `git merge-base HEAD upstream/main` should return `bb2020fea…`. If
upstream has moved, rebase before trusting any `file:line` in the dossier — every anchor was
verified at that commit, and one of this mission's own recurring defects was stale anchors.

## The dossier

`kitty-specs/egress-refusal-consolidation-3110-01KYW895/`

| File | What it is |
|---|---|
| `spec.md` | **ACCEPTED.** 27 FRs, 5 NFRs, 11 constraints, 25 SCs, edge cases, falsifiers, follow-ups. |
| `plan.md` | **ACCEPTED.** IC-01..IC-07, verification strategy, mutation suite MUT-1..MUT-6, risks. |
| `tasks.md` + `tasks/WP0*.md` | 7 work packages, subtasks T001–T039, SC→WP coverage, ungated-obligations table. |
| `tracer-evidence-base.md` | The measured recon: every claim carries `file:line`. |
| `tracer-squad-findings.md` | **Every review finding, its adjudication, and its resolution.** Read this before re-raising anything. |
| `lanes.json` | Lane assignment and write scopes. |
| `acceptance-matrix.json` | **A STUB.** All-TODO, keyed on `FR-###` only, carries retired/folded rows. Do **not** accept against it — `tasks.md`'s SC→WP table is the substitute. |

Also read the **parent** mission's dossier, `kitty-specs/journal-project-consent-3030-01KYKWQS/`
— specifically `tracer-tooling-friction.md`. It is the record of measurements that produced
confident wrong answers, and §11 of this document quotes the parts that bind you.

---

# 2. What the mission is

Three bundled items sharing a surface and an abstraction. They are bundled because `#3111`'s
fix lands *inside* the thing `#3110` consolidates.

## The ground you are standing on

Parent mission `#3030` (merged 2026-07-31, PR #3098) closed a P0 leak: a single `sync now`
delivered **1,322 events belonging to five never-opted-in projects** alongside 7,811 from the
intended one. **In this product `mission_slug` values are client engagement names, so metadata
is the confidential content.**

**The bug class, stated once:** *a path reaches a consent answer through something other than
the data's own `project_uuid`.* Substitutes already found and closed: the current working
directory, `repo_root`, machine-global arming, daemon scope, and a checkout-level grant.

A reviewer sharpened this during design, and **this formulation supersedes the one above** —
adopt it:

> The invariant is about the argument's **provenance**, not its **type**. Consent must be
> keyed on something derived from **the record being sent**, never from ambient context.
> Uuid-typing a seam does not make the substitutions inexpressible — it makes them one call
> longer: `resolve(project_uuid_of(locate_project_root()))` is the same bug respelled.
> Conversely some *path*-keyed sites are sound, because the path is derived from the data.

## `#3110` — the duplicated refusal wrapper

`saas_client/egress_consent.py` and `tracker/egress_consent.py` are near-identical. What is
duplicated is the **wrapper** — the refusal text and the verdict→message mapping — **not** the
consent chain, which is already single (both reach `invocation.adapters.resolve_egress_consent`).

**Measured:** six diff hunks, of which **exactly one is a runtime string** (the `DENIED` branch
says "mission and **decision** identifiers" in saas_client, "mission and **engagement**
identifiers" in tracker). The other five are comments/docstrings. **No test pins either side.**

## `#3111` — `decision widen` answers consent for the wrong project

`spec-kitty agent decision widen` (note: **`agent`** — there is no top-level `decision` typer,
and the command is `hidden`) resolves the project root as `locate_project_root() or Path.cwd()`
while the `decision_id` is an **operator-supplied argument**.

**The failure is consent laundering, not unconsented egress.** The gate
(`_refuse_unless_project_consents`) runs **before the URL is used**, so a non-consenting
checkout transmits nothing. The defect is that standing in consenting project A and widening a
decision owned by B sends **B's identifier to A's team, under A's token** — and every gate
answers truthfully, about the wrong project.

## `#3109`'s residual — a seam with no production caller

**Do not re-do the deletion.** It landed at `bb2020fea`. `token_manager._ws_client` survives
only in comments explaining its removal (verified: four hits in `src/`, all inside `#`
comments; zero live `getattr`, zero assignment). The only open question was keep-or-delete
`invocation/adapters.register_saas_client_factory`. **It was decided: keep and pin.** See §4.

---

# 3. THE DEPENDENCY — Bundle A, and how to check it yourself

**This mission halted at design because Bundle A had not landed.** Bundle A fixes the things
that make CI trustworthy for exactly the files this mission changes.

**Measured 2026-07-31: NOT LANDED.** Both issues OPEN.

## Check each signal concretely — do not ask, measure

```bash
gh issue view 3115 --repo Priivacy-ai/spec-kitty --json number,state,closedAt
gh issue view 3113 --repo Priivacy-ai/spec-kitty --json number,state,closedAt
```

**Signal 1 — `#3115`, shard-parallel test isolation.** Its known pollution victims **are this
mission's test surface.** Several `#3030` tests pass alone and fail under `-n auto --dist
loadfile`, and the failure text is a *production refusal message*, which on this codebase reads
as a gate defect rather than fixture pollution.

**Signal 2 — `#3113`, the egress guard's positional-call blind spot.** Located mechanically:

```bash
sed -n '/def _transmits_a_body/,/^def /p' tests/architectural/test_egress_consent_boundary.py
```

If the body still derives `kwargs` solely from `node.keywords` and returns
`"headers" in kwargs and bool(kwargs & _REQUEST_BODY_KWARGS)` → **not fixed.** It never reads
`node.args`, so a fully positional `poster(url, data, headers)` is not classified as a sink at
all.

**Signal 3 — the `pytest.ini` timeout gap.**

```bash
grep addopts pytest.ini
```

If it still reads exactly `addopts = --tb=short` → the gap is open. (`pytest-timeout` **is** a
declared dev dependency and a `timeout` marker is registered; the gap is purely the missing
`addopts` entry. The only `--timeout=30` in the repo is inside the **mutmut** config block and
does not apply to normal runs.)

## If Bundle A has only partly landed

- **`#3115` landed, `#3113` not** → your isolation greens are trustworthy; any claim that a
  *moved sink* is still guarded is **not**. Say so explicitly in the PR body.
- **`#3113` landed, `#3115` not** → the reverse. Verify every new/changed test in **single-file
  isolation** and quote the `N passed` line per file, with the file count.
- **Neither** → do both of the above, and treat CI reds on this mission's surface as suspect
  until reproduced in isolation.

## Which parts of this plan assume A's fixes — named specifically

| Assumes | Why |
|---|---|
| **NFR-005 / SC-009** (single-file isolation) | Exists *because* `#3115` has not landed. If A lands, this stays valid but stops being load-bearing. |
| **WP01's guard work, WP04's acceptance test** | Both live in directories whose autouse conftest fixtures are `#3115`'s pollution surface. |
| **Nothing depends on `#3113`** — and this is deliberate | A reviewer corrected an earlier over-claim: `#3113`'s blind spot is in the **egress-boundary** guard's `_transmits_a_body`. The **attribution** guards match by class name and count every match regardless of call form, so they have **no positional blind spot.** Do not cite `#3113` as a bound on WP01's coverage claims — it is not one. |

---

# 4. The decisions — with reasoning, and with what would falsify each

A successor who sees only conclusions re-litigates them. Each of these was contested.

## D-1 — `#3109`: KEEP `register_saas_client_factory`, and pin it

**The obvious framing is wrong.** It treats the seam as orphaned. It is not: the **read** side
(`get_saas_client`, `invocation/adapters.py:188-215`) has a live production consumer at
`propagator.py:137`, inside a documented consent-gate ordering (`propagator.py:96-100`). Only
the **write** side is dead (three `src/` references, all definitional).

**The choice is three-way and the middle option is dominated:**
- **(a) keep the whole seam** — status quo.
- **(b) delete only `register_…`** — leaves a getter that can never return non-`None` and a
  consumer branch dead by construction. **Strictly more confusing than either neighbour.**
- **(c) delete the entire seam**, including the propagator's egress branch.

**(a) over (c)** on two grounds: **scope** — (c) edits the gated egress path `#3030` hardened,
squarely outside Bundle B; and **absence is already pinned** —
`test_sync_registers_no_saas_client_factory` exists because when the correct state is *absence*,
you must pin the absence or the next author reads the empty seam as an oversight.

**A third ground was offered and then withdrawn.** It was argued that keeping the slot keeps the
consent gate in front of it, so a future transport lands behind the gate. A reviewer pointed out
nothing makes a future author *find* a seam with no production caller. **Do not quote that ground
as load-bearing.**

**A fourth option was missed initially and is recorded so it is not re-proposed:** *(d) delete
`register_…` and `get_saas_client`, keep the propagator's consent gate and its recorded
`request_text` refusal.* It preserves the refusal in a **more** discoverable location. It still
edits `propagator.py`, so (a) wins on scope — but the analysis is only honest with (d) named.

**Falsifiers:**
- If `propagator.py`'s egress branch is ever removed, the read side dies and **(c) becomes
  correct**.
- If a real transport is registered, `test_sync_registers_no_saas_client_factory` reds **by
  design** — that is the moment to prove the propagator's consent gate holds against the new
  transport *before* landing it.
- If the repo adopts a policy that empty seams must not exist regardless of read-side liveness,
  ground 1 is overridden by policy and (c) follows.

**Careful — a measured trap.** Deleting the `def` is **not** a valid before-state for a red-first
proof: `tests/invocation/test_adapters.py:29` and
`tests/specify_cli/invocation/test_propagator_consent_gate_3030.py:53` import it at module scope,
so deletion is a **collection-time ImportError in two files**. Only the **export half** is
genuinely unpinned (verified: `adapters.py` has zero `__all__`; `grep "from specify_cli.invocation import" src/` → zero;
`test_all_declarations_required.py` gates only `src/charter/` and `src/kernel/`).

## D-2 — `#3111`'s ownership check is a **within-checkout search**

**There is no `decision_id` → owning-project mapping. Not locally, not remotely.** This is a
finding, not a gap:
- The ledger lives at `<repo_root>/kitty-specs/<mission-slug>/decisions/index.json`.
- `IndexEntry` (`decisions/models.py:68-96`) carries `mission_id` + `mission_slug` and **nothing
  else identifying**. `model_config = ConfigDict(frozen=True, extra="forbid")` — a `project_uuid`
  **cannot even be present** in a valid file.
- Creation takes `repo_root` as a parameter, uses it, and **discards** it.
- The SaaS client's complete surface is five endpoints; **none** returns a decision's project,
  and there is no "get decision" endpoint.

**Ownership is positional** — encoded by which directory the file sits in, never as data.

**The mechanism:** glob `<repo_root>/kitty-specs/*/decisions/index.json` and membership-test with
the existing `load_index`. This needs **no** mapping, **no** mandatory `--mission-slug`, **no**
network call, and **no** cross-checkout enumeration. Measured cost: 333 mission dirs, 49 ledgers,
glob 0.0017 s, parse 0.0032 s; `rglob` returns the same 49 (0 missed by the one-level glob);
0 symlinked dirs.

**Two rejected alternatives, recorded so they are not re-proposed:**
- *Require `--mission-slug`* — every currently-succeeding slug-less invocation becomes a refusal.
- *Cross-checkout search* — has its own disclosure implications and is deferred to a follow-up.

**Falsifier:** if a `decision_id` → owning-project mapping ever lands, the search stops being the
only option and the design should be revisited.

## D-3 — the re-resolve implementation is **deleted, not deferred**

An earlier draft admitted two shapes: refuse on divergence, **or** re-resolve token and team from
the owning root. Under re-resolve exactly one request *is* sent, which contradicts the acceptance
criteria — a spec that permits at requirement level what its own acceptance forbids.

**Refuse-on-divergence is forced**, because re-resolve requires *identifying* project B, and the
within-checkout search returns *owns it* / *ownership not established* — never an identified B.

**The stated ground was wrong once and is corrected here.** It was written as "unimplementable
under C-009". C-009 is about the missing **mapping**; what actually blocks re-resolve is the
absence of a **checkout enumeration** — a different and entirely **buildable** thing (measured:
`checkout_roots` has exactly two callers, both one-element lists from
`locate_project_root(cwd)`; zero machine-level enumeration in `src/specify_cli/`). The correct
statement: **not expressible under D-2's within-checkout design; the cross-checkout search that
would express it is deferred to a follow-up.**

## D-7 — the ownership derivation lives in `decisions/ownership.py`, **not** the shared module

Three grounds, strongest first:

1. **Bounded-context ownership.** "Which project owns this record" is a *decisions*-context
   question; the shared module is a presentation wrapper for a refusal string. Putting a ledger
   reader inside it makes it a two-concern module and re-creates the conflation the requirement
   exists to prevent.
2. **The operative criterion never said otherwise** — SC-018 names **no package**. Per the spec's
   own reading rule, SC-018 is the implementation surface and the Requirements table is the
   justification record; where they disagreed, the table was stale.
3. **Cohesion** — the ledger lives in `specify_cli/decisions/`.

**A fourth ground was led with and then falsified.** It was argued that placing it in the shared
module would break the neutrality premise the placement rests on. Measured: that premise is about
**transport** neutrality, and `specify_cli.decisions.store`'s module-level closure is 2 modules
and **does not** reach `specify_cli.sync`. **Do not restate that ground** — a falsifiable lead
ground in an accepted spec invites a successor to overturn a correct decision for the right
reasons.

## D-8 — the shared wrapper is a **plain module**, `src/specify_cli/egress.py`

This resolved two reviewers' **incompatible** fixes. One measured that a package layout
(`egress/refusal.py` defining + `egress/__init__.py` re-exporting) creates a **fourth** name, so a
mutation patching the definition site is inert at both decision points **while the identity gate
stays green** — rot-mode 5 reappearing inside the fix for rot-mode 5. Its fix was to stop
re-exporting. But the identity criterion asserts `specify_cli.egress.project_egress_refusal`,
which that fix would delete.

**The module form dissolves it:** one definition site — exactly the asserted name. Three names
total, the existing **two** identity comparisons correct as written, no third assertion.

Verified: `test_no_dead_symbols` walks every `*.py`; `test_layer_rules` filters `p.is_dir()` **and**
scans top-level only; the integration gate catches the module in **all three** import shapes
including function-scope, via `mod == prefix`; and the package `__getattr__` (which raises
`AttributeError` for every name but one) does **not** break the identity assertions — measured,
all three import spellings resolve to the same object.

**A cost, honestly booked:** a *package* over 500 LOC while unmapped would appear in the
unclaimed-src-dir worklist; a *module* never can, at any size. That is a **lost latent detector**,
not a gain — which is *why* the classification criterion is needed.

**Falsifier:** if the merged wrapper cannot be written without importing from a transport, the
neutral premise is false and *keep-both-files-and-pin-equivalence* becomes the honest answer.

## PB-5 — both `*/egress_consent.py` modules are **deleted**, not kept as shims

**Ground:** the accepted spec carries exactly **two** identity comparisons. "Shims survive" would
oblige a **third** the spec does not have — and an implementer working from the operative blocks
*as the spec instructs* would never write it, leaving the shim hazard **known and unguarded**.
Deletion is the choice under which the accepted spec is self-sufficient.

The seam-allowance gate does **not** force survival: it is a **substring** test over
`src/specify_cli/tracker/saas_client.py`, and the rebound import line satisfies it alone.

**Falsifier F3 (measured, re-runnable):** deletion is falsified if any importer exists outside the
four measured sites, or if either module path appears in an architectural allowlist. Measured:
importers are exactly `saas_client/client.py:23`, `tracker/saas_client.py:34`, and two
**in-function** test imports; `grep` over `tests/architectural/` → **zero**. If F3 fires → keep
both as pure re-exports **and add the third comparison**.

## Q2 (operator decision) — per-caller fragment in a shared template

The shared module owns the template, the four verdict branches, the undetermined-refusal constant,
the `None` guard and the import-failure degradation. **Each transport passes its own
identifier-set fragment as an argument.** Both current `DENIED` strings survive **verbatim**.

**Why not the alternatives:** the identifier sets are **asymmetric** (`mission_id` is the only
shared member — the tracker carries no `decision_id`; the SaaS client no `project_slug` and no
issue titles). A single union string would tell a tracker operator that *decision* identifiers
were at stake when the tracker cannot transmit one. **Overstating exposure in a confidentiality
message is the wrong direction to be wrong.** A superordinate "identifiers" is never untrue but
drops the specificity that is the whole point of the message.

**Falsifier:** if a future endpoint makes the two sets identical, the fragment becomes ceremony and
the union string becomes correct.

---

# 5. The board

7 work packages, all `planned`. Dependency graph:

```
WP01 ──▶ WP03 ──┐
                ├──▶ WP06 ──┐
WP02 ──▶ WP04 ──┘           ├──▶ WP07
WP05 (independent) ─────────┘
```

| WP | Scope | Lane | Depends on |
|---|---|---|---|
| **WP01** | Hoist both guards' inline AST predicates to module-level functions, then per-class floors, synthetic assertions, MUT-4/5/6 | lane-a | — |
| **WP02** | CI routing: the job if-gate + **three** dorny glob lines | lane-b | — |
| **WP03** | Create `src/specify_cli/egress.py`, delete both `*/egress_consent.py`, rebind, classify, MUT-1/MUT-2 | lane-a | WP01 |
| **WP04** | `#3111`: `decisions/ownership.py` + `cmd_widen` refusal + acceptance module. **P1, indivisible** | lane-c | WP02 |
| **WP05** | `#3109`: docstring truth + export pin | lane-d | — |
| **WP06** | ADR + glossary entry | lane-e | WP03, WP04 |
| **WP07** | Verification evidence, docs-lockfile reconciliation | lane-planning | all |

## Two orderings whose *stated reason* matters more than the edge

**WP01 → WP03.** The guards must be hardened before the consolidation they protect.

**WP02 → WP04, and the reason is NOT what it looks like.** A PR confined to
`src/specify_cli/cli/**` does not run the SaaS attribution guard, and WP04 edits
`cli/commands/decision.py:558`. **But the guard runs on WP04's diff anyway**, because WP04 creates
`src/specify_cli/decisions/ownership.py` and `decisions/**` is in the `closeout` filter group,
which gates the job that collects it. **The edge closes the general routing hole; it is not why
the guard runs on WP04's diff.** Do not report WP02 as the reason your guard ran — that is a
false guarantee, and a successor splitting WP04 would satisfy the stated ordering while breaking
the real invariant.

**WP04 is deliberately indivisible.** Splitting `decision.py` from `ownership.py` would satisfy
the stated ordering and break the real one.

---

# 6. Traps that will bite you — each measured, each in the WP that hits it

**These are not style notes. Each was found by measurement, and most were found only because
someone asked "could this have failed?"**

1. **A green 28-test module is in your blast radius and was nearly missed.**
   `tests/specify_cli/cli/commands/test_decision_widen_subcommand.py` drives `cmd_widen`
   end-to-end with `DECISION_ID = "01KWIDETEST00000000001"` — **22 chars, contains `I`**, so it
   fails every ULID regex the fix reuses. Measured baseline: **`28 passed`**, with **19 of 28**
   tests naming the fixture directly (26 references) and **8** live-path patch sites (a ninth is
   the `assert_not_called` test). Both mandated changes red it independently.
   **The two cheapest exits are FORBIDDEN REPAIRS:** relaxing the ULID check, and making
   ownership permissive when the acting root has no `kitty-specs/` — *the fall-through under
   another name*. Fix the fixture to a well-formed 26-char ULID and arrange an owning ledger.

2. **The unreadable-ledger test must chmod the containing `decisions/` DIRECTORY, not the file.**
   Measured on both interpreters, control first:
   ```
                        3.11.15                3.14.4
   file=0o000    ->     True                   True     <- NO divergence
   dir=0o000     ->     PermissionError(13)    False    <- THE BRANCH
   ```
   `stat(2)` needs search permission on the **parent**, not read permission on the file — POSIX,
   not interpreter-dependent. The file shape yields the *same* result on both, so a test using it
   proves nothing while appearing to discharge the portability requirement.
   **This matters because `decisions/store.py:64` is `if not path.exists()`, inside the very
   `load_index` the ownership check reuses** — so an unreadable ledger refuses correctly on 3.14
   and produces an **uncaught traceback on CI**. The ownership module needs an explicit
   `except OSError`, executed under 3.11.

3. **Both candidate test directories fabricate consent.** Autouse fixtures in
   `tests/specify_cli/saas_client/conftest.py:74` and `tests/sync/tracker/conftest.py:166` inject
   a **consenting** `project_root` whenever the kwarg is omitted. The real path is safe — but by a
   mechanism nobody had written down: `from_env` **always** passes `project_root=` as a keyword,
   **even when `None`** (`client.py:137-142`), so the guard `if "project_root" not in kwargs` is
   unreachable from `cmd_widen`.
   **This is a two-file conjunction and the falsifier must watch both.** Changing a conftest guard
   to `if kwargs.get("project_root") is None` re-arms it — and **the fabrication would be
   invisible to every test this mission adds**, because the ownership gate keys on the acting root,
   not on `project_root`, so the refusal still fires and the positive control still passes.
   Hence the compensating runtime assertion: assert the client the command actually built carries
   A's on-disk root.

4. **Rot-mode 5 is live on the exact symbol being consolidated.** Both deciding modules bind by
   value (`saas_client/client.py:23`, `tracker/saas_client.py:34`). **A mutation patching the
   shared module does NOT reach either decision point — and no layout can make it.** That is a
   property of `from X import f`. What the module form buys is that the definition site *is* the
   asserted name, so patching it makes the identity assertion **red**. **Identity is a detector,
   never an actuator.** Patch every name the symbol is reachable by and **report the per-site
   split** — an aggregate count cannot distinguish "both mutated" from "one inert".

5. **The guards' predicates are inline in test-function bodies**, so a synthetic assertion cannot
   call them and a `PYTHONPATH` plugin cannot patch them. The natural outcome is a **second copy**,
   after which the mutants mutate one and the assertions check the other. WP01 extracts each
   predicate to a module-level function so the live scan **and** the synthetic assertions call the
   **same object**.

6. **The extraction's own acceptance test is a metric proven blind.** "The counts must not change"
   cannot see the predicate changes it exists to license — the counter increments **before** the
   attribution test, so vocabulary widening leaves counts *exactly* unchanged; the tracker's three
   sites are all bare `ast.Name`, so narrowing leaves it *exactly* at the floor. Use the **four
   synthetic witness shapes** with their `(matched, attributed)` tuples.

7. **Two new `docs/` pages meet a blocking lockfile.** The repo keeps a 1:1 page inventory —
   baseline **685/685 clean** — and *every* drift row is `severity="error"`. WP07 owns the lockfile
   and the ADR era README; WP06 lands deliberately lockfile-dirty and hands WP07 the filename.
   **Note:** the docs-freshness workflow is the **only** CI workflow with no base-branch filter, so
   it *would* red a per-lane PR. Do not open one, and do not reach for a skip label.

8. **The ADR template omits a field the reconciler requires.** `freshen_adr_inventory.py` raises
   unless the ADR carries **both** `title:` and `date:`; the shared template has `title`,
   `description`, `doc_status`, `updated` — **no `date:`**. All 95 live ADRs carry both, so copy a
   neighbour, not the template. The failure otherwise surfaces in WP07, on a file WP07 cannot edit.

---

# 7. What the reviews found, and how each was resolved

Five review rounds ran across three artifacts, all profile-loaded, read-only, opus.

| Artifact | Rounds | Above MEDIUM found | Outcome |
|---|---|---|---|
| **spec** | 3 | 2 CRITICAL, 3 BLOCKER, 17 HIGH | ACCEPTED after operator-authorised closing fixes |
| **plan** | 2 | 4 HIGH | ACCEPTED (round 2: 0 above MEDIUM, both lenses) |
| **tasks** | 2 | 1 BLOCKER, 6 HIGH | ACCEPTED (round 2: 0 above MEDIUM, both lenses) |

**Convergence, measured the same way each round.** On the spec: undeclared no-op criteria
**45% → 18% → 6%**, and criteria unsatisfiable even by a correct implementation **1 → 0**. On the
work packages: undeclared no-op subtasks **10% → 2.6%**, and on the criteria denominator
**12% → 0%**.

**Every artifact is accepted. No escalation is pending.** The spec's 3-round gate tripped once and
was resolved by explicit operator authorisation (see the residual in this section).

## The findings worth knowing about, because they shaped the design

- **The mission's primary acceptance criterion was vacuous-passable.** It said "from a checkout
  that does not own the named decision produces zero outbound requests" — and never said
  *consenting*. A non-consenting checkout already sends zero today. An implementer could have
  written that test, watched it pass against unfixed code, and shipped nothing. It now requires a
  **consenting** checkout **and** a well-formed ULID present in B's ledger and absent from every
  mission under A.
- **A criterion instructed the defect it was added to prevent.** It required the guard to *match*
  a callee shape the predicate excludes **by design** — so the only way to green it was widening
  the predicate, which is the silent-halving direction two other requirements forbid.
- **The compatibility clause had a repair that reinstates the leak.** The design substitutes "this
  checkout's ledger lists the decision" for "the server knows this decision" — not the same set.
  An implementer meeting the resulting red has one obvious fix: *fall through to the acting root
  when the ledger doesn't list it*. **The spec now forbids that repair by name.**
- **A CI observation was structurally unobtainable.** Any PR carrying the routing fix edits the
  workflow file, which is itself in the filter group being tested — so the run proves nothing. And
  the proposed workaround (a stacked PR based on the mission branch) produces **no CI run at all**,
  because the trigger filters on the PR's *base* ref. That obligation is now **necessarily
  post-merge**.

## The work-package round specifically

Round 1 found **1 BLOCKER and 6 HIGH**, all distinct across two lenses, and every one of them was
a *"can this actually land?"* failure rather than a design flaw:

- the 28-test module in §6.1, in **no** lane's write scope and named **zero** times in the dossier;
- an operative criterion still naming the superseded package form — the one a cold reader would
  have followed;
- a criterion whose one-off half had been silently dropped, leaving the mission's **headline
  requirement** discharged by the only criterion with no anti-vacuity clause and no mutation;
- a criterion instructing the exact inline-client construction its own work package exists to
  prevent;
- **two packages that could not land green at all** — both create `docs/` pages against a 1:1
  lockfile (685/685 clean, every drift row a blocking error) that **no lane owned**;
- an evidence file placed in a directory violating the structural lint's placement and frontmatter
  contract, when the repo's own precedent sits elsewhere;
- **219 lines of load-bearing rationale deleted with no destination** — including the only written
  record of a high-impact requirement that deliberately has *no* criterion — while a live comment
  was repointed at a module that would not contain the text it names.

Round 2 closed all of them **at the mechanism rather than the wording**, and both lenses said so
independently. Three of the residual MEDIUMs were in surface created *by* the remediation — which
is worth knowing: each of them fails **loudly** (a named exception, a rejected path, a false-red
review count), none can produce a silent wrong outcome.

## Findings raised and judged WRONG — do not re-raise these

- **"The CI glob edit is needed to avoid running the whole suite forever."** Measured backwards:
  adding the module to `core_misc` *alone* stops the unmatched-fallthrough and strands the tracker's
  tests, which run **nowhere else** because that shard explicitly ignores them. The single-group
  form is a **silent coverage loss** — worse than the run-everything default. Hence **two** glob
  lines, on the in-repo precedent of a file that sits in both groups.
- **"Assert the SaaS guard does NOT match `mod.SaasClient(...)`."** Measured: that predicate is
  already the **stricter** of the two, so widening it can only make the guard see **more** sites — a
  coverage **gain**. The pin would red on an improvement **and** cement the hole a filed follow-up
  exists to close. Replaced by a per-class **match** assertion on a genuinely unused-but-matching
  shape.
- **"A neutral package is the only candidate that preserves the import-failure behaviour."**
  Measured: only the `sync/` candidate reaches `specify_cli.sync` at module level, so that
  constraint eliminates one option and discriminates nothing else.
- **"`#3113` bounds this mission's guard-coverage claims."** It does not — see §3.

## Residuals deliberately carried (all MEDIUM or below)

- The spec is long (1571 lines) and the length goal was not met — cuts recovered ~55 lines while
  fixes added ~180. Mitigated by the navigation note, not by brevity.
- The `[ratchet]` label has a doctrinal edge: three rows are ratchets *and* carry a criterion that
  must still be authored.
- One duplicated passage survives in a fourth location.
- **The closing fixes to the spec were applied without a further review round**, on explicit
  operator authorisation after the 3-round gate tripped. Treat the corrected chmod shape and the
  identity clause as **the least-scrutinised text in the document** — though the chmod shape was
  independently re-measured afterwards (§6.2), which halves that exposure.

---

# 8. The one obligation nothing enforces

**The CI glob lines.** The classification half is gated by a criterion. **The glob half is not**,
and cannot be — the detector that would catch it only inspects directories over 500 LOC, and this
module will be ~150–250.

Forgetting a glob line is **fail-safe in the coverage direction** (unmatched → run everything), so
its risk is CI minutes, not coverage. **The dangerous direction is making the `core_misc` entry
without the `sync` entry** — that is the silent coverage loss. The review question is not "is the
glob there?" but **"are there two?"**

**A guarantee that expires:** the tracker's behavioural ratchets are not routed to the file they
protect. This mission's PR is covered incidentally because it carries the new module. A *future*
PR touching only `tracker/saas_client.py` runs neither ratchet, while the substring gate stays
green on the import line alone. A third glob line addresses it; if you strike it, **file it**
rather than leave it half-done.

---

# 9. Open questions and what was NOT proven

Stated as plainly as the decisions.

- **The CI routing model is a reading of workflow YAML, not a run.** Both reviewers said so
  explicitly and neither could discharge it pre-implementation. It needs a pushed diff. This is the
  single largest unverified premise in the mission.
- **Nothing was run on Python 3.12.** CI runs 3.11 and 3.12; the design measured 3.11.15 and
  3.14.4. The EACCES divergence is expected to behave as 3.11 does on 3.12, **but that is inference.**
- **The `#3111` leak was never reproduced end to end.** The gate-precedes-URL claim is read from
  source and was labelled "reasoning, not measurement" by the reviewer who made it. **Your red-first
  proof is the first time anyone will actually observe it.**
- **The stale-checkout compatibility break was not constructed.** The claim that a
  pushed-but-not-pulled decision becomes a refusal rests on `cmd_widen` performing no ledger read
  today — verified by reading, not by building the scenario.
- **The acceptance matrix is an unpopulated stub** and must be rewritten per-clause before accept.
- **An upstream defect was found and not fixed:** the ownership validator has a helper documented
  for "a planning-artifact WP that legitimately owns nothing" — with a docstring and a regression
  test saying so — but the manifest builder silently drops any WP with an empty ownership list, and
  the lane computer then treats the missing manifest as a hard error. The documented intent has no
  path to a green run. Worth filing upstream.

---

# 10. Follow-up issues to file (out of scope, deliberately)

The spec's follow-up table carries these with rationale and falsifiers. At minimum:

- **Re-key guard routing on construction-site locations.** Zero of the four SaaS-client
  construction sites live under `saas_client/**` — they are in the `cli` and `missions` groups. A
  PR confined to `cli/**` does not run the guard whose purpose is catching exactly that edit.
- **Extend the consented-batch pattern to both transports** — the transports stop accepting a bare
  path attribution and accept a value that cannot be constructed without a data-derived consent
  answer. Seven construction sites across four CI groups. *Falsifier: if a `decision_id` → project
  mapping ever lands, the positional derivation stops being the only option.*
- **Nine pre-existing CORE modules already reach `specify_cli.sync` transitively** through
  unclassified packages, all green under the boundary gate. The classification constraint says "do
  not add a tenth"; it does **not** close the class. Needs a transitive-reach scan.
- **The unguarded `mod.SaasClient.from_env(x)` shape**, matched by neither guard and named by no
  requirement.
- **The upstream ownership-validator defect** (§9).

---

# 11. Standing rules — verbatim, and non-negotiable

Every one comes from a measurement that lied during the parent mission. The full record is
`kitty-specs/journal-project-consent-3030-01KYKWQS/tracer-tooling-friction.md` — **read it, and
quote the relevant entries into every subagent brief you write.**

## Measurement

- **Never pipe a suite whose exit status you intend to trust.** `pytest … | tail` reports `tail`'s
  status, and `tail` buffers until exit so the file reads empty meanwhile. Quote the `N passed`
  line; **an empty output file is no measurement.**
- **A killed run is neither a pass nor a fail.** Re-run it narrowed; do not explain it.
- **Measure in a `git worktree` pinned to a commit — and set `PYTHONPATH=$WT/src` or use a
  dedicated venv.** This repo's editable install hard-codes the **main checkout's** src path, so a
  worktree run otherwise imports the live tree and any "identical results" conclusion is a tautology.
- **Read the failure text, not the tally.**
- **Print the input count alongside any "all checks passed".** A gate that ran on zero files passes
  vacuously — that happened during `#3030` and hid a real error.

## Proof

- **Red first**, and make the red the *consequence*, not a boolean. For `#3111`, the strongest red
  is the engagement-relevant identifier reaching the transport under a divergent checkout — assert
  the **bytes**, not a flag.
- **A plain revert may not be a valid before-state.** During `#3030` reverting a gate red on a
  constructor `TypeError` rather than the leak, so the honest before-state was a mutation. Check
  which you have.
- **Include a positive control that must pass.**
- **Any assertion of absence must establish why the thing would otherwise have happened.**
- **Control your diagnostic**: run any probe against a case whose answer you already know before
  trusting it.
- **Mutations as pytest plugins via `PYTHONPATH`, never source edits, and never source edits during
  a verification run.**

## The five recorded ways a mutation silently lies — check each

1. The architecture moved and the patched gate became a redundant second → all-green, reads as
   "your pin is fine".
2. The reds are `TypeError`s from a changed signature, not assertion failures.
3. The mutant hard-codes a value the tests **vary** → no-ops for exactly the tests most likely to
   catch the defect.
4. The branch is unreachable on the local interpreter and **live on CI's** (3.11/3.12 vs 3.14) →
   zero binds means *your environment differs*, not *the code is dead*.
5. **`from X import f` rebinds by value** → patching the defining module leaves the *deciding*
   module inert. **Patch every name a symbol is reachable by and report the per-site split**; an
   aggregate count cannot distinguish "both mutated" from "one inert". This bit twice in `#3030`,
   once inside a fix's own coverage.

## Hygiene

- **Explicit-path staging.** `git add <paths>`, never `git add -A`. **13 files were lost to a stray
  `add -A` during `#3030`.**
- **`ruff format` is NOT clean on this repo** (`line-length = 164`); running it reflows other
  people's committed work. **Only `ruff check` is meaningful.**
- **One live agent per file**; tell each subagent which paths others hold.

## This clone's environment — measured

- A **user-site** `.pth` puts `/home/jeroennouws/dev/spec-kitty/src` on `sys.path` for every bare
  `python3`. **`pytest` from the clone root is SAFE** (`pytest.ini` sets `pythonpath = src`, which
  wins — measured). **Everything else needs
  `PYTHONPATH=/home/jeroennouws/dev/sk-missions/3110/src`.** Never trust a bare
  `python3 -c "import specify_cli"` here.
- **Only Python 3.14 is installed system-wide; CI runs 3.11/3.12.** A 3.11 venv is constructible
  with `uv venv --python 3.11`. **Every local green is a 3.14 green** until you do that.
- Collection is slow: a single trivial test takes ~60 s wall-clock. Budget for a large fixed cost
  per invocation.

## Known pre-existing failures — do not chase, do not fix in-PR, do not retry to green

`tests/architectural/test_tid251_enforcement.py` (4 tests, proven pre-existing on `origin/main` in
a pinned worktree), `test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out`,
two `test_safe_commit_cmd::…_3033`, `test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed`,
and `test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock, fails under load).
`ModuleNotFoundError: No module named 'typer'` in subprocess daemon tests is a user-site install
interacting with `HOME` isolation — **environmental**.

**Not on that list, and therefore yours:** `tests/specify_cli/cli/commands/test_decision_widen_subcommand.py`
(28 tests, green at baseline). See §6.1.

---

# 12. How to run this

Use the **spec-kitty SDD workflow**, driven by
`spec-kitty next --mission egress-refusal-consolidation-3110-01KYW895`.

## The review loop, and when to stop

- Every work package goes through implement → **independent review** (a different agent than the
  implementer; **reviewers do not edit code, they issue a verdict**).
- A REJECT means: fix the findings, then **send it back for re-review**. Repeat.
- **After 3 review rounds on the same work package**, if any finding above **MEDIUM** severity still
  stands (HIGH / BLOCKER / CRITICAL) — **halt and escalate to the operator with a multiple-choice
  question.** Do not attempt a fourth round, and **do not lower a severity to clear the gate.**
- MEDIUM and below may be carried as recorded residuals, **provided they are written where a
  successor will find them.**

**This rule governs artifacts too, not just implementation** — it is how the spec, plan and tasks
were driven.

## Adversarial squad at every point-cut

Run the **adversarial-squad** skill as a distinct pass — bounded (3–4 lenses), profile-loaded,
read-only, structured output, second-opinion on divergence. **Remediate confirmed findings before
advancing.** Two lenses converging independently is strong evidence; two lenses proposing
*incompatible* fixes means adjudicate from source, never average.

## Model policy for subagents

- **Default: `sonnet`.**
- **`opus` where reasoning is the work** — say in one line why. Expected here: any REJECT
  remediation turning on a judgement call, all adversarial squads and independent reviews.
- **`fable` is off limits.** Do not use it for any subagent.
- Mechanical work — moving a helper, updating imports, adjusting fixtures — is sonnet.

## Landing

Drive to a **DRAFT PR** via the **`pr-landing` skill** — mandatory, and a PreToolUse hook enforces
it. That flow: rebase onto current `upstream/main` → compress history (**admin bunched, code by
slice**, not one squash) → run CI's gates locally (`commitlint`, `ruff check`,
`pytest tests/architectural/`) → red-first proof → lease push to the **MOES-Media fork** → open the
cross-fork DRAFT PR to `Priivacy-ai:main` → post the remediation-summary comment.

- **Never `gh pr merge`.** The maintainer merges.
- **Do not un-draft** without the operator's explicit go.
- **After creating the PR, read its state back** (`gh pr view <N> --json isDraft,state`). During
  `#3030` the `--draft` flag was accepted and the command succeeded while GitHub recorded
  `isDraft: false` — **verify, don't trust the exit code.**
- Include the full `kitty-specs/<mission>/**` dossier in the PR.
- **File follow-up issues for anything found out of scope rather than absorbing it.**

## Things the PR body must say

- Which greens depend on Bundle A's holes being closed (§3).
- That the CI routing model is a YAML reading, not an observation, and the one-off confirmation is
  **necessarily post-merge** (§9).
- That one criterion's anchor moved because its host file was deleted — **substance preserved,
  anchor moves** — so a reviewer does not read it as unsatisfiable.
- Any Sonar hotspot review or UI-side work that remains, so a later agent does not try to fix it in
  code.

---

# 13. Your first hour

A suggested order, because the dossier is large and the wrong entry point costs a day.

1. **Confirm no drift.** `git merge-base HEAD upstream/main` → expect `bb2020fea…`. If upstream
   moved, rebase before trusting any anchor in this document.
2. **Check Bundle A** with the three commands in §3. **Write the answer into your PR body** — every
   coverage claim you make is conditional on it.
3. **Read the spec's three operative blocks only** (§0). Roughly 470 lines. Not the whole file.
4. **Read §6 of this document twice.** Those eight traps are the difference between a green run and
   a green run that proves nothing.
5. **Run the baseline that will bite you first:**
   ```
   pytest tests/specify_cli/cli/commands/test_decision_widen_subcommand.py
   ```
   Expect **`28 passed`**. Those are the tests your `#3111` change reds, in a file that until
   recently no lane owned. Know them before you write a line.
6. **Then** `spec-kitty next --mission egress-refusal-consolidation-3110-01KYW895`.

## What "done" looks like

A draft PR to `Priivacy-ai:main` from the MOES-Media fork, carrying the full dossier, whose body
states — in this order — what shipped, the measured evidence with **every failure attributed**, the
red-first proof for `#3111` asserting **bytes not counts**, which greens are conditional on Bundle
A, what you found and deliberately did not fix, and **the limits of what you verified**.

**State what you did not prove as plainly as what you did.** That instruction produced most of the
value in the design phase, and it is the one most easily dropped under time pressure.

---

*Design phase completed 2026-07-31 against `bb2020fea`. Three artifacts, seven review rounds across
two adversarial lenses each, 1 CRITICAL-class escalation resolved by the operator. Every decision
above carries the precondition that would falsify it — if you find one of those preconditions has
become true, the decision is not binding on you.*
