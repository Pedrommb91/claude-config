#!/usr/bin/env bash
# Install or update the paparazzi skill (live agent map) and link it into Claude Code.
#
#   scripts/install-paparazzi.sh             clone or update, then link
#   scripts/install-paparazzi.sh uninstall   remove the link (keeps the checkout)
#
# Env overrides:
#   PAPARAZZI_DIR   checkout location (default ~/Documents/personal/paparazzi)
#   PAPARAZZI_REPO  git URL (default the public GitHub repo over HTTPS)
#   CLAUDE_CONFIG_DIR  Claude Code config dir (default ~/.claude)
set -euo pipefail

REPO="${PAPARAZZI_REPO:-https://github.com/Pedrommb91/paparazzi.git}"
DEST="${PAPARAZZI_DIR:-$HOME/Documents/personal/paparazzi}"
SKILLS="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/skills"
LINK="$SKILLS/paparazzi"
OLD_LINK="$SKILLS/agent-map"  # pre-rename name

die() { echo "error: $*" >&2; exit 1; }

if [[ "${1:-}" == "uninstall" ]]; then
  if [[ -L "$LINK" ]]; then
    rm "$LINK" && echo "removed link $LINK (checkout kept at $DEST)"
  else
    echo "nothing to do: $LINK is not a symlink"
  fi
  exit 0
fi
[[ $# -eq 0 ]] || die "usage: $0 [uninstall]"

command -v git >/dev/null || die "git not found"

if [[ -d "$DEST/.git" ]]; then
  git -C "$DEST" pull --ff-only --quiet || die "could not fast-forward $DEST; resolve it manually"
  echo "updated $DEST"
elif [[ -e "$DEST" && -n "$(ls -A "$DEST")" ]]; then
  die "$DEST exists, is not empty and is not a git checkout"
else
  mkdir -p "$(dirname "$DEST")"
  git clone --quiet "$REPO" "$DEST"
  echo "cloned $REPO into $DEST"
fi
# Block pushes with non-noreply emails (the repo is public)
git -C "$DEST" config core.hooksPath .githooks

if [[ -L "$OLD_LINK" && "$(readlink "$OLD_LINK")" == "$DEST" ]]; then
  rm "$OLD_LINK" && echo "removed old link $OLD_LINK"
fi

mkdir -p "$SKILLS"
if [[ -L "$LINK" ]]; then
  if [[ "$(readlink "$LINK")" == "$DEST" ]]; then
    echo "link ok: $LINK -> $DEST"
    exit 0
  fi
  rm "$LINK"
elif [[ -e "$LINK" ]]; then
  die "$LINK exists and is not a symlink; move it away first"
fi
ln -s "$DEST" "$LINK"
echo "linked $LINK -> $DEST"
echo "run /paparazzi start in Claude Code"
