import unittest

from meshrush.core.contracts import GraphViewRef, GroundingState, RuntimeCommand, RuntimeContext, RuntimeInput, RuntimeStatus
from meshrush.core.in_memory_runtime import InMemoryMeshRushRuntime
from meshrush.crystal.basic_compiler import BasicCrystalCompiler, BasicCrystalConfig
from meshrush.omni.basic_session import BasicOmniConfig, BasicOmniSession


class BasicRuntimeFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = InMemoryMeshRushRuntime(
            omni_session=BasicOmniSession(BasicOmniConfig(min_region_size=1, coherence_stop_threshold=0.75)),
            crystal_compiler=BasicCrystalCompiler(
                BasicCrystalConfig(min_region_size=1, min_support_score=0.25, require_stop_candidate=False)
            ),
        )
        self.context = RuntimeContext(workspace_id="workspace-1", session_id="session-1", actor_id="agent-1")
        self.graph_view = GraphViewRef(graph_view_id="graph-1", world_ref="world-1")
        self.grounding = GroundingState(graph_view_id="graph-1", anchor_node_ids=("n1", "n2"))

    def test_start_diffuse_crystallize_dissolve_flow(self) -> None:
        snapshot = self.runtime.start(context=self.context, graph_view=self.graph_view, grounding_state=self.grounding)
        self.assertEqual(snapshot.status, RuntimeStatus.INITIALIZED)

        diffuse = self.runtime.step(RuntimeInput(session_id="session-1", command=RuntimeCommand.DIFFUSE, target_ids=("n3", "n4")))
        self.assertEqual(diffuse.snapshot.status, RuntimeStatus.RUNNING)
        self.assertEqual(len(diffuse.exploration_traces), 1)
        self.assertGreaterEqual(len(diffuse.candidate_regions), 1)

        crystallize = self.runtime.step(
            RuntimeInput(session_id="session-1", command=RuntimeCommand.CRYSTALLIZE, target_ids=("n3", "n4"))
        )
        self.assertEqual(len(crystallize.compile_decisions), 1)
        self.assertEqual(crystallize.compile_decisions[0].outcome.value, "accept")
        self.assertEqual(len(crystallize.snapshot.active_artifacts), 1)

        artifact_id = crystallize.snapshot.active_artifacts[0].artifact_id
        self.assertTrue(any(event.event_type.value == "artifact_compiled" for event in crystallize.lifecycle_events))

        dissolve = self.runtime.step(
            RuntimeInput(session_id="session-1", command=RuntimeCommand.DISSOLVE, target_ids=(artifact_id,), payload={"reason": "cleanup"})
        )
        self.assertEqual(len(dissolve.snapshot.active_artifacts), 0)
        self.assertTrue(any(event.event_type.value == "artifact_dissolved" for event in dissolve.lifecycle_events))

    def test_checkpoint_resume_stop_flow(self) -> None:
        self.runtime.start(context=self.context, graph_view=self.graph_view, grounding_state=self.grounding)
        self.runtime.step(RuntimeInput(session_id="session-1", command=RuntimeCommand.LOCALIZE, target_ids=("n1",)))

        checkpoint = self.runtime.checkpoint("session-1", reason="checkpoint")
        self.assertEqual(checkpoint.status, RuntimeStatus.CHECKPOINTED)

        resumed = self.runtime.resume(checkpoint)
        self.assertEqual(resumed.status, RuntimeStatus.RUNNING)

        stopped = self.runtime.step(RuntimeInput(session_id="session-1", command=RuntimeCommand.STOP))
        self.assertEqual(stopped.snapshot.status, RuntimeStatus.STOPPED)
        self.assertTrue(any(event.event_type.value == "run_ended" for event in stopped.lifecycle_events))
