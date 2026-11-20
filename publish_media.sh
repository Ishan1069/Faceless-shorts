#!/usr/bin/env bash
# Publish today's video (+ cover) as the only content of the `media` branch, force-pushed,
# so the repo never accumulates video history. Prints public raw URLs.
set -e
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
TMP=$(mktemp -d)
cp "$@" "$TMP/"
cd "$TMP"
git init -q -b media
git config user.email "faceless-bot@users.noreply.github.com"
git config user.name "faceless-shorts bot"
git add -A
git commit -q -m "media $(date +%F)"
git remote add origin "$(git -C "$REPO_DIR" remote get-url origin)"
git push -q -f origin media
for f in "$@"; do
  echo "https://raw.githubusercontent.com/Ishan1069/Faceless-shorts/media/$(basename "$f")"
done
rm -rf "$TMP"
