"""Tests for Issue #6: Docker deployment support.

Tests the Docker configuration files and deployment utilities:
- Dockerfile validity and structure
- docker-compose.yml services
- Health check configuration
- Environment variable handling
- .dockerignore existence
- Multi-stage build support
"""

import os
import yaml

import pytest


FINCLAW_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDockerfile:
    def _read_dockerfile(self):
        path = os.path.join(FINCLAW_ROOT, "Dockerfile")
        with open(path) as f:
            return f.read()

    def test_dockerfile_exists(self):
        assert os.path.exists(os.path.join(FINCLAW_ROOT, "Dockerfile"))

    def test_base_image_is_python(self):
        content = self._read_dockerfile()
        assert "FROM python:" in content

    def test_workdir_set(self):
        content = self._read_dockerfile()
        assert "WORKDIR" in content

    def test_port_exposed(self):
        content = self._read_dockerfile()
        assert "EXPOSE" in content
        assert "8080" in content

    def test_healthcheck_configured(self):
        content = self._read_dockerfile()
        assert "HEALTHCHECK" in content

    def test_non_root_user(self):
        content = self._read_dockerfile()
        # Should create and use a non-root user
        assert "USER" in content or "useradd" in content or "adduser" in content

    def test_copies_source(self):
        content = self._read_dockerfile()
        assert "COPY" in content

    def test_installs_dependencies(self):
        content = self._read_dockerfile()
        assert "pip install" in content

    def test_has_multi_stage_or_slim(self):
        content = self._read_dockerfile()
        # Should use slim image or multi-stage
        assert "slim" in content or "AS builder" in content


class TestDockerCompose:
    def _load_compose(self):
        path = os.path.join(FINCLAW_ROOT, "docker-compose.yml")
        with open(path) as f:
            return yaml.safe_load(f)

    def test_compose_exists(self):
        assert os.path.exists(os.path.join(FINCLAW_ROOT, "docker-compose.yml"))

    def test_has_finclaw_service(self):
        config = self._load_compose()
        assert "finclaw" in config.get("services", {})

    def test_has_api_service(self):
        config = self._load_compose()
        assert "finclaw-api" in config.get("services", {})

    def test_api_ports_mapped(self):
        config = self._load_compose()
        api = config["services"]["finclaw-api"]
        assert "ports" in api

    def test_volumes_configured(self):
        config = self._load_compose()
        finclaw = config["services"]["finclaw"]
        assert "volumes" in finclaw

    def test_environment_variables(self):
        config = self._load_compose()
        finclaw = config["services"]["finclaw"]
        assert "environment" in finclaw

    def test_restart_policy(self):
        config = self._load_compose()
        finclaw = config["services"]["finclaw"]
        assert "restart" in finclaw

    def test_healthcheck_in_compose(self):
        config = self._load_compose()
        api = config["services"]["finclaw-api"]
        assert "healthcheck" in api

    def test_resource_limits(self):
        config = self._load_compose()
        api = config["services"]["finclaw-api"]
        # Should have deploy or resource limits
        has_limits = (
            "deploy" in api
            or "mem_limit" in api
            or "cpus" in api
        )
        assert has_limits


class TestDockerIgnore:
    def test_dockerignore_exists(self):
        assert os.path.exists(os.path.join(FINCLAW_ROOT, ".dockerignore"))

    def _read_dockerignore(self):
        path = os.path.join(FINCLAW_ROOT, ".dockerignore")
        with open(path) as f:
            return f.read()

    def test_excludes_git(self):
        content = self._read_dockerignore()
        assert ".git" in content

    def test_excludes_pycache(self):
        content = self._read_dockerignore()
        assert "__pycache__" in content

    def test_excludes_tests(self):
        content = self._read_dockerignore()
        assert "tests" in content or "test" in content

    def test_excludes_venv(self):
        content = self._read_dockerignore()
        assert "venv" in content or ".venv" in content

    def test_excludes_node_modules(self):
        content = self._read_dockerignore()
        assert "node_modules" in content


class TestDeploymentUtils:
    """Test the deployment configuration module."""

    def test_import_deployment_config(self):
        from src.deploy import DeploymentConfig
        config = DeploymentConfig()
        assert config.port > 0
        assert config.host is not None

    def test_default_config(self):
        from src.deploy import DeploymentConfig
        config = DeploymentConfig()
        assert config.port == 8080
        assert config.workers >= 1
        assert config.log_level == "info"

    def test_from_env(self):
        from src.deploy import DeploymentConfig
        os.environ["FINCLAW_PORT"] = "9090"
        os.environ["FINCLAW_WORKERS"] = "4"
        try:
            config = DeploymentConfig.from_env()
            assert config.port == 9090
            assert config.workers == 4
        finally:
            os.environ.pop("FINCLAW_PORT", None)
            os.environ.pop("FINCLAW_WORKERS", None)

    def test_validate_config(self):
        from src.deploy import DeploymentConfig
        config = DeploymentConfig(port=8080, workers=2)
        assert config.validate() is True

    def test_invalid_port(self):
        from src.deploy import DeploymentConfig
        config = DeploymentConfig(port=-1)
        assert config.validate() is False

    def test_generate_env_file(self):
        from src.deploy import DeploymentConfig
        config = DeploymentConfig()
        env_content = config.to_env_string()
        assert "FINCLAW_PORT" in env_content
        assert "FINCLAW_HOST" in env_content
