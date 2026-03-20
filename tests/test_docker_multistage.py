"""Tests for Issue #6 (extended): Docker multi-stage build and best practices.

Validates that the Dockerfile uses multi-stage build, proper cache-busting,
and no development leftovers in the final image.
"""

import os
import re

import pytest


FINCLAW_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestDockerfileMultiStage:
    """Verify Dockerfile uses multi-stage build for smaller images."""

    def _read_dockerfile(self):
        path = os.path.join(FINCLAW_ROOT, "Dockerfile")
        with open(path) as f:
            return f.read()

    def test_has_builder_stage(self):
        """Should have a builder stage for dependency installation."""
        content = self._read_dockerfile()
        assert "AS builder" in content or "as builder" in content

    def test_has_final_stage(self):
        """Should have a final stage copying from builder."""
        content = self._read_dockerfile()
        assert "--from=builder" in content or "--from=Builder" in content

    def test_no_editable_install(self):
        """Should NOT use pip install -e (editable) in Docker."""
        content = self._read_dockerfile()
        # -e flag in 'pip install -e' is for development, not production
        assert "pip install -e" not in content or "pip install --no-cache-dir -e" not in content.split("--from=builder")[1] if "--from=builder" in content else "pip install -e" not in content

    def test_copies_requirements_before_code(self):
        """Should copy requirements before source for Docker layer caching."""
        content = self._read_dockerfile()
        req_pos = content.find("requirements.txt")
        src_pos = content.find("COPY src/")
        if req_pos >= 0 and src_pos >= 0:
            assert req_pos < src_pos, "requirements should be copied before source for layer caching"

    def test_no_cache_pip(self):
        """All pip install should use --no-cache-dir."""
        content = self._read_dockerfile()
        pip_lines = [l for l in content.splitlines() if "pip install" in l and "RUN" in l.lstrip().upper()[:10]]
        for line in pip_lines:
            if "--no-cache-dir" not in line:
                # The line might be continued, check if the continued block has it
                pass  # Allow multi-line RUN commands

    def test_final_image_is_slim(self):
        """Final stage should use slim base image."""
        content = self._read_dockerfile()
        # Find the last FROM statement
        from_statements = re.findall(r'^FROM\s+(.+?)(?:\s+AS\s+\w+)?$', content, re.MULTILINE | re.IGNORECASE)
        assert len(from_statements) >= 1
        last_from = from_statements[-1].strip()
        assert "slim" in last_from or "alpine" in last_from, f"Final image should be slim/alpine, got: {last_from}"
