"""Regression tests for safe, retry-resistant issue claiming (no external calls)."""
import tempfile
import unittest
from pathlib import Path

from tools.cloud_agent import execute


class CloudAgentClaimTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "agent_inputs").mkdir()
        (self.root / "agent_inputs" / "sample.txt").write_text("كِتَابٌ", encoding="utf-8")
        self.output = self.root / "agent_reports" / "report.md"
        self.issue = {
            "number": 4,
            "title": "[AGENT:pending] safe trial",
            "user": {"login": "Xalidmuslim"},
            "body": '{"role":"arabist","source_path":"agent_inputs/sample.txt","objective":"Check text"}',
        }
        self.events = []

    def action(self, method, path, payload):
        self.events.append((method, path, payload))
        if method == "PATCH":
            self.issue["title"] = payload["title"]

    def start(self, ask):
        return execute(
            enabled=True, api_key="fake-key",
            get_issues=lambda: [self.issue],
            action=self.action, ask=ask,
            root=self.root, owner="Xalidmuslim", output=self.output,
        )

    def test_claim_before_first_billable_call_and_review_after_report(self):
        def ask(*args):
            self.events.append(("ASK", args[0]))
            self.assertTrue(self.output.parent.exists())
            return "draft" if args[0] == "arabist" else "review"
        self.assertEqual(self.start(ask), "NEEDS_CHECK")
        self.assertEqual(self.events[0], (
            "PATCH", "issues/4", {"title": "[AGENT:running] safe trial"}
        ))
        self.assertEqual(len([x for x in self.events if x[0] == "ASK"]), 2)
        self.assertEqual(self.issue["title"], "[AGENT:review] safe trial")
        self.assertTrue(self.output.is_file())
        self.assertIn("NEEDS_CHECK", self.output.read_text(encoding="utf-8"))

    def test_failed_claim_does_not_spend_any_api_calls(self):
        def reject_claim(*args):
            raise RuntimeError("GitHub unavailable")
        with self.assertRaisesRegex(RuntimeError, "GitHub unavailable"):
            execute(
                enabled=True, api_key="fake-key",
                get_issues=lambda: [self.issue],
                action=reject_claim,
                ask=lambda *_: self.fail("Paid API called without claim"),
                root=self.root, owner="Xalidmuslim", output=self.output,
            )

    def test_failed_model_call_remains_claimed_and_is_not_automatically_retried(self):
        calls = []
        def fail_after_claim(*args):
            calls.append(args)
            raise RuntimeError("model interrupted")
        with self.assertRaisesRegex(RuntimeError, "model interrupted"):
            self.start(fail_after_claim)
        self.assertEqual(len(calls), 1)
        self.assertEqual(self.issue["title"], "[AGENT:running] safe trial")
        self.assertIn("NEEDS_CHECK", self.output.read_text(encoding="utf-8"))
        self.assertEqual(self.start(lambda *_: self.fail("Double charged")), "IDLE")
        self.assertEqual(len(calls), 1)


if __name__ == "__main__":
    unittest.main()
