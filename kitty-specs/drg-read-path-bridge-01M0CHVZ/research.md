# Research: DRG Read-Path Bridge

Phase 0 output. Every decision below is grounded in a read of the current
`upstream/main` code (post-#3534) and, where noted, an executed probe. The spec's
FR/NFR/C tables are the normative contract; this document resolves the
engineering unknowns the approach leaves open.

## Ground truth established (reads + probes)

- **Two distinct DRG shapes live in an org pack.** They are not the same file:
  - `drg/fragment.yaml` — the `OrgDRGFragment` shape (#3387). Read by
    `doctrine.drg.org_pack_loader.load_org_pack` (`load_org_pack` reads
    `<pack_root>/drg/fragment.yaml` explicitly), surfaced through
    `charter.drg.load_org_drg` → `merge_three_layers`.
  - pack-root `*.graph.yaml` and `drg/*.graph.yaml` — the `DRGGraph` shape.
    `load_validated_graph` reads **pack-root** `*.graph.yaml` only (via
    `has_graph_files` + `merge_layers`); `drg/*.graph.yaml` is read by **no**
    runtime path.
- **Cascade reads root-level `*.graph.yaml` only.** `_drg_helpers.load_validated_graph`
  folds each org root with `merge_layers(merged, load_graph_or_dir(root))` guarded
  by `has_graph_files(root)`. Fragment edges never enter this graph. Confirmed by
  the (currently green) pinning test
  `TestGraphlessPackWithFragmentEdgeIsInvisibleToCascade`.
- **`merge_three_layers` already owns the bridge machinery.** It resolves edge
  endpoints (`_resolve_edge_endpoint`: fragment-local bare id → fully-qualified
  URN → bare id matched by declared kind), canonicalises + de-duplicates edges
  (`_OrgEdgeCollector`), tags provenance, and returns a `DRGGraph` whose `.edges`
  carry the fragment `requires`/`suggests` edges. The diagnostic path
  (`lint`, `_status_collectors`, `_doctrine_collect`, `_profile_health_render`)
  already calls it as `merge_three_layers(load_built_in_graph(), fragments, None)`.
- **PROBE (executed): `load_org_drg` raises on a fragment-less pack.** A pack that
  ships a root-level `*.graph.yaml` but **no** `drg/fragment.yaml` makes
  `load_org_drg(repo_root)` raise `OrgPackMissingError` (it calls `load_org_pack`
  for every configured pack, and `load_org_pack` raises when
  `drg/fragment.yaml` is absent). This is the linchpin constraint for the caller
  design (D3).
- **PROBE (executed): baseline is green.**
  `tests/specify_cli/cli/commands/charter/test_org_cascade_chain.py` = **15
  passed** on the mission base. The root-graph cascade tests
  (`TestSingleOrgPackCascade`, `TestTwoPackChainCascade`) use root-level
  `fixture.graph.yaml` with **no** `drg/fragment.yaml` — so any caller that routes
  the cascade path through a strict `load_org_drg` would regress these to red.

## Decisions

### D1 — Bridge composition inside `load_validated_graph`

**Decision.** Add `org_fragments: list[OrgDRGFragment] | None = None` to
`load_validated_graph`. Keep the existing per-root `merge_layers` loop for
pack-root `*.graph.yaml` packs. When `org_fragments` is non-empty, fold them by
calling the **existing** `merge_three_layers`, using the built-in+root-graph
merge as its `built_in` base and passing the project layer through it:

```
built_in = load_built_in_graph()
root_merged = built_in
for root in roots:
    if has_graph_files(root): root_merged = merge_layers(root_merged, load_graph_or_dir(root))
    elif root.exists() and not (root / "drg" / "fragment.yaml").exists(): WARN   # D2
project = load project overlay (unchanged)
if org_fragments:
    merged = merge_three_layers(built_in=root_merged, org_fragments=org_fragments, project=project)
else:
    merged = merge_layers(root_merged, project)      # today's exact path
assert_valid(merged)
return merged
```

**Rationale.** Reuses `merge_three_layers` endpoint-resolution + `_OrgEdgeCollector`
dedup verbatim (C-002 — no forked canonicalisation). The `else` branch is the
current code path unchanged, so build-time and no-fragment callers are
byte-identical (FR-003). Cascade only needs *reachability* (`.edges` by relation);
it does not read provenance, so treating `root_merged` as `merge_three_layers`'
`built_in` base is behaviourally correct for the cascade consumer.

**Alternatives considered.**
- *Call `merge_three_layers(load_built_in_graph(), fragments, project)` and fold
  root-graph roots separately afterwards* — rejected: `merge_three_layers` folds
  `project` internally and runs the asset/template uniqueness scan; splitting
  project across two merges risks double-count and ordering drift.
- *Re-implement a fragment→edge bridge inside `_drg_helpers`* — rejected outright
  by C-002.

**Note (reviewer check).** `merge_three_layers` protects `built_in` invariants via
`_built_in_invariant_ids(built_in)`. With `root_merged` as base, org root-graph
URNs join the protected set, so a fragment that re-declares a root-graph URN with
a *different kind* would hard-fail. This is an acceptable, rare edge (same-pack
double-declaration); documented so review can confirm no in-repo fixture hits it.

### D2 — D-005 graphless-warning re-scope (FR-004, C-003)

**Decision.** The warning branch fires only when a configured, on-disk root ships
**neither** a root-level `*.graph.yaml` **nor** a `drg/fragment.yaml`. A
fragment-bearing pack is no longer graphless once its edges cascade (D1), so
warning it would be a lie. The degrade posture (never silent for a genuinely
graphless pack) is preserved — only the trigger narrows. Symmetric with D5's
validator re-scope: both key off "neither root graph nor fragment.yaml".

### D3 — Resilient fragment resolution for the caller (`load_org_drg(strict=…)`)

**Decision.** Add `strict: bool = True` to `charter.drg.load_org_drg`. With
`strict=True` (default) behaviour is **identical** to today (delegates to
`load_org_pack`, which raises `OrgPackMissingError` on a missing
`drg/fragment.yaml`). With `strict=False`, a pack whose `drg/fragment.yaml` does
not exist is **skipped** (contributes no fragment layer); its root-level
`*.graph.yaml`, if any, is still folded by D1's `merge_layers` loop, and a pack
with neither is warned by D2. The cascade callers pass `strict=False`.

**Rationale.** The diagnostic callers keep the strict default, so `doctor
doctrine` / `charter list` / `lint` / status behaviour and their
`OrgPackMissingError` reporting are byte-identical (NFR-001). Per-pack resilience
(vs. a caller-side `try/except OrgPackMissingError → []`) correctly handles a
**mixed** chain (pack1 root-graph, pack2 fragment): the all-or-nothing catch
would drop pack2's real fragment edges on pack1's absence. Reuses `load_org_pack`
for the per-pack parse — no re-implementation (C-002). `layer_index` continues to
come from the full-registry `enumerate`, so a skipped pack does not renumber its
siblings.

**Alternatives considered.**
- *Change `load_org_pack`/`load_org_drg` default to skip-on-missing* — rejected:
  it alters the diagnostic contract (NFR-001) and hides genuinely-misconfigured
  packs from `lint`.
- *A separate `load_present_org_drg` function* — rejected: a keyword flag on the
  one canonical loader is more discoverable and avoids a near-duplicate.

### D4 — Which runtime call sites thread `org_fragments`

**Decision.** Thread the cascade consumers required by the spec's success
criteria: `activate.py` (both load sites, L315/L409) and `deactivate.py` (L165) —
these are the `--cascade` path SC-001 measures. Evaluate `review/gate_bindings.py`
(L295) and `mission_step_contracts/executor.py` (L344/L362) as **additive
consumers**: threading them makes org fragment edges visible to review gates and
mission-step resolution too, which is consistent and low-risk (one call-site
argument each). Default: fold gate_bindings + executor threading in the same
change; if the executor's pre-probe/`healthy_roots` degrade logic makes it
non-trivial, defer executor threading as a tracked follow-up with rationale (its
own graph-load already degrades graphless packs and is not on SC-001's path).
Build-time callers (`compiler.py`, `consistency_check.py`, `reference_resolver.py`,
`glossary/drg_builder.py`, `action_doctrine_bundle.py`) are **not** touched — they
pass no org roots and must stay org-inert (FR-003).

### D5 — Validator reconciliation (FR-006, C-001, NFR-003)

**Current behaviour.** `_check_drg_root_graph_missing` fires an **error** when a
pack has `drg/*.graph.yaml` **and** no pack-root `*.graph.yaml`, with the message:
"…The runtime … reads the pack root directly, **not drg/ fragments** — this pack's
DRG content will not be read as authored." The blanket "not drg/ fragments" claim
is *the* statement that inverts once the runtime reads `drg/fragment.yaml`.

**Decision (CORRECTED post pre-merge squad / CI — see correction note below).**
Reconcile in the SAME change as D1 (atomic — NFR-003):
1. **Do not re-scope the trigger on `drg/fragment.yaml` presence.** ~~Re-scope so the
   finding does not fire when the pack ships a `drg/fragment.yaml`, mirroring D2.~~
   *(This mirroring was WRONG — see the correction note.)* The finding fires when a
   `drg/*.graph.yaml` document exists with no pack-root `*.graph.yaml`, **regardless**
   of a coexisting `drg/fragment.yaml`: the graph document is read by no runtime path,
   so the author still needs the signal. A `fragment.yaml`-only pack already yields no
   finding because it ships no `drg/*.graph.yaml` (glob miss).
2. **Correct the message** to state the actual runtime read-set — pack-root
   `*.graph.yaml` **and** `drg/fragment.yaml` — removing the false blanket "not
   drg/ fragments" claim, so `pack validate` never contradicts the runtime
   (SC-003).

**CORRECTION (post pre-merge squad / CI).** The original D5 mirrored the validator
finding onto D2's runtime predicate ("suppress when a `drg/fragment.yaml` exists").
That was wrong: the validator finding and the runtime graphless-warning answer
**different** questions and are **not** mirror predicates. The runtime warning asks
"does this pack contribute *anything* to cascade?" (a fragment satisfies it); the
validator asks "is this *specific* `drg/*.graph.yaml` document unread?" (independent
of any fragment). Because `org init` scaffolds a `drg/fragment.yaml` into every pack,
the mirrored suppression neutered the guard for all scaffolded packs — caught by the
pre-existing `tests/cli/test_doctrine_org_commands.py` AC-7b test (red on CI's
`fast-tests-cli`). SC-003 / US3 AC1 still hold: a `fragment.yaml`-only pack ships no
`drg/*.graph.yaml` and so never matches the glob.

**Rationale / spec tension noted for review.** The spec's overview says the
validator "never flags a fragment.yaml-only pack" (true: `fragment.yaml` does not
match the `*.graph.yaml` glob, so a fragment-only pack already gets no finding),
while US3's independent test phrases it as "no longer reports it as
uncascaded/unread." The reconciliation above satisfies both the letter (a
fragment-bearing pack yields no "will not be read" finding) and the intent (the
tool tells one story). Full removal of the finding was considered and **rejected**:
`drg/*.graph.yaml` is genuinely unread by every runtime path, so the finding still
protects operators against that dead-content shape; removing it would trade one
silent gap for another. This is an engineering call within the locked approach,
flagged here so review can confirm the chosen scope.

### D6 — Golden re-ledger & diagnostic invariance (NFR-001/002)

**Decision.** During implementation, grep the affected test surfaces for
golden/count assertions that could move when fragment edges become cascade-visible
(cascade-reach counts, `charter list` / `doctor doctrine` snapshots). Capture any
real delta in **one** reviewed update with a written rationale; assert the four
diagnostic `merge_three_layers` callers and their output are unchanged (they are
not touched). If no golden moves, record that explicitly (silence is not proof).

## Adversarial evidence

No security-impacting dependency decision is made (no dependency change), so the
supply-chain adversarial pass is N/A. The load-bearing adversarial concern for
this mission is **regression risk to the currently-green root-graph cascade
tests** (D3) and **diagnostic-path invariance** (D6); both are pinned by executed
probes above and by the preserved `TestSingleOrgPackCascade` /
`TestTwoPackChainCascade` / `TestGraphlessOrgPackDegradesGracefully` tests, which
must stay green. No contested finding is dropped.
