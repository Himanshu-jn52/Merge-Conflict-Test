"""Shared pytest fixtures for merge conflict tests.

Provides common setup/teardown functionality for creating isolated test
repositories and managing git state across test runs.
"""

from __future__ import annotations

import logging
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT, datefmt=_DATE_FORMAT)
log = logging.getLogger("test_fixtures")


@pytest.fixture
def temp_git_repo(tmp_path: Path) -> Iterator[Path]:
    """Create a temporary git repository for testing.

    :param tmp_path: pytest-provided temporary directory
    :yield: Path to the temporary git repository
    """
    repo_dir = tmp_path / "test_repo"
    repo_dir.mkdir()

    # Initialize git repo
    subprocess.run(
        ["git", "init"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
        timeout=10
    )

    # Configure git user for commits
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
        timeout=10
    )

    # Create initial commit with a base file
    base_file = repo_dir / "base.txt"
    base_file.write_text("Initial content\nLine 2\nLine 3\n")

    subprocess.run(
        ["git", "add", "base.txt"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
        timeout=10
    )
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=repo_dir,
        check=True,
        capture_output=True,
        text=True,
        timeout=10
    )

    log.info(f"Created temporary git repository at {repo_dir}")

    yield repo_dir

    # Cleanup is handled automatically by tmp_path fixture
    log.info(f"Cleaned up temporary repository at {repo_dir}")


@pytest.fixture
def git_helper():
    """Provide helper functions for git operations in tests.

    :return: GitHelper instance with utility methods
    """
    class GitHelper:
        """Helper class for common git operations in tests."""

        @staticmethod
        def run_git(cmd: list[str], cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
            """Execute a git command.

            :param cmd: Git command as list of arguments
            :param cwd: Working directory for the command
            :param check: If True, raise on non-zero exit
            :return: CompletedProcess result
            """
            return subprocess.run(
                cmd,
                cwd=cwd,
                check=check,
                capture_output=True,
                text=True,
                timeout=10
            )

        @staticmethod
        def create_branch(branch_name: str, cwd: Path) -> None:
            """Create and checkout a new branch.

            :param branch_name: Name of the branch to create
            :param cwd: Repository directory
            """
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )

        @staticmethod
        def checkout_branch(branch_name: str, cwd: Path) -> None:
            """Checkout an existing branch.

            :param branch_name: Name of the branch to checkout
            :param cwd: Repository directory
            """
            subprocess.run(
                ["git", "checkout", branch_name],
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )

        @staticmethod
        def commit_file(file_path: Path, message: str, cwd: Path) -> None:
            """Stage and commit a file.

            :param file_path: Path to the file (relative to cwd or absolute)
            :param message: Commit message
            :param cwd: Repository directory
            """
            subprocess.run(
                ["git", "add", str(file_path.name if file_path.is_absolute() else file_path)],
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )

        @staticmethod
        def merge_branch(branch_name: str, cwd: Path) -> subprocess.CompletedProcess:
            """Attempt to merge a branch (may fail with conflicts).

            :param branch_name: Branch to merge
            :param cwd: Repository directory
            :return: CompletedProcess (may have non-zero returncode on conflict)
            """
            return subprocess.run(
                ["git", "merge", "--no-commit", "--no-ff", branch_name],
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
                timeout=10
            )

        @staticmethod
        def abort_merge(cwd: Path) -> None:
            """Abort an in-progress merge.

            :param cwd: Repository directory
            """
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=cwd,
                check=False,
                capture_output=True,
                text=True,
                timeout=10
            )

        @staticmethod
        def get_conflicted_files(cwd: Path) -> list[str]:
            """Get list of files with merge conflicts.

            :param cwd: Repository directory
            :return: List of conflicted file paths
            """
            result = subprocess.run(
                ["git", "diff", "--name-only", "--diff-filter=U"],
                cwd=cwd,
                check=True,
                capture_output=True,
                text=True,
                timeout=10
            )
            return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    return GitHelper()
