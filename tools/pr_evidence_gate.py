#!/usr/bin/env python3
"""Evidence-only review of an explicitly allowlisted public GitHub draft PR.

No source execution, AI models, write API, approvals or automatic merges.
"""
import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ALLOWED_REPOSITORIES = frozenset({"Xalidmuslim/Arabic-Academy-Flutter"})
ALLOWED_FILES = frozenset({
    "lib/main.dart",
    "pubspec.yaml",
    "test/local_state_failure_test.dart",
    "test/local_state_regression_test.dart",
    ".github/workflows/council-regression.yml",
})
REQUIRED_WORKFLOW = "AI-Council local-data regression (PR)"
REQUIRED_STEPS = frozenset({
    "Static analysis (info-level deprecations visible, errors still fatal)",
    "Test existing features and local data recovery",
})
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
MAX_BYTES = 4 * 1024 * 1024


def _is_sha(value):
    return isinstance(value, str) and SHA_RE.fullmatch(value) is not None


def _preflight(repository, number, expected_sha):
    if repository not in ALLOWED_REPOSITORIES:
        raise ValueError("Repository not allowlisted for public evidence review")
    if not isinstance(number, int) or not (1 <= number <= 1000000):
        raise ValueError("Invalid PR number")
    if not _is_sha(expected_sha):
        raise ValueError("Expected exact full commit SHA")


def evaluate_pr(repository, number, expected_sha, *, get_json):
    """Fail closed on mismatched PR, changed content, stale CI, or incomplete data."""
    _preflight(repository, number, expected_sha)
    base = "https://api.github.com/repos/" + repository
    meta = get_json(base)
    if (not isinstance(meta, dict) or meta.get("full_name") != repository
            or meta.get("private") is not False
            or meta.get("visibility") != "public"):
        raise ValueError("Private or unverified repository cannot be reviewed")

    pr = get_json(base + "/pulls/" + str(number))
    if not isinstance(pr, dict):
        raise ValueError("Missing pull request")
    head = pr.get("head") if isinstance(pr.get("head"), dict) else {}
    target = pr.get("base") if isinstance(pr.get("base"), dict) else {}
    owner = pr.get("user") if isinstance(pr.get("user"), dict) else {}
    if (pr.get("number") != number
            or pr.get("state") != "open"
            or pr.get("draft") is not True
            or head.get("sha") != expected_sha
            or (head.get("repo") or {}).get("full_name") != repository
            or target.get("ref") != "main"
            or not _is_sha(target.get("sha"))
            or owner.get("login") != "Xalidmuslim"):
        raise ValueError("PR identity, head SHA, base, or draft state mismatch")

    report = {
        "repository": repository,
        "pull_request": number,
        "head_sha": expected_sha,
        "base_sha": target["sha"],
        "status": "FAILED",
        "ci_status": "NOT_CHECKED",
        "run_id": None,
        "changed_files": 0,
        "file_paths": [],
        "issues": [],
        "tests_run_by_reviewer": [],
        "arabic_semantic_review": "NOT_PERFORMED",
        "review_limitations": [
            "Workflow reports and step conclusions are metadata, not a code-security audit",
            "Proposed CI workflow is itself within the PR; manual diff review is required",
            "No independent AI reviewer, on-device tests, APK, or automatic merge",
        ],
    }

    files = get_json(base + "/pulls/" + str(number) + "/files?per_page=100")
    count = pr.get("changed_files")
    if (not isinstance(count, int) or isinstance(count, bool)
            or count < 1 or count > 100 or not isinstance(files, list)
            or len(files) != count):
        report["issues"].append("Incomplete or oversized changed file list")
        return report

    paths = []
    for item in files:
        if not isinstance(item, dict):
            report["issues"].append("Invalid changed file metadata")
            continue
        path = item.get("filename")
        status = item.get("status")
        if not isinstance(path, str):
            report["issues"].append("Missing changed file name")
            continue
        paths.append(path)
        if path not in ALLOWED_FILES or status not in ("added", "modified"):
            report["issues"].append("Unapproved changed file: " + path)
    report["file_paths"] = paths
    report["changed_files"] = len(paths)
    if report["issues"]:
        return report

    runs = get_json(base + "/actions/runs?head_sha=" + expected_sha + "&per_page=100")
    if (not isinstance(runs, dict) or not isinstance(runs.get("workflow_runs"), list)
            or not isinstance(runs.get("total_count"), int)
            or runs["total_count"] > 100):
        report["issues"].append("Incomplete workflow run evidence")
        return report
    matches = [
        run for run in runs["workflow_runs"]
        if (isinstance(run, dict)
            and run.get("name") == REQUIRED_WORKFLOW
            and run.get("head_sha") == expected_sha
            and run.get("event") == "pull_request"
            and type(run.get("id")) is int)
    ]
    if not matches:
        report["issues"].append("No matching CI workflow on exact head SHA")
        return report
    latest = max(matches, key=lambda item: item["id"])
    report["run_id"] = latest["id"]
    if latest.get("status") != "completed" or latest.get("conclusion") != "success":
        report["ci_status"] = "FAIL"
        report["issues"].append("Latest matching CI run is not successful")
        return report

    jobs = get_json(base + "/actions/runs/" + str(latest["id"]) + "/jobs?per_page=100")
    if (not isinstance(jobs, dict) or not isinstance(jobs.get("jobs"), list)
            or not isinstance(jobs.get("total_count"), int)
            or jobs["total_count"] > 100):
        report["issues"].append("Incomplete CI job evidence")
        return report

    verified = False
    for job in jobs["jobs"]:
        if not isinstance(job, dict) or job.get("name") != "verify":
            continue
        if job.get("status") != "completed" or job.get("conclusion") != "success":
            continue
        steps = job.get("steps")
        if not isinstance(steps, list):
            continue
        successful = {
            step.get("name")
            for step in steps if isinstance(step, dict) and step.get("conclusion") == "success"
        }
        if REQUIRED_STEPS.issubset(successful):
            verified = True
    if not verified:
        report["ci_status"] = "FAIL"
        report["issues"].append("Required analyzer/test steps were not both successful")
        return report

    report["ci_status"] = "PASS"
    report["status"] = "NEEDS_CHECK"
    return report


