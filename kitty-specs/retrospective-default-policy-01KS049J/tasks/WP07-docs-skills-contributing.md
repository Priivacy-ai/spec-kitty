---
work_package_id: WP07
title: Docs + shipped skills + CONTRIBUTING note
dependencies:
- WP04
- WP05
requirement_refs:
- FR-017
- FR-018
- FR-019
- FR-020
- FR-022
planning_base_branch: main
merge_target_branch: main
branch_strategy: Planning artifacts for this mission were generated on main. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into main unless the human explicitly redirects the landing branch.
subtasks:
- T035
- T036
- T037
- T038
- T039
- T040
- T041
phase: Polish
assignee: ''
agent: claude
history:
- timestamp: '2026-05-19T13:29:59Z'
  agent: system
  action: Prompt generated via /spec-kitty.tasks
agent_profile: curator-carla
authoritative_surface: docs/how-to/use-retrospective-learning.md
execution_mode: code_change
model: claude-sonnet-4-6
owned_files:
- docs/how-to/use-retrospective-learning.md
- docs/how-to/accept-and-merge.md
- docs/how-to/merge-feature.md
- docs/explanation/retrospective-learning-loop.md
- docs/reference/cli-commands.md
- docs/reference/slash-commands.md
- docs/tutorials/your-first-feature.md
- README.md
- CONTRIBUTING.md
- src/doctrine/skills/spec-kitty-mission-review/SKILL.md
- src/doctrine/skills/spec-kitty-implement-review/SKILL.md
- src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md
- src/doctrine/skills/spec-kitty-runtime-next/SKILL.md
- src/doctrine/agent_profiles/built-in/retrospective-facilitator.agent.yaml
role: curator
tags: []
---

