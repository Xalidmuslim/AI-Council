"""Contract for two-stage model selection without requiring billable API calls."""
import unittest

from tools.cloud_agent import model_for_role


class ModelRoutingTests(unittest.TestCase):
    def test_first_stage_uses_primary_model(self):
        for role in ("programmer", "arabist"):
            with self.subTest(role=role):
                self.assertEqual(model_for_role(role, "primary", "independent"), "primary")

    def test_tester_uses_independent_model_when_configured(self):
        self.assertEqual(model_for_role("tester", "primary", "independent"), "independent")

    def test_tester_defaults_to_primary_model_when_unconfigured(self):
        self.assertEqual(model_for_role("tester", "primary", ""), "primary")
        self.assertEqual(model_for_role("tester", "primary", None), "primary")


if __name__ == "__main__":
    unittest.main()
