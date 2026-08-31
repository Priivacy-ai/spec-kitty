# Research: Profile Invocation Runtime and Audit Trail

**Phase 0 findings for** `profile-invocation-runtime-audit-trail-01KPQRX2`
**Date**: 2026-04-21

---

## R-0-1 — ULID dependency

**Decision**: Use `python-ulid` (already present in the spec-kitty dependency graph via `src/specify_cli/status/models.py`).
**Evidence**: `grep -r "ulid" src/specify_cli/status/` confirms ULID generation is already in use for `StatusEvent.event_id`. No new dependency.
**Implication for plan**: WP4.1 imports from the same ULID source as the status module. No `pyproject.toml` change needed.

---

## R-0-2 — `build_charter_context` programmatic API

**Decision**: The executor calls `build_charter_context(repo_root, profile=profile_id, action=action, mark_loaded=False)` directly.
**Evidence**: `src/charter/context.py::build_charter_context` accepts `profile: str | None`, `action: str`, `mark_loaded: bool = True`, `depth: int | None = None`. Returns `CharterContextResult(action, mode, first_load, text, references_count, depth)`. The function is importable without a CLI subprocess.
**Critical detail**: `mark_loaded=False` must be set. The function updates `.kittify/charter/context-state.json` when `mark_loaded=True`, recording which actions have had their "first load". Invocations must not poison this state — the `specify`/`plan`/`implement`/`review` flows depend on first-load detection for bootstrap vs compact context switching.
**Degraded mode**: when no charter is present (`mode="missing"`), `result.text` is an empty string. The executor treats this as `governance_context_available=False` and returns a partial `InvocationPayload` with a warning. The `InvocationRecord` is still written.
**Implication for plan**: executor imports `from charter.context import build_charter_context`. No CLI subprocess shelling.

---

## R-0-3 — AgentProfileRepository constructor and project-local override

**Decision**: Construct as `AgentProfileRepository(project_dir=repo_root / ".kittify" / "profiles")`. Shipped-profile fallback is automatic.
**Evidence**: `AgentProfileRepository.__init__` accepts `project_dir: Path | None = None`. When `project_dir` is supplied and the directory exists, it loads project-local `.agent.yaml` files and merges them with shipped profiles by `profile-id`. When the directory does not exist, the constructor proceeds with shipped profiles only, no exception.
**Implication for plan**: `ProfileRegistry` wraps the repository with `project_dir` set. For projects that have not run Phase 3 synthesis, only shipped profiles are available. This is expected and correct — the error message for "no profiles configured" should direct the operator to `spec-kitty charter synthesize`.
**Shipped profiles location**: `src/doctrine/agent_profiles/shipped/`. These ship with the package and are always available.

---

## R-0-4 — DEFAULT_ROLE_CAPABILITIES canonical verbs (confirmed)

**Decision**: Use `DEFAULT_ROLE_CAPABILITIES` directly from `src/doctrine/agent_profiles/capabilities.py` in the router.
**Evidence**: Verified all 8 roles and their canonical_verbs:

| Role | Canonical Verbs |
|------|----------------|
| IMPLEMENTER | generate, refine, implement |
| REVIEWER | audit, assess, review |
| ARCHITECT | audit, synthesize, plan |
| DESIGNER | synthesize, draft, design |
| PLANNER | plan, decompose, prioritize |
| RESEARCHER | analyze, investigate, summarize |
| CURATOR | classify, curate, validate |
| MANAGER | coordinate, delegate, monitor |

**Router alias table** (derived from canonical verbs, maps request tokens → canonical action):

| Request token | Canonical action | Source |
|--------------|-----------------|--------|
| implement, build, code, develop, create | implement | IMPLEMENTER canonical verbs |
| generate, write, produce | implement | IMPLEMENTER aliases |
| refine, improve, fix, patch | implement | IMPLEMENTER aliases |
| review, check, audit, assess, inspect | review | REVIEWER canonical verbs |
| plan, decompose, break down, outline | plan | PLANNER canonical verbs |
| prioritize, triage, rank | plan | PLANNER aliases |
| specify, spec, define, design | specify | ARCHITECT/DESIGNER |
| analyze, investigate, research, explore | analyze | RESEARCHER canonical verbs |
| summarize, synthesize, compile | analyze | RESEARCHER/ARCHITECT aliases |
| curate, classify, organize, validate | curate | CURATOR canonical verbs |
| coordinate, manage, delegate, monitor | coordinate | MANAGER canonical verbs |

