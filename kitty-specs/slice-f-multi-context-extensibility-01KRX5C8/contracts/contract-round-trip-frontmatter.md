# Contract — Contract Round-Trip Frontmatter

> Mission: `slice-f-multi-context-extensibility-01KRX5C8`
> Closes: FR-140, FR-141 | Companions: [ratchet-baseline-format.md](ratchet-baseline-format.md), [org-drg-schema.md](org-drg-schema.md), [workflow-sequence-schema.md](workflow-sequence-schema.md)

The contract round-trip backstop closes Process Gap 1 at the architectural-test level. Today, Step 3.5 of the runtime-review skill (the Contract Round-Trip Check) is a human-only checklist item — a reviewer who skips it is not challenged. This contract turns that checklist into a CI gate.

The mechanism is **YAML codeblock frontmatter** on every example in `kitty-specs/*/contracts/*.md`. The frontmatter declares the Pydantic model the codeblock should parse against AND the expected outcome (`valid` or `invalid`). A walker (`tests/contract/test_example_round_trip.py`) exercises every tagged codeblock and asserts the outcome matches.

---

## Input Contract

### Frontmatter convention on YAML codeblocks

Every YAML codeblock in `kitty-specs/<mission>/contracts/*.md` that documents a parseable contract example MUST be preceded by a frontmatter comment of the shape:

```
# pydantic_model: <module.dotted.path.ClassName>
# expect: valid | invalid
```

Example:

````markdown
```yaml
# pydantic_model: charter.drg.OrgDRGFragment
# expect: valid
pack_name: acme-compliance
source_kind: local_path
...
```
````

### Recognised frontmatter keys

| Key | Type | Required | Purpose |
|---|---|---|---|
| `pydantic_model` | `str` (dotted import path) | yes | The Pydantic model to instantiate via `model_validate(yaml.safe_load(...))`. MUST be importable from the running test process |
| `expect` | `Literal["valid", "invalid"]` | yes | The expected outcome. `valid` ⇒ `model_validate` MUST succeed; `invalid` ⇒ MUST raise `pydantic.ValidationError` |
| `expect_message` | `str` (substring match) | no | When `expect: invalid`, optionally pin a substring that MUST appear in the raised exception's message |

### Codeblocks NOT subject to round-trip

In a **non-legacy** contract, discovery is block-level: every YAML codeblock must either carry the `pydantic_model:` frontmatter (executed) OR carry an explicit non-executable marker as a comment line — `# round-trip: skip: <reason>` — with a mandatory reason. A block carrying neither fails the gate on that specific block, so a tagged sibling can never silently mask a forgotten tag. The skip marker is the home for documentation prose, shape sketches, CI-wiring snippets, and non-Pydantic operator config.

In a **legacy** contract (tracked in the allowlist below), the gate keeps file-level leniency: untagged codeblocks are skipped with a warning rather than failing, pending backfill.

### Legacy contract allowlist (FR-141)

Contracts from missions predating this convention live under an allowlist tracked in `tests/architectural/_baselines.yaml`:

```yaml
# round-trip: skip: baseline-format illustration with an <N> placeholder, not a Pydantic payload
test_example_round_trip:
  legacy_contract_allowlist: <N>
```

Files in this allowlist warn rather than fail when their codeblocks lack frontmatter or when an example's `expect:` claim cannot be verified. The allowlist participates in the FR-110 baseline — it shrinks over time as legacy missions backfill frontmatter (or get tickets opened to do so).

---

## Output Contract

### Walker behaviour — `tests/contract/test_example_round_trip.py`

```python
from pathlib import Path
import importlib
import yaml
import re

FRONTMATTER_RE = re.compile(r"^# pydantic_model: (?P<model>[\w\.]+)\s*\n# expect: (?P<expect>valid|invalid)", re.MULTILINE)

def _discover_examples():
    """Walk kitty-specs/*/contracts/*.md and yield (file, model, expect, payload)."""
    for contract_md in Path("kitty-specs").glob("*/contracts/*.md"):
        text = contract_md.read_text()
        # Extract every fenced ```yaml ...``` block; for each, look at the first two non-blank lines for frontmatter
        for codeblock in _iter_yaml_codeblocks(text):
            frontmatter = FRONTMATTER_RE.search(codeblock)
            if not frontmatter:
                continue
            model_path = frontmatter.group("model")
            expect = frontmatter.group("expect")
            payload = _strip_frontmatter(codeblock)
            yield contract_md, model_path, expect, payload

@pytest.mark.parametrize("contract_md,model_path,expect,payload", list(_discover_examples()))
def test_contract_example_round_trip(contract_md, model_path, expect, payload):
    module_name, _, class_name = model_path.rpartition(".")
    module = importlib.import_module(module_name)
    model = getattr(module, class_name)
    parsed = yaml.safe_load(payload)

    if expect == "valid":
        model.model_validate(parsed)  # MUST succeed
    else:
        with pytest.raises(pydantic.ValidationError):
            model.model_validate(parsed)
```