def write_report(report, prefix):
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_path = prefix.with_suffix(".json")
    md_path = prefix.with_suffix(".md")
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                         encoding="utf-8")
    rows = [
        "# AI-Council: PR evidence check (read only)", "",
        "Status: **" + report["status"] + "**",
        "Repository: " + report["repository"],
        "Pull request: #" + str(report["pull_request"]),
        "Pinned commit: `" + report["head_sha"] + "`",
        "CI: " + report["ci_status"],
        "Run ID: " + str(report["run_id"]), "",
        "## Changed file paths", "",
    ]
    rows.extend("- " + path for path in report["file_paths"])
    if not report["file_paths"]:
        rows.append("- none validated")
    rows.extend(["", "## Issues", ""])
    rows.extend("- " + issue for issue in report["issues"])
    if not report["issues"]:
        rows.append("- none detected by this limited metadata gate")
    rows.extend(["", "## Evidence limitations", ""])
    rows.extend("- " + line for line in report["review_limitations"])
    rows.extend(["", "Tests executed by this reviewer: NONE. Human review required.", ""])
    md_path.write_text("\n".join(rows), encoding="utf-8")
    return json_path, md_path


def github_get(url):
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "AI-Council-pr-evidence-review"}
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(MAX_BYTES + 1)
            if len(raw) > MAX_BYTES:
                raise ValueError("GitHub API response exceeds size limit")
            return json.loads(raw)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("GitHub API returned HTTP " + str(exc.code)) from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output-prefix", default="review_reports/pr-evidence")
    args = parser.parse_args()
    report = evaluate_pr(
        args.repository, args.pr, args.expected_sha, get_json=github_get)
    json_path, md_path = write_report(report, args.output_prefix)
    print("PR evidence:", report["status"], "CI:", report["ci_status"])
    print("Reports:", json_path, md_path)
    if report["status"] != "NEEDS_CHECK":
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, urllib.error.URLError) as exc:
        print("PR evidence failure:", exc, file=sys.stderr)
        sys.exit(1)
