"""TDD: deterministic, API-free handoff contracts for Codex Cloud."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.codex_handoff import validate_task, make_handoffs, write_handoffs

REPO = "Xalidmuslim/Arabic-Academy-Flutter"
SHA = "d6728363bf7969bf76a95457e2c5c12b29fbe057"
TASK = {
    "repository": REPO,
    "issue_url": "https://github.com/Xalidmuslim/Arabic-Academy-Flutter/issues/48",
    "base_commit": SHA,
    "objective": "Add coverage for role switching without touching lesson content.",
    "allowed_paths": ["test/widget_test.dart", "test/content_test.dart"],
    "acceptance": ["flutter analyze --no-fatal-infos", "flutter test"],
    "constraints": ["Preserve every Arabic lesson string and local user data."],
}


class CodexHandoffTests(unittest.TestCase):
    def test_valid_task_is_strict_and_normalized(self):
        self.assertEqual(validate_task(TASK)["base_commit"], SHA)
        self.assertEqual(validate_task(TASK)["allowed_paths"], TASK["allowed_paths"])

    def test_wrong_repository_issue_and_commit_are_rejected(self):
        cases = (
            {"repository": "Xalidmuslim/Malina-PRO-Android"},
            {"repository": "attacker/project"},
            {"issue_url": "https://github.com/attacker/project/issues/48"},
            {"issue_url": "https://github.com/Xalidmuslim/Arabic-Academy-Flutter/pull/49"},
            {"base_commit": "main"},
            {"base_commit": "deadbeef"},
            {"objective": ""},
            {"unrecognized": "secret"},
        )
        for delta in cases:
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                validate_task({**TASK, **delta})

    def test_unsafe_path_or_unapproved_command_is_rejected(self):
        changes = (
            {"allowed_paths": ["../assets/content/level1.json"]},
            {"allowed_paths": ["/etc/passwd"]},
            {"allowed_paths": ["lib/main.dart"]},
            {"allowed_paths": ["test/../../secrets.txt"]},
            {"allowed_paths": ["test/widget_test.dart", "test/widget_test.dart"]},
            {"allowed_paths": []},
            {"acceptance": ["flutter test; rm -rf /"]},
            {"acceptance": ["flutter test"]},
            {"acceptance": ["flutter analyze --no-fatal-infos", "flutter test --update-goldens"]},
        )
        for delta in changes:
            with self.subTest(delta=delta), self.assertRaises(ValueError):
                validate_task({**TASK, **delta})

    def test_programmer_and_reviewer_are_distinct_human_started_tasks(self):
        result = make_handoffs(TASK)
        self.assertEqual(result["status"], "NEEDS_CHECK")
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["external_actions"], [])
        self.assertIn(SHA, result["programmer_prompt"])
        self.assertIn(SHA, result["reviewer_prompt"])
        self.assertIn("test/widget_test.dart", result["programmer_prompt"])
        self.assertIn("test/content_test.dart", result["reviewer_prompt"])
        self.assertIn("GitHub Issue #48", result["programmer_prompt"])
        self.assertIn("draft PR", result["programmer_prompt"])
        self.assertIn("separate Codex task", result["reviewer_prompt"])
        self.assertIn("НЕ запускались", result["reviewer_prompt"])
        self.assertNotIn("OPENAI_API_KEY", result["programmer_prompt"])

    def test_files_are_reproducible_and_cannot_claim_execution(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            result = make_handoffs(TASK)
            files = write_handoffs(result, output)
            self.assertEqual(sorted(files), ["handoff.json", "programmer.md", "reviewer.md"])
            meta = json.loads((output / "handoff.json").read_text(encoding="utf-8"))
            self.assertEqual(meta["status"], "NEEDS_CHECK")
            self.assertEqual(meta["model_calls"], 0)
            self.assertEqual(meta["base_commit"], SHA)
            self.assertNotIn("programmer_prompt", meta)
            self.assertNotIn("reviewer_prompt", meta)
            self.assertIn("NEEDS_CHECK", (output / "reviewer.md").read_text(encoding="utf-8"))

    def test_no_silent_guessing_or_private_data_in_constraints(self):
        for constraints in (
            [],
            [""] ,
            ["a" * 601],
        ):
            with self.subTest(constraints=constraints), self.assertRaises(ValueError):
                validate_task({**TASK, "constraints": constraints})


if __name__ == "__main__":
    unittest.main()
