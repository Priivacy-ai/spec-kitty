# Quickstart: Glossary Semantic Integrity Runtime

**Feature**: 041-mission-glossary-semantic-integrity
**Date**: 2026-02-16
**Audience**: Mission authors, developers using spec-kitty 2.x

## Overview

This guide shows how to use the glossary semantic integrity runtime to enforce semantic consistency in mission execution.

**What it does**:
- Automatically extracts domain terms from mission step inputs/outputs
- Resolves terms against a 4-tier scope hierarchy
- Detects semantic conflicts (unknown, ambiguous, inconsistent, unresolved critical)
- Blocks LLM generation on high-severity conflicts
- Prompts for interactive clarification with checkpoint/resume

**Default behavior**: Checks enabled by default (opt-out model), `medium` strictness (warn broadly, block only high-severity).

---

## Quick Start (5 minutes)

### 1. Install spec-kitty 2.x

```bash
pip install --upgrade spec-kitty-cli>=2.0.0
```

### 2. (Optional) Configure strictness mode

```bash
# Edit .kittify/config.yaml
glossary:
  strictness: medium  # off | medium | max
```

**Modes**:
- `off`: No enforcement (skip all checks)
- `medium` (default): Warn broadly, block only high-severity conflicts
- `max`: Block any unresolved conflict

### 3. (Optional) Create seed files

```bash
mkdir -p .kittify/glossaries
```

**team_domain.yaml** (example):
```yaml
# Team-specific terminology
terms:
  - surface: workspace
    definition: Git worktree directory for a work package
    confidence: 1.0
    status: active

  - surface: WP
    definition: Work package (execution slice inside a mission)
    confidence: 1.0
    status: active
```

**Supported scopes**:
- `spec_kitty_core.yaml`: Spec Kitty canonical terms
- `team_domain.yaml`: Team-specific terms
- `audience_domain.yaml`: Audience-specific terms
- `mission_local`: Generated at runtime (not a seed file)

### 4. Run a mission step

```bash
spec-kitty specify "Add user authentication"
```

**What happens**:
1. Extraction middleware extracts terms from your input
2. Semantic check resolves terms against scope hierarchy
3. If conflict detected: generation gate blocks, clarification prompt appears
4. You resolve conflict, step resumes from checkpoint

---

## Common Workflows

### Mission Author: Enable glossary checks for a custom primitive

Edit `mission.yaml` (mission config):

```yaml
mission_type: custom
steps:
  - id: step-design
    primitive: design
    glossary_check: enabled  # Enable glossary checks for this step
    glossary_watch_terms:    # Explicit terms to track
      - "authentication"
      - "session"
      - "token"
    glossary_fields:         # Which input fields to scan
      - "requirements"
      - "constraints"
```

**Metadata hints**:
- `glossary_check`: `enabled` | `disabled` (default: enabled unless strictness=off)
- `glossary_watch_terms`: Explicit terms to extract (highest confidence)
- `glossary_aliases`: Synonyms (e.g., `{"WP": "work package"}`)
- `glossary_exclude_terms`: Common words to ignore (e.g., `["the", "and"]`)
- `glossary_fields`: Which input/output fields to scan

---

### Developer: Resolve a semantic conflict interactively

**Scenario**: You run `/spec-kitty.plan` and encounter an ambiguous term.

**CLI output**:
```
🔴 High-severity conflict: "workspace"

Term: workspace
Context: "The workspace contains implementation files"
Scope: team_domain (2 matches)

Candidate senses:
1. [team_domain] Git worktree directory for a work package (confidence: 0.9)
2. [team_domain] VS Code workspace configuration file (confidence: 0.7)

Select: 1-2 (candidate), C (custom sense), D (defer to async)
>
```

**Your choices**:
- **1-2**: Select a candidate (resolves immediately, step resumes)
- **C**: Provide custom definition (prompts for free text)
- **D**: Defer to async (conflict logged, generation stays blocked, you can resolve later)

**Example resolution**:
```
> 1
✅ Resolved: workspace = Git worktree directory for a work package

Resuming from checkpoint...
Generation proceeding.
```

---

### Operator: Adjust strictness for different environments

**Local development** (fast iteration, no blocking):
```bash
spec-kitty --strictness off specify "Quick prototype"
```

**CI pipeline** (warn broadly, block high-severity):
```bash
spec-kitty --strictness medium plan  # Default mode
```

**Production** (block any unresolved conflict):
```bash
spec-kitty --strictness max specify "Critical feature"
```

**Precedence**: runtime override > step metadata > mission config > global config

---

## Advanced Usage

### Defer conflict resolution to async mode

