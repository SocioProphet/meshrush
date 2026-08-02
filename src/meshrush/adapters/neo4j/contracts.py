"""Project cairnpath / crystal artifacts into Neo4j (CP-05).

Contract-first: this emits **parameterized Cypher statements** (query + params) as
data — it never opens a driver or a socket. A caller with a licensed Neo4j driver
runs them; MeshRush stays sovereign and side-effect-free.

Security: node/relationship *labels* are fixed constants (Cypher cannot parameterize
them, and they never come from artifact data), while every artifact-derived value
travels in the ``params`` map via ``$`` placeholders — so a maliciously crafted
line_id / entity id cannot inject Cypher.

Two projections:
  * ``cairnline_to_cypher`` — a CairnLine as ``(:CairnLine)-[:HAS_STEP]->(:CairnStep)``
    chained ``[:NEXT]``, each step ``[:REACHED]->(:Entity)`` for its frontier.
  * ``orbits_to_cypher`` — MR-04b automorphism orbits as ``(:Orbit)-[:CONTAINS]->(:Node)``
    equivalence classes under a named graph view.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from meshrush.core.cairn import CairnLine


@dataclass(frozen=True)
class CypherStatement:
    """A single parameterized Cypher statement. ``params`` carries all data values."""

    query: str
    params: dict = field(default_factory=dict)


def cairnline_to_cypher(line: CairnLine) -> list[CypherStatement]:
    """Project a CairnLine (and its steps/frontier) into parameterized Cypher."""
    stmts: list[CypherStatement] = [
        CypherStatement(
            "MERGE (l:CairnLine {line_id: $line_id}) "
            "SET l.dataset_ref = $dataset_ref, l.digest = $digest",
            {"line_id": line.line_id, "dataset_ref": line.dataset_ref, "digest": line.digest},
        )
    ]
    prev_digest: str | None = None
    for step in line.steps:
        stmts.append(CypherStatement(
            "MATCH (l:CairnLine {line_id: $line_id}) "
            "MERGE (s:CairnStep {digest: $digest}) "
            "SET s.index = $index, s.opcode = $opcode, s.cap_k = $cap_k, "
            "s.rank_policy = $rank_policy, s.materialized = $materialized "
            "MERGE (l)-[:HAS_STEP]->(s)",
            {
                "line_id": line.line_id, "digest": step.digest, "index": step.index,
                "opcode": step.opcode, "cap_k": step.cap_k,
                "rank_policy": step.rank_policy, "materialized": step.materialized,
            },
        ))
        if prev_digest is not None:
            stmts.append(CypherStatement(
                "MATCH (a:CairnStep {digest: $prev}), (b:CairnStep {digest: $cur}) "
                "MERGE (a)-[:NEXT]->(b)",
                {"prev": prev_digest, "cur": step.digest},
            ))
        for canon in step.frontier_out:
            stmts.append(CypherStatement(
                "MATCH (s:CairnStep {digest: $digest}) "
                "MERGE (e:Entity {canonical: $canonical}) "
                "MERGE (s)-[:REACHED]->(e)",
                {"digest": step.digest, "canonical": canon},
            ))
        prev_digest = step.digest
    return stmts


def orbits_to_cypher(
    orbits: "tuple[tuple[int, ...], ...]",
    *,
    graph_id: str,
    node_ids: "tuple[str, ...] | None" = None,
) -> list[CypherStatement]:
    """Project automorphism orbits (MR-04b) as ``(:Orbit)-[:CONTAINS]->(:Node)`` classes.

    ``node_ids`` optionally maps integer node indices to stable identifiers; without
    it, indices are used as ``"<graph_id>:<index>"``.
    """
    stmts: list[CypherStatement] = []
    for oi, orbit in enumerate(orbits):
        orbit_key = f"{graph_id}:orbit:{oi}"
        stmts.append(CypherStatement(
            "MERGE (o:Orbit {orbit_id: $orbit_id}) SET o.graph_id = $graph_id, o.size = $size",
            {"orbit_id": orbit_key, "graph_id": graph_id, "size": len(orbit)},
        ))
        for idx in orbit:
            node_key = node_ids[idx] if node_ids is not None else f"{graph_id}:{idx}"
            stmts.append(CypherStatement(
                "MATCH (o:Orbit {orbit_id: $orbit_id}) "
                "MERGE (n:Node {node_id: $node_id}) "
                "MERGE (o)-[:CONTAINS]->(n)",
                {"orbit_id": orbit_key, "node_id": node_key},
            ))
    return stmts
