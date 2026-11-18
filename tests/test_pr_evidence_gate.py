"""Read-only pull request evidence gate (fully offline tests)."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.pr_evidence_gate import evaluate_pr, write_report

REPO = "Xalidmuslim/Arabic-Academy-Flutter"
SHA = "e91c8feb2a7f0cc630db1bc5d76d79053af13ea1"
BASE = "d6728363bf7969bf76a95457e2c5c12b29fbe057"
API = "https://api.github.com/repos/" + REPO
RUN = 44266100331


class EvidenceGateTests(unittest.TestCase):
    def setUp(self):
        self.requests = []
        self.private = False
        self.head = SHA
        self.extra_file = None
        self.run_result = "success"
        self.test_step = "success"
        self.pr_changed_files = 5

    def fake(self, url):
        self.requests.append(url)
        if url == API:
            return {"full_name": REPO, "private": self.private,
                    "visibility": "private" if self.private else "public"}
        if url == API + "/pulls/49":
            return {"number": 49, "draft": True, "state": "open",
                    "changed_files": self.pr_changed_files,
                    "user": {"login": "Xalidmuslim"},
                    "head": {"sha": self.head, "repo": {"full_name": REPO}},
                    "base": {"ref": "main", "sha": BASE}}
        if url == API + "/pulls/49/files?per_page=100":
            files = [
                {"filename": "lib/main.dart", "status": "modified"},
                {"filename": "pubspec.yaml", "status": "modified"},
                {"filename": "test/local_state_failure_test.dart", "status": "added"},
                {"filename": "test/local_state_regression_test.dart", "status": "added"},
                {"filename": ".github/workflows/council-regression.yml", "status": "added"},
            ]
            if self.extra_file is not None:
                files.append({"filename": self.extra_file, "status": "modified"})
            return files
        if url == API + "/actions/runs?head_sha=" + SHA + "&per_page=100":
            return {"total_count": 1, "workflow_runs": [{
                "id": RUN, "name": "AI-Council local-data regression (PR)",
                "status": "completed", "conclusion": self.run_result,
                "head_sha": SHA, "event": "pull_request",
            }]}
        if url == API + "/actions/runs/" + str(RUN) + "/jobs?per_page=100":
            return {"total_count": 1, "jobs": [{
                "name": "verify", "status": "completed", "conclusion": "success",
                "steps": [
                    {"name": "Static analysis (info-level deprecations visible, errors still fatal)",
                     "conclusion": "success"},
                    {"name": "Test existing features and local data recovery",
                     "conclusion": self.test_step},
                ],
            }]}
        raise AssertionError("Unexpected API request: " + url)

    def check(self, repository=REPO, head=SHA):
        return evaluate_pr(repository, 49, head, get_json=self.fake)

    def test_verified_pinned_evidence_requires_human_approval(self):
        report = self.check()
        self.assertEqual(report["status"], "NEEDS_CHECK")
        self.assertEqual(report["ci_status"], "PASS")
        self.assertEqual(report["head_sha"], SHA)
        self.assertEqual(report["changed_files"], 5)
        self.assertEqual(report["tests_run_by_reviewer"], [])
        self.assertEqual(report["run_id"], RUN)
        self.assertEqual(report["issues"], [])
        self.assertEqual(len(self.requests), 5)

    def test_unapproved_repository_is_rejected_before_network(self):
        with self.assertRaises(ValueError):
            self.check(repository="Xalidmuslim/Malina-PRO-Android")
        self.assertEqual(self.requests, [])

    def test_private_or_wrong_source_commit_fails_closed(self):
        self.private = True
        with self.assertRaises(ValueError):
            self.check()
        self.assertEqual(self.requests, [API])
        self.private = False
        self.requests.clear()
        self.head = "f" * 40
        with self.assertRaises(ValueError):
            self.check()
        self.assertEqual(self.requests, [API, API + "/pulls/49"])

    def test_content_or_unexpected_workflow_change_is_blocked(self):
        self.pr_changed_files = 6
        for bad in ("assets/content/level1.json", ".github/workflows/steal.yml"):
            self.requests.clear()
            self.extra_file = bad
            report = self.check()
            self.assertEqual(report["status"], "FAILED")
            self.assertTrue(any(bad in x for x in report["issues"]))
            self.assertEqual(len(self.requests), 3)

    def test_incomplete_changed_files_list_is_blocked(self):
        self.pr_changed_files = 101
        report = self.check()
        self.assertEqual(report["status"], "FAILED")
        self.assertIn("file list", " ".join(report["issues"]))

    def test_failed_ci_and_skipped_test_step_block_review(self):
        self.run_result = "failure"
        report = self.check()
        self.assertEqual(report["status"], "FAILED")
        self.run_result = "success"
        self.test_step = "skipped"
        report = self.check()
        self.assertEqual(report["status"], "FAILED")

    def test_report_contains_only_public_metadata_not_source_content(self):
        report = self.check()
        with tempfile.TemporaryDirectory() as folder:
            json_path, md_path = write_report(report, Path(folder) / "review")
            parsed = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(parsed["head_sha"], SHA)
            self.assertIn("NEEDS_CHECK", md_path.read_text(encoding="utf-8"))
            self.assertNotIn("source_code", parsed)
            self.assertNotIn("AI model reviewed", md_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
