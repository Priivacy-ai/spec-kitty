# Paula Patterns — Adversarial Scope Review: Missed Identity-Derivation Sites

**Mission:** `naming-identity-routing-rider-01KV7SFD` · **Reviewer:** paula-patterns (architecture-scout) · **Date:** 2026-06-16
**Posture:** adversarial — default "incomplete" until coverage is proven. Verified every claim with `rg`/`ast` against `src/`.

## Method

The planner's inventory (`research.md` Decision 1) keyed Class A on `rg '\b\w*_id\[0?:8\]'`. That idiom has two
structural blind spots I exploited:

1. **Variable-name dependence** — it only matches when the slice operand is a name *ending in* `_id`. Any
   intermediate binding (`mid`, `raw_mid`, `mission_id_meta`) or `str(...)` wrap escapes it.
2. **Domain conflation between two ratchets** — the spec (FR-004) says "extend the literal-ban ratchet to detect
   bare `…_id[:8]`", but the actual ratchet (`test_no_worktree_name_guess.py`) detects **name composes** (idioms
   1/2/3: `.worktrees/` joins, `kitty/mission-` literals, `mid8`-suffix dedup). It contains **no `[:8]` short-id
   detector at all**. So IC-01 must *add a new detector*, and that detector — if it copies the research regex —
   inherits blind spot (1) and will miss the same sites the inventory missed. The grep blind spot and the ratchet
   blind spot are **the same hole**.

## Finding 1 (PRIMARY) — Five in-scope mid8 derivations the `_id[:8]` grep AND the ratchet miss

All five read `meta["mission_id"]` (or a ULID `mission_id` value) and slice `[:8]` to produce a **mission `mid8`** —
canonically `mid8()`/`resolve_mid8`/`IdentityFragment.mid8`. All are in active `src/`. None match `\b\w*_id\[0?:8\]`.
A naive IC-01 detector that ports the research regex catches **zero** of them.

| # | file:line | idiom | why the grep missed it | mission-identity? | IC owner | ratchet (IC-01) catches? |
|---|-----------|-------|------------------------|-------------------|----------|--------------------------|
| M1 | `src/mission_runtime/resolution.py:171` | `return str(raw_mission_id)[:8]` | `str(...)` wrap — operand is a call, not a `*_id` name | YES — `meta["mission_id"]` truncation (`_mid8_from_primary_meta`) | **IC-02** (currently absent) | NO unless detector handles `str(x)[:8]` |
| M2 | `src/specify_cli/cli/commands/mission_type.py:643` | `return mission_id_meta[:8] if len(mission_id_meta) >= 8 else ""` | var name is `mission_id_meta`, not `*_id` (the `_meta` tail defeats `\b\w*_id\[`) | YES — `_read_mission_mid8`, `meta["mission_id"]` | **IC-02** (currently absent) | NO — name not `*_id` |
| M3 | `src/specify_cli/cli/commands/agent/workflow.py:292` | `mid[:8] if isinstance(mid, str) and len(mid) >= 8 else None` | var name `mid` (bound from `meta.get("mission_id")`) | YES — `_load_coord_branch_meta` mid8 fallback | **IC-02** (currently absent) | NO — name not `*_id` |
| M4 | `src/specify_cli/cli/commands/agent/mission.py:772` | `mid8 = raw_mid[:8] if isinstance(raw_mid, str) and len(raw_mid) >= 8 else None` | var name `raw_mid` (bound from `meta.get("mission_id")`); feeds `CoordinationWorkspace.resolve` | YES — coord-worktree mid8 for commit routing | **IC-02** (currently absent) | NO — name not `*_id` |
| M5 | `src/specify_cli/retrospective/generator.py:112` | `if mid == mission_handle or mid[:8] == mission_handle or slug == mission_handle:` | var name `mid` (= `meta.get("mission_id")`); a mid8 **selector comparison** | YES — mid8 prefix match for mission-dir resolution | **IC-02** (currently absent) | NO — name not `*_id` |

**Severity:** M1–M5 are exactly the recurrence shape the mission exists to eliminate (consumer re-derives `mid8`
inline while a canonical answer exists). They are NOT in IC-02's affected-surfaces list (plan.md §IC-02), so the
routing WP will not touch them, **and** the IC-01 tripwire will not flag a *future* one of this shape — the
"can't silently regrow" guarantee (Scenario 2 / SC-001) is false for the `mid`/`raw_mid`/`mission_id_meta`/`str(x)`
variants. M5 additionally needs care: it is a `==` comparison, so routing must preserve the selector semantics
(compare against `resolve_mid8`/`mid8(mission_id)`), not just substitute a producer call.

## Finding 2 (SCOPING ERROR) — IC-03's "~10 inline lanes-path read sites" is inflated ~5×

`research.md` Decision 4 and plan IC-03 claim ~10 inline `feature_dir / "lanes.json"` read sites needing adoption,
and build the entire C-002 "carry-with-adoption / half-strangle" argument on that count. Verified: the **only**
inline lanes-*path* composes in `src/` are:

| file:line | idiom | note |
|-----------|-------|------|
| `src/specify_cli/lanes/persistence.py:43` | `lanes_path = feature_dir / LANES_FILENAME` (write) | inside the seam module itself |
| `src/specify_cli/lanes/persistence.py:78` | `lanes_path = feature_dir / LANES_FILENAME` (read) | inside the seam module itself |

