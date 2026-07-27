---
work_package_id: WP04
title: Shipped Profile Migration and Renames
dependencies:
- WP01
- WP02
agent_profile: "reviewer-renata"
role: "reviewer"
agent: "claude"
model: "claude-sonnet-4-6"
requirement_refs:
- C-005
- FR-006
- FR-011
- FR-012
- FR-013
planning_base_branch: doctrine/profile_reinforcement
merge_target_branch: doctrine/profile_reinforcement
branch_strategy: Planning artifacts for this feature were generated on doctrine/profile_reinforcement. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into doctrine/profile_reinforcement unless the human explicitly redirects the landing branch.
subtasks:
- T021
- T022
- T023
- T024
- T025
- T026
- T027
- T028
history:
- at: '2026-04-21T18:24:37Z'
  event: created
authoritative_surface: src/doctrine/agent_profiles/shipped/
execution_mode: code_change
mission_slug: profile-roles-as-value-object-01KPRJRY
owned_files:
- src/doctrine/agent_profiles/shipped/*.agent.yaml
- src/doctrine/agent_profiles/shipped/README.md
- src/doctrine/graph.yaml
- tests/doctrine/test_shipped_profiles.py
tags: []
---

# WP04 — Shipped Profile Migration and Renames

## ⚡ Do This First: Load Agent Profile

Use the `/ad-hoc-profile-load` skill to load the agent profile specified in the frontmatter, and behave according to its guidance before parsing the rest of this prompt.

- **Profile**: `python-pedro`
- **Role**: `implementer`
- **Agent/tool**: `claude`

If no profile is specified, run `spec-kitty agent profile list` and select the best match for this work package's `task_type` and `authoritative_surface`.

---

## Objective

Migrate all 11 shipped profiles from the deprecated `role: <scalar>` key to
`roles: [...]` list syntax and rename 7 profiles to carry character names in
their `profile-id`. Update `graph.yaml` URNs, `shipped/README.md`, and
`test_shipped_profiles.py`.

**CRITICAL ATOMIC CONSTRAINT**: The rename of `implementer.agent.yaml` →
`implementer-ivan.agent.yaml` AND the update of `specializes-from: implementer-ivan`
in `java-jenny.agent.yaml` and `python-pedro.agent.yaml` **must be in the same git commit**.
`validate_hierarchy()` rejects dangling `specializes-from` references. A split commit
would cause CI to fail.

## Implementation Command

```bash
spec-kitty agent action implement WP04 --agent python-pedro
```

## Branch Strategy

- **Plan base**: `doctrine/profile_reinforcement`
- **Depends on**: WP01 (new `roles:` syntax valid in model) + WP02 (schema accepts `roles:`)
- **Parallelizes with**: WP03 (different files)
- **Merge target**: `doctrine/profile_reinforcement`

---

## Context

### Rename Map

| Old filename | New filename | Old profile-id | New profile-id | Name change |
|---|---|---|---|---|
| `architect.agent.yaml` | `architect-alphonso.agent.yaml` | `architect` | `architect-alphonso` | none |
| `curator.agent.yaml` | `curator-carla.agent.yaml` | `curator` | `curator-carla` | none |
| `designer.agent.yaml` | `designer-dagmar.agent.yaml` | `designer` | `designer-dagmar` | none |
| `implementer.agent.yaml` | `implementer-ivan.agent.yaml` | `implementer` | `implementer-ivan` | none |
| `planner.agent.yaml` | `planner-priti.agent.yaml` | `planner` | `planner-priti` | "Planner Petra" → "Planner Priti" |
| `researcher.agent.yaml` | `researcher-robbie.agent.yaml` | `researcher` | `researcher-robbie` | "Researcher Rosa" → "Researcher Robbie" |
| `reviewer.agent.yaml` | `reviewer-renata.agent.yaml` | `reviewer` | `reviewer-renata` | none |

**No rename** (only `role:` → `roles:` migration):
- `generic-agent.agent.yaml` — profile-id unchanged
- `human-in-charge.agent.yaml` — profile-id unchanged
- `java-jenny.agent.yaml` — already has character name
- `python-pedro.agent.yaml` — already has character name

### Graph URNs

DRG nodes in `src/doctrine/graph.yaml` use the pattern `agent_profile:<profile-id>`.
The 7 renamed profiles require URN updates:

```
agent_profile:architect       → agent_profile:architect-alphonso
agent_profile:curator         → agent_profile:curator-carla
agent_profile:designer        → agent_profile:designer-dagmar
agent_profile:implementer     → agent_profile:implementer-ivan
agent_profile:planner         → agent_profile:planner-priti
agent_profile:researcher      → agent_profile:researcher-robbie
agent_profile:reviewer        → agent_profile:reviewer-renata
```

Also update node `label` fields where the label contains the old role-only name.
`planner` label → "Planner Priti" and `researcher` label → "Researcher Robbie".

---

## Subtask Guidance

### T021 — `git mv` 7 renamed YAML files

**IMPORTANT**: This must be done atomically with T022 and T023 (all in a single commit).
Do the `git mv` commands but do not commit yet — stage them and continue with T022/T023
before committing.

```bash
cd src/doctrine/agent_profiles/shipped

git mv architect.agent.yaml   architect-alphonso.agent.yaml
git mv curator.agent.yaml     curator-carla.agent.yaml
git mv designer.agent.yaml    designer-dagmar.agent.yaml
git mv implementer.agent.yaml implementer-ivan.agent.yaml
git mv planner.agent.yaml     planner-priti.agent.yaml
git mv researcher.agent.yaml  researcher-robbie.agent.yaml
git mv reviewer.agent.yaml    reviewer-renata.agent.yaml
```

Verify with `git status` that all 7 files show as renamed (not deleted + added).

---

### T022 — Update `profile-id` + `role:` → `roles: [...]` in 7 renamed files; update names for planner/researcher

For each of the 7 renamed files, open and edit:

1. Change `profile-id: <old>` → `profile-id: <new>`
2. Change `role: <value>` → `roles:\n  - <value>`
3. For `planner-priti.agent.yaml`: change `name: Planner Petra` → `name: Planner Priti`
4. For `researcher-robbie.agent.yaml`: change `name: Researcher Rosa` → `name: Researcher Robbie`

**Example diff for `architect-alphonso.agent.yaml`**:
```yaml
# Before:
profile-id: architect
role: architect

# After:
profile-id: architect-alphonso
roles:
  - architect
```

Do all 7 files. Do not commit yet (T023 must happen in the same commit).

---

### T023 — [ATOMIC] Update `specializes-from` in java-jenny + python-pedro

**THIS MUST BE IN THE SAME COMMIT AS T021 + T022.**

Open `java-jenny.agent.yaml` and `python-pedro.agent.yaml`. Both currently have:
```yaml
specializes-from: implementer
```

Change to:
```yaml
specializes-from: implementer-ivan
```

Now stage and commit everything from T021 + T022 + T023 together:

```bash
git add src/doctrine/agent_profiles/shipped/
git commit -m "feat(profiles): rename 7 shipped profiles to character IDs, migrate role → roles

atomic: implementer → implementer-ivan rename + specializes-from update in
java-jenny and python-pedro (validate_hierarchy rejects dangling refs)"
```

Verify `validate_hierarchy()` does not raise by running:
```bash
pytest tests/doctrine/test_shipped_profiles.py -x -k "hierarchy"
```

---

### T024 — Migrate `role:` → `roles:` in generic-agent and human-in-charge

**File**: `src/doctrine/agent_profiles/shipped/generic-agent.agent.yaml`
**File**: `src/doctrine/agent_profiles/shipped/human-in-charge.agent.yaml`

These profiles are not renamed; only the `role:` scalar needs updating to `roles:`.

For each file, change:
```yaml
role: <value>
```
to:
```yaml
roles:
  - <value>
```

No `profile-id` or `name` changes needed. Commit these after T021-T023.

---

### T025 — Migrate `role:` → `roles:` in java-jenny and python-pedro

**File**: `src/doctrine/agent_profiles/shipped/java-jenny.agent.yaml`
**File**: `src/doctrine/agent_profiles/shipped/python-pedro.agent.yaml`

Same as T024 — change scalar `role:` to `roles:` list. These files also carry a
`specializes-from:` key (already updated in T023 to `implementer-ivan`).

Verify the final YAML for these two files looks like:
```yaml
profile-id: java-jenny
name: Java Jenny
specializes-from: implementer-ivan
roles:
  - implementer
...
```

---

### T026 — Update `graph.yaml` — 7 URN renames + label corrections

**File**: `src/doctrine/graph.yaml`

For each of the 7 renamed profiles, find the node with the old URN and update it:

```bash
# Find all nodes to update
rg "agent_profile:(architect|curator|designer|implementer|planner|researcher|reviewer)[^-]" src/doctrine/graph.yaml
```

Update each occurrence:
- `agent_profile:architect` → `agent_profile:architect-alphonso`
- `agent_profile:curator` → `agent_profile:curator-carla`
- `agent_profile:designer` → `agent_profile:designer-dagmar`
- `agent_profile:implementer` → `agent_profile:implementer-ivan`
- `agent_profile:planner` → `agent_profile:planner-priti`
- `agent_profile:researcher` → `agent_profile:researcher-robbie`
- `agent_profile:reviewer` → `agent_profile:reviewer-renata`

Also update node `label` fields for planner and researcher:
- `label: Planner Petra` → `label: Planner Priti` (if this label exists)
- `label: Researcher Rosa` → `label: Researcher Robbie` (if this label exists)

Verify edge URNs are also updated — edges reference nodes by their URN. Run:
```bash
rg "agent_profile:implementer[^-]" src/doctrine/graph.yaml
```
to confirm no stale references remain (should return zero matches).

---

### T027 — Update `shipped/README.md` table

**File**: `src/doctrine/agent_profiles/shipped/README.md`

Update the profile table to reflect new filenames and profile-IDs:

| Old row | New row |
|---------|---------|
| `architect.agent.yaml \| architect` | `architect-alphonso.agent.yaml \| architect-alphonso` |
| `curator.agent.yaml \| curator` | `curator-carla.agent.yaml \| curator-carla` |
| `designer.agent.yaml \| designer` | `designer-dagmar.agent.yaml \| designer-dagmar` |
| `implementer.agent.yaml \| implementer` | `implementer-ivan.agent.yaml \| implementer-ivan` |
| `planner.agent.yaml \| planner` | `planner-priti.agent.yaml \| planner-priti` |
| `researcher.agent.yaml \| researcher` | `researcher-robbie.agent.yaml \| researcher-robbie` |
| `reviewer.agent.yaml \| reviewer` | `reviewer-renata.agent.yaml \| reviewer-renata` |

Also update any `role:` column values to `roles:` if the table documents the field name.

---

### T028 — Update `test_shipped_profiles.py` — EXPECTED_PROFILE_IDS + parametrize entries

**File**: `tests/doctrine/test_shipped_profiles.py`

1. Find `EXPECTED_PROFILE_IDS` (or equivalent set/list of expected IDs). Replace old IDs
   with new character IDs:
   ```python
   # Before (example):
   EXPECTED_PROFILE_IDS = {"architect", "curator", "designer", "implementer",
                           "planner", "researcher", "reviewer",
                           "generic-agent", "human-in-charge",
                           "java-jenny", "python-pedro"}
   # After:
   EXPECTED_PROFILE_IDS = {"architect-alphonso", "curator-carla", "designer-dagmar",
                           "implementer-ivan", "planner-priti", "researcher-robbie",
                           "reviewer-renata", "generic-agent", "human-in-charge",
                           "java-jenny", "python-pedro"}
   ```

2. Find all `@pytest.mark.parametrize` entries referencing old profile IDs and update
   them to the new IDs.

3. Find any assertions referencing `profile.role` as an attribute (the `StrEnum.value`
   pattern). If they call `.value`, replace with direct string comparison:
   ```python
   # Before:
   assert profile.role.value == "implementer"
   # After:
   assert profile.role == "implementer"  # Role is a str subclass, .value does not exist
   ```

4. Add an assertion that all loaded profiles have `len(profile.roles) >= 1`:
   ```python
   def test_all_shipped_profiles_have_roles(loaded_profile):
       assert len(loaded_profile.roles) >= 1
   ```

5. Add an assertion that no loaded profile emits a DeprecationWarning:
   ```python
   def test_no_deprecation_warnings_on_load(shipped_yaml_path):
       import warnings
       with warnings.catch_warnings(record=True) as w:
           warnings.simplefilter("always")
           # load the profile...
       deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
       assert len(deprecation_warnings) == 0, f"Got: {deprecation_warnings}"
   ```

Run `pytest tests/doctrine/test_shipped_profiles.py -v` to verify all pass.

---

## Definition of Done

- [ ] All 7 renamed files: `git mv` tracked, `profile-id` updated, `role:` → `roles:`
- [ ] `planner-priti.agent.yaml` name is "Planner Priti"
- [ ] `researcher-robbie.agent.yaml` name is "Researcher Robbie"
- [ ] `java-jenny.agent.yaml` and `python-pedro.agent.yaml`: `specializes-from: implementer-ivan`
- [ ] T021+T022+T023 are in a **single** git commit (no dangling `specializes-from` reference at any point)
- [ ] `generic-agent.agent.yaml` and `human-in-charge.agent.yaml`: `roles:` list
- [ ] `java-jenny.agent.yaml` and `python-pedro.agent.yaml`: `roles:` list
- [ ] `graph.yaml`: all 7 URN renames applied; planner + researcher labels updated
- [ ] `shipped/README.md` table reflects new filenames and IDs
- [ ] `test_shipped_profiles.py`: EXPECTED_PROFILE_IDS updated; no `.role.value` patterns
- [ ] `pytest tests/doctrine/test_shipped_profiles.py -v` passes
- [ ] `rg "role:" src/doctrine/agent_profiles/shipped/` returns zero matches
  (all profiles use `roles:`)

## Risks

- **Atomic commit constraint**: The `implementer` → `implementer-ivan` rename and
  `specializes-from` update MUST be a single commit. If interrupted, reset the staging
  area and retry from T021.
- **Edge references in graph.yaml**: Edges (relationships) between nodes also reference
  node URNs. Run `rg "agent_profile:implementer[^-]" src/doctrine/graph.yaml` after
  editing to catch any missed occurrences.
- **`git mv` vs file edit**: Use `git mv` (not manual copy-delete) so git tracks the
  rename in history. If a rename is accidentally done as delete+create, use
  `git rm --cached <old>` + `git add <new>` and confirm `git status` shows "renamed".
