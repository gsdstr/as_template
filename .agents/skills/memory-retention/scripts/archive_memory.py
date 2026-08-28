#!/usr/bin/env python3
"""Safe archive copier: source memory and planning files are never rewritten."""
import argparse, datetime as dt, hashlib, json, os
from pathlib import Path

PLAN_ARTIFACTS = ("task_plan.md", "findings.md", "progress.md")
def old_low(record, days, floor):
    try: stamp = dt.datetime.fromisoformat(record.get("timestamp", "").replace("Z", "+00:00")); stamp = stamp.replace(tzinfo=dt.timezone.utc) if stamp.tzinfo is None else stamp
    except (TypeError, ValueError): return False
    return stamp < dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days) and float(record.get("salience", record.get("importance", 1))) < floor

def resolved_child(plans_dir, plan_id):
    """Return plan_id only when it names a direct child of .planning."""
    if not plan_id or Path(plan_id).name != plan_id or plan_id in (".", ".."):
        return None
    candidate = plans_dir / plan_id
    return candidate if candidate.is_dir() else None

def active_plan_dir(project_root):
    """Match planning-with-files precedence: PLAN_ID, pointer, newest, legacy."""
    plans_dir = project_root / ".planning"
    from_environment = resolved_child(plans_dir, os.environ.get("PLAN_ID", ""))
    if from_environment:
        return from_environment
    pointer = plans_dir / ".active_plan"
    if pointer.exists():
        from_pointer = resolved_child(plans_dir, pointer.read_text(encoding="utf-8").strip())
        if from_pointer:
            return from_pointer
    candidates = [path for path in plans_dir.iterdir() if path.is_dir()] if plans_dir.is_dir() else []
    if candidates:
        return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))
    return project_root if (project_root / "task_plan.md").exists() else None

def stale_plan_artifacts(project_root, days):
    plans_dir = project_root / ".planning"
    active = active_plan_dir(project_root)
    if not plans_dir.is_dir():
        return active, []
    cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=days)
    selected = []
    for plan_dir in sorted((path for path in plans_dir.iterdir() if path.is_dir()), key=lambda path: path.name):
        if plan_dir == active:
            continue
        artifacts = [plan_dir / name for name in PLAN_ARTIFACTS if (plan_dir / name).is_file()]
        if artifacts and max(dt.datetime.fromtimestamp(path.stat().st_mtime, dt.timezone.utc) for path in artifacts) < cutoff:
            selected.append((plan_dir, artifacts))
    return active, selected

def copy_stale_plans(selected, snapshots):
    copied = 0
    plans_snapshot = snapshots / "planning"
    for plan_dir, artifacts in selected:
        for artifact in artifacts:
            content = artifact.read_bytes()
            digest = hashlib.sha256(content).hexdigest()
            target = plans_snapshot / plan_dir.name / f"{artifact.stem}-{digest}{artifact.suffix}"
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
                copied += 1
    return copied
def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--memory-root", required=True); parser.add_argument("--planning-root", help="Project root containing .planning (default: parent of .agents)"); parser.add_argument("--days", type=int, default=90); parser.add_argument("--salience-floor", type=float, default=2); parser.add_argument("--plan-days", type=int, default=30); parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(); root = Path(args.memory_root); project_root = Path(args.planning_root) if args.planning_root else root.parent.parent; source = root / "episodic" / "AGENT_LEARNINGS.jsonl"; snapshots = root / "episodic" / "snapshots"
    records = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()] if source.exists() else []
    selected = [record for record in records if old_low(record, args.days, args.salience_floor)]
    active, stale_plans = stale_plan_artifacts(project_root, args.plan_days); plan_artifacts = sum(len(artifacts) for _, artifacts in stale_plans); active_label = active.name if active and active != project_root else ("legacy" if active else "none")
    print(f"episodes_to_copy={len(selected)} plans_to_copy={len(stale_plans)} plan_artifacts_to_copy={plan_artifacts} active_plan={active_label} apply={str(args.apply).lower()}")
    if not args.apply: return
    snapshots.mkdir(parents=True, exist_ok=True); target = snapshots / f"archive_{dt.datetime.now(dt.timezone.utc).date()}.jsonl"; known = set()
    for file in snapshots.glob("*.jsonl"):
        known.update(hashlib.sha256(line.encode()).hexdigest() for line in file.read_text(encoding="utf-8").splitlines() if line.strip())
    with target.open("a", encoding="utf-8") as stream:
        for record in selected:
            raw = json.dumps(record, ensure_ascii=False, sort_keys=True); digest = hashlib.sha256(raw.encode()).hexdigest()
            if digest not in known: stream.write(raw + "\n"); known.add(digest)
    copy_stale_plans(stale_plans, snapshots)
if __name__ == "__main__": main()
