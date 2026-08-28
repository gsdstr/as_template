#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FIXTURE=$(mktemp -d "${TMPDIR:-/tmp}/memory-auto-dream.XXXXXX")
trap 'rm -rf "$FIXTURE"' EXIT HUP INT TERM
MEMORY="$FIXTURE/memory"
mkdir -p "$MEMORY/episodic"
printf '%s\n' '{"timestamp":"one","action":"repeat UTC conversion service","salience":4}' '{"timestamp":"two","reflection":"repeat UTC conversion service","salience":4}' > "$MEMORY/episodic/AGENT_LEARNINGS.jsonl"
python3 "$ROOT/scripts/run_dream.py" --memory-root "$MEMORY" --threshold 1 | grep -F 'apply=false' >/dev/null
[ ! -d "$MEMORY/candidates" ]
python3 "$ROOT/scripts/run_dream.py" --memory-root "$MEMORY" --threshold 1 --apply | grep -F 'staged=1 apply=true' >/dev/null
[ -f "$MEMORY/candidates/events.jsonl" ]
echo 'memory-auto-dream: PASS'
