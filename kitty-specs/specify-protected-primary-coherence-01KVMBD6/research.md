# Phase 0 Research: Specify on Protected Primary + Branch-Protection Config

Consolidated decisions. The carrier decision has a full record in
[research/protected-branch-carrier-decision.md](research/protected-branch-carrier-decision.md)
(5-agent design squad); summarized here with the two other resolved unknowns.

## D1 — Protection carrier shape (DECIDED — squad + ADR 2026-06-21-1)

- **Decision**: a standalone, frozen `ProtectionPolicy` value object
  (`protected_branches: frozenset[str]`, `operator_hatch_active: bool`, `is_protected(ref) -> bool`)
  with one `resolve(repo_root)` boundary resolver, passed explicitly, feeding the existing
  `core/commit_guard.evaluate(ProtectionState)` decision seam.
- **Rationale**: no protection callsite holds a built `ExecutionContext` — least of all the standalone
  `safe-commit` deadlock process (its only factory `resolve_action_context` fails closed without a
  mission). A context-nested carrier cannot reach the callsite the mission exists to fix. The decision
  seam already exists; only the input is scattered.
- **Alternatives considered**: nest on `ExecutionContext` (can't reach the deadlock site); nest on
  `WorkspaceContext` (per-WP JSON-persisted → owner-config snapshot leak); no new object / config-aware
  `protected_branches()` (read stays at the callsite → fails FR-007/FR-010). All rejected; see ADR.

## D2 — On-demand materialization at the spec commit boundary (pillar A)

- **Decision**: reuse the canonical `coordination/workspace.CoordinationWorkspace.resolve()` (the same
  on-demand materializer that `_planning_commit_worktree` already invokes for plan/tasks) at a **new
  mission-aware spec-commit entrypoint** (`spec_commit_cmd.py` → the extracted `coordination/commit_router.py`
  helper; the generic `safe_commit_cmd.py` stays mission-blind and unchanged — operator/post-tasks decision):
  when the resolved policy says the destination is protected, materialize the coordination worktree and route
  the commit there (materialize-then-retry); make the refusal error actionable.
- **Rationale**: debugger investigation confirmed the materializer exists and works; the bug is pure
  path-coverage (no call on the specify path). Reusing it honors canonical-sources discipline (C-001)
  and avoids a parallel materialization path.
- **Alternatives considered**: (a) eager materialization at `mission create` — larger blast radius,
  materializes worktrees for missions that never need them; (b) make the guard error merely *say* the
  command — leaves the operator to run it manually (off-runbook). Rejected in favor of materialize-then-
  retry at the commit boundary; the actionable-error wording is a secondary safety net (FR-003).
- **#1718 preservation**: materialization is triggered at the **commit** boundary, not at read time, so
  the create→first-write window still resolves reads to the primary (NFR-001).

## D3 — `.kittify` protected-branch configuration schema (pillar B)

- **Decision**: an additive key under `.kittify/config.yaml` declaring the protected-branch set; absent
  key → default `{main, master}` (+ remote-default augmentation, preserved). Read via the existing
  config-loader pattern (`core/agent_config.py` `load_config`), surfaced only through `ProtectionPolicy.resolve`.
- **Rationale**: matches the repo's established config idiom; additive + backward compatible (C-004);
  keeps owner intent declarative (no GitHub-protection-API network dependency — out of scope per spec).
- **Schema** (see `contracts/protection-config.md`): a top-level `protection:` block with
  `protected_branches: [..]`. Empty list = nothing protected (US2 edge case — NOT a silent fallback to
  default). Unknown branch names are simply unmatched.
- **Alternatives considered**: a flat top-level `protected_branches:` key (less namespaced, risks
  collision with future repo settings); reuse `commit_guard`/`repo_defaults` sections (overloads an
  existing block). Chose a dedicated `protection:` block with headroom for future protection settings.

## D4 — Single-authority guard (FR-010 / #1868)

- **Decision**: a `tests/architectural/` guard restricting `protected_branches(repo_root)` /
  hardcoded `{main, master}` protection decisions to the resolver + demoted-delegate allowlist.
- **Rationale**: `coordination/policy.py` already self-describes as "the single chokepoint" while
  re-reading — a live #1868 instance. The guard makes the single-authority property enforceable, the
  same load-bearing-guard pattern used by the untrusted-path audit.
- **Alternatives considered**: rely on review discipline (insufficient — the drift already happened).

## Out of scope (confirmed)

- #2040 read/write surface-authority desync (distinct seam — C-005).
- Real GitHub branch-protection API detection (replaced by owner config).
- Consolidating the four scattered `.kittify/config.yaml` loaders (deferred strangler — Paula).
- Attaching `ProtectionPolicy` as an `ExecutionContext` fragment (optional future coherence; non-critical).
