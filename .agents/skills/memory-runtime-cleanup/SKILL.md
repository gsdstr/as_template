---
name: memory-runtime-cleanup
description: Audit and remove only obsolete memory runtime Python files after equivalent skills are present. Use for extraction migrations, never for memory data cleanup.
---

# Memory runtime cleanup

Run `scripts/audit_runtime.py --project-root <root>` first. It checks exactly
the former top-level runtime modules. Add `--apply` only after replacement skills
are verified. It never targets memory data directories, JSONL, Markdown, feature
configuration, candidates, or permissions.
