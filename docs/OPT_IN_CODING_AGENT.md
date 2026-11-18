# AI-Council: opt-in AI programmer — bounded proposal pilot

**Version 2026-11-18.** This module prepares a **reviewable code proposal**, not an automatic change to a target repository. It uses genuine model requests only when separately enabled by the repository owner. All code models and APIs are disabled by default.

## What it does
- Uses the fixed public `Xalidmuslim/Arabic-Academy-Flutter` Issue [#48](https://github.com/Xalidmuslim/Arabic-Academy-Flutter/issues/48) and commit `d6728363bf7969bf76a95457e2c5c12b29fbe057` (not floating main).
- Reads only one explicitly permitted file: `test/widget_test.dart`. Denies private repos, other paths, other owners, closed issues and changed commits.
- Programmer AI proposes **one exact text replacement** in that file, as structured JSON; strict validation converts it into a single-file unified diff. Source is untrusted data, not executable instructions.
- Reviewer AI sees original source, task, and patch and returns `NEEDS_CHECK` or `REJECT`. **NEVER `VERIFIED`, auto-approval or merge.**
- Creates `agent_reports/coding-proposal.json`, `.md` and optional `.patch` artifact. No file is changed in the target repo, no generated patch is executed or tested. Rejects malformed or out-of-scope outputs.
- Both requests have `store: false`, `max_output_tokens: 2000` each, no tools, no retries. Maximum two requests in one invocation. **This is not a guaranteed monetary cap** because input tokens and pricing depend on the actual configured API models.
- Different model IDs may be configured for programmer and reviewer (`AI_CODING_MODEL` and `AI_CODING_REVIEW_MODEL`). Two separate calls to the same model are not independent models. No models have actually been invoked merely by committing this code.

## Real opt-in: manual setup, NOT performed by the PR
1. Review this draft PR, tests, source and security controls. Adopt its workflow only after explicit approval and review of dependencies.
2. In the **AI-Council** repository's Actions variables, configure `AI_CODING_ENABLED=true`, `AI_CODING_COST_ACKNOWLEDGED=true`, `AI_CODING_MODEL=<supported API model ID>`, optionally `AI_CODING_REVIEW_MODEL=<supported API model ID>`. These are GitHub Actions *variables*, not ChatGPT model-menu labels.
3. In GitHub Actions **secrets**, configure `OPENAI_API_KEY` with an appropriately budget-limited API project key, which is separate from a ChatGPT subscription.
4. Open Actions → **AI-Council opt-in coding agent (proposal only)** → Run workflow. Check **run_paid**. If any of the three opt-ins (enable variable, acknowledged-cost variable, per-run checkbox) is missing or the API key absent, no model or external source fetch is performed.
5. Inspect artifact `ai-council-code-proposal` and review the diff yourself. Do not apply a patch without checking source changes and running real Flutter CI in the *target* repository. The model is a proposer, not a trusted executor.

## Security boundaries and gaps
- No `pull-requests: write`, `contents: write` or cross-repo PAT; only `contents: read` / `issues: read`.
- Runs on `workflow_dispatch` only — never schedule, pull_request, or unknown third-party issue text. Explicit JSON contract in `agent_inputs/opt_in_coding_pilot.json` is pinned, with strict allowlists.
- Any manually re-run workflow may make **another** pair of paid requests; no automatic retries, but user-run retries are distinct chargeable actions. No background automation.
- User or code in GitHub is treated as untrusted prompt data; output never executes on the runner. The patch is bounded and limited to the one test file.
- Workflow run artifacts (including generated code) reside in a **public repository** and must not contain secrets, proprietary text, personal data or private repository content.
- The gate cannot prove that suggested tests compile, nor that a patch is secure. Manual code review and actual `flutter analyze`, `flutter test` in a separate target branch remain mandatory.
- No Flutter APK, device measurement or cross-repo draft PR is produced. That requires a separate, explicitly approved stage with secure write privileges.

## Local offline tests
```bash
python3 -m unittest discover -s tests -v
```
These unit tests fake the GitHub and model responses — **no billable calls**. Test failures against missing module before implementation are expected TDD RED evidence. Success confirms validation and orchestration only.
