#!/usr/bin/env python3
"""Safe scheduled reflection: cluster episodes and stage, never promote."""
import argparse, json, subprocess, tempfile
from pathlib import Path
def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--memory-root", required=True); parser.add_argument("--threshold", type=float, default=7); parser.add_argument("--apply", action="store_true"); parser.add_argument("--cluster-script"); parser.add_argument("--manager-script")
    args = parser.parse_args(); here = Path(__file__).resolve().parents[2]; cluster = Path(args.cluster_script) if args.cluster_script else here / "memory-clustering/scripts/cluster_patterns.py"; manager = Path(args.manager_script) if args.manager_script else here / "memory-manager/scripts/memory_manager.py"; root = Path(args.memory_root); episodic = root / "episodic/AGENT_LEARNINGS.jsonl"
    if not episodic.exists(): print("patterns=0 staged=0 (no episodic source)"); return
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as output:
        output_path = Path(output.name)
    try:
        subprocess.run(["python3", str(cluster), "--input", str(episodic), "--output", str(output_path)], check=True)
        patterns = [item for item in json.loads(output_path.read_text(encoding="utf-8")) if item.get("canonical_salience", 0) >= args.threshold]
        staged = 0
        for item in patterns:
            command = ["python3", str(manager), "--memory-root", str(root), "stage", "--id", item["id"], "--claim", item["claim"], "--reviewer", "auto-dream"]
            for value in item.get("conditions", []): command.extend(["--condition", value])
            for value in item.get("evidence_ids", []): command.extend(["--evidence", value])
            if args.apply and subprocess.run(command, capture_output=True).returncode == 0: staged += 1
        print(f"patterns={len(patterns)} staged={staged} apply={str(args.apply).lower()}")
    finally: output_path.unlink(missing_ok=True)
if __name__ == "__main__": main()
