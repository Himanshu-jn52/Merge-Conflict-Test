#!/usr/bin/env python3
"""Tests for conflict resolution scenarios.

This module tests large file conflicts and resolution verification strategies.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestLargeFileConflicts(unittest.TestCase):
    """Test cases for large file conflicts."""

    def setUp(self):
        """Set up test environment with temporary git repository."""
        self.test_dir = tempfile.mkdtemp(prefix="test_conflicts_")
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Initialize git repo
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)

        # Create initial large file (1000+ lines)
        self.large_file = Path("large_file.txt")
        self._create_large_file(1000)
        subprocess.run(["git", "add", str(self.large_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True, capture_output=True, timeout=10)

        # Get the default branch name dynamically
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True
        )
        self.default_branch = result.stdout.strip()

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        subprocess.run(["rm", "-rf", self.test_dir], check=False, timeout=10)

    def _create_large_file(self, num_lines: int, prefix: str = "") -> None:
        """Create a large file with specified number of lines.

        :param num_lines: Number of lines to generate
        :param prefix: Optional prefix for each line
        """
        lines = [f"{prefix}Line {i}: Some content here\n" for i in range(num_lines)]
        self.large_file.write_text("".join(lines))

    def test_large_file_conflict_single_line(self):
        """Test conflict in a large file with single line difference."""
        # Branch A: modify line 500
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        content = self.large_file.read_text()
        lines = content.split("\n")
        lines[500] = "Line 500: Branch A modification"
        self.large_file.write_text("\n".join(lines))
        subprocess.run(["git", "add", str(self.large_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch A: modify line 500"], check=True, capture_output=True, timeout=10)

        # Branch B: modify same line differently
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        content = self.large_file.read_text()
        lines = content.split("\n")
        lines[500] = "Line 500: Branch B modification"
        self.large_file.write_text("\n".join(lines))
        subprocess.run(["git", "add", str(self.large_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch B: modify line 500"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should conflict
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Large file merge should conflict")

        # Verify conflict markers exist
        content = self.large_file.read_text()
        self.assertIn("<<<<<<<", content)
        self.assertIn(">>>>>>>", content)

    def test_large_file_multiple_conflicts(self):
        """Test large file with multiple conflict regions."""
        # Branch A: modify lines 100, 500, 900
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        content = self.large_file.read_text()
        lines = content.split("\n")
        lines[100] = "Line 100: Branch A"
        lines[500] = "Line 500: Branch A"
        lines[900] = "Line 900: Branch A"
        self.large_file.write_text("\n".join(lines))
        subprocess.run(["git", "add", str(self.large_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch A: multiple changes"], check=True, capture_output=True, timeout=10)

        # Branch B: modify same lines differently
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        content = self.large_file.read_text()
        lines = content.split("\n")
        lines[100] = "Line 100: Branch B"
        lines[500] = "Line 500: Branch B"
        lines[900] = "Line 900: Branch B"
        self.large_file.write_text("\n".join(lines))
        subprocess.run(["git", "add", str(self.large_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch B: multiple changes"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should have multiple conflicts
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Large file should have multiple conflicts")

        # Verify multiple conflict regions
        content = self.large_file.read_text()
        conflict_count = content.count("<<<<<<<")
        self.assertGreaterEqual(conflict_count, 3, "Should have at least 3 conflict regions")

    def test_large_file_performance(self):
        """Test that large file conflicts are handled efficiently."""
        # Create a very large file (5000 lines)
        self.large_file.write_text("")
        self._create_large_file(5000)
        subprocess.run(["git", "add", str(self.large_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Very large file"], check=True, capture_output=True, timeout=10)

        # Branch A: modify near end
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        content = self.large_file.read_text()
        lines = content.split("\n")
        lines[4999] = "Line 4999: Branch A modification"
        self.large_file.write_text("\n".join(lines))
        subprocess.run(["git", "add", str(self.large_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch A change"], check=True, capture_output=True, timeout=10)

        # Branch B: modify same line
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        content = self.large_file.read_text()
        lines = content.split("\n")
        lines[4999] = "Line 4999: Branch B modification"
        self.large_file.write_text("\n".join(lines))
        subprocess.run(["git", "add", str(self.large_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch B change"], check=True, capture_output=True, timeout=10)

        # Attempt merge with timeout to ensure performance
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10  # Should complete within 10 seconds
        )

        self.assertNotEqual(result.returncode, 0, "Merge should conflict")


class TestConflictResolutionStrategies(unittest.TestCase):
    """Test cases for verifying conflict resolution strategies."""

    def setUp(self):
        """Set up test environment with temporary git repository."""
        self.test_dir = tempfile.mkdtemp(prefix="test_conflicts_")
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Initialize git repo
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)

        # Create initial file
        self.test_file = Path("conflict_file.txt")
        self.test_file.write_text("Line 1\nLine 2\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], check=True, capture_output=True, timeout=10)

        # Get the default branch name dynamically
        result = subprocess.run(
            ["git", "symbolic-ref", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True
        )
        self.default_branch = result.stdout.strip()

    def tearDown(self):
        """Clean up test environment."""
        os.chdir(self.original_dir)
        subprocess.run(["rm", "-rf", self.test_dir], check=False, timeout=10)

    def test_conflict_resolution_ours(self):
        """Test resolving conflict by choosing 'ours' strategy."""
        # Create conflict
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2 - Branch A\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch A change"], check=True, capture_output=True, timeout=10)

        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2 - Branch B\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch B change"], check=True, capture_output=True, timeout=10)

        # Merge with conflict
        subprocess.run(["git", "merge", "--no-commit", "branch-a"], check=False, capture_output=True)

        # Resolve using 'ours' strategy
        subprocess.run(["git", "checkout", "--ours", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)

        # Verify resolution used our version
        content = self.test_file.read_text()
        self.assertIn("Branch B", content, "Should contain our version (Branch B)")
        self.assertNotIn("Branch A", content, "Should not contain their version")
        self.assertNotIn("<<<<<<<", content, "Should not have conflict markers")

    def test_conflict_resolution_theirs(self):
        """Test resolving conflict by choosing 'theirs' strategy."""
        # Create conflict
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2 - Branch A\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch A change"], check=True, capture_output=True, timeout=10)

        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2 - Branch B\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch B change"], check=True, capture_output=True, timeout=10)

        # Merge with conflict
        subprocess.run(["git", "merge", "--no-commit", "branch-a"], check=False, capture_output=True)

        # Resolve using 'theirs' strategy
        subprocess.run(["git", "checkout", "--theirs", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)

        # Verify resolution used their version
        content = self.test_file.read_text()
        self.assertIn("Branch A", content, "Should contain their version (Branch A)")
        self.assertNotIn("Branch B", content, "Should not contain our version")
        self.assertNotIn("<<<<<<<", content, "Should not have conflict markers")

    def test_conflict_resolution_manual(self):
        """Test manual conflict resolution by editing the file."""
        # Create conflict
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2 - Branch A\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch A change"], check=True, capture_output=True, timeout=10)

        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2 - Branch B\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch B change"], check=True, capture_output=True, timeout=10)

        # Merge with conflict
        subprocess.run(["git", "merge", "--no-commit", "branch-a"], check=False, capture_output=True)

        # Manually resolve by creating merged version
        self.test_file.write_text("Line 1\nLine 2 - Merged from A and B\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)

        # Verify manual resolution
        content = self.test_file.read_text()
        self.assertIn("Merged from A and B", content, "Should contain manual resolution")
        self.assertNotIn("<<<<<<<", content, "Should not have conflict markers")

    def test_merge_abort(self):
        """Test aborting a merge with conflicts."""
        # Create conflict
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2 - Branch A\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch A change"], check=True, capture_output=True, timeout=10)

        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        original_content = "Line 1\nLine 2 - Branch B\nLine 3\n"
        self.test_file.write_text(original_content)
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch B change"], check=True, capture_output=True, timeout=10)

        # Merge with conflict
        subprocess.run(["git", "merge", "--no-commit", "branch-a"], check=False, capture_output=True)

        # Abort merge
        result = subprocess.run(
            ["git", "merge", "--abort"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertEqual(result.returncode, 0, "Merge abort should succeed")

        # Verify file is back to original state
        content = self.test_file.read_text()
        self.assertEqual(content, original_content, "File should be restored to pre-merge state")
        self.assertNotIn("<<<<<<<", content, "Conflict markers should be removed")

    def test_conflict_markers_verification(self):
        """Test verification that conflict markers are properly detected."""
        # Create conflict
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2 - Branch A\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch A change"], check=True, capture_output=True, timeout=10)

        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2 - Branch B\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch B change"], check=True, capture_output=True, timeout=10)

        # Merge with conflict
        subprocess.run(["git", "merge", "--no-commit", "branch-a"], check=False, capture_output=True)

        # Verify all three types of conflict markers
        content = self.test_file.read_text()
        self.assertIn("<<<<<<<", content, "Should have conflict start marker")
        self.assertIn("=======", content, "Should have conflict separator")
        self.assertIn(">>>>>>>", content, "Should have conflict end marker")

        # Verify markers appear in correct order
        start_pos = content.find("<<<<<<<")
        sep_pos = content.find("=======")
        end_pos = content.find(">>>>>>>")

        self.assertLess(start_pos, sep_pos, "Start marker should come before separator")
        self.assertLess(sep_pos, end_pos, "Separator should come before end marker")


def main():
    """Run the test suite."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
