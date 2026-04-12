# ADR 0003: Ecosystem Boundary

- Status: Accepted (design baseline)
- Date: 2026-03-31
- Owner: SocioProphet / MeshRush

## Decision

MeshRush is the graph-operating runtime for autonomous agents acting over graph views derived from a hypergraph world model.

MeshRush integrates with adjacent systems but does not absorb their responsibilities.

- Sociosphere — workspace/controller layer
- agentplane — governed execution and rollout layer
- Alexandrian Academy — learning, evaluation, transfer, and experiment-memory layer

## MeshRush owns

- graph entry and traversal
- diffusion and exploration
- grounding during exploration
- stop conditions
- crystallization / bounded compilation
- artifact persistence and reuse
- telemetry, traces, and evidence emission
- graph-view interfaces derived from the underlying hypergraph model

## MeshRush does not own

- workspace orchestration
- governance gates
- rollout approval policy
- RL trainer implementation
- long-term learning-object storage
- evaluation archive ownership
- product UI
- website publishing infrastructure
