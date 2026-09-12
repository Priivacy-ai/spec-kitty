# Research: Meta.json Fail-Closed Read Routing

Phase 0 decisions. Most were resolved by the pre-spec research pass and the post-spec adversarial squad (structure / anti-laziness / live-gate / sequencing lenses); this consolidates them in Decision / Rationale / Alternatives form.

## D1 — Home of the L1 decode primitive and the unified comparator

- **Decision**: Place the L1 `decode_meta` primitive, its typed error, and the unified VCS-lock comparator + named field-set in `src/kernel/` (new modules `kernel/meta_decode.py`, `kernel/vcs_lock.py`).
- **Rationale**: `src/kernel/` is the CI-enforced zero-dependency root (`kernel <- doctrine <- charter <- specify_cli`, `test_layer_rules.py`). Site A lives in `git/ref_advance.py`, which is git plumbing and must not import `specify_cli` (documented at `ref_advance.py:37-38`). L2 (`_parse_meta_text`) lives in `mission_metadata.py`, which imports `specify_cli.core.*` — so co-locating L1 there makes site A un-routable. Kernel is the only layer both plumbing and application can depend on. Bonus: it lets `core.paths` and `mission_metadata` both depend downward on kernel, relieving the existing deferred-import cycle (`mission_metadata.py:480-494`).
- **Alternatives considered**: (a) L1 in `mission_metadata.py` beside L2 — REJECTED: re-breaks C-003 for site A. (b) Comparator in `core/vcs/types.py` (already declares `vcs_locked_at`) — REJECTED: still under `specify_cli`, unreachable by plumbing.

## D2 — L1 signature and the malformed-vs-empty boundary

- **Decision**: `decode_meta(raw: str | bytes, *, on_malformed: Literal["raise","empty","none"] = "raise") -> dict[str, Any] | None`, pure (no I/O). `None`/typed-raise means **malformed only** (`json.JSONDecodeError`, `UnicodeDecodeError` on explicit utf-8 decode, or non-object top level). Empty/whitespace-only content is **not** L1's concern: it stays a benign short-circuit at L2 or the caller (`→ {}` where currently contracted, e.g. `merge_driver`).
- **Rationale**: The three current parsers disagree on empty input — `merge_driver` short-circuits empty→`{}` *before* `json.loads`, while `ref_advance`/`implement_cores` let `json.loads("")` raise and fold empty into the same silent `None` as corruption. If L1's single `None` channel meant "empty or malformed", routing would convert `merge_driver`'s benign empty→`{}` into a loud failure (violating FR-005) and make a red-first "empty at merge_driver" test non-deterministic. Keeping empty benign at L2/caller preserves each site's contract while L1 owns *malformed* exclusively.
- **Alternatives considered**: three-state return distinguishing empty from malformed at L1 — REJECTED as over-broad; the empty→benign decision is caller-specific, not a property of the bytes.

## D3 — Routed-census growth requires extending `ROUTED_CALLEES`

- **Decision**: Add the new decode symbols (kernel L1 + the public L2 entry) to `ROUTED_CALLEES` in `test_inline_meta_read_gate.py` in the same change that routes the sites, then re-derive `ROUTED_LOAD_META_FLOOR` from a fresh live measurement.
- **Rationale**: `scan_routed_load_meta_calls` counts only calls to the fixed `ROUTED_CALLEES` set (`load_meta`, `load_meta_strict`, `load_meta_or_empty`, `load_meta_fail_closed`, `_load_meta_fail_closed`, `_require_meta`) — all dir-level. The blob-fed sites route onto the new pure-decode symbols, which are invisible to the census unless added. Live census measured on this branch = **134**; floor = **130**, margin = **4** → the gate sits at its exact ceiling (134−130=4). Without extending `ROUTED_CALLEES`, routing does not raise the census and FR-008 is a no-op.
- **Alternatives considered**: leave census unchanged and rely on the inline-read gate — REJECTED: the inline gate is a *ceiling* on un-routed reads and would not credit the routing.

## D4 — Floor re-derivation is verifiable via the existing margin, not an honor-system "not copied"

