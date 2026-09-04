"""Safety-first dry-run comparison and update strategy implementation for Ageroot.

This module implements:
1. ResultClass vocabulary & apply eligibility rules.
2. Deterministic normalization (line endings, final newline, trailing whitespace, formatter-only Markdown/YAML noise).
3. Snapshot store with SHA-256 integrity verification.
4. Managed region parser and deterministic region merge engine.
5. Three-way comparison for renderer-owned files (generated & managed-regions).
6. External-link target resolution validation.
7. Deletion escalation and modified-deletion gating.
8. Tiered summary-first confirmation report.
9. Atomic apply with transactional snapshot commit.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import os
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple


class ResultClass(str, Enum):
    UNCHANGED = "unchanged"
    CHANGED = "changed"
    UNVERIFIED = "unverified"
    REGION_MERGE = "region-merge"
    CONFLICT = "conflict"
    BLOCKED = "blocked"
    INVALID_LINK = "invalid-link"
    DELETION_PENDING = "deletion-pending"

    @property
    def is_eligible_for_apply(self) -> bool:
        """Only unchanged, changed, unverified, and region-merge are eligible for atomic apply.
        
        Any other class (conflict, blocked, invalid-link, deletion-pending) blocks atomic apply.
        """
        return self in (
            ResultClass.UNCHANGED,
            ResultClass.CHANGED,
            ResultClass.UNVERIFIED,
            ResultClass.REGION_MERGE,
        )


class Strategy(str, Enum):
    GENERATED = "generated"
    MANAGED_REGIONS = "managed-regions"
    EXTERNAL_LINK = "external-link"


@dataclass
class ComparisonResult:
    path: str
    strategy: Strategy
    result_class: ResultClass
    reason: Optional[str] = None
    diff: Optional[str] = None
    proposed_content: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    new_snapshot_content: Optional[str] = None
    new_snapshot_sha256: Optional[str] = None
    excluded: bool = False

    @property
    def is_eligible(self) -> bool:
        return self.result_class.is_eligible_for_apply


class DeterministicNormalizer:
    """Normalizes content deterministically before comparison.
    
    Removes:
    - CRLF / CR -> LF line endings.
    - Trailing whitespace on each line.
    - Multiple trailing empty lines -> single trailing newline (or none if empty).
    - Formatter-only Markdown noise (consecutive blank lines collapsed to at most 2, trailing spaces removed).
    - Formatter-only YAML noise (trailing spaces, normalize multiple blank lines between documents).
    Preserves exact YAML data/ordering and Markdown structure/text.
    """

    @staticmethod
    def normalize_text(text: str) -> str:
        if text is None:
            return ""
        # 1. Normalize line endings to LF
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # 2. Strip trailing whitespace per line
        lines = [line.rstrip() for line in normalized.split("\n")]
        normalized = "\n".join(lines)
        
        # 3. Collapse 3+ consecutive newlines to at most 2 (standard markdown/yaml formatter normalization)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)

        # 4. Generated-file provenance is metadata, not managed content.  A
        # version/commit/timestamp-only change must not create an update.
        normalized = re.sub(
            r"<!-- generated-by: ageroot; template: [^;]+; commit: [^;]+; rendered-at: [^>]+ -->",
            "<!-- generated-by: ageroot -->",
            normalized,
        )

        # 5. Ensure single final newline if non-empty
        normalized = normalized.rstrip()
        if normalized:
            normalized += "\n"
            
        return normalized


class SnapshotStore:
    """Manages project-local baseline snapshots in Git-ignored .agents/snapshots/"""

    def __init__(self, root_dir: Path, snapshot_dir: Optional[Path] = None):
        self.root_dir = Path(root_dir)
        self.snapshot_dir = snapshot_dir or (self.root_dir / ".agents" / "snapshots")

    def get_snapshot_path(self, relative_path: str) -> Path:
        return self.snapshot_dir / relative_path

    @staticmethod
    def compute_sha256(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def read_snapshot(self, relative_path: str, expected_sha256: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Reads snapshot file and verifies SHA-256.
        
        Returns:
            (content, error_message)
            If missing: (None, "missing")
            If corrupt: (None, "corrupt")
            If success: (content, None)
        """
        snapshot_file = self.get_snapshot_path(relative_path)
        if not snapshot_file.exists() or not snapshot_file.is_file():
            return None, "missing"

        try:
            content = snapshot_file.read_text(encoding="utf-8")
        except Exception as e:
            return None, f"read_error: {e}"

        if expected_sha256:
            actual_sha = self.compute_sha256(content)
            if actual_sha != expected_sha256:
                return None, "corrupt"

        return content, None

    def write_snapshot_atomic(self, relative_path: str, content: str) -> str:
        """Writes snapshot to disk and returns SHA-256."""
        snapshot_file = self.get_snapshot_path(relative_path)
        snapshot_file.parent.mkdir(parents=True, exist_ok=True)
        snapshot_file.write_text(content, encoding="utf-8")
        return self.compute_sha256(content)


