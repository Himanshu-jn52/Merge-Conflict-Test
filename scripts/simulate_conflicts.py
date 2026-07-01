#!/usr/bin/env python3
"""Simulate merge conflicts for testing and demonstration.

This script programmatically creates branches, applies conflicting changes,
and produces merge conflicts for use in testing, CI, and demos.

Usage examples
--------------
::

    # Create a content conflict (default scenario)
    python3 scripts/simulate_conflicts.py

    # Create a delete-modify conflict
    python3 scripts/simulate_conflicts.py --scenario delete-modify

    # Create a rename conflict
    python3 scripts/simulate_conflicts.py --scenario rename

    # Dry-run to see what would happen
    python3 scripts/simulate_conflicts.py --dry-run

    # Cleanup branches after demonstration
    python3 scripts/simulate_conflicts.py --cleanup

Conflict scenarios
------------------
- **content**: Two branches modify the same lines with different content
- **delete-modify**: One branch deletes a file, another modifies it
- **rename**: Both branches rename the same file to different names
- **type-change**: One branch replaces a file with a directory (or vice versa)
"""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT, datefmt=_DATE_FORMAT)
log = logging.getLogger("simulate_conflicts")


class ConflictScenario:
    """Encapsulates branch creation, file modification, and merge conflict generation."""

    def __init__(self, scenario_type: str, dry_run: bool = False, base_branch: Optional[str] = None, target_file: Optional[str] = None):
        """Initialize conflict scenario.

        :param scenario_type: Type of conflict to simulate
        :param dry_run: If True, show what would happen without executing
        :param base_branch: Base branch name (auto-detected if None)
        :param target_file: Target file for conflicts (auto-detected if None)
        """
        self.scenario_type = scenario_type
        self.dry_run = dry_run
        self.base_branch = base_branch or self._detect_base_branch()
        self.target_file = target_file
        self.original_branch = self._get_current_branch() if not dry_run else None
        self.branch_a = f"conflict-test-a-{scenario_type}"
        self.branch_b = f"conflict-test-b-{scenario_type}"

    def _detect_base_branch(self) -> str:
        """Detect the default branch name dynamically.

        :return: Base branch name (e.g., 'main', 'master')
        """
        if self.dry_run:
            return "main"

        try:
            # Try to get the default branch from origin
            result = subprocess.run(
                ["git", "symbolic-ref", "refs/remotes/origin/HEAD"],
                check=True,
                capture_output=True,
                text=True
            )
            # Output is like 'refs/remotes/origin/main', extract 'main'
            branch = result.stdout.strip().split("/")[-1]
            log.debug(f"Detected base branch: {branch}")
            return branch
        except subprocess.CalledProcessError:
            # Fallback: check if 'main' or 'master' exists
            for candidate in ["main", "master"]:
                result = subprocess.run(
                    ["git", "rev-parse", "--verify", candidate],
                    capture_output=True
                )
                if result.returncode == 0:
                    log.debug(f"Detected base branch: {candidate}")
                    return candidate

            # Last resort: use current branch
            log.warning("Could not detect default branch, using current branch")
            return self._get_current_branch()

    def _run_git(self, cmd: list[str], check: bool = True, capture_output: bool = False) -> Optional[subprocess.CompletedProcess]:
        """Execute git command with logging and dry-run support.

        :param cmd: Git command as list of arguments
        :param check: If True, raise exception on non-zero exit
        :param capture_output: If True, capture stdout/stderr
        :return: CompletedProcess if executed, None if dry-run
        """
        log.info("Running: %s", " ".join(cmd))
        if self.dry_run:
            log.info("  [DRY-RUN] Would execute: %s", " ".join(cmd))
            return None

        try:
            result = subprocess.run(cmd, check=check, capture_output=capture_output, text=True)
            if capture_output and result.stdout:
                log.debug("  Output: %s", result.stdout.strip())
            return result
        except subprocess.CalledProcessError as e:
            if capture_output:
                log.error("  stderr: %s", e.stderr)
            raise

    def _get_current_branch(self) -> str:
        """Get the current branch name."""
        if self.dry_run:
            return "main"
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            check=True,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()

    def _ensure_clean_state(self) -> None:
        """Ensure we're on main branch with no uncommitted changes."""
        log.info("Ensuring clean state...")
        if not self.dry_run:
            # Check for uncommitted changes
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                check=True,
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                log.error("Working directory has uncommitted changes. Please commit or stash them first.")
                sys.exit(1)

        current = self._get_current_branch()
        if current != self.base_branch:
            log.info(f"Switching from {current} to {self.base_branch}")
            self._run_git(["git", "checkout", self.base_branch])

    def _create_branch(self, branch_name: str) -> None:
        """Create and checkout a new branch from main.

        :param branch_name: Name of the branch to create
        """
        log.info(f"Creating branch: {branch_name}")
        self._run_git(["git", "checkout", "-b", branch_name, self.base_branch])

    def _commit_changes(self, message: str, files: Optional[list[str]] = None) -> None:
        """Stage and commit changes.

        :param message: Commit message
        :param files: Specific files to stage (None = use -u for tracked changes only)
        """
        log.info(f"Committing changes: {message}")
        if files:
            for f in files:
                self._run_git(["git", "add", f])
        else:
            # Use -u to only stage changes to tracked files, not new untracked files
            self._run_git(["git", "add", "-u"])
        self._run_git(["git", "commit", "-m", message])

    def _attempt_merge(self, branch_name: str) -> bool:
        """Attempt to merge branch, expecting a conflict.

        :param branch_name: Branch to merge into current branch
        :return: True if conflict occurred, False otherwise
        """
        log.info(f"Attempting merge of {branch_name}...")
        result = self._run_git(
            ["git", "merge", "--no-commit", "--no-ff", branch_name],
            check=False,
            capture_output=True
        )

        if self.dry_run:
            log.info("  [DRY-RUN] Would attempt merge and produce conflict")
            return True

        if result.returncode != 0:
            log.info("✓ Merge conflict detected (as expected)")
            # Show conflict status
            status_result = subprocess.run(
                ["git", "status", "--short"],
                capture_output=True,
                text=True
            )
            log.info("Conflict status:\n%s", status_result.stdout)
            return True
        else:
            log.warning("✗ Merge succeeded without conflict (unexpected)")
            return False

    def simulate_content_conflict(self) -> None:
        """Simulate a content conflict by modifying the same lines differently."""
        log.info("=== Simulating CONTENT conflict ===")

        # Use provided target file or default to README.md (more universal than trigger.py)
        target_file = Path(self.target_file) if self.target_file else Path("README.md")

        if not self.dry_run and not target_file.exists():
            log.error(f"Target file {target_file} does not exist. Use --target-file to specify a different file.")
            sys.exit(1)

        self._ensure_clean_state()

        # Branch A: Modify first heading or line
        self._create_branch(self.branch_a)
        log.info(f"Branch A: Modifying {target_file}")

        if not self.dry_run:
            content = target_file.read_text()
            lines = content.split('\n')
            if len(lines) > 0:
                # Modify first non-empty line
                for i, line in enumerate(lines):
                    if line.strip():
                        lines[i] = line + " [Branch A modification]"
                        break
                target_file.write_text('\n'.join(lines))

        self._commit_changes("Branch A: Modify first line", [str(target_file)])

        # Branch B: Modify same line differently
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch(self.branch_b)
        log.info(f"Branch B: Modifying {target_file}")

        if not self.dry_run:
            content = target_file.read_text()
            lines = content.split('\n')
            if len(lines) > 0:
                # Modify same line differently
                for i, line in enumerate(lines):
                    if line.strip():
                        lines[i] = line + " [Branch B different modification]"
                        break
                target_file.write_text('\n'.join(lines))

        self._commit_changes("Branch B: Modify first line differently", [str(target_file)])

        # Attempt merge
        conflict_occurred = self._attempt_merge(self.branch_a)

        if conflict_occurred:
            log.info("\n✓ Successfully created content conflict!")
            log.info(f"  Branches: {self.branch_a}, {self.branch_b}")
            log.info(f"  Conflicting file: {target_file}")
            log.info(f"  To resolve: git merge --abort")
        else:
            log.warning("\n✗ Failed to create content conflict")

    def simulate_delete_modify_conflict(self) -> None:
        """Simulate a delete-modify conflict."""
        log.info("=== Simulating DELETE-MODIFY conflict ===")

        # Use provided target file or try LICENSE, fallback to README.md
        if self.target_file:
            target_file = Path(self.target_file)
        else:
            target_file = Path("LICENSE") if Path("LICENSE").exists() or self.dry_run else Path("README.md")

        if not self.dry_run and not target_file.exists():
            log.error(f"Target file {target_file} does not exist. Use --target-file to specify a different file.")
            sys.exit(1)

        self._ensure_clean_state()

        # Branch A: Delete the file
        self._create_branch(self.branch_a)
        log.info(f"Branch A: Deleting {target_file}")
        if not self.dry_run:
            target_file.unlink()
        self._commit_changes(f"Branch A: Remove {target_file}", [str(target_file)])

        # Branch B: Modify the file
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch(self.branch_b)
        log.info(f"Branch B: Modifying {target_file}")

        if not self.dry_run:
            content = target_file.read_text()
            modified = content + "\n\n# Additional content added by Branch B\n"
            target_file.write_text(modified)

        self._commit_changes(f"Branch B: Update {target_file}", [str(target_file)])

        # Attempt merge
        conflict_occurred = self._attempt_merge(self.branch_a)

        if conflict_occurred:
            log.info("\n✓ Successfully created delete-modify conflict!")
            log.info(f"  Branches: {self.branch_a}, {self.branch_b}")
            log.info(f"  Conflicting file: {target_file}")
            log.info(f"  To resolve: git merge --abort")
        else:
            log.warning("\n✗ Failed to create delete-modify conflict")

    def simulate_rename_conflict(self) -> None:
        """Simulate a rename conflict where both branches rename the same file."""
        log.info("=== Simulating RENAME conflict ===")

        # Use provided target file or default to README.md
        original_file = Path(self.target_file) if self.target_file else Path("README.md")

        if not self.dry_run and not original_file.exists():
            log.error(f"Target file {original_file} does not exist. Use --target-file to specify a different file.")
            sys.exit(1)

        # Generate generic rename targets
        stem = original_file.stem
        suffix = original_file.suffix
        rename_a = Path(f"{stem}_version_a{suffix}")
        rename_b = Path(f"{stem}_version_b{suffix}")

        self._ensure_clean_state()

        # Branch A: Rename to version_a
        self._create_branch(self.branch_a)
        log.info(f"Branch A: Renaming {original_file} to {rename_a}")
        self._run_git(["git", "mv", str(original_file), str(rename_a)])
        self._commit_changes(f"Branch A: Rename to {rename_a}")

        # Branch B: Rename to version_b
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch(self.branch_b)
        log.info(f"Branch B: Renaming {original_file} to {rename_b}")
        self._run_git(["git", "mv", str(original_file), str(rename_b)])
        self._commit_changes(f"Branch B: Rename to {rename_b}")

        # Attempt merge
        conflict_occurred = self._attempt_merge(self.branch_a)

        if conflict_occurred:
            log.info("\n✓ Successfully created rename conflict!")
            log.info(f"  Branches: {self.branch_a}, {self.branch_b}")
            log.info(f"  Original file: {original_file}")
            log.info(f"  Branch A renamed to: {rename_a}")
            log.info(f"  Branch B renamed to: {rename_b}")
            log.info(f"  To resolve: git merge --abort")
        else:
            log.warning("\n✗ Failed to create rename conflict")

    def simulate_type_change_conflict(self) -> None:
        """Simulate a type-change conflict (file vs directory)."""
        log.info("=== Simulating TYPE-CHANGE conflict ===")
        target_path = Path("conflicting_item")

        self._ensure_clean_state()

        # Check if file already exists on base branch
        file_exists_on_base = not self.dry_run and target_path.exists()

        if not file_exists_on_base and not self.dry_run:
            log.warning(f"{target_path} does not exist on base branch. Creating it on test branches only.")

        # Branch A: Create/modify as file
        self._create_branch(self.branch_a)
        log.info(f"Branch A: Creating/modifying {target_path} as file")

        if not self.dry_run:
            if not file_exists_on_base:
                target_path.write_text("# Original file created on Branch A\n")
            else:
                content = target_path.read_text()
                target_path.write_text(content + "\n# Branch A modifications\n")

        self._commit_changes(f"Branch A: Update {target_path} file", [str(target_path)])

        # Branch B: Create as directory or replace with directory
        self._run_git(["git", "checkout", self.base_branch])
        self._create_branch(self.branch_b)
        log.info(f"Branch B: Creating/replacing {target_path} with directory")

        if not self.dry_run:
            if file_exists_on_base:
                target_path.unlink()
            target_path.mkdir(exist_ok=True)
            (target_path / "README.md").write_text("# This is now a directory\n")

        self._commit_changes(f"Branch B: Replace {target_path} with directory", [str(target_path)])

        # Attempt merge
        conflict_occurred = self._attempt_merge(self.branch_a)

        if conflict_occurred:
            log.info("\n✓ Successfully created type-change conflict!")
            log.info(f"  Branches: {self.branch_a}, {self.branch_b}")
            log.info(f"  Path: {target_path}")
            log.info(f"  Branch A: file")
            log.info(f"  Branch B: directory")
            log.info(f"  To resolve: git merge --abort")
        else:
            log.warning("\n✗ Failed to create type-change conflict")

    def cleanup(self) -> None:
        """Clean up test branches and abort any in-progress merge."""
        log.info("=== Cleaning up test branches ===")

        # Abort merge if in progress
        log.info("Aborting any in-progress merge...")
        self._run_git(["git", "merge", "--abort"], check=False)

        # Determine where to return
        current_branch = self._get_current_branch() if not self.dry_run else "main"
        target_branch = self.base_branch

        # If we saved the original branch and it's not one of the test branches, return there
        if self.original_branch and self.original_branch not in [self.branch_a, self.branch_b]:
            target_branch = self.original_branch
            log.info(f"Returning to original branch: {target_branch}")
        elif current_branch in [self.branch_a, self.branch_b]:
            log.info(f"Returning to base branch: {target_branch}")
        else:
            log.info(f"Staying on current branch: {current_branch}")
            target_branch = current_branch

        if current_branch != target_branch:
            self._run_git(["git", "checkout", target_branch])

        # Delete test branches
        for branch in [self.branch_a, self.branch_b]:
            log.info(f"Deleting branch: {branch}")
            self._run_git(["git", "branch", "-D", branch], check=False)

        # Clean up type-change test artifact if it exists
        if not self.dry_run:
            target_path = Path("conflicting_item")
            if target_path.exists():
                if target_path.is_dir():
                    import shutil
                    shutil.rmtree(target_path)
                else:
                    target_path.unlink()
                log.info("Removed conflicting_item test artifact")

        log.info("✓ Cleanup complete")

    def run(self) -> int:
        """Execute the conflict simulation scenario.

        :return: Exit code (0 for success)
        """
        try:
            if self.scenario_type == "content":
                self.simulate_content_conflict()
            elif self.scenario_type == "delete-modify":
                self.simulate_delete_modify_conflict()
            elif self.scenario_type == "rename":
                self.simulate_rename_conflict()
            elif self.scenario_type == "type-change":
                self.simulate_type_change_conflict()
            else:
                log.error(f"Unknown scenario type: {self.scenario_type}")
                return 1

            return 0

        except subprocess.CalledProcessError as e:
            log.error(f"Git command failed: {e}")
            return 1
        except Exception as e:
            log.error(f"Unexpected error: {e}", exc_info=True)
            return 1


