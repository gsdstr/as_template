# Memory lifecycle extraction audit

Audited source: former `.agents/memory/*.py` runtime plus the removed episodic
reflection entrypoint and its harness-hook responsibilities.

| Former module | Replacement | Retention change |
|---|---|---|
| `memory_search.py` | `memory-manager search` | Read-only search; no index database. |
| `validate.py` | `memory-manager` explicit reviewer gate | No automatic rejection. |
| `review_state.py`, `promote.py` | `memory-manager` stage/accept/reject/reopen | Immutable candidates plus append-only events. |
| `render_lessons.py` | `memory-manager render` | `lessons.jsonl` remains source; managed projection only. |
| `cluster.py` | `memory-clustering` | Read-only episodic input, JSON pattern output. |
| `auto_dream.py` | `memory-auto-dream` | Defaults dry-run; only stages when `--apply`. |
| `decay.py`, `archive.py` | `memory-retention` | Copy-only archive; never moves/deletes source. |
| `.agent/tools/memory_reflect.py`, `post_execution.py`, `on_failure.py` | `memory-manager/scripts/memory_reflect.py` | Portable append-only success/failure records, source provenance, and 3 failures in 14 days rewrite signal. |

Lifecycle coverage is complete under the portable design: automatic rejection
was intentionally replaced by an explicit reviewer gate, and destructive decay
or workspace moves were intentionally replaced by copy-only retention.

`memory-runtime-cleanup` owns fixed allowlist audit/removal. It does not target
data, configuration, candidates, Markdown, JSONL, or permissions.
