#!/usr/bin/env python3
"""Read-only, public-only repository inventory and three-role handoff.

This is deterministic source metadata gathering, NOT an AI agent or build runner.
Never reads private repositories and never sends source contents to a model.
"""
import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ALLOWED_REPOSITORIES = frozenset({"Xalidmuslim/Arabic-Academy-Flutter"})
SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
REF_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,127}\Z")
PATH_RE = re.compile(r"[A-Za-z0-9._/-]{1,255}\Z")
MAX_PATHS = 10000
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
TEST_LIMIT = 40
CONTENT_LIMIT = 25
WORKFLOW_LIMIT = 20


def validate_ref(ref):
    if (not isinstance(ref, str) or not REF_RE.fullmatch(ref)
            or ".." in ref or "//" in ref or ref.endswith(("/", ".", ".lock"))):
        raise ValueError("Unsafe or empty Git ref")
    return ref


def validate_repo(repository, allowed_repositories):
    if not isinstance(repository, str) or repository not in allowed_repositories:
        raise ValueError("Repository is not in public allowlist")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise ValueError("Invalid repository name")
    return repository


def public_manifest(entries):
    if not isinstance(entries, list) or len(entries) > MAX_PATHS:
        raise ValueError("Missing or excessive repository tree")
    paths = set()
    for item in entries:
        if not isinstance(item, dict) or item.get("type") != "blob":
            continue
        path = item.get("path")
        if (isinstance(path, str) and PATH_RE.fullmatch(path)
                and ".." not in path.split("/") and not path.startswith("/")):
            paths.add(path)
    return sorted(paths)


def inspect_repository(repository, ref, *, get_json, allowed_repositories=None):
    """Fetch only GitHub repository metadata, resolved SHA, and file paths."""
    allow = ALLOWED_REPOSITORIES if allowed_repositories is None else allowed_repositories
    validate_repo(repository, allow)
    validate_ref(ref)
    base = "https://api.github.com/repos/" + repository
    metadata = get_json(base)
    if (not isinstance(metadata, dict)
            or metadata.get("full_name") != repository
            or metadata.get("private") is not False
            or metadata.get("visibility") != "public"):
        raise ValueError("Only explicitly allowlisted public repositories are supported")

    resolved = get_json(base + "/commits/" + urllib.parse.quote(ref, safe=""))
    sha = resolved.get("sha") if isinstance(resolved, dict) else None
    if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
        raise ValueError("GitHub did not return a valid pinned commit SHA")

    tree = get_json(base + "/git/trees/" + sha + "?recursive=1")
    if not isinstance(tree, dict) or tree.get("truncated") is not False:
        raise ValueError("GitHub tree is truncated or missing")
    paths = public_manifest(tree.get("tree"))
    files = set(paths)
    stack = ("Flutter" if "pubspec.yaml" in files else
             "Android/Gradle" if any(x in files for x in (
                 "settings.gradle", "settings.gradle.kts", "build.gradle",
                 "build.gradle.kts")) else "Unknown")
    instructions = [
        p for p in paths
        if p in ("AGENTS.md", "CLAUDE.md", "ANDROID_PLAYBOOK.md")
        or p.endswith("/AGENTS.md")
    ][:20]
    tests = [
        p for p in paths
        if (p.startswith(("test/", "tests/"))
            or "/src/test/" in "/" + p
            or "/src/androidTest/" in "/" + p)
    ][:TEST_LIMIT]
    workflows = [p for p in paths if p.startswith(".github/workflows/")][:WORKFLOW_LIMIT]
    content = [
        p for p in paths
        if p.startswith(("assets/", "res/raw/", "src/main/assets/"))
        and p.lower().endswith((".json", ".arb", ".xml", ".txt", ".md", ".yaml"))
    ][:CONTENT_LIMIT]
    handoff = []
    for role, objective in (
        ("programmer", "Read the pinned source tree and its instructions; map modules and propose minimal diff and tests."),
        ("arabist", "Check the supplied primary Arabic source against relevant content; do not infer diacritics."),
        ("tester", "Review test inventory and any proposed diff; require real test logs, CI and device measurements."),
    ):
        handoff.append({
            "role": role,
            "repository": repository,
            "commit_sha": sha,
            "requested_ref": ref,
            "objective": objective,
            "tests_run": [],
            "status": "NEEDS_CHECK",
        })
    return {
        "status": "NEEDS_CHECK",
        "repository": repository,
        "requested_ref": ref,
        "commit_sha": sha,
        "repository_url": "https://github.com/" + repository + "/tree/" + sha,
        "stack": stack,
        "files_count": len(paths),
        "instructions": instructions,
        "tests": tests,
        "workflows": workflows,
        "content_candidates": content,
        "tests_run": [],
        "source_content_collected": False,
        "handoff": handoff,
        "limitations": [
            "Metadata inventory only; no code or content was downloaded",
            "No Android/Flutter tests, build, device profiling, translation or AI model ran",
            "Target code must be opened and checked in its own authorized environment",
            "Private repositories cannot be processed via public AI-Council artifacts",
        ],
    }


def render_markdown(report):
    lines = [
        "# AI-Council: read-only repository intake", "",
        "Status: NEEDS_CHECK", "",
        "Repository: " + report["repository"],
        "Requested ref: " + report["requested_ref"],
        "Pinned commit: " + report["commit_sha"],
        "Repository URL: " + report["repository_url"],
        "Detected stack: " + report["stack"],
        "Discovered file paths: " + str(report["files_count"]), "",
    ]
    for key, heading in (
        ("instructions", "Instructions to inspect first"),
        ("tests", "Existing test paths (NOT executed)"),
        ("workflows", "CI workflows (NOT executed)"),
        ("content_candidates", "Potential content paths (NOT checked)"),
    ):
        lines.extend(["## " + heading, ""])
        lines.extend("- " + x for x in report[key])
        if not report[key]:
            lines.append("- none discovered")
        lines.append("")
    lines.extend(["## Hand-off plan", ""])
    for task in report["handoff"]:
        lines.append("- " + task["role"] + ": " + task["objective"])
    lines.extend([
        "", "## Evidence boundary", "",
        "Tests: не запускались. APK: не собирался. FPS: не измерялся.",
        "Source content: not downloaded. Model calls: none.",
        "No source changes, PR, deployments or private source exports.", "",
    ])
    return "\n".join(lines)


def write_report(report, prefix):
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_file = prefix.with_suffix(".json")
    md_file = prefix.with_suffix(".md")
    json_file.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    md_file.write_text(render_markdown(report), encoding="utf-8")
    return json_file, md_file


def github_get_json(url):
    # URLs come from validated repo, ref and pinned SHA only.
    headers = {"Accept": "application/vnd.github+json",
               "User-Agent": "AI-Council-public-repo-intake"}
    token = os.environ.get("GITHUB_TOKEN", "")
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=25) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
            if len(payload) > MAX_RESPONSE_BYTES:
                raise ValueError("Oversized GitHub API response")
            return json.loads(payload)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("GitHub API failed: HTTP " + str(exc.code)) from None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--output-prefix", default="intake_reports/repository-intake")
    args = parser.parse_args()
    report = inspect_repository(args.repository, args.ref, get_json=github_get_json)
    json_file, md_file = write_report(report, args.output_prefix)
    print("NEEDS_CHECK: metadata saved to", json_file, "and", md_file)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError) as exc:
        print("Repository intake failed:", exc, file=sys.stderr)
        sys.exit(1)
