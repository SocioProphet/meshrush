import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from meshrush.cli import main


class CliSmokeTests(unittest.TestCase):
    def test_demo_run_with_artifact_output_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            artifact_path = Path(tmpdir) / "artifact.json"
            buffer = io.StringIO()

            with redirect_stdout(buffer):
                exit_code = main([
                    "demo-run",
                    "--artifact-out",
                    str(artifact_path),
                ])

            self.assertEqual(exit_code, 0)
            self.assertTrue(artifact_path.exists())

            payload = json.loads(buffer.getvalue())
            self.assertEqual(payload["kind"], "meshrush.demo_run")

            artifact_record = json.loads(artifact_path.read_text(encoding="utf-8"))
            self.assertEqual(artifact_record["kind"], "meshrush.artifact_record")
