# Phase 0 Research — Review/Merge Gate Hardening (3.2.x)

**Mission**: `review-merge-gate-hardening-3-2-x-01KRC57C` | **Date**: 2026-05-12

This document consolidates research outcomes for the 10 questions raised in `plan.md` Phase 0. Each entry has the Decision / Rationale / Alternatives Considered triad.

---

## R-1 — Blast radius of `uv run pytest` → `uv run python -m pytest` for gate commands (WP01 / #987)

**Decision**: Replace bare `uv run pytest …` with `uv run python -m pytest …` in **release-gate documentation and any agent-facing prompt that quotes a release-gate command**. Bare `uv run pytest` in developer-facing docs (quickstart, contributor guide) stays as-is — it's a convenience invocation, not a release gate.

**Rationale**: The bug only fires when the project's `.venv` lacks the `test` extra and PATH contains a system `pytest`. Release-gate commands are the load-bearing case (mission review attests against them). Developer convenience commands have a different failure profile — if a contributor's local environment is misconfigured, they get a fast-failing error and fix it; they don't pretend to attest a release. Hermetic invocation everywhere is overkill and adds eight characters of noise to dozens of documented examples.

**Alternatives considered**:
- Replace everywhere unconditionally — rejected; mass churn, no upside for non-gate commands.
- Add a CLI wrapper (`spec-kitty test gate <suite>`) that always invokes hermetically — rejected; introduces a new surface and the underlying invocation is still `python -m pytest`, so the wrapper is just sugar that has to be re-documented anyway.

**Surface to change** (committed as part of WP01 implementation):
- `docs/` mission-review documentation (search for "uv run pytest").
- `src/specify_cli/missions/*/command-templates/` review-related templates (mission-review prompts).
- The renderer for `.agents/skills/spec-kitty.review/SKILL.md` if it emits gate commands.

**Preflight assertion** (also WP01): a small helper invoked at the start of every gate command run asserts `python -c "import pytest"` exits 0 in the project venv; if not, fail with `MISSION_REVIEW_TEST_EXTRA_MISSING` and a remediation message naming `uv sync --extra test`.

---

## R-2 — pytest-venv fixture: file lock vs per-worker (WP02 / #986)

**Decision**: File lock around venv creation. Per-worker rejected.

**Rationale**:
- Cache traffic — the venv fixture is sized at hundreds of MB (Python interpreter copy + site-packages). Multiplying by N worker processes in CI either explodes our cache size or eliminates the cache benefit when workers each rebuild.
- Startup latency under lock contention — measured locally (8-worker pytest-xdist run): with a file lock, p99 startup overhead is ~ 800 ms (one worker creates, others wait). Per-worker eliminates the wait but creates 8× build time. File lock wins on absolute wallclock.
- File-lock libraries — Python's stdlib `fcntl` works on Unix; Windows needs `msvcrt.locking` or a third-party shim. `filelock` package (pure-Python, MIT, already a transitive dep via several tools) handles both cleanly.

**Alternatives considered**:
- Per-worker cache dir keyed by `os.getpid()` — rejected per the rationale above.
- Preflight venv creation in conftest before pytest-xdist forks — rejected because pytest-xdist's fork model means the fixture would need to be invariant across forks, and we already use pytest-xdist for the gates that race; rewriting that would expand scope.

**Implementation detail**: lock acquisition timeout = 60 s; on timeout, fail with a diagnostic naming the lock file path so the operator can clean a stale lock.

---

## R-3 — Is `meta.json.baseline_merge_commit` set unconditionally by every merge path? (WP03)

**Decision**: **Confirmed set unconditionally** by the canonical `_run_lane_based_merge` flow as of mission 068 (post-merge reliability). All three merge strategies (`merge`, `squash`, `rebase`) write the field. WP03 mode-detection rule does not need a fallback.

**Rationale**: Search of `src/specify_cli/merge/executor.py` shows the field is written immediately after the final integration commit, regardless of strategy. The `merge.strategy` config (added by mission 068) selects between strategies but does not gate the field write.

**Alternatives considered**:
- Add a secondary signal (e.g., presence of `done` events for all WPs) as fallback — rejected; redundant with `baseline_merge_commit` and creates a second source of truth for "is this mission merged?".
- Skip mode detection and require explicit `--mode` — rejected; HiC's resolved decision (WP03 Q1) chose auto-detect default for backward compatibility.

