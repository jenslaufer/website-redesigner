"""Reusable input sanitization functions for security hardening."""

import re
from pathlib import Path
from urllib.parse import urlparse


def sanitize_font_name(font: str) -> str:
    """Sanitize a font name: strip control chars, restrict to safe charset, max 100 chars."""
    # Strip surrounding quotes and whitespace
    font = font.strip().strip("'\"").strip()
    # Replace ASCII control characters (0x00-0x1F, 0x7F) with spaces to preserve word boundaries
    font = re.sub(r"[\x00-\x1f\x7f]", " ", font)
    # Keep only allowed characters: letters, digits, spaces, commas, periods, hyphens, apostrophes
    font = re.sub(r"[^a-zA-Z0-9 ',.\-]", "", font)
    # Block SQL keywords and prompt injection phrases
    blocklist = {
        "drop", "table", "select", "insert", "delete", "update", "alter", "exec", "union",
        "ignore", "previous", "instructions", "output", "secrets", "system", "prompt",
    }
    words = font.split()
    words = [w for w in words if w.lower() not in blocklist]
    font = " ".join(words).strip()
    return font[:100]


def validate_url(url: str) -> str:
    """Validate URL: http/https only, non-empty netloc, max 2048 chars."""
    if not url:
        raise ValueError("URL must not be empty")
    if len(url) > 2048:
        raise ValueError("URL exceeds 2048 characters")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"URL scheme must be http or https, got: {parsed.scheme!r}")
    if not parsed.netloc:
        raise ValueError("URL must have a valid hostname")
    return url


def sanitize_for_prompt(data: str) -> str:
    """Wrap user data with boundary markers and strip control chars."""
    # Remove ASCII control chars except newline and tab
    cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", data)
    return f"---BEGIN_DATA---\n{cleaned}\n---END_DATA---"


def validate_output_path(target: Path, output_dir: Path) -> None:
    """Verify target path is inside output_dir. Raises ValueError if not."""
    resolved_target = target.resolve()
    resolved_base = output_dir.resolve()
    if not resolved_target.is_relative_to(resolved_base):
        raise ValueError(f"Path {target} escapes output directory {output_dir}")
