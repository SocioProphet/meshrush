import math
import unittest

import numpy as np

from meshrush.core.graph_build import (
    WeightedGraph,
    build_knn_graph,
    is_connected,
    laplacian,
    transition,
)


def _ring_embeddings(n: int) -> list[list[float]]:
    return [[math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)] for i in range(n)]


class GraphBuildTests(unittest.TestCase):
    def test_weights_symmetric_zero_diagonal_positive_degrees(self) -> None:
        g = build_knn_graph(_ring_embeddings(12), k=2)
        self.assertIsInstance(g, WeightedGraph)
        self.assertTrue(np.allclose(g.weights, g.weights.T), "W must be symmetric")
        self.assertTrue(np.allclose(np.diag(g.weights), 0.0), "diagonal must be zero")
        self.assertTrue(np.all(g.degrees > 0.0), "no isolated nodes on a ring")

    def test_laplacian_rows_sum_to_zero(self) -> None:
        g = build_knn_graph(_ring_embeddings(10), k=2)
        rows = laplacian(g).sum(axis=1)
        self.assertTrue(np.allclose(rows, 0.0, atol=1e-12))

    def test_transition_is_row_stochastic(self) -> None:
        g = build_knn_graph(_ring_embeddings(10), k=2)
        p = transition(g)
        self.assertTrue(np.allclose(p.sum(axis=1), 1.0, atol=1e-12))
        self.assertTrue(np.all(p >= 0.0))

    def test_node_ids_default_and_custom(self) -> None:
        g = build_knn_graph(_ring_embeddings(4), k=1)
        self.assertEqual(g.node_ids, ("n0", "n1", "n2", "n3"))
        g2 = build_knn_graph(_ring_embeddings(4), node_ids=["a", "b", "c", "d"], k=1)
        self.assertEqual(g2.node_ids, ("a", "b", "c", "d"))

    def test_fixed_sigma_matches_manual_kernel(self) -> None:
        emb = [[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]]
        g = build_knn_graph(emb, k=2, sigma=1.0)
        # nodes 0-1 distance^2 = 1 -> exp(-1); symmetric.
        self.assertAlmostEqual(g.weights[0, 1], math.exp(-1.0), places=12)
        self.assertAlmostEqual(g.weights[0, 1], g.weights[1, 0], places=12)

    def test_invalid_inputs_raise(self) -> None:
        with self.assertRaises(ValueError):
            build_knn_graph([[0.0, 0.0]], k=1)  # need >= 2 nodes
        with self.assertRaises(ValueError):
            build_knn_graph(_ring_embeddings(5), k=0)  # k out of range
        with self.assertRaises(ValueError):
            build_knn_graph(_ring_embeddings(5), k=5)  # k must be <= n-1
        with self.assertRaises(ValueError):
            build_knn_graph(_ring_embeddings(5), k=2, sigma=-1.0)

    def test_is_connected(self) -> None:
        self.assertTrue(is_connected(build_knn_graph(_ring_embeddings(8), k=2)))
        # Two disconnected edges: {0-1} and {2-3}.
        w = np.zeros((4, 4))
        w[0, 1] = w[1, 0] = 1.0
        w[2, 3] = w[3, 2] = 1.0
        g = WeightedGraph(node_ids=("a", "b", "c", "d"), weights=w, degrees=w.sum(axis=1))
        self.assertFalse(is_connected(g))

    def test_transition_rejects_isolated_node(self) -> None:
        g = WeightedGraph(
            node_ids=("a", "b"),
            weights=np.zeros((2, 2)),
            degrees=np.zeros(2),
        )
        with self.assertRaises(ValueError):
            transition(g)


if __name__ == "__main__":
    unittest.main()
