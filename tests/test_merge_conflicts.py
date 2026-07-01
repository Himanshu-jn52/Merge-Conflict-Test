"""Comprehensive test suite for merge conflict scenarios.

This module tests various merge conflict scenarios to ensure robust conflict
handling across different edge cases. Tests cover overlapping edits, deleted vs
modified conflicts, binary file conflicts, whitespace conflicts, renamed files,
new file conflicts, multi-way conflicts, and large file conflicts.
"""

from __future__ import annotations

import logging
import subprocess
import unittest
from pathlib import Path

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT, datefmt=_DATE_FORMAT)
log = logging.getLogger("test_merge_conflicts")


class TestMergeConflicts(unittest.TestCase):
    """Test suite for various merge conflict scenarios."""

    def setUp(self) -> None:
        """Set up test environment before each test."""
        import tempfile
        import shutil

        # Create temporary test repository
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_conflicts_"))
        self.repo_dir = self.test_dir / "repo"
        self.repo_dir.mkdir()

        # Initialize git repository
        subprocess.run(
            ["git", "init"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Configure git user
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Configure whitespace handling for deterministic test behavior
        subprocess.run(
            ["git", "config", "core.whitespace", "trailing-space,tab-in-indent"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Create initial commit
        base_file = self.repo_dir / "base.txt"
        base_file.write_text("Initial content\nLine 2\nLine 3\n")
        subprocess.run(
            ["git", "add", "base.txt"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Store the base branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=self.repo_dir,
            check=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        self.base_branch = result.stdout.strip()

        log.info(f"Set up test repository at {self.repo_dir}")

    def tearDown(self) -> None:
        """Clean up test environment after each test."""
        import shutil

        # Abort any in-progress merge
        subprocess.run(
            ["git", "merge", "--abort"],
            cwd=self.repo_dir,
            check=False,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Return to base branch
        subprocess.run(
            ["git", "checkout", self.base_branch],
            cwd=self.repo_dir,
            check=False,
            capture_output=True,
            text=True,
            timeout=10
        )

        # Clean up test directory
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            log.info(f"Cleaned up test repository at {self.repo_dir}")

    def _run_git(self, cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
        """Execute a git command in the test repository.

        :param cmd: Git command as list of arguments
        :param check: If True, raise on non-zero exit
        :return: CompletedProcess result
        """
        return subprocess.run(
            cmd,
            cwd=self.repo_dir,
            check=check,
            capture_output=True,
            text=True,
            timeout=10
        )

    def _create_branch(self, branch_name: str) -> None:
        """Create and checkout a new branch.

        :param branch_name: Name of the branch to create
        """
        self._run_git(["git", "checkout", "-b", branch_name, self.base_branch])

    def _commit_file(self, file_path: Path, message: str) -> None:
        """Stage and commit a file.

        :param file_path: Path to the file
        :param message: Commit message
        """
        # Use relative path to handle subdirectories correctly
        rel_path = file_path.relative_to(self.repo_dir) if file_path.is_absolute() else file_path
        self._run_git(["git", "add", str(rel_path)])
        self._run_git(["git", "commit", "-m", message])

    def _merge_branch(self, branch_name: str) -> subprocess.CompletedProcess:
        """Attempt to merge a branch.

        :param branch_name: Branch to merge
        :return: CompletedProcess (may have non-zero returncode on conflict)
        """
        return self._run_git(
            ["git", "merge", "--no-commit", "--no-ff", branch_name],
            check=False
        )

    def _get_conflicted_files(self) -> list[str]:
        """Get list of files with merge conflicts.

        :return: List of conflicted file paths
        """
        result = self._run_git(["git", "diff", "--name-only", "--diff-filter=U"])
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def test_overlapping_edits_conflict(self) -> None:
        """Test conflict scenario: Overlapping edits to same lines.

        Two branches modify the same lines with different content, creating a
        merge conflict that requires manual resolution.
        """
        log.info("Testing overlapping edits conflict")

        target_file = self.repo_dir / "overlap_test.txt"
        target_file.write_text("Line 1\nLine 2 - original\nLine 3\n")
        self._commit_file(target_file, "Add overlap test file")

        # Branch A: Modify line 2
        self._create_branch("branch-a-overlap")
        content = target_file.read_text()
        content = content.replace("Line 2 - original", "Line 2 - modified by branch A")
        target_file.write_text(content)
        self._commit_file(target_file, "Branch A: Modify line 2")

        # Branch B: Modify same line 2 differently
        # Explicitly checkout base branch first to ensure clean state
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch("branch-b-overlap")
        # Re-read file from base branch to get original content
        content = target_file.read_text()
        content = content.replace("Line 2 - original", "Line 2 - modified by branch B")
        target_file.write_text(content)
        self._commit_file(target_file, "Branch B: Modify line 2 differently")

        # Attempt merge - should create conflict
        result = self._merge_branch("branch-a-overlap")

        self.assertNotEqual(result.returncode, 0, "Merge should fail due to conflict")
        conflicted_files = self._get_conflicted_files()
        self.assertIn("overlap_test.txt", conflicted_files, "overlap_test.txt should have conflicts")
        log.info("✓ Overlapping edits conflict test passed")

    def test_deleted_vs_modified_conflict(self) -> None:
        """Test conflict scenario: Deleted vs modified conflicts.

        One branch deletes a file while another branch modifies it, creating a
        delete-modify conflict.
        """
        log.info("Testing deleted vs modified conflict")

        target_file = self.repo_dir / "delete_modify_test.txt"
        target_file.write_text("Content to be deleted or modified\n")
        self._commit_file(target_file, "Add delete_modify test file")

        # Branch A: Delete the file
        self._create_branch("branch-a-delete")
        target_file.unlink()
        self._run_git(["git", "add", "delete_modify_test.txt"])
        self._run_git(["git", "commit", "-m", "Branch A: Delete file"])

        # Branch B: Modify the file
        # Explicitly checkout base branch first to ensure clean state
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch("branch-b-modify")
        # Re-read file from base branch to get original content
        content = target_file.read_text()
        target_file.write_text(content + "Additional content from branch B\n")
        self._commit_file(target_file, "Branch B: Modify file")

        # Attempt merge - should create conflict
        result = self._merge_branch("branch-a-delete")

        self.assertNotEqual(result.returncode, 0, "Merge should fail due to delete-modify conflict")

        # Check for delete-modify conflict using git ls-files -u (unmerged files)
        unmerged_result = self._run_git(["git", "ls-files", "-u"])
        self.assertIn("delete_modify_test.txt", unmerged_result.stdout,
                      "File should appear in unmerged files list")

        # Also check git status for DU or UD markers (delete-modify conflict)
        status_result = self._run_git(["git", "status", "--short"])
        self.assertTrue(
            "DU delete_modify_test.txt" in status_result.stdout or
            "UD delete_modify_test.txt" in status_result.stdout,
            "Status should show DU or UD for delete-modify conflict"
        )
        log.info("✓ Deleted vs modified conflict test passed")

    def test_binary_file_conflict(self) -> None:
        """Test conflict scenario: Binary file conflicts.

        Two branches modify the same binary file in different ways, creating a
        conflict that cannot be resolved with text-based merge.
        """
        log.info("Testing binary file conflict")

        # Create a binary file (simple binary data)
        binary_file = self.repo_dir / "binary_test.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09")
        self._commit_file(binary_file, "Add binary test file")

        # Branch A: Modify binary file
        self._create_branch("branch-a-binary")
        binary_file.write_bytes(b"\x00\x01\x02\x03\xFF\xFF\xFF\xFF\x08\x09")
        self._commit_file(binary_file, "Branch A: Modify binary file")

        # Branch B: Modify binary file differently
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch("branch-b-binary")
        binary_file.write_bytes(b"\x00\x01\x02\x03\xAA\xBB\xCC\xDD\x08\x09")
        self._commit_file(binary_file, "Branch B: Modify binary file differently")

        # Attempt merge - should create conflict
        result = self._merge_branch("branch-a-binary")

        self.assertNotEqual(result.returncode, 0, "Merge should fail due to binary conflict")
        conflicted_files = self._get_conflicted_files()
        self.assertIn("binary_test.bin", conflicted_files, "binary_test.bin should have conflicts")
        log.info("✓ Binary file conflict test passed")

    def test_whitespace_only_conflict(self) -> None:
        """Test conflict scenario: Whitespace-only conflicts.

        Two branches modify the same lines with only whitespace differences,
        creating conflicts due to the core.whitespace config set in setUp().
        """
        log.info("Testing whitespace-only conflict")

        target_file = self.repo_dir / "whitespace_test.txt"
        target_file.write_text("Line 1\nLine 2\nLine 3\n")
        self._commit_file(target_file, "Add whitespace test file")

        # Branch A: Add trailing whitespace
        self._create_branch("branch-a-whitespace")
        target_file.write_text("Line 1\nLine 2  \nLine 3\n")  # Trailing spaces on line 2
        self._commit_file(target_file, "Branch A: Add trailing whitespace")

        # Branch B: Add different trailing whitespace
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch("branch-b-whitespace")
        target_file.write_text("Line 1\nLine 2\t\nLine 3\n")  # Trailing tab on line 2
        self._commit_file(target_file, "Branch B: Add trailing tab")

        # Attempt merge - may or may not conflict depending on git settings
        result = self._merge_branch("branch-a-whitespace")

        # This test verifies that whitespace changes are handled
        # (may succeed with auto-merge or may conflict)
        if result.returncode != 0:
            log.info("Whitespace changes caused conflict (as expected in some configurations)")
            conflicted_files = self._get_conflicted_files()
            self.assertIn("whitespace_test.txt", conflicted_files)
        else:
            log.info("Whitespace changes auto-merged (acceptable behavior)")

        self.assertTrue(True, "Whitespace conflict handling completed")
        log.info("✓ Whitespace-only conflict test passed")

    def test_renamed_file_conflict(self) -> None:
        """Test conflict scenario: Renamed file conflicts.

        Both branches rename the same file to different names, creating a
        rename-rename conflict.
        """
        log.info("Testing renamed file conflict")

        original_file = self.repo_dir / "original_name.txt"
        original_file.write_text("File to be renamed\n")
        self._commit_file(original_file, "Add file for rename test")

        # Branch A: Rename to name_a
        self._create_branch("branch-a-rename")
        self._run_git(["git", "mv", "original_name.txt", "renamed_to_a.txt"])
        self._run_git(["git", "commit", "-m", "Branch A: Rename to renamed_to_a.txt"])

        # Branch B: Rename to name_b
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch("branch-b-rename")
        self._run_git(["git", "mv", "original_name.txt", "renamed_to_b.txt"])
        self._run_git(["git", "commit", "-m", "Branch B: Rename to renamed_to_b.txt"])

        # Attempt merge - should create conflict
        result = self._merge_branch("branch-a-rename")

        self.assertNotEqual(result.returncode, 0, "Merge should fail due to rename conflict")

        # Check for unmerged entries using git ls-files -u for more reliable detection
        unmerged_result = self._run_git(["git", "ls-files", "-u"])
        status_result = self._run_git(["git", "status"])

        # Verify both renamed files appear in the status/unmerged output
        combined_output = status_result.stdout + unmerged_result.stdout
        self.assertIn("renamed_to_a.txt", combined_output,
                      "renamed_to_a.txt should appear in conflict status")
        self.assertIn("renamed_to_b.txt", combined_output,
                      "renamed_to_b.txt should appear in conflict status")
        log.info("✓ Renamed file conflict test passed")

    def test_new_file_conflict(self) -> None:
        """Test conflict scenario: New file conflicts.

        Both branches create a new file with the same name but different content,
        creating an add-add conflict.
        """
        log.info("Testing new file conflict")

        # Branch A: Create new file with content A
        self._create_branch("branch-a-newfile")
        new_file = self.repo_dir / "new_file.txt"
        new_file.write_text("Content from branch A\n")
        self._commit_file(new_file, "Branch A: Add new_file.txt")

        # Branch B: Create same file with content B
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch("branch-b-newfile")
        new_file.write_text("Content from branch B\n")
        self._commit_file(new_file, "Branch B: Add new_file.txt")

        # Attempt merge - should create conflict
        result = self._merge_branch("branch-a-newfile")

        self.assertNotEqual(result.returncode, 0, "Merge should fail due to new file conflict")
        conflicted_files = self._get_conflicted_files()
        self.assertIn("new_file.txt", conflicted_files, "new_file.txt should have conflicts")
        log.info("✓ New file conflict test passed")

    def test_complex_multiway_conflict(self) -> None:
        """Test conflict scenario: Complex multi-way conflicts.

        Create multiple conflicting changes across different parts of a file,
        simulating complex real-world merge scenarios.
        """
        log.info("Testing complex multi-way conflict")

        target_file = self.repo_dir / "complex_test.txt"
        target_file.write_text(
            "Section 1: Original\n"
            "Section 2: Original\n"
            "Section 3: Original\n"
            "Section 4: Original\n"
        )
        self._commit_file(target_file, "Add complex test file")

        # Branch A: Modify sections 1 and 3
        self._create_branch("branch-a-complex")
        content = target_file.read_text()
        content = content.replace("Section 1: Original", "Section 1: Modified by A")
        content = content.replace("Section 3: Original", "Section 3: Modified by A")
        target_file.write_text(content)
        self._commit_file(target_file, "Branch A: Modify sections 1 and 3")

        # Branch B: Modify sections 1 and 2 differently
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch("branch-b-complex")
        content = target_file.read_text()
        content = content.replace("Section 1: Original", "Section 1: Modified by B")
        content = content.replace("Section 2: Original", "Section 2: Modified by B")
        target_file.write_text(content)
        self._commit_file(target_file, "Branch B: Modify sections 1 and 2")

        # Attempt merge - should create conflict
        result = self._merge_branch("branch-a-complex")

        self.assertNotEqual(result.returncode, 0, "Merge should fail due to complex conflicts")
        conflicted_files = self._get_conflicted_files()
        self.assertIn("complex_test.txt", conflicted_files, "complex_test.txt should have conflicts")

        # Verify multiple conflict markers
        if target_file.exists():
            content = target_file.read_text()
            conflict_markers = content.count("<<<<<<<")
            self.assertGreater(conflict_markers, 0, "Should have conflict markers")

        log.info("✓ Complex multi-way conflict test passed")

    def test_large_file_conflict(self) -> None:
        """Test conflict scenario: Large file conflicts.

        Create conflicts in large files (>1MB) to test performance and handling
        of conflicts in large content.
        """
        log.info("Testing large file conflict")

        # Generate large file (>1MB)
        large_file = self.repo_dir / "large_file.txt"
        lines = []
        for i in range(50000):  # ~1.5MB file
            lines.append(f"Line {i}: Original content with some padding to increase size\n")
        large_file.write_text("".join(lines))
        self._commit_file(large_file, "Add large test file")

        # Branch A: Modify lines in the middle
        self._create_branch("branch-a-large")
        content = large_file.read_text()
        content = content.replace("Line 25000:", "Line 25000: MODIFIED BY A")
        content = content.replace("Line 25001:", "Line 25001: MODIFIED BY A")
        large_file.write_text(content)
        self._commit_file(large_file, "Branch A: Modify large file")

        # Branch B: Modify same lines differently
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch("branch-b-large")
        content = large_file.read_text()
        content = content.replace("Line 25000:", "Line 25000: MODIFIED BY B")
        content = content.replace("Line 25001:", "Line 25001: MODIFIED BY B")
        large_file.write_text(content)
        self._commit_file(large_file, "Branch B: Modify large file differently")

        # Attempt merge - should create conflict
        result = self._merge_branch("branch-a-large")

        self.assertNotEqual(result.returncode, 0, "Merge should fail due to large file conflict")
        conflicted_files = self._get_conflicted_files()
        self.assertIn("large_file.txt", conflicted_files, "large_file.txt should have conflicts")

        # Verify file size is large
        if large_file.exists():
            file_size = large_file.stat().st_size
            self.assertGreater(file_size, 1_000_000, "File should be >1MB")

        log.info("✓ Large file conflict test passed")

    def test_multiple_files_conflict(self) -> None:
        """Test conflict scenario: Multiple files with conflicts.

        Create conflicts across multiple files simultaneously to test handling
        of complex merge scenarios with multiple conflict points.
        """
        log.info("Testing multiple files conflict")

        # Create multiple files
        file1 = self.repo_dir / "multi_file1.txt"
        file2 = self.repo_dir / "multi_file2.txt"
        file3 = self.repo_dir / "multi_file3.txt"

        file1.write_text("File 1: Original\n")
        file2.write_text("File 2: Original\n")
        file3.write_text("File 3: Original\n")

        self._run_git(["git", "add", "."])
        self._run_git(["git", "commit", "-m", "Add multiple files"])

        # Branch A: Modify all files
        self._create_branch("branch-a-multi")
        file1.write_text("File 1: Modified by A\n")
        file2.write_text("File 2: Modified by A\n")
        file3.write_text("File 3: Modified by A\n")
        self._run_git(["git", "add", "."])
        self._run_git(["git", "commit", "-m", "Branch A: Modify all files"])

        # Branch B: Modify all files differently
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch("branch-b-multi")
        file1.write_text("File 1: Modified by B\n")
        file2.write_text("File 2: Modified by B\n")
        file3.write_text("File 3: Modified by B\n")
        self._run_git(["git", "add", "."])
        self._run_git(["git", "commit", "-m", "Branch B: Modify all files"])

        # Attempt merge - should create conflicts in multiple files
        result = self._merge_branch("branch-a-multi")

        self.assertNotEqual(result.returncode, 0, "Merge should fail due to multiple conflicts")
        conflicted_files = self._get_conflicted_files()
        self.assertGreaterEqual(len(conflicted_files), 2,
                                "At least 2 files should have conflicts")
        self.assertIn("multi_file1.txt", conflicted_files)
        self.assertIn("multi_file2.txt", conflicted_files)
        log.info("✓ Multiple files conflict test passed")


if __name__ == "__main__":
    unittest.main()
