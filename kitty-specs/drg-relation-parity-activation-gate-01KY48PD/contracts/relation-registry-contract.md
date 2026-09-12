# Contract: Relation registry + doc parity

**Owner**: `src/doctrine/drg/models.py` (`Relation`, `RELATION_DESCRIPTIONS`);
`tests/doctrine/drg/test_models.py`; `tests/doctrine/test_relation_doc_parity.py`;
`docs/architecture/doctrine-relationships.md` (the single parity surface)
**Requirements**: FR-005, FR-006, FR-007, FR-008, NFR-003, C-006

## Obligation

1. **Completeness**: `set(RELATION_DESCRIPTIONS) == set(Relation)`; all values non-empty. Enforced by
   `test_models.py` — convert its `== {the 3}` pin to `== set(Relation)` and re-parametrize the
   non-empty sibling over all members.
2. **Distinctness**: `RELATION_DESCRIPTIONS[APPLIES] != RELATION_DESCRIPTIONS[SCOPE]`; each names its
   distinct edge-role (adjudication, not transcription).
3. **Content parity (single surface)**: for every relation, `doctrine-relationships.md` has a dedicated
   `### …` section whose body equals `RELATION_DESCRIPTIONS[relation]` (whitespace-normalized);
   `_SCOPED_RELATIONS` widened 3→15. Enforced by `test_relation_doc_parity.py`.
4. **Prose-only surface**: `docs/context/doctrine.md` extended for reader completeness, **explicitly
   NOT under the parity test** (it deliberately paraphrases).

## Emission-status wording (do not misrepresent)

- `vocabulary`/`refines`/`delegates_to`: 0 edges everywhere → intended-but-dormant.
- `enhances`/`overrides`/`replaces`: 0 in built-in **by design** → org-pack overlay relations; describe
  by actual emission status, not as actively-exercised built-in relations.
- `applies` (1) vs `scope` (157): distinct edge-roles; describe the contrast.

## Constraint

The adjudication describes intent only — **no existing graph edges are rewired** (157 live `scope`
edges make re-classification out of scope, C-006). Update the now-stale "the other twelve are out of
scope / a follow-up" docstrings in `test_relation_doc_parity.py` and the doc's "Tension vocabulary" prose.
