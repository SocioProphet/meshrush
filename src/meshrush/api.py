"""Additive public API surface for MeshRush.

This module provides a stable import surface without rewriting existing package
`__init__` files during the current review pass.
"""

from meshrush.core.contracts import (
    ArtifactBoundary,
    ArtifactHandle,
    CandidateRegion,
    CompileDecision,
    CompileOutcome,
    EvidenceRef,
    ExplorationTrace,
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
from meshrush.core.in_memory_runtime import InMemoryMeshRushRuntime
from meshrush.crystal.basic_compiler import BasicCrystalCompiler, BasicCrystalConfig
from meshrush.crystal.compile import ArtifactMutationResult, CompileCertificate, CompileInput, CompileResult, CrystalCompiler
from meshrush.crystal.serialization import artifact_record_to_json, build_artifact_record, write_artifact_record
from meshrush.omni.basic_session import BasicOmniConfig, BasicOmniSession
from meshrush.omni.session import DiffusionResult, OmniSession, OmniState, ProbeRequest, ProbeResult

__all__ = [
    "ArtifactBoundary",
    "ArtifactHandle",
    "ArtifactMutationResult",
    "BasicCrystalCompiler",
    "BasicCrystalConfig",
    "BasicOmniConfig",
    "BasicOmniSession",
    "CandidateRegion",
    "CompileCertificate",
    "CompileDecision",
    "CompileInput",
    "CompileOutcome",
    "CompileResult",
    "CrystalCompiler",
    "DiffusionResult",
    "EvidenceRef",
    "ExplorationTrace",
    "GraphViewRef",
    "GroundingState",
    "InMemoryMeshRushRuntime",
    "LifecycleEvent",
    "LifecycleEventType",
    "OmniSession",
    "OmniState",
    "ProbeRequest",
    "ProbeResult",
    "RuntimeCommand",
    "RuntimeContext",
    "RuntimeInput",
    "RuntimeSnapshot",
    "RuntimeStatus",
    "RuntimeStepResult",
    "StopCandidate",
    "StopReason",
    "artifact_record_to_json",
    "build_artifact_record",
    "write_artifact_record",
]