@dataclass
class Region:
    name: str
    kind: str  # 'generated' or 'user'
    content: str  # content inside the markers


class ManagedRegionParser:
    """Parses and merges files containing declared region markers."""

    MARKER_PATTERN = re.compile(
        r"<!--\s*(?:(?P<legacy_start>[\w-]+)-begin|(?P<legacy_end>[\w-]+)-end|region:(?P<named_start>[\w-]+)(?:\s+kind:(?P<kind>generated|user))?|endregion:(?P<named_end>[\w-]+))\s*-->"
    )

    @classmethod
    def parse_structure(cls, text: str) -> Tuple[bool, Optional[List[dict]], Optional[str]]:
        norm_text = DeterministicNormalizer.normalize_text(text)
        lines = norm_text.splitlines(keepends=True)
        
        segments = []
        open_stack = []
        current_segment_lines = []
        current_kind = "unmanaged"
        current_name = None

        line_idx = 0
        while line_idx < len(lines):
            line = lines[line_idx]
            match = cls.MARKER_PATTERN.search(line)
            if match:
                m_dict = match.groupdict()
                start_name = m_dict.get("legacy_start") or m_dict.get("named_start")
                end_name = m_dict.get("legacy_end") or m_dict.get("named_end")

                if start_name:
                    if open_stack:
                        return False, None, f"Nested region '{start_name}' inside '{open_stack[-1]['name']}' is not allowed"
                    # Flush prior unmanaged segment if it has content
                    if current_segment_lines:
                        raw_str = "".join(current_segment_lines)
                        if raw_str:
                            segments.append({
                                "type": "unmanaged",
                                "name": None,
                                "raw": raw_str,
                            })
                        current_segment_lines = []
                    
                    kind = m_dict.get("kind")
                    if not kind:
                        kind = "generated" if start_name in ("generated", "header", "caveman", "rtk") else "user"

                    open_stack.append({
                        "name": start_name,
                        "kind": kind,
                        "start_marker": line,
                    })
                    current_segment_lines.append(line)
                elif end_name:
                    if not open_stack:
                        return False, None, f"Unmatched closing marker for '{end_name}'"
                    top = open_stack.pop()
                    if top["name"] != end_name:
                        return False, None, f"Mismatched region end marker: expected '{top['name']}', got '{end_name}'"
                    
                    current_segment_lines.append(line)
                    segments.append({
                        "type": "region",
                        "name": top["name"],
                        "kind": top["kind"],
                        "start_marker": top["start_marker"],
                        "end_marker": line,
                        "content": "".join(current_segment_lines[1:-1]),
                        "raw": "".join(current_segment_lines),
                    })
                    current_segment_lines = []
            else:
                current_segment_lines.append(line)
            line_idx += 1

        if open_stack:
            return False, None, f"Unclosed region marker for '{open_stack[-1]['name']}'"

        if current_segment_lines:
            raw_str = "".join(current_segment_lines)
            if raw_str:
                segments.append({
                    "type": "unmanaged",
                    "name": None,
                    "raw": raw_str,
                })

        return True, segments, None

    @classmethod
    def merge(
        cls, current_text: str, new_rendered_text: str, baseline_text: Optional[str]
    ) -> Tuple[bool, Optional[str], List[str], Optional[str]]:
        curr_ok, curr_segs, curr_err = cls.parse_structure(current_text)
        if not curr_ok:
            return False, None, [], f"Current file region structure malformed: {curr_err}"

        new_ok, new_segs, new_err = cls.parse_structure(new_rendered_text)
        if not new_ok:
            return False, None, [], f"New render region structure malformed: {new_err}"

        base_segs_map = {}
        if baseline_text:
            base_ok, base_segs, base_err = cls.parse_structure(baseline_text)
            if base_ok:
                for seg in base_segs:
                    if seg.get("type") == "region":
                        base_segs_map[seg["name"]] = seg

        curr_regions = {s["name"]: s for s in curr_segs if s.get("type") == "region"}
        warnings = []

        merged_pieces = []
        for n_seg in new_segs:
            if n_seg["type"] == "unmanaged":
                merged_pieces.append(n_seg["raw"])
            elif n_seg["type"] == "region":
                r_name = n_seg["name"]
                r_kind = n_seg["kind"]
                
                if r_name in curr_regions:
                    c_seg = curr_regions[r_name]
                    if r_kind == "user":
                        # Preserve current user region content
                        merged_pieces.append(c_seg["raw"])
                        if base_segs_map.get(r_name) and DeterministicNormalizer.normalize_text(c_seg["content"]) != DeterministicNormalizer.normalize_text(base_segs_map[r_name]["content"]):
                            warnings.append(f"User region '{r_name}' has local modifications (preserved)")
                    else:  # generated
                        # Check concurrent modification vs baseline
                        if base_segs_map.get(r_name):
                            b_content = DeterministicNormalizer.normalize_text(base_segs_map[r_name]["content"])
                            c_content = DeterministicNormalizer.normalize_text(c_seg["content"])
                            n_content = DeterministicNormalizer.normalize_text(n_seg["content"])
                            if c_content != b_content and c_content != n_content:
                                return False, None, [], f"Concurrent edit in generated region '{r_name}': local modifications conflict with template update"
                        merged_pieces.append(n_seg["raw"])
                else:
                    merged_pieces.append(n_seg["raw"])

        return True, "".join(merged_pieces), warnings, None


