from __future__ import annotations

from typing import Iterable

from meshrush.core.contracts import (
    ArtifactHandle,
    CandidateRegion,
    GraphViewRef,
    GroundingState,
    LifecycleEvent,
    LifecycleEventType,
    RuntimeCommand,
    RuntimeContext,
    RuntimeInput,
    RuntimeSnapshot,
    RuntimeStatus,
    RuntimeStepResult,
    StopCandidate,
    StopReason,
)
from meshrush.core.runtime import MeshRushRuntime
from meshrush.crystal.compile import CompileInput, CrystalCompiler
from meshrush.omni.session import OmniSession, OmniState


def _unique_artifacts(artifacts: Iterable[ArtifactHandle]) -> tuple[ArtifactHandle, ...]:
    seen: set[str] = set()
    out: list[ArtifactHandle] = []
    for artifact in artifacts:
        if artifact.artifact_id not in seen:
            seen.add(artifact.artifact_id)
            out.append(artifact)
    return tuple(out)


class InMemoryMeshRushRuntime(MeshRushRuntime):
    """Deterministic in-memory reference runtime.

    This runtime is intentionally small and auditable. It exists to make the
    canonical contracts executable and to provide a first end-to-end path for
    future examples, tests, and experiments.
    """

    def __init__(
        self,
        *,
        omni_session: OmniSession,
        crystal_compiler: CrystalCompiler,
    ) -> None:
        self._omni = omni_session
        self._crystal = crystal_compiler
        self._snapshots: dict[str, RuntimeSnapshot] = {}
        self._omni_states: dict[str, OmniState] = {}
        self._candidate_regions: dict[str, tuple[CandidateRegion, ...]] = {}

    def start(
        self,
        *,
        context: RuntimeContext,
        graph_view: GraphViewRef,
        grounding_state: GroundingState,
    ) -> RuntimeSnapshot:
        snapshot = RuntimeSnapshot(
            session_id=context.session_id,
            status=RuntimeStatus.INITIALIZED,
            context=context,
            graph_view=graph_view,
            grounding_state=grounding_state,
            active_artifacts=(),
            metadata={},
        )
        self._snapshots[context.session_id] = snapshot
        self._omni_states[context.session_id] = self._omni.start(snapshot)
        return snapshot

    def step(self, runtime_input: RuntimeInput) -> RuntimeStepResult:
        prior = self._require_snapshot(runtime_input.session_id)
        omni_state = self._require_omni_state(runtime_input.session_id)

        diffusion = self._omni.advance(
            state=omni_state,
            runtime_input=runtime_input,
        )
        self._omni_states[runtime_input.session_id] = diffusion.state

        candidate_regions = diffusion.candidate_regions
        if candidate_regions:
            self._candidate_regions[runtime_input.session_id] = candidate_regions

        active_artifacts = list(prior.active_artifacts)
        compile_decisions = []
        lifecycle_events: list[LifecycleEvent] = []
        evidence_refs = list(diffusion.evidence_refs)
        status = self._next_status(prior.status, runtime_input.command)

        if runtime_input.command is RuntimeCommand.RESUME:
            lifecycle_events.append(
                LifecycleEvent(
                    event_id=f"run-resumed-{runtime_input.session_id}",
                    event_type=LifecycleEventType.RUN_RESUMED,
                    session_id=runtime_input.session_id,
                )
            )

        if runtime_input.command is RuntimeCommand.CRYSTALLIZE:
            compile_result = self._compile_from_runtime(
                session_id=runtime_input.session_id,
                graph_view=prior.graph_view,
                grounding_state=prior.grounding_state,
                candidate_regions=candidate_regions,
                stop_candidates=diffusion.stop_candidates,
                evidence_refs=tuple(evidence_refs),
                payload=runtime_input.payload,
            )
            if compile_result is not None:
                compile_decisions.append(compile_result.decision)
                lifecycle_events.extend(compile_result.lifecycle_events)
                if compile_result.artifact_handle is not None:
                    active_artifacts.append(compile_result.artifact_handle)

        if runtime_input.command is RuntimeCommand.PERSIST:
            for artifact in active_artifacts:
                lifecycle_events.append(
                    LifecycleEvent(
                        event_id=f"artifact-persisted-{artifact.artifact_id}",
                        event_type=LifecycleEventType.ARTIFACT_PERSISTED,
                        session_id=runtime_input.session_id,
                        artifact_id=artifact.artifact_id,
                    )
                )

        if runtime_input.command is RuntimeCommand.DISSOLVE:
            target_ids = set(runtime_input.target_ids)
            survivors: list[ArtifactHandle] = []
            for artifact in active_artifacts:
                should_dissolve = not target_ids or artifact.artifact_id in target_ids
                if should_dissolve:
                    mutation = self._crystal.dissolve(
                        artifact,
                        reason=runtime_input.payload.get("reason", "runtime_dissolve"),
                        metadata=runtime_input.payload,
                    )
                    lifecycle_events.extend(mutation.lifecycle_events)
                    evidence_refs.extend(mutation.evidence_refs)
                else:
                    survivors.append(artifact)
            active_artifacts = survivors

        if runtime_input.command is RuntimeCommand.STOP:
            lifecycle_events.extend(
                [
                    LifecycleEvent(
                        event_id=f"stop-candidate-{runtime_input.session_id}",
                        event_type=LifecycleEventType.STOP_CANDIDATE_EMITTED,
                        session_id=runtime_input.session_id,
                        metadata={"stop_count": len(diffusion.stop_candidates)},
                    ),
                    LifecycleEvent(
                        event_id=f"run-ended-{runtime_input.session_id}",
                        event_type=LifecycleEventType.RUN_ENDED,
                        session_id=runtime_input.session_id,
                    ),
                ]
            )

        snapshot = RuntimeSnapshot(
            session_id=prior.session_id,
            status=status,
            context=prior.context,
            graph_view=prior.graph_view,
            grounding_state=prior.grounding_state,
            active_artifacts=_unique_artifacts(active_artifacts),
            metadata={"last_command": runtime_input.command.value},
        )
        self._snapshots[runtime_input.session_id] = snapshot

        return RuntimeStepResult(
            session_id=runtime_input.session_id,
            snapshot=snapshot,
            exploration_traces=diffusion.exploration_traces,
            stop_candidates=diffusion.stop_candidates,
            candidate_regions=diffusion.candidate_regions,
            compile_decisions=tuple(compile_decisions),
            lifecycle_events=tuple(lifecycle_events),
            evidence_refs=tuple(evidence_refs),
        )

    def checkpoint(
        self,
        session_id: str,
        *,
        reason: str | None = None,
    ) -> RuntimeSnapshot:
        prior = self._require_snapshot(session_id)
        checkpointed = RuntimeSnapshot(
            session_id=prior.session_id,
            status=RuntimeStatus.CHECKPOINTED,
            context=prior.context,
            graph_view=prior.graph_view,
            grounding_state=prior.grounding_state,
            active_artifacts=prior.active_artifacts,
            metadata={"reason": reason} if reason else {},
        )
        self._snapshots[session_id] = checkpointed
        return checkpointed

    def resume(self, snapshot: RuntimeSnapshot) -> RuntimeSnapshot:
        resumed = RuntimeSnapshot(
            session_id=snapshot.session_id,
            status=RuntimeStatus.RUNNING,
            context=snapshot.context,
            graph_view=snapshot.graph_view,
            grounding_state=snapshot.grounding_state,
            active_artifacts=snapshot.active_artifacts,
            metadata=snapshot.metadata,
        )
        self._snapshots[snapshot.session_id] = resumed
        self._omni_states[snapshot.session_id] = self._omni.resume(
            snapshot=resumed,
            prior_state=self._omni_states.get(snapshot.session_id),
        )
        return resumed

    def end(
        self,
        session_id: str,
        *,
        reason: str | None = None,
    ) -> RuntimeSnapshot:
        prior = self._require_snapshot(session_id)
        ended = RuntimeSnapshot(
            session_id=prior.session_id,
            status=RuntimeStatus.STOPPED,
            context=prior.context,
            graph_view=prior.graph_view,
            grounding_state=prior.grounding_state,
            active_artifacts=prior.active_artifacts,
            metadata={"reason": reason} if reason else {},
        )
        self._snapshots[session_id] = ended
        return ended

    def _compile_from_runtime(
        self,
        *,
        session_id: str,
        graph_view: GraphViewRef,
        grounding_state: GroundingState,
        candidate_regions: tuple[CandidateRegion, ...],
        stop_candidates: tuple[StopCandidate, ...],
        evidence_refs,
        payload,
    ):
        region = self._select_candidate_region(
            session_id=session_id,
            graph_view=graph_view,
            candidate_regions=candidate_regions,
        )
        if region is None:
            return None

        compile_stop_candidates = stop_candidates or (
            StopCandidate(
                candidate_id=f"stop-{session_id}-synthetic",
                session_id=session_id,
                reason=StopReason.POLICY_DIRECTED_PAUSE,
                score=1.0,
                metadata={"source": "runtime_synthetic_stop"},
            ),
        )

        compile_input = CompileInput(
            candidate_region=region,
            graph_view=graph_view,
            grounding_state=grounding_state,
            stop_candidates=compile_stop_candidates,
            evidence_refs=evidence_refs,
            metadata=payload,
        )
        decision = self._crystal.evaluate(compile_input)
        return self._crystal.compile(
            compile_input=compile_input,
            decision=decision,
        )

    def _select_candidate_region(
        self,
        *,
        session_id: str,
        graph_view: GraphViewRef,
        candidate_regions: tuple[CandidateRegion, ...],
    ) -> CandidateRegion | None:
        if candidate_regions:
            return candidate_regions[-1]

        cached = self._candidate_regions.get(session_id, ())
        if cached:
            return cached[-1]

        omni_state = self._omni_states.get(session_id)
        if omni_state and omni_state.explored_node_ids:
            return CandidateRegion(
                region_id=f"region-{session_id}-fallback",
                session_id=session_id,
                graph_view_id=graph_view.graph_view_id,
                node_ids=omni_state.explored_node_ids,
                support_score=1.0,
                metadata={"source": "runtime_fallback"},
            )

        return None

    def _next_status(
        self,
        prior_status: RuntimeStatus,
        command: RuntimeCommand,
    ) -> RuntimeStatus:
        if command is RuntimeCommand.STOP:
            return RuntimeStatus.STOPPED
        if command is RuntimeCommand.RESUME:
            return RuntimeStatus.RUNNING
        if prior_status in {RuntimeStatus.INITIALIZED, RuntimeStatus.CHECKPOINTED}:
            return RuntimeStatus.RUNNING
        return RuntimeStatus.RUNNING

    def _require_snapshot(self, session_id: str) -> RuntimeSnapshot:
        if session_id not in self._snapshots:
            raise KeyError(f"unknown session_id: {session_id}")
        return self._snapshots[session_id]

    def _require_omni_state(self, session_id: str) -> OmniState:
        if session_id not in self._omni_states:
            raise KeyError(f"unknown omni state for session_id: {session_id}")
        return self._omni_states[session_id]
