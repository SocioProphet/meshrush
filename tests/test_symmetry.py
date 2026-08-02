import math
import unittest

import numpy as np

from meshrush.core.graph_build import WeightedGraph, build_knn_graph
from meshrush.crystal.symmetry import (
    is_automorphism,
    permutation_matrix,
    refine_colors,
    survives_null,
    symmetry_defect,
)


def _ring(n: int):
    emb = [[math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)] for i in range(n)]
    return build_knn_graph(emb, k=2)


def _triangle_tail():
    # Triangle {0,1,2} + tail 3-0. Automorphism group = {identity, swap(1,2)}.
    w = np.zeros((4, 4))
    for i, j in [(0, 1), (1, 2), (2, 0), (0, 3)]:
        w[i, j] = w[j, i] = 1.0
    return WeightedGraph(node_ids=("0", "1", "2", "3"), weights=w, degrees=w.sum(axis=1))


class AutomorphismTests(unittest.TestCase):
    def test_ring_rotation_and_reflection_are_automorphisms(self):
        n = 12
        g = _ring(n)
        rot = np.array([(i + 1) % n for i in range(n)])
        refl = np.array([(n - i) % n for i in range(n)])
        self.assertTrue(is_automorphism(g, rot))
        self.assertTrue(is_automorphism(g, refl))
        self.assertTrue(symmetry_defect(g, rot).accepted)

    def test_triangle_tail_swap_is_automorphism_but_tail_swap_is_not(self):
        g = _triangle_tail()
        swap_12 = np.array([0, 2, 1, 3])
        swap_03 = np.array([3, 1, 2, 0])
        self.assertTrue(is_automorphism(g, swap_12))
        self.assertFalse(is_automorphism(g, swap_03))
        self.assertGreater(symmetry_defect(g, swap_03).total, 1e-3)
        self.assertFalse(symmetry_defect(g, swap_03).accepted)


class DefectFunctionalTests(unittest.TestCase):
    def test_feature_defect_zero_for_constant_features(self):
        g = _ring(8)
        rot = np.array([(i + 1) % 8 for i in range(8)])
        const = np.ones((8, 2))
        d = symmetry_defect(g, rot, features=const)
        self.assertAlmostEqual(d.d_feature, 0.0, places=9)

    def test_feature_defect_positive_when_features_break_symmetry(self):
        g = _triangle_tail()
        swap_12 = np.array([0, 2, 1, 3])
        feats = np.array([[0.0], [1.0], [2.0], [3.0]])  # node 1 != node 2
        d = symmetry_defect(g, swap_12, features=feats)
        self.assertTrue(is_automorphism(g, swap_12))       # structural symmetry
        self.assertGreater(d.d_feature, 0.0)               # but features are not invariant

    def test_permutation_matrix_rejects_non_permutation(self):
        with self.assertRaises(ValueError):
            permutation_matrix(np.array([0, 0, 1]), 3)


class ColorRefinementTests(unittest.TestCase):
    def test_ring_is_vertex_transitive_single_color(self):
        colors = refine_colors(_ring(10))
        self.assertEqual(len(set(colors.tolist())), 1)

    def test_triangle_tail_roles_separate(self):
        colors = refine_colors(_triangle_tail())
        c = colors.tolist()
        self.assertEqual(c[1], c[2])          # the two symmetric triangle nodes share a role
        self.assertNotEqual(c[0], c[3])       # hub and tail are distinct roles
        self.assertNotEqual(c[0], c[1])

    def test_refine_colors_validates_args(self):
        g = _ring(6)
        with self.assertRaises(ValueError):
            refine_colors(g, quantum=0.0)
        with self.assertRaises(ValueError):
            refine_colors(g, max_iter=-1)


class EmpiricalNullTests(unittest.TestCase):
    def test_true_symmetry_survives_null_and_asymmetry_does_not(self):
        g = _triangle_tail()
        rng = np.random.default_rng(0)
        swap_12 = np.array([0, 2, 1, 3])
        swap_03 = np.array([3, 1, 2, 0])
        surv_sym, p_sym = survives_null(g, swap_12, samples=200, rng=rng)
        surv_asym, p_asym = survives_null(g, swap_03, samples=200, rng=rng)
        self.assertTrue(surv_sym)
        self.assertFalse(surv_asym)
        self.assertLess(p_sym, p_asym)

    def test_color_incompatible_perm_is_rejected_up_front(self):
        # swap(0,3) maps the hub role onto the tail role -> not color-compatible.
        g = _triangle_tail()
        surv, p = survives_null(g, np.array([3, 1, 2, 0]), samples=10)
        self.assertFalse(surv)
        self.assertEqual(p, 1.0)


if __name__ == "__main__":
    unittest.main()
