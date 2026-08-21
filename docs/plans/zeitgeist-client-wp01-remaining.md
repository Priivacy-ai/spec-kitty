# zeitgeist_client WP01 — remaining scope

Status note for `src/specify_cli/zeitgeist_client/` (Bead `Z1-T1`). This is the
committed source of truth that in-code comments and error messages point to
for "what's left in WP01" — mirrors the ordered task list from the Z1
drafting note (`Z1.md §5`, an out-of-repo scratchpad draft, items 2-6), kept
current in this repo instead of in a document that never lands here.

Landed so far: `grammar.py`, `sanitizer.py`, `budget.py`, `transport.py`
(`offer()`/`focus_start()`/`focus_heartbeat()`/`focus_pause()`/`focus_end()`/
`presence()`/`ClientConfig.for_repository()`), `credentials.py` (local
storage primitive: `store()`/`load()`/`revoke()`), `repo_identity.py`
(`Deadline`, `repo_name()`, `branch_name()`, `commit_oid()`, `identity()` —
landed by Z6-C, NOT a literal port of `zeitgeist/integrations/
repo_identity.py`; see its module docstring for the deliberate divergence:
no directory-basename fallback, fail-closed on ambiguity).

## Not yet implemented

1. **`validator.py` + bundled schemas + `DIGESTS.json`** — blocked on F1-T1
   and F3-T1 landing as producer candidates in `spec-kitty-events` /
   `zeitgeist` (no real JSON Schema files or `registry_digest()` /
   `support_matrix_digest()` exist yet to pin against). Until this lands,
   `ZeitgeistClient.offer()` performs only the sanitizer gate, not the
   schema-validation gate.
2. **`ZeitgeistClient.status()` / `.watch()`** — both raise
   `NotImplementedError`; both depend on `validator.py` above (no LiveFrame
   streaming, no version-skew or unknown-kind rejection yet).
3. **`mcp_stdio.py`** — the stdio MCP adapter (FastMCP-based). No CLI/MCP
   parity coverage, no SDK/protocol interop test. The `mcp` dependency has not
   been added to `pyproject.toml` — nothing needs it yet.
4. **CLI adapter** — `src/specify_cli/cli/commands/zeitgeist.py` (a
   `status`/`watch`/`checkout`/`focus` sub-group plus a hidden `mcp-serve`
   command) and its registration in `cli/commands/__init__.py`.
5. **`checkout`/auth network half** — `spec-kitty zeitgeist checkout
   <relay-url>` (health-reachability probe + canary `offer`, per
   `install.py`'s `cmd_verify` precedent). `credentials.py`'s storage
   primitive is implemented and tested; nothing calls it from a CLI flow yet.
   `repo_identity.identity()` (landed, Z6-C) is what this future CLI flow
   should call to get the canonical `repo` key to store against — tests use
   a literal `"spec-kitty"` string today because no CLI flow exists to wire
   it through yet, not because the derivation is missing.
6. **Harness-asset staging** — `.mcp.json` companion asset, the
   `ClaudeCodeHookRegistrar` `PostToolUse` event-constant extension, per-harness
   hook re-homing under `zeitgeist_client/assets/hooks/<harness>/`, and
   `tool_surface.repair` registration.
7. **`CHANGELOG.md` entry and `docs/zeitgeist-client.md`** — not written.

See the module docstrings of `transport.py` and `credentials.py` for the
specific contract clauses each gap corresponds to.
