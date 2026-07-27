# Phase 1 Data Model: Phase 3 Charter Synthesizer Pipeline

**Mission**: `phase-3-charter-synthesizer-pipeline-01KPE222`
**Source**: confirmed planning answers (KD-1…KD-6) + Phase 0 research.
**Runtime language**: Python 3.11+. All entities are Pydantic v2 models or `@dataclass(frozen=True)`, chosen per field's mutability and schema-surfacing needs.

---

## E-1 · `SynthesisRequest` (frozen dataclass)

The input envelope handed to a single adapter `generate(...)` call.

| Field | Type | Required | Description |
|---|---|---|---|
| `target` | `SynthesisTarget` | yes | What to synthesize. |
| `interview_snapshot` | `InterviewAnswersSnapshot` | yes | Frozen copy of current interview answers. Never mutated. |
| `doctrine_snapshot` | `DoctrineCatalogSnapshot` | yes | Frozen read-only view of shipped doctrine relevant to this target. |
| `drg_snapshot` | `DRGGraphSnapshot` | yes | Merged (shipped + pre-existing project layer, if any) DRG used as resolution context. Shipped-only when first-time synthesizing. |
| `adapter_hints` | `Mapping[str, str]` \| `None` | no | Optional opaque hints the orchestrator may pass (e.g. `language="python"`); adapter may ignore. Included in hash. |
| `run_id` | `ULID` | yes | Run-scoped identity; NOT included in fixture-hash (see normalization rule 4). |

**Invariants**:
- All `*_snapshot` fields are immutable.
- Equality is structural, excluding `run_id`.

**Normalization for fixture keying (R-0-6)**: canonical JSON over `{target, interview_snapshot, doctrine_snapshot, drg_snapshot, adapter_hints, adapter_id, adapter_version}` with rules 1-3 from R-0-6; `run_id` excluded.

---

## E-2 · `SynthesisTarget` (frozen dataclass)

One unit of synthesis.

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | `Literal["directive", "tactic", "styleguide"]` | yes | Artifact kind (C-005 bounds this to three values in tranche 1). |
| `slug` | `str` | yes | Kebab-case artifact slug. Unique per `(kind,)`. |
| `source_section` | `str` \| `None` | maybe | Interview section label this target derives from. At least one of `source_section` / `source_urns` must be non-empty. |
| `source_urns` | `tuple[str, ...]` | maybe | DRG URNs (e.g. `directive:DIRECTIVE_003`) this target derives from. |
| `title` | `str` | yes | Human-readable title (flows to artifact YAML). |
| `artifact_id` | `str` | yes | Canonical artifact identity. For `directive`, conforms to `Directive.id` regex `^[A-Z][A-Z0-9_-]*$` (tranche-1 default: `PROJECT_<NNN>`, disjoint from shipped `DIRECTIVE_<NNN>`). For `tactic` / `styleguide`, equal to `slug`. Used as the URN identifier (see below) and, for directives, as the `id` field in the emitted artifact body. |

**URN rule** (computed, not stored): `urn = f"{kind}:{artifact_id}"`. This is the node URN emitted to the project DRG layer. For tactic / styleguide this reduces to `f"{kind}:{slug}"` because `artifact_id == slug`; for directive it is `f"directive:{PROJECT_<NNN>}"`.

**Filename rule** (computed, used by the storage writer): matches existing repository globs.
- `directive`: `<NNN>-<slug>.directive.yaml` where `<NNN>` is the numeric segment extracted from `artifact_id` (e.g. `PROJECT_001` → `001`).
- `tactic`: `<slug>.tactic.yaml`.
- `styleguide`: `<slug>.styleguide.yaml`.

**Validation**:
- `slug` matches `^[a-z][a-z0-9-]*$` (aligned with `Tactic.id` and `Styleguide.id` regex).
- For `kind == "directive"`, `artifact_id` matches `^[A-Z][A-Z0-9_-]*$` (aligned with `Directive.id` regex) and must *not* start with `DIRECTIVE_` (namespace reserved for shipped directives).
- At least one of `source_section` or `source_urns` is non-empty (otherwise the target has no provenance story).
- Every URN in `source_urns` must resolve in `drg_snapshot`.

---

## E-3 · `AdapterOutput` (frozen dataclass)

What an adapter returns from `generate(...)`.

