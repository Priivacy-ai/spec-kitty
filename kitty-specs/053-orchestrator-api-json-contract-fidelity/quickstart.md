# Quickstart: Feature 053 — Orchestrator-API JSON Contract Fidelity

## What changed

The orchestrator-api now guarantees JSON output on stdout for all invocations — including errors — regardless of whether it's invoked directly or through the root `spec-kitty` CLI.

## Before (broken)

```bash
$ spec-kitty orchestrator-api contract-version --bogus
Usage: spec-kitty orchestrator-api contract-version [OPTIONS]
Try 'spec-kitty orchestrator-api contract-version --help' for help.

Error: No such option: --bogus
```

Prose on stderr. No JSON. External orchestrators can't parse this.

## After (fixed)

```bash
$ spec-kitty orchestrator-api contract-version --bogus
{"contract_version":"1.0.0","command":"orchestrator-api.unknown","timestamp":"...","correlation_id":"corr-...","success":false,"error_code":"USAGE_ERROR","data":{"message":"No such option: --bogus"}}
```

JSON envelope on stdout. Orchestrators parse `error_code` to handle errors programmatically.

## Key changes

1. **`_JSONErrorGroup.invoke()` override** — catches errors at the dispatch level, works when nested as a sub-group of the root CLI
2. **Docs updated** — `--json` flag removed from `contract-version` signature (the API is always-JSON, no flag needed)
3. **Root CLI tests added** — integration tests invoke through `spec-kitty orchestrator-api ...`, not just the sub-app

## No `--json` flag

The orchestrator-api is always JSON. There is no `--json` flag. Callers that pass `--json` will receive a `USAGE_ERROR` envelope.
