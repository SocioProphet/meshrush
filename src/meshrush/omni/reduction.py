"""MR-01 — diffusion-coordinate reduction (Coifman/Nadler diffusion maps).

The random-walk operator ``P = D^-1 W`` is not symmetric, but it is *similar* to
the symmetric matrix ``M = D^-1/2 W D^-1/2`` (``P = D^-1/2 M D^1/2``). We therefore
diagonalize the symmetric ``M`` with a stable symmetric eigensolver and map its
eigenvectors back to ``P``'s right eigenvectors ``phi = D^-1/2 v``. The leading
non-trivial eigenvectors, scaled by their eigenvalues, are the diffusion
coordinates — the slow variables of the diffusion, i.e. the reduced geometry the
Omni layer explores and the Crystal layer condenses.

The top eigenpair of ``M`` is trivial (eigenvalue 1, eigenvector ``∝ sqrt(D)``,
the stationary distribution) and is dropped.

Requires the ``scientific`` extra (``numpy``); see ``core.graph_build``.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from meshrush.core.graph_build import WeightedGraph, is_connected


@dataclass(frozen=True)
class DiffusionMap:
    """Reduced diffusion geometry.

    ``eigenvalues`` are the leading non-trivial eigenvalues of ``P`` in
    descending order; ``coordinates`` is the ``(n, n_coords)`` diffusion embedding
    ``Psi_i = (lambda_1^t phi_1(i), ..., lambda_r^t phi_r(i))``.
    """

    node_ids: tuple[str, ...]
    eigenvalues: np.ndarray
    coordinates: np.ndarray

    @property
    def n_coords(self) -> int:
        return int(self.coordinates.shape[1])


def diffusion_coordinates(
    graph: WeightedGraph,
    n_coords: int = 8,
    *,
    t: int = 1,
) -> DiffusionMap:
    """Compute the leading ``n_coords`` diffusion coordinates at diffusion time ``t``.

    Parameters
    ----------
    graph : WeightedGraph
        A connected weighted graph (no isolated nodes).
    n_coords : int
        Number of non-trivial coordinates to return. Clamped to ``n - 1``.
    t : int
        Diffusion time; coordinates are scaled by ``lambda^t``.
    """
    if n_coords < 1:
        raise ValueError("n_coords must be >= 1")
    if t < 0:
        raise ValueError("t must be >= 0")
    n = graph.n
    if n < 2:
        raise ValueError("diffusion reduction needs at least 2 nodes")
    d = graph.degrees
    if np.any(d <= 0.0):
        raise ValueError("graph has an isolated node (zero degree); reduction is undefined")
    # Fail closed on disconnected graphs: the stationary eigenpair is then
    # degenerate (one per component), so the trivial pair we drop is not unique
    # and the returned coordinates would be misleading.
    if not is_connected(graph):
        raise ValueError(
            "graph is disconnected; diffusion coordinates are ambiguous "
            "(reduce each connected component separately)"
        )

    r = min(n_coords, n - 1)

    inv_sqrt_d = 1.0 / np.sqrt(d)
    # Symmetric conjugate of P. Symmetrize to kill round-off asymmetry.
    m = inv_sqrt_d[:, None] * graph.weights * inv_sqrt_d[None, :]
    m = 0.5 * (m + m.T)

    # eigh returns ascending eigenvalues with orthonormal eigenvectors.
    vals, vecs = np.linalg.eigh(m)
    # Descending order.
    vals = vals[::-1]
    vecs = vecs[:, ::-1]

    # Right eigenvectors of P: phi = D^-1/2 v.
    phi = inv_sqrt_d[:, None] * vecs

    # Drop the trivial stationary pair (index 0), take the next r.
    sel_vals = vals[1 : 1 + r]
    sel_phi = phi[:, 1 : 1 + r]

    scale = sel_vals ** t if t != 1 else sel_vals
    coords = sel_phi * scale[None, :]

    return DiffusionMap(
        node_ids=graph.node_ids,
        eigenvalues=sel_vals.copy(),
        coordinates=coords,
    )


def diffusion_distance(dmap: DiffusionMap, i: int, j: int) -> float:
    """Euclidean distance between two nodes in the diffusion embedding.

    This is the diffusion distance (at the map's time ``t``): small between nodes
    the random walk mixes between quickly, large across bottlenecks.
    """
    delta = dmap.coordinates[i] - dmap.coordinates[j]
    return float(np.sqrt(np.dot(delta, delta)))
