"""Emit MeshRush signals as global-devsecops-intelligence (GDI) AI4IT events (GDI-1).

MeshRush is a signal *source* for GDI, the estate's ops-intelligence normalizer /
query plane. Its operational exhaust — cairnpath walks (retrieval/exploration
traces) and slot-fill results (with epistemic level + refusals) — is serialized
here into GDI's normative ``event-envelope`` so GDI can normalize, correlate, and
make it queryable. Events validate against the vendored GDI schema (conformance
gate); this module performs no transport (the mesh producer is the caller's).

Event types (lowercase snake_case, per the envelope):
- ``meshrush_cairnpath_walk`` — a bounded-frontier retrieval/exploration walk.
- ``meshrush_slot_fill``     — a slot-filling result, carrying epistemic level and
  refusals (a first-class governance signal: what was retrieved, and what was refused).

Stdlib-only.
"""
from __future__ import annotations

import datetime
import re

from meshrush.core.cairn import CairnLine
from meshrush.crystal.retrieval import SlotFillResult

_TYPE_RE = re.compile(r"^[a-z0-9_]+$")


def now_event_fields() -> "tuple[int, str]":
    """Return ``(timestamp_ms, utc_timestamp)`` for 'now' (UTC), envelope-shaped."""
    dt = datetime.datetime.now(datetime.timezone.utc)
    ms = int(dt.timestamp() * 1000)
    return ms, dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"


def make_event(
    type: str,
    data: dict,
    *,
    timestamp_ms: int,
    utc_timestamp: str,
    story_id: str | None = None,
    data_name: str | None = None,
) -> dict:
    """Build a GDI AI4IT event-envelope. Fail closed on a non-conforming ``type``."""
    if not _TYPE_RE.fullmatch(type):
        raise ValueError(f"event type must match ^[a-z0-9_]+$, got {type!r}")
    if not isinstance(timestamp_ms, int):
        raise ValueError("timestamp_ms must be an int (POSIX ms)")
    event: dict = {"timestamp": timestamp_ms, "utc_timestamp": utc_timestamp, "type": type, "data": data}
    if story_id is not None:
        event["story_id"] = story_id
    if data_name is not None:
        event["data_name"] = data_name
    return event


def cairnline_to_event(line: CairnLine, *, timestamp_ms: int, utc_timestamp: str, story_id: str | None = None) -> dict:
    """A ``meshrush_cairnpath_walk`` GDI event for a completed cairn walk."""
    data = {
        "line_id": line.line_id,
        "dataset_ref": line.dataset_ref,
        "digest": line.digest,
        "n_steps": len(line.steps),
        "opcodes": [s.opcode for s in line.steps],
        "materialized_steps": sum(1 for s in line.steps if s.materialized),
    }
    return make_event(
        "meshrush_cairnpath_walk", data,
        timestamp_ms=timestamp_ms, utc_timestamp=utc_timestamp,
        story_id=story_id, data_name="cairnpath_walk",
    )


def slot_fill_to_event(result: SlotFillResult, *, timestamp_ms: int, utc_timestamp: str, story_id: str | None = None) -> dict:
    """A ``meshrush_slot_fill`` GDI event — carries epistemic level and refusals so
    the governance signal (what was refused, and why) reaches the ops-intel plane."""
    data = {
        "n_filled": len(result.fills),
        "n_refused": len(result.refused),
        "fills": [
            {
                "slot": f.slot_name,
                "artifact_id": f.artifact_id,
                "entity_ref": f.entity_ref,
                "epistemic": f.epistemic.value,
                "score": round(f.score, 6),
            }
            for f in result.fills.values()
        ],
        "refused": [
            {
                "slot": r.slot_name,
                "reason": r.reason,
                "best_available_epistemic": (
                    r.best_available_epistemic.value if r.best_available_epistemic else None
                ),
            }
            for r in result.refused
        ],
    }
    return make_event(
        "meshrush_slot_fill", data,
        timestamp_ms=timestamp_ms, utc_timestamp=utc_timestamp,
        story_id=story_id, data_name="slot_fill",
    )
