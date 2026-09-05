# AGENTS.md — Adapter for Ageroot

<!-- region:adapter kind:generated -->
Reads `.agents/AGENTS.md` before doing any work. This file points it at
the portable brain in `.agents/`.

## Startup
Read `.agents/AGENTS.md` before doing any work.

## Hard rules
- No force push to `main`, `production`, `staging`.

## Managed regions

This file uses the `managed-regions` update strategy.

- Keep every Ageroot region marker intact, paired, and unnested.
- Ageroot replaces `generated` regions during an approved update.
- Put project-specific instructions only in the `project` user region. Ageroot
  preserves that region across updates.
- A malformed marker structure blocks the update instead of guessing how to
  merge the file.
<!-- endregion:adapter -->
