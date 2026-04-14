# Core Runtime

## 1. Scope

The core runtime defines the primitive operational loop by which an autonomous agent acts through MeshRush on graph views derived from the world model.

The core runtime is intentionally smaller than the full Omni and Crystal layers.
It does not prescribe every diffusion model or every compile certificate.
Instead, it defines the stable runtime contract those layers plug into.

## 2. Runtime objects

The core runtime reasons over six primary object classes.

### 2.1 Graph view

A navigable graph-derived surface extracted from the broader world model.
A graph view is the immediate operating substrate for an agent.

### 2.2 Agent context

The runtime state associated with an acting agent, including workspace context, policy context, prior artifacts, and local operational memory.

### 2.3 Diffusion state

A transient exploratory state indicating current spread, attention, activation, or traversal pressure over the graph view.

### 2.4 Stop state

A decision state indicating whether continued diffusion remains useful or whether bounded local structure should be compiled.

### 2.5 Artifact

A bounded local structure compiled from graph activity and retained with provenance for reuse, replay, evaluation, or transfer.

### 2.6 Evidence package

A structured emission containing traces, metrics, context, and artifact references suitable for external control and learning systems.

## 3. Primitive runtime loop

The baseline MeshRush runtime loop is:

1. ingest graph view and agent context
2. initialize or resume diffusion state
3. traverse or diffuse through the graph view
4. evaluate local relevance, boundedness, and stability
5. decide whether to continue diffusion or stop
6. if stopping is warranted, compile a bounded artifact
7. emit evidence and updated context
8. hand off results to adapters and downstream systems

This loop is intentionally generic so that multiple diffusion, stopping, and compile strategies can be implemented without breaking the runtime contract.

## 4. Stop/continue boundary

The most important runtime decision is whether to continue exploring or to crystallize.

The runtime therefore requires a stable stop/continue interface:

- `continue` means additional exploration is justified
- `stop` means bounded local structure is stable enough to compile
- `defer` means insufficient evidence exists for either decision

Omni is responsible for enriching the exploration side of this boundary.
Crystal is responsible for enriching the compile side of this boundary.
The core runtime only guarantees that the boundary exists and that decisions are emitted in a traceable form.

## 5. Artifact lifecycle contract

The core runtime defines the following artifact lifecycle states:

- candidate
- compiled
- persisted
- reused
- annealed
- merged
- dissolved
- deprecated

Not every artifact must pass through every state, but all artifact implementations must preserve provenance across state transitions.

## 6. Adapter contract surfaces

The core runtime must expose enough structure for external systems to integrate cleanly.

### 6.1 Sociosphere-facing surface

- workspace context input
- session/run identifiers
- artifact persistence hooks
- state handoff points

### 6.2 agentplane-facing surface

- run manifests or run context
- replayable traces
- evidence packages
- rollout metadata
- versioned artifact references

### 6.3 Alexandrian Academy-facing surface

- trajectories and episodes
- compiled artifact records
- probe/evaluation outputs
- policy-context references
- error/failure cases suitable for learning or review

## 7. Minimal execution contract

Any MeshRush-compatible runtime implementation must be able to:

- accept a graph view and context
- produce a traversed or diffused operational state
- expose a stop/continue decision
- compile at least one bounded artifact representation
- emit an evidence package
- retain provenance across the above transitions

## 8. Out of scope for the core runtime

The core runtime does not define:

- the full Omni diffusion mathematics
- the full Crystal symmetry/compile certificate
- learning-object schemas
- rollout governance policy
- platform UI behavior

Those are defined in later layers and integration specs.
