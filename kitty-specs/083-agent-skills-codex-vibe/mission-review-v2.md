# Mission Review Report v2: 083-agent-skills-codex-vibe (post-remediation)

**Reviewer**: Claude Opus 4.6 (mission-review skill, second pass)
**Date**: 2026-04-14T11:30:00Z
**Mission**: `083-agent-skills-codex-vibe` — Agent Skills Support for Codex and Vibe
**Baseline commit**: `1ca0310c` (pre-mission main)
**HEAD at review**: `07b89982` (remediation commit)
**Prior review**: [`mission-review.md`](./mission-review.md) — verdict was **FAIL** (2 CRITICAL, 2 HIGH drifts)

This v2 review verifies the remediation of the v1 findings and performs an
adversarial pass on the remediation itself. A fix that introduces a new
release-blocking regression is a worse outcome than the original defect; the
v1 findings cannot be assumed resolved just because the remediation commit
landed.

---

## v1 finding closure status

| v1 Finding | Severity | Status after `07b89982` | Evidence |
|------------|----------|--------------------------|----------|
| **RISK-1**: no live code path installs vibe's command-skill packages | CRITICAL | **RESOLVED** | `init.py:544-553` now calls `command_installer.install(project_path, agent_key)` for codex/vibe; `agent/config.py:134-148` does the same in `add_agents`. New test `test_init_vibe_installs_command_skills` asserts 11 SKILL.md files + manifest after `init --ai vibe`. Production-shape smoke (tmpdir with no `src/specify_cli/` inside) installs 11 packages + manifest. |
| **RISK-2**: `_resolve_template` used project-relative filesystem path | CRITICAL | **RESOLVED** | `command_installer.py:_package_templates_dir()` derives templates via `Path(specify_cli.__file__).parent / "missions" / ...`. `_resolve_template` takes `repo_root` only for signature symmetry and is marked unused. Smoke test against tmpdir without source symlink: `install(p, "vibe") → added=11, errors=0`. |
| **RISK-3**: dead codex/vibe branch in `_sync_agent_commands` (would have written to `~/.agents/skills/`) | HIGH | **RESOLVED** | Branch removed (`agent_commands.py:119-121` no longer present). Docstring updated to note codex/vibe are driven from init and `agent config add`. `test_sync_does_not_invoke_skill_installer` asserts the installer is never called from `_sync_agent_commands` for any agent in `AGENT_COMMAND_CONFIG`. |
| **RISK-4**: test fixtures symlinked production source tree | HIGH | **RESOLVED** | `test_command_installer.py::repo` fixture no longer creates the `src/specify_cli/missions` symlink; explicit docstring: *"we deliberately do not seed that path here"*. `test_m_3_2_0_codex_to_skills.py::_copy_fixture` likewise stripped. Production templates are now resolved from the installed package. |
| **DRIFT-1**: FR-004 named 16 commands; implementation renders 11 | MEDIUM | **RESOLVED** | `spec.md` FR-004 rewritten to enumerate the actual 11 canonical commands and mark the 5 CLI-only commands (`tasks-finalize`, `accept`, `merge`, `status`, `dashboard`) as explicitly out of scope and tracked as follow-up. Status upgraded from Proposed → Accepted. |
| **DRIFT-2**: FR-012 edge case — user edits silently discarded | HIGH | **RESOLVED** | `m_3_2_0_codex_to_skills.py:287-326` now **moves** owned files into `.codex/prompts.superseded/` instead of deleting them. New `_print_superseded_notice` surfaces every preserved file path to stderr. Smoke: 11 files moved to `prompts.superseded/`, none deleted, idempotent second run leaves state unchanged. |
| **DRIFT-3**: FR-013 literal text required vibe in `AGENT_DIRS` | LOW | **RESOLVED** | `spec.md` FR-013 rewritten to name only the registries that actually apply to skill-only agents (`AI_CHOICES`, `AGENT_SKILL_CONFIG`, `AGENT_TOOL_REQUIREMENTS`) and to state explicitly that `AGENT_DIRS` is command-layer-only. Status upgraded Proposed → Accepted. |
| **DRIFT-4**: FR-015 ADR not delivered to `architecture/adrs/` | HIGH | **RESOLVED** | `architecture/adrs/2026-04-14-2-agent-skills-renderer-for-codex-and-vibe.md` authored (189 lines). Covers context, decision, four alternatives considered with explicit rejections, consequences (positive/negative/security), and implementation references. Discoverable from the repo ADR index. |

