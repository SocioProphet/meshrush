# Omni Diffusion

## Purpose

Omni is the exploratory diffusion and reduction layer inside MeshRush.

Its purpose is to let agents move through graph-derived runtime views in a grounded way, gather local structure, expand or contract their frontier of attention, and surface candidate stopping conditions without prematurely hardening the result into an artifact.

Omni is the part of MeshRush that says:
explore first, reduce while exploring, and expose when continued diffusion may no longer be worth its cost.

## Role inside MeshRush

MeshRush is the graph-operating runtime.

Within MeshRush:

- Foundation defines invariants
- Core defines the primitive runtime loop
- Omni defines exploratory diffusion and reduction
- Crystal defines bounded stopping and compilation
- Adapters define external integration boundaries

Omni is therefore not a standalone product or parallel runtime.
It is an internal layer that prepares bounded structure for Crystal.

## Problem statement

Agents acting on a graph or graph-derived view need more than raw traversal.
They need a controlled way to expand outward from a local grounding point, accumulate structure, and decide whether exploration is still yielding useful signal.

Without Omni, agents either:

- remain too local and fail to discover meaningful structure, or
- diffuse indefinitely and fail to converge to reusable local knowledge

Omni exists to solve that problem.

## Inputs

Omni operates on runtime graph views derived from the wider world model.

Typical inputs include:

- a graph view, projection, neighborhood, or local slice derived from a canonical hypergraph world model
- a current grounding state
- one or more seed nodes, regions, or anchors
- local context from the Core runtime
- optional policy hints or strategy parameters supplied through integrations
- prior artifacts or resumes supplied by Crystal or external systems

Omni may consume guidance from external systems, but it does not own rollout policy, curriculum, or learning control.

## Outputs

Omni emits exploratory products rather than final compiled artifacts.

Its outputs include:

- diffusion traces
- frontier state
- relevance or salience gradients
- reduced local views
- probe responses
- candidate stopping signals
- candidate bounded regions for compilation
- evidence surfaces for replay, evaluation, and learning integrations

These outputs are handed to Core, Crystal, and adapters rather than treated as final truth.

## Non-goals

Omni does not own:

- final compile authority
- artifact persistence policy
- rollout governance
- RL trainer logic
- long-term learning-object storage
- evaluation archive ownership
- website/publication concerns

Those remain outside the Omni layer.

## Runtime concepts

### Graph view

A graph view is the navigable operational surface presented to an agent at runtime.
It may be a projection, neighborhood graph, induced subgraph, typed slice, or other graph-derived structure from the wider hypergraph world model.

### Grounding state

Grounding state identifies where the agent is operating, what local context anchors that operation, and which graph-derived surface is currently authoritative for action.

### Diffusion frontier

The diffusion frontier is the evolving boundary between explored and not-yet-explored local structure.

### Reduction surface

A reduction surface is the simplified or compressed local picture that Omni maintains while exploring.
This may be geometric, spectral, topological, statistical, or policy-informed.

### Stop candidate

A stop candidate is a signal that continued diffusion may no longer be justified.
Omni does not finalize that decision, but it must surface it.

### Probe family

A probe family is a controlled set of interventions or measurements used to test local behavior during exploration.
Probe outputs may later support compile certification, replay, evaluation, or learning.

## Core responsibilities

Omni is responsible for:

1. building or selecting the runtime graph view used for exploration
2. seeding the diffusion process from an initial grounding state
3. expanding through the graph view while preserving local provenance
4. maintaining a representation of the active frontier
5. reducing or compressing local structure as diffusion evolves
6. surfacing candidate stop conditions
7. emitting evidence and traces suitable for downstream replay, evaluation, and compilation

## Baseline runtime loop

The Omni layer participates in the MeshRush runtime loop as follows:

1. receive a grounded graph view from Core
2. initialize one or more seeds, anchors, or entry points
3. diffuse outward through the graph view
4. update local relevance, salience, or support estimates
5. maintain a reduced representation of the explored region
6. evaluate whether the diffusion frontier is still productive
7. emit stop candidates and candidate bounded regions
8. hand bounded candidates to Crystal for compile evaluation
9. emit traces and evidence to adapters

