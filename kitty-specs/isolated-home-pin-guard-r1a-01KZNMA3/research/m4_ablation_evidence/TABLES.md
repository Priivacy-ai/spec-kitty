### Per-member table — all 28 (arm 1 over all 28; repeated arm and arm 2 as noted)

| # | Partition | File | Fixture (qualified) | `(argname, baseid)` key | arm1 | repeated | arm2 | in `P` |
|---|---|---|---|---|---|---|---|---|
| 1 | B1 | `tests/cli/commands/test_sync_commands.py` | `_isolated_home` | `_isolated_home@tests/cli/commands/test_sync_commands.py` | PASS 37/37 | n/a (not in P1∩A) | RED 27/37 | no |
| 2 | B1 | `tests/cli/commands/test_sync_doctor_consent_health_3030.py` | `checkout` | `checkout@tests/cli/commands/test_sync_doctor_consent_health_3030.py` | PASS 15/15 | n/a (not in P1∩A) | RED 15/15 | no |
| 3 | B1 | `tests/cli/commands/test_sync_doctor_per_project_3030.py` | `_isolated_home` | `_isolated_home@tests/cli/commands/test_sync_doctor_per_project_3030.py` | PASS 12/12 | n/a (not in P1∩A) | RED 12/12 | no |
| 4 | B2 | `tests/cli/commands/test_sync_migrate_backfills_h4.py` | `_isolated_home` | `_isolated_home@tests/cli/commands/test_sync_migrate_backfills_h4.py` | PASS 9/9 | n/a (not in P1∩A) | RED 9/9 | no |
| 5 | B2 | `tests/cli/commands/test_sync_now_empty_selection_t005.py` | `_now_machinery` | `_now_machinery@tests/cli/commands/test_sync_now_empty_selection_t005.py` | PASS 7/7 | n/a (not in P1∩A) | RED 7/7 | no |
| 6 | B1 | `tests/cli/commands/test_sync_purge_3030.py` | `checkout` | `checkout@tests/cli/commands/test_sync_purge_3030.py` | PASS 25/25 | n/a (not in P1∩A) | RED 22/25 | no |
| 7 | B1 | `tests/cli/commands/test_sync_report_label_is_a_purge_selector_3030.py` | `checkout` | `checkout@tests/cli/commands/test_sync_report_label_is_a_purge_selector_3030.py` | PASS 5/5 | n/a (not in P1∩A) | RED 5/5 | no |
| 8 | B1 | `tests/cli/commands/test_sync_status_per_project_3030.py` | `_isolated_home` | `_isolated_home@tests/cli/commands/test_sync_status_per_project_3030.py` | PASS 4/4 | n/a (not in P1∩A) | RED 4/4 | no |
| 9 | A | `tests/delivery/test_body_queue_purge_differential_3030.py` | `_isolated_home` | `_isolated_home@tests/delivery/test_body_queue_purge_differential_3030.py` | PASS 8/8 | PASS 16/16 | RED 1/8 | **YES** |
| 10 | A | `tests/delivery/test_dispatch_window_consent_3030.py` | `_consent_records` | `_consent_records@tests/delivery/test_dispatch_window_consent_3030.py` | RED 2/2 | n/a (not in P1∩A) | RED 2/2 | no |
| 11 | A | `tests/delivery/test_liveness_predicate_before_limit_3030.py` | `_consent` | `_consent@tests/delivery/test_liveness_predicate_before_limit_3030.py` | RED 2/3 | n/a (not in P1∩A) | RED 3/3 | no |
| 12 | A | `tests/delivery/test_nfr002_loop_permanence_3030.py` | `_consent_records` | `_consent_records@tests/delivery/test_nfr002_loop_permanence_3030.py` | RED 1/2 | n/a (not in P1∩A) | RED 2/2 | no |
| 13 | A | `tests/delivery/test_nfr003_predicate_cost_3030.py` | `_consent` | `_consent@tests/delivery/test_nfr003_predicate_cost_3030.py` | RED 2/5 | n/a (not in P1∩A) | RED 5/5 | no |
| 14 | A | `tests/delivery/test_per_project_report_3030.py` | `_home` | `_home@tests/delivery/test_per_project_report_3030.py` | RED 4/20 | n/a (not in P1∩A) | RED 20/20 | no |
| 15 | A | `tests/delivery/test_purge_all_body_uploads_3030.py` | `_isolated_home` | `_isolated_home@tests/delivery/test_purge_all_body_uploads_3030.py` | PASS 12/12 | PASS 24/24 | GREEN 12/12 | **YES** |
| 16 | A | `tests/delivery/test_purge_all_events_3030.py` | `_isolated_home` | `_isolated_home@tests/delivery/test_purge_all_events_3030.py` | PASS 11/11 | PASS 22/22 | GREEN 11/11 | **YES** |
| 17 | A | `tests/specify_cli/identity/test_identity_value_faults_3030.py` | `TestThePolicyGateAnswersInsteadOfCrashing._isolated_home` | `_isolated_home@tests/specify_cli/identity/test_identity_value_faults_3030.py::TestThePolicyGateAnswersInsteadOfCrashing` | PASS 147/147 | PASS 294/294 | GREEN 147/147 | **YES** |
| 18 | A | `tests/specify_cli/sync/test_local_commit_consent_3030.py` | `_isolated_home` | `_isolated_home@tests/specify_cli/sync/test_local_commit_consent_3030.py` | RED 1/13 | n/a (not in P1∩A) | RED 1/13 | no |
| 19 | A | `tests/sync/test_body_drain_consent_3030.py` | `_isolated_home` | `_isolated_home@tests/sync/test_body_drain_consent_3030.py` | RED 6/10 | n/a (not in P1∩A) | RED 7/10 | no |
| 20 | A | `tests/sync/test_body_upload_consent_3030.py` | `_isolated_home` | `_isolated_home@tests/sync/test_body_upload_consent_3030.py` | RED 2/5 | n/a (not in P1∩A) | RED 3/5 | no |
| 21 | A | `tests/sync/test_capture_gate_project_identity_3030.py` | `_isolated_home` | `_isolated_home@tests/sync/test_capture_gate_project_identity_3030.py` | RED 2/8 | n/a (not in P1∩A) | RED 8/8 | no |
| 22 | B1 | `tests/sync/test_consent_fault_vocabulary_3030.py` | `home` | `home@tests/sync/test_consent_fault_vocabulary_3030.py` | PASS 18/18 | n/a (not in P1∩A) | RED 6/18 | no |
| 23 | B1 | `tests/sync/test_consent_field_fault_3030.py` | `_isolated_home` | `_isolated_home@tests/sync/test_consent_field_fault_3030.py` | RED 1/50 | n/a (not in P1∩A) | RED 50/50 | no |
| 24 | A | `tests/sync/test_consent_read_fault_3030.py` | `_isolated_home` | `_isolated_home@tests/sync/test_consent_read_fault_3030.py` | RED 5/14 | n/a (not in P1∩A) | RED 11/14 | no |
| 25 | A | `tests/sync/test_consent_resolver_3030.py` | `_isolated_home` | `_isolated_home@tests/sync/test_consent_resolver_3030.py` | RED 5/28 | n/a (not in P1∩A) | RED 16/28 | no |
| 26 | B1 | `tests/sync/test_consent_write_refusal_3030.py` | `home` | `home@tests/sync/test_consent_write_refusal_3030.py` | PASS 29/29 | n/a (not in P1∩A) | RED 29/29 | no |
| 27 | A | `tests/sync/test_daemon_publish_consent_3030.py` | `_isolated_home` | `_isolated_home@tests/sync/test_daemon_publish_consent_3030.py` | PASS 18/18 | PASS 36/36 | RED 7/18 | **YES** |
| 28 | A | `tests/sync/test_ws_publish_consent_3030.py` | `_isolated_home` | `_isolated_home@tests/sync/test_ws_publish_consent_3030.py` | RED 2/9 | n/a (not in P1∩A) | RED 6/9 | no |

