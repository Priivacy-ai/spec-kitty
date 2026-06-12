# Contracts — Commit Guard + Findings Carrier (01KTRC04)

Behavioural contracts for the parity/negative suites and per-WP DoD. Not API signatures.

## C-GUARD-1 — One entry point, one policy
- **Given** any surface that creates a commit (CLI, coordination, orchestrator-api, acceptance, upgrade, merge)
- **Then** it routes through `safe_commit` (git/commit_helpers), whose protection decision is made SOLELY by
  the SK policy module (`core/commit_guard.evaluate`). `test_safe_commit_import_boundary` (tightened, #1355)
  enforces: no other module imports protection internals or re-implements the decision.

## C-GUARD-2 — No privilege from message content, file content, or ambient env (FR-008 / #1334 / F-1)
- **Given** ANY commit message (including `release: …`, `chore: apply spec-kitty upgrade changes`,
  `…: record done transitions for merged WPs`)
- **When** committed to a protected ref WITHOUT a matching explicit capability
- **Then** the guard refuses. The #1334 live repro (tmp repo, prefix-crafted message) is a permanent
  negative test asserting refusal.
- **Per-channel refusal (the other four):** after IC-02, each deleted channel has a negative test —
  (a) passing the retired `allow_protected_branch_in_test_mode`-style bool has no effect / does not exist,
  (b) `allow_completed_op_on_protected_branch`-style bool likewise, (c) an op-record FILE whose content
  matches the old completed-op exception grants nothing, (d) the env hatches grant nothing (except any
  explicitly documented operator escape hatch, which must be named in the guard's docstring).

## C-GUARD-3a — Single destination authority (IC-02↔IC-04 anti-split-brain)
- `commit_guard.evaluate` ECHOES `CommitTarget.ref` — it never re-derives a destination; `--to-branch`
  resolves INTO the same CommitTarget before evaluation; `resolve_placement_only` shares the resolver's
  internal helpers (one authority, two projections). A grep finds no second destination derivation on any
  commit path post-mission.

## C-GUARD-3 — Legitimacy = resolved placement (FR-003)
- **Given** a planning artifact (spec.md/plan.md/tasks) on a repo whose target branch is protected
- **When** the resolved `ArtifactPlacementFragment`/CommitTarget names ref R as the destination
- **Then** the commit to R succeeds; finalize-tasks reads the SAME resolution (no catch-22, #1784);
  and a refusal message (when refused) names the resolved destination — never "switch to the lane branch"
  before lanes exist (#1777/#1631).

## C-GUARD-4 — Protection preserved (C-003; the ratchet)
- Direct push to origin/main remains blocked under ALL outcomes of this mission.
- A commit to a protected ref that is NOT the resolved placement and carries NO explicit capability is refused.
- No capability can grant direct-push-to-origin/main.
- These three are authored as tests FIRST (IC-01, NFR-005) and stay green through every conversion.

## C-GUARD-5 — Ergonomics (FR-002)
- Directory/bulk arguments expand to contained files validated against `worktree_root`, with an explicit
  expansion report; explicit `--to-branch` is always honored; no "No requested changes" misfire for files
  that genuinely differ from HEAD.

## C-FIND-1 — Verdict from structure only (FR-004 / #1819)
- **Given** an analysis report whose frontmatter (`analysis-findings/v1`) has zero critical/high findings,
  with body prose containing the words "CRITICAL", "HIGH", and "BLOCK"
- **Then** the recorded verdict is `ready` (prose never read).
- **Given** frontmatter with one `critical` finding and body prose saying "no issues, ready for implementation"
- **Then** the verdict is `blocked`.

## C-FIND-2 — Loud failure on drift (WRITE path only)
- Missing schema key, unknown severity value, counts≠tally, or `verdict_hint` disagreeing with the computed
  verdict → structured validation error on the **write/record path** (no silent fallback, no substring
  re-inference).
- The **read/freshness path** (`check_analysis_report_current`, accept/review gates) tolerates pre-v1
  legacy reports: `verdict: unknown` + remediation hint — it must NOT wedge existing missions.

## C-FIND-3 — finalize-tasks / downstream read-side
- **Given** a mission whose analysis-report was recorded pre-v1 (no carrier)
- **Then** downstream consumers (finalize-tasks, implement gates) proceed on freshness as today; the
  `unknown` verdict is advisory, never fabricated into `ready`/`blocked`.

## C-STAT-1 — Fragment is the source (FR-005 / #1821)
- `MissionStatus.load` + `status_transition` consume the carried `StatusSurfaceFragment`; grep/parity
  assertion confirms no local coord-path composition remains.

## C-DRG-1 — Typed provenance, total migration (FR-007 / #1624)
- Post-migration: zero `getattr(node, "provenance", None)` consumers; zero `object.__setattr__` provenance
  writes; `mypy --strict` clean on the DRG path; all 3 consumer layers on `Provenanced[T]`.

## C-DOC-1 — Pure extraction (FR-006 / #1623)
- `doctor.py` health-render extraction is behavior-preserving: identical render output for identical inputs
  (golden/snapshot check or diff-review); imports repointed; no logic edits.