## Diffusion doctrine

Omni follows five operational principles.

### Local-first expansion

Diffusion begins from grounded local anchors, not from an unbounded global sweep.

### Evidence-preserving exploration

Every meaningful expansion step should be attributable to a graph view, a frontier state, and a runtime context.

### Reversible exploration

Diffusion is exploratory, not declarative.
Regions may be revisited, narrowed, re-expanded, or abandoned.

### Reduction during motion

Omni should reduce while exploring rather than waiting until the entire space has been traversed.

### Stop-surface generation

Omni is responsible for surfacing when continued diffusion may have diminishing value.

## Stop-surface categories

Omni should be able to surface at least the following stop-candidate categories.

### Frontier exhaustion

The local frontier no longer yields significant new reachable structure under current constraints.

### Signal saturation

Newly explored structure resembles already-explored structure strongly enough that marginal gain is low.

### Coherence concentration

A bounded region begins to exhibit stronger internal coherence than external relevance.

### Budget exhaustion

Operational budgets such as time, expansion count, or probe budget indicate diffusion should pause or hand off.

### Policy-directed pause

An external policy or control-plane integration requests pause, checkpoint, or staged handoff.

Omni may emit one or more of these signals simultaneously.
Crystal determines whether they justify bounded compilation.

## Reduction and representation

Omni is allowed to maintain reduced local representations of explored structure.
Those representations may eventually include:

- neighborhood summaries
- path summaries
- support fields
- cluster candidates
- spectral or diffusion coordinates
- local topological signatures
- frontier envelopes
- probe-response summaries

The exact mathematical forms are deferred to later technical specifications and implementation passes.

## Relationship to Crystal

Omni and Crystal are coupled but distinct.

Omni explores.  
Crystal stops and compiles.

Omni may say:
“this region appears bounded, coherent, and worth evaluating.”

Crystal may then decide:
“this region satisfies compile conditions and should become a reusable artifact.”

Omni therefore prepares bounded candidates.
Crystal confers compiled status.

## Integration surfaces

Omni must expose outputs useful to the rest of the ecosystem.

### Core integration

Omni receives graph views and grounding state from Core and returns frontier state, exploratory traces, and stop candidates.

### Crystal integration

Omni hands candidate bounded regions, local evidence, and stop-surface information to Crystal.

### Sociosphere integration

Omni should be able to reflect workspace or context constraints back into diffusion behavior through adapter-defined boundaries.

### agentplane integration

Omni should emit replayable exploration traces, evidence packages, and checkpointable diffusion sessions suitable for governed execution and rollout.

### Alexandrian Academy integration

Omni should emit trajectories, probe outputs, local exploration episodes, and other learning-relevant traces that can be curated outside MeshRush.

## Canonical output surfaces

The canonical conceptual outputs of Omni are:

- `GraphView`
- `GroundingState`
- `DiffusionSession`
- `FrontierState`
- `ReductionState`
- `StopCandidate`
- `ProbeBundle`
- `ExplorationTrace`

These are conceptual names at this stage.
Formal schemas are deferred.

## Constraints

Omni implementations must preserve the following constraints.

### No detached diffusion

Exploration must remain tied to a specific graph view and grounding context.

### No silent compile

Omni may produce stop candidates but must not silently treat a candidate as a compiled artifact.

### No erased provenance

Exploration traces and supporting evidence must remain exportable.

### No ownership creep

Omni must not absorb responsibilities that belong to Crystal, agentplane, Alexandrian Academy, or Sociosphere.

## Deferred formalization

The following are intentionally deferred to later specs and implementation:

- exact diffusion operators
- exact reduction math
- exact probe families
- exact stop metrics
- exact frontier update equations
- exact serialization of Omni outputs

## Consequences

### Positive

- agents gain a disciplined exploratory layer
- diffusion becomes grounded and auditable
- bounded candidates become available for Crystal without collapsing exploration into premature commitment
- learning and evaluation systems receive rich exploratory traces

### Tradeoffs

- Omni adds runtime complexity
- stop-surface quality matters significantly
- reduced representations can distort local structure if handled poorly
- poor boundary discipline would let Omni expand into Crystal or learning concerns
