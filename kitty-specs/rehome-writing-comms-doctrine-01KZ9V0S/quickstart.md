# Quickstart: Validate the Re-homed Writing-Comms Doctrine

Prerequisites: Shadow Clone isolated env active
(`source scripts/dev/activate-isolated-env.sh`), on `feat/rehome-writing-comms-doctrine`.

## 1. Source content

The contributed artifacts are on the fetched ref `pr-2918` at OLD paths
`src/doctrine/<type>/built-in/…`. View any file with e.g.
`git show pr-2918:src/doctrine/agent_profiles/built-in/comms-cleo.agent.yaml`.

## 2. Per-WP validation (targeted — charter Testing Requirements)

```bash
# Relocation + assets present, old tree empty
git ls-files 'src/doctrine/*/built-in/*'                 # expect: empty
ls packs/built-in/assets/audiences/                       # expect: 5 personas + sidecars + README

# Schema validation of the new artifacts
spec-kitty doctrine pack validate packs/built-in          # expect: OK (incl. type:asset tactic ref)

# Regenerate DRG from frontmatter, confirm freshness
spec-kitty doctrine regenerate-graph                      # writes fragments
spec-kitty doctrine regenerate-graph --check              # expect: exit 0 (fresh)

# Doctrine health (25/25 profiles, no skipped, no DRG errors)
spec-kitty doctor doctrine --json | python3 -c "import json,sys;d=json.load(sys.stdin);print(d['profile_health']['healthy'], [p for p in d['profile_health']['packs']])"

# The pinned + behavioral gates
pytest tests/doctrine/test_shipped_profiles.py \
       tests/doctrine/test_pack_relocation_doctor_gate.py \
       tests/doctrine/drg/test_reachability.py \
       tests/specify_cli/invocation/test_router.py -q

# Terminology canon (fast; catches CI-only forbidden-term regressions)
pytest tests/architectural/test_no_legacy_terminology.py -q
```

## 3. Red-first proof (routing)

Before the role-narrowing edit, the two negative router regressions (R-1, R-2 in
`contracts/routing-behavior.md`) must FAIL (return diagram-daisy / comms-cleo). After the edit
they PASS. Capture both states as the ATDD evidence.

## 4. Manual smoke — honesty checks (WS2, not automatable)

Re-read each reconciled artifact and confirm the blocker is gone (research D-06):
- `diagram-daisy`: no Directive-031 attribution, no hexagon/three-tier ban, tool matrix → toolguide refs.
- `minutes-maker-mahad` + `meeting-minutes-pipeline`: no unshipped-enforcement claims; trust boundaries stated.
- `050`: connector-side/pre-redaction primary, strip-after as fallback.
- `049`: advisory language matches the `advisory` field.
- `047`: `references` point at `writing-audience-catalog`, not the stakeholder artifacts.
- `lexical-larry`: diagnostic-feeder boundary vs curator-carla's glossary ownership.

## 5. Full suite

Reserved for CI (release authority) — do not run the full `tests/` suite in-session (~1h).
