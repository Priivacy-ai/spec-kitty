"""Golden round-trip ratchet for the WP-authoring frontmatter contract (#2220 + #2221).

The WP-frontmatter ownership contract is encoded in three independent places that
historically drifted apart:

1. Doctrine prose — BOTH ``tasks/guidelines.md`` copies (the ``actions/`` runtime
   copy and the ``mission-steps/`` step-contract copy).
2. The authoring template — ``software-dev/templates/task-prompt-template.md``
   frontmatter.
3. The ownership validator — ``specify_cli.ownership.validation`` whose
   ``_CODE_PREFIXES = ("src/", "tests/")`` is **repo-root-relative**.

Per C-004 the *code* (the validator) is the single source of authority for the
path shape: ``owned_files`` must be **repo-root-relative**, never absolute. This
module is the SSOT ratchet that locks the prose and template to that authority so
they cannot silently re-diverge:

- A mandatory prose ratchet pins BOTH ``guidelines.md`` copies to repo-root-relative
  guidance and forbids the literal ``absolute path`` drift vector.
- A golden round-trip drives the REAL ownership validator + finalize resolve path
  (read from the on-disk template, not a hand-written fixture): a WP authored with
  repo-relative ``owned_files`` passes; an absolute-path entry fails consistently.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from specify_cli.frontmatter import read_frontmatter
from specify_cli.ownership.frontmatter_source import (
    InMemoryFrontmatterSource,
    resolve_wp_manifests,
)
from specify_cli.ownership.validation import validate_glob_matches, validate_ownership
from specify_cli.status import WPMetadata
from tests.doctrine.conftest import DOCTRINE_SOURCE_ROOT, REPO_ROOT

pytestmark = [pytest.mark.fast, pytest.mark.doctrine]

# --- The three drifting encodings, pinned to disk -------------------------------

SOFTWARE_DEV_ROOT = DOCTRINE_SOURCE_ROOT / "missions" / "software-dev"

GUIDELINES_ACTIONS = SOFTWARE_DEV_ROOT / "actions" / "tasks" / "guidelines.md"
GUIDELINES_STEPS = (
    DOCTRINE_SOURCE_ROOT
    / "missions"
    / "mission-steps"
    / "software-dev"
    / "tasks"
    / "guidelines.md"
)
TASK_PROMPT_TEMPLATE = SOFTWARE_DEV_ROOT / "templates" / "task-prompt-template.md"

GUIDELINES_COPIES = (GUIDELINES_ACTIONS, GUIDELINES_STEPS)

# The four ownership-contract keys a template-authored WP must self-declare so it
# validates + finalizes on the first pass.
OWNERSHIP_CONTRACT_KEYS = (
    "owned_files",
    "authoritative_surface",
    "execution_mode",
    "create_intent",
)

# The drift vector the prose ratchet forbids (C-004: code is repo-relative).
FORBIDDEN_PROSE_TOKEN = "absolute path"
# The instruction the prose must now carry instead.
REQUIRED_PROSE_TOKEN = "repo-root-relative"

# Production-shaped, repo-root-relative owned_files for the authored WP. Both are
# real existing files under the authoritative surface, so the surface-prefix check
# and the literal-path glob check both resolve them.
AUTHORED_AUTHORITATIVE_SURFACE = "src/specify_cli/ownership/"
AUTHORED_OWNED_FILES = (
    "src/specify_cli/ownership/validation.py",
    "src/specify_cli/ownership/models.py",
)
# A planned-new file modelled in create_intent (real-format repo-relative path).
AUTHORED_CREATE_INTENT = ("src/specify_cli/ownership/_roundtrip_probe.py",)


# --- T003 step 2: mandatory prose ratchet (pins the doctrine TEXT) ---------------


@pytest.mark.parametrize("guidelines_path", GUIDELINES_COPIES, ids=lambda p: p.parent.parent.parent.name)
def test_guidelines_copy_instructs_repo_root_relative_owned_files(guidelines_path: Path) -> None:
    """Each ``guidelines.md`` copy must instruct repo-root-relative owned_files.

    The validator is repo-root-relative (C-004); the prose must match it and must
    not carry the ``absolute path`` drift vector that contradicts the validator.
    """
    assert guidelines_path.exists(), f"missing doctrine copy: {guidelines_path}"
    text = guidelines_path.read_text(encoding="utf-8").lower()

    assert FORBIDDEN_PROSE_TOKEN not in text, (
        f"{guidelines_path} still instructs '{FORBIDDEN_PROSE_TOKEN}' owned_files — "
        "this contradicts the repo-root-relative ownership validator (C-004)."
    )
    assert REQUIRED_PROSE_TOKEN in text, (
        f"{guidelines_path} must instruct '{REQUIRED_PROSE_TOKEN}' owned_files paths "
        "to match the ownership validator."
    )


def test_both_guidelines_copies_share_owned_files_guidance() -> None:
    """Both copies must carry the same repo-root-relative owned_files guidance line.

    The original defect was two copies drifting apart; pin the shared guidance line
    so they cannot re-diverge on the owned_files contract.
    """

    def _owned_files_line(path: Path) -> str:
        for line in path.read_text(encoding="utf-8").splitlines():
            if "owned" in line.lower() and "frontmatter" in line.lower():
                return line.strip()
        raise AssertionError(f"no owned-files guidance line found in {path}")

    actions_line = _owned_files_line(GUIDELINES_ACTIONS)
    steps_line = _owned_files_line(GUIDELINES_STEPS)
    assert actions_line == steps_line, (
        "owned_files guidance diverges between the two guidelines.md copies:\n"
        f"  actions:      {actions_line!r}\n"
        f"  mission-steps:{steps_line!r}"
    )


# --- T003 step 3: GREEN round-trip — drive the REAL validator from the template --


def _template_frontmatter() -> dict[str, Any]:
    """Read the on-disk task-prompt template frontmatter (raw mapping)."""
    frontmatter, _body = read_frontmatter(TASK_PROMPT_TEMPLATE)
    return dict(frontmatter)


def test_template_declares_ownership_contract_keys() -> None:
    """The on-disk template must declare all four ownership-contract keys.

    Read from disk (not fabricated) so the ratchet fails if the template omits a
    key — this forbids the ``template-exists``-by-fabrication anti-pattern.
    """
    frontmatter = _template_frontmatter()
    missing = [key for key in OWNERSHIP_CONTRACT_KEYS if key not in frontmatter]
    assert not missing, (
        f"task-prompt-template.md frontmatter omits ownership-contract keys: {missing}. "
        "A template-authored WP cannot validate + finalize on the first pass without them."
    )


def _authored_wp_from_template(owned_files: tuple[str, ...]) -> WPMetadata:
    """Build a WP as if authored from the on-disk template.

    Pulls ``execution_mode`` and ``authoritative_surface`` from the REAL template
    frontmatter (so the test fails if the template drops or mis-shapes them) and
    fills the placeholder ``owned_files``/``create_intent`` with the supplied
    production-shaped repo-relative paths — mirroring how an author completes the
    template before finalize.
    """
    frontmatter = _template_frontmatter()
    for key in OWNERSHIP_CONTRACT_KEYS:
        assert key in frontmatter, f"template must declare {key!r} before round-trip"

    return WPMetadata(
        work_package_id="WP01",
        title="WP-authoring contract round-trip probe",
        execution_mode=str(frontmatter["execution_mode"]),
        owned_files=list(owned_files),
        authoritative_surface=AUTHORED_AUTHORITATIVE_SURFACE,
        create_intent=list(AUTHORED_CREATE_INTENT),
    )


def test_template_authored_wp_passes_ownership_and_finalize_first_time() -> None:
    """A WP authored from the template with repo-relative owned_files validates.

    Drives the REAL resolve→validate seam (``resolve_wp_manifests`` →
    ``validate_ownership``) plus the finalize-time literal-path glob check, exactly
    as ``spec-kitty agent mission finalize-tasks`` does — not a structural
    template-exists assertion (C-006).
    """
    wp_meta = _authored_wp_from_template(AUTHORED_OWNED_FILES)
    source = InMemoryFrontmatterSource({"WP01": wp_meta})
    manifests = resolve_wp_manifests(source)
    assert "WP01" in manifests, "authored WP did not resolve to an ownership manifest"

    ownership_result = validate_ownership(manifests, {"WP01": []})
    assert ownership_result.passed, (
        f"repo-relative authored WP unexpectedly failed ownership validation: "
        f"{ownership_result.errors}"
    )

    create_intent = {"WP01": list(AUTHORED_CREATE_INTENT)}
    glob_result = validate_glob_matches(manifests, REPO_ROOT, create_intent=create_intent)
    assert glob_result.passed, (
        f"repo-relative authored WP failed the finalize literal-path glob check: "
        f"{glob_result.errors}"
    )


# --- T003 step 4: RED case — an absolute-path entry fails consistently -----------


def test_absolute_owned_files_entry_fails_validation_consistently() -> None:
    """An absolute ``owned_files`` path fails ownership validation, every run.

    Models the drift the contract forbids: the author used absolute paths. The
    only difference from the green case is the leading ``/abs/`` on every entry, so
    the failure is attributable to absoluteness alone. The repo-root-relative
    validator rejects them (an absolute path is not under the repo-relative
    authoritative_surface), so finalize would Exit(1) before lanes are written.
    Asserted across repeated runs to prove the failure is consistent, not
    order-dependent.
    """
    absolute_entries = tuple("/abs/" + path for path in AUTHORED_OWNED_FILES)
    wp_meta = _authored_wp_from_template(absolute_entries)

    for _ in range(3):
        source = InMemoryFrontmatterSource({"WP01": wp_meta})
        manifests = resolve_wp_manifests(source)
        result = validate_ownership(manifests, {"WP01": []})
        assert not result.passed, (
            "absolute owned_files paths were accepted by ownership validation — "
            "the repo-relative contract (C-004) is not enforced."
        )
        assert any(absolute_entries[0] in err for err in result.errors), (
            f"validation failed but the absolute path was not surfaced: {result.errors}"
        )
