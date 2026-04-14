from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from meshrush.core.contracts import (
    CandidateRegion,
    EvidenceRef,
    ExplorationTrace,
    RuntimeInput,
    RuntimeSnapshot,
    StopCandidate,
)

Metadata = dict[str, object]


@dataclass(slots=True)
class OmniState:
    session_id: str
    graph_view_id: str
    frontier_node_ids: tuple[str, ...] = ()
    explored_node_ids: tuple[str, ...] = ()
    reduction_refs: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class ProbeRequest:
    request_id: str
    probe_family: str
    target_ids: tuple[str, ...] = ()
    parameters: Metadata = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class ProbeResult:
    request: ProbeRequest
    evidence_refs: tuple[EvidenceRef, ...] = ()
    stop_candidates: tuple[StopCandidate, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class DiffusionResult:
    state: OmniState
    exploration_traces: tuple[ExplorationTrace, ...] = ()
    stop_candidates: tuple[StopCandidate, ...] = ()
    candidate_regions: tuple[CandidateRegion, ...] = ()
    evidence_refs: tuple[EvidenceRef, ...] = ()
    metadata: Metadata = field(default_factory=dict)


class OmniSession(ABC):
    """Abstract diffusion/session boundary for the Omni layer."""

    @abstractmethod
    def start(self, snapshot: RuntimeSnapshot) -> OmniState:
        """Initialize Omni state from a runtime snapshot."""

    @abstractmethod
    def advance(
        self,
        *,
        state: OmniState,
        runtime_input: RuntimeInput,
    ) -> DiffusionResult:
        """Advance diffusion against the current runtime input."""

    @abstractmethod
    def probe(
        self,
        *,
        state: OmniState,
        request: ProbeRequest,
    ) -> ProbeResult:
        """Run a bounded probe family against the current diffusion state."""

    @abstractmethod
    def resume(
        self,
        *,
        snapshot: RuntimeSnapshot,
        prior_state: OmniState | None = None,
    ) -> OmniState:
        """Restore or rebuild Omni state for a resumed session."""
