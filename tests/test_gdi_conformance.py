"""GDI-1 conformance gate: MeshRush-emitted signals MUST validate against the
vendored GDI AI4IT event-envelope, and the vendored schema MUST match its pinned
provenance (tamper-evidence). Requires the ``conformance`` extra (``jsonschema``)."""
import hashlib
import json
import os
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from meshrush.core.cairn import CairnLimits, CairnLine, EntityRef
from meshrush.crystal.retrieval import EpistemicLevel, Fill, RefusedSlot, SlotFillResult
from meshrush.adapters.gdi.contracts import (
    cairnline_to_event,
    make_event,
    now_event_fields,
    slot_fill_to_event,
)

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / "vendor" / "global-devsecops-intelligence"
TS = 1_754_100_000_000
UTC = "2026-08-02T00:00:00.000Z"


def _load(p: Path) -> dict:
    return json.loads(p.read_text(encoding="utf-8"))


class VendorIntegrityTests(unittest.TestCase):
    def test_vendored_schema_matches_pinned_hash(self):
        prov = _load(VENDOR / "PROVENANCE.json")
        self.assertEqual(prov["license"], "MIT")
        vendor_root = VENDOR.resolve()
        for entry in prov["files"]:
            rel = entry["path"]
            self.assertFalse(Path(rel).is_absolute())
            self.assertNotIn("..", Path(rel).parts)
            target = (vendor_root / rel).resolve()
            self.assertTrue(str(target).startswith(str(vendor_root) + os.sep))
            self.assertEqual(hashlib.sha256(target.read_bytes()).hexdigest(), entry["sha256"])


class EventConformanceTests(unittest.TestCase):
    def setUp(self):
        self.validator = Draft202012Validator(_load(VENDOR / "schemas/event-envelope.schema.json"))

    def _assert_conforms(self, event):
        errors = sorted(self.validator.iter_errors(event), key=lambda e: list(e.path))
        self.assertEqual(errors, [], f"event errors: {[e.message for e in errors]}")

    def test_cairnpath_walk_event_conforms(self):
        line = CairnLine("L1", "dataset@snap", limits=CairnLimits(max_hops=3, max_cap_k=8))
        line.record_step("retrieve", [EntityRef("meshrush", "artifact", "a1")], cap_k=2, materialized=True)
        ev = cairnline_to_event(line, timestamp_ms=TS, utc_timestamp=UTC, story_id="s1")
        self._assert_conforms(ev)
        self.assertEqual(ev["type"], "meshrush_cairnpath_walk")
        self.assertEqual(ev["data"]["n_steps"], 1)

    def test_slot_fill_event_carries_epistemic_and_refusals(self):
        result = SlotFillResult(
            fills={"a": Fill("a", "artA", 0.1, 0.9, EpistemicLevel.BOUNDED, ("n0",), ("cert-A",), "meshrush:artifact:artA")},
            refused=[RefusedSlot("b", "no artifact meets floor", EpistemicLevel.SYNTHETIC)],
        )
        ev = slot_fill_to_event(result, timestamp_ms=TS, utc_timestamp=UTC)
        self._assert_conforms(ev)
        self.assertEqual(ev["type"], "meshrush_slot_fill")
        self.assertEqual(ev["data"]["n_filled"], 1)
        self.assertEqual(ev["data"]["n_refused"], 1)
        self.assertEqual(ev["data"]["fills"][0]["epistemic"], "bounded")
        self.assertEqual(ev["data"]["refused"][0]["best_available_epistemic"], "synthetic")

    def test_make_event_rejects_bad_type(self):
        with self.assertRaises(ValueError):
            make_event("MeshRush-Walk", {}, timestamp_ms=TS, utc_timestamp=UTC)  # not snake_case

    def test_now_event_fields_shape(self):
        ms, utc = now_event_fields()
        self.assertIsInstance(ms, int)
        self.assertTrue(utc.endswith("Z"))
        ev = make_event("meshrush_probe", {"ok": True}, timestamp_ms=ms, utc_timestamp=utc)
        self._assert_conforms(ev)


if __name__ == "__main__":
    unittest.main()
