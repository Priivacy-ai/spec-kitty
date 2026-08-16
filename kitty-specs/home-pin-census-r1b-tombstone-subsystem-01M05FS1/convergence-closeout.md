# R1b Convergence Closeout — #3121 ("converge only the provable class")

**Result:** census **40 → 26**. All **14** provable-class members converged onto the canonical
`SPEC_KITTY_HOME` owner (`canonical_home`), each recorded in the auditable tombstone manifest
(`tests/architectural/census/spec_kitty_home_pin_tombstones.yaml`) with a cause. The census guard
is green throughout; the ratchet still bites (spurious pin reds; a tombstone over a live pin is
refused at generation and reds t023).

## Converged (14) — `census ∪ tombstones` still == the frozen 40-key set

| Op | Members | Kind |
|----|---------|------|
| op1 | `body_queue_purge_differential::_isolated_home` | PC |
| op2 | `per_project_report::_home` | PC |
| op3 | 6× `upgrade/` inline pins (`test_m_0_6_7`×2, `test_compat`×2, `test_m_0_12_0`×2) | JC |
| op4 | `legacy_queue::test_a_credentials_read_failure…`, `routing::test_opt_out_purge…` | JC (surgical) |
| op5 | `body_drain::_isolated_home`, `nfr003::_consent`, `body_upload::_isolated_home` | JC (SAAS-premise preserved) |
| op6 | `daemon_publish::_isolated_home` | CR (SAAS_URL retained) |

## NOT converged — out of scope, by design

**Deletion-scope (3)** — arm-2-GREEN in the ablation (the pin is redundant → a *deletion* mission's
job, not convergence; converting them would adopt an owner they do not need and pre-empt that
adjudication): `purge_all_body_uploads::_isolated_home`, `purge_all_events::_isolated_home`,
`identity_value_faults::TestThePolicyGate…_isolated_home`.

**Must-stay (23)** — genuinely different seams (this is #3121's confirmed thesis: "a name
collision, not a duplicated seam"):
- **HOME/LOCALAPPDATA co-pins (13):** `test_sync_commands`, `sync_doctor_consent_health`,
  `sync_doctor_per_project`, `sync_doctor_tracker_egress`, `sync_migrate_backfills_h4`,
  `sync_now_empty_selection`, `sync_purge`, `sync_report_label…`, `sync_status_per_project`,
  `consent_fault_vocabulary`, `consent_field_fault`, `consent_write_refusal`,
  `tracker_egress_refusal::_isolated_home_and_arming` — each co-pins `HOME`/`LOCALAPPDATA`
  (and some `USERPROFILE`), a different isolation seam than the canonical owner provides.
- **Counter-autouse `delenv SAAS` (4):** `consent_read_fault`, `consent_resolver`,
  `local_commit_consent`, `local_commit_purge::test_the_flush…` — these *delete*
  `SPEC_KITTY_ENABLE_SAAS_SYNC` as a load-bearing precondition; adopting the owner (which does not
  delenv) would silently re-arm SAAS and invert the test.
- **`setattr`/`ProjectSyncStore` publish setup (5):** `capture_gate_project_identity`,
  `ws_publish_consent`, `dispatch_window_consent`, `liveness_predicate_before_limit`,
  `nfr002_loop_permanence` — home pin entangled with store-publish/cutover setup.
- **Nested-context inline pin (1):** `tracker_egress_refusal::test_bind_counter_wrapper…::_run_once`
  — the pin lives inside a nested `MonkeyPatch.context()` helper a fixture cannot be injected into.

## Definition of Done — met

- Census green at 26; `census ∪ tombstones` frozen at the 40-key set (hash unchanged).
- Every removed member has a manifest tombstone with recorded cause; **no** `members.json`/anchor/`E`
  edits; the ratchet still bites (verified).
- `census == ∅` remains a far-horizon DoD requiring a deletion mission (for the DS trio) and a
  member-promotion mechanism (for the 23 must-stay seams) that does not exist yet — a follow-on.

**#3121 is closeable on its re-scoped "converge only the provable class" mandate.**