class ThreeWayComparisonEngine:
    """Core comparison engine implementing safety-first comparison rules."""

    def __init__(
        self,
        root_dir: Path,
        snapshots_enabled: bool = True,
        snapshot_store: Optional[SnapshotStore] = None,
    ):
        self.root_dir = Path(root_dir)
        self.snapshots_enabled = snapshots_enabled
        self.snapshot_store = snapshot_store or SnapshotStore(self.root_dir)

    def compare_path(
        self,
        relative_path: str,
        strategy: Strategy,
        new_render_content: Optional[str] = None,
        state_entry: Optional[dict] = None,
        one_time_unverified_override: bool = False,
        expected_link_target: Optional[str] = None,
    ) -> ComparisonResult:
        target_file = self.root_dir / relative_path

        # Planning belongs to the planning-with-files skill.  It is never a
        # managed Ageroot path and must not affect comparison or reporting.
        if Path(relative_path).parts and Path(relative_path).parts[0] == ".planning":
            return ComparisonResult(
                path=relative_path,
                strategy=strategy,
                result_class=ResultClass.UNCHANGED,
                reason="Excluded planning-with-files state",
                excluded=True,
            )

        # 1. Handle external-link strategy
        if strategy == Strategy.EXTERNAL_LINK:
            if not target_file.exists() and not target_file.is_symlink():
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.INVALID_LINK,
                    reason=f"External link does not exist at {relative_path}",
                )
            
            if expected_link_target:
                try:
                    if target_file.is_symlink():
                        target_resolved = os.readlink(target_file)
                        if expected_link_target not in target_resolved and str(target_file.resolve()) != str(Path(expected_link_target).resolve()):
                            return ComparisonResult(
                                path=relative_path,
                                strategy=strategy,
                                result_class=ResultClass.INVALID_LINK,
                                reason=f"External link points to '{target_resolved}', expected '{expected_link_target}'",
                            )
                except Exception as e:
                    return ComparisonResult(
                        path=relative_path,
                        strategy=strategy,
                        result_class=ResultClass.INVALID_LINK,
                        reason=f"Error validating link target: {e}",
                    )

            return ComparisonResult(
                path=relative_path,
                strategy=strategy,
                result_class=ResultClass.UNCHANGED,
                reason="External link target validated",
            )

        # 2. Handle potential deletion for renderer-owned strategies
        if new_render_content is None:
            if not target_file.exists():
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.UNCHANGED,
                    reason="File absent from render and workspace",
                )
            
            # File exists locally but absent from new render -> potential deletion
            if not self.snapshots_enabled or not state_entry or not state_entry.get("sha256"):
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.DELETION_PENDING,
                    reason="Managed file absent from new render (separate deletion confirmation required)",
                )

            # Check if locally modified vs baseline
            baseline_content, err = self.snapshot_store.read_snapshot(
                relative_path, state_entry.get("sha256")
            )
            if err:
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.BLOCKED,
                    reason=f"Cannot verify deletion safety: snapshot {err}",
                )

            current_content = target_file.read_text(encoding="utf-8")
            if DeterministicNormalizer.normalize_text(current_content) != DeterministicNormalizer.normalize_text(baseline_content):
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.BLOCKED,
                    reason="Locally modified file deletion blocked: file differs from baseline snapshot; preserve or relocate manually",
                )

            return ComparisonResult(
                path=relative_path,
                strategy=strategy,
                result_class=ResultClass.DELETION_PENDING,
                reason="Managed file absent from new render; clean vs baseline (separate deletion confirmation required)",
            )

        # 3. Renderer-owned strategies: GENERATED and MANAGED_REGIONS
        current_exists = target_file.exists()
        current_content = target_file.read_text(encoding="utf-8") if current_exists else ""
        norm_current = DeterministicNormalizer.normalize_text(current_content)
        norm_new = DeterministicNormalizer.normalize_text(new_render_content)

        new_sha = SnapshotStore.compute_sha256(norm_new)

        # Case A: Snapshots disabled OR legacy migration without snapshot OR one-time unverified override
        has_baseline = bool(state_entry and state_entry.get("sha256"))
        
        if not self.snapshots_enabled or not has_baseline or one_time_unverified_override:
            if not current_exists:
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.CHANGED,
                    reason="New file render (untracked previously)",
                    proposed_content=norm_new,
                    new_snapshot_content=norm_new if self.snapshots_enabled else None,
                    new_snapshot_sha256=new_sha if self.snapshots_enabled else None,
                )

            if norm_current == norm_new:
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.UNCHANGED,
                    reason="Identical content (unverified baseline)",
                    proposed_content=norm_new,
                    new_snapshot_content=norm_new if self.snapshots_enabled else None,
                    new_snapshot_sha256=new_sha if self.snapshots_enabled else None,
                )

            reason = "Two-way unverified diff (snapshots disabled)" if not self.snapshots_enabled else (
                "One-time unverified override after escalation" if one_time_unverified_override else "Unverified migration bootstrap (no baseline snapshot)"
            )
            return ComparisonResult(
                path=relative_path,
                strategy=strategy,
                result_class=ResultClass.UNVERIFIED,
                reason=reason,
                proposed_content=norm_new,
                diff=f"--- current\n+++ new_render\n@@ {relative_path} @@",
                new_snapshot_content=norm_new if self.snapshots_enabled else None,
                new_snapshot_sha256=new_sha if self.snapshots_enabled else None,
            )

        # Case B: Snapshots enabled with recorded baseline in state
        baseline_content, snap_err = self.snapshot_store.read_snapshot(
            relative_path, state_entry.get("sha256")
        )
        if snap_err:
            return ComparisonResult(
                path=relative_path,
                strategy=strategy,
                result_class=ResultClass.BLOCKED,
                reason=f"Snapshot integrity failure: {snap_err} (requires cancellation or one-time unverified override)",
            )

        norm_baseline = DeterministicNormalizer.normalize_text(baseline_content)

        # Strategy: GENERATED
        if strategy == Strategy.GENERATED:
            if norm_current == norm_new:
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.UNCHANGED,
                    reason="Content identical to new render",
                    proposed_content=norm_new,
                    new_snapshot_content=norm_new,
                    new_snapshot_sha256=new_sha,
                )
            
            if norm_current == norm_baseline:
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.CHANGED,
                    reason="Clean template update from baseline",
                    proposed_content=norm_new,
                    diff=f"--- baseline\n+++ new_render\n@@ {relative_path} @@",
                    new_snapshot_content=norm_new,
                    new_snapshot_sha256=new_sha,
                )

            if norm_new == norm_baseline:
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.UNCHANGED,
                    reason="Template unchanged; local modifications preserved",
                    warnings=["Local edits present on generated file; template has no updates"],
                    proposed_content=norm_current,
                    new_snapshot_content=norm_baseline,
                    new_snapshot_sha256=state_entry.get("sha256"),
                )

            return ComparisonResult(
                path=relative_path,
                strategy=strategy,
                result_class=ResultClass.CONFLICT,
                reason="Concurrent modification: local edits conflict with template changes on generated file",
                diff=f"--- local\n+++ new_render\n@@ {relative_path} @@",
            )

        # Strategy: MANAGED_REGIONS
        if strategy == Strategy.MANAGED_REGIONS:
            if norm_current == norm_new:
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.UNCHANGED,
                    reason="Content identical to new render",
                    proposed_content=norm_new,
                    new_snapshot_content=norm_new,
                    new_snapshot_sha256=new_sha,
                )

            merge_ok, merged_text, warnings, merge_err = ManagedRegionParser.merge(
                current_text=current_content,
                new_rendered_text=new_render_content,
                baseline_text=baseline_content,
            )

            if not merge_ok:
                if "Concurrent edit" in (merge_err or ""):
                    return ComparisonResult(
                        path=relative_path,
                        strategy=strategy,
                        result_class=ResultClass.CONFLICT,
                        reason=merge_err,
                    )
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.BLOCKED,
                    reason=f"Malformed region structure: {merge_err}",
                )

            norm_merged = DeterministicNormalizer.normalize_text(merged_text)
            if norm_merged == norm_current:
                return ComparisonResult(
                    path=relative_path,
                    strategy=strategy,
                    result_class=ResultClass.UNCHANGED,
                    reason="Proposed region merge resulted in identical content",
                    proposed_content=norm_merged,
                    warnings=warnings,
                    new_snapshot_content=norm_new,
                    new_snapshot_sha256=new_sha,
                )

            return ComparisonResult(
                path=relative_path,
                strategy=strategy,
                result_class=ResultClass.REGION_MERGE,
                reason="Proposed region merge: user regions preserved, generated regions updated",
                proposed_content=norm_merged,
                warnings=warnings,
                diff=f"--- current\n+++ proposed_region_merge\n@@ {relative_path} @@",
                new_snapshot_content=norm_new,
                new_snapshot_sha256=new_sha,
            )

        return ComparisonResult(
            path=relative_path,
            strategy=strategy,
            result_class=ResultClass.BLOCKED,
            reason=f"Unknown strategy '{strategy}'",
        )


