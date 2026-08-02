import math
import unittest

import numpy as np

from meshrush.core.graph_build import build_knn_graph, laplacian
from meshrush.crystal.dynamics import DynamicsParams
from meshrush.omni.probes import (
    impulse_probe,
    seed_persistence_probe,
    spectral_band_probe,
    symmetry_probe,
)


def _ring(n: int):
    emb = [[math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)] for i in range(n)]
    return build_knn_graph(emb, k=2)


def _line(n: int):
    # A non-regular graph (endpoints differ from interior) with a reflection automorphism.
    return build_knn_graph([[float(i), 0.0] for i in range(n)], k=2)


class ImpulseProbeTests(unittest.TestCase):
    def test_pulse_spreads_over_time(self) -> None:
        # Participation ratio is the parity-robust spread metric (a ring is
        # bipartite, so anchor-retained mass oscillates with step parity).
        g = _ring(16)
        near = impulse_probe(g, [0], steps=1)
        far = impulse_probe(g, [0], steps=6)
        self.assertLess(near.participation_ratio, far.participation_ratio)
        # Some mass has left the anchor after one step.
        self.assertLess(near.retained_at_anchors, 1.0)

    def test_distribution_is_a_probability_vector(self) -> None:
        g = _ring(10)
        resp = impulse_probe(g, [0, 1], steps=3)
        self.assertAlmostEqual(float(resp.distribution.sum()), 1.0, places=9)
        self.assertTrue(np.all(resp.distribution >= -1e-12))

    def test_invalid_inputs_raise(self) -> None:
        g = _ring(6)
        with self.assertRaises(ValueError):
            impulse_probe(g, [0], steps=0)
        with self.assertRaises(ValueError):
            impulse_probe(g, [], steps=1)
        with self.assertRaises(ValueError):
            impulse_probe(g, [99], steps=1)

    def test_rejects_duplicate_anchors(self) -> None:
        g = _ring(6)
        with self.assertRaises(ValueError):
            impulse_probe(g, [0, 0, 1], steps=2)


class SpectralBandProbeTests(unittest.TestCase):
    def test_energy_fraction_bounded(self) -> None:
        g = _ring(16)
        resp = spectral_band_probe(g, 0.0, 4.0)
        self.assertGreaterEqual(resp.energy_fraction, 0.0)
        self.assertLessEqual(resp.energy_fraction, 1.0 + 1e-9)

    def test_signal_in_band_has_near_full_energy_there(self) -> None:
        g = _ring(16)
        vals, vecs = np.linalg.eigh(laplacian(g))
        # Build a signal from eigenvectors in a mid band, then probe that band.
        lo, hi = float(vals[5]), float(vals[9])
        in_band = (vals >= lo) & (vals <= hi)
        signal = vecs[:, in_band].sum(axis=1)
        resp = spectral_band_probe(g, lo, hi, signal=signal)
        self.assertGreater(resp.energy_fraction, 0.99)
        self.assertGreaterEqual(resp.eigenvalues_in_band, 1)

    def test_bad_band_raises(self) -> None:
        g = _ring(6)
        with self.assertRaises(ValueError):
            spectral_band_probe(g, 2.0, 1.0)


class SeedPersistenceProbeTests(unittest.TestCase):
    def test_supra_threshold_seed_survives_release(self) -> None:
        g = _ring(12)
        res = seed_persistence_probe(
            g, seed_nodes=[0, 1, 2], params=DynamicsParams(),
            hold_steps=3, release_steps=3,
        )
        self.assertTrue(res.survived)
        self.assertGreater(res.retained_crystallinity, res.control_crystallinity)

    def test_control_region_does_not_spontaneously_crystallize(self) -> None:
        g = _ring(12)
        res = seed_persistence_probe(g, seed_nodes=[0], params=DynamicsParams())
        self.assertLess(res.control_crystallinity, 0.5)

    def test_invalid_seed_raises(self) -> None:
        g = _ring(6)
        with self.assertRaises(ValueError):
            seed_persistence_probe(g, seed_nodes=[], params=DynamicsParams())

    def test_fails_closed_on_bad_steps_and_threshold(self) -> None:
        g = _ring(6)
        with self.assertRaises(ValueError):
            seed_persistence_probe(g, [0], DynamicsParams(), hold_steps=-1)
        with self.assertRaises(ValueError):
            seed_persistence_probe(g, [0], DynamicsParams(), release_steps=-1)
        with self.assertRaises(ValueError):
            seed_persistence_probe(g, [0], DynamicsParams(), threshold=1.5)


class SymmetryProbeTests(unittest.TestCase):
    def test_identity_is_equivariant(self) -> None:
        g = _ring(8)
        resp = symmetry_probe(g, np.arange(8))
        self.assertLess(resp.defect, 1e-9)
        self.assertTrue(resp.equivariant)

    def test_ring_rotation_is_an_automorphism(self) -> None:
        g = _ring(12)
        rot = np.array([(i + 1) % 12 for i in range(12)])
        resp = symmetry_probe(g, rot)
        self.assertLess(resp.defect, 1e-6)
        self.assertTrue(resp.equivariant)

    def test_line_reflection_is_automorphism_on_non_regular_graph(self) -> None:
        # A line graph is non-regular (endpoints differ from interior); its
        # reflection i <-> n-1-i is a true automorphism. This guards the
        # row-vs-column operator convention on a graph where P is not symmetric.
        n = 9
        g = _line(n)
        reflection = np.array([n - 1 - i for i in range(n)])
        resp = symmetry_probe(g, reflection)
        self.assertLess(resp.defect, 1e-6)
        self.assertTrue(resp.equivariant)

    def test_adjacent_transposition_breaks_symmetry(self) -> None:
        g = _ring(8)
        perm = np.arange(8)
        perm[0], perm[1] = 1, 0  # swap two nodes: not a ring automorphism
        resp = symmetry_probe(g, perm)
        self.assertGreater(resp.defect, 1e-3)
        self.assertFalse(resp.equivariant)

    def test_non_permutation_raises(self) -> None:
        g = _ring(6)
        with self.assertRaises(ValueError):
            symmetry_probe(g, np.array([0, 0, 1, 2, 3, 4]))


if __name__ == "__main__":
    unittest.main()
