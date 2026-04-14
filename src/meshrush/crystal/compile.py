from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from meshrush.core.contracts import (
    ArtifactHandle,
    CandidateRegion,
    CompileDecision,
    CompileOutcome,
    EvidenceRef,
    GraphViewRef,
    GroundingState,
    LifecycleEvent,
    StopCandidate,
)

Metadata = dict[str, object]


@dataclass(slots=True)
class CompileInput:
    candidate_region: CandidateRegion
    graph_view: GraphViewRef
    grounding_state: GroundingState
    stop_candidates: tuple[StopCandidate, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class CompileCertificate:
    certificate_id: str
    outcome: CompileOutcome
    candidate_region_id: str
    graph_view_id: str
    evidence_refs: tuple[EvidenceRef, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class CompileResult:
    decision: CompileDecision
    artifact_handle: ArtifactHandle | None = None
    certificate: CompileCertificate | None = None
    lifecycle_events: tuple[LifecycleEvent, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class ArtifactMutationResult:
    artifact_handles: tuple[ArtifactHandle, ...] = ()
    lifecycle_events: tuple[LifecycleEvent, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    metadata: Metadata = field(default_factory=dict)


class CrystalCompiler(ABC):
    """Abstract compile/lifecycle boundary for the Crystal layer."""

    @abstractmethod
    def evaluate(self, compile_input: CompileInput) -> CompileDecision:
        """Evaluate whether a candidate region should be compiled."""

    @abstractmethod
    def compile(
        self,
        *,
        compile_input: CompileInput,
        decision: CompileDecision,
    ) -> CompileResult:
        """Materialize a compiled artifact from an accepted decision."""

    @abstractmethod
    def anneal(
        self,
        artifact_handle: ArtifactHandle,
        *,
        reason: str,
        metadata: Metadata | None = None,
    ) -> ArtifactMutationResult:
        """Relax or revise an existing artifact."""

    @abstractmethod
    def merge(
        self,
        artifact_handles: tuple[ArtifactHandle, ...],
        *,
        reason: str,
        metadata: Metadata | None = None,
    ) -> ArtifactMutationResult:
        """Merge two or more artifacts into a new bounded structure."""

    @abstractmethod
    def dissolve(
        self,
        artifact_handle: ArtifactHandle,
        *,
        reason: str,
        metadata: Metadata | None = None,
    ) -> ArtifactMutationResult:
        """Return an artifact to non-compiled or exploratory status."""
