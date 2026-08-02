"""Project cairnpath / crystal artifacts into AtomSpace / Atomese (CP-05).

Contract-first: this emits **Atomese s-expressions** as strings — it never loads
OpenCog or touches a running AtomSpace. A caller with a licensed AtomSpace ingests
them; MeshRush stays sovereign and side-effect-free.

Node names are quoted Atomese strings; ``_atom_name`` escapes embedded quotes and
backslashes so artifact-derived identifiers cannot produce malformed atoms.

Two projections:
  * ``cairnline_to_atomese`` — a CairnLine as ConceptNodes linked by ``has_step`` /
    ``next_step`` / ``reached`` EvaluationLinks over ListLinks.
  * ``orbits_to_atomese`` — MR-04b orbits as ``MemberLink``s of each node into its
    orbit ConceptNode (equivalence classes).
"""
from __future__ import annotations

from meshrush.core.cairn import CairnLine


def _atom_name(s: str) -> str:
    """Escape a string for use inside an Atomese ``"..."`` node name."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


def _concept(name: str) -> str:
    return f'(ConceptNode "{_atom_name(name)}")'


def _eval(predicate: str, *members: str) -> str:
    listlink = "(ListLink " + " ".join(members) + ")"
    return f'(EvaluationLink (PredicateNode "{_atom_name(predicate)}") {listlink})'


def cairnline_to_atomese(line: CairnLine) -> list[str]:
    """Project a CairnLine (and its steps/frontier) into Atomese s-expressions."""
    line_atom = _concept(f"meshrush:cairnline:{line.line_id}")
    atoms: list[str] = [line_atom]
    prev_atom: str | None = None
    for step in line.steps:
        # line-scope the step atom: CairnStep.digest excludes line_id, so naming by
        # digest alone would collide (and cross-link next_step) across CairnLines.
        step_atom = _concept(f"meshrush:cairnstep:{line.line_id}:{step.digest}")
        atoms.append(step_atom)
        atoms.append(_eval("has_step", line_atom, step_atom))
        if prev_atom is not None:
            atoms.append(_eval("next_step", prev_atom, step_atom))
        for canon in step.frontier_out:
            atoms.append(_eval("reached", step_atom, _concept(f"meshrush:entity:{canon}")))
        prev_atom = step_atom
    return atoms


def orbits_to_atomese(
    orbits: "tuple[tuple[int, ...], ...]",
    *,
    graph_id: str,
    node_ids: "tuple[str, ...] | None" = None,
) -> list[str]:
    """Project automorphism orbits (MR-04b) as MemberLinks into orbit ConceptNodes."""
    atoms: list[str] = []
    for oi, orbit in enumerate(orbits):
        orbit_atom = _concept(f"meshrush:orbit:{graph_id}:{oi}")
        atoms.append(orbit_atom)
        for idx in orbit:
            node_key = node_ids[idx] if node_ids is not None else f"{graph_id}:{idx}"
            atoms.append(f"(MemberLink {_concept(node_key)} {orbit_atom})")
    return atoms
