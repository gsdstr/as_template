#!/usr/bin/env python3
"""Append one portable success or failure event to episodic memory."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
from pathlib import Path
from typing import Any

try:
    import fcntl
except ImportError:  # Native Windows: retain append-only behavior without flock.
    fcntl = None

FAILURE_THRESHOLD = 3
FAILURE_WINDOW_DAYS = 14


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def memory_root(value: str | None) -> Path:
    raw = value or os.environ.get("MEMORY_MANAGER_DATA_ROOT")
    return Path(raw).expanduser().resolve() if raw else (Path.cwd() / ".agents" / "memory").resolve()


def commit_sha(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root.parent.parent,
            capture_output=True, text=True, timeout=2, check=False,
        )
        return result.stdout.strip() if result.returncode == 0 else ""
    except OSError:
        return ""


def append_jsonl(path: Path, record: dict[str, Any]) -> None:
    payload = (json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n").encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("ab") as stream:
        if fcntl is not None:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            stream.write(payload)
            stream.flush()
        finally:
            if fcntl is not None:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def recent_failures(path: Path, skill: str) -> int:
    if not path.exists():
        return 0
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=FAILURE_WINDOW_DAYS)
    count = 0
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            record = json.loads(raw)
            stamp = dt.datetime.fromisoformat(str(record.get("timestamp", "")).replace("Z", "+00:00"))
            stamp = stamp.replace(tzinfo=dt.timezone.utc) if stamp.tzinfo is None else stamp
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if record.get("skill") == skill and record.get("result") == "failure" and stamp > cutoff:
            count += 1
    return count


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(description=__doc__)
    command.add_argument("--memory-root", help="project-owned memory data root")
    command.add_argument("skill")
    command.add_argument("action")
    command.add_argument("outcome")
    command.add_argument("--fail", action="store_true", help="record a failure")
    command.add_argument("--importance", type=int, default=None)
    command.add_argument("--note", default="", help="success reflection or failure context")
    command.add_argument("--confidence", type=float)
    command.add_argument("--evidence", nargs="*", default=[])
    command.add_argument("--pain", type=int)
    return command


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    root = memory_root(args.memory_root)
    episodic = root / "episodic" / "AGENT_LEARNINGS.jsonl"
    failure = args.fail
    reflection = args.note[:300]
    if failure:
        reflection = f"FAILURE in {args.skill}: {args.outcome[:200]}"
        if args.note:
            reflection += f" | context: {args.note[:300]}"
    record: dict[str, Any] = {
        "timestamp": now(),
        "skill": args.skill,
        "action": args.action[:200],
        "result": "failure" if failure else "success",
        "detail": args.outcome[:500],
        "pain_score": args.pain if args.pain is not None else (8 if failure else 2),
        "importance": args.importance if args.importance is not None else (7 if failure else 5),
        "reflection": reflection,
        "confidence": args.confidence if args.confidence is not None else (0.9 if failure else 0.5),
        "source": {
            "skill": args.skill,
            "profile": os.environ.get("AGENT_PROFILE", "default"),
            "run_id": os.environ.get("AGENT_RUN_ID", f"pid-{os.getpid()}"),
            "commit_sha": commit_sha(root),
        },
        "evidence_ids": args.evidence,
    }
    if failure:
        record["context"] = args.note[:300]
        failures = recent_failures(episodic, args.skill) + 1
        if failures >= FAILURE_THRESHOLD:
            record["reflection"] += f" | THIS SKILL HAS FAILED {failures} TIMES IN {FAILURE_WINDOW_DAYS}d. Flag for rewrite."
            record["pain_score"] = 10
    append_jsonl(episodic, record)
    print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
