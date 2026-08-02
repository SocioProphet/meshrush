"""Non-blow-up guarantees of the cairn apparatus.

These tests adversarially stress the bounded-frontier machinery to *demonstrate* the
central promise: no matter how explosively (or cyclically, or endlessly) an expander
proposes candidates, a cairnpath plan stays tractable —

  * the live frontier never exceeds ``cap_k`` (F[t+1] = TopK(Rank(Dedup(Expand(F[t])))));
  * the whole recorded plan is bounded by ``cap_k * max_hops`` — *linear* in hops, so
    it can never become the exponential plan a naive expansion would build;
  * an infinite walk is halted at ``max_hops`` (fail closed) rather than growing an
    unbounded plan;
  * cycles are deduped, so revisiting does not blow the frontier up;
  * ``cap_k`` cannot be widened past the policy ceiling ``max_cap_k``;
  * materialization egress is capped by a byte budget and short-circuited (no wasted
    fetches once the budget is spent).
"""
import itertools
import unittest

import numpy as np

from meshrush.core.cairn import (
    CairnLimits,
    CairnLine,
    EntityRef,
    bounded_frontier_step,
)
from meshrush.core.graph_build import WeightedGraph
from meshrush.crystal.materialize import (
    MaterializeMode,
    MaterializePolicy,
    MaterializeRequest,
    materialize,
)
from meshrush.crystal.retrieval import ArtifactSlotFiller, SlotSpec
from meshrush.omni.reduction import diffusion_coordinates


def _ref(key: str) -> EntityRef:
    return EntityRef(namespace="demo", kind="Node", key=key)


def _exponential_expander(branch: int):
    """Every node in the frontier spawns ``branch`` brand-new unique nodes, so the
    *naive* frontier size would be ``branch ** steps`` — the blow-up we must contain."""
    counter = itertools.count()
    def expand(frontier):
        return [_ref(f"n{next(counter)}") for _ in frontier for _ in range(branch)]
    return expand


class FrontierStaysBoundedTests(unittest.TestCase):
    def test_frontier_never_exceeds_cap_under_exponential_expansion(self):
        branch, cap_k, steps = 8, 4, 12
        expand = _exponential_expander(branch)
        frontier = [_ref("seed")]
        for _ in range(steps):
            frontier = bounded_frontier_step(
                expand(frontier), rank_key=lambda e: 0.0, cap_k=cap_k
            )
            self.assertLessEqual(len(frontier), cap_k)          # bounded every step
            self.assertEqual(len({e.canonical for e in frontier}), len(frontier))  # unique
        # the contrast: an uncapped walk would have reached branch**steps candidates.
        self.assertGreater(branch ** steps, 10 ** 10)           # >10 billion, unmanaged

    def test_total_recorded_plan_is_linear_in_hops(self):
        cap_k, max_hops, branch = 5, 8, 16
        expand = _exponential_expander(branch)
        line = CairnLine("walk", "ds@snap", limits=CairnLimits(max_hops=max_hops, max_cap_k=cap_k))
        frontier = [_ref("seed")]
        for _ in range(max_hops):
            frontier = bounded_frontier_step(
                expand(frontier), rank_key=lambda e: 0.0, cap_k=cap_k, limits=line.limits
            )
            line.record_step("expand", frontier, cap_k=cap_k)
        total_nodes = sum(len(s.frontier_out) for s in line.steps)
        # the whole plan is bounded by cap_k * max_hops regardless of branching factor
        self.assertLessEqual(total_nodes, cap_k * max_hops)
        self.assertLessEqual(len(line.steps), max_hops)


class InfiniteAndCyclicWalksTests(unittest.TestCase):
    def test_infinite_walk_is_halted_at_max_hops(self):
        max_hops = 6
        line = CairnLine("endless", "ds", limits=CairnLimits(max_hops=max_hops, max_cap_k=4))
        expand = _exponential_expander(4)
        frontier = [_ref("seed")]
        steps_taken = 0
        with self.assertRaises(ValueError):
            for _ in range(10_000):  # would run forever without the hop cap
                frontier = bounded_frontier_step(
                    expand(frontier), rank_key=lambda e: 0.0, cap_k=4, limits=line.limits
                )
                line.record_step("expand", frontier, cap_k=4)
                steps_taken += 1
        self.assertEqual(steps_taken, max_hops)          # stopped exactly at the cap
        self.assertEqual(len(line.steps), max_hops)

    def test_cycle_does_not_blow_up_the_frontier(self):
        # a cyclic expander keeps proposing the same 3 nodes; dedup keeps it bounded.
        cycle = [_ref("a"), _ref("b"), _ref("c")]
        def expand(_frontier):
            return cycle + cycle + cycle          # heavy revisiting
        frontier = list(cycle)
        seen_sizes = []
        for _ in range(20):
            frontier = bounded_frontier_step(expand(frontier), rank_key=lambda e: 0.0, cap_k=8)
            seen_sizes.append(len(frontier))
        self.assertTrue(all(sz == 3 for sz in seen_sizes))    # never grows past the 3 unique
        self.assertEqual({e.canonical for e in frontier}, {"demo:Node:a", "demo:Node:b", "demo:Node:c"})


