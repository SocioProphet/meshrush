from __future__ import annotations

from meshrush.core.contracts import GraphViewRef, GroundingState, RuntimeCommand, RuntimeContext, RuntimeInput
from meshrush.core.in_memory_runtime import InMemoryMeshRushRuntime
from meshrush.crystal.basic_compiler import BasicCrystalCompiler, BasicCrystalConfig
from meshrush.crystal.serialization import artifact_record_to_json, build_artifact_record
from meshrush.omni.basic_session import BasicOmniConfig, BasicOmniSession


def main() -> None:
    runtime = InMemoryMeshRushRuntime(
        omni_session=BasicOmniSession(BasicOmniConfig(min_region_size=1, coherence_stop_threshold=0.75)),
        crystal_compiler=BasicCrystalCompiler(
            BasicCrystalConfig(min_region_size=1, min_support_score=0.25, require_stop_candidate=False)
        ),
    )

    context = RuntimeContext(workspace_id="workspace-1", session_id="session-1", actor_id="agent-1")
    graph_view = GraphViewRef(graph_view_id="graph-1", world_ref="world-1")
    grounding = GroundingState(graph_view_id="graph-1", anchor_node_ids=("n1", "n2"))

    runtime.start(context=context, graph_view=graph_view, grounding_state=grounding)

    runtime.step(
        RuntimeInput(
            session_id="session-1",
            command=RuntimeCommand.DIFFUSE,
            target_ids=("n3", "n4"),
        )
    )

    crystallize_result = runtime.step(
        RuntimeInput(
            session_id="session-1",
            command=RuntimeCommand.CRYSTALLIZE,
            target_ids=("n3", "n4"),
        )
    )

    if not crystallize_result.compile_decisions:
        raise SystemExit("No compile decision was emitted.")

    decision = crystallize_result.compile_decisions[0]
    if decision.artifact_handle is None:
        raise SystemExit("Compile decision did not produce an artifact.")

    artifact_record = build_artifact_record(
        decision=decision,
        snapshot=crystallize_result.snapshot,
        lifecycle_events=crystallize_result.lifecycle_events,
        extra_evidence_refs=crystallize_result.evidence_refs,
    )

    print(artifact_record_to_json(artifact_record))


if __name__ == "__main__":
    main()
