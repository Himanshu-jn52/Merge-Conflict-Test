#!/usr/bin/env python3
"""Tests for basic merge conflict scenarios.

This module tests overlapping edits, deleted vs modified conflicts,
binary file conflicts, and whitespace-only conflicts.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


class TestOverlappingEdits(unittest.TestCase):
    """Test cases for overlapping edits to same lines."""

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
        self.test_file = Path("test_file.txt")
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

    def test_same_line_different_content(self):
        """Test conflict when two branches modify the same line with different content."""
        # Branch A: modify line 2
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2 - Branch A change\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch A changes"], check=True, capture_output=True, timeout=10)

        # Branch B: modify same line differently
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2 - Branch B change\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch B changes"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should fail with conflict
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Merge should fail due to conflict")

        # Verify conflict markers exist
        content = self.test_file.read_text()
        self.assertIn("<<<<<<<", content, "Conflict markers should be present")
        self.assertIn(">>>>>>>", content, "Conflict markers should be present")
        self.assertIn("=======", content, "Conflict markers should be present")

    def test_adjacent_line_modifications(self):
        """Test that adjacent line modifications merge cleanly without conflict."""
        # Branch A: modify line 1
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        self.test_file.write_text("Line 1 - Branch A\nLine 2\nLine 3\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch A changes"], check=True, capture_output=True, timeout=10)

        # Branch B: modify line 3
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\nLine 2\nLine 3 - Branch B\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch B changes"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should succeed
        result = subprocess.run(
            ["git", "merge", "--no-edit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertEqual(result.returncode, 0, "Adjacent line changes should merge cleanly")

        # Verify both changes are present
        content = self.test_file.read_text()
        self.assertIn("Branch A", content)
        self.assertIn("Branch B", content)


class TestDeleteModifyConflicts(unittest.TestCase):
    """Test cases for deleted vs modified file conflicts."""

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
        self.test_file = Path("deletable.txt")
        self.test_file.write_text("Original content\n")
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

    def test_delete_vs_modify_conflict(self):
        """Test conflict when one branch deletes a file and another modifies it."""
        # Branch A: delete the file
        subprocess.run(["git", "checkout", "-b", "branch-delete"], check=True, capture_output=True)
        self.test_file.unlink()
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Delete file"], check=True, capture_output=True, timeout=10)

        # Branch B: modify the file
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-modify"], check=True, capture_output=True)
        self.test_file.write_text("Modified content\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Modify file"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should fail with conflict
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-delete"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Merge should fail due to delete-modify conflict")

        # Check git status for conflict indication
        status_result = subprocess.run(
            ["git", "status", "--short"],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Status should show conflict markers (DU or UD)
        self.assertIn(str(self.test_file), status_result.stdout)

    def test_modify_vs_delete_reverse(self):
        """Test conflict from opposite perspective (modify branch merging delete)."""
        # Branch A: modify the file
        subprocess.run(["git", "checkout", "-b", "branch-modify"], check=True, capture_output=True)
        self.test_file.write_text("Modified content\n")
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Modify file"], check=True, capture_output=True, timeout=10)

        # Branch B: delete the file
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-delete"], check=True, capture_output=True)
        self.test_file.unlink()
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Delete file"], check=True, capture_output=True, timeout=10)

        # Merge from delete branch perspective
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-modify"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Merge should fail due to conflict")


class TestBinaryFileConflicts(unittest.TestCase):
    """Test cases for binary file conflicts."""

    def setUp(self):
        """Set up test environment with temporary git repository."""
        self.test_dir = tempfile.mkdtemp(prefix="test_conflicts_")
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Initialize git repo
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)

        # Create initial binary file (simulate with random bytes)
        self.binary_file = Path("image.bin")
        self.binary_file.write_bytes(b'\x89PNG\x0d\x0a\x1a\x0a' + b'\x00' * 100)
        subprocess.run(["git", "add", str(self.binary_file)], check=True, capture_output=True)
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

    def test_binary_file_conflict(self):
        """Test conflict when two branches modify a binary file differently."""
        # Branch A: modify binary file
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        self.binary_file.write_bytes(b'\x89PNG\x0d\x0a\x1a\x0a' + b'\x01' * 100)
        subprocess.run(["git", "add", str(self.binary_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch A binary change"], check=True, capture_output=True, timeout=10)

        # Branch B: modify binary file differently
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        self.binary_file.write_bytes(b'\x89PNG\x0d\x0a\x1a\x0a' + b'\x02' * 100)
        subprocess.run(["git", "add", str(self.binary_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Branch B binary change"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should fail with conflict
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Binary file merge should conflict")

        # Check that git recognizes this as a binary conflict
        status_result = subprocess.run(
            ["git", "status"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertIn(str(self.binary_file), status_result.stdout)


class TestWhitespaceConflicts(unittest.TestCase):
    """Test cases for whitespace-only conflicts."""

    def setUp(self):
        """Set up test environment with temporary git repository."""
        self.test_dir = tempfile.mkdtemp(prefix="test_conflicts_")
        self.original_dir = os.getcwd()
        os.chdir(self.test_dir)

        # Initialize git repo
        subprocess.run(["git", "init"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@example.com"], check=True, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], check=True, capture_output=True)
        # Ensure whitespace differences trigger conflicts
        subprocess.run(["git", "config", "merge.renormalize", "false"], check=True, capture_output=True)

        # Create initial file with specific whitespace
        self.test_file = Path("whitespace.txt")
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

    def test_trailing_whitespace_conflict(self):
        """Test conflict when branches add different trailing whitespace."""
        # Branch A: add trailing spaces
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        self.test_file.write_text("Line 1  \nLine 2\nLine 3\n")  # Two spaces at end
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add trailing spaces"], check=True, capture_output=True, timeout=10)

        # Branch B: add trailing tabs
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\t\nLine 2\nLine 3\n")  # Tab at end
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Add trailing tab"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should fail with conflict
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Whitespace differences should cause conflict")

    def test_indentation_conflict(self):
        """Test conflict when branches use different indentation (tabs vs spaces)."""
        # Branch A: use tabs for indentation
        subprocess.run(["git", "checkout", "-b", "branch-a"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\n\tIndented line\nLine 3\n")  # Tab indent
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Use tab indentation"], check=True, capture_output=True, timeout=10)

        # Branch B: use spaces for indentation
        subprocess.run(["git", "checkout", self.default_branch], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "-b", "branch-b"], check=True, capture_output=True)
        self.test_file.write_text("Line 1\n    Indented line\nLine 3\n")  # Space indent
        subprocess.run(["git", "add", str(self.test_file)], check=True, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Use space indentation"], check=True, capture_output=True, timeout=10)

        # Attempt merge - should fail with conflict
        result = subprocess.run(
            ["git", "merge", "--no-commit", "branch-a"],
            capture_output=True,
            text=True,
            timeout=10
        )

        self.assertNotEqual(result.returncode, 0, "Indentation differences should cause conflict")


def main():
    """Run the test suite."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
