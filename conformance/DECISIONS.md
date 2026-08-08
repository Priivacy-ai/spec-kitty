# Decision Record — muster ⇄ Spec Kitty Agent-Conformance Programme

This file is the **single canonical decision record** for the muster ⇄
spec-kitty agent-conformance programme (wave 1 onward). It carries the
programme's D1–D5 design decisions verbatim in substance, as inherited from
the mission seed (`MOES-Media/spec-kitty#22`, section 11), which is itself
drawn from the programme plan. No duplicate copy of this decision text lives
elsewhere in this mission — FR-004.

**Citation pinning**: every citation carries an explicit baseline suffix.
The baseline is chosen by what the citation is evidence *for*, never
globally:

- **Consumed-CLI citations** — any claim about behaviour this suite's
  `npx @garrison-hq/muster@1.1.0` invocation actually executes — pin to
  **`@v1.1.0`** (`6bdb070`). Non-negotiable: a HEAD-computed line number
  here is a defect, because it describes code the suite does not run.
- **Architectural-evidence citations** — claims about muster's design state
  supporting D1–D5 — pin to **the immutable commit SHA at which the claim
  is true** (`@8953ee8`). Never to the word "HEAD": HEAD is a moving
  reference that resolves differently between checkouts.

---

## D1 — Persona adapter vs projector: new static adapter now; projector only for the crosslayer slot, later, SK-side

**Options.** (a) New `spec-kitty-profile` adapter in muster. (b)
Deterministic projector `*.agent.yaml → Soul.md` reusing `rfc1`. (c) Both,
split by purpose.