# Work Package Prompt: WP07 — Docs + Shipped Skills + CONTRIBUTING Note

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load curator-carla
```

Curator Carla curates documentation and shipped artifacts for fidelity, consistency, and accuracy. The avoidance boundary is "writing new code in `src/specify_cli/`" — that's already-done work by other WPs. Your job is to make the retrospective story coherent across docs and shipped skills.

## Objective

Update operator-facing docs and shipped skills to reflect the four distinct retrospective CLI semantics shipped by WP04+WP05. Correct PR #1136's overstated post-merge wording in place. Review the `retrospective-facilitator.agent.yaml` profile boundaries against the new FR-001/FR-010 model. Add the #1137 namespace-package diagnostic note to `CONTRIBUTING.md`.

This WP is the carrier for **bulk-edit shape B** (doc semantics correction). Coordinate with the `occurrence_map.yaml` produced at finalize-tasks.

## Context

PR #1136 ("Clarify accept, merge, and retrospective workflow") shipped wording that treats `summary` and `synthesize` as the post-merge retrospective capture step. After WP04+WP05 land, that wording is wrong:

- `summary` aggregates across records (read-only).
- `create` authors a record for one mission.
- `backfill` authors historical records.
- `synthesize` previews/applies proposals from an existing record.

The canonical post-merge sequence (FR-019) is: **mission review → create/capture retrospective → summary or synthesize**.

References:
- Operator quickstart: [quickstart.md](../quickstart.md)
- CLI contracts: [contracts/retrospect-cli.contract.md](../contracts/retrospect-cli.contract.md)
- #1137 diagnostic from research: [research.md § R-7 / R-11](../research.md)

## Branch Strategy

- Planning base: `main`
- Final merge target: `main`
- Execution worktree resolved via `lanes.json` after `finalize-tasks`.

## Subtasks

### T035 — `docs/how-to/use-retrospective-learning.md` (canonical operator how-to)

**Purpose**: This is the single canonical operator-facing how-to for retrospective learning. Other docs link here.

**Steps**:

1. Either rewrite the existing file or create it if missing. Use [quickstart.md](../quickstart.md) as the source narrative; trim CI-specific test commands for an operator audience.
2. Required sections:
   - 30-second mental model (Policy / Record / Summary / Synthesize)
   - The default path (you do nothing) — `spec-kitty merge` produces a record automatically
   - The opt-out path (`retrospective.enabled: false`)
   - The strict path (governed projects with `before_completion + block`)
   - Authoring on demand (`retrospect create`)
   - Backfilling historical records (`retrospect backfill`)
   - Reviewing and applying proposals (`agent retrospect synthesize`)
   - Migration from env vars (deprecation guidance + table)
   - What the commands DON'T do (`summary` is read-only; `synthesize` doesn't author; runtime doesn't mutate doctrine)
   - Common errors and remediations
3. Link to `quickstart.md` as the verifying-your-install reference.

**Files**:
- `docs/how-to/use-retrospective-learning.md` (new or rewrite, ~250 lines)

**Validation**:
- [ ] `uv run markdownlint --config .markdownlint-cli2.jsonc docs/how-to/use-retrospective-learning.md` exits 0
- [ ] Every documented command runs cleanly against a fresh test project (smoke)

---

### T036 — `accept-and-merge.md` (correct PR #1136 wording) + `merge-feature.md`

**Purpose**: Correct the post-merge wording introduced by PR #1136.

**Steps**:

1. Read both files end-to-end. Identify every sentence that conflates `summary` or `synthesize` with authoring.
2. Replace the post-merge guidance section (whatever its current heading) with the canonical sequence:
   > **After merge, before declaring the mission done**:
   > 1. **Mission review** — run `spec-kitty agent mission review --mission <handle>` to confirm spec→code fidelity and FR coverage.
   > 2. **Capture the retrospective** — under default policy this already happened during merge; verify with `cat .kittify/missions/<mission_id>/retrospective.yaml`. If absent (e.g. older mission), run `spec-kitty retrospect create --mission <handle>`.
   > 3. **Surface findings** — run `spec-kitty retrospect summary` to aggregate across recent missions, or `spec-kitty agent retrospect synthesize --mission <handle> --preview` to inspect proposals in one record.
3. Cross-link to `docs/how-to/use-retrospective-learning.md` (T035) for full details.
4. Both files must speak the same canonical sequence (FR-019).

**Files**:
- `docs/how-to/accept-and-merge.md` (edit, ~40 line change)
- `docs/how-to/merge-feature.md` (edit, ~30 line change)

**Validation**:
- [ ] No sentence in either file says `summary` "captures" or "generates" a retrospective
- [ ] No sentence says `synthesize` "creates" or "writes" a retrospective record (it previews/applies)
- [ ] Both files link to T035's canonical how-to

---

### T037 — `retrospective-learning-loop.md` + `cli-commands.md` + `slash-commands.md`

**Purpose**: Conceptual explanation + reference docs.

**Steps**:

1. `docs/explanation/retrospective-learning-loop.md`: explain the four-category model (policy → generation → record → application) with a diagram showing the bounded contexts (Authoring vs Doctrine/DRG/Glossary) and the `synthesize` ACL. Use the bounded-context diagram from the ADR as the source.
2. `docs/reference/cli-commands.md`: add reference entries for:
   - `spec-kitty retrospect create` (link to contract)
   - `spec-kitty retrospect backfill` (link to contract)
   - `spec-kitty retrospect summary` (read-only) — update existing entry with new `findings_status` + `policy_source` output keys
   - `spec-kitty agent retrospect synthesize` — note the default-path tightening and `--fabricate-empty` flag
3. `docs/reference/slash-commands.md`: this is for slash-command surfaces (`/spec-kitty.*`), not for the new `retrospect` CLI commands. Only edit if PR #1136 wording leaked into a slash-command description; otherwise leave untouched and note as such in the WP commit message.

**Files**:
- `docs/explanation/retrospective-learning-loop.md` (rewrite/extend, ~120 lines)
- `docs/reference/cli-commands.md` (extend, ~80 lines added)
- `docs/reference/slash-commands.md` (audit; edit only if PR #1136 contamination found)

**Validation**:
- [ ] Markdownlint clean
- [ ] Bounded-context model matches the ADR

---

### T038 — `README.md` + `docs/tutorials/your-first-feature.md`

**Purpose**: First-touch surfaces for new users.

**Steps**:

1. `README.md`: locate the retrospective blurb (if absent, add a brief one in the feature highlights section). Two sentences: "Every completed mission generates a retrospective by default. Tune via `.kittify/config.yaml#retrospective` or charter; see [how-to](docs/how-to/use-retrospective-learning.md)."
2. `docs/tutorials/your-first-feature.md`: at the end-of-tutorial wrap-up, add a one-paragraph note pointing users at where the retrospective record landed and how to inspect it.

