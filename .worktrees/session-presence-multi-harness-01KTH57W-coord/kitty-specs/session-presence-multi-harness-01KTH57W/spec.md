# Session Presence Multi-Harness Orientation

**Mission ID:** 01KTH57W8EWXDH8TCHNP485YMS
**Mission slug:** session-presence-multi-harness-01KTH57W
**Mission type:** software-dev
**Status:** Proposed

## Purpose

After `spec-kitty init`, every configured AI agent operates blind — it has no awareness that Spec Kitty exists, what it does, or how to route a user request like "hey spec kitty, fix X" to the correct command. This mission injects an orientation block into each agent's native config files so that, from the first session after init, agents know how to use Spec Kitty without any manual setup by the user.

The work is delivered in two phases. Phase 1 (issue #1760) establishes the shared `session_presence` package and covers Claude Code exclusively — it must ship first because Phase 2 builds on its foundation. Phase 2 (issue #1761) extends coverage to all remaining configured harnesses (up to 18 additional agents) using the writer abstraction introduced in Phase 1.

## Domain Language

| Canonical term | Meaning | Synonyms to avoid |
|---|---|---|
| session presence | The state in which a Spec Kitty orientation block is installed in an agent's config | "injection", "setup" |
| orientation block | The rendered text placed inside an agent's config file, bounded by `<!-- spec-kitty:orientation -->` markers | "section", "snippet" |
| harness | A specific AI agent integration (Claude Code, Cursor, Copilot, etc.) | "agent", "tool" (ambiguous) |
| Pattern A/B/C/D/E | Harness classification by how orientation is written | — |
| session-start | The CLI command invoked by Claude Code's SessionStart hook | — |

## Functional Requirements

### Phase 1 — Foundation and Claude Code (issue #1760)

| ID | Description | Status |
|---|---|---|
| FR-001 | When `spec-kitty init` is run, it writes a Spec Kitty orientation block to the Claude Code rules file (`.claude/CLAUDE.md`). The block is bounded by idempotency markers so a second `init` or `upgrade` run never creates a duplicate. | Proposed |
| FR-002 | When `spec-kitty init` is run, it registers `spec-kitty session-start` as a `SessionStart` hook entry in the Claude Code settings file (`.claude/settings.json`). Only the spec-kitty entry is added; all pre-existing hook entries are preserved. | Proposed |
| FR-003 | The `spec-kitty session-start` command, when invoked inside a spec-kitty project, emits an orientation message to stdout containing: the installed version, the project slug, the project health state (`healthy`, `upgrade-available`, or `migration-required`), two usage patterns (full mission and lightweight dispatch), and an optional upgrade warning when a newer version is available. | Proposed |
| FR-004 | The `spec-kitty session-start` command emits no output when invoked outside a spec-kitty project (no `.kittify/` directory reachable from the working directory). | Proposed |
| FR-005 | The `spec-kitty session-start` command exits with code 0 on all code paths, including all exception conditions. | Proposed |
| FR-006 | The PyPI version check result is cached locally with a one-hour TTL. When the cache is valid, no network call is made during `session-start`. When the cache is stale or missing, the refresh runs as a background process that does not block `session-start` completion; the most recently cached value (which may be `None` on first run) is used for the current invocation. | Proposed |
| FR-007 | An upgrade migration is shipped alongside Phase 1 that detects existing Claude Code projects lacking session presence and backfills both the orientation block in `.claude/CLAUDE.md` and the `SessionStart` hook in `.claude/settings.json` when `spec-kitty upgrade` is run. | Proposed |
| FR-008 | Running `spec-kitty init` or `spec-kitty upgrade` twice on the same Claude Code project produces no duplicate orientation blocks and no duplicate hook entries. | Proposed |
| FR-009 | A `Writer` protocol and a `NullWriter` fallback are defined in Phase 1 so that Phase 2 harnesses can be added to the writer registry without modifying Phase 1 internals. | Proposed |

### Phase 2 — All Remaining Harnesses (issue #1761, depends on FR-001 through FR-009)

| ID | Description | Status |
|---|---|---|
| FR-010 | `spec-kitty init` installs an orientation block for each Pattern B harness configured in the project: Cursor, Windsurf, GitHub Copilot, Roo, Kiro, and Gemini. Each block is written to that harness's native rules or instructions file and is bounded by the same idempotency markers. | Proposed |
| FR-011 | `spec-kitty init` installs an orientation block for each Pattern C harness configured in the project: Codex, OpenCode, and Google Antigravity. These three harnesses share `AGENTS.md` at the project root as their orientation target. | Proposed |
| FR-012 | `spec-kitty init` installs an orientation block for each Pattern D harness configured in the project: Pi, Vibe, and Letta. Orientation is injected into the skills preamble or `AGENTS.md` as appropriate per harness. | Proposed |
| FR-013 | Pattern E harnesses (Qwen, Kilocode, Augment Code, Amazon Q) that do not yet have a known orientation mechanism are handled by a `NullWriter`: no orientation is written and no error is raised. | Proposed |
| FR-014 | `spec-kitty init` installs orientation for all configured harnesses in a single invocation — one command covers Claude Code through all Pattern B/C/D harnesses. | Proposed |
| FR-015 | An upgrade migration is shipped alongside Phase 2 that detects existing projects where one or more non-Claude harnesses are configured but lack session presence, and backfills orientation for all such harnesses when `spec-kitty upgrade` is run. | Proposed |
| FR-016 | Running `spec-kitty init` or `spec-kitty upgrade` twice on the same project produces no duplicate orientation blocks on any Pattern B, C, or D harness. | Proposed |
| FR-017 | When a Pattern E harness is resolved in future work and its writer is registered, the Phase 2 upgrade migration's detection logic naturally picks it up without requiring a new migration. | Proposed |

## Non-Functional Requirements

| ID | Description | Threshold | Status |
|---|---|---|---|
| NFR-001 | `spec-kitty session-start` must complete quickly enough to not noticeably delay Claude Code session startup. | Under 200ms on a warm local filesystem | Proposed |
| NFR-002 | The version upgrade check must never block foreground execution. | Background refresh only; zero network calls on the `session-start` hot path | Proposed |
| NFR-003 | All orientation file writes are atomic so a crash mid-write cannot leave a config file in a corrupt state. | Write to temp file in same directory, then rename; no partial writes observable | Proposed |
| NFR-004 | All new code introduced in both phases passes the project's static analysis and type checking gates. | Zero ruff issues, zero mypy issues (mypy --strict), no suppression directives added | Proposed |

## Constraints

| ID | Description | Status |
|---|---|---|
| C-001 | Phase 2 implementation cannot begin until Phase 1 is merged. All Phase 2 writers depend on the `Writer` protocol, `MarkdownRulesWriter`, `NullWriter`, `SessionPresenceContent`, and `SessionPresenceManager` introduced in Phase 1. | Proposed |
| C-002 | When unregistering the spec-kitty `SessionStart` hook, only the spec-kitty entry is removed. All other `SessionStart` hook entries in `.claude/settings.json` must be preserved. | Proposed |
| C-003 | Orientation blocks are bounded by `<!-- spec-kitty:orientation -->` and `<!-- /spec-kitty:orientation -->` markers in all harnesses that support Markdown rules files. These markers are the sole idempotency signal — no other mechanism is used to detect existing presence. | Proposed |
| C-004 | The `session_presence` package must not import from `src/specify_cli/next/` (the deprecated shim). All imports must respect the shared package boundary established in the 3.x architecture. | Proposed |
| C-005 | The upgrade migration for Phase 2 uses `get_agent_dirs_for_project()` to enumerate configured agents. It must not hardcode the full list of 19 agents, must not create agent directories that do not exist, and must not process agents absent from `.kittify/config.yaml`. | Proposed |

## User Scenarios & Testing

### Scenario 1 — New project init (Claude Code)
A developer runs `spec-kitty init --ai claude` in a new repository. After init completes, `.claude/CLAUDE.md` contains an orientation block explaining what Spec Kitty is and how to trigger a mission or a lightweight dispatch. `.claude/settings.json` contains a `SessionStart` hook entry for `spec-kitty session-start`. The next time Claude Code is opened in this project, the hook fires, the orientation is echoed, and Claude is aware of Spec Kitty immediately.

### Scenario 2 — Session start fires
Claude Code's `SessionStart` hook invokes `spec-kitty session-start`. The command prints the installed version, the project slug, the health state (`healthy`), and the two usage patterns. It completes and exits 0. The developer sees the orientation in the session context.

### Scenario 3 — Upgrade available
The cache records a newer PyPI version. `spec-kitty session-start` includes an upgrade warning line in the orientation output alongside the normal content. The developer sees "⚠ Upgrade available: X.Y.Z".

### Scenario 4 — Migration required
`spec-kitty session-start` detects the project needs a migration. The orientation output includes a warning directing the developer to run `spec-kitty upgrade` before using missions. The command still exits 0.

### Scenario 5 — Invoked outside a spec-kitty project
`spec-kitty session-start` is invoked in a directory with no `.kittify/` ancestor. It emits no output and exits 0. No error is shown.

### Scenario 6 — Idempotent re-init
A developer runs `spec-kitty init` a second time (or `spec-kitty upgrade`). Both `.claude/CLAUDE.md` and `.claude/settings.json` contain exactly the same content as after the first run — no duplicate sections, no duplicate hook entries.

### Scenario 7 — Multi-harness init (Phase 2)
A developer runs `spec-kitty init` on a project configured for Claude Code, Cursor, GitHub Copilot, and Codex. After init: `.claude/CLAUDE.md` has the orientation block, `.cursor/rules/spec-kitty.mdc` exists with orientation, `.github/copilot-instructions.md` has the orientation section appended, and `AGENTS.md` contains the orientation block. All four are bounded by the same markers.

### Scenario 8 — Upgrade backfills existing project (Phase 2)
An existing project was initialized before session presence existed. The developer runs `spec-kitty upgrade`. The migration detects which configured harnesses are missing orientation and writes it to each one. Harnesses that already have orientation are skipped.

### Scenario 9 — NullWriter harness
A project is configured for Amazon Q (`q`). `spec-kitty init` runs, reaches the `q` harness, finds a `NullWriter`, writes nothing, logs a debug message, and continues without error.

## Success Criteria

1. 100% of configured harnesses with a known writer receive an orientation block after `spec-kitty init` — zero manual steps required by the user.
2. Claude Code sessions in spec-kitty projects begin with Spec Kitty orientation visible in context within 200ms of session start.
3. Running `spec-kitty init` or `spec-kitty upgrade` any number of times produces no duplicate content in any agent config file.
4. Existing projects gain orientation for all resolvable harnesses after a single `spec-kitty upgrade` invocation — no manual migration steps needed.
5. `spec-kitty session-start` never causes a Claude Code session to fail or show an error — exit 0 on every code path.

## Key Entities

| Entity | Description |
|---|---|
| `SessionPresenceContent` | Value object: version, project slug, health state, available version. Renders the orientation text string. |
| `Writer` (protocol) | Interface defining `can_write`, `has_presence`, `write`, and `remove` for a single harness. |
| `SessionPresenceManager` | Orchestrates `install` and `update` across all configured harnesses; builds `SessionPresenceContent`; delegates to individual writers. |
| `UpgradeChecker` | Manages the PyPI version check cache; fires background refresh; never blocks or raises. |
| `MarkdownRulesWriter` | Concrete `Writer` for any harness whose orientation target is a Markdown file; handles both append-mode (section within existing file) and own-file mode. |
| `ClaudeCodeWriter` | Extends `MarkdownRulesWriter` for Claude Code; additionally manages the `SessionStart` hook in `.claude/settings.json`. |
| `AgentsMdWriter` | Concrete `Writer` for harnesses that share `AGENTS.md` at project root (Pattern C). |
| `SkillsPreambleWriter` | Concrete `Writer` for skills-based harnesses (Pattern D). |
| `NullWriter` | No-op `Writer` for harnesses with no known orientation mechanism (Pattern E). |
| Upgrade migration (Phase 1) | Detects and backfills Claude Code session presence for existing projects. |
| Upgrade migration (Phase 2) | Detects and backfills session presence for all non-Claude harnesses on existing projects. |

## Assumptions

- `spec-kitty do "<request>"` referenced in the orientation text is an existing or separately-planned command. This mission only renders the routing instruction — it does not implement `spec-kitty do`.
- Pattern D harness behavior (Pi, Vibe, Letta) defaults to AGENTS.md injection where the skills preamble path is not definitively resolved; research notes (`architecture/3.x/research/session-presence-harness-gaps.md`) document the open questions.
- The one-hour TTL for the PyPI version cache is sufficient to balance freshness with performance; no user-configurable TTL is needed in this mission.
- All 19 harnesses are addressed either by a real writer or by an explicit `NullWriter` entry — no harness is silently skipped.

## Out of Scope

- Implementing `spec-kitty do` — the orientation text references it but this mission does not build it.
- Resolving Pattern E harnesses (Qwen, Kilocode, Augment Code, Amazon Q) beyond `NullWriter` stubs — follow-on work tracked in research notes.
- SaaS sync of session presence state — all operations are local-only.
- User-configurable orientation content or TTL settings.
