from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from meshrush.core.contracts import (
    CandidateRegion,
    EvidenceRef,
    ExplorationTrace,
    RuntimeCommand,
    RuntimeInput,
    RuntimeSnapshot,
    StopCandidate,
    StopReason,
)
from meshrush.omni.session import DiffusionResult, OmniSession, OmniState, ProbeRequest, ProbeResult


def _unique_preserve_order(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return tuple(out)


@dataclass(slots=True)
class BasicOmniConfig:
    min_region_size: int = 1
    coherence_stop_threshold: float = 0.75


class BasicOmniSession(OmniSession):
    """Deterministic reference Omni session.

    This is intentionally simple. It is not the full scientific runtime.
    Its job is to provide a bounded, inspectable exploration layer that
    exercises the contracts and keeps the package executable end to end.
    """

    def __init__(self, config: BasicOmniConfig | None = None) -> None:
        self.config = config or BasicOmniConfig()

    def start(self, snapshot: RuntimeSnapshot) -> OmniState:
        anchors = snapshot.grounding_state.anchor_node_ids
        return OmniState(
            session_id=snapshot.session_id,
            graph_view_id=snapshot.graph_view.graph_view_id,
            frontier_node_ids=anchors,
            explored_node_ids=anchors,
            reduction_refs=(),
            metadata={"phase": "initialized"},
        )

    def advance(
        self,
        *,
        state: OmniState,
        runtime_input: RuntimeInput,
    ) -> DiffusionResult:
        target_ids = self._resolve_targets(state=state, runtime_input=runtime_input)
        explored = _unique_preserve_order(state.explored_node_ids + target_ids)
        frontier = self._next_frontier(
            prior_frontier=state.frontier_node_ids,
            target_ids=target_ids,
            command=runtime_input.command,
        )

        next_state = OmniState(
            session_id=state.session_id,
            graph_view_id=state.graph_view_id,
            frontier_node_ids=frontier,
            explored_node_ids=explored,
            reduction_refs=state.reduction_refs,
            metadata={"last_command": runtime_input.command.value},
        )

        trace = ExplorationTrace(
            trace_id=f"trace-{state.session_id}-{runtime_input.command.value}-{len(explored)}",
            session_id=state.session_id,
            graph_view_id=state.graph_view_id,
            command=runtime_input.command,
            node_ids=target_ids,
            metadata={"frontier_size": len(frontier), "explored_size": len(explored)},
        )

        evidence_refs = (
            EvidenceRef(
                evidence_id=f"evidence-{state.session_id}-{runtime_input.command.value}-{len(explored)}",
                kind="exploration_trace",
                metadata={"command": runtime_input.command.value},
            ),
        )

        candidate_regions = self._candidate_regions(
            session_id=state.session_id,
            graph_view_id=state.graph_view_id,
            command=runtime_input.command,
            explored=explored,
            target_ids=target_ids,
        )
        stop_candidates = self._stop_candidates(
            session_id=state.session_id,
            command=runtime_input.command,
            target_ids=target_ids,
            explored=explored,
        )

        return DiffusionResult(
            state=next_state,
            exploration_traces=(trace,),
            stop_candidates=stop_candidates,
            candidate_regions=candidate_regions,
            evidence_refs=evidence_refs,
            metadata={
                "frontier_size": len(frontier),
                "explored_size": len(explored),
            },
        )

    def probe(
        self,
        *,
        state: OmniState,
        request: ProbeRequest,
    ) -> ProbeResult:
        evidence = EvidenceRef(
            evidence_id=f"probe-{state.session_id}-{request.request_id}",
            kind="probe_bundle",
            metadata={
                "probe_family": request.probe_family,
                "target_count": len(request.target_ids),
            },
        )

        stop_candidates: tuple[StopCandidate, ...] = ()
        if request.probe_family == "saturation":
            stop_candidates = (
                StopCandidate(
                    candidate_id=f"stop-{state.session_id}-probe-{request.request_id}",
                    session_id=state.session_id,
                    reason=StopReason.SIGNAL_SATURATION,
                    score=1.0,
                    metadata={"probe_family": request.probe_family},
                ),
            )

        return ProbeResult(
            request=request,
            evidence_refs=(evidence,),
            stop_candidates=stop_candidates,
            metadata={"graph_view_id": state.graph_view_id},
        )

    def resume(
        self,
        *,
        snapshot: RuntimeSnapshot,
        prior_state: OmniState | None = None,
    ) -> OmniState:
        if prior_state is not None:
            return prior_state
        return self.start(snapshot)

    def _resolve_targets(
        self,
        *,
        state: OmniState,
        runtime_input: RuntimeInput,
    ) -> tuple[str, ...]:
        if runtime_input.target_ids:
            return runtime_input.target_ids

        if runtime_input.command in {
            RuntimeCommand.ENTER,
            RuntimeCommand.LOCALIZE,
            RuntimeCommand.RESUME,
        }:
            return state.frontier_node_ids or state.explored_node_ids

        if runtime_input.command in {
            RuntimeCommand.TRAVERSE,
            RuntimeCommand.DIFFUSE,
            RuntimeCommand.SCORE,
            RuntimeCommand.CRYSTALLIZE,
        }:
            return state.frontier_node_ids

        return ()

    def _next_frontier(
        self,
        *,
        prior_frontier: tuple[str, ...],
        target_ids: tuple[str, ...],
        command: RuntimeCommand,
    ) -> tuple[str, ...]:
        if command in {RuntimeCommand.TRAVERSE, RuntimeCommand.DIFFUSE}:
            return target_ids
        if command in {RuntimeCommand.STOP, RuntimeCommand.CRYSTALLIZE, RuntimeCommand.DISSOLVE}:
            return ()
        return prior_frontier

    def _candidate_regions(
        self,
        *,
        session_id: str,
        graph_view_id: str,
        command: RuntimeCommand,
        explored: tuple[str, ...],
        target_ids: tuple[str, ...],
    ) -> tuple[CandidateRegion, ...]:
        if command not in {
            RuntimeCommand.TRAVERSE,
            RuntimeCommand.DIFFUSE,
            RuntimeCommand.SCORE,
            RuntimeCommand.CRYSTALLIZE,
        }:
            return ()

        basis = target_ids or explored
        if len(basis) < self.config.min_region_size:
            return ()

        support_score = len(basis) / max(1, len(explored))
        return (
            CandidateRegion(
                region_id=f"region-{session_id}-{len(explored)}",
                session_id=session_id,
                graph_view_id=graph_view_id,
                node_ids=basis,
                support_score=support_score,
                metadata={"explored_size": len(explored)},
            ),
        )

    def _stop_candidates(
        self,
        *,
        session_id: str,
        command: RuntimeCommand,
        target_ids: tuple[str, ...],
        explored: tuple[str, ...],
    ) -> tuple[StopCandidate, ...]:
        if command is RuntimeCommand.STOP:
            return (
                StopCandidate(
                    candidate_id=f"stop-{session_id}-policy",
                    session_id=session_id,
                    reason=StopReason.POLICY_DIRECTED_PAUSE,
                    score=1.0,
                ),
            )

        if command in {RuntimeCommand.TRAVERSE, RuntimeCommand.DIFFUSE} and not target_ids:
            return (
                StopCandidate(
                    candidate_id=f"stop-{session_id}-frontier",
                    session_id=session_id,
                    reason=StopReason.FRONTIER_EXHAUSTION,
                    score=0.0,
                ),
            )

        if command in {RuntimeCommand.SCORE, RuntimeCommand.DIFFUSE} and explored:
            concentration = len(target_ids or explored) / max(1, len(explored))
            if concentration >= self.config.coherence_stop_threshold:
                return (
                    StopCandidate(
                        candidate_id=f"stop-{session_id}-coherence",
                        session_id=session_id,
                        reason=StopReason.COHERENCE_CONCENTRATION,
                        score=concentration,
                    ),
                )

        return ()
