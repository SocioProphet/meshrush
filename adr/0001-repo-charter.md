# ADR 0001: MeshRush Repo Charter

- Status: Accepted (design baseline)
- Date: 2026-03-31
- Owner: SocioProphet / MeshRush

## Context

MeshRush needs to exist as a distinct protocol/runtime boundary inside the SocioProphet ecosystem.
It is not the platform itself and not a detached documentation artifact.
It is the graph-operating runtime used by autonomous agents acting on graph views derived from a typed hypergraph world model.

## Decision

We establish `meshrush` as a public MIT-licensed repository in the SocioProphet organization.

MeshRush is defined as:

> the open protocol and reference runtime for graph-native autonomous agents operating over graph views derived from a typed hypergraph world model.

MeshRush owns:

- graph entry and traversal
- diffusion and exploration
- grounding during exploration
- stopping criteria
- crystallization / bounded compilation
- artifact persistence and reuse
- telemetry and evidence emission

MeshRush is internally organized into five layers:

1. Foundation
2. Core
3. Omni
4. Crystal
5. Adapters

## Non-goals

MeshRush does not own platform UI, workspace-controller implementation, rollout governance, RL trainer implementation, learning-object storage, or website ownership.

## Consequences

MeshRush gets a clean protocol/runtime identity with its own specifications, code, experiments, issues, and releases.
