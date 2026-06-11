#!/usr/bin/env python3
"""p4ai Perforce trigger script.

Install as a ``change-commit`` trigger so that every submitted changelist
automatically gets an AI-generated description (if the description is
empty or is the default placeholder).

Perforce trigger table entry
-----------------------------
::

    Triggers:
        p4ai-describe change-commit //... "/path/to/python /path/to/p4ai_trigger.py %changelist%"

Or, if p4ai is installed as a CLI tool and on PATH::

    Triggers:
        p4ai-describe change-commit //... "p4ai trigger-run %changelist%"

How it works
-------------
1. Receives the changelist number from Perforce (``%changelist%``).
2. Checks if the description is empty / default placeholder.
3. Calls ``p4ai describe --apply -c <CL>`` to generate + apply.
4. Exits 0 on success (trigger must not block submit).

Environment
-----------
- Set ``P4AI_PROVIDER``, ``P4PORT``, ``P4USER`` etc. as env vars, or
  ensure ``~/.p4ai/config.json`` is accessible by the trigger user.
- The trigger runs as the Perforce server's OS user, so the config and
  any API keys must be available to that user.
- Set ``P4AI_LOG_FILE`` to override the log file path
  (default: ``/tmp/p4ai_trigger.log``).
"""

from __future__ import annotations

import logging
import logging.handlers
import os
import sys

_LOG_FILE = os.environ.get("P4AI_LOG_FILE", "/tmp/p4ai_trigger.log")
_LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s cl=%(cl)s %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

logging.basicConfig(level=logging.INFO, format=_LOG_FORMAT, datefmt=_DATE_FORMAT)

_file_handler = logging.handlers.RotatingFileHandler(
    _LOG_FILE,
    maxBytes=5 * 1024 * 1024,  # 5 MiB
    backupCount=5,
    encoding="utf-8",
)
_file_handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))

log = logging.getLogger("p4ai.trigger")
log.addHandler(_file_handler)


class _CLAdapter(logging.LoggerAdapter):
    """Injects the current changelist number into every log record."""

    def process(self, msg, kwargs):
        kwargs.setdefault("extra", {})
        kwargs["extra"].setdefault("cl", self.extra.get("cl", "-"))
        return msg, kwargs


def _get_logger(changelist: str = "-") -> logging.LoggerAdapter:
    return _CLAdapter(log, {"cl": changelist})


# Default / placeholder descriptions that should be auto-generated
_PLACEHOLDER_PATTERNS = [
    "",
    "<enter description here>",
    "enter description here",
    "new changelist",
]


def should_generate(description: str) -> bool:
    """Return True if the CL description looks empty/default."""
    cleaned: str = description.strip().lower()
    if not cleaned:
        return True
    return any(cleaned == p for p in _PLACEHOLDER_PATTERNS)


def main() -> int:
    if len(sys.argv) < 2:
        _get_logger().error("Usage: p4ai_trigger.py <changelist>")
        return 0  # Don't block submit on trigger misconfiguration

    changelist = sys.argv[1]
    clog = _get_logger(changelist)
    clog.info("Trigger fired")

    try:
        from p4ai.config import load_config
        from p4ai.p4 import P4Client, P4Error
        from p4ai.ai import build_describe_prompt, run_ai

        config = load_config()
        p4 = P4Client(config)
        cl = p4.describe(changelist, with_diff=True)

        if not should_generate(cl.description):
            clog.info("CL already has a description, skipping.")
            return 0

        system, user_prompt = build_describe_prompt(cl)
        result = run_ai(config, system, user_prompt, stream=False)

        from p4ai.providers.base import ProviderResponse
        if isinstance(result, ProviderResponse):
            p4.update_description(changelist, result.text)
            clog.info("Auto-generated description applied successfully.")
        else:
            clog.warning("Unexpected AI response type: %s", type(result).__name__)

    except Exception as exc:
        # NEVER block a submit due to AI failure
        clog.warning("Trigger failed: %s", exc, exc_info=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
