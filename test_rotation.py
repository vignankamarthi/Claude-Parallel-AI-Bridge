#!/usr/bin/env python3
"""
Test log rotation by generating large amounts of log data.
"""

import os
from utils.logger import SystemLogger, log_entry, log_exit

def generate_large_logs():
    """Generate enough logs to trigger rotation."""
    log_entry("generate_large_logs")

    # Generate a large string (1KB)
    large_data = "x" * 1000

    print("Generating large logs to test rotation...")
    print("This will create approximately 10MB of logs...")

    # Generate approximately 10MB of logs (10,000 x 1KB entries)
    for i in range(10000):
        if i % 1000 == 0:
            print(f"Progress: {i/10000*100:.1f}%")

        SystemLogger.info(f"Large log entry {i}", {
            "iteration": i,
            "data": large_data,
            "nested": {
                "level1": {
                    "level2": {
                        "level3": f"Deep nested data {i}"
                    }
                }
            },
            "array": list(range(100))
        })

        # Also generate some errors every 100 iterations
        if i % 100 == 0 and i > 0:
            SystemLogger.error(
                f"Test error at iteration {i}",
                context={
                    "iteration": i,
                    "data": large_data,
                    "nested": {
                        "level1": {
                            "level2": {
                                "level3": f"Deep nested data {i}"
                            }
                        }
                    },
                    "array": list(range(100))
                }
            )

    print("Progress: 100.0%")
    log_exit("generate_large_logs", {"total_entries": 10000})

def check_rotation():
    """Check if log rotation occurred."""
    log_entry("check_rotation")

    log_files = []
    if os.path.exists("logs"):
        for file in sorted(os.listdir("logs")):
            filepath = os.path.join("logs", file)
            size = os.path.getsize(filepath)
            log_files.append((file, size))

    SystemLogger.info("Log files after rotation test", {
        "files": [{"name": f, "size_bytes": s, "size_mb": round(s/1024/1024, 2)} for f, s in log_files]
    })

    # Check for rotated files
    rotated_files = [f for f, _ in log_files if ".log." in f]
    if rotated_files:
        print(f"\n✅ LOG ROTATION SUCCESSFUL! Found rotated files: {rotated_files}")
    else:
        print("\n⚠️  No rotated files found (may need more logs to trigger rotation)")

    print("\nCurrent log files:")
    for file, size in log_files:
        print(f"  📁 {file:<25} ({size:,} bytes / {size/1024/1024:.2f} MB)")

    log_exit("check_rotation", {"rotated_files": rotated_files})

def main():
    """Run log rotation test."""
    print("\n" + "="*60)
    print("TESTING LOG ROTATION")
    print("="*60 + "\n")

    SystemLogger.info("Starting log rotation test")

    # Check initial state
    print("Initial log files:")
    if os.path.exists("logs"):
        for file in os.listdir("logs"):
            filepath = os.path.join("logs", file)
            size = os.path.getsize(filepath)
            print(f"  📁 {file:<25} ({size:,} bytes)")
    print()

    # Generate large logs
    generate_large_logs()

    # Check for rotation
    check_rotation()

    SystemLogger.info("Log rotation test completed")

    print("\nTo manually check logs:")
    print("  ls -lh logs/          # List all log files")
    print("  tail logs/system.log  # View latest entries")
    print()

if __name__ == "__main__":
    main()