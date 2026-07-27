# Quickstart: Phase 1 Excision Developer Workflow

**Mission**: `excise-doctrine-curation-and-inline-references-01KP54J6`
**Plan**: [plan.md](plan.md)
**Spec**: [spec.md](spec.md)
**Date**: 2026-04-14

This quickstart is for the implementer(s) working through the three WPs. It assumes you have the spec and plan open in another pane.

---

## Prerequisites

- `main` @ the commit this plan was generated against (post #609)
- `pipx install --force --pip-args="--pre" spec-kitty-cli` up-to-date
- `python -m venv .venv && source .venv/bin/activate && uv pip install -e .`
- `mypy`, `ruff`, `pytest` runnable locally
- `SPEC_KITTY_ENABLE_SAAS_SYNC=1` if you need to exercise SaaS sync paths (not required for this mission)

---

## Branch contract

- Start branch: `main`
- All three WP PRs open against `main`
- All three WP PRs merge back to `main`
- Mission `mission_id`: `01KP54J6W03W8B05F3P2RDPS8S` (`mid8`: `01KP54J6`)
- Mission slug: `excise-doctrine-curation-and-inline-references-01KP54J6`
- Always pass `--mission excise-doctrine-curation-and-inline-references-01KP54J6` (or `--mission 01KP54J6`) to any `spec-kitty` command in this repo — there are multiple active missions.

---

## Before starting any WP

1. Pull `main` and rebase your working branch.
2. Run `spec-kitty agent tasks status --mission excise-doctrine-curation-and-inline-references-01KP54J6` to confirm WP lanes.
3. Read the relevant WP slice of `plan.md` and the full `spec.md`.
4. Read the contract files relevant to your WP:
   - WP1.1: `contracts/occurrence-artifact.schema.yaml`, `contracts/removed-cli-surface.md`
   - WP1.2: `contracts/occurrence-artifact.schema.yaml`
   - WP1.3: `contracts/occurrence-artifact.schema.yaml`, `contracts/validator-rejection-error.schema.json`, `contracts/resolve-transitive-refs.contract.md`

---

## WP1.1 — Excise curation surface

### Step 1. Author the occurrence artifact FIRST (before any deletion)

```bash
# From repo root
mkdir -p kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences
```

Populate `kitty-specs/.../occurrences/WP1.1.yaml` per the schema. The `to_change` list must include every file to be deleted/modified, classified by the eight #393 categories. Reference `contracts/occurrence-artifact.schema.yaml`.

### Step 2. Write the verifier

Add `scripts/verify_occurrences.py` — a small Python script that:
- Loads an occurrence artifact YAML
- For each category, greps the repo for each `strings[i]` within `include_globs` excluding `exclude_globs`
- Fails if any hit is found that is not listed in `permitted_exceptions`
- Fails if `requires_merged` contains WP IDs not yet merged (check via `git log main` or equivalent)
- Emits a green/red summary

Run it against WP1.1.yaml before any deletions — it should list every hit you plan to delete.

### Step 3. Delete in order

```bash
rm -rf src/doctrine/curation/
rm -f src/specify_cli/cli/commands/doctrine.py
rm -f src/specify_cli/validators/doctrine_curation.py
rm -rf tests/doctrine/curation/
rm -f tests/cross_cutting/test_doctrine_curation_unit.py

# Delete _proposed/ trees (only the dirs themselves)
for kind in directives tactics procedures styleguides toolguides paradigms; do
  rm -rf "src/doctrine/${kind}/_proposed"
done
```

### Step 4. Unregister the Typer app

Edit `src/specify_cli/cli/commands/__init__.py` — remove the single `app.add_typer(doctrine_module.app, name="doctrine")` line and the `from . import doctrine as doctrine_module` import above it.

### Step 5. Update SOURCE templates

Grep SOURCE prose for the removed command names (NOT agent copy dirs):

```bash
# SOURCE prose only — agent copies regenerate on upgrade
grep -rn "doctrine curate\|doctrine promote\|doctrine reset\|doctrine status\|_proposed" \
  src/specify_cli/missions src/specify_cli/skills src/doctrine \
  | grep -v 'curation/imports'
```

Rewrite any hits in SOURCE templates. Do not touch `.claude/`, `.amazonq/`, `.augment/`, `.codex/`, `.cursor/`, `.gemini/`, `.github/prompts/`, `.kilocode/`, `.opencode/`, `.qwen/`, `.roo/`, `.windsurf/`.

### Step 6. Add the regression test

Create `tests/specify_cli/cli/test_doctrine_cli_removed.py` per `contracts/removed-cli-surface.md`.

### Step 7. Run gates locally

```bash
pytest tests/
mypy --strict src/
python scripts/verify_occurrences.py kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/WP1.1.yaml
```

All three must be green.

### Step 8. Open PR

Target `main`. PR body should reference #476 and paste the verifier's green summary.

---

## WP1.2 — Strip inline reference fields from shipped artifacts, schemas, models

**Only start after WP1.1 is merged to `main`.**

### Step 1. Run R-1 audit

Create `scripts/r1_inline_vs_graph_audit.py` (ephemeral — deleted at end of WP1.2):
- Walks every shipped YAML under `src/doctrine/` (exclude `_proposed/` — already gone — and `schemas/`, `graph.yaml`)
- Extracts every `tactic_refs: [...]` reference
- Loads `src/doctrine/graph.yaml`
- Asserts every inline reference has a matching edge `{from, to, kind: uses}`
- Emits a `missing_edges.yaml` in the mission directory (ephemeral)

Read `research.md` R-1 for method and expected output shape.

### Step 2. Patch `graph.yaml` with missing edges (if any)

For every missing edge, add a record to `src/doctrine/graph.yaml`. Preserve file ordering conventions. Add a comment if the origin of the relationship is ambiguous.

### Step 3. Author the occurrence artifact

Populate `kitty-specs/.../occurrences/WP1.2.yaml` per the schema. Categories to cover: `yaml_key`, `symbol_name` (for Pydantic fields), `docstring_or_comment` (for schema comments).

### Step 4. Strip inline refs from shipped YAMLs

Edit each of the 13 shipped YAMLs (8 directives, 3 paradigms, 2 procedures) to remove `tactic_refs:`. For procedures, remove `tactic_refs:` from each `steps[*]` entry too.

Use `ruamel.yaml` round-trip to preserve comments and key order where possible.

### Step 5. Strip inline ref fields from schemas and models

```bash
# Remove tactic_refs / paradigm_refs / applies_to from these:
src/doctrine/schemas/directive.schema.yaml
src/doctrine/schemas/paradigm.schema.yaml
src/doctrine/schemas/procedure.schema.yaml

# And from per-kind Pydantic models
src/doctrine/directives/models.py
src/doctrine/paradigms/models.py
src/doctrine/procedures/models.py
src/doctrine/tactics/models.py           # paradigm_refs if present
src/doctrine/styleguides/models.py       # tactic_refs if present
src/doctrine/toolguides/models.py        # tactic_refs if present
src/doctrine/agent_profiles/models.py    # any of three if present

# And from charter schemas
src/charter/schemas.py                   # strip applies_to: list[str] from Directive
```

### Step 6. Update tests that asserted these fields

Edit every affected test to assert the fields are absent instead. Do NOT delete these tests.

### Step 7. Run gates locally

```bash
pytest tests/
mypy --strict src/
python scripts/verify_occurrences.py kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/WP1.2.yaml
grep -R "tactic_refs\|paradigm_refs\|applies_to" src/doctrine src/charter/schemas.py
```

Last command must return zero hits outside `index.yaml` permitted exceptions.

### Step 8. Delete the R-1 audit script

`rm scripts/r1_inline_vs_graph_audit.py`. Commit.

### Step 9. Open PR

Target `main`. PR body references #477 and paste verifier + grep output.

---

## WP1.3 — Validators reject, single context builder, reference-resolver excision

**Only start after WP1.2 is merged to `main`.**

Follow the sequencing from plan.md D-1 strictly:

### Step 1. Add `resolve_transitive_refs()` in DRG

Implement per `contracts/resolve-transitive-refs.contract.md`. Add `tests/doctrine/drg/test_resolve_transitive_refs.py` covering the six test dimensions from the contract.

### Step 2. Flip resolver/compiler imports

Both `src/charter/resolver.py` and `src/charter/compiler.py` (and their `specify_cli/charter/*` twins) swap their `resolve_references_transitively` import for `resolve_transitive_refs`. Also load/merge/validate the DRG at the call site (or via a shared helper).

### Step 3. Add validator rejection

Edit the seven per-kind `validation.py` files to reject `tactic_refs`, `paradigm_refs`, `applies_to` with `InlineReferenceRejectedError` per `contracts/validator-rejection-error.schema.json`. Add `tests/doctrine/test_inline_ref_rejection.py` with one negative fixture per kind.

### Step 4. Flip `build_charter_context` call sites to `build_context_v2`

Update the five call sites:
- `src/specify_cli/next/prompt_builder.py`
- `src/specify_cli/cli/commands/charter.py`
- `src/specify_cli/cli/commands/agent/workflow.py`
- `src/charter/__init__.py` (re-export)
- `src/specify_cli/charter/__init__.py` (re-export)
- `src/specify_cli/charter/context.py` (wrapper — delete if no longer needed)

Run full pytest at this point. All tests should pass (legacy `build_charter_context` is now dead code in src/ but still tested).

### Step 5. Rename `build_context_v2` → `build_charter_context`

Edit `src/charter/context.py`:
- Delete the legacy `build_charter_context()` function (lines ~33–119)
- Rename `build_context_v2` (lines ~495+) to `build_charter_context`
- Update module docstring/comments

Re-point the call sites back to the now-restored name.

Update `src/charter/__init__.py` and `src/specify_cli/charter/__init__.py` re-export lists.

### Step 6. Delete `reference_resolver.py`

```bash
rm src/charter/reference_resolver.py
```

All importers have been flipped in step 2. Verify with:
```bash
grep -R "reference_resolver\|resolve_references_transitively\|ResolvedReferenceGraph" src/ tests/
```

### Step 7. Remove `include_proposed` from catalog

Edit `src/charter/catalog.py :: load_doctrine_catalog()` — remove the parameter. Update every caller (should be few; most callers pass `False` implicitly).

### Step 8. Add merged-graph-on-live-path regression test

Create `tests/charter/test_merged_graph_on_live_path.py`. Mock or spy `assert_valid` and assert it is called on every bootstrap `build_charter_context` invocation (FR-016).

### Step 9. Rewrite `tests/charter/test_context.py`

Collapse any v1/v2 split into a single-builder suite. Use the Phase 0 golden fixture outputs as the golden set for NFR-002 byte-identical parity.

### Step 10. Delete parity and legacy resolver tests

**ONLY AFTER** steps 1, 8, 9 are green. Delete:
- `tests/charter/test_context_parity.py`
- `tests/charter/test_reference_resolver.py`

Run pytest again. Must stay green.

### Step 11. Author the final occurrence artifact + index

Populate `kitty-specs/.../occurrences/WP1.3.yaml` and finalize `kitty-specs/.../occurrences/index.yaml` with the full mission-level must-be-zero assertion.

### Step 12. Run gates locally

```bash
pytest tests/
mypy --strict src/
python scripts/verify_occurrences.py kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/WP1.3.yaml
python scripts/verify_occurrences.py kitty-specs/excise-doctrine-curation-and-inline-references-01KP54J6/occurrences/index.yaml

# NFR-002 byte-parity check (capture pre-merge baseline first, see below)
diff <(spec-kitty charter context --action specify --json) pre_merge_context.json

# Final must-be-zero grep
grep -RE "curation|_proposed|tactic_refs|paradigm_refs|applies_to|reference_resolver|include_proposed|build_context_v2" src tests \
  | grep -vFf permitted_exceptions.txt
```

### Step 13. Measure NFR-001 runtime budget

```bash
# On main before WP1.1 merged: pytest --durations=0 > baseline_durations.txt
# On WP1.3 branch: pytest --durations=0 > post_durations.txt
# Compare p50 of total runtime across three CI runs; must stay within 5%.
```

### Step 14. Open PR

Target `main`. PR body references #475 and paste all verifier/grep/parity/runtime outputs.

---

## Verifier (`scripts/verify_occurrences.py`)

Sketch — fill in during WP1.1.

```python
#!/usr/bin/env python3
"""Verify a phase-1 excision occurrence-classification artifact.

Loads the artifact YAML, walks each category, greps for each string in scope,
and fails if any hit is not listed in permitted_exceptions.
"""
from __future__ import annotations
import sys
from pathlib import Path
from ruamel.yaml import YAML

REPO_ROOT = Path(__file__).resolve().parents[1]

def load_artifact(path: Path) -> dict:
    return YAML(typ="safe").load(path.read_text())

def grep_in_scope(string: str, include_globs: list[str], exclude_globs: list[str]) -> list[tuple[str, int, str]]:
    hits = []
    for glob in include_globs:
        for file_path in REPO_ROOT.glob(glob):
            if not file_path.is_file():
                continue
            if any(file_path.match(ex) for ex in exclude_globs):
                continue
            try:
                content = file_path.read_text()
            except (UnicodeDecodeError, OSError):
                continue
            for lineno, line in enumerate(content.splitlines(), 1):
                if string in line:
                    hits.append((str(file_path.relative_to(REPO_ROOT)), lineno, line.rstrip()))
    return hits

def main(artifact_path_str: str) -> int:
    artifact = load_artifact(Path(artifact_path_str))
    is_index = "wps" in artifact  # mission-level index vs per-WP artifact
    failures: list[str] = []

    if is_index:
        # handle mission-level index
        for assertion in artifact["must_be_zero"]:
            literal = assertion["literal"]
            scopes = assertion["scopes"]
            excluding = assertion.get("excluding", [])
            hits = grep_in_scope(literal, scopes, excluding)
            permitted = [e["pattern"] for e in artifact.get("permitted_exceptions", [])]
            real_hits = [h for h in hits if not any(p in h[0] or p == h[2] for p in permitted)]
            if len(real_hits) != assertion.get("final_count", 0):
                failures.append(f"Index assertion violated for literal '{literal}': {len(real_hits)} hits, expected {assertion.get('final_count', 0)}")
                for h in real_hits[:5]:
                    failures.append(f"    {h[0]}:{h[1]}  {h[2]}")
    else:
        # handle per-WP artifact
        for cat in artifact["categories"]:
            for string in cat["strings"]:
                hits = grep_in_scope(string, cat["include_globs"], cat["exclude_globs"])
                permitted = [e["pattern"] for e in artifact.get("permitted_exceptions", [])]
                real_hits = [h for h in hits if not any(p in h[0] or p == h[2] for p in permitted)]
                if len(real_hits) != cat["expected_final_count"]:
                    failures.append(f"{artifact['wp_id']} category '{cat['name']}' string '{string}': {len(real_hits)} hits, expected {cat['expected_final_count']}")
                    for h in real_hits[:5]:
                        failures.append(f"    {h[0]}:{h[1]}  {h[2]}")

    if failures:
        print("VERIFIER FAILED")
        print("\n".join(failures))
        return 1
    print(f"VERIFIER GREEN for {artifact_path_str}")
    return 0

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: verify_occurrences.py <artifact.yaml>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
```

This is a sketch — final version lives under `scripts/` after WP1.1.

---

## Escalation

If any of the following happen, stop and escalate (open a comment on the tracking issue):

- R-1 reveals more than ~5 missing graph edges (suggests the inventory was incomplete and may indicate Phase 0 calibration gaps).
- R-2 behavioral equivalence fails for any shipped directive (means `resolve_transitive_refs` has a semantic gap — fix in `resolve_transitive_refs` before proceeding; do NOT patch the legacy resolver).
- Any of the existing tests fail in a way that is NOT explained by the known excision set (suggests a hidden dependency — capture in the occurrence artifact and escalate).
- NFR-001 runtime budget is projected to be breached.
- A caller of a removed symbol is discovered outside the known five `build_charter_context` call sites.

Escalation is a comment on [#463](https://github.com/Priivacy-ai/spec-kitty/issues/463) plus a `[NEEDS CLARIFICATION: ...]` marker on the affected WP's occurrence artifact. Do not silently work around it.
