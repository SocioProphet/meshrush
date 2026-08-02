import unittest

import numpy as np

from meshrush.core.graph_build import WeightedGraph
from meshrush.crystal.symmetry import is_automorphism
from meshrush.crystal.symmetry_discovery import (
    discover_automorphisms,
    set_native_backend,
)


def _wg(edges, n):
    w = np.zeros((n, n))
    for i, j in edges:
        w[i, j] = w[j, i] = 1.0
    return WeightedGraph(node_ids=tuple(f"n{i}" for i in range(n)), weights=w, degrees=w.sum(axis=1))


def _c4():
    return _wg([(0, 1), (1, 2), (2, 3), (3, 0)], 4)


def _p3():
    return _wg([(0, 1), (1, 2)], 3)


def _paw():  # triangle 0-1-2 with pendant 0-3
    return _wg([(0, 1), (1, 2), (2, 0), (0, 3)], 4)


class DiscoveryTests(unittest.TestCase):
    def tearDown(self):
        set_native_backend(None)  # never leak a backend across tests

    def test_c4_is_dihedral_order_8_single_orbit(self):
        res = discover_automorphisms(_c4())
        self.assertTrue(res.exact)
        self.assertEqual(res.method, "backtrack")
        self.assertEqual(res.order, 8)  # D4
        self.assertEqual(res.orbits, ((0, 1, 2, 3),))

    def test_p3_reversal_only(self):
        res = discover_automorphisms(_p3())
        self.assertTrue(res.exact)
        self.assertEqual(res.order, 2)  # identity + reversal
        self.assertEqual(res.orbits, ((0, 2), (1,)))

    def test_paw_swaps_two_triangle_vertices(self):
        res = discover_automorphisms(_paw())
        self.assertTrue(res.exact)
        self.assertEqual(res.order, 2)
        self.assertEqual(res.orbits, ((0,), (1, 2), (3,)))

    def test_every_discovered_perm_is_a_genuine_automorphism(self):
        g = _c4()
        for p in discover_automorphisms(g).automorphisms:
            self.assertTrue(is_automorphism(g, np.asarray(p, dtype=int)))

    def test_identity_always_present(self):
        g = _paw()
        self.assertIn(tuple(range(g.n)), discover_automorphisms(g).automorphisms)

    def test_deterministic(self):
        a = discover_automorphisms(_c4()).automorphisms
        b = discover_automorphisms(_c4()).automorphisms
        self.assertEqual(a, b)

    def test_empty_graph(self):
        res = discover_automorphisms(WeightedGraph((), np.zeros((0, 0)), np.zeros(0)))
        self.assertTrue(res.exact)
        self.assertEqual(res.order, 0)


class FailClosedTests(unittest.TestCase):
    def tearDown(self):
        set_native_backend(None)

    def test_step_budget_exhausted_is_not_exact(self):
        res = discover_automorphisms(_c4(), max_steps=1)
        self.assertFalse(res.exact)
        self.assertEqual(res.method, "refinement")

    def test_too_large_falls_back_to_refinement(self):
        res = discover_automorphisms(_c4(), max_nodes=2)
        self.assertFalse(res.exact)
        self.assertEqual(res.method, "refinement")
        # C4 is vertex-transitive -> one color class -> single over-approx orbit
        self.assertEqual(res.orbits, ((0, 1, 2, 3),))


class NativeBackendTests(unittest.TestCase):
    def tearDown(self):
        set_native_backend(None)

    def test_registered_backend_is_used_and_certified(self):
        set_native_backend(lambda g: (tuple(range(g.n)),))  # identity only
        res = discover_automorphisms(_c4())
        self.assertEqual(res.method, "native")
        self.assertTrue(res.exact)
        self.assertEqual(res.automorphisms, ((0, 1, 2, 3),))

    def test_backend_returning_non_automorphism_is_rejected(self):
        set_native_backend(lambda g: ((1, 0, 2, 3),))  # swap 0,1 is not an aut of C4
        with self.assertRaises(ValueError):
            discover_automorphisms(_c4())

    def test_allow_native_false_ignores_backend(self):
        set_native_backend(lambda g: (tuple(range(g.n)),))
        res = discover_automorphisms(_c4(), allow_native=False)
        self.assertEqual(res.method, "backtrack")


if __name__ == "__main__":
    unittest.main()
