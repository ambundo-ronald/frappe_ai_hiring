#!/usr/bin/env python
# Copyright (c) 2025, Your Company and contributors
# For license information, please see license.txt

"""
Test runner utilities for frappe_ai_hiring
Run tests against local ERPNext instance
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def run_tests(test_type="all", verbose=False, coverage=False, markers=None):
	"""
	Run tests with pytest

	Args:
		test_type: 'unit', 'integration', 'all'
		verbose: Show verbose output
		coverage: Generate coverage report
		markers: pytest markers to filter tests
	"""
	cmd = ["python", "-m", "pytest"]

	test_dir = Path(__file__).parent / "frappe_ai_hiring" / "ai_hiring" / "tests"

	if test_type == "unit":
		cmd.append(str(test_dir / "test_services.py"))
	elif test_type == "integration":
		cmd.append(str(test_dir / "test_integration.py"))
	else:
		cmd.append(str(test_dir))

	if verbose:
		cmd.append("-vv")
	else:
		cmd.append("-v")

	if coverage:
		cmd.extend([
			"--cov=frappe_ai_hiring",
			"--cov-report=html",
			"--cov-report=term-missing",
		])

	if markers:
		cmd.append(f"-m {markers}")

	# Add common pytest options
	cmd.extend([
		"--tb=short",
		"-p", "no:warnings",
	])

	print(f"Running: {' '.join(cmd)}")
	result = subprocess.run(cmd)
	return result.returncode


def run_frappe_tests():
	"""Run tests using Frappe's built-in test runner"""
	cmd = [
		"bench",
		"test",
		"--app", "frappe_ai_hiring",
		"--verbose",
	]
	print(f"Running: {' '.join(cmd)}")
	result = subprocess.run(cmd)
	return result.returncode


def main():
	"""Main test runner"""
	parser = argparse.ArgumentParser(
		description="Run frappe_ai_hiring tests"
	)
	parser.add_argument(
		"--type",
		choices=["unit", "integration", "all"],
		default="all",
		help="Type of tests to run",
	)
	parser.add_argument(
		"--verbose",
		"-v",
		action="store_true",
		help="Verbose output",
	)
	parser.add_argument(
		"--coverage",
		"-c",
		action="store_true",
		help="Generate coverage report",
	)
	parser.add_argument(
		"--frappe",
		"-f",
		action="store_true",
		help="Use Frappe's built-in test runner",
	)
	parser.add_argument(
		"--markers",
		"-m",
		help="pytest markers to filter tests",
	)

	args = parser.parse_args()

	if args.frappe:
		return run_frappe_tests()
	else:
		return run_tests(
			test_type=args.type,
			verbose=args.verbose,
			coverage=args.coverage,
			markers=args.markers,
		)


if __name__ == "__main__":
	sys.exit(main())
