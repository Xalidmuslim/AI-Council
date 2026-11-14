"""Contract checks for the three role profiles (configuration only)."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROLES = ("programmer", "arabist", "tester")


class ThreeAgentConfigurationTests(unittest.TestCase):
    def test_each_role_has_distinct_valid_profile(self):
        for role in ROLES:
            with self.subTest(role=role):
                path = ROOT / ".github" / "agents" / (role + ".agent.md")
                content = path.read_text(encoding="utf-8")
                self.assertTrue(content.startswith("---\n"), path)
                self.assertRegex(content, r"(?m)^name: " + re.escape(role) + r"$")
                self.assertRegex(content, r"(?m)^description: .+")
                self.assertIn("\n---\n", content[4:])
                self.assertIn("docs/AGENT_PROTOCOL.md", content)
                self.assertGreater(len(content.splitlines()), 15)

    def test_work_playbook_is_explicit_not_autonomous(self):
        protocol = (ROOT / "docs/AGENT_PROTOCOL.md").read_text(encoding="utf-8")
        playbook = (ROOT / "docs/CHATGPT_WORK_START.md").read_text(encoding="utf-8")
        for role in ROLES:
            self.assertIn(role, protocol)
            self.assertIn(role, playbook)
        for status in ("VERIFIED", "FAILED", "NEEDS_CHECK"):
            self.assertIn(status, protocol)
        self.assertIn("не активируют", protocol)
        self.assertIn("не становятся автоматически", playbook)
        self.assertIn("не сливай", playbook)
        self.assertIn("main", playbook)


if __name__ == "__main__":
    unittest.main()
