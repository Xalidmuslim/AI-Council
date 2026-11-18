# AI-Council: automatic engineering skill selection

Select relevant installed skills based on the **user's natural-language task**, without requiring the user to invoke them by name. Skill directories: `.agents/skills/replica-*/SKILL.md` and `.agents/skills/ai-council-router/SKILL.md`.

- Existing app / inspect current state: `replica-recon` first.
- Redesign / approved screenshot: `replica-design` plus `replica-diff`.
- Bugs / crashes / back navigation / scrolling: reproduce using `replica-test`, make a minimum `replica-build` change, verify via `replica-diff`.
- Frame drops / jank / FPS: inspect sources and measured device traces; select `recon/test/diff` only as needed.
- New features: `replica-architect`, `replica-build`, `replica-test` as required.
- API/auth/data: `replica-backend`, `replica-test`. Reviews: `replica-entrepreneur`. Brand/launch/deploy only with a relevant user request.

**Critical for native Android or Flutter:** read [ANDROID_PLAYBOOK.md](ANDROID_PLAYBOOK.md) and the target project's own instruction files first. Inspect the real source and branch, preserve Kotlin/Compose or Flutter, content and prior optimizations. Avoid web-stack defaults from imported skills. Do not imply that running tests, building an APK or measuring 120 FPS happened unless it actually happened. Do not change production infrastructure or publish externally without authorization.

These rules are active only in agent environments that load this repository's instructions and skill directories. GitHub storage by itself does not activate skills in ChatGPT or unrelated repositories. Never load all 11 for a simple task.

## Three-role coordination (opt-in)

For requests that explicitly use the programmer, arabist or tester roles, read
[docs/AGENT_PROTOCOL.md](docs/AGENT_PROTOCOL.md) and the corresponding
[.github/agents/](.github/agents/) profile **before** acting. Roles are task
instructions, not proof of a separately running agent. Prefer explicit input
(repository/ref/commit, scope, evidence) and safe draft PR handoffs.
Read target-repository AGENTS.md first; never assume these instructions are loaded
automatically by ChatGPT Work or unrelated repositories.


## Codex Cloud without a separate OpenAI API key

When the task asks for AI-Council using Codex Cloud and GitHub Actions,
read [docs/CODEX_NO_API_WORKFLOW.md](docs/CODEX_NO_API_WORKFLOW.md).
Prepare the explicit fixed-scope pilot handoff with
`python3 tools/codex_handoff.py`. This creates prompts and metadata only;
it never starts models, creates cloud environments or transfers repository
permissions. Programmer and reviewer must be separate real Codex tasks
launched by the user in the authorized target repository. Do not call a
successful handoff CI run "agents executed". Do not turn on legacy
`AI_AUTOMATION_ENABLED` or `AI_CODING_ENABLED` for this no-API route.