**Interactive**:
```
Select: 1-2 (candidate), C (custom sense), D (defer to async)
> D

⚠️ Conflict deferred to async resolution.
   Conflict ID: uuid-1234-5678
   Generation remains blocked.

You can resolve this conflict later:
  - In SaaS decision inbox (when available)
  - Via CLI: spec-kitty glossary resolve uuid-1234-5678
```

**Non-interactive mode** (CI):
Conflicts auto-defer, exit with error code:
```bash
spec-kitty plan  # Non-interactive
# Exit code 1: Conflicts deferred
```

---

### Resume after conflict resolution

**Scenario**: You deferred a conflict, resolved it later, now want to resume.

**CLI**:
```bash
spec-kitty resume --retry-token uuid-1234-5678
```

**What happens**:
1. Resume middleware loads `StepCheckpointed` event
2. Verifies input_hash matches current inputs
3. If changed: prompts for confirmation ("Context may have changed. Proceed?")
4. Restores strictness, scope_refs from checkpoint
5. Loads updated glossary state from events
6. Resumes from cursor (`pre_generation_gate`)

---

### View glossary state

**List active terms in a scope**:
```bash
spec-kitty glossary list --scope team_domain
```

**Output**:
```
Team Domain Glossary (v3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Term          Definition                        Confidence  Status
────────────────────────────────────────────────────────────────
workspace     Git worktree directory            1.0         active
WP            Work package                      1.0         active
mission       Purpose-specific workflow         0.9         active
────────────────────────────────────────────────────────────────
```

**View conflict history**:
```bash
spec-kitty glossary conflicts --mission 041-mission
```

**Output**:
```
Conflict History (041-mission)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Conflict ID        Term         Type        Severity  Resolved
────────────────────────────────────────────────────────────────
uuid-1234-5678     workspace    ambiguous   high      ✅ 2026-02-16
uuid-9999-0000     auth         unknown     medium    ⏳ pending
────────────────────────────────────────────────────────────────
```

---

## Troubleshooting

### "Generation blocked by semantic conflict" but I don't see a prompt

**Cause**: Non-interactive mode (CI environment) auto-defers conflicts.

**Solution**:
1. Check conflict log: `spec-kitty glossary conflicts`
2. Resolve manually: `spec-kitty glossary resolve <conflict_id>`
3. Or: Run in interactive mode

---

### Checkpoint resume fails with "Context changed"

**Cause**: Step inputs changed between conflict and resolution.

**Example**:
```
⚠️ Context may have changed since conflict.
   Input hash: abc123... (checkpoint)
              vs.
              def456... (current)

Proceed with resolution? [y/N]
```

**Options**:
- **Y**: Resume anyway (risk: glossary may not match new context)
- **N**: Abort resume, re-run step from scratch

---

### Too many clarification prompts (UX fatigue)

**Cause**: Strictness too aggressive or too many unknown terms.

**Solution 1**: Reduce strictness
```bash
spec-kitty --strictness medium plan  # Instead of max
```

**Solution 2**: Add seed file with known terms
```yaml
# .kittify/glossaries/team_domain.yaml
terms:
  - surface: authentication
    definition: User identity verification process
  - surface: session
    definition: Stateful user connection
```

**Solution 3**: Use metadata hints to pre-populate
```yaml
# mission.yaml
steps:
  - id: step-design
    glossary_watch_terms:
      - "authentication"
      - "session"
```

---

### Glossary checks slow down mission execution

**Cause**: Term extraction is heavyweight or LLM-based.

**Check**: Current extraction uses deterministic heuristics (< 100ms per step). If slow:
1. Verify no LLM extraction in hot path (should be async enrichment only)
2. Check seed file size (large seed files slow loading)
3. Profile with `--debug` flag

**Mitigation**: Use `--strictness off` for local dev, `medium` for CI.

---

## Best Practices

### 1. Start with seed files for known terms

**Why**: Reduces initial conflict noise, improves UX.

**How**: Create `.kittify/glossaries/team_domain.yaml` with 5-10 core terms.

```yaml
terms:
  - surface: workspace
    definition: Git worktree directory for a work package
    confidence: 1.0

  - surface: mission
    definition: Purpose-specific workflow machine
    confidence: 1.0
```

---

### 2. Use metadata hints for critical terms

**Why**: Metadata hints have highest confidence (no false positives).

**How**: Add `glossary_watch_terms` to step definitions.

```yaml
steps:
  - id: step-specify
    glossary_watch_terms:
      - "workspace"
      - "mission"
      - "primitive"
```

---

### 3. Tune strictness per environment

**Why**: Balance quality (strict) vs velocity (lenient).

**How**:
- **Local dev**: `strictness: off` (fast iteration)
- **CI**: `strictness: medium` (catch high-severity only)
- **Production**: `strictness: max` (zero ambiguity)

---

### 4. Review conflict history periodically

**Why**: Identifies frequently conflicting terms (candidates for seed file).