**Files**:
- `README.md` (edit, ~5 lines)
- `docs/tutorials/your-first-feature.md` (edit, ~15 lines added)

**Validation**:
- [ ] README's retrospective blurb under 50 words
- [ ] Tutorial mentions the record location in `.kittify/missions/<mission_id>/retrospective.yaml`

---

### T039 — Update 4 shipped skills

**Purpose**: Shipped skill files describe the canonical workflow; agents follow them.

**Steps**:

1. For each of:
   - `src/doctrine/skills/spec-kitty-mission-review/SKILL.md`
   - `src/doctrine/skills/spec-kitty-implement-review/SKILL.md`
   - `src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md`
   - `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md`

   audit the post-merge / mission-completion guidance. Replace any text that conflates `summary` or `synthesize` with authoring. Insert the canonical sequence: "mission review → create/capture retrospective → summary or synthesize".

2. Each skill file's edit is small (5-15 lines) but cumulative. Use `grep` to find every reference:
   ```bash
   grep -rln "retrospect summary\|retrospect synthesize\|capture.*retrospective" src/doctrine/skills/spec-kitty-{mission-review,implement-review,program-orchestrate,runtime-next}/
   ```

3. Verify the skill snapshot tests in `tests/specify_cli/skills/__snapshots__/` will regenerate consistently. After edits, run:
   ```bash
   uv run pytest tests/specify_cli/skills/ -q
   ```
   Update snapshots if the test infrastructure supports auto-regeneration; otherwise update them by hand to match.

**Files**:
- `src/doctrine/skills/spec-kitty-mission-review/SKILL.md` (edit, ~10 lines)
- `src/doctrine/skills/spec-kitty-implement-review/SKILL.md` (edit, ~10 lines)
- `src/doctrine/skills/spec-kitty-program-orchestrate/SKILL.md` (edit, ~10 lines)
- `src/doctrine/skills/spec-kitty-runtime-next/SKILL.md` (edit, ~10 lines)

**Validation**:
- [ ] All four skill files speak the same canonical sequence
- [ ] Skill snapshot tests pass after edits

---

### T040 — Review `retrospective-facilitator.agent.yaml` boundaries

**Purpose**: Align the profile's declared boundaries and permissions with the FR-001/FR-010 model (policy resolver + no structural auto-apply).

**Steps**:

1. Read `src/doctrine/agent_profiles/built-in/retrospective-facilitator.agent.yaml` end-to-end.
2. Check three things:
   - `specialization.primary_focus` mentions authoring retrospectives — should now also note that authoring runs as a pure-Python module by default (the profile is for human-mediated rich post-mortems, not the runtime default).
   - `specialization.avoidance_boundary` mentions doctrine/DRG/glossary mutation — should explicitly note "no structural auto-apply" per FR-010.
   - `collaboration.handoff_to` / `handoff_from` should include the `synthesize` command as the explicit ACL for proposal application.
3. Make minimal edits — do NOT rewrite the profile structurally. Targeted line-level changes to the three sections above.
4. Document any changes in this WP's commit message AND in the mission-review report (for FR-020 traceability).

