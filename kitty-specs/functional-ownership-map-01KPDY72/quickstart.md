# Quickstart — Using the Functional Ownership Map

**Mission**: Functional Ownership Map (`functional-ownership-map-01KPDY72`)
**Audiences**: (A) Extraction-PR authors; (B) Reviewers of extraction PRs.

This quickstart demonstrates acceptance scenarios 1 and 2 from `spec.md` as worked examples. The same content (or a trimmed version of it) is inlined into the "How to use this map" section of `architecture/2.x/05_ownership_map.md`.

---

## Audience A — Extraction-PR Author

**Goal**: Prepare a PR that extracts a slice (e.g. glossary, runtime, lifecycle) to its canonical package without missing any obligation.

**Procedure**:

1. **Locate the slice entry**.
   - Open `architecture/2.x/05_ownership_map.md`.
   - Find the H2 for the slice you are extracting (e.g. *Glossary*).
2. **Read the required fields in order**:
   - `current_state` — list the exact files you will move.
   - `canonical_package` — the target package; use this as the destination path.
   - `adapter_responsibilities` — keep these in `src/specify_cli/` (the CLI shell). Do not move them.
   - `shims` — for each entry, create the shim file at `path` that re-exports from `canonical_import`. Record the `removal_release`.
   - `seams` — for each seam sentence, verify the seam still works after the move (typically a single test at the seam boundary).
   - `extraction_sequencing_notes` — confirm the prerequisites for this slice are landed (usually a subset of #393, #394, #395 safeguards).
3. **For the runtime slice only**: also honour `dependency_rules`. Add an import-graph test (or rely on #395's tooling once it lands) that asserts `may_call` / `may_be_called_by` hold.
4. **Confirm the slice entry in the PR description**. Copy the slice's H2 from the map into the PR description and tick every field off. If a field is deferred, name the follow-up tracker.

**Worked example** — Glossary extraction (mission #613):

- `current_state`: `src/specify_cli/glossary/*` (14 modules).
- `canonical_package`: `src/glossary/`.
- `adapter_responsibilities`: CLI argument parsing + Rich rendering for `spec-kitty glossary *` commands (stays in `src/specify_cli/cli/commands/glossary.py`).
- `shims`: one entry for `src/specify_cli/glossary/` with `canonical_import: glossary`, `removal_release: 3.3.0` (or as pinned by #615).
- `seams`: "doctrine registers a glossary runner via `kernel.glossary_runner.register()`; mission execution reads via `get_runner()`" (already resolved by DIV-5 / ADR `2026-03-25-1`).
- `extraction_sequencing_notes`: depends on #393 architectural tests, #394 deprecation scaffolding landing first.
- Author lands PR that moves all 14 modules to `src/glossary/`, adds the shim, ticks every field off in the PR description.

---

## Audience B — Reviewer

**Goal**: Reject extraction PRs that silently skip obligations or place code in the wrong package.

**Procedure**:

1. Open the PR and read its description.
2. Open `architecture/2.x/05_ownership_map.md` and the slice entry the PR claims to target.
3. For each required field in the slice entry:
   - Confirm the PR delivers it, or
   - Confirm the PR names a follow-up tracker that covers the deferral, or
   - Request changes.
4. Verify **Mission / Work Package** canon (C-005) — no "feature/task" language in the PR description or commit messages.
5. Verify the CHANGELOG entry exists (if the slice had a shim removal as part of the PR).
6. For the runtime slice only: confirm `dependency_rules` have a corresponding test.

**Worked example** — Runtime extraction PR review (mission #612):

- PR claims: "extracts runtime to `src/runtime/`".
- Reviewer checks the runtime slice entry's `dependency_rules`:
  - `may_call: [charter_governance, doctrine, lifecycle_status, kernel]` — PR adds an import-graph test covering these.
  - `may_be_called_by: [cli_shell]` — PR adds the reverse assertion.
- Reviewer checks `adapter_responsibilities` — CLI commands under `src/specify_cli/cli/commands/` that use runtime must stay in place.
- Reviewer checks `shims` — one shim at `src/specify_cli/runtime/` with canonical_import `runtime`, removal_release aligned with #615.
- Reviewer checks `extraction_sequencing_notes` — the PR confirms #393, #394, #395 are in place.
- If every field is accounted for, approve. Otherwise, request changes with the specific missing field named.

---

## Cross-reference check

After landing the map, navigate from `architecture/2.x/04_implementation_mapping/README.md` and confirm the prominent cross-link to `05_ownership_map.md` resolves and the map's "How to use" section is discoverable in one click. This validates FR-007 / acceptance scenario 7.

---

## Manifest-driven tooling

Third-party tools (CI checks, the shim registry in #615, future scripts) parse `architecture/2.x/05_ownership_manifest.yaml` directly rather than the Markdown map. A typical consumer pattern:

```python
import yaml
from pathlib import Path

manifest = yaml.safe_load(Path("architecture/2.x/05_ownership_manifest.yaml").read_text())
runtime = manifest["runtime_mission_execution"]
may_call = runtime["dependency_rules"]["may_call"]
# …assert import-graph compliance
```

The manifest is validated by `tests/architecture/test_ownership_manifest_schema.py` against the schema in `kitty-specs/functional-ownership-map-01KPDY72/contracts/ownership_manifest.schema.yaml` — if either changes, the test fails and the contract is surfaced.
