# p4ai - Perforce AI Trigger

**p4ai** is a Perforce trigger script that automatically generates AI-powered changelist descriptions for submissions with empty or placeholder descriptions.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

## Overview

p4ai integrates with Perforce as a `change-commit` trigger to enhance developer workflows by automatically generating meaningful changelist descriptions using AI. When a changelist is submitted with an empty or default placeholder description, p4ai analyzes the changes and generates a descriptive summary automatically.

The trigger is designed to be non-blocking and fail-safe: it never prevents a submit from succeeding, even if AI generation fails.

## Key Features

- **Automatic Description Generation**: Detects empty or placeholder changelist descriptions and auto-generates meaningful descriptions using AI
- **Non-Blocking Behavior**: Never blocks a submit operation, even on failures or errors
- **Smart Detection**: Recognizes common placeholder patterns like:
  - Empty descriptions
  - `<enter description here>`
  - `enter description here`
  - `new changelist`
- **Configurable Logging**: Rotating log files with configurable paths for audit and debugging
- **Environment-Based Configuration**: Flexible configuration via environment variables or config files

## Prerequisites

- **Python 3.x** (Python 3.7 or higher recommended)
- **Perforce Server**: Access to a Perforce server with trigger configuration permissions
- **p4ai Package**: The `p4ai` Python package and its dependencies must be installed and accessible to the Perforce server's OS user
- **AI Provider Access**: Valid API keys for the configured AI provider (e.g., OpenAI, Anthropic)

## Installation

### 1. Install the p4ai Package

Ensure the `p4ai` package is installed in the Python environment accessible to the Perforce server user:

```bash
pip install p4ai
```

### 2. Configure the Perforce Trigger

Add the trigger to your Perforce server's trigger table using `p4 triggers`:

```bash
p4 triggers
```

Add one of the following entries:

**Option A: Direct Python Script**
```
Triggers:
    p4ai-describe change-commit //... "/usr/bin/python3 /path/to/trigger.py %changelist%"
```

**Option B: Using p4ai CLI (if installed as a command-line tool)**
```
Triggers:
    p4ai-describe change-commit //... "p4ai trigger-run %changelist%"
```

Replace `/path/to/trigger.py` with the actual path to the `trigger.py` script.

### 3. Set Permissions

Ensure the Perforce server's OS user has:
- Read access to the trigger script
- Write access to the log file location (default: `/tmp/p4ai_trigger.log`)
- Access to configuration files and API keys

## Configuration

### Environment Variables

The trigger supports the following environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `P4AI_PROVIDER` | AI provider to use (e.g., `openai`, `anthropic`) | Required |
| `P4PORT` | Perforce server address | Required |
| `P4USER` | Perforce user for trigger operations | Required |
| `P4AI_LOG_FILE` | Path to the log file | `/tmp/p4ai_trigger.log` |

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

**Important**: The configuration file and API keys must be accessible to the OS user running the Perforce server process.

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

1. **Trigger Fires**: Perforce calls the trigger script after a changelist is submitted
2. **Description Check**: The script checks if the description is empty or a placeholder
3. **AI Generation**: If needed, p4ai analyzes the changelist diff and generates a description
4. **Apply**: The generated description is applied to the changelist
5. **Non-Blocking Exit**: The trigger always exits successfully (code 0), ensuring submits are never blocked

## Project Structure

```
.
├── trigger.py           # Main trigger script
├── LICENSE             # MIT License
└── README.md           # This file
```

### Key Components

- **`trigger.py`**: The main trigger script containing:
  - `should_generate(description)`: Determines if a description needs AI generation
  - `main()`: Entry point that orchestrates the trigger workflow
  - Logging configuration with rotating file handlers
  - Non-blocking error handling

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

To test the trigger behavior:

1. Create a test changelist
2. Add some files to the changelist
3. Submit with an empty or placeholder description
4. Check the log file for trigger execution details
5. Verify the description was updated

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

To enable more verbose logging, modify the `trigger.py` script:

```python
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