**Files**:
- `src/doctrine/agent_profiles/built-in/retrospective-facilitator.agent.yaml` (light edits, ~10-15 lines)

**Validation**:
- [ ] Profile YAML still validates against the doctrine profile schema (run `spec-kitty agent profile show retrospective-facilitator` if available)
- [ ] No structural rewrite of the profile

---

### T041 — `CONTRIBUTING.md` namespace-package diagnostic for #1137

**Purpose**: Document the local-env diagnostic that contributors will hit if their `spec-kitty-events` install is corrupted.

**Steps**:

1. Locate `CONTRIBUTING.md`'s troubleshooting section (or add one if absent).
2. Add the diagnostic from [#1137 closing comment](https://github.com/Priivacy-ai/spec-kitty/issues/1137#comment) and [research.md § R-7](../research.md):
   ```markdown
   ## Pytest collection fails with "cannot import name 'normalize_event_id' from 'spec_kitty_events'"

   **Symptom**: Pytest collection fails before any tests run with:
   `ImportError: cannot import name 'normalize_event_id' from 'spec_kitty_events' (unknown location)`

   **Cause**: Local PEP 420 namespace-package corruption from a partial `pip uninstall`. The wheel
   is fine; CI is unaffected. This is NOT a Spec Kitty bug — it's a Python install integrity issue.

   **Diagnostic**:
   ```bash
   python -c "import spec_kitty_events; print(repr(spec_kitty_events.__file__), spec_kitty_events.__path__)"
   # Healthy:   prints a path ending in __init__.py
   # Corrupt:   prints None followed by _NamespacePath([...])  ← this is the bad state
   ```

   **Fix**:
   ```bash
   uv sync --reinstall-package spec-kitty-events
   ```

   Per the closing comment on [#1137](https://github.com/Priivacy-ai/spec-kitty/issues/1137), the Spec Kitty code
   path deliberately does NOT fall back to importing from `spec_kitty_events.models.*` — that
   would violate the FR-024 frozen public-surface architectural contract and mask local-env
   corruption that future contributors should still hit visibly.
   ```

3. If `CONTRIBUTING.md` has a "Local development" section already, integrate there; otherwise add at the end.

**Files**:
- `CONTRIBUTING.md` (edit, ~40 lines added)

**Validation**:
- [ ] Diagnostic block contains the exact `python -c` command and `uv sync` fix
- [ ] References the architectural rationale (FR-024) so future contributors don't undo the decision

---

## Definition of Done

- [ ] All 7 subtasks complete
- [ ] `uv run markdownlint --config .markdownlint-cli2.jsonc <touched-paths>` exits 0
- [ ] `uv run pytest tests/specify_cli/skills/ -q` exits 0 (snapshot tests updated if needed)
- [ ] No file outside `owned_files` modified
- [ ] Bulk-edit shape B occurrence map matches actual changes (cross-checked at mission review)
- [ ] FR-020 review notes recorded in commit message

## Risks & Reviewer Guidance

- **Bulk-edit shape B**: doc semantics correction spans 8 docs + 4 skills + README. `occurrence_map.yaml` (finalize-tasks output) enumerates each occurrence; reviewer cross-checks.
- **Test snapshot tests**: editing shipped skill files may break `tests/specify_cli/skills/` snapshot tests. The skill-snapshot infrastructure typically auto-regenerates with a `--regenerate` flag or similar; verify the project's specific convention before editing.
- **Profile review (T040)**: do NOT rewrite the profile structurally. Targeted line-level changes only. Reviewer should diff the YAML and confirm minimal-touch.
- **Reviewer**: walk a fresh project through the documented quickstart commands end-to-end; any command that fails or produces output that doesn't match the docs is a blocker.

## Next

After this WP merges, the mission is feature-complete. Mission review (`spec-kitty agent mission review`) is the next step before declaring done.

Implementation command:

```bash
spec-kitty agent action implement WP07 --agent claude
```
