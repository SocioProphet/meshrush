"""MR-08 — the governance seam (ADR 0005 §2–3).

The capstone of the scientific engine: it makes the observe→compile loop *governed*
rather than an open-ended agent process, and lets MeshRush extend that governance
over adjacent runtimes.

Three mechanics, all fail-closed:

  * **Bounded ExpansionPoint** — the observe→compile loop may only expand at declared
    points, each with admissible shapes and depth / breadth / budget caps. A loop is
    thus a *bounded* correction (it terminates and stays within budget), never an
    unbounded agent-authored edge — the "loop as DAG" discipline. `admit_expansion`
    refuses any step that breaches a cap.
  * **Conductor manifest** — a conductor (the human operator) publishes a
    content-addressed manifest declaring the admissible ExpansionPoints and allowed
    transforms. It "gates entrances and dynamics, not notes": nothing may author a
    claim outside a published manifest (`authorizes` fails closed on actor/transform).
  * **Adjacent-runtime seam** — an `agent-machine` governed execution receipt, or a
    `prophet-mesh` reasoning trace, becomes a MeshRush **observation** only when the
    manifest authorizes it; the observation carries an epistemic floor and provenance.

Stdlib only.
"""
from __future__ import annotations

from dataclasses import dataclass

from meshrush.core.cairn import canonical_hash
from meshrush.crystal.retrieval import EpistemicLevel


@dataclass(frozen=True)
class ExpansionPoint:
    """A declared, bounded place where the observe→compile loop may expand.

    ``admissible_shapes`` are the opcodes/shapes permitted to expand here; the
    depth / breadth / budget caps bound the loop so it terminates within budget.
    """

    name: str
    admissible_shapes: tuple[str, ...]
    max_depth: int
    max_breadth: int
    max_budget: float

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("ExpansionPoint.name must be non-empty")
        if self.max_depth < 1 or self.max_breadth < 1:
            raise ValueError("max_depth and max_breadth must be >= 1")
        if self.max_budget < 0:
            raise ValueError("max_budget must be >= 0")
        if not self.admissible_shapes:
            raise ValueError("an ExpansionPoint with no admissible shapes can never expand")


@dataclass(frozen=True)
class ExpansionState:
    """Progress through an ExpansionPoint: how deep, how wide, how much budget spent."""

    depth: int = 0
    breadth: int = 0
    spent: float = 0.0


@dataclass(frozen=True)
class ExpansionDecision:
    """The result of an admission check. ``next_state`` is set only when admitted."""

    admitted: bool
    reason: str
    next_state: "ExpansionState | None" = None


def admit_expansion(
    point: ExpansionPoint,
    state: ExpansionState,
    *,
    shape: str,
    breadth: int,
    cost: float,
) -> ExpansionDecision:
    """Fail-closed admission of one loop expansion step against a bounded point.

    Refuses (does not raise) when the shape is inadmissible or any cap would be
    breached, so the loop can record the refusal and halt rather than run away.
    """
    if shape not in point.admissible_shapes:
        return ExpansionDecision(False, f"shape {shape!r} not in admissible_shapes")
    if breadth < 1:
        return ExpansionDecision(False, "breadth must be >= 1")
    if cost < 0:
        return ExpansionDecision(False, "cost must be >= 0")
    if state.depth + 1 > point.max_depth:
        return ExpansionDecision(False, f"depth {state.depth + 1} exceeds max_depth {point.max_depth}")
    if breadth > point.max_breadth:
        return ExpansionDecision(False, f"breadth {breadth} exceeds max_breadth {point.max_breadth}")
    if state.spent + cost > point.max_budget:
        return ExpansionDecision(
            False, f"budget {state.spent + cost} exceeds max_budget {point.max_budget}"
        )
    return ExpansionDecision(
        True,
        "admitted",
        ExpansionState(depth=state.depth + 1, breadth=breadth, spent=state.spent + cost),
    )


