# MeshRush

MeshRush is the open protocol and reference runtime for graph-native autonomous agents operating over graph views derived from a typed hypergraph world model.

MeshRush lives in the SocioProphet ecosystem as the graph-operating runtime. It does not replace the workspace controller, execution control plane, or learning/evaluation plane. Instead, it gives agents the operational semantics they need to act on the graph:

- enter and traverse graph views
- diffuse and explore while staying grounded
- decide when diffusion should stop
- crystallize stable local structure
- persist and reuse artifacts across workspaces
- emit evidence, traces, and learning surfaces for adjacent systems

## Internal layer model

MeshRush is organized into five layers:

- `foundation` — worldview, invariants, provenance, reversibility
- `core` — primitive runtime, state model, action surfaces
- `omni` — exploratory diffusion, localization, reduction
- `crystal` — stopping, compilation, persistence, dissolution
- `adapters` — integration contracts to external systems

## Ecosystem position

MeshRush integrates with:

- **Sociosphere** for workspace/controller context
- **agentplane** for governed execution, replay, evidence, and rollout
- **Alexandrian Academy** for learning, evaluation, transfer, and experiment memory

MeshRush is therefore:

- not the platform UI
- not the workspace controller
- not the rollout/governance plane
- not the learning system
- not the docs website

## Canonical source of truth

The authoring order is:

1. `adr/` — architectural decisions
2. `specs/` — canonical protocol/runtime specifications
3. `src/` — reference implementation
4. `experiments/` — reproducible validation
5. published platform docs — reader-facing explanation

The canonical authored source of truth for MeshRush lives in `specs/`.

## Publishing model

MeshRush is intended to be developed in its own public MIT-licensed repository. Official reader-facing publication belongs in the SocioProphet platform documentation surface. This repository therefore carries canonical specifications and contributor-facing materials; the polished ecosystem-facing docs are expected to be published through the platform documentation pipeline.

## What is in this scaffold

This scaffold intentionally includes only the design gate and the first canonical specifications:

- ADR 0001 — repo charter
- ADR 0002 — source of truth
- ADR 0003 — ecosystem boundary
- ADR 0004 — publication contract
- Spec 00 — MeshRush charter
- Spec 01 — foundation
- Spec 02 — core runtime

It does **not** yet include a full runtime implementation or a standalone docs site.
