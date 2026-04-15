import unittest

from meshrush import api


class PublicApiSmokeTests(unittest.TestCase):
    """Smoke tests verifying the public API surface of the meshrush.api module."""

    def test_api_exports_expected_symbols(self) -> None:
        expected = [
            "InMemoryMeshRushRuntime",
            "BasicOmniSession",
            "BasicCrystalCompiler",
            "GraphViewRef",
            "RuntimeContext",
            "RuntimeInput",
            "RuntimeCommand",
            "build_artifact_record",
            "artifact_record_to_json",
        ]

        for name in expected:
            with self.subTest(name=name):
                self.assertTrue(hasattr(api, name))
