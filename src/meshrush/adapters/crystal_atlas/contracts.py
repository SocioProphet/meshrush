"""Project slot fills into a Crystal Atlas ``graph-upsert-request.v0`` envelope.

Each filled slot becomes: an artifact **node** (node_kind=evidence_bundle), an
**evidence** row (the retrieval act, carrying the artifact's certificate refs and
epistemic standing), and a **claim** (``slot --filled_by--> artifact``) whose
confidence is the retrieval score. Refused slots produce no claim — the refusal is
surfaced to the caller, not written as a silent low-confidence assertion.

Field names match ``prophet-platform/contracts/crystal-atlas/schemas/*`` exactly.
"""
from __future__ import annotations

from meshrush.crystal.retrieval import SlotFillResult

_DISTRIBUTION = "internal_private"


def fills_to_graph_upsert(
    result: SlotFillResult,
    tenant_id: str,
    *,
    timestamp: str,
    distribution_class: str = _DISTRIBUTION,
) -> dict:
    """Build a graph-upsert-request.v0 dict from a SlotFillResult."""
    nodes: list[dict] = []
    claims: list[dict] = []
    evidence: list[dict] = []

    for slot_name, fill in sorted(result.fills.items()):
        node_id = f"meshrush-artifact:{fill.artifact_id}"
        evidence_id = f"meshrush-ev:{slot_name}:{fill.artifact_id}"

        nodes.append({
            "node_id": node_id,
            "tenant_id": tenant_id,
            "node_kind": "evidence_bundle",
            "display_name": f"MeshRush artifact {fill.artifact_id}",
            "aliases": [],
            "attributes": {
                "epistemic_level": fill.epistemic.value,
                "included_node_ids": list(fill.node_ids),
                "certificate_refs": list(fill.certificate_refs),
                "producer": "meshrush.crystal.retrieval",
            },
            "distribution_class": distribution_class,
            "created_at": timestamp,
            "updated_at": timestamp,
        })
        evidence.append({
            "evidence_id": evidence_id,
            "tenant_id": tenant_id,
            "source_ref": node_id,
            "anchor_ref": ",".join(fill.node_ids),
            "observed_at": timestamp,
            "ingested_at": timestamp,
            "extractor_ref": "meshrush.crystal.retrieval",
            "provider_ref": "meshrush",
            "confidence": round(fill.score, 6),
            "distribution_class": distribution_class,
            "receipt_ref": "",
        })
        claims.append({
            "claim_id": f"meshrush-claim:{slot_name}:{fill.artifact_id}",
            "tenant_id": tenant_id,
            "subject_ref": f"slot:{slot_name}",
            "predicate": "filled_by",
            "object_ref": node_id,
            "value": fill.epistemic.value,
            "confidence": round(fill.score, 6),
            "evidence_refs": [evidence_id],
            "distribution_class": distribution_class,
            "created_at": timestamp,
        })

    return {
        "tenant_id": tenant_id,
        "nodes": nodes,
        "edges": [],
        "claims": claims,
        "evidence": evidence,
    }
