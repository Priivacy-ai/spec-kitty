# Issue matrix — `tracker-egress-refusal-3108-01KYWF1R`

Verdicts are from the closed allow-list: `fixed`, `verified-already-fixed`,
`deferred-with-followup`, `in-mission`.

`in-mission` is accepted at per-WP `approved` but is **rejected on the `done` transition**. Every
`in-mission` row below must resolve to a terminal verdict before the mission lands.

| issue | verdict | evidence_ref | title | scope |
|---|---|---|---|---|
| #3108 | fixed | WP01–WP08; acceptance suite `41 passed` (21 committed reds all green); `docs/migrations/tracker-egress-refusal.md` | Tracker egress refusal | **Gaps A and B are closed.** Gap B was the real defect — the `beads`/`fp` subprocess path was ungated entirely and shipped issue titles as argv. Gap A was the absence of separability. **The issue's *stated* premise — that `local_service.py` reaches Jira/Linear — is false and was falsified by measurement; that path was already gated by `#3030`.** The closing comment must say so, so the issue is not closed in a way implying a leak existed where none did. See the note below. |
| #3167 | deferred-with-followup | `bundle-c-handoff.md` §3.4; filed `Priivacy-ai/spec-kitty#3167` | Finish `#3030`'s Chain-B migration at the two remaining enforcement sites | Out of scope. Chain B (`sync/routing.py:255 is_sync_enabled_for_checkout`) is live on real egress gates at `sync/batch.py:338` and `sync/runtime.py:106` and honours the repo-slug-keyed `[sync.repo_defaults]` record that `sync/consent.py:625` refuses as a consent level. A fresh clone of an already-opted-in repository drains events Chain A denies. |
| #3168 | deferred-with-followup | `bundle-c-handoff.md` §3.4; filed `Priivacy-ai/spec-kitty#3168` | `tracker sync publish` raises an uncaught `AttributeError` on a beads/fp binding | Incidental live bug. `service.py:202-203` delegates unconditionally; `LocalTrackerService` defines no `sync_publish`; `_run_or_exit` (`cli/commands/tracker.py:346`) catches only `RuntimeError`/`ValueError`. Filed rather than absorbed, to keep this mission's diff attributable. |
| #3169 | deferred-with-followup | `bundle-c-handoff.md` §3.4; filed `Priivacy-ai/spec-kitty#3169` | Audit `TrackerProjectConfig._extra` consumers before promoting further keys | Mitigated here, not answered. This mission promotes `tracker.egress` from `_extra` to a known field. The general question — who reads `_extra` — is untouched. **It became load-bearing in review:** WP02's FR-010 deviation is justified precisely by refusing to widen `_extra`'s unaudited surface. |
| #3170 | deferred-with-followup | `bundle-c-handoff.md` §3.4; filed `Priivacy-ai/spec-kitty#3170` | `finalize-tasks` requirement-ID scraper cannot distinguish own IDs from citations | Upstream tooling gap hit by this mission. `runtime_bridge_cores.py:93` scrapes `\b(?:FR\|NFR\|C)-\d+\b` over the whole spec. Two modes: phantom unmapped IDs (cosmetic, hit here) and **false-positive mapping** (silent, inflates apparent coverage). Four citations of `#3030`'s IDs remain deliberately. |
| #3172 | deferred-with-followup | WP01 review finding F6; filed `Priivacy-ai/spec-kitty#3172` | `saas.readiness._probe_auth` blocks acceptance coverage of hosted tracker CLI commands | Found during WP01. The auth pre-flight aborts a `CliRunner` invocation of hosted tracker commands before mission code is reached, so a hosted refusing cell driven through the CLI would pass on an unrelated `exit 1`. WP01 constructs the real un-patched services directly instead; independent review confirmed the workaround sound and the transport path genuinely production. |
| #3174 | deferred-with-followup | WP08 review finding LOW-4; filed `Priivacy-ai/spec-kitty#3174` | No executed test that a refusing project keeps its ungated tracker commands working | The mission leaves `status`, `bind`, `unbind`, `map add` and un-scoped `map list` ungated, and the upgrade note tells operators so, but nothing executes that claim. "No over-gating" is the property distinguishing a correct gate from one that refuses everything — a gate refusing unconditionally would satisfy every refusal assertion in the suite. Measured true during WP04's review as a probe, and corroborated structurally by the 6-call-site census, but not committed as a test. |

## The `#3108` premise note

`#3108` says `tracker/local_service.py` sends issue titles to Jira/Linear under a machine-scoped
credential. **That is false.** Measured at `bb2020fea` with an isolated `HOME` and an HTTP
trip-wire on `httpx.Client.request`, calling `SaaSTrackerClient.push(provider="jira", …)` against
three project-local `.kittify/config.yaml` states:

- **no record (absence)** — REFUSED, `error_code=project_consent_denied`, **0 HTTP**
- **`sync: {enabled: false}`** — REFUSED, `error_code=project_consent_denied`, **0 HTTP**
- **`sync: {enabled: true}`** — gate passed, then failed later at `No valid access token`

The third case is the **positive control**. Without it, the first two are indistinguishable from a
probe that never reached the code.

`build_connector` cannot construct a Jira or Linear connector (`factory.py:17`,
`SUPPORTED_PROVIDERS = ("beads", "fp")`), those providers route to `SaaSTrackerService`, and that
path was **already gated by `#3030`** (`saas_client.py:329-331`).

The mission therefore implements what is actually broken:

- **Gap A — no separability.** One key, `sync.enabled`, answers both *may my events go to
  spec-kitty's hosted SaaS?* and *may my issue titles go to a tracker?*
- **Gap B — the `beads`/`fp` path is ungated entirely.** Observed, not inferred: with a real fake
  `bd` on disk and nothing in the production path patched, a project committing
  `sync.enabled: false` still shipped `['…/fake-bd','--json','create','ACME Holdings carve-out',…,
  '--description','confidential body','--assignee','alice@acme.example','--label','secret-label']`
  as argv. In this product, mission slugs and issue titles are client engagement names — the
  metadata *is* the confidential content.

At merge, `#3108` resolves to `fixed` for Gaps A and B. The hosted-path claim in its text is
`verified-already-fixed` by `#3030` and should be stated as such in the closing comment, so the
issue is not closed in a way that implies a leak existed where none did.
