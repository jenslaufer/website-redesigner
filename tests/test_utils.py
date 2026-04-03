"""Tests for shared utility functions."""

from utils import safe_name, score_signals, AUDIT_JS


def test_safe_name_basic():
    assert safe_name("Steuerberater Frankfurt") == "steuerberater_frankfurt"


def test_safe_name_umlauts():
    assert safe_name("Händler München") == "haendler_muenchen"
    assert safe_name("Böse Größe") == "boese_groesse"
    assert safe_name("Straße") == "strasse"


def test_safe_name_empty():
    assert safe_name("") == ""


def test_score_signals_perfect_site():
    """A modern site with all signals should score 0."""
    signals = {
        "hasViewport": True,
        "isHttps": True,
        "usesFlexbox": True,
        "usesGrid": True,
        "usesBootstrap": False,
        "usesWordPress": False,
        "loadTimeMs": 500,
        "hasStructuredData": True,
        "hasOpenGraph": True,
        "copyrightYear": 2025,
    }
    score, reasons = score_signals(signals)
    assert score == 0
    assert reasons == []


def test_score_signals_outdated_site():
    """An outdated site should accumulate points."""
    signals = {
        "hasViewport": False,
        "isHttps": False,
        "usesFlexbox": False,
        "usesGrid": False,
        "usesBootstrap": True,
        "usesWordPress": True,
        "loadTimeMs": 5000,
        "hasStructuredData": False,
        "hasOpenGraph": False,
        "copyrightYear": 2018,
    }
    score, reasons = score_signals(signals)
    assert score == 15
    assert "no mobile viewport" in reasons
    assert "no HTTPS" in reasons
    assert "no modern CSS layout" in reasons


def test_score_signals_no_copyright_year():
    """Missing copyright year should not add points."""
    signals = {
        "hasViewport": True,
        "isHttps": True,
        "usesFlexbox": True,
        "usesGrid": False,
        "loadTimeMs": 1000,
        "hasStructuredData": True,
        "hasOpenGraph": True,
        "copyrightYear": None,
    }
    score, reasons = score_signals(signals)
    assert score == 0


def test_audit_js_is_string():
    """AUDIT_JS should be a non-empty JS string."""
    assert isinstance(AUDIT_JS, str)
    assert "hasViewport" in AUDIT_JS
    assert "copyrightYear" in AUDIT_JS
