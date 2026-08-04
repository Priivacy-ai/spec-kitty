# Implementation Plan: One Wrapper, One Shape — Project Egress Refusal Consolidation

**Branch**: `pr/egress-refusal-consolidation-3110` | **Date**: 2026-07-31 | **Revised**: 2026-07-31 — reconciled against the **ACCEPTED** spec (three adversarial rounds + operator escalation outcome + closing-fix outcome), then **remediated against plan review round 1** (§3-R1: four HIGHs — PR-1, PR-2, PA-1, PA-2 — all closed; Q1's answer changed from a **package** to a **module** and the CI accompaniment from one glob line to **two**) | **Spec**: [`spec.md`](./spec.md)
**Input**: `spec.md` (**ACCEPTED, 1571 lines**) · [`tracer-squad-findings.md`](./tracer-squad-findings.md) (§1.5 decisions D-2…D-6; §1-R2/§1-R2b/§1-R3 rounds 2–3; ESCALATION OUTCOME; CLOSING-FIX OUTCOME with rulings PB-3/PB-4/PB-5; **§3-R1 plan review round 1 — debugger-debbie PR-1…PR-6 and architect-alphonso PA-1…PA-8, all remediated in this revision**) · [`tracer-evidence-base.md`](./tracer-evidence-base.md) (measured, `file:line`, corrections C-1…C-4) · [`../journal-project-consent-3030-01KYKWQS/tracer-tooling-friction.md`](../journal-project-consent-3030-01KYKWQS/tracer-tooling-friction.md) (the parent mission's recorded measurement failures — this plan's verification strategy is built to survive them).

**Reading order for an implementer**: this plan decides Q1 (§Project Structure — **the wrapper is a module, `src/specify_cli/egress.py`, with TWO dorny glob lines; read the adjudication before changing either**), the **PB-5 shim question** (§Project Structure → *The shim decision*), and Q5/Q7/Q8; it re-measures the baseline rather than transcribing it (§Technical Context) and states a verification protocol (§Verification Strategy) that is binding on every work package. Decisions D-2…D-6 in `tracer-squad-findings.md` §1.5 are **not reopened**. **The two spec corrections this plan authorises are listed once, at the end** — [§The two spec corrections](#the-two-spec-corrections-this-plan-authorises).

**Read the spec the way the spec says to read it.** Per its `## How to use this document`, the implementation surface is exactly three contiguous blocks — **Edge Cases**, **Success Criteria**, and the **FR→SC coverage table**. The Requirements/NFR/Constraints tables and *Falsifiers and preconditions* are the **justification record**, not instructions. Every criterion cited in this plan is cited from the operative blocks; where this plan disagrees with a Requirements-table cell, that is called out in place. *(FR-020's home was such a case and **is no longer** — the spec now carries a POST-ACCEPTANCE CORRECTION adopting `decisions/ownership.py`, so that block is a **concordance**: [§Where FR-001's ownership derivation lives](#where-fr-001s-ownership-derivation-lives--not-in-egresspy).)*

### What this revision absorbed (spec rounds 2–3 + closing fixes)

| Change in the accepted spec | Where this plan moved |
|---|---|
| **Q2 RESOLVED by the operator** — per-caller identifier fragment in a shared template; **both `DENIED` strings survive verbatim** | Q2 is no longer an open question; falsifier **F2 does not fire**; load-bearing ordering 4 is **discharged, not pending** |
| **FR-025 / SC-017 retired**, folded into **SC-004 clause 3** — now a **binding-identity** assertion (`is`), not a per-site-split report | [§Rot-mode 5](#rot-mode-5-in-detail-sc-004-clause-3), MUT-2, IC-03, R1, R7 |
| **SC-014's mandated shape corrected** — chmod the **`decisions/` directory** to `0o000`, not the file | [§rot-mode 4](#measured-rot-mode-4-is-live-and-it-lands-on-this-missions-own-edge-case), rule 12, IC-07 |
| **SC-013 → two per-class MATCH assertions**; the non-match proposal **withdrawn entirely** | MUT-5 + new **MUT-6**; the control-corpus note in §Technical Context |
| **SC-002 gains the must-not-veto half** (unreadable ledger in X + hit in Y ⇒ normal single request) | IC-04 verification, MUT-3's control |
| **SC-025 is new** — the assertion that reds if the `INTEGRATION_PREFIXES` line is removed | IC-03, R2a (downgraded), Complexity Tracking |
| **SC-001 asserts two divergence routes, not four** | [§the red-first proof](#the-red-first-proof-for-3111-stated-concretely-enough-to-execute), IC-04 |
| **FR-009 relabelled `[ratchet]`**, scoped by ruling PB-3 to *the identifiers of the project being refused* | §Open questions (Q2 closed), IC-03 |
| **Corrected `store.py` anchors** (`:46`, `:61`, `:64`, `:66`, `:67`, `:115-118`) | every cite in this plan; the old `:63` was wrong and `:58` is a comment banner |
| **PB-5 carried as a binding plan-phase item** | Decided below: **the shims are deleted** |

### What plan review round 1 changed (§3-R1: debugger-debbie PR-1…PR-6, architect-alphonso PA-1…PA-8)

| Finding | Where this revision moved |
|---|---|
| **PR-1 [HIGH]** — the package layout creates a **fourth** name; a mutation on the definition site is inert at both decision points **and** clause 3 stays green (8 cases, control first) | **ADJUDICATED: the wrapper is a plain module `src/specify_cli/egress.py`.** One definition site; three names; the spec's existing two `is` comparisons become correct as written, with **no spec change to SC-004**. [§Q1](#q1--decision-the-shared-wrapper-lives-in-a-new-srcspecify_cliegresspy-a-module-not-a-package) |
| **PR-1's residue** — *"once identity is pinned, any future patch of the shared module provably reaches both decision points"* is **measured false** | Struck and replaced with what identity actually delivers. [§Rot-mode 5](#rot-mode-5-in-detail-sc-004-clause-3) |
| **PR-2 [HIGH]** — both guards' predicates are **inline in test-function bodies**, so SC-012/SC-013 cannot assert against a synthetic sample and MUT-4/5/6 cannot patch them under rule 11 | New **IC-01 deliverable**: extract each predicate to a **module-level function** in its own guard file; live scan and synthetic assertions call the **same object**. [§IC-01](#ic-01--attribution-guard-hardening-must-land-first) |
| **PR-3** — SC-014's assertion target was stated at `Path.exists()` level (a pathlib characterization test); SC-002 clause (c)'s **refuse** half had no stated home | Target restated as **`resolve_decision_ownership`'s outcome**; that same test is named as the refuse half's home. Rule 12, IC-04, IC-07, R3 |
| **PR-4** — MUT-2 stated as a source state, which rule 11 forbids | Restated in its **plugin** form (§Mutation suite, MUT-2's row) |
| **PR-5** — acceptance step 2 not executable under step 5; the mechanism that actually closes the fabricated-consent trap was unstated; the acceptance module's directory was unnamed | Step 2 replaced with `SPECIFY_REPO_ROOT`; the measured `from_env`/`conftest` reason recorded; the directory named |
| **PR-6** — the per-site-split rule is over-generalised and MUT-1's row omits the patch-all-names binding | Split rule scoped to MUT-1/MUT-2; the binding repeated inside MUT-1's row |
| **PA-1 [HIGH]** — a `core_misc`-only glob makes routing **worse**: one group true + `unmatched=false` ⇒ `fast-tests-sync` does not run, and `tests/sync/` runs **nowhere else** | **ADJUDICATED: add the module to BOTH the `sync` and `core_misc` groups.** Direct in-repo precedent measured. [§Q1's accompaniments](#the-two-accompaniments--both-mandatory) |
| **PA-2 [HIGH]** — SC-006's `[one-off]` CI observation is **structurally unobtainable** from any PR carrying the fix (`ci-quality.yml` is itself a `core_misc` glob member) | Rescheduled as a **stacked throwaway PR based on the mission branch**, or declared a post-merge observation; the confound written down. Q8 table, IC-02 |
| **PA-3** — load-bearing ordering 2's rationale does not hold for this mission's own diff | Restated as *"the PR carrying the `decision.py:558` edit must either include a non-`cli` path or postdate IC-02"* |
| **PA-6** — R2 conflates a safety failure and a cost failure | Split into **R2a** (safety, gated by SC-025) and **R2b** (cost, fail-safe in the coverage direction only if **both** glob lines are present) |
| **PA-7** — PB-5's carry-through misses a **src-side** pointer and two cross-references inside the relocated text | Both added to IC-03's carry-through list |
| **PA-8** — the "DECLARED DISAGREEMENT" block is stale (the spec now carries the POST-ACCEPTANCE CORRECTION) | Retitled as a **concordance** citing the correction block |
| **Spec corrections authorised by this round — exactly two** | (1) SC-025 / C-005's antecedent covers a new **module OR package**; (2) the FR-020 correction block is rewritten (ground 1 demoted as falsified, bounded-context ground promoted to first) and **moved below the FR table**, which it was breaking |

---

## Summary

Three issues meet at one seam — the boundary between a transport and the single project-consent chain.

- **`#3111` (P1, the only live defect)** — `spec-kitty agent decision widen` resolves the repo root from the operator's *location*, not from the record being sent. Standing in consenting project A and widening a decision owned by B sends **B's identifier to A's team under A's token**, and every gate answers truthfully about the wrong project. This is consent *laundering*, not unconsented egress. Fix: establish, from local files under the acting root only, that the acting checkout owns the decision — before any URL is built (Decision D-2's within-checkout ledger search) — and refuse otherwise (Decision D-3).
- **`#3110` (P2, maintainability)** — two `egress_consent.py` modules whose *only* runtime divergence is one string (`decision` vs `engagement` identifiers). Consolidate to one editable presentation.
- **`#3109` residual (P3)** — keep `register_saas_client_factory`, pin its **export**, and correct its stale docstring (Decision D-1).

Guarding all three: the two attribution guards must survive at full strength per **transport class** (not per package — A-11), and the guard covering this mission's own construction-site edit must actually run on this mission's own diff (FR-017, Decision D-4).

**The central planning decision this document takes is Q1 — where the shared wrapper lives. Answer: (d) in its *plain-module* form — a new `src/specify_cli/egress.py`, NOT a package — mapped into **both** the `sync` and `core_misc` dorny groups and added to `INTEGRATION_PREFIXES`.** The reasoning, including a correction to two claims in the spec's own Q1 table and the plan-review adjudication that reduced the package to a module, is in [§Project Structure](#project-structure).

**Scope bound (C-011) is respected**: no cross-checkout search (FU-4), no uuid-typed seam (FU-5), no general guard-routing re-key (FU-1), no transitive-reach scan (FU-3).

---

## Technical Context

**Language/Version**: Python 3.11+ (charter §Technical Standards). **CI runs 3.11/3.12; only 3.14 is installed locally** (F-ENV-2) — see the measured divergence below, which is live and load-bearing for this mission.
**Primary Dependencies**: typer, pydantic (`extra="forbid"` on the ledger schema), pytest. No new runtime dependency.
**Storage**: local files only — `<repo_root>/kitty-specs/<mission-slug>/decisions/index.json`. **No network round-trip is added** (NFR-002); there is no decision-owner endpoint to call (F-B1/C-009).
**Testing**: pytest. Both attribution guards are `pytestmark = pytest.mark.fast` (`test_client_consent_gate_3030.py:28`, `test_saas_client_consent_gate_3030.py:39`) — **re-measured**, because it determines which FR-017 fix shapes are viable.
**Project Type**: single project (CLI + library), `src/specify_cli/`.
**Constraints**: C-001…C-011 from the spec, all inherited unchanged except the two corrections recorded below.

### Re-measured baseline — not transcribed (discharges orchestrator correction C-4)

Both guards' AST predicates were copied **verbatim** from source and re-run in this clone at `bb2020fea`, with a known-answer control executed **first** (control-your-diagnostic) and the **input file count printed alongside** the result (a scan over zero files passes vacuously — that happened during `#3030`).

```
== CONTROL (synthetic corpus, known answers) ==
  saas    scanned=4 (expect 4)  unattributed=2 (expect 2)
  tracker scanned=3 (expect 3)  unattributed=1 (expect 1)
  CONTROL VERDICT: PASS — predicates behave as documented

== LIVE SCAN ==
INPUT FILE COUNT: 937   (root: src/specify_cli)

SaasClient        scanned=4   unattributed=0
    src/specify_cli/cli/commands/charter/interview.py:216
    src/specify_cli/cli/commands/decision.py:558
    src/specify_cli/missions/plan/plan_interview.py:150
    src/specify_cli/missions/plan/specify_interview.py:150

SaaSTrackerClient scanned=3   unattributed=0
    src/specify_cli/tracker/origin.py:165
    src/specify_cli/tracker/origin.py:265
    src/specify_cli/tracker/saas_service.py:109
```

**Confirmed: tracker 3, SaaS client 4, over 937 input files.** This is the fourth independent reproduction (F-A3, reviewer-renata, architect-alphonso, and now the plan); the closing-fix applier made it a fifth (PB-7 — and it disposed of a grep-suggested fifth SaaS site at `saas_client/__init__.py:28`, which is **inside a module docstring**). C-4's "inherited, not re-measured" caveat is discharged **at plan time in this clone**, not by citing the squad.

**Re-measured at revision time, because SC-013's SaaS half now depends on it** — all four SaaS sites, read from source in this clone:

```
INPUT SITE COUNT: 4 (expect 4)
  cli/commands/charter/interview.py:216   SaasClient.from_env(repo_root)
  cli/commands/decision.py:558            SaasClient.from_env(repo_root=locate_project_root() or Path.cwd())
  missions/plan/plan_interview.py:150     SaasClient.from_env(repo_root)
  missions/plan/specify_interview.py:150  SaasClient.from_env(repo_root)
⇒ direct=0, from_env=4
```

**`direct=0` is what makes SC-013's SaaS half non-trivial**: `SaasClient(project_root=…)` is *matched and attributed* by the guard today and *used nowhere*, exactly parallel to the tracker's attribute-receiver shape — so a unification that collapses onto the `from_env` form drops it **silently, with no count moving**.

The control is not decoration: it discriminates the two error modes that matter — it includes `mod.SaasClient(...)` and `SaaSTrackerClient(repo_root=…)` (which the tracker predicate must flag **unattributed**, because tracker accepts only `project_root=`).

> **Correction carried from round 3 — do not turn the control into a pin.** An earlier reading of this control treated `mod.SaasClient(...)`'s **non-match** as an FR-016 property to assert. **The accepted spec withdraws that proposal entirely and it must not be reintroduced anywhere.** Grounds, measured: the SaaS predicate is already the **stricter** of the two, so unifying can only *loosen* it — the guard would see **more** constructions, a coverage **gain**, not a Mechanism-3 loss; and a non-match pin would **collide with FU-8**, which exists precisely because `mod.SaasClient.from_env(x)` is unguarded on both guards and closing it means widening a predicate. `mod.SaasClient(...)` may stay in the *diagnostic corpus* (it tells the probe's author that the predicate is behaving as documented); it may **not** become a test assertion. FR-016's assertions are the **two MATCH shapes** in SC-013.

### Bundle A — re-measured at plan time, per C-006's own falsifier

| Item | Check run | Result |
|---|---|---|
| `#3113` egress-guard positional blind spot | `sed -n '/def _transmits_a_body/,/^def /p' tests/architectural/test_egress_consent_boundary.py` | **OPEN.** Body still derives `kwargs` solely from `node.keywords`; returns `"headers" in kwargs and bool(kwargs & _REQUEST_BODY_KWARGS)`. `gh issue view 3113` → `state: OPEN, closedAt: null`. |
| `#3115` shard-parallel isolation | `gh issue view 3115` | **OPEN**, `closedAt: null`. |
| Global pytest timeout (FU-6) | `grep addopts pytest.ini` | **OPEN.** `pytest.ini:11: addopts = --tb=short` — unchanged, no `--timeout`. A hang consumes a run rather than failing it. |

Per-work-item consequences are in the [Implementation Concern Map](#implementation-concern-map); the summary is: **`#3113` bounds the egress-consent *boundary* guard only** (R-12/D-10 — the attribution guards have no positional blind spot and must not claim `#3113` as a bound), and **`#3115` means full-suite reds on this surface are not attributable**, which is why NFR-005 requires per-file isolated runs with the count and file list stated.

### Environment hazards, measured in this clone

- **`pytest` from this clone's root is SAFE** — `pytest.ini` sets `pythonpath = src`, inserted ahead of the user-site `.pth` (F-ENV-1, measured).
- **Every other python invocation must set `PYTHONPATH=/home/jeroennouws/dev/sk-missions/3110/src`.** A bare `python3 -c "import specify_cli"` resolves to `/home/jeroennouws/dev/spec-kitty/src` — a *different checkout*, concurrently edited by the Bundle A mission. Every probe in this plan was run with `PYTHONPATH` set.
- **`ruff format` is NOT clean on this repo** (line-length 164). Only `ruff check` is meaningful. **Never run `ruff format`.**
- Fixed collection cost is ~69 s per pytest invocation regardless of test count. Budget accordingly; do not "just run the suite".

### MEASURED: rot-mode 4 is live, and it lands on this mission's own edge case

The spec (edge case "the decision ledger is MALFORMED", NFR-006, SC-014, debugger finding D-11) inherits the friction doc's recorded `Path.exists()`/`EACCES` divergence. **This plan executed it rather than citing it**, on both interpreters, with a non-root euid.

**Re-executed at revision time in the shape SC-014 now mandates, control first, with the case count printed** — because round 3 established (HIGH-1) that the shape originally mandated *cannot reach the branch*, and the closing-fix outcome (PB-4) then measured both halves on both interpreters rather than extrapolating one from the other:

```
python 3.11.15  euid=1000                     python 3.14.4  euid=1000
  CONTROL readable            -> True           CONTROL readable            -> True
  CASE A file=0o000           -> True           CASE A file=0o000           -> True        <- NO divergence
  CASE B dir=0o000            -> PermissionError(13)   CASE B dir=0o000     -> False       <- THE BRANCH
  INPUT CASE COUNT: 3 (expect 3)                INPUT CASE COUNT: 3 (expect 3)
```

**Only CASE B reaches the divergence, and the reason is POSIX, not interpreter-dependent**: `stat(2)` requires **search permission on the parent directory**, not read permission on the file. With `file=0o000` the file is still `stat`-able, `Path.exists()` returns `True` on *both* interpreters, and the `PermissionError` arrives later from `read_text()` at `store.py:66`. **A test built on the file shape returns an identical result on 3.11 and 3.14, and the honest reading of an identical result is "no divergence, NFR-006 discharged" — a false negative in this mission's only portability gate.** That is why SC-014 mandates the **directory** shape.

This is not abstract. **`decisions/store.py:64` is `if not path.exists(): return DecisionIndex(mission_id="", entries=())`** — the exact call, on the exact function Decision D-2 mandates FR-001 reuse (`load_index`). Consequence:

- On **3.14 (local)** an unreadable ledger yields an *empty index* → membership fails → FR-002 refuses. **Correct behaviour, green locally.**
- On **3.11/3.12 (CI)** the same ledger raises `PermissionError` out of `load_index`, out of the ownership function, uncaught → **a traceback, not an operator-actionable refusal.** NFR-004 is answered by a stack trace and the "unreadable ownership is not consent" edge case is not delivered.

**Binding consequence for IC-04**: FR-002's unreadable-ledger branch **cannot** be implemented by relying on `load_index`'s `exists()` check. The ownership function must wrap the ledger read in an explicit `except OSError` — **alongside** the `JSONDecodeError` / `ValidationError` handling the malformed case needs — and convert it to *not established*, and the test for it must be **executed under 3.11**, not reasoned about on 3.14. This is the single highest-value item NFR-006 buys, and it would have been missed by a plan-phase judgement made on the wrong interpreter.

**Corrected `store.py` anchors, verified in this clone at revision time** (the earlier `:63` / `:58-64` / `:112-120` cites were stale; **`:58` is a comment banner**, not the `def`). Every cite in this plan uses these:

| Anchor | Line | Read |
|---|---|---|
| `def index_path` | `:46` | `decisions_dir(mission_dir) / "index.json"` |
| `def load_index` | `:61` | the function Decision D-2 mandates reusing |
| `path.exists()` | `:64` | the swallow-EACCES branch → empty index |
| `json.loads(path.read_text(...))` | `:66` | `JSONDecodeError` on bad JSON; also where a `file=0o000` `PermissionError` lands |
| `DecisionIndex.model_validate(raw)` | `:67` | `ValidationError` on schema-invalid content |
| membership shape | `:115-118` | `load_index` → `next((e for e in current.entries if e.decision_id == …), None)` |

**Missing ≠ malformed ≠ unreadable, and they must not be lumped** (the spec states this once, in *Edge Cases*): a **missing** ledger returns an empty index and is simply a mission that owns no decisions — it contributes **no** unreadable-ledger flag and the search moves on.

### Two corrections to the spec, established by measurement in this clone

Both concern Q1 and are load-bearing on the decision below.

**Correction 1 — "(d) is the only candidate that preserves FR-013" is too strong.** The spec's Q1 table (row (d)) and architect finding A-3 are read together as saying a neutral package is uniquely FR-013-safe. A-3's *mechanism* is sound but it is specific to `sync/`: a module-scope `from specify_cli.<PKG>.<mod> import …` forces `specify_cli/<PKG>/__init__.py` to execute, and it is only fatal if that `__init__` reaches `specify_cli.sync` at module level. I measured that closure for every surviving candidate (TYPE_CHECKING bodies correctly excluded — see the diagnostic note below):

| Candidate | module-level closure | reaches `specify_cli.sync`? |
|---|---|---|
| (b) `saas_client/` | 6 modules | **NO** |
| (c) `tracker/` | 11 modules | **NO** |
| (d) `egress` (new) | 2 modules | **NO** (by construction) |
| (f) `delivery/` | 4 modules | **NO** |
| (a) `sync/` — ELIMINATED D-5 | 2 modules | **YES** (reflexively — the package itself) |

Controls: `saas_client` and `tracker` must measure **NO**, because FR-013 demonstrably holds today through exactly those two import paths (`client.py:23`, `tracker/saas_client.py:34`); and `specify_cli.cli.commands.agent.tasks` must measure **YES** (it has a column-0 `from specify_cli.sync.events import …` at `:51`), proving the probe can still see a real edge. All three controls passed.

**⇒ FR-013 does not discriminate among the surviving candidates.** It eliminates (a) and nothing else. (d) must therefore be justified on other grounds, which it is below — but the spec's implied "only candidate" advantage is withdrawn.

> *Diagnostic control, recorded because it nearly produced a false finding.* My first pass reported `delivery/` **reaching sync** and I was one step from writing that (f) fails A-3 exactly as (a) does. The edge was `delivery/targets.py:56` — which sits inside `if TYPE_CHECKING:` and is annotated in source *"typing-only import (C-001: no runtime edge)"*. The probe was walking non-executing branches. The v1 control (saas_client/tracker → NO, sync → YES) had passed, because neither of those packages has a TYPE_CHECKING sync import — **the control did not discriminate the error mode**. Fixed by excluding TYPE_CHECKING bodies and adding a control that does discriminate it. This is the friction doc's "control your diagnostic" rule (`:531-547`) firing on this plan's own work, and it is exactly why the plan re-measures rather than transcribes.

**Correction 2 — "(f) `delivery/` is already classified, so no C-005 edit" conflates two senses of *classified*.** Measured:

- `src/specify_cli/delivery/**` **is** in the `core_misc` dorny filter group (`ci-quality.yml:273`) — this is A-10's finding and it is correct. That is **CI-routing** classification.
- `specify_cli.delivery` is **NOT** in `INTEGRATION_PREFIXES` (`tests/architectural/test_integration_boundary.py:75-81`, which lists exactly `orchestrator_api`, `sync`, `tracker`, `saas`, `saas_client`). That is **C-005's** sense, and C-005 says so verbatim: *"that package must be added to the integration-boundary gate's INTEGRATION prefixes."*

**⇒ In C-005's sense, `delivery/` is unclassified.** Option (f) therefore carries D-8's laundering gap *and* the spec asserts it does not — a gap plus the belief that there is no gap, which is strictly the worst of the available states. A-10 itself got this right ("*without C-005 binding it, which means the exposure is unrecorded rather than absent*"); the Q1 table's "For" column is where the drift entered.

---

## Charter Check

*GATE: re-checked after the Q1 design decision below.*

| Standing order | Disposition |
|---|---|
| **1. Adversarial squad cadence** | Post-specify passes complete: **three rounds** (round 1: 4 lenses; rounds 2–3: renata + debbie), escalation gate tripped at round 3, **operator ACCEPTED** the spec with both surviving HIGHs closed. **A post-plan pass has now run — §3-R1, two lenses (debugger-debbie, architect-alphonso), four HIGHs (PR-1, PR-2, PA-1, PA-2), all closed in this revision.** Its highest-value targets were the named ones: Q1 (which it changed — package → module), the PB-5 shim decision (which survived), and the declared FR-020 disagreement (which the spec had already adopted, so the block is now a concordance). Advisory, not a gate. **Carry the operator's explicitly accepted risk into the handoff: the round-3 closing fixes were *not re-reviewed*** — SC-014's corrected chmod shape and SC-004's binding-identity clause are the **least-scrutinised text in the spec**, and this plan leans on both. *(This revision independently re-executed the SC-014 measurement on both interpreters with a control — see §rot-mode 4 — which reduces that exposure for one of the two.)* |
| **2. Campsite cleaning** | The touched surfaces are small and already clean: `egress_consent.py` ×2 (150 + 219 lines), `cmd_widen` (`decision.py:523-572`, 50 lines), `adapters.py` docstrings. **No god-surface, no campsite scout needed.** Domain-matched debt folded: FR-026 (stale correctness prose) and FR-018 (stale docstring) are exactly this. |
| **3. Mission tracer files** | Three tracer files already exist for this mission (`tracer-evidence-base.md`, `tracer-squad-findings.md`, and this plan's measurements). A `tracer-tooling-friction.md` **must** be seeded for this mission and appended during implementation — the parent's is the reason this plan is survivable. |
| **4. Test remediation & red-first (DIRECTIVE_041)** | Binding and fully specified in [§Verification Strategy](#verification-strategy). Red-first is required for `#3111` **through the real entry point** (`spec-kitty agent decision widen`, C-008) and the red must be the **consequence** (B's `decision_id` in the transmitted bytes), never a boolean. |
| **5. Architectural gate non-vacuity (DIRECTIVE_043)** | The core of IC-01. Concrete per-class floors (tracker 3, SaaS 4) + self-mutation tests + shrink-only allowlist. **Explicitly recorded: the floor is necessary and nowhere near sufficient** (paula P-5, debugger D-5) — the guard is syntactic by construction and proves a root was passed, never that it was the *owning* root. |
| **6. Canonical sources & terminology** | FR-023: "engagement" is absent from `docs/context/` (0 of 22). **Q2 resolved keeping "engagement" verbatim in the tracker fragment, so FR-023 is now UNCONDITIONAL** — the round-1 escape ("*or* resolve Q2 toward vocabulary the glossary already knows") is closed, and this mission ships an operator-facing term the glossary must first define (DIR-032). Run `pytest tests/architectural/test_no_legacy_terminology.py` before pushing prose. |
| **7. Git & workflow discipline** | **Explicit-path staging only — never `git add -A`** (the parent mission's commit `2e6aa1d78f` swallowed eight files that way). PRs only; the operator merges. |
| **8. Mission hygiene** | Reviewer ≠ implementer. Every FR gets an issue-matrix row. Tiered rigour: IC-04 is P1 confidentiality (highest rigour); IC-05 is two cheap edits. |
| **9. Red-main discipline** | **Known pre-existing reds are not to be chased or fixed** — see the do-not-touch list in [§Verification Strategy](#pre-existing-reds--do-not-chase-do-not-plan-to-fix). Green-washing them is forbidden; so is folding them into this mission. |

**Violations requiring justification**: one — a new top-of-`specify_cli` module for one function and one constant. Recorded in [Complexity Tracking](#complexity-tracking). *(Reduced by plan review round 1: it was a **package**; PR-1's measurement and PA-5's structural-cost argument collapsed it to a **module**, which is a strictly smaller violation.)*

---

## Verification Strategy

Built against the five recorded rot-modes and the parent mission's measurement failures. **Every rule here is binding on every work package.**

### Standing measurement rules (non-negotiable)

1. **Never pipe a suite whose exit status you intend to trust.** `pytest … | tail` reports **`tail`'s** status, and `tail` buffers until exit so the output file reads empty meanwhile. Write full output to a file and read the file. **Quote the `N passed` line as the evidence; the exit code is noise. An empty output file is no measurement.**
2. **A killed run is neither a pass nor a fail.** Re-run **narrowed**; do not explain it. `exit 143` on a `timeout N … | tail` pipeline is triply ambiguous. Check elapsed-time-vs-timeout before attributing anything.
3. **Measure in a `git worktree` pinned to a commit, and set `PYTHONPATH=$WT/src` or use a dedicated venv.** The worktree alone is insufficient — the user-site editable `.pth` silently redirects imports to another checkout, which *manufactures sameness conclusions*.
4. **Read the failure text, not the tally.** `mutB`'s three reds looked like a working mutation until they turned out to be `TypeError`s.
5. **Print the input count alongside any "all checks passed."** A gate that ran on zero files passes vacuously; that happened during `#3030` and hid a real error. Every count in this plan carries its input file count.
6. **Red first, and make the red the *consequence*, not a boolean.**
7. **A plain revert may not be a valid before-state.** Specifically for SC-008: deleting `register_saas_client_factory`'s `def` is a **collection-time `ImportError` in two test files** (`tests/invocation/test_adapters.py:29`, `tests/specify_cli/invocation/test_propagator_consent_gate_3030.py:53`) and is pinned by a node-id baseline (`fast-tests-core-misc-nodeids.txt:1841`). **Only the export half is unpinned** — the before-state is removing `invocation/__init__.py:21` and `:111`, nothing else (D-4).
8. **Include a positive control that must pass**, in every mutation run and in the `#3111` acceptance file itself.
9. **Any assertion of absence must establish why the thing would otherwise have happened.** "No request was constructed" is also what an unrelated upstream short-circuit produces.
10. **Control your diagnostic**: run any probe against a case whose answer you already know **before** trusting it — and make sure the control discriminates the error mode you actually have (this plan's own TYPE_CHECKING near-miss is the worked example).
11. **Mutations are pytest plugins injected via `PYTHONPATH`, never source edits.** **No source edits during a verification run**, ever.
12. **Only 3.14 is installed locally; CI runs 3.11/3.12.** `uv venv --python 3.11` is available and mandatory for SC-014. **The unreadable-ledger test is chmod `0o000` on the containing `decisions/` *directory*, file left readable** — the file shape does not reach the branch (measured above) and does not discharge NFR-006. A `file=0o000` companion case is permitted **only** if labelled as asserting `read_text` → `PermissionError` at `store.py:66`, explicitly **not** the version-divergent path. **Skip honestly**: if the process can read regardless of mode bits (root, or a filesystem ignoring them), the test must **skip with a stated reason**, never pass — a `0o000` test that silently succeeds is the vacuous case, and that applies to the directory shape too.
    **What the test asserts is `resolve_decision_ownership`'s OUTCOME, not `Path.exists()`'s return value** *(corrected — plan review PR-3)*. An earlier statement of this rule named the expectation as *"at `store.py:64`: `Path.exists()` returns `False` on 3.12+ and raises `PermissionError` on 3.11"*. **That is a characterization test for `pathlib`**: it passes identically whether or not `decisions/ownership.py` carries the `except OSError` — i.e. it cannot red on the one regression the whole rot-mode-4 section exists to catch, which is the traceback escaping on 3.11. The binding target is: with `decisions/` at `0o000`, `resolve_decision_ownership(...)` returns **not established** with the **unreadable flag set** and **no exception escaping**, and that holds **on both interpreters**. The `Path.exists()` divergence is the *reason the branch exists*; it is not the assertion. (The plan already carried the correct requirement at [§rot-mode 4](#measured-rot-mode-4-is-live-and-it-lands-on-this-missions-own-edge-case) and in IC-04; this rule was the side that contradicted it.)
    **That same test is the home of SC-002 clause (c)'s *refuse* half.** Spec `:1205-1206` assigns it there — *no positive hit AND at least one unreadable ledger ⇒ refuse* — and until now the plan named the **must-not-veto** half four times and the refuse half nowhere. Both sides of the two-sided rule now have a stated address: the refuse half in SC-014's unreadable-ledger test, the must-not-veto half in the `#3111` acceptance module (§How the acceptance test avoids fabricated consent, item 6).
13. **Never run `ruff format`** (not clean on this repo at line-length 164). `ruff check` only.
14. **Explicit-path staging only. Never `git add -A`. Do not commit `kitty-specs/` from a lane branch.**
15. **Every mutation plugin must fail loudly when its target is absent, so a no-op cannot masquerade as a clean gate** *(moved here from the MUT-1/MUT-2 scoping block by plan review round 2, PR-G [LOW] — over-scoping had carried it away with the per-site-split rule)*. This binds **every** plugin, not only MUT-1/MUT-2: it is needed **most** by MUT-4/MUT-5/MUT-6, the only plugins that reach a symbol in a *test* module by dotted path whose target does not exist until IC-01 creates it — a rename during the hoist, a wrong dotted path, or rootdir not on `sys.path` at `pytest_configure` would each give a silently absent target, "mutant survived", and a false finding about the code rather than the mutation.

### The five rot-modes, and what each costs this mission

| Rot mode | Live here? | Required countermeasure |
|---|---|---|
| **1 — architecture moved; the patched gate became redundant** | Latent | Patch the **primary decision point**. After consolidation the decisions are at `saas_client/client.py:157` and `tracker/saas_client.py:329` — **not** the shared module. A mutation that patches only `specify_cli.egress.…` proves nothing. |
| **2 — the reds were `TypeError`s, not assertion failures** | Latent | Every mutation run must **quote the assertion text** of at least one red. A red whose text is an import/signature error is not a kill. |
| **3 — the mutation hard-coded what the tests vary** | Live | The merged refusal string is precisely what the tests vary. A mutation must **recover** the string from the module under test, never hard-code today's wording. |
| **4 — inert on your interpreter, live on CI's** | **LIVE AND MEASURED** (above) | `uv venv --python 3.11`; SC-014 quotes the `N passed` verbatim, **and the run must include the `decisions/`-directory-at-`0o000` test** — the shape that actually reaches the branch. The unreadable-ledger branch is the concrete casualty. |
| **5 — `from X import f` rebinds; patching X leaves the caller inert** | **LIVE ON THE EXACT SYMBOL BEING CONSOLIDATED** (D-6) | See below — this is the most important row. |

### Rot-mode 5, in detail (SC-004 clause 3)

> **Retitled in this revision.** FR-025 and SC-017 are **retired** in the accepted spec: both were conditionals *over tests* ("*any test that* patches…"), so writing no such test satisfied them while the hazard stood. Their content is now **SC-004 clause 3**, unconditionally, and in round 3 that clause stopped being a *reporting instruction* and became a **binding-identity assertion**. Do not cite FR-025 or SC-017 in a work package.

Both deciding modules bind the symbol **by value at import time**:

```
src/specify_cli/saas_client/client.py:23   from specify_cli.saas_client.egress_consent import project_egress_refusal
src/specify_cli/tracker/saas_client.py:34  from specify_cli.tracker.egress_consent  import project_egress_refusal
```

with the decisions taken at `client.py:157` and `tracker/saas_client.py:329`. **After consolidation the symbol is reachable by exactly three names**:

```
1. specify_cli.egress.project_egress_refusal                    <- the ONE definition site
2. specify_cli.saas_client.client.project_egress_refusal        <- by-value rebind (client.py:23)
3. specify_cli.tracker.saas_client.project_egress_refusal       <- by-value rebind (saas_client.py:34)
```

Patching or mutating name 1 alone leaves **both deciding modules inert**.

> **Three, and it is three by construction — this is why the wrapper is a module and not a package** *(plan review PR-1, measured over 8 cases with a control)*. Under the previously-planned `egress/` **package** layout there were **four** names: `egress/refusal.py` **defined** the symbol, `egress/__init__.py` **re-exported** it by value, and the two deciding modules rebound from `specify_cli.egress`. A mutation patching the **definition site** — the natural target for MUT-1, whose cell says *"delete the `DENIED` branch from the consolidated wrapper"* — was measured **inert at both decision points while SC-004 clause 3 stayed green**, i.e. rot-mode 5 reappearing inside the fix for rot-mode 5, reporting a false finding about SC-016 rather than about the code. **The plain module removes the extra hop by construction**: definition site and import target are the same object, `specify_cli.egress.project_egress_refusal` — which is **exactly the name SC-004 clause 3 already asserts** (spec `:1263-1264`). No spec change to SC-004, no third assertion, and the spec's existing **two** `is` comparisons are correct as written. See [§Q1](#q1--decision-the-shared-wrapper-lives-in-a-new-srcspecify_cliegresspy-a-module-not-a-package).

**The hazard splits into two arms, and the accepted spec answers them differently** (round 3, both lenses converged):

- **Production arm** — a partial consolidation leaves a **second live definition**. **Already doubly covered, and not by SC-004**: SC-015 reds if a second definition appears, and SC-016 pins the merged `DENIED` wording by content in **both** trees. Sufficient; do not buy a third copy.
- **Verification arm** — *this* is what rot-mode 5 actually is: a future mutation patching `specify_cli.egress.project_egress_refusal` leaves **both** `client.py:157` and `tracker/saas_client.py:329` calling the original object. **Nothing but SC-004 clause 3 reds on this.**

**SC-004 clause 3 — the binding-identity assertion. Two `is` comparisons, standing, zero cost:**

```python
from specify_cli import egress
from specify_cli.saas_client import client as saas_mod
from specify_cli.tracker import saas_client as tracker_mod

assert saas_mod.project_egress_refusal    is egress.project_egress_refusal
assert tracker_mod.project_egress_refusal is egress.project_egress_refusal
```

- **Why identity and not text.** A surviving re-export renders the **identical correct string**, so three correct text observations are exactly what a correct consolidation *and* a stale re-export both produce — **text cannot separate them** (RM-1). Under Q2 the two `DENIED` strings are moreover *supposed* to differ, so clause 1 no longer even corroborates clause 3. SC-015 does not close it either: **a re-export is not "a second definition."**
- **What identity buys — RESTATED, because the previous statement of it was measured false** *(plan review PR-1)*. This bullet used to read *"once identity is pinned, **any** future patch of the shared module **provably** reaches both decision points."* **That is not true and it was measured false**: after `specify_cli.egress.project_egress_refusal = mutant`, the decision point at `client.py:157` still returned the real string, because `client.py:23` holds its own by-value binding. **Rebinding a name is not patching a function.** What identity actually buys is narrower and still worth its zero cost:
  - **It DETECTS a stale binding.** It reds precisely on the state where a deciding module's attribute is not the same object as the shared module's — the partial-consolidation / stale-re-export state that **no text comparison can see** (a stale path renders the identical correct string).
  - **It converts "did the consolidation happen?" from a source scan into a runtime assertion**, which is what makes FR-008's "exactly one editable presentation" behaviourally checkable.
  - **It does NOT make any patch effective.** Identity is a *detector*, never an *actuator*. The property the friction doc's rot-mode-5 rule was actually written to obtain is delivered by the **operative rule below — patch every name it is reachable by** — and identity is what tells you afterwards whether the name set you patched was complete. The two are complements, not substitutes; reading identity as the actuator is what lets a mutation be applied to one name and reported as a kill.
- **Anti-vacuity, binding**: the comparison must be between **two independently imported names**, never two imports of one path — comparing an object to itself proves nothing (R-7).
- **Whether a *third* comparison is required is decided by this plan's shim decision (PB-5).** It is: **the shims are deleted**, so two assertions are complete. See [§The shim decision](#the-shim-decision-pb-5--the-two-egress_consentpy-modules-are-deleted).

**Binding requirements on every *mutation of the consolidated symbol* — that is MUT-1 and MUT-2, and no other** *(scoped by plan review PR-6: demanding a per-site split of MUT-3/4/5/6, which do not touch this symbol, produces filler that dilutes the one place it discriminates)*:

- **Patch every name the symbol is reachable by — all three, enumerated above.** `specify_cli.egress.project_egress_refusal` **and** `specify_cli.saas_client.client.project_egress_refusal` **and** `specify_cli.tracker.saas_client.project_egress_refusal`. Patching the shared module alone is the inert case; it is not a mutation, it is a no-op that reads like one. *(This is the operative rule; identity does not substitute for it — see "What identity buys" above.)*
- **Report the per-site split** (`egress=<n>, saas_client=<n>, tracker=<n>`). **An aggregate count cannot distinguish "both mutated" from "one mutated, the other inert."** A zero or uneven split is a finding about the mutation, not about the code. *(This is a rule on mutation hygiene, not a success criterion — the criterion that reds is clause 3.)*
- **The concrete collapse route to defend against**: a partial consolidation leaving `tracker/egress_consent.py` as a re-export lets a shared-module test report the correct string **while the tracker transport still calls the old object.** C-004 does not prevent this — the seam-allowance gate is a substring test that the import line at `tracker/saas_client.py:34` **already satisfies on its own** (A-5, correcting F-A5). Clause 3 is what closes it.

### The red-first proof for `#3111`, stated concretely enough to execute

This is the mission's load-bearing proof. SC-001's request-count clause is **not sufficient**: a count of zero is also what an unrelated upstream short-circuit produces (`tracer-tooling-friction.md:632-645`), and a **non-consenting** checkout already produces zero requests at `bb2020fea` because `_refuse_unless_project_consents` runs at `client.py:181` *before* `url = f"{self._base_url}{path}"` at `:182` (D-1, the pass's most serious finding). **Assert the bytes.**

**Before-state (must be observed, not assumed):**

1. `git worktree add $WT bb2020fea`; run with `PYTHONPATH=$WT/src` (or a dedicated venv). No source edits in that tree during the run.
2. Build the fixture (below) and run the widen path from **consenting** A naming a **well-formed ULID present in B's ledger and absent from every mission under A**.
3. **Observe a request being constructed carrying B's `decision_id`, addressed to A's `team_slug`, under A's token.** Quote the captured request line. *This is what establishes that the absence asserted after the fix would otherwise have happened* (rule 9).

**After-state:**

```python
assert DECISION_ID_OWNED_BY_B not in transmitted_text(sink)
assert sink == []
```

using the **in-repo idiom `transmitted_text(sink)`** — **defined** at `tests/specify_cli/saas_client/test_client_consent_gate_3030.py:73` and used exactly this way at `:293-296`. **Import it; do not re-implement it** (see the acceptance module's directory, fixed below). The byte assertion comes **first**; the count assertion is corroboration only. Assert against the **constructed request line**, never the response — *a 404 is not evidence of non-disclosure*.

**Route coverage — TWO routes, not four (changed in round 2; the plan previously said four).** SC-001 now requires exactly: the operator-supplied **`--mission-slug`** route, and **one** root-shaped route (**`SPECIFY_REPO_ROOT`**, per US1-AS3). The reduction is not a weakening and must not be "restored" by a diligent implementer: FR-006 itself concedes that the three root-shaped routes — cwd, `SPECIFY_REPO_ROOT`, and the `or Path.cwd()` fallback (`decision.py:558`) — **converge in `locate_project_root` and hold by construction**, so three parameterisations of one code path are one piece of evidence, not three. The slug route is genuinely different code: it is **new with FR-003** and is slug-shaped, not root-shaped (paula P-1).
**Standing bound on the reduction**: it depends on the named convergence point. **If a future change makes any root-shaped route stop converging at `locate_project_root`, this reduction is wrong and SC-001 goes back to four.** State that in the test module so the next reader knows what the two routes are standing in for.

**A third short-circuit that no clause of SC-001 closes, and what discriminates it**: an **unauthenticated** fixture also sends zero requests at `bb2020fea` (`saas_client/auth.py:66-69` → `errors.py:12,24` → caught at `decision.py:570`). **SC-002's "exactly one request" is the only thing in the spec that reds on it** — which is why SC-002 must live in the same module and be built from the same fixture. A green SC-001 alone is *not* evidence that the fix works; the pair is.

### How the acceptance test avoids fabricated consent (C-010 / SC-024)

**Both** candidate test directories carry an **autouse** fixture that injects a *consenting* `project_root` when the kwarg is omitted:

- `tests/specify_cli/saas_client/conftest.py:51,74` — `_default_saas_client_project`, which monkeypatches `SaasClient.__init__` and injects a consenting checkout `if "project_root" not in kwargs`.
- `tests/sync/tracker/conftest.py:55,166` — the mirror image.

Any `#3111` test constructing a client inline in those directories **inherits fabricated consent**, which is the precondition US1 depends on. This is the recorded trap twice over: the filename-matched guard (`tracer-tooling-friction.md:104-122`) and tests green only because a directory fixture arranged their premise (`:666-686`).

**THE ACCEPTANCE MODULE'S HOME — decided here, because it was unspecified and the choice is load-bearing** *(plan review PR-5)*. **`tests/specify_cli/saas_client/test_decision_widen_ownership_3111.py`** — i.e. **inside** the fixture-carrying directory, deliberately. Two reasons, and the second is the one that decides it: (a) `transmitted_text` is defined at `test_client_consent_gate_3030.py:73` in that directory and **must be imported, never re-implemented** — a re-implemented byte extractor is the single most load-bearing line in the mission's red-first proof, and a private copy of it can drift into asserting nothing; (b) the fabricated-consent trap **is closed on this path by construction**, measured below — so the directory's autouse fixture is not a hazard here. The package is importable (`tests/__init__.py`, `tests/specify_cli/__init__.py`, `tests/specify_cli/saas_client/__init__.py` all exist — verified).

**WHY THE AUTOUSE FIXTURES CANNOT FIRE ON THIS PATH — measured, not assumed** *(plan review PR-5; the previous text left this to luck)*:

```
src/specify_cli/saas_client/client.py:137-142   from_env: root = Path(...) if repo_root is not None else None
                                                 return cls(..., project_root=root,)   <- KEYWORD ALWAYS PASSED
tests/specify_cli/saas_client/conftest.py:74     if "project_root" not in kwargs:      <- therefore UNREACHABLE
tests/sync/tracker/conftest.py:166               (mirror image, same shape)
```

`from_env` passes `project_root=` **as a keyword even when the value is `None`**. The autouse guard injects **only when the kwarg is absent**. `cmd_widen` reaches the client exclusively through `from_env` (`decision.py:558`), so **the guard is structurally unreachable from the real invocation** — the fixture cannot fabricate consent on this path. Record this in the acceptance module as a comment: it is the fact the whole directory choice rests on, and if a future refactor makes `from_env` omit the kwarg on the `None` branch, the trap reopens and the module must move.

**The reopening condition is a conjunction over two files, and it must name both sides** *(PR-F [MEDIUM], plan review round 2)*. The paragraph above names only the **producer** side (`from_env` always passing the kwarg). The **consumer** side reopens it just as surely: if a future edit changes either autouse guard from `if "project_root" not in kwargs` to `if kwargs.get("project_root") is None` — a natural-looking "improvement," and the conftest's own comment already shows its author reasoning about the `project_root=None` case — the injection fires on the real path and consent is fabricated again. **Critically, such a reopening would be invisible to every test this mission adds**: the ownership gate keys on the acting root from `SPECIFY_REPO_ROOT`, not on `project_root`, so SC-001's refusal still occurs and the in-file positive control still passes either way — green whether or not the trap is armed, which is the trap's signature. Comment both `file:line`s (`client.py:137-142`, `conftest.py:74` and its mirror `tests/sync/tracker/conftest.py:166`) as the reopening condition, and see item 9 below for the compensating assertion that closes the blind spot.

**Mandatory shape:**

1. **Write both checkouts' `.kittify/config.yaml` on disk** — A consenting (`sync.enabled: true` plus project uuid/slug), B likewise. Do not rely on any fixture to arrange consent.
2. **Convey A's root through `SPECIFY_REPO_ROOT`** (`core/paths.py:224` — the highest-priority tier in `locate_project_root`, ahead of the walk-up), via `monkeypatch.setenv`. **This replaces the previous instruction "pass both roots explicitly, never omit the kwarg", which was not executable** *(plan review PR-5)*: under item 5 the **real invocation** is mandatory, and under the real invocation **the test never constructs a client — `cmd_widen` does** (`decision.py:558`). There is no kwarg for the test to pass. An implementer reconciling the old items 2 and 5 would have constructed a client inline, **abandoning C-008's real entry point and the FR-003 slug route with it** — which is the mission's only genuinely-different code path. The env var is the supported channel and it is also **one of SC-001's two required divergence routes**, so this item and route coverage are now the same arrangement rather than two.
3. **Carry an in-file positive control that must pass** — A's consent actually *grants* for a decision A owns (one request, same endpoint, same payload). This is what distinguishes "A's consent was honoured" from "A's consent was never consulted."
4. **SC-002's positive control lives in the same module, built from the same fixture as SC-001** — not merely co-listed, or an implementer satisfies each from a different arrangement (D-1). It is also SC-001's **auth** control (see above).
5. Use the **real invocation** `spec-kitty agent decision widen` (C-008 — there is no top-level `decision` typer and `cmd_widen` is `hidden`).
6. **The must-not-veto case, new in round 3 and mandatory** (SC-002 clause (c), second side). The malformed-ledger scoping rule is **two-sided** and until round 3 only one side was asserted. The test: construct **an unreadable ledger under mission X together with a positive membership hit under mission Y**, and assert the invocation produces **the normal single request** — same endpoint, same payload — **not a refusal**.
   - **Refusal is correct only when the search terminates with no positive hit AND at least one ledger was unreadable.** An unreadable ledger in a mission that is *not* the answer may be **warned about**; it must never veto.
   - **Why this is not optional**: an implementation that refuses on *any* unreadable index passes every other criterion in this spec while breaking widen invocations that succeed today because of one corrupt `index.json` in an unrelated mission — measured: **49 ledgers across 333 mission dirs** in this repository, so an unrelated corrupt file is not theoretical. It is also **the one fall-through variant SC-001 does not catch**, because no request carrying B's identifier is involved.
7. **The forbidden repair, restated because the danger in SC-002 is the repair, not the break.** When the search finds no positive hit, **do not fall through to the acting root.** That fall-through is the obvious fix for a mid-flight SC-002 red and it **reinstates exactly the leak this mission closes** (DB-1). Admissible responses to an SC-002 red: restore the ledger (`git pull`), narrow with `--mission-slug`, fix the scoping rule in clause (c), or record the case as an intended behaviour change. Never a fall-through. *(Verified binding, not narrated: the **broad** fall-through makes SC-001 red, because a request is then constructed from consenting A for B's ULID. Only the **narrow** variant escapes — which is precisely what item 6 above closes.)*
8. **The refusal message must name the operator action**, not merely the failure: the acting root, the missions searched, and **`git pull` (or otherwise restore `kitty-specs/`), then retry**. Silence here is what makes the fall-through look reasonable.
9. **The compensating runtime assertion, mandatory** *(PR-F [MEDIUM], plan review round 2)*: assert that the client the command actually built carries A's on-disk root — e.g. `client._project_root == A_ROOT` — captured via the same sink/spy the byte assertion in this module already uses. This reds the moment **either** side of the fabricated-consent falsifier changes (the `from_env` producer or either conftest guard's consumer-side predicate), which the byte assertion and the positive control do not: both stay green under a re-armed conftest guard, because they discriminate on `SPECIFY_REPO_ROOT`, not on `project_root`.

### Mutation suite (each is a pytest plugin on `PYTHONPATH`; each asserts its own binding; **MUT-1 and MUT-2 additionally report a per-site split**)

*(The per-site-split obligation is **scoped to MUT-1 and MUT-2** — the two mutations of the consolidated symbol. MUT-3/4/5/6 do not touch it and a split report for them is filler. Plan review PR-6.)*

| ID | Mutation | Must red | Must stay green (control) |
|---|---|---|---|
| **MUT-1** | Delete the `DENIED` branch from the consolidated wrapper. **BINDING, repeated here because this is where the reader looks and this is the mutant most likely to be applied to one name** *(plan review PR-1/PR-6)*: the plugin must rebind **all three** names — `specify_cli.egress.project_egress_refusal`, `specify_cli.saas_client.client.project_egress_refusal`, `specify_cli.tracker.saas_client.project_egress_refusal`. Patching only the shared module is **inert at both decision points** and reports "survived", which reads as *"SC-016's content pins do not detect deletion of the `DENIED` branch"* — **a false finding about the gate**, and the exact measured failure PR-1 reproduced. Report `egress=<n>, saas_client=<n>, tracker=<n>`; a zero or uneven split is a finding about the mutation | SC-016 content pins in **both** packages' test trees | The four pre-existing `could not be determined` assertions (they target `UNDETERMINED`, a different branch) |
| **MUT-2** *(restated twice — see the two notes)* | **Plugin form, mandatory** *(plan review PR-4)*: a `conftest`/plugin `pytest_configure` that rebinds **the deciding module's attribute** — `specify_cli.tracker.saas_client.project_egress_refusal` — to a **delegating wrapper that returns the identical string** produced by the real function. That reproduces the stale-binding state *behaviourally*. **It must not create, edit or restore any file** — in particular it must not write a `tracker/egress_consent.py` back into the tree; rule 11 forbids source edits during a verification run, twice. *(The earlier cell described the mutation as a **source state** — "leave `tracker/egress_consent.py` in place" — which is producible only by a source edit, and since MUT-2 demonstrates the mission's headline property, leaving its mechanism underspecified invited exactly that violation.)* The clause-3 snippet is already correctly shaped to detect it: it reads module **attributes** at assert time | **SC-004 clause 3's `is` assertion** for the tracker binding | **Every string observation stays green** — clause 1, clause 2 and SC-016 all pass, because the delegating wrapper renders the identical correct string. That is the point of the mutation: it demonstrates in the evidence that *text cannot separate the two states* and identity can |
| **MUT-3** | Neutralise the ownership check (always "owned") | SC-001 **and** SC-011, with B's `decision_id` appearing in `transmitted_text(sink)` | SC-002's positive control (A owns → one request) **and SC-002's must-not-veto case** (unreadable X + hit in Y → one request) |
| **MUT-4** | Widen the tracker guard's vocabulary to accept `repo_root=` | SC-012 | **Both scanned counts, which must be exactly unchanged (3 and 4)** — that is the whole point: `scanned += 1` runs *before* the attribution test in both guards (`test_client_consent_gate_3030.py:340` vs `:342-346`; `test_saas_client_consent_gate_3030.py:387` vs `:388`), so vocabulary widening is **invisible to every count** |
| **MUT-5** | Narrow the **tracker** predicate to a literal `Name` receiver | **SC-013's tracker half** (`mod.SaaSTrackerClient(project_root=…)`) | `scanned["SaaSTrackerClient"] == 3` — **exactly at the floor**, proving the floor alone does not detect this (D-5, measured: all three tracker sites are bare `ast.Name` callees) |
| **MUT-6** *(new — SC-013's SaaS half)* | Collapse the **SaaS** predicate onto the `from_env` form only, dropping bare direct construction | **SC-013's SaaS half** (`SaasClient(project_root=…)`) | `scanned["SaasClient"] == 4` — **exactly unchanged**, because the live corpus is `direct=0, from_env=4` (re-measured above). The shape is dropped **silently, with no count moving** — the SaaS-class analogue of MUT-5 |

**Why MUT-2 changed shape.** Its old form — *restore `"engagement identifiers"` at the tracker binding* — is no longer a mutation at all: **the operator's Q2 decision keeps both `DENIED` strings verbatim**, so "mission and engagement identifiers" is the tracker's *correct* rendered text. A mutation that produces the correct state cannot red anything. The hazard it was written for (partial consolidation) is now caught by identity, not by text, so the mutation moved to the state identity catches and text does not.

MUT-4 and MUT-5/MUT-6 are the set that demonstrates why NFR-003 is retitled *"scanned-site count neither decreases nor grows unaccounted"*: the metric cannot support a coverage claim. **Coverage is carried by FR-015/FR-016 and SC-012/SC-013, not by any count.** MUT-5 and MUT-6 are also why SC-013 carries **two per-class MATCH assertions** and **no non-match anywhere**.

### Q8 — "Demonstrated" per criterion (**closed in the spec; this table is now confirmation, not a choice**)

**Q8 was closed in spec round 2**, with the rule *any property that could regress later is a standing gate; any mutation demonstration is one-off PR evidence*, and the per-criterion application now lives in **each criterion's own `[standing]` / `[one-off]` tag** — round 3 deleted the restating table from the spec as redundant. The plan's original table is retained below **updated to the tags the accepted spec carries**, because three of its rows were one-sided and one row is superseded. **Where this table and a criterion's tag ever disagree, the tag wins.**

| Criterion | Spec's tag | Consequence for this plan |
|---|---|---|
| **SC-004** (both transports end-to-end) | clauses 1–2 **`[ratchet]`**, clause 3 **`[standing]`** | **Only clause 3 discriminates.** Clauses 1 and 2 are true of the *unconsolidated* state — do not report a green SC-004 as evidence the consolidation worked. Clause 2's one live edge: if "fully named / no foreign kind" fails against the Key-Entities sets **on the existing text**, that is a real finding, the fix is a wording change, and FR-009 returns to `[build]`. |
| **SC-005** (per-class floor) | **`[standing]`** integers **+ `[one-off]`** removal demonstration | The floors are named integers in the guards themselves. The one-off half is **actually removing one site of each class and quoting the two reds** in mission evidence. **Do not build a synthetic-corpus harness to keep the demonstration standing** — a harness that can drift from the real guard is a gate that goes green while the guard goes blind. |
| **SC-006** (CI routing) | **`[standing]`** `_gate_coverage` assertion **+ `[one-off]`** real CI observation | *Changed from the plan's original "Standing".* The static assertion stands (D-6 names `filter_groups` / `job_gating_groups` at `:474`, `:476`, `:496-497`, parsed `:611-615` — verified present in this clone). **The one-off half is separately required** — but it is **NOT obtainable from the mission PR, and the plan previously implied it was.** See [§SC-006's one-off half is structurally unobtainable from the mission PR](#sc-006s-one-off-half-is-structurally-unobtainable-from-the-mission-pr-pa-2) for the confound and the two admissible substitutes. |
| **SC-008** (seam export) | **`[standing]`** pin **+ `[one-off]`** removal demonstration | The pin is a one-line assertion; the demonstration removes the export half only (see rule 7 — deleting the `def` is not a valid before-state). |
| **SC-012 / SC-013** | **`[standing]`** | Asserted against a **synthetic sample**, not the live corpus, so they cannot rot with the corpus and add no coupling to real call sites. |
| **SC-014** (3.11 run) | **`[standing]`** unreadable-ledger test **+ `[one-off]`** 3.11 run | *Changed from the plan's original "One-off".* The **test** is standing and lives in the suite; only the **3.11 execution** is the point-in-time observation, quoted verbatim. A one-off-only reading would let the test itself never land. **Its assertion target is `resolve_decision_ownership`'s outcome, not `Path.exists()`'s return value** (rule 12, corrected by plan review PR-3) — and it is also the home of **SC-002 clause (c)'s refuse half**. |
| **SC-015** (one editable presentation) | **`[standing]`** mechanism **+ `[one-off]`** divergence demonstration | The "second definition appears" test stands; the demonstration is one-off. |
| **SC-018, SC-025** | **`[standing]`** | Ordinary tests; SC-025 is the gate that notices a forgotten `INTEGRATION_PREFIXES` line. |
| **SC-012 / SC-013's binding sentence** | **`[standing]`** | *(New — plan review PR-2.)* **A synthetic assertion that does not call the same predicate object the live scan calls does not satisfy SC-012/SC-013.** The predicates must be extracted to module-level functions first — see [IC-01](#ic-01--attribution-guard-hardening-must-land-first). |
| **A-1's tracker-routing premise** | **Neither — carried as an explicitly unverified premise** | It needs a pushed diff and cannot be done pre-implementation (D-4's stated premise). Do not report it as measured. **It is discharged by SC-006's one-off half — which is not obtainable from the mission PR; see the section immediately below.** |

### SC-006's one-off half is structurally unobtainable from the mission PR (PA-2)

**Measured.** `.github/workflows/ci-quality.yml` is **itself a member of the `core_misc` dorny glob list** — `ci-quality.yml:263`, the first entry under `core_misc:` at `:262`. This mission's PR **must** edit that file (the FR-017 gate fix at `:1580`, plus the two filter-group globs). Therefore, on any PR carrying the fix, `needs.changes.outputs.core_misc == 'true'` **regardless of what else the diff contains** — and `fast-tests-core-misc` is selected for that reason, not because the routing fix worked.

**⇒ A `core_misc`-green run on the mission PR proves nothing about SC-006, and it looks exactly like proof.** Write the confound down so nobody offers it: *"`fast-tests-core-misc` ran on the mission PR"* is **not** evidence for SC-006's one-off half; it is a tautology produced by the workflow file's own membership in the group.

**The "stacked throwaway PR" substitute is struck — it is inoperative in this repo** *(plan review round 2, PR-A [MEDIUM])*. `ci-quality.yml:3-14` sets `on.pull_request.branches: [main, develop, 2.x]`, and that filter applies to the PR's **base** ref, not the branch a PR is opened from. A PR based on `bundle-b-egress-refusal-3110` is therefore **never selected for a CI Quality run at all** — no job runs, nothing to quote. The workaround-of-the-workaround also fails: adding the mission branch to `on.pull_request.branches` edits `ci-quality.yml` itself, the `core_misc` glob member at `:263` — reinstating the exact confound this section exists to avoid.

**⇒ In this repo, SC-006's `[one-off]` half is *necessarily* a post-merge observation.** Take it on the first `cli`-only PR that lands after the mission merges, quoting the selected job list and the run URL, and route it through the **`post-merge-arch-gate-adjudication`** procedure (`packs/built-in/procedures/post-merge-arch-gate-adjudication.procedure.yaml`) rather than treating it as a loose, undirected follow-up. It moves the evidence outside the mission's own record — say so explicitly in the PR body rather than leaving SC-006's one-off half looking discharged.

**What is NOT admissible**: reading the workflow YAML again and calling it an observation. The static half already does that; D-4's premise is precisely that the runner's behaviour has never been watched.

### Pre-existing reds — do not chase, do not plan to fix

`tests/architectural/test_tid251_enforcement.py` (4 tests) · `test_charter_package_exports::test_charter_package_cold_import_keeps_status_orchestration_out` · two `test_safe_commit_cmd::…_3033` · `test_charter_io::test_get_mission_id_returns_none_when_meta_json_malformed` · `test_doctor_ops::test_sweep_nfr_002_10k_files_under_5s` (wall-clock) · `ModuleNotFoundError: No module named 'typer'` in subprocess daemon tests (environmental).

Additionally pre-existing and relevant to **this** surface: `tests/specify_cli/invocation/test_propagator_consent_gate_3030.py` run **before** `tests/specify_cli/saas_client/test_client_consent_gate_3030.py` in one process fails with *"no hosted-sync consent resolver is registered"* — a fixture-teardown ordering artefact, **deterministic in alphabetical order**, not a gate defect. On a consent mission that failure text reads exactly like the defect under repair. Do not chase it.

---

## Project Structure

### Documentation (this mission)

```
kitty-specs/egress-refusal-consolidation-3110-01KYW895/
├── spec.md                      # remediated specification (authority)
├── plan.md                      # this file
├── tracer-evidence-base.md      # measured evidence, file:line
├── tracer-squad-findings.md     # four lenses + §1.5 decisions D-2…D-6
├── tracer-tooling-friction.md   # TO BE SEEDED (charter standing order 3)
└── tasks/                       # Phase 2 output (/spec-kitty.tasks)
```

### Q1 — DECISION: the shared wrapper lives in a new `src/specify_cli/egress.py` (a MODULE, not a package)

**This is option (d) in its plain-module form, with three mandatory one-line accompaniments** (`INTEGRATION_PREFIXES` + **two** dorny glob lines). The spec deliberately did not decide; the plan owns it. The reasoning is shown because the constraint set is *not* over-determined — A-0 established every surviving candidate is legal, so this is a judgement, not a deduction.

> **Changed by plan review round 1.** This section previously chose a **package**, `src/specify_cli/egress/`, with **one** accompanying glob line. Both were wrong and both were measured wrong: PR-1 found the package layout creates a **fourth** name that defeats MUT-1 while leaving SC-004 clause 3 green, and PA-1 found the single `core_misc` glob silently switches **off** the tracker-side tests on this mission's own change shape. The adjudications are inline below, at [§The package→module adjudication](#the-packagemodule-adjudication-plan-review-pr-1--pa-5--read-this-before-restoring-the-package) and [§The two accompaniments](#the-two-accompaniments--both-mandatory).

#### What does **not** discriminate (cleared first, so the decision rests on real differences)

- **FR-013 / architect A-3.** Measured above: only `sync/` reaches `specify_cli.sync` at module level. (b), (c), (d), (f) preserve FR-013 equally. **This retracts the spec's "(d) is the only candidate" advantage.**
- **Guard coverage (A-11).** Both guards `rglob("*.py")` the **entire** `src/specify_cli` tree (`test_client_consent_gate_3030.py:319-324`, `test_saas_client_consent_gate_3030.py:373-378`). **Placement cannot shrink coverage.** Only merging the counters or the predicates can. This worry is retired for every candidate.
- **C-004.** A substring test over `tracker/saas_client.py`, satisfied by the import line at `:34` alone, under every option. It constrains *renaming*, not placement. (FR-027 supplies the behavioural companion.)
- **C-001.** Excludes only `invocation/`, `core/`, `status/`, `readiness/` — none of which is a candidate.

#### What does discriminate

**(b) `saas_client/` and (c) `tracker/` — rejected on a measured, unbuyable cost.**
I measured the existing edges: **there is no import edge between `specify_cli.tracker` and `specify_cli.saas_client` in either direction today.** (The `tracker/saas_client.py` matches are the tracker's *own* module of that name — a genuine trap for a grep-based reader, flagged here for the implementer.) Options (b)/(c) create that edge, in one direction, permanently, so that one transport's import surface depends on the other's **for a presentation string**. It also encodes a claim that is simply false — neither transport owns the other's refusal policy. Every other cost in this comparison is a one-line edit that can be bought back; this one cannot. **Rejected.**

**(f) `delivery/` — rejected, and the spec's stated reason for favouring it does not hold.**
Its routing advantage is real and I reproduced it (`core_misc` at `ci-quality.yml:273` → `fast-tests-core-misc`, whose gate at `:1580` **does** list `core_misc` → the `specify-cli-rest` shard collects `tests/specify_cli` and **does not** ignore `saas_client/` → the SaaS guard runs). But:

1. Per **Correction 2**, `specify_cli.delivery` is **not** in `INTEGRATION_PREFIXES`. In C-005's sense it is unclassified, so (f) carries D-8's gap *while the spec records that it does not*.
2. Closing that means adding an existing **11-file / 5 699-LOC** package to `INTEGRATION_PREFIXES`, permanently forbidding CORE→`delivery` imports. I measured this is green today (**0 CORE violations**, over an input set of **93 CORE files**), so it is *possible* — but it is a standing architectural policy for a package this mission otherwise does not touch, and **C-011 bounds scope**.
3. `delivery/` is where `ConsentedBatch` expresses the **provenance invariant** (framing 3) — the structurally stronger idea, and the end state FU-2 aims at. Putting a transport *presentation string* there dilutes the one package that currently means something precise.

**(e) two files + an equivalence gate — retained as the named fallback, not chosen.**
Legal under FR-008 as restated (one *editable presentation*, mechanically enforced), honest to the measurement (the duplication is one runtime string), zero layering risk, guard independence trivial. Rejected as the primary because the gate becomes the artefact that must not drift, a text-equality gate is brittle against legitimate per-caller wording, and it does not satisfy a literal reading of "consolidate" — the mission's own title. **It remains the correct answer if falsifier F2 below fires.**

**(d) — CHOSEN, in its PLAIN-MODULE form: `src/specify_cli/egress.py`, not `src/specify_cli/egress/`.**

#### The package→module adjudication (plan review PR-1 / PA-5) — read this before "restoring" the package

**The conflict the two lenses produced, and why it had to be adjudicated rather than averaged.** debugger-debbie (PR-1) measured that the package layout creates a **fourth** name: `egress/refusal.py` defines the symbol, `egress/__init__.py` re-exports it by value, and both deciding modules rebind from `specify_cli.egress`. A mutation patching the **definition site** is **inert at both decision points while SC-004 clause 3 stays green** — 8 cases, control first. Its proposed fix (a) was to make `__init__` re-export nothing and have the deciding modules import from `egress.refusal`. But architect-alphonso pointed out that **SC-004 clause 3 asserts `specify_cli.egress.project_egress_refusal`** (spec `:1263-1264`) — so an `__init__` that re-exports nothing makes an **accepted-spec assertion reference a name that does not exist**. The two fixes are incompatible.

**RULING: take the plain module.** Grounds:

1. **It eliminates the fourth name by construction.** One definition site, and its name is `specify_cli.egress.project_egress_refusal` — **exactly what SC-004 clause 3 already asserts.** Three names total; the spec's existing **two** `is` comparisons become correct as written. **No spec change to SC-004, no third assertion, no `egress.refusal` indirection for clause 3 to miss.** Neither lens's fix costs anything here because the problem both were solving does not arise.
2. **Lower structural cost (PA-5).** A module obtains **every** property the package was chosen for, and I verified each in this clone rather than assuming it:
   - **transport-neutral, no inter-transport edge** — a property of what the file imports, not of whether it is a directory;
   - **C-001-clean** — C-001 excludes `invocation/`, `core/`, `status/`, `readiness/`; a top-of-`specify_cli` module is none of them;
   - **FR-013 preserved** — the module imports neither transport and does not reach `specify_cli.sync`; and a module has **no `__init__.py` to execute**, so A-3's mechanism (a module-scope `from specify_cli.<PKG>.<mod> import …` forcing `<PKG>/__init__.py` to run) **cannot fire at all**;
   - **the dead-symbol ratchet still applies** — `test_no_dead_symbols.py` states in its own docstring that it *"walk[s] every `*.py` file under `src/`"*, so FR-011's "keep the constant out of `__all__`" stays self-enforcing;
   - **`test_layer_rules._DEFINED_LAYERS` is untouched** — `test_no_unregistered_src_packages` builds `src_packages` from `_SRC.iterdir()` filtered on `p.is_dir()` **and** `(p / "__init__.py").exists()` (`test_layer_rules.py:202-208`, re-verified). It counts **top-level `src/` directories**; a `specify_cli`-level *module* is invisible to it in a second, independent way.
   - **Measured, and correctly read as a cost, not a bonus** *(reworded, plan review round 2, PR-D [LOW] — this bullet previously booked the same fact as an advantage)*: `_gate_coverage._src_dir_of_glob` returns `None` for any `src/specify_cli/<file>.py` glob, and the worklist iterates `src_package_loc`'s **direct child directories** — so a module is not merely under `T_LOC = 500`, it is **structurally outside the unclaimed-src-dir worklist, at any size**. A **package** that grew past `T_LOC = 500` while unmapped would eventually surface in `live_derived_worklist`; a **module never can**, regardless of size. That is the loss of a latent detector, not a strength — the spec's own SC-025 text states it this way, as a reason SC-025 is *needed* (spec `:1551-1554`). The LOC-threshold argument stops being load-bearing **because there is one fewer safety net, not because there is one more**; SC-025 is what closes the gap this loss opens.
3. **`"specify_cli.egress"` in `INTEGRATION_PREFIXES` prefix-matches a module just as well as a package.** Verified in the gate's own matcher: `test_integration_boundary.py:151-152` is `if mod == prefix or mod.startswith(prefix + ".")` — the `mod == prefix` arm is the module case, and it is the first arm.

**The one consequence to handle, and it is a spec edit, not a workaround.** C-005 and SC-025 are written with **package-shaped antecedents** — *"If this mission lands a new `src/specify_cli/<name>/` package"*. Under a module, SC-025 would go **vacuous**: its antecedent would be false, so the criterion would assert nothing and the `INTEGRATION_PREFIXES` half would silently return to being ungated. **This plan therefore amends both antecedents to cover a new module OR a new package** (one of the two authorised spec corrections). That is an improvement to the spec independent of this ruling: the laundering hazard SC-025 exists to gate is about **an unclassified thing that lazily imports `specify_cli.sync`**, and it does not care whether the thing is a directory or a file. **The package-shaped antecedent was a latent gap regardless.**

*What does **not** change:* the choice **among candidates** is untouched. (b)/(c)/(f)/(e) are rejected for the reasons above, all of which are about *ownership and edges*, none about directory-vs-file. This adjudication changes the **form** of (d), not the answer to Q1.

#### The two accompaniments — both mandatory

- **C-005 classification**: add `"specify_cli.egress"` to `INTEGRATION_PREFIXES` (`test_integration_boundary.py:75-81`). **Measured: 0 CORE violations today** — it lands green. Verified to need **no** second edit (see ground 2 above). **Gated by SC-025**, whose antecedent this plan's spec correction widens to cover the module form.
- **CI routing — TWO glob lines, not one** *(changed by plan review PA-1; the previous single-line form made routing **worse**, measured)*. Add `'src/specify_cli/egress.py'` to **both**:
  - the **`sync`** filter group (`ci-quality.yml:201-204`), and
  - the **`core_misc`** filter group (`ci-quality.yml:262-…`).

**Why both, measured.** With only the `core_misc` line, a diff confined to the new module sets **one** group true and therefore `unmatched=false` — so the `run_all` fallthrough does **not** fire, and `fast-tests-sync` (gated on the **`sync` group alone**, `ci-quality.yml:1098-1101`) does **not** run. And `tests/sync/` runs **nowhere else**: `fast-tests-core-misc`'s `core-misc` shard carries an explicit `--ignore=tests/sync`. What that leaves unrun, on exactly the diff shape FR-008 is designed to produce (a change to the one consolidated wrapper):

- **SC-021 / FR-027's two tracker behavioural ratchets** (`tests/sync/tracker/test_saas_client_consent_gate_3030.py:258-289`, `:311-324`) — the only things that catch a consolidation that leaves the import at `saas_client.py:34` but kills the call at `:329`;
- **FR-024 / SC-016's tracker-side `DENIED` content pin** — one of the two halves whose *pair* is the point;
- **the tracker attribution guard** itself.

**Without the glob edit at all, `unmatched → run_all` → all of that runs.** So a `core_misc`-only accompaniment trades **fail-safe-but-loud** for **half-blind** — it is worse than doing nothing. Dual membership is the fix, and it has **direct in-repo precedent — measured through the gate's own parser, not by reading YAML**:

```
== CONTROL (known answers) ==
  'sync' group exists                       -> True   (expect True)
  bogus group 'zzz' exists                  -> False  (expect False)
  'src/specify_cli/sync/**' in sync         -> True   (expect True)
INPUT: workflow models = 5,  named filter groups = 30

== MEASURED: dual-membership precedent ==
  'src/specify_cli/core/loopback_http.py' listed verbatim in 'sync'   -> True   (ci-quality.yml:203)
  'src/specify_cli/core/**'               in 'core_misc'              -> True   (ci-quality.yml:271)
  => the SAME FILE is claimed by TWO groups                           -> True
  groups globbing src/specify_cli/core*   -> ['core_misc', 'sync']

== MEASURED: the module form maps no src DIR at all ==
  _src_dir_of_glob('src/specify_cli/egress.py') -> None       <- module: outside the worklist by construction
  _src_dir_of_glob('src/specify_cli/egress/**') -> 'egress'   <- CONTROL: the package form does map one
```

**Nothing enforces src-glob exclusivity** — `_gate_coverage.aggregate_filter_groups` **unions** globs across workflows per group name and `mapped_src_dirs` unions across groups; neither checks for a path claimed twice (`:1384-1426`). This is better than `run_all`-forever and **strictly better than the half-blind single-group form.**

*(The `run_all` fallthrough is still not the target state: the workflow's own comment at `:438-446` calls it *"a LOUD ALARM, not steady state — add a named group for any hot unmatched dir."* Two globs is one line more than one glob and buys back everything the single glob would have silently switched off.)*

**One unnamed cost, stated plainly** *(architect lens, plan review round 2)*: joining the `sync` filter group does not only route `fast-tests-sync` — it also fires `integration-tests-sync-real-port` and the serial daemon family (`ci-quality.yml:2317-2362`) on every future PR that touches only the refusal string. Still far cheaper than `run_all`, but it is a real cost, not a free one, and it should be named rather than left implicit.

**Two senses of "sync," unlabelled** *(PR-H [LOW], plan review round 2 — this mission's own recorded recurrence pattern, PL-3, two senses of "classified")*: `egress.py` joining the `sync` **CI filter group** is CI **routing**, not an import-edge claim — `egress.py` must still import nothing from `specify_cli.sync` (F2/FR-013). Removing this glob switches off the tracker guard and both SC-021 ratchets on an `egress.py`-confined diff. Do not read group membership as licence for an import edge, and do not "tidy" the glob away to restore apparent consistency with F2/FR-013's prohibition — they answer two different questions.

**A pre-existing routing hole this mission's own accompaniments do not close** *(PR-B [MEDIUM], plan review round 2)*: `agent_surface` — which owns `src/specify_cli/tracker/**` (`ci-quality.yml:401`) — selects `fast-tests-core-misc` but **not** `fast-tests-sync`. A future PR confined to `src/specify_cli/tracker/saas_client.py` — the file whose call at `:329` FR-027/SC-021 exists to protect — therefore runs **neither** ratchet, while C-004's substring gate stays green on the import line alone. **Pre-existing, not introduced by this mission**, and this mission's own PR is covered (it carries `egress.py`, which fires `sync`). **Closing it**: add `'src/specify_cli/tracker/**'` to the **`sync`** filter group as a **third glob line** — same one-line pattern, same `core/loopback_http.py` precedent (`ci-quality.yml:203`) — so SC-021's ratchets are routed to the file they protect rather than only to this mission's own diff shape. Also recorded under FU-1 below, so the gap is not silently inherited.

**Trade-off I am accepting**: a new module for one function and one constant, plus **three** one-line edits (`INTEGRATION_PREFIXES` + two globs). **One of the three is now gated (SC-025); the two glob lines are not** — and the integration-boundary gate is blind to an unclassified module in both directions (D-8). **All three are therefore explicitly listed tasks in IC-03**, and none may be treated as covered by "no gate objects." **The failure modes of the two ungated edits are different from each other and from the gated one — see R2a/R2b in the risk register**, because that difference decides how alarmed to be about each.

**Preconditions that would falsify this choice:**

- **F1 — `specify_cli.delivery` enters `INTEGRATION_PREFIXES`.** If FU-3's transitive-reach mission (or any other) classifies `delivery/` in C-005's sense, then (f) becomes genuinely classified at **zero marginal cost to this mission**, keeps its `core_misc` routing, and sits in the package that already expresses the provenance invariant. At that point a separate single-function module stops earning its keep and **Q1 should be revisited toward (f)**.
- **F2 — the wrapper cannot be written neutrally. RESOLVED: F2 DOES NOT FIRE; the module may be created.** F2's antecedent, stated exactly: **the shared module must import from `saas_client/` or `tracker/`** at module scope, to resolve a transport-specific identifier-kind list. If so, the "neutral" premise is false and **(e)** becomes the honest answer. **Q2 was resolved by the operator on 2026-07-31: the shared module owns the sentence template, the four verdict branches, `UNDETERMINED_PROJECT_REFUSAL`, the `None` guard and the import-failure degradation; each transport passes its own identifier-set fragment *as an argument*.** A fragment passed in is not an import: **the shared module imports from neither transport**, the neutral premise holds, and **option (d) stands**. *(Consequence for sequencing: load-bearing ordering 4 — "Q2 resolved before the module is created" — is **discharged**, not pending.)*
  > **F2 is about *transport* neutrality, and nothing else.** *(Recorded because plan review PA-5 falsified a misreading of it that this plan itself had propagated into the FR-020 disagreement block below.)* An edge from the shared module to `specify_cli.decisions.store` — a **non-transport** package — **does not satisfy F2's antecedent** and therefore does not fire it. Measured, controls first (known sync-importer YES; `saas_client` 6 modules NO, `tracker` 11 NO, `delivery` 4 NO — reproducing PL-2's probe exactly): **`specify_cli.decisions.store` module-level closure = 2 modules; reaches `specify_cli.sync` = NO.** So such an edge endangers neither F2 nor FR-013. The correct objection to putting the ownership derivation in `egress` is **bounded-context ownership**, not F2 — see [§Where FR-001's ownership derivation lives](#where-fr-001s-ownership-derivation-lives--not-in-egresspy).

#### The shim decision (PB-5) — the two `egress_consent.py` modules are **DELETED**

The closing-fix outcome carried this as *"a binding plan-phase item"* and made the third `is` comparison conditional on it: **deleted → two assertions are complete; surviving as shims → a third is *required*,** because a stale shim renders the identical correct string — the exact collapse route round 3 identified.

**Decision: `src/specify_cli/saas_client/egress_consent.py` and `src/specify_cli/tracker/egress_consent.py` are deleted.** Both deciding modules rebind to `specify_cli.egress`.

**Why deletion rather than shims — the decisive reason is about what the accepted spec actually contains.** The spec implements **exactly two** `is` comparisons in SC-004 clause 3. If this plan chose "shims survive", the plan would be imposing an assertion **the accepted spec does not carry** — and an implementer working from the three operative blocks, exactly as the spec's own `## How to use this document` instructs, would never write the third one. The shim hazard would then be *known and unguarded*. **Deletion is the choice that leaves the accepted spec sufficient on its own.** Secondarily: a surviving `egress_consent.py` in each transport is precisely the file a future author edits when adding a branch, which is the second-editable-presentation FR-008 exists to make impossible; deleting removes the hazard class instead of pinning it.

**C-004 does not force a shim to survive.** C-004 requires the literal text `project_egress_refusal` to remain in `src/specify_cli/tracker/saas_client.py`. The rebound import line at `:34` — `from specify_cli.egress import project_egress_refusal` — **already satisfies it on its own**, which is exactly A-5's point about that gate being a substring test. (And FR-027/SC-021 keep the *call* at `:329` live behaviourally, which is the half C-004 does not protect.)

**Falsifier F3, measured at plan time, re-runnable in one command.** Deletion is falsified if any importer of `specify_cli.saas_client.egress_consent` or `specify_cli.tracker.egress_consent` exists outside the set below, or if either module **path** is named in an architectural allowlist or ratchet baseline.

```
grep -rn "egress_consent" --include=*.py src tests
grep -rn "saas_client/egress_consent\|tracker/egress_consent" tests/architectural/
```

Measured in this clone at revision time — **the complete importer set is four sites, all of which this mission already touches**:

| Importer | Disposition |
|---|---|
| `src/specify_cli/saas_client/client.py:23` | rebind to `specify_cli.egress` (IC-03, already listed) |
| `src/specify_cli/tracker/saas_client.py:34` | rebind to `specify_cli.egress` (IC-03, already listed) |
| `tests/specify_cli/saas_client/test_client_consent_gate_3030.py:371` | in-function import inside the SC-004 end-to-end idiom — repoint |
| `tests/sync/tracker/test_saas_client_consent_gate_3030.py:413` | same — repoint |

**And the allowlist grep returns zero**: `tests/architectural/_baselines.yaml` keys `test_egress_consent_boundary` (the *boundary guard's* baseline), not any `*/egress_consent.py` source path. Nothing in `tests/architectural/` names either file.

**Four consequences the implementer must carry, because deletion moves text that criteria anchor on and strands text that points at it.** *(Items 3 and 4 are new — plan review PA-7 found the carry-through list was two items short, and both misses are in the direction that ships a dangling pointer.)*

1. **SC-022's anchor moves with its content.** FR-026/SC-022 name the per-site enumeration at `saas_client/egress_consent.py:52-76`. Deleting the file means the enumeration — rewritten for the post-FR-001 state — **relocates into `src/specify_cli/egress.py`**. The criterion's substance is unchanged and is arguably strengthened (one home for one rationale, which is FR-008's own logic); **only the `file:line` anchor moves.** Record the move in the PR body so a reviewer does not read SC-022 as unsatisfiable. *This is the one place where deletion costs something the spec did not anticipate; it is cheap, but it must not be silent.*
2. **Four prose pointers in the two guards go stale** and must be hand-corrected to the new home: `test_client_consent_gate_3030.py:313` and `:360`, `test_saas_client_consent_gate_3030.py:361` and `:402`. These are failure-message and docstring pointers telling a future reader where the precondition is written down; a dangling pointer on a consent guard is exactly the campsite debt standing order 2 folds.
3. **A fifth pointer, and it is on the SRC side** — `src/specify_cli/saas_client/__init__.py:17`, in the package docstring: *"Every call is gated on the consent of the project that owns the data (#3030 FR-030); see ``egress_consent.py``."* **It dangles the moment the file is deleted.** The four in item 2 are all in `tests/`; the F3 grep in this section is scoped to importers, so a reader could reasonably conclude the src side was clear. It is not. Repoint it to `specify_cli/egress.py`. *(Measured: `grep -n "egress_consent" src/specify_cli/saas_client/__init__.py` → exactly this one hit.)*
4. **The relocated FR-026 enumeration carries pointers to the file being deleted, and a verbatim move ships them.** Measured, in `src/specify_cli/saas_client/egress_consent.py`, the cross-references to `tracker/egress_consent.py` are at **`:20`, `:48`, `:83` and `:148`** — and the enumeration being relocated (`:52-76`) sits **between** `:48` (*"See ``tracker/egress_consent.py`` for the full statement of why this is written down rather than assumed"*) and `:83`. **Both of those name a file this mission also deletes.** So the relocation is not a copy: the surrounding cross-references must be rewritten to point at the consolidated module — which is FR-008's own logic (one home for one rationale) applied to the prose, and is the natural place to do it, since the rationale now genuinely *is* in one file and the pointer has nowhere else to go.

**If F3 fires** — a fifth importer outside this mission's touched set, or an allowlist naming the path — **keep both shims as pure re-exports and add the third `is` comparison** (`egress.project_egress_refusal is tracker.egress_consent.project_egress_refusal`, and its SaaS twin), and say so in the PR body. That is a reversal of this decision, not a variation of it.

#### Where FR-001's ownership derivation lives — *not* in `egress.py`

FR-020 requires a single named function with a stated home. **It is not an egress concern**; it is a decision-ownership concern, and it must not be smuggled into the new module to save a file.

**Home: `src/specify_cli/decisions/ownership.py`** — the `decisions/` package already owns the ledger (`store.py`, `models.py`) and `load_index` is the function Decision D-2 mandates reusing. `src/specify_cli/decisions/**` is in the `closeout` dorny group (`ci-quality.yml:408`), and `closeout` **is** in `fast-tests-core-misc`'s gate list at `:1580` — so a `decisions/`-only diff already routes to a job collecting the SaaS guard. No new routing work.

> **CONCORDANCE WITH THE SPEC — no disagreement remains.** *(Retitled by plan review PA-8. This block previously read "DECLARED DISAGREEMENT WITH A SPEC CELL". It is **stale**: the spec now carries a **POST-ACCEPTANCE CORRECTION to FR-020** — orchestrator ruling D-7, after plan reconciliation — which adopts `src/specify_cli/decisions/ownership.py` and says so in FR-020's own cell. **The plan and the spec agree.** Reading this block as a live divergence would send a work package looking for an escalation that has already happened.)*
>
> - **The spec's operative text now names this home.** FR-020's cell ends *"Its home is `src/specify_cli/decisions/ownership.py`, NOT `src/specify_cli/egress/`"*, and the correction block that follows the Requirements table states the grounds. Cite **that block**, not this one, when a reviewer asks why the derivation is not in the wrapper.
> - **The operative criterion never said otherwise, and still does not.** FR-020's criterion is **SC-018**, which requires exactly three properties: a **single named function**, in a **stated module**, **outside `src/specify_cli/cli/commands/**`**, **imported by name from a non-CLI test module**. `decisions/ownership.py` satisfies all three. **SC-018 names no package or module**, and the FR→SC coverage table maps FR-020 → SC-018 with no placement clause. This ground is decisive on its own.
> - **The load-bearing reason, and it is stronger than the two the correction originally led with: bounded-context ownership (DIR-031).** *"Which project owns this record"* is a question in the **decisions** context — it is answered by reading the decision ledger, and it means nothing outside it. `egress.py` is a **presentation wrapper for a refusal string**: its whole content is a sentence template and four verdict branches. Putting a **ledger reader** inside it makes it a **two-concern module**, and those two concerns are precisely the pair FR-020 exists to keep apart — P-8 records **three live spellings** of "which project owns this data" and warns the plan not to merge them. Merging the ownership derivation into the refusal wrapper would re-create that conflation *inside the fix for it*, one level up.
> - **A weaker but true structural point**: it adds a dependency to a module whose entire value is its emptiness. `egress.py` earns its place by importing nothing interesting; a `specify_cli.decisions.store` import turns "one function and one constant" into "a module that reads ledgers", and strands the function away from the ledger code it is a client of.
> - **What this block used to claim, and why it no longer does — recorded so it is not re-proposed.** The original lead ground was that placing the derivation in `egress` *"would break the premise `egress/` rests on… the basis on which F2 does not fire"*. **That is false, and plan review PA-5 falsified it by measurement.** (a) **F2's antecedent** (stated verbatim in the F2 bullet under *Preconditions that would falsify this choice*, above) is that the shared module **imports from `saas_client/` or `tracker/`** — F2 is about *transport* neutrality; an edge to `specify_cli.decisions.store` does not satisfy it. (b) Measured, controls first (known sync-importer YES; `saas_client` 6 modules NO, `tracker` 11 NO, `delivery` 4 NO): **`specify_cli.decisions.store` module-level closure = 2 modules, reaches `specify_cli.sync` = NO** — so the edge does not endanger FR-013 either. **A falsifiable claim sitting in the lead position of a ruling is an invitation to overturn the ruling by falsifying it**; the ruling stands on the bounded-context and SC-018 grounds, which measurement cannot touch. The same demotion is applied to the spec's correction block — see [§The spec corrections](#the-two-spec-corrections-this-plan-authorises).

Shape (a single named function, callable by future construction sites — paula P-2/P-8):

```
resolve_decision_ownership(repo_root, decision_id, *, mission_slug=None) -> Ownership
```

returning an explicit outcome (**owned** / **not established**, with the acting root and the missions searched), never a bare bool. Per C-009 it can **never** name project B, which is exactly why AS1 and the first edge case are weakened. **It must catch `OSError` around the ledger read** (see the measured 3.11 divergence) and convert it to *not established*.

### Source Code (repository root) — files this mission touches

```
src/specify_cli/
├── egress.py                        # NEW (Q1 decision (d), PLAIN MODULE — not a package; PR-1/PA-5)
│                                    #   project_egress_refusal (shared TEMPLATE + the four verdict
│                                    #   branches; each transport passes its own identifier fragment as
│                                    #   an ARGUMENT — Q2) + UNDETERMINED_PROJECT_REFUSAL
│                                    #   ONE definition site. `specify_cli.egress.project_egress_refusal`
│                                    #   is BOTH the definition and the name SC-004 clause 3 asserts —
│                                    #   there is no __init__ re-export hop, so no fourth name (PR-1)
│                                    #   NO module-level import of specify_cli.sync, and NO import from
│                                    #   saas_client/ or tracker/ (F2's neutral premise)
│                                    #   NOTE: the constant stays OUT of __all__ (FR-011, self-enforcing
│                                    #   — test_no_dead_symbols walks every *.py under src/, per its own
│                                    #   docstring; a module is in scope exactly as a package would be)
│                                    #   NEW HOME of the FR-026 per-site enumeration (SC-022's anchor
│                                    #   moves here — see The shim decision, items 1 and 4)
├── decisions/
│   └── ownership.py                 # NEW — FR-001/FR-020/FR-021 single named function
│                                    #   (concordant with FR-020's POST-ACCEPTANCE CORRECTION — see above)
├── saas_client/
│   ├── __init__.py                  # :17 docstring pointer "see ``egress_consent.py``" → repoint (PA-7)
│   ├── egress_consent.py            # DELETED (PB-5). FR-026's :52-76 enumeration moves to egress.py —
│   │                                #   and its neighbouring cross-refs at :20/:48/:83/:148 name
│   │                                #   tracker/egress_consent.py, ALSO deleted: rewrite, do not copy
│   └── client.py                    # :23 rebind → egress; decision point at :157 (rot-mode 5)
├── tracker/
│   ├── egress_consent.py            # DELETED (PB-5) — removes the stale-shim collapse route structurally
│   └── saas_client.py               # :34 rebind → egress; MUST keep `project_egress_refusal` textually
│                                    #   (C-004 — the rebound import line satisfies it) AND as a LIVE CALL
│                                    #   at :329 (FR-027/SC-021, ratchet: two existing tests already assert it)
├── cli/commands/decision.py         # cmd_widen :523-572 — ownership check before SaasClient.from_env(:558)
└── invocation/adapters.py           # :130-145 docstring only (FR-018)
                                     #   TRAP: the identical sentence at :113 on
                                     #   register_egress_consent_resolver is TRUE — do not grep-and-replace

tests/
├── architectural/
│   ├── test_integration_boundary.py # +1 line: "specify_cli.egress" in INTEGRATION_PREFIXES (C-005).
│   │                                #   Prefix matcher at :151-152 is `mod == prefix or startswith(...)`,
│   │                                #   so the `mod == prefix` arm covers the MODULE form (verified)
│   ├── <SC-025 assertion>           # NEW — reds if that line is removed; must compare the module name
│   │                                #   against the gate's OWN prefix list, never restate the list
│   │                                #   (`"specify_cli.egress" in ["specify_cli.egress"]` is the vacuous form)
│   └── test_gate_coverage.py        # SC-006 via _gate_coverage filter_groups/job_gating_groups
├── specify_cli/saas_client/
│   ├── test_client_consent_gate_3030.py       # per-class floor, SC-012/013/016;
│   │                                #   repoint the :371 import + the :313/:360 prose pointers (PB-5);
│   │                                #   EXTRACT its inline AST predicate to a module-level function (PR-2)
│   └── test_decision_widen_ownership_3111.py  # NEW — the #3111 acceptance module. HOME FIXED HERE (PR-5):
│                                    #   imports transmitted_text from test_client_consent_gate_3030.py:73;
│                                    #   conveys A's root via SPECIFY_REPO_ROOT; in-file positive control;
│                                    #   SC-002 must-not-veto case
├── sync/tracker/test_saas_client_consent_gate_3030.py         # per-class floor, SC-012/013/016;
│                                    #   repoint the :413 import + the :361/:402 prose pointers (PB-5);
│                                    #   EXTRACT its inline AST predicate to a module-level function (PR-2).
│                                    #   Its :258-289 and :311-324 are SC-021's ratchet — must keep passing
└── <new>                            # SC-004 clause 3: the two `is` comparisons (two independently
                                     #   imported names, never two imports of one path)

.github/workflows/ci-quality.yml     # +2 glob lines: 'src/specify_cli/egress.py' into BOTH the `sync`
                                     #   group (:201-204) AND the `core_misc` group (:262-…) — PA-1;
                                     #   +FR-017 routing fix at the :1580 if-gate
docs/adr/3.x/<date>-egress-consent-boundary.md   # NEW (FR-022)
docs/context/<glossary>.md                       # "engagement" (FR-023) — MANDATORY: Q2 kept the word
```

**Structure Decision**: single project, `src/specify_cli/`. **Two new modules and no new package** — `specify_cli/egress.py` and `decisions/ownership.py`. No top-level `src/` package is added and **no `specify_cli`-level package either**, so `test_no_unregistered_src_packages` (`test_layer_rules.py:202-208`) is untouched in **two** independent ways: it scans `_SRC.iterdir()` (top-level `src/` only) **and** filters on `p.is_dir()`.

### FR-017 — the CI routing fix, with the viable shapes measured

Independently reproduced A-2's chain in this clone: `fast-tests-cli` (`:1540`) runs **only** `tests/cli/ tests/specify_cli/cli/` and never `tests/specify_cli/saas_client/`; and `fast-tests-core-misc`'s gate (`:1580`) lists ten groups in which **`cli` is absent**. ⇒ **a PR confined to `src/specify_cli/cli/**` does not run the SaaS attribution guard** — and that is exactly the file this mission edits (`decision.py:558` is one of the four SaaS construction sites).

| Shape | Cost | Measured risk |
|---|---|---|
| **(i) PRIMARY — add `needs.changes.outputs.cli == 'true'` to `fast-tests-core-misc`'s if-gate (`:1580`)** | one line | Changes job **selection** only, not collection ownership. A `cli`-only PR now runs the core-misc matrix (slower). **No topology invariant touched.** |
| (ii) fallback — add `tests/specify_cli/saas_client/` to `fast-tests-cli`'s pytest paths | one line | Viable *only because both guards are `pytest.mark.fast`* (re-measured) so `-m "fast and not windows_ci"` would collect it. **But** it would make that root owned by two same-tier jobs, risking `test_catch_all_ignore_lists_mirror_owned_roots_live` and the stated NFR-003 "never same-tier double-run" property (`:1560`). **Check that invariant before taking (ii).** |

Take **(i)**. SC-006's **standing** half asserts it statically through `_gate_coverage`'s `job_gating_groups`; it is **red at baseline**, which is correct and desirable.

*Premise carried, not measured (D-4):* A-1/A-2's chain is a reading of the workflow YAML and the dorny/`needs` evaluation model, **not a run**. It cannot be confirmed pre-implementation. Do not report it as measured. **SC-006's `[one-off]` half is what discharges it**: a real CI observation on a `cli`-only diff. It is required in addition to the static assertion, not instead of it — the static test proves the workflow *says* the right thing, the observation proves the runner *does* it. **But it cannot be taken on the mission's own PR** — `ci-quality.yml` is itself a `core_misc` glob member (`:263`), so that group goes true regardless and the run proves nothing. The two admissible substitutes (a stacked throwaway PR based on the mission branch; or a declared post-merge observation) and the confound to write down are in [§SC-006's one-off half is structurally unobtainable from the mission PR](#sc-006s-one-off-half-is-structurally-unobtainable-from-the-mission-pr-pa-2).

---

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| A new `src/specify_cli/` **module** for one function + one constant *(was: a subpackage — reduced by plan review PR-1/PA-5)* | Q1 (d): the only placement owned by neither transport that creates no new inter-transport edge. Both transports import it; neither owns it. **In its module form it also has exactly one definition site**, which is what makes SC-004 clause 3's two `is` comparisons sufficient as the spec wrote them. | **(b)/(c)** create a permanent `tracker`↔`saas_client` package edge that **measurably does not exist today**, to express a false ownership claim, for a presentation string. **(f)** carries C-005's gap while the spec records that it does not, and closing it means reclassifying an existing 5 699-LOC package — outside C-011. **(e)** is retained as the fallback under falsifier F2, but a text-equality gate is brittle and does not satisfy the mission's own title. **A *package* (the previous choice)** was rejected on measurement: `__init__.py`'s by-value re-export creates a fourth name at which MUT-1 is inert while SC-004 clause 3 stays green. |
| **Three** one-line edits (`INTEGRATION_PREFIXES`, **two** dorny glob lines) of which **two have no pre-existing gate** | D-8: the module lands under `T_LOC = 500` — and, as a module, it is **structurally outside** the unclaimed-src-dir worklist entirely (`_src_dir_of_glob` returns `None` for a `<file>.py` glob; the worklist iterates direct child **directories**). So neither the integration-boundary gate nor the LOC-gated coverage detector notices any of the three. | There is no cheaper *pre-existing* enforcement. **One third is closed by the spec: SC-025 is a standing assertion that reds if the `INTEGRATION_PREFIXES` line is removed** — the sentence-in-a-cell that round 2 flagged (N-9) became a real gate; this plan's spec correction widens its antecedent so it still fires for a **module**. **The two glob lines remain unasserted** and stay explicitly listed tasks, never treated as covered by "no gate objects." **Their failure modes differ from the prefix line's and from each other — R2a vs R2b.** |

### Risk register — what could go wrong, and how it would be detected

| # | Risk | Detection | Severity |
|---|---|---|---|
| R1 | **Partial consolidation**: a surviving re-export leaves a deciding module bound to the old object. **It renders the identical correct string**, so no text comparison distinguishes it from a correct consolidation. C-004 does **not** catch it (substring, satisfied by the import at `:34`); SC-015 does not either (a re-export is not "a second definition"). | **SC-004 clause 3's two `is` comparisons** — the only thing that reds — plus **MUT-2**, which must demonstrate in the evidence that *every string observation stays green* on the mutated state. **Structurally reduced** by the PB-5 decision: the shims are deleted, so the collapse route has no file to live in. | **High → Medium** *(after PB-5)* |
| **R2a** *(split from R2 — plan review PA-6: this is a **SAFETY** failure)* | **The C-005 classification edit is forgotten.** `specify_cli.egress` is absent from `INTEGRATION_PREFIXES`, so a CORE module may lazily import it and reach `specify_cli.sync` through it unchallenged — the tenth laundering route. **This direction is not fail-safe: forgetting it makes the gate *permissive*.** | **SC-025** — a standing assertion that reds if the line is removed (new in the accepted spec; D-8's "nothing detects it" is no longer the whole story). **Its antecedent is amended by this plan's spec correction to cover a new *module* as well as a new package** — without that amendment the criterion would go vacuous under the module form and this risk would silently return to ungated. | **High → Medium** *(gated)* |
| **R2b** *(split from R2 — plan review PA-6: this is a **COST** failure, and the two must not be reported as one)* | **A dorny glob line is forgotten.** *(a)* **Both** forgotten ⇒ the module matches no named group ⇒ `unmatched → run_all` ⇒ every future PR touching it runs the **entire suite, forever**. **Say plainly what this costs: CI minutes, not coverage.** It is **fail-safe in the coverage direction** — more tests run, not fewer — and it is loud by design; the workflow's own comment calls `run_all` *"a LOUD ALARM, not steady state"*. *(b)* **THE DANGEROUS DIRECTION — making the `core_misc` entry without the `sync` entry.** One group true ⇒ `unmatched=false` ⇒ `run_all` does **not** fire ⇒ `fast-tests-sync` (gated on `sync` alone) does **not** run ⇒ **`tests/sync/tracker/` runs nowhere** (`core-misc` shard carries `--ignore=tests/sync`), taking SC-021/FR-027's two behavioural ratchets, FR-024/SC-016's tracker-side `DENIED` pin and the tracker attribution guard with it. **That is a genuine coverage loss, and it is silent.** Half-blind is worse than fail-safe-but-loud. | **Nothing gates either glob line.** Procedural by necessity (D-8). Both are explicit tasks in IC-03, listed as a **pair**. The mitigation is the pairing itself: an implementer who adds one must add the other. **In review, the question to ask is not "is there a glob line?" but "are there two?"** | **(a) Low — cost only.  (b) High — silent coverage loss** |
| R3 | **The unreadable-ledger branch is green on 3.14 and a traceback on CI.** Measured, not hypothetical. | SC-014's `uv venv --python 3.11` run **with the `decisions/`-directory-at-`0o000` test in it**, plus an explicit `except OSError` in `decisions/ownership.py`. A local green proves nothing here — **and neither does a 3.11 green over the `file=0o000` shape, which returns `True` on both interpreters.** **Nor does a test that asserts `Path.exists()`'s return value** *(plan review PR-3)*: that passes identically with or without the `except OSError`, i.e. it is green on exactly the state this risk describes. The assertion must be on **`resolve_decision_ownership`'s outcome** — *not established*, unreadable flag set, **no exception escaping, on both interpreters**. See rule 12. | **High** |
| R4 | **FR-003 lands without FR-001/FR-002**, making an operator-typed slug affect the live path for the first time — a *widened* disclosure surface shipped as a fix (D-9). | Sequencing gate: FR-003 has no independent WP. See [§Sequencing](#sequencing-and-dependencies). | **High** |
| R5 | **The per-class floor is mistaken for coverage.** A reviewer reads FR-014–FR-017 + SC-005/SC-007 and concludes ownership is now guarded. **It is not** — the guard is syntactic by construction and its own docstring concedes so at `test_client_consent_gate_3030.py:312-315`. | MUT-4/MUT-5 make it concrete: vocabulary widening leaves counts **exactly unchanged**; predicate narrowing leaves tracker **exactly at its floor**. Both must be in the evidence. | **Medium** |
| R6 | **Fabricated consent** via the autouse conftest fixtures makes the `#3111` acceptance test green without ever consulting A's consent. | SC-024's in-file positive control. Without it, "A's consent was honoured" and "A's consent was never consulted" are indistinguishable. | **High** |
| R7 | **Mutation rot** — an obsolete plugin patching a renamed/relocated symbol silently does nothing and reads as a clean gate. Symmetrical failure: it lies in the same voice as a real pass. | Every plugin asserts its own binding, **fails loudly when its target is absent** (rule 15), and — **MUT-1/MUT-2 only** — reports the per-site split *(qualified, plan review round 2, PR-G [LOW]: the split report is scoped to the two mutations of the consolidated symbol, not every plugin)*; every kill quotes assertion text (guards against rot-mode 2). | **Medium** |
| R8 | **FR-018's grep-and-replace breaks a correct docstring.** The identical sentence at `adapters.py:113` on `register_egress_consent_resolver` is **TRUE** — sync does register that resolver. | SC-023 asserts `:113` is **unchanged**. Edit by hand, never by grep. | **Medium** |
| R9 | **`#3115` is open**: a full-suite red on this surface is not attributable. | NFR-005/SC-009 — every touched test also passes as an isolated single-file run, **with the count and file list stated** (an empty set satisfies the bare claim). | **Medium** |
| R10 | **The glossary entry is skipped.** *(Restated: Q2 is decided and it **kept** "engagement", so this is no longer a risk about which word gets picked — the word is fixed and it is one the glossary does not know, 0 of 22 entries in `docs/context/`.)* | SC-020, plus `pytest tests/architectural/test_no_legacy_terminology.py` before pushing prose. **SC-020 is a grep-gate**: presence is mechanical, but whether the entry actually *defines* the term is a plan/PR-review item — do not over-read the green. | **Low → Medium** *(now unconditional)* |
| R11 | **A hang consumes a run** — `pytest.ini` has no `--timeout` (re-measured OPEN). | Narrow the scope rather than raising the timeout; a killed run is re-run, not explained. | **Low** |
| R12 | **The narrow unreadable-ledger fall-through**: an implementation refuses on *any* unreadable index, breaking widen invocations that succeed today because one unrelated mission carries a corrupt `index.json` (49 ledgers across 333 mission dirs here). It passes **every other criterion**, and it is the one fall-through variant **SC-001 does not catch** — no request carrying B's identifier is involved. | **SC-002's must-not-veto case**, new in round 3: unreadable ledger under X **plus** a positive hit under Y ⇒ **the normal single request**. Without that test this risk is invisible. | **High** |
| R13 | **A green SC-004 is over-read.** Clauses 1 and 2 are `[ratchet]` — both hold of the *unconsolidated* state — so "SC-004 passes" is compatible with the consolidation not having happened. | Report SC-004 **per clause**, never as one verdict. Only clause 3 discriminates. Same discipline for SC-010, SC-021, and NFR-004's five pins. | **Medium** |

---

## Implementation Concern Map

> Implementation concerns are **not** work packages and are **not** executable units. `/spec-kitty.tasks` translates these into WPs.

### IC-01 — Attribution guard hardening (must land first)

- **Purpose**: Make both guards non-vacuous **per transport class** before anything moves, so the consolidation cannot silently halve coverage. US3 states this is the property that makes the rest safe to do at all.
- **Relevant requirements**: FR-014, FR-015, FR-016; NFR-003; C-002. → SC-005, SC-007, SC-012, SC-013.
- **Affected surfaces**: `tests/specify_cli/saas_client/test_client_consent_gate_3030.py`, `tests/sync/tracker/test_saas_client_consent_gate_3030.py`.
- **Sequencing/depends-on**: none. **Blocks IC-03.**
- **DELIVERABLE, NEW AND LOAD-BEARING — extract each guard's predicate to a module-level function** *(plan review PR-2 [HIGH]; without it, half the mutation suite has nothing it can provably kill)*.
  - **Measured problem.** Both attribution predicates are **local code inside a single test function body**, not importable symbols: SaaS at `tests/specify_cli/saas_client/test_client_consent_gate_3030.py:~329-345` (inside `test_every_production_construction_site_attributes_its_project`, which does `import ast` in-function and inlines the `is_direct` / `is_from_env` / `attributed` logic), tracker at `tests/sync/tracker/test_saas_client_consent_gate_3030.py:~383-388` (same shape). **Two of this plan's own rules collide with that and it previously resolved neither**: `[§Q8 table]` and this section require SC-012/SC-013 to be *"asserted against a synthetic sample, not the live corpus"* — but an inline predicate **cannot be called** on a synthetic sample; and **rule 11** mandates *"mutations are pytest plugins via `PYTHONPATH`, never source edits"* — but a plugin **cannot patch logic inside a function body**, and MUT-4/MUT-5/MUT-6 mutate exactly that logic.
  - **The failure it produces if unaddressed, and it is silent.** The path of least resistance is to **re-write the predicate in the new test** — a second copy. Then MUT-4/5/6 mutate one copy while SC-012/SC-013 assert against the other: **the mutants become unkillable, or are applied to the copy and reported as kills that prove nothing about the live guard.** This plan already names that exact failure for SC-005 — *"a harness that can drift from the real guard is a gate that goes green while the guard goes blind"* — and never generalised it to SC-012/SC-013, **which are the criteria that structurally require it**. Blast radius is IC-01, the must-land-first package: MUT-5/MUT-6 are the *only* evidence in the mission that the per-class floor does not detect predicate narrowing, and MUT-4 the only evidence for vocabulary widening. Losing all three is rot-mode 2/3 territory.
  - **The deliverable.** In **each guard file**, hoist that file's predicate to a **module-level function** — e.g. `def _saas_site_attribution(node: ast.Call) -> tuple[bool, bool]` returning `(matched, attributed)`, and its tracker twin. Then: **the live `rglob` scan calls it**, and **the synthetic SC-012/SC-013 assertions call it**, and **MUT-4/5/6 patch that symbol** via `PYTHONPATH` plugin. Importability is verified: `tests/__init__.py`, `tests/specify_cli/__init__.py`, `tests/specify_cli/saas_client/__init__.py`, `tests/sync/__init__.py` and `tests/sync/tracker/__init__.py` **all exist** in this clone.
  - **BINDING SENTENCE — quote it in the work package.** *A synthetic assertion that does not call the same predicate object the live scan calls does not satisfy SC-012/SC-013.* This is the whole point of the extraction: **one object, two callers.** Two objects with the same source text is the state that goes green while the guard goes blind.
  - **Behaviour-preserving, and prove it that way.** The extraction must not change a single count: re-run the live scan before and after and quote **`SaasClient scanned=4 unattributed=0` / `SaaSTrackerClient scanned=3 unattributed=0`** on both sides, with the input file count printed. An extraction that moves a count is a rewrite, not a hoist.
  - **The counts alone are not sufficient proof — add four synthetic witness shapes** *(PR-E [MEDIUM], plan review round 2)*. This plan's own mutation table already measured that the live-scan counts cannot see the predicate changes the extraction must preserve: MUT-4's counts are **exactly unchanged** (`scanned += 1` runs before the attribution test), MUT-5's `scanned == 3` sits **exactly at the floor**, and MUT-6's `scanned == 4` is unchanged because `direct=0`. `unattributed=0` is equally blind, because every live site is already attributed. **So an extraction that accidentally widened or narrowed a predicate would emit byte-identical before/after evidence and pass the stated proof.** Keep the counts, and additionally record, for each of the four shapes below, its `(matched, attributed)` tuple before and after the hoist, with the expected value derived from reading the pre-hoist source:
    - `SaaSTrackerClient(repo_root=…)`
    - `SaasClient.from_env(project_root=r)`
    - `mod.SaaSTrackerClient(project_root=…)`
    - `SaasClient(project_root=…)`

    These four are exactly the shapes the live corpus does **not** contain, which is why they discriminate a widened or narrowed predicate and the live-scan counts do not.
- **Verification**: per-class floors as named integers (**tracker 3, SaaS client 4** — re-measured above over **937 files**). MUT-4, MUT-5 **and MUT-6** are mandatory evidence, including the counter-intuitive controls (counts unchanged / exactly at floor). **All three depend on the predicate extraction above** — they patch the extracted symbol, and they are not writable against an inline predicate without violating rule 11. SC-012 and SC-013 assert against a **synthetic** sample, not the live corpus, **by calling the extracted predicate the live scan calls**. **SC-013 is two per-class MATCH assertions** — tracker `mod.SaaSTrackerClient(project_root=…)`, SaaS `SaasClient(project_root=…)` (measured `direct=0, from_env=4`) — and **no non-match is asserted anywhere**; reintroducing one would red on a coverage *gain* and collide with FU-8. **SC-005 carries a `[one-off]` half**: actually remove one site of each class and quote the two reds; do **not** convert the demonstration into a standing synthetic harness that can drift from the real guard. **SC-012's SaaS witness is `SaasClient.from_env(project_root=r)` → matched and FLAGGED unattributed** — the obvious witness ("the SaaS guard is not widened to admit tracker-only spellings") is **vacuously true**, because the SaaS guard already accepts `project_root=` for direct construction (DB-4).
- **Bundle A bite**: `#3113` **does not bound this work** — it is a property of `_transmits_a_body` in the *boundary* guard. The attribution guards count every match regardless of call form and have **no positional blind spot** (R-12/D-10). Do not credit a coverage claim to `#3113` here. The real bound is the **literal class-name match** (`ast.Name(id="SaasClient")` / `name != "SaaSTrackerClient"`): an aliased import, a factory, or an injected transport is invisible. State that bound explicitly; it is not `#3113`'s.
- **Risks**: R5.

### IC-02 — FR-017 CI routing (must land before IC-04)

- **Purpose**: Ensure the guard covering this mission's own construction-site edit runs on this mission's own diff. Non-negotiable: otherwise IC-04 ships unguarded.
- **Relevant requirements**: FR-017 (Decision D-4, narrow half). → SC-006.
- **Affected surfaces**: `.github/workflows/ci-quality.yml` (gate at `:1580`), `tests/architectural/test_gate_coverage.py`.
- **Sequencing/depends-on**: none. **Blocks IC-04** — this is the whole point of the requirement.
- **Verification**: SC-006 asserted **statically** through `_gate_coverage`'s `filter_groups` / `job_gating_groups` (verified present at `:474`, `:476`, `:496-497`, `:611-615`). **Red at baseline** — confirm the red before fixing. **`[standing]` assertion + `[one-off]` real CI observation on a `cli`-only diff**; the one-off half is separately required because it is what discharges D-4's explicit unverified premise.
- **The `[one-off]` half is RESCHEDULED, because it cannot be taken here** *(plan review PA-2 [HIGH]; the stacked-throwaway-PR substitute struck at plan review round 2, PR-A [MEDIUM])*. `.github/workflows/ci-quality.yml` is itself a `core_misc` glob member (`:263`) and this IC edits that file, so on **any** PR carrying the fix `core_misc` goes true regardless of the diff's shape and `fast-tests-core-misc` is selected **for the wrong reason**. **The run proves nothing and looks like proof.** It is **necessarily a post-merge observation**: take it on the first `cli`-only PR that lands after the mission merges, quoting the selected job list and the run URL, routed through the **`post-merge-arch-gate-adjudication`** procedure. **Write the confound into the PR body**, so nobody offers the mission PR's own `core_misc` run as evidence. Full statement: [§SC-006's one-off half…](#sc-006s-one-off-half-is-structurally-unobtainable-from-the-mission-pr-pa-2).
- **Bundle A bite**: `#3115` most directly — FR-017's ultimate evidence would be a CI job-selection observation, which is unavailable **in-mission for the reason above as well as `#3115`'s**. The static assertion is what makes it verifiable in-mission.
- **Risks**: taking shape (ii) and tripping the same-tier double-run invariant. Take shape (i).
- **Premise**: A-1/A-2's chain is a YAML reading, not a run (D-4). Carry it as stated.

### IC-03 — The wrapper consolidation (Q1 (d), module form)

- **Purpose**: One editable presentation of the refusal policy, in a **module** owned by neither transport.
- **Relevant requirements**: FR-008, **FR-009 `[ratchet]`**, FR-010 `[ratchet]`, FR-011 `[ratchet]`, FR-012 `[ratchet]`, FR-013 `[ratchet]`, FR-024, FR-026, FR-027 `[ratchet]`; C-001, C-003, C-004, **C-005**. → SC-004, SC-010, SC-015, SC-016, SC-021, SC-022, **SC-025**. *(FR-025/SC-017 are **retired** — folded into SC-004 clause 3.)*
- **Affected surfaces**: **new** `src/specify_cli/egress.py` (**a module — not a package**; see the [package→module adjudication](#the-packagemodule-adjudication-plan-review-pr-1--pa-5--read-this-before-restoring-the-package)); **deleted** `saas_client/egress_consent.py` and `tracker/egress_consent.py` (PB-5); `saas_client/__init__.py:17`; `saas_client/client.py:23,157`; `tracker/saas_client.py:34,329`; the two guards' imports and prose pointers; `tests/architectural/test_integration_boundary.py` + the SC-025 assertion; `.github/workflows/ci-quality.yml` (**two** globs).
- **Sequencing/depends-on**: **IC-01** (guards hardened first). **Q2 is resolved** (operator, per-caller fragment in a shared template) and **falsifier F2 does not fire**, so the module may be created — this precondition is **discharged, not pending**.
- **The module form is not a stylistic choice and must not be "tidied" into a package.** `specify_cli.egress.project_egress_refusal` must be **the definition site itself**, not a re-export. Adding an `egress/__init__.py` that re-exports from `egress/refusal.py` re-creates the measured **fourth name** at which MUT-1 is inert while SC-004 clause 3 stays green (PR-1, 8 cases, control first). If the module ever genuinely needs splitting, the split must land **with** a third `is` comparison and a restatement of the three-names list — that is a reversal of this decision, not a refactor.
- **Q2's binding shape for the module**: the shared module owns the **template**, the four verdict branches, `UNDETERMINED_PROJECT_REFUSAL`, the `None` guard and the import-failure degradation; **each transport passes its own identifier-set fragment as an argument**. **Both current `DENIED` strings survive verbatim** — `saas_client` "mission and **decision** identifiers", `tracker` "mission and **engagement** identifiers". **This consolidation changes no operator-visible text.** A "consolidation" that leaves two templates and merely parameterises them does **not** satisfy FR-008 (SC-015).
- **FR-009 is `[ratchet]`, and its bar is scoped** (ruling PB-3): it covers **the identifiers of the project whose consent was refused** — the confidential content this mission protects. It does **not** cover every field in the request: `team_slug` is the **destination** (the team the request would be addressed to, not the refusing project's identity) and `invited_user_ids` are **recipient** ids, ints. Neither is an identifier *of the project being refused*. **Corollary, and it is the reason the scoping is written down: nobody may "fix" the refusal string by appending the destination team's name** — that would *add* an identifier to an operator-facing message rather than remove one.
- **Explicitly listed tasks with their own assertions — THREE, not two** *(the CI-routing accompaniment became two lines; plan review PA-1)*:
  1. `"specify_cli.egress"` added to `INTEGRATION_PREFIXES` (`test_integration_boundary.py:75-81`) — measured green (0 CORE violations over 93 CORE files); the gate's matcher at `:151-152` (`mod == prefix or mod.startswith(prefix + ".")`) covers the module form on its first arm. **Gated by SC-025**, which must compare the module name against the gate's own prefix list (`"specify_cli.egress" in ["specify_cli.egress"]` is the vacuous form the criterion forbids). **This mission also amends SC-025's antecedent so it covers a module** — without that amendment the criterion is vacuous here and this task returns to ungated.
  2. `'src/specify_cli/egress.py'` added to the **`sync`** filter group (`ci-quality.yml:201-204`). **Gated by nothing.**
  3. `'src/specify_cli/egress.py'` added to the **`core_misc`** filter group (`ci-quality.yml:262-…`). **Gated by nothing.**

  **Tasks 2 and 3 are a pair and must land together.** Doing 3 without 2 is the **dangerous** direction: one group true ⇒ `unmatched=false` ⇒ `run_all` does not fire ⇒ `fast-tests-sync` (gated on `sync` alone, `:1098-1101`) does not run ⇒ `tests/sync/tracker/` runs **nowhere** (`core-misc` shard has `--ignore=tests/sync`), silently dropping SC-021/FR-027's two ratchets, FR-024/SC-016's tracker-side `DENIED` pin, and the tracker attribution guard. Doing neither is merely expensive (`run_all`). See R2b.
- **Verification**: **SC-004 is reported per clause.** Clauses 1–2 are `[ratchet]` and hold of the unconsolidated state; **clause 3 — the two `is` comparisons between independently imported names — is the clause that reds**, and under the PB-5 decision two are complete. FR-027/SC-021 is a **`[ratchet]`: no new test is required** — the two existing tests in `tests/sync/tracker/test_saas_client_consent_gate_3030.py` (`:258-289`, `:311-324`) already drive the tracker into a non-consenting project through the call at `saas_client.py:329`; **the requirement is that they keep passing**, and a change leaving only the import at `:34` reds them. MUT-1, MUT-2 mandatory. The four pre-existing `could not be determined` assertions are **added alongside, never modified** (`delete-the-assertion-not-the-test`).
- **PB-5 carry-through — FOUR items, not two** *(items 3 and 4 added by plan review PA-7; the full statement with measurements is in [§The shim decision](#the-shim-decision-pb-5--the-two-egress_consentpy-modules-are-deleted))*:
  1. Repoint the two **in-test imports** — `test_client_consent_gate_3030.py:371`, `test_saas_client_consent_gate_3030.py:413`.
  2. Hand-correct the **four test-side prose pointers** — `:313`, `:360`; `:361`, `:402`.
  3. **Repoint the SRC-side pointer at `src/specify_cli/saas_client/__init__.py:17`** — *"…(#3030 FR-030); see ``egress_consent.py``"* — which dangles the moment the file is deleted. The F3 grep in this plan is scoped to *importers*, so the src side reads as clear and is not.
  4. **Relocate FR-026's enumeration into `egress.py` — rewriting, not copying, its neighbouring cross-references.** The enumeration (`:52-76`) sits between references to `tracker/egress_consent.py` at `:48` and `:83` (also `:20`, `:148`), and **that file is deleted too**, so a verbatim relocation ships a pointer to a deleted file into the brand-new module. **SC-022's anchor moves with the content; say so in the PR body.**
- **Bundle A bite**: `#3113` — if the consolidation *moves a sink* or reaches the wrapper through an alias, the **boundary** guard may not see it. Any green from `test_egress_consent_boundary.py` on a moved sink must be reported as **conditional on `#3113`**.
- **Risks**: R1, **R2a**, **R2b**, R7.

### IC-04 — Ownership before egress (the `#3111` half, P1)

- **Purpose**: Establish from local files under the acting root only that the checkout owns the decision, before any request is built; refuse otherwise.
- **Relevant requirements**: FR-001, FR-002, FR-003, FR-004 *(folded)*, FR-005, FR-006, FR-007, FR-020, FR-021; NFR-002; C-007, C-009, C-010. → SC-001, SC-002, SC-003, SC-011, SC-018, SC-024.
- **Affected surfaces**: **new** `src/specify_cli/decisions/ownership.py`; `cli/commands/decision.py:523-572`; **new acceptance module `tests/specify_cli/saas_client/test_decision_widen_ownership_3111.py`** (home fixed by plan review PR-5 — see below).
- **Sequencing/depends-on**: **IC-02** (so the SaaS guard actually runs on this diff). **FR-003 must not land without FR-001 + FR-002** — they are one work package, never separable (D-9).
- **Verification**: the red-first proof above — **observe the pre-fix request carrying B's `decision_id` to A's team**, then assert the bytes with `transmitted_text(sink)`. Both checkouts' `.kittify/config.yaml` **on disk**; **A's root conveyed through `SPECIFY_REPO_ROOT`**; **in-file positive control**. SC-002's control in the **same module and fixture**. **Two divergence routes — `--mission-slug` and `SPECIFY_REPO_ROOT` — not four** (the other two root routes are held by construction at `locate_project_root`; state the bound in the module). **SC-002's must-not-veto case is mandatory**: unreadable ledger under X + positive hit under Y ⇒ **the normal single request**, not a refusal.
- **Acceptance-module shape — three items corrected by plan review PR-5**:
  1. **Home: `tests/specify_cli/saas_client/test_decision_widen_ownership_3111.py`.** Previously unspecified, which mattered because `transmitted_text` **must be imported** from `test_client_consent_gate_3030.py:73` in that directory, **never re-implemented** — a private copy of the byte extractor is the single easiest way to make the mission's load-bearing assertion assert nothing. The package is importable (all `__init__.py` verified present).
  2. **Convey A's root through `SPECIFY_REPO_ROOT`, not through a kwarg.** The old instruction *"pass both roots explicitly, never omit the kwarg"* is **not executable** alongside the mandatory real invocation: under `spec-kitty agent decision widen` the test never constructs a client — **`cmd_widen` does**, at `decision.py:558`. There is no kwarg. An implementer reconciling the two would construct inline and **lose C-008's real entry point and the FR-003 slug route with it.** `SPECIFY_REPO_ROOT` is the supported channel and the highest-priority tier of `locate_project_root` (`core/paths.py:224`), and it doubles as one of SC-001's two required routes.
  3. **Record the measured reason the autouse fixtures cannot fire on this path** — it is what makes the directory choice safe, and it was previously unstated: **`from_env` always passes `project_root=` as a keyword even when the value is `None`** (`client.py:137-142`), so the guard `if "project_root" not in kwargs` (`conftest.py:74`; mirror at `tests/sync/tracker/conftest.py:166`) is **structurally unreachable from `cmd_widen`**. Put that in a comment in the module, with the two `file:line`s: if a refactor ever makes `from_env` omit the kwarg on the `None` branch, **or** either conftest guard changes to `if kwargs.get("project_root") is None`, the fabricated-consent trap reopens and the module must move *(consumer-side falsifier added by plan review round 2, PR-F [MEDIUM] — such a reopening is invisible to every other test this mission adds, because the ownership gate keys on `SPECIFY_REPO_ROOT`, not `project_root`)*. Item 9 of the mandatory shape above adds the compensating runtime assertion that catches it.
- **SC-002 clause (c) — both sides now have a stated address** *(plan review PR-3: the plan carried the must-not-veto half four times and never said where the refuse half lived)*. **Must-not-veto half**: here, in this acceptance module (unreadable X + hit in Y ⇒ the normal single request). **Refuse half** (no positive hit **and** at least one unreadable ledger ⇒ refuse): **SC-014's unreadable-ledger test**, per spec `:1205-1206` — the same test whose target is `resolve_decision_ownership`'s outcome under `decisions/` at `0o000`. Neither half may be reported as discharging the other.
- **FR-021 discharge — take option (ii)**: do **not** use `resolve_feature_dir_for_mission` (`missions/_read_path_resolver.py:1608-1631`), which accepts ambient context through **three** parameters (`mission_slug`, `cwd`, `env` — the channel `SPECIFY_REPO_ROOT` travels on) and returns `Path(context.feature_dir)` with **no containment assertion**. Restrict the slug to selecting among the mission directories FR-001's glob has **already enumerated under `repo_root`**, which makes containment hold by construction rather than by assertion. Cheaper, and it removes the seam instead of guarding it.
- **SC-018 is conditional on that choice, and option (ii) changes what must be asserted** (N-4). Under **(i)** the containment check is shown **biting**; under **(ii)** the outside-root case **cannot be constructed**, so the substitute is an **enumeration equality** — a test asserts that **every path fed to `load_index` is a member of the glob's own result set**. *"No test, because the case can't happen" is not a discharge.* **Under either discharge**, two further obligations hold: candidate paths are **`.resolve()`d before** the membership test (`Path.glob` follows a symlinked mission directory, and `is_relative_to` on the unresolved path returns `True`), and the **one-level depth of the glob is pinned**. Measured: **0 symlinks** under `kitty-specs/` today, and one-level glob vs repo-wide `rglob` both return **49** with **0 missed** — a shape assumption held by measurement, not by construction (N-5).
- **Compatibility, declared not discovered** (SC-002 clause (a)): this design substitutes *"this checkout's committed ledger lists the decision"* for *"the decision exists"*, and **those are not the same set**. At `bb2020fea` `cmd_widen` reads **no** ledger, so **every ULID the server accepts succeeds today**. Currently-succeeding invocations that become refusals: a decision **pushed but not yet pulled here**, and any checkout where `kitty-specs/` is filtered, sparse-checked-out or cleaned. **The lane-worktree case is not separate** — `locate_project_root` returns the **main** repo root even when invoked from a worktree (`core/paths.py:184-186`, and its docstring says so), so FR-001's glob reads the main checkout's `kitty-specs/`. **SC-002 does not claim these keep working; it claims they refuse loudly and for a stated reason.**
- **Q5 — RESOLVED: `--dry-run` warns, it does not refuse.** Dry-run transmits nothing so it is not an egress path, and refusing would remove its inspection value. But it **must** surface the ownership verdict, or dry-run becomes a way to get the id formatted for copy-paste into a real invocation without ever seeing the mismatch. *(Operator may overrule; recorded as a decision, not a silent choice.)*
- **Q7 — RESOLVED: one check, at the CLI boundary, reusing an existing regex.** FR-005's shape check binds `cmd_widen`'s argument — the boundary where the value's provenance changes from keyboard to store. **Reuse** one of the three existing ULID regexes (`decisions/verify.py:40`, `invocation/record.py:30`, `context/mission_resolver.py:55`) rather than writing a fourth; adding a fourth at the CLI *and* a fifth in the client would be this mission's own whack-a-field (paula P-10). **It is defence-in-depth and does not discharge FR-001/FR-002** — a bare regex would make a naive reading of SC-001 green with no ownership logic at all (R-5), which is why SC-001 requires a well-formed ULID present in B's ledger.
- **Bundle A bite**: `#3115` — full-suite reds here are not attributable; NFR-005's isolated per-file runs are the compensation. The timeout gap (FU-6) means a hang consumes the run.
- **Risks**: R3 (the `except OSError` requirement is **not optional**), R4, R6.

### IC-05 — The `#3109` seam (Decision D-1: keep and pin)

- **Purpose**: Make the empty seam read as a decision rather than an oversight.
- **Relevant requirements**: FR-018, FR-019. → SC-008, SC-023.
- **Affected surfaces**: `invocation/adapters.py:130-145` (docstring only), `invocation/__init__.py:21,111`, a pin test.
- **Sequencing/depends-on**: none. Fully independent; can land any time.
- **Verification**: **the before-state is the export half only.** Deleting the `def` is a collection-time `ImportError` in two files and is node-id pinned — it is *not* a valid before-state (D-4), and an implementer working red-first would otherwise find the red already present and land a pin with no discriminating power. **SC-008 is `[standing]` pin + `[one-off]` removal demonstration**: quote the red from actually removing the export. *The export half is genuinely unpinned today, independently verified in spec round 2*: `invocation/adapters.py` has **zero** `__all__` declarations, `grep "from specify_cli.invocation import" src/` returns **zero** hits, and `test_all_declarations_required.py:1-20` gates only `src/charter/` and `src/kernel/`. FR-018 narrows to (i) delete the false sentence at `:135`, (ii) state nothing registers a factory today, (iii) **point to** `propagator._get_saas_client` (`propagator.py:70-83`) as the canonical record rather than restating it — a second copy of one rationale is the exact defect FR-008 removes (A-9).
- **Risks**: R8 — **SC-023 asserts `adapters.py:113` is unchanged.** Hand-edit only.

### IC-06 — Durable record: ADR + glossary

- **Purpose**: Put the boundary in the charter authority path. This is the only item acting on **recurrence** rather than on an instance, and the cheapest in the bundle (paula P-4).
- **Relevant requirements**: FR-022, FR-023. → SC-019, SC-020.
- **Affected surfaces**: `docs/adr/3.x/`, `docs/context/`.
- **Sequencing/depends-on**: **IC-03** (the ADR names the wrapper's home). *The glossary entry no longer waits on Q2 — the word is **"engagement"**, fixed by the operator's decision — so FR-023 could in principle land earlier; keeping it here costs nothing and keeps the durable-record work in one package.*
- **Verification**: SC-019's grep is the same one that measured zero, with a controlled diagnostic already established (a known-present term returns 12, a nonsense term returns 0). **Both SC-019 and SC-020 are grep-gates and the spec says so in their own text: presence is mechanical, content is not enforceable by them.** A file containing only the three search terms passes SC-019. That is accepted rather than papered over — the alternative pins prose wording — **so the content is a plan-review and PR-review item, and the reviewer must read the ADR rather than trust the green.** The ADR must name **three** things: the boundary; the **provenance invariant** (consent keyed on something derived from the record being sent, never from ambient context — framing 3, superseding the orchestrator's earlier "path-typed seam is the defect" framing); and that **the attribution guard is syntactic** — it can prove a root was passed, never that it was the owning root.
- **Risks**: R10.

### IC-07 — Cross-cutting verification evidence

- **Purpose**: Produce the evidence NFR-005/NFR-006 require, in the stated form.
- **Relevant requirements**: NFR-004, NFR-005, NFR-006. → SC-009, SC-014.
- **Sequencing/depends-on**: all other ICs.
- **Verification**: `uv venv --python 3.11`, run this mission's touched test files **plus both attribution guards**, quote the `N passed` line **verbatim**. **The run must include the unreadable-ledger test, and that test must be in the shape that can reach the branch: chmod the containing `decisions/` *directory* to `0o000`, leaving `index.json` readable.** **What it asserts is `resolve_decision_ownership`'s OUTCOME — *not established*, unreadable flag set, no exception escaping — and that must hold on BOTH interpreters** *(corrected by plan review PR-3; see rule 12)*. The earlier phrasing here named the expectation as *"at `decisions/store.py:64`: `Path.exists()` returns `False` on 3.12+ and raises `PermissionError` on 3.11"` — **that is a `pathlib` characterization test**: true whether or not `decisions/ownership.py` carries the `except OSError`, therefore green on precisely the regression this whole section exists to catch. The `Path.exists()` divergence is the **reason** the `except OSError` must be written; the **assertion** is on the function's outcome. *(This same test is the home of **SC-002 clause (c)'s refuse half** — no positive hit + at least one unreadable ledger ⇒ refuse, spec `:1205-1206`.)* **Name the test in the evidence as one the 3.11 run included** — *"a green 3.11 run over files that never touch the branch is a true statement about nothing."* A `file=0o000` companion is permitted **only** if labelled as `read_text` → `PermissionError` at `:66` and explicitly **not** offered as NFR-006 evidence. **Skip honestly** if mode bits are not enforced for this process; a silently-passing `0o000` test is the vacuous case. Isolated single-file runs for every touched file, **with the count and the file list stated** — "all isolated runs passed" over an unstated set is vacuous (R-22). NFR-004's five per-branch pins (`DENIED` contains `sync opt-in`; import-failure contains the exception text; `NO_RESOLVER` names the resolver; `UNDETERMINED` and `UNANSWERABLE` remain **distinguishable** despite both containing `could not be determined` — correction C-1). All five already hold at `bb2020fea`; **NFR-004 is a `[ratchet]` — the build work is pinning them, and the pins do not discriminate a correct implementation from an incorrect one.**

### Sequencing and dependencies

```
IC-01 (guards)  ──────────────┐
                              ├──▶ IC-03 (consolidation) ──▶ IC-06 (ADR + glossary)
IC-02 (CI routing) ──▶ IC-04 (ownership / #3111) ─────────────┘
IC-05 (seam)  — independent, any time
                                          all ──▶ IC-07 (evidence)
```

**The four orderings that are load-bearing, and why:**

1. **IC-01 before IC-03.** The guards are what make the consolidation safe to attempt (US3). Moving the wrapper first means the only protection against F-A3's halving mechanisms is a global `assert scanned` that stays positive from the surviving class.
2. **The PR carrying the `decision.py:558` edit must either include a non-`cli` path or postdate IC-02.** *(Restated by plan review PA-3; the old form was "IC-02 before IC-04", justified by "a `cli/**`-only PR does not run the SaaS attribution guard". That premise is true in general but **does not hold for this mission's own diff**, so the ordering was resting on a rationale that does not apply to it.)* The general hazard is real and measured: a PR confined to `src/specify_cli/cli/**` selects `fast-tests-cli`, which runs only `tests/cli/ tests/specify_cli/cli/`, and `fast-tests-core-misc`'s gate (`:1580`) does not list `cli` — so the SaaS attribution guard does not run, and `decision.py:558` is one of its four sites (A-2). **But IC-04 also creates `src/specify_cli/decisions/ownership.py`**, and `src/specify_cli/decisions/**` is in the **`closeout`** group (`ci-quality.yml:408`), which **is** in `fast-tests-core-misc`'s gate list — so the guard runs on IC-04's diff **regardless of IC-02**. The obligation that actually binds is therefore the restated one above, and **`decisions/ownership.py` is what supplies the non-`cli` path today**. Keep IC-02 first anyway (it is free, and it closes the general hole FR-017 names), but **do not report "IC-02 landed first" as the reason the guard ran on IC-04** — it is not, and a work package that splits `decision.py` away from `ownership.py` would break the real invariant while satisfying the stated one.
3. **FR-003 never lands without FR-001 + FR-002.** In isolation FR-003 *widens* the disclosure surface: it makes an operator-typed slug affect the live path for the first time (today it is inert, `decision.py:550`, dry-run only). They are one work package (D-9).
4. **Q2 resolved before `egress.py` is created — DISCHARGED, not pending.** Falsifier F2 is decided by Q2's answer, and discovering it after the module exists would mean unwinding it rather than choosing option (e). **Q2 was resolved by the operator (per-caller fragment passed as an argument), so `egress.py` imports from neither transport and F2 does not fire.** The ordering is retained here because it is the reason the module is safe to create, not because anything is still blocked. *(If a future edit makes the shared module import a transport-specific list **from `saas_client/` or `tracker/`** at module scope, F2 fires retroactively and the answer is option (e) — that is a standing property of the module, not a one-time check. **An edge to a non-transport package such as `specify_cli.decisions` is not F2's antecedent** — see the note under F2.)*

**Deliberate, in-scope behaviour change to declare up front (not an SC-002 red):** an invocation that today succeeds *while passing a `--mission-slug` that disagrees with the record* succeeds only because the flag is silently ignored on the live path. Making it stop is the **point** of FR-003. That case belongs to SC-001, not SC-002. Declare it in the PR body; do not let it surface as an SC-002 failure.

### Open questions — **only Q3 remains open**

- **Q2 — which wording survives? — CLOSED by the operator, 2026-07-31.** *(This was the plan's one open item; it is no longer one, and the plan's earlier framing of it was superseded.)* **A per-caller identifier fragment injected into a shared template; both current `DENIED` strings survive verbatim.** Two things the plan previously said about Q2 are now **withdrawn**: (a) that FR-009 requires the merged string to name the **union** of the enumerated identifier-kind sets — **the union string is explicitly *not* the requirement**, because naming `decision_id` to a tracker operator overstates exposure and FR-009's second clause forbids it; and (b) that Q2 gates IC-03's start — it no longer does. What survives from the plan's framing is the asymmetry that made the union wrong: **the tracker carries no `decision_id`; the SaaS client carries no `project_slug` and no issue titles** — `mission_id` is the **only** member the two sets share. **FR-023 is now unconditional**: the answer keeps "engagement" in operator-facing text, so the glossary entry must land (the round-1 escape "*or* resolve Q2 away from the word" is closed).
  *Q2's own falsifier, carried*: if a future endpoint makes the two transports' identifier sets **identical**, the per-caller fragment becomes ceremony and the union string becomes correct and simpler. Revisit then.
- **PB-5 — do the `egress_consent.py` modules survive as shims? — DECIDED BY THIS PLAN: deleted.** See [§The shim decision](#the-shim-decision-pb-5--the-two-egress_consentpy-modules-are-deleted) for the four carry-through consequences and falsifier **F3**. **Two `is` comparisons are complete — and it now takes BOTH decisions to make that true.** PB-5's deletion closes the **shim** route; the **module** form closes the **fourth-name** route PR-1 measured, which PB-5 never considered and which deletion alone does not touch. Reversing either one re-opens the need for a third comparison, and they reverse for different reasons (F3 fires / the module is split into a package).
- **Q5 (dry-run) and Q7 (ULID check placement)** are resolved above as *recorded decisions* with reasoning, not silent choices — overrule either if you disagree. Both are now recorded in the spec as plan-phase resolutions, with falsifiers.
- **Q3 (uuid-typed seam)** stays deferred to **FU-5** per C-011 and framing 3: a type cannot express provenance, so the change is optional rather than indicated. **It is the only question still open.**

### Follow-up issues to file (FU-1…FU-8 — all now carried in the spec)

FU-1 re-key guard routing on construction-site locations · FU-2 extend `ConsentedBatch` to both transports · FU-3 scan for CORE→`sync` transitive reach (nine exist today) · FU-4 cross-checkout ownership search · FU-5 uuid-typed seam · FU-6 global `pytest` timeout.

**FU-1, one sentence recorded here** *(PR-B [MEDIUM], plan review round 2)*: `agent_surface` routes `src/specify_cli/tracker/**` to `fast-tests-core-misc` but not to `fast-tests-sync`, so without the third `sync`-group glob line proposed at [§The two accompaniments](#the-two-accompaniments--both-mandatory), SC-021's ratchets are not routed to the file they protect (`tracker/saas_client.py:329`) — the mission must not hand over a guarantee that expires the moment `egress.py` leaves the diff.

**FU-7 — classify `specify_cli.delivery` in `INTEGRATION_PREFIXES`.** Generated by this plan and **since adopted into the spec's follow-up table**. Measured: it is in the `core_misc` dorny group but **not** in the integration-boundary gate's INTEGRATION prefixes, and adding it is **green today (0 CORE violations over 93 CORE files)**. Out of scope here under C-011, and it is the falsifier F1 that would reopen Q1 toward option (f).

**FU-8 — guard `mod.SaasClient.from_env(...)`, matched by *neither* attribution guard today** (new in the spec, round 2). Recorded here because it **binds this mission's test design**: closing FU-8 means *widening* a predicate, so **no non-match may be pinned anywhere in this mission** — a non-match pin would cement the hole FU-8 exists to close. Not a regression this mission introduces; recorded so the silence is not mistaken for coverage.

---

### THE MISSION'S UNENFORCED OBLIGATIONS — restated, because there are now TWO and they are both glob lines

*(Previously one line; PA-1's adjudication made it two. Both are procedural by necessity — the LOC-gated detector needs `T_LOC = 500` and a module is outside the dir-based worklist entirely, so nothing in the repo will notice either omission.)*

**Nothing gates `'src/specify_cli/egress.py'` in the `sync` group. Nothing gates it in the `core_misc` group.** SC-025 closed the `INTEGRATION_PREFIXES` third; these two remain open, and **they are fail-safe in the coverage direction only if BOTH are present**:

| State | Consequence |
|---|---|
| **both present** *(the required state)* | `fast-tests-sync` **and** `fast-tests-core-misc` are selected on an `egress.py`-confined diff. Everything that must run, runs. |
| **neither present** | No named group matches ⇒ `unmatched → run_all` ⇒ **the whole suite runs, forever, on every future touch.** Costly and loud; **fail-safe in the coverage direction** — it is CI minutes, not coverage. |
| **`core_misc` only** *(the trap)* | One group true ⇒ `unmatched=false` ⇒ `run_all` does **not** fire ⇒ `fast-tests-sync` (gated on `sync` alone) does **not** run ⇒ `tests/sync/tracker/` runs **nowhere** (`core-misc` shard: `--ignore=tests/sync`). **Silent coverage loss on exactly this mission's change shape.** |
| **`sync` only** | `fast-tests-core-misc` is not selected on that diff; the SaaS-side guard and the architectural shard are missed. Same shape of failure as the row above, other half. |

**Named here, in the plan, and required in the handoff — as a pair, never as "add a glob line".** In review, the question is *"are there two?"*, not *"is there one?"*

---

## The two spec corrections this plan authorises

**Exactly two, both applied to `spec.md`, no others.** Recorded here so a reader of the plan knows which spec text moved and why, and so no successor re-opens them by re-deriving the falsified ground.

**1 — SC-025's and C-005's antecedents cover a new *module* OR a new *package*.**
Both were written package-shaped (*"If this mission lands a new `src/specify_cli/<name>/` package"*) at a time when Q1's answer was a package. Under this plan's module form the antecedent would be **false**, SC-025 would assert nothing, and the `INTEGRATION_PREFIXES` classification would silently return to the ungated state N-9 flagged and SC-025 was created to close. **This is not a workaround for the module decision.** The laundering hazard both texts exist to gate is *an unclassified thing that lazily imports `specify_cli.sync`* — it is a property of **what the thing imports**, not of whether it is a directory or a file, and the boundary gate's own matcher treats the two identically (`test_integration_boundary.py:151-152`: `mod == prefix or mod.startswith(prefix + ".")`, the first arm being the module case). **The package-shaped antecedent was a latent gap regardless of Q1's answer**, and closing it improves the spec independently.

**2 — the FR-020 POST-ACCEPTANCE CORRECTION block is rewritten and relocated.** Two defects, both found at plan review:

- **Its lead ground was falsifiable and was falsified.** Ground 1 read *"It would break the premise `egress/` rests on"* — i.e. that a `specify_cli.decisions.store` edge would fire falsifier F2 and undermine the Q1 placement. **Measured false on both counts** (PA-5): F2's antecedent is an import **from `saas_client/` or `tracker/`** — F2 is about *transport* neutrality — and the closure probe (controls first: known sync-importer YES; `saas_client` 6 NO, `tracker` 11 NO, `delivery` 4 NO) gives **`specify_cli.decisions.store` = 2 modules, reaches `specify_cli.sync` = NO**. **A falsifiable lead ground sitting in an ACCEPTED spec invites a successor to overturn the whole ruling by measuring exactly what alphonso measured.** The correction therefore: demotes ground 1 to the weaker **true** claim (*it adds a dependency to a module whose entire value is its emptiness*), **promotes bounded-context ownership (DIR-031) to first** — *"which project owns this record"* is a **decisions**-context question; `egress` is a presentation wrapper for a refusal string, and putting a ledger reader in it makes a two-concern module that re-creates the exact three-spellings conflation FR-020 exists to prevent — and **records that ground 1 was falsified by measurement** so it is not re-proposed. SC-018 (ground 2) is unchanged and remains decisive on its own.
- **It renders as a defect.** The block was inserted **inside** the Requirements markdown table, between the FR-020 and FR-021 rows, so **FR-021 through FR-027 stop rendering as table rows.** It is moved **below the table**, immediately before the Non-Functional Requirements heading. **Content-preserving except for the ground reordering above.**

*(No other spec text is touched. In particular SC-004 clause 3 is **not** amended: the module form makes its two `is` comparisons correct as written, which is the reason the module form was chosen over debugger-debbie's fix (a).)*