All eight v1 findings are closed with cited evidence. 426/426 tests still pass.

---

## NEW findings surfaced by the remediation

### RISK-5: Manifest file path collision between legacy and new installers (CRITICAL, release-blocking)

**Type**: CROSS-WP-INTEGRATION (latent; exposed by wiring `command_installer` into the init flow)
**Severity**: CRITICAL
**Location**: `src/specify_cli/skills/manifest.py:16`, `src/specify_cli/skills/manifest_store.py:61`
**Trigger condition**: Any `spec-kitty init` or `spec-kitty agent config add` invocation that configures both a command-layer agent (claude, gemini, opencode, cursor, qwen, windsurf, kilocode, auggie, roo, copilot, q, antigravity) AND a skill-only agent (codex, vibe).

**Evidence**:

Both modules define the same filename constant and write to the same project-local path:

```
src/specify_cli/skills/manifest.py:16:           MANIFEST_FILENAME = "skills-manifest.json"
src/specify_cli/skills/manifest.py:75:           """Persist the manifest to .kittify/skills-manifest.json."""
src/specify_cli/skills/manifest_store.py:61:     _MANIFEST_FILENAME = "skills-manifest.json"
src/specify_cli/skills/manifest_store.py:192:    """Load the skills manifest from `<repo_root>/.kittify/skills-manifest.json`."""
```

The two manifests have **incompatible schemas**:

| Field | Legacy (`ManagedSkillManifest`) | New (`SkillsManifest`) |
|-------|---------------------------------|------------------------|
| Version key | `version: 1` | `schema_version: 1` |
| Top-level fields | `version`, `created_at`, `updated_at`, `spec_kitty_version`, `entries` | `schema_version`, `entries` |
| Entry fields | `skill_name`, `source_file`, `installed_path`, `installation_class`, `agent_key`, `content_hash`, `installed_at`, `delivery_mode` | `path`, `content_hash`, `agents`, `installed_at`, `spec_kitty_version` |
| Entry `additionalProperties` | (dataclass — silent drop of unknowns) | `false` per `skills-manifest.schema.json` (strict rejection) |

**Empirical reproduction** (using the dev-install venv):

```
After command_installer(vibe):  manifest keys = ['entries', 'schema_version']
After legacy save_manifest:     manifest keys = ['version', 'created_at', 'updated_at', 'spec_kitty_version', 'entries']
New-schema load after collision: FAILED — code=unsupported_schema_version
Subsequent command_installer.install(vibe): FAILED — InstallerError: manifest_parse_failed
```

**Where both writers are invoked in the same init flow**:

1. `init.py:544-553` — for codex/vibe, writes the new manifest via `command_installer.install()`.
2. `init.py:585` — after the per-agent loop, `save_manifest(skill_manifest, project_path)` writes the **legacy** manifest for ALL agents that went through the legacy `install_skills_for_agent` path (claude, gemini, cursor, opencode, windsurf, kilocode, auggie, roo, qwen, copilot, q, antigravity).

The two writes use the same `.kittify/skills-manifest.json` path. Last write wins; the previous write is silently discarded. The loser's data is gone from disk.

**Concrete failure modes**:

- `spec-kitty init --ai claude --ai vibe`: loop order is non-deterministic (dict insertion order). Whichever runs last wipes the other's manifest. A subsequent `spec-kitty agent config remove vibe` will try to load via `manifest_store.load()`, see the legacy `version: 1` key, and raise `ManifestError("unsupported_schema_version")`. The user cannot uninstall vibe.
- `spec-kitty init --ai claude`, then `spec-kitty agent config add vibe`: legacy manifest already exists; `command_installer.install()` in `add_agents` calls `manifest_store.load()` first, which raises `unsupported_schema_version`. Installer returns its error via the `errors` list; vibe is NOT added to config. User sees "Failed to install vibe skills: …" with a schema error they cannot interpret.
- `spec-kitty init --ai vibe`, then later `spec-kitty agent config add claude`: the legacy `save_manifest` in the add-agent flow (if invoked) would clobber the new manifest. The claude add appears to succeed; the vibe skill packages are still on disk but the manifest thinks they don't exist. `spec-kitty doctor` would report all 11 vibe files as orphans.

**Why no test catches it**:

The test suite covers the two manifest systems in isolation:

