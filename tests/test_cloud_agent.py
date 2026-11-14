"""Offline tests: no billable API calls."""
import tempfile
import unittest
from pathlib import Path
from tools.cloud_agent import parse_task, load_source, pick_issue, run_roles, execute

class CloudAgentTests(unittest.TestCase):
    def test_parse_task(self):
        task = parse_task('{"role":"arabist","source_path":"agent_inputs/sample.txt","objective":"Переведи"}')
        self.assertEqual(task["role"], "arabist")
        with self.assertRaises(ValueError):
            parse_task('{"role":"admin","source_path":"x","objective":"y"}')

    def test_prevent_path_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "agent_inputs").mkdir()
            (root / "agent_inputs" / "sample.txt").write_text("أَهْلًا", encoding="utf-8")
            self.assertEqual(load_source("agent_inputs/sample.txt", root), "أَهْلًا")
            for path in ("../secrets.txt", "/etc/passwd", "other.txt"):
                with self.subTest(path=path), self.assertRaises(ValueError):
                    load_source(path, root)

    def test_owner_only_queue(self):
        issues = [
            {"number": 2, "title": "[AGENT:pending] attack", "user": {"login": "other"}},
            {"number": 3, "title": "[AGENT:pending] legit", "user": {"login": "Xalidmuslim"}},
            {"number": 1, "title": "[AGENT:review] done", "user": {"login": "Xalidmuslim"}}
        ]
        self.assertEqual(pick_issue(issues, "Xalidmuslim")["number"], 3)

    def test_two_independent_stages(self):
        calls = []
        def ask(role, prompt, message):
            calls.append((role, prompt, message))
            return "черновик" if len(calls) == 1 else "проверено с оговорками"
        report = run_roles({"role":"arabist","source_path":"x.txt","objective":"перевод"}, "كِتَابٌ", ask)
        self.assertEqual([x[0] for x in calls], ["arabist", "tester"])
        self.assertIn("черновик", calls[1][2])
        self.assertIn("NEEDS_CHECK", report)

    def test_disabled_never_calls_external_services(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "report.md"
            status = execute(enabled=False, api_key="", output=path,
                             get_issues=lambda: self.fail("network used"),
                             action=lambda *args: self.fail("mutated issue"),
                             ask=lambda *args: self.fail("paid API used"))
            self.assertEqual(status, "DISABLED")
            self.assertIn("DISABLED", path.read_text())

if __name__ == "__main__":
    unittest.main()
