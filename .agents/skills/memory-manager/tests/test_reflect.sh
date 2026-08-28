#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT="$ROOT/scripts/memory_reflect.py"
FIXTURE=$(mktemp -d "${TMPDIR:-/tmp}/memory-reflect.XXXXXX")
trap 'rm -rf "$FIXTURE"' EXIT HUP INT TERM
MEMORY="$FIXTURE/memory"

AGENT_PROFILE=fixture AGENT_RUN_ID=run-1 python3 "$SCRIPT" --memory-root "$MEMORY" sample action ok --note reflected --evidence proof-a proof-b >/dev/null
python3 "$SCRIPT" --memory-root "$MEMORY" sample failure-a broken --fail >/dev/null
python3 "$SCRIPT" --memory-root "$MEMORY" sample failure-b broken --fail >/dev/null
python3 "$SCRIPT" --memory-root "$MEMORY" sample failure-c broken --fail >/dev/null

EPISODIC="$MEMORY/episodic/AGENT_LEARNINGS.jsonl"
[ "$(wc -l < "$EPISODIC" | tr -d ' ')" = 4 ]
grep -F '"result": "success"' "$EPISODIC" >/dev/null
grep -F '"profile": "fixture"' "$EPISODIC" >/dev/null
grep -F '"evidence_ids": ["proof-a", "proof-b"]' "$EPISODIC" >/dev/null
grep -F '"pain_score": 10' "$EPISODIC" >/dev/null
grep -F 'THIS SKILL HAS FAILED 3 TIMES IN 14d' "$EPISODIC" >/dev/null
echo 'memory-reflect: PASS'
