# Contract: Canonical Operator Surface Map

**Governs**: M2 authoritative output `canonical-operator-surface-map.md` and frozen CLI projection `canonical-cli-route-map.md`
**Requirements**: FR-004, FR-005, NFR-003, C-003, C-004, C-005
**Consumed by**: M2 implementation/review, M3–M6 exclusion checks, out-of-repo consumer coordination

## Boundary

M2 has one bounded local design question: the canonical replacement for every still-unfixed
operator-visible command route, serialized/API token, supported public Python API identifier, or
public distribution/project/wheel name, plus the publication-evidence disposition for that distribution.
It answers the question once in this frozen
map before implementation and owns every affected producer, reader, renderer, schema, event/API/JSON
consumer, workflow, test, prompt/skill, and doc regardless directory. M3–M5 exclude these assigned
hits. This is one map/question, not an invitation to defer unrelated path, glossary, skill/profile,
directive, or semantic-config decisions already fixed by the ADR contract.

The inventory and `stacked-plan.md` assignment table are exhaustive inputs. Every M2-owned route,
flag, output label, serialized config key, schema field/alias, enum value, policy key, event target
URN, or JSON field appears exactly once. ADR-fixed `governance.doctrine` (M1), overlay pathname and
directive ID (M3), and skill/profile IDs (M4) remain outside this M2 map; the ADR-fixed org-pack and
tracker seams are mandatory fixed M2 rows.
Non-public Python/module/symbol names may remain X1 even when an emitted alias is in scope. A Python
name/import is public when it appears in `__all__`, a package `__init__` re-export, public API/operator
docs or skills, or a supported external contract; installable distribution/project/wheel names and
metadata are public too. Those hits are OC, never X1. Inventory must enumerate the exact
`doctrine.api.__all__` members and the public metadata/content and wheel-closure contract rooted at
`src/doctrine/pyproject.toml`. A tracked implementation pathname such as
`src/doctrine/pyproject.toml` or `src/doctrine/api.py` is independently X1 unless that pathname is
itself installed or user-visible; public values/imports/exports inside it remain S7 OC.

## Required row fields

Each row records: stable map ID; OC IDs; semantic kind; full legacy form; canonical form; active
writers; active readers; renderers/consumers; compatibility reservation ID and disposition; named
canonical/legacy/enumeration tests; M6 removal proof; and any out-of-repo repo/owner/milestone/tracking
reference. Every legacy-bearing row joins exactly one planned `CR-##`. Before M2's first edit it
atomically replaces any `owner:M2; source_oc:<OC-##>` target descriptor with the literal canonical
form/map-row reference and resolves the reservation to `active` or, only for an unpublished
distribution name with publication evidence, `closed-no-channel`. The latter creates no product
alias/fingerprint, but its exact X3 control/evidence tombstone remains through M6. No blank owner,
`TBD`, wildcard family, representative-only row, or second compatibility question is permitted.

Command rows additionally record parent group, subcommand/flag, canonical route, hidden legacy route,
warning assertion, workflow/prompt/docs consumers, and route-specific test. The eight-command legacy
group and `doctor` route are enumerated individually.

Public-Python-API rows additionally record old module/symbol, canonical charter-facade import,
`__all__`/package re-export sites, documented/external consumers, parity test, 3.x
`DeprecationWarning` alias, and M6 supported-export/docs removal. The internal `src/doctrine/`
implementation may remain; after M6, direct imports from it are unsupported internals, not advertised
public surface.

Public-distribution rows additionally record legacy project/distribution/wheel metadata (including
`spec-kitty-doctrine` in `src/doctrine/pyproject.toml`), the canonical distribution and import facade,
build/install/packaging consumers, exact `doctrine.api.__all__` export membership, and wheel-closure
tests. One aggregate `doctrine.api` facade row joins the module/path OC once and carries a
`public_member_evidence` list of the exact `__all__` members. Only member names/imports that themselves
contain the legacy term receive additional OC-backed rows; legacy-free members are evidence, not
invented audit hits or duplicate OC joins. M2 records publication evidence: an unpublished legacy
distribution is renamed before first publication, resolves its CR to `closed-no-channel`, and gets no
invented product alias; a previously published name resolves its CR to `active` and requires
migration/owner/milestone plus supported 3.x compatibility where the package channel permits. Both
CR control/evidence records persist to M6.
M6 proves legacy distribution metadata, supported exports/docs, and wheel contents absent.