**Evidence.**
- RFC-1's required front-matter keyspace is `soul_spec, id, name, locale,
  composition, profiles, profile_overrides, values, voice, interaction,
  safety, extensions`, where `voice` requires four 0–100 integers and
  `interaction` requires four enums
  (`src/adapters/rfc1/schema.json:11-24 @v1.1.0≡8953ee8`
  and sub-blocks). **None of these exist in an agent profile.** A projector
  must fabricate them. Static checks against fabricated values are vacuous,
  and grading them would launder muster-invented numbers as SK conformance
  — against the spirit of constraint 5.
- The three candidate artefacts are all lossy except the source YAML: the
  `.claude/agents/<id>.md` projection keeps only name/description/roles +
  purpose + primary-focus + avoidance-boundary
  (`src/specify_cli/tool_surface/profiles/_render_helpers.py:35-65`);
  `spec-kitty profiles show --json` omits capabilities, routing-priority,
  context-sources, output-artifacts, operating-procedures
  (`profiles_cmd.py:261-295`). Cross-profile lints (handoff graph, reference
  resolution) need fields only the **source YAML** carries.
- The adapter pattern question resolves from the code: the registry that
  motivates `implements SpecAdapter` stubs serves only `muster check
  --adapter` over Soul documents (`src/cli/index.ts:224-227,1282 @v1.1.0` —
  the `ADAPTER_REGISTRY` const and the `check` command's
  registration); the newest adapter (`memory-utilization`) skips
  `SpecAdapter` entirely and is manifest-runner + factory + hand-wired CLI
  command (`src/adapters/memory-utilization/index.ts:562-601 @8953ee8`,
  `src/cli/index.ts:1717-1755 @8953ee8` — **both citations as given in the
  seed issue, unverifiable against `v1.1.0`**: the `memory-utilization` adapter
  was introduced entirely in commit `8953ee8`, the single commit *after*
  the `v1.1.0` tag; the file does not exist and `src/cli/index.ts` is only
  1643 lines long at `v1.1.0`. See the re-derivation note at the end of
  this file). A profile adapter has no reason to enter the Soul registry.
- The projector **is** unavoidable for cross-layer composition:
  `composition.ts` supports exactly `persona | sop | skill` and the persona
  slot must resolve through RFC-1 §7.5/Appendix G
  (`src/crosslayer/composition.ts:25,74,82-91,295-303 @v1.1.0≡8953ee8`), and
  persona+sop are both mandatory (`:103-131 @v1.1.0≡8953ee8`).

**Recommendation (c), narrowly.** M2 (garrison-hq/muster#58) builds a
manifest-runner-shaped `spec-kitty-profile` adapter that grades the
**source YAML** (schema conformance cites the upstream schema pinned to a
SHA; cross-profile lints cite a muster-published rubric). The projector is
deferred to M7 (MOES-Media/spec-kitty#26), lives in the SK fork's
conformance tooling (not muster — the scope guard's "not a prompt optimizer
**or generator**; it reports violations; it does not rewrite files",
`BRIEF.md:99-100`), its fabricated defaults are published in a mapping
document, and its output is used **only** to satisfy the composition slot —
fabricated fields are never themselves graded. Drift-as-second-source-of-truth
is neutralized by regenerating in CI and byte-comparing (same pattern SK
itself uses for projection integrity via `agent_profiles_manifest.json`).

**What would change my mind.** If `composition.ts` gains a raw-persona mode
or a fourth slot type (a C-005 change), the projector dies entirely. If SK
profiles grow voice/interaction-like fields, the projector stops fabricating
and could become a first-class path.

---

## D2 — The behavioral endpoint: no shim, no new runtime; the SOP behavioral engine over a raw BYOM endpoint is the seam

**Options.** (a) Context-assembly shim service (profile + doctrine → system
prompt, proxying `/chat/completions`). (b) A2A façade over a headless
Claude Code runner. (c) SK orchestrator-API bridge. (d) No new runtime:
muster manifests embed the SK-derived context as scenario system prompts
and drive any OpenAI-compatible endpoint directly.

**Evidence.**
- (c) is dead: the orchestrator API cannot execute an agent or return a
  transcript (correction #10 of the programme plan).
- SK ships no server surface of any kind (no fastapi/flask/uvicorn; no
  `/chat/completions`; no A2A — verified repo-wide).
- A Claude Code subagent **is** system prompt + model + harness; the
  deployed system prompt is the projected `.claude/agents/<id>.md` body.
  muster's SOP compliance probes already carry `scenario.systemPrompt` +
  turns and run through the core client against any OpenAI-compatible
  endpoint — and this path is **already wired in the CLI**: `doSopRun`
  builds a real client from `MUSTER_ENDPOINT`/`MUSTER_MODEL`/`MUSTER_API_KEY`
  and executes probes (`src/cli/index.ts:1054-1067,1104-1125 @v1.1.0` —
  `buildSopClient()` and `doSopRun()`). Verified directly, not assumed.
- (a) would be a running service whose only job is assembling text muster
  can embed in a manifest — a moving part with no added test power, and
  wherever it lived it would strain either muster's scope guard or SK's
  dependency surface. The strawman's framing of the shim as "highest-risk"
  is right; the resolution is that **it isn't needed** for doctrine-level
  behavioral conformance.

**Recommendation (d).** Behavioral conformance = SOP rule manifests whose
scenarios embed the deployed context (projected profile body verbatim;
AGENTS.md or directive text where the rule under test requires it), driven
by `muster sop run` against whatever endpoint the operator brings (Ollama on
the DGX Spark, NIM, hosted). muster never hosts, schedules or operates the
agent — the scope guard holds (`BRIEF.md:98`).

**Honest limit + escape hatch.** This tests model+context, not the Claude
Code harness (no real tool loop, no skill routing machinery). Trigger-routing
(M6, MOES-Media/spec-kitty#25) partially closes this with tools-shaped probes
(`makeClientWithTools`). If model-only results are shown to diverge from
observed in-harness behavior, the escape hatch is (b): an A2A façade over
`claude -p` in a **separate repo**, consumed by muster's existing A2A adapter
unchanged — zero muster changes. Kept out of this programme's critical path
(OQ-8).

**What would change my mind.** Evidence of divergence (M4,
MOES-Media/spec-kitty#24, findings that don't reproduce in the real harness,
or vice versa) promotes the A2A façade from option to mission.

---

## D3 — Rule extraction: hand-authored manifests; `sopFile` = the directive YAML itself; `integrity_rules` are the ruleText; `validation_criteria` feed judge rubrics

**Options.** (a) Hand-author SOP rule manifests per directive. (b) Generate
manifests from doctrine (generator in muster or SK). Sub-decision:
`integrity_rules` vs `validation_criteria` as `ruleText`.

**Evidence.**
- `checkRuleTextPresence` requires `ruleText` to be a **verbatim substring
  of the SOP file**
  (`src/adapters/openclaw-sop/manifest.ts:426-446 @v1.1.0≡8953ee8`).
  Pointing `sopFile` at the directive YAML makes verbatim `integrity_rules`
  lines satisfy this for free, and turns the drift lint into exactly what
  we want: **when upstream edits a directive, the manifest goes stale and
  the lint says so.**
- `integrity_rules` are phrased as enforceable invariants ("Production code
  must not be written ahead of a failing test…", `034:19-22`);
  `validation_criteria` are phrased as reviewer checks ("Agent guidance
  explicitly states…", `029:21-23`). The former map to `ruleText`; the
  latter are judge-rubric material.
- Decidability: of the 26 directives, roughly 9 are trace-decidable in whole
  or part (018 versioning, 028 tooling, 029 signing, 030 gates, 033 targeted
  staging, 034 test-first ordering, 035 occurrence-map artifact, 042 docs
  lifecycle headers, 045 no-direct-push) and the rest are judge-graded —
  mapped rule-by-rule in M3 (MOES-Media/spec-kitty#23) against the 5 binary
  + 2 judge classes of `docs/rubric/sop-rule-taxonomy.md` (which **already
  exists and is normative**, so M3 needs zero new muster rubric surface).
- Citation shape has direct precedent: `source.normative` = the muster
  rubric class; `source.supporting` = "OpenClaw doc URL pinned to a commit
  SHA (C-002)" (`manifest.ts:35-68 @v1.1.0≡8953ee8`) — substitute the directive file's
  GitHub URL @ SHA.
- Volume: 25 directives × 2–4 integrity_rules ≈ 60–90 entries. Authored
  once, drift-guarded thereafter. A generator is a second source of truth
  with its own drift and residence problem; nothing in the evidence
  justifies it at this volume.

**Recommendation (a).** One manifest per directive (or small thematic
groups), `sopFile:` the directive YAML, `ruleText` verbatim from
`integrity_rules`, `gradingClass`/`aggregation` per the existing taxonomy
(pass-k for safety-critical, k-of-n for stylistic —
`sop-rule-taxonomy.md` §Aggregation), `passThreshold == k` enforced for
pass-k by the loader itself (`manifest.ts:283-321 @v1.1.0≡8953ee8`). Judge rules quote
`validation_criteria` inside `rubricText`. Start with the trace-decidable
set plus the highest-value judge rules; grow by evidence.

**What would change my mind.** If directive churn produces >~1
stale-manifest PR per month, build the generator — in the SK fork's
conformance tooling, emitting manifests that are then committed (so muster
still consumes plain files and the drift lint still guards).

---

## D4 — Where each mission runs

- **muster**: M2 (garrison-hq/muster#58) (profile adapter + rubrics), M5
  (garrison-hq/muster#59) (skills behavioral enablement — it's a muster
  CLI/adapter fix), M9 (garrison-hq/muster#60) (docs). These change muster
  source; nowhere else is possible.
- **spec-kitty fork** (MOES-Media, PR upstream when ripe): M1, M3
  (MOES-Media/spec-kitty#23), M4 (MOES-Media/spec-kitty#24), M6
  (MOES-Media/spec-kitty#25), M7 (MOES-Media/spec-kitty#26) — everything
  that is manifests, fixtures, query sets, the projector, and SK-side CI.
  Reason: muster resolves `skillDir`/`sopFile`/`querySetPath` **relative to
  the manifest's own directory** (`src/cli/index.ts:993 @v1.1.0` —
  manifest-relative path resolution; `manifest.ts`'s `sopFile` "path
  relative to the manifest file") — conformance data must live beside the
  artefacts it cites, and the artefacts live in spec-kitty. This also keeps
  muster spec-agnostic and gives SK core **zero** muster dependency (a
  `conformance/` directory is passive data + one small tool; muster arrives
  only via `npx` in CI).
- **muster-action**: M8 (garrison-hq/muster-action#2). It's the only repo
  that can close its own input gap.
- **No new repository.** The strawman's implied "bridge" home is the SK
  fork's `conformance/` tree. A dedicated repo adds a third moving surface
  for ~200 lines of tooling; if upstream ultimately refuses the
  `conformance/` directory, promoting it to its own repo is a `git mv`, not
  a redesign (OQ-2).

**OQ-2 — Upstream the `conformance/` directory to Priivacy-ai?** Options:
(a) fork-resident indefinitely; (b) PR upstream after M4
(MOES-Media/spec-kitty#24) demonstrates a real finding (evidence beats
proposal); (c) separate garrison-hq repo if upstream declines *and* fork
maintenance hurts. Recommendation: (b), with (a) as the working state. M1
therefore lands fork-side and makes no upstream PR.

---

## D5 — The rubric surface

Constraint 5 (`BRIEF.md:92-94`) plus the house pattern (both existing
rubrics shipped **inside the mission that introduced their checks**) gives:

| Document | Ships in | Normatively defines | Checks citing it |
|---|---|---|---|
| `docs/rubric/spec-kitty-profile-taxonomy.md` | M2 (garrison-hq/muster#58) | Profile check classes: schema-conformance (delegating normativity to `agent-profile.schema.yaml@<SHA>` as the upstream clause), handoff-graph resolution & symmetry semantics (incl. the role-vs-profile-id typing of `handoff-to`), doctrine-reference resolution vs the activation set, `context-sources` integrity, profile-id-as-native-filename legality, projection-drift semantics vs `agent_profiles_manifest.json` (schema_version 1, 9 fields). Follows the `[NORMATIVE]/[CONVENTION]/[MUSTER-OWN]` source-tagging of `memory-utilization-taxonomy.md`. | all M2 checks |
| `docs/rubric/spec-kitty-behavioral-axes.md` | M2 (needed before M4, MOES-Media/spec-kitty#24) | What "behaved correctly" means per profile axis: avoidance-boundary adherence, capability containment, handoff discipline, canonical-verb usage — each with grading class, aggregation, the verbatim `rubricText` blocks M4's `JudgeAssertion`s embed (the judge injects rubricText verbatim between `<RUBRIC>` tags — `judge.ts:62-67` — so the published text **is** the operative rubric), and its required discrimination control. | all M4 profile-axis rules |
| `docs/rubric/sop-rule-taxonomy.md` **v1.1 appendix** | M2 | Directive-mapping appendix: which directive fields become `ruleText`, decidability mapping of the 26 directives onto the existing 5 binary + 2 judge classes, citation format for `source.supporting` = directive@SHA. The classes themselves are already normative at v1.0.0 — M3 (MOES-Media/spec-kitty#23) checks cite the **existing** classes; the appendix is author guidance, so M3 is not blocked on it. | M3/M4 directive rules (classes), authors (appendix) |
| `docs/rubric/skills-trigger-taxonomy.md` | M5 (garrison-hq/muster#59) | The trigger-testing methodology muster currently attributes to an unverified upstream anchor (correction #5): 8-minimum per axis, should-trigger vs near-miss semantics, threshold semantics, k-of-n rationale (`trigger.ts:26-31`), discrimination-control requirement (M6's trigger-routing sense — distinct from this mission's static rigged-fixture control case, see `conformance/README.md`). Citations in `trigger.ts`/`types.ts`/fixtures repointed here (or to the upstream anchor if OQ-1 verifies it exists — then this doc just anchors to it). | all trigger checks (M6, MOES-Media/spec-kitty#25) |

Not in scope, recorded in M9 (garrison-hq/muster#60): rubrics for
tools/memory/heartbeat/crosslayer (pre-existing gap).

---

## Relevant corrections from verification (context for FR-006 and the scope guard)

- Correction #4: `doSkillsRun` unconditionally records every `type:
  behavioral` case as `{passed: true, skipped: true}` and never constructs a
  client (`src/cli/index.ts:1010 @v1.1.0`); `runTriggerConformance` is
  reachable only from tests. Behavioral skill cases cannot run through the
  CLI until M5 (garrison-hq/muster#59) — hence static-only here.
- Latent defects (recorded in `conformance/README.md`, not fixed here): the
  skills manifest is parsed with a bare TypeScript cast — no Ajv schema, no
  runtime validation (`src/cli/index.ts:996 @v1.1.0`) — and
  `expectations.violations` is never compared, only `expectations.ok`
  (`src/cli/index.ts:956 @v1.1.0`, `passed = ok === c.expectations.ok`).

---

## Note on citation re-derivation scope (T007)

This mission's binding constraint 4 (`kitty-specs/sk-skills-static-conformance-01KYG7GE/tasks/WP02-decisions-and-readme.md`)
requires every `src/cli/index.ts` citation above to resolve against muster's
`v1.1.0` tag exactly. All `src/cli/index.ts` citations in this file were
individually re-derived and confirmed against
`git show v1.1.0:src/cli/index.ts` in `/home/jeroennouws/dev/garrison-hq/muster`
before this file was committed:

| Citation (this file) | Confirmed content at `v1.1.0` |
|---|---|
| `:993` | `const baseDir = dirname(absManifestPath);` — manifest-relative path resolution |
| `:956` | `const passed = ok === c.expectations.ok;` — the pass/fail rule |
| `:996` | `const parsed = parseYaml(raw) as { cases: SkillsManifestCase[] };` — bare cast, no schema validation |
| `:1010` | `results.push({ id: c.id, type: "behavioral", passed: true, skipped: true });` — behavioral cases unconditionally skipped |
| `:224-227,1282` | `ADAPTER_REGISTRY` const definition and the `.command("check")` registration — corrected from the seed issue's HEAD-computed `:245-248,1610` |
| `:1054-1067,1104-1125` | `buildSopClient()` and `doSopRun()` — corrected from the seed issue's HEAD-computed `:1367-1444` |

Citations into `src/adapters/skills/schema.ts:18-33`,
`src/adapters/skills/validate.ts:18-24`, `src/crosslayer/composition.ts`,
`src/adapters/rfc1/schema.json`, and `src/adapters/openclaw-sop/manifest.ts`
are confirmed byte-identical across `v1.1.0..8953ee8`: all five files were
byte-compared via `git hash-object` at both revisions and produced matching
hashes at each. These citations are therefore valid at both baselines and
carry over unchanged; a later mission does not need to repeat this
verification.

**Discovered during this pass (beyond what research.md §2 or the WP
instructions anticipated):** the D1 citation pair
`src/adapters/memory-utilization/index.ts:562-601 @8953ee8` /
`src/cli/index.ts:1717-1755 @8953ee8` does not merely suffer line-number
drift — the `memory-utilization` adapter does not exist at all at the
`v1.1.0` tag. `git log --oneline v1.1.0..8953ee8 --
src/adapters/memory-utilization/` shows it was introduced in exactly one
commit, `8953ee8` ("feat: memory-utilization / learning-lift conformance
adapter (+ spec-kitty 3.2.5 upgrade) (#52)"), which is the same single
commit that separates `v1.1.0` from `8953ee8` (`v1.1.0-1-g8953ee8`). `git
show v1.1.0:src/adapters/memory-utilization/index.ts` fails ("exists on
disk, but not in 'v1.1.0'"), and `git show v1.1.0:src/cli/index.ts | wc -l`
reports 1643 lines, so line 1717 cannot exist there either. Per the
citation-pinning rule above, this pair is correctly classed as
architectural-evidence, not consumed-CLI, and is pinned accordingly to the
immutable SHA at which it is true — there is no `v1.1.0`-valid line number
for a feature that is not present at that tag, nor should there be one.

Both halves of the pair are **confirmed at immutable commit `8953ee8`**,
not merely carried over from the seed issue unverified:
`src/adapters/memory-utilization/index.ts:562-601 @8953ee8` spans
`AdapterResult` through `createMemoryUtilizationAdapter()`, and includes
the doc comment at `:579-582` reading: "Does not implement the full
SpecAdapter interface from src/core/adapter.ts — that contract is
Soul.md/RFC-1-specific..." — which is precisely D1's evidentiary point,
stated by muster's own source, and corroborates the recommendation above.
`src/cli/index.ts:1717-1755 @8953ee8` is the hand-wired
`memory-utilization` command registration, closing on `});` at line 1755.

This is a scope observation, not a fix: this mission's scope guard (C-001)
forbids any muster change, and D1's substantive point (the
memory-utilization adapter's `SpecAdapter`-registry bypass) is a statement
about muster's design state at commit `8953ee8`, not about behavior this
mission's CI pins (that behavior remains pinned to `v1.1.0` per the
citation-pinning rule above).
