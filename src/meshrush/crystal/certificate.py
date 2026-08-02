"""MR-06 — the 6-gate compile certificate + sp-orchestrator attestation handoff.

The keystone governance decision of the Crystal layer (Omni-Crystal spec §14): a
candidate region is compiled into a durable artifact ONLY if it passes all six
gates. This module produces the concrete **gate certificate** (the scientific
verdict) and bridges it onto two estate surfaces:

  * ``to_compile_decision`` → the contract-level ``CompileDecision`` /
    ``CompileOutcome`` vocabulary already used by the ``CrystalCompiler`` boundary
    (accept / rework / defer), so the certifier plugs into the existing lifecycle.
  * ``certificate_to_attestation`` → a content-addressed **attestation** carrying
    the derived epistemicLevel and the gate evidence: the artifact→durable-cell
    handoff sp-orchestrator ingests, so a compiled artifact is admissible,
    auditable, and never a bare claim.

The six gates (spec §14; gate 1 is the two conditions hardness AND support, so the
certificate records seven ``GateResult`` checks):
  1. hardness + support   mean phi > phi*, mean c > c*    (MR-02)
  2. symmetry             D_sym < eps_sym                 (MR-04a)
  3. spectral sharpness   S_sharp > s*                    (MR-03 probes)
  4. boundary defect      m^T L m / |m| < d*              (MR-01, below)
  5. persistence          T_persist > T*                  (MR-03 seed probe)
  6. compression gain     dH(codebook) > h*               (MR-05)

Discipline (ECO-1 / sp-core): thresholds are declared config, not hardcoded; an
UNCALIBRATED certifier cannot mint confidence — it DEFERS (SPECULATIVE), never
compiles. A passing artifact is BOUNDED at best (a compile is not a proof).

Stdlib + numpy (via core.graph_build for the boundary-defect helper).
"""
from __future__ import annotations

from dataclasses import dataclass

from meshrush.core.cairn import canonical_hash
from meshrush.core.contracts import CompileDecision, CompileOutcome, EvidenceRef
from meshrush.crystal.retrieval import EpistemicLevel


@dataclass(frozen=True)
class CompileThresholds:
    """Declared gate thresholds. Until calibrated against telemetry the certifier
    refuses to mint anything above SPECULATIVE (spec §19 thresholds are unset)."""

    phi_star: float = 0.75
    c_star: float = 0.0
    eps_sym: float = 1e-3
    s_star: float = 0.5
    d_star: float = 0.5
    t_star: float = 0.5
    h_star: float = 0.0
    calibrated: bool = False


@dataclass(frozen=True)
class CompileMetrics:
    """Measured properties of a candidate region (produced by MR-01/02/03/04a)."""

    mean_phi: float          # crystallinity (MR-02)
    mean_c: float            # support density (MR-02)
    d_sym: float             # symmetry defect (MR-04a)
    s_sharp: float           # spectral sharpness (MR-03 probes)
    d_gb: float              # boundary/grain defect (boundary_defect below)
    t_persist: float         # seed-persistence (MR-03 probes)
    delta_h: float           # codebook compression gain (MR-05)


@dataclass(frozen=True)
class GateResult:
    name: str
    value: float
    threshold: float
    op: str                  # ">" or "<"
    passed: bool


@dataclass(frozen=True)
class GateCertificate:
    """The 6-gate scientific verdict for a candidate region.

    Distinct from the contract-level ``compile.CompileCertificate`` (the durable
    boundary artifact); this is the gate evaluation that *decides* the compile.
    """

    artifact_id: str
    passed: bool
    epistemic: EpistemicLevel
    gates: tuple[GateResult, ...]
    rationale: str = ""

    @property
    def failed_gates(self) -> tuple[str, ...]:
        return tuple(g.name for g in self.gates if not g.passed)


def boundary_defect(graph, mask) -> float:
    """Grain-boundary defect ``D_gb = mᵀ L m / |m|`` (spec §14.4) for a 0/1 mask.

    Low when the artifact domain has a clean (low-cut) boundary on the graph.
    """
    import numpy as np
    from meshrush.core.graph_build import laplacian

    m = np.asarray(mask, dtype=float)
    if m.shape != (graph.n,):
        raise ValueError(f"mask length {m.shape} does not match graph size ({graph.n},)")
    if not np.all(np.isin(m, (0.0, 1.0))):
        # A binary indicator is required: fractional/negative entries silently compute
        # a different quantity and could be used to game D_gb past the gate.
        raise ValueError("mask must be a binary 0/1 indicator")
    denom = float(m.sum())
    if denom == 0.0:
        raise ValueError("mask is empty; boundary defect is undefined")
    lap = laplacian(graph)
    return float(m @ (lap @ m)) / denom


