"""TDD contract for a manually gated, proposal-only AI programmer."""
import base64
import json
import tempfile
import unittest
from pathlib import Path

from tools.opt_in_coder import (
    validate_task, validate_proposal, inspect_source, execute,
)

REPO = "Xalidmuslim/Arabic-Academy-Flutter"
SHA = "d6728363bf7969bf76a95457e2c5c12b29fbe057"
PATH = "test/widget_test.dart"
SRC = "void main() {\n  testWidgets('demo', (_) {});\n}\n"
TASK = {
    "issue_number": 48,
    "repository": REPO,
    "source_sha": SHA,
    "file_path": PATH,
    "objective": "Propose a minimal test for switching demo role in Flutter; no app changes.",
}
PROPOSAL = {
    "file_path": PATH,
    "old_text": "  testWidgets('demo', (_) {});",
    "new_text": "  testWidgets('demo', (_) { expect(true, true); });",
    "summary": "Minimal regression example, needs human review.",
    "test_command": "flutter test test/widget_test.dart",
}
REVIEW = {"verdict": "NEEDS_CHECK", "issues": ["Run real Flutter tests on a review branch."]}


class OptInCoderTests(unittest.TestCase):
    def fake_data(self):
        return {
            "issue": {"number": 48, "state": "open",
                      "user": {"login": "Xalidmuslim"}, "title": "Flutter QA"},
            "repository": {"full_name": REPO, "private": False, "visibility": "public"},
            "commit": {"sha": SHA},
            "file": {"type": "file", "path": PATH, "size": len(SRC.encode("utf-8")),
                     "encoding": "base64",
                     "content": base64.b64encode(SRC.encode()).decode()},
        }

    def test_disabled_is_zero_cost_zero_network(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(
                enabled=False, cost_acknowledged=False, api_key="",
                task=TASK, output_prefix=Path(tmp) / "report",
                get_data=lambda *_: self.fail("Network used"),
                ask=lambda *_: self.fail("Billable call"),
            )
            self.assertEqual(result["status"], "DISABLED")
            self.assertEqual(result["model_calls"], 0)

    def test_cost_ack_is_required_before_any_network_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(
                enabled=True, cost_acknowledged=False, api_key="test",
                task=TASK, output_prefix=Path(tmp) / "report",
                get_data=lambda *_: self.fail("Network used"),
                ask=lambda *_: self.fail("Billable call"),
            )
            self.assertEqual(result["status"], "DISABLED")

    def test_strict_task_contract_and_path_allowlist(self):
        validate_task(TASK)
        for change in (
            {"repository": "Xalidmuslim/Malina-PRO-Android"},
            {"file_path": "assets/content/level1.json"},
            {"file_path": "../secrets.txt"},
            {"source_sha": "main"},
            {"issue_number": -1},
            {"objective": ""},
            {"unapproved": "field"},
        ):
            bad = {**TASK, **change}
            with self.subTest(bad=change), self.assertRaises(ValueError):
                validate_task(bad)

    def test_inspection_requires_pinned_sha_public_repo_owner_issue(self):
        data = self.fake_data()
        self.assertEqual(inspect_source(TASK, data), SRC)
        for key, mutate in (
            ("private", lambda d: d["repository"].update(private=True, visibility="private")),
            ("commit", lambda d: d["commit"].update(sha="f" * 40)),
            ("issue", lambda d: d["issue"]["user"].update(login="other")),
            ("state", lambda d: d["issue"].update(state="closed")),
            ("path", lambda d: d["file"].update(path="lib/main.dart")),
            ("symlink", lambda d: d["file"].update(type="symlink")),
        ):
            bad = self.fake_data()
            mutate(bad)
            with self.subTest(key=key), self.assertRaises(ValueError):
                inspect_source(TASK, bad)

    def test_source_base64_must_reject_ignored_garbage(self):
        corrupted = self.fake_data()
        corrupted["file"]["content"] += "$"
        with self.assertRaises(ValueError):
            inspect_source(TASK, corrupted)

    def test_full_source_patch_is_not_required_and_diff_is_pinned(self):
        result = validate_proposal(TASK, SRC, PROPOSAL)
        self.assertIn("-  testWidgets('demo', (_) {});", result["diff"])
        self.assertIn("+  testWidgets('demo', (_) { expect(true, true); });", result["diff"])
        self.assertIn("--- a/test/widget_test.dart", result["diff"])
        self.assertIn("+++ b/test/widget_test.dart", result["diff"])
        self.assertEqual(result["updated_source"].count("void main()"), 1)

    def test_proposal_refuses_other_paths_ambiguous_or_missing_old_text(self):
        for proposal in (
            {**PROPOSAL, "file_path": "lib/main.dart"},
            {**PROPOSAL, "old_text": "not found"},
            {**PROPOSAL, "old_text": ""},
            {**PROPOSAL, "new_text": ""},
            {**PROPOSAL, "test_command": "rm -rf /"},
            {**PROPOSAL, "extra": "bad"},
        ):
            with self.subTest(case=proposal), self.assertRaises(ValueError):
                validate_proposal(TASK, SRC, proposal)
        duplicated = SRC + SRC
        with self.assertRaises(ValueError):
            validate_proposal(TASK, duplicated, PROPOSAL)

    def test_real_two_stage_proposal_is_reviewed_but_not_applied(self):
        data = self.fake_data()
        calls = []
        def get_data(kind, *_):
            return data[kind]
        def ask(role, model, prompt, schema):
            calls.append((role, model, prompt, schema))
            return PROPOSAL if role == "programmer" else REVIEW
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "proposal"
            result = execute(
                enabled=True, cost_acknowledged=True, api_key="fake",
                task=TASK, get_data=get_data, ask=ask,
                output_prefix=prefix, primary_model="model-one",
                review_model="model-two",
            )
            self.assertEqual(result["status"], "NEEDS_CHECK")
            self.assertEqual(result["model_calls"], 2)
            self.assertEqual([x[0] for x in calls], ["programmer", "tester"])
            self.assertEqual([x[1] for x in calls], ["model-one", "model-two"])
            self.assertIn("testWidgets", prefix.with_suffix(".patch").read_text())
            self.assertEqual(json.loads(prefix.with_suffix(".json").read_text())["source_sha"], SHA)
            self.assertTrue(all("tools" not in x[2] for x in calls))
            self.assertTrue(result["review_models_distinct"])

    def test_review_rejection_never_becomes_verified(self):
        data = self.fake_data()
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(
                enabled=True, cost_acknowledged=True, api_key="fake",
                task=TASK, get_data=lambda kind,*_: data[kind],
                ask=lambda role,*_: PROPOSAL if role == "programmer" else
                     {"verdict": "REJECT", "issues": ["Malformed test"]},
                output_prefix=Path(tmp) / "proposal",
                primary_model="same-model",
            )
            self.assertEqual(result["status"], "REJECT")
            self.assertFalse(result["review_models_distinct"])
            self.assertEqual(result["model_calls"], 2)

    def test_invalid_model_proposal_aborts_without_reviewer_or_writing(self):
        data = self.fake_data()
        calls = []
        def ask(role, *_):
            calls.append(role)
            return {**PROPOSAL, "file_path": "lib/main.dart"}
        with tempfile.TemporaryDirectory() as tmp:
            prefix = Path(tmp) / "report"
            with self.assertRaises(ValueError):
                execute(
                    enabled=True, cost_acknowledged=True, api_key="fake",
                    task=TASK, get_data=lambda kind,*_: data[kind],
                    ask=ask, output_prefix=prefix, primary_model="model-one",
                )
            self.assertEqual(calls, ["programmer"])
            self.assertFalse(prefix.with_suffix(".patch").exists())

    def test_no_api_key_makes_no_model_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = execute(
                enabled=True, cost_acknowledged=True, api_key="",
                task=TASK, get_data=lambda *_: self.fail("Network used"),
                ask=lambda *_: self.fail("Model used"),
                output_prefix=Path(tmp)/"proposal",
            )
            self.assertEqual(result["status"], "NEEDS_CHECK")
            self.assertEqual(result["model_calls"], 0)


if __name__ == "__main__":
    unittest.main()