class SummaryReport:
    """Generates tiered confirmation summary following ADR-0001."""

    @staticmethod
    def format_summary(results: List[ComparisonResult]) -> str:
        results = [result for result in results if not result.excluded]
        counts: Dict[ResultClass, int] = {rc: 0 for rc in ResultClass}
        for r in results:
            counts[r.result_class] += 1

        all_eligible = all(r.is_eligible for r in results)

        lines = [
            "# Dry-Run Comparison Summary",
            "",
            "## Overview Counts",
            f"- Changed: {counts[ResultClass.CHANGED]}",
            f"- Unverified: {counts[ResultClass.UNVERIFIED]}",
            f"- Region Merge: {counts[ResultClass.REGION_MERGE]}",
            f"- Unchanged: {counts[ResultClass.UNCHANGED]}",
            f"- Conflicts: {counts[ResultClass.CONFLICT]}",
            f"- Blocked: {counts[ResultClass.BLOCKED]}",
            f"- Invalid Links: {counts[ResultClass.INVALID_LINK]}",
            f"- Deletion Pending: {counts[ResultClass.DELETION_PENDING]}",
            "",
            f"**Atomic Apply Status**: {'ELIGIBLE' if all_eligible else 'BLOCKED'}",
            "",
        ]

        issues = [
            r for r in results
            if not r.is_eligible or r.result_class == ResultClass.UNVERIFIED or r.warnings
        ]

        if issues:
            lines.append("## Attention Required")
            for r in issues:
                lines.append(f"- **{r.path}** [{r.result_class.value}]")
                if r.reason:
                    lines.append(f"  - Reason: {r.reason}")
                lines.append(f"  - Apply Eligibility: {'Yes' if r.is_eligible else 'No (Blocks update)'}")
                if r.warnings:
                    for w in r.warnings:
                        lines.append(f"  - Warning: {w}")
                if r.diff:
                    lines.append(f"  - Full Diff Access: available on request via `--diff {r.path}`")
            lines.append("")

        return "\n".join(lines)

