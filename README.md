# Merge-Conflict-Test

This repository contains a Perforce AI trigger script (`trigger.py`) that automatically generates AI-powered changelist descriptions for submissions with empty or placeholder descriptions.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Development](#development)
  - [Running Locally](#running-locally)
  - [Testing](#testing)
  - [Merge Conflict Simulation](#merge-conflict-simulation)
  - [Log File Analysis](#log-file-analysis)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

The `trigger.py` script integrates with Perforce as a `change-commit` trigger to enhance developer workflows by automatically generating meaningful changelist descriptions using AI. When a changelist is submitted with an empty or default placeholder description, the trigger analyzes the changes and generates a descriptive summary automatically.

The trigger is designed to be non-blocking and fail-safe: it never prevents a submit from succeeding, even if AI generation fails.

## Key Features

- **Automatic Description Generation**: Detects empty or placeholder changelist descriptions and auto-generates meaningful descriptions using AI
- **Non-Blocking Behavior**: Never blocks a submit operation, even on failures or errors
- **Smart Detection**: Recognizes these placeholder patterns (case-insensitive):
  - Empty descriptions
  - `<enter description here>`
  - `enter description here`
  - `new changelist`
- **Configurable Logging**: Rotating log files with configurable paths for audit and debugging
- **Environment-Based Configuration**: Flexible configuration via environment variables or config files

## Prerequisites

- **Python 3.x** (Python 3.7 or higher recommended)
- **Perforce Server**: Access to a Perforce server with trigger configuration permissions
- **p4ai Package**: The `p4ai` Python package and its dependencies must be installed and accessible to the Perforce server's OS user (this is internal/unreleased software - see installation instructions)
- **AI Provider Access**: Valid API keys for the configured AI provider (e.g., OpenAI, Anthropic)

## Installation

### 1. Install the p4ai Package

Ensure the `p4ai` package is installed in the Python environment accessible to the Perforce server user. Since this is internal/unreleased software, installation steps will depend on your organization's deployment process (e.g., installing from a private repository, local wheel file, or source):

```bash
# Example: Install from source or private repository
pip install /path/to/p4ai-package
# OR
pip install git+https://your-internal-repo/p4ai.git
```

### 2. Configure the Perforce Trigger

Add the trigger to your Perforce server's trigger table using `p4 triggers`:

```bash
p4 triggers
```

Add one of the following entries:

**Option A: Direct Execution (if executable bit is set)**
```
Triggers:
    p4ai-describe change-commit //... "/path/to/trigger.py %changelist%"
```

**Option B: Explicit Python Interpreter**
```
Triggers:
    p4ai-describe change-commit //... "/usr/bin/python3 /path/to/trigger.py %changelist%"
```

**Option C: Using p4ai CLI (if installed as a command-line tool)**
```
Triggers:
    p4ai-describe change-commit //... "p4ai trigger-run %changelist%"
```

Replace `/path/to/trigger.py` with the actual path to the `trigger.py` script. For Option A, ensure the script has execute permissions (`chmod +x trigger.py`).

### 3. Set Permissions

Ensure the Perforce server's OS user has:
- Read access to the trigger script
- Write access to the log file location (default: `/tmp/p4ai_trigger.log`)
- Access to configuration files and API keys

## Configuration

### Environment Variables

Environment variables recognized by the p4ai system and this trigger:

| Variable | Description | Default |
|----------|-------------|---------|
| `P4AI_PROVIDER` | AI provider to use (e.g., `openai`, `anthropic`) | Required (unless configured in `~/.p4ai/config.json`) |
| `P4PORT` | Perforce server address | Required (unless configured in `~/.p4ai/config.json`) |
| `P4USER` | Perforce user for trigger operations | Required (unless configured in `~/.p4ai/config.json`) |
| `P4AI_LOG_FILE` | Path to the log file (read directly by trigger.py) | `/tmp/p4ai_trigger.log` |

### Configuration File

Alternatively, create a configuration file at `~/.p4ai/config.json` (relative to the Perforce server user's home directory):

```json
{
  "provider": "openai",
  "api_key": "your-api-key-here",
  "p4port": "perforce:1666",
  "p4user": "p4admin"
}
```

**Important**: 
- The configuration file and API keys must be accessible to the OS user running the Perforce server process.
- **Security Warning**: Never commit config files with real API keys to version control. Consider using environment variables for secrets in production environments.

### Setting Environment Variables

For the Perforce service (example for systemd):

```bash
# Edit the service file
sudo systemctl edit perforce

# Add environment variables
[Service]
Environment="P4AI_PROVIDER=openai"
Environment="P4AI_LOG_FILE=/var/log/p4ai_trigger.log"
Environment="P4PORT=localhost:1666"
Environment="P4USER=p4admin"
```

## Usage

Once installed and configured, the trigger runs automatically on every changelist submission.

### Example Scenarios

**Scenario 1: Empty Description**
```bash
# User submits with empty description
$ p4 submit -d ""

# p4ai automatically generates and applies a description based on the changes
```

**Scenario 2: Placeholder Description**
```bash
# User submits with placeholder text
$ p4 submit -d "<enter description here>"

# p4ai detects the placeholder and generates a proper description
```

**Scenario 3: Existing Description**
```bash
# User submits with a meaningful description
$ p4 submit -d "Fix login validation bug"

# p4ai skips generation since a description already exists
```

### How It Works

1. **Trigger Fires**: Perforce calls the trigger script during changelist submission (as part of the submit process)
2. **Description Check**: The script checks if the description is empty or a placeholder (case-insensitive matching)
3. **AI Generation**: If needed, p4ai analyzes the changelist diff and generates a description
4. **Apply**: The generated description is applied to the changelist
5. **Non-Blocking Exit**: The trigger always exits successfully (code 0), ensuring submits are never blocked

## Project Structure

```
.
├── trigger.py                    # Main Perforce trigger script
├── scripts/
│   └── simulate_conflicts.py     # Merge conflict simulation tool for testing
├── test_simulate_conflicts.py    # Test suite for conflict simulation script
├── README.md                     # This file
└── LICENSE                       # MIT License
```

### trigger.py Key Components

The `trigger.py` script is the main trigger implementation, containing:

- **`should_generate(description)`**: Determines if a description needs AI generation using case-insensitive pattern matching
- **`main()`**: Entry point that orchestrates the trigger workflow
- **Logging configuration**: Rotating file handlers for production use
- **Non-blocking error handling**: Ensures submits are never blocked by failures

## Development

### Running Locally

To test the trigger script locally without installing it in Perforce:

```bash
# Set required environment variables
export P4AI_PROVIDER=openai
export P4PORT=localhost:1666
export P4USER=your-username
export P4AI_LOG_FILE=/tmp/p4ai_trigger_test.log

# Run the script with a test changelist number
python3 trigger.py 12345
```

### Testing

#### Unit Tests

The project includes a comprehensive test suite covering various merge conflict scenarios. Tests are located in the `tests/` directory and cover:

**Test Coverage:**
- Overlapping edits to same lines
- Deleted vs modified conflicts
- Binary file conflicts
- Whitespace-only conflicts
- Renamed file conflicts
- New file conflicts
- Complex multi-way conflicts
- Large file conflicts
- Conflict resolution strategies

**Running Tests Locally:**

```bash
# Run all tests
python3 -m unittest discover tests/

# Run a specific test file
python3 -m unittest tests.test_merge_conflicts

# Run a specific test class
python3 -m unittest tests.test_merge_conflicts.TestOverlappingEdits

# Run a specific test method
python3 -m unittest tests.test_merge_conflicts.TestOverlappingEdits.test_same_line_different_content

# Run with verbose output
python3 -m unittest discover tests/ -v
```

**Running Tests in CI:**

```bash
# CI environments should run all tests with verbose output and coverage
python3 -m unittest discover tests/ -v

# With coverage tracking (requires coverage.py)
coverage run -m unittest discover tests/
coverage report -m
```

**Test Suite Organization:**

- `tests/test_merge_conflicts.py`: Tests for overlapping edits, delete-modify, binary files, and whitespace conflicts
- `tests/test_conflict_detection.py`: Tests for renamed files, new files, and complex multi-way conflicts
- `tests/test_conflict_resolution.py`: Tests for large files and resolution verification strategies

**Notes:**
- Each test creates a temporary git repository for isolation
- Tests are deterministic and safe to run in parallel
- All tests clean up after themselves automatically
- Tests use standard unittest framework (no external dependencies required)

#### Trigger Testing

To test the trigger behavior:

1. Create a test changelist
2. Add some files to the changelist
3. Submit with an empty or placeholder description
4. Check the log file for trigger execution details
5. Verify the description was updated

### Merge Conflict Simulation

The `scripts/simulate_conflicts.py` script programmatically creates merge conflicts for testing and demos. This is useful for:
- Testing merge conflict resolution workflows
- Demonstrating conflict scenarios in training
- CI integration tests that require reproducible conflicts
- Local development testing

**Available conflict scenarios:**

- `content`: Two branches modify the same lines with different content (default)
- `delete-modify`: One branch deletes a file while another modifies it
- `rename`: Both branches rename the same file to different names
- `type-change`: One branch replaces a file with a directory

**Usage examples:**

```bash
# Create a content conflict (default scenario, uses README.md)
python3 scripts/simulate_conflicts.py

# Create a delete-modify conflict
python3 scripts/simulate_conflicts.py --scenario delete-modify

# Create a rename conflict
python3 scripts/simulate_conflicts.py --scenario rename

# Create a type-change conflict
python3 scripts/simulate_conflicts.py --scenario type-change

# Specify a custom target file
python3 scripts/simulate_conflicts.py --scenario content --target-file trigger.py

# Specify a custom base branch
python3 scripts/simulate_conflicts.py --base-branch master

# Dry-run to see what would happen without executing
python3 scripts/simulate_conflicts.py --dry-run

# Clean up test branches after demonstration
python3 scripts/simulate_conflicts.py --cleanup

# Enable verbose logging
python3 scripts/simulate_conflicts.py --scenario rename --verbose
```

**Expected output for content conflict:**

```bash
$ python3 scripts/simulate_conflicts.py
2026-07-01T10:30:15 [INFO] === Simulating CONTENT conflict ===
2026-07-01T10:30:15 [INFO] Ensuring clean state...
2026-07-01T10:30:15 [INFO] Creating branch: conflict-test-a-content
2026-07-01T10:30:15 [INFO] Branch A: Modifying README.md
2026-07-01T10:30:15 [INFO] Committing changes: Branch A: Modify first line
2026-07-01T10:30:16 [INFO] Creating branch: conflict-test-b-content
2026-07-01T10:30:16 [INFO] Branch B: Modifying README.md
2026-07-01T10:30:16 [INFO] Committing changes: Branch B: Modify first line differently
2026-07-01T10:30:17 [INFO] Attempting merge of conflict-test-a-content...
2026-07-01T10:30:17 [INFO] ✓ Merge conflict detected (as expected)
2026-07-01T10:30:17 [INFO] Conflict status:
UU README.md

2026-07-01T10:30:17 [INFO] ✓ Successfully created content conflict!
2026-07-01T10:30:17 [INFO]   Branches: conflict-test-a-content, conflict-test-b-content
2026-07-01T10:30:17 [INFO]   Conflicting file: README.md
2026-07-01T10:30:17 [INFO]   To resolve: git merge --abort
```

**Usage in CI:**

```yaml
# Example GitHub Actions workflow
- name: Test merge conflict handling
  run: |
    python3 scripts/simulate_conflicts.py --scenario content
    # Your conflict resolution test logic here
    python3 scripts/simulate_conflicts.py --cleanup
```

**Notes**:
- The script requires a clean working directory (no uncommitted changes)
- Base branch is auto-detected (main/master) or can be specified with `--base-branch`
- Target files default to universal files (README.md, LICENSE) or can be customized with `--target-file`
- After creating conflicts, use `git merge --abort` to clean up, or run the script with `--cleanup`
- The script returns to your original branch after creating conflicts (unless it was a test branch)

### Log File Analysis

Monitor the trigger log for debugging:

```bash
tail -f /tmp/p4ai_trigger.log
```

Log entries include:
- Trigger firing events
- Description generation decisions
- AI generation results
- Error messages (if any)

## Troubleshooting

### Common Issues

**Issue: Trigger doesn't fire**
- Verify the trigger is correctly configured in `p4 triggers`
- Check file permissions on `trigger.py`
- Ensure Python path is correct

**Issue: Description not generated**
- Check the log file at `$P4AI_LOG_FILE` for errors
- Verify AI provider credentials are accessible
- Ensure the p4ai package is installed for the server user
- Check that the description matches a placeholder pattern

**Issue: Permission denied errors**
- Ensure the Perforce server user has access to:
  - The trigger script
  - The log file location
  - The configuration file and API keys

**Issue: API errors**
- Verify API keys are valid and have sufficient quota
- Check network connectivity from the Perforce server to the AI provider
- Review rate limiting settings

### Debug Mode

To enable more verbose logging, modify the `trigger.py` script (line 48):

```python
# Change from:
logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT, datefmt=_DATE_FORMAT)

# To:
logging.basicConfig(level=logging.DEBUG, format=_LOG_FORMAT, datefmt=_DATE_FORMAT)
```

## Contributing

Contributions are welcome! To contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes following the existing code style:
   - Use type hints
   - Include docstrings for functions and classes
   - Follow PEP 8 conventions
   - Maintain non-blocking error handling
4. Test your changes locally
5. Submit a pull request with a clear description of your changes

### Code Style

- Python 3.7+ with type hints (`from __future__ import annotations`)
- Comprehensive docstrings in reStructuredText format
- Descriptive logging with context-specific log adapters
- Non-blocking error handling (trigger must never block submits)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Copyright (c) 2026 Himanshu-jn52

---

**Need Help?**

- Check the logs at `/tmp/p4ai_trigger.log` (or your configured `P4AI_LOG_FILE` path)
- Review the [Troubleshooting](#troubleshooting) section above
- Ensure all prerequisites are met and properly configured
