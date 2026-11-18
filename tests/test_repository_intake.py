"""TDD: read-only repository intake with safe agent handoff (fake HTTP only)."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.repository_intake import inspect_repository, render_markdown, write_report

REPOSITORY = "Xalidmuslim/Arabic-Academy-Flutter"
COMMIT_SHA = "d6728363bf7969bf76a95457e2c5c12b29fbe057"
API = "https://api.github.com/repos/" + REPOSITORY


class PublicRepoIntakeTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.visibility = "public"
        self.truncated = False

    def fake_get_json(self, url):
        self.requests.append(url)
        if url == API:
            return {"full_name": REPOSITORY, "private": self.visibility != "public",
                    "visibility": self.visibility}
        if url == API + "/commits/main":
            return {"sha": COMMIT_SHA}
        if url == API + "/git/trees/" + COMMIT_SHA + "?recursive=1":
            return {"truncated": self.truncated, "tree": [
                {"path": "AGENTS.md", "type": "blob", "size": 320},
                {"path": "README.md", "type": "blob", "size": 980},
                {"path": "pubspec.yaml", "type": "blob", "size": 450},
                {"path": "lib/main.dart", "type": "blob", "size": 1000},
                {"path": "assets/content/level1.json", "type": "blob", "size": 4900},
                {"path": "test/widget_test.dart", "type": "blob", "size": 1000},
                {"path": ".github/workflows/flutter-ci.yml", "type": "blob", "size": 1200},
                {"path": "android/app/build.gradle.kts", "type": "blob", "size": 600},
            ]}
        raise AssertionError("Unexpected API request: " + url)

    def inspect(self, repository=REPOSITORY, ref="main", allowlist=None):
        return inspect_repository(
            repository, ref,
            get_json=self.fake_get_json,
            allowed_repositories=allowlist or {REPOSITORY},
        )

    def test_public_flutter_manifest_and_handoff_are_pinned(self):
        result = self.inspect()
        self.assertEqual(result["repository"], REPOSITORY)
        self.assertEqual(result["requested_ref"], "main")
        self.assertEqual(result["commit_sha"], COMMIT_SHA)
        self.assertEqual(result["stack"], "Flutter")
        self.assertIn("AGENTS.md", result["instructions"])
        self.assertIn("test/widget_test.dart", result["tests"])
        self.assertIn("assets/content/level1.json", result["content_candidates"])
        self.assertEqual(result["tests_run"], [])
        self.assertEqual(result["status"], "NEEDS_CHECK")
        self.assertEqual([x["role"] for x in result["handoff"]],
                         ["programmer", "arabist", "tester"])
        self.assertTrue(all(x["commit_sha"] == COMMIT_SHA for x in result["handoff"]))
        self.assertEqual(len(self.requests), 3)
        self.assertTrue(all(url.startswith(API) for url in self.requests))

    def test_no_unapproved_repository_or_ref_is_ever_fetched(self):
        cases = [
            ("attacker/repo", "main"),
            ("Xalidmuslim/Private", "main"),
            (REPOSITORY, "../main"),
            (REPOSITORY, "main?recursive=1"),
            (REPOSITORY, ""),
        ]
        for repo, ref in cases:
            with self.subTest(repo=repo, ref=ref):
                self.requests.clear()
                with self.assertRaises(ValueError):
                    self.inspect(repo, ref)
                self.assertEqual(self.requests, [])

    def test_private_repo_is_blocked_even_if_allowlisted(self):
        self.visibility = "private"
        with self.assertRaisesRegex(ValueError, "private|public"):
            self.inspect()
        self.assertEqual(self.requests, [API])

    def test_incomplete_tree_must_not_appear_as_full_inventory(self):
        self.truncated = True
        with self.assertRaisesRegex(ValueError, "truncated"):
            self.inspect()

    def test_report_exposes_only_metadata_and_not_source_content(self):
        result = self.inspect()
        text = render_markdown(result)
        self.assertIn(COMMIT_SHA, text)
        self.assertIn("NEEDS_CHECK", text)
        self.assertIn("test/widget_test.dart", text)
        self.assertIn("не запускались", text)
        with tempfile.TemporaryDirectory() as folder:
            prefix = Path(folder) / "intake"
            json_path, md_path = write_report(result, prefix)
            self.assertTrue(json_path.exists())
            self.assertTrue(md_path.exists())
            parsed = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["commit_sha"], COMMIT_SHA)
            self.assertNotIn("source_content", parsed)


if __name__ == "__main__":
    unittest.main()
