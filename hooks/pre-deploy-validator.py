#!/usr/bin/env python3
"""
Pre-deployment validation script.

Performs comprehensive checks before deployment to catch common issues:
- Git repository state
- Uncommitted changes
- Branch validation
- Recent test results
- Documentation updates
- Environment file checks
- Deployment checklist verification

Usage:
  ./pre-deploy-validator.py [--branch main] [--require-tests] [--strict]

Exit codes:
  0 - All checks passed, ready to deploy
  1 - Critical issues found, do not deploy
  2 - Warnings found, review before deploying
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Dict, Tuple


class Colors:
    """Terminal colors for output"""
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'


class ValidationResult:
    """Store validation results"""
    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []
        self.passed: List[str] = []

    def add_error(self, msg: str):
        self.errors.append(msg)

    def add_warning(self, msg: str):
        self.warnings.append(msg)

    def add_info(self, msg: str):
        self.info.append(msg)

    def add_passed(self, msg: str):
        self.passed.append(msg)

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def exit_code(self) -> int:
        if self.has_errors():
            return 1
        if self.has_warnings():
            return 2
        return 0


def run_command(cmd: List[str], cwd: str = None) -> Tuple[int, str, str]:
    """Run shell command and return exit code, stdout, stderr"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Command timeout"
    except Exception as e:
        return 1, "", str(e)


def check_git_status(result: ValidationResult, target_branch: str = None):
    """Check git repository status"""
    # Check if in git repo
    code, _, _ = run_command(['git', 'rev-parse', '--git-dir'])
    if code != 0:
        result.add_error("Not in a git repository")
        return

    result.add_passed("Git repository detected")

    # Check for uncommitted changes
    code, output, _ = run_command(['git', 'status', '--porcelain'])
    if code == 0 and output.strip():
        result.add_error("Uncommitted changes detected. Commit or stash before deploying.")
        result.add_info(f"Changed files:\n{output[:500]}")
    else:
        result.add_passed("No uncommitted changes")

    # Check current branch
    code, output, _ = run_command(['git', 'branch', '--show-current'])
    if code == 0:
        current_branch = output.strip()
        result.add_info(f"Current branch: {current_branch}")

        if target_branch and current_branch != target_branch:
            result.add_warning(f"Not on target branch '{target_branch}' (currently on '{current_branch}')")

    # Check if ahead/behind remote
    code, output, _ = run_command(['git', 'status', '-sb'])
    if code == 0:
        if 'ahead' in output:
            result.add_warning("Local branch is ahead of remote. Push changes before deploying.")
        elif 'behind' in output:
            result.add_warning("Local branch is behind remote. Pull changes first.")
        else:
            result.add_passed("Branch synchronized with remote")


def check_changelog(result: ValidationResult):
    """Check if CHANGELOG is updated"""
    changelog_paths = ['CHANGELOG.md', 'CHANGELOG.MD', 'CHANGELOG', 'docs/CHANGELOG.md']

    changelog_found = False
    for path in changelog_paths:
        if Path(path).exists():
            changelog_found = True
            result.add_passed(f"CHANGELOG found: {path}")

            # Check if recently modified (within last 7 days)
            code, output, _ = run_command(['git', 'log', '-1', '--format=%ct', path])
            if code == 0 and output.strip():
                import time
                last_modified = int(output.strip())
                days_ago = (time.time() - last_modified) / 86400

                if days_ago > 7:
                    result.add_warning(f"CHANGELOG not updated recently (last update: {int(days_ago)} days ago)")
            break

    if not changelog_found:
        result.add_warning("No CHANGELOG.md found in repository")


def check_tests(result: ValidationResult, require_tests: bool = False):
    """Check for test files and recent test results"""
    test_patterns = ['tests/', 'test/', '**/test_*.py', '**/*.test.js', '**/*.spec.ts']

    test_files_found = False
    for pattern in test_patterns:
        if list(Path('.').glob(pattern)):
            test_files_found = True
            break

    if not test_files_found:
        if require_tests:
            result.add_error("No test files found (required for deployment)")
        else:
            result.add_warning("No test files found")
        return

    result.add_passed("Test files detected")

    # Check for recent test execution evidence
    test_result_files = ['.pytest_cache', 'coverage', '.coverage', 'test-results']
    recent_tests = False

    for test_file in test_result_files:
        path = Path(test_file)
        if path.exists():
            recent_tests = True
            break

    if not recent_tests:
        result.add_warning("No evidence of recent test execution. Run tests before deploying.")
    else:
        result.add_info("Test execution artifacts found (ensure tests passed)")


