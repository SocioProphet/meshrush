import unittest

from meshrush.experiments.matrix import (
    CANONICAL_EXPERIMENT_COUNT,
    ExperimentFamily,
    ExperimentSpec,
    OBSERVATION_NOOP_DUPLICATES,
    RAW_EXPERIMENT_COUNT,
    count_reconciliation,
    observe,
    representative_suite,
    ring_graph,
    run_experiment,
)


class CountReconciliationTests(unittest.TestCase):
    def test_141_minus_12_equals_129(self):
        rec = count_reconciliation()
        self.assertEqual(rec.raw_count, 141)
        self.assertEqual(rec.deduplicated, 12)
        self.assertEqual(rec.corrected_count, 129)
        self.assertEqual(rec.raw_count - rec.deduplicated, rec.corrected_count)

    def test_constants_agree(self):
        self.assertEqual(RAW_EXPERIMENT_COUNT - OBSERVATION_NOOP_DUPLICATES,
                         CANONICAL_EXPERIMENT_COUNT)

    def test_reason_cites_noop_special_case(self):
        self.assertIn("no-op", count_reconciliation().reason)


class NoOpObservationEquivalenceTests(unittest.TestCase):
    def test_noop_observation_returns_the_supplied_graph(self):
        # operational root of the correction: a no-op observation over a structural
        # graph *is* that structural graph -> not a distinct experiment.
        g = ring_graph(6)
        self.assertIs(observe(g, noop=True), g)

    def test_noop_requires_a_graph(self):
        with self.assertRaises(ValueError):
            observe([[0.0, 1.0]], noop=True)  # points, not a WeightedGraph


class RunnerTests(unittest.TestCase):
    def test_every_representative_experiment_passes(self):
        suite = representative_suite()
        for spec in suite:
            report = run_experiment(spec)
            self.assertTrue(report.passed, f"{spec.id} failed: {report.failures}")

    def test_all_three_families_represented(self):
        fams = {s.family for s in representative_suite()}
        self.assertEqual(fams, set(ExperimentFamily))

    def test_ring_has_symmetry_observation_recorded(self):
        report = run_experiment(representative_suite()[0])  # struct-ring-8
        self.assertGreater(report.observations["automorphism_order"], 1)

    def test_unknown_generator_raises(self):
        bad = ExperimentSpec("x", ExperimentFamily.STRUCTURAL, "nope", {}, ())
        with self.assertRaises(ValueError):
            run_experiment(bad)

    def test_failure_is_reported_not_raised(self):
        # a rigid invariant on a symmetric ring must be reported as a failure
        spec = ExperimentSpec("ring-rigid", ExperimentFamily.STRUCTURAL, "ring",
                              {"n": 6}, ("rigid",))
        report = run_experiment(spec)
        self.assertFalse(report.passed)
        self.assertIn("rigid", report.failures)


if __name__ == "__main__":
    unittest.main()
