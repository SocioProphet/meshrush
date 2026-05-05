# Network Intelligence Evidence

## 1. Scope

This specification defines evidence payloads for MeshRush network-intelligence operations.

Evidence packages are intended for replay, audit, evaluation, policy review, downstream learning, and cross-repo operational intelligence.

## 2. Evidence doctrine

MeshRush evidence MUST preserve:

- graph-view identity
- transition-model semantics
- policy scope
- metric assumptions
- estimator method
- provenance references
- replayability metadata
- warnings and invalidity conditions

Metrics MUST NOT be emitted without enough context to reproduce or challenge them.

## 3. Spectral-gap evidence

```text
spectral_gap:
  graph_view_id: string
  transition_model_ref: string
  reversible_assumption: boolean
  lambda2_abs_estimate: number | null
  gap_estimate: number | null
  estimator: exact | power_iteration | lanczos | empirical_decay | unknown
  convergence_time_estimate: number | null
  norm_family: tv | l1 | l2 | pi_weighted_l2 | other
  epsilon_target: number | null
  observed_residual_decay: array
  frontier_stability_score: number | null
  confidence: number | null
  warnings: array
```

## 4. Conductance evidence

```text
conductance_evidence:
  graph_view_id: string
  transition_model_ref: string
  volume_definition: cardinality | stationary_mass | weighted_degree | capacity | policy_scope
  cut_semantics: structural | policy | trust | latency | service_boundary | semantic_cluster
  candidate_cut:
    nodes_in_s: array
    nodes_in_complement: array | null
    boundary_edges: array
  boundary_mass: number | null
  volume_s: number | null
  phi_estimate: number | null
  estimator: exact | sweep_cut | sampling | approximation | unknown
  confidence: number | null
  topology_warnings: array
```

## 5. Gossip trace evidence

```text
gossip_trace:
  graph_view_id: string
  transition_model_ref: string
  source_nodes: array
  gossip_variant: push | pull | push_pull | custom
  round_count: integer
  informed_count_by_round: array
  frontier_by_round: array
  crossing_events: array
  completion_threshold: number
  completion_round: integer | null
  spread_time_estimate: number | null
  conductance_estimate_ref: string | null
  warnings: array
```

## 6. Cheeger consistency evidence

```text
cheeger_consistency:
  graph_view_id: string
  transition_model_ref: string
  reversible_assumption: boolean
  conductance_ref: string
  spectral_gap_ref: string
  phi_estimate: number | null
  gap_estimate: number | null
  cheeger_lower_bound: number | null
  cheeger_upper_bound: number | null
  normalized_volume_model: cardinality | stationary_mass | weighted_degree | capacity | policy_scope
  consistent: boolean | null
  consistency_class: consistent | suspect | invalid_assumptions | insufficient_evidence
  inconsistency_reason: array
```

## 7. Katz relevance evidence

```text
katz:
  graph_view_id: string
  adjacency_ref: string
  beta_ref: string
  graph_view_policy_scope: string
  edge_weight_semantics: string
  directed: boolean
  normalized: boolean
  alpha: number
  spectral_radius_estimate: number | null
  convergence_safe: boolean
  top_nodes: array
  walk_depth_truncation: integer | null
  residual_norm: number | null
  solver:
    method: direct | iterative | truncated_series
    tolerance: number | null
    iterations: integer | null
  score_units: relative_relevance
  score_normalization: none | l1 | l2 | max
```

## 8. Exp-min estimator evidence

```text
exp_min_estimator:
  graph_view_id: string
  estimator_target: node_count | value_sum | weighted_mass | custom
  rate_source: unit | node_value | edge_value | policy_weight | custom
  rate_semantics: string
  trial_count: integer
  minima: array
  sum_of_minima: number
  estimator:
    consistent: number | null
    unbiased_corrected: number | null
    bias_note: upward_biased_if_using_L_over_sum | corrected | unknown
  confidence:
    method: gamma_chi_square | bootstrap | none | unknown
    level: number | null
    lower: number | null
    upper: number | null
  rng:
    seed_ref: string | null
    generator: string | null
    replayable: boolean
  gossip_min:
    traces_ref: string | null
    all_trials_converged: boolean
    failed_trials: array
  validation:
    all_rates_nonnegative: boolean
    zero_rate_policy: excluded | included_as_never_wins | error
    graph_connected_for_estimator_scope: boolean | null
  warnings: array
```

## 9. Gossip-min trace

```text
gossip_min_trace:
  graph_view_id: string
  trial_id: string
  source_node_of_min: string | null
  min_value: number | null
  round_count: integer
  nodes_that_observed_min: integer
  completion_fraction: number
  completion_round: integer | null
  cut_warnings: array
  stalled_frontier: boolean
  convergence_status: complete | partial | failed | unknown
```

## 10. Evidence validity

An evidence package SHOULD be marked invalid or partial when:

- graph scope is disconnected but treated as connected
- policy partitions are ignored
- directed graph assumptions are silently treated as undirected
- weighted edges lack semantics
- random seeds are not replayable when replay is required
- gossip-min has not converged
- estimator rates are negative
- transition model is not row-stochastic or not normalized

## 11. Cross-plane consumers

- agentplane consumes run manifests, replayable traces, rollout metadata, and evidence packages.
- memory-mesh persists reusable traces, estimator receipts, and local graph artifacts.
- global-devsecops-intelligence consumes topology risk, bottleneck, partial-visibility, and propagation warnings.
- agent-registry exposes network-intelligence capabilities.
- socioprophet-agent-standards defines vocabulary and contract language.
