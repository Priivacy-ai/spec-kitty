# WP02 independent review

Source `393e43497`; reviewed complete generated prompt, directive/procedure, activation/configuration/provenance changes and all five new tests. Disposition: approve source governance with installed adoption explicitly pending.

Independent verification in lane-b: `<CLI root venv>/bin/pytest -q -o pythonpath=<approved WP01 lane-a>/src tests/charter/test_hosted_binding_governance.py` — **5 passed, 17.48 seconds**. This composes approved WP01's actual canonical command with WP02's actual linked-checkout authority. The initial PYTHONPATH-only invocation got four passes and one `No such option: --owned-checkout` failure because pytest's repository configuration prepended lane-b's pre-WP01 source. That mismatch is preserved as an integration prerequisite, not an implementation pass. Explicit pytest source selection corrected the test environment; the final integrated mission must also run this test without a cross-lane override.

The genuine declared baseline and supported head comparison use the same `DeclaredCommandScopeSource/junit_xml`: zero failures and `no_new_failures`. The original source-mismatch artifact remains preserved. The configured regression scope covers existing charter/CLI neighbors; the five new governance tests above provide their separate direct evidence.

The required native-ID doctrine and linked verification procedure resolve through the actual activation-aware service. Directive deactivation, procedure deactivation and source removal each fail the consumer witness. The actual owned-checkout command returns effective project authority. Existing selected built-in directive filename slugs become their corresponding canonical IDs; existing activated selections and substantive policy remain intact. Source release, installed client, deployed server and all-team repair are explicitly distinguished.

Checklist:

1. Dead code — N/A: no new product module; existing activation and command consumers read the authored artifacts.
2. Synthetic-fixture test — PASS: real project files, actual canonical resolver/command and removal mutations.
3. Silent empty return — N/A: no new runtime exception/fallback path.
4. FR coverage — PASS: FR-003 native identity/supported-contract rules; FR-004 scoped truthful completion; NFR-002 each required authority's removal fails.
5. Frozen surface — PASS: authored governance/test ownership only.
6. Locked decision — PASS: canonical resolver and ownership retained; no installed tool patch, production operation or source-only deployment claim.
7. Shared-file ownership — PASS: WP01 owns implementation, WP02 owns project governance. Cross-lane command composition is explicit and final integrated verification remains required.
8. Production fragility — N/A: no new production code; required missing authority fails the canonical consumer witness.

Warnings reflect existing legacy org-pack configuration and unavailable/language-filtered unrelated catalog entries. Full installed CLI bootstrap remains affected by tracked #4017; this review does not claim installed CLI/Factory protection or authorize incident closure.
