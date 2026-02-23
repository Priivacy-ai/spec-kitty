# 2.x Glossary System

## Living Glossary Structure

2.x glossary content is organized by context domain:

1. `glossary/README.md`
2. `glossary/contexts/*.md`

Current domains include execution, orchestration, governance, identity, doctrine, dossier, lexical, system-events, and technology-foundations.

## Term Lifecycle

1. New terms are added as `candidate`.
2. Candidate terms can be refined through glossary curation rounds.
3. Promotion to canonical is controlled by Human-in-Charge governance.

Doctrine artifacts for this flow:

1. `src/doctrine/tactics/glossary-curation-interview.tactic.yaml`
2. `src/doctrine/styleguides/writing/kitty-glossary-writing.styleguide.yaml`

## Runtime Integration

Glossary checks are integrated into mission primitive execution via:

1. `src/doctrine/missions/glossary_hook.py`
2. `src/doctrine/missions/primitives.py`
3. Compatibility import path: `src/specify_cli/missions/glossary_hook.py`

Hook behavior is metadata/config driven with enabled-by-default semantics.

## Validation Coverage

1. Link/anchor integrity for context docs: `tests/doctrine/test_glossary_link_integrity.py`
2. Glossary hook behavior: `tests/doctrine/missions/test_glossary_hook.py`
3. Primitive context strictness/enablement behavior: `tests/doctrine/missions/test_primitives.py`