Every other caller in research's list (`context/resolver.py:203`, `workspace/context.py:798`) is a `feature_dir /
'lanes.json'` **inside an f-string error message** — not a path used to open the file — and the remaining named
files (`worktree_allocator.py`, `compute.py`, `recovery.py`, `merge.py`, `core/worktree_topology.py`) go through
`read_lanes_json`/`require_lanes_json`/`write_lanes_json` already. So the "half-strangle `_lanes_feature_dir` twin"
C-002 guards against is largely **hypothetical** at the read sites; the genuine extraction is two lines in the
module that already owns `LANES_FILENAME`. This is not a *missed* derivation — it is an **over-counted** one that
inflates IC-03's risk/effort framing. Recommend re-baselining IC-03's count to "2 in-module composes + the error-
message f-strings" before tasks.

## Finding 3 (DEFERRED CLASS, acknowledge in IC-01 honesty note) — `feature_dir.parent.parent` repo-root shadow

A second identity-derivation class exists that the mission's `mid8`-only lens never names: deriving the **repo /
project root from a `feature_dir`** by `feature_dir.parent.parent`. `status/emit.py:392` literally documents this as
"a concurrency defect of the same class the topology seam exists to kill", and a canonical seam exists
(`workspace.root_resolver.resolve_canonical_root` + `coordination.surface_resolver.classify_worktree_topology`).
Live shadow sites:

| file:line | idiom |
|-----------|-------|
| `src/specify_cli/coordination/status_transition.py:54` | `return feature_dir.parent.parent` |
| `src/specify_cli/cli/commands/agent/workflow.py:793` | `feedback_root = feature_dir.parent.parent` |
| `src/specify_cli/cli/commands/agent/workflow.py:820` | `feedback_root = feature_dir.parent.parent` |
| `src/specify_cli/status/emit.py:417,422,424` | `return feature_dir.parent.parent` (×3, fallback arms) |
| `src/specify_cli/status/work_package_lifecycle.py:82,87,89` | `return feature_dir.parent.parent` (×3) |
| `src/specify_cli/policy/merge_gates.py:200` | `repo_root = feature_dir.parent.parent` |
| `src/specify_cli/dashboard/scanner.py:255` | `project_root = ... else feature_dir.parent.parent` |
| `src/specify_cli/dashboard/scanner.py:571` | `worktree_root = feature_dir.parents[1]` |

**Verdict: OUT OF SCOPE by decision, not by miss.** This is the write-side/topology authority surface deferred to
**#1716 / #1832** (C-005), and `status/` is fence-posted by the NFR-001 diff-scan (only `aggregate.py` may change).
The mission is correct to leave it. **BUT** the IC-01 tripwire honesty note (plan §IC-01 Risks) currently only
admits the `mid[:8]`/helper-indirection limit; it must ALSO state that this `parent.parent` repo-root class is
undetected and deferred to #1716 — otherwise a reader infers SC-001 ("the class cannot silently regrow") covers a
class it does not. Recommend one sentence in the ratchet docstring + the IC-01 risk note.

## Finding 4 (TRUE NEGATIVES — verified, not in scope)

To bound the attack surface honestly, these `[:8]`-family hits are **correctly excluded** (different domain or
already-seam) and need no action:

- `invocation/executor.py:469` `invocation_id[:8]` — Op invocation id, different identity domain (research already flagged as non-target).
- `git/commit_helpers.py:378`, `git/ref_advance.py:51/93`, `ops.py:47`, `invocations_cmd.py:423` `[:12]` — git SHA / op-id truncations, not mid8.
- `mission_runtime/context.py:99/112`, `branch_naming.py:139/192/408` — the **seam internals** (the SSOT; KEEP).
- `lanes/recovery.py:135` (glob), `core/vcs/detection.py:161` (seam-parser round-trip) — already ratchet-allow-listed, benign.
- `core/mission_creation.py:139` `split("-")` and `branch_naming.py:163` `rsplit("-",1)` — the latter is the seam's own slug-tail parse; the former is a slug-normalisation, neither is a #1918-class mid8-from-slug-tail re-derivation. **No live `mid8`-recomputed-from-slug-tail shadow found outside the seam.**

## Idiom-classes the IC-01 ratchet (as specced) would still fail to detect

1. **`str(x)[:8]`** — operand is a `Call`, not a `Name` (M1). A regex/`ast` short-id detector keyed on `Name[:8]` misses it.
2. **`<anyname>[:8]` where the name is bound from `meta["mission_id"]`** (M2–M5) — requires either (a) widening the detector to *all* `[:8]` slices with an allow-list for the non-mid8 ones (`[:12]` SHAs, `invocation_id`, hashes — noisy), or (b) `ast` def-use binding to trace the operand back to `mission_id`. The research's "syntax-level, defeated by `mid[:8]`" honesty note **understates** this: it is not a future hypothetical, there are **5 live sites today**.
3. **`feature_dir.parent.parent` repo-root derivation** (Finding 3) — a different seam entirely; the `mid8` ratchet has no detector for it (correctly deferred, but must be named in the honesty note).

## Recommendation to the planner

- **Add M1–M5 to IC-02's affected-surfaces and FR-001 routing scope** (or, if M2–M4 are judged genuinely
  context-free meta-dict reads, route them to `resolve_mid8`/`mid8()` exactly like the other 10). They are the
  same defect class FR-001 targets.
- **IC-01 detector must catch the intermediate-var/`str()` shape**, or the SC-001 / Scenario-2 guarantee is
  unmet. Cheapest robust form: flag every `…[:8]` slice in `src/` whose operand resolves (by `ast` binding or by
  literal name) to a `mission_id`, with the `[:12]`/`invocation_id`/hash sites on a justified allow-list.
- **Re-baseline IC-03's count** (Finding 2) to 2 in-module composes; the half-strangle risk is near-zero.
- **Extend the IC-01 honesty note** to name the deferred `parent.parent` repo-root class (Finding 3).
