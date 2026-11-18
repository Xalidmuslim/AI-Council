#!/usr/bin/env python3
"""Prepare two explicit Codex Cloud task handoffs without APIs or network.

This utility prepares prompts only. It cannot launch Codex, edit GitHub,
run Flutter, execute generated patches, approve code or merge pull requests.
"""
import argparse
import json
import re
import sys
from pathlib import Path

APPROVED_REPOSITORY = "Xalidmuslim/Arabic-Academy-Flutter"
EXPECTED_FIELDS = frozenset({
    "repository", "issue_url", "base_commit", "objective",
    "allowed_paths", "acceptance", "constraints",
})
ALLOWED_COMMANDS = ("flutter analyze --no-fatal-infos", "flutter test")
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")
ISSUE_RE = re.compile(
    r"https://github\.com/Xalidmuslim/Arabic-Academy-Flutter/issues/([1-9][0-9]*)\Z"
)
FILE_RE = re.compile(r"test/[a-z][a-z0-9_]*_test\.dart\Z")


def validate_task(task):
    """Strict pilot contract: public-only path and pinned immutable source."""
    if not isinstance(task, dict) or set(task) != EXPECTED_FIELDS:
        raise ValueError("Task fields must match the declared contract exactly")
    if task["repository"] != APPROVED_REPOSITORY:
        raise ValueError("Private or unapproved repository")
    url = task["issue_url"]
    if not isinstance(url, str) or not ISSUE_RE.fullmatch(url):
        raise ValueError("Issue URL must be within the approved public repository")
    sha = task["base_commit"]
    if not isinstance(sha, str) or not COMMIT_RE.fullmatch(sha):
        raise ValueError("A full immutable commit SHA is required")
    objective = task["objective"]
    if (not isinstance(objective, str)
            or not 1 <= len(objective.strip()) <= 600
            or "\x00" in objective):
        raise ValueError("Objective is empty or too long")
    paths = task["allowed_paths"]
    if (not isinstance(paths, list) or not 1 <= len(paths) <= 8
            or any(not isinstance(x, str) or not FILE_RE.fullmatch(x) for x in paths)
            or len(set(paths)) != len(paths)):
        raise ValueError("Only unique test/*_test.dart files are allowed")
    if task["acceptance"] != list(ALLOWED_COMMANDS):
        raise ValueError("Commands must be the fixed, non-destructive Flutter checks")
    constraints = task["constraints"]
    if (not isinstance(constraints, list) or not 1 <= len(constraints) <= 10
            or any(not isinstance(x, str) or not 1 <= len(x.strip()) <= 600
                   or "\x00" in x for x in constraints)):
        raise ValueError("Explicit nonempty bounded constraints are required")
    return {
        "repository": task["repository"],
        "issue_url": url,
        "base_commit": sha,
        "objective": objective.strip(),
        "allowed_paths": paths.copy(),
        "acceptance": list(ALLOWED_COMMANDS),
        "constraints": [x.strip() for x in constraints],
    }


def make_handoffs(task):
    """Produce separate programmer and reviewer task prompts, NOT agent runs."""
    t = validate_task(task)
    number = ISSUE_RE.fullmatch(t["issue_url"]).group(1)
    paths_text = "\n".join("- " + p for p in t["allowed_paths"])
    acceptance_text = "\n".join("- " + p for p in t["acceptance"])
    constraints_text = "\n".join("- " + p for p in t["constraints"])
    source = t["repository"]
    pinned = t["base_commit"]
    header = (
        "AI-Council Codex Cloud, no external OpenAI API key.\n"
        "Repository: " + source + "\n"
        "GitHub Issue #" + number + ": " + t["issue_url"] + "\n"
        "Pin your baseline to the exact source commit " + pinned + ".\n"
        "Check live GitHub branch, target AGENTS.md and actual source before any change.\n"
        "Scope is exactly:\n" + paths_text + "\n"
        "Acceptance commands:\n" + acceptance_text + "\n"
        "Constraints:\n" + constraints_text + "\n"
        "Objective: " + t["objective"] + "\n"
    )
    programmer = (
        "# AI-Council · programmer / Codex task\n\n"
        + header
        + "\n1. RECON: inspect actual target repo/branch and source commit; "
          "confirm Issue scope. Do not copy private source into AI-Council.\n"
          "2. Write a regression test first, reproduce RED if behavior changes, "
          "then propose the smallest diff in allowed test files only.\n"
          "3. Run both specified Flutter commands in the authorized target environment. "
          "Show their real exit codes, logs and any Flutter SDK limitations.\n"
          "4. Create a separate branch and draft PR only if the environment has "
          "authorized GitHub write access; never merge into main. "
          "If it cannot push, provide a patch and state that honestly.\n"
          "5. In the draft PR include source SHA, changed paths, issue link, "
          "RED/GREEN evidence, test run URLs and limitations.\n"
          "6. Send the PR URL or patch to a separate Codex task for independent "
          "review. Never claim reviewers or CI ran before they actually do.\n"
    )
    reviewer = (
        "# AI-Council · independent review / separate Codex task\n\n"
        + header
        + "\nThis is a separate Codex task with a fresh context. "
          "Do not reuse the programmer's self-assessment as independent evidence.\n"
          "1. Open the resulting draft PR URL provided by the owner. "
          "If no PR exists, mark NEEDS_CHECK; do not invent one.\n"
          "2. Verify actual base/head commits, complete file diff, all scope "
          "constraints and that all changed paths are authorized.\n"
          "3. Check actual GitHub Actions / Flutter logs and statuses. "
          "If no logs are available, say tests НЕ запускались or evidence unavailable.\n"
          "4. Audit test assertions (avoid tautological checks), existing behavior, "
          "data retention and Arabic text integrity.\n"
          "5. Report VERIFIED / FAILED / NEEDS_CHECK, exact evidence, defects "
          "and residual risks. A reviewer report is not a merge approval.\n"
          "6. Do not change files, push commits, approve the PR or merge main "
          "within this review task.\n"
    )
    return {
        "status": "NEEDS_CHECK",
        "model_calls": 0,
        "external_actions": [],
        "repository": source,
        "issue_url": t["issue_url"],
        "base_commit": pinned,
        "allowed_paths": t["allowed_paths"],
        "acceptance": t["acceptance"],
        "programmer_prompt": programmer,
        "reviewer_prompt": reviewer,
    }


def write_handoffs(result, output_directory):
    """Write artifact drafts; do not fabricate agent output or CI results."""
    root = Path(output_directory)
    root.mkdir(parents=True, exist_ok=True)
    meta = {key: value for key, value in result.items()
            if not key.endswith("_prompt")}
    (root / "handoff.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (root / "programmer.md").write_text(
        result["programmer_prompt"], encoding="utf-8"
    )
    (root / "reviewer.md").write_text(
        result["reviewer_prompt"], encoding="utf-8"
    )
    return ["handoff.json", "programmer.md", "reviewer.md"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task", default="agent_inputs/codex_cloud_pilot_48.json"
    )
    parser.add_argument("--out", default="handoff_reports/codex")
    args = parser.parse_args()
    source = Path(args.task)
    if source.stat().st_size > 16384:
        raise ValueError("Task manifest is oversized")
    task = json.loads(source.read_text(encoding="utf-8"))
    report = make_handoffs(task)
    files = write_handoffs(report, args.out)
    print("Codex no-API handoff: NEEDS_CHECK (no model calls, no network)")
    print("Artifacts:", ", ".join(str(Path(args.out) / path) for path in files))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print("Invalid Codex handoff:", exc, file=sys.stderr)
        sys.exit(1)
