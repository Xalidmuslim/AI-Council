import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from PIL import Image, ImageDraw

TOOL = Path(__file__).resolve().parents[1] / 'tools' / 'reference_qa.py'


class ReferenceQaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.ref = self.root / 'ref.png'
        self.actual = self.root / 'actual.png'
        self.out = self.root / 'report'

    def screenshot(self, path, rectangle=(2, 2, 8, 8), color=(170, 120, 95), size=(20, 20)):
        image = Image.new('RGB', size, (245, 243, 239))
        ImageDraw.Draw(image).rectangle(rectangle, fill=color)
        image.save(path)

    def run_tool(self, *args):
        return subprocess.run([sys.executable, str(TOOL), str(self.ref),
                               str(self.actual), '--out-dir', str(self.out), *map(str, args)],
                              capture_output=True, text=True)

    def report(self):
        return json.loads((self.out / 'report.json').read_text(encoding='utf-8'))

    def test_exact_match_passes_and_writes_outputs(self):
        self.screenshot(self.ref)
        self.screenshot(self.actual)
        result = self.run_tool()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.report()['changed_percent'], 0)
        self.assertTrue((self.out / 'diff.png').exists())
        self.assertTrue((self.out / 'overlay.png').exists())
        self.assertTrue((self.out / 'summary.md').exists())

    def test_shifted_3d_card_fails(self):
        self.screenshot(self.ref)
        self.screenshot(self.actual, rectangle=(3, 2, 9, 8))
        result = self.run_tool('--max-changed-percent', 0)
        self.assertEqual(result.returncode, 1, result.stderr)
        report = self.report()
        self.assertGreater(report['changed_percent'], 0)
        self.assertEqual(report['status'], 'different')
        self.assertIn('changed_bounds', report)

    def test_small_color_difference_uses_channel_tolerance(self):
        self.screenshot(self.ref)
        self.screenshot(self.actual, color=(171, 120, 95))
        self.assertEqual(self.run_tool('--tolerance', 1).returncode, 0)
        self.assertEqual(self.run_tool('--tolerance', 0).returncode, 1)

    def test_resolution_mismatch_fails_even_with_matching_content(self):
        self.screenshot(self.ref)
        self.screenshot(self.actual, size=(21, 20))
        result = self.run_tool()
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.report()['status'], 'dimension_mismatch')

    def test_mask_ignores_only_dynamic_region(self):
        self.screenshot(self.ref)
        self.screenshot(self.actual, color=(200, 120, 95))
        mask = self.root / 'mask.json'
        mask.write_text(json.dumps({'ignore_regions': [{'x': 2, 'y': 2, 'width': 7, 'height': 7}]}))
        self.assertEqual(self.run_tool('--mask', mask).returncode, 0)
        self.assertGreater(self.report()['ignored_percent'], 0)

    def test_mask_cannot_hide_entire_screen(self):
        self.screenshot(self.ref)
        self.screenshot(self.actual, color=(200, 120, 95))
        mask = self.root / 'mask.json'
        mask.write_text(json.dumps({'ignore_regions': [{'x': 0, 'y': 0, 'width': 20, 'height': 20}]}))
        self.assertEqual(self.run_tool('--mask', mask).returncode, 2)

    def test_missing_image_never_reports_success(self):
        self.screenshot(self.ref)
        self.assertEqual(self.run_tool().returncode, 2)


if __name__ == '__main__':
    unittest.main()