### Failure shape

When a `expect: valid` codeblock fails to parse:

> **FAIL**: `kitty-specs/<mission>/contracts/<file>.md` (codeblock #N) declared `pydantic_model: <Model>, expect: valid` but `model_validate` raised: `<exception text>`.

When a `expect: invalid` codeblock parses cleanly:

> **FAIL**: `kitty-specs/<mission>/contracts/<file>.md` (codeblock #N) declared `pydantic_model: <Model>, expect: invalid` but `model_validate` succeeded.

When a `pydantic_model:` references a non-importable model:

> **FAIL**: `kitty-specs/<mission>/contracts/<file>.md` (codeblock #N) declared `pydantic_model: <bad.path.Model>` but the module is not importable: `<ImportError text>`.

### Legacy allowlist behaviour

For files in the legacy allowlist, FAIL conditions become WARN conditions and the test passes — but the legacy file's path is reported in a pytest warning so the operator sees the unwound work.

---

## Failure modes

| Trigger | Reporter | Operator message |
|---|---|---|
| A new contract's `expect: valid` example doesn't actually parse | `test_example_round_trip` FAIL | "Contract `<file>` codeblock #N declares `expect: valid` but `model_validate` raised: `<exc>`. Fix the example OR the model" |
| A new contract's `expect: invalid` example DOES parse | `test_example_round_trip` FAIL | "Contract `<file>` codeblock #N declares `expect: invalid` but `model_validate` succeeded. Either the example was meant to be valid OR the model lost a validator" |
| A contract file in `kitty-specs/<mission>/contracts/` has YAML codeblocks but none carry frontmatter | If the contract is post-Slice-F (not in legacy allowlist) — `test_example_round_trip` FAIL | "Contract `<file>` has unfronted YAML codeblocks. Add `# pydantic_model:` and `# expect:` frontmatter or move the file to the legacy allowlist (`_baselines.yaml:test_example_round_trip.legacy_contract_allowlist`)" |
| A contract is in the legacy allowlist but no longer exists | `test_ratchet_baselines` FAIL with stale-allowlist message | "Stale legacy contract `<file>` in allowlist. Remove from `_baselines.yaml`" |

---

## Backward compatibility guarantee

- **Pre-Slice-F contract files** (every contract under `kitty-specs/<mission>/contracts/` predating this mission) participate via the legacy allowlist (FR-141). The allowlist is initially sized by WP03's discovery sweep (RR-7 mitigation).
- **Slice F's own contracts** (the 6 contracts in this directory) DOGFOOD the convention — every `expect: valid` and `expect: invalid` example above is exercised at WP03 acceptance.
- The walker does NOT crash on contracts with NO YAML codeblocks (e.g. prose-only contracts) — they are simply skipped.

---

## Example use of `expect: invalid` for negative testing

```yaml
# pydantic_model: charter.drg.OrgDRGFragment
# expect: invalid
# expect_message: "unknown kind"
pack_name: acme-compliance
source_kind: local_path
source_ref: ../acme-org-doctrine
layer_index: 1
provenance_marker: org
nodes:
  - id: bogus
    kind: not-a-real-kind
    title: "Bogus"
edges: []
```

This codeblock asserts that the org-DRG schema correctly REJECTS unknown kinds (C-009 enforcement). The walker:

1. Imports `charter.drg.OrgDRGFragment`.
2. Parses the YAML payload.
3. Calls `model.model_validate(payload)`.
4. Asserts that the call raises `pydantic.ValidationError` AND the error message contains `"unknown kind"`.

---

## Charter pinning (optional, FR-303 derivative)

The frontmatter convention itself is documented in `src/specify_cli/upgrade/migrations/README.md` (per Q7 resolution) so new contributors authoring contracts see it before they author. The convention does NOT become a charter rule in this mission; only the ATDD-first discipline (C-011) and burn-down policy (C-004) are charter-pinned.

---

## ATDD anchors

- `tests/contract/test_example_round_trip.py` (FR-140, FR-141; AC-10)
- All 6 Slice F contracts (this directory) — each contains at least one `expect: valid` example, and `contracts/org-drg-schema.md` + `contracts/workflow-sequence-schema.md` each contain at least one `expect: invalid` example for negative testing
- `tests/architectural/test_ratchet_baselines.py` (the legacy-allowlist baseline participates per FR-141)
