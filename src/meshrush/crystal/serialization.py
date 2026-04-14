from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from meshrush.core.contracts import CompileDecision, EvidenceRef, LifecycleEvent, RuntimeSnapshot


def _serialize_evidence_ref(evidence: EvidenceRef) -> dict[str, Any]:
    return {
        "evidence_id": evidence.evidence_id,
        "kind": evidence.kind,
        "uri": evidence.uri,
        "metadata": evidence.metadata,
    }


def _serialize_lifecycle_event(event: LifecycleEvent) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type.value,
        "session_id": event.session_id,
        "artifact_id": event.artifact_id,
        "metadata": event.metadata,
    }


def build_artifact_record(
    *,
    decision: CompileDecision,
    snapshot: RuntimeSnapshot,
    lifecycle_events: tuple[LifecycleEvent, ...] = (),
    extra_evidence_refs: tuple[EvidenceRef, ...] = (),
) -> dict[str, Any]:
    """Build the first canonical serialized artifact record shape."""
    artifact = decision.artifact_handle
    if artifact is None:
        raise ValueError("compile decision does not contain an artifact handle")

    boundary = artifact.boundary
    evidence_refs = tuple(decision.certificate_refs) + tuple(extra_evidence_refs)

    return {
        "schema_version": "0.1.0",
        "kind": "meshrush.artifact_record",
        "artifact": {
            "artifact_id": artifact.artifact_id,
            "kind": artifact.kind,
            "graph_view_id": artifact.graph_view_id,
            "boundary": {
                "included_node_ids": list(boundary.included_node_ids) if boundary else [],
                "excluded_node_ids": list(boundary.excluded_node_ids) if boundary else [],
                "metadata": boundary.metadata if boundary else {},
            },
            "metadata": artifact.metadata,
        },
        "compile": {
            "candidate_region_id": decision.candidate_region_id,
            "outcome": decision.outcome.value,
            "reasons": list(decision.reasons),
            "certificate_refs": [_serialize_evidence_ref(e) for e in evidence_refs],
            "metadata": decision.metadata,
        },
        "runtime": {
            "workspace_id": snapshot.context.workspace_id,
            "session_id": snapshot.context.session_id,
            "actor_id": snapshot.context.actor_id,
            "policy_snapshot_id": snapshot.context.policy_snapshot_id,
            "graph_view_id": snapshot.graph_view.graph_view_id,
            "world_ref": snapshot.graph_view.world_ref,
            "grounding": {
                "anchor_node_ids": list(snapshot.grounding_state.anchor_node_ids),
                "metadata": snapshot.grounding_state.metadata,
            },
            "status": snapshot.status.value,
            "snapshot_metadata": snapshot.metadata,
        },
        "lifecycle": [_serialize_lifecycle_event(event) for event in lifecycle_events],
        "provenance": {
            "active_artifact_ids": [a.artifact_id for a in snapshot.active_artifacts],
        },
    }


def artifact_record_to_json(record: dict[str, Any], *, indent: int = 2) -> str:
    return json.dumps(record, indent=indent, sort_keys=False)


def write_artifact_record(
    path: str | Path,
    record: dict[str, Any],
    *,
    indent: int = 2,
) -> Path:
    output_path = Path(path)
    output_path.write_text(artifact_record_to_json(record, indent=indent) + "\n", encoding="utf-8")
    return output_path
