# Omni Network Diffusion

## 1. Scope

This specification defines the network-intelligence primitives used by the MeshRush Omni layer to explore graph views before Crystal decides whether bounded local structure should be compiled.

The primitives in this document are operational semantics, not truth assertions. They initialize, guide, and audit graph diffusion over graph views derived from richer typed hypergraph world models.

## 2. Canonical runtime objects

### 2.1 Graph view

A graph-derived operating surface. A graph view may be unweighted, weighted, directed, policy-filtered, semantic, service-topology based, dependency-derived, or projected from a hypergraph.

### 2.2 Transition model

A row-stochastic transition matrix or equivalent transition operator over the graph view.

For an undirected unweighted lazy random walk:

```text
P = 1/2 * (I + D^-1 A)
```

where `A` is adjacency and `D` is the degree matrix.

### 2.3 Diffusion state

A transient vector, frontier, distribution, or trace describing current spread, attention, activation, or traversal pressure over the graph view.

### 2.4 Relevance prior

A pre-diffusion score or seed vector used to bias exploration without asserting truth.

## 3. Random-walk foundation

For an undirected connected graph, the lazy random walk is irreducible and aperiodic.

Its stationary distribution is:

```text
pi_i = degree_i / (2m)
```

For a symmetric weighted graph with weighted degree:

```text
s_i = sum_j W_ij
```

the stationary distribution is:

```text
pi_i = s_i / sum_l s_l
```

The reversible case satisfies detailed balance:

```text
pi_i P_ij = pi_j P_ji
```

MeshRush implementations MUST record whether a transition model is reversible, approximately reversible, non-reversible, or unknown.

## 4. Katz relevance prior

Katz centrality solves:

```text
v = alpha A v + beta
```

When `alpha < 1 / lambda_max(A)`:

```text
v = (I - alpha A)^-1 beta
  = beta + alpha A beta + alpha^2 A^2 beta + ...
```

MeshRush uses Katz as a relevance prior for Omni exploration.

Valid uses:

- rank candidate neighborhoods before deeper diffusion
- bias traversal toward workspace intent or prior artifacts
- explain multi-hop relevance through attenuated walk counts
- seed bounded candidate regions for Crystal review

Invalid uses:

- proof of truth
- governance approval
- replacement for provenance
- replacement for Crystal stop/continue decisions

## 5. Spectral stabilization feature

Let the eigenvalues of the transition operator be ordered by magnitude:

```text
1 = lambda_1, |lambda_2| >= |lambda_3| >= ...
```

Define spectral gap:

```text
g(P) = 1 - |lambda_2|
```

Approximate convergence time:

```text
T_conv(epsilon) ~= (log C + log(1/epsilon)) / g(P)
```

When exactness matters, use:

```text
T_conv(epsilon) >= log(C / epsilon) / -log(|lambda_2|)
```

## 6. Conductance feature

Lecture-style conductance over a transition matrix is:

```text
Phi(P) = min_{S subset N, |S| <= n/2} sum_{i in S, j in S^c} P_ij / |S|
```

Conductance measures boundary escape. Low conductance indicates trapped diffusion, weak boundaries, bottlenecks, policy partitions, or sparse cuts.

MeshRush implementations MUST record the volume convention used:

- cardinality
- stationary mass
- weighted degree
- capacity
- policy scope

## 7. Gossip/spread feature

For a gossip process with conductance `Phi(P)`, the lecture-level scaling is:

```text
T_spr ~= log(n) / Phi(P)
```

MeshRush uses gossip traces to test whether information actually propagated through the graph view, or whether the frontier remained trapped near its source.

## 8. Cheeger consistency

Cheeger's inequality couples conductance and spectral gap:

```text
1/2 * Phi(P)^2 <= g(P) <= 2 * Phi(P)
```

MeshRush uses this as a consistency check between cut evidence and convergence evidence.

## 9. Stop/continue impact

Omni emits diffusion features. Crystal decides whether to stop, continue, or defer.

Omni SHOULD flag:

- low spectral gap
- low conductance
- stalled gossip frontier
- graph partition or reducibility suspicion
- non-reversible transition model without fallback evidence
- inconsistent Cheeger evidence

## 10. Non-goals

This spec does not define final governance policy, UI rendering, storage backend, or the full Crystal compile certificate. It defines the Omni network-intelligence inputs that later layers consume.
