from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from meshrush.core.contracts import (
    ArtifactHandle,
    CompileDecision,
    EvidenceRef,
    ExplorationTrace,
    RuntimeSnapshot,
)

Metadata = dict[str, object]


@dataclass(slots=True)
class PolicySnapshotRef:
    policy_snapshot_id: str
    uri: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class EvaluationContext:
    evaluation_id: str
    scenario: str | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class TransferContext:
    artifact_handles: tuple[ArtifactHandle, ...] = ()
    episode_refs: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class CurriculumHint:
    hint_id: str
    parameters: Metadata = field(default_factory=dict)
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class LearningContext:
    policy_snapshot: PolicySnapshotRef | None = None
    evaluation_context: EvaluationContext | None = None
    transfer_context: TransferContext | None = None
    curriculum_hint: CurriculumHint | None = None
    metadata: Metadata = field(default_factory=dict)


@dataclass(slots=True)
class LearningExport:
    session_id: str
    exploration_trace_ids: tuple[str, ...] = ()
    artifact_ids: tuple[str, ...] = ()
    evidence_ids: tuple[str, ...] = ()
    metadata: Metadata = field(default_factory=dict)


@runtime_checkable
class AlexandrianAcademyAdapter(Protocol):
    """Learning / evaluation / transfer integration boundary."""

    def build_learning_context(
        self,
        *,
        policy_snapshot: PolicySnapshotRef | None = None,
        evaluation_context: EvaluationContext | None = None,
        transfer_context: TransferContext | None = None,
        curriculum_hint: CurriculumHint | None = None,
    ) -> LearningContext:
        """Build learning-side context that can inform a MeshRush session."""

    def export_episode(
        self,
        *,
        snapshot: RuntimeSnapshot,
        exploration_traces: tuple[ExplorationTrace, ...],
        compile_decisions: tuple[CompileDecision, ...],
        artifact_handles: tuple[ArtifactHandle, ...],
        evidence_refs: tuple[EvidenceRef, ...],
        learning_context: LearningContext | None = None,
    ) -> LearningExport:
        """Export a bounded runtime episode to the learning/evaluation plane."""
