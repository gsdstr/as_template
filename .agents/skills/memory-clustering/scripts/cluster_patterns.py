#!/usr/bin/env python3
"""Read episodic JSONL and emit deterministic, reviewable recurrence patterns."""
import argparse, hashlib, json, re
from pathlib import Path

STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "the", "to", "with"}
def words(value): return {word for word in re.findall(r"[\w-]+", value.casefold()) if word not in STOP}
def features(entry): return words(" ".join(str(entry.get(key, "")) for key in ("action", "reflection", "detail")))
def score(entry): return float(entry.get("salience", entry.get("canonical_salience", entry.get("importance", 1))) or 1)
def similarity(left, right): return len(left & right) / len(left | right) if left or right else 0.0
def load(path):
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
def patterns(entries, threshold):
    groups = []
    for entry in entries:
        feature = features(entry)
        if not feature: continue
        hits = [index for index, group in enumerate(groups) if any(similarity(feature, prior) >= threshold for _, prior in group)]
        if not hits: groups.append([(entry, feature)]); continue
        groups[hits[0]].append((entry, feature))
        for index in reversed(hits[1:]): groups[hits[0]].extend(groups.pop(index))
    output = []
    for group in groups:
        if len(group) < 2: continue
        canonical, _ = max(group, key=lambda pair: score(pair[0]))
        claim = str(canonical.get("reflection") or canonical.get("action") or "").strip()
        if not claim: continue
        shared = sorted(set.intersection(*(feature for _, feature in group)))
        identifier = hashlib.sha256((claim.casefold() + "|" + "|".join(shared)).encode()).hexdigest()[:12]
        output.append({"id": identifier, "name": "pattern_" + identifier[:6], "claim": claim,
                       "conditions": shared, "evidence_ids": [str(item.get("timestamp", "")) for item, _ in group if item.get("timestamp")],
                       "cluster_size": len(group), "canonical_salience": score(canonical) * len(group)})
    return output
def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument("--input", required=True); parser.add_argument("--output", required=True); parser.add_argument("--threshold", type=float, default=.3)
    args = parser.parse_args(); Path(args.output).write_text(json.dumps(patterns(load(args.input), args.threshold), indent=2) + "\n", encoding="utf-8")
if __name__ == "__main__": main()