- `test_command_installer.py` tests `command_installer.install/remove/verify` against a tmpdir that has only `.kittify/config.yaml` and no legacy manifest file.
- `test_init_vibe.py::test_init_vibe_installs_command_skills` tests init with `--ai vibe` alone (no command-layer agent in the same invocation).
- `test_installer.py` (legacy) tests the legacy installer against tmpdirs that have no new manifest file.

The cross-writer scenario is untested. This is the classic "cross-WP integration gap" failure mode the mission-review skill guide warns about, and it was introduced specifically by the v1 remediation's wiring step — because before the wiring, the new `command_installer` was never called from the live init path and thus never wrote the manifest file in competition with the legacy writer.

**Analysis**: The v1 remediation for RISK-1 correctly hooked up `command_installer.install()` to `init.py` and `agent/config.py`, making Vibe support functional. But it did so without discovering that the new `manifest_store` ships a filename constant (`skills-manifest.json`) that matches the pre-existing legacy manifest path, and that both writers are reachable within a single `init` invocation. The collision is latent in commit `07b89982` and will bite the first user who runs `spec-kitty init --ai <command-layer-agent> --ai vibe` against the next release.

Mitigating context: pure installs (only command-layer agents, or only codex/vibe) do not trigger the collision. Users with `init --ai vibe` or `init --ai claude` alone are safe. But mixed installs are a primary supported user scenario — announcing "Mistral Vibe works alongside your existing Claude setup" implicitly promises the mixed install works.

**Remediation outside this review's scope** (suggested direction only, since the skill rules forbid fixing during review): give the two manifests distinct paths. Options:

