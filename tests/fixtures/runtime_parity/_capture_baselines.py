# QUARANTINED-BY-C-006: dev-only / migration-support utility.
# This file is NOT a production code path. It exists to regenerate the
# golden parity baselines from the upstream `spec_kitty_runtime` source
# tree during the WP01 internalization of mission
# `shared-package-boundary-cutover-01KQ22DS`. C-006 forbids editable / path /
# git overrides on production paths; this script is the documented
# exception and must never be invoked by runtime code.
"""Capture golden parity baselines for the internalized runtime.

This script is intended to run against the upstream ``spec_kitty_runtime``
0.4.x source tree (or installed package) to generate the reference JSON
snapshots that the WP01 parity tests compare against. It must be deterministic:
running it twice on the same upstream commit must produce zero diff.

Usage (from repo root, with the upstream runtime importable):

    PYTHONPATH=src:.../spec-kitty-runtime/src python3 \
        tests/fixtures/runtime_parity/_capture_baselines.py

The script also accepts a ``--target internal`` flag to capture against the
internalized runtime ``specify_cli.next._internal_runtime``. The parity test
uses ``--target internal`` semantics in-process and compares the result to
the committed ``--target upstream`` baselines.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
from pathlib import Path
from typing import Any
from collections.abc import Callable

FIXTURE_DIR = Path(__file__).resolve().parent
REFERENCE_MISSION_DIR = FIXTURE_DIR / "reference_mission"


def _normalize(value: Any, run_dir_str: str) -> Any:
    """Recursively normalize timestamps, paths, and run_ids for byte-equal comparison."""
    if isinstance(value, dict):
        return {k: _normalize(v, run_dir_str) for k, v in value.items()}
    if isinstance(value, list):
        return [_normalize(v, run_dir_str) for v in value]
    if isinstance(value, str):
        result = value
        # Normalize the run-store directory path (varies per run / per machine).
        if run_dir_str and run_dir_str in result:
            result = result.replace(run_dir_str, "<RUN_DIR>")
        # Normalize ISO-ish timestamps.
        result = re.sub(
            r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?",
            "<TIMESTAMP>",
            result,
        )
        # Normalize 32-char hex run ids (uuid4 hex).
        result = re.sub(r"\b[0-9a-f]{32}\b", "<RUN_ID>", result)
        # Normalize SHA-256 (64-char hex) hashes.
        result = re.sub(r"\b[0-9a-f]{64}\b", "<SHA256>", result)
        return result
    return value


def _to_jsonable(obj: Any) -> Any:
    """Convert pydantic / dataclass-ish objects to plain JSON-serializable structures."""
    if hasattr(obj, "model_dump"):
        return obj.model_dump(mode="json")
    if hasattr(obj, "__dict__"):
        return {k: _to_jsonable(v) for k, v in vars(obj).items() if not k.startswith("_")}
    return obj


def _resolve_runtime(target: str) -> dict[str, Callable[..., Any] | type]:
    """Return the runtime symbols to call for the given target."""
    if target == "upstream":
        from spec_kitty_runtime import (  # type: ignore[import-not-found]
            DiscoveryContext,
            MissionPolicySnapshot,
            NullEmitter,
            next_step,
            provide_decision_answer,
            start_mission_run,
        )
        from spec_kitty_runtime.schema import ActorIdentity  # type: ignore[import-not-found]
    elif target == "internal":
        from specify_cli.next._internal_runtime import (
            DiscoveryContext,
            MissionPolicySnapshot,
            NullEmitter,
            next_step,
            provide_decision_answer,
            start_mission_run,
        )
        from specify_cli.next._internal_runtime.schema import ActorIdentity
    else:  # pragma: no cover
        raise ValueError(f"Unknown target: {target}")

    return {
        "DiscoveryContext": DiscoveryContext,
        "MissionPolicySnapshot": MissionPolicySnapshot,
        "NullEmitter": NullEmitter,
        "next_step": next_step,
        "provide_decision_answer": provide_decision_answer,
        "start_mission_run": start_mission_run,
        "ActorIdentity": ActorIdentity,
    }


def capture(target: str, out_dir: Path) -> dict[str, dict[str, Any]]:
    """Capture parity scenarios against the requested runtime target.

    The mission template requires an input ``topic``; we drive the runtime
    through:
      1. start_mission_run()                        → MissionRunRef
      2. next_step()                                → decision_required (input:topic)
      3. provide_decision_answer()                  → completes input
      4. next_step()                                → step decision (discovery)
    """
    runtime = _resolve_runtime(target)

    with tempfile.TemporaryDirectory(prefix="parity-baseline-") as tmp:
        run_store = Path(tmp) / "runs"
        context = runtime["DiscoveryContext"](
            project_dir=REFERENCE_MISSION_DIR,
            builtin_roots=[REFERENCE_MISSION_DIR],
        )

        run_ref = runtime["start_mission_run"](
            template_key=str(REFERENCE_MISSION_DIR / "mission.yaml"),
            inputs={},
            policy_snapshot=runtime["MissionPolicySnapshot"](),
            context=context,
            run_store=run_store,
            emitter=runtime["NullEmitter"](),
        )
        run_dir_str = str(run_ref.run_dir)

        snap_start = _to_jsonable(run_ref)

        decision_1 = runtime["next_step"](
            run_ref,
            agent_id="parity-agent",
            result="success",
            emitter=runtime["NullEmitter"](),
        )
        snap_next_1 = _to_jsonable(decision_1)

        # The first next_step should produce a decision_required for the
        # missing required input "topic". Answer it.
        actor = runtime["ActorIdentity"](actor_id="parity-actor", actor_type="human")
        runtime["provide_decision_answer"](
            run_ref,
            decision_1.decision_id,
            "parity-topic",
            actor,
            emitter=runtime["NullEmitter"](),
        )
        snap_provide = {
            "decision_id": decision_1.decision_id,
            "answer": "parity-topic",
            "actor_type": actor.actor_type,
        }

        decision_2 = runtime["next_step"](
            run_ref,
            agent_id="parity-agent",
            result="success",
            emitter=runtime["NullEmitter"](),
        )
        snap_next_2 = _to_jsonable(decision_2)

    snapshots = {
        "snapshot_start_mission_run.json": _normalize(snap_start, run_dir_str),
        "snapshot_next_step_1.json": _normalize(snap_next_1, run_dir_str),
        "snapshot_provide_decision_answer.json": _normalize(snap_provide, run_dir_str),
        "snapshot_next_step_2.json": _normalize(snap_next_2, run_dir_str),
    }

    if out_dir is not None:
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, payload in snapshots.items():
            (out_dir / name).write_text(
                json.dumps(payload, sort_keys=True, indent=2) + "\n",
                encoding="utf-8",
            )

    return snapshots


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--target",
        choices=["upstream", "internal"],
        default="upstream",
        help="Which runtime to invoke (default: upstream).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=FIXTURE_DIR,
        help="Where to write snapshot_*.json files (default: fixture dir).",
    )
    args = parser.parse_args(argv)

    capture(args.target, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
