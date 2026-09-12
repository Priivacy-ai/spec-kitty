# Quickstart: Docs SEO Metadata Audit and Enforcement

**Mission**: `docs-seo-metadata-enforcement-01KZ9PJ2`
**Branch**: `feat/docs-seo-metadata-enforcement`

---

## 0. Establish the baseline BEFORE editing anything

**Do this first. It is not optional.**

Planning ran without a working Python environment (no `uv`, no `pytest` on any available interpreter), so the current green baseline of the docs gates was **never empirically confirmed**. If you start editing and then see red, you will not know whether it is yours.

```bash
cd /Users/spec-kittycmo/spec-kitty-projects/spec-kitty
uv sync

# The four docs-freshness gates, unchanged, on an unchanged tree:
PYTHONPATH=. uv run python scripts/docs/related_validator.py --strict --repo-root .
PYTHONPATH=. uv run python scripts/docs/description_length_check.py --strict --repo-root .
PYTHONPATH=. uv run python scripts/docs/relative_link_fixer.py --check --repo-root .
uv run python packs/built-in/assets/docs_structural_lint.py \
  --styleguide packs/built-in/styleguides/common-docs.styleguide.yaml

PWHEADLESS=1 uv run pytest tests/docs/ -q
```

Record what is red **before** you change anything. Per the repository's baseline-red policy, only failures red on your branch *and* green on the merge base are yours.

---

## 1. Confirm the measured numbers still hold

Planning measured these. If yours differ materially, assumptions have drifted — stop and re-check before building on them.

```bash
python3 - <<'PY'
import re, pathlib
globs = ["index.md","context","architecture","adr","plans","api","configuration",
         "integrations","security","guides","development","operations","migrations",
         "changelog","release-goals","doctrine","core-concepts","reference","updates"]
root = pathlib.Path("docs"); built = []
for g in globs:
    p = root / g
    if p.is_file(): built.append(p)
    elif p.is_dir(): built += [f for f in p.rglob("*.md") if not f.name.startswith("_")]
def fm(f):
    t = f.read_text(encoding="utf-8", errors="replace")
    if not t.startswith("---"): return None
    e = t.find("\n---", 3)
    return t[3:e] if e > 0 else None
no_fm = no_desc = 0
for f in built:
    b = fm(f)
    if b is None: no_fm += 1
    elif not re.search(r"^description:", b, re.M): no_desc += 1
print(f"built={len(built)} (expect 674)")
print(f"no frontmatter={no_fm} (expect 3)")
print(f"no description={no_desc} (expect 144)")
PY
```

Verify the gate's true coverage — this is the defect, reproduced:

```bash
python3 - <<'PY'
from pathlib import Path
D = Path("docs")
pats = ["index.md","tutorials/*.md","how-to/*.md","how-to/harnesses/*.md",
        "reference/*.md","explanation/*.md","recovery/*.md","3x/**/*.md",
        "archive/**/*.md","migration/**/*.md"]
files = set()
for p in pats:
    files.update(x for x in D.glob(p) if x.is_file() and not x.name.startswith("_"))
print(f"test_docs_seo.py currently guards {len(files)} pages (expect 16)")
PY
```

---

## 2. Suggested landing order

The one hard constraint: **descriptions before the exclusion flip.** Everything else is flexible.

| Step | Concern | Why here |
|---|---|---|
| 1 | IC-01 resolver | Foundation; IC-02 and IC-03 both consume it |
| 2 | IC-04 ADR descriptions | Long pole, no code coupling — start early, run in parallel |
| 3 | IC-03 render + verifier | Independent of IC-02; can proceed alongside IC-04 |
| 4 | IC-02 gate hardening | **Exclusion removal requires IC-04 complete** |
| 5 | IC-05 navigation, IC-06 CI scoping | Independent; land any time |

---

## 3. Traps found during planning

