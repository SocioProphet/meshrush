"""MR-04a — symmetry certification (Omni-Crystal spec §12.4-§12.5).

The certification core of the symmetry-discovery cascade: given a candidate node
permutation, decide whether it is a (near-)symmetry of the graph, and do so
*governed* — with defect functionals, a typed prepartition, and an empirical null
so an accepted generator is one an auditor can stand behind.

- **Defect functionals** (§12.5): adjacency defect ``d_A``, feature defect ``d_X``,
  and response-transport defect ``d_R`` (from ``omni.probes.symmetry_probe``),
  combined as ``E = w_A d_A + w_X d_X + w_R d_R``.
- **Color refinement** (1-WL) — the typed prepartition / weighted role refinement
  (§12.4 stages 1-2): nodes in different colors can never be exchanged by a symmetry.
- **Empirical null** (§12.5): a candidate is accepted only if its defect is clearly
  separated from within-color random permutations — not just below a fixed tol.

Exact automorphism *discovery* (§12.4 stage 3) is implemented in
``crystal/symmetry_discovery.py`` (MR-04b) as a pure-Python, color-refinement-guided
backtracking search — the ``pynauty`` binding is GPLv3 and thus not used; this module
provides the certification that search re-verifies each discovered generator against.

Requires the ``scientific`` extra (``numpy``).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from meshrush.core.graph_build import WeightedGraph
from meshrush.omni.probes import symmetry_probe

_EPS = 1e-12


@dataclass(frozen=True)
class SymmetryDefect:
    d_adjacency: float
    d_feature: float
    d_response: float
    total: float
    accepted: bool


def permutation_matrix(perm: np.ndarray, n: int) -> np.ndarray:
    perm = np.asarray(perm, dtype=int)
    if perm.shape != (n,) or sorted(perm.tolist()) != list(range(n)):
        raise ValueError("perm must be a permutation of range(n)")
    mat = np.zeros((n, n))
    mat[perm, np.arange(n)] = 1.0
    return mat


def symmetry_defect(
    graph: WeightedGraph,
    perm,
    *,
    features: "np.ndarray | None" = None,
    w_a: float = 1.0,
    w_x: float = 1.0,
    w_r: float = 1.0,
    tol: float = 1e-6,
) -> SymmetryDefect:
    """Combined active-symmetry defect ``E(Π)`` of ``perm`` on ``graph`` (§12.5)."""
    n = graph.n
    pmat = permutation_matrix(perm, n)
    a = graph.weights

    d_a = float(np.abs(a - pmat @ a @ pmat.T).sum()) / (float(np.abs(a).sum()) + _EPS)

    if features is not None:
        x = np.asarray(features, dtype=float)
        if x.shape[0] != n:
            raise ValueError(f"features must have {n} rows")
        d_x = float(np.linalg.norm(x - pmat @ x)) / (float(np.linalg.norm(x)) + _EPS)
    else:
        d_x = 0.0
        w_x = 0.0

    d_r = symmetry_probe(graph, perm).defect

    total = w_a * d_a + w_x * d_x + w_r * d_r
    return SymmetryDefect(d_a, d_x, d_r, total, total <= tol)


def is_automorphism(graph: WeightedGraph, perm, *, tol: float = 1e-9) -> bool:
    """True iff ``perm`` preserves the weighted adjacency (``Π A Πᵀ = A``)."""
    n = graph.n
    pmat = permutation_matrix(perm, n)
    a = graph.weights
    d_a = float(np.abs(a - pmat @ a @ pmat.T).sum()) / (float(np.abs(a).sum()) + _EPS)
    return d_a <= tol


def refine_colors(graph: WeightedGraph, *, max_iter: int = 0, quantum: float = 1e-6) -> np.ndarray:
    """1-WL color refinement — the typed prepartition (§12.4). Returns an integer
    color per node; nodes with different colors cannot be exchanged by any symmetry.

    Weighted: each node's signature is its current color plus the sorted multiset of
    ``(neighbour color, quantized weight)`` — so weight structure refines roles.
    """
    if quantum <= 0:
        raise ValueError("quantum must be > 0")
    if max_iter < 0:
        raise ValueError("max_iter must be >= 0")
    n = graph.n
    w = graph.weights
    max_iter = max_iter or n
    colors = np.zeros(n, dtype=np.int64)  # start: one class

    for _ in range(max_iter):
        signatures = []
        for i in range(n):
            neigh = sorted(
                (int(colors[j]), int(round(float(w[i, j]) / quantum)))
                for j in range(n) if w[i, j] != 0.0
            )
            signatures.append((int(colors[i]), tuple(neigh)))
        # Relabel signatures to dense integer colors (stable by sorted signature).
        order = {sig: idx for idx, sig in enumerate(sorted(set(signatures)))}
        new_colors = np.array([order[s] for s in signatures], dtype=np.int64)
        if len(set(new_colors.tolist())) == len(set(colors.tolist())):
            colors = new_colors
            break
        colors = new_colors
    return colors


def survives_null(
    graph: WeightedGraph,
    perm,
    *,
    samples: int = 200,
    rng: "np.random.Generator | None" = None,
    w_a: float = 1.0,
    w_r: float = 1.0,
) -> tuple[bool, float]:
    """Empirical null (§12.5): is ``perm``'s defect clearly below within-color random
    permutations? Returns ``(survives, p_value)`` where ``p_value`` is the fraction of
    null permutations that are STRICTLY better (lower defect) than ``perm``. A real
    symmetry has p_value ~0 and survives.

    A candidate that is not color-compatible (does not preserve the refinement
    partition) cannot be a symmetry, so it is rejected up front as ``(False, 1.0)``."""
    rng = rng or np.random.default_rng(0)
    n = graph.n
    permutation_matrix(perm, n)  # validate it is a permutation of range(n)
    colors = refine_colors(graph)

    # A symmetry must preserve refinement colors; an incompatible perm is not one.
    perm_arr = np.asarray(perm, dtype=int)
    if any(int(colors[perm_arr[i]]) != int(colors[i]) for i in range(n)):
        return (False, 1.0)

    observed = symmetry_defect(graph, perm, w_a=w_a, w_x=0.0, w_r=w_r).total

    # Null: shuffle nodes only within their color class (compatible permutations).
    classes: dict[int, list[int]] = {}
    for i, c in enumerate(colors.tolist()):
        classes.setdefault(c, []).append(i)

    null_defects = []
    for _ in range(samples):
        p = np.arange(n)
        for members in classes.values():
            if len(members) > 1:
                shuffled = list(members)
                rng.shuffle(shuffled)
                p[members] = shuffled
        null_defects.append(symmetry_defect(graph, p, w_a=w_a, w_x=0.0, w_r=w_r).total)

    null_defects = np.asarray(null_defects)
    # p_value = fraction of compatible random permutations that are STRICTLY better
    # (lower defect) than the candidate. Strict comparison keeps the test meaningful
    # when refinement has already isolated the symmetry (a degenerate all-zero null:
    # a true symmetry then has p_value 0 rather than being masked by equal-defect ties).
    p_value = float(np.mean(null_defects < observed - _EPS))
    # Survives if essentially nothing compatible beats it (extreme low tail).
    return (p_value <= 0.01, p_value)
