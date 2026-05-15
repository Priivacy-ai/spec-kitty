# Contract: Org Doctrine Source — HTTP API Protocol

**Version**: 1.0  
**Mission**: `layered-doctrine-org-layer-01KRNPEE`  
**Status**: Draft — normative for organisations implementing the `api` source type

---

## Purpose

This document specifies the HTTP API contract that an organisation's doctrine service must
implement for spec-kitty's `ApiSource` to fetch from it. Implementing this contract is only
required if the organisation chooses `source_type: api` in their `doctrine.org` config.

Organisations using git or HTTPS bundle sources do not need to implement anything; they just
publish a pack directory. This contract is for organisations that have an existing governance
API (e.g., a policy service or a Confluence-backed governance hub) and want spec-kitty to
fetch doctrine artifacts from it directly.

---

## Base URL

The `url` field in `doctrine.org` config is the base URL. All endpoints are relative to it.

```
doctrine.org.url: "https://governance.internal.example.com/doctrine/v1"
```

---

## Authentication

Authentication uses bearer token via the `Authorization` header:

```
Authorization: Bearer <token>
```

The token is sourced from the `SPEC_KITTY_ORG_TOKEN` environment variable. If the variable
is not set, `ApiSource` proceeds without an `Authorization` header (for public endpoints).

For custom authentication schemes, the `SPEC_KITTY_ORG_AUTH_HEADER` environment variable
can provide the full value of the `Authorization` header (e.g.,
`SPEC_KITTY_ORG_AUTH_HEADER="Basic dXNlcjpwYXNz"`).

---

## Endpoints

### List artifact types

```
GET /artifact-types
```

**Response** `200 OK`:
```json
{
  "types": ["directives", "tactics", "styleguides", "toolguides",
            "paradigms", "procedures", "agent_profiles",
            "mission_step_contracts"]
}
```

`ApiSource` calls this endpoint first to discover which artifact types the server exposes.
Types not in the response are skipped (no error).

---

### Fetch artifacts by type

```
GET /artifacts/{artifact_type}
```

`{artifact_type}` is one of the values returned by `/artifact-types`.

**Response** `200 OK`:
```json
{
  "artifacts": [
    {
      "id": "acme-sec-001-threat-modelling",
      "filename": "acme-sec-001-threat-modelling.directive.yaml",
      "content": "... YAML string ..."
    }
  ]
}
```

Each item in `artifacts`:

| Field | Type | Description |
|---|---|---|
| `id` | `string` | The artifact's `id` field value |
| `filename` | `string` | Suggested filename for the local snapshot (must end in the correct extension) |
| `content` | `string` | Full YAML content of the artifact |

`ApiSource` writes each artifact's `content` to `<target_dir>/<artifact_type>/<filename>`.

---

### Fetch DRG extensions (optional)

```
GET /drg-extensions
```

If the server exposes DRG extensions, this endpoint returns them. If the endpoint returns
`404`, `ApiSource` skips DRG extensions (no error).

**Response** `200 OK`:
```json
{
  "fragments": [
    {
      "filename": "010-security.graph.yaml",
      "content": "... YAML string ..."
    }
  ]
}
```

`ApiSource` writes each fragment to `<target_dir>/drg/<filename>`.

---

### Pack version (optional)

```
GET /version
```

**Response** `200 OK`:
```json
{ "version": "v1.2.0" }
```

If `404`, `ApiSource` uses the HTTP response date as the version string in `pack-manifest.yaml`.

---

## Error handling

| HTTP status | `ApiSource` behaviour |
|---|---|
| `200` | Process response |
| `404` for optional endpoint | Skip silently |
| `401` / `403` | Fail fetch with credential error; print remediation hint |
| `429` | Retry once after `Retry-After` seconds; fail if second attempt also fails |
| `5xx` | Fail fetch with server error message |
| Network error | Fail fetch with connection error message |

On any failure, the existing local snapshot is not modified (atomic fetch guarantee).

---

## Versioning

This contract is versioned. The `spec-kitty` release notes will note any breaking changes.
Non-breaking additions (new optional endpoints) do not increment the contract version.

Implementors SHOULD expose the `/version` endpoint so that operators can audit which version
of governance artifacts their snapshot contains.

---

## Example server implementation sketch

A minimal Flask/FastAPI server satisfying this contract:

```python
# Pseudocode — not production code
@app.get("/artifact-types")
def artifact_types():
    return {"types": ["directives", "agent_profiles"]}

@app.get("/artifacts/{artifact_type}")
def artifacts(artifact_type: str):
    items = load_from_governance_store(artifact_type)
    return {"artifacts": [
        {"id": a.id, "filename": a.filename, "content": a.to_yaml()}
        for a in items
    ]}

@app.get("/version")
def version():
    return {"version": governance_store.current_version()}
```