class PolicyCeilingTests(unittest.TestCase):
    def test_cap_k_cannot_be_widened_past_policy(self):
        limits = CairnLimits(max_cap_k=4)
        # a caller cannot request a wider frontier than policy allows — fail closed.
        with self.assertRaises(ValueError):
            bounded_frontier_step([_ref("a")], rank_key=lambda e: 0.0, cap_k=1000, limits=limits)
        line = CairnLine("l", "d", limits=limits)
        with self.assertRaises(ValueError):
            line.record_step("expand", [_ref("a")], cap_k=1000)


class MaterializationEgressBoundedTests(unittest.TestCase):
    def test_output_bytes_never_exceed_budget_and_fetch_is_single_pass(self):
        # These are the *hard* guarantees for any target set / size distribution:
        # the granted payload can never exceed the byte budget, and materialize makes
        # a single pass (it never expands the target set into a fetch storm).
        targets = tuple(_ref(f"t{i}") for i in range(100))
        fetch_calls: list[str] = []

        def fetcher(target, mode, projection):
            fetch_calls.append(target.canonical)
            return {"id": target.canonical, "pad": "x" * 20}

        budget = 175  # deliberately NOT a clean multiple of the payload size
        result = materialize(
            MaterializeRequest(targets=targets, mode=MaterializeMode.METADATA_ONLY),
            MaterializePolicy(max_bytes=budget), fetcher,
        )
        self.assertLessEqual(result.total_bytes, budget)          # output hard-capped
        self.assertTrue(0 < len(result.granted) < len(targets))   # partial grant
        self.assertTrue(result.refused)                           # rest refused, not dropped
        self.assertLessEqual(len(fetch_calls), len(targets))      # single pass, no fan-out
        self.assertLessEqual(len(result.granted), len(fetch_calls))

    def test_short_circuit_withholds_without_fetch_once_budget_saturated(self):
        # With a target-independent fixed 40B payload and a budget that is an exact
        # multiple of it, the budget saturates precisely — after which remaining
        # targets are refused WITHOUT a fetch (no wasted governed egress).
        targets = tuple(_ref(f"t{i}") for i in range(50))
        fetch_calls: list[str] = []

        def fetcher(target, mode, projection):
            fetch_calls.append(target.canonical)
            return {"pad": "x" * 30}  # json -> exactly 40 bytes, independent of target

        result = materialize(
            MaterializeRequest(targets=targets, mode=MaterializeMode.METADATA_ONLY),
            MaterializePolicy(max_bytes=200), fetcher,  # exactly 5 * 40B
        )
        self.assertEqual(result.total_bytes, 200)                 # saturated to the budget
        self.assertEqual(len(result.granted), 5)
        self.assertEqual(len(fetch_calls), 5)                     # no fetch after saturation
        self.assertTrue(any("without fetch" in reason for _, reason in result.refused))


def _dumbbell():
    n = 8
    w = np.zeros((n, n))
    for group in (range(4), range(4, 8)):
        for i in group:
            for j in group:
                if i != j:
                    w[i, j] = 1.0
    w[3, 4] = w[4, 3] = 0.05
    return WeightedGraph(tuple(f"n{i}" for i in range(n)), w, w.sum(axis=1))


def _record(aid, nodes):
    return {
        "artifact": {"artifact_id": aid, "boundary": {"included_node_ids": nodes}},
        "compile": {"outcome": "ACCEPT", "certificate_refs": [{"evidence_id": f"cert-{aid}"}]},
    }


class ProductionRetrievalWalkIsBoundedTests(unittest.TestCase):
    """The real slot-filling cairnpath walk (retrieval.fill) obeys the same bounds."""

    def test_recorded_retrieval_line_stays_within_cap_and_hops(self):
        dmap = diffusion_coordinates(_dumbbell(), n_coords=3)
        filler = ArtifactSlotFiller(dmap, [
            _record("artA", ["n0", "n1", "n2", "n3"]),
            _record("artB", ["n4", "n5", "n6", "n7"]),
        ])
        cap_k = 2
        slots = [SlotSpec(name=f"s{i}", anchor_nodes=(f"n{i}",)) for i in range(6)]
        res = filler.fill(slots, cap_k=cap_k)

        line = res.cairnline
        self.assertIsNotNone(line)
        # every recorded step respected the frontier cap ...
        for step in line.steps:
            self.assertLessEqual(len(step.frontier_out), cap_k)
            self.assertLessEqual(step.cap_k, line.limits.max_cap_k)
        # ... the walk length is bounded by the hop policy ...
        self.assertLessEqual(len(line.steps), line.limits.max_hops)
        # ... and the whole recorded plan is bounded by cap_k * max_hops.
        total = sum(len(s.frontier_out) for s in line.steps)
        self.assertLessEqual(total, cap_k * line.limits.max_hops)


if __name__ == "__main__":
    unittest.main()
