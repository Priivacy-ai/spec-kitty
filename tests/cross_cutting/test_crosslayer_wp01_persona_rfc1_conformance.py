"""C-011 (ATDD-first) pin: WP01's committed personas must be RFC-1-conformant
against muster's REAL parser, not merely eyeballed.

Mission crosslayer-composition-suite-01KYJA33 (M7), WP01 remediation.

**Why this test exists**: WP01's original T006 verified projector determinism,
PROJECTION.md's fidelity-loss table, and the drift gate — but never actually
ran a generated persona through muster's own parser. ``spec.md:281`` calls the
committed personas an "RFC-1-conformant document" and C-001 makes RFC-1
validity a precondition for any cross-layer composition; nothing checked that
claim. This module closes that gap: it invokes the real, offline-cached
``@garrison-hq/muster`` CLI's ``check`` subcommand (static conformance of one
Soul.md document, per ``src/cli/index.ts`` — never touches the network) against
each committed persona and asserts ``ok: true`` with zero errors, exit code 0.

This was RED against WP01's original (broken) personas: `muster check` on
``conformance/crosslayer/personas/architect-alphonso.Soul.md`` fails with
``ok: false`` and a `"missing or malformed front matter"` (§3.1.1) error,
because the generator emits a `"# generated: true, ..."` comment BEFORE the
opening `---` delimiter, which muster's front-matter extractor
(``src/adapters/rfc1/frontmatter.ts``) does not tolerate — the document's
first line must be exactly `---`. See this file's own git history (this
module was authored as ``tests/conformance/test_persona_rfc1_parser_
conformance.py`` and later ``git mv``'d here — ``git log --follow`` on this
path surfaces the original RED/GREEN commits) for the commit this was RED at.

**Why this module lives under ``tests/cross_cutting/`` and not
``tests/conformance/``**: this suite's CI marker-selection ratchet
(``tests/architectural/test_gate_coverage.py``) requires every collected test
to be selected by at least one gate. This module's ``integration``/``e2e``
markers are explicitly negated by ``unit-contract-residual``
(``.github/workflows/ci-quality.yml``, the whole-tree marker catch-all), and
no scoped marker gate covers ``tests/conformance/**`` — that path was never
wired into any workflow's ``pytest`` path arguments, on any lane. Originally
authored under ``tests/conformance/``, this module was therefore selected by
**zero** CI gates (a silent orphan the ratchet itself caught). The
``e2e-cross-cutting`` job runs `tests/e2e/` and `tests/cross_cutting/`
directly by path (see that job's ``pytest`` invocation), which is why this
module was relocated here — mirroring where WP05's sibling
``test_crosslayer_wp05_rule_survival_cases.py`` already lives, and following
its own ``_run_muster`` helper convention exactly. The routing property that
matters is that a test is *selected by some CI gate*, not merely that it
lives somewhere under ``tests/`` — a file can satisfy the latter while
failing the former, as this one did.

Every ``npx`` invocation goes through ``_run_muster`` (mirrors WP02/WP05's own
helper exactly): prefer the offline-cached pinned package, fall back to a
live-registry fetch only on an explicit ``ENOTCACHED``/offline-message error —
never a bare ``npx --offline`` with no fallback (that only "works" off an
untracked, gitignored, developer-machine ``node_modules/`` that CI never
creates).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.utils import REPO_ROOT

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

_MUSTER_PKG = "@garrison-hq/muster@1.1.0"
_PERSONAS_DIR = REPO_ROOT / "conformance" / "crosslayer" / "personas"
_COMMITTED_PERSONAS: tuple[str, ...] = (
    "architect-alphonso.Soul.md",
    "reviewer-renata.Soul.md",
)


def _npx_available() -> bool:
    return shutil.which("npx") is not None


def _run_muster(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the real muster CLI, preferring the offline-cached package.

    Mirrors WP02's and WP05's own ``_run_muster`` helper exactly (same
    cache-warm-then-offline convention, ENOTCACHED/offline-message fallback to
    a live registry fetch). A bare ``npx --offline`` call with no fallback
    only "works" when a local ``node_modules/@garrison-hq/muster`` happens to
    already be present on disk — an untracked, gitignored, developer-machine
    artefact CI never creates — which would make a real CI run's RED/GREEN
    figures silently diverge from what this module actually pins.
    """
    run_env = os.environ.copy()

    offline = subprocess.run(
        ["npx", "--offline", _MUSTER_PKG, *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=run_env,
    )
    if offline.returncode != 0 and ("ENOTCACHED" in offline.stderr or "offline" in offline.stderr.lower()):
        return subprocess.run(
            ["npx", _MUSTER_PKG, *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
            env=run_env,
        )
    return offline


@pytest.fixture(autouse=True, scope="module")
def _require_npx() -> None:
    if not _npx_available():
        pytest.skip(
            "npx not found on PATH — this test requires Node.js/npm to invoke "
            "the real @garrison-hq/muster CLI (environment gap, not a code "
            "defect; never silently mocked)."
        )


@pytest.mark.parametrize("persona_filename", _COMMITTED_PERSONAS)
def test_committed_persona_is_rfc1_conformant_against_real_muster_parser(
    persona_filename: str,
) -> None:
    """The gap this module closes: a committed persona must actually parse
    and validate under muster's real, shipped RFC-1 parser (``muster check``,
    static, never touches the network) — never merely be assumed conformant
    because the projector's own unit tests pass.
    """
    persona_path = _PERSONAS_DIR / persona_filename
    assert persona_path.is_file(), f"committed persona not found at {persona_path}"

    result = _run_muster(["check", str(persona_path), "--json"], cwd=REPO_ROOT)

    report = json.loads(result.stdout)
    assert result.returncode == 0, f"{persona_filename} failed muster's real RFC-1 parser (exit {result.returncode}): {report.get('errors')}"
    assert report["ok"] is True, report["errors"]
    assert report["errors"] == []
