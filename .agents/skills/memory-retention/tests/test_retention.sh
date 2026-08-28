#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
FIXTURE=$(mktemp -d "${TMPDIR:-/tmp}/memory-retention.XXXXXX")
trap 'rm -rf "$FIXTURE"' EXIT HUP INT TERM
MEMORY="$FIXTURE/project/.agents/memory"
PLANS="$FIXTURE/project/.planning"
mkdir -p "$MEMORY/episodic" "$PLANS/active" "$PLANS/stale"
printf '%s\n' '{"timestamp":"2000-01-01T00:00:00+00:00","action":"old","salience":1}' > "$MEMORY/episodic/AGENT_LEARNINGS.jsonl"
printf '%s\n' 'active plan' > "$PLANS/active/task_plan.md"
printf '%s\n' 'active findings' > "$PLANS/active/findings.md"
printf '%s\n' 'active progress' > "$PLANS/active/progress.md"
printf '%s\n' 'stale plan' > "$PLANS/stale/task_plan.md"
printf '%s\n' 'stale findings' > "$PLANS/stale/findings.md"
printf '%s\n' 'stale progress' > "$PLANS/stale/progress.md"
printf '%s\n' 'active' > "$PLANS/.active_plan"
touch -t 200001010000 "$PLANS/stale/task_plan.md" "$PLANS/stale/findings.md" "$PLANS/stale/progress.md"
before_episode=$(cksum "$MEMORY/episodic/AGENT_LEARNINGS.jsonl")
before_plans=$(find "$PLANS" -type f -exec cksum {} \; | sort)
PLAN_ID=stale python3 "$ROOT/scripts/archive_memory.py" --memory-root "$MEMORY" | grep -F 'plans_to_copy=0 plan_artifacts_to_copy=0 active_plan=stale apply=false' >/dev/null
python3 "$ROOT/scripts/archive_memory.py" --memory-root "$MEMORY" | grep -F 'plans_to_copy=1 plan_artifacts_to_copy=3 active_plan=active apply=false' >/dev/null
[ ! -e "$MEMORY/episodic/snapshots" ]
python3 "$ROOT/scripts/archive_memory.py" --memory-root "$MEMORY" --apply | grep -F 'episodes_to_copy=1' >/dev/null
[ "$before_episode" = "$(cksum "$MEMORY/episodic/AGENT_LEARNINGS.jsonl")" ]
[ "$before_plans" = "$(find "$PLANS" -type f -exec cksum {} \; | sort)" ]
grep -R -F '"action": "old"' "$MEMORY/episodic/snapshots" >/dev/null
[ ! -e "$MEMORY/episodic/snapshots/planning/active" ]
grep -R -F 'stale plan' "$MEMORY/episodic/snapshots/planning/stale" >/dev/null
first_count=$(find "$MEMORY/episodic/snapshots/planning/stale" -type f | wc -l | tr -d ' ')
python3 "$ROOT/scripts/archive_memory.py" --memory-root "$MEMORY" --apply >/dev/null
[ "$first_count" = "$(find "$MEMORY/episodic/snapshots/planning/stale" -type f | wc -l | tr -d ' ')" ]
echo 'memory-retention: PASS'
