# Alexandrian Academy Integration

## Purpose

This specification defines the integration boundary between MeshRush and Alexandrian Academy.

Alexandrian Academy is treated as the learning, evaluation, transfer, and experiment-memory plane in the wider ecosystem. MeshRush does not replace that role. MeshRush produces graph-operating episodes, traces, artifacts, probe outputs, and lifecycle evidence that Alexandrian Academy can curate into learning and evaluation objects over time.

## Role separation

Alexandrian Academy owns:

- learning-object formation
- transcript and segment curation
- evaluation archives
- policy-parameter snapshots
- governance and change records related to learning artifacts
- long-horizon experiment memory
- transfer-oriented packaging of learning outputs

MeshRush owns:

- graph-view operation
- diffusion and exploration
- stop and compile behavior
- artifact lifecycle inside runtime
- evidence and trace emission

MeshRush therefore provides learning surfaces without becoming the learning system.

## Bounded-context alignment

The visible Academy bounded contexts already suggest a natural mapping for MeshRush outputs.

MeshRush traces and artifacts may later flow into contexts such as:

- immutable artifacts or content-addressed stores
- anchors and spans into artifacts
- transcripts, captions, or segments
- learning objects, claims, rationales, and maps
- append-only change or contribution records
- evaluations and policy-parameter snapshots

This specification does not force a one-to-one mapping, but it does require MeshRush to expose outputs that can be curated into those forms later.

## Integration goals

The MeshRush ↔ Alexandrian Academy boundary must support:

- capture of graph-operating episodes as learning-relevant material
- curation of runtime traces and probe outputs into evaluable objects
- persistence of compile certificates and artifact histories as reviewable evidence
- transfer-learning use of compiled artifacts where appropriate
- experiment memory over time
- policy and strategy evolution informed by MeshRush evidence

## Learning doctrine

MeshRush should support learning by exposing high-quality operational surfaces.
These include:

- exploratory episodes
- graph-view state transitions
- frontier evolution
- probe outputs
- stop candidates
- compile decisions
- artifact lifecycle events
- reuse and dissolve events
- bounded evaluation metrics
- provenance and runtime context

MeshRush does not need to know how those are ultimately taught from, ranked, or promoted. It only needs to preserve enough structure that the learning plane can use them.

## Minimum inbound surfaces

- `PolicySnapshotRef`
- `EvaluationContext`
- `TransferContext`
- `CurriculumHint`

## Minimum outbound surfaces

- `EpisodeTrace`
- `ProbeBundle`
- `CompileCertificateRef`
- `ArtifactLifecycleRecord`
- `EvaluationInputBundle`
- `TransferArtifactRef`

## Reinforcement-learning and training stance

MeshRush is not the trainer.

But MeshRush should expose the ingredients that trainers and evaluation systems need, including:

- state-like graph-view observations
- action-like graph-operating decisions
- bounded outcomes
- evidence of stop and compile behavior
- artifact-quality signals
- reusable trace surfaces
- references to policy snapshots and evaluation contexts

That gives the learning plane enough structure to support reinforcement learning, transfer learning, curriculum learning, offline evaluation, and comparative experimentation without pushing trainer ownership into MeshRush.

## Experiment memory

Alexandrian Academy should be able to preserve and compare MeshRush-derived episodes over time.
MeshRush should therefore emit enough provenance to support questions like:

- which policy context produced this artifact
- which runtime conditions preceded this compile decision
- which probes were used
- which graph-view surface was involved
- how later episodes compared to earlier ones
- whether transfer from a prior artifact helped or harmed performance

## Transfer doctrine

Compiled artifacts may become useful transfer surfaces. This does not mean all artifacts should be transferred blindly.

The MeshRush side of the contract is simply to make transfer candidates identifiable, attributable, and bounded. The Academy side decides whether and how those candidates become learning or transfer resources.

## Evaluation doctrine

MeshRush should provide evaluation-relevant outputs without embedding the full evaluation system.
Useful conceptual outputs include:

- exploration efficiency traces
- frontier saturation signals
- stop-condition evidence
- compile acceptance or deferral outcomes
- artifact reuse histories
- dissolution or failure cases
- probe-derived behavior signatures

## Failure and negative-learning surfaces

Learning systems need failures, not only successes.
This integration should therefore preserve:

- failed exploration episodes
- rejected compile candidates
- deferred compile cases
- artifact invalidations
- regressions under changed policy context
- degraded transfer outcomes
- repeated failure motifs where discoverable

These should remain exportable from MeshRush rather than discarded.

## Boundaries on ownership

MeshRush must not become:

- the experiment archive
- the policy repository
- the evaluation service
- the learning-object canon
- the transcript or caption system
- the governance ledger

It contributes runtime evidence to those systems. It does not replace them.

## Deferred formalization

Deferred:

- exact episode schema
- exact learning-object mapping
- exact reward or evaluation hook format
- exact transfer-package schema
- exact policy snapshot reference format
- exact curation workflow into Academy bounded contexts