def main() -> int:
    """Main entry point for conflict simulation script."""
    parser = argparse.ArgumentParser(
        description="Simulate merge conflicts for testing and demonstration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a content conflict (default)
  %(prog)s

  # Create a delete-modify conflict
  %(prog)s --scenario delete-modify

  # Show what would happen without executing
  %(prog)s --dry-run

  # Clean up test branches after demonstration
  %(prog)s --cleanup

Conflict scenarios:
  content       Two branches modify the same lines differently (default)
  delete-modify One branch deletes a file, another modifies it
  rename        Both branches rename the same file to different names
  type-change   One branch replaces a file with a directory
        """
    )

    parser.add_argument(
        "--scenario",
        choices=["content", "delete-modify", "rename", "type-change"],
        default="content",
        help="Type of merge conflict to simulate (default: content)"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without executing commands"
    )

    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Clean up test branches and abort in-progress merge"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug-level logging"
    )

    parser.add_argument(
        "--base-branch",
        type=str,
        help="Base branch name (auto-detected if not specified)"
    )

    parser.add_argument(
        "--target-file",
        type=str,
        help="Target file for conflicts (defaults vary by scenario)"
    )

    args = parser.parse_args()

    if args.verbose:
        log.setLevel(logging.DEBUG)

    scenario = ConflictScenario(
        args.scenario,
        dry_run=args.dry_run,
        base_branch=args.base_branch,
        target_file=args.target_file
    )

    if args.cleanup:
        scenario.cleanup()
        return 0

    return scenario.run()


if __name__ == "__main__":
    sys.exit(main())
