# ADR 0004: Publication Contract

- Status: Accepted (design baseline)
- Date: 2026-03-31
- Owner: SocioProphet / MeshRush

## Decision

We adopt a dual-home model.

### Canonical home

`SocioProphet/meshrush` is the canonical source of truth for:

- ADRs
- protocol/specification text
- reference runtime code
- experiments
- issues
- releases

### Publication home

`SocioProphet/socioprophet` is the official public publication surface for MeshRush documentation.

The intended publication target is a platform docs path such as:

`docs/protocols/meshrush/`

## Publication workflow

Initial workflow is manual and review-driven.

1. author or update canonical content in `meshrush/specs/`
2. review and merge in the MeshRush repo
3. port stable reader-facing content into the platform docs tree
4. review and merge in the platform docs repo
5. publish through the existing platform docs pipeline
