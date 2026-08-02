import math
import unittest

import numpy as np

from meshrush.core.graph_build import build_knn_graph
from meshrush.omni.reduction import diffusion_coordinates
from meshrush.crystal.retrieval import ArtifactSlotFiller, SlotSpec, dedup_by_symmetry
from meshrush.crystal.retrieval import IndexedArtifact
from meshrush.crystal.retrieval import EpistemicLevel
from meshrush.adapters.memory_mesh.contracts import (
    build_recall_request,
    prime_slot,
    recalled_anchor_nodes,
    scope_envelope,
)


def _ring(n):
    emb = [[math.cos(2 * math.pi * i / n), math.sin(2 * math.pi * i / n)] for i in range(n)]
    return build_knn_graph(emb, k=2)


def _record(aid, nodes):
    return {"artifact": {"artifact_id": aid, "boundary": {"included_node_ids": nodes}},
            "compile": {"outcome": "ACCEPT", "certificate_refs": [{"evidence_id": f"c-{aid}"}]}}


class SymmetryAwareRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.g = _ring(8)
        self.dmap = diffusion_coordinates(self.g, n_coords=3)
        # A over {n0,n1}, B over {n2,n3} — rotations of each other by 2 on the ring.
        self.arts = [_record("A", ["n0", "n1"]), _record("B", ["n2", "n3"])]
        self.rot2 = np.array([(i + 2) % 8 for i in range(8)])

    def test_symmetric_artifacts_are_deduped_to_one_orbit_rep(self):
        plain = ArtifactSlotFiller(self.dmap, self.arts)
        self.assertEqual(len(plain._artifacts), 2)
        symm = ArtifactSlotFiller(self.dmap, self.arts, symmetry_generators=[self.rot2], symmetry_graph=self.g)
        self.assertEqual(len(symm._artifacts), 1)  # A and B are one finding up to symmetry

    def test_non_automorphism_generator_fails_closed(self):
        bad = np.array([1, 0, 2, 3, 4, 5, 6, 7])  # adjacent transposition — not a ring automorphism
        with self.assertRaises(ValueError):
            ArtifactSlotFiller(self.dmap, self.arts, symmetry_generators=[bad], symmetry_graph=self.g)

    def test_generators_require_graph(self):
        with self.assertRaises(ValueError):
            ArtifactSlotFiller(self.dmap, self.arts, symmetry_generators=[self.rot2])

    def test_orbit_exceeding_cap_fails_closed(self):
        # Rotation-by-1 on the 8-ring: a single node's orbit is all 8 nodes.
        rot1 = np.array([(i + 1) % 8 for i in range(8)])
        art = IndexedArtifact(
            artifact_id="A", node_ids=("n0",),
            centroid=np.zeros(3), epistemic=EpistemicLevel.BOUNDED,
        )
        with self.assertRaises(ValueError):
            dedup_by_symmetry([art], [rot1], tuple(self.dmap.node_ids), self.g, max_orbit=3)


class RecallPrimingTests(unittest.TestCase):
    def test_build_recall_request_shape(self):
        env = scope_envelope(user_id="u1", agent_id="a1", run_id="r1")
        slot = SlotSpec(name="competitors", anchor_nodes=("n0",), description="who competes here")
        req = build_recall_request(slot, envelope=env, top_k=7)
        self.assertEqual(set(req), {"envelope", "query", "top_k", "scope_order", "include_relations", "filters"})
        self.assertEqual(req["query"], "who competes here")
        self.assertEqual(req["top_k"], 7)
        self.assertEqual(req["filters"], {"slot": "competitors"})
        self.assertEqual(req["envelope"]["user_id"], "u1")

    def test_scope_envelope_emits_only_non_null(self):
        env = scope_envelope(user_id="u1")
        self.assertEqual(env, {"source_interface": "meshrush", "user_id": "u1"})

    def test_recalled_anchor_nodes_extracts_and_dedups(self):
        resp = {"hits": [
            {"memory_id": "m1", "metadata": {"node_id": "n5"}},
            {"memory_id": "m2", "metadata": {"node_id": "n5"}},   # dup
            {"memory_id": "m3", "metadata": {}},                  # no node_id -> ignored
            {"memory_id": "m4", "metadata": {"node_id": "n6"}},
        ]}
        self.assertEqual(recalled_anchor_nodes(resp), ["n5", "n6"])

    def test_prime_slot_is_additive_and_preserves_declared_anchors(self):
        slot = SlotSpec(name="s", anchor_nodes=("n0",))
        resp = {"hits": [{"metadata": {"node_id": "n0"}}, {"metadata": {"node_id": "n5"}}]}
        primed = prime_slot(slot, resp)
        self.assertEqual(primed.anchor_nodes, ("n0", "n5"))  # existing lead, recalled appended, n0 dedup
        # No recalled nodes -> unchanged object identity semantics (returns same slot).
        self.assertIs(prime_slot(slot, {"hits": []}), slot)


if __name__ == "__main__":
    unittest.main()
