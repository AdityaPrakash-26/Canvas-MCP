#!/usr/bin/env python3
"""
Master test script for Canvas-MCP.

This script runs all the test scripts and generates a comprehensive report.

Usage:
    python scripts/run_all_tests.py [--verbose] [--fix] [--term_id TERM_ID]

Options:
    --verbose       Enable verbose logging
    --fix           Attempt to fix identified issues
    --term_id       Specify a term ID to sync (default: -1, most recent term)
"""

import argparse
import logging
import subprocess
import sys
import time
from datetime import datetime

# Configure logging
log_file = f"canvas_mcp_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("master_test")


def run_test_script(script_path, args=None):
    """Run a test script and return the result."""
    cmd = [sys.executable, script_path]
    if args:
        cmd.extend(args)

    logger.info(f"Running: {' '.join(cmd)}")

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end_time = time.time()

    elapsed_time = end_time - start_time

    if result.returncode == 0:
        logger.info(
            f"✅ {script_path} completed successfully in {elapsed_time:.2f} seconds"
        )
    else:
        logger.error(
            f"❌ {script_path} failed with exit code {result.returncode} in {elapsed_time:.2f} seconds"
        )

    # Log stdout and stderr
    if result.stdout:
        for line in result.stdout.splitlines():
            logger.debug(f"STDOUT: {line}")

    if result.stderr:
        for line in result.stderr.splitlines():
            logger.warning(f"STDERR: {line}")

    return {
        "script": script_path,
        "success": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "elapsed_time": elapsed_time,
    }


def run_pytest(test_path, args=None):
    """Run pytest on a test path and return the result."""
    cmd = [sys.executable, "-m", "pytest", "-xvs", test_path]
    if args:
        cmd.extend(args)

    logger.info(f"Running: {' '.join(cmd)}")

    start_time = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True)
    end_time = time.time()

    elapsed_time = end_time - start_time

    if result.returncode == 0:
        logger.info(
            f"✅ pytest {test_path} completed successfully in {elapsed_time:.2f} seconds"
        )
    else:
        logger.error(
            f"❌ pytest {test_path} failed with exit code {result.returncode} in {elapsed_time:.2f} seconds"
        )

    # Log stdout and stderr
    if result.stdout:
        for line in result.stdout.splitlines():
            logger.debug(f"STDOUT: {line}")

    if result.stderr:
        for line in result.stderr.splitlines():
            logger.warning(f"STDERR: {line}")

    return {
        "script": f"pytest {test_path}",
        "success": result.returncode == 0,
        "exit_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "elapsed_time": elapsed_time,
    }


def generate_report(results):
    """Generate a comprehensive test report."""
    report_path = (
        f"canvas_mcp_test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )

    with open(report_path, "w") as f:
        f.write("# Canvas-MCP Test Report\n\n")
        f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        # Summary
        total_tests = len(results)
        passed_tests = sum(1 for r in results if r["success"])
        failed_tests = total_tests - passed_tests
        total_time = sum(r["elapsed_time"] for r in results)

        f.write("## Summary\n\n")
        f.write(f"- Total tests: {total_tests}\n")
        f.write(f"- Passed: {passed_tests}\n")
        f.write(f"- Failed: {failed_tests}\n")
        f.write(f"- Total time: {total_time:.2f} seconds\n\n")

        # Test results
        f.write("## Test Results\n\n")

        for result in results:
            status = "✅ PASSED" if result["success"] else "❌ FAILED"
            f.write(f"### {result['script']} - {status}\n\n")
            f.write(f"- Exit code: {result['exit_code']}\n")
            f.write(f"- Elapsed time: {result['elapsed_time']:.2f} seconds\n\n")

            if not result["success"]:
                f.write("#### Error Details\n\n")
                f.write("```\n")
                if result["stderr"]:
                    f.write(result["stderr"])
                else:
                    f.write("No error details available\n")
                f.write("```\n\n")

        # Recommendations
        f.write("## Recommendations\n\n")

        if failed_tests > 0:
            f.write("### Issues to Address\n\n")
            for result in results:
                if not result["success"]:
                    f.write(f"- Fix issues in {result['script']}\n")
            f.write("\n")
        else:
            f.write("All tests passed! No issues to address.\n\n")

    logger.info(f"Test report generated: {report_path}")
    return report_path


def main():
    """Main function to run all tests."""
    parser = argparse.ArgumentParser(description="Run all Canvas-MCP tests")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--fix", action="store_true", help="Attempt to fix identified issues"
    )
    parser.add_argument(
        "--term_id",
        type=int,
        default=-1,
        help="Term ID to sync (default: -1, most recent term)",
    )
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    logger.info("Starting comprehensive Canvas-MCP testing")

    # List of tests to run
    tests = [
        # First run the unit and integration tests
        {"type": "pytest", "path": "tests/unit/"},
        {"type": "pytest", "path": "tests/integration/"},
        # Core test utilities
        {
            "type": "script",
            "path": "scripts/extract_tools_test.py",
            "args": ["--test"] + (["--verbose"] if args.verbose else []),
        },
        {
            "type": "script",
            "path": "scripts/direct_tools_test.py",
            "args": ["--test"] + (["--verbose"] if args.verbose else []),
        },
        {
            "type": "script",
            "path": "scripts/diagnostics/test_tools_integration.py",
            "args": ["--verbose"] if args.verbose else [],
        },
        # Then run the diagnostic scripts
        {
            "type": "script",
            "path": "scripts/diagnostics/test_full_sync_process.py",
            "args": [f"--term_id={args.term_id}"],
        },
        {
            "type": "script",
            "path": "scripts/diagnostics/check_database_relationships.py",
            "args": ["--fix"] if args.fix else [],
        },
        {"type": "script", "path": "scripts/diagnostics/test_error_handling.py"},
    ]

    # Run all tests and collect results
    results = []

    for test in tests:
        if test["type"] == "pytest":
            result = run_pytest(test["path"], test.get("args"))
        else:  # script
            result = run_test_script(test["path"], test.get("args"))

        results.append(result)

    # Generate report
    report_path = generate_report(results)

    # Print summary
    total_tests = len(results)
    passed_tests = sum(1 for r in results if r["success"])
    failed_tests = total_tests - passed_tests

    logger.info("\nTest Summary:")
    logger.info(f"- Total tests: {total_tests}")
    logger.info(f"- Passed: {passed_tests}")
    logger.info(f"- Failed: {failed_tests}")
    logger.info(f"- Report: {report_path}")

    if failed_tests > 0:
        logger.warning("Some tests failed. See the report for details.")
        sys.exit(1)
    else:
        logger.info("All tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
