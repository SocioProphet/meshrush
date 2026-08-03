"""Ledger-convergence conformance: meshrush's certificate_to_proof_pack emits the CANONICAL
estate ProofPack (prophet-core-contracts proof-pack.schema.json), validated against the vendored
hash-pinned schema. Also asserts vendor integrity (tamper-evidence).

Requires the ``conformance`` extra (``jsonschema``)."""
import hashlib
import json
import os
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from meshrush.crystal.certificate import (
    CompileMetrics,
    CompileThresholds,
    certificate_to_proof_pack,
    evaluate_certificate,
)

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "prophet-core-contracts"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


def _bounded_cert():
    m = CompileMetrics(mean_phi=0.9, mean_c=0.5, d_sym=1e-6, s_sharp=0.8, d_gb=0.1, t_persist=0.9, delta_h=1.0)
    return evaluate_certificate("artC", m, CompileThresholds(calibrated=True))


class VendorIntegrityTests(unittest.TestCase):
    def test_vendored_canonical_schemas_match_pinned_hashes(self):
        prov = _load(VENDOR / "PROVENANCE.json")
        self.assertEqual(prov["license"], "MIT")
        root = VENDOR.resolve()
        for entry in prov["files"]:
            rel = entry["path"]
            self.assertNotIn("..", Path(rel).parts, f"path traversal in provenance: {rel!r}")
            target = (root / rel).resolve()
            self.assertTrue(str(target).startswith(str(root) + os.sep), f"escapes vendor dir: {rel!r}")
            actual = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertEqual(actual, entry["sha256"], f"{rel} drifted from its pinned hash")


class ProofPackConformanceTests(unittest.TestCase):
    def setUp(self):
        self.schema = _load(VENDOR / "schemas/proof-pack.schema.json")
        self.validator = Draft202012Validator(self.schema)

    def _pack(self, **over):
        cert = over.pop("cert", _bounded_cert())
        kw = dict(included_node_ids=("n0", "n1"), graph_view_id="gv1",
                  signatures=["did:key:z6MkExample"], created_at="2026-08-03T00:00:00Z")
        kw.update(over)
        return certificate_to_proof_pack(cert, **kw)

    def test_emitted_pack_conforms_to_canonical_schema(self):
        pack = self._pack()
        errors = sorted(self.validator.iter_errors(pack), key=lambda e: list(e.path))
        self.assertEqual(errors, [], f"proof-pack schema errors: {[e.message for e in errors]}")

    def test_pack_carries_epistemic_gates_and_ledger_head(self):
        pack = self._pack()
        self.assertEqual(pack["epistemic_level"], "bounded")
        self.assertEqual(pack["claim_mode"], "formal_construction")
        self.assertEqual(pack["ledger"]["algo"], "blake2b")
        self.assertRegex(pack["ledger"]["head"], r"^[a-f0-9]{16,128}$")
        self.assertEqual(len(pack["checks"]), 7)  # the 7 compile-gate checks
        self.assertTrue(pack["proof_pack_id"].startswith("proofpack_"))

    def test_unsigned_pack_is_unrepresentable(self):
        with self.assertRaises(ValueError):
            self._pack(signatures=[])

    def test_synthetic_certificate_carries_through(self):
        m = CompileMetrics(mean_phi=0.9, mean_c=0.5, d_sym=0.1, s_sharp=0.8, d_gb=0.1, t_persist=0.9, delta_h=1.0)
        cert = evaluate_certificate("artD", m, CompileThresholds(calibrated=True))  # symmetry fails -> synthetic
        pack = self._pack(cert=cert)
        self.assertEqual(pack["epistemic_level"], "synthetic")
        self.assertEqual(list(self.validator.iter_errors(pack)), [])


if __name__ == "__main__":
    unittest.main()
