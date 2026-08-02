"""Serialize a MeshRush ``CairnLine`` into normative cairnpath-mesh frames (CP-04).

MeshRush is the CairnPath runtime; cairnpath-mesh is the normative schema home
(ADR 0006). This adapter emits ``cairn/line.v0`` + ``cairn/step.v0`` frames so a
MeshRush walk can be validated against the vendored normative schemas (the
conformance gate) and transported to any CairnPath-speaking backend.

A MeshRush ``retrieve`` step is the compound "bounded-frontier narrow + fetch"; it
maps to a normative ``cap`` step (the TopK bound) followed, when the winner was
materialized, by a ``materialize`` step (minimum-necessary, metadata_only).
"""
from __future__ import annotations

from meshrush.core.cairn import CairnLine

_OPCODE_MAP = {"retrieve": "cap"}


def _ctx(line_id: str, i: int) -> str:
    return f"ctx:{line_id}:{i}"


def cairnline_to_frames(line: CairnLine, *, created_at: str, status: str = "complete") -> dict:
    """Return ``{"line": <line.v0>, "steps": [<step.v0>, ...]}`` for ``line``.

    ``created_at`` must be an RFC3339/ISO-8601 date-time (both schemas require it).
    """
    line_id = line.line_id
    steps: list[dict] = []
    ctx_i = 0

    def push(opcode: str, args: dict, fanout: int, cap_hit: bool, materialized_bytes: int | None):
        nonlocal ctx_i
        metrics = {
            "fanout": fanout,
            "dedup_ratio": 0.0,
            "cap_hit": cap_hit,
            "elapsed_ms": 0,
        }
        if materialized_bytes is not None:
            metrics["materialized_bytes"] = materialized_bytes
        step = {
            "step_id": f"{line_id}:{len(steps)}",
            "line_id": line_id,
            "index": len(steps),
            "opcode": opcode,
            "args": args,
            "in_context_id": _ctx(line_id, ctx_i),
            "out_context_id": _ctx(line_id, ctx_i + 1),
            "metrics": metrics,
            "created_at": created_at,
        }
        ctx_i += 1
        steps.append(step)

    for ms in line.steps:
        opcode = _OPCODE_MAP.get(ms.opcode, ms.opcode)
        fanout = len(ms.frontier_out)
        cap_hit = fanout >= ms.cap_k
        if opcode == "cap":
            push("cap", {"cap_k": ms.cap_k}, fanout, cap_hit, None)
        else:  # pass-through for already-normative opcodes carrying a cap
            push(opcode, {"cap_k": ms.cap_k}, fanout, cap_hit, None)
        if ms.materialized and ms.frontier_out:
            push(
                "materialize",
                {
                    "mode": "metadata_only",
                    "targets": list(ms.frontier_out),
                    "max_bytes": line.limits.max_materialize_bytes,
                },
                fanout=len(ms.frontier_out),
                cap_hit=False,
                materialized_bytes=0,
            )

    line_frame = {
        "line_id": line_id,
        "root_context_id": _ctx(line_id, 0),
        "steps": [s["step_id"] for s in steps],
        "status": status,
        "created_at": created_at,
        "updated_at": created_at,
    }
    return {"line": line_frame, "steps": steps}
