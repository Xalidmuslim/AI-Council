"""Fail-closed contract for pinned Flutter pilot CI (offline only)."""
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "three-role-pilot.yml"


class PinnedFlutterPilotWorkflowTests(unittest.TestCase):
    def test_analysis_preserves_warnings_but_does_not_fail_on_info(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("flutter analyze --no-fatal-infos", workflow)
        self.assertNotIn("--no-fatal-warnings", workflow)
        self.assertIn("flutter test", workflow)

    def test_flutter_version_is_reproducibly_pinned(self):
        workflow = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("flutter-version: '3.50.0'", workflow)
        self.assertIn("d6728363bf7969bf76a95457e2c5c12b29fbe057", workflow)


if __name__ == "__main__":
    unittest.main()
