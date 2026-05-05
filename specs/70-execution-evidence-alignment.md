# Execution Evidence Alignment

## Purpose

This specification aligns MeshRush runtime outputs with the active execution, policy, and workspace-fingerprint seams emerging across the SocioProphet ecosystem.

It is a hardening bridge between MeshRush and adjacent work in:

- agentplane Agentic PR Work Orders
- agentplane Policy Fabric verdict envelopes
- Sociosphere / Lattice environment fingerprints

MeshRush should not absorb those systems. It should emit enough structured context that those systems can govern, replay, evaluate, fingerprint, and learn from MeshRush runtime activity.

## Context

Recent upstream movement introduced or refined adjacent seams that matter to MeshRush:

- Agentic PR Work Orders define structured agentic work with separation of duties, denied paths, required validation, linked issues, and policy evidence.
- Policy Fabric verdict envelopes define execution-admission verdict surfaces and schema-index discoverability.
- Lattice environment fingerprints define system, user, agent, release-set, artifact, policy, tenant/workspace, and rollback fingerprints with provenance bindings and receipt links.

MeshRush runtime traces and artifacts should be able to reference those seams without duplicating their schemas.

## Decision

MeshRush runtime outputs should expose references, not copies, for adjacent governance objects.

At minimum, MeshRush runtime evidence should be able to carry:

- work-order reference
- policy-verdict reference
- environment-fingerprint reference
- workspace or tenant fingerprint reference
- artifact fingerprint reference
- runtime trace reference
- compile certificate reference
- run or replay reference

These should be expressed as optional metadata surfaces in runtime, adapter, and artifact records before they become hard requirements.

## Non-goals

MeshRush does not own:

- Agentic PR Work Order schema
- Policy Fabric verdict-envelope schema
- Lattice environment-fingerprint registry
- workspace or release-set fingerprint calculation
- merge-gate approval policy
- separation-of-duties enforcement

Those remain owned by adjacent systems.

## Alignment surfaces

### Agentic PR Work Order

MeshRush should preserve references to work orders when a MeshRush runtime session is initiated as part of bounded agentic implementation, review, or validation work.

Relevant metadata:

- work order id
- linked issue or PR
- implementation actor
- review actor
- merge-gate actor
- expected files
- denied paths
- validation commands
- policy evidence refs

MeshRush should treat this metadata as governance context, not as runtime logic.

### Policy Fabric verdict envelope

MeshRush should preserve references to execution-admission and policy verdicts when a run is admitted, denied, replayed, or promoted through agentplane.

Relevant metadata:

- verdict id
- policy pack reference
- decision status
- denial reasons if any
- risk score or risk band if exposed
- evidence bundle refs

MeshRush should not compute the verdict unless explicitly acting through a Policy Fabric adapter.

### Environment fingerprints

MeshRush should preserve references to environment and workspace fingerprints when a runtime session depends on workspace state, release state, artifact state, or rollback eligibility.

Relevant metadata:

- system fingerprint id
- user fingerprint id
- agent fingerprint id
- release-set fingerprint id
- artifact fingerprint id
- policy fingerprint id
- tenant/workspace fingerprint id
- rollback fingerprint id

These references allow MeshRush traces and compiled artifacts to remain attributable to the operational environment that produced them.

## Runtime metadata guidance

The following conceptual shape should be supported in metadata fields until formal schemas exist:

```json
{
  "work_order_ref": "work-order://example",
  "policy_verdict_ref": "policy-verdict://example",
  "environment_fingerprint_ref": "fingerprint://environment/example",
  "workspace_fingerprint_ref": "fingerprint://workspace/example",
  "artifact_fingerprint_refs": ["fingerprint://artifact/example"],
  "replay_ref": "run://example/replay/1"
}
```

This is not a final wire schema. It is an alignment target for current adapter hardening.

## Adapter implications

### agentplane adapter

The agentplane adapter should carry work-order and policy-verdict references in run context and outcome summaries.

### Sociosphere adapter

The Sociosphere adapter should carry workspace, tenant, environment, and artifact fingerprint references in workspace context and state hints.

### Alexandrian Academy adapter

The Academy adapter should preserve these references when exporting episodes, because learning and transfer records must remain tied to the operational evidence that produced them.

## Artifact implications

Compiled artifacts should preserve environment and policy context as provenance, especially when artifacts are candidates for transfer across workspaces.

A compiled artifact should be able to answer:

- which workspace context produced it
- which run or work order produced it
- which policy verdict admitted or denied relevant work
- which environment or release fingerprint was active
- which evidence bundle supports it

## Deferred formalization

Deferred to future PRs:

- concrete metadata field additions to runtime contracts
- JSON Schema for MeshRush runtime evidence records
- compatibility tests against agentplane work-order fixtures
- compatibility tests against Policy Fabric verdict-envelope fixtures
- compatibility tests against Sociosphere/Lattice fingerprint registry entries

## Consequences

### Positive

- MeshRush remains aligned with fast-moving adjacent governance work.
- Runtime traces become more useful for replay, audit, learning, and transfer.
- MeshRush avoids duplicating schemas owned by agentplane, policy-fabric, or Sociosphere.

### Tradeoffs

- Adapter metadata becomes more important.
- Version coordination across repos remains necessary.
- Early metadata references may be stringly typed until formal schemas stabilize.
