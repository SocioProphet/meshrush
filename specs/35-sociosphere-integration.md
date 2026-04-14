# Sociosphere Integration

## Purpose

This specification defines the integration boundary between MeshRush and Sociosphere.

Sociosphere is treated as the workspace-controller and governance-gates layer in the wider SocioProphet ecosystem. MeshRush does not replace that controller role. MeshRush consumes workspace context from it and returns runtime artifacts, traces, and state hooks that can be coordinated at the workspace level.

## Role separation

Sociosphere owns workspace composition, validation, coordination, and controller concerns.

MeshRush owns graph-operating runtime semantics for agents working inside graph views derived from the wider world model.

The integration boundary exists so that:

- MeshRush remains a reusable graph-operating runtime
- Sociosphere remains the workspace/controller layer
- runtime state can move between them without collapsing responsibilities into one repo

## Integration goals

The MeshRush ↔ Sociosphere boundary must support:

- workspace-scoped runtime initialization
- graph-view handoff into an agent runtime session
- context and policy constraints flowing into MeshRush sessions
- artifact/state hooks flowing back to workspace control
- replay and governance surfaces remaining attributable to a workspace context
- cross-workspace portability under explicit policy

## Conceptual contract

Sociosphere should be treated as the source of workspace context and controller constraints.
MeshRush should be treated as the runtime that acts within that context.

At a conceptual level, Sociosphere provides:

- workspace identity
- session identity
- actor or agent identity
- scope and boundary context
- optional policy or governance constraints
- references to relevant world-model surfaces or graph-view entry points

At a conceptual level, MeshRush returns:

- runtime session handles
- graph-view usage metadata
- exploration traces
- stop and compile events
- artifact handles
- artifact boundary metadata
- provenance or evidence references
- resume or dissolution surfaces where applicable

## Workspace doctrine

MeshRush runtime sessions are always assumed to occur inside some workspace or workspace-derived scope.
Every meaningful MeshRush runtime action should remain relatable to:

- a workspace
- a session
- an agent or actor
- a graph-view context
- a traceable runtime episode

## Minimum inbound surfaces

- `WorkspaceContext`
- `SessionContext`
- `GraphEntryContext`
- `ConstraintContext`
- `ResumeContext`

## Minimum outbound surfaces

- `RuntimeSessionHandle`
- `ExplorationTraceRef`
- `ArtifactHandleSet`
- `LifecycleEvents`
- `EvidenceBundleRef`
- `WorkspaceStateHints`

## Runtime handshake

Conceptual handshake:

1. Sociosphere establishes workspace and session context.
2. Sociosphere provides a graph-entry surface or graph-view reference.
3. MeshRush initializes a runtime session under that context.
4. MeshRush explores, stops, compiles, persists, resumes, or dissolves as needed.
5. MeshRush emits traces, artifact handles, lifecycle events, and evidence references.
6. Sociosphere uses those outputs for workspace-local coordination and persistence.

## Artifact portability

Artifacts created by MeshRush may later be reused across workspaces, but cross-workspace reuse must remain policy-aware. This spec does not define those policies. It only requires that MeshRush expose enough artifact provenance and boundary metadata for Sociosphere to make bounded portability decisions.

## Provenance rule

Every object passed across this boundary should preserve enough metadata to answer:

- which workspace did this come from
- which session produced it
- which graph view was involved
- which runtime phase produced it
- whether it is exploratory, compiled, resumed, annealed, merged, or dissolved

## Failure and deferral surfaces

This integration should also support negative or incomplete outcomes, including:

- initialization refusal
- graph-view insufficiency
- deferred compile state
- unresolved runtime state
- artifact invalidation or dissolution notice

## Deferred formalization

Deferred:

- exact request and response schemas
- exact event envelope format
- exact workspace identity model
- exact cross-workspace portability policy
- exact persistence-backend integration
