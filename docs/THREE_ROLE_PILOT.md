# AI-Council: three-role evidence pilot on a real Flutter repository

Version: 2026-11-18. **Read-only engineering checks, not an autonomous coding agent.**

This pilot consumes exactly this public source revision:

- Repository: `Xalidmuslim/Arabic-Academy-Flutter`
- Pinned commit: `d6728363bf7969bf76a95457e2c5c12b29fbe057`
- Target project instructions: `AGENTS.md`
- Existing Flutter CI command sequence: `flutter create --project-name arabic_academy --platforms android,ios .`, `flutter pub get`, `flutter analyze`, `flutter test`

## What three separate CI jobs actually perform

1. **Programmer / RECON (Python).** Reads the existing public source in a checkout pinned by SHA, discovers project instructions, test and workflow paths, and records the SHA-256 of the Arabic catalog. No code is changed; it does not claim to execute AI.
2. **Arabist / structural checks (Python).** Parses `assets/content/level1.json` as UTF-8 JSON; validates module/lesson IDs, Arabic field presence, dangerous directional controls, replacement characters, combining-mark placement and quiz answer indices. Passing is **not** proof of correct Arabic morphology, translation, diacritics or source attribution. Final status is `NEEDS_CHECK` even when these automated structural checks pass.
3. **Tester / actual Flutter CLI.** Installs Flutter in a separate runner, generates temporary platform folders only inside the runner, runs `flutter analyze` and `flutter test` on that exact source checkout. Test and analysis logs are saved as artifacts. APK is not built; real-device FPS, navigation, performance and visual fidelity are not assessed.
4. **Quality gate.** Records each job's actual outcome. If any job fails, the gate fails. Otherwise it confirms only CI-level checks and keeps human approval required.

Each job has `contents: read`; public target checkout uses `persist-credentials: false`. No `OPENAI_API_KEY`, cross-repository write token, secrets, model billing, write-back to the target repository, publishing or auto-merge. This is a pinned demo source: it does not pretend to test whatever is currently on the target's `main`.

## How to inspect results

- New workflow: `.github/workflows/three-role-pilot.yml`.
- On the PR adding this workflow, look for the role jobs and `Quality gate` in GitHub Actions.
- Review artifacts `ai-council-programmer-recon`, `ai-council-arabist-structure`, `ai-council-tester-flutter-logs`.
- Before claiming success, verify the real Flutter test exit status, inspected commit and artifact contents.
- After adopting the workflow into the default branch it can be launched manually using GitHub Actions > AI-Council three-role Flutter pilot > Run workflow.

## Safe progression to actual independent AI coding

The next **separate** integration requires a Work/Codex executor *within an authorized target repository* (especially for private Android code), scoped write access, a single task and pinned baseline, approval for API costs if API used, a pre-change failing regression test, a minimal proposed diff, independent CI, and a **draft** PR for the owner's review. GitHub Actions metadata and prompt text alone do not start Sol/Astra or three separate AI models.

Do **not** reuse public artifacts for `Xalidmuslim/Malina-PRO-Android` because it is private. Do not change Arabic primary texts, translations, bookmarks or saved user data without explicit reviewed diffs and provenance. A successful source-code test run is not an APK or 120 FPS claim.
