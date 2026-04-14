# Foundation

## 1. World model assumption

MeshRush assumes the broader system may represent the world as a typed hypergraph or other richly relational structure.
MeshRush does not require the entire runtime substrate to expose raw hypergraph operations at every boundary.
Instead, MeshRush operates over graph views, projections, neighborhoods, traversable summaries, or other navigable graph-derived surfaces extracted from that richer world model.

This gives MeshRush two simultaneous commitments:

- the world may be richer than a plain graph
- agent operation must still remain graph-tractable

## 2. Operational invariants

The MeshRush runtime preserves the following invariants.

### 2.1 Grounding

Every exploration step must remain attributable to a graph context, workspace context, or previously compiled artifact.

### 2.2 Provenance

Operational traces, compile events, and artifacts must retain enough provenance to support replay, explanation, evaluation, or downstream learning.

### 2.3 Reversibility

Crystallized state is not absolute. Artifacts may be annealed, revised, merged, dissolved, or superseded when new evidence or better graph structure emerges.

### 2.4 Boundedness

Compiled artifacts must represent bounded local structure rather than unbounded graph fog.

### 2.5 Reusability

Artifacts should be reusable across time, tasks, and possibly workspaces when policy and context permit.

## 3. Primitive conceptual cycle

MeshRush is founded on the following cycle:

1. observe a graph view
2. diffuse through that view
3. localize structure and relevance
4. decide whether to continue or stop
5. crystallize bounded local structure
6. persist with provenance
7. reuse, anneal, or dissolve later

This cycle is the conceptual core from which Omni and Crystal derive.

## 4. Learning surfaces

MeshRush is not the learning plane, but it must expose learning-relevant surfaces.
Those include:

- observation/state surfaces
- action surfaces on graph views
- stop/continue events
- compile/dissolve events
- artifact-quality metrics
- replayable traces
- policy-context references
- reward/evaluation hooks

These surfaces exist so agentplane and Alexandrian Academy can orchestrate, evaluate, and improve agents without MeshRush needing to become the trainer or archive itself.

## 5. Workspace relationship

MeshRush does not define workspace orchestration.
It expects workspace/session context to be supplied by the adjacent controller layer.
Within a workspace, MeshRush provides graph-operating semantics and artifact lifecycle behavior suitable for local action.
Across workspaces, MeshRush may permit artifact reuse or transfer when allowed by surrounding policy and adapter contracts.

## 6. Non-goals at the foundation layer

The foundation layer does not define:

- user interface semantics
- final policy-governance rules
- rollout approval logic
- storage implementation details for all external systems
- full hypergraph algebra for every platform component

Its role is to set invariants and conceptual boundaries, not absorb the whole ecosystem.
