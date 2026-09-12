"""ADR-hygiene gate for the Convergence retirement + client-repo inversion.

Mission ``post-convergence-governance-01M1TMPH`` (Tier-3, A1). The Convergence
(#3881 / #3824) retired the in-place CLI→SaaS sync/daemon/delivery subsystem and
inverted feature-ownership (this core repo is now a CLIENT of the authoritative
``spec-kitty/zeitgeist`` + ``spec-kitty/saas`` repos). Four Accepted ADRs still
governed the deleted subsystems; a new ADR supersedes them and records the
inversion. This gate keeps that decision record honest:

* the four retired-subsystem ADRs are ``Superseded`` and point at the new ADR;
* the new ADR is ``Accepted``, ``supersedes`` all four, and names the inversion;
* the shared-package-boundary ADR (2026-04-25-1) stays ``Accepted`` — it is the
  precedent the inversion extends, not a reversal of it.

Runs in well under the 5 s NFR-002 budget (parses ~6 small markdown headers).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architectural

_REPO_ROOT = Path(__file__).resolve().parents[2]
_ADR = _REPO_ROOT / "docs" / "adr"

_NEW_ADR_REL = "docs/adr/3.x/2026-09-06-1-convergence-retirement-and-client-repo-inversion.md"
_NEW_ADR_BASENAME = "2026-09-06-1-convergence-retirement-and-client-repo-inversion.md"

# The four ADRs the Convergence retirement supersedes.
_SUPERSEDED_ADRS: tuple[str, ...] = (
    "docs/adr/3.x/2026-06-30-1-sync-daemon-identity-and-cleanup-classification.md",
    "docs/adr/3.x/2026-04-11-1-saas-rollout-and-readiness.md",
    "docs/adr/3.x/2026-08-09-1-project-sync-store-boundary.md",
    "docs/adr/2.x/2026-02-27-1-cli-tracker-surface-gated-by-saas-sync-flag.md",
)

# Left Accepted deliberately — the precedent the inversion extends.
_STILL_ACCEPTED_ADR = "docs/adr/3.x/2026-04-25-1-shared-package-boundary.md"


def _parse_front_matter(text: str) -> dict[str, object]:
    """Parse a leading ``---`` YAML front-matter block into a dict.

    Pure function of its input so the non-vacuity test can drive it with a
    synthetic header and prove the status check has teeth without touching disk.
    Returns ``{}`` when no front-matter block is present.
    """
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    block = text[3:end]
    parsed = yaml.safe_load(block)
    return parsed if isinstance(parsed, dict) else {}


def _retired_adrs_not_superseded(headers: dict[str, dict[str, object]]) -> list[str]:
    """Return every ``path`` whose front-matter is not a valid supersession.

    A valid supersession has ``status == "Superseded"`` AND a ``superseded_by``
    that names the new convergence-retirement ADR. Pure over its input.
    """
    offenders: list[str] = []
    for path, fm in headers.items():
        status = fm.get("status")
        superseded_by = str(fm.get("superseded_by", ""))
        if status != "Superseded" or _NEW_ADR_BASENAME not in superseded_by:
            offenders.append(path)
    return offenders


def _front_matter_for(rel_paths: tuple[str, ...]) -> dict[str, dict[str, object]]:
    return {rel: _parse_front_matter((_REPO_ROOT / rel).read_text(encoding="utf-8")) for rel in rel_paths}


def test_retired_adrs_are_superseded_and_point_at_new_adr() -> None:
    headers = _front_matter_for(_SUPERSEDED_ADRS)
    offenders = _retired_adrs_not_superseded(headers)
    assert not offenders, f"these retired-subsystem ADRs are not marked Superseded with a pointer to {_NEW_ADR_BASENAME}: {offenders}"


def test_new_convergence_retirement_adr_shape() -> None:
    new_path = _REPO_ROOT / _NEW_ADR_REL
    assert new_path.exists(), f"missing convergence-retirement ADR at {_NEW_ADR_REL}"
    text = new_path.read_text(encoding="utf-8")
    fm = _parse_front_matter(text)

    assert fm.get("status") == "Accepted", "the convergence-retirement ADR must be Accepted"

    supersedes = fm.get("supersedes")
    assert isinstance(supersedes, list), "the new ADR must declare a `supersedes:` list"
    supersedes_set = {str(s) for s in supersedes}
    missing = set(_SUPERSEDED_ADRS) - supersedes_set
    assert not missing, f"the new ADR's `supersedes:` omits: {sorted(missing)}"

    # Records the client-repo inversion, in prose.
    body = text.lower()
    assert "client" in body and "spec-kitty/zeitgeist" in body and "spec-kitty/saas" in body, (
        "the new ADR must record the client-repo inversion naming the upstream authoritative repos spec-kitty/zeitgeist and spec-kitty/saas"
    )


def test_shared_package_boundary_adr_stays_accepted() -> None:
    fm = _parse_front_matter((_REPO_ROOT / _STILL_ACCEPTED_ADR).read_text(encoding="utf-8"))
    assert fm.get("status") == "Accepted", (
        "2026-04-25-1-shared-package-boundary.md must stay Accepted — it is the precedent the client-repo inversion extends, not a reversal of it"
    )


def test_supersession_matcher_is_non_vacuous() -> None:
    """Proof-of-teeth: a synthetic still-Accepted retired ADR must be flagged.

    Without this, ``_retired_adrs_not_superseded`` could silently pass everything
    and the gate above would be vacuous.
    """
    synthetic_bad = {"fake/adr.md": {"status": "Accepted"}}
    assert _retired_adrs_not_superseded(synthetic_bad) == ["fake/adr.md"]

    synthetic_good = {
        "fake/adr.md": {
            "status": "Superseded",
            "superseded_by": f"docs/adr/3.x/{_NEW_ADR_BASENAME}",
        }
    }
    assert _retired_adrs_not_superseded(synthetic_good) == []