`canonical-cli-route-map.md` is a mechanically derived, frozen projection of exactly those command
rows. It records the authoritative map SHA-256 and has no independent decisions. M2 freezes both files
before edits; tests require set-equal command row IDs and values so the projection cannot drift.

## Fixed known serialized/API mappings

These mappings are inputs, not local questions. `<kind>` and `<id>` preserve their values.

| Legacy serialized/API surface | Canonical surface | Owner / compatibility |
|---|---|---|
| `doctrine:<kind>:<id>` target URN | `charter:<kind>:<id>` | M2 writers/readers/renderers/events; 3.x active-read alias; M6 removal |
| target kinds `doctrine_directive`, `doctrine_tactic`, `doctrine_procedure` | `charter_directive`, `charter_tactic`, `charter_procedure` | M2 schema + proposal/event consumers; M6 removal |
| proposal category `doctrine` | `charter` | M2 schema/API consumers; M6 removal |
| policy key `propose_doctrine_changes` | `propose_charter_changes` | M2 policy/config readers; M6 removal |
| serialized fixture/hash key `doctrine_snapshot` | `charter_snapshot` | M2 canonical hash writes + canonical-first/legacy-hash fallback warning + fixture manifest/rekey migration; M6 only after zero legacy fixture hashes |
| tool-surface enum value `doctrine_skill` | `charter_skill` | M2 tool API readers/writers; M6 removal |
| emitted JSON field `missing_from_doctrine` | `missing_from_charter` | M2 serialization alias/renderers; internal attribute may remain X1; M6 old alias removal |

Mandatory public-API rows include every exported/documented `DoctrineCatalog`,
`DoctrineSelectionConfig`, and `DoctrineService` surface, their loaders/factories/re-exports, and any
additional legacy-bearing public symbol discovered by inventory. They also include the single
OC-backed aggregate `doctrine.api` facade row with exact `public_member_evidence`, plus the
`spec-kitty-doctrine` project/distribution/wheel metadata and wheel-closure consumers. M2's sole map
question chooses collision-free canonical charter-facade and distribution names where this contract
does not fix one; M2 owns all local consumers.

Discovery of another M2-scope serialized/API token adds a complete row governed by the same M2
question before any edits. It cannot be reassigned by directory to M3–M5. The final map records zero
unmapped M2 operator-surface OC hits and its joined OC/manifest totals.

## Write/read/history contract

- Canonical writers emit only canonical values after M2.
- During 3.x, active readers accept registered old values, migrate or normalize them, and warn where
  operator-triggered. Exact registry fingerprints and frozen maxima follow C-004. An evidence-backed
  unpublished distribution has no old external reader/channel, must not invent one, and retains only
  its `closed-no-channel` CR control/evidence tombstone until M6.
- Active persisted state is upgraded or given an owner/milestone before M6; M6 removes active legacy
  reads and proves the compatibility inventory empty.
- The fixture-hash seam writes the canonical key/hash only, first probes the canonical fixture path,
  then the registered legacy-hash path with warning during 3.x. M2 ships a deterministic manifest/rekey
  migration and byte-equivalence tests; M6 requires zero legacy fixture paths before removing fallback.
- Immutable X2 journals/snapshots remain byte-identical. Each applicable map row names the existing
  readers/renderers that translate its old value at the display boundary. Any literal matcher used
  solely for this non-emitting X2 translation is X3 from the start, has a named zero-legacy-output
  test, and is never an active-input alias.

## Pass conditions

Every inventory OC classified as command, serialized/API, supported public Python API, or public
distribution/wheel metadata is joined exactly once. The aggregate facade row enumerates exact
`__all__` membership without inventing hits or reusing its OC in member rows. Every row has a canonical
form, complete local consumers, external coordination, and exactly one CR whose target and
`active|closed-no-channel` disposition M2 resolves before edits. Canonical writers emit only new values;
registered old active reads warn in 3.x; no alias is invented for an unpublished distribution;
the unpublished CR tombstone/control persists until M6; immutable history renders canonically; the CLI projection is set-equal to authoritative command rows;
M3–M5 contain no mapped hit or unresolved dependency.
