# Behavioural Contracts — fail-loud / single-source seams

No HTTP/API surface changes in this mission. The contracts here are the
**boundary behaviours** each fix must guarantee, expressed as testable
pre/postconditions. These are the acceptance anchors the WPs implement red-first.

## C-IC1 — DRG node-kind recognition is enum-derived (behaviour-pinned)

- **Given** the canonical `NodeKind` enum
- **Then** `_DRG_NODE_KINDS` is built by iterating `NodeKind` at import (reusing /
  aligning with the existing SSOT twin `merge.py:504` `_NODE_KIND_PREFIXES`), not a
  literal
- **Non-fakeable pin** (F7): a test that **monkeypatches `NodeKind`** with an extra
  member asserts `_DRG_NODE_KINDS` reflects it AND a URN `"{new}:id"` passes the
  gate at `topic_resolver.py:236` — proving derivation, not a second hand-copy that
  merely matches today. (Plain set-equality is a post-derive tautology — do not
  rely on it alone.)
- **Regression**: adding a real `NodeKind` member requires **no** edit to
  `topic_resolver.py`.

## C-IC2 — one profile-reference surface; no inert declared field

- **Given** any agent profile
- **Then** authoring a `context-sources` block causes a **load-time rejection**
  (pydantic `extra="forbid"`), not silent acceptance
- **Non-fakeable migration pin** (F6): a **divergent user-profile fixture** whose
  `context-sources.{directives,tactics}` contain ids **absent** from `*-references`
  — post-migration those ids appear on `*-references` (this is the only assertion
  that exercises the data-moving branch; the 25 shipped profiles are
  green-by-construction because their refs already duplicate the block).
- **And** a **frozen pre-migration snapshot** of each profile's `context-sources`
  ids proves "no reference lost" (once deleted there is nothing to compare against).
- **And** reviewer-renata's `additional: adversarial-evidence-disposition` binding
  is **re-homed deliberately** (F3), not dropped —
  `test_supply_chain_profile_bindings.py:158` (updated) still passes.
- **And** all 25 shipped profiles carry 0 `context-sources` blocks after migration
  (a *cleanup* check, not proof of migration correctness).
- **And** the full consumer set (F2) is updated: `agent_profiles/__init__.py`
  `__all__`, `generate_schemas.py:485`, `inline_reference_inventory.py`, and every
  asserting test — removal breaks nothing silently.

## C-IC3 — governance-profile selection fails loud (both tiers)

- **Built-in** (F8): an **end-to-end `generate_graph`** test over a doctrine root
  whose `governance-profile.yaml` has a fictional `selected_*` id raises
  `ValueError` naming `mission_type:field=id` (not just the synthetic-edge unit
  tests that exist today).
- **Org tier** (F9, net-new): org-tier governance-profile scope extraction is
  **implemented** (none exists today), and an org-tier fictional `selected_*` id
  fails loud the same way. C-IC3 is satisfied only when a red-first org-tier test
  passes — not by "documenting the gap".
- **And** valid selections (both tiers) mint scope edges unchanged (no false
  positive).

## C-IC4 — org `drg/fragment.yaml` reaches the deficient consumers

- **Given** an org pack shipping only `drg/fragment.yaml` (the canonical org shape,
  e.g. `packs/internal/`)
- **When** doctrine is loaded via the executor (`executor.py:362`) or
  `action_doctrine_bundle.py:192` — the two callers fixed to thread
  `org_fragments=load_org_drg(repo_root, strict=False)`
- **Then** the pack's fragment nodes and edges are folded into the merged DRG
  (not dropped) — a **valid**-fragment red test (the existing degrade test at
  `test_executor.py:915` uses a *malformed* fragment and does not cover this)
- **Non-fakeable count pin** (F11): the merged edge/node **multiset count** for the
  internal pack equals the single-fold count exactly (n, not 2n) — proving the
  fix did not introduce a double-fold for the 4 dual-callers
- **And** the fix is at the callers, **not** the `org_roots=` seam (F1: a seam fix
  double-folds for the dual-callers and mis-tiers org content as built-in). The
  `:245` DoctrineService seam is out of scope (F13).

## C-IC5 — chain delivers every declared kind (both classes); misconfig fails loud

- **Class-b (fragment-drop, this mission)**: built-in + spec-kitty-internal — every
  kind the internal pack declares (glossary pack, procedure, directive) and its
  `refines` edges reach the consumer via the executor/action-bundle seam.
- **Class-a (multi-org-pack fold)**: built-in + internal + a **2nd minimal org
  fixture** — assert **pack #2's** fragment node/edge appears in the merged graph
  (`merge_three_layers` iterates all fragments — `merge.py:1251` — so this is only
  provable with ≥2 org packs; F10).
- **Misconfig fails loud (enumerated, F11)** — parametrized cases, each with the
  expected exception type + message fragment, and **raise ≠ warn**:
  (i) `refines` edge → nonexistent built-in target → **raise** naming the target;
  (ii) missing required key in `drg/fragment.yaml` → **raise**;
  (iii) declared kind with no node → **raise**.
  (Distinct from C-IC4's honest "no graph" **warning** for a genuinely graphless root.)
- **Closes** #3530 (leaving the explicitly-non-child #3412 open).

## C-006 — no silent delivery change (golden-pinned)

- **Verification artifact** (F4/F6): regenerate `packs/built-in/agent_profile.graph.yaml`;
  the per-`agent_profile:*` edge-set diff is **empty** except the deliberately-
  ledgered delta of **exactly 3 added edges, 0 removed** (ledger entry 21 in
  `test_extractor_projection.py`): `python-pedro → directive:DIRECTIVE_034`
  (`requires` — the requires+suggests diamond) and `diagram-daisy → toolguide:{mermaid,plantuml}-diagramming`
  (`suggests` ×2 — the net-new `toolguide-references`→`suggests` projection; both
  targets were already transitively reachable, so delivery is unchanged). Any other
  diff is a regression. This same golden diff also catches omission of FR-007 (drop
  the extractor projection → all directive edges vanish).
