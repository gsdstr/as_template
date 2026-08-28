---
name: memory-clustering
description: Deterministically cluster episodic JSONL records into reviewable memory patterns. Use for recurring-experience extraction, not semantic acceptance.
---

# Memory clustering

Run `scripts/cluster_patterns.py --input <episodes.jsonl> --output <patterns.json>`.
It uses only standard-library token Jaccard similarity and produces candidate-shaped
patterns. It never changes source episodes or accepts lessons. Pass its output to
`memory-auto-dream` or review patterns manually with `memory-manager`.

Use a temporary output file when experimenting. Clusters are heuristic signals;
reviewer acceptance and rationale remain mandatory.
