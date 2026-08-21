"""Z1-T1 N1/N2/N20: forbidden-field zero-attempt + forbidden-key set parity.

FORBIDDEN_CONTROL_KEYS mirrors F3's FORBIDDEN_KEYS_V1 (m1-contract-drafts/F3.md
§3.1 item 2); FORBIDDEN_OBSERVATION_KEYS mirrors F1's set
(m1-contract-drafts/F1.md §3.3, ``FORBIDDEN_OBSERVATION_KEYS``). ``assert_clean``
is a recursive, key-only walk — the client-side dual of the relay's own check
(Z1.md §3.2 item 3) — called before any network attempt (Z1.md §3.2 item 8
step 2).
"""

from __future__ import annotations

import pytest

from specify_cli.zeitgeist_client import sanitizer

# See test_grammar.py's pytestmark comment for why this is required, not
# cosmetic.
pytestmark = pytest.mark.fast


def test_forbidden_control_keys_matches_f3_forbidden_keys_v1():
    # m1-contract-drafts/F3.md:103
    assert frozenset(
        {
            "token",
            "authorization",
            "bearer",
            "password",
            "detail",
            "team",
            "team_id",
            "deployment",
            "deployment_id",
            "membership",
            "role",
            "user_id",
            "url",
            "runtime_url",
        }
    ) == sanitizer.FORBIDDEN_CONTROL_KEYS
    assert sanitizer.FORBIDDEN_CONTROL_KEYS_VERSION == 1


def test_forbidden_observation_keys_matches_f1_set():
    # m1-contract-drafts/F1.md:162-166
    assert frozenset(
        {
            "detail",
            "message",
            "text",
            "prose",
            "body",
            "command_text",
            "stdout",
            "stderr",
            "user",
            "user_id",
            "email",
            "actor",
            "team",
            "team_id",
            "team_slug",
            "deployment",
            "deployment_id",
            "token",
            "authorization",
            "bearer",
            "password",
            "secret",
            "url",
            "runtime_url",
            "branch",
        }
    ) == sanitizer.FORBIDDEN_OBSERVATION_KEYS
    assert sanitizer.FORBIDDEN_OBSERVATION_KEYS_VERSION == "v1"


def test_assert_clean_passes_a_document_with_no_forbidden_keys():
    sanitizer.assert_clean({"op": "presence.publish", "args": {"activity": "file_edit"}})


def test_assert_clean_raises_on_root_level_forbidden_key():
    # N1: offer("presence.publish", {..., "detail": "x"})
    with pytest.raises(sanitizer.ForbiddenFieldError) as excinfo:
        sanitizer.assert_clean({"op": "presence.publish", "args": {"detail": "x"}})
    assert excinfo.value.key == "detail"


def test_assert_clean_raises_on_nested_forbidden_key():
    # N2: nested forbidden key, control-envelope shape.
    # (FORBIDDEN_CONTROL_KEYS is F3's set; "user" is F1-observation-only —
    # this exercises the same nested-walk claim against a control-plane key.)
    with pytest.raises(sanitizer.ForbiddenFieldError) as excinfo:
        sanitizer.assert_clean({"args": {"meta": {"team_id": "t-1"}}})
    assert excinfo.value.key == "team_id"


def test_assert_clean_raises_on_nested_forbidden_key_observation_set():
    # N2 against the observation-key forbidden set (F1's), e.g. a presence
    # payload smuggling a free identity field.
    with pytest.raises(sanitizer.ForbiddenFieldError) as excinfo:
        sanitizer.assert_clean(
            {"args": {"meta": {"user": "robert"}}},
            forbidden=sanitizer.FORBIDDEN_OBSERVATION_KEYS,
        )
    assert excinfo.value.key == "user"


def test_assert_clean_is_key_only_a_forbidden_word_as_a_value_is_accepted():
    # F3.md:153 "a string VALUE equal to a forbidden key name is accepted"
    sanitizer.assert_clean({"args": {"note": "token"}})


def test_assert_clean_walks_lists_of_dicts():
    with pytest.raises(sanitizer.ForbiddenFieldError):
        sanitizer.assert_clean({"items": [{"ok": 1}, {"token": "x"}]})


def test_assert_clean_key_match_is_case_sensitive_by_design():
    # Case-sensitivity is a deliberate parity choice with F3's own
    # case-sensitive forbidden-key check (F3.md §3.1 item 2), not an
    # oversight — see sanitizer.py's module docstring. A differently-cased
    # key is therefore NOT caught by either forbidden set.
    sanitizer.assert_clean({"args": {"Token": "x"}})
    sanitizer.assert_clean(
        {"args": {"USER": "robert"}}, forbidden=sanitizer.FORBIDDEN_OBSERVATION_KEYS
    )


def test_assert_clean_never_repairs_only_raises():
    doc = {"args": {"detail": "x"}}
    with pytest.raises(sanitizer.ForbiddenFieldError):
        sanitizer.assert_clean(doc)
    # the input document is untouched
    assert doc == {"args": {"detail": "x"}}
