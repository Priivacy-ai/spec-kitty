"""Boundary self-test for the ``description`` metadata gate.

A gate that cannot go RED is fake, so the Definition of Done is the boundary
proof. The original band proof — **49 and 181 characters RED, 50 and 180
green** — is preserved verbatim below, and the widened gate adds four more
red-proofs: a **missing** description, a **boilerplate** one inherited from the
render-side fallback, a **duplicate** shared with another page, and an **empty
page set**, which must fail rather than report a comfortable "0 violations".

Two structural notes:

* The gate now asks ``docfx.json`` which pages are published, and the resolver
  refuses any set below :data:`MINIMUM_EXPECTED_PAGES`. There is deliberately no
  "skip the floor" parameter, because such a parameter would be the degraded
  code path the contract forbids — so the fixtures here build a synthetic tree
  that clears the floor honestly.
* :func:`test_live_tree_is_clean` runs the gate against the real repository.
  It is the acceptance test for the description backfill, not a smoke test.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.docs import seo_postprocess
from scripts.docs._published_pages import MINIMUM_EXPECTED_PAGES, PublishedPageSet
from scripts.docs.description_length_check import (
    BOILERPLATE_DESCRIPTIONS,
    EXIT_COVERAGE_FAILURE,
    MAX_DESCRIPTION_LENGTH,
    MIN_DESCRIPTION_LENGTH,
    CoverageError,
    check_description_length,
    main,
    validate_descriptions,
)

# Imported private-first on purpose: the gate re-asserts the coverage floor that
# the resolver also enforces, so under normal operation the resolver raises
# first. Reaching the gate's own assertion directly is the only way to prove it
# is load-bearing rather than decorative.
from scripts.docs.description_length_check import _assert_coverage  # noqa: E402
from tests.docs.conftest import commit_all_changes, init_git_repo_with_base

pytestmark = pytest.mark.architectural

REPO_ROOT = Path(__file__).resolve().parents[2]
LIVE_DOCS_ROOT = REPO_ROOT / "docs"

#: Filler pages written into every synthetic tree so it clears the resolver's
#: non-vacuity floor without needing an override the resolver refuses to have.
_FILLER_COUNT = MINIMUM_EXPECTED_PAGES + 20

#: The single fallback string ``seo_postprocess`` substitutes for a page that
#: rendered no description. Probed, never retyped (see
#: :func:`test_boilerplate_set_matches_seo_postprocess`).
BOILERPLATE = seo_postprocess.extract_description("<html><head></head></html>")


def _desc(length: int) -> str:
    """A description string of exactly ``length`` characters."""
    return "x" * length


def _unique_desc(index: int) -> str:
    """A distinct, in-band description for filler page ``index``."""
    text = f"Filler page {index:05d} describing a synthetic documentation page that exists only to clear the coverage floor."
    assert MIN_DESCRIPTION_LENGTH <= len(text) <= MAX_DESCRIPTION_LENGTH
    return text


def _write_page(path: Path, description: str | None) -> None:
    """Write a docs page with an optional ``description`` frontmatter value."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["---", 'title: "Configuring the lane allocator"']
    if description is not None:
        lines.append(f'description: "{description}"')
    lines += ["doc_status: active", "---", "", "# Body", ""]
    path.write_text("\n".join(lines), encoding="utf-8")


def _write_docfx(docs: Path, files: list[str]) -> None:
    """Write a minimal ``docfx.json`` declaring ``files`` as the published set."""
    docs.mkdir(parents=True, exist_ok=True)
    docs.joinpath("docfx.json").write_text(
        json.dumps({"build": {"content": [{"files": files, "exclude": ["**/_*.md"]}]}}),
        encoding="utf-8",
    )


def _build_tree(
    root: Path,
    pages: dict[str, str | None] | None = None,
    *,
    filler: int = _FILLER_COUNT,
    files: list[str] | None = None,
) -> Path:
    """Build a published docs tree under ``root`` and return its ``docs`` dir.

    ``filler`` unique-description pages keep the tree above the non-vacuity
    floor; ``pages`` maps a docs-relative path to the description under test
    (``None`` writes no ``description`` key at all).
    """
    docs = root / "docs"
    _write_docfx(docs, files if files is not None else ["**.md"])
    for index in range(filler):
        _write_page(docs / "filler" / f"page_{index:05d}.md", _unique_desc(index))
    for relative, description in (pages or {}).items():
        _write_page(docs / relative, description)
    return docs


