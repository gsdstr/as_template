---
name: memory-manager
description: Manage project-owned personal, working, episodic, and semantic memory safely. Use when staging/reviewing lesson candidates, rendering LESSONS.md, retracting a lesson, or inspecting memory lifecycle state.
---

# Memory manager

Use this skill for portable memory lifecycle operations. Runtime code lives in
this directory; memory data lives in the configured data root and remains
project-owned.

## Trigger

Use for: episodic success/failure reflection; candidate staging or review;
accepting, rejecting, reopening, or retracting a lesson; rendering
`LESSONS.md`; lifecycle status; and safe memory search by normal project tools.
Do not use it to edit a person's preferences or to delete historical memory.

## Included scope

This skill implements lifecycle core: append-only episodic reflection,
read-only keyword search, immutable candidate staging, explicit human/agent
review decisions, candidate promotion (accept), semantic retraction, and
lesson rendering. Related lifecycle skills handle deterministic recurrence
extraction (`memory-clustering`), scheduled staging (`memory-auto-dream`),
copy-only retention (`memory-retention`), and the one-time runtime migration
audit (`memory-runtime-cleanup`). A harness must not infer an acceptance without
a reviewer and rationale.

## Safety and retention rules

- Never delete, truncate, or rewrite personal, working, episodic, or semantic
  source data. `episodic/AGENT_LEARNINGS.jsonl` and
  `semantic/lessons.jsonl` are append-only.
- Candidates are immutable JSON records. Review decisions append to
  `candidates/events.jsonl`; no candidate is moved, replaced, or removed.
- Accept and retract append a new semantic record. Retraction preserves the
  lesson and records why it must no longer appear in the rendered view.
- `semantic/LESSONS.md` is a generated projection, not a semantic source. The
  renderer preserves all text before its managed sentinel and rewrites only the
  managed section. It refuses an existing file without a sentinel unless
  `--adopt-existing` is explicitly passed.
- Run against a temporary `--memory-root` for validation. Never point tests at
  project memory.

## Data-path configuration

Resolution order: `--memory-root`, `MEMORY_MANAGER_DATA_ROOT`, a JSON config
passed with `--config`, then `.agents/memory` relative to current directory.
Config shape: `{"memory_root": ".agents/memory"}`. A relative configured path
is resolved relative to that config file. Copy
`templates/memory-manager.config.json` into a project-owned configuration
location if the default is unsuitable.

The root contains data only: `personal/`, `working/`, `episodic/`, `semantic/`,
and `candidates/`. It contains no lifecycle implementation.

## Harness-agnostic workflow

All commands use Python standard library only:

```sh
SCRIPT=.agents/skills/memory-manager/scripts/memory_manager.py
REFLECT=.agents/skills/memory-manager/scripts/memory_reflect.py

# Log a significant action. `--fail` preserves the failure signal and flags
# a skill for rewrite after three failures in fourteen days.
python3 "$REFLECT" --memory-root .agents/memory memory-manager \
  "render lesson projection" success --importance 5 --evidence run-2026-08-28

# Stage a candidate without interpreting or promoting it.
python3 "$SCRIPT" --memory-root .agents/memory stage \
  --claim "Serialize timestamps in UTC for cross-region comparisons" \
  --evidence run-2026-08-28 --reviewer codex

# Human/host-agent review: rationale or reason is mandatory.
python3 "$SCRIPT" --memory-root .agents/memory list
python3 "$SCRIPT" --memory-root .agents/memory search "timestamp UTC"
python3 "$SCRIPT" --memory-root .agents/memory accept <candidate-id> \
  --reviewer codex --rationale "Repeated incidents support this guidance"
python3 "$SCRIPT" --memory-root .agents/memory reject <candidate-id> \
  --reviewer codex --reason "Too task-specific"
python3 "$SCRIPT" --memory-root .agents/memory reopen <candidate-id> --reviewer codex

# Render only a managed LESSONS.md and retract append-only when obsolete.
python3 "$SCRIPT" --memory-root .agents/memory render
python3 "$SCRIPT" --memory-root .agents/memory retract lesson_<candidate-id> \
  --reviewer codex --rationale "Superseded by migration policy"
```

Run `python3 "$SCRIPT" --help` for the complete CLI. Staging and review are
mechanical; deciding whether a claim is true remains the reviewing agent's or
human's responsibility.

## Verification

```sh
python3 .agents/skills/memory-manager/scripts/memory_manager.py --help
sh .agents/skills/memory-manager/tests/test_lifecycle.sh
sh .agents/skills/memory-manager/tests/test_reflect.sh
rg -n '\.agents/memory|agents\.memory' .agents/skills/memory-manager/scripts
```
