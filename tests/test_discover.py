"""Tests for discover.py subprocess query handling (security fix #10)."""
import subprocess
import sys
import unittest
from unittest.mock import patch, MagicMock

from discover import search_businesses


class TestSearchBusinessesInjection(unittest.TestCase):
    """Verify query is passed via stdin, never embedded in script source."""

    @patch("discover.subprocess.run")
    def test_query_not_in_script_source(self, mock_run):
        """The query string must not appear in the -c script argument."""
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
        query = "Steuerberater Frankfurt"
        search_businesses(query, max_results=5)

        args, kwargs = mock_run.call_args
        script = args[0][2]  # [python, "-c", <script>]
        assert query not in script, "Query must not be embedded in script source"
        assert kwargs.get("input") == query, "Query must be passed via stdin"

    @patch("discover.subprocess.run")
    def test_injection_payload_not_in_script(self, mock_run):
        """Malicious payloads must not reach the script source."""
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
        payload = '"; import os; os.system("rm -rf /"); "'
        search_businesses(payload, max_results=5)

        args, kwargs = mock_run.call_args
        script = args[0][2]
        assert "os.system" not in script, "Injection payload must not be in script"
        assert kwargs.get("input") == payload, "Payload must be passed safely via stdin"

    @patch("discover.subprocess.run")
    def test_quote_escape_payload(self, mock_run):
        """Quotes and backslashes must not break script syntax."""
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
        payload = """test'); __import__('os').system('id'); print('"""
        search_businesses(payload, max_results=5)

        args, kwargs = mock_run.call_args
        script = args[0][2]
        assert "__import__" not in script
        assert kwargs.get("input") == payload

    @patch("discover.subprocess.run")
    def test_max_results_in_script(self, mock_run):
        """max_results (always int) is still interpolated in the script."""
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
        search_businesses("test", max_results=10)

        args, _ = mock_run.call_args
        script = args[0][2]
        assert "max_results=20" in script  # 10 * 2

    @patch("discover.subprocess.run")
    def test_script_reads_from_stdin(self, mock_run):
        """Script source must use sys.stdin.read() to get the query."""
        mock_run.return_value = MagicMock(returncode=0, stdout="[]", stderr="")
        search_businesses("anything", max_results=5)

        args, _ = mock_run.call_args
        script = args[0][2]
        assert "sys.stdin.read()" in script
