# Quickstart: verifying the Glossary Pack doctrine kind

How to confirm Mission A delivered, without touching the runtime glossary.

## 1. The kind exists and is classified correctly

```python
from doctrine.artifact_kinds import ArtifactKind, CHARTER_KIND_TOKENS
from doctrine.artifact_kinds import _NON_AUGMENTATION_ELIGIBLE_KINDS

assert ArtifactKind.GLOSSARY_PACK.value == "glossary_pack"
assert "glossary-pack" in CHARTER_KIND_TOKENS          # charter-activatable
assert ArtifactKind.GLOSSARY_PACK not in _NON_AUGMENTATION_ELIGIBLE_KINDS
```

## 2. The URN is underscore (hyphen rejected)

```python
from doctrine.drg.models import NodeKind  # + URN builder/validator
# glossary_pack:spec-kitty-core  -> valid
# glossary-pack:spec-kitty-core  -> rejected by the URN regex / prefix==kind.value assertion
```

## 3. The built-in pack loads with all 104 terms

```python
from doctrine.service import DoctrineService
svc = DoctrineService(...)
core = next(p for p in svc.glossary_packs if p.id == "spec-kitty-core")
assert len(core.terms) == 104            # zero-loss migration (NFR-002)
assert isinstance(core.terms[0].confidence, float)   # seed confidence is a float
```

## 4. It resolves as a loaded DRG node + is active by default

```bash
spec-kitty doctor doctrine --json | jq '.glossary_packs'
# built-in spec-kitty-core present, healthy, and active without a manual `charter activate`
```

## 5. Regression safety — runtime untouched

```bash
# The runtime glossary suite and the casing gate stay green (C-003):
pytest tests/architectural/test_glossary_canonical_terms.py tests/architectural/test_no_legacy_terminology.py -q
pytest tests/ -k glossary -q      # existing runtime-glossary tests unaffected
```

## 6. Enforcement fields round-trip (unwired)

Author a pack term with `aliases`/`banned_synonyms` populated, load it, and confirm the values
survive — but note NO gate consumes them in Mission A (that is Mission B).