- Rename the new one to `.kittify/command-skills-manifest.json` (narrowest change, new-only code is in this mission's diff).
- Rename the legacy one to `.kittify/managed-skills-manifest.json` (touches pre-existing call sites).
- Merge the two schemas (largest change; requires a cross-mission effort).

The cheapest fix that doesn't touch pre-mission code is to rename the new constant in `manifest_store.py:61` and update the 4 call sites that reference the file path. Add a regression test that calls both writers in sequence and asserts both manifests exist with their expected schemas.

---

### RISK-6: Manifest file location not declared in the new schema's contract (LOW)

**Type**: DOCUMENTATION GAP
**Severity**: LOW
**Location**: `kitty-specs/083-agent-skills-codex-vibe/contracts/skills-manifest.schema.json`
**Trigger condition**: Any future maintainer reading the schema in isolation.

**Evidence**: The schema declares itself as "Spec Kitty Skills Manifest" and says it records Agent Skills packages, but does not state the on-disk path. The path is defined only in the Python `_MANIFEST_FILENAME` constant. A future refactor that consults only the contract file (e.g., for a renumbering to avoid RISK-5) will not discover the collision from the schema alone.

**Analysis**: Minor documentation gap. Adding a `"x-storage-path"` extension field to the schema's `$id`-adjacent metadata would surface the on-disk location alongside the structural definition. Not blocking.

---

## FR Coverage Matrix (v2)

| FR ID | v1 Adequacy | v2 Adequacy | Change |
|-------|-------------|-------------|--------|
| FR-001 | ADEQUATE | ADEQUATE | — |
| FR-002 | ADEQUATE | ADEQUATE | — |
| FR-003 | FALSE_POSITIVE | **ADEQUATE** | new test `test_init_vibe_installs_command_skills` asserts SKILL.md creation (v1 RISK-1 fix) |
| FR-004 | PARTIAL (16 vs 11) | **ADEQUATE** | spec tightened to 11; implementation matches |
| FR-005 | ADEQUATE | ADEQUATE | — |
| FR-006 | PARTIAL (symlink fixture) | **ADEQUATE** | fixture symlink removed; test now exercises production path |
| FR-007 | ADEQUATE | ADEQUATE | — |
| FR-008 | PARTIAL (symlink fixture) | **ADEQUATE** | same |
| FR-009 | ADEQUATE | ADEQUATE | — |
| FR-010 | ADEQUATE | ADEQUATE | — |
| FR-011 | PARTIAL (no live path) | **ADEQUATE** | codex migration + init now both route to installer |
| FR-012 | PARTIAL (silent delete) | **ADEQUATE** | files moved to `.codex/prompts.superseded/` with user notice |
| FR-013 | PARTIAL (literal `AGENT_DIRS`) | **ADEQUATE** | spec rewritten to reflect registry distinction |
| FR-014 | ADEQUATE | ADEQUATE | — |
| FR-015 | MISSING (no ADR) | **ADEQUATE** | `architecture/adrs/2026-04-14-2-…md` delivered |
| FR-016 | PARTIAL (SKILL.md check missing) | **ADEQUATE** | integration test added; production-shape smoke passes |

All 16 FRs now map to at least one test that constrains production behavior against a non-synthetic fixture. Zero false positives remaining in the FR trace.

---

## Silent Failure Candidates (delta from v1)

| Location | v1 status | v2 status |
|----------|-----------|-----------|
| `init.py:541-544` (skip skill install on SHARED) | **ACTIVE**: silent skip for vibe | **RESOLVED**: replaced with explicit codex/vibe installer call; other SHARED-class agents remain in the skip branch with unchanged semantics |
| `agent/config.py:134-140` (skill-only add had no install) | **ACTIVE**: silent no-op install | **RESOLVED**: now installs; errors surface via `errors` list |
| `runtime/agent_commands.py:243-249` (swallowed exception in auto-sync) | pre-existing | unchanged — still swallows, but applies only to the 12 command-layer agents. |
| `m_3_2_0_codex_to_skills.py:255-260` (silent edit loss) | **ACTIVE**: silent delete | **RESOLVED**: files moved with user notice |

One new silent-failure candidate introduced by the remediation is the manifest collision in **RISK-5**, where the losing writer's data vanishes with no log, no warning, and no error. That's documented above.

---

## Security Notes (v2)

No change from v1. No new subprocess calls, network calls, credentials, or lock scopes introduced by the remediation. `agent_key` input validation is preserved (`SUPPORTED_AGENTS` allowlist). Atomic write pattern unchanged.

One tangential observation: the migration's new rename-to-`prompts.superseded/` path uses `p.path.rename(target)` inside a pre-existing-directory check. `Path.rename` on POSIX is atomic within the same filesystem; on Windows it fails if the target exists. The code handles that case by unlinking the stale source before attempting the rename, preserving idempotency. No security concern.

---

## Final Verdict

### **FAIL**

### Verdict rationale

All eight v1 findings are correctly resolved and verified with production-shape smoke tests. The remediation is high quality in its stated scope.

However, the v1 remediation introduced a new CRITICAL release-blocker — **RISK-5**: the legacy `ManagedSkillManifest` and new `SkillsManifest` both write to `.kittify/skills-manifest.json` with incompatible schemas. Fixing RISK-1 (wiring `command_installer.install()` into the init and add flows) is what exposed this collision in the live runtime. Any user who installs both a command-layer agent and a skill-only agent in the same project (the exact scenario the release announcement will implicitly promise works) will experience data loss on at least one manifest and errors on the next install/remove operation for the loser.

The mission cannot ship as-is for a second consecutive review. The good news: the remaining fix is small (rename one constant and add one integration test). The bad news: the mission's test suite does not currently exercise the cross-installer scenario, which means the next remediation must include a test that installs both a legacy-path agent and a new-path agent in the same init invocation and verifies both manifests persist correctly.

### Release-blocking findings that must be fixed before next review

- **RISK-5** (CRITICAL): disambiguate the two manifest file paths. Simplest option: rename the new manifest to `.kittify/command-skills-manifest.json` and update all four call sites (`manifest_store.py:61,192,214,277`). Add a regression test that runs `init --ai claude --ai vibe` (or equivalent programmatic equivalent) and asserts both the legacy manifest (tracking claude's canonical skills) and the new manifest (tracking vibe's command-skills) exist on disk with their expected schemas after the init completes.

### Open items (non-blocking)

- **RISK-6** (LOW): add an `x-storage-path` extension or a prose note to `contracts/skills-manifest.schema.json` so the on-disk location is discoverable from the contract alone.
- Follow-up mission candidate: the two parallel skill-installers (legacy `skills/installer.py` for canonical skills + new `skills/command_installer.py` for command-skills) share conceptual ownership of `.agents/skills/` but maintain independent manifests. A future unification would reduce cross-system integration risk and eliminate the "which manifest wins" failure class at the architectural level rather than papering it over with a rename.

### Review cycle signal (v2)

No new rejection cycles since v1 remediation — the fix commit `07b89982` landed cleanly. The prior v1 review itself was the quality gate that caught RISK-1/RISK-2; this v2 review is the quality gate that catches RISK-5. This pattern (each review surfaces an issue the previous reviews missed because the bug only manifests at the current integration level) is consistent with the mission-review skill's explicit design: per-WP reviews cannot catch cross-WP holes, and a post-merge review cannot catch holes that only appear after post-merge fixes are applied. A third review cycle after the RISK-5 remediation is appropriate.
