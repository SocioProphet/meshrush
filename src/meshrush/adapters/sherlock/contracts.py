"""Render a SlotFillResult as a Sherlock **evidence-answer contract**.

Each filled slot becomes an ``anchor`` (the artifact), an ``evidence`` row (the
retrieval, scored), and a ``proposedClaim`` (with ``confidenceBounds`` derived
from the fill's epistemic level). Crucially, **each refused slot becomes a
proposedClaim with status ``abstained``** — the refusal is carried into the CI
answer as first-class content, not dropped, so Holmes/Policy see the gap.

Shapes match sherlock-search `docs/evidence-answer-contract.md` field names.
"""
from __future__ import annotations

from meshrush.crystal.retrieval import EpistemicLevel, SlotFillResult

_BOUNDS = {
    EpistemicLevel.PROVED: (0.99, 1.0),
    EpistemicLevel.BOUNDED: (0.75, 0.95),
    EpistemicLevel.EMPIRICAL: (0.5, 0.8),
    EpistemicLevel.SYNTHETIC: (0.25, 0.55),
    EpistemicLevel.SPECULATIVE: (0.05, 0.3),
    EpistemicLevel.REJECTED: (0.0, 0.05),
}


def fills_to_evidence_answer(result: SlotFillResult, query_text: str, *, trace_id: str) -> dict:
    """Build a Sherlock evidence-answer contract dict from a SlotFillResult."""
    anchors: list[dict] = []
    evidence: list[dict] = []
    proposed_claims: list[dict] = []

    for slot_name, fill in sorted(result.fills.items()):
        anchor_id = f"anchor:{slot_name}:{fill.artifact_id}"
        evidence_id = f"evidence:{slot_name}:{fill.artifact_id}"
        lo, hi = _BOUNDS[fill.epistemic]
        anchors.append({
            "anchorId": anchor_id,
            "sourceRef": f"meshrush-artifact:{fill.artifact_id}",
            "kind": "meshrush_artifact",
            "locators": list(fill.node_ids),
        })
        evidence.append({
            "evidenceId": evidence_id,
            "anchorRefs": [anchor_id],
            "stance": "supports",
            "freshness": "current",
            "score": round(fill.score, 6),
            "snippet": f"artifact {fill.artifact_id} over nodes {list(fill.node_ids)}",
        })
        proposed_claims.append({
            "claimId": f"claim:{slot_name}",
            "text": f"slot {slot_name!r} filled by artifact {fill.artifact_id}",
            "status": "proposed",
            "evidenceRefs": [evidence_id],
            "confidenceBounds": {"lower": lo, "upper": hi},
            "epistemicLevel": fill.epistemic.value,
        })

    for refusal in result.refused:
        best = refusal.best_available_epistemic.value if refusal.best_available_epistemic else None
        proposed_claims.append({
            "claimId": f"claim:{refusal.slot_name}",
            "text": f"slot {refusal.slot_name!r} refused: {refusal.reason}",
            "status": "abstained",
            "evidenceRefs": [],
            "confidenceBounds": {"lower": 0.0, "upper": 0.0},
            "epistemicLevel": best,
        })

    return {
        "query": {"text": query_text, "entityCandidates": [], "relationCandidates": []},
        "anchors": anchors,
        "evidence": evidence,
        "proposedClaims": proposed_claims,
        "explanationTrace": {
            "traceId": trace_id,
            "status": "complete",
            "summary": f"{len(result.fills)} slot(s) filled, {len(result.refused)} refused",
        },
        "policyDecision": {
            "decisionId": f"policy:{trace_id}",
            "status": "pending",
            "summary": "policy evaluation deferred to Policy Fabric",
        },
    }
