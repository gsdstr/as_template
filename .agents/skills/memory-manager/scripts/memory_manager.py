#!/usr/bin/env python3
"""Portable, append-only memory lifecycle CLI. Python standard library only."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Iterable

SENTINEL = "<!-- memory-manager:generated -->"


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def json_line(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    records: list[dict[str, Any]] = []
    for number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid JSONL at {path}:{number}: {error.msg}") from error
        if not isinstance(record, dict):
            raise ValueError(f"invalid JSONL object at {path}:{number}")
        records.append(record)
    return records


def memory_root(args: argparse.Namespace) -> Path:
    raw = args.memory_root or os.environ.get("MEMORY_MANAGER_DATA_ROOT")
    if raw:
        return Path(raw).expanduser().resolve()
    if args.config:
        config_path = Path(args.config).expanduser().resolve()
        config = json.loads(config_path.read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            raise ValueError(f"{config_path}: configuration must be a JSON object")
        configured = config.get("memory_root")
        if not isinstance(configured, str) or not configured:
            raise ValueError(f"{config_path}: memory_root must be a non-empty string")
        path = Path(configured).expanduser()
        return (config_path.parent / path).resolve() if not path.is_absolute() else path.resolve()
    return (Path.cwd() / ".agents" / "memory").resolve()


def candidates_dir(root: Path) -> Path:
    return root / "candidates"


def candidate_path(root: Path, candidate_id: str) -> Path:
    if Path(candidate_id).name != candidate_id or not candidate_id:
        raise ValueError("candidate id must be a plain filename")
    return candidates_dir(root) / f"{candidate_id}.json"


def load_candidate(root: Path, candidate_id: str) -> dict[str, Any]:
    path = candidate_path(root, candidate_id)
    if not path.exists():
        raise ValueError(f"candidate not found: {candidate_id}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or value.get("id") != candidate_id:
        raise ValueError(f"invalid candidate record: {path}")
    return value


def events(root: Path) -> list[dict[str, Any]]:
    return read_jsonl(candidates_dir(root) / "events.jsonl")


def candidate_state(root: Path, candidate_id: str) -> str:
    state = "staged"
    for event in events(root):
        if event.get("candidate_id") == candidate_id:
            state = str(event.get("action", state))
    return state


def append_event(root: Path, candidate_id: str, action: str, reviewer: str, notes: str) -> None:
    json_line(candidates_dir(root) / "events.jsonl", {
        "ts": now(), "candidate_id": candidate_id, "action": action,
        "reviewer": reviewer, "notes": notes,
    })


def latest_by_id(records: Iterable[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for record in records:
        record_id = record.get("id")
        if isinstance(record_id, str) and record_id:
            latest[record_id] = record
    return latest


def cmd_stage(root: Path, args: argparse.Namespace) -> int:
    claim = args.claim.strip()
    if not claim:
        raise ValueError("claim must not be empty")
    candidate_id = args.id or hashlib.sha256(claim.encode("utf-8")).hexdigest()[:12]
    path = candidate_path(root, candidate_id)
    if path.exists():
        raise ValueError(f"candidate already exists (immutable): {candidate_id}")
    candidate = {
        "id": candidate_id, "claim": claim, "conditions": args.condition or [],
        "evidence_ids": args.evidence or [], "staged_at": now(),
        "reviewer": args.reviewer, "schema": "memory-manager/candidate-v1",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(candidate, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    append_event(root, candidate_id, "staged", args.reviewer, "candidate recorded")
    print(candidate_id)
    return 0


def cmd_list(root: Path, _: argparse.Namespace) -> int:
    for path in sorted(candidates_dir(root).glob("*.json")) if candidates_dir(root).exists() else []:
        candidate = json.loads(path.read_text(encoding="utf-8"))
        print(f"{candidate.get('id')}\t{candidate_state(root, str(candidate.get('id')))}\t{candidate.get('claim', '')}")
    return 0


def cmd_search(root: Path, args: argparse.Namespace) -> int:
    """Read-only case-insensitive search of memory data, excluding retractions."""
    terms = [term.casefold() for term in args.query.split() if term]
    if not terms:
        raise ValueError("query must contain at least one word")
    semantic = latest_by_id(read_jsonl(root / "semantic" / "lessons.jsonl"))
    for lesson in semantic.values():
        if lesson.get("status") in {"accepted", "provisional", "legacy"}:
            text = str(lesson.get("claim", ""))
            if all(term in text.casefold() for term in terms):
                print(f"semantic/{lesson['id']}\t{text}")
    for relative in ("personal", "working", "episodic"):
        directory = root / relative
        if not directory.exists():
            continue
        for path in sorted(item for item in directory.rglob("*") if item.is_file() and item.suffix in {".md", ".jsonl"}):
            for line_number, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if all(term in line.casefold() for term in terms):
                    print(f"{path.relative_to(root)}:{line_number}\t{line}")
    return 0


def cmd_accept(root: Path, args: argparse.Namespace) -> int:
    candidate = load_candidate(root, args.candidate_id)
    if candidate_state(root, args.candidate_id) != "staged":
        raise ValueError("only staged candidates can be accepted")
    lesson_id = f"lesson_{args.candidate_id}"
    semantic = root / "semantic" / "lessons.jsonl"
    latest = latest_by_id(read_jsonl(semantic))
    if lesson_id in latest:
        raise ValueError(f"lesson already exists: {lesson_id}")
    lesson = {
        "id": lesson_id, "claim": candidate["claim"],
        "conditions": candidate.get("conditions", []),
        "evidence_ids": candidate.get("evidence_ids", []),
        "status": "provisional" if args.provisional else "accepted",
        "accepted_at": now(), "reviewer": args.reviewer, "rationale": args.rationale,
        "source_candidate": args.candidate_id,
    }
    json_line(semantic, lesson)
    append_event(root, args.candidate_id, "accepted", args.reviewer, args.rationale)
    print(lesson_id)
    return 0


def cmd_reject(root: Path, args: argparse.Namespace) -> int:
    load_candidate(root, args.candidate_id)
    if candidate_state(root, args.candidate_id) != "staged":
        raise ValueError("only staged candidates can be rejected")
    append_event(root, args.candidate_id, "rejected", args.reviewer, args.reason)
    return 0


def cmd_reopen(root: Path, args: argparse.Namespace) -> int:
    load_candidate(root, args.candidate_id)
    if candidate_state(root, args.candidate_id) != "rejected":
        raise ValueError("only rejected candidates can be reopened")
    append_event(root, args.candidate_id, "staged", args.reviewer, "reopened for review")
    return 0


def cmd_retract(root: Path, args: argparse.Namespace) -> int:
    semantic = root / "semantic" / "lessons.jsonl"
    lesson = latest_by_id(read_jsonl(semantic)).get(args.lesson_id)
    if lesson is None:
        raise ValueError(f"lesson not found: {args.lesson_id}")
    if lesson.get("status") not in {"accepted", "provisional", "legacy"}:
        raise ValueError("only active lessons can be retracted")
    retraction = dict(lesson)
    retraction.update({"status": "retracted", "retracted_at": now(), "reviewer": args.reviewer,
                      "rationale": args.rationale, "retracts": args.lesson_id})
    json_line(semantic, retraction)
    return 0


def cmd_render(root: Path, args: argparse.Namespace) -> int:
    semantic_dir = root / "semantic"
    output = semantic_dir / "LESSONS.md"
    existing = output.read_text(encoding="utf-8") if output.exists() else "# Lessons\n"
    if SENTINEL not in existing:
        if output.exists() and not args.adopt_existing:
            raise ValueError(f"{output} has no managed sentinel; use --adopt-existing to preserve it as preamble")
        prefix = existing.rstrip()
    else:
        prefix = existing.split(SENTINEL, 1)[0].rstrip()
    latest = latest_by_id(read_jsonl(semantic_dir / "lessons.jsonl"))
    lines = ["## Managed lessons", ""]
    active = [value for value in latest.values() if value.get("status") in {"accepted", "provisional", "legacy"}]
    if not active:
        lines.append("_No accepted lessons._")
    for lesson in active:
        marker = " [PROVISIONAL]" if lesson.get("status") == "provisional" else ""
        lines.append(f"- {lesson.get('claim', '').strip()}{marker}  <!-- status={lesson.get('status')} id={lesson.get('id')} -->")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(f"{prefix}\n\n{SENTINEL}\n\n" + "\n".join(lines) + "\n", encoding="utf-8")
    print(output)
    return 0


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--memory-root", help="project-owned memory data root")
    parser.add_argument("--config", help="JSON file containing memory_root")
    commands = parser.add_subparsers(dest="command", required=True)
    stage = commands.add_parser("stage", help="create immutable candidate")
    stage.add_argument("--claim", required=True); stage.add_argument("--id")
    stage.add_argument("--condition", action="append"); stage.add_argument("--evidence", action="append")
    stage.add_argument("--reviewer", required=True); stage.set_defaults(handler=cmd_stage)
    commands.add_parser("list", help="list candidates with derived state").set_defaults(handler=cmd_list)
    search = commands.add_parser("search", help="read-only keyword search of memory data")
    search.add_argument("query"); search.set_defaults(handler=cmd_search)
    accept = commands.add_parser("accept", help="append accepted semantic lesson")
    accept.add_argument("candidate_id"); accept.add_argument("--reviewer", required=True)
    accept.add_argument("--rationale", required=True); accept.add_argument("--provisional", action="store_true")
    accept.set_defaults(handler=cmd_accept)
    reject = commands.add_parser("reject", help="append rejection decision")
    reject.add_argument("candidate_id"); reject.add_argument("--reviewer", required=True); reject.add_argument("--reason", required=True)
    reject.set_defaults(handler=cmd_reject)
    reopen = commands.add_parser("reopen", help="append re-review decision")
    reopen.add_argument("candidate_id"); reopen.add_argument("--reviewer", required=True); reopen.set_defaults(handler=cmd_reopen)
    retract = commands.add_parser("retract", help="append semantic retraction")
    retract.add_argument("lesson_id"); retract.add_argument("--reviewer", required=True); retract.add_argument("--rationale", required=True)
    retract.set_defaults(handler=cmd_retract)
    render = commands.add_parser("render", help="render LESSONS.md projection")
    render.add_argument("--adopt-existing", action="store_true", help="adopt existing LESSONS.md as preserved preamble")
    render.set_defaults(handler=cmd_render)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        return args.handler(memory_root(args), args)
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as error:
        print(f"memory-manager: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
