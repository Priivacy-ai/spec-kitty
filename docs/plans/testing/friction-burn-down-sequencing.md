---
title: Friction Burn-Down Sequencing — false-red / manual-toll engines
description: 'Sequencing note for the 3.2.x dev-friction burn-down: which false-red / manual-toll gates to drain, in what order, and which look like friction but must NOT be touched.'
doc_status: draft
updated: '2026-08-17'
related:
- docs/plans/testing/test-suite-friction-audit.md
- docs/plans/code-quality/targeted-cleanup-scoping.md
- docs/plans/3-2-x-executive-overview.md
- docs/development/how-to/manage-issue-tracker.md
- docs/adr/3.x/2026-07-17-1-red-main-is-honest-ci-is-release-authority.md
---

# Friction Burn-Down Sequencing — false-red / manual-toll engines

Companion sequencing note to the [test-suite friction audit](test-suite-friction-audit.md)
(epic [#2071](https://github.com/Priivacy-ai/spec-kitty/issues/2071) / [#1931](https://github.com/Priivacy-ai/spec-kitty/issues/1931)).
The audit named *what* the friction is; this note orders *what to drain first* for the
3.2.x **G3 — "faster, more honest engineering"** goal, and — just as important — fences off
the gates that **look** like friction but are load-bearing.

The organising principle from the audit holds: the friction is **dense and localized**, not
pervasive rot. Do not "clean the suite." Drain three named engines and harden the gate
layer, in an order that breaks the gate-vs-fix deadlock without regressing behavior.

## The friction map (what taxes every PR)

| Engine | Audit ref | What it costs | Tracked as |
|---|---|---|---|
| `file:line` architectural ratchets / frozen baselines | CT1 | A correct, behavior-neutral edit above a pinned line shifts the number → the gate goes **RED**, forcing a manual re-key **in the same PR**. The systemic finding. | **#2853** (P1), audit WP00 |
| Golden-count / cardinality gates | CT5 | Honest `len(x)==N` asserts get forced annotations for **zero real catches** (PR #3456: 0 catches, 2 forced). | **#3458**, #2625, #2631 |
| Duplicate-knowledge meta scaffold | CT3 | N hand-rolled schema/kind sources drift on every meta.json / kind change; the charter renderer's copy already **fails open** 2 kinds behind. | **#2981** (P1), #2976 |
| Parity / equivalence & bridge-compat sentinels | CT4/CT6 | Mission-scoped functional-parity tests and `runtime_bridge` round-trip sentinels that pinned a one-time cutover and now only **block deletion** of the thing they mirrored. | **#2633**, #2631, CT6 shim sweep |
| Gate-reliability layer (a red gate must mean a real regression) | — | Pre-review / regression gates that give **false verdicts** (false-red on every move-task; silent false-green testing the wrong src), leak daemons, or cover nothing. | epic **#3260** + children (#2803, #2927, #3224, #3241, #2979, #2762, #2801, #3189, #3265, #3463) |

## Sequencing

### Slice 0 (front-loadable, mechanical, no new infra) — re-key the ratchets onto `composite_key`
The audit's key insight: the drift-proof primitive `_ratchet_keys.composite_key`
(`(qualname, normalized token-line)`, content-addressed) **already exists** and is adopted
by only one test. Converting the surviving `file:line` allowlist entries onto it is
**mechanical**, and because composite keys survive line drift it is **front-loadable ahead
of any seam edit** (a plain line re-key is not — it re-keys to a line the next edit moves
again).

Scope: `tests/architectural/test_single_mission_surface_resolver.py`
(`_ALLOWLISTED_RAW_JOINS`), `test_no_write_side_rederivation.py` (delete the private
verbatim `_code_tokens_by_line` copy; converge onto the shared primitive), and the ~113
baseline/allowlist refs the audit inventoried. **This is #2853's churn-fix obligation.**

### Slice 1 (paired with Slice 0, but a *separate* obligation) — drain, don't re-home
Per paula's correction in the audit: each surviving ratchet entry must be **classified**,
not blindly re-keyed —

- **PERMANENT-BY-DESIGN** (DIAG / topology-blind-by-design seam joins) → annotate as
  permanent so they aren't mistaken for debt.
- **DEFERRED-DEFECT** → carry a tracker link + a **non-vacuous drain condition**; when the
  fix lands the entry is **removed**, not re-keyed.

Do **not** speculatively drain a load-bearing fallback (regression risk) and do **not**
re-pin a dead line (immortalized exemption). Where reachability is unknown, instrument and
prove on a real repro before draining (the `status_transition.py:336` live-evidence rule).

### Slice 2 — retire the stale parity / bridge-compat sentinels
Mission-scoped functional-parity tests and `test_bridge_compat_surface` round-trip sentinels
(#2633) whose only remaining effect is to **block deletion** of the 34 `runtime_bridge`
delegates and the `specify_cli.next` shim (CT6, 77 importers, `__removal_release__ = 3.3.0`).
Keep the one real-outcome test per seam; demote/delete the wiring twins and dead sentinels.
Gate: nothing here may relax an ATDD ratchet that is still true-red-only.

### Slice 3 — golden-count / cardinality gate calibration
#3458 / #2625 / #2631: drop redundant `len()==N` where an adjacent set-equality already
covers the contract; keep counts only where cardinality **is** the contract. This is the
"0 catches, forced annotations" toll.

### Parallel track (independent of the ratchet slices) — harden the gate layer
Epic **#3260**. These are not ratchet work; they can proceed independently and several are
cheap, high-frequency wins:

- **#3224** — pre-review baseline venv missing `hatchling` → spurious "new failure" on
  **every** move-task run. Cheapest high-frequency win; do first.
- **#2803** — lane `.venv` missing pytest → silently tests PRIMARY src (false red *and*
  green). Gate-integrity; high priority.
- **#2927** — regression-tests INTERNALERROR reads as a failure when nothing ran.
- **#2979 / #3241 / #3189 / #3265 / #3463** — coverage-integrity gaps (unmarked tests
  invisible to the partition; test files in zero gates; no >3.12 job; missing push:main
  backstops; coord-shard gap).
- **#2762 / #2801** — pre-review gate leaks orphan daemons / reuses sync toggles as its
  opt-out.

### Recurrence prevention (close the epic, don't just remediate) — CT7
Codify the anti-patterns as doctrine + a mechanizable guard: ban `pytest.xfail` with a
"not blocked/implemented" reason; ban new raw `file.py:NNN` ratchet keys; fixtures delegate
to production seams; assert observable contracts, not wiring. Prior art: the post-merge AST
stale-assertion analyzer (mission 068, `src/specify_cli/post_merge/`).

## Counterweight — do NOT "fix" these (they look like friction, they are contracts)

Straight from the audit's "where the theory does NOT hold":

- **Convergence-invariant assertions** (`read_dir == write_dir` for flattened topology,
  triple-equality collapse) — **correct contracts**, not codified bugs.
- `test_execution_context_parity.py`, `tests/git/test_protection_preserved.py` — gold-standard
  ATDD ratchets *with* anti-vacuity injection proofs. Models to emulate.
- `assert_called*` in `tests/sync/` (non-tracker) and `tests/auth/` — legitimate boundary
  verification paired with observable outcomes.
- `_baselines.yaml` **count**-keyed ratchets — semantically meaningful burn-down accounting;
  churn is inherent, not fixable friction.
- The one honest release-blocker (`test_dogfood_corpus_backfilled`, #2917) is **corpus drift,
  not suite friction** — resolve by re-running the backfill, never by relaxing the predicate
  (ADR 2026-07-17-1).

## First mission slice (recommendation)

**Slice 0 + Slice 1 on the two architectural-ratchet guards** is the right thin, low-risk,
front-loadable start for a remediation mission: it kills the systemic false-red engine
(#2853) for the whole architectural-gate chain, needs no new infra (`composite_key` exists),
and is verifiable by the existing gates re-running green after a deliberate line-shift.
The gate-reliability parallel track (#3260) can start immediately and independently — begin
with #3224 and #2803.