| Field | Type | Required | Description |
|---|---|---|---|
| `body` | `Mapping[str, Any]` | yes | The artifact body, matching the shipped-layer Pydantic schema for `kind`. |
| `adapter_id_override` | `str` \| `None` | no | Optional per-call identity override (KD-3 / R). |
| `adapter_version_override` | `str` \| `None` | no | Optional per-call version override (KD-3 / R). |
| `generated_at` | `datetime (aware, UTC)` | yes | When the adapter produced this output. |
| `notes` | `str` \| `None` | no | Optional human-readable adapter note; not used for validation, recorded in provenance verbatim. |

**Validation** (performed by orchestrator, not adapter):
- `body` parses against shipped-layer schema for `kind` (FR-019). Failure → `SynthesisSchemaError`; artifact rejected; no provenance written.

---

## E-4 · `ProvenanceEntry` (Pydantic model, round-tripped via `ruamel.yaml`)

Per-artifact provenance sidecar at `.kittify/charter/provenance/<kind>-<slug>.yaml`. Lives under the bookkeeping tree, separate from the content it describes (`.kittify/doctrine/<kind-dir>/…`), so doctrine loaders never see it.

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | `Literal["1"]` | yes | Reserved for future provenance schema changes. |
| `artifact_urn` | `str` | yes | e.g. `tactic:how-we-apply-directive-003`. |
| `artifact_kind` | `Literal["directive","tactic","styleguide"]` | yes | — |
| `artifact_slug` | `str` | yes | — |
| `artifact_content_hash` | `str` | yes | blake3-256 hex over the emitted artifact YAML bytes. |
| `inputs_hash` | `str` | yes | blake3-256 hex over the normalized `SynthesisRequest` (R-0-6). |
| `adapter_id` | `str` | yes | The effective adapter id for this call (override-first, fallback to `adapter.id`). |
| `adapter_version` | `str` | yes | The effective adapter version. |
| `source_section` | `str` \| `None` | maybe | Copied from `SynthesisTarget.source_section`. |
| `source_urns` | `list[str]` | yes | Copied from `SynthesisTarget.source_urns` (may be empty if `source_section` is set). |
| `generated_at` | `str` (ISO 8601 UTC) | yes | Copied from `AdapterOutput.generated_at`. |
| `adapter_notes` | `str` \| `None` | no | Verbatim copy of `AdapterOutput.notes`. |

**Invariants**:
- `artifact_urn == f"{artifact_kind}:{artifact_slug}"`.
- `inputs_hash` is byte-stable under normalization (NFR-006 / test lock).

---

## E-5 · `ProjectDRGOverlay` (Pydantic model)

Additive overlay graph. Emitted to `.kittify/doctrine/graph.yaml` — the exact path the existing `src/charter/_drg_helpers.py` project-layer loader already reads. No loader change is required.

Reuses the existing `src/doctrine/drg/models.py :: DRGGraph` schema verbatim. Additional discipline:

- Every `DRGNode.urn` in the overlay is a `<kind>:<artifact_id>` (e.g. `directive:PROJECT_001`, `tactic:how-we-apply-directive-003`) that is NOT present in the shipped graph's nodes — synthesized artifacts carry new URNs; they do not shadow shipped URNs.
- Every `DRGEdge.source` is either a shipped URN or a newly-emitted overlay URN.
- Every `DRGEdge.target` is either a shipped URN or a newly-emitted overlay URN (never a dangling reference).
- The `generated_by` field is set to `"spec-kitty charter synthesize <version>"` for auditability.

**Validation gate** (FR-008, NFR-009, US-5): the merged graph (shipped + overlay via existing `merge_layers()`) must pass `validate_graph` with zero errors before promote.

---

## E-6 · `SynthesisManifest` (Pydantic model, manifest-last commit marker)

Top-of-bundle manifest at `.kittify/charter/synthesis-manifest.yaml`. The manifest lives under bookkeeping but lists content paths under `.kittify/doctrine/` — it is the explicit bridge between the two trees.

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | `Literal["1"]` | yes | Reserved. |
| `mission_id` | `str` \| `None` | no | Optional — captures which mission ran the synthesis for audit. |
| `created_at` | `str` (ISO 8601 UTC) | yes | When the manifest was written (== commit time). |
| `run_id` | `str` (ULID) | yes | Matches the staging dir that promoted. |
| `adapter_id` | `str` | yes | Primary adapter id used for this run (aggregated from `ProvenanceEntry.adapter_id` — for runs that mixed overrides, this field is empty string and per-artifact provenance is the authoritative record). |
| `adapter_version` | `str` | yes | Primary adapter version (see above). |
| `artifacts` | `list[ManifestArtifactEntry]` | yes | One entry per committed artifact. |

