"""MR-02 — crystal phase-field dynamics (meshrush ADR 0005, Omni-Crystal spec §9).

Two coupled graph fields evolve over the observation graph built in MR-01:

- **support density** ``c`` — where evidence/coherence is accumulating. Evolved by
  a graph Cahn-Hilliard-like update: a double-well bulk drive, a graph interfacial
  penalty, an optional preferred-band term, and coupling to crystallinity (§9.1).
  With no decay/injection the update is **conservative** (``sum(c)`` preserved),
  because ``L`` has zero row sums.
- **crystallinity** ``phi in [0,1]`` — whether that support is hardening into a
  durable object. Evolved by a graph Allen-Cahn update: a ``[0,1]`` double-well,
  a smoothing term, promotion by support, reward by relevance, suppression by
  symmetry-defect pressure, and optional annealed noise (§9.2). Projected to
  ``[0,1]`` each step.

An optional MBO threshold pass (§9.3) sharpens a soft mask into a hard artifact
domain via short diffusion + thresholding.

Requires the ``scientific`` extra (``numpy``); operates on ``core.graph_build`` graphs.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from meshrush.core.graph_build import WeightedGraph, laplacian


@dataclass(frozen=True)
class DynamicsParams:
    """Phase-field coefficients. Defaults keep the base behaviour plain (band term,
    external injection, decay, relevance, symmetry, and noise all OFF) so the base
    update is conservative Cahn-Hilliard / Allen-Cahn; enable terms explicitly."""

    # support density (c)
    a: float = 1.0              # double-well bulk drive
    kappa_c: float = 1.0        # graph interfacial penalty
    kappa_b: float = 0.0        # preferred-band term (off by default)
    omega0: float = 0.0         # band target (normalized-Laplacian eigenvalue)
    eta: float = 0.1            # c <-> phi coupling
    tau_c: float = 0.01         # support time step
    beta_u: float = 0.0         # external observation injection (off)
    gamma_c: float = 0.0        # support decay (off -> conservative)
    # crystallinity (phi)
    nu: float = 1.0             # [0,1] double-well strength
    kappa_phi: float = 0.1      # crystallinity smoothing
    lambda_rel: float = 0.0     # relevance reward (off)
    lambda_sym: float = 0.0     # symmetry-defect suppression (off)
    tau_phi: float = 0.05       # crystallinity time step
    # annealed noise
    sigma0: float = 0.0         # initial noise scale (off)
    rho: float = 0.95           # anneal factor per step


@dataclass
class CrystalState:
    """Evolving fields over the graph. ``step`` drives the noise anneal."""

    c: np.ndarray
    phi: np.ndarray
    step: int = 0
    history: list = field(default_factory=list)


def normalized_laplacian(graph: WeightedGraph) -> tuple[np.ndarray, float]:
    """Return ``(L_tilde, lambda_max)`` where ``L_tilde = L / (lambda_max + eps)``."""
    lap = laplacian(graph)
    lam_max = float(np.linalg.eigvalsh(lap).max())
    return lap / (lam_max + 1e-12), lam_max


def support_step(
    graph: WeightedGraph,
    c: np.ndarray,
    phi: np.ndarray,
    params: DynamicsParams,
    *,
    u: "np.ndarray | None" = None,
    lap: "np.ndarray | None" = None,
    l_tilde: "np.ndarray | None" = None,
) -> np.ndarray:
    """One support-density update (spec §9.1)."""
    p = params
    lap = laplacian(graph) if lap is None else lap
    if p.kappa_b != 0.0 and l_tilde is None:
        l_tilde, _ = normalized_laplacian(graph)

    mu = p.a * (c ** 3 - c) + p.kappa_c * (lap @ c) - p.eta * phi
    if p.kappa_b != 0.0:
        m = l_tilde - p.omega0 * np.eye(graph.n)
        mu = mu + p.kappa_b * (m @ (m @ c))

    c_new = c - p.tau_c * (lap @ mu) - p.gamma_c * c
    if p.beta_u != 0.0 and u is not None:
        u = np.asarray(u, dtype=float)
        c_new = c_new + p.beta_u * (u - u.mean())
    return c_new


def crystallinity_step(
    graph: WeightedGraph,
    phi: np.ndarray,
    c: np.ndarray,
    params: DynamicsParams,
    *,
    r: "np.ndarray | None" = None,
    s: "np.ndarray | None" = None,
    step: int = 0,
    rng: "np.random.Generator | None" = None,
    lap: "np.ndarray | None" = None,
) -> np.ndarray:
    """One crystallinity update, projected to ``[0,1]`` (spec §9.2)."""
    p = params
    lap = laplacian(graph) if lap is None else lap
    n = graph.n
    r = np.zeros(n) if r is None else np.asarray(r, dtype=float)
    s = np.zeros(n) if s is None else np.asarray(s, dtype=float)

    g = (
        2.0 * p.nu * phi * (1.0 - phi) * (1.0 - 2.0 * phi)
        + p.kappa_phi * (lap @ phi)
        - p.eta * c
        - p.lambda_rel * r
        + p.lambda_sym * s
    )
    phi_new = phi - p.tau_phi * g
    if p.sigma0 != 0.0:
        rng = np.random.default_rng() if rng is None else rng
        sigma_n = p.sigma0 * (p.rho ** step)
        phi_new = phi_new + sigma_n * rng.standard_normal(n)
    return np.clip(phi_new, 0.0, 1.0)


def mbo_step(mask: np.ndarray, graph: WeightedGraph, tau_m: float, *, lap: "np.ndarray | None" = None) -> np.ndarray:
    """MBO threshold pass (spec §9.3): short diffusion ``exp(-tau_m L)`` then a
    0.5 threshold, sharpening a soft mask into a hard 0/1 artifact domain.

    The matrix exponential is computed from the symmetric eigendecomposition of
    ``L`` (numpy only)."""
    if tau_m < 0:
        raise ValueError("tau_m must be >= 0")
    lap = laplacian(graph) if lap is None else lap
    vals, vecs = np.linalg.eigh(lap)
    diffused = vecs @ (np.exp(-tau_m * vals) * (vecs.T @ np.asarray(mask, dtype=float)))
    return (diffused > 0.5).astype(float)


def advance(
    graph: WeightedGraph,
    state: CrystalState,
    params: DynamicsParams,
    *,
    u: "np.ndarray | None" = None,
    r: "np.ndarray | None" = None,
    s: "np.ndarray | None" = None,
    rng: "np.random.Generator | None" = None,
) -> CrystalState:
    """Advance both fields one step: support then crystallinity (shares one ``L``)."""
    lap = laplacian(graph)
    c_new = support_step(graph, state.c, state.phi, params, u=u, lap=lap)
    phi_new = crystallinity_step(
        graph, state.phi, c_new, params, r=r, s=s, step=state.step, rng=rng, lap=lap
    )
    return CrystalState(c=c_new, phi=phi_new, step=state.step + 1)
