# agentplane Integration

## Purpose

This specification defines the integration boundary between MeshRush and agentplane.

agentplane is treated as the execution control plane responsible for bundle validation, governed run control, evidence handling, replay, and rollout discipline. MeshRush does not replace that role. MeshRush provides the graph-operating runtime that agentplane can execute, replay, and evaluate under governance.

## Role separation

agentplane owns:

- run orchestration
- bundle validation
- governed execution
- replay surfaces
- evidence routing
- staged rollout and promotion logic

MeshRush owns:

- graph-view operation
- diffusion and exploration
- stopping surfaces
- compilation and artifact lifecycle
- runtime traces and evidence emission

MeshRush therefore integrates into agentplane as a governed runtime component, not as a control plane.

## Integration goals

The MeshRush ↔ agentplane boundary must support:

- packaging MeshRush runtime sessions as governable runs
- replayable graph-operating execution
- evidence capture tied to runtime traces and compile events
- rollout-safe routing of policies, strategies, or parameter sets into MeshRush
- staged comparison of runtime behaviors over time
- checkpointing and reproducibility at the run level

## Conceptual contract

agentplane should be treated as the run-governance shell around MeshRush runtime execution.

At a conceptual level, agentplane provides:

- run manifests
- execution bundles
- validation context
- rollout or deployment metadata
- replay or reproduction identifiers
- policy or strategy references
- evidence-collection expectations

At a conceptual level, MeshRush returns:

- runtime session traces
- graph-view action sequences
- stop and compile lifecycle events
- artifact handles and references
- evidence bundles or references
- replayable state transitions
- bounded metrics relevant to run evaluation

## Run doctrine

Every MeshRush execution under agentplane should be representable as a governed run.

A governed run should have:

- a run identifier
- an input bundle or manifest
- a strategy or policy context
- a graph-view entry context
- a replayable trace surface
- emitted evidence
- a terminal or checkpoint state

## Minimum inbound surfaces

- `RunManifest`
- `ExecutionBundleRef`
- `ValidationContext`
- `RolloutContext`
- `ReplaySeed`

## Minimum outbound surfaces

- `RunTrace`
- `EvidenceBundle`
- `LifecycleEventStream`
- `ArtifactReferenceSet`
- `OutcomeSummary`
- `ReplaySurface`

## Blue/green and A/B patterns

MeshRush itself does not own experimentation governance, but it must support it.

This integration boundary should allow agentplane to run different policy, strategy, or parameter variants against MeshRush in a controlled way.

Typical patterns include:

- A/B comparison of strategy variants
- blue or green runtime promotion
- shadow or dry-run observation
- staged rollout from sandbox to broader scope
- replay-based regression comparison

MeshRush should therefore expose stable evidence and trace surfaces so these patterns are possible. It should not define the decision policy for them.

## Replay doctrine

A replay surface should be sufficient to reconstruct or approximate:

- the runtime graph-entry context
- the action or diffusion sequence
- stop candidates
- compile decisions
- artifact lifecycle events
- emitted evidence references

Replay does not require bit-perfect determinism in all cases. It requires bounded inspectability and comparative reproducibility.

## Policy and strategy routing

agentplane may route policies, strategies, or parameters into MeshRush sessions.
MeshRush must treat these as runtime inputs rather than as ownership transfer of the learning or rollout plane.

## Evidence doctrine

Evidence emitted from MeshRush into agentplane should support:

- governance review
- replay
- regression comparison
- rollout evaluation
- failure analysis

## Failure and deferral surfaces

This integration should support:

- validation refusal before run start
- runtime refusal due to insufficient graph-view context
- compile deferral
- partial checkpoint success
- explicit run failure with attributable evidence
- artifact invalidation or dissolution during execution

## Deferred formalization

Deferred:

- exact run-manifest schema
- exact event-stream format
- exact replay encoding
- exact blue/green routing metadata
- exact evidence-payload schema
- exact checkpoint and resume wire format
