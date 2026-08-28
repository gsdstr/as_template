---
name: memory-retention
description: Copy stale episodic records and inactive planning artifacts to append-only archives without deleting source data. Use for retention review and safe archival.
---

# Memory retention

Run `scripts/archive_memory.py --memory-root <data-root>` to preview. Add
`--apply` only after reviewing output. It copies qualifying old low-salience
episodes into `episodic/snapshots/`; it never moves, truncates, or deletes
source records. Duplicate episode copies are content-hash suppressed. Archival
is not semantic removal.

It also retains stale inactive planning-with-files artifacts (`task_plan.md`,
`findings.md`, and `progress.md`) from `.planning/<plan-id>/` into
`episodic/snapshots/planning/`. The active plan is excluded using
planning-with-files precedence: `$PLAN_ID`, `.planning/.active_plan`, newest
plan directory, then legacy root `task_plan.md`. Use `--planning-root <project-root>`
when the project cannot be inferred as the parent of `.agents`. A plan is stale
only when all of its present plan artifacts are older than `--plan-days`
(default: 30). Archived plan copies use content-hash names, so repeat runs do
not duplicate them. This is copy-only: no plan source is moved, truncated, or
deleted.
