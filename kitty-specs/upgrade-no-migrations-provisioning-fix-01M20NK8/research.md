# Research — Upgrade No-Migrations Provisioning Fix (#4032)

## Decision 1 — Fix seam: the assessment/compiler layer, not the installer guard

- **Decision**: Make `PreparedUpgradeRepairs.provisioning` **Optional** and null it at the single assessment/compiler authority (`upgrade/assessment.py`) when the config authority is absent (`write.before_bytes is None` / `write.absent_parents`). Reduce `_prepare_skill_provisioning` (`skills/installer.py:416-442`) to a pure integrity validator (raise only on a malformed/non-canonical descriptor). Surface the absent case as a **non-error** diagnostic.
- **Rationale**: The guard's `ValueError` at `installer.py:428` is already caught by `assess_project_skills` (`installer.py:665-668`) and converted to an `error`-severity diagnostic that poisons `PreparedUpgradeRepairs.complete` (`assessment.py:65`) → `activation_errors` → failed outcome (`finalize.py:59-62`). It is not an escaping exception, so "stop the guard raising" is the wrong lever. Critically, a *second* raw descriptor (`PreparedUpgradeRepairs.provisioning`, built at `assessment.py:120`, applied at `upgrade.py:1035`) is decoupled from the guard; a benign guard lets the finalizer's raw `.apply()` emit a `"create"` effect for the absent authority (`assessment.py:100`) — i.e. it would silently perform the #4047 create-from-absent behavior this mission defers (C-001). Nulling the Optional descriptor at the single seam keeps guard/recheck/effects/finalizer consistent and makes #4047 a one-seam toggle.
- **Alternatives considered**: (a) *Guard-only non-fatal clause* — rejected: leaves the decoupled raw `.apply()` free to create the authority (violates C-001) and splits the policy across two sites. (b) *Full create-from-absent now* — rejected: out of scope; `_recheck_skill_provisioning` (`installer.py:445-473`) is in-place-only and cannot validate a create transition → #4047.

## Decision 2 — Diagnostic channel: non-error, dedicated key

