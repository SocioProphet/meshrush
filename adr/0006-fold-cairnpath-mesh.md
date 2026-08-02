# ADR 0006 — Fold CairnPath Mesh into MeshRush

**Status:** Proposed
**Date:** 2026-08-02
**Owner:** M. Heller
**Relates to:** ADR 0005 (Omni-Crystal fold-in), MR-01 (graph/reduction), the slot-filling IR layer (`crystal/retrieval.py`); `SocioProphet/cairnpath-mesh`

## Context

**CairnPath Mesh** is the normative bundle for **CairnPath** — a bounded-frontier
traversal framework for graph/hypergraph backends. Its central invariant is:

```
F[t+1] = TopK(Rank(Dedup(Expand(F[t]))))
```

and it defines: **EntityRef** (canonical `namespace:kind:key`, NFC-normalized —
the keystone identity that makes things *findable* and dedup/replay/conformance
possible), **CairnLimits** (policy caps: `max_hops`, `max_cap_k`, allowed opcodes,
materialization budgets — the *boundaries*), **Step / Line / Result / StepTrace /
frontier_digest** (the replayable, signable record — the *memorials and marks*),
and **Materialize** (metadata → properties → subgraph → packet, policy-governed,
minimum-necessary, *after* frontier narrowing).

Cairns are what make things easy to find, and they set the boundaries and
memorials we navigate by. That is not a metaphor here — it is the same job
MeshRush already needs done: the Omni layer expands and contracts a *frontier of
attention*, the slot-filling IR layer *ranks and caps* candidate artifacts, and
compiled artifacts carry *boundaries* and *provenance*. MeshRush has been building
cairns without the name.

## Decision

**Adopt CairnPath as MeshRush's canonical bounded-frontier traversal, identity,
materialization, and provenance-path model.** Fold the cairnpath-mesh contract in
(as ADR 0005 folded Omni-Crystal in), behind one vocabulary:

1. **Omni frontier ≡ the CairnPath invariant.** Omni diffusion/exploration is a
   `Dedup→Rank→Cap` bounded-frontier walk; a walk is a **CairnLine** of **CairnSteps**.
2. **Everything findable is addressed by an `EntityRef`.** Graph nodes, retrieval
   anchors, and compiled artifacts get canonical `namespace:kind:key` identities —
   the dedup/ordering/replay keystone, and the address the slot-filling IR fills against.
3. **Retrieval is a cairnpath walk.** The slot-filling IR (`crystal/retrieval.py`)
   expresses each fill as a bounded-frontier step (Expand candidate artifacts →
   Dedup by EntityRef → Rank by diffusion distance → Cap TopK → **Materialize** the
   winner), recorded as a replayable **StepTrace/Line**.
4. **Boundaries are `CairnLimits`.** `max_hops` / `max_cap_k` / materialization
   budgets bound every walk; a request that would exceed them **fails closed**
   (structured refusal), never silently truncates — the same discipline as
   BMG-1 and the IR epistemic floor.
5. **Materialization is minimum-necessary.** Traverse over EntityRefs + light
   metadata; fetch heavy payloads only after narrowing, under policy — matching the
   IR layer's retrieve-then-materialize split.

## Consequences

- MeshRush gains one findable-marker vocabulary spanning Omni (frontier), Crystal
  (artifact boundaries + materialization), and the IR layer (retrieval path).
- cairnpath-mesh remains the **normative schema home** (frame envelope, cairn
  schemas, conformance fixtures); MeshRush **consumes** those schemas and provides
  the runtime — exactly the split cairnpath-mesh's README declares ("not the full
  production runtime; runtime can live in AgentPlane or backend runners").
- Backend adapters (Neo4j/APOC, OpenCog AtomSpace) and the TriTRPC frame envelope
  are consumed, not reimplemented.

## Guardrails

- MIT/Apache only. cairnpath-mesh schemas are vendored/referenced, not forked-and-drifted.
- EntityRef `canonical` is **NFC-normalized before hashing/comparison** (identity.md) — non-negotiable for cross-backend conformance.
- Fail closed on CairnLimits breach; deterministic ranking (stable tie-break by `canonical`).
- Tests + CI green; no auto-merge before review.

## Work-order sequence (CP-00..)

| WO | Deliverable |
|---|---|
| **CP-00** | *(this ADR)* charter; adopt CairnPath as MeshRush's traversal/identity/materialization/provenance model |
| CP-01 | `core/cairn.py` — EntityRef (canonical NFC identity), CairnLimits, `bounded_frontier_step` (the invariant), CairnStep/CairnLine (replayable record) *(this PR)* |
| CP-02 | express `crystal/retrieval.py` slot-filling as a cairnpath walk (fills → CairnLine/StepTrace; artifacts addressed by EntityRef) |
| CP-03 | `Materialize` discipline over compiled artifacts (metadata→packet, CairnLimits-governed) |
| CP-04 | conformance: validate MeshRush cairn frames against cairnpath-mesh `schemas/cairn/*` + `envelope/frame.v0` |
| CP-05 | backend adapters (Neo4j/APOC, AtomSpace) consumed via the frame envelope |
