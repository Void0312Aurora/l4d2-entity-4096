#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: capture_demo.sh --output FILE [--display DISPLAY] [--duration SECONDS]

This is a guarded recorder template. It does not launch, stop, or modify the
game. Start the already prepared private server/client yourself, then run the
recorder and follow docs/demo/storyboard.md.
EOF
}

out=
display=${DISPLAY:-}
duration=90
while (($#)); do
  case "$1" in
    --output) out=${2:?missing output path}; shift 2 ;;
    --display) display=${2:?missing display}; shift 2 ;;
    --duration) duration=${2:?missing duration}; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown option: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ -n "$out" ]] || { echo "--output is required" >&2; exit 2; }
command -v ffmpeg >/dev/null || { echo "ffmpeg is required" >&2; exit 2; }
[[ -n "$display" ]] || {
  echo "no display source is configured; use --display for an X11 display" >&2
  echo "Wayland/PipeWire capture must be configured by the operator." >&2
  exit 3
}

mkdir -p "$(dirname "$out")"
echo "Recording an already-running private client for ${duration}s from DISPLAY=${display}."
echo "No game process will be launched or stopped by this script."
exec ffmpeg -y -f x11grab -framerate 30 -video_size 1280x720 -i "${display}" \
  -t "$duration" -c:v libx264 -preset veryfast -pix_fmt yuv420p "$out"
