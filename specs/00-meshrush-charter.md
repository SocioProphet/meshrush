# MeshRush Charter

## 1. Name and purpose

MeshRush is the open protocol and reference runtime for graph-native autonomous agents operating over graph views derived from a typed hypergraph world model.

Its purpose is to define the operational semantics agents need in order to act on the world model in a grounded but autonomous way.

## 2. Problem statement

A rich world representation alone is not sufficient for autonomous agency.
Agents require an operational layer that tells them how to:

- enter a graph view of the world
- explore without losing grounding
- move from broad diffusion to local commitment
- recognize when continued exploration is no longer useful
- compile stable local structure
- preserve and reuse those structures across workspaces and time

MeshRush exists to provide that operational layer.

## 3. Runtime doctrine

MeshRush is built on four runtime commitments:

### 3.1 Observation before commitment

Agents should form graph-operating views from available observations, context, and prior artifacts before making hard commitments.

### 3.2 Diffuse before crystallize

Exploration is necessary before stable local structure can be compiled.
Diffusion without stopping never becomes actionable.
Crystallization without prior diffusion becomes brittle or uninformed.

### 3.3 Grounding during autonomy

Agent autonomy is only useful when actions remain anchored to graph structure, workspace context, provenance, and evidence.

### 3.4 Reversibility and evidence

Every meaningful MeshRush action should be inspectable, replayable, and attributable to a trace, context, or artifact history.

## 4. Internal layer model

MeshRush is organized into five layers.

### Foundation
Worldview, invariants, provenance, reversibility, workspace semantics, compile/dissolve lifecycle.

### Core
Primitive runtime, graph action surfaces, state model, artifact lifecycle, evidence emission.

### Omni
Exploratory diffusion, localization, reduction, observation-driven graph operations.

### Crystal
Stopping, bounded compilation, symmetry reasoning, persistence, annealing, dissolution.

### Adapters
Integration contracts for Sociosphere, agentplane, Alexandrian Academy, and future consumers.

## 5. Ecosystem position

MeshRush is part of the SocioProphet ecosystem.
It integrates with other planes but does not replace them.

- Sociosphere provides workspace/controller context.
- agentplane provides governed execution, replay, evidence, and rollout control.
- Alexandrian Academy provides learning, evaluation, transfer, and experiment memory.

MeshRush is therefore the graph-operating runtime, not the control plane, not the learning plane, and not the platform itself.

## 6. Canonical publishing rule

The canonical authored description of MeshRush lives in this repository.
The official public reading experience is expected to be published through the SocioProphet platform documentation surface.
