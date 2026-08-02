import unittest

import numpy as np

from meshrush.core.contracts import CompileOutcome
from meshrush.core.graph_build import WeightedGraph
from meshrush.crystal.retrieval import EpistemicLevel
from meshrush.crystal.certificate import (
    CompileMetrics,
    CompileThresholds,
    boundary_defect,
    certificate_to_attestation,
    evaluate_certificate,
    to_compile_decision,
)


def _calibrated():
    return CompileThresholds(calibrated=True, phi_star=0.75, c_star=0.0, eps_sym=1e-3,
                             s_star=0.5, d_star=0.5, t_star=0.5, h_star=0.0)


def _passing_metrics(**over):
    m = dict(mean_phi=0.9, mean_c=0.5, d_sym=1e-6, s_sharp=0.8, d_gb=0.1, t_persist=0.9, delta_h=1.0)
    m.update(over)
    return CompileMetrics(**m)


def _path4():
    # path n0-n1-n2-n3, unit weights
    w = np.zeros((4, 4))
    for i, j in [(0, 1), (1, 2), (2, 3)]:
        w[i, j] = w[j, i] = 1.0
    return WeightedGraph(node_ids=("n0", "n1", "n2", "n3"), weights=w, degrees=w.sum(axis=1))


class CertificateTests(unittest.TestCase):
    def test_all_gates_pass_is_bounded(self):
        cert = evaluate_certificate("A", _passing_metrics(), _calibrated())
        self.assertTrue(cert.passed)
        self.assertEqual(cert.epistemic, EpistemicLevel.BOUNDED)
        self.assertEqual(cert.failed_gates, ())
        self.assertEqual(len(cert.gates), 7)

    def test_single_gate_failure_is_synthetic_and_named(self):
        cert = evaluate_certificate("A", _passing_metrics(d_sym=0.1), _calibrated())  # symmetry fails
        self.assertFalse(cert.passed)
        self.assertEqual(cert.epistemic, EpistemicLevel.SYNTHETIC)
        self.assertIn("symmetry", cert.failed_gates)

    def test_uncalibrated_refuses_regardless_of_metrics(self):
        cert = evaluate_certificate("A", _passing_metrics(), CompileThresholds(calibrated=False))
        self.assertFalse(cert.passed)
        self.assertEqual(cert.epistemic, EpistemicLevel.SPECULATIVE)
        self.assertIn("not calibrated", cert.rationale)

    def test_each_gate_can_fail(self):
        floors = dict(mean_phi=0.0, mean_c=-1.0, d_sym=1.0, s_sharp=0.0, d_gb=1.0, t_persist=0.0, delta_h=-1.0)
        for field in floors:
            cert = evaluate_certificate("A", _passing_metrics(**{field: floors[field]}), _calibrated())
            self.assertFalse(cert.passed, f"{field} should have failed the certificate")


class CompileDecisionBridgeTests(unittest.TestCase):
    def test_bounded_maps_to_accept(self):
        cert = evaluate_certificate("A", _passing_metrics(), _calibrated())
        d = to_compile_decision(cert, candidate_region_id="r1", attestation_id="att.xyz")
        self.assertEqual(d.outcome, CompileOutcome.ACCEPT)
        self.assertEqual(d.candidate_region_id, "r1")
        self.assertEqual(d.metadata["epistemic_level"], "bounded")
        self.assertEqual(d.certificate_refs[0].evidence_id, "att.xyz")

    def test_synthetic_maps_to_rework_with_failed_gates(self):
        cert = evaluate_certificate("A", _passing_metrics(d_sym=0.1), _calibrated())
        d = to_compile_decision(cert, candidate_region_id="r1")
        self.assertEqual(d.outcome, CompileOutcome.REWORK)
        self.assertIn("symmetry", d.metadata["failed_gates"])
        self.assertEqual(d.certificate_refs, ())

    def test_uncalibrated_maps_to_defer(self):
        cert = evaluate_certificate("A", _passing_metrics(), CompileThresholds(calibrated=False))
        d = to_compile_decision(cert, candidate_region_id="r1")
        self.assertEqual(d.outcome, CompileOutcome.DEFER)


class BoundaryDefectTests(unittest.TestCase):
    def test_matches_weighted_cut(self):
        g = _path4()
        # mask {n0,n1}: the only cut edge is (n1,n2) weight 1; |m|=2 -> D_gb = 0.5
        d = boundary_defect(g, [1, 1, 0, 0])
        self.assertAlmostEqual(d, 0.5, places=9)

    def test_empty_mask_raises(self):
        with self.assertRaises(ValueError):
            boundary_defect(_path4(), [0, 0, 0, 0])

    def test_wrong_length_mask_raises(self):
        with self.assertRaises(ValueError):
            boundary_defect(_path4(), [1, 1, 0])  # graph has 4 nodes


class AttestationTests(unittest.TestCase):
    def test_attestation_is_content_addressed_and_carries_evidence(self):
        cert = evaluate_certificate("artA", _passing_metrics(), _calibrated())
        att = certificate_to_attestation(cert, included_node_ids=("n0", "n1"), graph_view_id="gv1")
        self.assertTrue(att["attestation_id"].startswith("att."))
        self.assertEqual(att["epistemic_level"], "bounded")
        self.assertTrue(att["passed"])
        self.assertEqual(len(att["gates"]), 7)
        self.assertEqual(att["boundary"]["included_node_ids"], ["n0", "n1"])

    def test_attestation_id_is_deterministic_and_sensitive(self):
        cert = evaluate_certificate("artA", _passing_metrics(), _calibrated())
        a1 = certificate_to_attestation(cert, included_node_ids=("n0",), graph_view_id="gv1")
        a2 = certificate_to_attestation(cert, included_node_ids=("n0",), graph_view_id="gv1")
        a3 = certificate_to_attestation(cert, included_node_ids=("n0",), graph_view_id="gv2")
        self.assertEqual(a1["attestation_id"], a2["attestation_id"])
        self.assertNotEqual(a1["attestation_id"], a3["attestation_id"])


if __name__ == "__main__":
    unittest.main()
