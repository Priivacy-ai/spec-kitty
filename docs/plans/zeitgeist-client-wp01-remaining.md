# zeitgeist_client WP01 — remaining scope

Status note for `src/specify_cli/zeitgeist_client/` (Bead `Z1-T1`). This is the
committed source of truth that in-code comments and error messages point to
for "what's left in WP01" — mirrors the ordered task list from the Z1
drafting note (`Z1.md §5`, an out-of-repo scratchpad draft, items 2-6), kept
current in this repo instead of in a document that never lands here.

Landed so far: `grammar.py`, `sanitizer.py`, `budget.py`, `transport.py`
(`offer()`/`focus_start()`/`focus_heartbeat()`/`focus_pause()`/`focus_end()`/
`presence()`), `credentials.py` (local storage primitive: `store()`/`load()`/
`revoke()`).

**Z4-C** (a separate Bead, branched from this WP01 base at `afa4020d`) added
`live_frame.py` (pure `LiveFrame` parsing + `StreamState`: gap/epoch/revoke
handling via full local-state reset, <=90s TTL clamp enforced client-side
regardless of what a relay sends, closed `focus.state=="ended"` signals
dropped rather than queued) and `filtered_stream.py`
(`FilteredStream.watch()`/`.check()`/`.current_focus()` — one SSE
subscription per team-bound `X-Zeitgeist-Capability` credential against F3's
managed-runtime `GET /managed/stream`, landed separately by Z3-T1 in the
`zeitgeist` repo). This does **not** resolve item 1/2 below: Z4-C's own
frame parsing is a deliberately narrower, hand-checked shape gate (exactly
the fields `StreamState` reads), not a general JSON-Schema validator run
against a bundled/pinned `managed_live.schema.json` — `ZeitgeistClient.
watch()`/`.status()` on `transport.py` are untouched by Z4-C and still raise
`NotImplementedError`; Z4-C's surfaces live on the new
`filtered_stream.FilteredStream` class instead, deliberately not folded into
`transport.ZeitgeistClient` (see `zeitgeist_client/__init__.py`'s module
docstring for why the two stay independent).

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
   Also not ported: `repo_identity.py` (`Deadline`, `repo_name`,
   `branch_name`, `identity()`) for deriving the canonical `repo` key
   `credentials.py` stores against — tests use a literal `"spec-kitty"`
   string today.
6. **Harness-asset staging** — `.mcp.json` companion asset, the
   `ClaudeCodeHookRegistrar` `PostToolUse` event-constant extension, per-harness
   hook re-homing under `zeitgeist_client/assets/hooks/<harness>/`, and
   `tool_surface.repair` registration.
7. **`CHANGELOG.md` entry and `docs/zeitgeist-client.md`** — not written.
8. **CLI/MCP wiring for Z4-C's `FilteredStream`** — the `status`/`watch`
   CLI sub-group in item 4 above and the stdio MCP adapter in item 3 above
   should eventually call `filtered_stream.FilteredStream`, once they exist;
   Z4-C landed only the client-library surfaces it was scoped to
   ("watch/check/current-focus surfaces over Z1 service"), not a CLI/MCP
   adapter. Also not covered by Z4-C: any server-side capability-credential
   issuance flow (Z2a/Z2b's job, not this client's) — a caller must already
   hold a valid `X-Zeitgeist-Capability` token to construct a
   `filtered_stream.TeamStreamConfig`; nothing here mints or requests one.

See the module docstrings of `transport.py`, `credentials.py`,
`live_frame.py`, and `filtered_stream.py` for the specific contract clauses
each gap corresponds to.
