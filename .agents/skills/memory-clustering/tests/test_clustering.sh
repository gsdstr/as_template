#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FIXTURE=$(mktemp -d "${TMPDIR:-/tmp}/memory-clustering.XXXXXX")
trap 'rm -rf "$FIXTURE"' EXIT HUP INT TERM
printf '%s\n' '{"timestamp":"one","action":"serialize timestamps UTC service","salience":4}' '{"timestamp":"two","reflection":"serialize timestamps UTC service","salience":5}' > "$FIXTURE/in.jsonl"
python3 "$ROOT/scripts/cluster_patterns.py" --input "$FIXTURE/in.jsonl" --output "$FIXTURE/out.json"
grep -F '"cluster_size": 2' "$FIXTURE/out.json" >/dev/null
echo 'memory-clustering: PASS'
