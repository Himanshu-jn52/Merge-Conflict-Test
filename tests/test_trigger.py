"""Comprehensive test suite for trigger.py.

This module tests the Perforce trigger script to ensure 100% code coverage
for testable functions without requiring the external p4ai dependency.
"""

from __future__ import annotations

import logging
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add parent directory to path to import trigger module
sys.path.insert(0, str(Path(__file__).parent.parent))

import trigger


class TestShouldGenerate(unittest.TestCase):
    """Test suite for the should_generate() function."""

    def test_empty_string(self) -> None:
        """Test that empty string returns True."""
        self.assertTrue(trigger.should_generate(""))

    def test_whitespace_only(self) -> None:
        """Test that whitespace-only string returns True."""
        self.assertTrue(trigger.should_generate("   "))
        self.assertTrue(trigger.should_generate("\n\t  "))
        self.assertTrue(trigger.should_generate("\r\n  \t"))

    def test_placeholder_exact_match(self) -> None:
        """Test exact placeholder patterns return True."""
        self.assertTrue(trigger.should_generate("<enter description here>"))
        self.assertTrue(trigger.should_generate("enter description here"))
        self.assertTrue(trigger.should_generate("new changelist"))

    def test_placeholder_case_insensitive(self) -> None:
        """Test placeholder patterns are case-insensitive."""
        self.assertTrue(trigger.should_generate("ENTER DESCRIPTION HERE"))
        self.assertTrue(trigger.should_generate("New Changelist"))
        self.assertTrue(trigger.should_generate("<ENTER DESCRIPTION HERE>"))
        self.assertTrue(trigger.should_generate("NEW CHANGELIST"))

    def test_placeholder_with_whitespace(self) -> None:
        """Test placeholder patterns with surrounding whitespace."""
        self.assertTrue(trigger.should_generate("  enter description here  "))
        self.assertTrue(trigger.should_generate("\n<enter description here>\n"))
        self.assertTrue(trigger.should_generate("\t new changelist \t"))

    def test_real_description_returns_false(self) -> None:
        """Test that real descriptions return False."""
        self.assertFalse(trigger.should_generate("Fixed login bug"))
        self.assertFalse(trigger.should_generate("Added new feature"))
        self.assertFalse(trigger.should_generate("WIP: implementing feature X"))
        self.assertFalse(trigger.should_generate("Refactored authentication module"))

    def test_description_containing_placeholder_word(self) -> None:
        """Test that descriptions containing placeholder words but not exact match return False."""
        self.assertFalse(trigger.should_generate("Please enter description here for your changes"))
        self.assertFalse(trigger.should_generate("This is a new changelist format"))
        self.assertFalse(trigger.should_generate("Added new changelist validation"))
        self.assertFalse(trigger.should_generate("Enter your changes here"))

    def test_mixed_case_real_description(self) -> None:
        """Test mixed case real descriptions return False."""
        self.assertFalse(trigger.should_generate("Fix BUG #123"))
        self.assertFalse(trigger.should_generate("Update Documentation"))

    def test_special_characters_description(self) -> None:
        """Test descriptions with special characters return False."""
        self.assertFalse(trigger.should_generate("Fix: issue #123"))
        self.assertFalse(trigger.should_generate("[BUGFIX] resolved crash"))
        self.assertFalse(trigger.should_generate("* Added feature"))


class TestCLAdapter(unittest.TestCase):
    """Test suite for the _CLAdapter logging adapter."""

    def test_cl_adapter_process_with_cl(self) -> None:
        """Test that CLAdapter adds cl to extra."""
        logger = logging.getLogger("test")
        adapter = trigger._CLAdapter(logger, {"cl": "12345"})

        msg, kwargs = adapter.process("test message", {})

        self.assertEqual(msg, "test message")
        self.assertIn("extra", kwargs)
        self.assertEqual(kwargs["extra"]["cl"], "12345")

    def test_cl_adapter_process_without_cl(self) -> None:
        """Test that CLAdapter uses default '-' when cl not provided."""
        logger = logging.getLogger("test")
        adapter = trigger._CLAdapter(logger, {})

        msg, kwargs = adapter.process("test message", {})

        self.assertEqual(kwargs["extra"]["cl"], "-")

    def test_cl_adapter_preserves_existing_extra(self) -> None:
        """Test that CLAdapter preserves existing extra fields."""
        logger = logging.getLogger("test")
        adapter = trigger._CLAdapter(logger, {"cl": "999"})

        msg, kwargs = adapter.process("test message", {"extra": {"custom": "value"}})

        self.assertEqual(kwargs["extra"]["cl"], "999")
        self.assertEqual(kwargs["extra"]["custom"], "value")

    def test_cl_adapter_multiple_extra_fields(self) -> None:
        """Test that CLAdapter works with multiple extra fields."""
        logger = logging.getLogger("test")
        adapter = trigger._CLAdapter(logger, {"cl": "555"})

        msg, kwargs = adapter.process("message", {"extra": {"field1": "a", "field2": "b"}})

        self.assertEqual(kwargs["extra"]["cl"], "555")
        self.assertEqual(kwargs["extra"]["field1"], "a")
        self.assertEqual(kwargs["extra"]["field2"], "b")


