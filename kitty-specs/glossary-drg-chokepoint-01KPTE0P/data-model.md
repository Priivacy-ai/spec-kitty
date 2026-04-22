# Data Model: Glossary DRG Residence and Executor Chokepoint

**Mission:** `glossary-drg-chokepoint-01KPTE0P`
**Date:** 2026-04-22

---

## New Types

### `GlossaryObservationBundle`

Module: `src/specify_cli/glossary/chokepoint.py`

```
GlossaryObservationBundle
  matched_urns:       tuple[str, ...]                  # stable glossary:<id> URNs found in request
  high_severity:      tuple[SemanticConflict, ...]     # surfaced inline to host (Severity.HIGH only)
  all_conflicts:      tuple[SemanticConflict, ...]     # all severities (written to trail)
  tokens_checked:     int                              # number of tokens examined by the chokepoint
  duration_ms:        float                            # elapsed time in milliseconds
  error_msg:          str | None                       # non-None on chokepoint failure; None on success
```

Immutable (`frozen=True` dataclass). Always fully populated — never `None`. An invocation with no glossary terms configured produces `GlossaryObservationBundle(matched_urns=(), high_severity=(), all_conflicts=(), tokens_checked=N, duration_ms=F, error_msg=None)`.

**JSONL serialization** (appended to invocation file as `event: "glossary_checked"`):

```json
{
  "event": "glossary_checked",
  "invocation_id": "01KPTE0P5JVQFWESWV07R0XG4M",
  "duration_ms": 12.4,
  "tokens_checked": 47,
  "matched_urns": ["glossary:d93244e7"],
  "high_severity_count": 1,
  "all_conflict_count": 2,
  "error_msg": null,
  "conflicts": [
    {
      "urn": "glossary:d93244e7",
      "term": "lane",
      "conflict_type": "inconsistent",
      "severity": "high",
      "confidence": 0.9,
      "context": "request_text"
    }
  ]
}
```

Low/medium conflicts appear in `conflicts` (written to trail) but are absent from `high_severity` (not surfaced to host).

---

### `GlossaryTermIndex`

Module: `src/specify_cli/glossary/drg_builder.py`

Internal data structure; not a public API surface. Built by `build_index()` from the `GlossaryStore`.

```
GlossaryTermIndex
  surface_to_urn:        dict[str, str]                 # normalized surface → glossary:<id>
  surface_to_senses:     dict[str, list[TermSense]]     # normalized surface → active senses
  applicable_scope_set:  frozenset[str]                 # GlossaryScope values used (v1: SPEC_KITTY_CORE + TEAM_DOMAIN)
  term_count:            int
```

Indexed on the normalized canonical surface (lowercased, stripped). Lemmatized form aliases point to the same URN as the canonical surface entry.

---

### `GlossaryChokepoint`

Module: `src/specify_cli/glossary/chokepoint.py`

Stateless except for the lazily loaded `GlossaryTermIndex`. Safe to construct without I/O.

```
GlossaryChokepoint(repo_root: Path, applicable_scopes: set[GlossaryScope] | None = None)
  _index: GlossaryTermIndex | None   (lazy, set on first run())

  run(request_text: str, invocation_id: str) -> GlossaryObservationBundle
    # tokenize → normalize → lemmatize → lookup → classify conflicts
    # never raises; catches all exceptions internally and returns error-bundle
```

The `applicable_scopes` parameter defaults to `{SPEC_KITTY_CORE, TEAM_DOMAIN}` (v1 broad applicability). Passing a narrower set is supported but not exercised in this tranche.

---

### `GlossaryDRGBuilder`

Module: `src/specify_cli/glossary/drg_builder.py`

Builds the in-memory glossary DRG layer from the active `GlossaryStore`. Returns a `DRGGraph` containing only `glossary:<id>` nodes and `vocabulary` edges.

```
build_glossary_drg_layer(store: GlossaryStore, applicable_scopes: set[GlossaryScope]) -> DRGGraph
  # For each active sense in applicable_scopes:
  #   mint DRGNode(urn=glossary_urn(sense.surface), kind=NodeKind.GLOSSARY, label=sense.surface.surface_text)
  #   add one DRGEdge per action node: source=action_urn, target=glossary_urn, relation=Relation.VOCABULARY
  # Returns DRGGraph with generated_by="glossary-drg-builder-v1"
  # This graph is NOT merged into the shipped DRG; it is used directly by GlossaryChokepoint.

glossary_urn(surface_text: str) -> str
  # "lane" → "glossary:d93244e7"
  # hashlib.sha256(surface_text.encode()).hexdigest()[:8]
```

