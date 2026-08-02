"""MR-01 — observation-first graph construction (SP-ARCH-000 / meshrush ADR 0005).

Build a weighted, undirected graph from embedded observation windows via a
symmetrized k-nearest-neighbour Gaussian affinity, and expose the two operators
the Omni-Crystal engine reasons over:

- ``L = D - W``  — the (unnormalized) graph Laplacian (dynamics / interface cost),
- ``P = D^-1 W`` — the row-stochastic random-walk / transition operator whose
  leading eigenvectors are the diffusion coordinates (see ``omni.reduction``).

This is the scientific-engine substrate; the ``Basic*`` sessions remain the
dependency-free fallback. Requires the ``scientific`` extra (``numpy``), which is
cataloged as internal-operations vendored IP (``ds.internal_ops.libraries.numpy``).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class WeightedGraph:
    """A weighted undirected graph over observation nodes.

    ``weights`` is a symmetric ``(n, n)`` affinity matrix with a zero diagonal;
    ``degrees`` is the row-sum vector ``D_ii = sum_j W_ij``.
    """

    node_ids: tuple[str, ...]
    weights: np.ndarray
    degrees: np.ndarray

    @property
    def n(self) -> int:
        return len(self.node_ids)


def _pairwise_sq_distances(x: np.ndarray) -> np.ndarray:
    sq = np.einsum("ij,ij->i", x, x)
    d2 = sq[:, None] + sq[None, :] - 2.0 * (x @ x.T)
    # Numerical floor: distances are non-negative; the diagonal is exactly zero.
    np.fill_diagonal(d2, 0.0)
    return np.maximum(d2, 0.0)


def build_knn_graph(
    embeddings,
    node_ids: "tuple[str, ...] | list[str] | None" = None,
    *,
    k: int | None = None,
    sigma: float | None = None,
) -> WeightedGraph:
    """Build a symmetrized kNN Gaussian-affinity graph from ``embeddings``.

    Parameters
    ----------
    embeddings : array-like ``(n, d)``
        One embedded observation window per row.
    node_ids : optional
        Stable identifiers; defaults to ``("n0", "n1", ...)``.
    k : int, optional
        Neighbours per node (excluding self). Defaults to ``min(10, n - 1)``.
    sigma : float, optional
        Fixed Gaussian bandwidth. When ``None`` (default) a **self-tuning**
        per-node bandwidth is used: ``sigma_i`` is the distance to node ``i``'s
        ``k``-th neighbour (Zelnik-Manor & Perona), and the kernel for edge
        ``(i, j)`` is ``exp(-||x_i - x_j||^2 / (sigma_i * sigma_j))``.

    The affinity is restricted to the **union** of the two kNN sets
    (``j in kNN(i)`` or ``i in kNN(j)``), then symmetrized — so the result is a
    genuine undirected graph.
    """
    x = np.asarray(embeddings, dtype=float)
    if x.ndim != 2:
        raise ValueError("embeddings must be a 2-D array of shape (n, d)")
    n = x.shape[0]
    if n < 2:
        raise ValueError("need at least 2 observation windows to build a graph")

    if k is None:
        k = min(10, n - 1)
    if not (1 <= k <= n - 1):
        raise ValueError(f"k must be in [1, n-1] = [1, {n - 1}], got {k}")

    if node_ids is None:
        ids = tuple(f"n{i}" for i in range(n))
    else:
        ids = tuple(node_ids)
        if len(ids) != n:
            raise ValueError("node_ids length must match number of embeddings")

    d2 = _pairwise_sq_distances(x)

    # k nearest neighbours per row (exclude self at rank 0).
    order = np.argsort(d2, axis=1)
    knn_idx = order[:, 1 : k + 1]

    # Bandwidths.
    if sigma is None:
        kth = d2[np.arange(n), knn_idx[:, -1]]
        scale_i = np.sqrt(kth)
        # Guard against coincident points collapsing the bandwidth to zero.
        floor = np.median(scale_i[scale_i > 0]) if np.any(scale_i > 0) else 1.0
        scale_i = np.where(scale_i > 0, scale_i, floor)
        denom = scale_i[:, None] * scale_i[None, :]
    else:
        if sigma <= 0:
            raise ValueError("sigma must be > 0")
        denom = np.full((n, n), sigma * sigma, dtype=float)

    affinity = np.exp(-d2 / denom)

    # Symmetric kNN adjacency: union of the directed kNN relations.
    adj = np.zeros((n, n), dtype=bool)
    rows = np.repeat(np.arange(n), k)
    adj[rows, knn_idx.reshape(-1)] = True
    adj = adj | adj.T
    np.fill_diagonal(adj, False)

    w = np.where(adj, affinity, 0.0)
    w = 0.5 * (w + w.T)
    np.fill_diagonal(w, 0.0)

    degrees = w.sum(axis=1)
    return WeightedGraph(node_ids=ids, weights=w, degrees=degrees)


def laplacian(graph: WeightedGraph) -> np.ndarray:
    """Unnormalized graph Laplacian ``L = D - W`` (rows sum to zero)."""
    return np.diag(graph.degrees) - graph.weights


def transition(graph: WeightedGraph) -> np.ndarray:
    """Row-stochastic random-walk operator ``P = D^-1 W`` (rows sum to one).

    Raises if any node is isolated (zero degree), since ``P`` is then undefined.
    """
    if np.any(graph.degrees <= 0.0):
        raise ValueError("graph has an isolated node (zero degree); P is undefined")
    return graph.weights / graph.degrees[:, None]
