# Random Walk Baselines

This experiment scaffold validates the smallest MeshRush network-intelligence claims against three graph families:

- path graph
- star graph
- complete graph

The goal is not performance. The goal is a reproducible evidence fixture proving that centrality, stationary mass, conductance, spectral gap, gossip spread, Cheeger consistency, and exp-min distributed aggregation are distinct but coupled diagnostics.

## Expected lessons

### Path

- low conductance
- slow spread
- slow mixing
- corridor bottleneck

### Star

- high hub stationary mass / degree centrality
- weak cuts under the lecture cardinality conductance convention
- hubness is not resilience

### Complete

- high conductance
- fast spread
- fast mixing
- boundary-rich topology

## Script

`path_star_complete.py` is a self-contained scaffold using the Python standard library. It emits JSON-like summaries for:

- graph family
- transition model
- stationary distribution
- candidate conductance estimate
- gossip spread rounds
- Cheeger-style consistency notes
- exp-min node-count estimate

The spectral gap field is a placeholder unless a later implementation adds a numerical linear algebra backend. The spec requires spectral evidence; this scaffold is intentionally conservative rather than silently emitting fake eigenvalues.

## Future hardening

- add deterministic numpy/scipy-backed spectral-gap calculation
- add exact conductance enumeration for larger graph families behind a size guard
- add JSON schema validation against `schemas/evidence/network-intelligence-event.schema.json`
- emit one evidence file per graph family
- wire the experiment into CI once the runtime layout is stable
