# Contract — Parity/Totality Gate

**File**: `tests/doctrine/drg/test_kind_mapping_totality.py` (extended) — or a named sibling in the same package
**Governs**: FR-007, NFR-003, C-002, US2

The existing gate is an AST scan that recognizes only `ArtifactKind.MEMBER` / `NodeKind.MEMBER`-keyed dict literals and asserts them total-or-exempt. It is blind to string-keyed kind maps and knows nothing about recursion. This contract extends it.

## Capability 1 — String-keyed kind-map coverage (FR-007)

The enum-keyed guard is blind to string-keyed kind maps. Coverage is delivered in three scoped, non-overreaching parts (a blanket "every string-keyed kind map must be total" is out of scope — many string-keyed maps across the tree are legitimate partial consumer subsets; forcing them total is M5/M6 cascade work):

- **String-keyed authority totality**: the canonical kind *authority* tables that must span every kind — `doctrine.artifact_kinds::_PLURALS` / `_PATTERNS` / `_HAS_BUILT_IN_CONTENT_DIR` — are asserted total (a new `ArtifactKind` omitted from one fails, named). Registry: `_STRING_KEYED_MUST_BE_TOTAL`.
- **Discovery visibility**: the scan *sees* previously-hidden string-keyed kind maps (e.g. `charter.synthesizer.project_drg::_KIND_TO_NODE_KIND`, an intentional 3-kind partial read via `.get`) — proving the escape is closed even where totality is not required.
- **Charter re-declaration guard (#2981 class)**: a `charter.*` module that re-introduces a **complete** hand copy of the plural↔singular vocabulary (every charter-activatable singular→plural pair) instead of importing the derived authority fails loudly. The one pre-existing fifth copy (`charter.drg::_SINGULAR_TO_PLURAL`, golden-adjacent, out of M1's named scope) is explicitly exempted with a documented follow-up; any NEW charter re-declaration reddens. Partial maps that merely use plurals as values are not flagged.

## Capability 2 — Loader↔resolver recursion parity (US2 AC-1/AC-2)
Behavioral, per `ArtifactKind` with a non-empty glob:
1. Build a temp org (and project) root with a nested artifact `<dir>/<sub>/x.<kind>.yaml`.
2. Assert the **loader** (`DoctrineService` / `BaseDoctrineRepository`) discovers it.
3. Assert the **resolver** (`charter.kind_vocabulary.resolve_artifact_urn` / `_iter_artifact_paths`) discovers it.
4. **Assert the two discovery sets are equal** for every kind.

Reintroducing `recursive=False` in either seam → sets diverge → gate fails **naming the kind** (US2 AC-2).

## Capability 3 — C-002 negative (kind-specific globs)
In the same nested fixture dir, place `.provenance/foo.yaml` and `bar.md`. Assert **neither** loader nor resolver captures them.

## Capability 4 — Falsifiability proof (NFR-003, both directions)
A test that parametrizes/monkeypatches one seam to non-recursive and asserts the parity check **reddens**, then restores and asserts it **greens** — proving the gate is not vacuous. Both directions on one commit.

## Pass/fail summary
| Scenario | Expected |
|----------|----------|
| Loader & resolver agree; maps consistent | **pass** |
| One seam reverted to `recursive=False` for kind K | **fail**, message names K |
| A string-keyed kind map gains a typo'd/removed key | **fail**, names map + key |
| `.provenance/*.yaml` or `.md` captured | **fail** |
| A charter module re-declares a local plural↔singular kind dict missing a kind | **fail** (string-keyed coverage) |
