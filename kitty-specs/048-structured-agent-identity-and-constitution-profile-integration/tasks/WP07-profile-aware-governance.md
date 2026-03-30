---
work_package_id: WP07
title: Profile-Aware Governance Compilation
lane: "done"
dependencies:
- WP05
- WP06
base_branch: feature/agent-profile-implementation
base_commit: 410f0e6e1c43e74b6a40ec7225c07c813ae52410
created_at: '2026-03-09T04:38:19.521896+00:00'
subtasks:
- T028
- T029
- T030
- T031
- T032
phase: Phase 3 - Compiler Wiring
assignee: ''
agent: "codex:gpt-5:reviewer:reviewer"
shell_pid: '197930'
review_status: "approved"
reviewed_by: "Codex"
review_feedback: ''
history:
- timestamp: '2026-03-08T10:13:04Z'
  lane: planned
  agent: system
  shell_pid: ''
  action: Prompt generated via /spec-kitty.tasks
requirement_refs:
- FR-008
---

# Work Package Prompt: WP07 – Profile-Aware Governance Compilation

## ⚠️ IMPORTANT: Review Feedback Status

**Read this first if you are implementing this task!**

- **Has review feedback?**: Check `review_status`. If it says `has_feedback`, read `review_feedback` first.
- **Mark as acknowledged**: When you understand the feedback, update `review_status: acknowledged`.

---

## Implementation Command

```bash
spec-kitty implement WP07 --base WP06
```

---

## Objectives & Success Criteria

- Extend `GovernanceResolution` with profile-aware fields (tactics, styleguides, toolguides, procedures, profile_id, role)
- Add `agent_profile` and `agent_role` optional fields to `ConstitutionInterview`
- Implement `resolve_governance_for_profile()` that merges profile directives with interview selections
- Create `generate-for-agent` CLI subcommand under `spec-kitty constitution`
- Ensure graceful error when DoctrineService is unavailable for profile-aware compilation

**Success metrics**:
- `spec-kitty constitution generate-for-agent --profile reviewer` produces constitution with profile-specific directives and transitively resolved artifacts
- Profile directives appear before interview directives in output
- Missing profile ID raises informative ValueError
- `GovernanceResolution` fields include tactics, styleguides, toolguides, procedures populated from transitive resolution

## Context & Constraints

- **Spec**: FR-008 (Profile-Aware Governance), User Story 3
- **Data model**: `data-model.md` — GovernanceResolution (extended), ConstitutionInterview (extended)
- **Contracts**: `contracts.md` — Contract 4 (resolve_governance_for_profile)
- **Research**: `research.md` — R6 (GovernanceResolution extension), R7 (generate-for-agent subcommand)
- **Dependency**: WP05 (transitive resolver), WP06 (compiler integration)
- **Key file**: `src/specify_cli/constitution/resolver.py` — `GovernanceResolution` at line 31
- **Key file**: `src/specify_cli/constitution/interview.py` — `ConstitutionInterview` at line 55
- **Key file**: `src/doctrine/agent_profiles/repository.py` — `resolve_profile()` handles inheritance
- **Existing CLI**: `spec-kitty constitution` has subcommands: `interview`, `generate`, `context`, `sync`, `status`
- **Tools**: Use `rg` (ripgrep) for all code searches — do NOT use `grep`. Example: `rg "GovernanceResolution" src/specify_cli/constitution/`

## Subtasks & Detailed Guidance

### Subtask T028 – Extend GovernanceResolution Fields

**Purpose**: Add fields to express the full transitive closure of governance artifacts selected for a profile.

**Steps**:
1. In `src/specify_cli/constitution/resolver.py` (~lines 31-40), add new fields:
   ```python
   @dataclass(frozen=True)
   class GovernanceResolution:
       """Resolved governance activation result."""
       paradigms: list[str]
       directives: list[str]
       tools: list[str]
       template_set: str
       metadata: dict[str, str]
       diagnostics: list[str] = field(default_factory=list)
       # NEW profile-aware fields
       tactics: list[str] = field(default_factory=list)
       styleguides: list[str] = field(default_factory=list)
       toolguides: list[str] = field(default_factory=list)
       procedures: list[str] = field(default_factory=list)
       profile_id: str | None = None
       role: str | None = None
   ```
2. New fields default to empty/None for backwards compatibility
3. Existing code that constructs `GovernanceResolution` continues to work (keyword args with defaults)

