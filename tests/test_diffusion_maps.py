import math
import unittest

import numpy as np

from meshrush.core.graph_build import build_knn_graph
from meshrush.omni.reduction import (
    DiffusionMap,
    diffusion_coordinates,
    diffusion_distance,
)


def _ring_embeddings(n: int) -> list[list[float]]:
    return [[math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)] for i in range(n)]


class DiffusionMapTests(unittest.TestCase):
    def test_eigenvalues_descending_and_bounded(self) -> None:
        g = build_knn_graph(_ring_embeddings(16), k=3)
        dmap = diffusion_coordinates(g, n_coords=5)
        vals = dmap.eigenvalues
        # Descending.
        self.assertTrue(np.all(np.diff(vals) <= 1e-9))
        # Eigenvalues of a stochastic operator lie in [-1, 1]; the trivial 1 is dropped.
        self.assertTrue(np.all(vals <= 1.0 + 1e-9))
        self.assertTrue(np.all(vals >= -1.0 - 1e-9))
        self.assertLess(float(vals[0]), 1.0)  # trivial eigenvalue was removed

    def test_shape_and_clamping(self) -> None:
        g = build_knn_graph(_ring_embeddings(6), k=2)
        dmap = diffusion_coordinates(g, n_coords=99)  # clamp to n-1
        self.assertIsInstance(dmap, DiffusionMap)
        self.assertEqual(dmap.coordinates.shape, (6, 5))
        self.assertEqual(dmap.n_coords, 5)

    def test_ring_preserves_locality(self) -> None:
        # On a ring, adjacent nodes must be closer in diffusion space than antipodal
        # nodes — the defining property of a manifold-respecting embedding.
        n = 16
        g = build_knn_graph(_ring_embeddings(n), k=2)
        dmap = diffusion_coordinates(g, n_coords=3)
        neighbor = diffusion_distance(dmap, 0, 1)
        antipodal = diffusion_distance(dmap, 0, n // 2)
        self.assertLess(neighbor, antipodal)

    def test_dumbbell_leading_coordinate_separates_lobes(self) -> None:
        # A connected "dumbbell": two 4-cliques joined by one weak bridge. It has a
        # clear spectral gap, so the eigenvalue 1 is simple and the FIRST non-trivial
        # diffusion coordinate is the unique Fiedler-like contrast that separates the
        # two lobes by sign. This validates the clustering behaviour deterministically.
        from meshrush.core.graph_build import WeightedGraph

        n = 8
        w = np.zeros((n, n))
        for group in (range(4), range(4, 8)):
            for i in group:
                for j in group:
                    if i != j:
                        w[i, j] = 1.0
        w[3, 4] = w[4, 3] = 0.05  # weak bridge
        graph = WeightedGraph(
            node_ids=tuple(f"n{i}" for i in range(n)),
            weights=w,
            degrees=w.sum(axis=1),
        )

        dmap = diffusion_coordinates(graph, n_coords=1)
        c0 = dmap.coordinates[:, 0]
        self.assertTrue(np.all(np.abs(c0) > 1e-9), "contrast coordinate should be non-zero")
        signs = np.sign(c0)
        self.assertEqual(len(set(signs[:4])), 1, "lobe A shares a sign")
        self.assertEqual(len(set(signs[4:])), 1, "lobe B shares a sign")
        self.assertNotEqual(signs[0], signs[4], "the two lobes are on opposite sides")

    def test_invalid_args_raise(self) -> None:
        g = build_knn_graph(_ring_embeddings(6), k=2)
        with self.assertRaises(ValueError):
            diffusion_coordinates(g, n_coords=0)
        with self.assertRaises(ValueError):
            diffusion_coordinates(g, n_coords=2, t=-1)

    def test_disconnected_graph_is_refused(self) -> None:
        # Two 3-cliques, no bridge: the stationary eigenpair is degenerate, so
        # the reduction must fail closed rather than return ambiguous coordinates.
        from meshrush.core.graph_build import WeightedGraph

        n = 6
        w = np.zeros((n, n))
        for group in (range(3), range(3, 6)):
            for i in group:
                for j in group:
                    if i != j:
                        w[i, j] = 1.0
        graph = WeightedGraph(
            node_ids=tuple(f"n{i}" for i in range(n)),
            weights=w,
            degrees=w.sum(axis=1),
        )
        with self.assertRaises(ValueError):
            diffusion_coordinates(graph, n_coords=2)


if __name__ == "__main__":
    unittest.main()
