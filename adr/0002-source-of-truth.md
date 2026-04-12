# ADR 0002: Source of Truth

- Status: Accepted (design baseline)
- Date: 2026-03-31
- Owner: SocioProphet / MeshRush

## Decision

MeshRush adopts the following source-of-truth order:

1. `adr/` — architectural decisions
2. `specs/` — canonical protocol/runtime specifications
3. `src/` — executable reference implementation
4. `experiments/` — reproducible validation
5. published platform docs — reader-facing explanatory material

`specs/` is canonical.

## Authoring order

1. decide in ADR
2. codify in spec
3. implement in source
4. validate in experiments
5. publish in platform docs

## Publication rule

If platform documentation diverges from MeshRush specifications, the MeshRush specifications win until the publication layer is updated.