def _reasons(root: Path, docs: Path) -> dict[str, str]:
    """Validate ``docs`` and return ``{path: reason}`` for non-filler pages."""
    report = validate_descriptions(docs_root=docs, repo_root=root)
    return {v.path: v.reason for v in report.violations if not v.path.startswith("docs/filler/")}


# --- check_description_length: the boundary contract (preserved) ------------


def test_band_boundaries_are_inclusive_50_and_180_green() -> None:
    """The 50 and 180 boundaries are valid (inclusive band)."""
    assert MIN_DESCRIPTION_LENGTH == 50
    assert MAX_DESCRIPTION_LENGTH == 180
    assert check_description_length(_desc(50)) is None
    assert check_description_length(_desc(180)) is None
    assert check_description_length(_desc(120)) is None


def test_49_chars_is_too_short_red() -> None:
    """One char below the floor is a RED ``too_short`` violation."""
    assert check_description_length(_desc(49)) == "too_short"


def test_181_chars_is_too_long_red() -> None:
    """One char above the ceiling is a RED ``too_long`` violation."""
    assert check_description_length(_desc(181)) == "too_long"


def test_missing_and_blank_description_is_red() -> None:
    """A missing or whitespace-only description is a RED ``missing`` violation."""
    assert check_description_length(None) == "missing"
    assert check_description_length("") == "missing"
    assert check_description_length("   ") == "missing"


# --- boilerplate: distinct from missing, pinned to the render side ---------


def test_boilerplate_description_is_red() -> None:
    """The render-side fallback is RED, and under its own reason (FR-006).

    ``boilerplate`` is deliberately not folded into ``missing``: "you wrote
    nothing" and "you inherited the default" call for different author actions.
    The fallback also sits *inside* the 50-180 band, so a length-only gate lets
    it through — which is the hole this reason closes.
    """
    assert MIN_DESCRIPTION_LENGTH <= len(BOILERPLATE) <= MAX_DESCRIPTION_LENGTH
    assert check_description_length(BOILERPLATE) == "boilerplate"
    assert check_description_length(BOILERPLATE) != "missing"


def test_boilerplate_set_matches_seo_postprocess() -> None:
    """The boilerplate set is pinned to the render side, not retyped (C-S3).

    ``seo_postprocess.extract_description`` is the single place that decides
    what a page with no description renders as. Probing it means changing that
    fallback cannot silently disarm this check — the drift-between-two-copies
    failure this mission exists to repair.
    """
    assert BOILERPLATE_DESCRIPTIONS, "the boilerplate set must not be empty"
    assert BOILERPLATE in BOILERPLATE_DESCRIPTIONS

    # Forward-compatible: if the render side ever names the fallback as a
    # constant, that constant must be covered too.
    named = getattr(seo_postprocess, "DEFAULT_DESCRIPTION", None)
    if named is not None:
        assert named in BOILERPLATE_DESCRIPTIONS


def test_boilerplate_page_is_flagged_in_a_tree(tmp_path: Path) -> None:
    """A page carrying the fallback is reported ``boilerplate`` by the walk."""
    docs = _build_tree(tmp_path, {"inherited.md": BOILERPLATE})

    assert _reasons(tmp_path, docs) == {"docs/inherited.md": "boilerplate"}


# --- uniqueness ------------------------------------------------------------


def test_duplicate_descriptions_are_red(tmp_path: Path) -> None:
    """Two pages sharing a description flag BOTH pages, not just the second."""
    shared = _desc(120)
    docs = _build_tree(tmp_path, {"a.md": shared, "b.md": shared, "c.md": _desc(121)})

    reasons = _reasons(tmp_path, docs)

    assert reasons == {"docs/a.md": "duplicate", "docs/b.md": "duplicate"}
    assert "docs/c.md" not in reasons, "a unique description must not be flagged"


