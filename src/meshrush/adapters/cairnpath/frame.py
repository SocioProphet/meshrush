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

import hashlib
import json

from meshrush.core.cairn import CairnLine

_OPCODE_MAP = {"retrieve": "cap"}

# cairn/context.v0 engine enum (kept in sync with the vendored schema).
_CONTEXT_ENGINES = ("neo4j", "atomspace", "terminusdb", "rdf", "custom")


def _ctx(line_id: str, i: int) -> str:
    return f"ctx:{line_id}:{i}"


def _dedup_set_hash(canonicals: "list[str]") -> str:
    """sha256 (64 hex, matching context.v0's pattern) over the deduped, sorted set —
    the frontier's content identity, independent of insertion order."""
    payload = json.dumps(sorted(set(canonicals)), ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cairnline_to_context(
    line: CairnLine,
    *,
    seed_entities: "list[str] | tuple[str, ...]",
    created_at: str,
    engine: str = "custom",
    engine_ref: "str | None" = None,
    allowed_namespaces: "tuple[str, ...]" = (),
    privacy_mode: "str | None" = None,
) -> dict:
    """Emit a normative ``cairn/context.v0`` frame for ``line``'s root traversal context.

    The context binds the walk to its dataset, entry seeds, bounded frontier, and the
    CairnLimits constraints — the governed setup a CairnPath backend replays under.
    ``seed_entities`` are canonical entity ids (>=1 required); ``created_at`` is an
    RFC3339 date-time. Fails closed on an unknown ``engine``.
    """
    seeds = list(seed_entities)
    if not seeds:
        raise ValueError("cairn context requires at least one seed entity")
    if engine not in _CONTEXT_ENGINES:
        raise ValueError(f"engine {engine!r} not in {_CONTEXT_ENGINES}")

    frontier = {
        "ordered": seeds,
        "dedup_set_hash": _dedup_set_hash(seeds),
        "cap_k": line.limits.max_cap_k,
        "dedup_strategy": "canonical_equivalence",  # dedup by canonical EntityRef
        "stable_order": "rank_then_lex",            # bounded_frontier_step ordering
    }
    constraints: dict = {
        "max_hops": line.limits.max_hops,
        "max_materialize_bytes": line.limits.max_materialize_bytes,
    }
    if allowed_namespaces:
        constraints["allowed_namespaces"] = list(allowed_namespaces)
    if privacy_mode is not None:
        constraints["privacy_mode"] = privacy_mode

    context = {
        "context_id": _ctx(line.line_id, 0),   # the root context the line references
        "engine": engine,
        "dataset_ref": line.dataset_ref,
        "seed_entities": seeds,
        "frontier": frontier,
        "constraints": constraints,
        "created_at": created_at,
    }
    if engine_ref is not None:
        context["engine_ref"] = engine_ref
    return context


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
        # Fail closed: only opcodes with a known, arg-correct normative mapping are
        # emitted. step.v0 constrains args per opcode (additionalProperties:false),
        # so emitting a generic {cap_k} for an unmapped opcode would produce a
        # non-conforming frame. Refuse rather than emit something invalid.
        if ms.opcode not in _OPCODE_MAP:
            raise ValueError(
                f"unsupported cairn opcode {ms.opcode!r} for normative frame emission; "
                f"mapped opcodes: {sorted(_OPCODE_MAP)} (extend the mapping before recording others)"
            )
        fanout = len(ms.frontier_out)
        cap_hit = fanout >= ms.cap_k
        push("cap", {"cap_k": ms.cap_k}, fanout, cap_hit, None)
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
