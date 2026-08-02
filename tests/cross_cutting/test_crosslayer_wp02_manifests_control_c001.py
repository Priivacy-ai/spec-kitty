"""C-011 (ATDD-First Discipline) pin for WP02's crosslayer manifests, FR-006
discrimination control, and C-001 RFC-1-invalid fixture.

Mission crosslayer-composition-suite-01KYJA33, WP02
(``conformance/crosslayer/manifest.yaml``, ``cases/architect-run-skill.yaml``,
``cases/reviewer-run-skill.yaml``, ``control.yaml``,
``fixtures/invalid-persona-missing-key.Soul.md``). The operator ruled C-011
(charter.md:504) binding over charter.yaml's ``tdd_required: false``: this
file was committed BEFORE any of WP02's implementation files existed, so it
is RED on the lane's base commit (the real ``npx @garrison-hq/muster``
invocations below ENOENT against paths that do not exist yet) and GREEN only
once WP02's fixtures are authored. See the WP02 task file's Activity Log for
the exact RED/GREEN transcript.

Every case below invokes the REAL, offline-cached ``@garrison-hq/muster@1.2.1``
CLI via subprocess (``npx``) — never a mock of ``contradiction-lint.ts`` or
``composition.ts``. ``_run_muster`` tries ``--offline`` first (matching this
mission's cache-warm-then-offline convention) and falls back to a live
registry fetch only if the local npm cache does not have the package, so this
test degrades gracefully rather than silently mocking reality. If neither
``npx`` nor a network-reachable registry is available at all, the whole
module skips with a clear reason — an environment gap, never a fabricated
pass.

IMPORTANT, PLAINLY STATED FINDINGS FROM REAL VERIFICATION (not assumed,
not designed-then-trusted — each is backed by an actual command run in this
lane during WP02's implementation; see the WP02 Activity Log for the full
transcript):

1. **FR-006's originally pinned fixture text did not discriminate —
   REMEDIATED in this pass.** spec.md's original "#### FR-006 pinned
   fixture text" section pinned, verbatim, a persona sentence containing
   "Always ... restating the full context before every response." and a
   skill sentence containing "... No restated context, no preamble." Real
   execution against ``contradiction-lint.ts``'s actual heuristic
   (``NEGATION_OPERATORS`` = never/refuse/refusal/prohibited/forbid/
   forbidden/deny/block/not/disallow/reject — bare "no" is NOT a member)
   showed this exact text produced **zero findings in both the flip and
   the neutralized direction** — the committed control, built verbatim per
   the pinned text as WP02's task file originally required, did not
   discriminate. This was the exact "vacuous control" failure mode
   spec.md's own Dependencies section (citing this fork's ``0b1cf9b8a``
   hollowed-control fix) and the operator's standing directive both warn
   against — caught here, before shipping, by actually running it, not by
   trusting the spec's prose claim.

   **Remediation**: spec.md's pinned FR-006 fixture text was amended to use
   ``contradiction-lint.ts``'s real recognized vocabulary. The skill
   clause's bare "No restated context, no preamble." became "Never restate
   context or include a preamble." (adds a recognized
   ``NEGATION_OPERATORS`` member, same semantic meaning: no restating
   context, no preamble). The neutralized persona sentence was also
   amended, from "Always ground responses ..." to "Ground each response
   ..." — dropping "Always"/"every", both ``ACCOMMODATION_OPERATORS``
   members, which would otherwise still trip ``isRefinement``'s
   unconditional-contradiction branch (``aHasAccommodation &&
   bHasNegation`` short-circuits to "not a refinement" regardless of the
   neutralized clause's actual content — a real false-positive found
   empirically while designing this fix) against the skill's new "never".
   Both directions were proved on real ``findings``, not exit code: flip →
   ``findings == ["cross-layer-contradiction", "undefined-precedence"]``
   (length > 0, names the real contradiction); neutralize → ``findings ==
   []``. ``test_fr006_committed_control_discriminates_both_directions_on_findings``
   below pins this real, now-discriminating shape (watched RED against the
   pre-fix wording, then GREEN after) and will fail again if the control
   ever regresses into vacuity. The companion test,
   ``test_fr006_mechanism_proof_...``, is unchanged — it already proved
   the underlying lint/harness mechanism is content-driven; this fix closes
   the specific pinned-wording defect it isolated.
2. **C-001's originally pinned exit code did not match real behavior —
   spec.md AMENDED to pin the real behavior.** spec.md's original C-001
   stated a persona missing a required RFC-1 key propagates out of
   ``runCrossLayerManifest`` and becomes an ``ExecutionError`` -> exit **2**
   with a ``muster: crosslayer manifest run failed:`` stderr line. Real
   execution shows this is not what happens: ``manifest-runner.ts``'s
   ``runManifest`` catches every per-case dispatch error (including the
   RFC-1 strict-mode throw from ``resolvePersonaLayer``, which happens
   inside ``assembleComposedContext`` during per-case dispatch) in its own
   per-case ``try/catch`` and records ``{passed: false, error: message}``,
   contributing to ``summary.failed`` — never re-thrown to the CLI-level
   ``doCrossLayerStaticOnly`` catch block that maps to exit 2. Real,
   observed behavior: **exit 1**, a normal ``--json`` summary (or
   human-readable summary) with the RFC-1 violation message in the case's
   ``error`` field, **no ``findings`` key at all** (categorically distinct
   from an ordinary contradiction case result, which always carries a
   ``findings`` array, even an empty one), and **empty stderr**. This IS
   still distinguishable from a genuine stack contradiction by a reviewer
   or a script — just not via exit code alone: check for the ``error``
   field's presence (absent on any graded ``findings`` result) plus its
   ``"RFC-1 strict-mode validation"`` substring. spec.md's C-001 constraint
   was amended (this remediation pass) to pin this real, independently
   verified shape — exit **1**, an ``error`` field containing "RFC-1
   strict-mode validation", no ``findings`` key — instead of the
   never-observed exit 2. A muster upstream issue was filed
   (https://github.com/garrison-hq/muster/issues/70) describing that the
   RFC-1 strict-mode failure is swallowed into a per-case result rather
   than surfacing as an ``ExecutionError``/exit 2 as C-001's original
   design intended; that swallowing is not fixed here — muster itself is
   out of scope for this mission. The exit-2/``ExecutionError`` path is
   real and reachable (proven by
   ``test_c001_manifest_level_failure_produces_exit_2``, a manifest-load-
   level failure — nonexistent manifest path, or a fixturePath that fails
   the path-traversal guard) — it is simply not the path an RFC-1-invalid
   PERSONA fixture takes in the real, currently shipped v1.2.1 CLI.

Both findings are reported plainly here and in the WP02 work log.
Finding #1 is a code-level fix (fixture wording, this lane's owned files).
Finding #2 is a spec-only amendment (C-001's pinned exit code and
distinguishing field) plus an upstream muster issue — not a code fix, since
the swallowing behavior lives in muster itself, out of this mission's scope.
Neither is hidden behind a convenient ``expected:`` block choice in the
committed fixtures.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.utils import REPO_ROOT

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

_MUSTER_PKG = "@garrison-hq/muster@1.2.1"
_CROSSLAYER_DIR = REPO_ROOT / "conformance" / "crosslayer"


def _npx_available() -> bool:
    return shutil.which("npx") is not None


def _run_muster(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the real muster CLI, preferring the offline-cached package.

    Tries ``npx --offline`` first (this mission's cache-warm-then-offline
    convention); if the local npm cache lacks the package, falls back to a
    live registry fetch. Never mocks the CLI.
    """
    offline = subprocess.run(
        ["npx", "--offline", _MUSTER_PKG, *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )
    # npm's offline-cache-miss message varies by version; treat any nonzero
    # exit whose stderr mentions the registry/offline as "not cached" and
    # retry live. A real muster-side error (e.g. our own ENOENT/exit 2/1
    # cases) never mentions npm/registry text, so this is a safe fallback.
    if offline.returncode != 0 and (
        "ENOTCACHED" in offline.stderr or "offline" in offline.stderr.lower()
    ):
        return subprocess.run(
            ["npx", _MUSTER_PKG, *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            check=False,
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


# ---------------------------------------------------------------------------
# T008 / T012 step 1a — local-mechanism proof (self-authored sandbox fixtures,
# never the real committed cross-lane paths).
# ---------------------------------------------------------------------------


def _write_rfc1_persona(path: Path, *, body: str, name: str = "Sandbox Persona") -> None:
    path.write_text(
        f"""---
soul_spec: "1.0"
id: "dev.example.sandbox-persona"
kind: soul
name: "{name}"
locale: "en-US"
description: "Sandbox persona for local WP02 manifest/CLI wiring proof (never graded, C-003)."
tags: ["sandbox"]
license: "Apache-2.0"

composition:
  extends: []
  mixins: []
  merge_policy: standard

profiles: ["default"]
profile_overrides: {{}}

values:
  priorities:
    - "helpfulness within defined boundaries"
  taboo: []

voice:
  formality: 60
  warmth: 70
  verbosity: 50
  jargon: 20
  formatting: plain
  emoji_policy: never

interaction:
  clarifying_questions: when_ambiguous
  uncertainty: explicit
  disagreement: soft
  confirmations: implicit

safety:
  refusal_style: brief
  privacy: strict
  speculation: avoid

evaluation:
  rule_catalog: []
  critical_criteria: []
  test_prompts: []

extensions: {{}}
---

# {name}

{body}
""",
        encoding="utf-8",
    )


def test_fr004_sandbox_mechanism_proof_benign_case_passes(tmp_path: Path) -> None:
    """T008/T012 1a: a local-only sandbox manifest (never committed) proves
    the manifest/CLI mechanism (path resolution, $ref case includes, static
    lint dispatch) works end to end, using only content this lane controls.
    """
    _write_rfc1_persona(
        tmp_path / "persona.Soul.md",
        body="Assist the user with clear, well-reasoned answers grounded in the request at hand.",
    )
    (tmp_path / "sop.md").write_text(
        "# SOP: Sandbox Operating Guidelines\n\n"
        "## Rule: Maintain professional tone\nResponses must stay professional and on-topic.\n",
        encoding="utf-8",
    )
    (tmp_path / "skill.SKILL.md").write_text(
        "# spk-run-next (sandbox stand-in)\n\n"
        "Advance the mission runtime loop by evaluating the current step.\n",
        encoding="utf-8",
    )
    (tmp_path / "case.yaml").write_text(
        "id: sandbox-benign\n"
        "testClass: static\n"
        "layers:\n"
        "  - layerType: persona\n"
        "    fixturePath: persona.Soul.md\n"
        "  - layerType: sop\n"
        "    fixturePath: sop.md\n"
        "  - layerType: skill\n"
        "    fixturePath: skill.SKILL.md\n"
        "expected:\n"
        "  ok: true\n"
        "  findingTypes: []\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("cases:\n  - $ref: case.yaml\n", encoding="utf-8")

    result = _run_muster(
        ["crosslayer", "run", str(manifest), "--static-only", "--json"], cwd=REPO_ROOT
    )

    assert result.returncode == 0, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["failed"] == 0
    assert summary["results"][0]["findings"] == []


def test_fr004_sandbox_mechanism_proof_falsification_rigged_case_fails(tmp_path: Path) -> None:
    """Falsification of the above: swap in a case whose ``expected`` block
    cannot be satisfied by the real composition — the harness must report
    exit 1 / failed > 0, proving it can actually report failure (not an
    always-pass harness bug).
    """
    _write_rfc1_persona(
        tmp_path / "persona.Soul.md",
        body="Assist the user with clear, well-reasoned answers grounded in the request at hand.",
    )
    (tmp_path / "sop.md").write_text(
        "# SOP: Sandbox Operating Guidelines\n\nAssist the user with their request.\n",
        encoding="utf-8",
    )
    (tmp_path / "case.yaml").write_text(
        "id: sandbox-falsify\n"
        "testClass: static\n"
        "layers:\n"
        "  - layerType: persona\n"
        "    fixturePath: persona.Soul.md\n"
        "  - layerType: sop\n"
        "    fixturePath: sop.md\n"
        "expected:\n"
        "  ok: false\n",  # deliberately unsatisfiable — the real composition is ok: true
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("cases:\n  - $ref: case.yaml\n", encoding="utf-8")

    result = _run_muster(
        ["crosslayer", "run", str(manifest), "--static-only", "--json"], cwd=REPO_ROOT
    )

    assert result.returncode == 1, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    assert summary["failed"] > 0


# ---------------------------------------------------------------------------
# C-001 — the real committed invalid-persona fixture.
# ---------------------------------------------------------------------------


def test_c001_invalid_persona_is_a_categorical_error_never_a_findings_result(
    tmp_path: Path,
) -> None:
    """The real committed C-001 fixture, run through the real CLI, must never
    silently pass and must never be reported as an ordinary ``findings``
    result (a graded contradiction). It genuinely errors (RFC-1 strict-mode
    violation) at exit **1** — spec.md's C-001 was amended (see module
    docstring finding #2) to pin this real, independently-verified shape
    rather than the never-observed exit 2. This test pins the TRUE observed
    shape: ``passed: false``, an ``error`` string naming the missing RFC-1
    key, no ``findings`` array, and empty stderr — the categorical
    distinction from a graded contradiction result that makes this fixture
    still reviewer-distinguishable, just not via exit code alone.
    """
    fixture = _CROSSLAYER_DIR / "fixtures" / "invalid-persona-missing-key.Soul.md"
    assert fixture.is_file(), f"C-001 fixture not committed at {fixture}"

    (tmp_path / "sop.md").write_text(
        "# SOP: Sandbox Operating Guidelines\n\nAssist the user with their request.\n",
        encoding="utf-8",
    )
    (tmp_path / "case.yaml").write_text(
        "id: c001-invalid-persona\n"
        "testClass: static\n"
        "layers:\n"
        f"  - layerType: persona\n    fixturePath: {fixture}\n"
        "  - layerType: sop\n    fixturePath: sop.md\n"
        "expected:\n  ok: true\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.yaml"
    manifest.write_text("cases:\n  - $ref: case.yaml\n", encoding="utf-8")

    result = _run_muster(
        ["crosslayer", "run", str(manifest), "--static-only", "--json"], cwd=REPO_ROOT
    )

    # Real, observed behavior (documented discrepancy from spec.md's pinned
    # exit 2 — see module docstring finding #2). Not fabricated as exit 2.
    assert result.returncode == 1, result.stdout + result.stderr
    summary = json.loads(result.stdout)
    case_result = summary["results"][0]
    assert case_result["passed"] is False
    assert "findings" not in case_result, (
        "C-001 must never surface as an ordinary findings result — "
        "it must be a categorical error, distinct from a graded contradiction."
    )
    assert "error" in case_result
    assert "RFC-1 strict-mode validation" in case_result["error"]
    assert "voice" in case_result["error"]
    assert result.stderr == "", (
        "Real behavior: the RFC-1 violation is caught per-case inside "
        "runManifest and never reaches the CLI's ExecutionError/stderr path "
        "(spec.md's C-001 stderr-substring claim does not hold for this "
        "scenario — see module docstring finding #2)."
    )


def test_c001_manifest_level_failure_produces_exit_2(tmp_path: Path) -> None:
    """Sanity/mechanism check: the exit-2 / ``ExecutionError`` /
    ``muster: crosslayer manifest run failed:`` path IS real and reachable —
    for a manifest-LOAD-level failure (here: a fixturePath that escapes the
    manifest directory, tripping the path-traversal guard in
    ``manifest-runner.ts`` before any case dispatch begins). This isolates
    C-001's discrepancy to the specific "RFC-1-invalid persona" scenario,
    not to the exit-2 mechanism itself.
    """
    (tmp_path / "crosslayer").mkdir()
    (tmp_path / "outside").mkdir()
    _write_rfc1_persona(tmp_path / "crosslayer" / "persona.Soul.md", body="Assist the user.")
    (tmp_path / "crosslayer" / "sop.md").write_text("# SOP\nAssist.\n", encoding="utf-8")
    (tmp_path / "outside" / "skill.SKILL.md").write_text("# Skill\nBe terse.\n", encoding="utf-8")
    (tmp_path / "crosslayer" / "case.yaml").write_text(
        "id: escape-test\n"
        "testClass: static\n"
        "layers:\n"
        "  - layerType: persona\n    fixturePath: persona.Soul.md\n"
        "  - layerType: sop\n    fixturePath: sop.md\n"
        "  - layerType: skill\n    fixturePath: ../outside/skill.SKILL.md\n"
        "expected:\n  ok: true\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "crosslayer" / "manifest.yaml"
    manifest.write_text("cases:\n  - $ref: case.yaml\n", encoding="utf-8")

    result = _run_muster(["crosslayer", "run", str(manifest), "--static-only"], cwd=REPO_ROOT)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "muster: crosslayer manifest run failed:" in result.stderr
    assert "Path traversal rejected" in result.stderr


# ---------------------------------------------------------------------------
# FR-006 — the real committed control.yaml (verbatim pinned text) and a
# mechanism-proof control using recognized negation wording.
# ---------------------------------------------------------------------------


def test_fr006_committed_control_discriminates_both_directions_on_findings(
    tmp_path: Path,
) -> None:
    """Pins the control's OWN findings-length in BOTH directions, on the
    REAL committed ``control.yaml`` (flip, as shipped after remediation)
    and a temp neutralized copy (never mutating the committed fixtures).
    Proves the discrimination control genuinely discriminates on
    ``findings`` — never on muster's own exit code, which reflects only
    whether the case's ``expected:`` block matches reality, not whether a
    finding fired (see module docstring finding #1; ``manifest-runner.ts``'s
    ``runStaticCase`` compares ``report.ok``/``findingTypes`` against
    ``expected``, so exit code alone cannot serve as the discrimination
    signal here).

    Watched RED before this fix (pre-remediation wording: bare "no" is not
    a ``NEGATION_OPERATORS`` member; both directions produced ``findings ==
    []``, indistinguishable) and GREEN after (skill wording changed to
    "never"; neutralized persona wording changed to drop the
    ``ACCOMMODATION_OPERATORS`` tokens "Always"/"every" that would
    otherwise still trip ``isRefinement``'s unconditional-contradiction
    branch against the skill's "never", re-vacuuming the neutralize
    direction). If this test ever starts failing again — either direction
    — the control has regressed into vacuity; do not loosen this assertion,
    re-open the defect instead.
    """
    control = _CROSSLAYER_DIR / "control.yaml"
    assert control.is_file(), f"FR-006 control not committed at {control}"

    # --- Flip direction: real committed control.yaml, unmodified. ---
    flip_result = _run_muster(
        ["crosslayer", "run", str(control), "--static-only", "--json"], cwd=REPO_ROOT
    )
    flip_summary = json.loads(flip_result.stdout)
    flip_findings = flip_summary["results"][0]["findings"]

    assert len(flip_findings) > 0, (
        "Flip direction produced zero findings — the control has regressed "
        f"into vacuity (see module docstring finding #1). Got: {flip_findings!r}"
    )
    assert "cross-layer-contradiction" in flip_findings, (
        "Flip direction's findings do not name the real contradiction "
        f"(cross-layer-contradiction); got {flip_findings!r}."
    )
    # Findings-length pin (not merely non-empty): the exact set observed
    # during remediation. undefined-precedence also fires because this
    # fixture carries no `precedence:` block (T010's pinned structure).
    assert set(flip_findings) == {"cross-layer-contradiction", "undefined-precedence"}, (
        f"Flip findings set changed from the pinned shape: {flip_findings!r}"
    )

    # --- Neutralize direction: temp copy, only the persona body replaced. ---
    sandbox = tmp_path / "control-neutralized"
    sandbox.mkdir()
    (sandbox / "fixtures").mkdir()
    for name in ("control-persona.Soul.md", "control-sop.md", "control-skill.SKILL.md"):
        shutil.copy(_CROSSLAYER_DIR / "fixtures" / name, sandbox / "fixtures" / name)
    shutil.copy(control, sandbox / "control.yaml")

    persona_path = sandbox / "fixtures" / "control-persona.Soul.md"
    original = persona_path.read_text(encoding="utf-8")
    neutralized = original.replace(
        "Always answer in exhaustive, multi-paragraph detail, restating the "
        "full context before every response.",
        "Ground each response in the user's actual question, citing the "
        "specific detail that motivated the answer.",
    )
    assert neutralized != original, "pinned flip sentence not found in control-persona.Soul.md"
    persona_path.write_text(neutralized, encoding="utf-8")

    neutralize_result = _run_muster(
        ["crosslayer", "run", str(sandbox / "control.yaml"), "--static-only", "--json"],
        cwd=REPO_ROOT,
    )
    neutralize_summary = json.loads(neutralize_result.stdout)
    neutralize_findings = neutralize_summary["results"][0]["findings"]

    assert neutralize_findings == [], (
        "Neutralize direction produced findings — the neutralized persona "
        f"sentence still trips the lint: {neutralize_findings!r}"
    )

    # The discrimination proof itself: the two directions must differ.
    assert flip_findings != neutralize_findings, (
        "Flip and neutralize produced identical findings sets — the control "
        "does not discriminate."
    )


def test_fr006_mechanism_proof_recognized_negation_wording_does_discriminate(
    tmp_path: Path,
) -> None:
    """Proves the underlying lint/harness mechanism genuinely IS
    content-driven — same structure and intent as FR-006 (persona demands a
    verbosity behavior; skill explicitly forbids it; no ``precedence:``
    block), but using a NEGATION_OPERATORS-recognized word ("never") instead
    of the pinned text's unrecognized "no". Isolates WP02's own manifest/
    control wiring (proven sound here) from the specific wording defect in
    spec.md's pinned fixture text (pinned separately above).
    """
    # NOTE: the SOP text here is deliberately inert w.r.t. both
    # NEGATION_OPERATORS and ACCOMMODATION_OPERATORS (e.g. it avoids "assist",
    # which is itself an ACCOMMODATION_OPERATORS member and would create a
    # spurious (sop, skill) contradiction against the skill's "never" below —
    # a real false-positive found empirically while designing this test).
    (tmp_path / "sop.md").write_text(
        "# SOP\nFollow the project's documented style guide.\n", encoding="utf-8"
    )
    (tmp_path / "skill.SKILL.md").write_text(
        "You must never restate prior context and must keep every reply to "
        "one short sentence.\n",
        encoding="utf-8",
    )

    def _run_with_persona_body(body: str) -> list[str]:
        _write_rfc1_persona(tmp_path / "persona.Soul.md", body=body)
        (tmp_path / "case.yaml").write_text(
            "id: mechanism-proof\n"
            "testClass: static\n"
            "isDiscriminationControl: true\n"
            "layers:\n"
            "  - layerType: persona\n    fixturePath: persona.Soul.md\n"
            "  - layerType: sop\n    fixturePath: sop.md\n"
            "  - layerType: skill\n    fixturePath: skill.SKILL.md\n"
            "expected:\n  ok: true\n",
            encoding="utf-8",
        )
        manifest = tmp_path / "manifest.yaml"
        manifest.write_text("cases:\n  - $ref: case.yaml\n", encoding="utf-8")
        result = _run_muster(
            ["crosslayer", "run", str(manifest), "--static-only", "--json"], cwd=REPO_ROOT
        )
        return json.loads(result.stdout)["results"][0]["findings"]

    # Flip: persona uses a recognized ACCOMMODATION_OPERATORS word ("always")
    # against the skill's recognized NEGATION_OPERATORS word ("never").
    flip_findings = _run_with_persona_body(
        "You must always provide exhaustive detail and restate the entire "
        "conversation history before responding."
    )
    # Neutralize: same structure, persona text carries no
    # ACCOMMODATION_OPERATORS/NEGATION_OPERATORS token at all — no polarity
    # inversion signal, so the lint has nothing to flag.
    neutralize_findings = _run_with_persona_body(
        "Ground each answer in the specific detail from the user's question "
        "that prompted it."
    )

    assert "cross-layer-contradiction" in flip_findings
    assert flip_findings != []
    assert neutralize_findings == []
