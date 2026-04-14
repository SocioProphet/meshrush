from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from meshrush.core.contracts import (
    ArtifactBoundary,
    ArtifactHandle,
    CompileDecision,
    CompileOutcome,
    EvidenceRef,
    LifecycleEvent,
    LifecycleEventType,
)
from meshrush.crystal.compile import (
    ArtifactMutationResult,
    CompileCertificate,
    CompileInput,
    CompileResult,
    CrystalCompiler,
)


def _unique_preserve_order(values: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            out.append(value)
    return tuple(out)


@dataclass(slots=True)
class BasicCrystalConfig:
    min_region_size: int = 1
    min_support_score: float = 0.25
    require_stop_candidate: bool = False


class BasicCrystalCompiler(CrystalCompiler):
    """Deterministic reference Crystal compiler.

    This compiler is deliberately conservative and minimal. It exercises the
    compile lifecycle without pretending to be the full MeshRush scientific
    compile engine.
    """

    def __init__(self, config: BasicCrystalConfig | None = None) -> None:
        self.config = config or BasicCrystalConfig()

    def evaluate(self, compile_input: CompileInput) -> CompileDecision:
        region = compile_input.candidate_region
        reasons: list[str] = []

        if not region.node_ids:
            return CompileDecision(
                candidate_region_id=region.region_id,
                outcome=CompileOutcome.REJECT,
                reasons=("empty_region",),
                certificate_refs=compile_input.evidence_refs,
            )

        if len(region.node_ids) < self.config.min_region_size:
            return CompileDecision(
                candidate_region_id=region.region_id,
                outcome=CompileOutcome.DEFER,
                reasons=("region_too_small",),
                certificate_refs=compile_input.evidence_refs,
            )

        if region.support_score is not None and region.support_score < self.config.min_support_score:
            return CompileDecision(
                candidate_region_id=region.region_id,
                outcome=CompileOutcome.DEFER,
                reasons=("insufficient_support",),
                certificate_refs=compile_input.evidence_refs,
            )

        if self.config.require_stop_candidate and not compile_input.stop_candidates:
            return CompileDecision(
                candidate_region_id=region.region_id,
                outcome=CompileOutcome.DEFER,
                reasons=("missing_stop_candidate",),
                certificate_refs=compile_input.evidence_refs,
            )

        reasons.extend(["bounded_candidate", "evidence_present"])
        if compile_input.stop_candidates:
            reasons.append("stop_surface_present")

        return CompileDecision(
            candidate_region_id=region.region_id,
            outcome=CompileOutcome.ACCEPT,
            reasons=tuple(reasons),
            certificate_refs=compile_input.evidence_refs,
        )

    def compile(
        self,
        *,
        compile_input: CompileInput,
        decision: CompileDecision,
    ) -> CompileResult:
        certificate = CompileCertificate(
            certificate_id=f"certificate-{compile_input.candidate_region.region_id}",
            outcome=decision.outcome,
            candidate_region_id=compile_input.candidate_region.region_id,
            graph_view_id=compile_input.graph_view.graph_view_id,
            evidence_refs=compile_input.evidence_refs,
            metadata={"grounded_graph_view": compile_input.graph_view.graph_view_id},
        )

        evaluated_event = LifecycleEvent(
            event_id=f"compile-evaluated-{compile_input.candidate_region.region_id}",
            event_type=LifecycleEventType.COMPILE_EVALUATED,
            session_id=compile_input.candidate_region.session_id,
            metadata={"outcome": decision.outcome.value},
        )

        if decision.outcome is not CompileOutcome.ACCEPT:
            return CompileResult(
                decision=decision,
                artifact_handle=None,
                certificate=certificate,
                lifecycle_events=(evaluated_event,),
            )

        included = _unique_preserve_order(compile_input.candidate_region.node_ids)
        boundary = ArtifactBoundary(
            included_node_ids=included,
            excluded_node_ids=(),
            metadata={"graph_view_id": compile_input.graph_view.graph_view_id},
        )
        artifact = ArtifactHandle(
            artifact_id=f"artifact-{compile_input.candidate_region.region_id}",
            kind="compiled_artifact",
            graph_view_id=compile_input.graph_view.graph_view_id,
            boundary=boundary,
            metadata={
                "candidate_region_id": compile_input.candidate_region.region_id,
                "support_score": compile_input.candidate_region.support_score,
            },
        )

        updated_decision = CompileDecision(
            candidate_region_id=decision.candidate_region_id,
            outcome=decision.outcome,
            reasons=decision.reasons,
            artifact_handle=artifact,
            certificate_refs=decision.certificate_refs,
            metadata=decision.metadata,
        )

        compiled_event = LifecycleEvent(
            event_id=f"artifact-compiled-{artifact.artifact_id}",
            event_type=LifecycleEventType.ARTIFACT_COMPILED,
            session_id=compile_input.candidate_region.session_id,
            artifact_id=artifact.artifact_id,
        )
        persisted_event = LifecycleEvent(
            event_id=f"artifact-persisted-{artifact.artifact_id}",
            event_type=LifecycleEventType.ARTIFACT_PERSISTED,
            session_id=compile_input.candidate_region.session_id,
            artifact_id=artifact.artifact_id,
        )

        return CompileResult(
            decision=updated_decision,
            artifact_handle=artifact,
            certificate=certificate,
            lifecycle_events=(evaluated_event, compiled_event, persisted_event),
        )

    def anneal(
        self,
        artifact_handle: ArtifactHandle,
        *,
        reason: str,
        metadata: dict[str, object] | None = None,
    ) -> ArtifactMutationResult:
        event = LifecycleEvent(
            event_id=f"artifact-annealed-{artifact_handle.artifact_id}",
            event_type=LifecycleEventType.ARTIFACT_ANNEALED,
            session_id="unknown",
            artifact_id=artifact_handle.artifact_id,
            metadata={"reason": reason, **(metadata or {})},
        )
        return ArtifactMutationResult(
            artifact_handles=(artifact_handle,),
            lifecycle_events=(event,),
        )

    def merge(
        self,
        artifact_handles: tuple[ArtifactHandle, ...],
        *,
        reason: str,
        metadata: dict[str, object] | None = None,
    ) -> ArtifactMutationResult:
        if not artifact_handles:
            return ArtifactMutationResult()

        merged_nodes: list[str] = []
        graph_view_id = artifact_handles[0].graph_view_id
        for artifact in artifact_handles:
            if artifact.boundary is not None:
                merged_nodes.extend(artifact.boundary.included_node_ids)

        merged = ArtifactHandle(
            artifact_id="artifact-merged",
            kind="compiled_artifact",
            graph_view_id=graph_view_id,
            boundary=ArtifactBoundary(
                included_node_ids=_unique_preserve_order(merged_nodes),
                metadata={"merged_from": tuple(a.artifact_id for a in artifact_handles)},
            ),
        )
        event = LifecycleEvent(
            event_id="artifact-merged-event",
            event_type=LifecycleEventType.ARTIFACT_MERGED,
            session_id="unknown",
            artifact_id=merged.artifact_id,
            metadata={"reason": reason, **(metadata or {})},
        )
        return ArtifactMutationResult(
            artifact_handles=(merged,),
            lifecycle_events=(event,),
        )

    def dissolve(
        self,
        artifact_handle: ArtifactHandle,
        *,
        reason: str,
        metadata: dict[str, object] | None = None,
    ) -> ArtifactMutationResult:
        event = LifecycleEvent(
            event_id=f"artifact-dissolved-{artifact_handle.artifact_id}",
            event_type=LifecycleEventType.ARTIFACT_DISSOLVED,
            session_id="unknown",
            artifact_id=artifact_handle.artifact_id,
            metadata={"reason": reason, **(metadata or {})},
        )
        evidence = EvidenceRef(
            evidence_id=f"evidence-dissolve-{artifact_handle.artifact_id}",
            kind="artifact_dissolution",
            metadata={"reason": reason, **(metadata or {})},
        )
        return ArtifactMutationResult(
            artifact_handles=(artifact_handle,),
            lifecycle_events=(event,),
            evidence_refs=(evidence,),
        )