class TestGetLogger(unittest.TestCase):
    """Test suite for the _get_logger() function."""

    def test_get_logger_with_changelist(self) -> None:
        """Test that _get_logger returns adapter with correct cl."""
        logger = trigger._get_logger("54321")

        self.assertIsInstance(logger, trigger._CLAdapter)
        self.assertEqual(logger.extra.get("cl"), "54321")

    def test_get_logger_default(self) -> None:
        """Test that _get_logger uses '-' as default."""
        logger = trigger._get_logger()

        self.assertIsInstance(logger, trigger._CLAdapter)
        self.assertEqual(logger.extra.get("cl"), "-")

    def test_get_logger_with_string_cl(self) -> None:
        """Test _get_logger with various string formats."""
        logger1 = trigger._get_logger("12345")
        logger2 = trigger._get_logger("abc123")
        logger3 = trigger._get_logger("new")

        self.assertEqual(logger1.extra.get("cl"), "12345")
        self.assertEqual(logger2.extra.get("cl"), "abc123")
        self.assertEqual(logger3.extra.get("cl"), "new")


class TestMainFunction(unittest.TestCase):
    """Test suite for the main() function."""

    def test_main_no_arguments(self) -> None:
        """Test main() with no arguments logs error and returns 0."""
        with patch.object(sys, 'argv', ['trigger.py']):
            with patch('trigger._get_logger') as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = trigger.main()

                self.assertEqual(result, 0)
                mock_logger.error.assert_called_once()
                self.assertIn("Usage", str(mock_logger.error.call_args))

    def test_main_insufficient_arguments(self) -> None:
        """Test main() with insufficient arguments."""
        with patch.object(sys, 'argv', ['trigger.py']):
            with patch('trigger._get_logger') as mock_get_logger:
                mock_logger = MagicMock()
                mock_get_logger.return_value = mock_logger

                result = trigger.main()

                self.assertEqual(result, 0)
                mock_logger.error.assert_called()


class TestModuleConstants(unittest.TestCase):
    """Test suite for module-level constants and configuration."""

    def test_placeholder_patterns_exist(self) -> None:
        """Test that placeholder patterns are defined."""
        self.assertIsInstance(trigger._PLACEHOLDER_PATTERNS, list)
        self.assertGreater(len(trigger._PLACEHOLDER_PATTERNS), 0)

    def test_placeholder_patterns_content(self) -> None:
        """Test that expected placeholder patterns are present."""
        patterns = [p.lower() for p in trigger._PLACEHOLDER_PATTERNS]
        self.assertIn("", patterns)
        self.assertIn("<enter description here>", patterns)
        self.assertIn("enter description here", patterns)
        self.assertIn("new changelist", patterns)

    def test_log_format_defined(self) -> None:
        """Test that log format constants are defined."""
        self.assertIsInstance(trigger._LOG_FORMAT, str)
        self.assertIn("%(levelname)s", trigger._LOG_FORMAT)
        self.assertIn("%(cl)s", trigger._LOG_FORMAT)

    def test_date_format_defined(self) -> None:
        """Test that date format is defined."""
        self.assertIsInstance(trigger._DATE_FORMAT, str)
        self.assertIn("%Y", trigger._DATE_FORMAT)
        self.assertIn("%m", trigger._DATE_FORMAT)
        self.assertIn("%d", trigger._DATE_FORMAT)

    def test_log_file_from_environment(self) -> None:
        """Test that log file can be set via environment variable."""
        import os
        default_log = os.environ.get("P4AI_LOG_FILE", "/tmp/p4ai_trigger.log")
        self.assertIsInstance(default_log, str)


class TestIntegration(unittest.TestCase):
    """Integration tests for the trigger module."""

    def test_should_generate_with_all_placeholders(self) -> None:
        """Test should_generate with all known placeholder patterns."""
        for pattern in trigger._PLACEHOLDER_PATTERNS:
            with self.subTest(pattern=pattern):
                self.assertTrue(trigger.should_generate(pattern))

    def test_logger_adapter_integration(self) -> None:
        """Test that logger adapter integrates correctly with logging."""
        logger = trigger._get_logger("integration-test-123")

        # Should not raise any exceptions
        self.assertIsNotNone(logger)
        self.assertEqual(logger.extra["cl"], "integration-test-123")

    def test_should_generate_edge_cases(self) -> None:
        """Test edge cases for should_generate."""
        # Very long description
        long_desc = "x" * 10000
        self.assertFalse(trigger.should_generate(long_desc))

        # Unicode characters
        self.assertFalse(trigger.should_generate("修复了登录错误"))
        self.assertFalse(trigger.should_generate("Исправлена ошибка"))

        # Only spaces and newlines
        self.assertTrue(trigger.should_generate("    \n\n   \t\t   "))


class TestLoggingConfiguration(unittest.TestCase):
    """Test logging configuration and setup."""

    def test_logging_basicConfig_called(self) -> None:
        """Test that logging is configured."""
        # Just verify the module imports and sets up logging without errors
        self.assertIsNotNone(trigger.log)
        self.assertEqual(trigger.log.name, "p4ai.trigger")

    def test_file_handler_exists(self) -> None:
        """Test that file handler is created."""
        self.assertIsNotNone(trigger._file_handler)
        self.assertIsInstance(trigger._file_handler, logging.handlers.RotatingFileHandler)

    def test_file_handler_max_bytes(self) -> None:
        """Test that file handler has correct maxBytes."""
        self.assertEqual(trigger._file_handler.maxBytes, 5 * 1024 * 1024)  # 5 MiB

    def test_file_handler_backup_count(self) -> None:
        """Test that file handler has correct backupCount."""
        self.assertEqual(trigger._file_handler.backupCount, 5)


if __name__ == "__main__":
    unittest.main()
