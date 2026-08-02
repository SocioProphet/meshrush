"""MR-04b — exact symmetry discovery (Omni-Crystal spec §12.4 stage 3).

MR-04a *certifies* a given permutation; this module *discovers* the automorphisms.
It finds the graph's automorphism group by **backtracking search guided by the
1-WL color refinement** (MR-04a ``refine_colors``): images are drawn only from the
same color class, and every partial assignment is pruned against the weighted
adjacency already fixed. Each completed permutation is a genuine automorphism by
construction (and re-certified via MR-04a ``is_automorphism``), from which node
**orbits** are derived — the downstream product for symmetry-aware retrieval/dedup.

Licensing note (ADR-0005 D-H gate): the usual native accelerator, the ``pynauty``
binding, is **GPLv3** — incompatible with this estate's MIT/Apache-only rule — so
it is neither pinned nor vendored. Instead we ship a pure-Python exact search (our
own MIT code, always available) and expose an import-guarded seam
(``NativeSymmetryBackend``) so an operator who supplies their *own* license-cleared
binding gets the fast path. The C library ``nauty`` itself is Apache-2.0; only the
common Python wrapper is GPL.

Fail-closed on exactness: a region larger than ``max_nodes`` or a search that
exhausts ``max_steps`` returns ``exact=False`` (with the color-refinement partition
as an orbit over-approximation, or the partial automorphisms found so far) — it
never claims an exact result it did not compute.

Requires the ``scientific`` extra (``numpy``).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from meshrush.core.graph_build import WeightedGraph
from meshrush.crystal.symmetry import is_automorphism, refine_colors

# Optional native backend: a callable (graph) -> tuple[perm, ...] | None. Left None
# so nothing GPL is required; an operator may install a license-cleared binding and
# register it via set_native_backend().
NativeSymmetryBackend = Callable[[WeightedGraph], "tuple[tuple[int, ...], ...] | None"]
_NATIVE_BACKEND: "NativeSymmetryBackend | None" = None


def set_native_backend(backend: "NativeSymmetryBackend | None") -> None:
    """Register (or clear) an optional license-cleared exact-discovery backend."""
    global _NATIVE_BACKEND
    _NATIVE_BACKEND = backend


@dataclass(frozen=True)
class AutomorphismResult:
    """Discovered symmetry of a graph.

    ``automorphisms`` are the permutations found (as index tuples, identity
    included); ``orbits`` are the node partition induced by them (sorted). ``method``
    records how they were found; ``exact`` is True only when the full group was
    enumerated within budget.
    """

    automorphisms: tuple[tuple[int, ...], ...]
    orbits: tuple[tuple[int, ...], ...]
    method: str
    exact: bool

    @property
    def order(self) -> int:
        """Number of automorphisms found (the group order when ``exact``)."""
        return len(self.automorphisms)


def _orbits_from_perms(n: int, perms: "tuple[tuple[int, ...], ...]") -> tuple[tuple[int, ...], ...]:
    """Union-find over ``i ~ perm[i]`` for every permutation → sorted node orbits."""
    parent = list(range(n))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for p in perms:
        for i in range(n):
            ra, rb = find(i), find(p[i])
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)

    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return tuple(tuple(sorted(g)) for g in sorted(groups.values(), key=lambda g: g[0]))


def _orbits_from_colors(colors: np.ndarray) -> tuple[tuple[int, ...], ...]:
    """Color classes as an orbit *over-approximation* (orbits refine the partition)."""
    groups: dict[int, list[int]] = {}
    for i, c in enumerate(colors.tolist()):
        groups.setdefault(int(c), []).append(i)
    return tuple(tuple(sorted(g)) for g in sorted(groups.values(), key=lambda g: g[0]))


def _backtrack_automorphisms(
    graph: WeightedGraph, colors: np.ndarray, max_steps: int
) -> "tuple[list[tuple[int, ...]], bool]":
    """Enumerate automorphisms by color-guided, adjacency-pruned backtracking.

    Returns ``(automorphisms, completed)`` where ``completed`` is False if the step
    budget was exhausted before the search finished.
    """
    n = graph.n
    a = graph.weights
    color_targets: dict[int, list[int]] = {}
    for i in range(n):
        color_targets.setdefault(int(colors[i]), []).append(i)

    autos: list[tuple[int, ...]] = []
    perm = [-1] * n
    used = [False] * n
    steps = [0]
    blown = [False]

    def bt(pos: int) -> None:
        if blown[0]:
            return
        if pos == n:
            autos.append(tuple(perm))
            return
        for j in color_targets[int(colors[pos])]:
            if used[j]:
                continue
            # partial consistency against every already-assigned node
            ok = True
            for k in range(pos):
                if a[pos, k] != a[j, perm[k]] or a[k, pos] != a[perm[k], j]:
                    ok = False
                    break
            if not ok:
                continue
            steps[0] += 1
            if steps[0] > max_steps:
                blown[0] = True
                return
            perm[pos] = j
            used[j] = True
            bt(pos + 1)
            perm[pos] = -1
            used[j] = False
            if blown[0]:
                return

    bt(0)
    return autos, (not blown[0])


def discover_automorphisms(
    graph: WeightedGraph,
    *,
    max_nodes: int = 64,
    max_steps: int = 200_000,
    allow_native: bool = True,
) -> AutomorphismResult:
    """Discover the automorphisms (and node orbits) of ``graph``.

    Tries a registered native backend first (if any and ``allow_native``); otherwise
    runs the pure-Python exact search, falling back to the color-refinement partition
    (``exact=False``) when the region is too large or the search exceeds budget.
    """
    n = graph.n
    if n == 0:
        return AutomorphismResult((), (), method="empty", exact=True)

    if allow_native and _NATIVE_BACKEND is not None:
        native = _NATIVE_BACKEND(graph)
        if native is not None:
            perms = tuple(tuple(int(x) for x in p) for p in native)
            # certify every returned permutation before trusting a foreign backend
            for p in perms:
                if not is_automorphism(graph, np.asarray(p, dtype=int)):
                    raise ValueError("native backend returned a non-automorphism")
            return AutomorphismResult(perms, _orbits_from_perms(n, perms), method="native", exact=True)

    colors = refine_colors(graph)
    if n > max_nodes:
        # too large for exact backtracking → refinement over-approximation, fail-closed
        return AutomorphismResult((), _orbits_from_colors(colors), method="refinement", exact=False)

    autos, completed = _backtrack_automorphisms(graph, colors, max_steps)
    perms = tuple(autos)
    if not perms:  # search blew budget before finding even identity
        return AutomorphismResult((), _orbits_from_colors(colors), method="refinement", exact=False)
    orbits = _orbits_from_perms(n, perms)
    return AutomorphismResult(perms, orbits, method="backtrack", exact=completed)
