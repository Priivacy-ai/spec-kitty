# Quickstart: Using Spec Kitty with Mistral Vibe (and Modernized Codex)

**Feature**: 083-agent-skills-codex-vibe
**Audience**: developers trying Spec Kitty with Vibe for the first time, and existing Codex users upgrading to the next release.

## Scenario 1: New Vibe user onboards

**Prerequisites**: Mistral Vibe installed (`curl -LsSf https://mistral.ai/vibe/install.sh | bash` or `uv tool install mistral-vibe`), Spec Kitty CLI installed, an empty project directory.

```bash
cd my-new-project
spec-kitty init --ai vibe --non-interactive
```

Expected output:

- `.kittify/config.yaml` is written with `agents.available: [vibe]`.
- `.agents/skills/spec-kitty.<command>/SKILL.md` is generated for every canonical command (`specify`, `plan`, `tasks`, `implement`, `review`, `merge`, etc.).
- `.kittify/skills-manifest.json` records each file with its hash and the agent (`vibe`) that installed it.
- `.gitignore` gains a stanza protecting project-local `.vibe/` runtime state.
- Printed next steps tell you to launch Vibe in the project and invoke `/spec-kitty.specify`.

Verify:

```bash
spec-kitty verify-setup --check-tools
```

`vibe` should appear in the tool-detection output with a green checkmark and the resolved binary path.

Launch Vibe and try it:

```bash
vibe
# inside Vibe's TUI:
/spec-kitty.specify "build a small URL shortener"
```

Vibe auto-completes `/spec-kitty.specify` from its skills menu. The invocation's free-form text (`"build a small URL shortener"`) is delivered to the skill body as turn content; the workflow reads it as User Input and proceeds to create the mission specification exactly as a Claude Code user would see.

## Scenario 2: Existing Codex user upgrades

**Prerequisites**: a project previously initialized with a pre-083 Spec Kitty release via `spec-kitty init --ai codex`, Spec Kitty CLI updated to the release containing this feature.

```bash
cd my-existing-project
spec-kitty upgrade
```

What happens:

- The upgrade migration enumerates `spec-kitty.*.md` files under `.codex/prompts/`.
- For each file, it compares the current content hash to the hash the previous Spec Kitty release's renderer would have produced.
- Files that match (unedited) are deleted after the equivalent Agent Skills package is installed under `.agents/skills/spec-kitty.<command>/`.
- Files that do not match (you edited them by hand) are **preserved** and surfaced in a notice: *"Preserved user-edited files in .codex/prompts/: <list>. Your Codex integration now reads from .agents/skills/; review and port your edits if still needed."*
- Non-Spec-Kitty files in `.codex/prompts/` (if any) are left untouched.
- `.kittify/skills-manifest.json` now records the new skill packages with `agents: ["codex"]`.

Verify:

```bash
spec-kitty verify-setup
```

Codex should report as healthy and served from `.agents/skills/`.

Launch Codex and try it:

```bash
codex
# inside Codex's TUI:
/skills
```

`spec-kitty.specify`, `spec-kitty.plan`, `spec-kitty.tasks`, and the others appear. Invoking one via `$spec-kitty.specify "build an app"` or `/spec-kitty.specify build an app` runs the same workflow body the Claude Code user sees.

## Scenario 3: Both Codex and Vibe configured in one project

```bash
spec-kitty agent config add codex vibe
spec-kitty agent config status
```

- Each canonical command's skill package under `.agents/skills/spec-kitty.<command>/` is installed once, with `agents: ["codex", "vibe"]` in the manifest.
- On-disk content is identical regardless of which agent was added first.
- Third-party files under `.agents/skills/` (authored by you or installed by another tool) are untouched.

Remove one agent:

```bash
spec-kitty agent config remove codex
```

- `codex` is dropped from every manifest entry's `agents` array.
- Skill packages still needed by `vibe` remain on disk unchanged.
- Third-party files remain byte-identical.

## Scenario 4: Repairing a broken install

If the `.agents/skills/` directory has been mutated out of band (a file edited by hand, a directory deleted, a skill package from a third-party tool renamed to collide with ours):

```bash
spec-kitty doctor
```

The doctor surfaces:

- Manifest entries whose on-disk hash no longer matches the recorded hash → drift.
- Files under `.agents/skills/spec-kitty.*/` that are not in the manifest → orphans.
- Missing files that the manifest says should exist → gaps.

Fix by re-running:

```bash
spec-kitty agent config sync
```

which reinstalls missing or drifted Spec-Kitty-owned skill packages without touching anything else.

## What to expect inside each agent's TUI

| Agent | How you see `/spec-kitty.*` | How arguments reach the workflow |
|-------|---------------------------|----------------------------------|
| **Vibe** | Slash-command autocomplete menu shows all `spec-kitty.*` entries alongside built-ins | Text you type after `/spec-kitty.<command> ...` becomes the invocation turn's content; the skill body reads it as User Input |
| **Codex** | `$spec-kitty.<command>` or `/skills` shows the full list | Text you type after `$spec-kitty.<command> ...` becomes the invocation turn's content; same semantics as Vibe |
| **Claude, Gemini, Cursor, opencode, Copilot, Qwen, Windsurf, Kilocode, Auggie, Roo, Q, Antigravity** | Slash-command autocomplete from the agent's own command directory (unchanged from earlier releases) | Text you type after the command is substituted into the template body at `$ARGUMENTS` / `{{args}}` placement (unchanged from earlier releases) |

This split is intentional and documented in `research.md`. The twelve command-layer agents keep their existing, well-tested pipeline; Codex and Vibe — neither of which has a viable command-layer path for us — use the new Agent Skills pipeline with turn-content-based argument delivery.

## Troubleshooting

- **`spec-kitty init --ai vibe` succeeds but `verify-setup` says `vibe` is missing.** Init does not require Vibe at install time. Install Vibe from the official channel, then re-run `verify-setup`.
- **`spec-kitty.*` does not appear in Vibe's autocomplete.** Check `.agents/skills/` exists and contains the `spec-kitty.<command>/SKILL.md` files. Run `spec-kitty doctor`. If the manifest is present but files are missing, run `spec-kitty agent config sync`.
- **After upgrade, some of my `.codex/prompts/spec-kitty.*.md` files are still there.** The migration preserves files whose content differs from the previous Spec Kitty release's output, interpreting those as user edits. The preserved paths are printed at upgrade time. Port the edits into `.agents/skills/spec-kitty.<command>/SKILL.md` if still needed.
- **A third-party tool complains that `.agents/skills/` changed.** Spec Kitty only ever writes and deletes files it owns (tracked in `.kittify/skills-manifest.json`). If a third-party file was affected, it's a bug — open an issue with the repro.
