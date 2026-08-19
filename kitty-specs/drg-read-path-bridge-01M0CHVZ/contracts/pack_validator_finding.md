# Contract: `_check_drg_root_graph_missing` reconciliation (#3573 / FR-006)

**Module**: `src/specify_cli/doctrine/pack_validator.py` (~L653–688)

## Atomicity

This finding change lands in the **same commit** as the runtime bridge
(`load_validated_graph` org-fragment support). At no commit may `pack validate`
state a claim the runtime contradicts (C-001 / NFR-003).

## Behaviour matrix (after reconciliation)

> **Correction (post pre-merge squad / CI).** An earlier draft suppressed the
> finding whenever a `drg/fragment.yaml` coexisted. That was wrong: `drg/*.graph.yaml`
> is a *distinct* shape no runtime path reads, so it must be flagged regardless of
> a coexisting fragment. A scaffolded pack always ships a `drg/fragment.yaml`, so
> suppressing on its presence neutered the guard — caught by the pre-existing
> `tests/cli/test_doctrine_org_commands.py` AC-7b test. The validator finding and
> the runtime graphless-warning answer **different** questions and are NOT mirror
> predicates: the runtime warning fires when a pack contributes *nothing* to
> cascade (a fragment satisfies it); this finding fires when a *specific*
> `drg/*.graph.yaml` document goes unread (independent of the fragment).

| Pack DRG contents | Finding `drg_root_graph_missing`? | Why |
|-------------------|-----------------------------------|-----|
| `drg/fragment.yaml` **only** (no `drg/*.graph.yaml`) | **no** | A fragment-only pack ships no `drg/*.graph.yaml`, so it never matches the `*.graph.yaml` glob (SC-003 / US3 AC1). Its edges cascade via the bridge. |
| `drg/*.graph.yaml` present, no pack-root graph — **with or without** a coexisting `drg/fragment.yaml` | **yes** | `drg/*.graph.yaml` is read by no runtime path; the coexisting fragment's edges cascade but the graph document stays unread, so the author still needs the signal. Does not contradict the runtime (it never reads `drg/*.graph.yaml`). |
| pack-root `*.graph.yaml` present | **no** (unchanged) | Runtime reads pack-root graph directly. |
| no DRG content at all | **no** (unchanged) | Nothing to flag. |

## Message

The finding text must state the actual runtime read-set and drop the false
blanket claim. Replace:

> "…reads the pack root directly, **not drg/ fragments** — this pack's DRG content
> will not be read as authored."

with an accurate statement that the runtime reads pack-root `*.graph.yaml` **and**
`drg/fragment.yaml`, and that `drg/*.graph.yaml` graph fragments are the unread
shape.

## Acceptance

- A `drg/fragment.yaml`-only pack yields **no** `drg_root_graph_missing` finding
  (SC-003 / US3 AC1).
- A `drg/*.graph.yaml` pack (no pack-root graph) still yields the finding **whether
  or not** a `drg/fragment.yaml` coexists (dead-content protection — the graph
  document is unread regardless).
- Diagnostic output for all other pack shapes is unchanged (NFR-001).
