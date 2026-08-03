import unittest

from meshrush.core.governance import (
    ConductorManifest,
    ExecutionReceipt,
    ExpansionPoint,
    ExpansionState,
    admit_expansion,
    govern_receipt,
    reasoning_trace_to_observation,
)
from meshrush.crystal.retrieval import EpistemicLevel


def _point(**over):
    kw = dict(name="observe_compile", admissible_shapes=("expand",), max_depth=3,
              max_breadth=4, max_budget=10.0)
    kw.update(over)
    return ExpansionPoint(**kw)


def _manifest(**over):
    kw = dict(conductor_id="mheller", expansion_points=(_point(),),
              allowed_transforms=("diffuse", "compile", "prophet-mesh.reason"))
    kw.update(over)
    return ConductorManifest(**kw)


class ExpansionPointTests(unittest.TestCase):
    def test_validation(self):
        for bad in (dict(name=""), dict(max_depth=0), dict(max_breadth=0),
                    dict(max_budget=-1.0), dict(admissible_shapes=())):
            with self.assertRaises(ValueError):
                _point(**bad)


class AdmitExpansionTests(unittest.TestCase):
    def test_admits_within_bounds_and_advances_state(self):
        d = admit_expansion(_point(), ExpansionState(), shape="expand", breadth=2, cost=3.0)
        self.assertTrue(d.admitted)
        self.assertEqual(d.next_state, ExpansionState(depth=1, breadth=2, spent=3.0))

    def test_refuses_inadmissible_shape(self):
        d = admit_expansion(_point(), ExpansionState(), shape="teleport", breadth=1, cost=0.0)
        self.assertFalse(d.admitted)
        self.assertIn("not in admissible_shapes", d.reason)

    def test_refuses_on_each_cap(self):
        p = _point()
        depth_maxed = admit_expansion(p, ExpansionState(depth=3), shape="expand", breadth=1, cost=0.0)
        breadth_over = admit_expansion(p, ExpansionState(), shape="expand", breadth=99, cost=0.0)
        budget_over = admit_expansion(p, ExpansionState(spent=9.0), shape="expand", breadth=1, cost=5.0)
        self.assertFalse(depth_maxed.admitted)
        self.assertFalse(breadth_over.admitted)
        self.assertFalse(budget_over.admitted)

    def test_bounded_loop_terminates(self):
        # loop-as-DAG: repeatedly expanding cannot run forever — it halts at max_depth.
        p = _point(max_depth=5, max_budget=1e9)
        state = ExpansionState()
        admitted = 0
        for _ in range(10_000):
            d = admit_expansion(p, state, shape="expand", breadth=1, cost=1.0)
            if not d.admitted:
                break
            state = d.next_state
            admitted += 1
        self.assertEqual(admitted, 5)  # exactly max_depth, then refused


class ConductorManifestTests(unittest.TestCase):
    def test_empty_conductor_is_unpublishable(self):
        with self.assertRaises(ValueError):
            _manifest(conductor_id="")

    def test_manifest_id_deterministic_and_sensitive(self):
        self.assertEqual(_manifest().manifest_id, _manifest().manifest_id)
        self.assertTrue(_manifest().manifest_id.startswith("manifest."))
        self.assertNotEqual(_manifest().manifest_id,
                            _manifest(allowed_transforms=("diffuse",)).manifest_id)

    def test_authorizes_is_fail_closed(self):
        m = _manifest()
        self.assertTrue(m.authorizes(actor="mheller", transform="compile"))
        self.assertFalse(m.authorizes(actor="someone_else", transform="compile"))  # wrong actor
        self.assertFalse(m.authorizes(actor="mheller", transform="exfiltrate"))     # undeclared

    def test_expansion_point_lookup(self):
        m = _manifest()
        self.assertIsNotNone(m.expansion_point("observe_compile"))
        self.assertIsNone(m.expansion_point("nope"))


class GovernReceiptTests(unittest.TestCase):
    def test_authorized_receipt_becomes_observation(self):
        r = ExecutionReceipt("r1", actor="mheller", transform="compile", outcome="granted",
                             evidence_refs=("ev1",))
        g = govern_receipt(r, _manifest())
        self.assertTrue(g.admitted)
        self.assertEqual(g.observation["epistemic_level"], "empirical")
        self.assertEqual(g.observation["provenance"]["manifest_id"], _manifest().manifest_id)
        self.assertEqual(g.observation["source"], "agent-machine.receipt")

    def test_unauthorized_receipt_is_refused(self):
        r = ExecutionReceipt("r1", actor="intruder", transform="compile", outcome="granted")
        g = govern_receipt(r, _manifest())
        self.assertFalse(g.admitted)
        self.assertIsNone(g.observation)

    def test_observation_cannot_enter_above_bounded(self):
        r = ExecutionReceipt("r1", actor="mheller", transform="compile", outcome="granted")
        with self.assertRaises(ValueError):
            govern_receipt(r, _manifest(), epistemic=EpistemicLevel.PROVED)


class ReasoningTraceTests(unittest.TestCase):
    def test_authorized_trace_becomes_observation(self):
        g = reasoning_trace_to_observation("t1", "blob://x", _manifest())
        self.assertTrue(g.admitted)
        self.assertEqual(g.observation["source"], "prophet-mesh.trace")

    def test_undeclared_transform_is_refused(self):
        m = _manifest(allowed_transforms=("compile",))  # prophet-mesh.reason not declared
        g = reasoning_trace_to_observation("t1", "blob://x", m)
        self.assertFalse(g.admitted)
        self.assertIsNone(g.observation)


if __name__ == "__main__":
    unittest.main()
