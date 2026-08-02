# ADR 0005 — Fold the Omni-Crystal scientific engine into MeshRush

**Status:** Proposed
**Date:** 2026-08-02
**Owner:** M. Heller
**Relates to:** SP-ARCH-000 (master reconciliation, decision D-G), specs 10 (omni-diffusion), 20 (crystal-compile); `sp-orchestrator` (execution algebra, merged)

## Context

Two systems share the "MeshRush / Omni / Crystal" vocabulary:

1. **This repo (as built):** an agent-navigation protocol — "graph-native agents traverse graph views derived from a pre-existing hypergraph world model." Omni/Crystal exist as abstract contracts (`OmniSession`, `CrystalCompiler`) with `Basic*` reference stubs that self-describe as *"not the full scientific compile engine."*

2. **The Omni-Crystal scientific spec:** an **observation-first** system — build the graph *from* trajectories (kNN + diffusion maps), harden candidate regions via graph phase-field dynamics (support-density Cahn–Hilliard-like + band term, crystallinity Allen–Cahn, optional MBO), compress with VQ + information bottleneck, discover symmetries via a cascade (typed prepartition → ε-role → nauty/Traces quotient → egonet → probe-equivariance), and emit a bounded artifact only when a 6-gate **compile certificate** passes.

The scientific engine is **not built anywhere in the estate** (verified 2026-08-02 via estate-wide code search over implementation paths — `src/`, `tests/`, `tools/`, excluding docs/ADRs: `Cahn`/`asymmetric-unit`/`band-selection`/`information-bottleneck`/`nauty` = 0 hits). The `Basic*` stubs were authored anticipating it.

## Decision

**Fold the scientific engine into this repo, behind the existing contracts, and run it on `sp-orchestrator`.**

1. **One repo, unified framing.** The scientific engine becomes the reference implementation of `OmniSession` / `CrystalCompiler`, replacing the `Basic*` stubs as the default. Framing is unified around **observation-first**: the graph is *built from observation* by default; the agent-navigation case (graph view supplied by a pre-existing world model) becomes the special case where the observation step is a no-op over a supplied graph.

2. **Run on the governed execution algebra.** The MeshRush runtime loop is expressed as `sp-orchestrator` Transforms/DAGs. Concretely:
   - the 6-gate **compile certificate → an sp-orchestrator attestation** (ProofArtifact);
   - a compiled **artifact `A_S` → a durable content-addressed cell** with lineage/provenance;
   - artifact **epistemicLevel via `meet`** (a symmetry-certified, gate-passing artifact is at most `bounded`; a diffuse candidate is `synthetic`);
   - the observe→compile loop is a **bounded ExpansionPoint** (declared admissible shapes, depth/breadth/budget), never an unbounded agent-authored edge.

3. **MeshRush governs adjacent runtimes via a conductor.** MeshRush extends governance over the Noetica **`agent-machine`** (its "governed execution receipts" become MeshRush cells/artifacts) and the **`prophet-mesh`** reasoning choir (reasoning traces become observations; compiled artifacts seed retrieval). A **conductor agent** (the human operator, M. Heller) declares manifests and gates *entrances and dynamics, not notes* — it cannot author a claim outside a published manifest.

## Consequences

- The `Basic*` stubs are retained as a deterministic reference/fallback and for contract tests, but are no longer the shipped default. This is documented, not deleted.
- MeshRush becomes a **consumer** of `sp-orchestrator`, not a parallel execution engine. No second provenance algebra.
- This is the "compile" instantiation of the estate's single canonical control loop (SP-ARCH-000): `observe → diffuse → residual/probe → gate(certificate) → attest`.

## Guardrails (non-negotiable at build time)

- **License:** MIT/Apache only. **nauty/Traces is Apache-2.0 since 2.6 — verify the exact vendored version before wiring the symmetry cascade (MR-04).**
- Vendor dependencies (tarball + hash), never reference an external CDN.
- Tests + lint + `gate/check` green before merge; do not auto-merge before review posts.

## Work-order sequence (MR-00..08)

| WO | Deliverable |
|---|---|
| **MR-00** | *(this ADR)* reconciliation + charter; declare `sp-orchestrator` dependency; deprecate `Basic*` as default |
| MR-01 | `core/graph_build` + `omni/reduction` — `W,D,L,P`; diffusion coordinates |
| MR-02 | `crystal/dynamics` — support-density `c` (Cahn–Hilliard-like + band term), crystallinity `φ` (Allen–Cahn), optional MBO |
| MR-03 | `omni/probes` — impulse / spectral-band / seed-persistence / symmetry |
| MR-04 | `crystal/symmetry` — cascade + defect functionals + empirical null *(nauty license gate)* |
| MR-05 | compression — VQ codebook + IB relevance |
| MR-06 | `crystal/compile` + 6-gate certificate; the `sp-orchestrator` seam (certificate→attestation, artifact→cell, epi mapping) |
| MR-07 | experiment matrix (structural / dynamical / observation-first; encode the 129-vs-141 count correction) |
| MR-08 | governance seam — loop as DAG + ExpansionPoints; govern `agent-machine` receipts + `prophet-mesh`; conductor manifest |

Each WO: tests + checks green, one weakest-link-at-a-time, report blocked rather than partial.
