# Post-plan adversarial squad — convergent findings

Point-cut: post-plan. Three profile-loaded, read-only lenses (debugger-debbie, architect-alphonso,
reviewer-renata). Core claim ("exempt planning_artifact from the finalize kitty-specs ban is safe
and fail-closed for code_change is preserved") **survives** — the mechanism is sound. The squad
found refinements that reshape the fix and the test design; each is folded into plan/data-model/contract.

## Falsified (do not re-litigate)
- `str(ExecutionMode.PLANNING_ARTIFACT) == "planning_artifact"` — TRUE (`StrEnum`); the exemption fires.
- `execution_mode` is populated at ban time for explicit AND inferred WPs (`_apply_ownership_inference`
  runs before the ban at `mission_finalize.py:2069`). No `None` reaches the ban except the
  unreadable-WP `continue`.
- Existing `code_change` ban tests pin the mode explicitly (`_build_feature` → `execution_mode: code_change`),
  so the exemption cannot silently flip the fail-closed floor green.
- The "no ownership manifest" raise cannot fire for the in-scope shape (owns a kitty-specs path ⇒
  `owned_files` non-empty ⇒ manifest built ⇒ routes to planning lane).

## Adopted refinements

| # | Severity | Finding | Disposition |
|---|----------|---------|-------------|
| R-1 | MEDIUM (renata) | Exempting on `execution_mode` alone newly ADMITS a mislabeled `planning_artifact` WP owning `src/` code (only warned) — removes the one hard-stop. | **CHANGED**: confine the exemption to `planning_artifact` WPs whose `owned_files` are ALL under `_PLANNING_PREFIXES` (import the canonical constant from `ownership.validation`, do not re-derive). Add a red test: `planning_artifact` + `src/` ownership still rejected. |
| A-1 | MEDIUM (architect) | The ban is not the last gate; the exemption now EXPOSES `validate_no_overlap` for two overlapping planning WPs (previously the ban rejected first). | **ACCEPTED**: add a negative test — two overlapping planning WPs still rejected (overlap fail-closed floor). |
| A-2 | MEDIUM (architect) | Decision table omits `unset → inferred planning_artifact → ACCEPT`, a real reachable path; inference→ban ordering is an implicit invariant. | **ACCEPTED**: add the row + an acceptance test pinning the ordering. |
| D-1 | HIGH (debbie) | Red-first positive test is CONFOUNDED: post-fix, control falls through to two downstream HARD gates — `validate_authoritative_surface` (surface must prefix a kitty-specs owned file) and `validate_glob_matches` (literal deliverable must exist or be in `create_intent`; runs even in `--validate-only`). A naive test is RED-both-times (proves nothing). | **ACCEPTED**: construct the acceptance test inference-driven (empty `owned_files` + planning-only body → inferred `owned_files=[kitty-specs/<slug>/**]`, inferred surface, glob matches existing `spec.md`/`plan.md`) OR set a kitty-specs `authoritative_surface` + `create_intent`. Assert finalize passes line 2085 AND `wp_id in compute_lanes(...).planning_artifact_wps`. |
| D-2 | HIGH (debbie) | C-003 "deliverable durability" is filename-scoped: `auto_rebase` take-theirs manages `{WORK_PACKAGE_TASK, LANE_STATE, ANALYSIS_REPORT}` kinds — a planning deliverable named `analysis-report.md` (a plausible "measurement snapshot") IS clobbered. A benign-name test manufactures false confidence. | **ACCEPTED**: reword C-003 — durability holds only where `kind_for_mission_file(path) is None`; add a NEGATIVE matrix assertion that `analysis-report.md` / `tasks/WP*.md` is NOT durable; document the carve-out. Exercise `_is_coordination_owned_artifact` (`auto_rebase.py:236`). |
| D-3 | MEDIUM (debbie) | The unset→inferred-`code_change` rejection is net-new; a `kitty-specs`-owning WP with a minimal body infers `planning_artifact`. A naive test is a false-negative. | **ACCEPTED**: the fail-closed-via-inference test must include a `src/`/`.py` code signal in the WP body and assert the resolved `execution_mode == code_change` before asserting `INVALID_WP_OWNED_FILES_KITTY_SPECS`. |
| D-4 | MEDIUM (debbie) | IC-02 regression assertions named hand-wavily. | **ACCEPTED**: bind them to seams — `infer_authoritative_surface` (`inference.py:154`) and `_is_coordination_owned_artifact` (`auto_rebase.py:236`) — as pure predicate unit tests, not fragile finalize integration tests. |
| D-5 / A-3 | LOW (debbie/architect) | "ban did not fire" ≠ proof of exemption (unreadable-WP `continue`). | **ACCEPTED**: assert the WP is present in the finalized manifest/planning lane, not merely exit 0. |
| R-2 | LOW-MED (renata) | INV-2 "never by path shape" overclaims — inference IS path-shaped one level up. | **CHANGED**: reword INV-2 — the predicate keys on `execution_mode`; inference may use path signals to set the mode for unset WPs, and any code signal forces `code_change` (fail-closed). |
| R-3 | LOW (renata) | enum==str comparison rides on `StrEnum`. | **ACCEPTED**: compare against `ExecutionMode.PLANNING_ARTIFACT.value` (or normalize) and pin the string-equality contract with a test. |
| A-4 | LOW (architect) | `commit_guard.py:88` (runtime) and the finalize ban (plan-time) duplicate the same topology rule with no shared helper. | **DEFERRED (follow-up ticket)**: file a dedup ticket; predicate-local is the right minimal fix for this mission (does not deepen #3214). |

No contested finding is silently dropped (adversarial-evidence contract). No finding is a blocker; all are refinements that harden the fix and its evidence.
