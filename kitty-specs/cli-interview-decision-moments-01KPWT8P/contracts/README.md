# Contracts — CLI Interview Decision Moments

Planning-phase sketches of CLI command surfaces and response schemas. These are NOT the committed runtime schemas — the runtime source of truth is Pydantic (or dataclass) models in `src/specify_cli/decisions/models.py` and the `spec-kitty-events` 4.0.0 event schemas (vendored).

Files:
- `cli-contracts.md` — subcommand surfaces (args, env, exit codes, output shape)
- `index_entry.schema.json` — shape of an entry in `decisions/index.json`
- `decision_open_response.schema.json` — JSON returned by `spec-kitty agent decision open`
- `decision_terminal_response.schema.json` — JSON returned by resolve/defer/cancel
- `decision_verify_response.schema.json` — JSON returned by verify (empty findings array on success)
