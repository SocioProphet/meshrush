# Crystal Compile

## Purpose

Crystal is the bounded stopping, compilation, persistence, and dissolution layer inside MeshRush.

Its job is to decide when exploratory graph work should harden into reusable local structure, create a reviewable artifact from that bounded structure, preserve evidence and provenance for the compile decision, and support later reuse, anneal, merge, or dissolve behavior.

Omni explores.
Crystal stops and compiles.

## Role inside MeshRush

Within MeshRush:

- Foundation defines invariants
- Core defines the primitive runtime loop
- Omni defines exploratory diffusion and reduction
- Crystal defines bounded stopping and compilation
- Adapters define ecosystem integration boundaries

Crystal is an internal runtime layer, not a separate product and not the whole memory system.

## Problem statement

A purely diffusive runtime never stabilizes into operationally useful local structure.
At the same time, premature hardening creates brittle or unjustified artifacts.

Crystal exists to solve that tension by turning sufficiently bounded, coherent, and evidenced candidate regions into reusable artifacts without treating them as eternal truth.

## Inputs

Crystal consumes:

- candidate bounded regions from Omni
- stop-candidate signals
- graph-view context
- grounding state
- exploration traces
- probe outputs or other evidence
- prior artifacts eligible for reuse, merge, anneal, or dissolve

## Outputs

Crystal emits:

- compile decisions
- compiled artifact handles
- artifact boundaries
- compile certificates
- lifecycle events
- persistence metadata
- evidence bundles or references

## Core responsibilities

Crystal is responsible for:

1. evaluating candidate bounded regions
2. deciding accept, defer, reject, or rework
3. constructing reusable artifacts when accepted
4. attaching evidence and provenance to those artifacts
5. supporting reuse, anneal, merge, and dissolve behavior
6. emitting compile lifecycle events to the wider ecosystem

## Compile doctrine

Crystal follows five doctrines.

### Boundedness before commitment
Only bounded local structure is eligible for compilation.

### Evidence before persistence
A candidate must carry enough supporting evidence to justify artifact status.

### Reuse without absolutization
Artifacts are reusable, but they are not permanent truth.

### Reversibility after compilation
Artifacts may be annealed, revised, merged, or dissolved.

### Provenance always travels
Artifacts retain enough context to explain where they came from and why they were compiled.

## Minimum compile conditions

At minimum, compilation should require:

- grounded candidate region
- operationally meaningful boundary
- enough internal coherence or support
- enough evidence for later review
- expected future reuse value
- provenance completeness

Formal thresholds are deferred.

## Compile outcomes

Every compile evaluation should end in one of four outcomes:

- Reject
- Defer
- Accept
- Rework

## Artifact lifecycle

Artifacts move through this conceptual lifecycle:

1. candidate surfaced
2. compile evaluation
3. compiled artifact created
4. persisted for reuse
5. reused in later runtime sessions
6. optionally annealed, merged, or revised
7. optionally dissolved back into exploratory state

## Compile certificate

Crystal should ultimately formalize a compile certificate recording:

- candidate region evaluated
- graph view used for evaluation
- grounding context
- stop surfaces that triggered review
- traces and probes supporting the decision
- artifact boundary
- decision outcome
- provenance needed for later review

Exact schema is deferred.

## Relationship to Omni

Omni provides bounded candidates and exploratory evidence.
Crystal decides whether those candidates deserve compiled status.
Crystal should never pretend it discovered the candidate itself.

## Integration surfaces

Crystal must expose outputs useful to the wider ecosystem.

### Core
Returns compile decisions, artifact handles, lifecycle events, and reuse surfaces.

### Omni
Consumes candidate regions, stop surfaces, and exploratory evidence.

### Sociosphere
Exposes enough artifact state and boundary metadata for workspace-local persistence and coordination.

### agentplane
Emits compile events, dissolve events, evidence payloads, replay identifiers, and rollout-relevant metadata.

### Alexandrian Academy
Exposes artifacts, compile certificates, lifecycle events, and related evidence as learning-relevant objects without owning their long-term storage.

## Canonical conceptual outputs

- `CompileDecision`
- `CompileCertificate`
- `Artifact`
- `ArtifactBoundary`
- `ArtifactHandle`
- `ArtifactLifecycleEvent`
- `ReuseRequest`
- `DissolutionEvent`

## Constraints

Crystal implementations must preserve:

- no compile without evidence
- no artifact without provenance
- no irreversible absolutization
- no ownership creep into control plane or learning archive

## Deferred formalization

Deferred to later specs and implementation:

- exact stop thresholds
- exact compile metrics
- exact compile certificate schema
- exact artifact serialization
- exact structural or symmetry certification logic
- exact persistence backends
- exact merge and dissolve mechanics
