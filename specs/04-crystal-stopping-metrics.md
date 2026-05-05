# Crystal Stopping Metrics

## 1. Scope

This specification defines the topology-aware metrics that Crystal uses when deciding whether MeshRush should stop diffusion and compile bounded local structure, continue exploration, or defer because evidence is insufficient.

Crystal MUST NOT treat any single centrality, diffusion, spectral, conductance, or gossip metric as sufficient proof for crystallization.

## 2. Stop/continue states

Crystal consumes Omni evidence and emits one of three decisions:

- `continue` — additional exploration is justified
- `stop` — bounded local structure is stable enough to compile
- `defer` — assumptions or evidence are insufficient for either decision

## 3. Required evidence families

A stop/continue decision SHOULD consider:

- diffusion residuals
- frontier stability
- spectral gap evidence
- conductance or cut evidence
- gossip/spread evidence
- Cheeger consistency
- graph assumptions and transition semantics
- provenance completeness
- policy scope and graph-view authorization

## 4. Spectral-gap threshold semantics

Spectral gap is a stabilization feature.

```text
fast:
  gap high relative to graph size and expected topology
  shorter diffusion horizon may be acceptable if residual and provenance checks pass

moderate:
  require residual decay and frontier-stability evidence

slow:
  require conductance check, bottleneck inspection, longer diffusion, or defer

invalid:
  reducible, periodic, non-reversible without fallback, or policy-partitioned graph
  do not use simple lambda_2 gap as the decision basis
```

## 5. Conductance semantics

Low conductance indicates that diffusion may be trapped behind a bottleneck. Crystal SHOULD treat unresolved low-conductance cuts as evidence against broad crystallization.

Crystal MUST record whether low conductance is:

- structural
- policy-induced
- trust-induced
- latency/capacity-induced
- semantic-cluster induced
- unknown

## 6. Gossip/spread semantics

A stalled or source-region-dominated gossip trace is evidence that the graph view may not have been explored adequately.

Crystal SHOULD continue or defer when:

- the informed frontier has not crossed suspected bottlenecks
- the spread trace remains source-region dominated
- conductance is low or missing
- the completion threshold has not been met
- graph visibility is partial

## 7. Cheeger consistency guardrail

Cheeger consistency cross-checks conductance and spectral gap.

```text
1/2 * Phi(P)^2 <= g(P) <= 2 * Phi(P)
```

Crystal SHOULD flag inconsistency when spectral gap, conductance, and observed gossip behavior disagree under the recorded graph assumptions.

## 8. Stop rule

Crystal MAY emit `stop` only if:

- bounded local structure is stable
- residual diffusion change is below tolerance
- graph assumptions are recorded
- provenance is sufficient
- spectral evidence does not contradict crystallization
- conductance does not reveal unresolved bottlenecks
- gossip/spread trace is not source-region trapped
- policy scope permits artifact compilation

## 9. Continue rule

Crystal SHOULD emit `continue` if:

- residual remains high
- frontier remains unstable
- low gap suggests slow stabilization
- conductance evidence is low or missing
- gossip spread has not crossed important cuts
- candidate artifact scope is larger than evidence support

## 10. Defer rule

Crystal SHOULD emit `defer` if:

- graph assumptions are invalid or unknown
- the graph view is disconnected or policy-partitioned
- transition semantics are not reproducible
- metrics disagree and inconsistency cannot be resolved
- required provenance or authorization is missing

## 11. Artifact impact

Crystal decisions SHOULD emit bounded artifacts only with:

- decision rationale
- metric references
- graph-view ID
- transition-model reference
- evidence package reference
- replay/provenance reference

## 12. Non-goals

This spec does not choose final thresholds for all graph families. Thresholds are policy and workload dependent. It defines the evidence semantics and decision guardrails that implementations must preserve.