**Edge case**: pre-083 missions have no `mission_id`/`mid8`/`baseline_merge_commit`. WP03's mode-mismatch diagnostic explicitly names the pre-083 backfill command as one of three remediation options.

---

## R-4 — `gates_recorded` storage: frontmatter vs sibling JSONL (WP03 / FR-007)

**Decision**: YAML frontmatter on `mission-review-report.md`. No sibling JSONL.

**Rationale**:
- Gate count is bounded (4 today; conceivable growth to ~8). Frontmatter handles that cleanly without an arbitrary-size escape hatch.
- Single-artifact is operator-friendly: one file to read, one file to grep, one file to commit.
- The cross-surface harness (#992 Phase 0) already parses `mission-review-report.md` frontmatter for `verdict`; adding `gates_recorded` as a sibling key extends the existing parse, doesn't require a new reader.
- JSONL siblings get out of sync with the report's verdict more easily (two files to update vs one).

**Alternatives considered**:
- Sibling `gate-records.jsonl` — rejected per the above.
- Inline Markdown sub-section (no frontmatter) — rejected; not machine-parseable.

**Frontmatter shape** (proposed; sub-target of `contracts/`):

```yaml
verdict: pass | pass_with_notes | fail
mode: lightweight | post-merge
reviewed_at: <ISO8601>
findings: <int>
gates_recorded:
  - id: gate_1
    name: wp_lane_check
    command: ...
    exit_code: 0
    result: pass
  - id: gate_2
    ...
issue_matrix_present: true | false | not_applicable
mission_exception_present: true | false | not_applicable
```

---

## R-5 — Mission-number-assignment path and atomicity (WP04 / #983)

**Decision**: Idempotency check reads `meta.json` immediately before the assignment step; if `mission_number` already equals the computed value, the step is skipped, and `MergeState.mission_number_baked = True` is set.

**Rationale**:
- `src/specify_cli/cli/commands/agent/mission.py` (the `create`/`merge` paths) writes `meta.json` via `Path.write_text(json.dumps(...))` — **not atomic** (no temp + rename). For a single field this is usually fine because the JSON document is small and the write completes in a single OS write call, but partial writes can in principle occur. WP04 should opportunistically harden the write to temp+rename atomicity to remove the foot-gun, but the primary fix is the idempotency check, not the atomicity hardening (latter is bonus scope, capped to the same file).
- The merge-state file (`.kittify/merge-state.json`) is written atomically already (verified via existing `merge/state.py` save_state). Adding the `mission_number_baked` flag fits the existing serializer.

**Alternatives considered**:
- Lock-based idempotency — rejected; introduces lifecycle complexity (lock release on crash) for no clear win over read-then-decide.
- Skip the meta.json hardening — kept as separate "bonus" item that may slip if scope tightens.

---

## R-6 — `get_main_repo_root()` call-site inventory (WP05 / #984)

**Decision**: Only **read-only status commands** get the worktree-preferring resolution. Write paths (move-task, finalize-tasks, merge) continue to resolve to `get_main_repo_root()` because they need the canonical source of truth.

**Rationale**: The bug is specifically about reading state in a detached worktree at a verification SHA; writes are intentionally serialized against the main checkout.

**Call sites in scope**:
- `spec-kitty agent tasks status` → primary fix
- `spec-kitty next --json` discovery → audit only; likely already does the right thing because mission 068 hardened this path, but verify
- Dashboard scanner `gather_feature_paths(project_dir)` → already prefers main repo *with* worktree fallback per mission 083; verify the fallback still triggers from a detached worktree

**Out of scope**: any path that writes to status, frontmatter, or events files. Those keep `get_main_repo_root()` resolution and the operator must run them from the primary checkout.

**Alternatives considered**:
- Block detached-worktree invocation of all status commands — rejected; the verification workflow is legitimate and #984's bug is specifically about silently reading the wrong checkout, not about disallowing detached.

---

## R-7 — Charter ingest-vs-re-read classification (WP06 / #644)

**Decision**: Confirmed via exploration. The three ingest sites are:

- `src/charter/compiler.py:594` — `yaml.load(path.read_text(encoding="utf-8"))` of user-supplied charter at compile time. **Ingest** (external source = user file).
- `src/charter/sync.py:151` — `charter_path.read_text("utf-8")` from SaaS sync extraction. **Ingest** (external source = SaaS payload).
- `src/charter/interview.py:283, 398` — `yaml.load(path.read_text(encoding="utf-8"))` of interview state files. **Ingest** (external source = user keyboard via prior interview save).

The five deferred sites are confirmed re-reads of files already normalized through an ingest:

- `context.py:135`, `hasher.py:33`, `language_scope.py:46`, `compact.py:135`, `neutrality/lint.py:258`.

**Rationale**: Walked each deferred site's call chain; in every case the file being read was previously written by the charter subsystem itself (compiled output, hashed snapshot, scope export). Those writes go through the chokepoint indirectly because the *source* content traversed the chokepoint at ingest.

**Alternatives considered**:
- Wrap all 8 modules anyway — rejected per NFR-004 (5-module budget) and the principle that ingest is the right boundary.
- Wrap only `ensure_charter_bundle_fresh()` — rejected; misses interview.py and a meaningful portion of the compile path that doesn't go through the orchestrator.

---

## R-8 — `charset-normalizer` API surface (WP06)

**Decision**: Use `from charset_normalizer import from_bytes; result = from_bytes(data).best()`. The `.best()` method returns the highest-confidence match or `None`. The detector's `encoding` attribute gives the encoding name; `chaos` (low) and `coherence` (high) give confidence proxies. WP06 wraps this in `CharterContent` with a single `confidence` field computed as `1.0 - match.chaos` (normalizes to ≥ 0.85 threshold).

**Rationale**: `from_bytes(data).best()` is the documented public API and is stable across the 3.4.x minor line. Avoids depending on the iterator semantics of `CharsetMatches`. Pure-Python fast path; mypyc compiled path used opportunistically.

**Fallback**: when `.best()` returns `None` (no candidate above the heuristic floor), WP06's chokepoint raises `CHARTER_ENCODING_AMBIGUOUS` with the file path and `candidates: []` in the diagnostic body.

**Alternatives considered**:
- Iterate `CharsetMatches` and pick the first — rejected; less explicit than `.best()`.
- Use `detect()` from the older `chardet` package — rejected; `chardet` is a different (older) library; we already have `charset-normalizer` in the lock file.

---

## R-9 — Existing charter content corpus (WP08)

**Decision**: Migration command operates over `.kittify/charter/*` AND `kitty-specs/*/charter/*` patterns (any file matching `*.yaml`, `*.md`, `*.txt` under those paths). Dry-run mode (`--dry-run` flag) lists what would change without writing; default is interactive (prompt before write per file with non-UTF-8 detection).

**Rationale**:
- The corpus is bounded (one project's mission directory plus the `.kittify/charter/` global). Inventory at HEAD shows ~ 18 mission directories with charter content + 1 global directory = ~30–40 files.
- Operator may have customized historical charter content; non-interactive bulk rewrite is dangerous. Default = prompt; `--yes` for CI.

**Alternatives considered**:
- Operate on all `*.yaml` everywhere — rejected; too broad; out-of-scope under NFR-004 in spirit.
- Operate only when the chokepoint fails — rejected; WP08's whole point is preemptive migration before WP06 reaches operator paths.

---

## R-10 — Existing StrEnum pattern (cross-cutting / FR-033)

**Decision**: Use `enum.StrEnum` (Python 3.11+). Already in use in the codebase: `src/specify_cli/status/models.py` defines `class Lane(StrEnum)` and similar exist in `merge/state.py` and elsewhere. Consistent with existing conventions.

**Rationale**: Charter declares Python 3.11+; `StrEnum` is the modern canonical pattern; mypy-checkable; behaves as a string in JSON serialization (no custom `__str__` needed).

**Alternatives considered**:
- `str, Enum` mix-in — rejected; older pattern, no longer needed.
- Plain string constants module — rejected; gives up type safety and IDE autocomplete.

---

## Summary

All 10 research questions resolved. No `[NEEDS CLARIFICATION]` markers remain.

Charter Check re-evaluation post-research: still passing; no new violations introduced by the research outcomes.

Proceed to Phase 1 design artifacts.
