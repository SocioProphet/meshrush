import importlib
import unittest


MODULES = [
    "meshrush.core.contracts",
    "meshrush.core.runtime",
    "meshrush.core.in_memory_runtime",
    "meshrush.omni.session",
    "meshrush.omni.basic_session",
    "meshrush.crystal.compile",
    "meshrush.crystal.basic_compiler",
    "meshrush.crystal.serialization",
    "meshrush.cli",
]


class ImportSmokeTests(unittest.TestCase):
    def test_modules_import(self) -> None:
        for module_name in MODULES:
            with self.subTest(module=module_name):
                module = importlib.import_module(module_name)
                self.assertIsNotNone(module)
