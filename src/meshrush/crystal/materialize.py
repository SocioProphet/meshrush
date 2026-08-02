"""CP-03 — CairnPath materialization discipline (cairnpath-mesh materialization.md).

Traversal operates over light EntityRefs; expensive payloads are fetched only
through an explicit, **policy-governed**, **minimum-necessary** materialize step —
after frontier narrowing, never before. This module enforces that discipline as
world-class governed data egress:

- **Minimum-necessary:** only declared ``targets`` and (for ``properties``) declared
  ``projection`` fields are fetched.
- **Byte budget:** cumulative payload bytes are capped by the policy; the target
  that would breach the budget is **refused with a structured reason**, not
  silently dropped.
- **Namespace allow-list + mode allow-list:** a target outside the allowed
  namespaces, or a disallowed mode, is refused.
- **Redaction:** an optional redactor is applied to every granted payload
  (privacy), and applied redactions are recorded.
- **Fail closed:** a policy denial always surfaces as a recorded refusal — the
  caller can see exactly what was withheld and why.

Stdlib-only; consumes ``core.cairn.EntityRef``.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable

from meshrush.core.cairn import EntityRef


class MaterializeMode(str, Enum):
    METADATA_ONLY = "metadata_only"
    PROPERTIES = "properties"
    FULL_SUBGRAPH = "full_subgraph"
    PACKET = "packet"


@dataclass(frozen=True)
class MaterializePolicy:
    """The boundaries on materialization (a projection of CairnLimits + privacy)."""

    max_bytes: int = 1 << 20
    allowed_modes: tuple[MaterializeMode, ...] = tuple(MaterializeMode)
    allowed_namespaces: tuple[str, ...] = ()      # empty = any namespace
    privacy_mode: str = "restricted"              # public | restricted | private

    def __post_init__(self) -> None:
        if self.max_bytes < 0:
            raise ValueError("max_bytes must be >= 0")


@dataclass(frozen=True)
class MaterializeRequest:
    targets: tuple[EntityRef, ...]
    mode: MaterializeMode = MaterializeMode.METADATA_ONLY
    projection: tuple[str, ...] = ()              # fields for `properties` mode
    max_bytes: int | None = None                  # caller ceiling (min'd with policy)
    purpose: str = ""


@dataclass
class MaterializeResult:
    mode: MaterializeMode
    granted: dict[str, object] = field(default_factory=dict)   # canonical -> payload
    refused: list[tuple[str, str]] = field(default_factory=list)  # (canonical, reason)
    total_bytes: int = 0
    redactions: list[str] = field(default_factory=list)

    @property
    def fully_granted(self) -> bool:
        return not self.refused


# fetcher(target, mode, projection) -> payload (JSON-serializable)
Fetcher = Callable[[EntityRef, MaterializeMode, tuple], object]
Redactor = Callable[[EntityRef, object], "tuple[object, list[str]]"]


def _sizeof(payload: object) -> int:
    return len(json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def materialize(
    request: MaterializeRequest,
    policy: MaterializePolicy,
    fetcher: Fetcher,
    *,
    redactor: "Redactor | None" = None,
) -> MaterializeResult:
    """Materialize ``request.targets`` under ``policy``, minimum-necessary and fail-closed."""
    result = MaterializeResult(mode=request.mode)

    # Mode gate (fail closed): a disallowed mode refuses everything.
    if request.mode not in policy.allowed_modes:
        for t in request.targets:
            result.refused.append((t.canonical, f"mode {request.mode.value!r} not permitted by policy"))
        return result

    budget = policy.max_bytes if request.max_bytes is None else min(request.max_bytes, policy.max_bytes)

    for target in request.targets:
        # Namespace allow-list.
        if policy.allowed_namespaces and target.namespace not in policy.allowed_namespaces:
            result.refused.append((target.canonical, f"namespace {target.namespace!r} not in allow-list"))
            continue

        payload = fetcher(target, request.mode, request.projection)
        if redactor is not None:
            payload, applied = redactor(target, payload)
            result.redactions.extend(applied)

        size = _sizeof(payload)
        # Byte budget (fail closed): refuse the breaching target with a reason.
        if result.total_bytes + size > budget:
            result.refused.append((
                target.canonical,
                f"materialization budget exceeded (+{size}B would pass {budget}B); withheld, not dropped",
            ))
            continue

        result.total_bytes += size
        result.granted[target.canonical] = payload

    return result
