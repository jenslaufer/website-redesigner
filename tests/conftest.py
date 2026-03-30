"""Shared fixtures for tests."""

import pytest
from pathlib import Path


@pytest.fixture
def tmp_output(tmp_path):
    """Provide a temporary output directory with fake job files."""
    job_dir = tmp_path / "test_job"
    job_dir.mkdir()
    # Create fake output files
    (job_dir / "original.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    (job_dir / "redesign.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    (job_dir / "redesign.html").write_text("<html><body>Redesigned</body></html>")
    (job_dir / "content.json").write_text('{"title": "Test"}')
    return tmp_path
