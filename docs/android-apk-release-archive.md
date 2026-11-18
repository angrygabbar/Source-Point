# Android APK archive workflow

The Android Gradle project stores each built APK and its notes on the codex/android-apk-releases branch, under android-apk-releases/v<VERSION>/<debug-or-release>/. The archive branch keeps APK pushes separate from main, whose push workflow deploys the website.

## Build behavior

The Android project finalizes assembleDebug and assembleRelease by running scripts/publish_android_apk.sh. Before building a new version, update release-notes.md in the Android project directory. The publisher requires non-empty notes, records the APK SHA-256 and signer certificate fingerprint, and pushes only the APK archive, notes, and publisher documentation.

To build without publishing, pass -PSOURCEPOINT_APK_PUBLISH=false. If a push fails, the APK remains in the local Gradle output folder; rerun the publish task after fixing Git access.

Each version is immutable. Bump both VERSION_NAME and VERSION_CODE before replacing an APK. Debug and release APKs for the same version are stored in separate subfolders and share one release-notes file.

## Signing continuity

The first archived APK, v1.3.9, records its signer as the baseline because comparison with the existing website release was deferred at the user's request. Every later APK must have the same signer fingerprint as that baseline; a mismatch stops the archive push. This establishes continuity from v1.3.9 onward, but does not retroactively prove that v1.3.9 matches the older website APK.
