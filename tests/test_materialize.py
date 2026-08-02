import unittest

from meshrush.core.cairn import EntityRef
from meshrush.crystal.materialize import (
    MaterializeMode,
    MaterializePolicy,
    MaterializeRequest,
    materialize,
)


def _ref(key, ns="meshrush"):
    return EntityRef(namespace=ns, kind="artifact", key=key)


def _fetcher_factory(record):
    def fetch(target, mode, projection):
        record.append((target.canonical, mode, tuple(projection)))
        if mode is MaterializeMode.PROPERTIES and projection:
            return {f: f"{target.key}:{f}" for f in projection}
        return {"id": target.canonical, "blob": "x" * 20}
    return fetch


class MaterializeTests(unittest.TestCase):
    def test_metadata_only_within_budget_is_granted(self):
        req = MaterializeRequest(targets=(_ref("a"), _ref("b")), mode=MaterializeMode.METADATA_ONLY)
        res = materialize(req, MaterializePolicy(max_bytes=10_000), _fetcher_factory([]))
        self.assertTrue(res.fully_granted)
        self.assertEqual(set(res.granted), {"meshrush:artifact:a", "meshrush:artifact:b"})
        self.assertGreater(res.total_bytes, 0)

    def test_budget_exceeded_refuses_breaching_target_not_drops(self):
        # Tight budget: first target fits, second is refused (withheld, not dropped).
        # Each payload is ~58B; budget 80 fits the first, refuses the second.
        req = MaterializeRequest(targets=(_ref("a"), _ref("b")), mode=MaterializeMode.METADATA_ONLY)
        res = materialize(req, MaterializePolicy(max_bytes=80), _fetcher_factory([]))
        self.assertIn("meshrush:artifact:a", res.granted)
        self.assertFalse(res.fully_granted)
        self.assertEqual(res.refused[0][0], "meshrush:artifact:b")
        self.assertIn("budget", res.refused[0][1])

    def test_namespace_allow_list_fails_closed(self):
        req = MaterializeRequest(targets=(_ref("a", ns="external"),), mode=MaterializeMode.METADATA_ONLY)
        res = materialize(req, MaterializePolicy(allowed_namespaces=("meshrush",)), _fetcher_factory([]))
        self.assertFalse(res.fully_granted)
        self.assertIn("allow-list", res.refused[0][1])

    def test_disallowed_mode_refuses_everything(self):
        req = MaterializeRequest(targets=(_ref("a"),), mode=MaterializeMode.PACKET)
        policy = MaterializePolicy(allowed_modes=(MaterializeMode.METADATA_ONLY,))
        res = materialize(req, policy, _fetcher_factory([]))
        self.assertEqual(res.granted, {})
        self.assertIn("not permitted", res.refused[0][1])

    def test_minimum_necessary_projection_passed_to_fetcher(self):
        calls = []
        req = MaterializeRequest(
            targets=(_ref("a"),), mode=MaterializeMode.PROPERTIES, projection=("name", "score"),
        )
        res = materialize(req, MaterializePolicy(max_bytes=10_000), _fetcher_factory(calls))
        self.assertEqual(calls[0][2], ("name", "score"))       # fetcher got only declared fields
        self.assertEqual(set(res.granted["meshrush:artifact:a"]), {"name", "score"})

    def test_redactor_applied_and_recorded(self):
        def redactor(target, payload):
            payload = dict(payload)
            redactions = []
            if "blob" in payload:
                payload["blob"] = "[REDACTED]"
                redactions.append(f"{target.canonical}:blob")
            return payload, redactions
        req = MaterializeRequest(targets=(_ref("a"),), mode=MaterializeMode.METADATA_ONLY)
        res = materialize(req, MaterializePolicy(max_bytes=10_000), _fetcher_factory([]), redactor=redactor)
        self.assertEqual(res.granted["meshrush:artifact:a"]["blob"], "[REDACTED]")
        self.assertIn("meshrush:artifact:a:blob", res.redactions)

    def test_invalid_policy_raises(self):
        with self.assertRaises(ValueError):
            MaterializePolicy(max_bytes=-1)


if __name__ == "__main__":
    unittest.main()