**Files**: `src/specify_cli/constitution/resolver.py`
**Parallel?**: Yes — can proceed in parallel with T029 and T032

### Subtask T029 – Add agent_profile and agent_role to ConstitutionInterview

**Purpose**: Allow the interview to carry agent profile context so the compiler can use it.

**Steps**:
1. In `src/specify_cli/constitution/interview.py` (~lines 55-92), add optional fields:
   ```python
   @dataclass(frozen=True)
   class ConstitutionInterview:
       mission: str
       profile: str
       answers: dict[str, str]
       selected_paradigms: list[str]
       selected_directives: list[str]
       available_tools: list[str]
       agent_profile: str | None = None   # NEW
       agent_role: str | None = None      # NEW
   ```
2. Update `to_dict()` to include new fields:
   ```python
   def to_dict(self) -> dict[str, object]:
       d = {
           "schema_version": "1.0.0",
           # ... existing fields ...
       }
       if self.agent_profile is not None:
           d["agent_profile"] = self.agent_profile
       if self.agent_role is not None:
           d["agent_role"] = self.agent_role
       return d
   ```
3. Update `from_dict()` to read new fields with None defaults:
   ```python
   agent_profile = data.get("agent_profile")
   agent_role = data.get("agent_role")
   return cls(
       # ... existing fields ...
       agent_profile=str(agent_profile) if agent_profile else None,
       agent_role=str(agent_role) if agent_role else None,
   )
   ```

**Files**: `src/specify_cli/constitution/interview.py`
**Parallel?**: Yes — can proceed in parallel with T028

### Subtask T030 – Implement resolve_governance_for_profile()

**Purpose**: Core function that loads an agent profile, extracts its directive references, merges with interview selections, and produces a profile-aware `GovernanceResolution`.

**Steps**:
1. In `src/specify_cli/constitution/resolver.py`, add:
   ```python
   def resolve_governance_for_profile(
       profile_id: str,
       role: str | None,
       doctrine_service: DoctrineService,
       interview: ConstitutionInterview,
   ) -> GovernanceResolution:
       """Compile governance resolution for a specific agent profile."""
       # 1. Load profile
       profile = doctrine_service.agent_profiles.resolve_profile(profile_id)
       if profile is None:
           raise ValueError(
               f"Agent profile '{profile_id}' not found. "
               f"Available profiles: {', '.join(p.id for p in doctrine_service.agent_profiles.list_all())}"
           )
       
       # 2. Extract directive references from profile
       profile_directive_ids = [
           ref.code for ref in profile.directive_references
       ]
       
       # 3. Merge with interview selections (union, profile first)
       interview_directive_ids = interview.selected_directives or []
       merged_directives = list(dict.fromkeys(
           profile_directive_ids + interview_directive_ids
       ))  # Preserves order, removes duplicates
       
       # 4. Run transitive resolution
       from specify_cli.constitution.reference_resolver import resolve_references_transitively
       graph = resolve_references_transitively(merged_directives, doctrine_service)
       
       # 5. Build GovernanceResolution
       diagnostics = []
       for ref_type, ref_id in graph.unresolved:
           diagnostics.append(f"Unresolved {ref_type}: {ref_id}")
       
       return GovernanceResolution(
           paradigms=interview.selected_paradigms or [],
           directives=graph.directives,
           tools=interview.available_tools or [],
           template_set="default",
           metadata={
               "profile_source": profile_id,
               "directives_source": "profile+interview",
           },
           diagnostics=diagnostics,
           tactics=graph.tactics,
           styleguides=graph.styleguides,
           toolguides=graph.toolguides,
           procedures=graph.procedures,
           profile_id=profile_id,
           role=role,
       )
   ```
2. Import `DoctrineService` with TYPE_CHECKING guard
3. Verify `profile.directive_references` attribute exists — check `src/doctrine/agent_profiles/profile.py`

**Files**: `src/specify_cli/constitution/resolver.py`
**Parallel?**: No — depends on T028 (GovernanceResolution fields)

### Subtask T031 – Wire Profile-Aware Path in Compiler

**Purpose**: When the interview has `agent_profile` set, route through profile-aware compilation.

