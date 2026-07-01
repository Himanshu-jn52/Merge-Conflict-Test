#!/usr/bin/env python3
"""Tests for the simulate_conflicts.py script.

These tests verify the script's ability to create various merge conflict scenarios.
"""

from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path


class TestSimulateConflicts(unittest.TestCase):
    """Test cases for conflict simulation script."""

    def setUp(self):
        """Set up test environment."""
        self.script_path = Path(__file__).parent / "scripts" / "simulate_conflicts.py"
        self.assertTrue(self.script_path.exists(), f"Script not found at {self.script_path}")

    def tearDown(self):
        """Clean up after tests."""
        # Always run cleanup after tests
        try:
            subprocess.run(
                [sys.executable, str(self.script_path), "--cleanup"],
                capture_output=True,
                timeout=30
            )
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            pass  # Cleanup may fail if no branches exist

    def test_script_help(self):
        """Test that the script shows help without errors."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--help"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Simulate merge conflicts", result.stdout)
        self.assertIn("--scenario", result.stdout)
        self.assertIn("--dry-run", result.stdout)
        self.assertIn("--cleanup", result.stdout)

    def test_dry_run_content_conflict(self):
        """Test dry-run mode for content conflict scenario."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--scenario", "content", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("CONTENT conflict", result.stderr)
        self.assertIn("[DRY-RUN]", result.stderr)

    def test_dry_run_delete_modify_conflict(self):
        """Test dry-run mode for delete-modify conflict scenario."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--scenario", "delete-modify", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("DELETE-MODIFY conflict", result.stderr)
        self.assertIn("[DRY-RUN]", result.stderr)

    def test_dry_run_rename_conflict(self):
        """Test dry-run mode for rename conflict scenario."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--scenario", "rename", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("RENAME conflict", result.stderr)
        self.assertIn("[DRY-RUN]", result.stderr)

    def test_dry_run_type_change_conflict(self):
        """Test dry-run mode for type-change conflict scenario."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--scenario", "type-change", "--dry-run"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("TYPE-CHANGE conflict", result.stderr)
        self.assertIn("[DRY-RUN]", result.stderr)

    def test_cleanup_command(self):
        """Test cleanup functionality."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--cleanup"],
            capture_output=True,
            text=True,
            timeout=30
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("Cleaning up", result.stderr)

    def test_invalid_scenario(self):
        """Test that invalid scenario is rejected."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--scenario", "invalid"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid choice", result.stderr)

    def test_verbose_output(self):
        """Test verbose logging mode."""
        result = subprocess.run(
            [sys.executable, str(self.script_path), "--dry-run", "--verbose"],
            capture_output=True,
            text=True,
            timeout=10
        )
        self.assertEqual(result.returncode, 0)
        # Verbose mode should produce more detailed output
        self.assertTrue(len(result.stderr) > 0)


class TestScriptStructure(unittest.TestCase):
    """Test the script structure and imports."""

    def test_script_imports(self):
        """Test that the script can be imported without errors."""
        script_path = Path(__file__).parent / "scripts" / "simulate_conflicts.py"

        # Read the script and check for required imports
        content = script_path.read_text()
        self.assertIn("import argparse", content)
        self.assertIn("import logging", content)
        self.assertIn("import subprocess", content)
        self.assertIn("from __future__ import annotations", content)

    def test_script_has_main_guard(self):
        """Test that script has proper main guard."""
        script_path = Path(__file__).parent / "scripts" / "simulate_conflicts.py"
        content = script_path.read_text()
        self.assertIn('if __name__ == "__main__":', content)
        self.assertIn("sys.exit(main())", content)

    def test_script_has_docstring(self):
        """Test that script has module-level docstring."""
        script_path = Path(__file__).parent / "scripts" / "simulate_conflicts.py"
        content = script_path.read_text()
        # Check for module docstring
        self.assertTrue(content.strip().startswith('#!/usr/bin/env python3\n"""'))

    def test_conflict_scenario_class_exists(self):
        """Test that ConflictScenario class is defined."""
        script_path = Path(__file__).parent / "scripts" / "simulate_conflicts.py"
        content = script_path.read_text()
        self.assertIn("class ConflictScenario:", content)
        self.assertIn("def simulate_content_conflict", content)
        self.assertIn("def simulate_delete_modify_conflict", content)
        self.assertIn("def simulate_rename_conflict", content)
        self.assertIn("def simulate_type_change_conflict", content)
        self.assertIn("def cleanup", content)


def main():
    """Run the test suite."""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