def test_duplicate_violation_names_the_peer(tmp_path: Path) -> None:
    """Each duplicate violation names its colliding peers (I-07).

    A uniqueness failure reporting only one side is not actionable: the author
    cannot tell what they collided with.
    """
    shared = _desc(120)
    docs = _build_tree(tmp_path, {"a.md": shared, "b.md": shared, "d/c.md": shared})

    report = validate_descriptions(docs_root=docs, repo_root=tmp_path)
    peers = {v.path: set(v.peers) for v in report.violations if v.reason == "duplicate"}

    assert peers == {
        "docs/a.md": {"docs/b.md", "docs/d/c.md"},
        "docs/b.md": {"docs/a.md", "docs/d/c.md"},
        "docs/d/c.md": {"docs/a.md", "docs/b.md"},
    }
    # Deterministic ordering, so the report diffs cleanly.
    assert [v.path for v in report.violations] == sorted(v.path for v in report.violations)


def test_duplicate_comparison_is_exact_match(tmp_path: Path) -> None:
    """Case and whitespace are NOT normalised — the rule stays explainable."""
    base = _desc(60)
    docs = _build_tree(tmp_path, {"a.md": base, "b.md": base.upper()})

    assert _reasons(tmp_path, docs) == {}


def test_duplicate_does_not_bury_a_more_specific_reason(tmp_path: Path) -> None:
    """Pages already flagged ``boilerplate`` are not re-reported as duplicates."""
    docs = _build_tree(tmp_path, {"a.md": BOILERPLATE, "b.md": BOILERPLATE})

    assert _reasons(tmp_path, docs) == {
        "docs/a.md": "boilerplate",
        "docs/b.md": "boilerplate",
    }


# --- coverage: a gate validating zero pages must fail ----------------------


def test_empty_page_set_is_red(tmp_path: Path) -> None:
    """Zero resolved pages is a FAILURE, not a pass (C-S5, FR-003).

    Reporting green over an empty set is precisely how the defect under repair
    stayed invisible for months.
    """
    docs = _build_tree(tmp_path, files=["nowhere/**.md"])

    with pytest.raises(CoverageError) as excinfo:
        validate_descriptions(docs_root=docs, repo_root=tmp_path)

    assert "empty" in str(excinfo.value).lower()


def test_below_floor_is_red_naming_counts_and_globs(tmp_path: Path) -> None:
    """An under-collected set fails, naming observed count, floor, and globs."""
    docs = _build_tree(tmp_path, {"only.md": _desc(80)}, filler=3, files=["*.md"])

    with pytest.raises(CoverageError) as excinfo:
        validate_descriptions(docs_root=docs, repo_root=tmp_path)

    message = str(excinfo.value)
    assert str(MINIMUM_EXPECTED_PAGES) in message, message
    assert "*.md" in message, "the failure must name the globs that produced the set"


def test_gate_asserts_the_floor_independently_of_the_resolver() -> None:
    """The gate's own coverage assertion reds on its own, not via the resolver.

    The resolver enforces the same floor and raises first in every real run, so
    this is the proof that relaxing the resolver's floor could not silently
    disarm the gate's promise that *every published page was checked*.
    """
    empty = PublishedPageSet(pages=frozenset(), source_globs=("**.md",), exclusions=())
    with pytest.raises(CoverageError, match="zero pages"):
        _assert_coverage(empty, docs_root=Path("docs"))

    collapsed = PublishedPageSet(pages=frozenset({Path("docs/a.md")}), source_globs=("**.md",), exclusions=())
    with pytest.raises(CoverageError) as excinfo:
        _assert_coverage(collapsed, docs_root=Path("docs"))

    message = str(excinfo.value)
    assert "1 published page(s)" in message, message
    assert str(MINIMUM_EXPECTED_PAGES) in message, message
    assert "**.md" in message, message


def test_coverage_failure_exits_nonzero_even_without_strict(tmp_path: Path) -> None:
    """A coverage failure is a gate malfunction: it reds regardless of --strict."""
    docs = _build_tree(tmp_path, files=["nowhere/**.md"])

    exit_code = main(["--docs-root", str(docs), "--repo-root", str(tmp_path)])

    assert exit_code == EXIT_COVERAGE_FAILURE
    assert exit_code != 0


def test_missing_docfx_is_a_coverage_failure(tmp_path: Path) -> None:
    """No authority to read is a loud failure, not a degraded walk."""
    docs = tmp_path / "docs"
    docs.mkdir()

    with pytest.raises(CoverageError):
        validate_descriptions(docs_root=docs, repo_root=tmp_path)