**The ADR README frontmatter trap.** The 3 files `docs/adr/{1.x,2.x,3.x}/README.md` have no frontmatter at all. Add **only** `title` and `description`. Adding `tag`, `divio_type`, or `owning_workstream` will drift the page-inventory lockfile and trip `INVENTORY-LOCKFILE-DRIFT` — a recurring CI failure in this repo. The other 144 ADRs already have frontmatter, so adding `description:` to them is inert for the lockfile.

**The census gate is compatible — verified, not assumed.** `test_adr_content_invariance.py::test_every_adr_has_bare_madr_status_frontmatter` asserts only that `status` is a canonical MADR value. It does not enumerate permitted keys. Adding `description:` will not trip it.

**The stale comment must be corrected, not deleted.** `description_length_check.py`'s `_EXCLUDE_PREFIXES` comment cites byte-invariance "enforced by `test_adr_content_invariance`". That enforcement was retired 2026-06-29 (`ccd278061`) per that module's own docstring. Replace the comment explaining the rationale expired (DIRECTIVE_037) — a bare deletion loses the history.

**`docs/` is in the terminology guard's scan roots.** Unlike `kitty-specs/`, authored ADR descriptions are subject to `tests/architectural/test_no_legacy_terminology.py`. Use "Mission" not "feature"; mind the `primary` / `merge` / `routing` overloaded-term guidance. Run it before pushing:
```bash
PWHEADLESS=1 uv run pytest tests/architectural/test_no_legacy_terminology.py -q
```

**DocFX glob semantics ≠ `pathlib` glob semantics.** `context/**.md` in DocFX matches `context/foo.md`; the naive translation `context/**/*.md` does not. Getting this wrong silently under-collects — the exact bug under repair. Validate the resolver by asserting membership of known pages and a realistic count, never by reasoning about glob translation.

**The `paths:` filter must cover the gates' true inputs.** Not just `docs/**`. Also `scripts/docs/**`, `packs/built-in/assets/docs_structural_lint.py`, `packs/built-in/styleguides/common-docs.styleguide.yaml`, and the workflow file. A filter narrower than the real input set silently stops guarding — same failure shape, new location.

---

## 4. Verifying the built output locally

Requires .NET; CI does this for you.

```bash
dotnet tool install -g docfx
python3 scripts/docs/generate_kitty_specs_docs.py
cd docs && docfx docfx.json && cd ..
python3 scripts/docs/seo_postprocess.py
python3 scripts/docs/glossary_linker.py --site-dir docs/_site
python3 scripts/docs/redirect_stub_generator.py generate --site-dir docs/_site
python3 scripts/docs/seo_verify.py --site-dir docs/_site --strict   # new
```

Spot-check a page the way an operator would (FR-010):

```bash
grep -oE '<title>[^<]*</title>|<meta name="description" content="[^"]*"|rel="canonical" href="[^"]*"' \
  docs/_site/adr/3.x/2026-07-08-1-mission-resolver-port.html
```

Against the live site:

```bash
curl -s https://docs.spec-kitty.ai/api/slash-commands.html \
  | grep -oE '<title>[^<]*</title>|<meta name="description" content="[^"]*"'
```

---

## 5. Definition of done

- [ ] Resolver reads `docs/docfx.json`; the retired pre-move glob list fails its floor assertion (the regression proof)
- [ ] `test_docs_seo.py` guards ~674 pages, not 16
- [ ] All 147 ADR pages carry unique, hand-authored descriptions in the 50–180 band
- [ ] `_EXCLUDE_PREFIXES` no longer excludes `docs/adr/`; its comment explains why the old rationale expired
- [ ] Boilerplate and duplicate detection go red on purpose-built fixtures
- [ ] `seo_postprocess.py` emits a description tag; idempotent across two runs
- [ ] `seo_verify.py --strict` runs last in `docs-pages.yml` and blocks before artifact upload
- [ ] Install guide and slash-command reference are one click from `docs/index.md`; `toc.yml` unchanged
- [ ] `docs-freshness.yml` has a `paths:` filter covering all gate inputs
- [ ] Audit record generated, including the stale-URL finding for issue #1652
- [ ] `ruff` and `mypy` clean with no new suppressions
- [ ] Existing redirect-coverage and glossary-linker gates still green
