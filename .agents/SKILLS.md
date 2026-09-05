# Project skills

<!-- generated-by: ageroot; template: <template-version>; commit: <short-git-commit>; rendered-at: <ISO-8601 timestamp> -->

Project skills are managed with [skills-manager](https://github.com/xingkongliang/skills-manager).
It creates symlinks from this project to shared skill store at `~/.skills-manager`.

## Operating rules

- Use `skills-manager` to install, update, and remove project skills.
- Do not copy skill directories into this repository or edit linked skill contents here.
- Read this file only when configuring or updating skills; it is not required at normal agent startup.
- Keep this list aligned with project needs. Categorization is policy, not an installed-state report.
- Required skills may be installed globally. A project symlink is needed only when
  the project must pin or otherwise manage that skill locally.

## Required

- `caveman` — concise communication protocol.
- `rtk` — token-efficient shell command output.

## Recommended

- `caveman-commit` — concise Conventional Commit messages.
- `caveman-explore` — read-only repository orientation and cross-file discovery.
- `caveman-review` — compact code-review findings.
- `planning-with-files` — durable planning for multi-step implementation work.
- `memory-manager` — episodic reflection, append-only journal writes, candidate review, semantic rendering, FTS5 search, and migration.
- `memory-maintenance` — offline clustering, candidate staging, decay/archival, review queue upkeep, and FTS rebuilds (depends on `memory-manager`).
