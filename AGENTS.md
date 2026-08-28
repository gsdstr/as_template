# AGENTS.md — Adapter for agentic-stack

Reads `AGENTS.md` before doing any work. This file points it at
the portable brain in `.agents/`.

## Startup (read in order)
1. `.agents/AGENTS.md` — the map
2. `.agents/memory/personal/PREFERENCES.md` — user conventions
3. `.agents/memory/semantic/LESSONS.md` — distilled lessons
4. `.agents/protocols/permissions.md` — hard rules

## Hard rules
- No force push to `main`, `production`, `staging`.
- No modification of `.agents/protocols/permissions.md`.
