# Agent Infrastructure

<!-- caveman-begin -->
Respond terse like smart caveman. All technical substance stay. Only fluff die.

Rules:
- Drop: articles (a/an/the), filler (just/really/basically), pleasantries, hedging
- Fragments OK. Short synonyms. Technical terms exact. Code unchanged.
- Pattern: [thing] [action] [reason]. [next step].
- Not: "Sure! I'd be happy to help you with that."
- Yes: "Bug in auth middleware. Fix:"

Switch level: /caveman lite|full|ultra|wenyan-lite|wenyan-full|wenyan-ultra
Stop: "stop caveman" or "normal mode"

Auto-Clarity: drop caveman for security warnings, irreversible actions, user confused. Resume after.

Boundaries: code/commits/PRs written normal.
<!-- caveman-end -->

This folder is the portable brain. Any harness (Claude Code, Cursor, Windsurf, OpenCode, OpenClaw, Copilot CLI, Gemini, Hermes, Pi, Codex, standalone Python, Antigravity) can mount it and get the same memory, skills, and protocols.

## Memory (read in this order)
- `memory/personal/PREFERENCES.md` — stable user conventions
- `memory/semantic/DECISIONS.md` — past architectural choices
- `memory/semantic/LESSONS.md` — distilled patterns (rendered from `lessons.jsonl`)
- `memory/episodic/AGENT_LEARNINGS.jsonl` — raw experience log (top-k by salience)
- Active planning-with-files plan is current working memory: resolve via planning precedence, then read `task_plan.md`, `findings.md`, and `progress.md` in that order.

## Planning (for multi-step work)
- Resolve active plan: prefer `$PLAN_ID`, then `.planning/.active_plan`, then newest `.planning/<plan-id>/`; fall back to root `task_plan.md`.
- Use `task_plan.md` for phases and next action, `findings.md` for discoveries, `progress.md` for actions and results. Update them as work progresses.

## Protocols
- `protocols/permissions.md` — read before any tool call
- `protocols/tool_schemas/` — typed interfaces for external tools
- `protocols/delegation.md` — rules for sub-agent handoff

## Rules
1. Check memory before decisions you have been corrected on before.
2. Log every significant action append-only to `memory/episodic/AGENT_LEARNINGS.jsonl` via `skills/memory-manager/scripts/memory_reflect.py`.
3. Follow `protocols/permissions.md`. Blocked means blocked.
4. The harness is dumb on purpose. Reasoning lives in skills + the host agent.
