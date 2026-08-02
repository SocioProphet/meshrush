import unittest

from meshrush.core.cairn import CairnLimits, CairnLine, EntityRef
from meshrush.adapters.neo4j.contracts import (
    CypherStatement,
    cairnline_to_cypher,
    orbits_to_cypher,
)
from meshrush.adapters.atomspace.contracts import (
    cairnline_to_atomese,
    orbits_to_atomese,
)


def _line(line_id="L1"):
    line = CairnLine(line_id=line_id, dataset_ref="ds:test", limits=CairnLimits(max_cap_k=8))
    line.record_step(
        "expand",
        [EntityRef("ns", "doc", "a"), EntityRef("ns", "doc", "b")],
        cap_k=4,
    )
    line.record_step("expand", [EntityRef("ns", "doc", "b")], cap_k=4)
    return line


class Neo4jTests(unittest.TestCase):
    def test_cairnline_projection_shape(self):
        stmts = cairnline_to_cypher(_line())
        self.assertIsInstance(stmts[0], CypherStatement)
        self.assertIn("MERGE (l:CairnLine", stmts[0].query)
        self.assertEqual(stmts[0].params["line_id"], "L1")
        joined = " ".join(s.query for s in stmts)
        self.assertIn("HAS_STEP", joined)
        self.assertIn("NEXT", joined)     # two steps -> a NEXT edge
        self.assertIn("REACHED", joined)  # frontier entities

    def test_all_data_values_travel_in_params_not_query(self):
        # injection-safety: a hostile line_id must never appear in a query string
        evil = 'x"}) DETACH DELETE n //'
        stmts = cairnline_to_cypher(_line(line_id=evil))
        self.assertTrue(any(s.params.get("line_id") == evil for s in stmts))
        for s in stmts:
            self.assertNotIn("DETACH DELETE", s.query)
            self.assertNotIn(evil, s.query)

    def test_orbits_projection(self):
        stmts = orbits_to_cypher(((0, 1), (2,)), graph_id="g1", node_ids=("u", "v", "w"))
        joined = " ".join(s.query for s in stmts)
        self.assertIn(":Orbit", joined)
        self.assertIn("CONTAINS", joined)
        node_ids = {s.params.get("node_id") for s in stmts if "node_id" in s.params}
        self.assertEqual(node_ids, {"u", "v", "w"})

    def test_orbits_default_node_keys(self):
        stmts = orbits_to_cypher(((0, 1),), graph_id="g1")
        keys = {s.params.get("node_id") for s in stmts if "node_id" in s.params}
        self.assertEqual(keys, {"g1:0", "g1:1"})


class AtomeseTests(unittest.TestCase):
    def test_cairnline_projection(self):
        atoms = cairnline_to_atomese(_line())
        self.assertIn('(ConceptNode "meshrush:cairnline:L1")', atoms)
        self.assertTrue(any("has_step" in a for a in atoms))
        self.assertTrue(any("next_step" in a for a in atoms))
        self.assertTrue(any("reached" in a for a in atoms))

    def test_names_are_escaped(self):
        line = CairnLine(line_id='has"quote', dataset_ref="ds", limits=CairnLimits())
        line.record_step("expand", [EntityRef("ns", "k", 'v"x')], cap_k=4)
        atoms = cairnline_to_atomese(line)
        # the raw unescaped quote must not appear; the escaped form must
        self.assertTrue(any('has\\"quote' in a for a in atoms))

    def test_orbits_projection(self):
        atoms = orbits_to_atomese(((0, 1), (2,)), graph_id="g1", node_ids=("u", "v", "w"))
        self.assertIn('(ConceptNode "meshrush:orbit:g1:0")', atoms)
        self.assertTrue(any("MemberLink" in a for a in atoms))
        self.assertTrue(any('"u"' in a for a in atoms))


if __name__ == "__main__":
    unittest.main()
