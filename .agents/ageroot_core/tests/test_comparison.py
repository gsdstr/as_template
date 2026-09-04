"""Comprehensive tests for safety-first comparison strategy in Ageroot."""

import os
from pathlib import Path
import tempfile
import unittest

from ageroot_core.comparison import (
    ComparisonResult,
    DeterministicNormalizer,
    ManagedRegionParser,
    ResultClass,
    SnapshotStore,
    Strategy,
    SummaryReport,
    ThreeWayComparisonEngine,
)


class TestDeterministicNormalizer(unittest.TestCase):
    def test_crlf_and_trailing_whitespace(self):
        raw = "line 1   \r\nline 2\t\r\n\r\n\r\n\r\nline 3   \r\n"
        norm = DeterministicNormalizer.normalize_text(raw)
        self.assertEqual(norm, "line 1\nline 2\n\nline 3\n")

    def test_empty_string(self):
        self.assertEqual(DeterministicNormalizer.normalize_text(""), "")
        self.assertEqual(DeterministicNormalizer.normalize_text("   \r\n\n"), "")

    def test_generated_by_provenance_is_metadata_only(self):
        old = "<!-- generated-by: ageroot; template: 0.1.0; commit: abc1234; rendered-at: 2026-09-03T00:00:00Z -->\n# Title\n"
        new = "<!-- generated-by: ageroot; template: 0.1.1; commit: def5678; rendered-at: 2026-09-04T00:00:00Z -->\n# Title\n"
        self.assertEqual(DeterministicNormalizer.normalize_text(old), DeterministicNormalizer.normalize_text(new))


