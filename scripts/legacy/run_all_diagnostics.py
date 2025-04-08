#!/usr/bin/env python3
"""
Master diagnostic script for Canvas-MCP.

This script runs all diagnostic scripts and generates a comprehensive report.

Usage:
    python scripts/run_all_diagnostics.py [--verbose] [--fix] [--term_id TERM_ID]

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
from pathlib import Path

# Configure logging
log_file = f"canvas_mcp_diagnostics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file),
    ],
)
logger = logging.getLogger("diagnostics")


def run_diagnostic_script(script_path, args=None):
    """Run a diagnostic script and return the result."""
    if args is None:
        args = []

    script_path = Path(script_path)
    if not script_path.exists():
        logger.error(f"Script not found: {script_path}")
        return {
            "script": str(script_path),
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": f"Script not found: {script_path}",
            "elapsed_time": 0,
        }

    logger.info(f"Running {script_path} {' '.join(args)}")

    start_time = time.time()

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)] + args,
            capture_output=True,
            text=True,
            check=False,
        )
        elapsed_time = time.time() - start_time

        logger.info(
            f"Completed in {elapsed_time:.2f} seconds with exit code {result.returncode}"
        )

        if result.stdout:
            for line in result.stdout.splitlines():
                logger.info(f"STDOUT: {line}")

        if result.stderr:
            for line in result.stderr.splitlines():
                logger.warning(f"STDERR: {line}")

        return {
            "script": f"python {script_path} {' '.join(args)}",
            "success": result.returncode == 0,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "elapsed_time": elapsed_time,
        }
    except Exception as e:
        elapsed_time = time.time() - start_time
        logger.error(f"Error running {script_path}: {e}")
        return {
            "script": f"python {script_path} {' '.join(args)}",
            "success": False,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
            "elapsed_time": elapsed_time,
        }


def generate_report(results):
    """Generate a comprehensive diagnostic report."""
    report_path = (
        f"canvas_mcp_diagnostics_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    )

    passed_tests = sum(1 for result in results if result["success"])
    failed_tests = len(results) - passed_tests

    with open(report_path, "w") as f:
        f.write("# Canvas-MCP Diagnostic Report\n\n")
        f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

        f.write("## Summary\n\n")
        f.write(f"- Total tests: {len(results)}\n")
        f.write(f"- Passed: {passed_tests}\n")
        f.write(f"- Failed: {failed_tests}\n\n")

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

        f.write("### Next Steps\n\n")
        f.write("1. Review the detailed logs for any warnings or potential issues\n")
        f.write("2. Run the tests regularly to ensure continued reliability\n")
        f.write("3. Consider adding more tests for new functionality\n")

    logger.info(f"Report generated: {report_path}")
    return report_path


def main():
    """Main function to run all diagnostic scripts."""
    parser = argparse.ArgumentParser(
        description="Run all Canvas-MCP diagnostic scripts"
    )
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

    verbose_arg = ["--verbose"] if args.verbose else []
    fix_arg = ["--fix"] if args.fix else []
    term_id_arg = [f"--term_id={args.term_id}"]

    logger.info("Starting comprehensive Canvas-MCP diagnostics")

    # List of diagnostic scripts to run
    diagnostics = [
        {
            "path": "scripts/diagnostics/check_database_relationships.py",
            "args": fix_arg + verbose_arg,
        },
        {
            "path": "scripts/diagnostics/test_full_sync_process.py",
            "args": term_id_arg + verbose_arg,
        },
        {
            "path": "scripts/diagnostics/test_error_handling.py",
            "args": verbose_arg,
        },
        {
            "path": "scripts/diagnostics/test_tools_comprehensive.py",
            "args": fix_arg + verbose_arg,
        },
    ]

    # Run all diagnostic scripts and collect results
    results = []

    for diagnostic in diagnostics:
        result = run_diagnostic_script(diagnostic["path"], diagnostic["args"])
        results.append(result)

    # Generate report
    report_path = generate_report(results)

    # Print summary
    passed_tests = sum(1 for result in results if result["success"])
    failed_tests = len(results) - passed_tests

    logger.info("\nDiagnostic Summary:")
    logger.info(f"- Total tests: {len(results)}")
    logger.info(f"- Passed: {passed_tests}")
    logger.info(f"- Failed: {failed_tests}")
    logger.info(f"- Report: {report_path}")

    if failed_tests > 0:
        logger.error("Some diagnostic tests failed")
        sys.exit(1)
    else:
        logger.info("All diagnostic tests passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
