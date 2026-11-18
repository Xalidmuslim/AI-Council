"""AI-Council pinned three-role pilot: offline contract and security tests."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.pilot_checks import inspect_programmer, inspect_arabist, write_report


SHA = "d6728363bf7969bf76a95457e2c5c12b29fbe057"


def create_fixture(root):
    (root / "lib").mkdir()
    (root / "test").mkdir()
    (root / "assets" / "content").mkdir(parents=True)
    (root / ".github" / "workflows").mkdir(parents=True)
    for name, text in (
        ("AGENTS.md", "# Follow task-specific skills\n"),
        ("pubspec.yaml", "name: arabic_academy\n"),
        ("lib/main.dart", "void main() {}\n"),
        ("test/widget_test.dart", "testWidgets('demo', (_) {});\n"),
        (".github/workflows/flutter-android.yml", "name: Flutter checks\n"),
    ):
        (root / name).write_text(text, encoding="utf-8")
    catalog = {
        "source_policy": "Original editorial drafts. Requires review.",
        "modules": [{"id": "u1", "title_ar": "دَرْسٌ"}],
        "lessons": [{
            "id": "l1", "title_ar": "التَّحِيَّةُ",
            "dialogue": [{"ar": "السَّلَامُ عَلَيْكُمْ.", "ru": "Мир вам"}],
            "vocabulary": [{"ar": "كِتَابٌ", "ru": "Книга"}],
            "options": ["Книга", "Другое"], "correct": 0,
        }],
    }
    (root / "assets" / "content" / "level1.json").write_text(
        json.dumps(catalog, ensure_ascii=False), encoding="utf-8"
    )
    return catalog


class PilotChecksTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.catalog = create_fixture(self.root)
        self.head = lambda _: SHA

    def test_programmer_inventory_pins_commit_and_lists_actual_tests(self):
        result = inspect_programmer(self.root, SHA, get_head=self.head)
        self.assertEqual(result["role"], "programmer")
        self.assertEqual(result["status"], "NEEDS_CHECK")
        self.assertEqual(result["commit_sha"], SHA)
        self.assertIn("test/widget_test.dart", result["tests_found"])
        self.assertIn("AGENTS.md", result["instructions_found"])
        self.assertIn("flutter-android.yml", result["workflows_found"][0])
        self.assertTrue(result["content_sha256"])
        self.assertEqual(result["tests_run"], [])
        self.assertFalse(result["source_modified"])

    def test_reject_wrong_commit_before_reading_project(self):
        with self.assertRaisesRegex(ValueError, "commit"):
            inspect_programmer(self.root, "f" * 40, get_head=self.head)
        with self.assertRaisesRegex(ValueError, "commit"):
            inspect_arabist(self.root, "f" * 40, get_head=self.head)

    def test_arabist_structural_pass_is_not_semantic_approval(self):
        result = inspect_arabist(self.root, SHA, get_head=self.head)
        self.assertEqual(result["role"], "arabist")
        self.assertEqual(result["structural_status"], "PASS")
        self.assertEqual(result["semantic_status"], "NOT_CHECKED")
        self.assertEqual(result["status"], "NEEDS_CHECK")
        self.assertEqual(result["errors"], [])
        self.assertGreater(result["arabic_fields_checked"], 2)

    def test_replacement_char_bidi_control_and_missing_arabic_are_detected(self):
        for bad in ("سَلَامٌ\ufffd", "سَلَامٌ\u202e", "plain Russian"):
            with self.subTest(bad=repr(bad)):
                self.catalog["lessons"][0]["dialogue"][0]["ar"] = bad
                (self.root / "assets/content/level1.json").write_text(
                    json.dumps(self.catalog, ensure_ascii=False), encoding="utf-8"
                )
                result = inspect_arabist(self.root, SHA, get_head=self.head)
                self.assertEqual(result["structural_status"], "FAIL")
                self.assertEqual(result["status"], "FAILED")
                self.assertTrue(result["errors"])
                self.assertNotIn(bad, json.dumps(result, ensure_ascii=False))

    def test_invalid_answer_index_is_detected(self):
        self.catalog["lessons"][0]["correct"] = 9
        (self.root / "assets/content/level1.json").write_text(
            json.dumps(self.catalog, ensure_ascii=False), encoding="utf-8"
        )
        result = inspect_arabist(self.root, SHA, get_head=self.head)
        self.assertEqual(result["status"], "FAILED")
        self.assertTrue(any("correct" in error for error in result["errors"]))

    def test_report_contains_provenance_not_arabic_source_content(self):
        result = inspect_arabist(self.root, SHA, get_head=self.head)
        jsonfile, mdfile = write_report(result, self.root / "reports" / "arabist")
        self.assertTrue(jsonfile.is_file())
        self.assertIn("NEEDS_CHECK", mdfile.read_text(encoding="utf-8"))
        saved = json.loads(jsonfile.read_text(encoding="utf-8"))
        self.assertEqual(saved["commit_sha"], SHA)
        self.assertNotIn("كِتَابٌ", mdfile.read_text(encoding="utf-8"))
        self.assertNotIn("السَّلَامُ عَلَيْكُمْ", json.dumps(saved, ensure_ascii=False))


if __name__ == "__main__":
    unittest.main()