### E-6a · `ManifestArtifactEntry`

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | `Literal["directive","tactic","styleguide"]` | yes | — |
| `slug` | `str` | yes | — |
| `path` | `str` | yes | Repo-relative path to the artifact YAML under `.kittify/doctrine/<kind-dir>/`. Filename matches the existing repository glob: `<NNN>-<slug>.directive.yaml` / `<slug>.tactic.yaml` / `<slug>.styleguide.yaml`. |
| `provenance_path` | `str` | yes | Repo-relative path to the provenance YAML under `.kittify/charter/provenance/<kind>-<slug>.yaml`. |
| `content_hash` | `str` | yes | blake3-256 hex of the artifact YAML bytes. |

**Invariants**:
- For every entry, the file at `path` exists and its blake3-256 hash equals `content_hash`. Readers verify this before trusting the live tree.
- `provenance_path` exists and contains `artifact_content_hash == content_hash`.
- `run_id` matches the staging dir that produced it — forensically useful when `.staging/<runid>.failed` markers need to be correlated.

**Authority rule (KD-2)**: live tree is authoritative IFF manifest is present AND all `content_hash` checks pass. Otherwise treat as partial-and-rerunable.

---

## E-7 · `TopicSelector` (discriminated union, Pydantic)

Input to `resynthesize --topic <selector>`.

```python
TopicSelector = Annotated[
    DRGUrnSelector | KindSlugSelector | InterviewSectionSelector,
    Field(discriminator="kind"),
]
```

### E-7a · `DRGUrnSelector`

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | `Literal["drg_urn"]` | yes | Discriminator. |
| `urn` | `str` | yes | e.g. `directive:DIRECTIVE_003`. Must match `^[a-z_]+:[A-Za-z0-9_.-]+$`. |

### E-7b · `KindSlugSelector`

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | `Literal["kind_slug"]` | yes | Discriminator. |
| `artifact_kind` | `Literal["directive","tactic","styleguide"]` | yes | — |
| `artifact_slug` | `str` | yes | — |

### E-7c · `InterviewSectionSelector`

| Field | Type | Required | Description |
|---|---|---|---|
| `kind` | `Literal["interview_section"]` | yes | Discriminator. |
| `section` | `str` | yes | Must match a known interview section label. |

**Parsing rule** (FR-012 order — local-first for synthesizable kinds):
1. If the string contains `:` AND LHS ∈ `{"directive","tactic","styleguide"}`, try `KindSlugSelector` against the **project-local** artifact set first. Hit → resolve, done. This is the "local-first for synthesizable kinds" rule: operators editing their project doctrine naturally type `tactic:how-we-apply-directive-003`, and we must not route that to a shipped DRG URN lookup when a project artifact exists.
2. Else if the string contains `:`, try `DRGUrnSelector` against the merged (shipped + project) DRG graph.
3. Else (no `:`) try `InterviewSectionSelector` (exact match against interview section labels).
4. Else raise `TopicSelectorUnresolvedError` with candidates.

**Disambiguation**: for a string like `directive:PROJECT_001` where `PROJECT_001` is both a project-local directive artifact AND a project-layer DRG URN (which it will be after synthesis, because synthesis emits the corresponding node), step 1 matches first. The resolution is unambiguous — the local artifact and the DRG node refer to the same thing; regenerating the artifact regenerates the node. For `directive:DIRECTIVE_003` (a shipped URN), step 1 does not match (no project-local artifact of that slug), so step 2 resolves it as a DRG URN and the resynthesizer regenerates every project-local artifact whose provenance references it.

---

## E-8 · Error taxonomy

All errors inherit from `SynthesisError(Exception)`. All carry structured fields for `rich`-rendered CLI output.

