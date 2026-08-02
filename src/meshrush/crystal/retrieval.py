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

from meshrush.core.cairn import CairnLimits, CairnLine, EntityRef, bounded_frontier_step
from meshrush.crystal.symmetry import is_automorphism
from meshrush.omni.reduction import DiffusionMap


def artifact_entity_ref(artifact_id: str) -> EntityRef:
    """Canonical cairn identity for a compiled artifact (the findable address)."""
    return EntityRef(namespace="meshrush", kind="artifact", key=artifact_id)


def dedup_by_symmetry(artifacts, generators, node_order, graph, *, max_orbit: int = 256):
    """Collapse symmetry-equivalent artifacts to one orbit representative.

    Two artifacts whose node-sets map onto each other under the graph's automorphism
    group are the same finding up to symmetry; returning both is redundant. Each
    supplied generator is **verified to be a graph automorphism** (fail closed) via
    ``crystal.symmetry.is_automorphism``; artifacts are then keyed by the canonical
    (lexicographically minimal) member of their node-set orbit, keeping the
    highest-epistemic representative per orbit.
    """
    import numpy as np

    gens = [np.asarray(g, dtype=int) for g in generators]
    for g in gens:
        if not is_automorphism(graph, g):
            raise ValueError("symmetry generator is not a graph automorphism (fail closed)")

    index_of = {nid: i for i, nid in enumerate(node_order)}

    def orbit_key(node_ids) -> tuple:
        start = tuple(sorted(index_of[n] for n in node_ids if n in index_of))
        seen = {start}
        frontier = [start]
        while frontier and len(seen) < max_orbit:
            cur = frontier.pop()
            for g in gens:
                img = tuple(sorted(int(g[i]) for i in cur))
                if img not in seen:
                    seen.add(img)
                    frontier.append(img)
        return min(seen)

    best: dict[tuple, object] = {}
    for a in artifacts:
        k = orbit_key(a.node_ids)
        cur = best.get(k)
        if cur is None or a.epistemic.rank > cur.epistemic.rank:
            best[k] = a
    return list(best.values())


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
    entity_ref: str = ""               # canonical cairn address of the artifact


@dataclass(frozen=True)
class RefusedSlot:
    slot_name: str
    reason: str
    best_available_epistemic: EpistemicLevel | None = None


@dataclass
class SlotFillResult:
    fills: dict[str, Fill] = field(default_factory=dict)
    refused: list[RefusedSlot] = field(default_factory=list)
    cairnline: "CairnLine | None" = None   # the recorded retrieval walk (CP-02)

    @property
    def all_filled(self) -> bool:
        return not self.refused


class ArtifactSlotFiller:
    """Indexes compiled artifacts in diffusion-coordinate space and fills slots by
    nearest-artifact retrieval under an epistemic floor."""

    def __init__(
        self,
        dmap: DiffusionMap,
        artifacts: "list[dict] | list[IndexedArtifact]",
        *,
        symmetry_generators=None,
        symmetry_graph=None,
    ):
        self._coord = {nid: dmap.coordinates[i] for i, nid in enumerate(dmap.node_ids)}
        self._artifacts: list[IndexedArtifact] = []
        for a in artifacts:
            self._artifacts.append(a if isinstance(a, IndexedArtifact) else self._index_record(a))
        # Symmetry-aware retrieval: collapse artifacts equivalent under the graph's
        # automorphisms so a slot is not filled by redundant symmetric copies.
        if symmetry_generators is not None:
            if symmetry_graph is None:
                raise ValueError("symmetry_generators requires symmetry_graph")
            self._artifacts = dedup_by_symmetry(
                self._artifacts, symmetry_generators, tuple(dmap.node_ids), symmetry_graph
            )

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

    def fill(
        self,
        slots: "list[SlotSpec]",
        *,
        cap_k: int = 8,
        dataset_ref: str = "meshrush:diffusion",
        limits: "CairnLimits | None" = None,
    ) -> SlotFillResult:
        """Fill each slot as a **cairnpath step**: Expand candidates that clear the
        epistemic floor → Dedup by EntityRef → Rank by diffusion distance → Cap
        (``bounded_frontier_step``) → materialize the nearest. The whole walk is
        recorded as a ``CairnLine`` on the result. A slot with no qualifying
        artifact is refused (never back-filled)."""
        limits = limits or CairnLimits(max_hops=max(len(slots), 1), max_cap_k=max(cap_k, 1))
        line = CairnLine(line_id="slotfill", dataset_ref=dataset_ref, limits=limits)
        result = SlotFillResult(cairnline=line)

        for slot in slots:
            query = self._centroid(slot.anchor_nodes)
            if query is None:
                line.record_step("retrieve", [], cap_k=cap_k)
                result.refused.append(
                    RefusedSlot(slot.name, "anchor nodes not present in the diffusion map")
                )
                continue

            # Expand: candidate artifacts that clear the epistemic floor (+ track the
            # best epistemic seen, for an informative refusal).
            candidates: list[EntityRef] = []
            by_canon: dict[str, tuple[float, IndexedArtifact]] = {}
            best_epi: EpistemicLevel | None = None
            for a in self._artifacts:
                if best_epi is None or a.epistemic.rank > best_epi.rank:
                    best_epi = a.epistemic
                if a.epistemic.meets(slot.min_epistemic):
                    ref = artifact_entity_ref(a.artifact_id)
                    by_canon[ref.canonical] = (float(np.linalg.norm(a.centroid - query)), a)
                    candidates.append(ref)

            # Dedup -> Rank(distance) -> Cap : the CairnPath invariant step.
            frontier = bounded_frontier_step(
                candidates,
                rank_key=lambda r: by_canon[r.canonical][0],
                cap_k=cap_k,
                limits=limits,
            )
            if not frontier:
                line.record_step("retrieve", [], cap_k=cap_k)
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

            # Materialize the nearest cairn on the frontier.
            line.record_step("retrieve", frontier, cap_k=cap_k, materialized=True)
            winner_ref = frontier[0]
            dist, winner = by_canon[winner_ref.canonical]
            result.fills[slot.name] = Fill(
                slot_name=slot.name,
                artifact_id=winner.artifact_id,
                distance=dist,
                score=1.0 / (1.0 + dist),
                epistemic=winner.epistemic,
                node_ids=winner.node_ids,
                certificate_refs=winner.certificate_refs,
                entity_ref=winner_ref.canonical,
            )
        return result