class TestSnapshotStore(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.store = SnapshotStore(self.root)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_write_and_read_snapshot_with_integrity(self):
        content = "hello world\n"
        sha = self.store.write_snapshot_atomic("sub/file.txt", content)
        self.assertEqual(sha, SnapshotStore.compute_sha256(content))

        # Read ok
        read_content, err = self.store.read_snapshot("sub/file.txt", sha)
        self.assertIsNone(err)
        self.assertEqual(read_content, content)

        # Corrupt check
        read_content, err = self.store.read_snapshot("sub/file.txt", "wrong_hash")
        self.assertEqual(err, "corrupt")
        self.assertIsNone(read_content)

        # Missing check
        read_content, err = self.store.read_snapshot("missing.txt", sha)
        self.assertEqual(err, "missing")
        self.assertIsNone(read_content)


class TestManagedRegionParser(unittest.TestCase):
    def test_valid_region_parsing(self):
        text = (
            "# Title\n\n"
            "<!-- caveman-begin -->\n"
            "caveman content\n"
            "<!-- caveman-end -->\n\n"
            "<!-- region:custom-user kind:user -->\n"
            "my custom user rules\n"
            "<!-- endregion:custom-user -->\n"
        )
        ok, segs, err = ManagedRegionParser.parse_structure(text)
        self.assertTrue(ok)
        self.assertIsNone(err)
        # Expected segments: 1. unmanaged "# Title", 2. caveman region, 3. custom-user region
        self.assertTrue(any(s["type"] == "region" and s["name"] == "caveman" for s in segs))
        self.assertTrue(any(s["type"] == "region" and s["name"] == "custom-user" for s in segs))

    def test_malformed_region_unpaired(self):
        text = "# Title\n<!-- caveman-begin -->\nno end marker"
        ok, segs, err = ManagedRegionParser.parse_structure(text)
        self.assertFalse(ok)
        self.assertIn("Unclosed region", err)

    def test_malformed_region_nested(self):
        text = (
            "<!-- caveman-begin -->\n"
            "<!-- rtk-begin -->\n"
            "<!-- rtk-end -->\n"
            "<!-- caveman-end -->\n"
        )
        ok, segs, err = ManagedRegionParser.parse_structure(text)
        self.assertFalse(ok)
        self.assertIn("Nested region", err)

    def test_region_merge_preserves_user_and_updates_generated(self):
        base = (
            "<!-- header-begin -->\nv1.0\n<!-- header-end -->\n"
            "<!-- user-notes-begin -->\nmy old note\n<!-- user-notes-end -->\n"
        )
        current = (
            "<!-- header-begin -->\nv1.0\n<!-- header-end -->\n"
            "<!-- user-notes-begin -->\nmy updated note\n<!-- user-notes-end -->\n"
        )
        new_render = (
            "<!-- header-begin -->\nv2.0\n<!-- header-end -->\n"
            "<!-- user-notes-begin -->\ndefault template note\n<!-- user-notes-end -->\n"
        )
        ok, merged, warnings, err = ManagedRegionParser.merge(current, new_render, base)
        self.assertTrue(ok)
        self.assertIn("v2.0", merged)
        self.assertIn("my updated note", merged)
        self.assertNotIn("default template note", merged)
        self.assertTrue(any("user-notes" in w for w in warnings))

    def test_concurrent_edit_in_generated_region_is_conflict(self):
        base = "<!-- header-begin -->\nv1.0\n<!-- header-end -->\n"
        current = "<!-- header-begin -->\nv1.0-custom-edit\n<!-- header-end -->\n"
        new_render = "<!-- header-begin -->\nv2.0\n<!-- header-end -->\n"
        ok, merged, warnings, err = ManagedRegionParser.merge(current, new_render, base)
        self.assertFalse(ok)
        self.assertIn("Concurrent edit", err)


class TestThreeWayComparisonEngine(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp_dir.name)
        self.store = SnapshotStore(self.root)
        self.engine = ThreeWayComparisonEngine(self.root, snapshots_enabled=True, snapshot_store=self.store)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_planning_path_is_excluded_from_comparison_and_reporting(self):
        result = self.engine.compare_path(".planning/test/task_plan.md", Strategy.GENERATED, "changed\n")
        self.assertTrue(result.excluded)
        self.assertEqual(result.result_class, ResultClass.UNCHANGED)
        self.assertNotIn(".planning/test/task_plan.md", SummaryReport.format_summary([result]))

    def test_clean_generated_update(self):
        rel_path = ".agents/AGENTS.md"
        base_text = "# Title\n"
        new_text = "# Title\n\nUpdated.\n"

        sha = self.store.write_snapshot_atomic(rel_path, base_text)
        (self.root / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel_path).write_text(base_text)

        res = self.engine.compare_path(
            rel_path,
            Strategy.GENERATED,
            new_text,
            state_entry={"sha256": sha},
        )
        self.assertEqual(res.result_class, ResultClass.CHANGED)
        self.assertTrue(res.is_eligible)

    def test_generated_file_conflict_when_locally_modified(self):
        rel_path = ".agents/AGENTS.md"
        base_text = "# Title\n"
        curr_text = "# Title\nLocal change\n"
        new_text = "# Title\nUpstream change\n"

        sha = self.store.write_snapshot_atomic(rel_path, base_text)
        (self.root / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel_path).write_text(curr_text)

        res = self.engine.compare_path(
            rel_path,
            Strategy.GENERATED,
            new_text,
            state_entry={"sha256": sha},
        )
        self.assertEqual(res.result_class, ResultClass.CONFLICT)
        self.assertFalse(res.is_eligible)

    def test_snapshots_disabled_returns_unverified(self):
        engine_no_snap = ThreeWayComparisonEngine(self.root, snapshots_enabled=False)
        rel_path = ".agents/PREFERENCES.md"
        curr_text = "pref 1\n"
        new_text = "pref 2\n"

        (self.root / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel_path).write_text(curr_text)

        res = engine_no_snap.compare_path(
            rel_path,
            Strategy.GENERATED,
            new_text,
            state_entry=None,
        )
        self.assertEqual(res.result_class, ResultClass.UNVERIFIED)
        self.assertTrue(res.is_eligible)

    def test_snapshot_corruption_blocks_and_escalates(self):
        rel_path = ".agents/AGENTS.md"
        base_text = "# Baseline\n"
        (self.root / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (self.root / rel_path).write_text(base_text)

        # Snapshot file has modified content vs expected state sha
        self.store.write_snapshot_atomic(rel_path, "corrupted content")
        expected_sha = SnapshotStore.compute_sha256(base_text)

        res = self.engine.compare_path(
            rel_path,
            Strategy.GENERATED,
            "# New Render\n",
            state_entry={"sha256": expected_sha},
        )
        self.assertEqual(res.result_class, ResultClass.BLOCKED)
        self.assertIn("corrupt", res.reason)
        self.assertFalse(res.is_eligible)

        # One-time unverified override allows progress as UNVERIFIED
        res_override = self.engine.compare_path(
            rel_path,
            Strategy.GENERATED,
            "# New Render\n",
            state_entry={"sha256": expected_sha},
            one_time_unverified_override=True,
        )
        self.assertEqual(res_override.result_class, ResultClass.UNVERIFIED)
        self.assertTrue(res_override.is_eligible)

    def test_external_link_validation(self):
        rel_link = ".agents/skills/planning"
        target = self.root / ".skills-manager" / "planning"
        target.mkdir(parents=True, exist_ok=True)

        link_path = self.root / rel_link
        link_path.parent.mkdir(parents=True, exist_ok=True)
        link_path.symlink_to(target)

        res = self.engine.compare_path(
            rel_link,
            Strategy.EXTERNAL_LINK,
            expected_link_target=str(target),
        )
        self.assertEqual(res.result_class, ResultClass.UNCHANGED)

    def test_deletion_gating(self):
        rel_path = ".agents/old_file.md"
        base_text = "original\n"
        sha = self.store.write_snapshot_atomic(rel_path, base_text)

        file_path = self.root / rel_path
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Clean deletion -> DELETION_PENDING
        file_path.write_text(base_text)
        res = self.engine.compare_path(
            rel_path,
            Strategy.GENERATED,
            None,  # absent from new render
            state_entry={"sha256": sha},
        )
        self.assertEqual(res.result_class, ResultClass.DELETION_PENDING)
        self.assertFalse(res.is_eligible)

        # 2. Locally modified deletion -> BLOCKED
        file_path.write_text("locally modified\n")
        res_modified = self.engine.compare_path(
            rel_path,
            Strategy.GENERATED,
            None,
            state_entry={"sha256": sha},
        )
        self.assertEqual(res_modified.result_class, ResultClass.BLOCKED)
        self.assertIn("Locally modified", res_modified.reason)
        self.assertFalse(res_modified.is_eligible)


class TestSummaryReport(unittest.TestCase):
    def test_summary_formatting(self):
        results = [
            ComparisonResult(
                path=".agents/AGENTS.md",
                strategy=Strategy.GENERATED,
                result_class=ResultClass.CHANGED,
            ),
            ComparisonResult(
                path=".agents/SETUP.md",
                strategy=Strategy.GENERATED,
                result_class=ResultClass.UNCHANGED,
            ),
            ComparisonResult(
                path=".agents/rules.md",
                strategy=Strategy.GENERATED,
                result_class=ResultClass.CONFLICT,
                reason="Concurrent edits",
                diff="some diff",
            ),
        ]
        summary = SummaryReport.format_summary(results)
        self.assertIn("**Atomic Apply Status**: BLOCKED", summary)
        self.assertIn("- Changed: 1", summary)
        self.assertIn("- Unchanged: 1", summary)
        self.assertIn("- Conflicts: 1", summary)
        self.assertIn("Attention Required", summary)
        self.assertIn(".agents/rules.md", summary)
        self.assertIn("Full Diff Access", summary)


if __name__ == "__main__":
    unittest.main()