# --- the walk: reasons, counts, and ADR scope ------------------------------


def test_validate_flags_out_of_band_pages_and_counts_checks(tmp_path: Path) -> None:
    """The walk flags each out-of-band page and never reports 0/0 silently."""
    docs = _build_tree(
        tmp_path,
        {
            "good.md": _desc(120),
            "short.md": _desc(49),
            "long.md": _desc(181),
            "absent.md": None,
        },
    )

    report = validate_descriptions(docs_root=docs, repo_root=tmp_path)

    assert report.checked_count == _FILLER_COUNT + 4
    assert _reasons(tmp_path, docs) == {
        "docs/absent.md": "missing",
        "docs/long.md": "too_long",
        "docs/short.md": "too_short",
    }
    # The valid page produced no violation, but it WAS checked.
    assert "docs/good.md" not in _reasons(tmp_path, docs)


def test_clean_tree_reports_zero_violations(tmp_path: Path) -> None:
    """A tree whose descriptions are all in-band and unique reports zero violations."""
    docs = _build_tree(tmp_path, {"a.md": _desc(50), "b.md": _desc(180)})

    report = validate_descriptions(docs_root=docs, repo_root=tmp_path)

    assert report.checked_count == _FILLER_COUNT + 2
    assert report.violations == []


def test_adr_pages_are_now_in_scope(tmp_path: Path) -> None:
    """An ADR without a description is flagged — the exclusion is retired (C-S2).

    ``docs/adr/`` used to be skipped wholesale on a byte-invariance rationale
    that expired on 2026-06-29. Removing that exemption is the point of this
    change, so it gets a direct proof rather than an inferred one.
    """
    docs = _build_tree(
        tmp_path,
        {"adr/3.x/2026-01-01-1-some-decision.md": None, "adr/3.x/2026-01-02-1-ok.md": _desc(90)},
    )

    assert _reasons(tmp_path, docs) == {"docs/adr/3.x/2026-01-01-1-some-decision.md": "missing"}


def test_live_tree_covers_the_adr_subtree() -> None:
    """The live run actually reaches ADR pages, so the scope claim is not vacuous."""
    report = validate_descriptions(docs_root=LIVE_DOCS_ROOT, repo_root=REPO_ROOT)
    adr_pages = list(LIVE_DOCS_ROOT.joinpath("adr").rglob("*.md"))

    assert adr_pages, "no ADR pages on disk — the scope assertion would pass vacuously"
    assert report.checked_count > len(adr_pages)


# --- diff scope: PRs report only changed published pages (#3316) ------------
#
# Every fixture here builds a *real* above-floor tree through ``_build_tree``
# (real ``docfx.json``, ``_FILLER_COUNT`` filler pages) and drives ``main``
# through a real git repo, so the shared published-page authority is exercised,
# never stubbed. That matters: the diff-scoped path re-asserts the corpus floor
# exactly as the whole-tree path does, and a stubbed authority would hide that.


def _diff_scoped_argv(docs: Path, root: Path, base: str, *extra: str) -> list[str]:
    """CLI argv for a strict, diff-scoped run of the gate over ``docs``."""
    return [
        "--docs-root",
        str(docs),
        "--repo-root",
        str(root),
        "--strict",
        *extra,
        "--changed-from",
        base,
    ]


