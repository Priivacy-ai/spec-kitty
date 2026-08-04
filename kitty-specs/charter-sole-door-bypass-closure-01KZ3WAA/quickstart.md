# Quickstart: Verifying the Sole-Door Property

For a reviewer or a later maintainer who wants to confirm this mission's claims hold, without reading every
diff.

## 1. Zero raw construction outside the factory

**Corrected post-plan squad**: a plain `grep` on the literal text `DoctrineService(` cannot distinguish the
forbidden raw class from the sanctioned wrapper (`charter.resolver.DoctrineService(inner, pack_context=None)`
shares the substring), and a whole-file `grep -v` on the two `.kittify/profiles` files would hide a
genuinely new bypass added elsewhere in the same file. The commands below are a coarse manual sanity check
only — the real gate (FR-007/NFR-001) resolves each site's bound import via AST, not text. Expect these
commands to need per-run judgement, not a clean zero:

```bash
# AgentProfileRepository: real zero-tolerance surface is 2 sites (the .kittify/profiles exclusions,
# confirmed by reading the match, not by filename)
grep -rn "AgentProfileRepository(" src/ --include='*.py' | grep -v "src/charter/resolver.py" \
  | grep -v "src/charter/doctrine_service_builder.py" | grep -v "src/specify_cli/doctrine_service_factory.py"
# Manually confirm every remaining match is registry.py:48 or profiles_cmd.py:83, constructing against
# .kittify/profiles — any other match is a real regression.

# doctrine.service.DoctrineService: exclude src/doctrine/ (the raw service's own repo construction,
# not a bypass) and the doc/skill markdown that also matches the literal string
grep -rn "DoctrineService(" src/ --include='*.py' | grep -v "^src/doctrine/" \
  | grep -v "src/charter/resolver.py" | grep -v "src/charter/doctrine_service_builder.py" \
  | grep -v "src/specify_cli/doctrine_service_factory.py"
# Manually confirm every remaining match is charter.resolver.DoctrineService(..., pack_context=None) — the
# sanctioned unfiltered-diagnostic mode (FR-002) — not a raw doctrine.service.DoctrineService(...) call.
```

## 2. No direct `doctrine.resolver` imports outside `src/charter/**`

```bash
grep -rln "^\s*\(from\|import\) doctrine\.resolver" src/ --include='*.py' | grep -v "^src/charter/" | grep -v "^src/doctrine/"
```
Expected: no output. (The looser pattern used pre-review also matches
`src/specify_cli/runtime/resolver.py`'s explanatory *comment* about `doctrine.resolver` — R6 explicitly rules
that file's tier-1-4 reimplementation out of this mission's scope; an import-anchored pattern avoids that
false positive.)

## 3. All 9 gated kinds resolve, bare project stays default

```bash
# Run the FR-005 bare-project regression suite
pytest tests/charter/test_resolver_activation_gating.py -v  # exact path assigned at tasks time
```
Expected: every kind (`paradigms`, `procedures`, `agent_profiles`, `directives`, `tactics`, `styleguides`,
`toolguides`, `mission_step_contracts`, `glossary_packs`) returns the full built-in catalog for a project
with no activated packs.

## 4. `mission-type` gates separately, same bare-project guarantee

```bash
pytest tests/charter/test_mission_type_activation_gating.py -v  # exact path assigned at tasks time
```
Expected: a bare project still resolves `research`/`software-dev`/`documentation`/`plan`.

## 5. The unified builder produces one catalog, not two

```bash
pytest tests/charter/test_doctrine_service_builder_unification.py -v  # exact path assigned at tasks time
```
Expected: both former builder call shapes, given the same `repo_root`, now produce identical output.

## 6. The gates are non-vacuous

```bash
# Each new architectural gate should have a paired self-mutation test in the same file —
# run just those and confirm they fail when the guarded shape is reintroduced.
pytest tests/architectural/ -k "charter_sole_door" -v
```

## 7. Performance did not regress on the sites that were guarded

```bash
# Compare against the pre-mission baseline captured in the mission's tracer file / PR description.
spec-kitty agent tasks status --mission <fixture-project-with-100-plus-wps>
```
Expected: p95 render latency within 10% of the recorded baseline (NFR-005); if not, the PR description
must name the architectural fix applied (caching/lazy-init), not accept the regression.

## 8. The five deferred issues are untouched

```bash
git diff main...feat/charter-sole-door-bypass-closure --stat | grep -iE "resolution.py|shippable|dead_doctrine|missions|packs-open"
```
Read the matched files' diffs (if any) and confirm none of them are scoped to #2986/#3036/#3039/#3091/#3022
— the PR description should name all five as confirmed-deferred, each still open at merge time.
