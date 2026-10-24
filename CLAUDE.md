# AI-Council — Claude Code project instructions

For app development requests, select relevant `.claude/skills/replica-*/SKILL.md` and the `ai-council-router` skill implicitly, using the user's normal phrasing. Do not require `/replica-*` commands or invoke all skills for every request.

Use recon for existing code, design+diff for visual changes, test+targeted build+diff for bugs, trace-based profiling for jank/FPS, architect+build+test for new features, backend for server APIs, entrepreneur for real linked reviews, brand/launch/deploy only when specifically relevant.

Read `ANDROID_PLAYBOOK.md` for any Android/Flutter task and obey the target application's existing branch, stack, data and accepted design. Do not replace Compose/Flutter with Next.js/Expo. Verify a real Gradle build before claiming an APK is ready and measure FPS on an actual device. Separate instructions from executed actions and never assert an agent panel that did not run.

This applies to this project workspace; copying files to GitHub does not change how standalone ChatGPT conversations automatically load skills.
