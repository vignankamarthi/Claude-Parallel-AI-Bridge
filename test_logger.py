#!/usr/bin/env python3
"""
Test script to verify the SystemLogger functionality.
"""

import os
import time
from utils.logger import SystemLogger, log_entry, log_exit, log_warning, log_progress

def test_basic_logging():
    """Test basic logging functionality."""
    log_entry("test_basic_logging")

    # Test different log levels
    SystemLogger.info("Testing INFO level", {"test": "basic", "level": "info"})
    SystemLogger.debug("Testing DEBUG level", {"test": "basic", "level": "debug"})
    SystemLogger.warning("Testing WARNING level", {"test": "basic", "level": "warning"})

    # Test error without exception
    SystemLogger.error("Testing ERROR level without exception", context={"test": "basic"})

    # Test error with exception (but don't fail fast)
    try:
        raise ValueError("Test exception for logging")
    except ValueError as e:
        SystemLogger.error("Testing ERROR level with exception", exception=e, context={"test": "basic"}, fail_fast=False)

    log_exit("test_basic_logging", {"status": "completed"})

def test_progress_logging():
    """Test progress logging."""
    log_entry("test_progress_logging")

    for i in range(5):
        log_progress(i, 4, f"Processing step {i+1}/5")
        time.sleep(0.1)

    log_exit("test_progress_logging")

def test_complex_context():
    """Test logging with complex context data."""
    log_entry("test_complex_context", {
        "nested": {
            "data": ["item1", "item2"],
            "count": 2
        }
    })

    SystemLogger.info("Testing complex context", {
        "user_data": {
            "id": "user123",
            "settings": {"theme": "dark", "language": "en"}
        },
        "metrics": {
            "response_time": 123.45,
            "success_rate": 0.95
        }
    })

    log_exit("test_complex_context", {"large_result": list(range(100))})

def test_log_files():
    """Verify log files are created."""
    log_entry("test_log_files")

    # Check if log directory exists
    if os.path.exists("logs"):
        SystemLogger.info("Logs directory exists", {
            "files": os.listdir("logs")
        })

        # Check for specific log files
        system_log = "logs/system.log"
        error_log = "logs/errors.log"

        if os.path.exists(system_log):
            size = os.path.getsize(system_log)
            SystemLogger.info(f"system.log exists", {"size_bytes": size})

        if os.path.exists(error_log):
            size = os.path.getsize(error_log)
            SystemLogger.info(f"errors.log exists", {"size_bytes": size})
    else:
        SystemLogger.warning("Logs directory does not exist yet")

    log_exit("test_log_files")

def main():
    """Run all logger tests."""
    print("\n" + "="*60)
    print("TESTING SYSTEMLOGGER")
    print("="*60 + "\n")

    SystemLogger.info("Starting logger tests", {"test_suite": "SystemLogger"})

    test_basic_logging()
    print("✅ Basic logging test completed")

    test_progress_logging()
    print("✅ Progress logging test completed")

    test_complex_context()
    print("✅ Complex context test completed")

    test_log_files()
    print("✅ Log files test completed")

    SystemLogger.info("All logger tests completed successfully")

    # Display log file locations
    print("\n" + "="*60)
    print("LOG FILES CREATED:")
    print("="*60)

    if os.path.exists("logs"):
        for file in os.listdir("logs"):
            filepath = os.path.join("logs", file)
            size = os.path.getsize(filepath)
            print(f"  📁 {file:<20} ({size:,} bytes)")

    print("\nTo view logs, run:")
    print("  tail -f logs/system.log    # All logs")
    print("  tail -f logs/errors.log    # Errors only")
    print()

if __name__ == "__main__":
    main()