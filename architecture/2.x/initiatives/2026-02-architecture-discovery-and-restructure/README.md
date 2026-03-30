# Initiative: 2026-02 Architecture Discovery and Restructure

This initiative captures the architecture discovery process that established
the 2.x system landscape, domain container model, and C4 documentation chain.

## Structure

- `brainstorm_index.md`: original session capture index
- `lineage/`: raw session transcripts from the discovery process
- `user_journey/`: exploratory user journeys developed during discovery
- `dialectics/`: structured trade-off reasoning
- `proposals/`: architecture structure and integration proposals

## Outcome Summary

The discovery process produced the following canonical artifacts:

1. **System Landscape** (`architecture/2.x/00_landscape/README.md`):
   8-domain container model, 6 architectural principles, interaction contracts,
   and dependency rules. This is the north star for all lower-level views.

2. **C4 Alignment Cascade**: Context, Container, and Component views were
   aligned to the landscape framing. All 4 C4 levels are now consistent.

3. **Implementation Mapping** (`architecture/2.x/04_implementation_mapping/README.md`):
   Maps each C4 level to current codebase modules, documents the doctrine stack
   layer model, and identifies as-is vs. target architecture gaps.

4. **Versioned architecture structure** adopted:
   - `architecture/1.x`, `architecture/2.x`, versioned ADRs
   - Initiative lane under `architecture/2.x/initiatives/`
   - 2.x user journey space

5. **Doctrine integration proposal** (`proposals/spec-kitty-doctrine-integration.md`):
   Strategic proposal for deeper doctrine integration. Partially realized through
   the doctrine artifact domain models feature (046).

## Related Canonical Artifacts

- System Landscape: `architecture/2.x/00_landscape/README.md`
- Implementation Mapping: `architecture/2.x/04_implementation_mapping/README.md`
- High-level evaluation: `architecture/README.md`
- Canonical 2.x user journeys: `architecture/2.x/user_journey/`
- Canonical decisions: `architecture/2.x/adr/`
