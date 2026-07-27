# Quickstart: Verifying Pack-Path Portability & Language-Scope Authority

## WP1 — Pack-path env-var indirection

1. Set an env var and write a portable config:
   ```bash
   export SPEC_KITTY_PACK_HOME=/tmp/acme-doctrine
   ```
   ```yaml
   # .kittify/config.yaml
   doctrine:
     org:
       packs:
         - name: acme
           local_path: "${SPEC_KITTY_PACK_HOME}/acme-doctrine"
   ```
2. Run `spec-kitty doctor doctrine --json` — the org pack should resolve to `/tmp/acme-doctrine/acme-doctrine`, with no literal `${...}` in the resolved path.
3. Unset `SPEC_KITTY_PACK_HOME` and re-run — expect a named, actionable error (not a silent empty org layer, not a literal-path passthrough).
4. Run any command that triggers `save_pack_registry` (e.g. `spec-kitty agent config add`), then re-read `.kittify/config.yaml` — `local_path` must still read `"${SPEC_KITTY_PACK_HOME}/acme-doctrine"` verbatim.

## WP2 — Language-scope authority

1. Create a project, run the discovery interview declaring Python only, generate the charter.
2. Edit `.kittify/charter/charter.md` directly to add "TypeScript" without re-running the interview.
3. Recompile (`charter sync`) so the structured language field is (re)persisted.
4. Run `spec-kitty charter context --action specify --json` (or any command surfacing `active_languages`) — both Python and TypeScript should be reflected, sourced from the compiled charter, not the stale interview transcript.
5. Run `pytest tests/charter/test_language_scope.py -v` — the corrected pinning test should assert charter-authoritative resolution on disagreement.
