# Tracer: Design Decisions — Charter Authority Flip (M1)

- **DD-1**: CR-01 remap is dict-level in `load_governance_config` (sync.py:262-263), NOT a pydantic `Field(alias)` — the alias remaps silently and fails SC-002 warn-once.
- **DD-2**: Value class `DoctrineSelectionConfig` is KEPT (renamed in M2); only the field key `doctrine`→`charter`.
- **DD-3**: "Pack Default Charter" is the new label for the pack-shipped default (NOT "Active Charter", which ADR 2026-08-22-2 §76 binds to an individual activated artefact). Per #3732 resolution.
- **DD-4**: Baseline store UNTRACKED and never under kitty-specs/ (resolves methodology.md:273 vs :144 contradiction in favour of the M6-archive-gate rationale).
- **DD-5**: The 18 agent-profile `related:` edges are hand-edited authored remainders; only the 2 docs lockfiles are regenerated.
- **DD-6**: charter generate uses the section-update path (compiler.py:515-516), never the whole-doc save (:725).

## Implement log
- (append per decision)

## Post-tasks squad folds (2026-08-28)
- **DD-7 (B2)**: The glossary already carries BOTH `surface: charter` ("a governance document ... synthesizing ... and doctrine") and `surface: doctrine` ("the body of governance artifacts"). Under doctrine->charter this is a duplicate term-ID under extra="forbid". Reconciliation: RETIRE `surface: doctrine`, fold its body-of-artifacts sense into the single canonical `charter` term, drop the "and doctrine" self-reference. Parity test pins exactly ONE `charter` surface. (WP01/T005a)
- **DD-8 (atomicity)**: The 3 intra-docs/context inline links to doctrine.md (orchestration/governance/configuration-project-structure) move into WP01/T003 with the rename — else WP01's own test_glossary_link_integrity gate reds. Heading anchors #doctrine-catalog/#procedure + link text preserved (kept domain vocab).
- **DD-9 (H4)**: test_charter_owner_map_executed asserts ONLY the owner actions M1 performs (glossary flip, Canon, key cutover); graph.yml/context-state.json/synthesis-manifest.yaml are verify-no-op (M1 raises no owner action on them).
- **DD-10 (archive immutability)**: The post-tasks squad's paula-MEDIUM asked to fix a stale line in the ARCHIVED retire-doctrine-term methodology.md (:273, "guard store in M1's mission dir"). Editing an archived mission dossier under kitty-specs/ violates archive immutability (NFR-002 / test_archive_root_byte_identical). Correction NOT applied to the archive; the authoritative rule is recorded here + in DD-4 (untracked, never under kitty-specs/), and should be carried to M2-M6 via a program follow-up, not an archive edit.
