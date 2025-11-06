"""Test that required dependencies are available."""


def test_httpx_importable():
    """Verify httpx can be imported."""
    import httpx

    assert hasattr(httpx, "AsyncClient")


def test_tenacity_importable():
    """Verify tenacity can be imported."""
    import tenacity

    assert hasattr(tenacity, "retry")


def test_vcrpy_importable():
    """Verify vcrpy can be imported for testing."""
    import vcr

    assert hasattr(vcr, "VCR")
