#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
SCRIPT="$ROOT/scripts/audit_runtime.py"
FIXTURE=$(mktemp -d "${TMPDIR:-/tmp}/memory-runtime-cleanup.XXXXXX")
trap 'rm -rf "$FIXTURE"' EXIT HUP INT TERM
mkdir -p "$FIXTURE/.agents/memory/semantic"
mkdir -p "$FIXTURE/.agents/skills/memory-manager/scripts" "$FIXTURE/.agents/skills/memory-clustering/scripts" "$FIXTURE/.agents/skills/memory-auto-dream/scripts" "$FIXTURE/.agents/skills/memory-retention/scripts"
touch "$FIXTURE/.agents/skills/memory-manager/scripts/memory_manager.py" "$FIXTURE/.agents/skills/memory-manager/scripts/memory_reflect.py" "$FIXTURE/.agents/skills/memory-clustering/scripts/cluster_patterns.py" "$FIXTURE/.agents/skills/memory-auto-dream/scripts/run_dream.py" "$FIXTURE/.agents/skills/memory-retention/scripts/archive_memory.py"
printf 'runtime\n' > "$FIXTURE/.agents/memory/auto_dream.py"
printf 'data\n' > "$FIXTURE/.agents/memory/semantic/lessons.jsonl"
python3 "$SCRIPT" --project-root "$FIXTURE" | grep -F 'runtime_files_present=1 removed=0' >/dev/null
python3 "$SCRIPT" --project-root "$FIXTURE" --apply | grep -F 'runtime_files_present=1 removed=1' >/dev/null
[ ! -e "$FIXTURE/.agents/memory/auto_dream.py" ]
[ -f "$FIXTURE/.agents/memory/semantic/lessons.jsonl" ]
echo 'memory-runtime-cleanup: PASS'
