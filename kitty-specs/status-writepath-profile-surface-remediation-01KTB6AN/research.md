# Research — MissionStatus Write-Path Completion & Profile-Load Surface Remediation

> ⚠️ **CORRECTED after dialectic review (`dialectic-review.md`, 2026-06-05).** This research was originally built on the `01KT6HVH` **mission-review-report** (RISK-001/RISK-006), which was **stale**: PR #1682 (`cdc258002`) landed afterward and already (a) added `transition()`/`save()` unit tests at `tests/unit/status/test_mission_status_aggregate.py:410-537` and (b) made `_read_meta` fail-closed. Part-1 claims of "UNTESTED" and "silently returns (None,False)" below are **superseded** — see the strike-through corrections inline and the revised `spec.md`. The profile-load (Part 2) findings stand, with the FR-016 contract corrected (see `spec.md` FR-016 / `data-model.md`).

Pre-spec investigation captured for the mission so `plan` builds on verified evidence rather than re-discovering it. All file:line citations verified on `feature/status-writepath-profile-surface-remediation` (base = `main` @ `7f0bb31d9`) on 2026-06-05.

---

## Part 1 — #1667 residual: `MissionStatus` already shipped; only the write path is incomplete

### 1.1 What already exists (shipped by `execution-state-domain-remediation-01KT6HVH`, WP04)

