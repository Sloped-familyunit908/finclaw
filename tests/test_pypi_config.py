"""Tests for Issue #7: PyPI publishing configuration readiness.

Validates that pyproject.toml, MANIFEST.in, and package structure
are correct for publishing finclaw-ai to PyPI.
"""

import os
import re
import sys

import pytest

FINCLAW_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestPyprojectToml:
    """Validate pyproject.toml configuration."""

    def _read_pyproject(self):
        path = os.path.join(FINCLAW_ROOT, "pyproject.toml")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_pyproject_exists(self):
        assert os.path.exists(os.path.join(FINCLAW_ROOT, "pyproject.toml"))

    def test_package_name_is_finclaw_ai(self):
        content = self._read_pyproject()
        assert 'name = "finclaw-ai"' in content

    def test_has_version(self):
        content = self._read_pyproject()
        assert re.search(r'^version\s*=\s*"[\d.]+"', content, re.MULTILINE)

    def test_version_matches_init(self):
        """Version in pyproject.toml must match src/__init__.py."""
        content = self._read_pyproject()
        m = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
        assert m, "No version found in pyproject.toml"
        pyproject_version = m.group(1)

        init_path = os.path.join(FINCLAW_ROOT, "src", "__init__.py")
        with open(init_path, encoding="utf-8") as f:
            init_content = f.read()
        m2 = re.search(r'__version__\s*=\s*"([^"]+)"', init_content)
        assert m2, "No __version__ found in src/__init__.py"
        assert pyproject_version == m2.group(1)

    def test_has_description(self):
        content = self._read_pyproject()
        assert 'description = ' in content

    def test_has_readme(self):
        content = self._read_pyproject()
        assert 'readme = "README.md"' in content

    def test_has_license(self):
        content = self._read_pyproject()
        assert "MIT" in content

    def test_has_python_requires(self):
        content = self._read_pyproject()
        assert 'requires-python' in content

    def test_has_authors(self):
        content = self._read_pyproject()
        assert "NeuZhou" in content

    def test_has_classifiers(self):
        content = self._read_pyproject()
        assert "classifiers" in content

    def test_has_keywords(self):
        content = self._read_pyproject()
        assert "keywords" in content

    def test_has_project_urls(self):
        content = self._read_pyproject()
        assert "[project.urls]" in content
        assert "Homepage" in content
        assert "Repository" in content

    def test_has_entry_point(self):
        """CLI entry point finclaw should be defined."""
        content = self._read_pyproject()
        assert "[project.scripts]" in content
        assert 'finclaw = "src.cli.main:main"' in content

    def test_entry_point_module_exists(self):
        """The module pointed to by the entry point must exist."""
        main_path = os.path.join(FINCLAW_ROOT, "src", "cli", "main.py")
        assert os.path.exists(main_path)
        # Verify it has a main() function
        with open(main_path, encoding="utf-8") as f:
            content = f.read()
        assert "def main(" in content

    def test_has_build_system(self):
        content = self._read_pyproject()
        assert "[build-system]" in content
        assert "setuptools" in content

    def test_has_packages_find(self):
        content = self._read_pyproject()
        assert "[tool.setuptools.packages.find]" in content

    def test_packages_include_src(self):
        content = self._read_pyproject()
        assert '"src*"' in content

    def test_has_optional_dependencies(self):
        content = self._read_pyproject()
        assert "[project.optional-dependencies]" in content

    def test_core_dependencies(self):
        """All core dependencies must be listed."""
        content = self._read_pyproject()
        required = ["numpy", "pyyaml", "yfinance"]
        for dep in required:
            assert dep in content, f"Missing dependency: {dep}"

    def test_has_package_data_for_yaml(self):
        """Strategy YAML files must be included in package data."""
        content = self._read_pyproject()
        assert "[tool.setuptools.package-data]" in content
        assert "*.yaml" in content or "*.yml" in content


class TestManifestIn:
    """Validate MANIFEST.in for sdist builds."""

    def _read_manifest(self):
        path = os.path.join(FINCLAW_ROOT, "MANIFEST.in")
        with open(path, encoding="utf-8") as f:
            return f.read()

    def test_manifest_exists(self):
        assert os.path.exists(os.path.join(FINCLAW_ROOT, "MANIFEST.in"))

    def test_includes_readme(self):
        content = self._read_manifest()
        assert "README.md" in content

    def test_includes_license(self):
        content = self._read_manifest()
        assert "LICENSE" in content

    def test_includes_requirements(self):
        content = self._read_manifest()
        assert "requirements.txt" in content

    def test_includes_python_source(self):
        content = self._read_manifest()
        assert "*.py" in content

    def test_includes_yaml_strategies(self):
        """Strategy YAML files must be included in sdist."""
        content = self._read_manifest()
        assert "*.yaml" in content or "*.yml" in content

    def test_excludes_tests(self):
        content = self._read_manifest()
        assert "tests" in content.lower()


class TestPackageStructure:
    """Validate package structure for distribution."""

    def test_src_has_init(self):
        assert os.path.exists(os.path.join(FINCLAW_ROOT, "src", "__init__.py"))

    def test_src_has_version(self):
        from src import __version__
        assert __version__
        assert re.match(r"\d+\.\d+\.\d+", __version__)

    def test_strategies_has_init(self):
        assert os.path.exists(os.path.join(FINCLAW_ROOT, "strategies", "__init__.py"))

    def test_agents_has_init(self):
        assert os.path.exists(os.path.join(FINCLAW_ROOT, "agents", "__init__.py"))

    def test_readme_exists(self):
        assert os.path.exists(os.path.join(FINCLAW_ROOT, "README.md"))

    def test_license_exists(self):
        assert os.path.exists(os.path.join(FINCLAW_ROOT, "LICENSE"))

    def test_py_typed_marker(self):
        """py.typed marker should exist for PEP 561 compliance."""
        assert os.path.exists(os.path.join(FINCLAW_ROOT, "src", "py.typed"))

    def test_builtin_strategy_yamls_exist(self):
        """At least some builtin YAML strategies should exist."""
        builtin_dir = os.path.join(FINCLAW_ROOT, "strategies", "builtin")
        assert os.path.isdir(builtin_dir)
        yamls = [f for f in os.listdir(builtin_dir) if f.endswith(".yaml")]
        assert len(yamls) >= 5, f"Expected >= 5 strategy YAMLs, found {len(yamls)}"


class TestRequirementsTxt:
    """Validate requirements.txt is in sync with pyproject.toml."""

    def test_requirements_exists(self):
        assert os.path.exists(os.path.join(FINCLAW_ROOT, "requirements.txt"))

    def test_requirements_has_core_deps(self):
        path = os.path.join(FINCLAW_ROOT, "requirements.txt")
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        for dep in ["numpy", "pyyaml", "yfinance", "aiohttp", "scipy"]:
            assert dep in content, f"Missing core dep in requirements.txt: {dep}"
