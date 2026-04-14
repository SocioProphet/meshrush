from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from meshrush.core.contracts import GraphViewRef, GroundingState, RuntimeCommand, RuntimeContext, RuntimeInput
from meshrush.core.in_memory_runtime import InMemoryMeshRushRuntime
from meshrush.crystal.basic_compiler import BasicCrystalCompiler, BasicCrystalConfig
from meshrush.crystal.serialization import build_artifact_record, write_artifact_record
from meshrush.omni.basic_session import BasicOmniConfig, BasicOmniSession


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="meshrush")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser(
        "demo-run",
        help="Run a deterministic MeshRush demo session and optionally write an artifact JSON record.",
    )
    demo.add_argument("--workspace-id", default="workspace-1")
    demo.add_argument("--session-id", default="session-1")
    demo.add_argument("--actor-id", default="agent-1")
    demo.add_argument("--graph-view-id", default="graph-1")
    demo.add_argument("--world-ref", default="world-1")
    demo.add_argument("--anchors", nargs="+", default=["n1", "n2"])
    demo.add_argument("--diffuse-targets", nargs="+", default=["n3", "n4"])
    demo.add_argument("--artifact-out", type=Path, default=None)

    return parser


def _build_demo_runtime() -> InMemoryMeshRushRuntime:
    return InMemoryMeshRushRuntime(
        omni_session=BasicOmniSession(BasicOmniConfig(min_region_size=1, coherence_stop_threshold=0.75)),
        crystal_compiler=BasicCrystalCompiler(
            BasicCrystalConfig(min_region_size=1, min_support_score=0.25, require_stop_candidate=False)
        ),
    )


def run_demo(args: argparse.Namespace) -> int:
    runtime = _build_demo_runtime()

    context = RuntimeContext(
        workspace_id=args.workspace_id,
        session_id=args.session_id,
        actor_id=args.actor_id,
    )
    graph_view = GraphViewRef(graph_view_id=args.graph_view_id, world_ref=args.world_ref)
    grounding = GroundingState(graph_view_id=args.graph_view_id, anchor_node_ids=tuple(args.anchors))

    start_snapshot = runtime.start(context=context, graph_view=graph_view, grounding_state=grounding)

    diffuse_result = runtime.step(
        RuntimeInput(
            session_id=args.session_id,
            command=RuntimeCommand.DIFFUSE,
            target_ids=tuple(args.diffuse_targets),
        )
    )

    crystallize_result = runtime.step(
        RuntimeInput(
            session_id=args.session_id,
            command=RuntimeCommand.CRYSTALLIZE,
            target_ids=tuple(args.diffuse_targets),
        )
    )

    artifact_record = None
    artifact_path = None

    if crystallize_result.compile_decisions:
        decision = crystallize_result.compile_decisions[0]
        if decision.artifact_handle is not None:
            artifact_record = build_artifact_record(
                decision=decision,
                snapshot=crystallize_result.snapshot,
                lifecycle_events=crystallize_result.lifecycle_events,
                extra_evidence_refs=crystallize_result.evidence_refs,
            )
            if args.artifact_out is not None:
                artifact_path = str(write_artifact_record(args.artifact_out, artifact_record))

    summary = {
        "schema_version": "0.1.0",
        "kind": "meshrush.demo_run",
        "workspace_id": args.workspace_id,
        "session_id": args.session_id,
        "graph_view_id": args.graph_view_id,
        "start_status": start_snapshot.status.value,
        "diffuse_status": diffuse_result.snapshot.status.value,
        "crystallize_status": crystallize_result.snapshot.status.value,
        "anchors": list(args.anchors),
        "diffuse_targets": list(args.diffuse_targets),
        "compiled_artifact_ids": [artifact.artifact_id for artifact in crystallize_result.snapshot.active_artifacts],
        "artifact_record_written_to": artifact_path,
        "artifact_record": artifact_record,
    }

    print(json.dumps(summary, indent=2))
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.command == "demo-run":
        return run_demo(args)

    parser.error(f"unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
