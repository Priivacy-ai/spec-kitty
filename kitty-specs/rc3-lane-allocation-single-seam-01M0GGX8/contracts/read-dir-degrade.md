# Contract — `resolve_read_dir_or_degrade` (WP4, FR-006, #3462)

Companion to the write-side `resolve_write_target_or_degrade`. Lives in
`src/mission_runtime/read_dir_degrade.py`, beside its sibling.

> **Right-sized (post-plan squad, architect+reviewer MED).** Ships for the **two genuine degrade
> consumers** — `retrospective/generator.py:264` (ZERO_EVIDENCE) and `core/worktree_topology.py:173`
> (DEGRADE_TO_FEATURE_DIR) — and is designed for growth. The `FAIL_CLOSED` pass-through sites and the
> bespoke sites are NOT force-migrated (they'd gain nothing); they are allowlisted (see below).

> **Layering constraint (post-plan squad, architect MED — CRITICAL, else `test_layer_rules.py` breaks).**
> `mission_runtime` may not import `specify_cli.*` at module scope. The sibling `write_target_degrade.py`
> keeps its `specify_cli.missions._read_path_resolver` imports **function-scoped/deferred** and is
> ledgered in `tests/architectural/test_layer_rules.py` via `_MISSION_RUNTIME_ALLOWED_SPECIFY_CLI["missions"]`.
> `read_dir_degrade.py` MUST do the same: import the typed errors / resolver **inside the function body**,
> and add its module to the layer-rules ledger in the SAME WP. A module-level import will fail CI's
> `test_layer_rules.py`.

## Signature

```python
def resolve_read_dir_or_degrade(
    repo_root: Path,
    mission_slug: str,
    kind: MissionArtifactKind,
    *,
    strategy: ReadDegradeStrategy,
    caught: tuple[type[BaseException], ...],
    degrade_target: Path | None = None,   # required for DEGRADE_TO_* / ZERO_EVIDENCE
) -> ReadDirDecision: ...
```

Resolution is attempted FIRST regardless of strategy (fail-closed callers still get the real surface when
one exists). Only when resolution raises an exception **in `caught`** does the strategy's fallback apply.

## Behavioral contract

1. Resolution succeeds → `ReadDirDecision(read_dir=<resolved>, degraded=False, strategy=...)`.
2. Resolution raises `e in caught` → apply strategy:
   - `DEGRADE_TO_FEATURE_DIR` / `ZERO_EVIDENCE` →
     `ReadDirDecision(read_dir=degrade_target, degraded=True, strategy=...)`, logged at WARNING.
   - `FAIL_CLOSED` → re-raise `e` verbatim.
3. Resolution raises `e not in caught` → propagate verbatim (never swallowed). **This is how #1848 is
   preserved:** the `status/aggregate.py:351` site declares a `caught` set that EXCLUDES
   `CoordinationBranchDeleted`, so the data-loss subclass propagates as `COORDINATION_BRANCH_DELETED`
   even though the more-general `StatusReadPathNotFound` is caught.

## Migration map (each site keeps its exact prior behavior — behavior-preserving)

| Site | Prior fallback | Disposition | `caught` |
|------|---------------|-------------|----------|
| `retrospective/generator.py:264` | degrade to empty trace list, WARNING | **MIGRATE** → `ZERO_EVIDENCE` | `(CoordinationBranchDeleted,)` |
| `core/worktree_topology.py:173` | degrade `status_feature_dir` to `feature_dir` | **MIGRATE** → `DEGRADE_TO_FEATURE_DIR` | `(CoordinationBranchDeleted,)` |
| `status/aggregate.py:351` | re-raise `CoordinationBranchDeleted`; re-wrap `StatusReadPathNotFound`→`CoordAuthorityUnavailable` | **ALLOWLIST (bespoke)** — fails all 4 strategies: has no single `degrade_target` to return AND must re-wrap one sibling error while re-raising its subclass (#1848 ordering) | n/a |
| `cli/commands/agent/status.py:154` | typer.Exit on typed errors | **ALLOWLIST (pass-through)** — `FAIL_CLOSED` re-raise removes no `try/except`; the caller owns the `typer.Exit` | n/a |
| `cli/commands/agent/status.py:195` | typer.Exit on typed errors | **ALLOWLIST (pass-through)** — same as `:154` | n/a |
| `cli/commands/_review_cycle_reconcile_doctor.py` | unconditional `CoordinationBranchDeleted` before read | **ALLOWLIST (not a degrade-read)** — absorbs before any read happens; record the "not resolve-then-degrade" proof at implement | n/a |

> **Design-pass rule (US-4.2):** the helper must NOT collapse sites into one hardcoded try/except. Only the
> two genuine resolve-then-degrade sites migrate. Every ALLOWLIST entry must, per the acceptance criterion
> below, state **which** of the four strategies it fails and **why** — a checkable claim, not "it's
> complicated". Preserve behavior byte-for-byte; add per-site red-first parity tests for the two migrated
> sites and a pinning test for the aggregate #1848 ordering.

## Allowlist acceptance criterion (post-plan squad, reviewer MED — anti-rubber-stamp)

The WP3 anti-bypass guard's allowlist is not a free pass. Each entry MUST record, as a rationale comment
adjacent to the entry: (a) the site `file:symbol`, (b) which strategy(ies) it fails, (c) the concrete
reason. Example (aggregate): *"fails DEGRADE_TO_* and ZERO_EVIDENCE — no single degrade dir exists; fails
FAIL_CLOSED — must re-wrap StatusReadPathNotFound→CoordAuthorityUnavailable while re-raising the
CoordinationBranchDeleted subclass verbatim (#1848 ordering)."* An entry that cannot name a failed
strategy + reason is a bypass, not an exception.

## Invariants pinned by tests (red-first)

- INV-R1: each migrated site's behavior is unchanged (before/after parity test per site).
- INV-R2 (#1848): a deleted coord branch carrying unmerged status still surfaces
  `COORDINATION_BRANCH_DELETED` verbatim — never degraded to an empty/primary read.
- INV-R3: `ZERO_EVIDENCE` degrade is logged at WARNING (retrospective trace-read parity).
