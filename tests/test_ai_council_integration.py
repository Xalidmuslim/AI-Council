import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = (
    "replica-recon", "replica-architect", "replica-design", "replica-build",
    "replica-backend", "replica-test", "replica-diff", "replica-entrepreneur",
    "replica-brand", "replica-launch", "replica-deploy"
)
ASSETS = (
    "replica-design/contrast.py", "replica-diff/imgdiff.py", "replica-diff/parity.py",
    "replica-entrepreneur/reviews.py", "replica-brand/sweep.py",
    "replica-launch/listing.py"
)

class AIIntegration(unittest.TestCase):
    def test_router_and_eleven_skills_in_both_hosts(self):
        for prefix in (".agents/skills", ".claude/skills"):
            base = ROOT / prefix
            self.assertTrue((base / "ai-council-router/SKILL.md").is_file())
            names = sorted(x.name for x in base.iterdir() if x.is_dir())
            self.assertEqual(names, sorted([*SKILLS, "ai-council-router"]))
            for n in SKILLS:
                content = (base / n / "SKILL.md").read_text(encoding="utf8")
                self.assertTrue(content.startswith("---\\n".replace("\\n","\n")))
                self.assertIn("name: " + n, content)
                self.assertIn("AI-Council", content)

    def test_both_host_skill_trees_identical(self):
        a = ROOT / ".agents/skills"
        b = ROOT / ".claude/skills"
        paths_a = sorted(x.relative_to(a) for x in a.rglob("*") if x.is_file())
        paths_b = sorted(x.relative_to(b) for x in b.rglob("*") if x.is_file())
        self.assertEqual(paths_a, paths_b)
        for path in paths_a:
            self.assertEqual((a/path).read_bytes(), (b/path).read_bytes(), str(path))

    def test_guardrails_source_and_six_helpers(self):
        for path in ("ANDROID_PLAYBOOK.md", "AGENTS.md", "CLAUDE.md",
                     "LICENSE-REPLICA-SKILL", "THIRD_PARTY_NOTICES.md"):
            self.assertTrue((ROOT / path).is_file(), path)
        guards=(ROOT / "ANDROID_PLAYBOOK.md").read_text()
        self.assertIn("120 FPS", guards)
        self.assertIn("Kotlin", guards)
        for path in ASSETS:
            self.assertTrue((ROOT/".agents/skills"/path).is_file(), path)

if __name__ == "__main__":
    unittest.main()
