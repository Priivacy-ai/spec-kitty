# Contract: SimpleIndexProvider

## Behaviour

- Implements `LatestVersionProvider.get_latest(package) -> LatestVersionResult`.
- Never raises.
- Fetches PEP 503 simple index HTML for the configured base URL + package.
- Parses version candidates from anchor hrefs / wheel filenames; returns the highest **stable** sanitised version matching `_VERSION_RE`. Pre-releases are excluded (mirroring `PyPIProvider`'s stable `info.version`); the highest pre-release is returned only when no stable version exists. Anchors carrying a PEP 592 `data-yanked` attribute are skipped.
- TLS verification on; response size capped (same order as PyPIProvider 1 MiB); redirects not followed.
- Successful lookups set `source="simple_index"`.
- Failures return `version=None, source="none", error=<token>` (`timeout`, `http_error`, `parse_error`, `oversized`).

## Construction

- Base class accepts `index_url` (+ optional package filename prefix) in `__init__`.
- Fork subclasses provide zero-arg `__init__` that calls `super().__init__(...)` with their URL — **upstream defaults must not embed fork URLs**.

## Non-goals

- Full PEP 503 JSON simple API (HTML only for this mission unless already trivial).
- Authentication headers for private indexes (packager subclass may override fetch later; not required in upstream base).
