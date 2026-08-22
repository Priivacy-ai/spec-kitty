# Contract: Remediation Effectiveness

**Mission**: `charter-preflight-remediation-01KYG9WK` · **Date**: 2026-07-27
**Requirements**: FR-001, FR-003, NFR-001, C-001 · **Success criteria**: SC-001, SC-005

The binding contract the FR-003 enforcement mechanism must implement. It is written as behaviour so
it stays true regardless of where the mechanism lives.

---

## C-EFF-1 — The effectiveness rule

> For every preflight check that emits a remediation, executing that remediation in a project
> exhibiting the check's non-passing state **must change that check's state**.

"Changes the state" means the check no longer reports the same non-passing state. It does **not**
require reaching a passing state in one step — a remediation that moves `missing` → `invalid` has
made progress and the operator has a next instruction. It does require that re-running the gate
does not reproduce an identical result, which is the loop the P0 describes.

## C-EFF-2 — Exemption is explicit and enumerable

> A check with no self-service remediation **must** emit `None` **and** be declared a member of the
> exemption set. Membership is never inferred from a `None` remediation.

A check may not satisfy C-EFF-1 by emitting prose that reads like escalation. Text that names any
command is a remediation and is bound by C-EFF-1.

## C-EFF-3 — The operator-visible surface is what is bound

> The assertion applies to the command the operator is actually shown, not only to the value a check
> returns internally.

Rationale: `preflight/runner.py:245` currently substitutes a default command when a check returns
`None`. A mechanism that inspected only return values would report green while the operator was
still shown an ineffective instruction — measuring the wrong surface.

## C-EFF-4 — Non-vacuity floor

> The mechanism must assert a concrete floor of **7** remediation-emitting states across **3** check
> producers, and must pin the size of the exemption set.

Both counts are load-bearing. The state floor prevents passing by finding nothing. The exemption
pin prevents passing by reclassifying a failing check as exempt.

> **Line citations in this document are as-of-authoring (2026-07-27, `main@1aed89411`) and WILL
> drift.** WP03 already moved the two exempt sites from `:318`/`:357` to `:331`/`:377` simply by
> adding docstrings. Treat every `:NNN` here as a pointer to *the state described*, not as an
> address to match. Anything that must track a site mechanically — the exemption declaration, the
> census — must resolve it from the module at runtime, never from a number copied out of this file.

Current census (`charter_runtime/freshness/computer.py`):

| Producer | Remediation-emitting states |
|---|---|
| `_compute_charter_source` | 2 (`:309`, `:318`) |
| `_compute_synced_bundle` | 2 (`:348`, `:357`) |
| `_compute_synthesized_drg` | 3 (`:447`, `:478`, `:491`) |

When a state is legitimately added or removed, the floor is updated deliberately in the same change
— that visibility is the point.

## C-EFF-5 — Isolation

> Effectiveness is proven by executing remediations against isolated fixture projects. The mechanism
> must never execute a remediation against the developer's or CI's own repository checkout.

**Use the existing fixture base.** `tests/specify_cli/charter_preflight/_fixtures.py` already
provides `init_git_repo`, `make_fresh_repo`, `seed_charter_yaml(valid=…)`, `seed_bundle_files`,
`seed_manifest` and `seed_graph` — between them they construct all four fixture shapes in
`data-model.md`. Extend it; authoring a parallel mechanism would violate DIRECTIVE_044 and drift
from the shapes `test_runner.py` and `test_computer.py` already assert against.

## C-EFF-6 — Non-vacuity is itself proven

> Introducing a deliberately ineffective remediation must turn the mechanism **red** (SC-005).

A mechanism that cannot be shown to fail has not been shown to work.

## C-EFF-7 — The mechanism must also be shown to go GREEN

> A genuinely effective remediation must turn the affected case **green**. The fixtures must be
> realistic enough for a real remediation to succeed against them.

**Added after WP01 review cycle 1**, which exposed this as a gap in C-EFF-6. C-EFF-6 only requires
proving the mechanism can *fail*. A mechanism that fails on everything — including correct fixes —
satisfies C-EFF-6 while being useless as a gate, and would make WP02 impossible to complete without
editing WP01's assertions (which WP02's reviewer must reject).