**Steps**:
1. In `compile_constitution()` in `compiler.py`, after catalog setup:
   ```python
   # Profile-aware compilation path
   if interview.agent_profile and doctrine_service is not None:
       from specify_cli.constitution.resolver import resolve_governance_for_profile
       resolution = resolve_governance_for_profile(
           profile_id=interview.agent_profile,
           role=interview.agent_role,
           doctrine_service=doctrine_service,
           interview=interview,
       )
       # Use resolution to build references and render
       selected_directives = resolution.directives
       # ... wire resolution into markdown rendering ...
   elif interview.agent_profile and doctrine_service is None:
       diagnostics.append(
           "Profile-aware compilation requested but DoctrineService unavailable. "
           "Falling back to standard compilation."
       )
   ```
2. Ensure the profile-aware path produces the same `CompiledConstitution` structure as the standard path
3. The rendered markdown should indicate which profile was used

**Files**: `src/specify_cli/constitution/compiler.py`
**Parallel?**: No — depends on T030

### Subtask T032 – Create generate-for-agent CLI Subcommand

**Purpose**: Add `spec-kitty constitution generate-for-agent` command that compiles a constitution for a specific agent profile.

**Steps**:
1. Locate the constitution CLI module — likely `src/specify_cli/cli/commands/constitution.py` or similar
2. Add new subcommand:
   ```python
   @app.command(name="generate-for-agent")
   def generate_for_agent(
       profile: Annotated[str, typer.Option("--profile", help="Agent profile ID (e.g., implementer, reviewer)")],
       role: Annotated[str | None, typer.Option("--role", help="Agent role (optional)")] = None,
       mission: Annotated[str, typer.Option("--mission", help="Mission type")] = "software-dev",
       output: Annotated[Path | None, typer.Option("--output", "-o", help="Output file path")] = None,
   ) -> None:
       """Generate a constitution tailored to a specific agent profile.
       
       This command loads the agent profile, traces its directive references
       transitively, and compiles a governance document containing only the
       rules relevant to that profile and role.
       
       Examples:
           spec-kitty constitution generate-for-agent --profile reviewer
           spec-kitty constitution generate-for-agent --profile implementer --role lead --output constitution-impl.md
       """
       # 1. Load interview (existing or create minimal)
       # 2. Set interview.agent_profile = profile, interview.agent_role = role
       # 3. Initialize DoctrineService
       # 4. Call compile_constitution() with doctrine_service and interview
       # 5. Write output
   ```
3. Handle error when DoctrineService can't be initialized:
   ```python
   try:
       service = DoctrineService(shipped_root=..., project_root=...)
   except Exception as e:
       console.print(f"[red]Error:[/red] Profile-aware compilation requires doctrine assets: {e}")
       raise typer.Exit(1)
   ```

**Files**: `src/specify_cli/cli/commands/constitution.py` (or equivalent)
**Parallel?**: Yes — can scaffold alongside T028/T029 (just needs stubs)

## Test Strategy

- Unit tests for `resolve_governance_for_profile()`: mock profile with known directives → verify resolution
- Unit tests for extended `GovernanceResolution`: verify new fields populated
- Unit tests for extended `ConstitutionInterview`: verify `to_dict()`/`from_dict()` round-trip with new fields
- CLI test: `generate-for-agent --profile reviewer` → verify output contains profile-specific content
- Regression: `pytest tests/specify_cli/constitution/ -v`

## Risks & Mitigations

- **Profile model API**: `directive_references` attribute may differ from expected → verify from source
- **Existing `--profile` flag on `generate`**: Different semantics (interview profile vs agent profile) → separate subcommand avoids confusion
- **DoctrineService initialization**: May fail if doctrine assets are missing → informative error message

## Review Guidance

- Verify `GovernanceResolution` new fields default correctly for existing callers
- Verify `ConstitutionInterview` serialisation preserves new fields
- Verify profile directives appear before interview directives in merged output
- Verify `generate-for-agent` subcommand is discoverable (`spec-kitty constitution --help`)
- Run `pytest tests/specify_cli/constitution/ -v` — 0 failures

## Activity Log

- 2026-03-08T10:13:04Z – system – lane=planned – Prompt created.
- 2026-03-09T06:11:32Z – codex:gpt-5:implementer:implementer – shell_pid=197930 – lane=for_review – Implementation complete: profile-aware governance compilation, CLI, and tests.
- 2026-03-09T06:12:55Z – codex:gpt-5:reviewer:reviewer – shell_pid=197930 – lane=done – Reviewed: no blocking findings in profile-aware governance implementation.
