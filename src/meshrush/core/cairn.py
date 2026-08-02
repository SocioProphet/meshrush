"""CP-01 — CairnPath primitives (meshrush ADR 0006, folding in cairnpath-mesh).

Cairns are the findable marks, boundaries, and memorials a traversal is navigated
by. This module gives MeshRush the canonical CairnPath vocabulary:

- **EntityRef** — canonical `namespace:kind:key` identity (NFC-normalized). The
  keystone that makes things *findable* and dedup/ordering/replay possible
  (cairnpath-mesh `docs/identity.md`).
- **CairnLimits** — bounded-traversal policy caps (`max_hops`, `max_cap_k`,
  materialization budget). The *boundaries*; breaching them **fails closed**.
- **bounded_frontier_step** — the CairnPath invariant
  ``F[t+1] = TopK(Rank(Dedup(F[t])))`` (Expand is backend-specific and happens
  before this call). Deterministic: dedup by canonical, stable tie-break by canonical.
- **CairnStep / CairnLine** — the replayable, digestible record (the *memorials*).

Stdlib-only; keeps the base package dependency-free.
"""
from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass, field
from typing import Callable, Iterable


def _nfc(s: str) -> str:
    return unicodedata.normalize("NFC", s)


def canonical_hash(obj) -> str:
    """Deterministic content hash over canonical JSON (sorted keys, NFC strings)."""
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return "blake2b:" + hashlib.blake2b(_nfc(payload).encode("utf-8"), digest_size=16).hexdigest()


@dataclass(frozen=True)
class EntityRef:
    """Canonical identity of a frontier entity (cairnpath-mesh EntityRef v0)."""

    namespace: str
    kind: str
    key: str
    backend: str | None = None
    labels: tuple[str, ...] = ()

    @property
    def canonical(self) -> str:
        """NFC-normalized ``namespace:kind:key`` — the dedup/ordering/replay keystone."""
        return _nfc(f"{self.namespace}:{self.kind}:{self.key}")


@dataclass(frozen=True)
class CairnLimits:
    """Bounded-traversal policy caps (cairnpath-mesh `policy/cairn_limits.v0`)."""

    max_hops: int = 8
    max_cap_k: int = 64
    max_materialize_bytes: int = 1 << 20
    allowed_opcodes: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.max_hops < 1 or self.max_cap_k < 1 or self.max_materialize_bytes < 0:
            raise ValueError("CairnLimits: max_hops/max_cap_k must be >=1, bytes >=0")

    def check_opcode(self, opcode: str) -> None:
        if self.allowed_opcodes and opcode not in self.allowed_opcodes:
            raise ValueError(f"opcode {opcode!r} not in allowed_opcodes {self.allowed_opcodes}")


def bounded_frontier_step(
    candidates: Iterable[EntityRef],
    *,
    rank_key: Callable[[EntityRef], float],
    cap_k: int,
    limits: "CairnLimits | None" = None,
) -> list[EntityRef]:
    """One CairnPath step: ``TopK(Rank(Dedup(candidates)))``.

    Dedup is by canonical identity (first occurrence wins). Rank is ascending by
    ``rank_key`` (e.g. distance), with a **stable lexicographic tie-break on the
    canonical string** so the ordering is deterministic and replayable. Cap keeps
    at most ``cap_k`` — and **fails closed** if ``cap_k`` exceeds ``limits.max_cap_k``.
    """
    if cap_k < 1:
        raise ValueError("cap_k must be >= 1")
    if limits is not None and cap_k > limits.max_cap_k:
        raise ValueError(f"cap_k {cap_k} exceeds CairnLimits.max_cap_k {limits.max_cap_k}")

    seen: set[str] = set()
    deduped: list[EntityRef] = []
    for c in candidates:
        canon = c.canonical
        if canon not in seen:
            seen.add(canon)
            deduped.append(c)

    deduped.sort(key=lambda e: (rank_key(e), e.canonical))
    return deduped[:cap_k]


@dataclass(frozen=True)
class CairnStep:
    """One recorded step of a cairnpath (a memorial mark)."""

    index: int
    opcode: str
    frontier_out: tuple[str, ...]        # canonical ids after the step, in order
    cap_k: int
    rank_policy: str = "distance"
    materialized: bool = False

    @property
    def digest(self) -> str:
        return canonical_hash({
            "index": self.index,
            "opcode": self.opcode,
            "frontier_out": list(self.frontier_out),
            "cap_k": self.cap_k,
            "rank_policy": self.rank_policy,
            "materialized": self.materialized,
        })


@dataclass
class CairnLine:
    """An ordered, replayable sequence of steps over a stable dataset — a cairnpath."""

    line_id: str
    dataset_ref: str
    limits: CairnLimits = field(default_factory=CairnLimits)
    steps: list[CairnStep] = field(default_factory=list)

    def record_step(
        self,
        opcode: str,
        frontier: Iterable[EntityRef],
        *,
        cap_k: int,
        rank_policy: str = "distance",
        materialized: bool = False,
    ) -> CairnStep:
        """Append a step, enforcing CairnLimits (fail closed on every breach)."""
        self.limits.check_opcode(opcode)
        if cap_k < 1:
            raise ValueError("cap_k must be >= 1")
        if cap_k > self.limits.max_cap_k:
            raise ValueError(f"cap_k {cap_k} exceeds CairnLimits.max_cap_k {self.limits.max_cap_k}")
        if len(self.steps) >= self.limits.max_hops:
            raise ValueError(f"cairnline exceeds CairnLimits.max_hops {self.limits.max_hops}")
        frontier = list(frontier)
        if len(frontier) > cap_k:
            raise ValueError(
                f"frontier size {len(frontier)} exceeds cap_k {cap_k}; a step may not record more than it caps"
            )
        step = CairnStep(
            index=len(self.steps),
            opcode=opcode,
            frontier_out=tuple(e.canonical for e in frontier),
            cap_k=cap_k,
            rank_policy=rank_policy,
            materialized=materialized,
        )
        self.steps.append(step)
        return step

    @property
    def digest(self) -> str:
        """Content-based replay identity: hash over the dataset and the ordered step
        digests only. Deliberately excludes ``line_id`` (an external handle) so two
        byte-identical replays share a digest regardless of their label."""
        return canonical_hash({
            "dataset_ref": self.dataset_ref,
            "steps": [s.digest for s in self.steps],
        })
