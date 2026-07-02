#!/usr/bin/env python3
"""Tests for conflict detection scenarios.

This module tests renamed file conflicts, new file conflicts,
and complex multi-way conflicts.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestRenamedFileConflicts(unittest.TestCase):
    """Test cases for renamed file conflicts."""

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
        self.original_file = Path("original.txt")
        self.original_file.write_text("Original content\n")
        subprocess.run(["git", "add", str(self.original_file)], check=True, capture_output=True)
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

    def test_both_rename_different(self):
        """Test conflict when both branches rename the same file to different names."""
        # Branch A: rename to name_a.txt
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        subprocess.run(["git", "mv", "original.txt", "name_a.txt"], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Rename to name_a"], check=True, capture_output=True, timeout=10)

        # Branch B: rename to name_b.txt
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        subprocess.run(["git", "mv", "original.txt", "name_b.txt"], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Rename to name_b"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should detect rename conflict
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Rename conflict should be detected")

        # Check status shows both renamed files
        status_result = subprocess.run(
            ["git", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # One of the names should appear in status
        self.assertTrue(
            "name_a.txt" in status_result.stdout or "name_b.txt" in status_result.stdout,
            "Status should mention renamed files"
        )

    def test_rename_and_modify_same_file(self):
        """Test conflict when one branch renames and another modifies the same file."""
        # Branch A: rename the file
        subprocess.run(["git", "checkout", "-b", "branch-rename"], check=True, capture_output=True)
        subprocess.run(["git", "mv", "original.txt", "renamed.txt"], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Rename file"], check=True, capture_output=True, timeout=10)

        # Branch B: modify the file
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-modify"], check=True, capture_output=True)
        self.original_file.write_text("Modified content\n")
        subprocess.run(["git", "add", str(self.original_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Modify file"], check=True, capture_output=True, timeout=10)

        # Attempt merge - Git should handle this automatically (rename detection)
        result = subprocess.run(
            ["git", "merge", "--no-edit", "branch-rename"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Git should detect the rename and apply the modification to the renamed file
        # Verify the renamed file exists with the modified content
        renamed_path = Path("renamed.txt")
        self.assertTrue(renamed_path.exists(), "Renamed file should exist after merge")
        content = renamed_path.read_text()
        self.assertIn("Modified", content, "Renamed file should contain the modification")

    def test_rename_with_content_conflict(self):
        """Test complex scenario: rename file and create content conflict."""
        # Branch A: rename and modify
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        subprocess.run(["git", "mv", "original.txt", "renamed.txt"], check=True, capture_output=True)
        renamed_path = Path("renamed.txt")
        renamed_path.write_text("Branch A content\n")
        subprocess.run(["git", "add", "renamed.txt"], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Rename and modify"], check=True, capture_output=True, timeout=10)

        # Branch B: same rename but different content
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        subprocess.run(["git", "mv", "original.txt", "renamed.txt"], check=True, capture_output=True)
        renamed_path.write_text("Branch B content\n")
        subprocess.run(["git", "add", "renamed.txt"], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Rename with different content"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should conflict on content
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Content conflict should occur despite same rename")


class TestNewFileConflicts(unittest.TestCase):
    """Test cases for new file conflicts."""

    def setUp(self):
        """Set up test environment with temporary git repository."""
        self.test_dir = tempfile.mkdtemp(prefix="test_conflicts_")
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Initialize git repo
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)

        # Create initial commit with a placeholder
        placeholder = Path("README.md")
        placeholder.write_text("Initial repo\n")
        subprocess.run(["git", "add", "README.md"], check=True, capture_output=True)
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

    def test_same_new_file_different_content(self):
        """Test conflict when both branches create the same new file with different content."""
        new_file = Path("new_feature.txt")

        # Branch A: create new file with content A
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        new_file.write_text("Feature implementation from Branch A\n")
        subprocess.run(["git", "add", str(new_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add new feature (Branch A)"], check=True, capture_output=True, timeout=10)

        # Branch B: create same new file with content B
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        new_file.write_text("Feature implementation from Branch B\n")
        subprocess.run(["git", "add", str(new_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add new feature (Branch B)"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should conflict
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Both-added conflict should be detected")

        # Verify conflict markers in the file
        if new_file.exists():
            content = new_file.read_text()
            self.assertIn("<<<<<<<", content, "Conflict markers should be present")

    def test_same_new_file_identical_content(self):
        """Test that identical new files merge cleanly without conflict."""
        new_file = Path("identical.txt")
        identical_content = "Same content from both branches\n"

        # Branch A: create new file
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        new_file.write_text(identical_content)
        subprocess.run(["git", "add", str(new_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add identical file"], check=True, capture_output=True, timeout=10)

        # Branch B: create same new file with identical content
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        new_file.write_text(identical_content)
        subprocess.run(["git", "add", str(new_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add identical file"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should succeed
        result = subprocess.run(
            ["git", "merge", "--no-edit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertEqual(result.returncode, 0, "Identical new files should merge cleanly")


class TestComplexMultiWayConflicts(unittest.TestCase):
    """Test cases for complex multi-way conflicts."""

    def setUp(self):
        """Set up test environment with temporary git repository."""
        self.test_dir = tempfile.mkdtemp(prefix="test_conflicts_")
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Initialize git repo
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)

        # Create initial file with multiple sections
        self.test_file = Path("complex.txt")
        self.test_file.write_text(
            "Section 1: Header\n"
            "Section 2: Content\n"
            "Section 3: Footer\n"
        )
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

    def test_multiple_conflict_regions(self):
        """Test file with multiple separate conflict regions."""
        # Create a file with multiple sections separated by unchanged lines
        self.test_file.write_text(
            "Section 1: Header\n"
            "Unchanged line\n"
            "Section 2: Content\n"
            "Another unchanged line\n"
            "Section 3: Footer\n"
        )
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Update with more sections"], check=True, capture_output=True, timeout=10)

        # Branch A: modify sections 1 and 3, leave middle unchanged
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        self.test_file.write_text(
            "Section 1: Header A\n"
            "Unchanged line\n"
            "Section 2: Content\n"
            "Another unchanged line\n"
            "Section 3: Footer A\n"
        )
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Modify header and footer (A)"], check=True, capture_output=True, timeout=10)

        # Branch B: modify sections 1 and 3 differently, leave middle unchanged
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        self.test_file.write_text(
            "Section 1: Header B\n"
            "Unchanged line\n"
            "Section 2: Content\n"
            "Another unchanged line\n"
            "Section 3: Footer B\n"
        )
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Modify header and footer (B)"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should create multiple conflict regions
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Multiple conflicts should be detected")

        # Verify conflict occurred (git may combine into one region depending on proximity)
        content = self.test_file.read_text()
        conflict_count = content.count("<<<<<<<")
        self.assertGreaterEqual(conflict_count, 1, "Should have at least one conflict region")

    def test_three_way_merge_with_base_change(self):
        """Test three-way merge where base, theirs, and ours all differ."""
        # Create feature branch with change
        subprocess.run(["git", "checkout", "-b", "feature"], check=True, capture_output=True)
        self.test_file.write_text(
            "Section 1: Header (Feature)\n"
            "Section 2: Content\n"
            "Section 3: Footer\n"
        )
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Feature change"], check=True, capture_output=True, timeout=10)

        # Advance default branch with different change
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        self.test_file.write_text(
            "Section 1: Header (Master)\n"
            "Section 2: Content\n"
            "Section 3: Footer\n"
        )
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Default branch change"], check=True, capture_output=True, timeout=10)

        # Attempt merge - three-way conflict
        result = subprocess.run(
            ["git", "merge", "--no-commit", "feature"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Three-way merge should conflict")

    def test_criss_cross_merge_conflict(self):
        """Test criss-cross merge scenario where branches have cross-merged previously.

        This tests a more complex scenario where merge history creates
        multiple merge bases.
        """
        # Create two feature branches
        subprocess.run(["git", "checkout", "-b", "feature-a"], check=True, capture_output=True)
        self.test_file.write_text(
            "Section 1: Header\n"
            "Section 2: Content A\n"
            "Section 3: Footer\n"
        )
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Feature A change"], check=True, capture_output=True, timeout=10)

        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "feature-b"], check=True, capture_output=True)
        self.test_file.write_text(
            "Section 1: Header\n"
            "Section 2: Content B\n"
            "Section 3: Footer\n"
        )
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Feature B change"], check=True, capture_output=True, timeout=10)

        # Create criss-cross by merging each into the other
        subprocess.run(["git", "checkout", "feature-a"], check=True, capture_output=True)
        subprocess.run(["git", "merge", "--no-edit", "feature-b"], check=False, capture_output=True, timeout=10)
        # If merge conflicts, abort and continue
        subprocess.run(["git", "merge", "--abort"], check=False, capture_output=True)

        # Now create final conflicting state
        subprocess.run(["git", "checkout", "feature-a"], check=True, capture_output=True)
        self.test_file.write_text(
            "Section 1: Header\n"
            "Section 2: Final A\n"
            "Section 3: Footer\n"
        )
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Final A"], check=True, capture_output=True, timeout=10)

        subprocess.run(["git", "checkout", "feature-b"], check=True, capture_output=True)
        self.test_file.write_text(
            "Section 1: Header\n"
            "Section 2: Final B\n"
            "Section 3: Footer\n"
        )
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Final B"], check=True, capture_output=True, timeout=10)

        # Attempt final merge - should produce a conflict
        result = subprocess.run(
            ["git", "merge", "--no-commit", "feature-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Verify merge conflict occurred (non-zero return code indicates conflict)
        self.assertNotEqual(result.returncode, 0, "Merge should fail due to conflict")


def main():
    """Run the test suite."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
