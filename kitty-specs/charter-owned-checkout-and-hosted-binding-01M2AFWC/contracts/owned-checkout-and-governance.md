# Owned checkout and hosted governance contract

This records the implemented boundaries in the approved WP01/WP02 source; it does not broaden the mission or claim installed adoption.

- `charter new` and `charter context` accept explicit `--owned-checkout PATH`. The existing checkout ownership classifier must accept that repository root or linked worktree, within the invocation repository. Invalid, foreign, missing or nested foreign roots fail before writes or unrelated authority delivery.
- The selected checkout is invocation-local. Authoring paths, bundle freshness, activation reads and JSON/text/include resolution retain that selection. Default invocations continue resolving the primary checkout. Scope resets on return/error and does not leak between concurrent contexts.
- Authoring refuses path/symlink escape before making directories. Existing primary files remain byte-stable during explicit linked-checkout operations.
- Project `CLI_HOSTED_BINDING_COMPATIBILITY` is required and references active `cli-hosted-binding-verification`. The canonical activation-aware service and owned action context consume these sources. Missing source or inactive required directive/procedure cannot satisfy the governance witness.
- Provider native repository ID defines identity; mutable owner/name locators require verified identity and eligibility. Denial, unavailable authority, reused locator and mismatched identity cannot authorize implicit admission.
- Source release, installed client, observed server deployment and all-team repair are distinct claims. This mission delivers source code and activated project source only. Installed CLI/Factory adoption and current operational outcomes belong to parent recovery #1711/#1713.

Evidence: `tests/specify_cli/cli/commands/test_charter_owned_checkout.py` and `tests/charter/test_hosted_binding_governance.py`, plus the independent WP reviews. The governance test must use the integrated WP01 implementation; its pre-integration cross-lane source override is documented and must be removed for final integrated verification.
