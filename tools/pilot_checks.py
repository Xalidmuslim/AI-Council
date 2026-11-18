#!/usr/bin/env python3
"""Read-only, pinned source inspection for an AI-Council pilot.

This script DOES NOT call an AI model, edit the target, or claim linguistic correctness.
It must run against a checked-out Git commit supplied independently by the workflow.
"""
import argparse
import hashlib
import json
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
ARABIC_RANGE = range(0x0600, 0x0700)
BIDI_CONTROLS = {"LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI"}
MAX_CONTENT_BYTES = 1_000_000


def actual_head(root):
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        text=True, timeout=12,
    ).strip()


def verify_checkout(root, expected_sha, get_head=actual_head):
    if not isinstance(expected_sha, str) or not SHA_RE.fullmatch(expected_sha):
        raise ValueError("Invalid expected commit SHA")
    root = Path(root).resolve()
    head = get_head(root)
    if head != expected_sha:
        raise ValueError("Checked out commit does not match expected commit")
    if not root.is_dir():
        raise ValueError("Repository root is not a directory")
    return root


def read_content(root):
    source = root / "assets" / "content" / "level1.json"
    if not source.is_file() or source.is_symlink():
        raise ValueError("Missing or unsafe public draft content")
    if source.stat().st_size > MAX_CONTENT_BYTES:
        raise ValueError("Draft content is too large")
    data = source.read_bytes()
    try:
        catalog = json.loads(data.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("Arabic content must be valid UTF-8 JSON") from exc
    if not isinstance(catalog, dict):
        raise ValueError("Draft content must be a JSON object")
    return catalog, hashlib.sha256(data).hexdigest()


def inspect_programmer(root, expected_sha, *, get_head=actual_head):
    root = verify_checkout(root, expected_sha, get_head)
    catalog, digest = read_content(root)
    if not (root / "pubspec.yaml").is_file():
        raise ValueError("Not a Flutter project: pubspec.yaml missing")
    tests = sorted(p.relative_to(root).as_posix()
                   for p in (root / "test").rglob("*.dart")
                   if p.is_file() and not p.is_symlink()) if (root / "test").is_dir() else []
    instructions = [p for p in ("AGENTS.md", "CLAUDE.md", "ANDROID_PLAYBOOK.md")
                    if (root / p).is_file() and not (root / p).is_symlink()]
    workflows = sorted(p.relative_to(root).as_posix()
                       for p in (root / ".github" / "workflows").glob("*.yml")
                       if p.is_file() and not p.is_symlink()) if (root / ".github/workflows").is_dir() else []
    modules = catalog.get("modules")
    lessons = catalog.get("lessons")
    return {
        "role": "programmer",
        "status": "NEEDS_CHECK",
        "commit_sha": expected_sha,
        "stack": "Flutter",
        "instructions_found": instructions,
        "tests_found": tests,
        "workflows_found": workflows,
        "content_path": "assets/content/level1.json",
        "content_sha256": digest,
        "module_count": len(modules) if isinstance(modules, list) else None,
        "lesson_count": len(lessons) if isinstance(lessons, list) else None,
        "tests_run": [],
        "source_modified": False,
        "limitations": [
            "Read-only structural inventory; no fixes or app builds",
            "Programmer AI agent has not run",
        ],
    }


def _check_arabic(value, location, errors):
    if not isinstance(value, str) or not value.strip():
        errors.append(location + ": missing Arabic text")
        return
    if "\ufffd" in value:
        errors.append(location + ": Unicode replacement character found")
    if any(unicodedata.bidirectional(ch) in BIDI_CONTROLS for ch in value):
        errors.append(location + ": bidi control character found")
    if any(ord(ch) < 32 and ch not in "\t\n" for ch in value):
        errors.append(location + ": forbidden control character found")
    if not any(ord(ch) in ARABIC_RANGE and unicodedata.category(ch).startswith("L")
               for ch in value):
        errors.append(location + ": no Arabic letter found")
    last_arabic_base = False
    for ch in value:
        category = unicodedata.category(ch)
        if category.startswith("M") and not last_arabic_base:
            errors.append(location + ": combining mark without preceding Arabic letter")
            break
        if category.startswith("L"):
            last_arabic_base = ord(ch) in ARABIC_RANGE
        elif category.startswith("Z") or category.startswith("P") or category.startswith("C"):
            last_arabic_base = False


def inspect_arabist(root, expected_sha, *, get_head=actual_head):
    root = verify_checkout(root, expected_sha, get_head)
    catalog, digest = read_content(root)
    errors = []
    checked = 0
    modules = catalog.get("modules")
    lessons = catalog.get("lessons")
    if not isinstance(modules, list) or not modules:
        errors.append("modules: expected non-empty list")
        modules = []
    if not isinstance(lessons, list) or not lessons:
        errors.append("lessons: expected non-empty list")
        lessons = []

    seen_module_ids = set()
    for i, m in enumerate(modules):
        if not isinstance(m, dict):
            errors.append(f"modules[{i}]: expected object")
            continue
        mid = m.get("id")
        if not isinstance(mid, str) or not mid or mid in seen_module_ids:
            errors.append(f"modules[{i}].id: missing or duplicate identifier")
        else:
            seen_module_ids.add(mid)
        _check_arabic(m.get("title_ar"), f"modules[{i}].title_ar", errors)
        checked += 1
    seen_lesson_ids = set()
    for i, lesson in enumerate(lessons):
        location = f"lessons[{i}]"
        if not isinstance(lesson, dict):
            errors.append(location + ": expected object")
            continue
        lid = lesson.get("id")
        if not isinstance(lid, str) or not lid or lid in seen_lesson_ids:
            errors.append(location + ".id: missing or duplicate identifier")
        else:
            seen_lesson_ids.add(lid)
        _check_arabic(lesson.get("title_ar"), location + ".title_ar", errors)
        checked += 1
        for section in ("dialogue", "vocabulary"):
            rows = lesson.get(section)
            if not isinstance(rows, list) or not rows:
                errors.append(location + "." + section + ": expected non-empty list")
                continue
            for j, entry in enumerate(rows):
                if not isinstance(entry, dict):
                    errors.append(f"{location}.{section}[{j}]: expected object")
                    continue
                _check_arabic(entry.get("ar"), f"{location}.{section}[{j}].ar", errors)
                checked += 1
        options = lesson.get("options")
        answer = lesson.get("correct")
        if not isinstance(options, list) or not options or not all(
                isinstance(item, str) and item.strip() for item in options):
            errors.append(location + ".options: invalid quiz choices")
        if not isinstance(answer, int) or isinstance(answer, bool) or (
                isinstance(options, list) and not (0 <= answer < len(options))):
            errors.append(location + ".correct: invalid answer index")
    return {
        "role": "arabist",
        "status": "FAILED" if errors else "NEEDS_CHECK",
        "structural_status": "FAIL" if errors else "PASS",
        "semantic_status": "NOT_CHECKED",
        "commit_sha": expected_sha,
        "content_path": "assets/content/level1.json",
        "content_sha256": digest,
        "arabic_fields_checked": checked,
        "module_count": len(modules),
        "lesson_count": len(lessons),
        "errors": errors,
        "tests_run": [],
        "source_modified": False,
        "limitations": [
            "Unicode, field structure and indices only; no source-level Arabic philology",
            "Diacritics and translations not validated against a primary source",
            "No Arabist AI model ran; human review still required",
        ],
    }


def write_report(result, prefix):
    prefix = Path(prefix)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    json_file = prefix.with_suffix(".json")
    md_file = prefix.with_suffix(".md")
    json_file.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                         encoding="utf-8")
    lines = [
        "# AI-Council pilot: " + result["role"], "",
        "Status: **" + result["status"] + "**",
        "Pinned commit: `" + result["commit_sha"] + "`",
        "Content SHA256: `" + result["content_sha256"] + "`",
        "Tests: **not run by this script**",
        "Semantic Arabic review: **not performed**",
        "",
    ]
    if result["role"] == "programmer":
        for label, key in (
            ("Instructions", "instructions_found"),
            ("Test files (not executed)", "tests_found"),
            ("Workflows (not executed)", "workflows_found"),
        ):
            lines.extend(["## " + label, ""])
            lines.extend("- " + x for x in result[key])
            if not result[key]:
                lines.append("- none")
            lines.append("")
    else:
        lines.extend([
            "Unicode / JSON structural status: " + result["structural_status"],
            "Arabic fields inspected: " + str(result["arabic_fields_checked"]),
            "",
            "## Structural problems", "",
        ])
        lines.extend("- " + x for x in result["errors"])
        if not result["errors"]:
            lines.append("- none detected")
    lines.extend(["", "## Limitations", ""])
    lines.extend("- " + x for x in result["limitations"])
    lines.append("")
    md_file.write_text("\n".join(lines), encoding="utf-8")
    return json_file, md_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--role", choices=("programmer", "arabist"), required=True)
    parser.add_argument("--root", required=True)
    parser.add_argument("--expected-sha", required=True)
    parser.add_argument("--output-prefix", required=True)
    args = parser.parse_args()
    if args.role == "programmer":
        result = inspect_programmer(args.root, args.expected_sha)
    else:
        result = inspect_arabist(args.root, args.expected_sha)
    json_file, md_file = write_report(result, args.output_prefix)
    print("AI-Council", args.role, result["status"], str(json_file), str(md_file))
    if result["status"] == "FAILED":
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        print("AI-Council pilot failed:", exc, file=sys.stderr)
        sys.exit(1)