| Surface | Location | State |
|---------|----------|-------|
| `MissionStatus` aggregate | `src/specify_cli/status/aggregate.py:119` | Shipped, exported from `status/__init__.py` |
| `ActiveWPStatus` projection | `src/specify_cli/status/aggregate.py:98` | Shipped |
| `MissionStatus.load(repo_root, mission_slug)` | `aggregate.py:145` | Shipped + **tested** (FR-017 ADEQUATE) |
| `MissionStatus.claim(wp_id)` | `aggregate.py:292` | Shipped + **tested** (FR-018 ADEQUATE) |
| `MissionStatus.transition(request)` | `aggregate.py:~355-378` | Shipped + **TESTED** (`tests/unit/status/test_mission_status_aggregate.py:410,437`, #1682). Still **no live production caller** |
| `MissionStatus.save(*, operation)` | `aggregate.py:~397-417` | Shipped + **TESTED** (`…:463,528`, #1682). Still **no live production caller** |
| `CoordAuthorityUnavailable` (fail-closed) | `aggregate.py:45` | Shipped |
| `agent/status.py` read-path migration | `cli/commands/agent/status.py:146,174,250,358,822` | Shipped — uses `MissionStatus.load().read_dir`; zero raw `kitty-specs/mission_slug` reads |

### 1.2 The residual (from `01KT6HVH` mission-review-report.md)

- ~~**RISK-001 (HIGH):** zero unit coverage~~ → **RESOLVED by #1682** (tests added). The *only* surviving half is **no live production caller**: `agent status emit` calls `emit_status_transition_transactional` directly (`cli/commands/agent/status.py:275`), bypassing the aggregate. This is the open D-1 fork (wire vs close #1667).
- ~~**RISK-006:** `_read_meta` silently returns `(None, False)`~~ → **RESOLVED by #1682**: `_read_meta` now raises `MissionMetadataUnavailable` on OSError/JSONDecodeError/non-dict/non-string fields (`aggregate.py:244-278`). FR-006 is a no-op.
- **Genuinely remaining (Workstream A):** FR-007 slug allowlist guard in `load()` (confirmed absent) + the D-1 decision.

### 1.3 Reuse map for the write path

| Component | Location | Role |
|-----------|----------|------|
| `validate_transition(from, to, ctx)` | `status/transitions.py:266` | Domain invariant; `transition()` delegates here (FR-005/FR-023) |
| `ALLOWED_TRANSITIONS` matrix | `status/transitions.py:20-57` | 9-lane legality table |
| `TransitionRequest` | `status/models.py:342-374` | **Exists** (issue ref correct); input to `transition()` |
| `emit_status_transition_transactional(request)` | `coordination/status_transition.py` | The existing live transactional caller `transition()` wraps |
| `BookkeepingTransaction.acquire(...)` | `coordination/transaction.py:598` | Infra; called internally; **must not be modified** (NFR-002) |
| `CommitReceipt` | `coordination/types.py:116-135` | Return type of `save()` |

### 1.4 #1672 parity ratchet — current coverage

- `tests/architectural/test_execution_context_parity.py` (478 lines) exists (WP02 of `01KT6HVH`).
- Per its docstring it is a **compact proof covering only `spec-kitty agent tasks status --json`** parity between main-checkout CWD and lane-worktree CWD.
- It does **not** cover the full `next → implement → move-task → review → status` sequence (#1672 AC). The write-path sequence parity is the open residual → narrow slice pulled in as **FR-008**.

---

## Part 2 — #1636 profile-load surfaces: activation model exists; consumers bypass it

### 2.1 Seam map (activation-aware vs activation-blind)

| Seam | Location | Activation-aware? |
|------|----------|-------------------|
| `charter list` | `cli/commands/charter/list_cmd.py:156` → `CharterPackManager.list_activated()` (`pack_manager.py:497`) | ✅ |
| Activation resolver (3-state) | `charter/pack_context.py:152` `_read_activated_agent_profiles` / `_read_list_key` (`:239-245`) | ✅ |
| **Activation-aware wrapper** | `charter/resolver.py:56-129` — `DoctrineService.agent_profiles` filters by `pack_ctx.activated_agent_profiles` | ✅ (when `pack_context` passed) |
| Wrapper construction pattern | `charter/generate.py:46-74`, `charter_runtime/lint/checks/org_layer.py:246` | ✅ (precedent to generalise) |
| `profile list` | `cli/commands/profiles_cmd.py:31` → `ProfileRegistry.list_all()` → `AgentProfileRepository.list_all()` (`agent_profiles/repository.py:556`) | ❌ blind |
| `profile show` | (does not exist — #1636) | ❌ |
| `charter context --include agent-profile:<id>` | `charter/context.py:282` → `_build_doctrine_service()` (`:1235`, unwrapped) | ❌ blind |
| `doctrine.service.DoctrineService.agent_profiles` | `doctrine/service.py:130` (raw repo) | ❌ blind |

### 2.2 Three-state activation contract (`activated_agent_profiles` in `.kittify/config.yaml`)

- `None` (key absent) → all built-ins active (FR-021 backward-compat / common case).
- `frozenset()` (present, empty) → nothing active (explicit opt-out).
- `frozenset({ids})` → only those ids active.

`charter list` already lists `agent-profile` as a first-class activatable kind (verified live: "agent-profile | (All built-ins — no explicit activation)"). So the activation model is end-to-end; only the two CLI consumers + the `--include` fetch path bypass it.

### 2.3 Why the activation-default makes `profile list` non-breaking

For projects with no explicit `activated_agent_profiles`, the key is absent → `None` → the wrapper returns **all** profiles. So default `profile list` output is identical to today; behavior only narrows for projects that deliberately restricted their set (NFR-001).

### 2.4 Skill drift (#1636)

`src/doctrine/skills/ad-hoc-profile-load/SKILL.md` documents four commands that do not exist (git history: never implemented):

| Command in SKILL.md | Lines | Exists? |
|---|---|---|
| `agent profile show <id>` | 52, 225 | ❌ |
| `agent profile hierarchy` | 81, 228 | ❌ |
| `agent profile init <id>` | 208, 231 | ❌ |
| `agent profile create` | 13, 39 | ❌ |

Canonical surfaces that **do** exist for *invoke/adopt*: `spec-kitty ask <profile> <request>` and `spec-kitty advise <request> --profile <p>` (`cli/commands/advise.py`). What is missing is an *inspect* surface (the new `profile show`, FR-013).

---

## Part 3 — Suggested contracts / design

### 3.1 Shared activation factory (single construction seam)

```python
# specify_cli — may import PackContext via charter.* (layer rule C-005)
def build_activation_aware_doctrine_service(repo_root: Path) -> "charter.resolver.DoctrineService":
    from charter.resolver import DoctrineService as ActivationDoctrineService
    from charter.pack_context import PackContext
    from doctrine.service import DoctrineService as InnerDoctrineService
    inner = InnerDoctrineService(built_in_root=..., project_root=..., org_roots=...)
    return ActivationDoctrineService(inner, pack_context=PackContext.from_config(repo_root))
```

Consumers routed through it: `profile list`, `profile show`, `charter context --include agent-profile:<id>`.

### 3.2 `profile show` resolution (lineage Option A + warning)

1. **Visibility gate** — `service.agent_profiles.get(id)`; absent & not `--all` → structured `profile_not_activated` listing activated candidates.
2. **Definition resolution** — compose `specializes_from` lineage via inner `AgentProfileRepository.resolve_profile(id)`; may traverse non-activated parents (abstract bases).
3. **Warning** — if any traversed ancestor ∉ activated set, emit: "resolved via non-activated parent profile(s): … — these act as abstract bases and are not directly selectable."

### 3.3 `profile list` UX (mirror `charter list`)

| Mode | Source | Output |
|------|--------|--------|
| default | wrapper `.agent_profiles` | activated-only |
| `--all` | inner `.list_all()` | every layer, annotated `activated | available` + source |
| `--show-available` | inner `.list_all()` | activated + available-but-not-activated |

### 3.4 Write-path completion (Workstream A)

- Test `transition()`: legal transition → 1 event + returned `StatusEvent`; illegal pair w/o force → raises before append/commit.
- Test `save()`: staged transitions → `CommitReceipt` with expected `event_ids`.
- Resolve D-1 (wire a real caller vs. document the existing `emit_status_transition_transactional` delegation as the sanctioned path).
- Fail-closed guards: `_read_meta` typed error on real I/O failure (RISK-006); slug allowlist at `load()` (DIRECTIVE_010).
- Extend the parity ratchet over the write transition (FR-008).

---

## Source references

- Issues: [#1667](https://github.com/Priivacy-ai/spec-kitty/issues/1667), [#1636](https://github.com/Priivacy-ai/spec-kitty/issues/1636), [#1672](https://github.com/Priivacy-ai/spec-kitty/issues/1672).
- Prior mission: `kitty-specs/execution-state-domain-remediation-01KT6HVH/` (`mission-review-report.md` RISK-001/RISK-006; `issue-matrix.md`).
- Governing ADRs: `architecture/3.x/adr/2026-06-03-1-execution-state-domain-model.md`, `…-2-executioncontext-owner-and-committarget.md`.
- #1636 design discussion: GitHub issue comments (2026-06-05), authored as Architect Alphonso.
