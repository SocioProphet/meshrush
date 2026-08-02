"""Prime slot-filling retrieval with memory-mesh recall (per-slot prior context).

Before dispatching diffusion retrieval for a slot, MeshRush can ask memory-mesh's
``memoryd POST /v1/recall`` for prior, scope-governed context — so a slot is filled
against what the estate already remembers, not from scratch. This adapter builds a
conformant ``RecallRequest`` per slot and folds a ``RecallResponse`` back into the
slot's anchor set. It performs no network I/O (transport belongs to the caller);
it is the contract boundary, matching memory-mesh ``services/memoryd/app/models.py``.
"""
from __future__ import annotations

from meshrush.crystal.retrieval import SlotSpec

_DEFAULT_SCOPE_ORDER = ("run", "agent", "user")


def scope_envelope(
    *,
    user_id: str | None = None,
    agent_id: str | None = None,
    run_id: str | None = None,
    workspace_id: str | None = None,
    channel: str | None = None,
    thread_id: str | None = None,
    source_interface: str = "meshrush",
) -> dict:
    """A memory-mesh ScopeEnvelope (only non-null fields are emitted)."""
    env = {"source_interface": source_interface}
    for k, v in (
        ("user_id", user_id), ("agent_id", agent_id), ("run_id", run_id),
        ("workspace_id", workspace_id), ("channel", channel), ("thread_id", thread_id),
    ):
        if v is not None:
            env[k] = v
    return env


def build_recall_request(slot: SlotSpec, *, envelope: dict, top_k: int = 5) -> dict:
    """A memory-mesh ``RecallRequest`` for ``slot`` (POST /v1/recall body)."""
    if top_k < 1:
        raise ValueError("top_k must be >= 1")
    return {
        "envelope": envelope,
        "query": slot.description or slot.name,
        "top_k": top_k,
        "scope_order": list(_DEFAULT_SCOPE_ORDER),
        "include_relations": False,
        "filters": {"slot": slot.name},
    }


def recalled_anchor_nodes(recall_response: dict) -> list[str]:
    """Extract graph node ids from a RecallResponse's hits (to prime slot anchors).

    A hit primes an anchor only if it carries a ``metadata.node_id`` — free-text
    memories without a graph address are ignored (they cannot anchor a diffusion query).
    """
    nodes: list[str] = []
    for hit in recall_response.get("hits", []):
        node_id = (hit.get("metadata") or {}).get("node_id")
        if isinstance(node_id, str) and node_id and node_id not in nodes:
            nodes.append(node_id)
    return nodes


def prime_slot(slot: SlotSpec, recall_response: dict) -> SlotSpec:
    """Return a new SlotSpec whose anchors are augmented with recalled graph nodes.

    Deterministic and additive: existing anchors are preserved and lead; recalled
    nodes are appended in recall order, de-duplicated. Never drops declared anchors.
    """
    extra = [n for n in recalled_anchor_nodes(recall_response) if n not in slot.anchor_nodes]
    if not extra:
        return slot
    return SlotSpec(
        name=slot.name,
        anchor_nodes=tuple(slot.anchor_nodes) + tuple(extra),
        description=slot.description,
        min_epistemic=slot.min_epistemic,
        modal_class=slot.modal_class,
    )