- **Decision**: Express the floor requirement as: after routing, `ROUTED_LOAD_META_FLOOR` sits within `ROUTED_LOAD_META_FLOOR_MARGIN` (4) of the freshly-measured live census and strictly below it (`live - MARGIN <= floor < live`), by the established `floor = live - 3` convention.
- **Rationale**: A stored integer is byte-identical whether measured or pasted, so "0 copied constants" is not machine-checkable. The *existing* gate already enforces the checkable control: `test_routed_load_meta_floor` asserts `len(routed) >= floor`, `len(routed) > floor` (anti-vacuity), and `len(routed) - floor <= MARGIN`. Anchoring the requirement to that gate makes it enforceable.
- **Alternatives considered**: a bespoke "derivation provenance" record — REJECTED as unverifiable ceremony; the margin gate already is the control.

## D5 — Enforce "one decoder" and "all reads routed" with gates, not a hand count

- **Decision**: Add (FR-010) an architectural check that fails on any `json.loads`/`json.load` applied to `meta.json` content outside the kernel L1, plus a completeness check that no un-routed bypass read hides beyond the enumerated 5. Close the NFR-002 inline-literal hole by asserting no inline VCS-lock field-set literal + exactly one named declaration.
- **Rationale**: The census/allow-list gates do not count *decoders*; a hidden hand-rolled `json.loads` over meta content would pass them. "5 sites" is a human count; the routed floor is a floor (≥) and cannot detect a 6th un-routed site. Machine enforcement makes NFR-001/SC-001/SC-003 non-fakeable.
- **Alternatives considered**: rely on review — REJECTED per anti-laziness lens (fakeable).

## D6 — Red-first is a captured deliverable with typed + identifier assertions

- **Decision**: Each site's diagnosability test is captured **red against pre-routing code** (record the failing output / a known-absorbing stub), and asserts BOTH the shared kernel typed error type AND a message naming `meta.json` + the site's source identifier (filesystem path for A-worktree/C; `ref:path` blob spec for the committed reads). At site E, tests reflect the honest per-parser starting state (one arm already names the path; one raises unnamed `JSONDecodeError`).
- **Rationale**: "red-first" as an adjective is fakeable (write green-first, relabel). `assert "meta.json" in str(exc)` is trivially satisfiable (any path ends in `meta.json`). Pinning the type + a site-appropriate identifier closes both holes.
- **Alternatives considered**: message-substring only — REJECTED as fakeable.

## D7 — Sequencing: per-module atomic, serialized on the floor constant

- **Decision**: Foundation first (kernel L1 + public L2 + L2/L3 re-express, census-neutral, green alone). Then per-module atomic routing units (ref_advance / implement_cores+implement / merge_driver), each deleting its parser AND rewiring its callers together. Routing units serialize on the single `ROUTED_LOAD_META_FLOOR`; a final closeout unit pins the cumulative floor and lands the gates + governance record.
- **Rationale**: Deleting a private parser breaks its in-module callers at *compile/import* time; a naive "all deletions, then all rewiring" split leaves the tree non-importable between WPs. Two routing units editing the floor in parallel each compute a different partial-correct floor and collide. Serial-with-final-pin is the only green path.
- **Alternatives considered**: one monolithic routing WP — viable but un-reviewable and loses per-module isolation; rejected in favor of atomic-per-module.

## D8 — Governance (#3240) resolved by deviation record

- **Decision**: Record the #3240 deviation (do not add a `_baselines.yaml` count baseline). Document that `test_allowlist_matches_floor` (equality) + `test_allowlist_shrink_only` are strictly stronger than a `<=` count baseline and add stale-entry eviction the baseline lacks.
- **Rationale**: Operator decision (confirmed during discovery). Adding a second count baseline duplicates governance; the compensating controls already exist and are stronger.
- **Alternatives considered**: register the baseline — available but redundant; not chosen.

## Confirmed-sound premises (live-verified by the squad)

- All three named gates exist and are green now: `test_inline_meta_read_floor`, `test_routed_load_meta_floor`, `test_no_unaccounted_load_meta_call_sites`.
- Site A (`ref_advance._meta_change_is_vcs_lock_only`) is genuinely unrouted (parses via local `_parse_meta_object` → silent `None`).
- The two diagnosability test files are genuinely absent on this branch (must be authored fresh).
- Every site has a practical red-first injection seam (merge_driver reads a path; implement_cores via injectable `GitPort`; only ref_advance's committed arm needs a `git_repo` fixture).