| Error | Trigger | Key fields |
|---|---|---|
| `PathGuardViolation` | Write target under `src/doctrine/` (FR-016, US-7). | `attempted_path`, `caller` |
| `SynthesisSchemaError` | `AdapterOutput.body` fails shipped schema (FR-019). | `artifact_kind`, `artifact_slug`, `validation_errors` |
| `ProjectDRGValidationError` | `validate_graph` returns ≥1 errors on merged graph (FR-008). | `errors: list[str]`, `merged_graph_summary` |
| `DuplicateTargetError` | Two targets in one run share `(kind, slug)` (EC-7). | `kind`, `slug`, `occurrences` |
| `TopicSelectorUnresolvedError` | `--topic` selector does not resolve (US-6). | `raw`, `candidates: list[str]` |
| `TopicSelectorAmbiguousError` | (Reserved — ambiguity rule above makes this rare; raised only if an explicit disambiguation call flags it.) | `raw`, `candidates: list[str]` |
| `FixtureAdapterMissingError` | Fixture adapter cannot find fixture for hash (test-only). | `expected_path`, `kind`, `slug`, `inputs_hash` |
| `ProductionAdapterUnavailableError` | Production adapter cannot instantiate (R-0-5). | `adapter_id`, `reason`, `remediation` |
| `StagingPromoteError` | `os.replace` or manifest write fails during promote; orchestration rolls back. | `run_id`, `staging_dir`, `cause` |
| `ManifestIntegrityError` | A reader finds manifest-listed `content_hash` not matching disk content. | `manifest_path`, `offending_artifact` |

Every error is *structured*: it carries fields, not just a message. CLI renders via a shared `rich` panel helper in `src/charter/synthesizer/errors.py`.

---

## E-9 · State transitions

### Run lifecycle

```
CREATED  ──▶  STAGING  ──▶  VALIDATING  ──▶  PROMOTING  ──▶  COMMITTED
   │              │               │               │
   │              ▼               ▼               ▼
   │           FAILED          FAILED          FAILED
   │         (adapter/       (schema/         (os.replace
   │          schema)         DRG/path-        or manifest
   │                          guard)           error)
   ▼
ABORTED
```

- `CREATED` → new staging dir opened, no writes yet.
- `STAGING` → writes inside staging only (never in live tree, per path guard).
- `VALIDATING` → schema + DRG + path-guard + cross-checks on staged tree.
- `PROMOTING` → ordered `os.replace` of artifact + provenance files; finally manifest.
- `COMMITTED` → manifest written; staging dir wiped.
- Any `FAILED` transition preserves staging as `.staging/<runid>.failed/` with a `cause.yaml` diagnostic and a nonzero CLI exit.

### Resynthesis lifecycle

- Identical to run lifecycle above, but `STAGING` only stages the targeted artifacts; `PROMOTING` replaces only those files; manifest is **rewritten** (not appended) with the new `run_id` and updated entries for the regenerated artifacts. Untouched artifacts retain their prior `content_hash` in the manifest.

---

## E-10 · Entity → requirement traceability

Confirms every FR/NFR has at least one entity footprint:

| Req | Entities |
|---|---|
| FR-001 | E-1 |
| FR-002 | E-2 (Literal bound) |
| FR-003 | `SynthesisAdapter` Protocol (see `contracts/adapter.py`) |
| FR-004 | `FixtureAdapter`; E-8 `FixtureAdapterMissingError` |
| FR-005 | E-6 paths; R-0-2 layout |
| FR-006 | E-4 |
| FR-007 | E-5 |
| FR-008 | E-8 `ProjectDRGValidationError`; validation gate in E-9 |
| FR-009 | `compiler.py`/`context.py` DoctrineService wiring (plan §Modified) |
| FR-010 / FR-011 | CLI surfaces — contracts in `contracts/topic-selector.md` |
| FR-012 / FR-013 | E-7 + E-8 `TopicSelectorUnresolvedError` |
| FR-014 | E-4 `inputs_hash` byte-stability |
| FR-015 | E-6 + bundle manifest additive fields (R-0-4) |
| FR-016 | E-8 `PathGuardViolation` |
| FR-017 | E-9 resynthesis lifecycle (only targeted artifacts replaced) |
| FR-018 | `compiler.py`/`context.py` DoctrineService wiring |
| FR-019 | E-3 + E-8 `SynthesisSchemaError` |
| FR-020 | E-5 additive-only invariants |
| NFR-001…010 | Tracked via plan §Review & Validation Strategy |
| C-001…012 | Tracked via path guard, E-2 Literal bound, CLI selector contract, etc. |
