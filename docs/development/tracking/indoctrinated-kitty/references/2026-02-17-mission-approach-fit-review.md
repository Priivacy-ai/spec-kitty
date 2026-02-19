# Review: Mission vs Approach Fit (Spec Kitty x AAD Doctrine)

**Date:** 2026-02-17  
**Scope:**
- `work/ideas/spec-kitty-doctrine-integration-ideation.md`
- `.kittify/memory/contexts/orchestration.glossary.yml`
- `.kittify/memory/contexts/governance.glossary.yml`
- `/home/stijn/Documents/_code/_publications/quickstart_agent-augmented-development/doctrine/*`

## Findings (ordered by severity)

1. **High: Current proposal redefines `Mission` in a way that conflicts with the canonical Spec Kitty glossary.**  
   - Proposal: “Mission = structural recipe / step graph” (`work/ideas/spec-kitty-doctrine-integration-ideation.md:32`, `work/ideas/spec-kitty-doctrine-integration-ideation.md:63`, `work/ideas/spec-kitty-doctrine-integration-ideation.md:148`).
   - Glossary: `Mission` is currently a “domain-specific behavioral adapter” configuring prompts, validation rules, and artifact structures (`.kittify/memory/contexts/orchestration.glossary.yml:81`).
   - Impact: This is a core semantic collision; if unchanged, docs/code/governance language will drift and create ambiguity in architecture and implementation.

2. **High: `Approach` semantics are internally inconsistent between AAD stack docs and AAD approaches corpus.**  
   - AAD doctrine stack says approaches are conceptual framing, not execution (`DOCTRINE_STACK.md:43-55`).
   - AAD approaches README and examples describe step-by-step operational guides (`approaches/README.md:3`, `approaches/README.md:23-25`, plus procedural content in `approaches/spec-driven-development.md`).
   - Spec Kitty glossary currently treats Approach as “how to think” (not step execution) and Tactic as “how to execute” (`.kittify/memory/contexts/governance.glossary.yml:39`, `.kittify/memory/contexts/governance.glossary.yml:59`).
   - Impact: Importing AAD approaches as-is will blur Approach vs Tactic boundaries and may duplicate/compete with Mission behavior.

3. **Medium: The proposal omits explicit compatibility mapping to existing Spec Kitty runtime primitives.**  
   - Missing direct mapping from proposed `step.yaml` / `recipe.yaml` to existing lifecycle concepts like phase/lane/command templates/work package orchestration in current glossary terms (`.kittify/memory/contexts/orchestration.glossary.yml:72-100`).
   - Impact: Architecture reads coherent, but migration and implementation sequencing remain under-specified.

4. **Medium (positive): Separation-of-concerns direction is strong and aligned with governance intent.**  
   - The idea “Spec Kitty decides what happens next; Doctrine decides how execution is shaped” is consistent with the desired orchestration vs governance split (`work/ideas/spec-kitty-doctrine-integration-ideation.md:181-185`).
   - This aligns with your existing governance glossary trajectory (Approach/Tactic/Directive/Constitution stack).

## Impressions

- The integration direction is promising, but the current terminology choices are the primary risk.
- The biggest correction needed is a stable, non-overlapping taxonomy before any structural refactor.
- Your instinct about overlap between Missions and Approaches is correct: right now they partially occupy the same semantic space unless you normalize definitions and artifact responsibilities.

## Recommended normalization path

1. **Freeze terminology first (glossary-first).**
   - Decide one canonical meaning for `Mission` and one for `Approach`.
   - If you want Mission to become structural recipe, explicitly version and migrate glossary language.

2. **Split AAD approaches into two buckets before import.**
   - Conceptual approaches (keep as `Approach`).
   - Procedural “approaches” (reclassify as `Tactic` or `Playbook`).

3. **Introduce an explicit mapping table artifact.**
   - `Current Spec Kitty concept -> Proposed concept -> Source artifact -> Migration impact`.
   - Include at least: Mission, Phase, Slash Command, Work Package, Approach, Tactic, Directive, Constitution.

4. **De-risk with a compatibility layer.**
   - Keep current Mission semantics for now.
   - Add a new experimental concept (e.g., `Workflow Recipe`) instead of redefining `Mission` immediately.

## Open questions

- Do you want `Mission` to remain behavior/config centric, or intentionally migrate it to structural recipe semantics in v2.x?
- Should AAD `approaches/` be curated (selected subset) or transformed (reclassified) before adoption?
- Is Doctrine Pack intended to be user-selected per project (constitution-level) or per feature/work package at runtime?
