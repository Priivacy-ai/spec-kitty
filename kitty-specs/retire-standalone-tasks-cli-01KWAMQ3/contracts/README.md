# Contracts — retire-standalone-tasks-cli-01KWAMQ3

This mission defines **no API/data contracts**. It is a net-removal mission
(deleting the dead, test-only standalone `scripts/tasks/` CLI in all three
copies) plus one small additive surface: an opt-in `spec-kitty accept
--normalize-encoding` flag that delegates to the **existing canonical**
`specify_cli.acceptance.normalize_feature_encoding` (no new contract).

The flag's behavior shape is recorded in [`../data-model.md`](../data-model.md)
("Added surface"), and the encoding-authority boundary (why it delegates to the
acceptance engine rather than `validate-encoding`'s `text_sanitization`) is
recorded in [`../plan.md`](../plan.md). No request/response schema, event
payload, or external integration contract is introduced or changed.

This directory exists to satisfy the software-dev mission's path convention.
