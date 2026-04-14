from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

Metadata = dict[str, Any]


class RuntimeCommand(str, Enum):
    ENTER = "enter"
    LOCALIZE = "localize"
    TRAVERSE = "traverse"
    DIFFUSE = "diffuse"
    SCORE = "score"
    STOP = "stop"
    CRYSTALLIZE = "crystallize"
    PERSIST = "persist"
    RESUME = "resume"
    DISSOLVE = "dissolve"


class RuntimeStatus(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    CHECKPOINTED = "checkpointed"
    STOPPED = "stopped"
    FAILED = "failed"


class StopReason(str, Enum):
    FRONTIER_EXHAUSTION = "frontier_exhaustion"
    SIGNAL_SATURATION = "signal_saturation"
    COHERENCE_CONCENTRATION = "coherence_concentration"
    BUDGET_EXHAUSTION = "budget_exhaustion"
    POLICY_DIRECTED_PAUSE = "policy_directed_pause"


class CompileOutcome(str, Enum):
    REJECT = "reject"
    DEFER = "defer"
    ACCEPT = "accept"
    REWORK = "rework"


class LifecycleEventType(str, Enum):
    RUN_STARTED = "run_started"
    RUN_CHECKPOINTED = "run_checkpointed"
    RUN_RESUMED = "run_resumed"
    STOP_CANDIDATE_EMITTED = "stop_candidate_emitted"
    COMPILE_EVALUATED = "compile_evaluated"
    ARTIFACT_COMPILED = "artifact_compiled"
    ARTIFACT_PERSISTED = "artifact_persisted"
    ARTIFACT_REUSED = "artifact_reused"
    ARTIFACT_ANNEALED = "artifact_annealed"
    ARTIFACT_MERGED = "artifact_merged"
    ARTIFACT_DISSOLVED = "artifact_dissolved"
    RUN_ENDED = "run_ended"
    RUN_FAILED = "run_failed"


@dataclass(slots=True)
class GraphViewRef:
    graph_view_id: str
    kind: str = "graph_view"
    world_ref: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class GroundingState:
    graph_view_id: str
    anchor_node_ids: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeContext:
    workspace_id: str
    session_id: str
    actor_id: str
    policy_snapshot_id: str | None = None
    constraints: Metadata = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class EvidenceRef:
    evidence_id: str
    kind: str = "evidence"
    uri: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class ExplorationTrace:
    trace_id: str
    session_id: str
    graph_view_id: str
    command: RuntimeCommand | None = None
    node_ids: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class StopCandidate:
    candidate_id: str
    session_id: str
    reason: StopReason
    score: float | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class CandidateRegion:
    region_id: str
    session_id: str
    graph_view_id: str
    node_ids: tuple[str, ...]
    support_score: float | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class ArtifactBoundary:
    included_node_ids: tuple[str, ...]
    excluded_node_ids: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class ArtifactHandle:
    artifact_id: str
    kind: str = "compiled_artifact"
    graph_view_id: str | None = None
    boundary: ArtifactBoundary | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class LifecycleEvent:
    event_id: str
    event_type: LifecycleEventType
    session_id: str
    artifact_id: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeInput:
    session_id: str
    command: RuntimeCommand
    target_ids: tuple[str, ...] = ()
    payload: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class CompileDecision:
    candidate_region_id: str
    outcome: CompileOutcome
    reasons: tuple[str, ...] = ()
    artifact_handle: ArtifactHandle | None = None
    certificate_refs: tuple[EvidenceRef, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeSnapshot:
    session_id: str
    status: RuntimeStatus
    context: RuntimeContext
    graph_view: GraphViewRef
    grounding_state: GroundingState
    active_artifacts: tuple[ArtifactHandle, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class RuntimeStepResult:
    session_id: str
    snapshot: RuntimeSnapshot
    exploration_traces: tuple[ExplorationTrace, ...] = ()
    stop_candidates: tuple[StopCandidate, ...] = ()
    candidate_regions: tuple[CandidateRegion, ...] = ()
    compile_decisions: tuple[CompileDecision, ...] = ()
    lifecycle_events: tuple[LifecycleEvent, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    metadata: Metadata = field(default_factory=dict)
