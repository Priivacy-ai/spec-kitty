# Research: Agent Harness Install Audit Follow-Through

*Phase 0 output — 2026-06-03*

---

## FR-001–006: Stale Codex Path Inventory

**Decision**: Update or remove stale `.codex/` references file-by-file per the rules below.
**Rationale**: The current Codex command skill install location is `.agents/skills/spec-kitty.<command>/SKILL.md`. References to `.codex/prompts/`, `.codex/skills/`, and `CODEX_HOME=$(pwd)/.codex` as active install guidance are incorrect and send users to a retired path.
**Alternatives considered**: A single global search-and-replace. Rejected because some occurrences are in historical/planning docs that should not be rewritten.

### Confirmed occurrence inventory (from grep 2026-06-03)

| File | Line(s) | Stale content | Action |
|------|---------|---------------|--------|
| `docs/explanation/ai-agent-architecture.md` | 49 | Table row: `GitHub Codex \| .codex/prompts/ \| Markdown` | Update table row to `.agents/skills/` |
| `docs/development/3-2-information-architecture.md` | 117 | Planning doc mentions `.codex/prompts/` in a rewrite-target note | Preserve as historical — mark or leave as-is |
| `docs/how-to/setup-codex-spec-kitty-launcher.md` | 10, 56, 97, 128 | Entire file explains the retired `.codex/` Codex launcher setup with `CODEX_HOME` | Major rework: rewrite to describe current `.agents/skills/` model and `$spec-kitty.<command>` invocation; or redirect to `docs/how-to/harnesses/codex.md` |
| `docs/how-to/upgrade-project.md` | 55 | `.codex/skills/` listed alongside active agent dirs | Replace with `.agents/skills/` |
| `docs/reference/upgrade-lifecycle.md` | 44 | `.codex/skills/spec-kitty.*/` listed as refresh target | Replace with `.agents/skills/spec-kitty.*/` |
| `docs/reference/environment-variables.md` | 241, 249, 282 | `CODEX_HOME` section documents `$(pwd)/.codex` as the correct value | Update section: document that Codex command skills no longer require `CODEX_HOME`; the correct path is `.agents/skills/spec-kitty.<command>/SKILL.md` |
| `docs/reference/supported-agents.md` | 195, 197, 388, 390 | `CODEX_HOME=$(pwd)/.codex` guidance in two places | Same as environment-variables.md update |

**Canonical replacement guidance (for implementer)**:
- Old Codex install path: `.codex/prompts/` or `.codex/skills/` or `CODEX_HOME=$(pwd)/.codex`
- New canonical path: `.agents/skills/spec-kitty.<command>/SKILL.md`
- Invocation syntax: `$spec-kitty.<command>` (not `@codex prompts:spec-kitty.*`)
- Exception: Historical/planning documents (changelog, IA planning docs) may retain stale paths if clearly labeled. Active how-to and reference docs must not.

---

## FR-007–008: Snapshot Drift Analysis

**Decision**: The canonical wording for WP lifecycle dependency gates is `approved or done`.
**Rationale**: The status model (`src/specify_cli/status/transitions.py`, documented in `CLAUDE.md`) explicitly states the dependency gate is satisfied when a WP reaches `approved` **or** `done`. The snapshot drift in `codex-implement` and `vibe-implement` shows `approved or done` vs `done` — the former is correct.
**Alternatives considered**: Using `done`-only. Rejected: this would create a deadlock for same-mission dependency chains (as documented in CLAUDE.md: "Gating strictly on `done` would ... deadlock every same-mission dependency chain").

### Snapshot resolution steps (for implementer)

1. Run `uv run pytest tests/specify_cli/skills/test_command_renderer.py -x 2>&1` to observe current failures.
2. Locate snapshot files for `codex-implement` and `vibe-implement` (likely under `tests/specify_cli/skills/snapshots/` or an equivalent `__snapshots__` directory).
3. Update snapshots to use `approved or done` wording if the source templates are correct, or update the source templates first if they contain the stale `done`-only wording.
4. Re-run the full suite to confirm all 102 tests pass.

---

## FR-009–010: Antigravity Install Surface Spike

**Decision**: Must verify via live CLI access or current upstream docs before updating `docs/reference/supported-harnesses.md`.
**Current modeling in spec-kitty**:
- Command/workflow surface: `.agent/workflows/`
- Possible skill surface: `.agent/skills/` plus shared `.agents/skills/`
- No `docs/how-to/harnesses/antigravity.md` exists yet
- `docs/reference/supported-agents.md` mentions Antigravity at `~/.agent/` (line 22 in grep output)

**Verification tasks (for implementer)**:
1. Access Antigravity CLI: check `agent --help`, `agent plugin`, `agent config`, `agent skills` or equivalent subcommands.
2. Identify: global vs workspace config dirs, manifest file format (if any), whether `.agent/workflows/` and `.agent/skills/` are workspace-local or global.
3. Verify a smoke test: can a Spec Kitty command be invoked from Antigravity using an installed skill?
4. If verified: update `docs/reference/supported-harnesses.md` with confirmed install targets and create `docs/how-to/harnesses/antigravity.md` with a minimal setup guide.
5. If unverified / CLI unavailable: update `docs/reference/supported-harnesses.md` with an explicit "Not yet verified (2026-06-03 audit)" note.

**Scope constraint**: No changes to `src/specify_cli/core/config.py`. Plugin-install implementation deferred to 3.3.x (#1635).

---

## FR-011–012: Kiro Plugin/Powers Surface Research

**Decision**: Must verify whether Kiro has a plugin or Powers bundle primitive before classifying it.
**Current Kiro status in spec-kitty**:
- `docs/how-to/harnesses/kiro.md` exists: describes Kiro as "bootstrap-only" with prompt-file mechanism at `.kiro/prompts/`
- `docs/reference/supported-harnesses.md` is referenced from `kiro.md` and both exist
- No plugin-bundle surface verified as of 2026-06-03 audit
- Kiro is the Amazon Q rebrand; currently modeled like Amazon Q (prompt/hook/MCP)

**Verification tasks (for implementer)**:
1. Review `https://kiro.dev/docs` for: `Powers`, extensions, plugins, MCP packaging, or bundle/manifest primitives.
2. Determine if any Kiro primitive can bundle prompts + hooks + MCP config + skills into one installable package.
3. If yes: document manifest/package shape and install locations; update classification to plugin-candidate.
4. If no: update `docs/reference/supported-harnesses.md` and `docs/how-to/harnesses/kiro.md` to explicitly state Kiro is prompt/hook/MCP-only and out of #1635 scope for 3.3.

**Expected outcome**: Either a promotion to plugin candidate (unlikely given current evidence) or a clear "prompt-based only, not in #1635 scope" record — resolving the open classification ambiguity.