- **Decision**: The absent-authority deferral emits a **non-error** diagnostic on a dedicated channel — a JSON `deferred_provisioning` (a.k.a. `skipped`) field + a human-mode `Note:` line (reusing the `upgrade.py:477` surface) — never an `errors` entry and never a `warnings` entry. Contract: [contracts/deferred-provisioning-diagnostic.md](./contracts/deferred-provisioning-diagnostic.md).
- **Rationale**: `complete` must not be poisoned (else the outcome flips to `failed`). `test_upgrade_char_net.py` asserts `warnings == []`, so a warning-channel diagnostic would break the behavior-preservation oracle. The `errors` channel is owned by genuine failures (and by the `upgrade.py:517` activation-backfill subsystem that the monkeypatch test forces). A dedicated non-error field keeps the deferral observable (so #4047's pull-forward signal can fire) without colliding with either.
- **Alternatives considered**: warning channel (breaks the oracle); silent skip (untestable, hides unhealed state — the greenwash risk renata flagged).

## Decision 3 — Tidy-first decomposition boundary

- **Decision**: Decompose `upgrade()` (`cli/commands/upgrade.py:1421`) into named sub-functions and drop `# noqa: C901`, as WP01 preceding the fix. Preserve the `repair_preflight` `with` span (the `ExitStack` + `_RECHECKED_PROJECT`/`_COMMAND_PARENTS` ContextVars + `_PROJECT_SKILL_LOCK` RLock; `finalize.py:59-64`, `installer.py:476-480`) as **one atomic extracted unit** spanning provision+surface; keep the exit-code matrix (`outcome.derive_exit_code()`) and the `if not dry_run and outcome.result.success` pre-`_prepare_finalizer_repairs` guard (`upgrade.py:1662-1663`) intact.
- **Rationale**: A behavior-preserving decomposition gives a testable, un-suppressed surface for the fix (Standing Order #2). The preflight `with` span is lifetime-scoped to the provision+surface contract; splitting it into functions that open/close their own contexts silently breaks the paired-preflight recheck — a behavior change existing green tests would not catch.
- **Alternatives considered**: fix-without-decomposition (rejected — lands on a 345-line suppressed function, and `test_no_stray_noqa_c901_marker` stays red).

## Decision 4 — Test disposition policy

- **Decision**: Config-absent (`metadata.yaml`-only) fixtures are **KEPT** as legitimate legacy-heal witnesses (made to pass by the fix). "Re-pin" is reserved for genuinely unreachable shapes (e.g. a present-but-corrupt authority no `init` produces), each citing the code proving unreachability and preserving assertion strength (else deleted). The oracle `test_upgrade_char_net.py` is re-pinned to a **real init-ed** fixture so it keeps exercising the provisioning **apply** path (not the new skip path), re-deriving churn/warnings. The monkeypatch test `test_failed_run_exit_code_equals_outcome_exit_code` is **redesigned** to assert the forced activation-backfill error (`errors`) and the guard/skip diagnostic (dedicated channel) separately — it straddles two subsystems (managed-skill guard `installer.py:427` vs activation backfill `upgrade.py:517`). A **new** guard-aligned test drives the config-absent path. The triplicated project fixture is consolidated into one shared builder.
- **Rationale**: `_init_project` in the failing tests does NOT run real `init`; the `metadata.yaml`-only shape IS the config-absent legacy shape the mission must heal. Re-pinning it to an init-ed project would green-by-avoidance (stop exercising `before_bytes is None`) and satisfy SC-002 without fixing the bug.
- **Alternatives considered**: blanket re-pin of all ~40 (rejected — greenwash); leave-oracle-fixture-unchanged (rejected — silently converts the oracle into a test of the skip path, gutting NFR-003).

## Adversarial Evidence (post-spec squad — dispositions)

Per `contracts/adversarial-evidence-contract.md`: every contested finding, its disposition (`accepted` / `changed` / `deferred_with_rationale`), and where it landed. No finding silently dropped.

### Lens: reviewer-renata (correctness / acceptance)
| # | Sev | Finding | Disposition | Landed in |
|---|-----|---------|-------------|-----------|
| R1 | blocker | Non-fatal skip can masquerade as "repaired"; FR-002 diagnostic untestable/ungated | **accepted** | FR-003 + SC-004 + contracts/deferred-provisioning-diagnostic.md |
| R2 | major | SC-002 "attributable to guard" has no operational definition | **accepted** | SC-002 reworded to a frozen Group A nodeid list (enumerated in tasks) |
| R3 | major | FR-005 re-pin criterion lacks evidentiary bar + assertion-strength floor | **accepted** | FR-008 (cite unreachability proof; preserve strength or delete) |
| R4 | major | Present-but-empty/partial `config.yaml` (`b""`) is under-provisioned but not "absent" | **changed** → scoped OUT | C-006 + Edge Cases (must not hard-error; healing is follow-up) |
| R5 | minor | US1-S1 disjunction "no-op OR auto-commit" is non-deterministic | **accepted** | US1-S1 pins the single `up_to_date` outcome |
| R6 | minor | Guard fires regardless of whether migrations ran | **accepted** | US1-S4 (migrations-ran-authority-absent scenario) |

### Lens: architect-alphonso (seam / layering)
| # | Sev | Finding | Disposition | Landed in |
|---|-----|---------|-------------|-----------|
| A1 | high | Guard-only skip re-opens create-from-absent via the decoupled raw `prepared.provisioning.apply()` | **accepted** | Decision 1 + FR-002 + C-001 (no-create assertion) |
| A2 | high | The non-fatal seam is the diagnostic SEVERITY, not the `raise` | **accepted** | FR-003 (non-error severity; `complete` not poisoned) |
| A3 | medium | Absent-authority is charter/activation policy, not installer-guard policy | **accepted** | FR-002 (decision at assessment/compiler) + FR-004 (guard→validator) |
| A4 | medium | Riskiest extraction boundary = the `repair_preflight` `with` span (ContextVars + RLock) | **accepted** | Decision 3 + FR-005 + US3-S2 |
| A5 | medium | #4047 is a clean toggle only if deferral lands at the Optional-descriptor seam | **accepted** | Decision 1 (single-seam) |
| A6 | low | `absent_parents` + "left uncommitted" branch depend on seam 1/2, not the guard | **accepted** | Edge Cases (nulling at assessment suppresses eager create-effects) |

### Lens: paula-patterns (test-quality / anti-laziness)
| # | Sev | Finding | Disposition | Landed in |
|---|-----|---------|-------------|-----------|
| P1 | high | FR-005 would re-pin away the exact config-absent fixture US1 requires (green-by-avoidance) | **accepted** (refines operator's "re-pin" instruction) | FR-008 (KEEP config-absent) + SC-003 |
| P2 | high | Monkeypatch test is a contract redesign across two subsystems, not a re-pin | **accepted** | FR-009 |
| P3 | high | FR-004 "keep oracle green" silently converts it into a skip-path test / breaks on a warning diagnostic | **accepted** | FR-006 (re-pin oracle fixture to the apply path) + Decision 2 (non-warning channel) |
| P4 | medium | Headline config-absent bug has no faithful guard-aligned test | **accepted** | FR-007 (new config-absent guard-aligned test) |
| P5 | medium | Project-shape fixture triplicated across ≥3 files (duplicate-knowledge, #1931) | **accepted** | FR-010 (shared fixture builder) |
| P6 | medium | FR-006 red-first could be satisfied on the wrong provisioning subsystem | **accepted** | FR-011 (reproduce exact signal via config-absent path; adopt a pre-existing failing test) |

All 18 findings accepted/changed; none deferred-without-rationale, none dropped. (R4 is the only "changed": scoped out to a follow-up with rationale in C-006.)

## Adversarial Evidence — post-tasks squad (WP-breakdown dispositions)

Second point-cut (post-tasks), 2 lenses. All findings accepted; no design blocker.

### Lens: reviewer-renata (anti-laziness / fakeability)
| # | Sev | Finding | Disposition | Landed in |
|---|-----|---------|-------------|-----------|
| RT1 | major | Frozen Group A implementer-enumerated with no rerunnable binding → under-enumeration | **accepted** | WP03 T011 (verbatim command output; reviewer re-runs; must equal) + reviewer guidance |
| RT2 | major | T008 non-vacuity test can pass with the guard gutted (absent shape raises for unrelated reason) | **accepted** | WP02 T008 (present-authority non-canonical descriptor; exact ValueError from the function) |
| RT3 | major | Red-first not bound to the guard signal in the DoD | **accepted** | WP02 T005 (capture RED traceback with literal signal from provisioning/guard path) |
| RT4 | major | WP03 green-by-avoidance under-bound (re-pin 39, keep 1 passes) | **accepted** | WP03 reviewer guidance/DoD (no reachable config-absent re-pin; each re-pin cites unreachability) |
| RT5 | minor | `deferred_provisioning` fakeable as presence-only | **accepted** | WP02 T009 (assert content/signal + errors==[] + warnings==[]) |
| RT6 | minor | Oracle re-pin can silently become a skip-path test while green | **accepted** | WP03 T013 (affirmative apply-effect witness) |

### Lens: planner-priti (sequencing / ownership)
| # | Sev | Finding | Disposition | Landed in |
|---|-----|---------|-------------|-----------|
| PT1 | high | WP02 T007 must edit `cli/commands/upgrade.py` (WP01-owned) to render the diagnostic — no ownership handoff | **accepted** | WP01 T002 (generic non-error-diagnostic render seam, behavior-preserving) + WP02 T007 (populate from owned layer; recorded out-of-map fallback) |
| PT2 | medium | T010 real-init-ed builder has no WP02 consumer (dead-on-arrival risk) | **accepted** | WP02 T010 (smoke-exercise the init-ed builder in WP02) |
| PT3 | low | `_fixtures.py` handoff clean only if T010 pre-builds all variants WP03 needs | **accepted** | WP02 T010 (cross-reference exact variants WP03 T012/T013 consume) |
| PT4 | low | C-006 (`b""` degenerate authority must-not-hard-error) pinned by no test; T008 reshapes that guard | **accepted** | WP02 T008 (b"" no-hard-error regression lock) |
| PT5 | info | authoritative_surface `src/specify_cli/upgrade/` valid; WP01→WP02→WP03 sequencing sound | **accepted (no change)** | — |

All 11 post-tasks findings accepted; none dropped. No ownership/frontmatter change required (fixes are DoD/guidance + a behavior-preserving WP01 render seam).
