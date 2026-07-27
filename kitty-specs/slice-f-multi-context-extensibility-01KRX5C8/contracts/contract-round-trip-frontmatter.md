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

Discovery is **block-level** for non-legacy contracts. Each YAML block is
classified independently — tagged (executed), skip-marked (intentionally
non-executable), or neither (a per-block gate failure). A tagged sibling can no
longer mask an untagged block.

```python
FRONTMATTER_RE = re.compile(r"^# pydantic_model: (?P<model>[\w\.]+)\s*\n# expect: (?P<expect>valid|invalid)", re.MULTILINE)
SKIP_MARKER_RE = re.compile(r"^# round-trip: skip:[ \t]*(?P<reason>\S.*)$", re.MULTILINE)

def _classify_yaml_block(block):
    """Return ('execute', info) | ('skip', {'reason': ...}) | ('missing', {})."""
    fm = FRONTMATTER_RE.search(block)
    if fm:                                  # frontmatter wins over a stray skip marker
        return "execute", {"model": fm.group("model"), "expect": fm.group("expect"),
                           "payload": _strip_frontmatter(block)}
    skip = SKIP_MARKER_RE.search(block)
    if skip:                                # mandatory reason; empty reason does NOT match
        return "skip", {"reason": skip.group("reason").strip()}
    return "missing", {}

def _discover_examples():
    """Walk kitty-specs/*/contracts/*.md and yield executable round-trip cases."""
    for contract_md in Path("kitty-specs").glob("*/contracts/*.md"):
        blocks = list(_iter_yaml_codeblocks(contract_md.read_text()))
        for idx, block in enumerate(blocks, start=1):
            kind, info = _classify_yaml_block(block)
            if kind == "execute":
                yield f"{contract_md}::block-{idx}", info["model"], info["expect"], info["payload"]
            elif kind == "missing" and not _is_legacy(contract_md):
                # Non-legacy + neither tagged nor skip-marked -> this block FAILS.
                yield f"{contract_md}::block-{idx}-MISSING_FRONTMATTER", "<MISSING_FRONTMATTER>", "valid", "{}"
            # kind == "skip", or a legacy file's untagged block -> not executed.

@pytest.mark.parametrize("label,model_path,expect,payload", list(_discover_examples()))
def test_contract_example_round_trip(label, model_path, expect, payload):
    if model_path == "<MISSING_FRONTMATTER>":
        pytest.fail(f"{label}: add '# pydantic_model:' frontmatter OR '# round-trip: skip: <reason>'.")
    module_name, _, class_name = model_path.rpartition(".")
    model = getattr(importlib.import_module(module_name), class_name)
    parsed = yaml.safe_load(payload)
    if expect == "valid":
        model.model_validate(parsed)  # MUST succeed
    else:
        with pytest.raises(pydantic.ValidationError):
            model.model_validate(parsed)
```

The ``# round-trip: skip:`` set in non-legacy contracts is itself ratcheted in
`tests/architectural/_baselines.yaml::test_example_round_trip.skip_marker_blocks`,
so adding a new permanently-non-executable block is an explicit, reviewable event.

### Failure shape

When a `expect: valid` codeblock fails to parse:

> **FAIL**: `kitty-specs/<mission>/contracts/<file>.md` (codeblock #N) declared `pydantic_model: <Model>, expect: valid` but `model_validate` raised: `<exception text>`.

When a `expect: invalid` codeblock parses cleanly:

> **FAIL**: `kitty-specs/<mission>/contracts/<file>.md` (codeblock #N) declared `pydantic_model: <Model>, expect: invalid` but `model_validate` succeeded.

When a `pydantic_model:` references a non-importable model:

> **FAIL**: `kitty-specs/<mission>/contracts/<file>.md` (codeblock #N) declared `pydantic_model: <bad.path.Model>` but the module is not importable: `<ImportError text>`.

When a non-legacy codeblock carries neither frontmatter nor a skip marker (the per-block strictness, `block-N-MISSING_FRONTMATTER`):

> **FAIL**: Contract block `<file>.md::block-N` carries neither `# pydantic_model:` frontmatter nor a `# round-trip: skip: <reason>` marker. Add frontmatter to round-trip the block, add a skip marker if it is non-executable, or (pre-Slice-F only) add the file to the legacy allowlist.

### Legacy allowlist behaviour

For files in the legacy allowlist, FAIL conditions become WARN conditions and the test passes — but the legacy file's path is reported in a pytest warning so the operator sees the unwound work. Legacy files keep **file-level** leniency (untagged blocks are tolerated); the per-block strictness above applies only to non-legacy contracts.

---

## Failure modes

| Trigger | Reporter | Operator message |
|---|---|---|
| A new contract's `expect: valid` example doesn't actually parse | `test_example_round_trip` FAIL | "Contract `<file>` codeblock #N declares `expect: valid` but `model_validate` raised: `<exc>`. Fix the example OR the model" |
| A new contract's `expect: invalid` example DOES parse | `test_example_round_trip` FAIL | "Contract `<file>` codeblock #N declares `expect: invalid` but `model_validate` succeeded. Either the example was meant to be valid OR the model lost a validator" |
| A non-legacy contract has a YAML codeblock with neither `# pydantic_model:` frontmatter nor a `# round-trip: skip: <reason>` marker | `test_example_round_trip` FAIL (per block, `block-N-MISSING_FRONTMATTER`) | "Block `<file>::block-N` carries neither frontmatter nor a skip marker. Tag it, skip-mark it, or (pre-Slice-F only) add the file to the legacy allowlist" |
| A new `# round-trip: skip:` marker is added in a non-legacy contract without bumping the baseline | `test_ratchet_baselines` FAIL (growth) | "skip_marker_blocks grew above baseline. Bump `_baselines.yaml:test_example_round_trip.skip_marker_blocks` with a one-line rationale naming the new block" |
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
