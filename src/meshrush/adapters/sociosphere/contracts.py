from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from meshrush.core.contracts import (
    ArtifactHandle,
    EvidenceRef,
    GraphViewRef,
    LifecycleEvent,
    RuntimeContext,
    RuntimeSnapshot,
)

Metadata = dict[str, object]


@dataclass(slots=True)
class WorkspaceContext:
    workspace_id: str
    controller_id: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class SessionContext:
    session_id: str
    actor_id: str
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class GraphEntryContext:
    graph_view: GraphViewRef
    entry_node_ids: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class ConstraintContext:
    policy_constraints: Metadata = field(default_factory=dict)
    operational_budgets: Metadata = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class ResumeContext:
    snapshot: RuntimeSnapshot | None = None
    artifact_handles: tuple[ArtifactHandle, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class WorkspaceStateHints:
    workspace_id: str
    artifact_handles: tuple[ArtifactHandle, ...] = ()
    lifecycle_events: tuple[LifecycleEvent, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@runtime_checkable
class SociosphereAdapter(Protocol):
    """Workspace/controller integration boundary."""

    def build_runtime_context(
        self,
        *,
        workspace: WorkspaceContext,
        session: SessionContext,
        graph_entry: GraphEntryContext,
        constraints: ConstraintContext | None = None,
        resume: ResumeContext | None = None,
    ) -> RuntimeContext:
        """Build a MeshRush runtime context from workspace/controller inputs."""

    def publish_runtime_outputs(
        self,
        *,
        snapshot: RuntimeSnapshot,
        lifecycle_events: tuple[LifecycleEvent, ...],
        artifact_handles: tuple[ArtifactHandle, ...],
        evidence_refs: tuple[EvidenceRef, ...],
        hints: WorkspaceStateHints | None = None,
    ) -> None:
        """Publish runtime outputs back into the workspace/controller layer."""