**Stop-word list** (30 words): a, an, the, this, that, these, those, is, are, was, were, be, been, being, have, has, had, do, does, did, will, would, could, should, may, might, must, can, please, kindly.

**Implication for plan**: the router is a pure function over this alias table + domain_keywords. WP4.2 tests every row in the alias table.

---

## R-0-5 — CLI-SaaS contract schema gap (unresolved)

**Decision**: WP4.7 has a mandatory entry gate to verify `ProfileInvocationStarted` / `ProfileInvocationCompleted` field coverage against `InvocationRecord` v1.
**Evidence**: Issue #495 (April 13, 2026) confirms these envelope types exist in `spec-kitty-saas`. The contract YAML at `spec-kitty-saas/contracts/cli-saas-current-api.yaml` could not be fetched (private repo, auth failure). Assumed fields from issue #495 context: `invocation_id`, `profile_id`, `action`, `started_at`. Fields that may be missing: `request_text`, `governance_context_hash`, `outcome`, `evidence_ref`.
**Risk**: if the SaaS contract lacks fields, WP4.7 implementer cannot adapt silently — they must raise a blocking issue with the spec-kitty-saas team.
**Implication for plan**: WP4.7 entry gate is a hard dependency on contract verification. If the gap is found during WP4.7, that WP is blocked until the contract is updated — this does not block WPs 4.1–4.6.

---

## R-0-6 — CLI registration pattern

**Decision**: Follow the existing `app.add_typer()` pattern in `src/specify_cli/cli/main.py`.
**Evidence**: Confirmed by reading `main.py` — each command group is registered with `app.add_typer(group_app, name="command-name")`. New groups (`profiles`, `advise`, `ask`, `do`, `profile-invocation`, `invocations`) follow the same pattern.
**Implication for plan**: `main.py` is the only existing file touched by WP4.1/WP4.3/WP4.5/WP4.8 (for registration only). Conflict risk is low — each WP adds one `add_typer()` call.

---

## R-0-7 — Concurrent write safety

**Decision**: Per-invocation JSONL files (filename = `<profile_id>-<invocation_id>.jsonl`) are inherently concurrent-write-safe.
**Evidence**: ULID is generated at executor entry (before any I/O). Two concurrent `advise` calls for the same profile produce ULIDs that differ in at least the millisecond component (and the random component guarantees uniqueness). File creation uses `Path.open("x")` (exclusive create) to detect the astronomically unlikely collision and retry with a new ULID.
**Implication for plan**: No cross-file locking needed. `invocations list` reads from a directory scan — concurrent writers add files while the scanner runs; the scanner only returns complete files (those where the initial write succeeded).

---

## R-0-8 — intake isolation

**Decision**: `src/specify_cli/cli/commands/intake.py` is a standalone command with no shared entry points with the executor.
**Evidence**: Confirmed by reading `intake.py` — it calls `OfflineQueue` and `charter context` directly, with no reference to any invocation or executor class. There is no shared import that would accidentally pull in the executor path.
**Implication for plan**: No defensive guards needed in the executor. The negative test ("intake produces 0 JSONL records") is a regression guard, not a required defensive measure.

---

## R-0-9 — Performance baseline for `invocations list`

**Decision**: Use directory scan + last-line read for the initial implementation. Add index file if benchmarking shows > 200ms at 10,000 entries.
**Evidence**: A directory scan of 10,000 small JSONL files on a macOS developer machine (SSD) takes approximately 50–100ms. Reading the last line of each file adds approximately 1ms per file for a 500-byte JSONL entry, totaling ~50–100ms additional. Total estimated: 100–200ms — borderline. WP4.8 must benchmark and add the index if the threshold is breached.
**Index design (if needed)**: Append-only `.kittify/events/invocation-index.jsonl`, one line per invocation, containing `invocation_id`, `profile_id`, `started_at`. `invocations list` reads the index backward until `limit` is satisfied. The `writer.write_started()` call appends to the index atomically after writing the invocation file.
