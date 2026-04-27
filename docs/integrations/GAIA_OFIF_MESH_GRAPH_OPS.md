# MeshRush Integration: GAIA / OFIF / MeshLab Graph Operations

Status: v0 integration contract

## Purpose

This document defines how MeshRush operates over graph views derived from GAIA, OFIF, Lampstand, Sherlock, Lattice Forge, SocioSphere, and SourceOS records.

MeshRush is not the world model, not the execution control plane, and not the governance layer. MeshRush is the graph-operating runtime: graph entry, diffusion, grounding, stop conditions, crystallization, bounded compilation, evidence traces, and reusable artifacts.

## Authority boundaries

| Concern | Authority |
| --- | --- |
| World-state and geospatial semantics | GAIA |
| Field events and sensor envelopes | OFIF |
| Local state sampling | Lampstand |
| Search/discovery | Sherlock Search |
| Runtime provenance | Lattice Forge |
| Workspace/fleet governance | SocioSphere |
| Governed execution/replay | Agentplane |
| Graph traversal/diffusion/crystallization | MeshRush |

## Integration doctrine

```text
GAIA / OFIF / Lampstand / Sherlock / Lattice / SocioSphere records
  -> typed graph view
  -> MeshRush diffusion
  -> evidence-grounded local structure
  -> crystallized graph artifact
  -> Agentplane governed execution if action is requested
  -> GAIA/Sherlock evidence update
```

## Graph view inputs

Initial graph-view sources:

- GAIA world-state features;
- OFIF EventEnvelopes;
- GAIA ControlTowerDecisionCards;
- GAIA RiskExposureRecords;
- MeshNodeRecords;
- SliceAllocationRecords;
- MeshTelemetryEnvelopes;
- Sherlock discovery records;
- Lattice runtime references;
- Lampstand LocalStateRecords when approved for percolation.

## Soil-intelligence graph operation example

A soil-intelligence graph view may include:

- OFIF field observation event;
- GAIA OFIF-derived world-state feature;
- GAIA EO/reanalysis context;
- GAIA soil-fusion artifact;
- GAIA soil decision card;
- MeshNodeRecord for local host;
- SliceAllocationRecord for local experiment;
- MeshTelemetryEnvelope for runtime health;
- Sherlock result record.

MeshRush operation:

1. Enter graph at the OFIF observation event.
2. Diffuse across spatial, temporal, provenance, model, and runtime links.
3. Reduce to the bounded local structure relevant to the soil decision.
4. Stop when evidence and runtime provenance are sufficient for the requested decision scope.
5. Crystallize a reusable evidence cluster.

## Navigation/control-tower graph operation example

A navigation graph view may include:

- LiDAR corridor observation;
- OFIF asset-health event;
- route plan;
- control-tower decision card;
- risk exposure record;
- work-order candidate;
- inventory node;
- Sherlock result record.

MeshRush operation:

1. Enter graph at vegetation-encroachment evidence.
2. Diffuse to route impact, asset condition, and work-order candidate.
3. Ground against confidence, policy, and safety notes.
4. Stop before action because policy requires human approval.
5. Crystallize a corridor-risk evidence cluster.

## Required MeshRush output artifact

A crystallized graph artifact should include:

- artifact ID;
- graph view ID;
- entry node refs;
- traversed node refs;
- traversed edge refs;
- stop condition;
- crystallized claims;
- evidence refs;
- policy refs;
- uncertainty/confidence notes;
- recommended next action if any;
- action boundary: advisory, approval-required, executable, blocked.

## Non-goals

- MeshRush does not mutate GAIA world-state directly.
- MeshRush does not bypass Agentplane for execution.
- MeshRush does not own OFIF event semantics.
- MeshRush does not define Lattice runtime provenance.
- MeshRush does not decide Smart Spaces domain home.

## Next implementation targets

1. Add soil-intelligence graph-view fixture.
2. Add navigation corridor-risk graph-view fixture.
3. Add a dependency-light validator for MeshRush crystallization fixtures.
4. Add Agentplane adapter contract for approval-required actions.
