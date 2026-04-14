from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from meshrush.core.contracts import (
    ArtifactHandle,
    EvidenceRef,
    ExplorationTrace,
    GraphViewRef,
    LifecycleEvent,
    RuntimeContext,
    RuntimeSnapshot,
    RuntimeStatus,
)

Metadata = dict[str, object]


@dataclass(slots=True)
class ExecutionBundleRef:
    bundle_id: str
    version: str | None = None
    uri: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class RunManifest:
    run_id: str
    execution_bundle: ExecutionBundleRef
    graph_view: GraphViewRef
    workspace_id: str | None = None
    strategy_ref: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class ValidationContext:
    validation_id: str
    approved: bool | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class RolloutContext:
    plan_id: str | None = None
    cohort: str | None = None
    variant: str | None = None
    stage: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class ReplaySeed:
    replay_id: str
    source_run_id: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class OutcomeSummary:
    run_id: str
    status: RuntimeStatus
    artifact_handles: tuple[ArtifactHandle, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@runtime_checkable
class AgentplaneAdapter(Protocol):
    """Governed execution / replay / rollout integration boundary."""

    def build_runtime_context(
        self,
        *,
        run_manifest: RunManifest,
        validation: ValidationContext | None = None,
        rollout: RolloutContext | None = None,
        replay_seed: ReplaySeed | None = None,
    ) -> RuntimeContext:
        """Build a MeshRush runtime context from a governed run description."""

    def publish_run_result(
        self,
        *,
        snapshot: RuntimeSnapshot,
        run_trace: tuple[ExplorationTrace, ...],
        lifecycle_events: tuple[LifecycleEvent, ...],
        evidence_refs: tuple[EvidenceRef, ...],
        artifact_handles: tuple[ArtifactHandle, ...] = (),
    ) -> OutcomeSummary:
        """Publish a bounded run outcome back to the control plane."""
