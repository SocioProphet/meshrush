#!/usr/bin/env python3
"""Validate MeshRush crystallization fixtures with dependency-light checks.

This validator intentionally checks the structural invariants MeshRush needs
before a full schema package exists.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = [
    ROOT / "fixtures/graph-views/soil-intelligence-crystallization.sample.v1.json",
]
REQUIRED = [
    "artifact_version",
    "artifact_type",
    "artifact_id",
    "graph_view_id",
    "entry_node_refs",
    "traversed_node_refs",
    "traversed_edge_refs",
    "diffusion",
    "stop_condition",
    "crystallized_claims",
    "policy_refs",
    "recommended_next_action",
    "provenance",
    "classification",
]


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def load_json(path: Path) -> Dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except FileNotFoundError:
        fail(f"missing fixture: {path}")
    except json.JSONDecodeError as exc:
        fail(f"invalid JSON in {path}: {exc}")
    if not isinstance(value, dict):
        fail(f"expected object at top level: {path}")
    return value


def require_fields(doc: Dict[str, Any], fields: Iterable[str], path: Path) -> None:
    missing = [field for field in fields if field not in doc]
    if missing:
        fail(f"{path} missing required fields: {', '.join(missing)}")


def require_nonempty_array(doc: Dict[str, Any], field: str, path: Path) -> None:
    value = doc.get(field)
    if not isinstance(value, list) or not value:
        fail(f"{path} field {field} must be a non-empty array")


def main() -> int:
    checked = 0
    for fixture in FIXTURES:
        doc = load_json(fixture)
        require_fields(doc, REQUIRED, fixture)
        if doc.get("artifact_version") != "v1":
            fail(f"{fixture} artifact_version must be v1")
        if doc.get("artifact_type") != "meshrush.crystallized_graph_artifact":
            fail(f"{fixture} has unexpected artifact_type")
        for field in ["entry_node_refs", "traversed_node_refs", "traversed_edge_refs", "crystallized_claims", "policy_refs"]:
            require_nonempty_array(doc, field, fixture)
        stop_condition = doc.get("stop_condition")
        if not isinstance(stop_condition, dict) or stop_condition.get("satisfied") is not True:
            fail(f"{fixture} stop_condition.satisfied must be true")
        action = doc.get("recommended_next_action")
        if not isinstance(action, dict) or "action_boundary" not in action:
            fail(f"{fixture} recommended_next_action.action_boundary is required")
        checked += 1
    print(f"validated {checked} MeshRush crystallization fixture(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