**How**:
```bash
spec-kitty glossary conflicts --mission 041-mission
# Add frequently conflicting terms to seed file
```

---

### 5. Use defer for non-blocking workflow

**Why**: Don't block mission progress on non-critical conflicts.

**How**: Defer low/medium severity conflicts, resolve async later.

```
Select: 1-2 (candidate), C (custom sense), D (defer to async)
> D
```

---

## FAQ

**Q: Is glossary checking enabled by default?**
A: Yes (FR-020). Checks run by default unless strictness=off or primitive metadata disables them.

**Q: Can I disable glossary checks globally?**
A: Yes. Set `strictness: off` in `.kittify/config.yaml`.

**Q: Does this slow down mission execution?**
A: Minimal (<100ms per step). Extraction uses deterministic heuristics, no LLM in hot path.

**Q: Can I use this in CI/CD pipelines?**
A: Yes. Non-interactive mode auto-defers conflicts, exits with error code if blocked.

**Q: What happens if I defer a conflict?**
A: Generation stays blocked. Resolve later via SaaS decision inbox or CLI, then resume.

**Q: Can I edit seed files manually?**
A: Yes. Edit `.kittify/glossaries/*.yaml`, restart mission. Changes take effect on next scope activation.

**Q: Where is glossary state stored?**
A: Event log only (JSONL). No side-channel state files (Feature 007 requirement).

**Q: Can I replay a mission with glossary evolution?**
A: Yes. Event log is deterministic. Same events → same glossary state → same generation gate outcomes.

---

## Programmatic Usage

### Running the pipeline directly

```python
from pathlib import Path
from specify_cli.glossary.pipeline import create_standard_pipeline
from specify_cli.glossary.strictness import Strictness
from specify_cli.glossary.exceptions import BlockedByConflict
from specify_cli.missions.primitives import PrimitiveExecutionContext

# Create execution context
context = PrimitiveExecutionContext(
    step_id="specify-001",
    mission_id="my-mission",
    run_id="run-001",
    inputs={"description": "Process workspace artifacts"},
    metadata={"glossary_check": "enabled"},
    config={},
)

# Run with max strictness
pipeline = create_standard_pipeline(
    repo_root=Path.cwd(),
    runtime_strictness=Strictness.MAX,
    interaction_mode="non_interactive",
)

try:
    result = pipeline.process(context)
    print(f"Extracted {len(result.extracted_terms)} terms")
    print(f"Conflicts: {len(result.conflicts)}")
except BlockedByConflict as e:
    print(f"Blocked by {len(e.conflicts)} conflict(s)")
    for c in e.conflicts:
        print(f"  - {c.term}: {c.conflict_type} ({c.severity})")
```

### Using the glossary CLI

```bash
# List all terms across scopes
spec-kitty glossary list

# Filter by scope and status
spec-kitty glossary list --scope team_domain --status active

# JSON output for scripting
spec-kitty glossary list --json

# View conflict history
spec-kitty glossary conflicts

# View only unresolved conflicts
spec-kitty glossary conflicts --unresolved

# Resolve a conflict interactively
spec-kitty glossary resolve <conflict-id>
```

### Disabling glossary checks for a step

```python
context = PrimitiveExecutionContext(
    step_id="skip-check",
    mission_id="my-mission",
    run_id="run-001",
    inputs={"description": "..."},
    metadata={"glossary_check": False},  # Disables checks
    config={},
)
```

## Troubleshooting

**Problem: Pipeline blocks unexpectedly**
- Check strictness mode: `grep strictness .kittify/config.yaml`
- Use `--strictness off` to disable temporarily
- Use `spec-kitty glossary conflicts --unresolved` to see blocking conflicts

**Problem: Term not recognized**
- Add to seed file in `.kittify/glossaries/<scope>.yaml`
- Ensure `status: active` and `confidence: 1.0`
- Restart mission for changes to take effect

**Problem: Too many false positives**
- Switch from `max` to `medium` strictness
- Add explicit terms to seed files with high confidence
- Defer non-critical conflicts with `D` during interactive prompts

**Problem: Events not persisting**
- Check that `.kittify/events/glossary/` directory is writable
- Verify `spec-kitty-events` package is installed: `pip show spec-kitty-events`
- Without the package, events are logged but not persisted to JSONL

---

## See Also

- [plan.md](plan.md) - Implementation plan with technical details
- [data-model.md](data-model.md) - Entity definitions and relationships
- [contracts/events.md](contracts/events.md) - Canonical event schemas
- [contracts/middleware.md](contracts/middleware.md) - Middleware interface contracts
- Feature 007 spec: `/Users/robert/ClaudeCowork/Spec-Kitty-Cowork/spec-kitty-planning/product-ideas/prd-mission-glossary-semantic-integrity-v1.md`
