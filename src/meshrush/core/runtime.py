from __future__ import annotations

from abc import ABC, abstractmethod

from .contracts import (
    GraphViewRef,
    GroundingState,
    RuntimeContext,
    RuntimeInput,
    RuntimeSnapshot,
    RuntimeStepResult,
)


class MeshRushRuntime(ABC):
    """Abstract runtime boundary for MeshRush.

    Concrete implementations may vary, but they must honor the canonical
    runtime semantics defined in the specifications.
    """

    @abstractmethod
    def start(
        self,
        *,
        context: RuntimeContext,
        graph_view: GraphViewRef,
        grounding_state: GroundingState,
    ) -> RuntimeSnapshot:
        """Initialize a runtime session against a graph-derived view."""

    @abstractmethod
    def step(self, runtime_input: RuntimeInput) -> RuntimeStepResult:
        """Advance the runtime by one bounded command."""

    @abstractmethod
    def checkpoint(
        self,
        session_id: str,
        *,
        reason: str | None = None,
    ) -> RuntimeSnapshot:
        """Capture a checkpointable runtime snapshot."""

    @abstractmethod
    def resume(self, snapshot: RuntimeSnapshot) -> RuntimeSnapshot:
        """Resume a runtime from an accepted snapshot."""

    @abstractmethod
    def end(
        self,
        session_id: str,
        *,
        reason: str | None = None,
    ) -> RuntimeSnapshot:
        """Terminate a runtime session in a reviewable way."""
