---
affected_files: []
cycle_number: 1
mission_slug: upgrade-no-migrations-provisioning-fix-01M20NK8
reproduction_command: spec-kitty agent tasks move-task WP03 --to approved --mission upgrade-no-migrations-provisioning-fix-01M20NK8
reviewed_at: '2026-09-08T18:49:16Z'
reviewer_agent: user
wp_id: WP03
---

Approved by user: Review passed: WP03 anti-laziness verified. (1) No green-by-avoidance: plan_json=False is an orthogonal pre-existing OptionInfo-trap fix, does not alter the config-absent shape; config-absent witnesses KEPT via build_config_absent_project (before_bytes is None) run through real CliRunner in integration/idempotency. (2) Re-pin justified: char_net re-pinned to real init-ed fixture, strips mission_type_activations to force genuine apply, affirmative assertions (config bytes changed, reason=='key_present', non-empty activations). (3) Genuine T014 redesign: split into real e2e deferral (a) + direct _finalizer_step_provision(prepared=None) forced-error seam (b); source confirms old monkeypatch point unreachable on real config-absent path. (4) installer split: dropped only 'absent', 8 tamper cases still assert full rejection, new defer test asserts complete=True + deferred_provisioning info/owner=provisioning + no config.yaml. (5) No weakened assertions; deletions are scaffold consolidation onto _fixtures.py. Spot-run 169 tests pass, ruff clean.
