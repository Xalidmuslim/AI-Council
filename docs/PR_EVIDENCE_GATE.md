# AI-Council — read-only PR evidence gate

Pilot as of 18 November 2026. Source: `Xalidmuslim/Arabic-Academy-Flutter` (public).

## Intended protection
This independent *CI job* checks a public GitHub draft PR's metadata. It does not use an AI model and does not issue code-review approval. Every claim must be backed by the current GitHub API result.

It verifies:
- explicit repository allowlist and publicly confirmed visibility;
- draft PR #49 is open, owner-authored, targets main, and has the **exact expected head commit SHA**;
- complete changed file inventory is limited to five specifically approved filenames;
- no unapproved book content, JSON, scripts, or other workflow files changed;
- latest matching CI workflow for the exact head SHA completed successfully;
- that workflow's `verify` job reports both the analyzer and Flutter test steps successful;
- output is `NEEDS_CHECK` even when the evidence gate passes.

The pilot deliberately pins:
- repository: `Xalidmuslim/Arabic-Academy-Flutter`
- PR: `49`
- head: `e91c8feb2a7f0cc630db1bc5d76d79053af13ea1`
- required CI: `AI-Council local-data regression (PR)`

**If the PR head changes, the gate fails closed until the approved SHA is explicitly updated and reviewed.** No automatic approval or merge. If changed files exceed one page or metadata is incomplete, fail rather than falsely declaring full coverage.

## Security limitations
A successful GitHub Actions run is not inherently proof that code is secure, nor proof that tests are meaningful. The modified PR itself includes a CI workflow: therefore a human must review that workflow's commands, the source diff, and test logs. A compromised workflow could otherwise report successful steps without adequate testing.

The review checks **public metadata only**. It must not handle private project source, credentials, unpublished texts, personal information or confidential user data. The runner has read-only permission and checkout doesn't retain credentials.

## Workflow
- `.github/workflows/pr-evidence-gate.yml` — runs on this PR and, after merge, supports manual execution.
- `tools/pr_evidence_gate.py` — GitHub API read-only evaluation.
- `tests/test_pr_evidence_gate.py` — offline fake API tests.
- Artifact `public-pr-evidence` contains `pr-evidence.json` and `pr-evidence.md`.

Next development stage (not in this PR): an actual separately authorized, sandboxed code-agent implementation on target repo plus a distinct independent review agent. These need scoped permissions, secrets isolation, cost limits and explicit human approval.
