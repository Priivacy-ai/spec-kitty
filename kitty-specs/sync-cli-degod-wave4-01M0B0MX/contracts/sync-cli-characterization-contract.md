# Contract — sync CLI characterization (the frozen behavior)

**Surface**: `spec-kitty sync <subcommand> [flags]` — 22 Typer subcommands. Extends
`kitty-specs/mvp-cli-sync-boundary-completion-01KRX11M/contracts/sync-status-output.md`.

## What is frozen (before any extraction)
For every subcommand: exact **flags**, **exit codes**, and **`--json` envelope shape**. Specifically:
1. `status --check --json` → single JSON, exit 0 (coherent) / exit 2 (incoherent); human block suppressed.
2. `status` (no `--check`) full human-render (the cc-90 build path) — snapshot of the rendered table.
3. `doctor` — takes **no arguments and has no `--json`** (pedro Pd-3): freeze the Rich table + issues list, the "No issues detected. Sync is healthy." vs unhealthy summary, and the `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE` (exit 4) recovery arm.
4. `sync_workspace` — full CLI golden (no existing coverage today; freeze before extraction). Its substantive SYNCED/CONFLICTS/FAILED arms run a live `git rebase` and are non-deterministic, so the golden **stubs `sync.get_vcs` and `sync._detect_workspace_context`** to return fixed `SyncResult`s (a monkeypatch-golden, not a black-box snapshot); pin the capture encoding for the emoji glyphs.
5. `now` — `--strict` exits, preflight exit 2, unauthenticated exit 1, `EXIT_LOGGED_OUT_ON_CONNECTED_TEAMSPACE`.
6. `diagnose` — `--json` shapes `{available:false,…}` exit 2 / `{total:0,…}` / full `{total,valid,invalid,results:[…]}` (the full-report arm needs a fixed event fixture).
7. The **coord exit-0 silent-skip** arm (SaaS-disabled guard: print-disabled + `return`/`Exit(0)`) — preserved exactly.

## Contract rules (given → then)
1. **Freeze-first**: for each of {`status`, `doctor`, `sync_workspace`, `diagnose`}, the human-render + every `--json` branch snapshot exists and is green **before** that function's extraction WP begins. A `--json`-happy-path-only freeze does not satisfy this.
2. **Behavior-stable**: any extraction commit keeps every golden snapshot green (INV-1).
3. **Seam co-gate**: the ~60 `sync`-monkeypatch tests pass green after each relocation (INV-4).
4. **Two-authority**: `tests/architectural/test_sync_two_authority.py` asserts distinct read/write port symbols, no shared authority class (INV-2).
5. **No ratchet mutation**: the harness does not grow the DIR-041 positional-anchor allowlists (C-003).
6. **Env set-unchanged**: `docs/plans/code-quality/sync-env-census.md` lists every `SPEC_KITTY_*` ref on the sync surface; a guard confirms the set is unchanged by the mission (FR-007).
