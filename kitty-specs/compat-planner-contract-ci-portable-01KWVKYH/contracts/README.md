# Contracts — compat-planner-contract-ci-portable-01KWVKYH (#2419)

This mission ships **no new API contract**. It revives dead test-time enforcement of a **pre-existing** contract that lives elsewhere in the repo:

- `kitty-specs/cli-upgrade-nag-lazy-project-migrations-01KQ6YDN/contracts/compat-planner.json`

That committed, "stable across patch releases" JSON schema is the contract under test; this mission makes the two dead conformance checks (`test_upgrade_command.py::_validate_json_contract`, `test_messages.py::_validate_against_schema`) actually validate against it in CI. The contract file itself is unchanged.
