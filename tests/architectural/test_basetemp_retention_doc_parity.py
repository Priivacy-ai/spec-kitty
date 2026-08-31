"""Architectural parity test for the basetemp retention rationale."""

from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple

import pytest

# This guard reads a repo documentation page, so a docs-only PR must select it.
pytestmark = [pytest.mark.architectural, pytest.mark.docs_scoped]

_REPO_ROOT = Path(__file__).resolve().parents[2]
_DOC_PATH = _REPO_ROOT / "docs/development/testing/testing-parallel.md"
_SUPPORT_PATH = _REPO_ROOT / "tests/_support/run_basetemp.py"

_DOC_RETENTION_BULLET = re.compile(
    r"^- Retention is outcome-gated \(#76\): (?P<body>.*?)^## ",
    re.MULTILINE | re.DOTALL,
)
_SUPPORT_RETENTION_BULLET = re.compile(
    r"^\* \*\*Reaped on success, retained on failure\*\* — (?P<body>.*?)^\* \*\*",
    re.MULTILINE | re.DOTALL,
)

_RETENTION_CONTRACT_CLAUSES = (
    "ExitCode.OK",
    "removes the run's dir",
    "failures, errors, or an interruption",
    "keeps its",
    "tree",
)


class _RetentionTexts(NamedTuple):
    doc_body: str
    support_body: str
    support_source: str


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _extract_body(pattern: re.Pattern[str], text: str, source: Path) -> str:
    match = pattern.search(text)
    assert match is not None, f"expected the retention bullet to remain in {source}"
    return _normalize(match.group("body"))


def _missing_clauses(body: str) -> list[str]:
    return [clause for clause in _RETENTION_CONTRACT_CLAUSES if clause not in body]


def _retention_texts() -> _RetentionTexts:
    doc_source = _DOC_PATH.read_text(encoding="utf-8")
    support_source = _SUPPORT_PATH.read_text(encoding="utf-8")
    return _RetentionTexts(
        doc_body=_extract_body(_DOC_RETENTION_BULLET, doc_source, _DOC_PATH),
        support_body=_extract_body(_SUPPORT_RETENTION_BULLET, support_source, _SUPPORT_PATH),
        support_source=support_source,
    )


def test_retention_rationale_matches_support_contract() -> None:
    texts = _retention_texts()
    for source, body in (
        (_DOC_PATH, texts.doc_body),
        (_SUPPORT_PATH, texts.support_body),
    ):
        missing = _missing_clauses(body)
        assert missing == [], f"{source} retention rationale is missing: {missing}"


def test_stale_sweep_is_documented_inline_and_implemented() -> None:
    doc_source = _normalize(_DOC_PATH.read_text(encoding="utf-8"))
    assert "stale-crash sweep below" not in doc_source, "testing-parallel.md must not point at a nonexistent sweep section"
    assert "24 h stale-crash sweep the next run performs at controller startup" in doc_source, "the doc must state when the stale-crash sweep runs"
    assert "`STALE_RUN_MAX_AGE_S`" in doc_source and "`install_run_basetemp`" in doc_source

    support_source = _SUPPORT_PATH.read_text(encoding="utf-8")
    assert "STALE_RUN_MAX_AGE_S = 24 * 60 * 60" in support_source
    assert "remove_run_dirs(stale_run_dirs(root, now=now))" in support_source


def test_retention_guard_detects_reap_drift() -> None:
    support_body = _retention_texts().support_body
    drifted_body = support_body.replace("removes the run's dir", "deletes every run's dir", 1)
    assert drifted_body != support_body, "mutation did not change the support rationale"
    assert _missing_clauses(drifted_body) == ["removes the run's dir"]
