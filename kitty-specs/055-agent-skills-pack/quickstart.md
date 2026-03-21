# Quickstart: Agent Skills Pack

**Feature**: 055-agent-skills-pack

## For Users

### Fresh Project

```bash
spec-kitty init my-project --ai=claude,codex
```

After init, your project has:
- `.claude/skills/spec-kitty-setup-doctor/SKILL.md` (native-root skill)
- `.agents/skills/spec-kitty-setup-doctor/SKILL.md` (shared-root skill for codex)
- `.claude/commands/spec-kitty.*.md` (wrappers, unchanged)
- `.codex/prompts/spec-kitty.*.md` (wrappers, unchanged)
- `.kittify/skills-manifest.json` (tracks all installed skill files)

### Verify Installed Skills

```bash
spec-kitty verify
```

Reports: installed skills, missing files, drifted files.

### Repair Drifted Skills

```bash
spec-kitty init --here
```

Re-initializes the project in place, restoring missing or modified managed skill files from canonical source.

## For Contributors

### Adding a New Skill

1. Create directory: `src/doctrine/skills/<skill-name>/`
2. Write `SKILL.md` with frontmatter:
   ```yaml
   ---
   name: spec-kitty-my-skill
   description: "Brief description with trigger phrases and negative scope"
   ---
   ```
3. Add optional subdirectories: `references/`, `scripts/`, `assets/`
4. The skill is automatically discovered and distributed by init

### Skill Authoring Rules (from PRD)

- Keep `SKILL.md` concise; move long guidance to `references/`
- Use scripts only for deterministic checks or repairs
- Frontmatter: `name` and `description` only
- Description must include positive trigger phrases AND negative scope boundaries
- No repo-specific absolute paths
- No internal-only assumptions
