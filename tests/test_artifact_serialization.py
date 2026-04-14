import json
import unittest

from meshrush.core.contracts import GraphViewRef, GroundingState, RuntimeCommand, RuntimeContext, RuntimeInput
from meshrush.core.in_memory_runtime import InMemoryMeshRushRuntime
from meshrush.crystal.basic_compiler import BasicCrystalCompiler, BasicCrystalConfig
from meshrush.crystal.serialization import artifact_record_to_json, build_artifact_record
from meshrush.omni.basic_session import BasicOmniConfig, BasicOmniSession


class ArtifactSerializationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.runtime = InMemoryMeshRushRuntime(
            omni_session=BasicOmniSession(BasicOmniConfig()),
            crystal_compiler=BasicCrystalCompiler(BasicCrystalConfig()),
        )
        self.context = RuntimeContext(workspace_id="workspace-1", session_id="session-1", actor_id="agent-1")
        self.graph_view = GraphViewRef(graph_view_id="graph-1", world_ref="world-1")
        self.grounding = GroundingState(graph_view_id="graph-1", anchor_node_ids=("n1", "n2"))

    def test_build_artifact_record(self) -> None:
        self.runtime.start(context=self.context, graph_view=self.graph_view, grounding_state=self.grounding)
        self.runtime.step(RuntimeInput(session_id="session-1", command=RuntimeCommand.DIFFUSE, target_ids=("n3", "n4")))
        crystallize_result = self.runtime.step(
            RuntimeInput(session_id="session-1", command=RuntimeCommand.CRYSTALLIZE, target_ids=("n3", "n4"))
        )

        decision = crystallize_result.compile_decisions[0]
        record = build_artifact_record(
            decision=decision,
            snapshot=crystallize_result.snapshot,
            lifecycle_events=crystallize_result.lifecycle_events,
            extra_evidence_refs=crystallize_result.evidence_refs,
        )

        self.assertEqual(record["schema_version"], "0.1.0")
        self.assertEqual(record["kind"], "meshrush.artifact_record")
        self.assertEqual(record["artifact"]["artifact_id"], decision.artifact_handle.artifact_id)
        self.assertEqual(record["runtime"]["session_id"], "session-1")

    def test_record_serializes_to_json(self) -> None:
        self.runtime.start(context=self.context, graph_view=self.graph_view, grounding_state=self.grounding)
        self.runtime.step(RuntimeInput(session_id="session-1", command=RuntimeCommand.DIFFUSE, target_ids=("n3", "n4")))
        crystallize_result = self.runtime.step(
            RuntimeInput(session_id="session-1", command=RuntimeCommand.CRYSTALLIZE, target_ids=("n3", "n4"))
        )

        record = build_artifact_record(
            decision=crystallize_result.compile_decisions[0],
            snapshot=crystallize_result.snapshot,
            lifecycle_events=crystallize_result.lifecycle_events,
            extra_evidence_refs=crystallize_result.evidence_refs,
        )
        payload = artifact_record_to_json(record)
        decoded = json.loads(payload)

        self.assertEqual(decoded["kind"], "meshrush.artifact_record")
        self.assertIn("compile", decoded)
        self.assertIn("lifecycle", decoded)
