import unittest

import numpy as np

from meshrush.core.graph_build import WeightedGraph
from meshrush.omni.reduction import diffusion_coordinates
from meshrush.crystal.retrieval import (
    ArtifactSlotFiller,
    EpistemicLevel,
    SlotSpec,
    artifact_epistemic,
)
from meshrush.adapters.crystal_atlas.contracts import fills_to_graph_upsert
from meshrush.adapters.sherlock.contracts import fills_to_evidence_answer


def _dumbbell():
    # Two 4-cliques joined by a weak bridge -> connected, two clear lobes.
    n = 8
    w = np.zeros((n, n))
    for group in (range(4), range(4, 8)):
        for i in group:
            for j in group:
                if i != j:
                    w[i, j] = 1.0
    w[3, 4] = w[4, 3] = 0.05
    return WeightedGraph(
        node_ids=tuple(f"n{i}" for i in range(n)),
        weights=w,
        degrees=w.sum(axis=1),
    )


def _record(aid, nodes, outcome="ACCEPT", cert=True):
    return {
        "artifact": {"artifact_id": aid, "boundary": {"included_node_ids": nodes}},
        "compile": {
            "outcome": outcome,
            "certificate_refs": [{"evidence_id": f"cert-{aid}"}] if cert else [],
        },
    }


class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.g = _dumbbell()
        self.dmap = diffusion_coordinates(self.g, n_coords=3)
        self.art_a = _record("artA", ["n0", "n1", "n2", "n3"])                 # bounded
        self.art_b = _record("artB", ["n4", "n5", "n6", "n7"], outcome="DEFER")  # synthetic
        self.filler = ArtifactSlotFiller(self.dmap, [self.art_a, self.art_b])

    def test_fills_nearest_artifact_per_slot(self):
        res = self.filler.fill([
            SlotSpec(name="lobeA", anchor_nodes=("n0",)),
            SlotSpec(name="lobeB", anchor_nodes=("n7",)),
        ])
        self.assertTrue(res.all_filled)
        self.assertEqual(res.fills["lobeA"].artifact_id, "artA")
        self.assertEqual(res.fills["lobeB"].artifact_id, "artB")
        self.assertEqual(res.fills["lobeA"].epistemic, EpistemicLevel.BOUNDED)

    def test_epistemic_floor_refuses_rather_than_backfills(self):
        res = self.filler.fill([
            SlotSpec(name="need_proof", anchor_nodes=("n0",), min_epistemic=EpistemicLevel.PROVED),
        ])
        self.assertFalse(res.all_filled)
        self.assertNotIn("need_proof", res.fills)
        refusal = res.refused[0]
        self.assertEqual(refusal.slot_name, "need_proof")
        self.assertEqual(refusal.best_available_epistemic, EpistemicLevel.BOUNDED)

    def test_bounded_floor_only_qualifies_bounded_artifact(self):
        # Anchored at lobe B, but a BOUNDED floor excludes the (synthetic) lobe-B
        # artifact; the only qualifying artifact is the (far) bounded lobe-A one.
        res = self.filler.fill([
            SlotSpec(name="s", anchor_nodes=("n7",), min_epistemic=EpistemicLevel.BOUNDED),
        ])
        self.assertEqual(res.fills["s"].artifact_id, "artA")

    def test_missing_anchor_is_refused(self):
        res = self.filler.fill([SlotSpec(name="ghost", anchor_nodes=("nope",))])
        self.assertFalse(res.all_filled)
        self.assertIn("not present", res.refused[0].reason)

    def test_index_rejects_artifact_with_unknown_nodes(self):
        with self.assertRaises(ValueError):
            ArtifactSlotFiller(self.dmap, [_record("bad", ["zzz"])])

    def test_artifact_epistemic_derivation(self):
        self.assertEqual(artifact_epistemic(_record("x", ["n0"])), EpistemicLevel.BOUNDED)
        self.assertEqual(artifact_epistemic(_record("x", ["n0"], cert=False)), EpistemicLevel.EMPIRICAL)
        self.assertEqual(artifact_epistemic(_record("x", ["n0"], outcome="DEFER")), EpistemicLevel.SYNTHETIC)
        self.assertEqual(artifact_epistemic(_record("x", ["n0"], outcome="REJECT")), EpistemicLevel.REJECTED)
        self.assertEqual(artifact_epistemic({"compile": {}}), EpistemicLevel.SPECULATIVE)


class CrystalAtlasAdapterTests(unittest.TestCase):
    def setUp(self):
        g = _dumbbell()
        dmap = diffusion_coordinates(g, n_coords=3)
        filler = ArtifactSlotFiller(dmap, [_record("artA", ["n0", "n1", "n2", "n3"])])
        self.res = filler.fill([SlotSpec(name="lobeA", anchor_nodes=("n0",))])

    def test_graph_upsert_shape_and_fields(self):
        up = fills_to_graph_upsert(self.res, tenant_id="tenantX", timestamp="2026-08-02T00:00:00Z")
        self.assertEqual(set(up), {"tenant_id", "nodes", "edges", "claims", "evidence"})
        self.assertEqual(up["tenant_id"], "tenantX")
        node = up["nodes"][0]
        self.assertEqual(node["node_kind"], "evidence_bundle")
        self.assertEqual(node["attributes"]["epistemic_level"], "bounded")
        claim = up["claims"][0]
        self.assertEqual(claim["predicate"], "filled_by")
        self.assertEqual(claim["subject_ref"], "slot:lobeA")
        self.assertEqual(claim["evidence_refs"], [up["evidence"][0]["evidence_id"]])


class SherlockAdapterTests(unittest.TestCase):
    def setUp(self):
        g = _dumbbell()
        dmap = diffusion_coordinates(g, n_coords=3)
        self.filler = ArtifactSlotFiller(dmap, [_record("artA", ["n0", "n1", "n2", "n3"])])

    def test_evidence_answer_filled_and_refused(self):
        res = self.filler.fill([
            SlotSpec(name="ok", anchor_nodes=("n0",)),
            SlotSpec(name="tooHigh", anchor_nodes=("n0",), min_epistemic=EpistemicLevel.PROVED),
        ])
        ans = fills_to_evidence_answer(res, "who competes here?", trace_id="t1")
        self.assertEqual(set(ans), {"query", "anchors", "evidence", "proposedClaims",
                                    "explanationTrace", "policyDecision"})
        by_id = {c["claimId"]: c for c in ans["proposedClaims"]}
        self.assertEqual(by_id["claim:ok"]["status"], "proposed")
        self.assertEqual(by_id["claim:ok"]["epistemicLevel"], "bounded")
        self.assertIn("lower", by_id["claim:ok"]["confidenceBounds"])
        # The refused slot is carried as an abstained claim, not dropped.
        self.assertEqual(by_id["claim:tooHigh"]["status"], "abstained")
        self.assertEqual(by_id["claim:tooHigh"]["evidenceRefs"], [])


if __name__ == "__main__":
    unittest.main()
