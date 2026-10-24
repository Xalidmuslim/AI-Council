# Native Android / Flutter safety rules

1. **Recon first:** before edits, inspect the actual GitHub repository, active branch/commit, modules, Gradle configs, manifests, screens, navigation and tests. If inaccessible, state so.
2. **Preserve the stack:** Kotlin/Jetpack Compose remains Kotlin/Compose; Flutter remains Flutter. The upstream Replica web defaults (Next.js, Tailwind, Expo) are not mandates.
3. **Preserve accepted work:** keep bundled books, Arabic/Russian translations, screenshots, trademarks/licences, bookmarks, reading positions, settings, user data and previous UI/performance optimizations.
4. **Minimal diffs:** reproduce a bug first, write a regression test, fix only the affected code, run adjacent tests, inspect before/after.
5. **Design:** use approved reference screenshots, measured typography, layout and states. Do not change unrelated assets or user-approved 3D styles.
6. **Performance:** baseline frame time, jank, recompositions, cold start and scroll traces on a real device (Perfetto/Macrobenchmark or Android Studio). Refresh rate alone does not prove app FPS. Never promise 120 FPS.
7. **Release:** run release build, verify actual APK/AAB existence and installability, signing and key user flows. Never say "ready APK" without a checked artifact.
8. **Truthfulness/security:** distinguish observations from guesses, report untested risks, never reveal secrets or access private third-party resources. Do not claim a multi-agent consultation unless agents actually ran.
9. **Scope:** existing user-owned applications may be inspected and edited with permission; unrelated third-party replication must use clean-room techniques and respect licences.