def check_environment_files(result: ValidationResult):
    """Check for environment file issues"""
    env_files = ['.env', '.env.production', '.env.local']

    for env_file in env_files:
        if Path(env_file).exists():
            result.add_info(f"Environment file found: {env_file}")

            # Check if tracked in git (should not be)
            code, output, _ = run_command(['git', 'ls-files', '--error-unmatch', env_file])
            if code == 0:
                result.add_error(f"Environment file '{env_file}' is tracked in git (security risk)")


def check_dependencies(result: ValidationResult):
    """Check dependency files are up to date"""
    dependency_files = {
        'requirements.txt': ['pip', 'freeze'],
        'package.json': ['npm', 'outdated'],
        'Pipfile': ['pipenv', 'check'],
    }

    for dep_file, check_cmd in dependency_files.items():
        if Path(dep_file).exists():
            result.add_passed(f"Dependency file found: {dep_file}")

            # Check if recently modified
            code, output, _ = run_command(['git', 'log', '-1', '--format=%ct', dep_file])
            if code == 0 and output.strip():
                import time
                last_modified = int(output.strip())
                days_ago = (time.time() - last_modified) / 86400

                if days_ago > 30:
                    result.add_info(f"{dep_file} not updated recently ({int(days_ago)} days)")


def check_project_specific(result: ValidationResult):
    """Check project-specific requirements from CLAUDE.md"""
    claude_md = Path('CLAUDE.md')

    if claude_md.exists():
        result.add_passed("CLAUDE.md found")

        # Look for deployment section
        content = claude_md.read_text()
        if 'deployment' in content.lower():
            result.add_info("Deployment instructions found in CLAUDE.md - review before deploying")
        else:
            result.add_warning("No deployment section found in CLAUDE.md")
    else:
        result.add_info("No CLAUDE.md found (project instructions)")


def print_results(result: ValidationResult):
    """Print validation results with colors"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}Pre-Deployment Validation Results{Colors.END}")
    print(f"{Colors.BOLD}{'='*60}{Colors.END}\n")

    if result.passed:
        print(f"{Colors.GREEN}✓ PASSED CHECKS:{Colors.END}")
        for msg in result.passed:
            print(f"  {Colors.GREEN}✓{Colors.END} {msg}")
        print()

    if result.info:
        print(f"{Colors.BLUE}ℹ INFORMATION:{Colors.END}")
        for msg in result.info:
            print(f"  {Colors.BLUE}ℹ{Colors.END} {msg}")
        print()

    if result.warnings:
        print(f"{Colors.YELLOW}⚠ WARNINGS:{Colors.END}")
        for msg in result.warnings:
            print(f"  {Colors.YELLOW}⚠{Colors.END} {msg}")
        print()

    if result.errors:
        print(f"{Colors.RED}✗ ERRORS (BLOCKING):{Colors.END}")
        for msg in result.errors:
            print(f"  {Colors.RED}✗{Colors.END} {msg}")
        print()

    print(f"{Colors.BOLD}{'='*60}{Colors.END}")

    if result.has_errors():
        print(f"{Colors.RED}{Colors.BOLD}DEPLOYMENT BLOCKED - Fix errors before proceeding{Colors.END}")
        return 1
    elif result.has_warnings():
        print(f"{Colors.YELLOW}{Colors.BOLD}WARNINGS DETECTED - Review carefully before deploying{Colors.END}")
        return 2
    else:
        print(f"{Colors.GREEN}{Colors.BOLD}ALL CHECKS PASSED - Ready to deploy{Colors.END}")
        return 0


def main():
    parser = argparse.ArgumentParser(description='Pre-deployment validation')
    parser.add_argument('--branch', help='Required deployment branch (e.g., main)')
    parser.add_argument('--require-tests', action='store_true', help='Require test files')
    parser.add_argument('--strict', action='store_true', help='Treat warnings as errors')

    args = parser.parse_args()

    result = ValidationResult()

    print(f"{Colors.BOLD}Running pre-deployment validation...{Colors.END}\n")

    # Run all checks
    check_git_status(result, args.branch)
    check_changelog(result)
    check_tests(result, args.require_tests)
    check_environment_files(result)
    check_dependencies(result)
    check_project_specific(result)

    # Print results
    exit_code = print_results(result)

    # Strict mode: treat warnings as errors
    if args.strict and result.has_warnings():
        exit_code = 1

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
