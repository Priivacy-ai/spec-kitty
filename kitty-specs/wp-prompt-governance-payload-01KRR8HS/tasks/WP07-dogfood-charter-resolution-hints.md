---
work_package_id: WP07
title: Dogfood — declare template_set, available_tools, and authority_paths in .kittify/charter/charter.md
dependencies:
- WP02
requirement_refs:
- FR-007
- FR-008
- FR-009
- C-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T029
- T030
- T031
agent: "claude:opus-4-7:curator-carla:curator"
agent_profile: curator-carla
authoritative_surface: .kittify/charter/charter.md
execution_mode: code_change
owned_files:
- .kittify/charter/charter.md
role: curator
history: []
tags: []
shell_pid: "1195624"
---

## Objective

Dogfood the FR-007 / FR-008 mechanism delivered by WP02 by adding a fenced YAML
declaration block to spec-kitty's own project charter. After this WP:

- `spec-kitty charter sync` reads the block and persists `template_set:
  software-dev-default`, `available_tools: [git, spec-kitty, pytest, mypy, ruff]`, and
  `authority_paths: [glossary/contexts/, architecture/2.x/adr/]` into the bundle.
- `spec-kitty charter context --action implement` emits **no**
  `Template set not selected in charter; fallback ... applied` diagnostic.
- ATDD tests `test_project_charter_declares_template_set` and
  `test_project_charter_declares_available_tools` turn green.

C-005 (non-optional dogfood) is satisfied at the moment this WP merges.

---

## Context

The spec's user-journey 3 is exactly this scenario: a project charter maintainer
declares `template_set:` and `available_tools:` and the resolver fallback diagnostics
go away. Doing so on spec-kitty's own charter is the dogfood contract pinned by FR-009
and C-005.

This WP is a **documentation / governance edit** (no code change), so the assigned
profile is `curator-carla` rather than `python-pedro`. The mechanism it depends on
(WP02's fenced-YAML reader) MUST be merged first — WP07 cannot land before WP02. WP07
does NOT depend on WP03, WP04, WP05, or WP06; it can land in parallel with WP03–WP06.

---

## Branch Strategy

- **Planning/base branch**: `feat/org-doctrine-layer`
- **Merge target**: `feat/org-doctrine-layer`
- **Worktree**: allocated by `finalize-tasks`
- **Implement command**: `spec-kitty agent action implement WP07 --agent claude`

---

## Subtask T029 — Add `## Charter Resolution Hints` section with fenced YAML block

**File**: `.kittify/charter/charter.md`

Append a new top-level section (near the end of the file, before any "Appendix" if
present):

````markdown
## Charter Resolution Hints

These declarations are read by `spec-kitty charter sync` (see FR-007 of mission
`wp-prompt-governance-payload-01KRR8HS`). Keep this block up to date as the project
adopts new template sets, tools, or authority directories.

```yaml
template_set: software-dev-default
```
````

Confirm the resulting `spec-kitty charter sync` run reports no
`Template set not selected in charter; fallback ... applied` diagnostic for the
`template_set` line.

---

## Subtask T030 — Extend the YAML block with `available_tools` and `authority_paths`

**File**: `.kittify/charter/charter.md`

Extend the fenced YAML block from T029 to its full form:

````yaml
```yaml
template_set: software-dev-default
available_tools:
  - git
  - spec-kitty
  - pytest
  - mypy
  - ruff
authority_paths:
  - glossary/contexts/
  - architecture/2.x/adr/
```
````

The choice of `available_tools` reflects what the spec-kitty codebase actually uses
day-to-day (per `CLAUDE.md`'s "Commands" section: `pytest`, `ruff check`, `mypy`).
`git` and `spec-kitty` are universal.

The `authority_paths` list mirrors the two defaults the resolver knows about, making
the declaration explicit and self-documenting. This block is the human-side
counterpart to the auto-detection in WP04's `_render_authority_paths`.

---

## Subtask T031 — Verify diagnostic-free sync + ATDD greens

After editing the charter:

```bash
spec-kitty charter sync
spec-kitty charter context --action implement
```

The output of `charter context` MUST NOT contain either of these diagnostic lines:

- `Template set not selected in charter; fallback ... applied`
- `No available_tools selection provided; using runtime tool registry fallback`

Then run the ATDD anchors for this WP:

```bash
pytest tests/specify_cli/next/test_wp_prompt_governance_contract.py::TestProjectCharterDeclaresResolverInputs -v
```

Expected: `2 passed` (both `test_project_charter_declares_template_set` and
`test_project_charter_declares_available_tools` green).

Record the absence of both fallback diagnostics in the WP activity log.

---

## Definition of Done

- [ ] `.kittify/charter/charter.md` contains a `## Charter Resolution Hints` section.
- [ ] The fenced YAML block under that section declares `template_set`, `available_tools`, and `authority_paths`.
- [ ] `spec-kitty charter sync` succeeds against the updated charter.
- [ ] `spec-kitty charter context --action implement` emits no fallback diagnostic for either declaration.
- [ ] ATDD `test_project_charter_declares_template_set` passes.
- [ ] ATDD `test_project_charter_declares_available_tools` passes.
- [ ] All other ATDD tests in the suite that were green pre-WP remain green.
- [ ] No regression in `tests/architectural/test_layer_rules.py` (the change is a markdown edit; layer tests should be untouched).

---

## Risks

- **R-1**: The fenced YAML block is malformed (wrong indentation, tab vs space) and
  `charter sync` errors. **Mitigation**: copy the exact block from T030; run sync
  immediately after the edit; fix-forward on any parse error.
- **R-2**: WP02 is not actually merged when this WP starts implementation, so the
  reader code does not exist yet. **Mitigation**: the dependency list (`[WP02]`)
  enforces ordering at the lanes-json level; the implementer waits on WP02 done.
- **R-3**: The chosen `available_tools` list is incorrect or incomplete for spec-kitty
  (e.g. missing `npm`). **Mitigation**: cross-reference `CLAUDE.md`'s Commands section
  and `pyproject.toml`'s dev dependencies; if the list needs expansion, a follow-up
  edit is a low-risk, additive change.

---

## Reviewer Guidance

Check that:

1. The fenced YAML block uses three backticks + `yaml` fence (not four backticks; not
   `~~~` fences) so the existing YAML extractor picks it up.
2. The keys are exactly `template_set`, `available_tools`, `authority_paths` — no
   typos, no plural/singular drift.
3. The `template_set` value is `software-dev-default` (the canonical spec-kitty template
   set) — not `software-dev`, not `default`.
4. After running `spec-kitty charter sync`, the file `.kittify/charter/governance.yaml`
   (or whichever bundle the resolver reads) reflects the three new fields.
5. After running `spec-kitty charter context --action implement`, neither fallback
   diagnostic appears in stderr or stdout.
6. The two ATDD tests in `TestProjectCharterDeclaresResolverInputs` both pass.
7. The charter edit is the ONLY change in this WP — no source code under `src/` is
   modified.

## Activity Log

- 2026-05-16T13:30:55Z – claude:opus-4-7:curator-carla:curator – shell_pid=1195624 – Started implementation via action command
- 2026-05-16T13:35:38Z – claude:opus-4-7:curator-carla:curator – shell_pid=1195624 – Charter Resolution Hints section added to .kittify/charter/charter.md with template_set, available_tools, authority_paths. ATDD suite 23/0 passed. Runtime charter context diagnostic will clear post-merge (chokepoint anchors on main-checkout per FR-010).