Concretely, WP01 cycle 1's minimal F2 fixture contained only the legacy bundle files. That is not a
state any real operator is in: a real legacy-bundle project is a real spec-kitty project, with the
rest of its scaffolding present. Against the minimal fixture, `spec-kitty upgrade`'s sequential
migration runner halted on an unrelated precondition (`runner.py:177-178` stops on first failure)
before ever reaching the consolidation migration — so a *correct* remediation still read as
ineffective. A false negative, not a detected defect.

**Requirement**: at least one case must be demonstrated flipping to green under an effective
remediation, and the fixtures must represent realistic project states rather than minimal artificial
ones. A false negative here is worse than no gate, because it looks like evidence.

---

## Hardening history — three variants of the same attack

The enforcement mechanism was itself attacked, successfully, twice during review. Recorded because
it is the strongest available evidence for C-001 (*a structural mechanism, not a corrected string*):
the failure mode this mission exists to close reappeared **inside the mechanism built to close it**.

Every variant has the same shape: **real coverage disappears while every gate reports green.**

| # | Attack | Outcome | Closed by |
|---|---|---|---|
| 1 | Make a real remediation-emitting state emit `None` without declaring it exempt; drop `_REMEDIATION_STATE_FLOOR` 5→4; remove the matching `_CASES` entry | **12 passed, all green** — a real state silently left coverage | Sum invariant: `_REMEDIATION_STATE_FLOOR + _EXEMPTION_FLOOR == 7`. A state may MOVE between buckets; it may not be LOST from both. |
| 2 | Add a bogus `_EXEMPT_STATES` member, bump the exemption floor, drop the state floor — keeping the sum at 7 | Caught — the state floor is a raw AST count over `computer.py`, independent of `_EXEMPT_STATES`, so it cannot be faked down by a test-file edit | (already closed) |
| 3 | **Swap** a legitimate exempt member for a real, still-effective `(function, state)` pair; remove the matching `_CASES` entry. Floors and sum all unchanged. | **12 passed, all green** — the exemption silently redirected onto a state that *does* have a working remediation, excluding it from C-EFF-1 | Identity pin: `_EXEMPT_STATES` asserted equal to its exact expected value, not merely its size. |

**Why variant 3 was invisible**: both genuinely-exempt states already emit `remediation=None`, so
neither ever appears in the AST discovery output. That made `_EXEMPT_STATES`' *values* inert with
respect to every other assertion — only its **length** was checked anywhere. Pinning the size looked
like pinning the set. It was not.

**The transferable lesson**: pinning a *count* is not pinning a *set*. Any gate that guards
membership must assert identity, or it guards only arithmetic. This is the same class as NFR-001's
"cannot pass by finding nothing", one level up — it can pass by finding *the wrong things* in the
right quantity.

## Verification scenarios

| # | Given | When | Then |
|---|---|---|---|
| V1 | A fixture in each non-passing state that emits a remediation | The remediation is executed and the check re-evaluated | The state differs from the original (C-EFF-1) |
| V2 | A check declared exempt | The preflight reports | Operator-visible output contains no command (C-EFF-2, C-EFF-3) |
| V3 | The current tree, before IC-02 | The mechanism runs | **Red** on the four `charter sync` states — this red is the NFR-002 red-first evidence for FR-002 |
| V4 | The tree after IC-02 | The mechanism runs | Green, with the C-EFF-4 floor unchanged |
| V5 | A deliberately ineffective remediation is introduced | The mechanism runs | Red (C-EFF-6 / SC-005) |
| V6 | A failing check is moved into the exemption set | The mechanism runs | Red — the pinned exemption size no longer matches (C-EFF-4) |

V3 is the load-bearing one: it is the only scenario that proves the mechanism detects the real
defect rather than a synthetic one.

---

## Known-ineffective remediations at authoring time

| Command | Why it cannot clear a check |
|---|---|
| `spec-kitty charter sync` | `charter.sync.sync()` is documented as a pure staleness reporter — `synced` is always `False` and `files_written` always empty. This is BC-2, the P0. |
| `spec-kitty charter status` | A status reporter by construction. Injected as the runner's default when a check emits `None` (`runner.py:245`) — the second instance of the same class (R-006). |

`spec-kitty charter synthesize` is **not** listed. It has a real write path and is deliberately left
for the mechanism to adjudicate empirically — hand-adjudicating it here would substitute authoring
judgement for the gate that is the deliverable.
