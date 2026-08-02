import unicodedata
import unittest

from meshrush.core.cairn import (
    CairnLimits,
    CairnLine,
    EntityRef,
    bounded_frontier_step,
    canonical_hash,
)


def _ref(key: str, ns: str = "demo", kind: str = "Node") -> EntityRef:
    return EntityRef(namespace=ns, kind=kind, key=key)


class EntityRefTests(unittest.TestCase):
    def test_canonical_format(self):
        self.assertEqual(_ref("acme").canonical, "demo:Node:acme")

    def test_canonical_is_nfc_normalized(self):
        # Same text, different Unicode normal forms -> same canonical id.
        composed = unicodedata.normalize("NFC", "café")
        decomposed = unicodedata.normalize("NFD", "café")
        self.assertNotEqual(composed, decomposed)  # different code points
        a = EntityRef("ns", "Org", composed).canonical
        b = EntityRef("ns", "Org", decomposed).canonical
        self.assertEqual(a, b)  # equal after NFC


class BoundedFrontierStepTests(unittest.TestCase):
    def test_dedup_rank_cap_invariant(self):
        dist = {"a": 0.1, "b": 0.5, "c": 0.2, "d": 0.9}
        cands = [_ref("a"), _ref("c"), _ref("b"), _ref("d"), _ref("a")]  # 'a' duplicated
        out = bounded_frontier_step(cands, rank_key=lambda e: dist[e.key], cap_k=3)
        # deduped, ranked ascending by distance, capped to 3
        self.assertEqual([e.key for e in out], ["a", "c", "b"])
        self.assertLessEqual(len(out), 3)

    def test_deterministic_tiebreak_by_canonical(self):
        cands = [_ref("z"), _ref("a"), _ref("m")]
        out = bounded_frontier_step(cands, rank_key=lambda e: 1.0, cap_k=10)  # all tie
        self.assertEqual([e.key for e in out], ["a", "m", "z"])  # lexicographic canonical

    def test_fails_closed_on_cap_exceeding_limits(self):
        limits = CairnLimits(max_cap_k=2)
        with self.assertRaises(ValueError):
            bounded_frontier_step([_ref("a")], rank_key=lambda e: 0.0, cap_k=5, limits=limits)
        with self.assertRaises(ValueError):
            bounded_frontier_step([_ref("a")], rank_key=lambda e: 0.0, cap_k=0)


class CairnLimitsTests(unittest.TestCase):
    def test_invalid_limits_raise(self):
        with self.assertRaises(ValueError):
            CairnLimits(max_hops=0)
        with self.assertRaises(ValueError):
            CairnLimits(max_cap_k=0)

    def test_opcode_gate(self):
        limits = CairnLimits(allowed_opcodes=("expand",))
        limits.check_opcode("expand")  # ok
        with self.assertRaises(ValueError):
            limits.check_opcode("materialize")


class CairnLineTests(unittest.TestCase):
    def test_record_step_and_frontier_order(self):
        line = CairnLine("line1", "dataset@snap1", limits=CairnLimits(max_hops=3))
        step = line.record_step("expand", [_ref("a"), _ref("b")], cap_k=2)
        self.assertEqual(step.frontier_out, ("demo:Node:a", "demo:Node:b"))
        self.assertEqual(step.index, 0)

    def test_max_hops_fails_closed(self):
        line = CairnLine("l", "d", limits=CairnLimits(max_hops=1))
        line.record_step("expand", [_ref("a")], cap_k=1)
        with self.assertRaises(ValueError):
            line.record_step("expand", [_ref("b")], cap_k=1)

    def test_digest_is_deterministic_and_sensitive(self):
        def build():
            ln = CairnLine("l", "d")
            ln.record_step("expand", [_ref("a")], cap_k=1)
            return ln
        self.assertEqual(build().digest, build().digest)  # replay-stable
        other = build()
        other.record_step("expand", [_ref("b")], cap_k=1)
        self.assertNotEqual(build().digest, other.digest)  # changes with steps


class CanonicalHashTests(unittest.TestCase):
    def test_stable_and_order_independent_for_keys(self):
        self.assertEqual(canonical_hash({"a": 1, "b": 2}), canonical_hash({"b": 2, "a": 1}))
        self.assertNotEqual(canonical_hash({"a": 1}), canonical_hash({"a": 2}))


if __name__ == "__main__":
    unittest.main()
