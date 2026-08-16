# Contract: Provenance tokens, secret redaction, release channel

## Provenance (both carriers, one normalizer)
- **C-PRV-1**: fresh charter compile → every built-in catalog `source_path` is `${SPEC_KITTY_PACKS_ROOT}/built-in/...`; 0 absolute paths. Same for `agent_profiles_manifest.json`.
- **C-PRV-2 (re-bake gate)**: with `SPEC_KITTY_PACKS_ROOT=/some/abs` exported, emitted artifacts are byte-identical to the unset case (token stored, never the resolved path).
- **C-PRV-3 (invariance)**: `charter.yaml` byte-identical across editable checkout and installed wheel.
- **C-PRV-4 (heal)**: an existing absolute `source_path` → rewritten to a token by the heal migration; re-run = 0 changes.
- **C-PRV-5 (leak-check)**: `spec-kitty doctor` (dedicated `_provenance_doctor.py` sibling under `cli/commands/doctor.py`, NOT `runtime/doctor.py`) flags any committed absolute built-in path with a heal hint.
- **C-PRV-6 (surgical normalizer, 3 classes)**: the shared path→token normalizer emits (a) token for built-in-pack paths, (b) repo-relative for in-tree project/org paths, (c) absolute for out-of-tree non-pack paths — replacing ONLY `compiler.py:1424/1447` + `projection.py:56`; a regression asserts mission-template callers (`compiler.py:1482/1494`) and manifest `output_path` (`manifest.py:112`) are byte-unchanged.

## Secret redaction (fail-closed allowlist)
- **C-SEC-1**: a var NOT on the printable-var allowlist (e.g. `SPEC_KITTY_SAAS_TOKEN`) never appears by value in `doctor`/`sync status`/logs — only its presence.
- **C-SEC-2**: `.kitty.env` matches an ignore rule in both `.gitignore` and `.claudeignore` (asserted by an architectural test).

## Release channel (consumer slice; interface with #3047)
- **C-CHN-1 (default off)**: with `SPEC_KITTY_PRERELEASE` unset and a newer rc on the index, `upgrade --agent-check` reports the latest **stable**; no rc advisory.
- **C-CHN-2 (opt-in)**: with it truthy, the newest PEP 440 pre-release on the same PyPI index the CLI already probes is surfaced; `upgrade_command` is `spec-kitty-cli==<rc>` (pinned, no `--pre`).
- **C-CHN-3 (doctor)**: `doctor` reports the active channel.
- **Interface with #3047**: producer must publish rc's as PEP 440 pre-releases on that index/scheme; this mission owns only the consumer read.

## Migration idempotency
- **C-MIG-1**: re-running the heal migration and the provision migration each yields 0 changes.
- **C-MIG-2 (no PACKS_ROOT seed)**: the provision scaffold never writes `SPEC_KITTY_PACKS_ROOT`; a regression asserts `SPEC_KITTY_TEMPLATE_ROOT` still governs asset resolution when the scaffold is present.
