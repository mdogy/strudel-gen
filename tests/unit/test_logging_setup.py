"""Tests for logging_setup.py."""

import logging
from pathlib import Path

from strudel_gen.logging_setup import APP_NAME, LOG_DIR, setup_logging


class TestLoggingSetup:
    def test_setup_logging_creates_log_dir(self):
        setup_logging("DEBUG")
        assert LOG_DIR.exists()
        assert LOG_DIR.is_dir()

    def test_setup_logging_sets_level(self):
        setup_logging("DEBUG")
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_default_level(self):
        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_logger_has_file_handler(self):
        setup_logging()
        root_logger = logging.getLogger()
        handlers = root_logger.handlers
        assert len(handlers) >= 1
        # At least one RotatingFileHandler
        has_file_handler = any(
            h.__class__.__name__ == "RotatingFileHandler" for h in handlers
        )
        assert has_file_handler
