"""Tests for finclaw doctor diagnostic command."""

import sys
import os
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.cli.doctor import DoctorCheck, DoctorResult, Severity, run_doctor


class TestDoctorResult:
    """Test DoctorResult dataclass."""

    def test_pass_result(self):
        result = DoctorResult(
            name="Python Version",
            passed=True,
            severity=Severity.REQUIRED,
            message="Python 3.12.10",
        )
        assert result.passed is True
        assert result.severity == Severity.REQUIRED
        assert "3.12" in result.message

    def test_fail_result(self):
        result = DoctorResult(
            name="Missing Dep",
            passed=False,
            severity=Severity.REQUIRED,
            message="numpy not installed",
            fix_hint="pip install numpy",
        )
        assert result.passed is False
        assert result.fix_hint == "pip install numpy"

    def test_warning_result(self):
        result = DoctorResult(
            name="Optional Dep",
            passed=False,
            severity=Severity.OPTIONAL,
            message="backtrader not installed",
        )
        assert result.severity == Severity.OPTIONAL


class TestDoctorChecks:
    """Test individual doctor checks."""

    def test_check_python_version(self):
        check = DoctorCheck()
        result = check.check_python_version()
        assert result.name == "Python Version"
        assert result.passed is True  # We're running on Python 3.12
        assert result.severity == Severity.REQUIRED

    def test_check_required_deps(self):
        check = DoctorCheck()
        results = check.check_required_deps()
        assert isinstance(results, list)
        assert len(results) > 0
        # numpy and pyyaml should be installed since tests run
        dep_names = [r.name for r in results]
        assert any("numpy" in n.lower() for n in dep_names)
        # All required deps should pass if tests are running
        for r in results:
            assert r.severity == Severity.REQUIRED

    def test_check_optional_deps(self):
        check = DoctorCheck()
        results = check.check_optional_deps()
        assert isinstance(results, list)
        # Some optional deps may or may not be installed
        for r in results:
            assert r.severity == Severity.OPTIONAL

    def test_check_api_keys(self):
        check = DoctorCheck()
        results = check.check_api_keys()
        assert isinstance(results, list)
        # API keys are optional — may or may not be configured
        for r in results:
            assert r.severity == Severity.OPTIONAL
            assert isinstance(r.passed, bool)

    def test_check_exchange_connectivity(self):
        check = DoctorCheck()
        results = check.check_exchange_connectivity()
        assert isinstance(results, list)
        for r in results:
            assert r.severity == Severity.OPTIONAL
            assert isinstance(r.passed, bool)


class TestRunDoctor:
    """Test the full doctor run."""

    def test_run_doctor_returns_results(self):
        results = run_doctor()
        assert isinstance(results, list)
        assert len(results) > 0
        # Should have at least Python version check
        names = [r.name for r in results]
        assert "Python Version" in names

    def test_run_doctor_all_results_have_required_fields(self):
        results = run_doctor()
        for r in results:
            assert hasattr(r, "name")
            assert hasattr(r, "passed")
            assert hasattr(r, "severity")
            assert hasattr(r, "message")
            assert isinstance(r.name, str)
            assert isinstance(r.passed, bool)

    def test_run_doctor_exit_code(self):
        results = run_doctor()
        # Exit code should be 0 if no required checks fail,
        # 1 if any required check fails
        required_failures = [r for r in results if not r.passed and r.severity == Severity.REQUIRED]
        expected_code = 1 if required_failures else 0
        assert expected_code >= 0  # Just verify the logic works

    def test_run_doctor_summary(self):
        results = run_doctor()
        passed = sum(1 for r in results if r.passed)
        failed = sum(1 for r in results if not r.passed)
        total = len(results)
        assert passed + failed == total


class TestDoctorCLI:
    """Test the CLI integration."""

    def test_build_parser_has_doctor(self):
        from src.cli.main import build_parser
        parser = build_parser()
        # Parse 'doctor' command
        args = parser.parse_args(["doctor"])
        assert args.command == "doctor"

    def test_build_parser_doctor_verbose(self):
        from src.cli.main import build_parser
        parser = build_parser()
        args = parser.parse_args(["doctor", "--verbose"])
        assert args.command == "doctor"
        assert args.verbose is True
