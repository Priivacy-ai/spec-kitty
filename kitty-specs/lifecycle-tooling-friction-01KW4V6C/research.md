# Phase 0 Research — Mission-Lifecycle Tooling Friction

Source: pre-planning adversarial squad (planner-priti, architect-alphonso, debugger-debbie,
paula-patterns), profile-loaded, **live-repro'd** against `upstream/main c44a4fa82`. Convergent
unless noted. This IS the brownfield/code-state check for this mission.

## Scope reshape (the squad's headline catches)

- **#2219 — ALREADY FIXED upstream → verify-and-close.** Both asks shipped after our
  retrospective: `--mission <slug>` scope (`migrate_cmd.py:315-322` → `backfill_topology.py:228-240`)
  and the pure non-persisting `read_topology()` (`backfill_topology.py:68-106`, #1814). Also
  idempotent-skip (`:182-189`) — never overwrites a set topology, so the witnessed 203-file churn
  only hit legacy missions lacking the field. Residual = a regression test + close. Landed via
  `0e270b10a`/`5b8e317aa`. (debbie confirmed live: `migrate backfill-topology --help` shows `--mission`.)
- **#2220 + #2221 — ONE defect, FOLDED (paula's only accepted consolidation).** The WP-frontmatter
  contract is independently encoded in three drifting places: doctrine prose (`tasks/guidelines.md:9`
  "absolute"), the template (`task-prompt-template.md:1-18`, omits `owned_files`/`authoritative_surface`/
  `execution_mode`/`create_intent`), and the validator (`ownership/validation.py:77` `_CODE_PREFIXES`,
  repo-relative). SSOT ratchet = **one golden round-trip test** (template-authored WP validates +
  finalizes first time). Campsite: the template under-lists `owned_files` too (#2221 +1).
- **#2223 — RE-SCOPED.** debbie: the "row for every `#NNNN`" rule does NOT exist in
  `validate_issue_matrix` (`review/_issue_matrix.py` enforces one-table/closed-verdict/
  deferred-needs-handle/mandatory-columns only); the completeness check lives in the approve-gate
  spec-scan. Errors are already structured (`:226`, `:342`). Net-new = wire the existing rule-engine
  as a finalize-tasks **advisory lint** (one engine, two callers); do NOT relax a non-existent rule.
- **#2218 — the one hidden-depth item.** `core/mission_creation.py:416` unconditionally mints the
  coord branch → `:431` classifies COORD. The `classify_topology` SSOT is healthy; the defect is the
  unconditional mint. A `--topology` flag threads cleanly, BUT a create-time non-coord mission is a
  third shape the coord-or-legacy fallbacks across `implement.py`/merge must handle → needs an
  end-to-end proof. **Causally amplifies #2222** (more non-coord missions → more lock friction).

## Per-issue live verdicts (debbie, on c44a4fa82)

| Issue | Verdict | Red-first surface |
|-------|---------|-------------------|
| #2217 | REPRODUCES (no `traces/` glob in `retrospective/generator.py`) | `spec-kitty retrospect create` |
| #2218 | REPRODUCES (specify --help has no `--topology`; scaffold wrote `topology:coord` + coord branch) | `spec-kitty specify --json` |
| #2219 | **ALREADY-FIXED** (drop to verify-close) | n/a |
| #2220 | REPRODUCES (doctrine "absolute" ⇄ validator repo-relative; both guidelines.md copies) | `validate_glob_matches`/`validate_execution_mode_consistency` |
| #2221 | REPRODUCES (template frontmatter lacks the 4 keys) | software-dev `task-prompt-template.md` frontmatter |
| #2222 | REPRODUCES (only `auto_commit=False`; `implement.py` lock self-write at ~:843 → next claim Exit(1) at ~:374) | `spec-kitty agent action implement` |
| #2223 | REPRODUCES (strict + approve-time-only; "every-#ref" rule does not exist) | `validate_issue_matrix(path)` |

## Seam findings (alphonso) + the two operator decisions

- **#2218 flag vocabulary (operator-decided)**: `--topology` accepts the 4 canonical `MissionTopology`
  enum values `single_branch | lanes | coord | lanes_with_coord` — NOT "flat". Conditional coord-branch
  mint; default coord (backward-compat). Create-time `lanes` sets the field; `lanes.json` materializes at finalize.
- **#2222 fix (operator-decided)**: STOP-GATING — exclude the vcs-lock self-write from the dirty-tree
  guard (the lock is one-time VCS-type state, never the concurrency mutex; no race introduced). NOT auto-commit.
- **#2220 authority (alphonso)**: code is canonical (the whole ownership subsystem is repo-relative);
  fix the doctrine TEXT, not the validator.
- **#2217 seam**: `generator.py` already ingests free-text artifacts via `_build_ingestor_findings`
  (workflow-failures-log/analysis-report/mission-review) — slot a tracer reader into that exact seam; don't fork.
- **#2223 seam**: extract the rule-engine to one validator + two callers (approve-gate + finalize lint).

## Coupling / sequencing (alphonso + priti)

- **Topology authority** (#2218/#2219): shared domain, distinct CLI seams; SSOT healthy → keep separate.
- **#2218 ↔ #2222 causal**: fixing #2218 mints more non-coord missions → exposes #2222. **Land Lane C
  (#2222) with/before Lane B (#2218)** (C-005), or include the C fix in B's flat-mission proof.
- **#2220 + #2221** strong coupling (same doctrine doc-set + validator) → one lane.
- **#2217 + #2223** parallel-safe (different files; same "reuse existing seam" pattern, different surfaces).

## Don't-rebuild flags
- #2219 (`read_topology` + `--mission` exist) · #2223 (`validate_issue_matrix` already structured — reuse) · #2217 (ingestor seam exists — extend).

## Open questions for `/spec-kitty.tasks`
1. IC-02: exact decomposition of the `single_branch` end-to-end proof (which implement/merge fallback sites need the third-shape handling).
2. IC-05: where the completeness scan (currently approve-gate) is best factored so both callers share it without a cycle.
