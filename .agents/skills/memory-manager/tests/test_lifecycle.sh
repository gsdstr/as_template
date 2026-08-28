#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT="$ROOT/scripts/memory_manager.py"
FIXTURE=$(mktemp -d "${TMPDIR:-/tmp}/memory-manager.XXXXXX")
trap 'rm -rf "$FIXTURE"' EXIT HUP INT TERM

python3 "$SCRIPT" --help >/dev/null
PYTHONDONTWRITEBYTECODE=1 python3 -c 'import importlib.util, sys; spec = importlib.util.spec_from_file_location("memory_manager", sys.argv[1]); module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)' "$SCRIPT"

MEMORY="$FIXTURE/memory"
mkdir -p "$MEMORY/semantic"
printf '%s\n' '# Curated preamble' > "$MEMORY/semantic/LESSONS.md"

python3 "$SCRIPT" --memory-root "$MEMORY" stage --id alpha --claim 'Serialize timestamps in UTC across service boundaries' --evidence run-1 --reviewer test >/dev/null
candidate_before=$(cksum "$MEMORY/candidates/alpha.json")
python3 "$SCRIPT" --memory-root "$MEMORY" accept alpha --reviewer test --rationale 'Repeated evidence' >/dev/null
python3 "$SCRIPT" --memory-root "$MEMORY" search 'timestamps UTC' | grep -F 'semantic/lesson_alpha' >/dev/null
python3 "$SCRIPT" --memory-root "$MEMORY" stage --id beta --claim 'Validate memory lifecycle transitions in a temporary fixture' --reviewer test >/dev/null
python3 "$SCRIPT" --memory-root "$MEMORY" reject beta --reviewer test --reason 'Need more evidence'
python3 "$SCRIPT" --memory-root "$MEMORY" reopen beta --reviewer test
python3 "$SCRIPT" --memory-root "$MEMORY" reject beta --reviewer test --reason 'Still insufficient evidence'

before=$(wc -l < "$MEMORY/semantic/lessons.jsonl")
python3 "$SCRIPT" --memory-root "$MEMORY" retract lesson_alpha --reviewer test --rationale 'Fixture retraction' >/dev/null
after=$(wc -l < "$MEMORY/semantic/lessons.jsonl")
[ "$after" -gt "$before" ]

python3 "$SCRIPT" --memory-root "$MEMORY" render --adopt-existing >/dev/null
grep -F '# Curated preamble' "$MEMORY/semantic/LESSONS.md" >/dev/null
grep -F 'memory-manager:generated' "$MEMORY/semantic/LESSONS.md" >/dev/null
! grep -F 'Serialize timestamps in UTC across service boundaries' "$MEMORY/semantic/LESSONS.md" >/dev/null

[ "$(wc -l < "$MEMORY/candidates/events.jsonl")" -eq 6 ]
[ "$candidate_before" = "$(cksum "$MEMORY/candidates/alpha.json")" ]
grep -F '"action": "rejected"' "$MEMORY/candidates/events.jsonl" >/dev/null
grep -F '"status": "retracted"' "$MEMORY/semantic/lessons.jsonl" >/dev/null

printf '{"memory_root":"%s"}\n' "$MEMORY" > "$FIXTURE/config.json"
python3 "$SCRIPT" --config "$FIXTURE/config.json" list | grep -F 'alpha' >/dev/null

echo 'memory-manager lifecycle: PASS'