def _gate(name, value, threshold, op) -> GateResult:
    passed = value > threshold if op == ">" else value < threshold
    return GateResult(name, float(value), float(threshold), op, bool(passed))


def evaluate_certificate(
    artifact_id: str, metrics: CompileMetrics, thresholds: CompileThresholds
) -> GateCertificate:
    """Evaluate all six gates → a GateCertificate with a derived epistemicLevel."""
    gates = (
        _gate("hardness", metrics.mean_phi, thresholds.phi_star, ">"),
        _gate("support", metrics.mean_c, thresholds.c_star, ">"),
        _gate("symmetry", metrics.d_sym, thresholds.eps_sym, "<"),
        _gate("spectral_sharpness", metrics.s_sharp, thresholds.s_star, ">"),
        _gate("boundary_defect", metrics.d_gb, thresholds.d_star, "<"),
        _gate("persistence", metrics.t_persist, thresholds.t_star, ">"),
        _gate("compression_gain", metrics.delta_h, thresholds.h_star, ">"),
    )
    all_pass = all(g.passed for g in gates)

    # ECO-1 discipline: an uncalibrated certifier cannot mint confidence.
    if not thresholds.calibrated:
        return GateCertificate(
            artifact_id, passed=False, epistemic=EpistemicLevel.SPECULATIVE, gates=gates,
            rationale="thresholds not calibrated; refusing to compile above Speculative",
        )
    if all_pass:
        # Gate-passing, symmetry-certified artifact is Bounded at best (never a proof).
        return GateCertificate(
            artifact_id, passed=True, epistemic=EpistemicLevel.BOUNDED, gates=gates,
            rationale="all six compile gates passed",
        )
    return GateCertificate(
        artifact_id, passed=False, epistemic=EpistemicLevel.SYNTHETIC, gates=gates,
        rationale=f"compile gates failed: {[g.name for g in gates if not g.passed]}",
    )


def to_compile_decision(
    cert: GateCertificate, *, candidate_region_id: str, attestation_id: str | None = None
) -> CompileDecision:
    """Bridge the gate verdict onto the estate ``CompileOutcome`` lifecycle.

    * BOUNDED (all gates pass)        → ACCEPT
    * SYNTHETIC (calibrated, failed)  → REWORK (revise the candidate and retry)
    * SPECULATIVE (uncalibrated)      → DEFER  (cannot decide; fail-closed)
    """
    if cert.epistemic is EpistemicLevel.BOUNDED:
        outcome = CompileOutcome.ACCEPT
    elif cert.epistemic is EpistemicLevel.SYNTHETIC:
        outcome = CompileOutcome.REWORK
    else:
        outcome = CompileOutcome.DEFER
    refs: tuple[EvidenceRef, ...] = ()
    if attestation_id is not None:
        refs = (EvidenceRef(evidence_id=attestation_id, kind="compile_attestation"),)
    return CompileDecision(
        candidate_region_id=candidate_region_id,
        outcome=outcome,
        reasons=(cert.rationale,) if cert.rationale else (),
        certificate_refs=refs,
        metadata={"epistemic_level": cert.epistemic.value, "failed_gates": list(cert.failed_gates)},
    )


def certificate_to_attestation(
    cert: GateCertificate,
    *,
    included_node_ids: "tuple[str, ...]",
    graph_view_id: str,
    provenance: "dict | None" = None,
) -> dict:
    """Artifact → durable content-addressed cell/attestation (the sp-orchestrator handoff).

    The attestation is content-addressed over the certificate + boundary + provenance,
    carries the epistemicLevel (sp-core lattice), and records every gate as evidence —
    so sp-orchestrator can ingest it as a durable cell with lineage.
    """
    body = {
        "kind": "meshrush.compile_attestation",
        "schema_version": "0.1.0",
        "artifact_id": cert.artifact_id,
        "graph_view_id": graph_view_id,
        "passed": cert.passed,
        "epistemic_level": cert.epistemic.value,
        "boundary": {"included_node_ids": list(included_node_ids)},
        "gates": [
            {"name": g.name, "value": g.value, "threshold": g.threshold, "op": g.op, "passed": g.passed}
            for g in cert.gates
        ],
        "rationale": cert.rationale,
        "provenance": provenance or {},
    }
    body["attestation_id"] = "att." + canonical_hash(body)
    return body
