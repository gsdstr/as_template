#!/usr/bin/env python3
"""Audit/remove a fixed obsolete runtime-file allowlist; never touch data."""
import argparse
from pathlib import Path
FILES = ("archive.py", "auto_dream.py", "cluster.py", "decay.py", "memory_search.py", "promote.py", "render_lessons.py", "review_state.py", "validate.py")
REPLACEMENTS = (
    "memory-manager/scripts/memory_manager.py", "memory-manager/scripts/memory_reflect.py", "memory-clustering/scripts/cluster_patterns.py",
    "memory-auto-dream/scripts/run_dream.py", "memory-retention/scripts/archive_memory.py",
)
def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--project-root", required=True); parser.add_argument("--apply", action="store_true"); args = parser.parse_args()
    root = Path(args.project_root).resolve(); runtime = root / ".agents" / "memory"; skills = root / ".agents" / "skills"; present = [runtime / name for name in FILES if (runtime / name).is_file()]
    for path in present: print(path.relative_to(root))
    missing = [skills / path for path in REPLACEMENTS if not (skills / path).is_file()]
    if args.apply and missing:
        raise SystemExit("refusing removal; missing replacement scripts: " + ", ".join(str(path.relative_to(root)) for path in missing))
    if args.apply:
        for path in present: path.unlink()
    print(f"runtime_files_present={len(present)} removed={len(present) if args.apply else 0}")
if __name__ == "__main__": main()
