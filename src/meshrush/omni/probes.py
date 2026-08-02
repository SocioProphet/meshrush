"""MR-03 — the Omni probe families (meshrush ADR 0005, Omni-Crystal spec §11).

Standardized perturbations that measure how the observation graph responds, so the
Crystal layer can decide what to compile. Four families:

- **impulse** (§11.1) — inject a localized pulse at anchor nodes; measure how it
  spreads (participation ratio) and how much mass stays put (localization).
- **spectral band** (§11.2) — measure how much of a signal's energy lives in a
  chosen graph spectral band; tests whether a characteristic module scale exists.
- **seed persistence** (§11.3) — impose a candidate seed, hold it, release it, and
  measure whether the crystallinity survives — distinguishing a nucleated artifact
  from a purely diffusive fluctuation.
- **symmetry** (§11.4) — apply a candidate node permutation to a signal and compare
  the response transport: the active-equivariance defect ``||R(Πx) − Π R(x)||``.

Requires the ``scientific`` extra (``numpy``).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from meshrush.core.graph_build import WeightedGraph, laplacian, transition
from meshrush.crystal.dynamics import CrystalState, DynamicsParams, advance


# --------------------------------------------------------------------------- #
# §11.1 Local impulse probe
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ImpulseResponse:
    anchors: tuple[int, ...]
    distribution: np.ndarray        # random-walk distribution after `steps`
    participation_ratio: float      # 1..n; higher = more spread
    retained_at_anchors: float      # probability mass still on the anchor set


def impulse_probe(graph: WeightedGraph, anchors, *, steps: int = 4) -> ImpulseResponse:
    """Diffuse a unit pulse from ``anchors`` for ``steps`` random-walk steps."""
    if steps < 1:
        raise ValueError("steps must be >= 1")
    n = graph.n
    anchors = tuple(int(a) for a in anchors)
    if not anchors or any(a < 0 or a >= n for a in anchors):
        raise ValueError("anchors must be non-empty node indices in range")

    pi0 = np.zeros(n)
    pi0[list(anchors)] = 1.0 / len(anchors)
    p = transition(graph)
    pi = pi0 @ np.linalg.matrix_power(p, steps)

    ss = float(np.sum(pi ** 2))
    participation = 1.0 / ss if ss > 0 else float(n)
    retained = float(pi[list(anchors)].sum())
    return ImpulseResponse(
        anchors=anchors,
        distribution=pi,
        participation_ratio=participation,
        retained_at_anchors=retained,
    )


# --------------------------------------------------------------------------- #
# §11.2 Spectral band probe
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SpectralBandResponse:
    lo: float
    hi: float
    eigenvalues_in_band: int
    energy_fraction: float          # fraction of the signal's energy in the band


def spectral_band_probe(
    graph: WeightedGraph, lo: float, hi: float, *, signal: "np.ndarray | None" = None,
) -> SpectralBandResponse:
    """Fraction of ``signal``'s energy that lives in the Laplacian eigenband ``[lo, hi]``.

    With no signal, a fixed pseudo-random signal is used so the probe reports the
    band's share of a generic excitation.
    """
    if hi < lo:
        raise ValueError("hi must be >= lo")
    lap = laplacian(graph)
    vals, vecs = np.linalg.eigh(lap)
    if signal is None:
        signal = np.random.default_rng(0).standard_normal(graph.n)
    signal = np.asarray(signal, dtype=float)
    if signal.shape != (graph.n,):
        raise ValueError(f"signal must have shape ({graph.n},)")

    coeffs = vecs.T @ signal           # projection onto each eigenvector
    total = float(np.sum(coeffs ** 2))
    in_band = (vals >= lo) & (vals <= hi)
    band_energy = float(np.sum(coeffs[in_band] ** 2))
    frac = band_energy / total if total > 0 else 0.0
    return SpectralBandResponse(
        lo=lo, hi=hi,
        eigenvalues_in_band=int(in_band.sum()),
        energy_fraction=frac,
    )


# --------------------------------------------------------------------------- #
# §11.3 Seed persistence probe
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SeedPersistence:
    seed_nodes: tuple[int, ...]
    retained_crystallinity: float   # mean phi on the seed region after release
    control_crystallinity: float    # mean phi there with no seed (baseline)
    survived: bool                  # retained clearly above the control


def seed_persistence_probe(
    graph: WeightedGraph,
    seed_nodes,
    params: DynamicsParams,
    *,
    hold_steps: int = 3,
    release_steps: int = 3,
    threshold: float = 0.5,
) -> SeedPersistence:
    """Impose a crystallinity seed, hold it clamped, release, and measure survival."""
    n = graph.n
    seed_nodes = tuple(int(s) for s in seed_nodes)
    if not seed_nodes or any(s < 0 or s >= n for s in seed_nodes):
        raise ValueError("seed_nodes must be non-empty node indices in range")
    mask = np.zeros(n, dtype=bool)
    mask[list(seed_nodes)] = True

    def run(seeded: bool) -> float:
        state = CrystalState(c=np.zeros(n), phi=np.zeros(n))
        for _ in range(hold_steps):
            if seeded:
                state.phi[mask] = 1.0      # clamp the seed high
                state.c[mask] = 1.0
            state = advance(graph, state, params)
        for _ in range(release_steps):     # released: no clamping
            state = advance(graph, state, params)
        return float(state.phi[mask].mean())

    retained = run(seeded=True)
    control = run(seeded=False)
    return SeedPersistence(
        seed_nodes=seed_nodes,
        retained_crystallinity=retained,
        control_crystallinity=control,
        survived=retained > threshold and retained > control + 1e-6,
    )


# --------------------------------------------------------------------------- #
# §11.4 Symmetry probe (active equivariance)
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SymmetryDefect:
    defect: float                   # ||R(Πx) − Π R(x)|| / ||R(x)||
    equivariant: bool


def _permutation_matrix(perm: np.ndarray, n: int) -> np.ndarray:
    if sorted(perm.tolist()) != list(range(n)):
        raise ValueError("perm must be a permutation of range(n)")
    mat = np.zeros((n, n))
    mat[perm, np.arange(n)] = 1.0     # node i maps to position perm[i]
    return mat


def symmetry_probe(
    graph: WeightedGraph,
    perm,
    *,
    signal: "np.ndarray | None" = None,
    tol: float = 1e-6,
) -> SymmetryDefect:
    """Active-equivariance defect of the graph's response operator under ``perm``.

    The response operator is one random-walk step ``R = P``. For a graph
    automorphism ``P`` commutes with the permutation and the defect is ~0; a
    non-automorphism produces a positive defect (spec §11.4 / §12.5 ``d_R``).
    """
    n = graph.n
    perm = np.asarray(perm, dtype=int)
    if perm.shape != (n,):
        raise ValueError(f"perm must have shape ({n},)")
    pmat = _permutation_matrix(perm, n)
    p = transition(graph)
    if signal is None:
        signal = np.random.default_rng(0).standard_normal(n)
    signal = np.asarray(signal, dtype=float)

    r_of_perm = p @ (pmat @ signal)     # R(Πx)
    perm_of_r = pmat @ (p @ signal)     # Π R(x)
    base = float(np.linalg.norm(p @ signal))
    defect = float(np.linalg.norm(r_of_perm - perm_of_r)) / (base + 1e-12)
    return SymmetryDefect(defect=defect, equivariant=defect <= tol)
