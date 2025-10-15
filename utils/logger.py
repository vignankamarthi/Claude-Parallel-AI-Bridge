"""
Comprehensive logging system for Parallel AI MCP Server.

Features automatic function detection, contextual error reporting, rotating file handlers,
and automatic cleanup of old logs. Based on agent-coordination-framework logging system.

Author: Vignan Kamarthi
"""

import logging
import logging.handlers
import traceback
import inspect
import os
import glob
from datetime import datetime, timedelta
from typing import Optional, Any


class SystemLogger:
    """
    Comprehensive logging system with automatic function detection and contextual error reporting.
    Provides INFO, DEBUG, and ERROR levels with human-readable messages and precise failure locations.
    """

    _logger = None
    _initialized = False

    @classmethod
    def _initialize(cls):
        """Initialize the logging system with rotating file handlers and console output."""
        if cls._initialized:
            return

        # Create logs directory if it doesn't exist
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        # Clean up old log files first
        cls._cleanup_old_logs(log_dir)

        # Configure the logger
        cls._logger = logging.getLogger("ParallelMCP")
        cls._logger.setLevel(logging.DEBUG)

        # Prevent duplicate handlers
        cls._logger.handlers.clear()

        # Console handler for development
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        cls._logger.addHandler(console_handler)

        # Rotating file handler for all logs (10MB max, keep 5 files)
        file_handler = logging.handlers.RotatingFileHandler(
            f"{log_dir}/system.log",
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(funcName)s() - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        cls._logger.addHandler(file_handler)

        # Rotating error-only file handler (5MB max, keep 3 files)
        error_handler = logging.handlers.RotatingFileHandler(
            f"{log_dir}/errors.log",
            maxBytes=5*1024*1024,  # 5MB
            backupCount=3
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        cls._logger.addHandler(error_handler)

        cls._initialized = True
        cls._logger.info("SystemLogger initialized successfully")

    @classmethod
    def _cleanup_old_logs(cls, log_dir: str, max_age_days: int = 30):
        """Remove log files older than max_age_days."""
        try:
            cutoff_time = datetime.now() - timedelta(days=max_age_days)

            # Find all log files
            log_patterns = [
                os.path.join(log_dir, "*.log"),
                os.path.join(log_dir, "*.log.*")  # Rotated log files
            ]

            deleted_count = 0
            for pattern in log_patterns:
                for log_file in glob.glob(pattern):
                    try:
                        # Get file modification time
                        file_mtime = datetime.fromtimestamp(os.path.getmtime(log_file))

                        if file_mtime < cutoff_time:
                            os.remove(log_file)
                            deleted_count += 1
                    except OSError:
                        # Ignore errors when deleting individual files
                        pass

            if deleted_count > 0:
                print(f"Cleaned up {deleted_count} old log files older than {max_age_days} days")

        except Exception:
            # Ignore cleanup errors - logging should still work
            pass

    @classmethod
    def _get_caller_info(cls, stack_level: int = 2):
        """Automatically detect function name, file name, and line number from call stack."""
        try:
            frame = inspect.stack()[stack_level]
            return {
                'function_name': frame.function,
                'file_name': os.path.basename(frame.filename),
                'line_number': frame.lineno,
                'code_context': frame.code_context[0].strip() if frame.code_context else "N/A"
            }
        except Exception:
            return {
                'function_name': 'unknown',
                'file_name': 'unknown',
                'line_number': 0,
                'code_context': 'N/A'
            }

    @classmethod
    def info(cls, message: str, context: Optional[dict] = None):
        """
        Log informational messages with automatic caller detection.

        Args:
            message: Human-readable info message
            context: Optional dictionary with additional context
        """
        cls._initialize()
        caller_info = cls._get_caller_info()

        log_message = f"[{caller_info['file_name']}:{caller_info['function_name']}()] {message}"
        if context:
            log_message += f" | Context: {context}"

        cls._logger.info(log_message)

    @classmethod
    def debug(cls, message: str, context: Optional[dict] = None):
        """
        Log debug messages with execution context.

        Args:
            message: Human-readable debug message
            context: Optional dictionary with debug context
        """
        cls._initialize()
        caller_info = cls._get_caller_info()

        log_message = f"[{caller_info['file_name']}:{caller_info['function_name']}()] DEBUG: {message}"
        if context:
            log_message += f" | Context: {context}"

        cls._logger.debug(log_message)

    @classmethod
    def error(cls, message: str, exception: Optional[Exception] = None, context: Optional[dict] = None, fail_fast: bool = False):
        """
        Log errors with precise failure location and code context.

        Args:
            message: Human-readable error message
            exception: The exception that occurred (if any)
            context: Optional dictionary with error context
            fail_fast: Whether to raise the exception after logging
        """
        cls._initialize()
        caller_info = cls._get_caller_info()

        # Build comprehensive error message
        error_parts = [
            f"ERROR in {caller_info['file_name']}:{caller_info['function_name']}() at line {caller_info['line_number']}",
            f"Code: {caller_info['code_context']}",
            f"Message: {message}"
        ]

        if exception:
            error_parts.append(f"Exception: {type(exception).__name__}: {str(exception)}")
            error_parts.append(f"Traceback: {traceback.format_exc()}")

        if context:
            error_parts.append(f"Context: {context}")

        full_error_message = " | ".join(error_parts)
        cls._logger.error(full_error_message)

        # Fail fast if requested
        if fail_fast and exception:
            raise exception
        elif fail_fast and not exception:
            raise RuntimeError(f"System failure: {message}")

    @classmethod
    def entry(cls, function_name: Optional[str] = None, params: Optional[dict] = None):
        """Log function entry with parameters."""
        cls._initialize()
        caller_info = cls._get_caller_info()
        func_name = function_name or caller_info['function_name']

        log_message = f"ENTERING {caller_info['file_name']}:{func_name}()"
        if params:
            log_message += f" with params: {params}"

        cls._logger.debug(log_message)

    @classmethod
    def exit(cls, function_name: Optional[str] = None, result: Optional[Any] = None):
        """Log function exit with result."""
        cls._initialize()
        caller_info = cls._get_caller_info()
        func_name = function_name or caller_info['function_name']

        log_message = f"EXITING {caller_info['file_name']}:{func_name}()"
        if result is not None:
            # For complex results, just log the type
            if isinstance(result, (dict, list)) and len(str(result)) > 100:
                log_message += f" with result: {type(result).__name__}(length={len(result)})"
            else:
                log_message += f" with result: {result}"

        cls._logger.debug(log_message)

    @classmethod
    def warning(cls, message: str, context: Optional[dict] = None):
        """
        Log warning messages with context.

        Args:
            message: Human-readable warning message
            context: Optional dictionary with warning context
        """
        cls._initialize()
        caller_info = cls._get_caller_info()

        log_message = f"[{caller_info['file_name']}:{caller_info['function_name']}()] WARNING: {message}"
        if context:
            log_message += f" | Context: {context}"

        cls._logger.warning(log_message)

    @classmethod
    def progress(cls, progress: float, total: float, message: str):
        """
        Log progress updates for long-running operations.

        Args:
            progress: Current progress value
            total: Total value for completion
            message: Progress message
        """
        cls._initialize()
        percent = (progress / total * 100) if total > 0 else 0
        cls._logger.info(f"PROGRESS: {percent:.1f}% - {message}")


# Convenience aliases for cleaner imports
logger = SystemLogger
log_info = SystemLogger.info
log_debug = SystemLogger.debug
log_error = SystemLogger.error
log_entry = SystemLogger.entry
log_exit = SystemLogger.exit
log_warning = SystemLogger.warning
log_progress = SystemLogger.progress