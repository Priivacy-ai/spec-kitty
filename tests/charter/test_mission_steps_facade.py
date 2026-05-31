"""Tests for the charter mission-step-contract facade."""

from __future__ import annotations

import importlib

import pytest


pytestmark = pytest.mark.fast


def test_mission_steps_facade_reexports_step_inputs() -> None:
    """The charter facade exposes the doctrine input model by identity."""
    from doctrine.mission_step_contracts.models import MissionStepInput

    facade = importlib.reload(importlib.import_module("charter.mission_steps"))

    assert facade.MissionStepInput is MissionStepInput