### `P` — published as a set, keyed `(file, qualified_name)`

| # | file | qualified_name | partition | arm1 | repeated/interleaved | arm2 discharge (A18) |
|---|---|---|---|---|---|---|
| 1 | `tests/delivery/test_body_queue_purge_differential_3030.py` | `_isolated_home` | A | PASS 8/8 | PASS 16/16 | **RED** → directory load-bearing → conversion candidate, member **STAYS** in the adopting set |
| 2 | `tests/delivery/test_purge_all_body_uploads_3030.py` | `_isolated_home` | A | PASS 12/12 | PASS 24/24 | **GREEN** → neither load-bearing → removed from adopting set; deletion **out of scope**, filed as follow-on |
| 3 | `tests/delivery/test_purge_all_events_3030.py` | `_isolated_home` | A | PASS 11/11 | PASS 22/22 | **GREEN** → neither load-bearing → removed from adopting set; deletion **out of scope**, filed as follow-on |
| 4 | `tests/specify_cli/identity/test_identity_value_faults_3030.py` | `TestThePolicyGateAnswersInsteadOfCrashing._isolated_home` | A | PASS 147/147 | PASS 294/294 | **GREEN** → neither load-bearing → removed from adopting set; deletion **out of scope**, filed as follow-on |
| 5 | `tests/sync/test_daemon_publish_consent_3030.py` | `_isolated_home` | A | PASS 18/18 | PASS 36/36 | **RED** → directory load-bearing → conversion candidate, member **STAYS** in the adopting set |
