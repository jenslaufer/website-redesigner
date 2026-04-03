"""Tests for CLI argument parsing and process_url."""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from redesign import main, process_url


def test_cli_requires_urls():
    """CLI exits with error when no URLs provided."""
    with pytest.raises(SystemExit) as exc_info:
        with patch("sys.argv", ["redesign.py"]):
            main()
    assert exc_info.value.code == 2


def test_cli_parses_urls():
    """CLI parses positional URL arguments."""
    with patch("sys.argv", ["redesign.py", "https://a.com", "https://b.com"]):
        with patch("redesign.process_url") as mock:
            mock.return_value = Path("/tmp/out")
            main()
    assert mock.call_count == 2
    assert mock.call_args_list[0][0][0] == "https://a.com"
    assert mock.call_args_list[1][0][0] == "https://b.com"


def test_cli_prepends_https():
    """CLI adds https:// prefix when missing."""
    with patch("sys.argv", ["redesign.py", "example.com"]):
        with patch("redesign.process_url") as mock:
            mock.return_value = Path("/tmp/out")
            main()
    mock.assert_called_once()
    assert mock.call_args[0][0] == "https://example.com"


def test_cli_custom_output_dir():
    """CLI respects -o flag."""
    with patch("sys.argv", ["redesign.py", "-o", "/tmp/custom", "https://a.com"]):
        with patch("redesign.process_url") as mock:
            mock.return_value = Path("/tmp/custom/a_com")
            main()
    output_base = mock.call_args[0][1]
    assert str(output_base) == "/tmp/custom"


def test_process_url_full_pipeline(tmp_path):
    """process_url runs scrape → redesign → screenshot with mocked externals."""
    fake_content = {
        "title": "Test Site",
        "description": "A test",
        "url": "https://test.com",
    }
    fake_html = "<html><body>Redesigned</body></html>"

    with patch("redesign.scrape_site") as mock_scrape, \
         patch("redesign.generate_redesign") as mock_redesign, \
         patch("redesign.screenshot_html") as mock_screenshot:

        mock_scrape.return_value = fake_content
        mock_redesign.return_value = fake_html
        mock_screenshot.side_effect = lambda html_path, png_path: Path(png_path).write_bytes(b"fake png")

        # Create the fake original.png that scrape_site would create
        output_dir = tmp_path / "test_com"
        output_dir.mkdir(parents=True)
        (output_dir / "original.png").write_bytes(b"fake png")

        result = process_url("https://test.com", tmp_path)

    assert result == output_dir
    mock_scrape.assert_called_once()
    mock_redesign.assert_called_once_with(fake_content, "https://test.com", output_dir)
    mock_screenshot.assert_called_once()

    # Verify output files
    assert (output_dir / "content.json").exists()
    assert (output_dir / "redesign.html").exists()
    content = json.loads((output_dir / "content.json").read_text())
    assert content["title"] == "Test Site"


def test_process_url_handles_error(tmp_path):
    """process_url propagates errors from scrape_site."""
    with patch("redesign.scrape_site", side_effect=Exception("Network error")):
        with pytest.raises(Exception, match="Network error"):
            process_url("https://fail.com", tmp_path)
