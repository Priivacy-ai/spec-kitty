# Closeout adversarial review — Architect Alphonso

Mission: `gate-read-surface-completion-01KVW9B0` (draft PR #2113)
Lens: architectural soundness + consolidation integrity. Read-only.
Range reviewed: `git diff ea7dc75c5..HEAD` on `feat/gate-read-surface-completion`.

Directives applied (architect-alphonso): 001 Architectural Integrity, 003 Decision
Documentation, 031 Context-Aware Design, 032 Conceptual Alignment, 041 Tests as Scaffold.

---

## VERDICT (one line)

**APPROVE for merge.** The consolidation is architecturally sound: ONE canonical
authority (the kind partition in `mission_runtime.artifacts`) drives BOTH read and
write surface routing, the write-partition fix is correct, and the FR-010 ratchet is
non-vacuous. Two recommendations (one ADR, one ratchet-scope follow-up), neither a
blocker.

---

## 1. Single-authority verdict — ONE seam or TWO?

**There are two call shapes but ONE canonical authority. This is acceptable, not a
split-brain.**

- The kind-aware seam is `resolve_planning_read_dir(repo_root, slug, kind=...)`
  (`src/specify_cli/missions/_read_path_resolver.py:1244`). Its routing decision is
  delegated to the SINGLE partition predicate `is_primary_artifact_kind`
  (`mission_runtime/artifacts.py:220`) over `_PRIMARY_ARTIFACT_KINDS`
  (`artifacts.py:85`). That partition is the canonical authority — both read and
  write consult it (`artifact_home_for`, `artifacts.py:171`).
- `_planning_read_dir` is a *thin per-module wrapper* over that seam — it exists in
  THREE copies (`mission.py:1136`, `acceptance/__init__.py:772`, and the inline
  callers in `tasks.py`). The wrappers differ only in their kind-naming surface:
  `mission.py` names by `artifact_type` string via `_kind_for_artifact` (no silent
  default — `mission.py:1147`); `tasks.py`/`acceptance` pass the `MissionArtifactKind`
  enum directly (`tasks.py:1073`, `1136`; `acceptance:809`).
- **This is NOT two seams.** Every wrapper bottoms out in the same
  `resolve_planning_read_dir` → same partition. The prompt's worry — "WP01 chokepoint
  `_planning_read_dir` AND direct `resolve_planning_read_dir` in tasks.py" — is a
  surface-naming difference, not a routing-logic fork. There is no parallel
  classification anywhere (verified: only `is_primary_artifact_kind` decides).

**Design-integrity note (001):** the `_planning_read_dir` wrapper is duplicated as a
private helper in `mission.py` and `acceptance/__init__.py` with byte-similar
docstrings that even cite each other ("mirroring `mission.py::_planning_read_dir`",
`acceptance:783`). That is acknowledged duplication of a trivial 2-line adapter, not
duplicated *logic*. **Recommendation (non-blocking):** the ratchet pins the seam, so
this is cosmetic; a future pass could promote one shared `_planning_read_dir(repo,
slug, kind)` adapter, but forcing a single chokepoint NOW would add an import edge
(`acceptance` → `mission.py`) for no behavioral gain. Leave as-is.

**Conclusion:** single canonical authority is genuinely present. The two call shapes
are an acceptable thin-adapter convenience, not an inconsistency.

## 2. Write-partition correctness (core/paths.py + core/git_ops.py)

**Correct.** Both `get_feature_target_branch` (`core/paths.py:621`) and
`resolve_target_branch` (`core/git_ops.py:374`) re-point the `meta.json` read from
`candidate_feature_dir_for_mission` → `primary_feature_dir_for_mission`. This is
correct because:

- `meta.json` is **PRIMARY_METADATA** kind — it ONLY ever lives on the primary
  checkout (`artifact_home_for` hard-codes `read_surface="primary"`, `artifacts.py:156`).
  The candidate resolver, under coord topology, returns the `-coord` worktree which has
  NO `meta.json`, so the old code silently fell back to `resolve_primary_branch` =
  protected `main`. That was the implement-loop "refusal-to-main" defect.
- The fix mirrors the already-proven `resolve_merge_target_branch` (`core/paths.py`),
  so it is consistency-restoring, not a new pattern.

**C-002 over-reach check (the explicit ask): NO over-reach found.** The partition is
right: planning + identity → primary; STATUS → coord. Crucially, the write fix is
scoped ONLY to the `target_branch` (meta.json) read, NOT to commit *destinations*:

- ANALYSIS_REPORT still commits to COORD via `commit_for_mission(...,
  kind=MissionArtifactKind.ANALYSIS_REPORT)` (`mission.py:2080`) — the status/coord
  write path is untouched (G-6 "status commit destinations UNCHANGED").
- The record-analysis dirty-tree preflight still drops coord residue ONLY under
  `routes_through_coordination(resolve_topology(...))` (`mission.py:924-928`), keyed on
  STORED topology, not a fabricated ref.
- I found **no case** where a write that *should* stay coord was redirected to primary.
  The only writes touched are the `meta.json`-derived *branch resolution*, which is
  unambiguously a primary-surface read. **No C-002 status-leniency regression.**

One subtlety worth recording (not a defect): in `record_analysis` the report is
*written* to the primary dir (`write_feature_dir = resolve_planning_read_dir(...,
kind=spec)`, `mission.py:2047`) but *committed* as a COORD kind (`mission.py:2080`).
This is intentional — the report file co-locates with `spec.md` on disk for the
writer's existence check, while its commit routes to coord under coord topology. The
inline comment (`mission.py:2042-2044`) documents this. Correct, but it is the single
least-obvious seam in the diff and reinforces the ADR recommendation below.

## 3. Ratchet (FR-010) sufficiency

**Sufficient for the enumerated class; non-vacuous; correctly fenced. One real
scope-boundary caveat.**

Strengths (041-compliant — it asserts a *contract*, not file:line):
- AST-based, so docstrings/comments that merely mention an idiom never trip it
  (verified: `_READ_CLEAN_VIA_SEAM` self-test, `test_gate_read_literal_ban.py:476`).
- Mandatory runnable synthetic-AST self-test for BOTH arms (flag-violation +
  pass-clean), so a future edit that neuters a scanner goes RED
  (`test_..._self_test_*`, lines 488-545). This is the right anti-rot design — not a
  recorded mutation log.
- The pin test (`test_enumerated_surface_set_is_pinned_and_live:423`) turns a
  rename/move/delete of any scanned surface into a hard failure, defeating the
  "silently-empty-scan → vacuous-green" failure mode.
- All 8 tests pass on HEAD (ran locally, 24.9s).

**Caveat (the prompt's exact question — could a NEW gate command bypass it tomorrow?):
YES, partially.** The scan set `_READ_ARM_SURFACES` / `_WRITE_ARM_SURFACES`
(`lines 126-172`) is **manually enumerated**, not auto-derived from
`@app.command`. The test's own docstring admits this (`lines 416-420`): "We do not
auto-derive the full scan set from @app.command — not every command reads a planning
artifact." So a NEW gate command added to `cli/commands/agent/` that joins
`feature_dir / "spec.md"` off a topology-routed dir would **NOT be caught** unless the
author also adds it to `_READ_ARM_SURFACES`. The pin test only guarantees the *existing*
pinned surfaces stay live; it does not guarantee *completeness* of the set.

This is a real residual gate-coverage gap, but it is a *known, documented* trade-off,
not a defect — fencing the whole of `cli/commands/agent/` would false-positive on the
many legitimate topology-aware STATUS joins. **Recommendation (non-blocking
follow-up):** add a "discovery" assertion that walks every `@app.command` entry
function in the two gate modules, and FAILS if one joins a `_PLANNING_ARTIFACT_LITERALS`
basename off ANY name not bound from the sanctioned seam — i.e. invert to allowlist
(default-deny) rather than the current pinned denylist. That would close the
"new-command-tomorrow" hole without false-positives (a STATUS join is on
`status.events.jsonl`, not a planning literal, so it would not trip). File as a
burn-down ticket against the seam epic.

The "silent-empty-scan" risk specifically asked about IS already covered by the pin
test for the enumerated set — the gap is *un-enumerated* new surfaces, above.

## 4. Design debt / boundary integrity

- **Allowlist vs residue disjointness (verified empirically):** `_SELF_BOOKKEEPING_*`
  (`{meta.json}` + provenance suffix) and `_COORD_RESIDUE_FILENAMES` are provably
  disjoint (`overlap == set()`; `meta.json` not in residue map). The G-5 invariant
  holds: a stale primary `spec.md` is in the residue *path-classifier* but maps to a
  PRIMARY kind, so `kind_is_coordination_residue` returns False (real dirt) — correct.
  Partition is clean.
- **mission_runtime vs specify_cli boundary (031):** respected. Consumers query the
  partition ONLY via the package-root public predicate `is_primary_artifact_kind`,
  never the private `_PRIMARY_ARTIFACT_KINDS` symbol (late imports at
  `_read_path_resolver.py:1302`, `acceptance:788`). Guard
  `test_mission_runtime_surface.py` updated (+4 lines). No layering violation.
- **No half-migrated abstraction found.** The kind partition is the single locus; the
  `_COORD_RESIDUE_FILENAMES` path→kind map is a separate, legitimate classifier (it
  answers "what kind is this path", the partition answers "where does that kind
  live"). The two are correctly composed, not redundant.
- Minor: the triple `_planning_read_dir` adapter duplication (see §1) is the only
  cosmetic debt.

## 5. ADR recommendation (003)

**YES — record the write-surface partition as an ADR.** The read-side partition is
implicitly covered by the execution-state-canonical-surface ADR
(`2026-06-07-1`) and coord-empty-fallback ADR (`2026-06-19-1`), but the **write twin**
— "the mission `target_branch` is read from `meta.json` on the PRIMARY surface for ALL
topologies, never the topology candidate (which falls back to protected main)" — is a
distinct, load-bearing architectural decision that currently lives only in code
comments + the in-mission contract (`contracts/gate-read-seam.md` G-6). It is exactly
the class of decision Directive 003 requires documented with context/options/rationale,
because it governs a protected-branch-safety invariant and a future author touching any
`*_target_branch` resolver needs the rationale to avoid reintroducing the candidate
anchor. **Recommend a short ADR**: "Write-branch resolution anchors meta.json on the
PRIMARY surface (write-surface twin of the read partition)", citing G-6, the
refusal-to-main defect, and the FR-010 write-arm ratchet as the enforcement.

---

## Pre-merge checklist for the closeout owner

1. (Optional, recommended) Author the write-surface-twin ADR per §5.
2. (Follow-up ticket, non-blocking) Default-deny discovery assertion per §3 caveat to
   close the un-enumerated-new-command gap.
3. (Cosmetic, defer) Consider de-duplicating the `_planning_read_dir` adapter per §1.

No blocking findings. Architecture is coherent and the ratchet protects it.
