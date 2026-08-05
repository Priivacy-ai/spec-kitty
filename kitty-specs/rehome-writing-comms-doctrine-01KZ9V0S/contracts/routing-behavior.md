# Contract: Routing Behavior (FR-005, NFR-002, SC-004)

Preserve legacy dispatch.

**Required test form (non-fakeable):** the regression MUST assert against the **shipped**
profiles — construct a `ProfileRegistry` populated from the real
`packs/built-in/agent_profiles/` YAML (not fixture stubs, not `MagicMock`), so the test pins the
narrowed YAML and not merely the router mechanic. The `_make_mock_registry([...])` form shown
below and in research D-03 is **illustrative of the mechanic only** — a mock hand-feeds `role`
and `priority`, so it passes regardless of the shipped YAML and MUST NOT be the sole coverage.
Each scenario also asserts the shipped `profile.role` (e.g. `diagram-daisy.role == "diagram-author"`)
so a mock cannot satisfy it.

## R-1 — Incumbent designer preserved (negative regression; RED-first)

- **Given** a registry with `designer-dagmar` (role `designer`, priority 50) and `diagram-daisy`
  (role `designer`, priority 60) and no discriminating context,
- **When** `route("design the login screen")`,
- **Then** `decision.profile_id == "designer-dagmar"`.
- **RED-first:** on the base (diagram-daisy still `roles[0]=designer`) this returns
  `diagram-daisy` — the test fails. After the narrowing (`roles[0]=diagram-author`) it passes.

## R-2 — Incumbent curator preserved (negative regression; RED-first)

- **Given** `curator-carla`@40, `doctrine-daphne`@48, `comms-cleo`@55, `synthesizer-sam`@50 all
  role `curator`, no context,
- **When** `route("classify these documents")`,
- **Then** `decision.profile_id in {"curator-carla", "doctrine-daphne"}` (an incumbent).
- **RED-first:** on the base returns `comms-cleo`; after narrowing cleo+sam leave the bucket → passes.

## R-3 — New profile still routes for its own scope (positive guard)

- **Given** `diagram-daisy` narrowed to `diagram-author` with its domain keywords,
- **When** a request explicitly names diagram-as-code / the profile hint,
- **Then** `diagram-daisy` is selected — narrowing did not strand it.

## R-4 — No unintended re-collision from canonical-verbs (guard)

- The `canonical-verbs` added for the shipped-profiles contract (D-04) must be domain-specific;
  assert the narrowed profiles do NOT re-enter the DESIGNER/CURATOR buckets via a generic verb.

## R-5 — Researcher non-collision (positive documentation; SC-004)

- **Given** a bare researcher verb (e.g. `route("research the market")`) with no context,
- **Then** an incumbent researcher (`researcher-robbie`) is selected — documenting that
  comms-cleo/synthesizer-sam do NOT collide on researcher (it is their secondary role). This
  proves the D-03 sharpening rather than leaving SC-004's researcher clause unmapped.

## Shipped-registry loading (required)

Populate a `ProfileRegistry` from the real `packs/built-in/agent_profiles/` set (copy the shipped
YAML into the registry dir — do NOT reuse `FIXTURES_DIR` stems, which `_make_registry` defaults
to). Assert the registry actually contains `diagram-daisy`/`comms-cleo`/`synthesizer-sam` loaded
from `packs/built-in`, and assert their narrowed `profile.role` values, so neither a mock nor a
stale fixture can pass the regression.
