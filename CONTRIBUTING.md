# Contributing

MeshRush is specification-first.

Before adding runtime code, contributors should confirm whether the change touches:

- architecture (`adr/`)
- protocol or contracts (`specs/`)
- implementation (`src/`)
- validation (`experiments/`)
- publication-only wording (external platform docs)

## Contribution order

1. architectural decisions in `adr/`
2. canonical behavior in `specs/`
3. implementation in `src/`
4. validation in `experiments/`
5. publication in the platform docs repo

## Initial discipline

- no direct pushes to `main`
- no generated prose treated as canonical
- no implementation that silently changes an accepted spec
- no platform/UI concerns absorbed into MeshRush
