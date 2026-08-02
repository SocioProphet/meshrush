"""CP-04 conformance gate: MeshRush cairn frames MUST validate against the vendored
normative cairnpath-mesh schemas, and the vendored schemas MUST match their pinned
provenance hashes (supply-chain tamper-evidence).

Requires the ``conformance`` extra (``jsonschema``)."""
import hashlib
import json
import os
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from meshrush.core.cairn import CairnLimits, CairnLine, EntityRef
from meshrush.adapters.cairnpath.frame import cairnline_to_frames

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "cairnpath-mesh"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


class VendorIntegrityTests(unittest.TestCase):
    def test_vendored_schemas_match_pinned_hashes(self):
        prov = _load(VENDOR / "PROVENANCE.json")
        self.assertEqual(prov["license"], "MIT")
        self.assertTrue(prov["files"], "provenance must pin at least one file")
        vendor_root = VENDOR.resolve()
        for entry in prov["files"]:
            rel = entry["path"]
            # Fail closed on path traversal: a tampered PROVENANCE.json must not make
            # CI read files outside the vendor directory.
            self.assertFalse(Path(rel).is_absolute(), f"provenance path must be relative: {rel!r}")
            self.assertNotIn("..", Path(rel).parts, f"provenance path must not contain '..': {rel!r}")
            target = (vendor_root / rel).resolve()
            self.assertTrue(
                str(target).startswith(str(vendor_root) + os.sep),
                f"provenance path escapes vendor dir: {rel!r}",
            )
            blob = target.read_bytes()
            actual = hashlib.sha256(blob).hexdigest()
            self.assertEqual(
                actual, entry["sha256"],
                f"{entry['path']} drifted from its pinned provenance hash",
            )


class CairnFrameConformanceTests(unittest.TestCase):
    def setUp(self):
        self.step_schema = _load(VENDOR / "schemas/cairn/step.v0.jsonschema.json")
        self.line_schema = _load(VENDOR / "schemas/cairn/line.v0.jsonschema.json")
        self.step_validator = Draft202012Validator(self.step_schema)
        self.line_validator = Draft202012Validator(self.line_schema)

        line = CairnLine("L1", "dataset@snap1", limits=CairnLimits(max_hops=4, max_cap_k=8))
        line.record_step("retrieve", [EntityRef("meshrush", "artifact", "a1")], cap_k=2, materialized=True)
        line.record_step("retrieve", [], cap_k=2)  # refused / empty frontier
        self.frames = cairnline_to_frames(line, created_at="2026-08-02T00:00:00Z")

    def test_line_frame_conforms(self):
        errors = sorted(self.line_validator.iter_errors(self.frames["line"]), key=lambda e: list(e.path))
        self.assertEqual(errors, [], f"line.v0 errors: {[e.message for e in errors]}")

    def test_every_step_frame_conforms(self):
        for step in self.frames["steps"]:
            errors = sorted(self.step_validator.iter_errors(step), key=lambda e: list(e.path))
            self.assertEqual(errors, [], f"step {step['opcode']} errors: {[e.message for e in errors]}")

    def test_retrieve_maps_to_cap_then_materialize(self):
        opcodes = [s["opcode"] for s in self.frames["steps"]]
        # first retrieve (materialized) -> cap + materialize; second (empty) -> cap only
        self.assertEqual(opcodes, ["cap", "materialize", "cap"])
        mat = self.frames["steps"][1]
        self.assertEqual(mat["args"]["mode"], "metadata_only")
        self.assertEqual(mat["args"]["targets"], ["meshrush:artifact:a1"])

    def test_line_references_all_step_ids(self):
        self.assertEqual(self.frames["line"]["steps"], [s["step_id"] for s in self.frames["steps"]])

    def test_unmapped_opcode_fails_closed(self):
        # An opcode with no normative arg-mapping must refuse, not emit an invalid frame.
        line = CairnLine("L2", "d", limits=CairnLimits(max_hops=2, max_cap_k=4))
        line.record_step("filter", [EntityRef("meshrush", "artifact", "a1")], cap_k=1, materialized=True)
        with self.assertRaises(ValueError):
            cairnline_to_frames(line, created_at="2026-08-02T00:00:00Z")


if __name__ == "__main__":
    unittest.main()
