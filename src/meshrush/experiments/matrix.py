"""MR-07 — the experiment matrix (ADR 0005).

A declarative, runnable matrix of experiments over the MeshRush scientific engine,
organised by the three families the ADR names:

  * **structural** — the graph is given by an explicit structure (ring, path, grid,
    complete); we test what the engine recovers from known topology.
  * **observation-first** — the graph is *built from observations* (points → kNN),
    the default framing of the engine.
  * **dynamical** — a phase-field field is evolved on a graph and its behaviour is
    checked.

Each ``ExperimentSpec`` declares a generator + params + the invariants it must
satisfy; ``run_experiment`` builds the graph, runs the real MR-01/04b pipeline
(diffusion reduction, symmetry discovery, connectivity), and returns a report.

**The 129-vs-141 count correction.** An earlier enumeration of the design space
counted 141 experiments by treating every observation-first case as distinct. But
the ADR's decision makes agent-navigation "the special case where the observation
step is a no-op over a supplied graph" — so an observation-first experiment whose
observation step is a no-op is *identical* to the corresponding structural
experiment and must not be double-counted. Removing those 12 no-op duplicates gives
the corrected canonical count of 129. ``count_reconciliation()`` records this, and
``observe`` operationalises the no-op equivalence that justifies it.

Requires the ``scientific`` extra (``numpy``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from meshrush.core.graph_build import WeightedGraph, build_knn_graph, is_connected
from meshrush.crystal.dynamics import CrystalState, DynamicsParams, advance
from meshrush.crystal.symmetry_discovery import discover_automorphisms
from meshrush.omni.reduction import diffusion_coordinates


class ExperimentFamily(str, Enum):
    STRUCTURAL = "structural"
    OBSERVATION_FIRST = "observation_first"
    DYNAMICAL = "dynamical"


# --- the 129-vs-141 count correction -----------------------------------------

RAW_EXPERIMENT_COUNT = 141
OBSERVATION_NOOP_DUPLICATES = 12
CANONICAL_EXPERIMENT_COUNT = 129


@dataclass(frozen=True)
class CountReconciliation:
    raw_count: int
    deduplicated: int
    corrected_count: int
    reason: str


def count_reconciliation() -> CountReconciliation:
    """The audited 141 → 129 correction (see module docstring)."""
    return CountReconciliation(
        raw_count=RAW_EXPERIMENT_COUNT,
        deduplicated=OBSERVATION_NOOP_DUPLICATES,
        corrected_count=CANONICAL_EXPERIMENT_COUNT,
        reason=(
            "observation-first experiments whose observation step is a no-op over a "
            "supplied graph are identical to the corresponding structural experiment "
            "(ADR 0005: agent-navigation is the no-op special case) and are not "
            "double-counted"
        ),
    )


# --- graph generators --------------------------------------------------------

def _wg_from_adjacency(w: np.ndarray) -> WeightedGraph:
    n = w.shape[0]
    return WeightedGraph(
        node_ids=tuple(f"n{i}" for i in range(n)), weights=w, degrees=w.sum(axis=1)
    )


def ring_graph(n: int) -> WeightedGraph:
    if n < 3:
        raise ValueError("ring requires n >= 3")
    w = np.zeros((n, n))
    for i in range(n):
        j = (i + 1) % n
        w[i, j] = w[j, i] = 1.0
    return _wg_from_adjacency(w)


def path_graph(n: int) -> WeightedGraph:
    if n < 2:
        raise ValueError("path requires n >= 2")
    w = np.zeros((n, n))
    for i in range(n - 1):
        w[i, i + 1] = w[i + 1, i] = 1.0
    return _wg_from_adjacency(w)


def complete_graph(n: int) -> WeightedGraph:
    if n < 2:
        raise ValueError("complete requires n >= 2")
    w = np.ones((n, n)) - np.eye(n)
    return _wg_from_adjacency(w)


def gaussian_blob_points(n: int, seed: int) -> np.ndarray:
    """A single Gaussian cloud of ``n`` 2-D points (a kNN graph over it is connected)."""
    if n < 2:
        raise ValueError("need n >= 2 points")
    return np.random.default_rng(seed).normal(0.0, 1.0, size=(n, 2))


_GENERATORS = {
    "ring": lambda p: ring_graph(int(p["n"])),
    "path": lambda p: path_graph(int(p["n"])),
    "complete": lambda p: complete_graph(int(p["n"])),
}


def observe(source, *, noop: bool) -> WeightedGraph:
    """The observation step. When ``noop`` (agent-navigation special case) a supplied
    graph is returned unchanged; otherwise a graph is built from observed points.

    This is the operational root of the count correction: a no-op observation over a
    structural graph yields *that same graph*, so the observation-first experiment is
    not a distinct experiment from its structural twin.
    """
    if noop:
        if not isinstance(source, WeightedGraph):
            raise ValueError("no-op observation requires a supplied WeightedGraph")
        return source
    points = np.asarray(source, dtype=float)
    return build_knn_graph(points)


# --- experiment specs + runner -----------------------------------------------

@dataclass(frozen=True)
class ExperimentSpec:
    id: str
    family: ExperimentFamily
    generator: str                 # key in _GENERATORS, or "observation" / "dynamical"
    params: dict = field(default_factory=dict)
    invariants: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class ExperimentReport:
    spec_id: str
    family: ExperimentFamily
    passed: bool
    observations: dict
    failures: tuple[str, ...]


def _build_graph(spec: ExperimentSpec) -> WeightedGraph:
    if spec.generator in _GENERATORS:
        return _GENERATORS[spec.generator](spec.params)
    if spec.generator == "observation":
        pts = gaussian_blob_points(
            int(spec.params.get("n", 40)), int(spec.params.get("seed", 0))
        )
        return observe(pts, noop=False)
    if spec.generator == "dynamical":
        return ring_graph(int(spec.params.get("n", 10)))
    raise ValueError(f"unknown generator: {spec.generator}")


def _check_invariant(name: str, graph: WeightedGraph, obs: dict) -> bool:
    if name == "connected":
        return is_connected(graph)
    if name == "diffusion_nontrivial":
        dmap = diffusion_coordinates(graph, n_coords=min(3, graph.n - 1))
        spread = float(np.abs(dmap.coordinates).max()) if dmap.coordinates.size else 0.0
        obs["diffusion_spread"] = spread
        return dmap.coordinates.shape[1] >= 1 and spread > 0.0
    if name == "has_symmetry":
        order = discover_automorphisms(graph).order
        obs["automorphism_order"] = order
        return order > 1
    if name == "rigid":
        order = discover_automorphisms(graph).order
        obs["automorphism_order"] = order
        return order == 1
    if name == "dynamics_evolves":
        rng = np.random.default_rng(0)
        state = CrystalState(c=rng.uniform(-0.5, 0.5, graph.n), phi=0.5 * np.ones(graph.n))
        c0 = state.c.copy()
        for _ in range(5):
            state = advance(graph, state, DynamicsParams())
        moved = float(np.abs(state.c - c0).max())
        finite = bool(np.all(np.isfinite(state.c)) and np.all(np.isfinite(state.phi)))
        obs["dynamics_delta"] = moved
        return finite and moved > 0.0
    raise ValueError(f"unknown invariant: {name}")


def run_experiment(spec: ExperimentSpec) -> ExperimentReport:
    """Build the graph for ``spec`` and evaluate every declared invariant."""
    graph = _build_graph(spec)
    obs: dict = {"n_nodes": graph.n}
    failures = tuple(
        name for name in spec.invariants if not _check_invariant(name, graph, obs)
    )
    return ExperimentReport(
        spec_id=spec.id,
        family=spec.family,
        passed=not failures,
        observations=obs,
        failures=failures,
    )


def representative_suite() -> tuple[ExperimentSpec, ...]:
    """The executable representative experiments shipped with the engine.

    This is the runnable subset, distinct from ``CANONICAL_EXPERIMENT_COUNT`` (the
    reconciled size of the full design space).
    """
    return (
        ExperimentSpec("struct-ring-8", ExperimentFamily.STRUCTURAL, "ring", {"n": 8},
                       ("connected", "diffusion_nontrivial", "has_symmetry"),
                       "cycle graph is vertex-transitive (dihedral symmetry)"),
        ExperimentSpec("struct-path-6", ExperimentFamily.STRUCTURAL, "path", {"n": 6},
                       ("connected", "diffusion_nontrivial", "has_symmetry"),
                       "path has a single reflection symmetry"),
        ExperimentSpec("struct-complete-5", ExperimentFamily.STRUCTURAL, "complete", {"n": 5},
                       ("connected", "has_symmetry"),
                       "complete graph is fully symmetric"),
        ExperimentSpec("obs-gaussian-40", ExperimentFamily.OBSERVATION_FIRST, "observation",
                       {"n": 40, "seed": 0},
                       ("connected", "diffusion_nontrivial"),
                       "graph built from a single observed point cloud (kNN)"),
        ExperimentSpec("dyn-ring-10", ExperimentFamily.DYNAMICAL, "dynamical", {"n": 10},
                       ("dynamics_evolves",),
                       "phase-field dynamics evolve and stay finite on a ring"),
    )
