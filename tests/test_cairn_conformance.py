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
from meshrush.adapters.cairnpath.frame import cairnline_to_context, cairnline_to_frames

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


class CairnContextConformanceTests(unittest.TestCase):
    def setUp(self):
        self.schema = _load(VENDOR / "schemas/cairn/context.v0.jsonschema.json")
        self.validator = Draft202012Validator(self.schema)
        self.line = CairnLine("L1", "dataset@snap1", limits=CairnLimits(max_hops=4, max_cap_k=8))

    def _context(self, **over):
        kw = dict(seed_entities=["meshrush:artifact:a1", "meshrush:artifact:a2"],
                  created_at="2026-08-02T00:00:00Z")
        kw.update(over)
        return cairnline_to_context(self.line, **kw)

    def test_context_frame_conforms(self):
        ctx = self._context()
        errors = sorted(self.validator.iter_errors(ctx), key=lambda e: list(e.path))
        self.assertEqual(errors, [], f"context.v0 errors: {[e.message for e in errors]}")

    def test_context_carries_limits_and_frontier(self):
        ctx = self._context(engine="neo4j", allowed_namespaces=("meshrush",), privacy_mode="neighborhood")
        self.assertEqual(ctx["constraints"]["max_hops"], 4)
        self.assertEqual(ctx["frontier"]["cap_k"], 8)
        self.assertEqual(ctx["constraints"]["allowed_namespaces"], ["meshrush"])
        self.assertRegex(ctx["frontier"]["dedup_set_hash"], r"^[a-f0-9]{64}$")
        self.assertEqual(ctx["context_id"], "ctx:L1:0")  # matches line's root_context_id

    def test_context_root_id_matches_line_root(self):
        frames = cairnline_to_frames(self.line, created_at="2026-08-02T00:00:00Z")
        self.assertEqual(self._context()["context_id"], frames["line"]["root_context_id"])

    def test_dedup_hash_is_order_independent(self):
        a = self._context(seed_entities=["x", "y"])["frontier"]["dedup_set_hash"]
        b = self._context(seed_entities=["y", "x"])["frontier"]["dedup_set_hash"]
        self.assertEqual(a, b)

    def test_empty_seeds_and_bad_engine_fail_closed(self):
        with self.assertRaises(ValueError):
            self._context(seed_entities=[])
        with self.assertRaises(ValueError):
            self._context(engine="mongodb")


if __name__ == "__main__":
    unittest.main()
