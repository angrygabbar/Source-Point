#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: $0 APK VERSION_NAME VERSION_CODE BUILD_VARIANT RELEASE_NOTES_FILE" >&2
  exit 2
}

[[ $# -eq 5 ]] || usage

apk_file=$1
version_name=$2
version_code=$3
build_variant=$4
notes_file=$5
script_dir="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(git -C "$script_dir/.." rev-parse --show-toplevel)"
remote_name="${SOURCEPOINT_APK_REMOTE:-origin}"
artifact_branch="${SOURCEPOINT_APK_BRANCH:-codex/android-apk-releases}"
skip_certificate_check="${SOURCEPOINT_SKIP_CERT_CHECK:-0}"

fail() {
  echo "Android APK archive: $*" >&2
  exit 1
}

[[ -f "$apk_file" ]] || fail "APK not found: $apk_file"
[[ "$version_name" =~ ^[0-9][A-Za-z0-9._-]*$ ]] || fail "Invalid version name: $version_name"
[[ "$version_code" =~ ^[0-9]+$ ]] || fail "Version code must be numeric."
[[ "$build_variant" == "debug" || "$build_variant" == "release" ]] || fail "Variant must be debug or release."
[[ -f "$notes_file" ]] || fail "Release notes are missing: $notes_file"
[[ -n "$(tr -d '[:space:]' < "$notes_file")" ]] || fail "Release notes are empty: $notes_file"
[[ "$artifact_branch" != "main" ]] || fail "APK artifacts must not be pushed to main because that branch deploys the website."
git -C "$repo_root" remote get-url "$remote_name" >/dev/null 2>&1 || fail "Git remote '$remote_name' is not configured."

sdk_root="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-$HOME/Library/Android/sdk}}"
apksigner_bin="$(command -v apksigner || true)"
if [[ -z "$apksigner_bin" ]]; then
  for candidate in "$sdk_root"/build-tools/*/apksigner; do
    if [[ -x "$candidate" ]]; then
      apksigner_bin=$candidate
    fi
  done
fi
[[ -x "$apksigner_bin" ]] || fail "apksigner is required to record and verify APK signing certificates."

signer_output="$("$apksigner_bin" verify --print-certs "$apk_file")" || fail "APK signature verification failed."
certificate_hashes="$(printf '%s\n' "$signer_output" | awk '/certificate SHA-256 digest:/ { print tolower($NF) }' | sort -u | paste -sd, -)"
[[ -n "$certificate_hashes" ]] || fail "Could not read an APK signing certificate."

if command -v shasum >/dev/null 2>&1; then
  apk_hash="$(shasum -a 256 "$apk_file" | awk '{ print $1 }')"
else
  apk_hash="$(sha256sum "$apk_file" | awk '{ print $1 }')"
fi

remote_url="$(git -C "$repo_root" config --get "remote.$remote_name.url" || true)"
[[ -n "$remote_url" ]] || fail "Could not read the Git URL for remote '$remote_name'."
cache_dir="${TMPDIR:-/tmp}/sourcepoint-apk-release-repo-$(id -u)"
if [[ -e "$cache_dir" && ! -d "$cache_dir/.git" ]]; then
  fail "The release cache path exists but is not a Git clone: $cache_dir"
fi
if [[ ! -d "$cache_dir/.git" ]]; then
  git clone --quiet --depth 1 --branch main --single-branch --origin "$remote_name" "$remote_url" "$cache_dir"
fi

if git ls-remote --exit-code --heads "$remote_url" "refs/heads/$artifact_branch" >/dev/null 2>&1; then
  git -C "$cache_dir" fetch --quiet --depth 1 "$remote_name" "refs/heads/$artifact_branch"
  git -C "$cache_dir" checkout --quiet -B "$artifact_branch" FETCH_HEAD
else
  git ls-remote --exit-code --heads "$remote_url" refs/heads/main >/dev/null 2>&1 || fail "Could not read the remote main branch."
  git -C "$cache_dir" fetch --quiet --depth 1 "$remote_name" refs/heads/main
  git -C "$cache_dir" checkout --quiet -B "$artifact_branch" FETCH_HEAD
fi
git -C "$cache_dir" reset --quiet --hard FETCH_HEAD
worktree_path="$cache_dir"

release_root="$worktree_path/android-apk-releases"
release_dir="$release_root/v$version_name"
variant_dir="$release_dir/$build_variant"
apk_name="SourcePoint_$version_name.apk"
archived_apk="$variant_dir/$apk_name"
baseline_file="$release_root/SIGNING_BASELINE.txt"

verification_status="verified against prior archived APK"
baseline_version_name=""
baseline_version_code=0
if [[ -f "$baseline_file" ]]; then
  baseline_version_name="$(sed -n 's/^version_name=//p' "$baseline_file" | head -1)"
  baseline_version_code="$(sed -n 's/^version_code=//p' "$baseline_file" | head -1)"
  prior_hash="$(sed -n 's/^certificate_sha256=//p' "$baseline_file" | head -1)"
  [[ -n "$prior_hash" && "$baseline_version_code" =~ ^[0-9]+$ ]] || fail "Signing baseline is malformed: $baseline_file"
  if (( version_code < baseline_version_code )); then
    fail "Version code $version_code is older than the signing baseline code $baseline_version_code."
  fi
  if [[ "$skip_certificate_check" != "1" && "$certificate_hashes" != "$prior_hash" ]]; then
    fail "APK signer does not match the archived baseline (expected $prior_hash, got $certificate_hashes); nothing was pushed."
  fi
  if [[ "$skip_certificate_check" == "1" ]]; then
    verification_status="certificate comparison explicitly deferred"
  elif (( version_code == baseline_version_code )) && [[ "$version_name" == "$baseline_version_name" ]]; then
    verification_status="matches archived v$baseline_version_name baseline; original website comparison remains deferred"
  elif (( version_code == baseline_version_code )); then
    fail "Version code $version_code is already assigned to v$baseline_version_name."
  else
    verification_status="verified against archived v$baseline_version_name"
  fi
else
  [[ "$skip_certificate_check" == "1" ]] || fail "No signing baseline exists. The first archive must explicitly defer comparison."
  verification_status="initial baseline; comparison with the then-active website APK was deferred"
fi

mkdir -p "$variant_dir" "$worktree_path/scripts" "$worktree_path/docs"
notes_destination="$release_dir/RELEASE_NOTES.md"
if [[ -f "$notes_destination" ]]; then
  cmp -s "$notes_file" "$notes_destination" || fail "Release notes for v$version_name are already archived and differ; use a new version."
else
  cp "$notes_file" "$notes_destination"
fi

if [[ -f "$archived_apk" ]]; then
  if command -v shasum >/dev/null 2>&1; then
    prior_apk_hash="$(shasum -a 256 "$archived_apk" | awk '{ print $1 }')"
  else
    prior_apk_hash="$(sha256sum "$archived_apk" | awk '{ print $1 }')"
  fi
  [[ "$prior_apk_hash" == "$apk_hash" ]] || fail "v$version_name/$build_variant is immutable; bump the app version before replacing its APK."
else
  cp "$apk_file" "$archived_apk"
fi

{
  printf 'version_name=%s\n' "$version_name"
  printf 'version_code=%s\n' "$version_code"
  printf 'build_variant=%s\n' "$build_variant"
  printf 'apk_sha256=%s\n' "$apk_hash"
  printf 'certificate_sha256=%s\n' "$certificate_hashes"
  printf 'certificate_check=%s\n' "$verification_status"
} > "$variant_dir/BUILD_INFO.txt"
printf '%s  %s\n' "$apk_hash" "$apk_name" > "$variant_dir/SHA256SUMS.txt"

if [[ ! -f "$baseline_file" || "$skip_certificate_check" == "1" || "$version_code" -gt "$baseline_version_code" ]]; then
  cat > "$baseline_file" <<EOF
version_name=$version_name
version_code=$version_code
certificate_sha256=$certificate_hashes
comparison_status=$verification_status
EOF
fi

cp "$script_dir/publish_android_apk.sh" "$worktree_path/scripts/publish_android_apk.sh"
chmod +x "$worktree_path/scripts/publish_android_apk.sh"
if [[ -f "$script_dir/../docs/android-apk-release-archive.md" ]]; then
  cp "$script_dir/../docs/android-apk-release-archive.md" "$worktree_path/docs/android-apk-release-archive.md"
fi
cat > "$release_root/README.md" <<'EOF'
# SourcePoint Android APK archive

This folder stores versioned Android APKs and their release notes. See the repository documentation for the build and signing workflow.
EOF

git -C "$worktree_path" add -- \
  "android-apk-releases/README.md" \
  "android-apk-releases/SIGNING_BASELINE.txt" \
  "android-apk-releases/v$version_name" \
  "scripts/publish_android_apk.sh" \
  "docs/android-apk-release-archive.md"
if git -C "$worktree_path" diff --cached --quiet; then
  echo "v$version_name ($build_variant) is already archived on $artifact_branch; no push was needed."
  exit 0
fi

git_name="$(git -C "$repo_root" config user.name || true)"
git_email="$(git -C "$repo_root" config user.email || true)"
[[ -n "$git_name" && -n "$git_email" ]] || fail "Git author name/email must be configured before publishing."
git -C "$worktree_path" -c user.name="$git_name" -c user.email="$git_email" \
  commit -m "Archive SourcePoint Android v$version_name ($build_variant)" --quiet
git -C "$worktree_path" push "$remote_name" "HEAD:refs/heads/$artifact_branch"
echo "Published android-apk-releases/v$version_name/$build_variant/$apk_name to $remote_name/$artifact_branch."
