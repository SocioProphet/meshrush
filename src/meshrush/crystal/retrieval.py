"""Slot-filling agentic IR over compiled MeshRush artifacts.

The connective tissue that lets Crystal Atlas and the Competitive-Intelligence
services (Sherlock/Holmes) consume MeshRush's crystallized knowledge. An
information need is decomposed into **slots**; each slot is filled by retrieving
the nearest compiled artifact in **diffusion-coordinate space** (MR-01), gated by
the slot's required epistemic floor.

The governing discipline (inherited from ECO-1 / sp-core): **a slot that cannot
be filled at or above its epistemic floor is REFUSED, never back-filled with a
weaker artifact.** Retrieval that cannot meet the bar returns the gap, not a
confident-looking wrong answer.

`EpistemicLevel` is the canonical estate lattice — the same six levels used by
`sp-core` and by memory-mesh's `gateway-call-audit` enum — so fills stamp a label
Sherlock, Holmes, and Crystal Atlas already understand.

Requires the ``scientific`` extra (``numpy``); consumes ``omni.reduction`` coordinates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from meshrush.omni.reduction import DiffusionMap


class EpistemicLevel(str, Enum):
    """Canonical estate epistemic lattice (proved highest, rejected lowest)."""

    REJECTED = "rejected"
    SPECULATIVE = "speculative"
    SYNTHETIC = "synthetic"
    EMPIRICAL = "empirical"
    BOUNDED = "bounded"
    PROVED = "proved"

    @property
    def rank(self) -> int:
        return _RANK[self]

    def meets(self, floor: "EpistemicLevel") -> bool:
        return self.rank >= floor.rank


_RANK = {
    EpistemicLevel.REJECTED: 0,
    EpistemicLevel.SPECULATIVE: 1,
    EpistemicLevel.SYNTHETIC: 2,
    EpistemicLevel.EMPIRICAL: 3,
    EpistemicLevel.BOUNDED: 4,
    EpistemicLevel.PROVED: 5,
}


def artifact_epistemic(record: dict) -> EpistemicLevel:
    """Derive an artifact's epistemic standing from its serialized compile record.

    A gate-passing artifact with a certificate is `bounded` at best (a compiled
    artifact is never a proof); accepted-without-certificate is `empirical`;
    deferred is `synthetic`; rejected is `rejected`; anything else is `speculative`.
    """
    compile_block = record.get("compile", {})
    outcome = str(compile_block.get("outcome", "")).upper()
    has_cert = bool(compile_block.get("certificate_refs"))
    if outcome in ("ACCEPT", "ACCEPTED"):
        return EpistemicLevel.BOUNDED if has_cert else EpistemicLevel.EMPIRICAL
    if outcome in ("DEFER", "DEFERRED"):
        return EpistemicLevel.SYNTHETIC
    if outcome in ("REJECT", "REJECTED"):
        return EpistemicLevel.REJECTED
    return EpistemicLevel.SPECULATIVE


@dataclass(frozen=True)
class SlotSpec:
    """One slot to fill. ``anchor_nodes`` locate the query in the graph; a fill must
    clear ``min_epistemic`` or the slot is refused."""

    name: str
    anchor_nodes: tuple[str, ...]
    description: str = ""
    min_epistemic: EpistemicLevel = EpistemicLevel.SPECULATIVE
    modal_class: str | None = None


@dataclass(frozen=True)
class IndexedArtifact:
    artifact_id: str
    node_ids: tuple[str, ...]
    centroid: np.ndarray
    epistemic: EpistemicLevel
    certificate_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Fill:
    slot_name: str
    artifact_id: str
    distance: float
    score: float                       # 1/(1+distance); higher = closer
    epistemic: EpistemicLevel
    node_ids: tuple[str, ...]
    certificate_refs: tuple[str, ...]


@dataclass(frozen=True)
class RefusedSlot:
    slot_name: str
    reason: str
    best_available_epistemic: EpistemicLevel | None = None


@dataclass
class SlotFillResult:
    fills: dict[str, Fill] = field(default_factory=dict)
    refused: list[RefusedSlot] = field(default_factory=list)

    @property
    def all_filled(self) -> bool:
        return not self.refused


class ArtifactSlotFiller:
    """Indexes compiled artifacts in diffusion-coordinate space and fills slots by
    nearest-artifact retrieval under an epistemic floor."""

    def __init__(self, dmap: DiffusionMap, artifacts: "list[dict] | list[IndexedArtifact]"):
        self._coord = {nid: dmap.coordinates[i] for i, nid in enumerate(dmap.node_ids)}
        self._artifacts: list[IndexedArtifact] = []
        for a in artifacts:
            self._artifacts.append(a if isinstance(a, IndexedArtifact) else self._index_record(a))

    def _centroid(self, node_ids) -> "np.ndarray | None":
        pts = [self._coord[n] for n in node_ids if n in self._coord]
        if not pts:
            return None
        return np.mean(np.vstack(pts), axis=0)

    def _index_record(self, record: dict) -> IndexedArtifact:
        art = record.get("artifact", {})
        boundary = art.get("boundary", {})
        node_ids = tuple(boundary.get("included_node_ids", ()))
        # Fail fast: every included node must be in the diffusion map. A partial
        # miss would silently shift the centroid and later emit phantom node IDs
        # into Crystal Atlas / Sherlock payloads.
        missing = [n for n in node_ids if n not in self._coord]
        if not node_ids or missing:
            raise ValueError(
                f"artifact {art.get('artifact_id')!r}: included nodes not in diffusion map: "
                f"{missing or 'none provided'}"
            )
        centroid = self._centroid(node_ids)
        cert_refs = tuple(
            eid
            for c in record.get("compile", {}).get("certificate_refs", [])
            if (eid := c.get("evidence_id"))
        )
        return IndexedArtifact(
            artifact_id=str(art.get("artifact_id", "")),
            node_ids=node_ids,
            centroid=centroid,
            epistemic=artifact_epistemic(record),
            certificate_refs=cert_refs,
        )

    def fill(self, slots: "list[SlotSpec]") -> SlotFillResult:
        result = SlotFillResult()
        for slot in slots:
            query = self._centroid(slot.anchor_nodes)
            if query is None:
                result.refused.append(
                    RefusedSlot(slot.name, "anchor nodes not present in the diffusion map")
                )
                continue
            # Single pass: track the nearest artifact that clears the floor, and the
            # best epistemic seen overall (for an informative refusal). No sort.
            best: "tuple[float, IndexedArtifact] | None" = None
            best_epi: EpistemicLevel | None = None
            for a in self._artifacts:
                if best_epi is None or a.epistemic.rank > best_epi.rank:
                    best_epi = a.epistemic
                if a.epistemic.meets(slot.min_epistemic):
                    dist = float(np.linalg.norm(a.centroid - query))
                    if best is None or dist < best[0]:
                        best = (dist, a)
            if best is None:
                result.refused.append(
                    RefusedSlot(
                        slot.name,
                        reason=(
                            f"no artifact meets epistemic floor {slot.min_epistemic.value!r}; "
                            "refused rather than back-filled with a weaker artifact"
                        ),
                        best_available_epistemic=best_epi,
                    )
                )
                continue
            dist, winner = best
            result.fills[slot.name] = Fill(
                slot_name=slot.name,
                artifact_id=winner.artifact_id,
                distance=dist,
                score=1.0 / (1.0 + dist),
                epistemic=winner.epistemic,
                node_ids=winner.node_ids,
                certificate_refs=winner.certificate_refs,
            )
        return result