The action URNs for v1 (vocabulary edge sources) are loaded from the shipped DRG via `load_validated_graph()` and filtered for `kind=NodeKind.ACTION`.

---

## Modified Types

### `NodeKind` (in `src/doctrine/drg/models.py`)

Added member:

```python
GLOSSARY = "glossary"   # Governs glossary:<id> URN prefix
```

Existing members unchanged. The existing URN validator (`prefix == kind.value`) passes because `"glossary".split(":")[0] == "glossary"` matches `NodeKind.GLOSSARY.value == "glossary"`.

Backward-compatibility: existing DRG YAML files that do not contain `kind: glossary` nodes load and validate successfully. The `NodeKind` StrEnum accepts unknown values gracefully in load paths that use `model_validate` with `extra="ignore"`.

---

### `InvocationPayload` (in `src/specify_cli/invocation/executor.py`)

Added slot:

```python
__slots__ = (
    # ... existing slots ...
    "glossary_observations",   # GlossaryObservationBundle — always set by invoke()
)
```

`to_dict()` already iterates `self.__slots__`, so `glossary_observations` appears automatically in the dict output. The value is always a `GlossaryObservationBundle` instance — never `None` (per FR-008).

---

### `InvocationWriter` (in `src/specify_cli/invocation/writer.py`)

Added method:

```python
def write_glossary_observation(
    self,
    invocation_id: str,
    bundle: GlossaryObservationBundle,
) -> None:
    """Append a 'glossary_checked' event to the invocation's JSONL file.

    Best-effort: exceptions are silently suppressed.
    The invocation trail remains valid if this write fails.
    """
```

Appends a third line to `.kittify/events/profile-invocations/{invocation_id}.jsonl`. The `started` and `completed` events are unchanged. Existing readers that understand only `started`/`completed` events are unaffected.

---

## Chokepoint Call Sequence in `ProfileInvocationExecutor.invoke()`

```
invoke(request_text, profile_hint, actor)
  ┌─ 1. Resolve (profile_id, action) [existing]
  ├─ 2. build_charter_context() [existing, mark_loaded=False]
  ├─ 3. Run GlossaryChokepoint.run()            ← NEW (try/except)
  │       on success → GlossaryObservationBundle
  │       on exception → empty bundle with error_msg
  ├─ 4. write_started(record) [existing]
  ├─ 5. write_glossary_observation()             ← NEW (best-effort, try/except)
  ├─ 6. propagator.submit() [existing]
  └─ 7. return InvocationPayload(glossary_observations=bundle)   ← NEW field
```

The chokepoint (step 3) runs BEFORE the started record is written (step 4). This ensures the bundle is available when the payload is returned, and the timing measurement reflects only the chokepoint's own work.

---

## Severity Routing Contract (for hosts)

```
GlossaryObservationBundle.high_severity   → render inline in agent output BEFORE governance context
GlossaryObservationBundle.all_conflicts   → write to JSONL trail only
GlossaryObservationBundle.error_msg       → if non-None, host SHOULD log a warning but MAY ignore it
```

Inline format (suggested for Codex and gstack hosts):

```
⚠ Glossary conflict detected:
  "lane" — possible inconsistent use (Spec Kitty: parallel execution slot)
  Consider using the canonical term to avoid ambiguity.
```

This text is prepended to the governance context block, not injected into the LLM system prompt.

---

## URN Stability Contract

| Canonical surface | URN |
|------------------|-----|
| `lane` | `glossary:d93244e7` |
| `work package` | `glossary:50064d7f` |
| `mission` | `glossary:ceb00a91` |

URNs are stable across process restarts, store rebuilds, and Spec Kitty version upgrades, as long as the canonical surface form (lowercased, stripped) does not change. If a term's canonical surface is renamed, the URN changes — this is expected and acceptable (the old URN becomes orphaned).

---

## Test Fixtures

Test seeds (in `tests/specify_cli/glossary/fixtures/`):

```yaml
# seed_spec_kitty_core.yaml
terms:
  - surface: "lane"
    definition: "A parallel execution slot in the Spec Kitty worktree model."
    status: active
    confidence: 1.0
  - surface: "work package"
    definition: "An atomic unit of implementation work tracked in kitty-specs/."
    status: active
    confidence: 1.0
  - surface: "mission"
    definition: "A governed feature or task lifecycle in Spec Kitty."
    status: active
    confidence: 1.0
```

Test request texts:

```
# zero conflicts
"What is the current status of WP01?"

# high-severity conflict
"Move the WP to a new lane (channel) for async processing."

# medium-severity ambiguity
"This sprint we should complete the mission planning."
```
