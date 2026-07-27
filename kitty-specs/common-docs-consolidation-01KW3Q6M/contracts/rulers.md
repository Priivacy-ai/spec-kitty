# Contracts — the rulers (Mission A)

Each ruler is a standalone script + a self-test. In Mission A all run **report-only** (exit 0); Mission B flips the exit semantics to blocking. The **self-test is the contract** — a ruler that cannot go RED is not done.

## `related_validator` (IC-03 / FR-005)

- **Input**: the `docs/` tree (markdown frontmatter `related:` lists).
- **Output**: `{ checked_count: int, dangling_edges: [{from: path, to: path}] }`. Prints both; **report-only exit 0**.
- **Contract**: every `related:` entry is a repo-relative path that resolves to an existing `.md`; a non-resolving entry is a dangling edge.
- **Self-test** (`test_related_validator.py`): a fixture with one deliberately-dangling `related:` asserts `dangling_edges` is non-empty (and, in blocking mode, exit≠0); a good fixture asserts empty; assert `checked_count > 0` (so "0 broken" can't mean "0 checked").

## `inventory_lockfile` (IC-04 / FR-006)

- **Input**: frontmatter across `docs/`.
- **Output**: a generated `page-inventory` lockfile (schema per data-model; **no `citation_refs`**).
- **Contract (freshness, inverted)**: `generated == committed`, else the check fails. The committed inventory is a *lockfile*, not a source.
- **Self-test** (`test_inventory_lockfile.py`, the linchpin): mutate one frontmatter field → regenerate → assert the lockfile **changes** and the freshness check goes **RED**; hand-edit the committed lockfile alone (frontmatter untouched) → assert **rejected**. (Proves frontmatter is the SSOT, not the sidecar.)
- **Coupling**: `LEAK-FRONTMATTER-MISMATCH` is retired **only after** this gate is proven red live.

## `anti_sprawl_ratchet` (IC-05 / FR-007)

- **Input**: the repository tree (`docs/`, ADRs).
- **Output**: `{ violations: [{condition, path}], baseline_count: int, directive_ref: <directive-id>, floor: [<13 section names>] }`. Prints; **report-only exit 0**.
- **Contract**: detect (a) a second doc root, (b) any `docs/*/` missing `index.md`, (c) an ADR missing the frontmatter schema, (d) a re-introduced `docs/<version>x` shadow tree. The **floor** is a concrete enumerated baseline (the 13 sections / exactly-one-root) so an empty set doesn't pass everything. The violation message **references the directive id** (binding, C-003).
- **Self-test** (`test_anti_sprawl_ratchet.py`): four injection fixtures (one per condition) each assert detection; the good fixture passes; assert the floor is the enumerated 13-section list, not empty.
