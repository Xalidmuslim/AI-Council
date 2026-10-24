---
name: ai-council-router
description: "Automatically select the relevant Replica engineering skills when the user asks to develop, fix, inspect, redesign, test, benchmark, or build Android/Flutter/software applications. Supports Russian requests: приложение, баг, исправь, редизайн, прокрутка, анимация, FPS, APK, проверь. Invoke implicitly only for programming and app work, never for unrelated requests."
---

# AI-Council automatic skill router

No user-written slash command required. Inspect the actual request and choose **only the necessary skills**. This is not a background service and does not run without an agent processing a task.

| User request | Skills |
| --- | --- |
| Open the latest app, inspect an existing source tree | replica-recon |
| Redesign UI / match approved reference | replica-recon, replica-design, replica-diff |
| Fix crashes, wrong navigation, back gesture, scroll bug | replica-recon, replica-test, replica-build, replica-diff |
| Jank, scroll smoothness, cold launch, frames/FPS | replica-recon, replica-test, replica-diff plus device profiler |
| New application or substantial feature | replica-architect, replica-build, replica-test |
| Server/API/auth/integrations | replica-backend, replica-test |
| Compare feature coverage or before/after | replica-diff |
| Real user reviews and market gaps | replica-entrepreneur |
| Naming/branding/store launch/release | replica-brand, replica-launch, replica-deploy when explicitly relevant |

Before acting on existing Android/Flutter apps, read ANDROID_PLAYBOOK.md and the current project's own instructions. Inspect code, branch, tests and references. Never convert Kotlin/Jetpack Compose to web or rewrite Flutter without justification. Preserve data, books, translations, bookmarks, reading position and working optimizations. Measure frame times on an actual device; a 120 Hz screen does not prove 120 FPS. Claim APK only after a real build and artifact verification. Do not invent independent reviewers or approvals.