@dataclass(frozen=True)
class ConductorManifest:
    """A published declaration by a conductor of what may run and expand.

    Content-addressed via [`manifest_id`]: the identity is the declaration itself,
    so an unpublished/edited manifest is a different manifest. It "gates entrances
    and dynamics, not notes" — nothing may author a claim outside it.
    """

    conductor_id: str
    expansion_points: tuple[ExpansionPoint, ...] = ()
    allowed_transforms: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.conductor_id:
            raise ValueError("a manifest with no conductor is unpublishable")

    @property
    def manifest_id(self) -> str:
        """Content address over the conductor + declared points + transforms."""
        return "manifest." + canonical_hash({
            "conductor_id": self.conductor_id,
            "allowed_transforms": sorted(self.allowed_transforms),
            "expansion_points": sorted(
                [
                    {
                        "name": p.name,
                        "admissible_shapes": sorted(p.admissible_shapes),
                        "max_depth": p.max_depth,
                        "max_breadth": p.max_breadth,
                        "max_budget": p.max_budget,
                    }
                    for p in self.expansion_points
                ],
                key=lambda d: d["name"],
            ),
        })

    def expansion_point(self, name: str) -> "ExpansionPoint | None":
        for p in self.expansion_points:
            if p.name == name:
                return p
        return None

    def authorizes(self, *, actor: str, transform: str) -> bool:
        """Fail-closed authority: only the conductor may act, and only via a declared
        transform. Anything else is unauthorized — there is no implicit permission."""
        return actor == self.conductor_id and transform in self.allowed_transforms


@dataclass(frozen=True)
class ExecutionReceipt:
    """A minimal ``agent-machine`` governed execution receipt to be governed here."""

    receipt_id: str
    actor: str
    transform: str
    outcome: str
    evidence_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class GovernedObservation:
    """A receipt/trace admitted as a MeshRush observation, or a refusal."""

    admitted: bool
    reason: str
    observation: "dict | None" = None


def govern_receipt(
    receipt: ExecutionReceipt,
    manifest: ConductorManifest,
    *,
    epistemic: EpistemicLevel = EpistemicLevel.EMPIRICAL,
) -> GovernedObservation:
    """Admit an ``agent-machine`` receipt as an observation iff the manifest authorizes
    its (actor, transform). Fail-closed: an unauthorized receipt yields no observation.

    A receipt is *measured* execution evidence, so the default epistemic floor is
    ``empirical`` — never above ``bounded`` (an observation is not a proof)."""
    if epistemic.rank > EpistemicLevel.BOUNDED.rank:
        raise ValueError("an observation cannot enter above 'bounded'")
    if not manifest.authorizes(actor=receipt.actor, transform=receipt.transform):
        return GovernedObservation(
            False,
            f"receipt actor/transform not authorized by manifest {manifest.manifest_id}",
        )
    observation = {
        "kind": "meshrush.observation",
        "source": "agent-machine.receipt",
        "receipt_id": receipt.receipt_id,
        "transform": receipt.transform,
        "outcome": receipt.outcome,
        "epistemic_level": epistemic.value,
        "evidence_refs": list(receipt.evidence_refs),
        "provenance": {"conductor_id": manifest.conductor_id, "manifest_id": manifest.manifest_id},
    }
    return GovernedObservation(True, "admitted", observation)


def reasoning_trace_to_observation(
    trace_id: str,
    content_ref: str,
    manifest: ConductorManifest,
    *,
    transform: str = "prophet-mesh.reason",
    epistemic: EpistemicLevel = EpistemicLevel.EMPIRICAL,
) -> GovernedObservation:
    """Admit a ``prophet-mesh`` reasoning trace as an observation under the manifest.

    Governed exactly like a receipt: the conductor must have declared ``transform``.
    """
    if epistemic.rank > EpistemicLevel.BOUNDED.rank:
        raise ValueError("an observation cannot enter above 'bounded'")
    if not manifest.authorizes(actor=manifest.conductor_id, transform=transform):
        return GovernedObservation(
            False, f"transform {transform!r} not authorized by manifest {manifest.manifest_id}"
        )
    observation = {
        "kind": "meshrush.observation",
        "source": "prophet-mesh.trace",
        "trace_id": trace_id,
        "content_ref": content_ref,
        "epistemic_level": epistemic.value,
        "provenance": {"conductor_id": manifest.conductor_id, "manifest_id": manifest.manifest_id},
    }
    return GovernedObservation(True, "admitted", observation)
