---
title: Profile-channel projection and delivery
description: Why styleguide/toolguide profile citations render pointer-only, and how to read the operating_procedures_unresolved diagnostic — for pack authors.
doc_status: active
updated: '2026-08-21'
type: explanation
audience: docs/context/audience/internal/lead-developer.md
related:
- docs/architecture/doctrine-kinds.md
- docs/architecture/doctrine-relationships.md
- docs/architecture/org-doctrine-layer.md
---
# Profile-channel projection and delivery

**BLUF:** When a pack author cites a directive, tactic, procedure, styleguide, or
toolguide on an agent profile, that citation reaches the DRG (the doctrine
relationship graph) *and* eventually reaches the agent — but not always the same
way. Directive/tactic/procedure citations inline their full body into the loaded
profile context. Styleguide/toolguide citations deliberately never do that —
they always render as a pointer (a fetch command), by design, to protect the
token budget. Separately, a built-in profile's `operating-procedures` entries are
checked at build time and by `spec-kitty doctor doctrine`; an entry that does not
resolve to a real procedure is a loud, fail-closed error at build time (and a
non-fatal `spec-kitty doctor doctrine` diagnostic that flips the health report
unhealthy), never a silent drop.

This page documents both contracts so a pack author knows what to expect without
reading the renderer source.

## Two contracts, one loaded profile

The implement loop loads an agent's resolved profile on every work package, so
the profile is a first-class governance entry vector
(`src/charter/context_renderers/profile_sections.py`). Five profile-selector
channels compose the rendered profile context:

| Channel | Profile field | Delivery |
|---|---|---|
| Directive | `directive-references` | Inline body |
| Tactic | `tactic-references` | Inline body |
| Procedure (`operating-procedures`) | `collaboration.operating-procedures` | Inline body |
| Styleguide | `styleguide-references` | **Pointer-only** |
| Toolguide | `toolguide-references` | **Pointer-only** |

This table (and the invariant it encodes — every channel is either inline-body
or a *documented* pointer-only choice, never a silent no-op) is structurally
pinned by `tests/charter/test_emit_delivery_bind.py`, which fails if a future
channel is wired into one seam and not the other.

## Contract 1 — styleguide/toolguide are pointer-only by design

A profile that cites a styleguide or toolguide never receives that artifact's
full body inline. Instead the rendered section carries a header line and the
canonical fetch stanza:

```
Profile-Cited Styleguides (<profile-id>):
  - plain-language: <rationale>
    Run: spec-kitty charter context --include styleguide:plain-language
    When you are about to apply a code change, run this command and apply the returned rule.
```

**Why.** Styleguide and toolguide bodies are shaped differently from a
directive's or tactic's (longer, more example-heavy) and are pulled *on demand*
rather than inlined on every profile load, to keep the profile block within the
prompt's token budget — a deliberate NFR-001 decision, not an oversight. The
reason is a named, importable constant so the choice is discoverable in code,
not only in a docstring:

```python
# src/charter/context_renderers/profile_sections.py
_STYLEGUIDE_TOOLGUIDE_POINTER_ONLY_REASON: str = (
    "styleguide/toolguide profile sections are pointer-only by design "
    "(NFR-001 token budget): their bodies are pulled on demand via the "
    "--include fetch stanza, never inlined on every profile load"
)
```

`tests/charter/test_emit_delivery_bind.py::test_pointer_only_reason_is_attested_non_empty`
pins that the constant exists and is non-empty, so the choice stays test-attested
rather than reverting to an unverified docstring aside.

Directive, tactic, and procedure citations are different: their bodies render
inline (subject to the same per-entry token-budget ceiling every channel
respects — an oversized entry falls back to the fetch stanza too, but that is a
budget fallback, not the styleguide/toolguide design default).

## Contract 2 — the `operating_procedures_unresolved` diagnostic

A built-in agent profile's `collaboration.operating-procedures` field lists
procedure IDs the profile relies on operationally. At DRG build time
(`_emit_operating_procedure_edges` in
`src/doctrine/drg/migration/extractor.py`) every entry is checked against the
real procedure nodes already minted in the graph:

- **Resolves to a procedure node** — an `agent_profile --requires--> procedure`
  DRG edge is emitted, and the profile channel's `requires` /
  `specializes_from` walk then delivers that procedure's body inline to the
  agent, the same as a directly-cited procedure.
- **Does not resolve** (a fictional entry, a typo, or an ID that names a node of
  the wrong kind) — the build **fails loud**: `extract_artifact_edges` raises
  `ValueError` rather than silently dropping the entry.

The same resolution question — "does this entry name a real procedure?" — is
also surfaced non-fatally by `spec-kitty doctor doctrine --json`, under
`org_drg["operating_procedures_unresolved"]`:

```json
{
  "org_drg": {
    "operating_procedures_unresolved": [
      {
        "profile_id": "example-profile",
        "entry": "not-a-real-procedure",
        "reason": "no_node",
        "resolved_kind": null
      }
    ]
  }
}
```

`reason` is `"no_node"` (the entry names nothing) or `"wrong_kind"` (the entry
names a real node of a different kind — `resolved_kind` then carries that
kind, e.g. `"tactic"`). The key is always present, even on a healthy tree
(an empty list), so a pack author can check its length rather than its
presence. A non-empty list also appends a message to `org_drg["errors"]`,
which makes `DoctrineHealthReport.healthy` report unhealthy — this diagnostic
is scoped to the **built-in** tier only; org/project-tier `operating-procedures`
entries are guarded at edge-emission time rather than hard-failed here.

Both consumers — the build-time raise and the doctor diagnostic — read through
the single authority `doctrine.agent_profiles.operating_procedures`
(`collect_operating_procedure_entries`, `resolve_operating_procedure_entries`,
`node_universe`), so the walk order, falsy-entry policy, and classification
logic cannot diverge between them.

## What this page does not cover

This page is about the **profile channel**: what a *loaded agent profile*
delivers. It is a different question from which `NodeKind`s reach a *mission
action's* rendered doctrine bundle — that delivery-verdict table (activation
gates, the `asset` special case, etc.) lives in
[Doctrine artifact kinds § Delivery verdicts](doctrine-kinds.md#delivery-verdicts-which-kinds-reach-a-mission).
For DRG edge semantics (`requires`, `suggests`, `specializes_from`, and the rest
of the relation vocabulary), see
[Doctrine relationships](doctrine-relationships.md).

**Resolved (#3629):** `AgentProfile` previously carried a
`context-sources.{doctrine-layers,tactics,toolguides,styleguides,additional}`
field family that was schema-legit but never read and reached no delivery path.
It has since been removed from the model and schema; profiles declare references
solely on the top-level `*-references` fields, which the extractor projects as
`agent_profile` DRG edges (`directive-references`/`tactic-references` →
`requires`, `toolguide-references`/`styleguide-references` → `suggests`).

## See also

- [`src/charter/context_renderers/profile_sections.py`](https://github.com/Priivacy-ai/spec-kitty/blob/main/src/charter/context_renderers/profile_sections.py) — the renderer source both contracts describe.
- [`src/doctrine/agent_profiles/operating_procedures.py`](https://github.com/Priivacy-ai/spec-kitty/blob/main/src/doctrine/agent_profiles/operating_procedures.py) — the single-authority resolution module for Contract 2.
- `tests/charter/test_emit_delivery_bind.py` — the structural test binding both contracts to the DRG-emit side.
- `tests/charter/test_profile_channel_delivery.py` — render-boundary tests for every profile-attested kind.
