---
name: memory-auto-dream
description: Stage recurring episodic patterns for review using portable clustering. Use for scheduled reflection; it never accepts lessons or alters source episodes.
---

# Memory auto-dream

Run `scripts/run_dream.py --memory-root <data-root>` for a dry-run. Add `--apply`
to create new immutable candidates only. It calls sibling clustering and manager
scripts by path, requires a salience threshold, skips duplicate immutable ids,
and never performs automatic rejection, promotion, archival, or semantic writes.
Run `memory-retention` separately for optional copy-only archival.
