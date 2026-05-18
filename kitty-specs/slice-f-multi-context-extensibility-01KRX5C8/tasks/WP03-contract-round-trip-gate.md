---
work_package_id: WP03
title: Contract round-trip CI gate + frontmatter convention + legacy allowlist
dependencies:
- WP01
requirement_refs:
- FR-140
- FR-141
- NFR-005
planning_base_branch: feat/org-doctrine-layer
merge_target_branch: feat/org-doctrine-layer
branch_strategy: Planning artifacts for this mission were generated on feat/org-doctrine-layer. During /spec-kitty.implement this WP may branch from a dependency-specific base, but completed changes must merge back into feat/org-doctrine-layer unless the human explicitly redirects the landing branch.
subtasks:
- T013
- T014
- T015
- T016
agent: "claude:sonnet-4-6:reviewer-renata:reviewer"
history: []
agent_profile: python-pedro
authoritative_surface: tests/contract/
execution_mode: code_change
owned_files:
- tests/contract/test_example_round_trip.py
- kitty-specs/slice-f-multi-context-extensibility-01KRX5C8/contracts/*.md
role: implementer
tags: []
shell_pid: "2321454"
---

## ⚡ Do This First: Load Agent Profile

```
/ad-hoc-profile-load python-pedro
```

Scope governance context to Python implementation before reading anything else.

---

## Objective

Land the contract round-trip backstop (FR-140/141): a CI gate that walks every `kitty-specs/<mission>/contracts/*.md` file, lifts fenced YAML codeblocks tagged with `pydantic_model:` + `expect:` frontmatter, imports the named model, attempts `model_validate(yaml.safe_load(...))`, and asserts the outcome matches `expect`. Ships with a legacy allowlist (participating in WP01's `_baselines.yaml`) so missions predating the convention warn instead of fail.

This is the contract-fidelity backstop the architect's LOW-3 finding identified — Mission B's WP01 singular/plural drift would have been caught at WP01 dispatch had this gate existed (contract example contradicted implementation).

---

## Context

`kitty-specs/<mission>/contracts/*.md` files contain fenced YAML codeblocks that document the expected shape of inputs and outputs. Today nothing exercises those codeblocks against the actual Pydantic models. A drift between contract example and implementation goes undetected until a human reads the contract independently — exactly the failure mode that bit Mission B WP01.

The convention introduced by this WP:

```markdown
Some prose explaining the contract...

```yaml
# pydantic_model: charter.drg.OrgDRGFragment
# expect: valid
pack_name: acme-compliance
source_kind: local_path
...
```

```yaml
# pydantic_model: charter.drg.OrgDRGFragment
# expect: invalid
pack_name: acme-compliance
nodes:
  - id: foo
    kind: not-a-real-kind   # ← C-009 violation
```
```

The walker:

1. Parses each `.md` file for fenced ` ```yaml ... ``` ` blocks.
2. Inspects the first lines of each block for `# pydantic_model: X.Y` and `# expect: valid|invalid` comment-frontmatter.
3. Lifts the YAML body (stripping comment lines), imports `X.Y` dynamically, attempts `Y.model_validate(yaml.safe_load(body))`.
4. Asserts the outcome matches `expect`.

Slice F's own contracts (the 6 files in `contracts/`) are the first dogfooded set; FR-140 ships them with frontmatter (the `org-drg-schema.md` example already carries it — see lines 44 and 67 of that file).

References:
- [spec.md §"Absorbed remediation — LOW-3 contract round-trip backstop"](../spec.md)
- [plan.md §1.8](../plan.md)
- [contracts/contract-round-trip-frontmatter.md](../contracts/contract-round-trip-frontmatter.md)
- [atdd-coverage.md AC-10](../atdd-coverage.md)

**Dependency on WP01:** WP01 owns `tests/architectural/_baselines.yaml`. T015 here adds the `test_example_round_trip.legacy_contract_allowlist` entry — by sequence, WP01 has already created the file and WP03 appends a new section (no ownership conflict because WP01 declares the section structure; WP03 fills the `test_example_round_trip` key).

---

## ATDD Discipline

Per **C-011** WP03 lands the failing-first test as its FIRST commit:

1. **Commit A (RED, T013):** `tests/contract/test_example_round_trip.py` walks `kitty-specs/*/contracts/*.md` and parameterises one assertion per tagged codeblock. On the planning base it fails because (a) the test file doesn't exist, and (b) several existing contracts lack `pydantic_model:` / `expect:` frontmatter or have stale examples. Commit message: `covers: AC-10 — expected GREEN at: WP03 final commit`.
2. **Commits B..D (GREEN progression, T014-T016):** add frontmatter to contracts (or allowlist them), populate `_baselines.yaml` legacy entry, sweep Slice F's own contracts.

ATDD anchor per [atdd-coverage.md](../atdd-coverage.md):
- AC-10: `test_contract_example_round_trip[*]` (parameterised over every tagged codeblock)

---

## Subtasks

### T013 — Land failing-first `tests/contract/test_example_round_trip.py`

**File:** `tests/contract/test_example_round_trip.py` (new)

```python
"""Contract round-trip backstop (FR-140).

Walks every kitty-specs/<mission>/contracts/*.md file, lifts fenced YAML
codeblocks tagged with `pydantic_model:` + `expect:` frontmatter, imports
the named model, attempts model_validate(yaml.safe_load(body)), and
asserts the outcome matches `expect`.
"""
from __future__ import annotations

import importlib
import re
from dataclasses import dataclass
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_GLOB = "kitty-specs/*/contracts/*.md"


@dataclass(frozen=True)
class ContractExample:
    file: Path
    block_index: int
    pydantic_model: str
    expect: str  # "valid" | "invalid"
    body: str


def _discover_examples() -> list[ContractExample]:
    examples: list[ContractExample] = []
    for md_path in sorted(REPO_ROOT.glob(CONTRACTS_GLOB)):
        for i, block in enumerate(_yaml_blocks(md_path.read_text())):
            tag = _frontmatter(block)
            if not tag:
                continue
            model, expect = tag
            body = _strip_frontmatter(block)
            examples.append(
                ContractExample(md_path, i, model, expect, body)
            )
    return examples


def _yaml_blocks(text: str) -> list[str]:
    return re.findall(r"```yaml\n(.*?)```", text, re.DOTALL)


def _frontmatter(block: str) -> tuple[str, str] | None:
    model_match = re.search(r"^#\s*pydantic_model:\s*(\S+)\s*$", block, re.MULTILINE)
    expect_match = re.search(r"^#\s*expect:\s*(valid|invalid)\s*$", block, re.MULTILINE)
    if model_match and expect_match:
        return model_match.group(1), expect_match.group(1)
    return None


def _strip_frontmatter(block: str) -> str:
    return "\n".join(
        line for line in block.splitlines()
        if not re.match(r"^#\s*(pydantic_model|expect):", line)
    )


@pytest.mark.parametrize("example", _discover_examples(), ids=lambda e: f"{e.file.name}#{e.block_index}")
def test_contract_example_round_trip(example: ContractExample) -> None:
    module_name, class_name = example.pydantic_model.rsplit(".", 1)
    module = importlib.import_module(module_name)
    model_cls = getattr(module, class_name)
    data = yaml.safe_load(example.body)
    try:
        model_cls.model_validate(data)
        actual = "valid"
    except Exception:
        actual = "invalid"
    assert actual == example.expect, (
        f"{example.file}#{example.block_index}: "
        f"model {example.pydantic_model} expected {example.expect}, got {actual}"
    )
```

**Validation:** `pytest tests/contract/test_example_round_trip.py -v` MUST FAIL on planning base (likely empty `_discover_examples()` return — file doesn't yet exist OR several examples lack frontmatter). Commit RED with failing output captured.

### T014 — Document frontmatter convention

**Files:** docstring in `tests/contract/test_example_round_trip.py`; reference in `kitty-specs/slice-f-multi-context-extensibility-01KRX5C8/contracts/contract-round-trip-frontmatter.md` (already exists from `/plan` time, verify it documents the convention).

The convention:

```yaml
# pydantic_model: <module.path>.<ClassName>
# expect: valid|invalid
<yaml body>
```

Both comment lines MUST appear in the first few lines of the YAML codeblock. The walker strips them before passing the body to `yaml.safe_load`.

If `contract-round-trip-frontmatter.md` does not document this fully, extend it. Otherwise leave it (cross-reference from the test docstring).

### T015 — Add legacy allowlist to `_baselines.yaml`

**File:** `tests/architectural/_baselines.yaml` (owned by WP01; WP03 appends)

After WP01 merges, the file exists with the section structure. Add the legacy contract allowlist count under the existing `test_example_round_trip` key:

```yaml
test_example_round_trip:
  legacy_contract_allowlist: <N>   # justification: pre-FR-140 missions without
                                   # frontmatter; shrinks as contracts get migrated
```

`N` is determined by T016's discovery sweep: count how many tagged codeblocks across `kitty-specs/*/contracts/*.md` currently produce a mismatch when run through the gate. The allowlist NAMES the offending file:block pairs (a list) so the gate can skip them with a WARNING.

Schema extension to `_baselines.yaml`:

```yaml
test_example_round_trip:
  legacy_contract_allowlist:
    count: <N>
    skip_files:
      - "kitty-specs/old-mission/contracts/something.md"
```

OR keep the integer-only schema and use a sidecar `legacy_skips.txt`. The implementer chooses; document the choice.

### T016 — Sweep contracts; gate GREEN

**Files:** `kitty-specs/slice-f-multi-context-extensibility-01KRX5C8/contracts/*.md`; possibly other contract files

Walk `kitty-specs/*/contracts/*.md`. For Slice F's own 6 contracts:

- `org-drg-schema.md` — already carries frontmatter on its two example blocks (lines 44, 67 per the current spec). Verify the `pydantic_model` paths are correct (e.g. `charter.drg.OrgDRGFragment`).
- `charter-scope-resolution.md` — add frontmatter to any code examples (or omit codeblocks if pure prose).
- `workflow-sequence-schema.md` — add frontmatter for `WorkflowSequence` and `ActionStep` examples.
- `ratchet-baseline-format.md` — likely pure prose; if a YAML example is illustrative, tag it with `expect: valid`.
- `catalog-miss-cli-visibility.md` — tag any payload examples.
- `contract-round-trip-frontmatter.md` — tag a meta-example demonstrating the convention.

For other missions' contracts (predecessor missions):

- If a contract has an obvious valid example, add frontmatter.
- If a contract has stale examples that don't match current implementation, add to legacy allowlist with a follow-up ticket reference.

Run:

```bash
pytest tests/contract/test_example_round_trip.py -v
```

All parameterised cases MUST be GREEN. Allowlisted cases emit `pytest.warns(LegacyContractWarning)` but do not fail. Re-run architectural sweep:

```bash
PWHEADLESS=1 pytest tests/architectural/ tests/contract/ -v
```

Exit 0.

---

## Definition of Done

The following tests turn GREEN with this WP:

- ✅ `tests/contract/test_example_round_trip.py::test_contract_example_round_trip[*]` (parameterised; was RED on planning base)
- ✅ Slice F's 6 contract files each carry valid `pydantic_model:` + `expect:` frontmatter on every YAML codeblock that documents a schema
- ✅ Legacy contracts either carry frontmatter or appear in the `_baselines.yaml` legacy allowlist with a justification
- ✅ `PWHEADLESS=1 pytest tests/architectural/ tests/contract/ -v` exit 0 (NFR-005)

FR coverage:

- ✅ FR-140 — round-trip gate walks every tagged codeblock; asserts outcome matches `expect`
- ✅ FR-141 — legacy allowlist participates in the FR-110 baseline; shrinks over time

AC coverage:

- ✅ AC-10 — `test_example_round_trip` exists and passes against all current `kitty-specs/*/contracts/*.md` examples (with documented allowlist for legacy contracts)

---

## Risks

1. **Discovery sweep surfaces dozens of legacy contract drift cases** (RR-7 in plan). Mitigation: T015 + T016 allowlist them with follow-up tickets; the allowlist is a ratchet that shrinks over time. Initial run is a discovery exercise, not a quality gate failure.
2. **A `pydantic_model:` path imports cleanly but is the wrong class** (e.g. typo). Mitigation: the gate catches a wrong-class assertion failure as a test failure with the model path printed; the file:block reference makes it cheap to fix.
3. **Dynamic import side-effects** (importing a charter module triggers a heavy doctrine load). Mitigation: the gate uses `importlib.import_module` once per unique module per test session; pytest's collection is cached. If the side-effect is unacceptable, the gate can split into a per-model fixture.
4. **YAML codeblock contains a multi-document YAML (`---` separator) and `yaml.safe_load` returns only the first doc**. Mitigation: explicitly use `yaml.safe_load_all` and validate each doc; OR document the convention as single-doc only and reject multi-doc blocks at sweep time.
5. **The walker mis-parses fenced ` ```yaml ` blocks inside fenced ` ```markdown ` blocks** (rare but possible in docs about docs). Mitigation: the regex is greedy and may capture nested fences; T013's regex test handles the canonical cases; nested cases get added to the allowlist.

---

## Reviewer Guidance

**ATDD red→green verification (mandatory per C-011):**

```bash
# 1. RED on planning base:
git checkout feat/org-doctrine-layer
pytest tests/contract/test_example_round_trip.py -v
# EXPECTED: failures OR collection error (test file doesn't exist yet)

# 2. GREEN on WP final commit:
git checkout <wp_branch>
pytest tests/contract/test_example_round_trip.py -v
# EXPECTED: all parameterised cases pass; allowlisted cases emit warnings
```

**Substantive review checks:**

- Confirm `tests/contract/test_example_round_trip.py` exists and parameterises over `_discover_examples()`.
- Confirm every Slice F contract has at least one tagged YAML codeblock (verify by `rg "pydantic_model:" kitty-specs/slice-f-multi-context-extensibility-01KRX5C8/contracts/`).
- Confirm `_baselines.yaml::test_example_round_trip.legacy_contract_allowlist` exists with a count and justification comment OR a sidecar file lists allowlisted paths.
- Confirm no new entries land in `legacy_contract_allowlist` for Slice F's own contracts (Slice F is the dogfood mission; the convention is born here).
- Confirm WP01's `_baselines.yaml` structure is preserved — WP03 only ADDS the `test_example_round_trip` section, does not modify others.
- Confirm full architectural sweep: `PWHEADLESS=1 pytest tests/architectural/ tests/contract/ -v` exit 0 (NFR-005).

**FR-304 commit-message check:** T013 RED commit cites `covers: AC-10` and `expected GREEN at: WP03 final commit`.

## Activity Log

- 2026-05-18T13:09:38Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2260092 – Started implementation via action command
- 2026-05-18T13:47:05Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2260092 – Contract round-trip CI gate landed (FR-140 + FR-141); Slice F contracts tagged; legacy allowlist baselined for shrink-over-time
- 2026-05-18T13:54:27Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2260092 – Moved to planned
- 2026-05-18T14:03:05Z – claude:sonnet-4-6:python-pedro:implementer – shell_pid=2260092 – Cycle 2 orchestrator remediation per HiC directive — deleted 3 stub Pydantic models, converted round-trip ImportError to pytest.skip with future-WP attribution, reverted BaselinesFile loosening, added binding skipif-removal acceptance criterion to WP06/WP09/WP10. 234 passed / 1 skipped on full architectural sweep.
- 2026-05-18T14:03:38Z – claude:sonnet-4-6:reviewer-renata:reviewer – shell_pid=2321454 – Started review via action command
