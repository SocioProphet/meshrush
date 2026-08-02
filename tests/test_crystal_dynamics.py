import math
import unittest

import numpy as np

from meshrush.core.graph_build import build_knn_graph
from meshrush.crystal.dynamics import (
    CrystalState,
    DynamicsParams,
    advance,
    crystallinity_step,
    mbo_step,
    spectrally_scaled_laplacian,
    support_step,
)


def _ring(n: int):
    emb = [[math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)] for i in range(n)]
    return build_knn_graph(emb, k=2)


class SupportDensityTests(unittest.TestCase):
    def test_support_step_is_conservative_without_decay_or_injection(self) -> None:
        g = _ring(12)
        rng = np.random.default_rng(0)
        c = rng.standard_normal(g.n)
        phi = rng.random(g.n)
        c1 = support_step(g, c, phi, DynamicsParams())  # gamma_c=0, beta_u=0 by default
        self.assertAlmostEqual(float(c1.sum()), float(c.sum()), places=9)

    def test_band_term_stays_conservative(self) -> None:
        g = _ring(12)
        rng = np.random.default_rng(1)
        c = rng.standard_normal(g.n)
        phi = rng.random(g.n)
        params = DynamicsParams(kappa_b=0.5, omega0=0.2)  # band term ON
        c1 = support_step(g, c, phi, params)
        self.assertAlmostEqual(float(c1.sum()), float(c.sum()), places=9)

    def test_decay_reduces_total_support(self) -> None:
        g = _ring(10)
        c = np.ones(g.n)
        phi = np.zeros(g.n)
        c1 = support_step(g, c, phi, DynamicsParams(gamma_c=0.1))
        self.assertLess(float(c1.sum()), float(c.sum()))


class CrystallinityTests(unittest.TestCase):
    def test_stays_within_unit_interval(self) -> None:
        g = _ring(12)
        rng = np.random.default_rng(2)
        phi = rng.random(g.n)
        c = rng.standard_normal(g.n) * 5.0
        phi1 = crystallinity_step(g, phi, c, DynamicsParams())
        self.assertTrue(np.all(phi1 >= 0.0) and np.all(phi1 <= 1.0))

    def test_zero_and_one_are_fixed_points(self) -> None:
        g = _ring(8)
        c = np.zeros(g.n)
        p = DynamicsParams()
        phi0 = crystallinity_step(g, np.zeros(g.n), c, p)
        phi1 = crystallinity_step(g, np.ones(g.n), c, p)
        self.assertTrue(np.allclose(phi0, 0.0, atol=1e-9))
        self.assertTrue(np.allclose(phi1, 1.0, atol=1e-9))

    def test_support_promotes_crystallinity(self) -> None:
        g = _ring(8)
        phi = np.full(g.n, 0.4)
        c = np.ones(g.n)
        phi1 = crystallinity_step(g, phi, c, DynamicsParams(eta=0.5))
        self.assertTrue(np.all(phi1 > phi))

    def test_annealed_noise_is_deterministic_and_clipped(self) -> None:
        g = _ring(8)
        phi = np.full(g.n, 0.5)
        c = np.zeros(g.n)
        p = DynamicsParams(sigma0=0.1)
        a = crystallinity_step(g, phi, c, p, step=0, rng=np.random.default_rng(7))
        b = crystallinity_step(g, phi, c, p, step=0, rng=np.random.default_rng(7))
        self.assertTrue(np.allclose(a, b))  # deterministic given the seed
        self.assertTrue(np.all(a >= 0.0) and np.all(a <= 1.0))


class MboAndDriverTests(unittest.TestCase):
    def test_mbo_produces_binary_mask(self) -> None:
        g = _ring(12)
        soft = np.linspace(0.0, 1.0, g.n)
        m = mbo_step(soft, g, tau_m=0.1)
        self.assertTrue(set(np.unique(m)).issubset({0.0, 1.0}))

    def test_mbo_rejects_negative_time(self) -> None:
        g = _ring(6)
        with self.assertRaises(ValueError):
            mbo_step(np.ones(g.n), g, tau_m=-1.0)

    def test_spectrally_scaled_laplacian_spectral_bound(self) -> None:
        g = _ring(16)
        l_tilde, lam_max = spectrally_scaled_laplacian(g)
        top = float(np.linalg.eigvalsh(l_tilde).max())
        self.assertGreater(lam_max, 0.0)
        self.assertLessEqual(top, 1.0 + 1e-9)

    def test_enabled_terms_fail_fast_when_vector_missing(self) -> None:
        g = _ring(8)
        # injection enabled but u omitted
        with self.assertRaises(ValueError):
            support_step(g, np.zeros(g.n), np.zeros(g.n), DynamicsParams(beta_u=0.5))
        # relevance enabled but r omitted
        with self.assertRaises(ValueError):
            crystallinity_step(g, np.full(g.n, 0.4), np.zeros(g.n), DynamicsParams(lambda_rel=0.3))
        # symmetry pressure enabled but s omitted
        with self.assertRaises(ValueError):
            crystallinity_step(g, np.full(g.n, 0.4), np.zeros(g.n), DynamicsParams(lambda_sym=0.3))
        # wrong-shape u
        with self.assertRaises(ValueError):
            support_step(g, np.zeros(g.n), np.zeros(g.n), DynamicsParams(beta_u=0.5), u=np.zeros(3))

    def test_advance_steps_both_fields(self) -> None:
        g = _ring(10)
        rng = np.random.default_rng(3)
        state = CrystalState(c=rng.standard_normal(g.n), phi=rng.random(g.n))
        nxt = advance(g, state, DynamicsParams())
        self.assertEqual(nxt.step, 1)
        self.assertEqual(nxt.c.shape, (g.n,))
        self.assertTrue(np.all(nxt.phi >= 0.0) and np.all(nxt.phi <= 1.0))


if __name__ == "__main__":
    unittest.main()
