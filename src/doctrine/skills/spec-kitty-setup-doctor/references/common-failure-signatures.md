# Common Failure Signatures

Known failure patterns for Spec Kitty 2.0.11+ installations with deterministic
recovery steps.

---

## 1. Missing Skill Root

**Symptom:** Agent cannot find skills; `spec-kitty verify` reports missing skill
files. Slash commands that reference skills fail with "skill not found" or
similar errors.

**Cause:** `spec-kitty init` was run before the skill pack was available, or the
skill root directory was manually deleted.

**Recovery:**

```bash
spec-kitty sync --repair-skills
```

If the skill root directory is entirely absent, re-initialize:

```bash
spec-kitty init --here
```

---

## 2. Missing Wrapper Root

**Symptom:** Slash commands (e.g., `/spec-kitty.implement`) are not found by the
agent. The agent does not recognize any `spec-kitty.*` commands.

**Cause:** The agent's wrapper directory was deleted, or `spec-kitty init` was
interrupted before wrapper files were written.

**Recovery:**

```bash
spec-kitty init --here
```

This regenerates wrapper files for all configured agents.

---

## 3. Manifest Drift

**Symptom:** `spec-kitty verify` reports drifted skill files. The hash of one or
more installed files does not match the manifest.

**Cause:** Managed skill files were manually edited after installation. This is
expected if a user intentionally customized a skill file, but may also indicate
accidental edits or merge conflicts.

**Recovery:**

```bash
spec-kitty sync --repair-skills
```

This overwrites drifted files with canonical content from the skill registry and
updates manifest hashes. Any local edits will be lost.

---

## 4. Runtime Not Found

**Symptom:** "next is blocked", "runtime can't find missions", or
`spec-kitty status` reports that `.kittify/` is missing.

**Cause:** The `.kittify/` directory was deleted, the repository was freshly
cloned without running init, or the user is in a subdirectory.

**Recovery:**

1. Ensure you are in the repository root:
   ```bash
   cd "$(git rev-parse --show-toplevel)"
   ```

2. Re-initialize:
   ```bash
   spec-kitty init --here
   ```

---

## 5. Dashboard Not Starting

**Symptom:** Dashboard URL is not accessible after initialization. Browser shows
connection refused or timeout.

**Cause:** Port conflict with another process, dashboard process crashed, or the
dashboard was never started.

**Recovery:**

```bash
spec-kitty dashboard
```

If the port is in use, the dashboard will report the conflict. Stop the
conflicting process or let the dashboard auto-select an available port.

---

## 6. Stale Agent Configuration

**Symptom:** `spec-kitty agent config status` shows orphaned agent directories
(directories exist on disk but are not listed in `config.yaml`), or configured
agents are missing their directories.

**Cause:** Agents were added or removed by manually editing the filesystem
instead of using `spec-kitty agent config add/remove` commands.

**Recovery:**

```bash
# Check current state
spec-kitty agent config status

# Sync filesystem with config (removes orphaned, creates missing)
spec-kitty agent config sync
```

---

## 7. Corrupted Config File

**Symptom:** `spec-kitty` commands fail with YAML parse errors referencing
`.kittify/config.yaml`.

**Cause:** The config file was manually edited and contains invalid YAML, or a
write was interrupted mid-operation.

**Recovery:**

1. Back up the corrupted file:
   ```bash
   cp .kittify/config.yaml .kittify/config.yaml.bak
   ```

2. Remove and re-initialize:
   ```bash
   rm .kittify/config.yaml
   spec-kitty init --here
   ```

3. Restore any custom settings from the backup if needed.

---

## 8. Worktree Linkage Broken

**Symptom:** `spec-kitty implement` fails with "worktree not found" or git
reports detached worktree references.

**Cause:** A worktree directory was moved or deleted without using
`git worktree remove`. The `.git/worktrees/` metadata is stale.

**Recovery:**

```bash
# List current worktrees
git worktree list

# Prune stale worktree references
git worktree prune

# Re-create the worktree if needed
spec-kitty implement WP01
```