class TestDiffScopeDescriptionCLI:
    """``--changed-from`` behavior through :func:`main` over real git repos."""

    def test_changed_length_violation_reds(self, tmp_path: Path) -> None:
        docs = _build_tree(tmp_path, {"existing.md": _desc(100)})
        base_sha = init_git_repo_with_base(tmp_path)
        _write_page(docs / "changed.md", _desc(49))
        commit_all_changes(tmp_path, "add short description")

        exit_code = main(_diff_scoped_argv(docs, tmp_path, base_sha))

        assert exit_code == 1

    def test_changed_unicode_path_length_violation_reds(self, tmp_path: Path) -> None:
        docs = _build_tree(tmp_path, {"existing.md": _desc(100)})
        base_sha = init_git_repo_with_base(tmp_path)
        _write_page(docs / "café.md", _desc(49))
        commit_all_changes(tmp_path, "add Unicode short description")

        exit_code = main(_diff_scoped_argv(docs, tmp_path, base_sha))

        assert exit_code == 1

    def test_unchanged_preexisting_violation_passes(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """A violation confined to an unchanged page is not reported on a PR."""
        docs = _build_tree(tmp_path, {"preexisting.md": _desc(49)})
        base_sha = init_git_repo_with_base(tmp_path)
        _write_page(docs / "changed.md", _desc(100))
        commit_all_changes(tmp_path, "add valid description")

        exit_code = main(_diff_scoped_argv(docs, tmp_path, base_sha, "--json"))

        assert exit_code == 0
        payload = json.loads(capsys.readouterr().out)
        # Only the changed page was *reported on*; the corpus was still read.
        assert payload["checked_count"] == 1
        assert payload["violations"] == []

    def test_only_changed_page_violations_are_reported(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """With violations on both sides of the diff, only the changed one shows."""
        docs = _build_tree(tmp_path, {"preexisting.md": _desc(49)})
        base_sha = init_git_repo_with_base(tmp_path)
        _write_page(docs / "changed.md", _desc(181))
        commit_all_changes(tmp_path, "add long description")

        exit_code = main(_diff_scoped_argv(docs, tmp_path, base_sha, "--json"))

        assert exit_code == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["checked_count"] == 1
        assert [v["path"] for v in payload["violations"]] == ["docs/changed.md"]
        assert payload["violations"][0]["reason"] == "too_long"

    def test_changed_duplicate_compares_with_unchanged_peer(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        """Uniqueness stays corpus-aware: the unchanged peer is named."""
        shared = _desc(120)
        docs = _build_tree(tmp_path, {"existing.md": shared})
        base_sha = init_git_repo_with_base(tmp_path)
        _write_page(docs / "changed.md", shared)
        commit_all_changes(tmp_path, "add duplicate description")

        exit_code = main(_diff_scoped_argv(docs, tmp_path, base_sha, "--json"))

        assert exit_code == 1
        payload = json.loads(capsys.readouterr().out)
        assert payload["checked_count"] == 1
        assert payload["violations"] == [
            {
                "length": 120,
                "path": "docs/changed.md",
                "peers": ["docs/existing.md"],
                "reason": "duplicate",
            }
        ]

    def test_resolved_zero_docs_passes(self, tmp_path: Path) -> None:
        """A resolved diff touching no published docs is a clean pass."""
        docs = _build_tree(tmp_path, {"preexisting.md": _desc(49)})
        base_sha = init_git_repo_with_base(tmp_path)
        (tmp_path / "README.md").write_text("# changed\n", encoding="utf-8")
        commit_all_changes(tmp_path, "change non-docs file")

        exit_code = main(_diff_scoped_argv(docs, tmp_path, base_sha))

        assert exit_code == 0

    def test_unresolvable_base_errors(self, tmp_path: Path) -> None:
        docs = _build_tree(tmp_path, {"existing.md": _desc(100)})
        init_git_repo_with_base(tmp_path)

        exit_code = main(_diff_scoped_argv(docs, tmp_path, "deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"))

        assert exit_code == EXIT_COVERAGE_FAILURE

    def test_collapsed_corpus_is_a_coverage_failure_on_a_pr(self, tmp_path: Path) -> None:
        """Diff scoping filters the report, not the corpus floor (FR-003).

        A PR whose published corpus has collapsed below the floor must red with
        a coverage failure even though the changed subset is tiny — the same
        malfunction signal the whole-tree path raises.
        """
        docs = _build_tree(tmp_path, {"existing.md": _desc(100)}, filler=3)
        base_sha = init_git_repo_with_base(tmp_path)
        _write_page(docs / "existing.md", _desc(101))
        commit_all_changes(tmp_path, "touch a page in a collapsed tree")

        exit_code = main(_diff_scoped_argv(docs, tmp_path, base_sha))

        assert exit_code == EXIT_COVERAGE_FAILURE

    def test_config_only_corpus_collapse_is_a_coverage_failure(self, tmp_path: Path) -> None:
        """Changing only docfx.json cannot bypass the PR corpus floor."""
        docs = _build_tree(tmp_path, {"existing.md": _desc(100)})
        base_sha = init_git_repo_with_base(tmp_path)
        _write_docfx(docs, ["existing.md"])
        commit_all_changes(tmp_path, "collapse published corpus config only")

        exit_code = main(_diff_scoped_argv(docs, tmp_path, base_sha))

        assert exit_code == EXIT_COVERAGE_FAILURE

    def test_diff_scoped_gate_asserts_the_floor_independently_of_the_resolver(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        """The diff-scoped path re-asserts the floor itself, mirroring the whole-tree path.

        Companion to :func:`test_gate_asserts_the_floor_independently_of_the_resolver`:
        the resolver raises first in every real run, so the only way to prove the
        gate's own assertion is load-bearing on this path is to hand it a
        collapsed set the resolver would not have refused. This is the one
        place the authority is bypassed, and only to prove the double-assert.
        """
        from scripts.docs import description_length_check as gate

        docs = _build_tree(tmp_path, {"existing.md": _desc(100)})
        collapsed = PublishedPageSet(
            pages=frozenset({Path("docs/existing.md")}),
            source_globs=("**.md",),
            exclusions=(),
        )
        monkeypatch.setattr(gate, "_resolve_page_set", lambda **_kw: collapsed)

        with pytest.raises(CoverageError) as excinfo:
            gate.validate_descriptions_diff_scoped(docs_root=docs, repo_root=tmp_path, changed_files=["docs/existing.md"])

        assert str(MINIMUM_EXPECTED_PAGES) in str(excinfo.value)


# --- main: the report-only / --strict exit contract (preserved) ------------


def test_report_only_exit_zero_even_with_violations(tmp_path: Path) -> None:
    """Default invocation is report-only: content violations still exit 0 (C-S6)."""
    docs = _build_tree(tmp_path, {"short.md": _desc(49)})

    exit_code = main(["--docs-root", str(docs), "--repo-root", str(tmp_path)])

    assert exit_code == 0


def test_strict_reds_on_violation(tmp_path: Path) -> None:
    """``--strict`` turns an out-of-band description non-zero."""
    docs = _build_tree(tmp_path, {"long.md": _desc(181)})

    exit_code = main(["--docs-root", str(docs), "--repo-root", str(tmp_path), "--strict"])

    assert exit_code == 1


def test_strict_reds_on_duplicate(tmp_path: Path) -> None:
    """``--strict`` reds on a uniqueness failure, not only on a length failure."""
    shared = _desc(120)
    docs = _build_tree(tmp_path, {"a.md": shared, "b.md": shared})

    exit_code = main(["--docs-root", str(docs), "--repo-root", str(tmp_path), "--strict"])

    assert exit_code == 1


def test_strict_stays_green_on_clean_tree(tmp_path: Path) -> None:
    """``--strict`` does not red a tree whose descriptions are all valid."""
    docs = _build_tree(tmp_path, {"a.md": _desc(100)})

    exit_code = main(["--docs-root", str(docs), "--repo-root", str(tmp_path), "--strict"])

    assert exit_code == 0


def test_json_report_carries_peers(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The JSON shape keeps ``path``/``reason``/``length`` and adds ``peers``."""
    shared = _desc(120)
    docs = _build_tree(tmp_path, {"a.md": shared, "b.md": shared})

    main(["--docs-root", str(docs), "--repo-root", str(tmp_path), "--json"])

    payload = json.loads(capsys.readouterr().out)
    assert payload["checked_count"] == _FILLER_COUNT + 2
    duplicates = [v for v in payload["violations"] if v["reason"] == "duplicate"]
    assert {v["path"] for v in duplicates} == {"docs/a.md", "docs/b.md"}
    assert duplicates[0]["peers"] == ["docs/b.md"]
    assert duplicates[0]["length"] == 120


# --- acceptance ------------------------------------------------------------


def test_live_tree_is_clean() -> None:
    """The real published tree yields zero violations.

    This is the acceptance test for the description backfill. A failure here is
    a content defect in ``docs/``, not a gate defect: read the reasons and fix
    the named pages.
    """
    report = validate_descriptions(docs_root=LIVE_DOCS_ROOT, repo_root=REPO_ROOT)

    detail = "\n".join(f"  {v.reason.upper()} {v.path}" + (f" (also on: {', '.join(v.peers)})" if v.peers else "") for v in report.violations)
    assert not report.violations, f"{len(report.violations)} description violation(s) across {report.checked_count} published page(s):\n{detail}"
