# Phase 0 Research: Unify charter activation surfaces

Grounded by the epic-#2519 pre-spec research squad (2026-07-10). The core decision was made at spec time (DM 01KX5SK7); this records the derived design decisions + the open sizing/blast-radius questions the post-plan squad must close.

## Decision 1 — config is the single authority (resolved, DM 01KX5SK7)

- **Decision**: `config.activated_*` is THE activation authority; `references.yaml` + graph + the compiled reference set derive from it; `answers.selected_*` is retired as an activation source.
- **Rationale**: charter Governing Principle #1 (single canonical authority); config is already the runtime SSOT (`PackContext.from_config`) and a superset of the answers-derived set (observed 25 vs 24 directives), so the switch is lossless.
- **Alternatives**: (a) write-through both ledgers + resynthesize, (b) `--resynthesize` flag. Rejected — (a) keeps two authorities; (b) leaves the default dangling. Config-single-authority is the only option that removes a shadow authority.

## Decision 2 — the derivation reads config the way the live resolver does

- **Decision**: IC-01 must resolve `config.activated_*` stems → artefacts via the same `DoctrineService`/DRG resolution the dangler test's live `_compiled_reference_id_suffixes()` uses, so the compiled `references.yaml` includes exactly the config-activated + directive-reachable set.
- **Rationale**: the #2524 dangler was precisely a mismatch between the runtime resolution (which found the artefact) and the compiled set (which didn't). Sourcing the compiled set from the same resolution eliminates the class.
- **Alternatives**: a bespoke config→references walk — rejected (re-introduces a second resolution path, the split-brain this mission kills).

## Decision 3 — parity guard lives in consistency_check, references (not duplicates) freshness

- **Decision**: FR-005's guard extends `charter/consistency_check.py` (config-anchored) to assert config ⇔ references ⇔ graph parity; it references the existing `freshness/computer.py` staleness logic rather than duplicating it.
- **Rationale**: the epic's central cross-contamination risk is two guards with contradictory notions of "authoritative." One config-anchored guard avoids it.

## Open question A — FR-007 (interview → config) sizing [POST-PLAN SQUAD]

Is promoting interview selections into `config.activated_*` a thin "activate the captured selections" step, or does it entangle the interview flow (org-pack pre-fill `apply_org_charter_to_interview`, paradigm selection, `charter generate` compile order)? The spec permits splitting FR-007 to a follow-up if large. **Decision deferred to the post-plan squad + tasks.**

## Open question B — IC-02 answers-consumers audit [POST-PLAN SQUAD]

Which code reads `answers.selected_*` today, and which of those are activation reads (must repoint to config) vs interview-record reads (leave alone)? Research flagged `spdd_reasons/activation.py` as one reader. **A complete grep-audit of `answers.selected_*` / `selected_directives` consumers is required before IC-02 can safely retire the source.**

## Open question C — IC-05 migration reverse-skew [POST-PLAN SQUAD]

Config is the superset *today*, but the migration must handle the reverse: an artefact in `answers.selected_*` but not `config.activated_*` would drop under config-authority. The migration must detect and promote (not silently drop) any answers-only artefact. **Scope of the migration depends on whether such skew exists in real projects.**

## Out of scope (confirmed)

Events (A #2520), scaffold (C #2522), mission-type-as-kind (#2468), cascade engine — all deferred per spec Out of Scope.
