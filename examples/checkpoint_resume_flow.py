from __future__ import annotations

from meshrush.core.contracts import GraphViewRef, GroundingState, RuntimeCommand, RuntimeContext, RuntimeInput
from meshrush.core.in_memory_runtime import InMemoryMeshRushRuntime
from meshrush.crystal.basic_compiler import BasicCrystalCompiler, BasicCrystalConfig
from meshrush.omni.basic_session import BasicOmniConfig, BasicOmniSession


def main() -> None:
    runtime = InMemoryMeshRushRuntime(
        omni_session=BasicOmniSession(BasicOmniConfig()),
        crystal_compiler=BasicCrystalCompiler(BasicCrystalConfig()),
    )

    context = RuntimeContext(workspace_id="workspace-1", session_id="session-1", actor_id="agent-1")
    graph_view = GraphViewRef(graph_view_id="graph-1", world_ref="world-1")
    grounding = GroundingState(graph_view_id="graph-1", anchor_node_ids=("n1", "n2"))

    start = runtime.start(context=context, graph_view=graph_view, grounding_state=grounding)
    print(f"start: {start.status.value}")

    runtime.step(RuntimeInput(session_id="session-1", command=RuntimeCommand.LOCALIZE, target_ids=("n1",)))
    checkpoint = runtime.checkpoint("session-1", reason="manual checkpoint")
    print(f"checkpoint: {checkpoint.status.value}")

    resumed = runtime.resume(checkpoint)
    print(f"resume: {resumed.status.value}")

    stopped = runtime.step(RuntimeInput(session_id="session-1", command=RuntimeCommand.STOP))
    print(f"stop: {stopped.snapshot.status.value}")


if __name__ == "__main__":
    main()
